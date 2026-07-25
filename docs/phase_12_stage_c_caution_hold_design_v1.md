# Phase 12 Stage C — Caution Hold Design V1

## 1. DOCUMENT IDENTITY
- **Phase**: 12
- **Stage**: C — Caution / Hold
- **Version**: 1
- **Status**: DESIGN_FROZEN
- **Application baseline commit**: c10133d582e1ecaa9d9a6ff9c12442c419a717d7

## 2. ALLOWED EFFECT & DEFAULT DENY
- Deterministic Python final authority.
- Explicit default-deny empty allowlist.
- Explicit prohibition on HOLD without owner-approved class binding.
- Applies HOLD only before quota consumption and publication progression.

## 3. CONFIGURATION STATES
- CLOSED
- STAGE_A_OBSERVE
- STAGE_B_ADVISORY
- STAGE_C_CAUTION_HOLD

## 4. SCHEMA AND BOUNDARIES
- No implicit promotion.
- Deterministic class allowlist schema.
- HOLD decision schema with bounded redacted HOLD reason.
- Idempotency key: RESERVATION_TRANSITION_ID.
- Duplicate-HOLD suppression.
- Stage B advisory preservation; Stage D exclusion.
- Fourteen kill switches remain active.
- Exact source allowlist: engine/phase_12_activation_configuration_v1.py, engine/controlled_production_signal_cycle_v1.py

## 5. EXIT CRITERIA
- Empty allowlist enforces zero HOLDs.
