from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import hashlib
import json
from pathlib import Path

import pytest

import engine.e5_provider_invocation_boundary_v1 as provider
import engine.e6_claude_daily_usage_store_v1 as usage_store_module
import engine.e6_durable_review_execution_v1 as subject
from test_e5_bounded_final_review_composition_v1 import (
    _claude_response_mapping,
    _transports,
)
from test_e5_claude_review_router_v1 import (
    ACTIVE_BINDING_SHA256,
    MODE_SIDE_DECISION,
    UTC_DAY,
    _payload,
)


TIMESTAMP = "2026-07-30T12:00:00Z"
RESULT_FIELDS = (
    "execution_version",
    "provider_binding_sha256",
    "payload_sha256",
    "prepared_stage_sha256",
    "usage_before",
    "proposed_usage_after",
    "committed_usage_after",
    "store_record_sha256",
    "store_generation",
    "persistence_outcome",
    "final_composition",
    "deepseek_provider_attempt_count",
    "claude_provider_attempt_count",
    "retry_count",
    "publication_allowed",
    "telegram_send_allowed",
    "ledger_mutation_allowed",
    "slot_mutation_allowed",
    "pair_lock_mutation_allowed",
    "execution_sha256",
)


def _canonical_hash(mapping):
    return hashlib.sha256(
        json.dumps(
            mapping,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _daily_file(root):
    return root / f"{UTC_DAY}.e6-claude-daily-usage.json"


def _execute(
    tmp_path,
    decision="CLEAR",
    *,
    mode="SWING",
    side="LONG",
    name="durable",
    usage_store=None,
    claude_measured=100,
    claude_requested=100,
    claude_counts_required=None,
    **transport_options,
):
    tmp_path.mkdir(parents=True, exist_ok=True)
    payload = _payload(tmp_path, mode, side, name=name)
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        decision,
        **transport_options,
    )
    if usage_store is None:
        usage_store = usage_store_module.E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=tmp_path
        )
    if claude_counts_required is None:
        claude_counts_required = decision in ("CAUTION", "HOLD")
    result = subject.execute_e6_durable_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        usage_store=usage_store,
        commit_timestamp=TIMESTAMP,
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=(
            claude_measured if claude_counts_required else None
        ),
        claude_requested_output_tokens=(
            claude_requested if claude_counts_required else None
        ),
        claude_transport=claude_transport,
    )
    return payload, result, deep_calls, claude_calls


def _assert_invalid(call):
    with pytest.raises(
        ValueError,
        match="^invalid E6 durable review execution$",
    ):
        call()


def test_exact_twenty_field_durable_result_hash_and_authority(tmp_path):
    _, result, deep_calls, claude_calls = _execute(
        tmp_path,
        "CAUTION",
        name="exact-result",
    )
    assert subject.E6_DURABLE_REVIEW_EXECUTION_VERSION == (
        "e6-durable-review-execution-v1"
    )
    assert subject.DURABLE_EXECUTION_FIELD_COUNT == 20
    assert subject.E6_DURABLE_REVIEW_PERSISTENCE_OUTCOMES == (
        "NO_DURABLE_RESERVATION_REQUIRED",
        "DURABLE_RESERVATION_COMMITTED",
    )
    assert tuple(
        field.name for field in fields(subject.E6DurableReviewExecutionResultV1)
    ) == RESULT_FIELDS
    assert subject.E6DurableReviewExecutionResultV1.__dataclass_params__.frozen
    assert "__dict__" not in subject.E6DurableReviewExecutionResultV1.__slots__
    assert tuple(result.to_mapping()) == RESULT_FIELDS
    assert _canonical_hash(json.loads(result.canonical_execution_json())) == (
        result.execution_sha256
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.persistence_outcome == "DURABLE_RESERVATION_COMMITTED"
    assert result.committed_usage_after == result.proposed_usage_after
    assert result.final_composition.may_continue_to_python_final_gate is True
    assert all(
        value is False
        for value in (
            result.publication_allowed,
            result.telegram_send_allowed,
            result.ledger_mutation_allowed,
            result.slot_mutation_allowed,
            result.pair_lock_mutation_allowed,
        )
    )
    with pytest.raises(FrozenInstanceError):
        result.retry_count = 1


class _OrderedStore:
    def __init__(self, inner, events):
        self.inner = inner
        self.events = events

    def load(self, **keywords):
        self.events.append("load")
        return self.inner.load(**keywords)

    def compare_and_commit(self, **keywords):
        self.events.append("commit")
        return self.inner.compare_and_commit(**keywords)


def test_durable_commit_is_confirmed_before_claude_transport(tmp_path):
    payload = _payload(tmp_path, name="ordering")
    deep_transport, base_claude, deep_calls, claude_calls = _transports(
        payload,
        "CAUTION",
    )
    events = []
    store = _OrderedStore(
        usage_store_module.E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=tmp_path
        ),
        events,
    )

    def claude_transport(request):
        assert events == ["load", "commit"]
        assert _daily_file(tmp_path).exists()
        events.append("claude")
        return base_claude(request)

    result = subject.execute_e6_durable_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        usage_store=store,
        commit_timestamp=TIMESTAMP,
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=100,
        claude_requested_output_tokens=100,
        claude_transport=claude_transport,
    )
    assert events == ["load", "commit", "claude"]
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.store_record_sha256 is not None


