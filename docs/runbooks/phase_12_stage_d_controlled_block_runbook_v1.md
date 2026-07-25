# Phase 12 Stage D Controlled Block Runbook V1

## 1. PURPOSE
Provides deterministic Python final authority for intercepting and blocking a candidate signal before quota consumption, slot allocation, and publication, based on an explicit default-deny empty allowlist.

## 2. PREREQUISITES
- Stage A, B, and C prerequisites met.
- Independent BLOCK-class evidence verified.
- Critical audit verified.

## 3. CONFIGURATION & ALLOWLIST
- Default empty allowlist; owner decision required for any non-empty allowlist.
- Threshold not yet approved.
- Stage C HOLD allowlist is strictly separate.

## 4. BOUNDARIES & EXCLUSIONS
- Deterministic BLOCK boundary: Pre-quota, pre-slot, pre-publication.
- Already-published-event exclusion.
- Unrelated-event exclusion.
- Idempotency: RESERVATION_TRANSITION_ID.
- Duplicate suppression: EXACTLY_ONCE.
- Redaction: NO_SECRET_EXPOSURE.
- Monitoring and 14 kill switches active.
- Rollback paths: STAGE_C, STAGE_B, STAGE_A, CLOSED.
- Restart recovery supported.
- Incident response procedures apply for rollback triggers.

## 5. AUDIT & ACTIVATION
- Critical audit required.
- No runtime activation authorized; no production class approved.
- Push/checkpoint prohibited.
