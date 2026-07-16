# Phase 10 Deterministic Escalation Router Contract

Status: Design freeze — documentation only

This document freezes the pure Python decision boundary between the accepted
DeepSeek primary review result and any future Claude execution. It authorizes
no provider call, credential access, network access, or production effect.

## Scope

The router consumes one validated semantic DeepSeek result and one explicit,
immutable router policy. It returns one immutable deterministic escalation
decision.

The router MUST be pure, replayable, input-order invariant, and independent of
provider execution metadata.

## Non-goals

The router does not define or authorize:

- DeepSeek or Claude execution;
- live Claude model IDs, endpoints, SDKs, or credentials;
- provider availability or price inspection;
- adjudication of two provider results;
- budget reservation, spend accounting, or token accounting;
- audit persistence, replay execution, publication, delivery, or trading;
- account, balance, position, capital, or exchange access.

## Architectural position

The frozen position is:

```text
DeepSeekPrimaryReviewResultV1
+ DeterministicEscalationRouterPolicyV1
        ↓
DeterministicEscalationDecisionV1
        ├── L0 — no Claude
        ├── L1 — Claude Sonnet policy
        └── L2 — Claude Opus policy
```

If a Claude review is later required, its result is consumed by a separately
authorized deterministic adjudication layer. The router only selects an
escalation level and approved model-policy class; it does not execute a model.

## Input contract

The semantic input MUST be exactly `DeepSeekPrimaryReviewResultV1`.

The router MUST reject:

- `DeepSeekPrimaryReviewRunV1`;
- provider execution records or telemetry;
- raw provider responses;
- Claude payloads;
- normalized events, source-policy decisions, or entity mappings;
- generic mappings, lookalikes, or proxy objects;
- account, market, or trading data.

An optional `DeterministicEscalationRouterPolicyV1` MAY be supplied. It MUST
be closed and immutable. Operational execution metadata MUST NOT influence a
route.

## Route vocabulary

The only executable route values are:

| Route | Semantic name | Meaning |
| --- | --- | --- |
| `L0` | `CLEAN_OR_ROUTINE` | DeepSeek semantic review is sufficient; no Claude execution. |
| `L1` | `MODERATE_AMBIGUITY` | Secondary review under the approved Sonnet policy is required. |
| `L2` | `CRITICAL_AMBIGUITY` | Secondary review under the approved Opus policy is required. |

No `UNKNOWN`, dynamic fallback, provider-selected, or silently executable route
is permitted. Invalid or unclassifiable input fails closed.

## Router policy contract

The future closed immutable policy type is
`DeterministicEscalationRouterPolicyV1`. Its conceptual fields are:

```text
DeterministicEscalationRouterPolicyV1(
    policy_version,
    l1_claude_model_policy_id,
    l2_claude_model_policy_id,
    ambiguity_rules,
    contradiction_rules,
    evidence_rules,
    entity_confidence_rules,
    source_policy_concern_rules,
    material_risk_rules,
    forced_l2_reason_codes,
    forced_fail_closed_reason_codes,
)
```

The policy MUST contain only closed deterministic values. It MUST NOT contain
API keys, endpoints, pricing, token usage, cache state, request IDs, account
state, or publication permission.

The policy MUST NOT freeze live Claude model IDs. The L1 and L2 identifiers are
approved semantic model-policy classes, for example fictional policy labels
such as `claude-sonnet-review-policy-v1` and
`claude-opus-review-policy-v1`.

## Routing input facts

Route logic MAY inspect only validated semantic result fields:

- `review_status`;
- `review_conclusion`;
- `ambiguity_level`;
- `contradiction_present`;
- `evidence_sufficiency`;
- `entity_confidence_state`;
- `source_policy_concern_state`;
- `material_risk_flags`;
- closed `reason_codes`;
- `escalation_evidence_refs`.

Bounded structured explanation MUST NOT directly determine a route. Free-form
provider prose has no routing authority.

## L0 contract

L0 MUST be selected only when the completed semantic result is clean or
routine, with sufficient evidence, acceptable entity confidence, no critical
contradiction or ambiguity, no escalation-grade source concern, and no forced
escalation code.

An L0 decision MUST contain:

- `route = L0`;
- `route_name = CLEAN_OR_ROUTINE`;
- `claude_review_required = false`;
- no Claude model-policy identifier;
- deterministic L0 reason codes;
- exact DeepSeek result, snapshot, and payload binding.

L0 MUST NOT imply publication or trading permission.

## L1 contract

L1 represents a moderate, non-critical concern requiring the approved Sonnet
model-policy class. Examples include:

- moderate ambiguity;
- limited evidence concern;
- moderate entity-confidence concern;
- moderate source-policy concern;
- a non-critical contradiction;
- an explicitly mapped non-critical reason code.

An L1 decision MUST contain:

- `route = L1`;
- `route_name = MODERATE_AMBIGUITY`;
- `claude_review_required = true`;
- exactly the configured L1 Claude model-policy identifier;
- deterministic L1 reason codes and evidence references;
- exact DeepSeek result, snapshot, and payload binding.

No live Sonnet model ID is frozen here.

## L2 contract

L2 represents a critical concern requiring the approved Opus model-policy
class. Examples include:

- critical ambiguity;
- material contradiction;
- critical evidence deficit;
- critical entity concern;
- critical source-policy concern;
- a forced-L2 reason code;
- an explicitly frozen combination of multiple moderate concerns.

An L2 decision MUST contain:

- `route = L2`;
- `route_name = CRITICAL_AMBIGUITY`;
- `claude_review_required = true`;
- exactly the configured L2 Claude model-policy identifier;
- deterministic L2 reason codes and evidence references;
- exact DeepSeek result, snapshot, and payload binding.

No live Opus model ID is frozen here.

## Precedence rules

The highest applicable condition MUST win, in this order:

1. invalid input or non-completed semantic result fails closed;
2. forced-fail-closed rules;
3. forced-L2 rules;
4. critical conditions;
5. explicitly defined combinations producing L2;
6. moderate conditions producing L1;
7. otherwise L0.

Input flag order, reason-code order, and evidence-reference order MUST NOT
change the selected route. Implementations MUST normalize duplicates and apply
one fixed reason-code precedence.

## Non-completed result handling

`PROVIDER_REJECTED`, `INVALID_RESPONSE`, `TRANSIENT_FAILURE`,
`PERMANENT_FAILURE`, and `BUDGET_BLOCKED` are not ordinary L0 conditions.

The default contract is fail-closed with no executable route decision. A
provider execution failure is not semantic ambiguity and MUST NOT trigger an
automatic Claude fallback inside the router. A later owner-approved contract
may define a separate non-executable failure decision.

## Deterministic decision contract

The future closed immutable result type is
`DeterministicEscalationDecisionV1`:

```text
DeterministicEscalationDecisionV1(
    policy_version,
    event_snapshot_id,
    deepseek_semantic_result_id,
    deepseek_payload_sha256,
    route,
    route_name,
    claude_review_required,
    claude_model_policy_id,
    reason_codes,
    escalation_evidence_refs,
    decision_id,
)
```

The decision MUST be closed and immutable. Its route, model-policy output,
reason codes, evidence references, and source-result bindings MUST be
internally consistent. It MUST contain no request ID, attempt, retry, usage,
cost, latency, cache, publication, or trading field.

## Decision identity

`decision_id` MUST be a lowercase SHA-256 digest of canonical semantic JSON
containing:

- router policy version;
- DeepSeek semantic result identity;
- event snapshot;
- DeepSeek payload identity;
- selected route;
- Claude-required boolean;
- Claude model-policy identifier or explicit absence;
- normalized reason codes;
- normalized escalation evidence references.

The decision ID MUST exclude execution records, request IDs, attempts, retries,
usage, cost, latency, cache state, wall-clock values, and randomness.

Equivalent semantic inputs MUST converge to the same decision ID. A material
routing fact MUST change it. A caller-supplied forged ID MUST be rejected.

## Closed reason-code taxonomy

The router MUST accept only a closed vocabulary. The initial conceptual set is:

### L0 reasons

- `ROUTINE_COMPLETE`;
- `EVIDENCE_SUFFICIENT`;
- `NO_MATERIAL_CONTRADICTION`.

### L1 reasons

- `MODERATE_AMBIGUITY`;
- `LIMITED_EVIDENCE_CONCERN`;
- `MODERATE_ENTITY_CONCERN`;
- `MODERATE_SOURCE_CONCERN`;
- `NONCRITICAL_CONTRADICTION`.

### L2 reasons

- `CRITICAL_AMBIGUITY`;
- `MATERIAL_CONTRADICTION`;
- `CRITICAL_EVIDENCE_DEFICIT`;
- `CRITICAL_ENTITY_CONCERN`;
- `CRITICAL_SOURCE_CONCERN`;
- `FORCED_CRITICAL_REVIEW`.

### Fail-closed reasons

- `INVALID_RESULT_STATUS`;
- `INVALID_ROUTER_INPUT`;
- `POLICY_MISMATCH`;
- `INCONSISTENT_RESULT_BINDING`.

Provider-generated arbitrary reason strings MUST NOT directly authorize a
route. Exact final names may be refined only in the next frozen test contract.

## Multi-factor routing

The initial decision table is:

| Validated semantic facts | Result |
| --- | --- |
| Critical ambiguity | L2 / `CRITICAL_AMBIGUITY` |
| Material contradiction | L2 / `MATERIAL_CONTRADICTION` |
| Critical evidence, entity, or source concern | L2 |
| Forced critical reason | L2 / `FORCED_CRITICAL_REVIEW` |
| Moderate ambiguity alone | L1 / `MODERATE_AMBIGUITY` |
| Limited evidence concern alone | L1 / `LIMITED_EVIDENCE_CONCERN` |
| Moderate entity or source concern alone | L1 |
| Non-critical contradiction alone | L1 / `NONCRITICAL_CONTRADICTION` |
| Moderate ambiguity plus insufficient evidence | L2 only when explicitly enabled by policy |
| Multiple moderate concerns | L1 or L2 only under one explicit policy rule |
| No concern and sufficient evidence | L0 |

No numeric score, floating-point threshold, provider-controlled weight, or
dynamic tuning is permitted. If a future policy uses integers, its thresholds
and combinations MUST be closed and immutable.

## Model-policy output

The router MUST produce:

- L0: no Claude model-policy identifier;
- L1: exactly one configured Sonnet model-policy identifier;
- L2: exactly one configured Opus model-policy identifier.

The router MUST NOT inspect availability, price, token usage, or budget to
choose a model. It MUST NOT fall back from Opus to Sonnet, Sonnet to DeepSeek,
or any route to a live provider.

Model-policy identifiers are semantic routing outputs only.

## Budget and telemetry separation

The router MUST NOT inspect balances, reserve or decrement budget, calculate
provider cost, or vary a route based on runtime token or cache usage.

A valid L1 or L2 decision may later be blocked by an execution budget gate.
Routing authority and spending authority remain separate.

The router MUST ignore request IDs, attempts, retries, token counts, cache
counts, cost, duration, provider failure strings, and execution records.

## Failure and error contract

Deterministic errors MUST cover:

- wrong semantic input type;
- wrong policy type;
- unsupported policy version;
- non-completed semantic result;
- malformed or inconsistent binding;
- unknown ambiguity, risk, or reason value;
- contradictory policy configuration;
- model-policy configuration inconsistency;
- forged decision identity.

Errors MUST be bounded, deterministic, sanitized, and free of provider prose,
credentials, filesystem paths, and operational telemetry.

## Immutability and non-mutation

The router policy and decision MUST be immutable. Reason codes and evidence
references MUST be detached tuples with deterministic duplicate handling.

Equivalent calls MUST return structurally equal decisions. Caller inputs MUST
remain unchanged. The router MUST have no mutable global state, accumulated
history, or policy mutation during evaluation.

## Authority boundary

The router MUST NOT:

- call DeepSeek or Claude;
- execute retries or inspect credentials;
- use environment, network, filesystem, wall clock, or randomness;
- adjudicate provider disagreement;
- reserve budget or persist decisions;
- publish, deliver, or create production signals;
- trade or access account, balance, position, or capital state;
- mutate Master Engine state, invoke replay, or schedule background work.

Production effect remains NONE.

## Next RED test strategy

The next test slice MUST use deterministic local fixtures only and MUST freeze:

- exact public API and policy schema;
- exact `DeepSeekPrimaryReviewResultV1` input type;
- completed-status requirement;
- L0 clean path;
- L1 moderate path;
- L2 critical path;
- precedence and multi-factor combinations;
- forced-L2 and fail-closed codes;
- duplicate and input-order invariance;
- evidence-reference normalization;
- decision identity and forged-ID rejection;
- model-policy output;
- no telemetry or budget influence;
- no provider calls or execution-record input;
- immutability and absence of publication/trading authority.

## Staged implementation plan

### Stage 1 — Contract and RED tests

Documentation and deterministic tests only. No implementation or provider call.

### Stage 2 — Pure Python router

A separately authorized pure implementation may consume validated semantic
results and return decisions without provider, network, credential, or budget
execution behavior.

### Stage 3 — Claude payload/provider integration

Separately authorized integration may consume the route decision. The router
itself MUST remain pure and MUST NOT execute Claude.

This document commit authorizes documentation only.

## Acceptance criteria

Acceptance requires:

- exactly one L0, L1, or L2 route for every valid completed semantic result;
- deterministic precedence with the highest severity winning;
- input-order and duplicate invariance;
- L0 with no Claude policy;
- L1 with the configured Sonnet policy class;
- L2 with the configured Opus policy class;
- no live model ID;
- no provider, telemetry, or budget influence;
- non-completed provider results fail closed;
- immutable decision and deterministic identity;
- no adjudication, publication, delivery, or trading authority;
- production effect NONE.

## Explicitly deferred decisions

The following MUST remain unresolved until separately verified and approved:

- exact live Sonnet model ID;
- exact live Opus model ID;
- Claude transport and SDK;
- Claude cache execution and telemetry;
- Claude pricing;
- budget authorization integration;
- provider availability fallback;
- deterministic adjudication;
- production router/service integration;
- publication and trading integration.

Deferred decisions MUST NOT be silently resolved by the first router
implementation slice.
