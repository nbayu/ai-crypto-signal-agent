# Phase 10 Claude Escalated Review Provider Contract

Status: Design freeze — documentation only

This document freezes the future Claude provider boundary for escalated Phase
10 news review. It authorizes no provider call, credential access, network
access, or production effect.

## Purpose and scope

The boundary executes a Claude review only after deterministic routing has
produced a valid L1 or L2 decision. It consumes an already projected Claude
payload, the exact router decision that authorized it, a closed execution
policy, and explicit budget authorization evidence.

The boundary MUST be deterministic at its validation and identity edges,
MUST preserve the semantic request across attempts, and MUST separate semantic
results from operational execution records.

## Non-goals

This contract does not define or authorize:

- Claude SDK or transport implementation;
- a live model identifier, endpoint, API version, credential source, or price;
- route selection or modification;
- adjudication of DeepSeek and Claude results;
- budget-ledger ownership, spend reservation, or publication permission;
- audit persistence, replay, delivery, trading, account, balance, position, or
  capital access.

## Architectural position

```text
AIReviewPayloadProjectionV1
        ↓
ClaudeReviewPayloadV1

DeepSeekPrimaryReviewResultV1
        ↓
DeterministicEscalationDecisionV1
        ├── L0 → no Claude boundary call
        ├── L1 → configured Sonnet policy class
        └── L2 → configured Opus policy class

ClaudeReviewPayloadV1
+ DeterministicEscalationDecisionV1
+ ClaudeExecutionPolicyV1
+ explicit budget authorization
        ↓
ClaudeEscalatedReviewResultV1
+ ClaudeProviderExecutionRecordV1
+ ClaudeEscalatedReviewRunV1
        ↓
future deterministic adjudication
```

The provider boundary MUST NOT adjudicate. L0 MUST never reach transport.

## Exact input contracts

The semantic inputs MUST be exactly:

- `ClaudeReviewPayloadV1`;
- `DeterministicEscalationDecisionV1`;
- `ClaudeExecutionPolicyV1`;
- explicit budget authorization evidence.

The boundary MUST reject DeepSeek payloads, DeepSeek runs, execution records
as semantic input, generic mappings, raw canonical objects, raw article
content, and account or trading state.

Before transport, it MUST verify agreement among:

- `event_snapshot_id`;
- Claude payload SHA-256;
- router decision source-result identity;
- route;
- selected Claude model-policy class.

The adapter MUST NOT rebuild or reinterpret the projector payload.

## Route authorization

L0 means Claude execution is prohibited. The boundary MUST fail before
transport and MUST create no request ID, usage, cost, retry, or semantic
result.

L1 requires Claude review under exactly the configured Sonnet policy class.
L2 requires Claude review under exactly the configured Opus policy class.

The boundary MUST reject route and policy mismatches, missing authorization,
forged decisions, dynamic fallback, and policy substitution. Live Sonnet and
Opus model IDs remain uncommitted.

## Claude execution policy

The future closed immutable value object is conceptually:

```text
ClaudeExecutionPolicyV1(
    policy_version,
    provider_name,
    route,
    model_policy_id,
    model_id,
    maximum_logical_reviews_per_event,
    maximum_provider_attempts,
    maximum_retry_count,
    timeout_seconds,
    input_token_hard_limit,
    target_input_token_minimum,
    target_input_token_maximum,
    output_token_hard_limit,
    prompt_cache_policy,
    budget_authorized,
    maximum_authorized_cost_micro_usd,
)
```

The policy MUST freeze these owner-approved limits:

- one logical Claude review per escalated event;
- two provider attempts maximum;
- one retry maximum;
- 8000 input tokens hard maximum;
- 2000–5000 target input range;
- 1000 output tokens hard maximum;
- integer micro-USD cost representation;
- external global Phase 10 testing cap of USD 5.

The policy MUST NOT freeze current pricing, live model IDs, endpoints, or
credentials. Global budget authority remains external.

## Token and payload-limit contract

The provider boundary MUST accept only a `ClaudeReviewPayloadV1` that has
already passed deterministic projector enforcement. It MUST verify the
available input estimate or count, payload identity, and the 8000-token hard
limit before transport.

Payloads containing raw candles, order books, full historical data, account
state, or trading data MUST fail closed. The boundary MUST NOT summarize,
silently truncate semantic fields, remove evidence to fit, or issue a repair
model call. Retries MUST reuse the same payload.

## Prompt-cache contract

Claude cache structure is:

- one breakpoint after the stable prefix;
- ephemeral mode only;
- TTL exactly 300 seconds;
- one-hour mode prohibited.

