# Phase 10 DeepSeek Primary Review Provider Contract

Status: Design freeze — documentation only

This document defines the future provider boundary for the DeepSeek primary
review role. It does not authorize provider execution, live calls, credentials,
or production integration.

## Scope

The boundary consumes one already-projected semantic review payload and, when a
separately authorized execution policy permits a call, returns a closed,
validated semantic result plus a separate operational execution record.

The contract MUST preserve canonical Phase 10 identities and MUST fail closed
when input, execution policy, provider response, or budget authorization is
invalid.

## Non-goals

This contract does not define or authorize:

- a live endpoint, SDK, transport, or model identifier;
- credentials, credential storage, or provider discovery;
- prompt construction or semantic payload rewriting;
- Claude selection, L0/L1/L2 routing, or adjudication;
- budget reservation or global spend accounting;
- audit persistence, replay, publication, delivery, or trading;
- account, position, balance, capital, or exchange access.

## Architectural position

The frozen pipeline position is:

```text
NormalizedNewsEventV1
+ SourcePolicyDecisionV1
+ EntityMappingResultV1
        ↓
AIReviewPayloadProjectionV1
        ↓
DeepSeek Primary Review Provider Boundary
        ↓
DeepSeekPrimaryReviewResultV1
        ↓
Deterministic Escalation Router
        ├── L0 — no Claude
        ├── L1 — Claude Sonnet
        └── L2 — Claude Opus
```

The boundary MUST consume the projector output without rebuilding or
reinterpreting it. It MUST NOT route, select Claude, adjudicate disagreement,
mutate canonical inputs, publish, or trade.

## Input contract

The semantic provider input MUST be exactly `DeepSeekReviewPayloadV1`.

The boundary MUST reject:

- `ClaudeReviewPayloadV1`;
- generic mappings or lookalike objects;
- raw normalized events, source-policy decisions, or entity mappings;
- unbounded article bodies or evidence outside the bounded payload;
- raw market data and all account or trading state;
- arbitrary operational metadata attached to the semantic request.

An optional execution-policy value object MAY be supplied separately. It MUST
be closed and immutable, and MUST NOT alter semantic payload bytes, payload
identity, logical-review identity, task, or snapshot binding.

Each logical review MUST bind to exactly:

- one event snapshot;
- one `payload_version`;
- one `payload_sha256`;
- one approved semantic task;
- one explicit model-policy selection.

## Semantic request identity

The semantic request identity consists of the approved payload version,
payload SHA-256, event snapshot identity, and a deterministic logical-review
identity or equivalent. A provider request ID is operational state only.

Retries MUST submit the exact same semantic payload and MUST preserve every
semantic identity. Request IDs MAY differ per attempt, but they MUST NOT alter
payload identity, logical-review identity, or any future adjudication identity.

## DeepSeekPrimaryReviewResultV1

The future result MUST be a closed immutable value object conceptually shaped
as follows. The exact implementation field names remain subject to the next
test-defined contract slice.

```text
DeepSeekPrimaryReviewResultV1(
    result_policy_version,
    event_snapshot_id,
    request_payload_sha256,
    review_status,
    structured_findings,
    ambiguity_indicators,
    contradiction_indicators,
    source_policy_concerns,
    entity_concerns,
    escalation_relevant_facts,
    reason_codes,
    bounded_explanation_summary,
    escalation_evidence_refs,
    semantic_result_id,
)
```

The result MUST bind to the exact event snapshot and request payload. Its
semantic identity MUST exclude request IDs, attempt numbers, retries, cache
usage, token usage, cost, latency, and transport details.

Provider prose MUST NOT be authoritative. Any retained text MUST be bounded,
explicitly non-authoritative, and excluded from deterministic routing or
adjudication unless parsed into closed validated fields.

## Closed review status

The semantic result status is closed and distinct from transport status:

| Status | Meaning |
| --- | --- |
| `COMPLETED` | A response passed complete schema and binding validation. |
| `PROVIDER_REJECTED` | The provider rejected the valid semantic request. |
| `INVALID_RESPONSE` | A response was received but failed closed validation. |
| `TRANSIENT_FAILURE` | An approved temporary execution failure remains after allowed attempts. |
| `PERMANENT_FAILURE` | Execution failed in a non-retryable way. |
| `BUDGET_BLOCKED` | Execution was not authorized by the supplied budget decision. |

