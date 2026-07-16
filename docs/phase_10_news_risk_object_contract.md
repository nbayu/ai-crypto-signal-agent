# Phase 10 News Risk Object Contract

Status: DESIGN FROZEN — DOCUMENTATION ONLY

## Purpose and scope

This document freezes a pure semantic News Risk Object boundary for one
immutable event snapshot. It consumes one accepted deterministic adjudication
result and represents news-derived risk for later, separately authorized
Signal Gate evaluation.

The object is informational semantic data only. Production effect remains
`NONE`.

This contract covers the exact input boundary, immutable policy and output
objects, closed vocabularies, deterministic precedence, mappings, identity,
errors, isolation, staged implementation, RED tests, acceptance, and deferred
decisions.

## Non-goals

This slice MUST NOT implement or authorize provider calls, routing, retries,
model selection, provider adapters, budget or pricing logic, market data,
technical indicators, account state, Signal Gate mutation, production signals,
publication, Telegram delivery, trading, persistence, replay, or background
work.

The News Risk Object MUST NOT select direction or calculate entry, stop,
target, size, leverage, or quantity.

## Architectural position

```text
DeterministicAdjudicationResultV1 + NewsRiskPolicyV1
        ↓
NewsRiskObjectV1
        ↓
later, separately authorized Signal Gate evaluation
```

The News Risk Object is a closed input to a later gate. It is not the gate and
MUST NOT open, close, or mutate one.

## Exact input contract

The future builder MUST consume exactly:

- `DeterministicAdjudicationResultV1`;
- `NewsRiskPolicyV1`.

It MUST reject DeepSeek or Claude semantic results, router decisions, provider
runs, execution records, raw events, payloads, dictionaries, mappings,
lookalikes, account state, market state, signal state, and trading state.
Subclasses and proxies MUST be rejected where exact type binding is required.
No semantic reconstruction from mappings is permitted.

## Completed and accepted adjudication requirement

The adjudication result MUST be the exact accepted semantic type, use the
supported adjudication policy version, carry a valid
`adjudication_result_id`, use closed outcome and final-state vocabularies, and
have internally consistent event, route, source, reason, and evidence
bindings.

Unsupported versions, malformed states, inconsistent bindings, and forged
identities MUST fail closed. The builder MUST NOT reinterpret a malformed or
failed result as a fresh provider opinion.

## NewsRiskPolicyV1

`NewsRiskPolicyV1` MUST be immutable, closed, deterministic, and free of
runtime state. Its conceptual fields are:

```text
policy_version
supported_adjudication_policy_versions
supported_routes
outcome_to_risk_classification
ambiguity_precedence
contradiction_precedence
evidence_precedence
entity_precedence
source_precedence
material_risk_precedence
fail_closed_outcomes
blocking_reason_codes
caution_reason_codes
deterministic_reason_order
maximum_reason_code_count
maximum_evidence_reference_count
```

The policy MUST normalize closed collections deterministically, collapse exact
duplicates, reject unknown fields and values, reject contradictory tables, and
validate positive bounded integer limits. Boolean and floating-point limits
MUST be rejected.

The policy MUST NOT contain model IDs, provider weights, floating-point
confidence, tokens, cache, cost, budget, market price, technical indicators,
direction, entry, stop, target, quantity, leverage, account state, or
publication permission. There MUST be no dynamic scoring, learned risk model,
or provider hierarchy.

## Risk classification vocabulary

The vocabulary is closed:

- `CLEAR` — no material news-derived blocker was identified;
- `CAUTION` — qualified or incomplete conditions remain;
- `ELEVATED` — material unresolved risk is present;
- `BLOCKING` — later Signal Gate approval MUST be prevented by policy;
- `FAIL_CLOSED` — invalid, unsupported, or unsafe semantic conditions exist.

Equivalent frozen names MAY be used only if the vocabulary remains closed. The
object MUST NOT express `BUY`, `SELL`, `LONG`, `SHORT`, `ENTRY`, `EXIT`, or
`HOLD`.

## News Gate recommendation vocabulary

The object MAY carry a closed, non-executable recommendation for a later gate:

- `NO_NEWS_RESTRICTION`;
- `REQUIRE_CAUTION`;
- `REQUIRE_BLOCK`;
- `FAIL_CLOSED`.

The field SHOULD be named `news_gate_recommendation`, not
`signal_permission`. It MUST NOT open, close, mutate, or evaluate a gate,
trigger a signal, publish, deliver, or trade.

## Deterministic precedence

The highest applicable severity MUST win, regardless of caller order:

