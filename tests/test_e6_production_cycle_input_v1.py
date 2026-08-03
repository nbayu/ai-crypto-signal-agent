from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json

import pytest

import engine.e6_production_cycle_input_v1 as module
from engine.e6_production_cycle_input_v1 import (
    DUE_WINDOW_ALREADY_HANDLED,
    E6_NO_TRADE_CYCLE_POLICY_V1,
    E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
    E6_NO_TRADE_REASON_CODES_V1,
    E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1,
    E6_PRODUCTION_DISPATCH_POLICY_V1,
    E6NoTradeCycleRequestV1,
    E6ProductionCycleInputValidationErrorV1,
    E6ProductionDispatchDecisionV1,
    MODE_JOB_SELECTED,
    NO_MODE_JOB_DUE,
    build_e6_production_dispatch_decision_v1,
)


COMMIT = "a" * 40
IDENTITY = "b" * 32
NOW = "2026-08-03T08:00:00Z"
SHA = "c" * 64
OCCURRENCE_ID = "e6dw1:" + "d" * 64


def _no_trade(**changes: object) -> E6NoTradeCycleRequestV1:
    values: dict[str, object] = {
        "schema_version": E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1,
        "policy_version": E6_NO_TRADE_CYCLE_POLICY_V1,
        "source_commit": COMMIT,
        "outcome_invocation_id": IDENTITY,
        "mode": "SWING",
        "due_job_id": "SWING:2026-08-03T08:00:00Z",
        "due_window_occurrence_id": OCCURRENCE_ID,
        "mode_lineage_sha256": "1" * 64,
        "observed_at": NOW,
        "reason_code": "E2_NO_ELIGIBLE_CANDIDATE",
        "source_reason_code": "SCANNER_ELIGIBLE_SET_EMPTY",
        "scan_composition_sha256": "2" * 64,
        "execution_sha256": "3" * 64,
        "e3_evidence_sha256": "4" * 64,
        "audit_manifest_sha256": "5" * 64,
        "provider_attempt_count": 0,
        "telegram_attempt_count": 0,
        "exchange_order_count": 0,
        "slot_mutation_count": 0,
        "pair_lock_mutation_count": 0,
        "entry_active_mutation_count": 0,
        "retry_count": 0,
    }
    values.update(changes)
    return E6NoTradeCycleRequestV1(**values)


def _dispatch(disposition: str, **changes: object) -> E6ProductionDispatchDecisionV1:
    selected: dict[str, object] = {
        "source_commit": COMMIT,
        "outcome_invocation_id": IDENTITY,
        "observed_at": NOW,
        "disposition": disposition,
        "reason_code": disposition,
    }
    if disposition != NO_MODE_JOB_DUE:
        selected.update(
            mode="INTRADAY",
            due_job_id="INTRADAY:2026-08-03T08:00:00Z",
            due_window_occurrence_id=OCCURRENCE_ID,
            mode_lineage_sha256=SHA,
        )
    selected.update(changes)
    return build_e6_production_dispatch_decision_v1(**selected)


def test_module_is_passive_and_has_no_external_effect_surface() -> None:
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
        "datetime.now",
        "uuid4",
        "open(",
        "create_order",
        "send_message",
    ):
        assert marker not in source


def test_no_trade_contract_is_exact_frozen_slotted_and_deterministic() -> None:
    expected_fields = (
        "schema_version",
        "policy_version",
        "source_commit",
        "outcome_invocation_id",
        "mode",
        "due_job_id",
        "due_window_occurrence_id",
        "mode_lineage_sha256",
        "observed_at",
        "reason_code",
        "source_reason_code",
        "scan_composition_sha256",
        "execution_sha256",
        "e3_evidence_sha256",
        "audit_manifest_sha256",
        "provider_attempt_count",
        "telegram_attempt_count",
        "exchange_order_count",
        "slot_mutation_count",
        "pair_lock_mutation_count",
        "entry_active_mutation_count",
        "retry_count",
    )
    assert is_dataclass(E6NoTradeCycleRequestV1)
    assert E6NoTradeCycleRequestV1.__dataclass_params__.frozen is True
    assert "__dict__" not in E6NoTradeCycleRequestV1.__slots__
    assert tuple(field.name for field in fields(E6NoTradeCycleRequestV1)) == expected_fields
    value = _no_trade()
    assert value.schema_version == E6_NO_TRADE_CYCLE_REQUEST_SCHEMA_V1
    assert value.policy_version == E6_NO_TRADE_CYCLE_POLICY_V1
    assert json.loads(value.canonical_payload()) == value.to_mapping()
    assert len(value.canonical_payload_sha256()) == 64
    assert value.canonical_payload_sha256() == value.canonical_payload_sha256()
    with pytest.raises(FrozenInstanceError):
        value.reason_code = "PUBLICATION_INELIGIBLE"  # type: ignore[misc]


@pytest.mark.parametrize("mode", ("SWING", "INTRADAY", "SCALP"))
@pytest.mark.parametrize("reason_code", sorted(E6_NO_TRADE_REASON_CODES_V1))
def test_all_modes_and_p1_no_trade_reasons_are_accepted(
    mode: str, reason_code: str
) -> None:
    assert _no_trade(mode=mode, reason_code=reason_code).reason_code == reason_code


