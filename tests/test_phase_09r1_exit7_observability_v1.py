from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine import e6_service_composition_root_v1 as service_root
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1
from engine.phase09r_observability_v1 import (
    E6_PRODUCTION_CONFIGURATION_BLOCKED_V1,
    E6_PRODUCTION_IDEMPOTENT_REPLAY_V1,
    E6_PRODUCTION_NO_TRADE_V1,
    E6_PRODUCTION_NO_WORK_DUE_V1,
    E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
    E6_PRODUCTION_STAGE_CONFIGURATION_V1,
    E6_PRODUCTION_STAGE_DISPATCH_V1,
    E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1,
    E6ProductionObservabilityEventV1,
    E6ProductionObservabilityValidationErrorV1,
    emit_e6_production_observability_event_v1,
)
from engine.production_signal_contract_v1 import build_delivery_id
from engine.run_production_signal_v1 import main
from engine.telegram_owner_control_state_v1 import initialize_state, load_state
from test_e6_integrated_orchestrator_v1 import _scenario


SECRET_EXCEPTION = "EXCEPTION_MESSAGE_MARKER_09R1"
SECRET_TOKEN = "TELEGRAM_TOKEN_MARKER_09R1"
SECRET_DESTINATION = "DESTINATION_ID_MARKER_09R1"
SECRET_DEEPSEEK = "DEEPSEEK_KEY_MARKER_09R1"
SECRET_URL = "https://secret-marker.invalid/phase09r1"
SECRET_PAYLOAD = "PAYLOAD_CONTENT_MARKER_09R1"
SECRET_MARKERS = (
    SECRET_EXCEPTION,
    SECRET_TOKEN,
    SECRET_DESTINATION,
    SECRET_DEEPSEEK,
    SECRET_URL,
    SECRET_PAYLOAD,
)
IDENTITY = "a" * 32
NOW = "2026-07-30T13:00:01Z"
SCENARIO_DESTINATION_ID = "isolated-owner-state-test"


class InjectedSecretError(RuntimeError):
    pass


class CountingAdapter:
    def __init__(self, *, failure=None, malformed=False):
        self.rejection_reason = None
        self.malformed_receipt = False
        self.calls = 0
        self.failure = failure
        self.force_malformed = malformed
        self.message_binding_recorder = None

    def __call__(self, payload, *, channel, destination_id):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        if self.force_malformed:
            self.malformed_receipt = True
            raise RuntimeError("malformed fixture receipt")
        if self.message_binding_recorder is not None:
            self.message_binding_recorder(
                payload={
                    "signal_id": payload.publication_envelope.signal_id,
                    "symbol": payload.publication_envelope.canonical_pair,
                    "mode": payload.publication_envelope.mode,
                },
                destination_id=str(destination_id),
                message_id=1,
                timestamp=NOW,
            )
        return {
            "channel": channel,
            "destination_id": destination_id,
            "external_delivery_id": "message-1",
            "delivered_at": NOW,
        }


def _authorization():
    return controlled.ControlledProductionSignalCycleAuthorizationV1(
        **{name: True for name, _ in controlled._GATES}
    )


def _assert_scenario_delivery_identity(scenario):
    request = scenario["request"]
    assert request.publication_delivery_id == build_delivery_id(
        signal_id=request.publication_signal_id,
        channel="TELEGRAM",
        destination_id=SCENARIO_DESTINATION_ID,
        publication_payload_hash=request.publication_payload_hash,
    )


def _invoke_main(tmp_path, capsys, *, adapter=None, runner=None, name):
    scenario = _scenario(tmp_path, name=name)
    _assert_scenario_delivery_identity(scenario)
    control_path = tmp_path / f"{name}-owner-control.json"
    initialize_state(control_path, timestamp=NOW)
    selected_adapter = CountingAdapter() if adapter is None else adapter
    runtime_calls = []
    constructor_calls = []
    config = SimpleNamespace(
        bot_token=SECRET_TOKEN,
        max_response_chars=4000,
    )

    def runtime_factory(*, outcome_invocation_id):
        runtime_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id=SCENARIO_DESTINATION_ID,
        )

    def adapter_factory(value, **kwargs):
        assert value is config
        constructor_calls.append(value)
        selected_adapter.message_binding_recorder = kwargs[
            "message_binding_recorder"
        ]
        return selected_adapter

    options = {}
    if runner is not None:
        options["e6_service_cycle_runner"] = runner
    exit_code = main(
        outcome_invocation_id=IDENTITY,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment={
            "TELEGRAM_DESTINATION_ID": SCENARIO_DESTINATION_ID,
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
        },
        telegram_config_loader=lambda _environment: config,
        telegram_delivery_adapter_factory=adapter_factory,
        **options,
    )
    captured = capsys.readouterr()
    assert runtime_calls == [IDENTITY]
    assert constructor_calls == [config]
    return (
        exit_code,
        captured.out,
        captured.err,
        selected_adapter,
        scenario,
        control_path,
    )