@pytest.mark.parametrize("decision", ("CLEAR",))
def test_l0_requires_no_durable_data_write_or_claude_call(tmp_path, decision):
    _, result, deep_calls, claude_calls = _execute(
        tmp_path,
        decision,
        name="l0-no-store",
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.persistence_outcome == "NO_DURABLE_RESERVATION_REQUIRED"
    assert result.committed_usage_after is None
    assert result.store_record_sha256 is None
    assert result.proposed_usage_after == result.usage_before
    assert not _daily_file(tmp_path).exists()


@pytest.mark.parametrize("decision", ("CAUTION", "HOLD"))
def test_token_preflight_failure_retains_durable_reservation_without_call(
    tmp_path,
    decision,
):
    limit = 4001 if decision == "CAUTION" else 6001
    _, result, deep_calls, claude_calls = _execute(
        tmp_path,
        decision,
        name=f"token-{decision}",
        claude_measured=limit,
    )
    assert len(deep_calls) == 1
    assert claude_calls == []
    assert result.persistence_outcome == "DURABLE_RESERVATION_COMMITTED"
    assert result.final_composition.final_outcome_code == (
        "BLOCK_D8_CLAUDE_TOKEN_PREFLIGHT"
    )
    assert result.committed_usage_after == result.proposed_usage_after
    assert _daily_file(tmp_path).exists()


@pytest.mark.parametrize(
    ("outcome", "cause"),
    (
        ("TIMEOUT", "HOLD_PROVIDER_TIMEOUT"),
        ("TEMPORARILY_UNAVAILABLE", "HOLD_PROVIDER_UNAVAILABLE"),
        (
            "AUTHENTICATION_OR_PERMISSION_FAILURE",
            "HOLD_PROVIDER_CONFIGURATION",
        ),
        ("UNSUPPORTED_MODEL", "HOLD_MODEL_BINDING"),
        ("MALFORMED_OR_SCHEMA_INVALID_RESPONSE", "HOLD_INVALID_RESPONSE"),
        ("TOKEN_LIMIT_EXCEEDED", "HOLD_TOKEN_LIMIT"),
    ),
)
def test_provider_failure_matrix_retains_reservation_once(
    tmp_path,
    outcome,
    cause,
):
    _, result, deep_calls, claude_calls = _execute(
        tmp_path,
        "CAUTION",
        name=f"provider-{outcome}",
        claude_outcome=outcome,
    )
    assert len(deep_calls) == len(claude_calls) == 1
    assert result.final_composition.underlying_d8_cause == cause
    assert result.final_composition.final_outcome_code == (
        "BLOCK_D8_CLAUDE_INVOCATION"
    )
    assert result.committed_usage_after == result.proposed_usage_after
    assert result.retry_count == 0


def test_budget_failure_and_unexpected_exception_retain_without_exposure(
    tmp_path,
):
    _, budget, _, budget_calls = _execute(
        tmp_path / "budget",
        "CAUTION",
        name="budget",
        claude_billed_cost=32501,
    )
    assert len(budget_calls) == 1
    assert budget.final_composition.underlying_d8_cause == "HOLD_BUDGET_BLOCKED"
    _, unexpected, _, exception_calls = _execute(
        tmp_path / "exception",
        "HOLD",
        name="exception",
        claude_raises=True,
    )
    assert len(exception_calls) == 1
    assert unexpected.final_composition.underlying_d8_cause == (
        "HOLD_PROVIDER_UNAVAILABLE"
    )
    assert "synthetic" not in json.dumps(unexpected.to_mapping())
    assert unexpected.committed_usage_after == unexpected.proposed_usage_after


def test_retained_reservation_blocks_duplicate_after_restart(tmp_path):
    payload, first, first_deep, first_claude = _execute(
        tmp_path,
        "CAUTION",
        name="restart-duplicate",
        claude_outcome="TIMEOUT",
    )
    assert len(first_deep) == len(first_claude) == 1
    deep_transport, claude_transport, second_deep, second_claude = _transports(
        payload,
        "CAUTION",
    )
    store = usage_store_module.E6ClaudeDailyUsageFileStoreV1(
        authorized_store_root=tmp_path
    )
    second = subject.execute_e6_durable_review_v1(
        payload=payload,
        deterministic_hard_gates_passed=True,
        pre_review_score=80,
        mode_score_floor=70,
        usage_store=store,
        commit_timestamp="2026-07-30T12:00:01Z",
        deepseek_measured_input_tokens=100,
        deepseek_requested_output_tokens=100,
        deepseek_transport=deep_transport,
        claude_measured_input_tokens=None,
        claude_requested_output_tokens=None,
        claude_transport=claude_transport,
    )
    assert len(second_deep) == 1
    assert second_claude == []
    assert second.persistence_outcome == "NO_DURABLE_RESERVATION_REQUIRED"
    assert second.final_composition.final_outcome_code == "BLOCK_D7_CLAUDE_ROUTING"
    assert second.final_composition.claude_route_result.decision_code == (
        "BLOCK_DUPLICATE_LOGICAL_REVIEW"
    )
    assert second.usage_before == first.committed_usage_after


class _ConflictStore:
    def __init__(self, inner):
        self.inner = inner

    def load(self, **keywords):
        return self.inner.load(**keywords)

    def compare_and_commit(self, **keywords):
        raise ValueError("synthetic CAS conflict")


def test_cas_conflict_fails_closed_before_claude_without_retry(tmp_path):
    payload = _payload(tmp_path, name="cas-conflict")
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        "CAUTION",
    )
    store = _ConflictStore(
        usage_store_module.E6ClaudeDailyUsageFileStoreV1(
            authorized_store_root=tmp_path
        )
    )
    _assert_invalid(
        lambda: subject.execute_e6_durable_review_v1(
            payload=payload,
            deterministic_hard_gates_passed=True,
            pre_review_score=80,
            mode_score_floor=70,
            usage_store=store,
            commit_timestamp=TIMESTAMP,
            deepseek_measured_input_tokens=100,
            deepseek_requested_output_tokens=100,
            deepseek_transport=deep_transport,
            claude_measured_input_tokens=100,
            claude_requested_output_tokens=100,
            claude_transport=claude_transport,
        )
    )
    assert len(deep_calls) == 1
    assert claude_calls == []