1. invalid input or identity → `FAIL_CLOSED`;
2. unsupported policy or version → `FAIL_CLOSED`;
3. adjudication `FAIL_CLOSED` → `FAIL_CLOSED`;
4. blocking adjudication reason → `BLOCKING` or `FAIL_CLOSED`;
5. critical material-risk state → `BLOCKING` or `FAIL_CLOSED`;
6. unresolved critical contradiction → `BLOCKING` or `FAIL_CLOSED`;
7. critical entity or source state → `BLOCKING` or `FAIL_CLOSED`;
8. insufficient evidence → `CAUTION`, `ELEVATED`, or `BLOCKING`;
9. material disagreement → `ELEVATED` or `BLOCKING`;
10. qualified consensus → `CAUTION`;
11. confirmed consensus → `CLEAR`;
12. accepted L0 primary review → the explicit policy mapping, normally
    `CLEAR` or `CAUTION`.

No numeric score, probability, floating-point confidence, or runtime weight MAY
participate.

## Adjudication outcome mapping

The policy MUST define a closed mapping for every accepted outcome:

| Adjudication outcome | Default semantic treatment |
| --- | --- |
| `ACCEPT_DEEPSEEK` | accepted single-review mapping, subject to final states |
| `ACCEPT_CLAUDE` | explicit policy-approved mapping only |
| `CONSENSUS_CONFIRMED` | normally `CLEAR`, unless higher state overrides |
| `CONSENSUS_WITH_QUALIFICATION` | normally `CAUTION` |
| `MATERIAL_DISAGREEMENT` | `ELEVATED` or `BLOCKING` |
| `INSUFFICIENT_EVIDENCE` | `CAUTION`, `ELEVATED`, or `BLOCKING` |
| `FAIL_CLOSED` | `FAIL_CLOSED` |

No outcome MAY silently clear a more severe final material-risk,
contradiction, entity, or source state.

## Material-risk and contradiction mapping

The policy MUST explicitly handle no risk, qualified concern, elevated risk,
critical unresolved risk, and fail-closed risk. Critical unresolved material
risk MUST map to `BLOCKING` or `FAIL_CLOSED`.

It MUST also handle no contradiction, resolved contradiction, qualified
contradiction, unresolved contradiction, critical contradiction, and
fail-closed contradiction. Critical unresolved contradiction MUST NOT map to
`CLEAR`. Provider prose MUST NOT resolve contradiction.

No risk mapping may become a trading action.

## Evidence mapping

The policy MUST handle sufficient, qualified, insufficient, malformed, missing,
and fail-closed evidence. Insufficient evidence MUST NOT map directly to
unrestricted `CLEAR` unless an explicit policy rule permits it and no higher
state exists.

Evidence references MUST be validated identifiers, sorted, duplicate-free,
immutable, and bounded. Article bodies, excerpts, and provider explanations
MUST NOT be copied.

## Entity and source mapping

The policy MUST handle confirmed, qualified, elevated, critical, and fail-closed
entity and source assessments. Critical entity or source concern MUST map to
`BLOCKING` or `FAIL_CLOSED`. Provider preference MUST NOT resolve conflicting
critical assessments.

## Reason-code taxonomy

News Risk reason codes MUST be closed, bounded, deduplicated, and emitted in a
deterministic policy-defined order. Conceptual values are:

Clear: `ADJUDICATION_CONFIRMED`, `NO_MATERIAL_NEWS_RISK`,
`EVIDENCE_SUFFICIENT`.

Caution: `QUALIFIED_ADJUDICATION`, `EVIDENCE_LIMITED`,
`MODERATE_ENTITY_CONCERN`, `MODERATE_SOURCE_CONCERN`.

Elevated: `MATERIAL_DISAGREEMENT`, `UNRESOLVED_CONTRADICTION`,
`MATERIAL_RISK_PRESENT`, `INSUFFICIENT_EVIDENCE`.

Blocking: `CRITICAL_MATERIAL_RISK`, `CRITICAL_CONTRADICTION`,
`CRITICAL_ENTITY_CONCERN`, `CRITICAL_SOURCE_CONCERN`,
`BLOCKING_ADJUDICATION_REASON`.

Fail closed: `INVALID_ADJUDICATION`, `UNSUPPORTED_POLICY`, `FORGED_IDENTITY`,
`FAIL_CLOSED_ADJUDICATION`.

Names MAY be refined only while remaining closed and policy-defined. Arbitrary
provider reason text MUST NOT become authority.

## NewsRiskObjectV1 contract

The future `NewsRiskObjectV1` MUST be immutable and closed. Its conceptual
fields are:

```text
policy_version
event_snapshot_id
adjudication_policy_version
adjudication_result_id
route
risk_classification
news_gate_recommendation
final_ambiguity_state
final_contradiction_state
final_evidence_state
final_entity_state
final_source_state
final_material_risk_state
reason_codes
evidence_refs
structured_explanation
news_risk_object_id
```

