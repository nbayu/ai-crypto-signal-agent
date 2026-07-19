"""Immutable, no-I/O Phase 12 controlled-production design-freeze evidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Phase12DecisionV1:
    decision_id: str
    frozen_rule: tuple[str, ...]
    rationale: str
    required_test_surface: str
    later_authority_requirement: str


@dataclass(frozen=True, slots=True)
class Phase12AuthorityMatrixV1:
    repository_design_inspection_authorized: bool
    design_contract_test_authorized: bool
    implementation_authorized: bool
    credential_source_access_authorized: bool
    credential_loading_authorized: bool
    credential_verification_execution_authorized: bool
    environment_read_authorized: bool
    secret_file_read_authorized: bool
    provider_authentication_authorized: bool
    pricing_network_revalidation_authorized: bool
    provider_connectivity_authorized: bool
    provider_request_creation_authorized: bool
    provider_transmission_authorized: bool
    provider_retry_authorized: bool
    reservation_creation_authorized: bool
    ledger_mutation_authorized: bool
    runtime_invocation_authorized: bool
    manifest_activation_authorized: bool
    content_creation_authorized: bool
    filesystem_content_read_authorized: bool
    content_hashing_authorized: bool
    integrity_inspection_authorized: bool
    result_acceptance_authorized: bool
    dry_run_execution_authorized: bool
    live_shadow_execution_authorized: bool
    production_publication_authorized: bool
    telegram_publication_authorized: bool
    launch_authorized: bool
    run_size_authorized: bool
    trading_authorized: bool


@dataclass(frozen=True, slots=True)
class Phase12DesignFreezeEvidenceV1:
    phase_id: str
    phase_name: str
    design_version: str
    design_status: str
    previous_locked_phase: str
    previous_checkpoint: str
    previous_locked_head: str
    launch_readiness: str
    production_effect: str
    zero_production_proof: str
    owner_design_authorized: bool
    implementation_authorized: bool
    authority_matrix: Phase12AuthorityMatrixV1
    blockers: tuple[str, ...]
    active_blocker_count: int
    classified_blocker_count: int
    resolved_blocker_count: int
    execution_authorized_blocker_count: int
    shadow_governance_blocker_count: int
    deferred_prerequisite_blocker_count: int
    explicitly_absent_authority_blocker_count: int
    decisions: tuple[Phase12DecisionV1, ...]


_BLOCKERS = (
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


def _decision(decision_id: str, frozen_rule: tuple[str, ...]) -> Phase12DecisionV1:
    return Phase12DecisionV1(
        decision_id=decision_id,
        frozen_rule=frozen_rule,
        rationale="The design freeze preserves a fail-closed Phase 12 boundary.",
        required_test_surface="Immutable design-freeze evidence contract tests.",
        later_authority_requirement="Separate explicit owner authorization is required.",
    )


_DECISIONS = (
    _decision(
        "CREDENTIAL_SOURCE_ABSTRACTION",
        (
            "Credentials may only be supplied through an explicitly injected, named secret-resolver boundary.",
            "The Phase 12 domain module must not discover ambient credentials.",
            "Direct os.environ access is forbidden inside the domain boundary.",
        ),
    ),
    _decision(
        "SECRET_LOADING_BOUNDARY",
        (
            "Secret loading must fail closed.",
            "Secret values must never be persisted, serialized, returned in evidence, or logged.",
            "Missing or ambiguous credential references deny execution.",
        ),
    ),
    _decision(
        "CREDENTIAL_VERIFICATION_BOUNDARY",
        (
            "Credential presence is not proof of credential validity.",
            "Credential verification and provider connectivity are separate authorities.",
            "No provider authentication is authorized by the design freeze.",
        ),
    ),
    _decision(
        "PROVIDER_ADAPTER_CONTRACT",
        (
            "Provider adapters must use a provider-neutral immutable request and response contract.",
            "Provider-specific SDK objects must not cross the domain boundary.",
        ),
    ),
    _decision(
        "PROVIDER_REQUEST_CONTRACT",
        (
            "Every request requires a canonical request identity.",
            "Every request requires an immutable payload identity or digest.",
            "Route, model, budget, timeout, and redaction metadata must be bound before execution.",
        ),
    ),
    _decision(
        "MODEL_ROUTE_ALLOWLIST",
        (
            "The allowlist mechanism must be explicit, immutable, versioned, and owner-controlled.",
            "No provider, route, or model is execution-approved by this design freeze.",
            "The initial execution allowlist is empty.",
        ),
    ),
    _decision(
        "TIMEOUT_POLICY",
        (
            "No implicit timeout is permitted.",
            "A per-attempt timeout and total deadline must be explicitly frozen before provider execution.",
        ),
    ),
    _decision(
        "RETRY_POLICY",
        (
            "The default retry count is zero.",
            "Existing two-attempt provider behavior is not approved for Phase 12 execution.",
            "Any retry requires separate owner authority and idempotency proof.",
        ),
    ),
    _decision(
        "IDEMPOTENCY_POLICY",
        (
            "A canonical request ID and immutable payload identity are required.",
            "Duplicate, uncertain, and replay outcomes must have explicit reconciliation semantics before execution.",
        ),
    ),
    _decision(
        "PRICING_REVALIDATION",
        (
            "Historical or static pricing evidence is insufficient for paid execution.",
            "Freshness, source identity, currency, effective time, and expiry are required.",
            "Network pricing revalidation remains unauthorized.",
        ),
    ),
    _decision(
        "TOKEN_CEILING",
        (
            "Input and output token ceilings must be explicit per approved route.",
            "Missing limits deny request creation and execution.",
        ),
    ),
    _decision(
        "REQUEST_COST_CEILING",
        (
            "A maximum request cost and currency representation must be explicit.",
            "Missing or stale pricing denies execution.",
        ),
    ),
    _decision(
        "RUN_COST_CEILING",
        (
            "A cumulative run ceiling and hard-stop behavior must be explicit.",
            "The initial authorized run ceiling is zero.",
        ),
    ),
    _decision(
        "RESERVATION_SEMANTICS",
        (
            "Reservation must occur before any paid provider transmission.",
            "Reservations must bind to a canonical request ID.",
            "Expiry and uncertain-outcome reconciliation must be deterministic.",
            "Reservation creation remains unauthorized.",
        ),
    ),
    _decision(
        "USAGE_LEDGER_SEMANTICS",
        (
            "Usage accounting must be append-only and durable before live use.",
            "Events require immutable event identities and reconciliation state.",
            "Ledger mutation remains unauthorized.",
        ),
    ),
    _decision(
        "AUDIT_EVENT_SCHEMA",
        (
            "Audit evidence must be append-only, immutable, and linked by stable identities.",
            "Audit events must contain no secrets or raw authorization headers.",
        ),
    ),
    _decision(
        "REDACTION_POLICY",
        (
            "Secrets, raw credentials, provider authorization headers, and unredacted sensitive payloads must never be serialized or logged.",
            "Redaction failure must deny execution.",
        ),
    ),
    _decision(
        "KILL_SWITCH",
        (
            "A fail-closed global kill switch must be evaluated before every external or mutable action.",
            "The initial kill-switch state is engaged.",
        ),
    ),
    _decision(
        "FAIL_CLOSED_BEHAVIOR",
        (
            "Missing identity, authority, pricing, allowlist entry, reservation, verification, or safety evidence must deny execution.",
        ),
    ),
    _decision(
        "DRY_RUN_MODE",
        (
            "Dry-run may construct sanitized evidence only.",
            "Dry-run must never invoke a provider transport.",
            "Dry-run execution itself is not authorized by this design freeze.",
        ),
    ),
    _decision(
        "BOUNDED_LIVE_SHADOW_MODE",
        (
            "Live shadow requires later explicit owner authorization.",
            "Request count, cost, route, model, and time limits must be explicit.",
            "All initial limits are zero.",
            "Live shadow cannot publish externally and cannot trade.",
        ),
    ),
    _decision(
        "PRODUCTION_PUBLICATION_GATE",
        (
            "Production publication must have a separate disabled-by-default authority gate.",
            "Provider execution does not imply publication authority.",
        ),
    ),
    _decision(
        "TELEGRAM_PUBLICATION_GATE",
        (
            "Telegram polling, sending, and publication require an independent disabled-by-default owner gate.",
            "Production publication authority does not automatically imply Telegram authority.",
        ),
    ),
    _decision(
        "ROLLBACK_AND_REVOCATION",
        (
            "Credential revocation, kill-switch activation, manifest rollback, reservation reconciliation, and publication disablement require explicit deterministic behavior.",
        ),
    ),
    _decision(
        "PROMOTION_CRITERIA",
        (
            "Dry-run, live-shadow, publication consideration, and launch readiness are separate states.",
            "No state promotes automatically.",
            "Every promotion requires evidence and explicit owner adjudication.",
        ),
    ),
    _decision(
        "LAUNCH_READINESS_TRANSITION",
        (
            "Launch readiness remains NOT_READY_FOR_LAUNCH.",
            "Only a separate immutable owner-reviewed transition artifact may change launch readiness.",
        ),
    ),
    _decision(
        "ZERO_TRADING_AUTHORITY",
        (
            "Phase 12 grants no order creation, exchange execution, position mutation, fund movement, or trading authority.",
            "Provider execution, publication, Telegram delivery, and launch readiness cannot imply trading authority.",
            "Trading scope may only change through a separate explicit owner decision outside this design freeze.",
        ),
    ),
)


_AUTHORITY_MATRIX = Phase12AuthorityMatrixV1(
    repository_design_inspection_authorized=True,
    design_contract_test_authorized=True,
    implementation_authorized=False,
    credential_source_access_authorized=False,
    credential_loading_authorized=False,
    credential_verification_execution_authorized=False,
    environment_read_authorized=False,
    secret_file_read_authorized=False,
    provider_authentication_authorized=False,
    pricing_network_revalidation_authorized=False,
    provider_connectivity_authorized=False,
    provider_request_creation_authorized=False,
    provider_transmission_authorized=False,
    provider_retry_authorized=False,
    reservation_creation_authorized=False,
    ledger_mutation_authorized=False,
    runtime_invocation_authorized=False,
    manifest_activation_authorized=False,
    content_creation_authorized=False,
    filesystem_content_read_authorized=False,
    content_hashing_authorized=False,
    integrity_inspection_authorized=False,
    result_acceptance_authorized=False,
    dry_run_execution_authorized=False,
    live_shadow_execution_authorized=False,
    production_publication_authorized=False,
    telegram_publication_authorized=False,
    launch_authorized=False,
    run_size_authorized=False,
    trading_authorized=False,
)


_EVIDENCE = Phase12DesignFreezeEvidenceV1(
    phase_id="PHASE_12",
    phase_name="CONTROLLED_PRODUCTION_ENABLEMENT",
    design_version="V1",
    design_status="DESIGN_AUTHORIZED_IMPLEMENTATION_BLOCKED",
    previous_locked_phase="PHASE_11",
    previous_checkpoint="CP-11-LOCKED",
    previous_locked_head="13513e25a81d03dc52a9cc125923edf8067f6f70",
    launch_readiness="NOT_READY_FOR_LAUNCH",
    production_effect="NONE",
    zero_production_proof="PROVEN_NONE",
    owner_design_authorized=True,
    implementation_authorized=False,
    authority_matrix=_AUTHORITY_MATRIX,
    blockers=_BLOCKERS,
    active_blocker_count=20,
    classified_blocker_count=20,
    resolved_blocker_count=0,
    execution_authorized_blocker_count=0,
    shadow_governance_blocker_count=6,
    deferred_prerequisite_blocker_count=12,
    explicitly_absent_authority_blocker_count=2,
    decisions=_DECISIONS,
)


def build_phase_12_controlled_production_enablement_design_v1() -> Phase12DesignFreezeEvidenceV1:
    """Return the fixed Phase 12 design-freeze evidence without side effects."""

    return _EVIDENCE