def _assert_single_event(
    stderr,
    *,
    stage,
    code,
    boundary,
    exception_class="E6ServiceCycleTerminalResult",
):
    lines = stderr.splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert list(event) == [
        "event",
        "schema_version",
        "exit_code",
        "failure_code",
        "failure_stage",
        "exception_class",
        "telegram_boundary_reached",
    ]
    assert event == {
        "event": "PHASE09R_EXIT7",
        "schema_version": 1,
        "exit_code": 7,
        "failure_code": code,
        "failure_stage": stage,
        "exception_class": exception_class,
        "telegram_boundary_reached": boundary,
    }
    assert stderr.endswith("\n")
    return event


def _terminal_runner(stage, code):
    def run(*, root, request):
        return service_root._result(
            root=root,
            disposition=service_root.HOLD,
            terminal_stage=stage,
            reason_code=code,
        )

    return run


def _post_attempt_terminal_runner(code):
    def run(*, root, request):
        delivered = service_root.run_e6_service_cycle_v1(
            root=root,
            request=request,
        )
        assert delivered.disposition == service_root.DELIVERED
        assert delivered.telegram_attempt_count == 1
        return replace(
            delivered,
            disposition=service_root.HOLD,
            terminal_stage=service_root.STAGE_5_ONE_TELEGRAM_ATTEMPT,
            reason_code=code,
            delivery_completion_disposition=code,
        )

    return run


def test_master_setup_failure_is_sanitized_before_adapter(tmp_path, capsys):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_terminal_runner(
            service_root.STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            service_root.E6_ORCHESTRATOR_FAILED,
        ),
        name="master-setup-failure",
    )
    exit_code, stdout, stderr, adapter, scenario, _control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
        code=service_root.E6_ORCHESTRATOR_FAILED,
        boundary="NO",
    )
    assert adapter.calls == 0
    assert active.load_ledger(scenario["ports"].active_ledger_path)[
        "ledger_revision"
    ] == 0


def test_source_envelope_failure_is_sanitized_before_adapter(tmp_path, capsys):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_terminal_runner(
            service_root.STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY,
            service_root.E6_ELIGIBILITY_OR_LINEAGE_INVALID,
        ),
        name="lineage-failure",
    )
    exit_code, stdout, stderr, adapter, _scenario_value, _control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_3_REQUIRE_EXACT_E6_ELIGIBILITY,
        code=service_root.E6_ELIGIBILITY_OR_LINEAGE_INVALID,
        boundary="NO",
    )
    assert adapter.calls == 0


def test_intent_persistence_failure_is_sanitized_without_delivery(
    tmp_path, capsys
):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_terminal_runner(
            service_root.STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
            service_root.E6_DELIVERY_REPLAY_CONFLICT,
        ),
        name="pre-delivery-persistence",
    )
    exit_code, stdout, stderr, adapter, _scenario_value, _control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
        code=service_root.E6_DELIVERY_REPLAY_CONFLICT,
        boundary="NO",
    )
    assert adapter.calls == 0
    for marker in SECRET_MARKERS:
        assert marker not in stdout + stderr


def test_completion_persistence_failure_is_yes_and_never_retries(
    tmp_path, capsys
):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_post_attempt_terminal_runner(
            "PUBLICATION_COMPLETION_PERSIST_FAILED"
        ),
        name="completion-persistence",
    )
    exit_code, stdout, stderr, adapter, _scenario_value, control_path = result
    assert exit_code == 7
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_5_ONE_TELEGRAM_ATTEMPT,
        code="PUBLICATION_COMPLETION_PERSIST_FAILED",
        boundary="YES",
    )
    assert adapter.calls == 1
    assert load_state(control_path)["signal_message_bindings"] == {}
    for marker in SECRET_MARKERS:
        assert marker not in stdout + stderr


