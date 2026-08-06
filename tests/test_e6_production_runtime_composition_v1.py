from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from types import SimpleNamespace

import pytest

import engine.e6_production_runtime_composition_v1 as module
from engine.e6_activation_configuration_v1 import (
    E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
    E6ActivationConfigurationV1,
    load_e6_activation_configuration_v1,
)
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
)
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    build_e6_deployment_state_binding_v1,
)
from engine.e6_production_cycle_input_v1 import (
    E6NoTradeCycleRequestV1,
    MODE_JOB_SELECTED,
    build_e6_production_dispatch_decision_v1,
)
from engine.e6_production_e3_bridge_v1 import E6ProductionE3CandidateV1
from engine.e6_production_market_acquisition_v1 import (
    E6ProductionBinancePublicMarketPortV1,
)
from engine.e6_production_runtime_composition_v1 import (
    E6ProductionRuntimeCompositionV1,
    E6ProductionRuntimeCompositionValidationErrorV1,
    build_e6_production_runtime_composition_v1,
    build_e6_production_selected_job_input_v1,
)
from engine.e6_production_technical_evaluator_v1 import (
    E6ProductionTechnicalEvaluatorV1,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_scan_execution_evidence_v1 import ModeExecutionCandidateRowV1


COMMIT = "a" * 40
TREE = "b" * 40
CHECKPOINT = "c" * 40
GATE_KEYS = (
    ("activation_gate", "E6_ACTIVATION_GATE"),
    ("workload_gate", "E6_WORKLOAD_GATE"),
    ("credential_gate", "E6_CREDENTIAL_GATE"),
    ("network_gate", "E6_NETWORK_GATE"),
    ("publication_gate", "E6_PUBLICATION_GATE"),
    ("telegram_publication_gate", "E6_TELEGRAM_PUBLICATION_GATE"),
)


def _mapping(**changes: str) -> dict[str, str]:
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile="CANDIDATE_CANARY", release_commit=COMMIT
    )
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
        "E6_DEPLOYMENT_BINDING_VERSION": E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
        "E6_DEPLOYMENT_PROFILE": binding.deployment_profile.value,
        "E6_RELEASE_COMMIT": binding.release_commit,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": CHECKPOINT,
        "E6_RELEASE_ROOT": binding.release_root,
        "E6_SERVICE_UNIT": binding.service_unit,
        "E6_TIMER_UNIT": binding.timer_unit,
        "E6_STATE_ROOT": binding.state_root,
        "E6_OWNER_STATE_ROOT": binding.owner_state_root,
        "E6_LEDGER_ROOT": binding.ledger_root,
        "E6_ACTIVE_SIGNAL_LEDGER_PATH": binding.active_ledger_path,
        "E6_OWNER_CONTROL_STATE_PATH": binding.owner_state_path,
        "E6_PUBLICATION_ROOT": binding.publication_root,
        "E6_OPERATIONAL_ARTIFACT_ROOT": binding.operational_artifact_root,
        "E6_RUNTIME_ROOT": binding.runtime_root,
        "E6_RUNTIME_LOCK_PATH": binding.runtime_lock,
        "E6_CACHE_ROOT": binding.cache_root,
        "E6_LOG_POLICY": binding.log_policy,
        "E6_CONTROL_ROOT": binding.control_root,
        "E6_RELEASE_REFERENCE_PATH": binding.install_pointer,
        "E6_ROLLBACK_REFERENCE_PATH": binding.rollback_pointer,
        "E6_ACCEPTED_RELEASE_MARKER_PATH": binding.accepted_marker,
        "E6_KILL_SWITCH_PATH": binding.kill_switch,
        "E6_CONFIGURATION_ROOT": binding.configuration_root,
        "E6_CREDENTIAL_METADATA_PATH": binding.credential_metadata_path,
        "E6_ACTIVATION_CONFIGURATION_PATH": binding.activation_configuration_path,
        "E6_SERVICE_USER": binding.service_user,
        "E6_SERVICE_GROUP": binding.service_group,
        "E6_PROVIDER_BINDING_VERSION": E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
        "E6_PROVIDER_BINDING_SHA256": E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
        "E6_RUNTIME_ENABLED": "false",
        "E6_PROVIDER_ENABLED": "false",
        "E6_ACTIVATION_GATE": "false",
        "E6_WORKLOAD_GATE": "false",
        "E6_CREDENTIAL_GATE": "false",
        "E6_NETWORK_GATE": "false",
        "E6_PUBLICATION_GATE": "false",
        "E6_TELEGRAM_PUBLICATION_GATE": "false",
        "E6_AUTOMATIC_RETRY_COUNT": "0",
        "E6_PROVIDER_SUBSTITUTION_ENABLED": "false",
        "E6_PROMPT_REPAIR_ENABLED": "false",
        "E6_STALE_REVIEW_REUSE_ENABLED": "false",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED": "false",
    }
    values.update(changes)
    return values


