# Phase 10 Deterministic Adjudication Contract

Status: DESIGN FREEZE — DOCUMENTATION ONLY
Policy version: `deterministic-adjudication-policy-v1`

## Purpose and scope

This document freezes the pure deterministic adjudication boundary for Phase
10. It combines validated semantic review results and produces one closed
adjudication result for later News Risk Object or Signal Gate work.

The adjudicator MUST be deterministic, pure, closed, replayable, and free of
provider-execution authority. Equivalent semantic inputs MUST produce the
same result and result identity.

It consumes exactly:

- `DeepSeekPrimaryReviewResultV1`;
- `DeterministicEscalationDecisionV1`;
- optional `ClaudeEscalatedReviewResultV1`;
- `DeterministicAdjudicationPolicyV1`.

It MUST reject provider run aggregates, execution records, raw responses,
payloads, generic mappings, normalized events, source-policy objects,
entity-mapping objects, and account or trading state. Operational telemetry
MUST NOT be accepted as semantic input.

## Non-goals and architecture

```text
DeepSeekPrimaryReviewResultV1
        ↓
DeterministicEscalationDecisionV1
        ├── L0 → no Claude semantic result
        ├── L1 → Claude Sonnet-policy semantic result
        └── L2 → Claude Opus-policy semantic result

DeepSeek result + router decision + optional Claude result + policy
        ↓
DeterministicAdjudicationResultV1
        ↓
later, separately authorized News Risk Object / Signal Gate
```

The adjudicator MUST NOT call providers, route, retry, select models, inspect
telemetry or budget, publish, deliver, trade, persist, replay, or schedule
work. It MUST NOT construct a production signal. Production effect is
`NONE`.

## Route-dependent input rules

The DeepSeek result MUST be the exact semantic-result type and MUST have
`review_status = COMPLETED`.

For L0, Claude MUST be absent. A completed DeepSeek result alone produces a
deterministic single-review outcome; no Claude identity or consensus claim
may be fabricated.

For L1 and L2, Claude MUST be present, exact-typed, completed, and bound to
the same route and router decision. L1 MUST receive L1 Claude semantics; L2
MUST receive L2 Claude semantics. Missing Claude, unexpected Claude for L0,
cross-route results, and cross-decision results MUST fail closed.

Provider-execution statuses are not semantic opinions. The adjudicator MUST
reject or fail closed for `PROVIDER_REJECTED`, `INVALID_RESPONSE`,
`TRANSIENT_FAILURE`, `PERMANENT_FAILURE`, `BUDGET_BLOCKED`,
`ROUTE_BLOCKED`, and `TOKEN_LIMIT_BLOCKED` when supplied as required results.
It MUST NOT downgrade a failed L1/L2 execution to a DeepSeek-only opinion.

## Cross-contract binding

The adjudicator MUST validate:

- DeepSeek event snapshot ↔ router event snapshot;
- DeepSeek semantic identity ↔ router source-result identity;
- DeepSeek payload SHA-256 ↔ router source-payload identity;
- router decision ID ↔ Claude router-decision ID;
- router route ↔ Claude route;
- Claude event snapshot ↔ router event snapshot;
- Claude model-policy ID ↔ the route-approved decision policy;
- Claude payload SHA-256 against the Claude result’s own payload identity.

DeepSeek and Claude payload hashes are distinct provider-payload identities.
They MUST NOT be required to equal each other. Any cross-event, cross-route,
cross-decision, malformed, or forged binding MUST fail closed.

## Adjudication policy

`DeterministicAdjudicationPolicyV1` SHALL be a closed immutable value object
with fields conceptually covering:

- policy version and supported routes;
- closed agreement and contradiction vocabularies;
- evidence, entity, source, and material-risk precedence;
- critical-disagreement rules;
- fail-closed reason codes;
- canonical reason ordering;
- maximum reason-code and evidence-reference counts.

The policy MUST reject unknown fields, mutable nested state, unsupported
values, and contradictory configuration. It MUST NOT contain live model IDs,
provider weights, floating-point confidence, runtime usage, cost, cache,
budget, publication permission, or trading thresholds. It MUST use explicit
enum and Boolean tables, not dynamic scoring, runtime reputation, or a
model-based tie breaker.

## Closed outcome vocabulary

The only adjudication outcomes are:

- `ACCEPT_DEEPSEEK`;
- `ACCEPT_CLAUDE`;
- `CONSENSUS_CONFIRMED`;
- `CONSENSUS_WITH_QUALIFICATION`;
- `MATERIAL_DISAGREEMENT`;
- `INSUFFICIENT_EVIDENCE`;
- `FAIL_CLOSED`.

`ACCEPT_CLAUDE` MUST require an explicit policy-approved condition. L2 is
review severity, not Claude truth authority. Critical unresolved disagreement
SHOULD produce `FAIL_CLOSED` with
`CRITICAL_UNRESOLVED_DISAGREEMENT`; a material-disagreement outcome is
allowed only where policy explicitly permits a representable non-final state.