Cache state is operational and MUST be excluded from semantic identity. The
boundary MAY later emit provider-native directives for this structure, but
MUST NOT implement a semantic cache, persist cache contents, fabricate hits or
misses, or change payload semantics to pursue a cache outcome.

## Logical review identity

`logical_review_id` MUST be deterministic over:

- Claude policy version;
- event snapshot;
- Claude payload version and SHA-256;
- router decision ID;
- route;
- model-policy ID and explicit model ID;
- escalated-review task identity.

It MUST exclude request IDs, attempts, retries, usage, cache state, cost,
latency, provider response IDs, wall-clock values, and randomness.

Retries share one logical identity. L1 and L2 requests MUST not collide.

## Provider request contract

The future closed request shape MAY contain:

```text
provider
route
model_id
model_policy_id
event_snapshot_id
payload_version
payload_sha256
router_decision_id
logical_review_id
semantic_payload
attempt_number
timeout_seconds
output_token_limit
cache_control
operational_request_id
```

Only attempt context may change between retries. Semantic payload, route,
model policy, model ID, snapshot, payload identity, cache structure, and output
limit MUST remain identical.

Live endpoint syntax, authorization headers, SDK methods, unrelated headers,
API versions, and current pricing are deferred.

## Semantic result contract

The future closed immutable semantic type is conceptually:

```text
ClaudeEscalatedReviewResultV1(
    policy_version,
    event_snapshot_id,
    request_payload_sha256,
    router_decision_id,
    logical_review_id,
    route,
    model_policy_id,
    review_status,
    review_conclusion,
    ambiguity_resolution,
    contradiction_resolution,
    evidence_assessment,
    entity_assessment,
    source_assessment,
    material_risk_assessment,
    agreement_state_with_deepseek,
    reason_codes,
    structured_explanation,
    adjudication_evidence_refs,
    semantic_result_id,
)
```

The result MUST contain no adjudication outcome, final signal gate,
publication instruction, trading action, request ID, token usage, cache usage,
cost, latency, or arbitrary metadata. Retained explanation text is bounded and
non-authoritative.

## Review status vocabulary

The closed status vocabulary is:

- `COMPLETED`;
- `PROVIDER_REJECTED`;
- `INVALID_RESPONSE`;
- `TRANSIENT_FAILURE`;
- `PERMANENT_FAILURE`;
- `BUDGET_BLOCKED`;
- `ROUTE_BLOCKED`;
- `TOKEN_LIMIT_BLOCKED`.

`ROUTE_BLOCKED` applies to L0 or route/policy mismatch. `TOKEN_LIMIT_BLOCKED`
and `BUDGET_BLOCKED` occur before transport. Malformed semantic output is
`INVALID_RESPONSE`. Transport success alone does not imply `COMPLETED`.

## Response validation

Provider responses MUST be validated against a closed schema. Validation MUST
cover required fields, snapshot, payload SHA-256, router decision, logical
identity, route, model policy, closed enums, bounded strings, bounded
collections, finite numeric values, exact integer rules, and deterministic
collection normalization.

Provider-reported model substitution MUST be rejected. Unknown fields,
arbitrary metadata, raw provider objects, implicit coercion, partial semantic
acceptance, and repair calls are prohibited. Response validation failures do
not retry.

## Execution record contract

The future immutable operational type is conceptually:

```text
ClaudeProviderExecutionRecordV1(
    request_id,
    event_snapshot_id,
    provider,
    route,
    model_id,
    model_policy_id,
    payload_version,
    payload_sha256,
    router_decision_id,
    logical_review_id,
    attempt_number,
    retry_count,
    execution_status,
    failure_class,
    failure_code,
    input_tokens,
    output_tokens,
    cache_creation_input_tokens,
    cache_read_input_tokens,
    usage_status,
    cost_micro_usd,
    duration_ms,
)
```

Only provider-native usage MAY be copied. Unavailable values MUST remain
explicitly unavailable. Token and cost fields MUST be exact integers where
present; booleans, negatives, and floating-point currency are invalid. These
records are operational and MUST NOT affect semantic result identity or be
persisted by this boundary.

## Run aggregate contract

The future immutable aggregate is conceptually:

```text
ClaudeEscalatedReviewRunV1(
    logical_review_id,
    event_snapshot_id,
    payload_sha256,
    router_decision_id,
    route,
    semantic_result,
    execution_records,
    final_run_status,
    total_attempts,
    total_retries,
)
```

It MUST contain no more than two contiguous attempt records, beginning at one,
and no more than one retry. All records and any result MUST share snapshot,
payload, decision, route, and logical identity. Blocked runs have zero
provider attempts. Nested state MUST be immutable.

## Retry contract

Exactly one logical review, two attempts maximum, and one retry maximum are
permitted. Retry is limited to approved transient transport failures. The
semantic request MUST remain byte- and identity-equivalent.