def test_module_is_passive_and_has_no_external_constructor_surface() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported.intersection(
        {"os", "pathlib", "random", "requests", "socket", "subprocess", "telegram"}
    )
    for marker in (
        "os.environ",
        "getenv(",
        "open(",
        "datetime.now",
        "provider_transport",
        "telegram_delivery",
        "service_cycle",
        "create_order",
    ):
        assert marker not in source


def test_exact_45_key_loader_runs_once_and_composition_is_immutable(capsys) -> None:
    configuration = _mapping()
    assert len(configuration) == 45
    calls: list[object] = []

    def loader(value):
        calls.append(value)
        return load_e6_activation_configuration_v1(value)

    composition = build_e6_production_runtime_composition_v1(
        configuration=configuration,
        activation_loader=loader,
    )
    assert calls == [configuration]
    assert is_dataclass(E6ProductionRuntimeCompositionV1)
    assert E6ProductionRuntimeCompositionV1.__dataclass_params__.frozen is True
    assert "__dict__" not in E6ProductionRuntimeCompositionV1.__slots__
    assert tuple(field.name for field in fields(composition)) == (
        "activation_configuration",
        "deployment_binding",
        "e6_enabled",
        "authorization",
        "e6_activation_authorized",
        "network_authorized",
        "publication_authorized",
    )
    assert composition.deployment_binding is composition.activation_configuration.deployment_binding
    with pytest.raises(FrozenInstanceError):
        composition.e6_enabled = True  # type: ignore[misc]
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert configuration["E6_CREDENTIAL_METADATA_PATH"] not in repr(composition)


@pytest.mark.parametrize("field,key", GATE_KEYS)
def test_all_six_gates_map_independently_without_implication(
    field: str, key: str
) -> None:
    composition = build_e6_production_runtime_composition_v1(
        configuration=_mapping(**{key: "true"})
    )
    assert getattr(composition.authorization, field) is True
    assert sum(
        getattr(composition.authorization, name) for name, _key in GATE_KEYS
    ) == 1
    assert composition.e6_enabled is False
    assert composition.e6_activation_authorized is (field == "activation_gate")
    assert composition.network_authorized is (field == "network_gate")
    assert composition.publication_authorized is (field == "publication_gate")


@pytest.mark.parametrize(
    "runtime_enabled,provider_enabled,expected",
    (
        ("false", "false", False),
        ("true", "false", False),
        ("false", "true", False),
        ("true", "true", True),
    ),
)
def test_runtime_enablement_is_exact_runtime_provider_conjunction(
    runtime_enabled: str, provider_enabled: str, expected: bool
) -> None:
    composition = build_e6_production_runtime_composition_v1(
        configuration=_mapping(
            E6_RUNTIME_ENABLED=runtime_enabled,
            E6_PROVIDER_ENABLED=provider_enabled,
        )
    )
    assert composition.e6_enabled is expected
    assert all(
        getattr(composition.authorization, field) is False for field, _ in GATE_KEYS
    )