def test_final_readback_failure_is_yes_and_never_retries(tmp_path, capsys):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_post_attempt_terminal_runner("PUBLICATION_READBACK_FAILED"),
        name="readback-failure",
    )
    exit_code, stdout, stderr, adapter, _scenario_value, control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_5_ONE_TELEGRAM_ATTEMPT,
        code="PUBLICATION_READBACK_FAILED",
        boundary="YES",
    )
    assert adapter.calls == 1
    assert load_state(control_path)["signal_message_bindings"] == {}
    assert SECRET_EXCEPTION not in stderr


@pytest.mark.parametrize(
    ("run_out", "stage", "code"),
    [
        ({}, "E6_SERVICE_CYCLE_RESULT", "SERVICE_INVOCATION_INVALID"),
        (
            {"production_signal_out": ["not", "a", "mapping"]},
            "E6_SERVICE_CYCLE_RESULT",
            "SERVICE_INVOCATION_INVALID",
        ),
        (
            {"production_signal_out": {"publication": []}},
            "E6_SERVICE_CYCLE_RESULT",
            "SERVICE_INVOCATION_INVALID",
        ),
        (
            {"production_signal_out": {"status": "UNRECOGNIZED"}},
            "E6_SERVICE_CYCLE_RESULT",
            "SERVICE_INVOCATION_INVALID",
        ),
    ],
)
def test_entrypoint_outcome_classification(run_out, stage, code, tmp_path, capsys):
    def invalid_runner(*, root, request):
        return run_out

    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=invalid_runner,
        name=f"invalid-result-{len(str(run_out))}",
    )
    exit_code, stdout, stderr, adapter, _scenario_value, _control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=stage,
        code=code,
        boundary="UNKNOWN",
        exception_class="TypeError",
    )
    assert adapter.calls == 0
    assert "Traceback" not in stderr


def test_successful_delivery_preserves_completed_publication(tmp_path, capsys):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        name="successful-delivery",
    )
    exit_code, stdout, stderr, adapter, scenario, control_path = result
    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""
    assert adapter.calls == 1
    state = load_state(control_path)
    assert len(state["signal_message_bindings"]) == 1
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)
    signal = ledger["signals"][scenario["request"].publication_signal_id]
    assert signal["state"] == active.PUBLISHED_PENDING_ENTRY
    assert active.inspect_capacity(ledger)["total_active"] == 0
    assert not any(
        item["state"] == active.ENTRY_ACTIVE
        for item in ledger["signals"].values()
    )


def test_no_trade_preserves_evaluation_without_adapter(tmp_path, capsys):
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=CountingAdapter(),
        runner=_terminal_runner(
            service_root.STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
            service_root.E6_ORCHESTRATOR_TERMINAL,
        ),
        name="nonpublication-hold",
    )
    exit_code, stdout, stderr, adapter, scenario, _control_path = result
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage=service_root.STAGE_2_RUN_CONTROLLED_E6_ORCHESTRATION,
        code=service_root.E6_ORCHESTRATOR_TERMINAL,
        boundary="NO",
    )
    assert adapter.calls == 0
    assert active.load_ledger(scenario["ports"].active_ledger_path)[
        "ledger_revision"
    ] == 0


def test_delivery_failed_remains_exit5_without_observability(tmp_path, capsys):
    adapter = CountingAdapter(
        failure=InjectedSecretError(
            "|".join((SECRET_EXCEPTION, SECRET_TOKEN, SECRET_PAYLOAD))
        )
    )
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=adapter,
        name="delivery-failed",
    )
    exit_code, stdout, stderr, selected, scenario, control_path = result
    assert exit_code == 5
    assert stdout == ""
    assert stderr == ""
    assert selected.calls == 1
    assert load_state(control_path)["signal_message_bindings"] == {}
    ledger = active.load_ledger(scenario["ports"].active_ledger_path)
    assert ledger["signals"][scenario["request"].publication_signal_id][
        "state"
    ] == active.PUBLISHED_PENDING_ENTRY
    for marker in SECRET_MARKERS:
        assert marker not in stdout + stderr


