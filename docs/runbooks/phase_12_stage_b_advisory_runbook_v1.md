# Phase 12 Stage B Advisory Runbook V1

## 1. RELEASE IDENTITY
- **Application baseline**: bea46a683de7e094eb1fb1e3351eae489928c29f

## 2. STAGE B PURPOSE
- Emit bounded redacted advisory alerts to the operator surface without candidate or publication effect.

## 3. CONFIGURATION TRANSITION
- Modify activation configuration mode from STAGE_A_OBSERVE to STAGE_B_ADVISORY.

## 4. BUDGET AND MONITORING
- Budget precheck remains active.
- False alarm classifications are tracked.

## 5. REDACTION AND IDEMPOTENCY
- Output must be redacted (no secrets).
- Exactly one advisory per transition.

## 6. ROLLBACK
- Can rollback to STAGE_A_OBSERVE or CLOSED/Phase 09 at any time.

## 7. STAGE C AND D
- Remain disabled.