def test_scalar_decisions_duplicate_only_their_exact_source_gate() -> None:
    composition = build_e6_production_runtime_composition_v1(
        configuration=_mapping(
            E6_ACTIVATION_GATE="true",
            E6_NETWORK_GATE="true",
            E6_PUBLICATION_GATE="true",
        )
    )
    assert composition.e6_activation_authorized is True
    assert composition.network_authorized is True
    assert composition.publication_authorized is True
    assert composition.authorization.workload_gate is False
    assert composition.authorization.credential_gate is False
    assert composition.authorization.telegram_publication_gate is False


def test_malformed_mapping_and_non_authoritative_loader_output_fail_closed() -> None:
    with pytest.raises(Exception):
        build_e6_production_runtime_composition_v1(configuration={})
    with pytest.raises(E6ProductionRuntimeCompositionValidationErrorV1):
        build_e6_production_runtime_composition_v1(
            configuration=_mapping(), activation_loader=lambda _value: object()
        )
    with pytest.raises(E6ProductionRuntimeCompositionValidationErrorV1):
        build_e6_production_runtime_composition_v1(  # type: ignore[arg-type]
            configuration=[], activation_loader=load_e6_activation_configuration_v1
        )


def test_activation_object_is_authoritative_and_safety_invariants_survive() -> None:
    composition = build_e6_production_runtime_composition_v1(
        configuration=_mapping()
    )
    assert type(composition.activation_configuration) is E6ActivationConfigurationV1
    activation = composition.activation_configuration
    assert activation.automatic_retry_count == 0
    assert activation.provider_substitution_enabled is False
    assert activation.prompt_repair_enabled is False
    assert activation.stale_review_reuse_enabled is False
    assert activation.automated_exchange_trading_enabled is False


class _EmptyPublicClient:
    def load_markets(self):
        return {}

    def fetch_tickers(self):
        return {}


class _OneMarketPublicClient:
    def load_markets(self):
        return {
            "BTC/USDT:USDT": {
                "active": True,
                "quote": "USDT",
                "settle": "USDT",
                "type": "swap",
                "linear": True,
                "swap": True,
                "precision": {"price": "0.1"},
                "id": "BTCUSDT",
            }
        }

    def fetch_tickers(self):
        return {"BTC/USDT:USDT": {"quoteVolume": 1000.0}}


def _authorized_composition() -> E6ProductionRuntimeCompositionV1:
    # M11C_R4R2_CANDIDATE_AUTHORIZED_COMPOSITION_PROFILE_V1
    values = {
        "E6_RUNTIME_ENABLED": "true",
        "E6_PROVIDER_ENABLED": "true",
        "E6_ACTIVATION_GATE": "true",
        "E6_WORKLOAD_GATE": "true",
        "E6_CREDENTIAL_GATE": "true",
        "E6_NETWORK_GATE": "true",
        "E6_PUBLICATION_GATE": "false",
        "E6_TELEGRAM_PUBLICATION_GATE": "false",
    }
    return build_e6_production_runtime_composition_v1(
        configuration=_mapping(**values)
    )


def _selected_decision():
    return build_e6_production_dispatch_decision_v1(
        source_commit=COMMIT,
        outcome_invocation_id="d" * 32,
        observed_at="2026-07-30T00:00:00Z",
        disposition=MODE_JOB_SELECTED,
        reason_code=MODE_JOB_SELECTED,
        mode="SWING",
        due_job_id="SWING:BASE_EVALUATION",
        due_window_occurrence_id="e6dw1:" + "e" * 64,
        mode_lineage_sha256=build_mode_audit_lineage("SWING").lineage_sha256,
    )