It MUST NOT include provider request IDs, execution records, attempts,
retries, tokens, cache, cost, duration, budget, market price, technical score,
direction, entry, stop loss, take profit, quantity, leverage, account,
balance, position, publication state, delivery state, or trading action.

## News Risk Object identity

`news_risk_object_id` MUST be a lowercase SHA-256 over canonical semantic
fields containing the News Risk policy version, event snapshot, adjudication
policy version, adjudication result ID, route, risk classification, News Gate
recommendation, final closed assessment states, reason codes, and evidence
references.

It MUST exclude itself, request IDs, execution records, attempts, retries,
tokens, cache, cost, duration, budget, wall clock, randomness, market data,
account state, and provider free text. Equivalent inputs MUST converge;
material changes MUST diverge; forged direct construction MUST fail.

## Free-text non-authority

DeepSeek, Claude, and adjudication explanations beyond closed semantic states,
embedded system messages, role injection, publication commands, Signal Gate
commands, and trading commands MUST NOT influence classification.

The object MAY include a bounded deterministic explanation generated from closed
risk codes only. It MUST NOT copy provider prose.

## Immutability and non-mutation

The policy and object MUST be immutable. Reason codes and evidence references
MUST use immutable tuples or an equivalent representation. The adjudication
input MUST remain unchanged. Collections MUST be defensively detached, sorted,
deduplicated, and bounded.

There MUST be no global state, risk history, adaptive policy, learned provider
preference, clock dependency, or randomness. Equivalent calls MUST be
structurally equal.

## Failure and error contract

The boundary MUST raise deterministic sanitized errors for wrong input or
policy type, unsupported policy version, invalid outcome or route, forged
adjudication identity, malformed final state, malformed evidence, unknown
reason, contradictory policy, and forged News Risk identity.

Errors MUST be concise, bounded, rule-specific, and MUST NOT expose provider
prose, raw payloads, article text, request IDs, tokens, cost, credentials,
filesystem paths, arbitrary representations, memory addresses, or stack
traces.

## Telemetry, budget, and market isolation

The News Risk layer MUST NOT accept or inspect provider runs, execution
records, request IDs, attempts, retries, token usage, cache usage, cost,
duration, budget authorization, provider pricing, market prices, candles,
technical indicators, account state, balances, or positions.

Equivalent adjudication semantics MUST produce identical risk objects regardless
of operational history. No budget mutation, market lookup, or pricing
calculation is permitted.

## Authority boundary

The News Risk layer MUST NOT call providers, route, retry, select models,
inspect credentials, access network or environment, use filesystem, reserve
budget, mutate Signal Gate, create production signals, publish, deliver
Telegram, trade, access account/balance/position/capital or exchanges, mutate
Master Engine state, persist, replay, or schedule background work.

Production effect remains `NONE`.

## Staged implementation plan

### Stage 1 — Contract and RED tests

- documentation;
- deterministic local fixtures;
- no implementation;
- no Signal Gate integration.

### Stage 2 — Pure News Risk Object builder

- exact `DeterministicAdjudicationResultV1` input;
- deterministic mapping tables;
- immutable output;
- no provider, market, or Signal Gate calls.

### Stage 3 — Signal Gate contract and implementation

- separately authorized;
- consumes `NewsRiskObjectV1`;
- no silent integration into the News Risk builder.

This commit authorizes documentation only.

## RED test strategy

Future RED tests MUST cover exact API, policy schema and version binding,
exact adjudication input type, identity validation, outcome mapping,
precedence, risk/contradiction/evidence/entity/source mappings, fail closed,
reason codes, evidence references, deterministic and forged identity,
free-text non-authority, immutability, telemetry/budget/market isolation, and
absence of provider, network, credential, Signal Gate, publication, and trading
authority.

Tests MUST use deterministic local adjudication fixtures only. They MUST NOT
call providers, inspect credentials, access environment secrets, use current
time or randomness, or perform external I/O.

## Acceptance criteria

Acceptance requires exact adjudication input type, valid identity, closed
immutable policy and output schemas, deterministic precedence, conservative
handling of insufficient evidence, non-clear critical risk/contradiction/
entity/source states, deterministic reason codes and identity, inert provider
prose, isolated telemetry/budget/market data, no provider calls, no Signal Gate
mutation, no publication, no trading, and production effect `NONE`.

## Deferred decisions

The following remain explicitly deferred:

- exact Signal Gate schema;
- gate-open and gate-close semantics;
- risk-to-signal permission mapping;
- production integration;
- publication and Telegram delivery;
- persistent storage;
- human override;
- market-data combination;
- trading integration;
- Phase 11 consumption.

No deferred decision MAY be silently implemented in this contract or its
Stage 2 builder.