Review status MUST NOT encode an escalation route, risk adjudication, or
publication decision.

## Structured review output

Structured findings MUST use closed value sets and immutable collections.
They MAY cover:

- review conclusion;
- ambiguity level;
- contradiction presence;
- evidence sufficiency;
- entity-confidence state as supplied by the review contract;
- source-policy concern state;
- material risk flags;
- closed reason codes;
- bounded explanation summary;
- escalation evidence references.

The result MUST NOT contain arbitrary score dictionaries, generic metadata,
executable instructions, routing commands, publication commands, or trading
actions. The provider may report bounded facts; deterministic Python code
decides what happens next.

## Provider response validation

Response handling MUST fail closed. Validation MUST enforce:

- exact response schema and closed vocabularies;
- required fields and exact types;
- snapshot and payload binding;
- deterministic normalization and ordering;
- bounded text and evidence references;
- finite numeric values where numeric fields exist;
- rejection of bool-as-int values;
- rejection of unknown authority-bearing fields;
- no retention of raw provider objects;
- no implicit coercion or partial semantic acceptance.

Malformed or incomplete semantic output MUST become `INVALID_RESPONSE`. It
MUST NOT be silently repaired by another model or by inferred defaults.

## Execution record contract

Operational execution evidence MUST be represented separately as a closed
conceptual value object, not merged into the semantic result:

```text
DeepSeekProviderExecutionRecordV1(
    request_id,
    event_snapshot_id,
    provider,
    model_id,
    payload_version,
    payload_sha256,
    attempt_number,
    retry_count,
    input_tokens,
    output_tokens,
    cache_creation_input_tokens,
    cache_read_input_tokens,
    usage_status,
    cost_micro_usd,
    duration_or_latency,
    failure_code,
)
```

Fields are operational evidence only. Token counts, cache counts, cost,
latency, and usage status MUST be recorded only when actually supplied by the
approved execution path. The adapter MUST NOT fabricate them. Integer token
and micro-USD fields MUST reject floating-point currency authority.

Operational records MAY reference semantic identities but MUST NOT mutate
semantic results or payload identities.

## Retry policy

For each event, the boundary MUST allow at most one logical DeepSeek review.
That logical review MUST have at most two provider attempts and at most one
retry.

Retry is permitted only for approved transient transport classes, including:

- timeout;
- temporary connection failure;
- explicitly transient provider unavailability;
- an explicitly approved retryable rate-limit response.

Retry is prohibited for:

- malformed semantic responses or schema violations;
- payload rejection;
- authentication or permission failure;
- budget block;
- permanent provider errors;
- deterministic validation failures.

Every retry MUST preserve payload bytes, payload SHA-256, event snapshot,
model policy, review task, and cache structure. No semantic prompt mutation,
fallback model, or hidden second logical review is permitted.

## Timeout and cancellation policy

Timeout and cancellation MUST be explicit execution-policy fields in the
future implementation. A bounded timeout is required; infinite waiting is
prohibited.

Cancellation MUST produce a closed operational status and MUST NOT fabricate a
semantic result. A timeout MUST NOT trigger semantic prompt reduction or an
implicit model fallback. Claude escalation remains the responsibility of the
later deterministic router.

Exact timeout values are deferred pending owner approval.

## Model policy boundary

Model selection MUST be explicit, deterministic, and validated against an
approved DeepSeek model policy. The policy MAY use a model-policy identifier
and an explicitly supplied model ID.

The boundary MUST NOT auto-discover models, dynamically choose a cheaper model,
switch model on retry, or silently accept a provider-selected model change.
No live model ID is frozen by this document.

## Token, usage, and cost telemetry

The future execution layer MAY record request ID, provider, model ID, payload
version, payload SHA-256, attempt number, retry count, input/output token
counts, native cache counts, usage status, integer micro-USD cost, and an
operational duration.

DeepSeek native prefix-cache usage MAY be recorded only when the provider
actually supplies it. The adapter MUST NOT fabricate cache hits, cache misses,
token counts, costs, latency, or usage status. These fields MUST remain
outside semantic result identity.

## Budget authority boundary

Provider testing remains subject to the owner-approved USD 5 hard cap. The
provider boundary MUST report execution facts but MUST NOT own the global
budget ledger or reserve spend.

Execution MUST fail closed when a supplied budget decision does not authorize
the attempt. Cost calculation requires a separately approved pricing policy
and MUST use integer micro-USD when represented. This document freezes no
current provider pricing.