@pytest.mark.parametrize(
    ("adapter_field", "adapter_value", "expected_exit"),
    [
        ("rejection_reason", "QUOTA_EXHAUSTED", 5),
        ("rejection_reason", "SLOTS_FULL", 5),
        ("malformed_receipt", True, 6),
    ],
)
def test_quota_slot_and_malformed_receipt_exit_codes_are_unchanged(
    adapter_field,
    adapter_value,
    expected_exit,
    tmp_path,
    capsys,
):
    adapter = CountingAdapter(malformed=adapter_field == "malformed_receipt")
    if adapter_field == "rejection_reason":
        runner = _terminal_runner(
            service_root.STAGE_4_DELIVERY_IDEMPOTENCY_PREFLIGHT,
            adapter_value,
        )
    else:
        runner = None
    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=adapter,
        runner=runner,
        name=f"exit-code-{adapter_value}",
    )
    exit_code, stdout, stderr, selected, _scenario_value, control_path = result
    assert exit_code == expected_exit
    assert selected.calls == (1 if expected_exit == 6 else 0)
    assert stdout == ""
    assert stderr == ""
    assert load_state(control_path)["signal_message_bindings"] == {}


def test_configuration_exit2_has_no_observability(capsys):
    assert main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_unclassified_exception_event_schema_and_secret_leak_barrier(
    tmp_path, capsys
):
    adapter = CountingAdapter()

    def fail_runner(*, root, request):
        raise InjectedSecretError("|".join(SECRET_MARKERS))

    result = _invoke_main(
        tmp_path,
        capsys,
        adapter=adapter,
        runner=fail_runner,
        name="unclassified-exception",
    )
    exit_code, stdout, stderr, selected, _scenario_value, _control_path = result
    assert exit_code == 7
    event = _assert_single_event(
        stderr,
        stage="E6_SERVICE_CYCLE_INVOCATION",
        code="PRODUCTION_SIGNAL_SERVICE_FAILED",
        boundary="UNKNOWN",
        exception_class="InjectedSecretError",
    )
    assert event["exception_class"] == "InjectedSecretError"
    assert selected.calls == 0
    assert stdout == ""
    for marker in SECRET_MARKERS:
        assert marker not in stdout + stderr


def _production_event(event_name, **changes):
    values = {
        "schema_version": E6_PRODUCTION_OBSERVABILITY_SCHEMA_V1,
        "event_name": event_name,
        "outcome_invocation_id": IDENTITY,
        "observed_at": "2026-08-03T08:00:00Z",
        "mode": None,
        "due_window_occurrence_id": None,
        "stage": E6_PRODUCTION_STAGE_DISPATCH_V1,
        "reason_code": "NO_MODE_JOB_DUE",
        "source_reason_code": None,
        "evidence_sha256": "a" * 64,
        "provider_attempt_count": 0,
        "telegram_attempt_count": 0,
        "retry_count": 0,
    }
    if event_name == E6_PRODUCTION_CONFIGURATION_BLOCKED_V1:
        values.update(
            stage=E6_PRODUCTION_STAGE_CONFIGURATION_V1,
            reason_code="ACTIVATION_CONFIGURATION_INVALID",
        )
    elif event_name == E6_PRODUCTION_IDEMPOTENT_REPLAY_V1:
        values.update(
            mode="SWING",
            due_window_occurrence_id="e6dw1:" + "b" * 64,
            reason_code="DUE_WINDOW_ALREADY_HANDLED",
        )
    elif event_name == E6_PRODUCTION_NO_TRADE_V1:
        values.update(
            mode="INTRADAY",
            due_window_occurrence_id="e6dw1:" + "a" * 64,
            stage=E6_PRODUCTION_STAGE_PRODUCTION_INPUT_V1,
            reason_code="E2_NO_ELIGIBLE_CANDIDATE",
            source_reason_code="SCANNER_ELIGIBLE_SET_EMPTY",
        )
    values.update(changes)
    return E6ProductionObservabilityEventV1(**values)


@pytest.mark.parametrize(
    ("event_name", "route"),
    (
        (E6_PRODUCTION_CONFIGURATION_BLOCKED_V1, "stderr"),
        (E6_PRODUCTION_NO_WORK_DUE_V1, "stdout"),
        (E6_PRODUCTION_NO_TRADE_V1, "stdout"),
        (E6_PRODUCTION_IDEMPOTENT_REPLAY_V1, "stdout"),
    ),
)
def test_production_observability_emits_one_canonical_record_to_fixed_route(
    event_name, route, capsys
):
    event = _production_event(event_name)
    emit_e6_production_observability_event_v1(event)
    captured = capsys.readouterr()
    selected = captured.err if route == "stderr" else captured.out
    other = captured.out if route == "stderr" else captured.err
    assert selected == event.canonical_json() + "\n"
    assert other == ""
    assert len(selected.splitlines()) == 1
    assert json.loads(selected) == event.to_mapping()
    assert event.canonical_json() == event.canonical_json()