def test_selected_job_boundary_returns_truthful_empty_market_no_trade_once() -> None:
    client = _EmptyPublicClient()
    factories = []
    port = E6ProductionBinancePublicMarketPortV1(
        client_factory=lambda: factories.append(client) or client
    )
    result = build_e6_production_selected_job_input_v1(
        composition=_authorized_composition(),
        dispatch_decision=_selected_decision(),
        observed_at="2026-07-30T00:00:00Z",
        market_acquisition_port=port,
    )
    assert type(result) is E6NoTradeCycleRequestV1
    assert result.reason_code == "EMPTY_ELIGIBLE_MARKET"
    assert factories == [client]
    assert result.provider_attempt_count == result.telegram_attempt_count == 0


def test_selected_job_boundary_rejects_partial_authorization_before_market() -> None:
    calls = []
    port = E6ProductionBinancePublicMarketPortV1(
        client_factory=lambda: calls.append("client") or _EmptyPublicClient()
    )
    with pytest.raises(E6ProductionRuntimeCompositionValidationErrorV1):
        build_e6_production_selected_job_input_v1(
            composition=build_e6_production_runtime_composition_v1(
                configuration=_mapping()
            ),
            dispatch_decision=_selected_decision(),
            observed_at="2026-07-30T00:00:00Z",
            market_acquisition_port=port,
        )
    assert calls == []


def test_selected_job_boundary_runs_one_scan_and_returns_one_typed_e3_bundle(
    monkeypatch,
) -> None:
    client = _OneMarketPublicClient()
    port = E6ProductionBinancePublicMarketPortV1(client_factory=lambda: client)
    calls = []
    candidate = ModeExecutionCandidateRowV1.__new__(ModeExecutionCandidateRowV1)
    object.__setattr__(candidate, "candidate_id", "e2c1:" + "1" * 64)
    object.__setattr__(candidate, "symbol", "BTC/USDT:USDT")
    evidence = SimpleNamespace(
        candidate_id=candidate.candidate_id,
        evidence_sha256="2" * 64,
    )
    output = E6ProductionE3CandidateV1.__new__(E6ProductionE3CandidateV1)
    execution = SimpleNamespace(execution_sha256="3" * 64)
    plan = SimpleNamespace(plan_sha256="4" * 64)

    monkeypatch.setattr(
        E6ProductionBinancePublicMarketPortV1,
        "fetch_executable_quote",
        lambda self, **_values: calls.append("quote") or object(),
    )

    result = build_e6_production_selected_job_input_v1(
        composition=_authorized_composition(),
        dispatch_decision=_selected_decision(),
        observed_at="2026-07-30T00:00:00Z",
        market_acquisition_port=port,
        scan_request_builder=lambda **_values: calls.append("request") or object(),
        scan_plan_builder=lambda **_values: calls.append("plan") or plan,
        scan_executor=lambda **_values: calls.append("scan") or execution,
        technical_evaluator_factory=E6ProductionTechnicalEvaluatorV1,
        technical_result_builder=lambda **_values: SimpleNamespace(
            final_top5=(candidate,),
            evidence_registry=(evidence,),
        ),
        e3_candidate_builder=lambda **_values: calls.append("e3") or output,
    )
    assert result is output
    assert calls == ["request", "plan", "scan", "quote", "e3"]


def test_p2_extension_has_no_e4_e5_service_publication_or_dispatch_activation() -> None:
    source = inspect.getsource(module)
    for marker in (
        "e4_",
        "e5_",
        "service_cycle",
        "telegram_delivery",
        "create_order",
        "_run_production_module_v1",
    ):
        assert marker not in source.casefold()

# M11C_R3_PROFILE_AWARE_RUNTIME_AUTHORIZATION_V1
def _m11c_r3_runtime_composition(
    *,
    deployment_profile,
    publication_authorized,
    publication_gate,
    telegram_publication_gate,
):
    from types import SimpleNamespace

    return SimpleNamespace(
        deployment_binding=SimpleNamespace(
            deployment_profile=deployment_profile,
        ),
        e6_enabled=True,
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=publication_authorized,
        authorization=SimpleNamespace(
            activation_gate=True,
            workload_gate=True,
            credential_gate=True,
            network_gate=True,
            publication_gate=publication_gate,
            telegram_publication_gate=telegram_publication_gate,
        ),
    )