def test_corrupt_store_fails_before_any_provider_call(tmp_path):
    path = _daily_file(tmp_path)
    path.write_text("{corrupt}\n", encoding="utf-8")
    path.chmod(0o600)
    payload = _payload(tmp_path, name="corrupt-store")
    deep_transport, claude_transport, deep_calls, claude_calls = _transports(
        payload,
        "CAUTION",
    )
    store = usage_store_module.E6ClaudeDailyUsageFileStoreV1(
        authorized_store_root=tmp_path
    )
    _assert_invalid(
        lambda: subject.execute_e6_durable_review_v1(
            payload=payload,
            deterministic_hard_gates_passed=True,
            pre_review_score=80,
            mode_score_floor=70,
            usage_store=store,
            commit_timestamp=TIMESTAMP,
            deepseek_measured_input_tokens=100,
            deepseek_requested_output_tokens=100,
            deepseek_transport=deep_transport,
            claude_measured_input_tokens=100,
            claude_requested_output_tokens=100,
            claude_transport=claude_transport,
        )
    )
    assert deep_calls == claude_calls == []


@pytest.mark.parametrize(
    ("mode", "side", "decision", "route"),
    MODE_SIDE_DECISION,
)
def test_six_mode_side_durable_chains(
    tmp_path,
    mode,
    side,
    decision,
    route,
):
    _, result, deep_calls, claude_calls = _execute(
        tmp_path,
        decision,
        mode=mode,
        side=side,
        name=f"chain-{mode}-{side}",
    )
    composition = result.final_composition
    assert result.provider_binding_sha256 == ACTIVE_BINDING_SHA256
    assert composition.claude_route_result.route == route
    assert len(deep_calls) == 1
    assert len(claude_calls) == (0 if route == "L0" else 1)
    assert result.retry_count == 0
    assert result.publication_allowed is False
    if route == "L1":
        assert composition.may_continue_to_python_final_gate is True
        assert composition.claude_invocation_result.model_id == "claude-opus-5"
    elif route == "L2":
        assert composition.may_continue_to_python_final_gate is False
        assert composition.publication_blocked is True
        assert composition.claude_invocation_result.model_id == "claude-fable-5"


def test_no_retry_release_cache_network_or_side_effect_surface():
    source_values = tuple(
        Path(path).read_text(encoding="utf-8")
        for path in (
            subject.__file__,
            usage_store_module.__file__,
        )
    )
    sources = "\n".join(source_values)
    imported = set()
    for source in source_values:
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
    assert {
        "requests",
        "httpx",
        "aiohttp",
        "anthropic",
        "openai",
        "socket",
        "subprocess",
    }.isdisjoint(module.split(".", 1)[0] for module in imported)
    assert "while " not in sources
    assert "rollback" not in sources.casefold()
    assert "release_reservation" not in sources
    assert "response_cache" not in sources
    assert "getenv" not in sources
