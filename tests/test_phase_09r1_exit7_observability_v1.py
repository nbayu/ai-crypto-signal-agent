from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from engine import active_signal_ledger_v1 as active
from engine import controlled_production_signal_cycle_v1 as controlled
from engine import e6_service_composition_root_v1 as service_root
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1
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
