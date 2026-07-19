"""RED contract for the Phase 12 controlled-production design freeze."""

from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from engine.phase_12_controlled_production_enablement_design_v1 import (
    Phase12AuthorityMatrixV1,
    Phase12DecisionV1,
    Phase12DesignFreezeEvidenceV1,
    build_phase_12_controlled_production_enablement_design_v1,
)


EXPECTED_AUTHORITY_VALUES = {
    "repository_design_inspection_authorized": True,
    "design_contract_test_authorized": True,
    "implementation_authorized": False,
    "credential_source_access_authorized": False,
    "credential_loading_authorized": False,
    "credential_verification_execution_authorized": False,
    "environment_read_authorized": False,
    "secret_file_read_authorized": False,
    "provider_authentication_authorized": False,
    "pricing_network_revalidation_authorized": False,
    "provider_connectivity_authorized": False,
    "provider_request_creation_authorized": False,
    "provider_transmission_authorized": False,
    "provider_retry_authorized": False,
    "reservation_creation_authorized": False,
    "ledger_mutation_authorized": False,
    "runtime_invocation_authorized": False,
    "manifest_activation_authorized": False,
    "content_creation_authorized": False,
    "filesystem_content_read_authorized": False,
    "content_hashing_authorized": False,
    "integrity_inspection_authorized": False,
    "result_acceptance_authorized": False,
    "dry_run_execution_authorized": False,
    "live_shadow_execution_authorized": False,
    "production_publication_authorized": False,
    "telegram_publication_authorized": False,
    "launch_authorized": False,
    "run_size_authorized": False,
    "trading_authorized": False,
}

EXPECTED_BLOCKERS = (
    "CONTENT_ACCESS_NOT_AUTHORIZED",
    "CONTENT_HASHING_NOT_AUTHORIZED",
    "FILESYSTEM_READ_NOT_AUTHORIZED",
    "INTEGRITY_INSPECTION_NOT_AUTHORIZED",
    "INTEGRITY_VERIFICATION_NOT_AUTHORIZED",
    "RESULT_ACCEPTANCE_NOT_AUTHORIZED",
    "CONTENT_CREATION_AUTHORITY_NOT_GRANTED",
    "CONTENT_INTEGRITY_NOT_VERIFIED",
    "CONTENT_NOT_ACCEPTED",
    "CREDENTIAL_CONFIGURATION_NOT_VERIFIED",
    "EXECUTABLE_CONTENT_IDENTITY_ABSENT",
    "EXECUTABLE_INPUT_CONTENT_ABSENT",
    "INTEGRITY_RESULT_ABSENT",
    "MANIFEST_ACTIVATION_NOT_AUTHORIZED",
    "PRE_CALL_RESERVATION_NOT_CREATED",
    "PRICING_REVALIDATION_INCOMPLETE",
    "PROVIDER_REQUEST_NOT_CREATED",
    "RUNTIME_INVOCATION_NOT_AUTHORIZED",
    "LAUNCH_NOT_AUTHORIZED",
    "RUN_SIZE_NOT_AUTHORIZED",
)

