# Phase 12 Stage B — Advisory Design V1

## 1. DOCUMENT IDENTITY
- **Phase**: 12
- **Stage**: B — Advisory
- **Version**: 1
- **Status**: DESIGN_FROZEN
- **Application baseline commit**: bea46a683de7e094eb1fb1e3351eae489928c29f
- **Owner decision**: OWNER_SELECT_PHASE_12_STAGE_B_ADVISORY_DESIGN_FREEZE
- **Scope statement**: Establish Stage B Advisory to expose bounded redacted risk explanations to operators without any candidate or publication effect.

## 2. STAGE A PROMOTION EVIDENCE
- Stage A observed successfully with stable latency, budget accounting, and zero candidate/publication effect.
- Audit completeness satisfied.

## 3. STAGE B ALLOWED EFFECT
- Preserve all Stage A observation behavior.
- Expose bounded redacted risk explanations.
- Expose bounded operator-facing advisory classifications.
- Emit exactly-once advisory evidence per eligible cycle.
- Collect false-alarm, latency, and cost evidence.

## 4. EXPLICIT NO-HOLD AND NO-BLOCK BOUNDARY
- Stage B must not HOLD a candidate.
- Stage B must not BLOCK a candidate.

## 5. PHASE 09 EXCLUSIVE AUTHORITY
- Phase 09 remains the exclusive production signal authority.
- No strategy, candidate, quota, slot, or publication mutation.

## 6. CONFIGURATION STATES
- CLOSED
- STAGE_A_OBSERVE
- STAGE_B_ADVISORY

## 7. NO IMPLICIT PROMOTION
- Modes must be explicitly set.

## 8. EXISTING-SOURCE REUSE
- `engine/phase_12_activation_configuration_v1.py`
- `engine/controlled_production_signal_cycle_v1.py`
- `Phase11FinalizationEvidenceBridgeV1` or equivalent standard logging.

## 9. EXACT ADVISORY DATA FLOW
- Configuration STAGE_B_ADVISORY enables output routing.
- Advisory generated internally.
- Emitted to operator surface.

## 10. EXACT ADVISORY SCHEMA
- Deterministic bounded payload.

## 11. OPERATOR-OUTPUT SURFACE
- Default standard output/logging (monitoring evidence surface).

## 12. IDEMPOTENCY KEY
- Cycle or transition identity.

## 13. DUPLICATE SUPPRESSION
- Exactly one advisory per cycle.

## 14. REDACTION BOUNDARY
- No credentials, headers, or raw prompts.

## 15. BOUNDED EVIDENCE
- Adherence to size and structure constraints.

## 16. BUDGET AND LATENCY ACCOUNTING
- Must log cost and response time.

## 17. FALSE-ALARM EVIDENCE CLASSIFICATION
- Categories: CONFIRMED_RELEVANT, FALSE_ALARM, INDETERMINATE, NOT_APPLICABLE.

## 18. FOURTEEN KILL SWITCHES
- All 14 kill switches from Stage A preserved.

## 19. ROLLBACK
- Supports rollback to Stage A or CLOSED/Phase 09.

## 20. RESTART SAFETY AND OBSERVABILITY
- Reconstructable state on restart.

## 21. RED CONTRACTS
- Define tests for configuration and output.

## 22. EXACT IMPLEMENTATION ALLOWLIST
- `engine/phase_12_activation_configuration_v1.py`
- `engine/controlled_production_signal_cycle_v1.py`

## 23. TARGETED-TEST PLAN
- Run new tests and existing targeted tests.

## 24. SYNTHETIC REHEARSAL
- Test Stage B behaviors without network calls.

## 25. STAGE C AND D DEFERRAL
- Stage C and D remain disabled.

## 26. PROMOTION REQUIREMENTS BEFORE STAGE C
- Low false-alarm rate, stable latency, stable cost.

## 27. PROHIBITED BEHAVIOR
- No Telegram, no push, no checkpoint, no modification of publication payloads.

## 28. EXIT CRITERIA
- Tests green, tests complete, bounded output verified.
