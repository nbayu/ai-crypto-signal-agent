# Phase 10 Deterministic Signal Gate Contract

Status: DESIGN FREEZE — DOCUMENTATION ONLY

## Purpose and scope

This document freezes a pure deterministic Signal Gate that consumes exactly
one accepted `NewsRiskObjectV1` and one immutable `SignalGatePolicyV1`, and
produces one immutable `SignalGateDecisionV1`.

The gate determines only whether news-derived semantic risk permits,
restricts, or blocks downstream signal eligibility. Production effect remains
NONE.

The decision is semantic authorization data only. It is not a production
signal, execution command, publication instruction, or order instruction.

## Non-goals

The Signal Gate MUST NOT create a signal, select an asset or direction, read
market or account state, calculate entry, stop, target, quantity, size, or
leverage, call providers, publish, deliver, place or modify orders, persist,
replay, or mutate production services.

## Architectural position

```text
NewsRiskObjectV1
+ SignalGatePolicyV1
        ↓
SignalGateDecisionV1
        ↓
later, separately authorized downstream eligibility evaluation
```

## Exact input contract

The future builder MUST accept exactly `NewsRiskObjectV1` and
`SignalGatePolicyV1`.

It MUST reject adjudication results, DeepSeek or Claude results, router
decisions, provider runs, raw events, payloads, dictionaries, mappings,
lookalikes, market data, scanner scores, signal candidates, account state,
balances, positions, orders, strings, and `None`.

No reconstruction from generic mappings is permitted.

## Accepted News Risk requirement

The News Risk input MUST be the exact accepted semantic type, use the
supported News Risk policy version, carry a valid `news_risk_object_id`, use
closed risk and recommendation vocabularies, and contain valid final states,
event and route bindings, reason codes, and evidence references.

The gate MUST validate the identity before mapping and MUST NOT repair
malformed or forged objects. Unsupported versions and forged identities MUST
fail closed.

## Signal Gate policy contract

The future immutable `SignalGatePolicyV1` SHALL have a closed schema covering:

- `policy_version`;
- `supported_news_risk_policy_versions`;
- `supported_routes`;
- `supported_risk_classifications`;
- `supported_news_gate_recommendations`;
- `risk_to_gate_state`;
- `recommendation_to_gate_state`;
- `blocking_reason_codes`;
- `caution_reason_codes`;
- `fail_closed_reason_codes`;
- `deterministic_reason_order`;
- `maximum_reason_code_count`;
- `maximum_evidence_reference_count`.

The policy MUST use closed tables, deterministic tuple normalization,
duplicate collapse, and bounded positive integer limits. Boolean and float
limits MUST be rejected. Contradictory and unknown policy fields MUST be
rejected.

It MUST NOT contain provider model IDs or weights, confidence or probability,
tokens, cache, cost, budget, market prices, technical indicators, scanner
scores, direction, trade parameters, account state, publication permission,
or order permission. No dynamic scoring, learned model, or provider
hierarchy is allowed.

## Gate state vocabulary

The closed gate-state vocabulary is:

- `OPEN`: news-derived risk adds no restriction to later eligibility;
- `CAUTION`: later layers require separately defined caution handling;
- `BLOCKED`: news-derived risk prohibits downstream signal eligibility;
- `FAIL_CLOSED`: semantic conditions are invalid, unsupported, or unsafe.

`OPEN` MUST NOT mean publish, create a signal, trade, place an order, or
authorize capital. `BLOCKED` is semantic eligibility data and does not cancel
an existing order because no order authority exists.

## Eligibility recommendation vocabulary

The closed non-executable recommendation vocabulary is:

- `ALLOW_NEWS_ELIGIBILITY`;
- `REQUIRE_NEWS_CAUTION`;
- `DENY_NEWS_ELIGIBILITY`;
- `FAIL_CLOSED`.

These values MUST NOT include or imply BUY, SELL, LONG, SHORT, ENTER, EXIT,
OPEN_POSITION, CLOSE_POSITION, PUBLISH, or SEND.