@pytest.mark.parametrize(
    "changes",
    (
        {"source_commit": "A" * 40},
        {"source_commit": "a" * 39},
        {"outcome_invocation_id": "A" * 32},
        {"outcome_invocation_id": "b" * 31},
        {"mode": "UNKNOWN"},
        {"observed_at": "2026-08-03T08:00:00.1Z"},
        {"observed_at": "2026-02-30T08:00:00Z"},
        {"due_job_id": ""},
        {"due_job_id": " SWING"},
        {"due_window_occurrence_id": "SWING/window"},
        {"mode_lineage_sha256": "C" * 64},
        {"scan_composition_sha256": "1" * 63},
        {"execution_sha256": "z" * 64},
        {"e3_evidence_sha256": None},
        {"audit_manifest_sha256": ""},
        {"reason_code": NO_MODE_JOB_DUE},
        {"reason_code": DUE_WINDOW_ALREADY_HANDLED},
        {"source_reason_code": "fixture_secret_token"},
    ),
)
def test_no_trade_malformed_identity_time_hash_and_reason_fail_closed(
    changes: dict[str, object]
) -> None:
    with pytest.raises(E6ProductionCycleInputValidationErrorV1) as raised:
        _no_trade(**changes)
    assert str(raised.value) == "INVALID_E6_PRODUCTION_CYCLE_INPUT"


@pytest.mark.parametrize(
    "field",
    (
        "provider_attempt_count",
        "telegram_attempt_count",
        "exchange_order_count",
        "slot_mutation_count",
        "pair_lock_mutation_count",
        "entry_active_mutation_count",
        "retry_count",
    ),
)
@pytest.mark.parametrize("value", (1, -1, True, 0.0, "0"))
def test_every_effect_counter_requires_exact_integer_zero(field: str, value: object) -> None:
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        _no_trade(**{field: value})


@pytest.mark.parametrize(
    "disposition", (NO_MODE_JOB_DUE, DUE_WINDOW_ALREADY_HANDLED, MODE_JOB_SELECTED)
)
def test_dispatch_contract_is_exact_frozen_and_self_bound(disposition: str) -> None:
    value = _dispatch(disposition)
    assert value.schema_version == E6_PRODUCTION_DISPATCH_DECISION_SCHEMA_V1
    assert value.policy_version == E6_PRODUCTION_DISPATCH_POLICY_V1
    assert value.reason_code == disposition
    assert len(value.dispatch_evidence_sha256) == 64
    assert json.loads(value.canonical_payload()) == value.to_mapping()
    assert value.canonical_payload_sha256() == value.canonical_payload_sha256()
    with pytest.raises(FrozenInstanceError):
        value.disposition = NO_MODE_JOB_DUE  # type: ignore[misc]


def test_dispatch_optionality_and_evidence_digest_fail_closed() -> None:
    no_work = _dispatch(NO_MODE_JOB_DUE)
    assert (
        no_work.mode,
        no_work.due_job_id,
        no_work.due_window_occurrence_id,
        no_work.mode_lineage_sha256,
    ) == (None, None, None, None)
    for disposition in (DUE_WINDOW_ALREADY_HANDLED, MODE_JOB_SELECTED):
        selected = _dispatch(disposition)
        assert selected.mode == "INTRADAY"
        assert selected.due_job_id is not None
        assert selected.due_window_occurrence_id is not None
        assert selected.mode_lineage_sha256 == SHA
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        _dispatch(NO_MODE_JOB_DUE, mode="SWING")
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        _dispatch(MODE_JOB_SELECTED, due_job_id=None)
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        replace(_dispatch(MODE_JOB_SELECTED), dispatch_evidence_sha256="0" * 64)


def test_due_window_occurrence_id_has_one_exact_lowercase_domain() -> None:
    accepted = "e6dw1:" + "0123456789abcdef" * 4
    assert _no_trade(due_window_occurrence_id=accepted).due_window_occurrence_id == accepted
    assert (
        _dispatch(MODE_JOB_SELECTED, due_window_occurrence_id=accepted)
        .due_window_occurrence_id
        == accepted
    )

    rejected: tuple[object, ...] = (
        "E6DW1:" + "a" * 64,
        "e6dw1:" + "A" * 64,
        "e6dw1:" + "a" * 63,
        "e6dw1:" + "a" * 65,
        "e6dw2:" + "a" * 64,
        " e6dw1:" + "a" * 64,
        "e6dw1:" + "a" * 64 + " ",
        "e6dw1:" + "a" * 64 + ":suffix",
        "",
        None,
        1,
    )
    for value in rejected:
        with pytest.raises(E6ProductionCycleInputValidationErrorV1):
            _no_trade(due_window_occurrence_id=value)
        with pytest.raises(E6ProductionCycleInputValidationErrorV1):
            _dispatch(MODE_JOB_SELECTED, due_window_occurrence_id=value)


def test_generic_due_job_identity_remains_uppercase_only() -> None:
    assert _no_trade(due_job_id="SWING:BASE_EVALUATION").due_job_id == (
        "SWING:BASE_EVALUATION"
    )
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        _no_trade(due_job_id="swing:base_evaluation")
    with pytest.raises(E6ProductionCycleInputValidationErrorV1):
        _dispatch(MODE_JOB_SELECTED, due_job_id="intraday:base_evaluation")


def test_rejected_secret_like_source_reason_never_appears_in_error_or_repr() -> None:
    marker = "PRIVATE_KEY_MATERIAL_MARKER"
    with pytest.raises(E6ProductionCycleInputValidationErrorV1) as raised:
        _no_trade(source_reason_code=marker)
    rendered = str(raised.value) + repr(raised.value)
    assert marker not in rendered
    assert marker not in repr(_no_trade())