## Cache boundary

DeepSeek prefix caching is provider-managed automatic behavior. The future
adapter MAY submit the deterministic payload structure and record native cache
usage returned by the provider.

The adapter MUST NOT implement a semantic cache, mutate payload content to
chase cache hits, fabricate cache state, persist provider cache state, or
interpret a cache miss as semantic failure. Cache state MUST NOT enter
semantic identity. Explicit Claude cache execution is a separate future
provider contract.

## Failure taxonomy

Failures MUST remain separated as follows:

### A. Pre-call validation

Wrong input type, invalid payload identity, unauthorized budget, or invalid
execution policy. These are deterministic and non-retryable.

### B. Transient transport

Timeout, temporary connection failure, transient provider unavailability, or
an approved retryable rate limit. These MAY consume the single retry.

### C. Permanent transport or provider failure

Authentication failure, permission denial, unsupported model, or non-retryable
provider rejection. These MUST NOT be retried.

### D. Response validation

Malformed response, schema violation, unknown status, snapshot mismatch,
payload mismatch, or missing required field. These become
`INVALID_RESPONSE` and MUST NOT be retried.

### E. Internal adapter error

Deterministic implementation error or unsupported internal state. This MUST
remain distinct from a semantic provider result.

Retryability, semantic status, and operational failure code MUST be separate
fields or closed concepts.

## Idempotency

Repeated execution with the same semantic request represents the same logical
review. Retry attempts are attempts within that logical review. The boundary
MUST NOT publish duplicate semantic results and MUST NOT persist or publish the
result itself.

Each provider response MUST bind to the exact payload identity submitted for
that attempt. Request IDs MAY differ, while payload and logical-review
identities remain fixed.

## Security and error sanitization

Stable errors MUST NOT expose API keys, authorization headers, complete
requests, full article bodies, credentials, environment values, filesystem
paths, unbounded provider responses, or stack traces.

Errors MAY include bounded deterministic identifiers such as event snapshot ID,
payload SHA-256, attempt number, and a closed failure code. Sensitive values
MUST never be interpolated into stable error messages or semantic results.

## Authority boundary

The provider boundary MUST NOT:

- perform routing or choose Claude;
- adjudicate disagreement or assign publication permission;
- create production signals or trading actions;
- access exchanges, accounts, positions, balances, or capital;
- write audit artifacts or execute replay;
- mutate Master Engine state or schedule background work;
- publish or deliver any result.

Production effect remains NONE.

## Staged implementation plan

### Stage 1 — Contract and fake transport

The next slice MAY add contracts, tests, and deterministic fake transport only.
It MUST use no live provider and no credentials.

Tests MUST cover the exact public API, closed execution policy, semantic result,
execution record, exact payload acceptance, snapshot binding, retry limits,
transient-only retry, malformed-response rejection, budget blocking, model
policy validation, response validation, telemetry separation, integer cost,
native-only cache usage, sanitization, and absence of routing or publication
authority.

### Stage 2 — Provider adapter implementation

This remains separately authorized. It MUST remain transport-injected and
test-driven, with no live call unless explicitly approved.

### Stage 3 — Controlled live provider probe

This requires separate owner authorization, explicit budget reservation,
credential readiness, a bounded single logical review, at most two attempts,
and no production effect. It MUST NOT route or publish.

This document commit authorizes none of Stage 2 or Stage 3.

## Acceptance criteria

Acceptance of the future provider boundary requires:

- exactly one DeepSeek semantic payload per logical review;
- at most one logical review per event;
- at most two attempts and one retry;
- retry only for approved transient failures;
- no semantic request mutation;
- exact payload and snapshot binding;
- a closed, validated semantic result;
- a separate operational execution record;
- no fabricated telemetry;
- no floating-point cost authority;
- no routing, adjudication, provider fallback, or publication;
- no trading authority;
- production effect NONE.

## Explicitly deferred decisions

The following MUST remain unresolved until separately verified and approved:

- exact live DeepSeek model ID;
- exact SDK or HTTP transport;
- exact endpoint;
- exact timeout values;
- exact provider pricing;
- exact native cache-telemetry field mapping;
- exact credential source;
- authorization for a live probe;
- production service integration;
- router integration;
- adjudication integration.

No deferred item may be silently decided by the first implementation slice.