## Deterministic precedence

The highest applicable severity MUST win:

1. invalid input or identity;
2. unsupported policy or version;
3. News Risk `FAIL_CLOSED`;
4. News Risk recommendation `FAIL_CLOSED`;
5. configured fail-closed reason;
6. News Risk `BLOCKING`;
7. `REQUIRE_BLOCK` recommendation;
8. configured blocking reason;
9. News Risk `ELEVATED`;
10. News Risk `CAUTION`;
11. `REQUIRE_CAUTION` recommendation;
12. News Risk `CLEAR`;
13. `NO_NEWS_RESTRICTION` recommendation.

Input ordering MUST NOT affect the decision. No score, probability,
floating-point confidence, or market context is permitted.

## Risk and recommendation mapping

The policy MUST define deterministic handling for every supported News Risk
classification:

- `CLEAR` MAY map to `OPEN` unless a stricter recommendation or reason wins;
- `CAUTION` maps to `CAUTION`;
- `ELEVATED` maps to `BLOCKED` or `CAUTION` only under an explicit frozen
  policy, with `BLOCKED` as the preferred safe default;
- `BLOCKING` maps to `BLOCKED`;
- `FAIL_CLOSED` maps to `FAIL_CLOSED`.

Recommendations map as follows:

- `NO_NEWS_RESTRICTION` → `OPEN`, unless risk overrides;
- `REQUIRE_CAUTION` → `CAUTION`, unless a stricter state overrides;
- `REQUIRE_BLOCK` → `BLOCKED`;
- `FAIL_CLOSED` → `FAIL_CLOSED`.

No lower-severity recommendation may clear a higher-risk classification.

## Reason-code taxonomy

Signal Gate reasons MUST be closed, ordered, duplicate-free, bounded, and
deterministic. Conceptual values include:

Open: `NEWS_RISK_CLEAR`, `NO_NEWS_RESTRICTION`.

Caution: `NEWS_RISK_CAUTION`, `CAUTION_RECOMMENDED`, `LIMITED_EVIDENCE`,
`QUALIFIED_NEWS_ASSESSMENT`.

Blocked: `NEWS_RISK_ELEVATED`, `NEWS_RISK_BLOCKING`, `BLOCK_RECOMMENDED`,
`CRITICAL_MATERIAL_RISK`, `CRITICAL_CONTRADICTION`,
`CRITICAL_ENTITY_CONCERN`, `CRITICAL_SOURCE_CONCERN`,
`BLOCKING_NEWS_REASON`.

Fail closed: `INVALID_NEWS_RISK_OBJECT`, `UNSUPPORTED_POLICY`,
`FORGED_NEWS_RISK_IDENTITY`, `FAIL_CLOSED_NEWS_RISK`,
`FAIL_CLOSED_GATE_POLICY`.

Provider prose and upstream explanations MUST NOT become gate reason codes.

## Signal Gate decision contract

The immutable `SignalGateDecisionV1` SHALL contain these semantic fields:

- `policy_version`;
- `event_snapshot_id`;
- `news_risk_policy_version`;
- `news_risk_object_id`;
- `route`;
- `gate_state`;
- `eligibility_recommendation`;
- `risk_classification`;
- `news_gate_recommendation`;
- `reason_codes`;
- `evidence_refs`;
- `structured_explanation`;
- `signal_gate_decision_id`.

It MUST NOT contain provider request IDs, execution records, attempts,
retries, tokens, cache, cost, budget, market data, technical or scanner
scores, direction, entries, stops, targets, quantity, leverage, account,
balance, position, order, publication, delivery, or execution state.

## Signal Gate identity

`signal_gate_decision_id` MUST be a lowercase SHA-256 over canonical semantic
fields including policy version, event snapshot, News Risk policy version,
News Risk object ID, route, gate state, eligibility recommendation, risk
classification, News Risk recommendation, reason codes, and evidence refs.

It MUST exclude the ID itself, provider identities beyond the News Risk
identity, execution records, telemetry, budget, clock, randomness, market
data, scanner state, account state, and free text. Equivalent inputs MUST
converge; material semantic changes MUST diverge; forged direct construction
MUST reject.