def _m11c_r3_is_fully_authorized(composition):
    from engine.e6_production_runtime_composition_v1 import (
        _fully_authorized,
    )

    return _fully_authorized(composition)


def test_m11c_r3_profile_publication_authorization_matrix():
    expected_states = {
        "PRODUCTION": (True, True, True),
        "CANDIDATE_CANARY": (False, False, False),
    }

    for profile, expected_state in expected_states.items():
        for publication_authorized in (False, True):
            for publication_gate in (False, True):
                for telegram_gate in (False, True):
                    composition = _m11c_r3_runtime_composition(
                        deployment_profile=profile,
                        publication_authorized=publication_authorized,
                        publication_gate=publication_gate,
                        telegram_publication_gate=telegram_gate,
                    )
                    expected = (
                        publication_authorized,
                        publication_gate,
                        telegram_gate,
                    ) == expected_state
                    assert (
                        _m11c_r3_is_fully_authorized(composition)
                        is expected
                    )


def test_m11c_r3_common_runtime_gates_remain_fail_closed():
    for field in (
        "e6_enabled",
        "e6_activation_authorized",
        "network_authorized",
    ):
        composition = _m11c_r3_runtime_composition(
            deployment_profile="CANDIDATE_CANARY",
            publication_authorized=False,
            publication_gate=False,
            telegram_publication_gate=False,
        )
        setattr(composition, field, False)
        assert _m11c_r3_is_fully_authorized(composition) is False

    for field in (
        "activation_gate",
        "workload_gate",
        "credential_gate",
        "network_gate",
    ):
        composition = _m11c_r3_runtime_composition(
            deployment_profile="CANDIDATE_CANARY",
            publication_authorized=False,
            publication_gate=False,
            telegram_publication_gate=False,
        )
        setattr(composition.authorization, field, False)
        assert _m11c_r3_is_fully_authorized(composition) is False


def test_m11c_r3_unknown_runtime_profile_remains_fail_closed():
    composition = _m11c_r3_runtime_composition(
        deployment_profile="UNKNOWN_PROFILE",
        publication_authorized=False,
        publication_gate=False,
        telegram_publication_gate=False,
    )
    assert _m11c_r3_is_fully_authorized(composition) is False
# M11H_STEP_8_REAL_CANDIDATE_DISPATCH_ADMISSION_REGRESSION
def test_m11h_step8_real_candidate_is_admitted_by_entrypoint_dispatch():
    from types import SimpleNamespace
    import engine.e6_production_runtime_composition_v1 as runtime
    import engine.run_production_signal_v1 as entrypoint

    candidate = runtime.build_e6_production_runtime_composition_v1(
        configuration=_mapping(
            E6_RUNTIME_ENABLED="true",
            E6_PROVIDER_ENABLED="true",
            E6_ACTIVATION_GATE="true",
            E6_WORKLOAD_GATE="true",
            E6_CREDENTIAL_GATE="true",
            E6_NETWORK_GATE="true",
            E6_PUBLICATION_GATE="false",
            E6_TELEGRAM_PUBLICATION_GATE="false",
        )
    )
    assert type(candidate) is runtime.E6ProductionRuntimeCompositionV1
    assert candidate.deployment_binding.deployment_profile.value == "CANDIDATE_CANARY"
    assert candidate.publication_authorized is False
    assert candidate.authorization.publication_gate is False
    assert candidate.authorization.telegram_publication_gate is False
    assert runtime._fully_authorized(candidate) is True
    assert entrypoint._composition_fully_authorizes_dispatch_v1(candidate) is True
    assert entrypoint._composition_fully_authorizes_dispatch_v1(SimpleNamespace()) is False