def test_production_observability_schema_contains_only_fixed_nonsecret_fields(
    capsys,
):
    event = _production_event(E6_PRODUCTION_NO_TRADE_V1)
    assert list(event.to_mapping()) == [
        "schema_version",
        "event_name",
        "outcome_invocation_id",
        "observed_at",
        "mode",
        "due_window_occurrence_id",
        "stage",
        "reason_code",
        "source_reason_code",
        "evidence_sha256",
        "provider_attempt_count",
        "telegram_attempt_count",
        "retry_count",
    ]
    assert event.provider_attempt_count == 0
    assert event.telegram_attempt_count == 0
    assert event.retry_count == 0
    forbidden = {
        "destination_id",
        "token",
        "credential",
        "path",
        "request",
        "response",
        "prompt",
        "exception",
    }
    assert forbidden.isdisjoint(event.to_mapping())

    replay = _production_event(E6_PRODUCTION_IDEMPOTENT_REPLAY_V1)
    no_work = _production_event(E6_PRODUCTION_NO_WORK_DUE_V1)
    assert event.due_window_occurrence_id == "e6dw1:" + "a" * 64
    assert replay.due_window_occurrence_id == "e6dw1:" + "b" * 64
    assert no_work.due_window_occurrence_id is None

    invalid_occurrences = (
        "E6DW1:" + "a" * 64,
        "e6dw1:" + "A" * 64,
        "e6dw1:" + "a" * 63,
        "e6dw1:" + "a" * 65,
        "e6dw2:" + "a" * 64,
        " e6dw1:" + "a" * 64,
        "e6dw1:" + "a" * 64 + " ",
        "e6dw1:" + "a" * 64 + "X",
        "",
        0,
    )
    for event_name in (
        E6_PRODUCTION_NO_TRADE_V1,
        E6_PRODUCTION_IDEMPOTENT_REPLAY_V1,
    ):
        for occurrence_id in invalid_occurrences:
            with pytest.raises(E6ProductionObservabilityValidationErrorV1):
                _production_event(
                    event_name,
                    due_window_occurrence_id=occurrence_id,
                )

    for change in (
        {"stage": "production_input"},
        {"reason_code": "e2_no_eligible_candidate"},
        {"source_reason_code": "scanner_eligible_set_empty"},
    ):
        with pytest.raises(E6ProductionObservabilityValidationErrorV1):
            _production_event(E6_PRODUCTION_NO_TRADE_V1, **change)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize(
    "change",
    (
        {"schema_version": "wrong"},
        {"outcome_invocation_id": "A" * 32},
        {"observed_at": "2026-08-03T08:00:00.1Z"},
        {"evidence_sha256": "A" * 64},
        {"provider_attempt_count": 1},
        {"telegram_attempt_count": True},
        {"retry_count": -1},
        {"stage": "UNKNOWN"},
        {"reason_code": "UNKNOWN"},
    ),
)
def test_invalid_production_event_fields_are_rejected(change):
    with pytest.raises(E6ProductionObservabilityValidationErrorV1):
        _production_event(E6_PRODUCTION_NO_TRADE_V1, **change)


def test_secret_like_source_reason_is_rejected_without_rendering_value(capsys):
    marker = "PRIVATE_KEY_SECRET_MARKER"
    with pytest.raises(E6ProductionObservabilityValidationErrorV1) as raised:
        _production_event(
            E6_PRODUCTION_NO_TRADE_V1,
            source_reason_code=marker,
        )
    assert marker not in str(raised.value) + repr(raised.value)
    captured = capsys.readouterr()
    assert marker not in captured.out + captured.err


def test_emitter_revalidates_mutated_event_and_does_not_convert_failure_to_success(
    capsys,
):
    event = _production_event(E6_PRODUCTION_NO_WORK_DUE_V1)
    object.__setattr__(event, "retry_count", 1)
    with pytest.raises(E6ProductionObservabilityValidationErrorV1):
        emit_e6_production_observability_event_v1(event)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
