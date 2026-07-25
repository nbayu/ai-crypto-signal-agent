# Phase 12 Stage A Observe Operator Runbook

## Identity
- **Application Release**: `291ab4697f7b7db16df5907c174b6b6ea6e616ba` (with Stage A enhancements)
- **Design Release**: `c58ed36213bbe0adb1803a61fc375a67e3c8c243`

## Purpose
Stage A Observe securely isolates provider intelligence outputs without affecting existing Phase 09 candidate structures or triggering publications.

## Stage A Zero-Effect Boundary
Stage A must not modify candidates, emit signals, or use actual provider credentials during local design/implementation phases.

## Prerequisite Checklist
- [ ] Phase 12 Activation Configuration V1 loaded
- [ ] Provider identity mapped (synthetic or safely isolated)

## Configuration
**CLOSED**:
Fully disables Phase 12 features. Execution safely reverts to Phase 09 native processing.
**STAGE_A_OBSERVE**:
Enables safe intelligence cycle monitoring. Bounded and isolated, it produces redacted storage traces while terminating before candidate mutation.

## Credential-Reference Handling
Credentials must only be referenced via secure, detached Phase 11 loaders. Values must not be stored, logged, or checked into Git.

## Connectivity Authorization
Real provider connectivity is NOT authorized by this runbook. It requires a separate explicit owner decision.

## Budget Configuration Placeholder
Budget caps must be explicitly defined and supplied via the separate credential/provider readiness authorization.

## Kill-Switch Inventory
Stage A is bounded by immediate closed failures under these conditions:
1. Provider outage
2. Budget cap reached
3. Excessive latency
4. Schema drift
5. Model identity mismatch
6. Unbounded retry behavior
7. Source timestamp failure
8. Point-in-time integrity failure
9. Protected strategy/publication mutation attempt
10. Fail-policy/runtime-behavior divergence
*(Additional kill switches deferred until measurable)*

## Monitoring Classifications
Expect deterministic, redacted outcomes mapped to `STAGE_A_OBSERVE_PROVIDER_OUTAGE` or `FAIL_CLOSED`.

## Evidence Locations
Evidence is stored locally using non-secret logical identifiers (e.g., `stage_a_evidence_store_v1`).

## Phase 09 Rollback Trigger
Change configuration to `CLOSED`. Restart service.

## Rollback Verification
Verify no Stage A logs are generated. Confirm Phase 09 `NO_ELIGIBLE_SIGNAL` or normal execution proceeds unchanged.

## Restart Recovery
System is idempotent. `systemctl restart` restores fail-closed states cleanly.

## Incident Handling
- In event of terminal conditions (e.g. timeout, identity mismatch), the pipeline safely terminates.
- **No retry after a terminal blocked condition unless separately authorized.**

## Operational Limits
- **Stage B–D disabled**: Advisory, HOLD, and BLOCK logics are strictly inactive.
- **Service remains disabled in local readiness**: Do not activate `systemctl start`.
- **Runtime enablement not authorized**: Awaiting owner review.
- **Provider execution not authorized**: Awaiting explicit bounds.
- **Production enablement not authorized**: System strictly off.
- **Checkpoint not ready**: No checkpoint creation authorized yet.
