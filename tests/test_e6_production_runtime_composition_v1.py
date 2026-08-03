from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
from types import SimpleNamespace

import pytest

import engine.e6_production_runtime_composition_v1 as module
from engine.e6_activation_configuration_v1 import (
    E6ActivationConfigurationV1,
    load_e6_activation_configuration_v1,
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
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": "e6-activation-configuration-v1",
        "E6_RELEASE_COMMIT": COMMIT,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": CHECKPOINT,
        "E6_RELEASE_ROOT": f"/opt/ai-crypto-signal-agent-releases/{COMMIT}",
        "E6_RELEASE_REFERENCE_PATH": "/var/lib/ai-crypto-signal-agent/e6-installed-release.path",
        "E6_CREDENTIAL_METADATA_PATH": "/etc/ai-crypto-signal-agent/e6-credentials.metadata",
        "E6_OWNER_CONTROL_STATE_PATH": "/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json",
        "E6_SERVICE_USER": "ai-crypto-signal-agent",
        "E6_SERVICE_GROUP": "ai-crypto-signal-agent",
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


def test_exact_23_key_loader_runs_once_and_composition_is_immutable(capsys) -> None:
    configuration = _mapping()
    assert len(configuration) == 23
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
        "e6_enabled",
        "authorization",
        "e6_activation_authorized",
        "network_authorized",
        "publication_authorized",
    )
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
    values = {key: "true" for _field, key in GATE_KEYS}
    values.update(E6_RUNTIME_ENABLED="true", E6_PROVIDER_ENABLED="true")
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