There is no prompt reduction, model fallback, route change, Sonnet-to-Opus
escalation, Opus-to-Sonnet downgrade, DeepSeek fallback, or third attempt.
Response validation, authentication, permission, unsupported model, budget,
route, token-limit, and permanent failures do not retry.

## Budget authority

Routing decides semantic escalation; an external budget authority reserves
spend. The Claude boundary only validates explicit authorization evidence and
reports provider-supplied usage or cost. It MUST NOT own a global ledger,
calculate current pricing, decrement the USD 5 cap, or reserve spend.

Absent or denied authorization produces `BUDGET_BLOCKED` before transport with
no request ID, usage, cost, retry, or semantic result.

## Failure taxonomy

The closed failure classes are:

- `PRE_CALL_VALIDATION`;
- `ROUTE_AUTHORIZATION`;
- `TOKEN_LIMIT_VALIDATION`;
- `BUDGET_AUTHORIZATION`;
- `TRANSIENT_TRANSPORT`;
- `PERMANENT_PROVIDER`;
- `RESPONSE_VALIDATION`;
- `INTERNAL_ADAPTER_ERROR`.

Retryability MUST derive from this closed classification, never arbitrary
provider prose. Unknown failures fail closed without retry.

## Security and error sanitization

Stable errors MUST exclude keys, authorization headers, full payloads, article
bodies, system prompt text, raw provider bodies, environment values,
filesystem paths, stack traces, arbitrary representations, and memory
addresses.

Errors MAY include only bounded identifiers such as failure code, snapshot,
payload SHA-256, router decision ID, route, and required attempt number.

## Idempotency and non-mutation

Repeated equivalent semantic requests represent one logical review. Retries
preserve payload bytes, payload identity, router decision, route, model policy,
model ID, cache structure, and output limit.

The boundary MUST NOT mutate the Claude payload, router decision, execution
policy, budget evidence, caller response mappings, usage mappings, or reason
collections.

## Authority boundary

The Claude boundary MUST NOT:

- select or change L0/L1/L2;
- adjudicate DeepSeek against Claude;
- produce a final risk object or signal gate;
- publish or deliver messages;
- create signals or trade;
- access accounts, balances, positions, capital, or exchanges;
- mutate engine state;
- persist audit artifacts or execute replay;
- schedule background work.

Production effect remains NONE.

## Staged implementation plan

### Stage 1 — Contract and RED tests

Documentation, immutable contracts, deterministic fixtures, and injected fake
transport only. No SDK, credentials, network, or live call.

### Stage 2 — Provider boundary implementation

Strict validation and injected transport remain required. No live call is
authorized without a separate owner decision.

### Stage 3 — Controlled live probe

Requires separate owner authorization, verified credentials, explicit budget
reservation, owner-approved model IDs, a bounded request, and no production
integration.

This commit authorizes documentation only.

## RED test strategy

The next deterministic test slice MUST cover:

- exact API and execution policy;
- exact Claude payload and router-decision types;
- L0 blocking;
- L1/Sonnet and L2/Opus binding;
- route and payload mismatches;
- token and budget blocks;
- cache structure and logical identity;
- single success, transient retry, exhaustion, and non-retryable failures;
- model substitution and malformed responses;
- semantic result, execution record, and run aggregate contracts;
- telemetry, sanitization, immutability, and non-mutation;
- absence of provider, network, credential, adjudication, publication, and
  trading authority.

All tests MUST use deterministic local fake transport. No live call is
authorized by the first implementation slice.

## Acceptance criteria

Acceptance requires:

- L0 never calls Claude;
- L1 binds only the approved Sonnet policy class;
- L2 binds only the approved Opus policy class;
- exact payload and router-decision binding;
- one logical review, two attempts maximum, and one transient retry maximum;
- 8000-token input hard cap, 2000–5000 target range, and 1000-token output
  hard cap;
- one ephemeral 300-second cache breakpoint and no one-hour mode;
- budget denial before transport;
- closed semantic output and separate operational telemetry;
- deterministic identities and no model fallback;
- no adjudication, publication, delivery, or trading authority;
- production effect NONE.

## Explicitly deferred decisions

The following MUST remain unresolved until separately verified and approved:

- live Sonnet model ID;
- live Opus model ID;
- SDK or raw transport choice;
- live endpoint and API version;
- timeout values;
- current pricing;
- credential source;
- provider-native usage and cache-field mapping;
- controlled live-probe authorization;
- budget-ledger implementation;
- deterministic adjudication;
- production service integration;
- publication and trading integration.

Deferred items MUST NOT be silently resolved by the first implementation
slice.