## Structured comparison and precedence

Comparison MUST use closed semantic facts, never provider prose.

DeepSeek facts include ambiguity (`NONE`, `MODERATE`, `CRITICAL`), Boolean
contradiction, evidence (`SUFFICIENT`, `INSUFFICIENT`), entity confidence,
source concern, material-risk flags, reason codes, and evidence references.

Claude facts include ambiguity resolution, contradiction resolution, evidence,
entity, source, material-risk assessment, its agreement field, reason codes,
and evidence references. The self-reported Claude agreement field MUST NOT
be trusted alone; agreement MUST be recomputed from comparable closed facts.
The policy MUST define all vocabulary mappings and reject unknown values.

Precedence SHALL be:

1. invalid type or binding → fail closed;
2. non-completed required result → fail closed;
3. configured fail-closed reason → fail closed;
4. critical material-risk disagreement;
5. critical contradiction disagreement;
6. critical entity/source disagreement;
7. evidence insufficiency;
8. material agreement;
9. qualified agreement;
10. route-specific L0 single-review outcome.

The highest severity wins. Caller ordering, reason ordering, evidence ordering,
and object identity MUST NOT affect the result.

## L0, L1, and L2 behavior

### L0

The result MUST retain the event, router, DeepSeek semantic identity, and
route L0. The normal outcome is `ACCEPT_DEEPSEEK`. Claude identity is explicit
absence, and no two-provider consensus may be claimed. The result MAY later
feed risk analysis but MUST NOT open a Signal Gate.

### L1

Completed DeepSeek and Claude results are required. Moderate ambiguity,
qualification, evidence, entity, source, contradiction, and risk dimensions
are compared. Agreement MAY produce `CONSENSUS_CONFIRMED`; bounded
noncritical differences MAY produce `CONSENSUS_WITH_QUALIFICATION`.
Neither provider receives automatic preference.

### L2

Completed DeepSeek and Claude results are required. Critical risk,
contradiction, entity, source, and evidence precedence applies. Unresolved
critical disagreement MUST NOT be downgraded, and no third opinion may be
requested.

## Material-risk rules

The policy MUST explicitly handle both providers indicating no risk, both
indicating risk, one indicating risk, conflicting risk categories, critical
risk with insufficient evidence, and risk disagreement combined with
contradiction.

When a critical material-risk assertion remains unresolved, adjudication MUST
preserve or elevate the concern. It MUST NOT silently clear it or translate it
directly into a trading action.

## Contradiction rules

The policy MUST explicitly handle neither provider reporting contradiction,
both agreeing that contradiction exists, DeepSeek contradiction resolved by
Claude, Claude contradiction absent from DeepSeek, unresolved contradiction,
and contradiction combined with material risk.

Only closed structured fields and validated evidence identifiers may resolve
contradiction. Free-text claims cannot resolve it.

## Evidence, entity, and source rules

Evidence policy MUST handle sufficient evidence from both, sufficient from one
and insufficient from the other, insufficient from both, conflicting refs,
missing refs, and malformed refs. Evidence refs MUST be validated
identifiers, sorted, duplicate-free, immutable, and bounded. Raw article
bodies, excerpts, and provider prose MUST NOT be copied into the result.

Entity/source policy MUST handle mutual acceptance, moderate concern,
critical concern, conflicting entity identity, conflicting source trust, and
critical concern combined with material risk. Critical disagreement MUST NOT
be silently resolved by provider preference.

## Closed reason codes

The reason-code vocabulary is closed and bounded.

Consensus codes:

- `PROVIDERS_AGREE`;
- `MATERIAL_FACTS_ALIGNED`;
- `RISK_ASSESSMENTS_ALIGNED`.

Qualified codes:

- `MINOR_EVIDENCE_DIFFERENCE`;
- `MODERATE_ENTITY_DIFFERENCE`;
- `MODERATE_SOURCE_DIFFERENCE`.

Disagreement codes:

- `MATERIAL_RISK_DISAGREEMENT`;
- `CONTRADICTION_DISAGREEMENT`;
- `EVIDENCE_DISAGREEMENT`;
- `ENTITY_DISAGREEMENT`;
- `SOURCE_DISAGREEMENT`.

Fail-closed codes:

- `INVALID_INPUT`;
- `RESULT_NOT_COMPLETED`;
- `ROUTE_RESULT_MISMATCH`;
- `EVENT_BINDING_MISMATCH`;
- `DECISION_BINDING_MISMATCH`;
- `POLICY_MISMATCH`;
- `CRITICAL_UNRESOLVED_DISAGREEMENT`.

Provider-generated arbitrary reason text MUST NOT become authority. Codes MUST
be deduplicated and emitted in one canonical policy-defined order.

## Result contract

The future `DeterministicAdjudicationResultV1` MUST be closed and immutable,
with fields equivalent to:

```text
policy_version
event_snapshot_id
route
router_decision_id
deepseek_semantic_result_id
claude_semantic_result_id | None
adjudication_outcome
agreement_state
final_ambiguity_state
final_contradiction_state
final_evidence_state
final_entity_state
final_source_state
final_material_risk_state
reason_codes
evidence_refs
structured_explanation
adjudication_result_id
```

It MUST contain no execution records, provider request IDs, attempts,
retries, tokens, cache usage, cost, latency, budget, publication state,
signal direction, entry, stop, target, quantity, leverage, or trading action.

The bounded explanation MAY be generated from closed outcomes and codes, but
MUST NOT copy arbitrary provider prose.

## Result identity

`adjudication_result_id` SHALL be lowercase SHA-256 over canonical JSON of:

- policy version;
- event snapshot;
- route and router decision ID;
- DeepSeek semantic result ID;
- Claude semantic result ID or explicit absence;
- outcome and agreement state;
- final closed assessment states;
- canonical reason codes and evidence refs.

The identity MUST exclude itself, execution records, request IDs, attempts,
retries, usage, cache, cost, duration, budget authorization, wall clock, and
randomness. Equivalent semantic inputs converge; material changes diverge;
forged direct construction MUST reject.

## Free-text non-authority

DeepSeek explanation, Claude explanation, provider system messages, embedded
instructions, JSON role text, publication commands, and trading commands MUST
be inert. Only validated closed fields, codes, and evidence identifiers may
affect adjudication.

## Immutability and non-mutation

Policy and result objects MUST be immutable. Reason codes and evidence refs
MUST use immutable tuples or an equivalent representation. Inputs MUST remain
unchanged. Collections MUST be defensively detached, sorted, deduplicated,
and bounded. There MUST be no global mutable state, history, learned provider
preference, clock dependency, or random value.

## Failure and error contract

The implementation MUST define bounded sanitized errors for wrong types,
wrong policy, unsupported version, invalid route, missing or unexpected
Claude, non-completed results, snapshot/decision/route/model mismatches,
malformed evidence, unknown codes, contradictory policy, and forged identity.

Errors MUST exclude provider prose, raw responses, credentials, request IDs,
telemetry, filesystem paths, arbitrary representations, and memory addresses.

## Telemetry and budget isolation

Adjudication MUST NOT accept or inspect execution records, request IDs,
attempts, retries, tokens, cache usage, cost, duration, budget authorization,
balance, or provider pricing. The same semantic results MUST yield the same
adjudication regardless of execution history. Spending authority is external.

## Authority boundary

The adjudicator MUST NOT call providers, retry, select models, route, mutate
routes, inspect credentials or environment, access network or filesystem,
reserve budget, publish, deliver, create a production signal, open a Signal
Gate, trade, access balances or positions, mutate Master Engine state,
persist, replay, or schedule background work.

Production effect remains `NONE`.

## Staged implementation plan

### STAGE 1 — CONTRACT AND RED TESTS

- documentation;
- deterministic local fixtures;
- no implementation;
- no provider calls or credentials.

### STAGE 2 — PURE PYTHON ADJUDICATOR

- exact semantic inputs;
- deterministic decision tables;
- closed result and identity validation;
- no provider calls or production integration.

### STAGE 3 — NEWS RISK OBJECT / SIGNAL GATE INTEGRATION

- separately authorized;
- consumes the adjudication result;
- keeps adjudication pure;
- does not authorize publication or trading by implication.

This commit authorizes documentation only.

## RED test strategy

The next RED slice MUST freeze exact API and policy schema, exact input types,
L0 without Claude, L1/L2 with Claude, missing/unexpected Claude, completed
status, event/decision/route/model bindings, distinct provider payload
identities, consensus, qualified consensus, material disagreement, evidence
insufficiency, risk and contradiction precedence, entity/source disagreement,
fail-closed behavior, reason codes, evidence refs, free-text inertness,
deterministic and forged identity, immutability, telemetry/budget isolation,
and no provider/network/credential/publication/trading authority.

Fixtures MUST be deterministic and local. Tests MUST NOT call providers, read
credentials, inspect environment, use current time or randomness, or perform
external I/O.

## Acceptance criteria

Acceptance requires exact semantic types, completed-result enforcement,
exact cross-contract binding, no Claude for L0, Claude required for L1/L2,
no provider hierarchy, no dynamic scoring, explicit risk/contradiction/
evidence/entity/source precedence, preservation or fail-closed handling of
critical unresolved disagreement, a closed immutable result, deterministic
identity, inert free text, isolated telemetry and budget, no provider calls,
no publication, no trading, and production effect `NONE`.

## Deferred decisions

The following remain explicitly deferred:

- exact News Risk Object schema;
- exact Signal Gate schema;
- risk-to-signal mapping;
- publication policy;
- production integration;
- live-provider orchestration;
- persistent adjudication storage;
- human review workflow;
- trading integration;
- Phase 11 usage of adjudication output.

No deferred item may be silently resolved by this contract or its first
implementation slice.