EXPECTED_RULES = {
    "CREDENTIAL_SOURCE_ABSTRACTION": (
        "Credentials may only be supplied through an explicitly injected, named secret-resolver boundary.",
        "The Phase 12 domain module must not discover ambient credentials.",
        "Direct os.environ access is forbidden inside the domain boundary.",
    ),
    "SECRET_LOADING_BOUNDARY": (
        "Secret loading must fail closed.",
        "Secret values must never be persisted, serialized, returned in evidence, or logged.",
        "Missing or ambiguous credential references deny execution.",
    ),
    "CREDENTIAL_VERIFICATION_BOUNDARY": (
        "Credential presence is not proof of credential validity.",
        "Credential verification and provider connectivity are separate authorities.",
        "No provider authentication is authorized by the design freeze.",
    ),
    "PROVIDER_ADAPTER_CONTRACT": (
        "Provider adapters must use a provider-neutral immutable request and response contract.",
        "Provider-specific SDK objects must not cross the domain boundary.",
    ),
    "PROVIDER_REQUEST_CONTRACT": (
        "Every request requires a canonical request identity.",
        "Every request requires an immutable payload identity or digest.",
        "Route, model, budget, timeout, and redaction metadata must be bound before execution.",
    ),
    "MODEL_ROUTE_ALLOWLIST": (
        "The allowlist mechanism must be explicit, immutable, versioned, and owner-controlled.",
        "No provider, route, or model is execution-approved by this design freeze.",
        "The initial execution allowlist is empty.",
    ),
    "TIMEOUT_POLICY": (
        "No implicit timeout is permitted.",
        "A per-attempt timeout and total deadline must be explicitly frozen before provider execution.",
    ),
    "RETRY_POLICY": (
        "The default retry count is zero.",
        "Existing two-attempt provider behavior is not approved for Phase 12 execution.",
        "Any retry requires separate owner authority and idempotency proof.",
    ),
    "IDEMPOTENCY_POLICY": (
        "A canonical request ID and immutable payload identity are required.",
        "Duplicate, uncertain, and replay outcomes must have explicit reconciliation semantics before execution.",
    ),
    "PRICING_REVALIDATION": (
        "Historical or static pricing evidence is insufficient for paid execution.",
        "Freshness, source identity, currency, effective time, and expiry are required.",
        "Network pricing revalidation remains unauthorized.",
    ),
    "TOKEN_CEILING": (
        "Input and output token ceilings must be explicit per approved route.",
        "Missing limits deny request creation and execution.",
    ),
    "REQUEST_COST_CEILING": (
        "A maximum request cost and currency representation must be explicit.",
        "Missing or stale pricing denies execution.",
    ),
    "RUN_COST_CEILING": (
        "A cumulative run ceiling and hard-stop behavior must be explicit.",
        "The initial authorized run ceiling is zero.",
    ),
    "RESERVATION_SEMANTICS": (
        "Reservation must occur before any paid provider transmission.",
        "Reservations must bind to a canonical request ID.",
        "Expiry and uncertain-outcome reconciliation must be deterministic.",
        "Reservation creation remains unauthorized.",
    ),
    "USAGE_LEDGER_SEMANTICS": (
        "Usage accounting must be append-only and durable before live use.",
        "Events require immutable event identities and reconciliation state.",
        "Ledger mutation remains unauthorized.",
    ),
    "AUDIT_EVENT_SCHEMA": (
        "Audit evidence must be append-only, immutable, and linked by stable identities.",
        "Audit events must contain no secrets or raw authorization headers.",
    ),
    "REDACTION_POLICY": (
        "Secrets, raw credentials, provider authorization headers, and unredacted sensitive payloads must never be serialized or logged.",
        "Redaction failure must deny execution.",
    ),
    "KILL_SWITCH": (
        "A fail-closed global kill switch must be evaluated before every external or mutable action.",
        "The initial kill-switch state is engaged.",
    ),
    "FAIL_CLOSED_BEHAVIOR": (
        "Missing identity, authority, pricing, allowlist entry, reservation, verification, or safety evidence must deny execution.",
    ),
    "DRY_RUN_MODE": (
        "Dry-run may construct sanitized evidence only.",
        "Dry-run must never invoke a provider transport.",
        "Dry-run execution itself is not authorized by this design freeze.",
    ),
    "BOUNDED_LIVE_SHADOW_MODE": (
        "Live shadow requires later explicit owner authorization.",
        "Request count, cost, route, model, and time limits must be explicit.",
        "All initial limits are zero.",
        "Live shadow cannot publish externally and cannot trade.",
    ),
    "PRODUCTION_PUBLICATION_GATE": (
        "Production publication must have a separate disabled-by-default authority gate.",
        "Provider execution does not imply publication authority.",
    ),
    "TELEGRAM_PUBLICATION_GATE": (
        "Telegram polling, sending, and publication require an independent disabled-by-default owner gate.",
        "Production publication authority does not automatically imply Telegram authority.",
    ),
    "ROLLBACK_AND_REVOCATION": (
        "Credential revocation, kill-switch activation, manifest rollback, reservation reconciliation, and publication disablement require explicit deterministic behavior.",
    ),
    "PROMOTION_CRITERIA": (
        "Dry-run, live-shadow, publication consideration, and launch readiness are separate states.",
        "No state promotes automatically.",
        "Every promotion requires evidence and explicit owner adjudication.",
    ),
    "LAUNCH_READINESS_TRANSITION": (
        "Launch readiness remains NOT_READY_FOR_LAUNCH.",
        "Only a separate immutable owner-reviewed transition artifact may change launch readiness.",
    ),
    "ZERO_TRADING_AUTHORITY": (
        "Phase 12 grants no order creation, exchange execution, position mutation, fund movement, or trading authority.",
        "Provider execution, publication, Telegram delivery, and launch readiness cannot imply trading authority.",
        "Trading scope may only change through a separate explicit owner decision outside this design freeze.",
    ),
}


def _assert_frozen_slotted(instance: object) -> None:
    assert is_dataclass(instance)
    assert type(instance).__dataclass_params__.frozen is True
    assert "__dict__" not in type(instance).__slots__


def _assert_immutable_nested(value: object) -> None:
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, tuple):
        for item in value:
            _assert_immutable_nested(item)
        return
    if is_dataclass(value):
        _assert_frozen_slotted(value)
        for field in fields(value):
            _assert_immutable_nested(getattr(value, field.name))
        return
    pytest.fail(f"mutable or unsupported nested evidence value: {type(value)!r}")