## Free-text non-authority

Provider, adjudication, and News Risk explanations, role or system
instructions, open-gate commands, publication commands, trading commands,
shell commands, and JSON control text MUST NOT influence gate state,
recommendation, reasons, evidence, or identity.

The decision MAY contain a bounded explanation generated solely from closed
gate reason codes. It MUST NOT copy upstream prose.

## Immutability and non-mutation

The policy and decision MUST be immutable. Reason codes and evidence refs MUST
be immutable tuples with deterministic sorting and duplicate collapse. Caller
collections and the News Risk input MUST remain unchanged. Equivalent calls
MUST produce structurally equal decisions. No global history or adaptive
policy is permitted.

## Failure and error contract

`SignalGateError` SHALL provide deterministic, bounded, sanitized failures for
wrong input or policy type, unsupported version, forged News Risk identity,
invalid route or classification, invalid recommendation, malformed reason or
evidence, contradictory policy, and forged Signal Gate identity.

Errors MUST exclude provider prose, upstream explanations, raw payloads,
request IDs, tokens, cost, credentials, market or account data, paths,
arbitrary representations, memory addresses, and stack traces.

## Telemetry, budget, market, and account isolation

The layer MUST NOT accept or inspect provider runs, execution records, request
IDs, attempts, retries, tokens, cache, cost, duration, budget authorization,
pricing, market prices, candles, technical indicators, scanner scores,
account state, balances, positions, or open orders.

Equivalent News Risk semantics MUST produce identical decisions regardless of
operational history.

## Authority boundary

The Signal Gate MUST NOT call providers, route requests, retry, select models,
inspect credentials, access network, environment, filesystem, clock, or
randomness, reserve budget, access market or scanner state, create a
production signal, select direction, calculate trade parameters, publish,
deliver Telegram messages, place/cancel/modify orders, access account,
balance, position, capital, or exchange state, mutate the Master Engine,
persist, replay, or schedule background work.

Production effect remains NONE.

## Distinction from production signal service

`SignalGateDecisionV1` is not `ProductionSignal`. `OPEN` is not signal
creation, publication, or trading authority. `BLOCKED` is only a semantic
eligibility result. Production integration remains separately authorized, and
the Phase 09 production service MUST NOT be modified or invoked here.

## Staged implementation plan

### Stage 1 — Contract and RED tests

- documentation;
- deterministic local News Risk fixtures;
- no implementation.

### Stage 2 — Pure Signal Gate engine

- exact `NewsRiskObjectV1` input;
- deterministic policy tables;
- immutable `SignalGateDecisionV1`;
- no downstream integration.

### Stage 3 — Downstream consumption

Separately authorized consumers MAY use `SignalGateDecisionV1`. No downstream
integration is silently implemented here.

## RED test strategy

Future RED tests SHALL cover exact API and policy schema, exact News Risk input
and supported version, identity validation, risk/recommendation mapping,
precedence, closed reasons and evidence, immutable decision and identity,
forged identity, free-text non-authority, telemetry/budget/market/account
isolation, and absence of provider, network, credential, signal creation,
publication, delivery, and trading authority.

Tests MUST use deterministic local News Risk fixtures only.

## Acceptance criteria

Acceptance requires exact News Risk input, valid identity, closed immutable
policy/output, deterministic precedence, non-clearable BLOCKING,
non-downgradable FAIL_CLOSED, explicit safe ELEVATED handling, deterministic
reasons and identity, inert prose, isolated operational state, no provider
call, no signal creation, no publication, no delivery, no trading, and
production effect NONE.

## Deferred decisions

The following are explicitly deferred:

- scanner or technical-signal combination;
- final signal eligibility aggregation;
- production integration and signal creation;
- publication and Telegram delivery;
- persistent storage and human override;
- market-state or account-state input;
- order execution;
- Phase 11 consumption.

Deferred decisions MUST NOT be silently implemented.