def test_public_contract_is_closed_and_immutable() -> None:
    evidence = build_phase_12_controlled_production_enablement_design_v1()

    assert isinstance(evidence, Phase12DesignFreezeEvidenceV1)
    assert tuple(field.name for field in fields(Phase12AuthorityMatrixV1)) == tuple(
        EXPECTED_AUTHORITY_VALUES
    )
    assert tuple(field.name for field in fields(Phase12DecisionV1)) == (
        "decision_id",
        "frozen_rule",
        "rationale",
        "required_test_surface",
        "later_authority_requirement",
    )
    assert tuple(field.name for field in fields(Phase12DesignFreezeEvidenceV1)) == (
        "phase_id",
        "phase_name",
        "design_version",
        "design_status",
        "previous_locked_phase",
        "previous_checkpoint",
        "previous_locked_head",
        "launch_readiness",
        "production_effect",
        "zero_production_proof",
        "owner_design_authorized",
        "implementation_authorized",
        "authority_matrix",
        "blockers",
        "active_blocker_count",
        "classified_blocker_count",
        "resolved_blocker_count",
        "execution_authorized_blocker_count",
        "shadow_governance_blocker_count",
        "deferred_prerequisite_blocker_count",
        "explicitly_absent_authority_blocker_count",
        "decisions",
    )
    for value in (evidence, evidence.authority_matrix, *evidence.decisions):
        _assert_frozen_slotted(value)


def test_top_level_identity_and_authority_matrix_are_fail_closed() -> None:
    evidence = build_phase_12_controlled_production_enablement_design_v1()

    assert (
        evidence.phase_id,
        evidence.phase_name,
        evidence.design_version,
        evidence.design_status,
        evidence.previous_locked_phase,
        evidence.previous_checkpoint,
        evidence.previous_locked_head,
        evidence.launch_readiness,
        evidence.production_effect,
        evidence.zero_production_proof,
        evidence.owner_design_authorized,
        evidence.implementation_authorized,
    ) == (
        "PHASE_12",
        "CONTROLLED_PRODUCTION_ENABLEMENT",
        "V1",
        "DESIGN_AUTHORIZED_IMPLEMENTATION_BLOCKED",
        "PHASE_11",
        "CP-11-LOCKED",
        "13513e25a81d03dc52a9cc125923edf8067f6f70",
        "NOT_READY_FOR_LAUNCH",
        "NONE",
        "PROVEN_NONE",
        True,
        False,
    )
    actual = {
        field.name: getattr(evidence.authority_matrix, field.name)
        for field in fields(evidence.authority_matrix)
    }
    assert actual == EXPECTED_AUTHORITY_VALUES
    assert not any(
        value
        for name, value in actual.items()
        if name not in {
            "repository_design_inspection_authorized",
            "design_contract_test_authorized",
        }
    )


def test_locked_blockers_and_design_decisions_are_exact_and_ordered() -> None:
    evidence = build_phase_12_controlled_production_enablement_design_v1()

    assert evidence.blockers == EXPECTED_BLOCKERS
    assert len(evidence.blockers) == len(set(evidence.blockers)) == 20
    assert (
        evidence.active_blocker_count,
        evidence.classified_blocker_count,
        evidence.resolved_blocker_count,
        evidence.execution_authorized_blocker_count,
        evidence.shadow_governance_blocker_count,
        evidence.deferred_prerequisite_blocker_count,
        evidence.explicitly_absent_authority_blocker_count,
    ) == (20, 20, 0, 0, 6, 12, 2)

    assert tuple(decision.decision_id for decision in evidence.decisions) == tuple(
        EXPECTED_RULES
    )
    assert len(evidence.decisions) == 27
    for decision in evidence.decisions:
        assert decision.frozen_rule == EXPECTED_RULES[decision.decision_id]
        assert all(
            isinstance(value, str) and value.strip()
            for value in (
                decision.rationale,
                decision.required_test_surface,
                decision.later_authority_requirement,
            )
        )
        assert isinstance(decision.frozen_rule, tuple)
        assert decision.frozen_rule


def test_builder_is_argument_free_deterministic_and_deeply_immutable() -> None:
    assert not inspect.signature(
        build_phase_12_controlled_production_enablement_design_v1
    ).parameters

    first = build_phase_12_controlled_production_enablement_design_v1()
    second = build_phase_12_controlled_production_enablement_design_v1()
    assert first == second
    _assert_immutable_nested(first)

    with pytest.raises(FrozenInstanceError):
        first.phase_id = "PHASE_12_MUTATED"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.authority_matrix.launch_authorized = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.decisions[0].decision_id = "MUTATED"  # type: ignore[misc]


def test_design_module_has_no_operational_dependency_surface() -> None:
    import engine.phase_12_controlled_production_enablement_design_v1 as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    prohibited_roots = {
        "aiohttp",
        "anthropic",
        "binance",
        "ccxt",
        "http",
        "httpx",
        "openai",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "telegram",
        "urllib",
    }
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

    assert not prohibited_roots.intersection(imported_roots)
    assert not prohibited_roots.intersection(used_names)
    assert "open" not in used_names
