# Phase 10 — News Intelligence & Event Reasoning Foundation Design Freeze

## 1. Document Control

- Phase: Phase 10 — News Intelligence & Event Reasoning Foundation
- Design version: `phase-10-news-intelligence-design-v1`
- Status: `APPROVED / DESIGN_FROZEN`
- Approval baseline: `a84375fa85c2f318944adfe57aaabac6e43c219c`
- Phase 09 checkpoint: `CP-09-LOCKED`
- Roadmap authority: AI Crypto Signal Agent — Post-Phase 09 Intelligence Roadmap, Version 1.1 — APPROVED / LOCKED
- Owner decision: `APPROVE DESIGN FREEZE`
- Owner approval status: `APPROVED / DESIGN_FROZEN`
- Production authority: `NONE`
- Capital authority: `NONE`
- Publication effect: `NONE`
- Implementation authority: implementation remains separately authorized one
  bounded slice at a time

Phase 09 remains unchanged. This document freezes an isolated Phase 10
foundation and does not reopen, revise, or extend Phase 09 publication
authority. No implementation is authorized by this document alone.

### 1.1 Immutable version registry

The frozen version registry is:

- `phase-10-news-intelligence-design-v1`;
- `news-event-schema-v1`;
- `news-source-policy-v1`;
- `news-entity-mapping-policy-v1`;
- `news-review-schema-v1`;
- `news-review-normalization-v1`;
- `news-prompt-v1`;
- `news-prompt-cache-v1`;
- `news-routing-policy-v1`;
- `news-critical-event-classes-v1`;
- `news-review-disagreement-v1`;
- `news-adjudication-policy-v1`;
- `news-provider-usage-mapping-v1`;
- `news-provider-pricing-2026-07-16-v1`;
- `news-budget-policy-v1`;
- `news-circuit-policy-v1`;
- `news-audit-schema-v1`;
- `news-replay-schema-v1`; and
- `news-replay-policy-v1`.

Every registered version is immutable. Any behavioral addition, removal,
reinterpretation, schema change, or policy change requires a new version,
owner approval, tests, and audit evidence. No version may be mutated in place.

## 2. Objective and Non-Objectives

The objective is to build a provider-neutral, auditable, replayable subsystem
that converts point-in-time news and institutional events into deterministic
structured risk evidence.

Phase 10 has zero strategy, setup-selection, score, signal-geometry,
publication, order, and capital authority. Models are bounded evidence
reviewers only.

Python exclusively owns source eligibility, deterministic normalization,
event and version identities, entity-mapping policy, severity routing,
provider selection, attempt eligibility, timeout behavior, budget reservation
and finalization, circuit-breaker transitions, response validation, final
adjudication, artifact identity, replay identity, and every terminal failure
outcome.

Explicit non-objectives:

- no setup creation;
- no side selection;
- no entry, stop-loss, take-profit, risk/reward, or score mutation;
- no candidate rescue or ranking authority;
- no signal publication or production delivery;
- no Telegram delivery or exposure;
- no exchange operation or order execution;
- no account, wallet, margin, balance, position, or capital access;
- no semantic deduplication authority;
- no live Master Engine integration;
- no Phase 11 shadow execution;
- no Phase 12 production gating; and
- no automatic production `BLOCK` behavior.

## 3. Dependency and Module Direction

The only authorized dependency direction is:

```text
event contracts
  -> normalization
  -> source policy
  -> review contracts
  -> prompt construction
  -> severity router
  -> provider policy and state
  -> provider adapters
  -> adjudicator
  -> audit artifacts
  -> replay
  -> orchestration service
```

Core contracts and deterministic policy modules must not import provider SDKs,
HTTP clients, `os.environ`, Telegram, exchange libraries, scanner modules,
Master Engine, Phase 09 publication modules, wall-clock functions, or
randomness.

Provider adapters receive injected transports or clients. They must not
construct live clients internally. Dependency injection must keep credentials,
network behavior, clocks, waiting, and provider composition outside pure
contracts and policy.

There is no dependency from Master Engine or Phase 09 publication into Phase
10. Phase 10 output has no live publication effect.

The locked runtime path is:

```text
input news or institutional event
  -> deterministic source validation
  -> canonical normalization
  -> exact deduplication and update lineage
  -> deterministic eligibility and entity mapping
  -> DeepSeek primary structured review
  -> Python severity router
       L0 -> no Claude
       L1 -> Claude Sonnet 5
       L2 -> Claude Opus 4.8
  -> deterministic adjudication
  -> immutable news-risk object
  -> isolated audit and replay evidence
```

## 4. Source and Raw Capture Contract

The source descriptor is a closed object containing exactly the fields frozen
by its schema version, including at least:

- `source_namespace`;
- `source_id`;
- `source_type`;
- `canonical_source_uri`;
- `publisher_identity`;
- `credibility_tier`;
- `publication_timestamp_utc`;
- `capture_timestamp_utc`;
- `point_in_time_timestamp_utc`;
- `content_type`;
- `language`;
- `raw_content_sha256`;
- `source_metadata`;
- `source_health_status`; and
- `schema_version`.

All timestamps are explicit caller inputs, timezone-aware, and normalized to
UTC. Ambient clock access is prohibited. Raw source content is untrusted data.
Unknown fields fail closed unless the active schema explicitly defines a
closed extension map. An extension map may carry evidence only; it may not
change contract authority.

The capture contract must preserve point-in-time provenance. It must not
silently replace an original capture with later content, current content, or a
mutable source URL response.

## 5. Event Identity, Versioning, and Lineage

All identities use lowercase SHA-256 over frozen canonical JSON.

### 5.1 Logical event identity

`event_id` is the SHA-256 digest of canonical JSON containing:

- event namespace;
- authoritative source namespace;
- authoritative source event ID when present, otherwise a deterministic
  source key;
- normalized primary subject; and
- canonical event class.

### 5.2 Immutable event version identity

`event_version_id` is the SHA-256 digest of canonical JSON containing:

- `event_id`;
- canonical normalized content hash;
- publication timestamp;
- material source metadata hash; and
- event schema version.

### 5.3 Exact snapshot identity

`event_snapshot_id` is the SHA-256 digest of the complete canonical immutable
normalized event envelope.

### 5.4 Lineage rules

- `event_id` identifies the logical event.
- `event_version_id` identifies one immutable version.
- `event_snapshot_id` identifies the exact review input.
- A later material update creates a new `event_version_id`.
- Every update references `previous_event_version_id`.
- An identical `event_version_id` is idempotent.
- Lineage cycles are prohibited.
- Version numbers are positive and strictly increasing within one event.
- A version may have at most one authoritative predecessor.
- Missing predecessor evidence fails closed.
- Semantic similarity may be recorded as non-authoritative evidence but may
  not merge, suppress, renumber, or replace events.
- Exact canonical identity is the only deduplication authority in Phase 10.

## 6. Normalization Contract

Normalization is deterministic and frozen for:

- Unicode normalization;
- line endings;
- whitespace;
- canonical URLs;
- source namespaces;
- publisher identities;
- symbols and entities;
- timestamps;
- language tags;
- canonical JSON; and
- lowercase hexadecimal SHA-256 digests.

Canonical JSON uses UTF-8, sorted keys, compact separators, `ensure_ascii=False`,
and rejects NaN and Infinity. Closed schemas reject missing and unknown fields.
Money uses integer micro-USD and never binary float.

Normalization may not summarize, infer, translate, classify impact, add facts,
remove material text, or alter semantic meaning. Every normalized field must
be traceable to source evidence or a frozen deterministic mapping rule.

## 7. Source Eligibility and Entity Mapping

Python owns source eligibility. Allowed statuses are:

- `ELIGIBLE`;
- `INELIGIBLE`;
- `BLOCKED`;
- `INSUFFICIENT_EVIDENCE`;
- `STALE`;
- `INVALID_POINT_IN_TIME`; and
- `SOURCE_UNHEALTHY`.

Python owns entity mapping. Allowed statuses are:

- `EXACT`;
- `UNIQUE_ALIAS`;
- `MULTIPLE_PLAUSIBLE`;
- `UNRESOLVED`;
- `CONFLICTING`; and
- `NOT_APPLICABLE`.

All outcomes contain closed reason codes and evidence references. Entity
mapping may identify candidates but may not choose a trading side, create a
setup, select a candidate, or mutate market-analysis output. Ambiguity is
preserved rather than guessed.

## 8. Review Request and Response Contract

The provider-neutral review request is closed and includes:

- `review_scope`;
- `request_id`;
- `event_id`;
- `event_version_id`;
- `event_snapshot_id`;
- `provider`;
- `requested_model_id`;
- `severity_level`;
- `review_role`;
- `prompt_identity`;
- `stable_prefix_identity`;
- `dynamic_payload_identity`;
- `prompt_version`;
- `review_schema_version`;
- `routing_policy_version`;
- `cache_policy_version`;
- `pricing_policy_version`;
- immutable event snapshot;
- evidence references; and
- required output schema.

Allowed reviewer verdicts are:

- `PASS`;
- `CAUTION`;
- `FAIL`; and
- `REVIEW_UNAVAILABLE`.

The closed response includes:

- `request_id`;
- `provider`;
- `requested_model_id`;
- `returned_model_id`;
- `review_result_id` when semantic validation succeeds;
- `review_execution_id`;
- `verdict`;
- `findings`;
- `contradiction_codes`;
- `mapping_assessment`;
- `novelty_assessment`;
- `impact_evidence`;
- `confidence_basis`;
- `evidence_refs`;
- `usage`;
- `latency_ms`;
- `finish_reason`;
- `raw_response_sha256`; and
- `schema_version`.

The requested model ID and provider-returned model ID are both recorded and
validated. Model aliases, substitutions, and model shopping are prohibited.

The response schema prohibits `setup`, `side`, `entry`, `stop_loss`,
`take_profit`, `rr`, `score`, `ranking`, `publication`, `delivery`, `quota`,
`order`, `account`, `position`, and `capital` fields. A prohibited field at
any depth causes schema rejection.

### 8.1 Semantic review normalization policy

Review-normalization policy version is `news-review-normalization-v1`. Every
validated provider review output is normalized under this policy before
`review_result_id` derivation. The operation is pure, deterministic,
provider-neutral, and incapable of changing semantic meaning.

Behavioral change requires a new normalization-policy version, owner approval,
focused tests, an explicit replay-compatibility decision, and audit evidence.
Version v1 may not be modified in place. The review schema validator and every
implementation test bind the exact normalization-policy version.

#### 8.1.1 Scalar strings

For closed enum fields, normalization preserves the exact validated enum
value. There is no post-validation case folding. Aliases are prohibited and
unknown values are rejected.

Free-text semantic evidence strings use NFC Unicode normalization, normalize
line endings to LF, and remove leading and trailing whitespace. Internal
whitespace is preserved. An empty string is prohibited unless the closed
schema expressly allows it. Normalization performs no summarization, case
folding, punctuation rewriting, translation, or semantic-equivalence
inference.

#### 8.1.2 Optional and nullable fields

Absent fields and explicit JSON null are distinct during raw-provider parsing.
For every optional field, the review contract declares exactly one closed
rule: prohibited, nullable, deterministic default, or omitted when empty.

In `normalized_review_semantic_payload`:

- an optional-and-omittable field is omitted when absent;
- a field declared omit-when-empty is omitted only after its validated empty
  representation is confirmed by the schema;
- explicit null is accepted only for a schema-declared nullable field;
- an accepted nullable value remains canonical JSON null;
- null is never converted silently to an empty string, empty array, empty
  object, zero, false, or a missing field; and
- required fields may never be absent or null.

#### 8.1.3 Unordered closed-code arrays

`contradiction_codes`, normalized reason codes, closed classification codes,
and closed finding-category codes are unordered sets unless an explicit
field-specific schema rule says otherwise. Normalization:

1. validates every item against its closed enum;
2. rejects null and non-string elements;
3. removes exact duplicate values only after validation;
4. sorts values in ascending Unicode code-point order; and
5. serializes the result as a canonical JSON array.

Duplicate removal applies only to exact duplicate closed scalar codes. It may
not hide conflicting structured objects or evidence.

#### 8.1.4 Evidence references

`evidence_refs` are semantic identifiers rather than display-order prose.
Normalization:

1. validates each reference against the closed evidence-reference schema;
2. converts each reference to its canonical JSON object;
3. derives or validates its deterministic `evidence_ref_id`;
4. rejects duplicate IDs that identify different canonical content;
5. collapses exact duplicate references;
6. sorts references by ascending `evidence_ref_id`; and
7. assigns no authority to provider-returned array order.

Semantically meaningful evidence order requires a separate explicit
ordered-evidence field and may not reuse `evidence_refs`.

#### 8.1.5 Structured findings

Findings are structured objects, not arbitrary prose strings. Each finding's
canonical semantic body contains exactly:

- `finding_code`;
- `finding_type`;
- `severity`;
- `subject_entity_id`, or null only when the schema permits it;
- `statement`;
- ordered `supporting_evidence_ref_ids`;
- `qualifiers`; and
- `finding_schema_version`.

Closed enum fields are validated. `statement` follows the free-text rules.
Invalid supporting evidence IDs are rejected; exact duplicates are removed;
the remaining IDs are sorted ascending. `qualifiers` is a closed canonical
object, and unknown fields are rejected.

`finding_id` is SHA-256 over the canonical finding body, excluding
`finding_id` itself. The normalized finding envelope adds that identity to the
body. The top-level findings collection is unordered: every finding is
validated, assigned its `finding_id`, checked so that an identical ID cannot
refer to different canonical content, deduplicated only when exactly
identical, and sorted by ascending `finding_id`. Provider-returned finding
order cannot affect `review_result_id`.

#### 8.1.6 Structured impact evidence

Impact evidence uses structured objects. Every item contains exactly the
fields frozen by the review schema, including deterministic
`impact_evidence_id`. The Phase 10 top-level impact-evidence collection is
unordered unless the schema explicitly declares a causal sequence.

By default, exact duplicates are collapsed, conflicts remain distinct, and
items are sorted by ascending `impact_evidence_id`. Semantic clustering and
paraphrase deduplication are prohibited.

#### 8.1.7 Mapping assessment

Mapping assessment is a closed canonical object. Candidate-entity and
candidate-symbol arrays are unordered. Canonical entity and symbol identities
are validated, exact duplicates are removed, entity IDs are sorted ascending,
and symbols are sorted ascending. Ambiguity status and conflicting candidates
are preserved. Normalization may not delete a candidate based on confidence.

#### 8.1.8 Novelty assessment and confidence basis

Novelty assessment and confidence basis use closed structured schemas. Enum
arrays are validated, exactly deduplicated, and sorted ascending. Narrative
evidence follows the free-text rules without equivalence inference.

Any schema-authorized numeric confidence value uses either an exact decimal
string or integer basis points, as frozen by that schema. Binary float is
prohibited. Canonical decimal strings prohibit exponent notation, a leading
plus sign, unnecessary leading zeroes, unnecessary trailing fractional
zeroes, and negative zero. Normalization does not introduce a numeric
confidence field that the closed review schema has not authorized.

#### 8.1.9 Ordered semantic arrays

Array order participates in `review_result_id` only when the schema marks the
array with `order_semantics: SIGNIFICANT`. Such an array preserves validated
order exactly. The schema explicitly identifies every order-significant
array. An array without that marker is unordered and follows its
field-specific canonical sorting rule. Provider output order alone cannot
make an array order-significant.

#### 8.1.10 Objects and keys

Every semantic object rejects unknown fields and uses exact schema field
names. Serialization uses UTF-8 canonical JSON, lexically sorted object keys,
and compact separators. NaN, Infinity, and binary floating-point money are
prohibited. Booleans remain JSON true or false. Nullable values remain JSON
null only where expressly allowed.

#### 8.1.11 Duplicate and contradiction handling

Normalization removes only exact duplicate semantic items. It never collapses
conflicting findings, contradictory evidence, different severity levels,
different subjects, different qualifiers, different evidence references,
semantically similar prose, paraphrases, or related but distinct entities.
Conflicting items remain separate canonical objects for deterministic
adjudication.

#### 8.1.12 Provider-added and unknown fields

Unknown provider-added semantic fields are rejected. Provider metadata that
is outside the semantic review contract is separated into the operational
execution envelope and cannot enter `review_result_id`. No semantic field may
be silently ignored.

### 8.2 Normalized semantic review payload

`normalized_review_semantic_payload` is the exact canonical object containing:

- `request_id`;
- provider;
- `requested_model_id`;
- `returned_model_id`;
- verdict;
- normalized findings;
- normalized `contradiction_codes`;
- normalized `mapping_assessment`;
- normalized `novelty_assessment`;
- normalized `impact_evidence`;
- normalized `confidence_basis`;
- normalized `evidence_refs`;
- `response_schema_version`;
- `review_normalization_policy_version`; and
- `finish_classification`.

`review_normalization_policy_version` is exactly
`news-review-normalization-v1`.

`review_result_id` is SHA-256 over the exact canonical UTF-8 JSON bytes of
`normalized_review_semantic_payload`. The payload excludes
`review_result_id`, raw provider key order, raw provider array order for
unordered fields, raw optional-field formatting, provider response UUID,
cache telemetry, token usage, latency, attempt number, billing, transport
headers, provider timestamps, raw sanitized response bytes, execution status,
and pricing information.

### 8.3 Raw and normalized review evidence

Two separate immutable artifacts are frozen:

`raw_provider_response_artifact`:

- stores a sanitized exact provider-response representation;
- preserves original provider ordering and optional-field presence;
- belongs to execution and audit evidence;
- is referenced by `review_execution_id`; and
- does not enter `review_result_id`.

`normalized_review_semantic_artifact`:

- stores the validated `normalized_review_semantic_payload`;
- is immutable and provider-neutral;
- is addressed and referenced by `review_result_id`; and
- is cache- and execution-independent.

The audit artifact connects both artifact references without treating their
content or identities as interchangeable. Replay retains both raw sanitized
execution evidence and normalized semantic evidence. `SEMANTIC_REPLAY`
consumes normalized semantic evidence. `OPERATIONAL_REPLAY` may additionally
validate raw-to-normalized mapping under `news-review-normalization-v1`.

### 8.4 Normalization failure policy

The following are closed normalization failures:

- unknown semantic field;
- invalid enum;
- invalid nullable state;
- duplicate ID with conflicting content;
- invalid canonical decimal;
- invalid evidence reference;
- malformed structured finding;
- unsupported order-significant array; and
- canonicalization failure.

Every such failure produces `REVIEW_SCHEMA_INVALID`. When the affected
reviewer is required, the deterministic result is
`adjudicated_status = REVIEW_UNAVAILABLE`.

Normalization failure occurs after a complete response and is not retryable.
It never becomes `PASS` or `GREEN`, invokes another model for a more favorable
verdict, becomes an empty semantic response, or is silently ignored.

## 9. Prompt, Request, and Response Identities

These identities are separate and non-interchangeable.

### 9.1 Prompt identity

`prompt_identity` is SHA-256 over:

- exact stable prompt template bytes;
- prompt version;
- response schema version;
- provider family;
- review role;
- severity contract; and
- cache policy version.

### 9.2 Stable-prefix identity

`stable_prefix_identity` is SHA-256 over:

- exact UTF-8 stable-prefix bytes;
- provider;
- exact requested model ID;
- prompt version; and
- cache policy version.

### 9.3 Dynamic-payload identity

`dynamic_payload_identity` is SHA-256 over the exact canonical dynamic-event
payload bytes.

### 9.4 Request identity

`request_id` is SHA-256 over:

- review scope;
- `event_snapshot_id`;
- provider;
- exact requested model ID;
- severity level;
- review role;
- `prompt_identity`;
- `stable_prefix_identity`;
- `dynamic_payload_identity`;
- review schema version; and
- routing policy version.

### 9.5 Semantic review-result identity

`review_result_id` is SHA-256 over the exact canonical UTF-8 JSON bytes of
`normalized_review_semantic_payload` defined in Section 8.2. That payload
contains exactly the frozen normalized semantic fields and binds
`review_normalization_policy_version: news-review-normalization-v1`.

It excludes raw provider key order, raw provider array order for unordered
fields, raw optional-field formatting, token usage, cache metadata, latency,
provider response UUID, attempt number, billing fields, provider timestamps,
transport headers, raw sanitized response bytes, execution status, and pricing
information.

`review_result_id` identifies semantic validated reviewer evidence. Cache hit,
cache miss, cache expiry, token variation, latency variation, provider UUID,
and billing variation cannot change it. Conflicting semantic responses produce
different `review_result_id` values.

### 9.6 Concrete review-execution identity

`review_execution_id` is SHA-256 over canonical UTF-8 JSON containing exactly:

- `review_result_id`, nullable only for an invalid or unavailable execution;
- `request_id`;
- provider response identifier when present;
- attempt number;
- normalized usage object;
- cache usage state;
- `latency_ms`;
- provider finish reason;
- raw sanitized response hash;
- `raw_provider_response_artifact` reference;
- execution status;
- pricing policy version;
- usage mapping version; and
- cache policy version.

`review_execution_id` identifies one concrete provider execution and its
billing evidence. Usage, attempt, latency, provider response identifier, or
cache-state variation may change `review_execution_id` without changing
`review_result_id`. A semantically identical eligible second attempt may have
a distinct execution identity and the same semantic result identity.

An invalid or unavailable execution has a `review_execution_id` with
`review_result_id: null`, unless the closed adjudication contract explicitly
creates a deterministic unavailable-result semantic input. The null is an
explicit closed-schema value, so the execution identity always hashes the same
exact field set. The term `response_id` is deprecated and prohibited from
every identity and new contract.

### 9.7 Supporting deterministic policy-result identities

`source_policy_result_id` is SHA-256 over canonical JSON containing exactly:

- `event_snapshot_id`;
- source policy version;
- eligibility status;
- ordered eligibility reason codes;
- source health status;
- point-in-time validation result; and
- normalized source identity.

`entity_mapping_result_id` is SHA-256 over canonical JSON containing exactly:

- `event_snapshot_id`;
- entity-mapping policy version;
- mapping status;
- ordered candidate entities;
- ordered candidate symbols;
- ordered mapping reason codes; and
- normalized alias evidence references.

`routing_result_id` is SHA-256 over canonical JSON containing exactly:

- `event_snapshot_id`;
- routing policy version;
- critical-event-class policy version;
- input `source_policy_result_id`;
- input `entity_mapping_result_id`;
- DeepSeek `review_result_id`;
- selected severity;
- selected required reviewer roles;
- exact requested model identities; and
- ordered routing and escalation reason codes.

`adjudication_result_id` is SHA-256 over canonical JSON containing exactly:

- `event_snapshot_id`;
- `source_policy_result_id`;
- `entity_mapping_result_id`;
- `routing_result_id`;
- ordered required `review_result_id` values;
- adjudication policy version;
- disagreement policy version;
- adjudicated status;
- ordered adjudication reason codes; and
- ordered decisive evidence references.

None of these semantic identities includes its own identity field. Execution
telemetry, cache metadata, latency, filesystem paths, provider response UUIDs,
and billing metadata are excluded. Missing required semantic input prevents
creation of the dependent identity. `REVIEW_UNAVAILABLE` may enter
adjudication only through its frozen deterministic unavailable-result input.
Consequently, usage or cache telemetry may affect `review_execution_id`, audit
evidence, and replay evidence, but cannot alter `review_result_id`,
`routing_result_id`, `adjudication_result_id`, or `risk_object_id`.

### 9.8 Review normalization identity graph

The semantic branch is:

```text
raw provider response
  -> closed schema validation
  -> news-review-normalization-v1
  -> normalized_review_semantic_payload
  -> review_result_id
```

The operational branch is:

```text
raw provider response
  -> usage/cache/latency/attempt normalization
  -> review_execution_id
```

Raw provider object-key order and unordered-array order cannot alter
`review_result_id`. Optional null and omitted-field behavior follows the exact
field schema. Canonical semantic differences remain identity-significant and
produce distinct `review_result_id` values. `review_execution_id` may vary
independently because it records concrete execution evidence.

Cache identity never substitutes for request identity. Cache behavior may not
change `request_id`, routing, severity, validation, or adjudication. Only an
exact completed `request_id` may be reused idempotently.

## 10. Prompt-Injection Containment

- Source content is serialized only as untrusted JSON data.
- Source content is never concatenated into system policy text.
- Source instructions cannot change reviewer role or authority.
- Models receive no tools, filesystem authority, network authority,
  publication authority, or execution authority.
- Reviewer output is parsed only through the closed response schema.
- Prohibited output fields cause rejection.
- Model prose outside the structured response is rejected.
- Requests in source text to ignore policy remain evidence and are never
  obeyed.
- Output cannot change severity, requested provider, budget, attempt policy,
  circuit state, or adjudication policy.
- Protected fields are compared before and after review; any mutation attempt
  fails closed.

## 11. Prompt Caching Policy

Cache policy version is `news-prompt-cache-v1`.

Caching is solely a provider-side cost and latency optimization. It is never an
evidence source, approval signal, routing signal, idempotency identity,
completed-review substitute, or replay reconstruction mechanism.

### 11.1 Claude explicit caching

Claude uses explicit block-level caching, not automatic moving-conversation
caching.

Stable prefix order:

1. system authority boundary;
2. reviewer role;
3. protected-field rules;
4. prompt-injection defenses;
5. severity contract;
6. exact structured-output schema; and
7. deterministic examples, if any.

Dynamic suffix order:

1. request metadata;
2. canonical event snapshot;
3. source evidence;
4. entity candidates;
5. DeepSeek primary review when Claude review is required; and
6. required response instruction.

Exactly one explicit cache breakpoint is placed at the end of the stable
prefix.

Secrets, API keys, mutable budget or circuit state, current timestamps, random
IDs, and event-specific content are prohibited from the stable prefix.

Frozen cache configuration:

- type: `ephemeral`;
- default TTL: 5 minutes;
- 1-hour TTL is prohibited unless separately owner-approved;
- maximum one explicit breakpoint per Phase 10 review prompt;
- no top-level automatic `cache_control`; and
- no mutable or event-specific content in the stable prefix.

Claude telemetry distinguishes, when returned:

- `input_tokens`;
- `output_tokens`;
- `cache_creation_input_tokens`;
- `cache_read_input_tokens`; and
- nested cache-creation TTL detail exposed by the SDK/API.

Telemetry states are:

- `PRESENT_VALID_ZERO`;
- `PRESENT_VALID_NONZERO`;
- `ABSENT`;
- `UNSUPPORTED`; and
- `MALFORMED`.

A selected model that does not support this frozen cache contract produces
`CACHE_UNSUPPORTED` and follows deterministic provider-failure policy. It does
not silently continue under another cache strategy.

### 11.2 DeepSeek automatic caching

DeepSeek caching is automatic and best-effort. No cache-control request field
is required.

The request preserves this byte-stable order:

1. stable system authority policy;
2. reviewer role;
3. protected-field rules;
4. response schema;
5. deterministic examples, if any; and
6. dynamic event content last.

Audit evidence records provider-returned:

- `prompt_tokens`;
- `completion_tokens`;
- `total_tokens`;
- `prompt_cache_hit_tokens`; and
- `prompt_cache_miss_tokens`.

Both provider-native field names and normalized canonical usage fields are
preserved. Phase 10 never infers a cache hit. An absent cache field is not
converted into a genuine zero-token hit or miss. Replay consumes recorded
metadata and never predicts provider cache behavior.

### 11.3 Cache equivalence

For the same validated mocked provider response:

- cached and uncached requests produce the same review contract;
- routing and adjudication are identical;
- identities other than recorded response usage remain identical;
- cache expiry or miss has no authority effect; and
- malformed cache metadata creates telemetry failure, never approval.

## 12. Deterministic Severity Routing

Severity levels are:

- `L0` — `CLEAN_OR_ROUTINE`;
- `L1` — `MODERATE_AMBIGUITY`; and
- `L2` — `CRITICAL_AMBIGUITY`.

Locked runtime paths:

```text
L0: DeepSeek -> deterministic adjudication -> no Claude
L1: DeepSeek -> claude-sonnet-5 -> deterministic adjudication
L2: DeepSeek -> claude-opus-4-8 -> deterministic adjudication
```

Exact Claude request model IDs are:

- L1: `claude-sonnet-5`
- L2: `claude-opus-4-8`

Direct-L2 event-class policy version is
`news-critical-event-classes-v1`. Its complete allowlist is:

- `CREDIBLE_PROTOCOL_EXPLOIT`;
- `CREDIBLE_CHAIN_COMPROMISE`;
- `CONFIRMED_MATERIAL_DELISTING`;
- `CREDIBLE_MATERIAL_DELISTING`;
- `MATERIAL_REGULATORY_ENFORCEMENT`;
- `MATERIAL_LEGAL_ENFORCEMENT`;
- `SOLVENCY_IMPAIRMENT`;
- `WITHDRAWAL_IMPAIRMENT`;
- `EXCHANGE_SECURITY_COMPROMISE`;
- `MATERIAL_COORDINATED_MANIPULATION`;
- `SYSTEMIC_CROSS_MARKET_EVENT`; and
- `MATERIAL_HIGH_CREDIBILITY_SOURCE_CONTRADICTION`.

No unlisted class may route directly to L2. Addition, removal, or
reinterpretation requires a new immutable policy version, owner approval,
tests, and audit evidence; v1 cannot be modified in place. Free-text event
descriptions cannot become direct-L2 reason codes. Models cannot add classes.
Configuration cannot add classes unless it loads an owner-approved immutable
versioned policy.

Sonnet-to-Opus escalation is allowed only when Python detects a closed
escalation reason after L1. Allowed reason families are:

- unresolved material contradiction;
- unresolved multi-entity mapping with material impact;
- source credibility conflict above a frozen threshold;
- Sonnet output that is schema-valid but materially inconclusive; and
- systemic implication requiring critical challenge.

Sonnet may report evidence but may not request Opus. The Python router alone
emits escalation reason codes.

## 13. Attempt, Timeout, and Retry Policy

Maximum provider attempts are one initial attempt plus at most one eligible
retry, for a hard maximum of two attempts.

Python-owned retry eligibility is limited to pre-response transient failures:

- connection establishment failure;
- provider HTTP 429;
- provider HTTP 500, 502, 503, or 504;
- transport interruption before a complete response; and
- explicitly classified provider timeout before a complete response.

There is no retry for schema-invalid output, malformed JSON, prohibited output
fields, refusal, a valid `PASS`, `CAUTION`, or `FAIL`, budget exhaustion,
circuit open, cache telemetry defect, model identity mismatch, completed
request identity, policy rejection, or unsupported cache contract.

There is no exponential or unbounded retry loop. Any wait schedule is supplied
by injected deterministic policy and disabled in unit tests.

Timeout and outage outcomes are:

- `REVIEW_TIMEOUT`;
- `PROVIDER_UNAVAILABLE`; and
- `REVIEW_UNAVAILABLE`.

Severity is preserved after failure. Failure never becomes `PASS` or `GREEN`
automatically. A reviewer failure is never sent to another model solely to
obtain a more favorable result.

## 14. Provider Circuit Policy

Circuit states are:

- `CLOSED`;
- `OPEN`; and
- `HALF_OPEN`.

Circuit identity is scoped by provider, exact requested model ID, and circuit
policy version. Only Python changes circuit state. Circuit state never enters
prompt content.

An open circuit prohibits the provider call and produces
`PROVIDER_CIRCUIT_OPEN`. A half-open probe requires explicit policy eligibility
and a completed budget reservation. There is no Sonnet-to-Opus or
Opus-to-Sonnet fallback solely because of an outage.

## 15. Budget and Cost Policy

Money is represented as integer micro-USD. One USD equals `1_000_000`
micro-USD. Binary floats are prohibited.

The Phase 10 Claude hard cap is `5_000_000` micro-USD. DeepSeek accounting is
separate and cannot consume, increase, or offset the Claude cap.

Budget transitions are:

```text
AVAILABLE -> RESERVED -> FINALIZED
AVAILABLE -> RESERVED -> RELEASED
```

A reservation is required before every live provider attempt. Reservation
identity includes:

- `request_id`;
- provider;
- requested model;
- pricing policy version;
- maximum input tokens;
- maximum output tokens;
- maximum cache-write assumption; and
- maximum retry exposure.

Atomic reservation rejects any call whose worst-case exposure exceeds the
remaining Claude cap. Finalization records actual provider usage and releases
unused reservation.

Missing, malformed, or unpriceable usage is never treated as zero. It retains
the conservative reservation, records `COST_UNRESOLVED`, and prohibits further
live calls when safe remaining budget cannot be established.

No live pricing lookup is allowed. Pricing comes from an immutable versioned
policy. Initial pricing policy identifier is
`news-provider-pricing-2026-07-16-v1`.

The pricing policy must cover Claude base input, output, 5-minute cache write,
cache read, and any applicable geography multiplier. A 1-hour cache-write
price is not active because 1-hour TTL is prohibited.

Pricing is implementation configuration and must be verified again against
official provider documentation immediately before the first live
contract-verification call.

## 16. Usage Accounting

Canonical normalized usage fields are:

- `input_tokens_uncached`;
- `output_tokens`;
- `cache_write_tokens_5m`;
- `cache_write_tokens_1h`;
- `cache_read_tokens`;
- `provider_prompt_tokens`;
- `provider_completion_tokens`;
- `provider_total_tokens`;
- `provider_cache_hit_tokens`;
- `provider_cache_miss_tokens`;
- `usage_status`;
- `provider_usage_raw_hash`; and
- `usage_mapping_version`.

Usage mapping version is `news-provider-usage-mapping-v1`.

Sanitized provider-native usage is retained in audit evidence. Token
arithmetic is validated according to provider-specific policy. Absent fields
remain absent-state evidence and are not normalized silently to zero.

## 17. Deterministic Adjudication

Final risk statuses are:

- `GREEN`;
- `AMBER`;
- `RED`;
- `BLOCK`; and
- `REVIEW_UNAVAILABLE`.

Adjudication receives only validated deterministic inputs:

- normalized event;
- source eligibility;
- entity mapping;
- routing result;
- validated DeepSeek review;
- validated Claude review when required;
- failure states; and
- policy versions.

Models do not own final adjudicated status. Any model-suggested status is
non-authoritative evidence and cannot populate the final field.

Disagreement policy version is `news-review-disagreement-v1`. Models return
only `PASS`, `CAUTION`, `FAIL`, or `REVIEW_UNAVAILABLE`; they never return
authoritative `GREEN`, `AMBER`, `RED`, or `BLOCK`.

Ordinal reviewer severity is:

```text
PASS = 0
CAUTION = 1
FAIL = 2
REVIEW_UNAVAILABLE = unavailable, not ordinal approval evidence
```

### 17.1 L0 matrix

The only required reviewer is DeepSeek.

- DeepSeek `PASS`: continue to deterministic source/event policy
  adjudication.
- DeepSeek `CAUTION`: minimum reviewer-derived status is `AMBER`.
- DeepSeek `FAIL`: minimum reviewer-derived status is `RED`.
- DeepSeek `REVIEW_UNAVAILABLE`: final status is `REVIEW_UNAVAILABLE`.

### 17.2 L1 matrix

Required reviewers are DeepSeek and Claude Sonnet.

- If either required reviewer is `REVIEW_UNAVAILABLE`, final status is
  `REVIEW_UNAVAILABLE`.
- `PASS + PASS` -> reviewer-derived `GREEN`.
- `PASS + CAUTION` or `CAUTION + PASS` -> reviewer-derived `AMBER`.
- `CAUTION + CAUTION` -> reviewer-derived `AMBER`.
- Every combination containing `FAIL` -> reviewer-derived `RED`.
- `PASS + FAIL` or `FAIL + PASS` also records
  `MATERIAL_REVIEWER_DISAGREEMENT`.
- `CAUTION + FAIL` or `FAIL + CAUTION` also records
  `MATERIAL_REVIEWER_DISAGREEMENT`.

### 17.3 Direct-L2 and L1-to-L2 matrix

Direct L2 requires DeepSeek and Claude Opus. L1-to-L2 requires DeepSeek,
Claude Sonnet, and Claude Opus. Claude Opus is the critical reviewer for both
routes.

- If any required reviewer, including the critical reviewer, is
  `REVIEW_UNAVAILABLE`, final status is `REVIEW_UNAVAILABLE`.
- Opus `FAIL` -> reviewer-derived `RED`.
- Opus `CAUTION` -> reviewer-derived at least `AMBER`.
- Opus `PASS` with DeepSeek `PASS` and, when present, Sonnet `PASS` ->
  reviewer-derived `GREEN`.
- Opus `PASS` while another required reviewer is `CAUTION` ->
  reviewer-derived `AMBER`.
- Opus `PASS` while another required reviewer is `FAIL` -> reviewer-derived
  `RED` with `MATERIAL_REVIEWER_DISAGREEMENT`.
- Opus `CAUTION` while another required reviewer is `FAIL` ->
  reviewer-derived `RED`.
- Every `PASS`-versus-`FAIL` contradiction -> reviewer-derived `RED` and
  `MATERIAL_REVIEWER_DISAGREEMENT`.
- No lower-severity reviewer verdict may downgrade a higher-severity verdict.

The conservative combination rule selects the maximum severity required by
this closed matrix, subject to required-review availability.

### 17.4 Final deterministic precedence

Precedence is:

1. invalid point-in-time or closed source hard-block condition;
2. required-review availability;
3. closed source eligibility status;
4. reviewer disagreement matrix;
5. deterministic event-risk policy; and
6. final status.

A hard source block remains `BLOCK`. Invalid point-in-time input has exactly:

```text
adjudicated_status = BLOCK
reason_code = INVALID_POINT_IN_TIME
model calls = prohibited
```

Invalid schema or malformed required-model output yields
`REVIEW_UNAVAILABLE`. It is not retried unless failure happened before a
complete response and qualifies under the frozen transient transport policy.
Budget exhaustion before a required review also yields `REVIEW_UNAVAILABLE`.
No absent required review implicitly yields `GREEN`.

No model verdict may downgrade `BLOCK` to `RED`, `AMBER`, or `GREEN`; `RED` to
`AMBER` or `GREEN`; or `AMBER` to `GREEN`. Adjudication reason codes record the
reviewer-verdict combination, disagreement policy version, decisive rule, and
every source hard-block rule.

## 18. News-Risk Object

The immutable closed output contains at least:

- `risk_object_id`;
- `event_id`;
- `event_version_id`;
- `event_snapshot_id`;
- `eligibility_status`;
- `entity_mapping_status`;
- `severity_level`;
- `routing_reason_codes`;
- `required_reviewers`;
- `completed_review_result_ids`;
- `supporting_review_execution_refs`;
- `adjudicated_status`;
- `adjudication_reason_codes`;
- `evidence_refs`;
- `source_snapshot_refs`;
- prompt versions;
- schema versions;
- policy versions;
- provider identities;
- exact requested model identities;
- `audit_snapshot_id`;
- caller-supplied `created_at_utc`; and
- `production_effect: NONE`.

`risk_object_id` is SHA-256 over canonical UTF-8 JSON containing exactly:

- `event_id`;
- `event_version_id`;
- `event_snapshot_id`;
- eligibility status;
- entity-mapping status;
- severity level;
- ordered routing reason codes;
- ordered required reviewers;
- ordered `completed_review_result_ids`;
- adjudicated status;
- ordered adjudication reason codes;
- ordered evidence references;
- ordered source-snapshot references;
- prompt versions;
- schema versions;
- policy versions;
- provider identities;
- exact requested model identities; and
- `production_effect`.

Its canonical semantic input excludes `risk_object_id`, `audit_snapshot_id`,
`supporting_review_execution_refs`, `created_at_utc`, cache telemetry, usage,
latency, budget state, circuit state, provider response identifiers,
filesystem paths, billing amounts, budget reservation IDs, execution attempt
numbers, and persistence timestamps.

`completed_review_result_ids` participates in `risk_object_id`.
`supporting_review_execution_refs` does not. Cache and billing telemetry is
reachable only through supporting execution references and the audit artifact.

The final immutable persisted risk-object envelope may add
`risk_object_id`, `audit_snapshot_id`, `created_at_utc`, and
`supporting_review_execution_refs`. These are references or operational
metadata outside the canonical semantic payload. The dependency direction is
strictly semantic adjudication -> `risk_object_id` -> `audit_snapshot_id`.
The audit reference is attached only after both identities are constructed and
never enters the hash input for `risk_object_id`.

The object contains no setup, trade geometry, score, ranking, publication,
delivery, order, account, position, quota, or capital field.

## 19. Audit Artifacts

The isolated Phase 10 root is `data/news_intelligence_v1/`, with dedicated
sub-roots:

```text
data/news_intelligence_v1/events/
data/news_intelligence_v1/provider_requests/
data/news_intelligence_v1/provider_responses/raw/
data/news_intelligence_v1/provider_responses/normalized/
data/news_intelligence_v1/provider_state/
data/news_intelligence_v1/budget_state/
data/news_intelligence_v1/risk_objects/
data/news_intelligence_v1/replay_bundles/
```

Artifact requirements are intent-first persistence where side effects exist,
canonical JSON, atomic replacement, fsync-compatible durability, root
isolation, symlink and traversal rejection, collision rejection, exact
idempotency, immutable completion records, sanitized errors, no secrets, and
no ambient environment capture.

Audit entries record:

- event and request identities;
- provider and exact requested/returned models;
- prompt, schema, policy, pricing, and mapping versions;
- review-normalization policy version;
- cache configuration;
- usage and cache telemetry;
- latency and attempt number;
- timeout result;
- circuit state;
- budget reservation and finalization;
- response verdict;
- linked `raw_provider_response_artifact` and
  `normalized_review_semantic_artifact` references;
- escalation reason;
- adjudication result; and
- evidence references.

### 19.1 Exact audit-snapshot identity

`audit_snapshot_id` is SHA-256 over canonical UTF-8 JSON containing exactly:

- audit schema version;
- `event_id`;
- `event_version_id`;
- `event_snapshot_id`;
- `source_policy_result_id`;
- `entity_mapping_result_id`;
- `routing_result_id`;
- ordered `review_execution_id` values;
- `adjudication_result_id`;
- `risk_object_id`;
- ordered evidence references;
- ordered artifact references;
- prompt versions;
- review schema versions;
- routing policy version;
- adjudication policy version;
- review-normalization policy version;
- cache policy version;
- usage mapping version;
- pricing policy version;
- budget policy version;
- circuit policy version; and
- replay policy version.

`audit_snapshot_id` itself is excluded from the hash input. Every collection
has deterministic canonical ordering. Provider latency, filesystem paths,
wall-clock persistence timestamps, attempt start/end timestamps, raw error
prose, and cache hit/miss counts are stored as operational audit fields but do
not enter the semantic audit identity. Unknown or mutable ambient fields are
prohibited from the identity. Reuse with different canonical identity content
is a collision and fails closed.

The ordered artifact references include the linked raw-provider and normalized
semantic review artifacts. Audit preserves both and never treats the raw
provider representation as equivalent to its validated normalized semantic
projection.

There is no circular dependency: semantic adjudication produces
`risk_object_id`; the resulting risk identity then participates in
`audit_snapshot_id`. A persisted risk envelope may reference the resulting
audit snapshot, but that reference is outside the semantic risk hash.

## 20. Replay Contract

Replay policy version is `news-replay-policy-v1`. Both modes are detached,
network-free, provider-free, clock-injected, deterministic, and exact-snapshot
based.

### 20.1 `SEMANTIC_REPLAY`

Purpose: reproduce deterministic contracts and semantic adjudication without
simulating whether a provider call would have been operationally allowed.

The bundle contains:

- normalized event snapshot;
- source-policy result;
- entity-mapping result;
- routing input and result;
- exact sanitized provider requests;
- raw sanitized provider-response artifacts;
- normalized review-semantic artifacts;
- recorded validated reviewer semantic results;
- recorded provider executions;
- usage and cache metadata;
- policy and schema versions;
- expected `review_result_id` values;
- expected risk-object semantic payload;
- expected `risk_object_id`; and
- expected adjudication.

Semantic replay neither requires nor reads current or recorded budget/circuit
state to reproduce semantic adjudication. It consumes the normalized semantic
artifact as reviewer evidence and does not derive semantic authority from raw
provider ordering.

### 20.2 `OPERATIONAL_REPLAY`

Purpose: reproduce historical call eligibility, attempt behavior, budget
effects, circuit behavior, and terminal operational outcomes.

In addition to semantic replay fields, the bundle contains:

- budget policy version;
- pricing policy version;
- pre-call available budget;
- reservation request and identity;
- worst-case reserved amount;
- reservation result;
- finalized or released amount;
- post-call available budget;
- unresolved-cost state when applicable;
- circuit policy version and identity;
- circuit state before the attempt;
- failure counters or closed deterministic transition inputs;
- half-open probe eligibility;
- circuit transition result;
- attempt records;
- timeout classification;
- retry-eligibility result; and
- expected operational terminal result.

Operational replay uses recorded responses and failures only. It never calls a
provider or reconstructs live cache behavior. It may verify the recorded
raw-to-normalized transformation using `news-review-normalization-v1` without
changing the recorded semantic result.

### 20.3 Exact replay-bundle identity

`replay_bundle_id` is SHA-256 over canonical UTF-8 JSON containing exactly:

- replay schema version;
- replay policy version;
- replay mode;
- `event_snapshot_id`;
- `source_policy_result_id`;
- `entity_mapping_result_id`;
- `routing_result_id`;
- ordered `review_result_id` values;
- ordered `review_execution_id` values;
- `adjudication_result_id`;
- expected `risk_object_id`;
- recorded policy versions;
- recorded review-normalization policy version;
- recorded schema versions;
- recorded model identities;
- recorded sanitized provider-request hashes;
- recorded raw sanitized provider-response artifact hashes;
- recorded normalized review-semantic artifact hashes;
- recorded usage-object hashes; and
- recorded cache-metadata hashes.

For `OPERATIONAL_REPLAY` only, the same identity input additionally contains:

- budget-state snapshot hash;
- reservation-transition hash;
- circuit-state snapshot hash;
- attempt-transition hash; and
- timeout/retry-decision hash.

The identity excludes `replay_bundle_id`, local filesystem path, replay
execution timestamp, current clock, current pricing, current budget, current
circuit state, machine identity, and provider network state. All collection
ordering is canonical. Reuse with different canonical content is a collision
and fails closed.

Replay never reads credentials, infers a cache hit, fetches current pricing,
uses current time, modifies production state, or publishes a signal.

## 21. SDK and Transport Strategy

Claude production adapter strategy:

- official Anthropic Python SDK;
- exact dependency version pinned only after isolated contract verification;
- `requirements.txt` remains unchanged during design freeze;
- injected SDK client or transport;
- no `ANTHROPIC_API_KEY` read in adapter core;
- credentials may be supplied only by a later authorized runtime composition;
- no client construction in contracts, router, adjudicator, replay, or
  artifact modules.

DeepSeek adapter strategy:

- new isolated Phase 10 adapter;
- injected OpenAI-compatible transport is permitted;
- legacy `engine/deepseek_validator_v4.py` must not be imported;
- no internal environment read;
- no hidden retry or timeout;
- no internal routing or adjudication; and
- no publication dependency.

## 22. Idempotency and Concurrency

- Only an exact completed `request_id` may be reused.
- Duplicate event similarity, a prompt-cache hit, and matching model prose are
  insufficient.
- Incomplete intents are not completed reviews.
- Concurrent identical requests converge on one completed identity.
- Concurrent budget reservations are atomic.
- Reservation collision fails closed.
- Provider response collision is rejected.
- Updates with different `event_version_id` values remain independent reviews.
- Provider invocation begins only after durable intent and budget reservation.

## 23. Protected Files and Forbidden Imports

Protected Phase 09 files:

```text
docs/phase_09_production_signal_service_design.md
engine/production_signal_contract_v1.py
engine/production_signal_artifact_v1.py
engine/production_signal_service_v1.py
tests/test_production_signal_contract_v1.py
tests/test_production_signal_artifact_v1.py
tests/test_production_signal_service_v1.py
```

Protected runtime and replay files:

```text
engine/master_engine_v4.py
engine/validated_pipeline_v4.py
engine/deepseek_validator_v4.py
engine/replay_contract_v4.py
engine/replay_artifact_v4.py
engine/replay_runner_v4.py
engine/quota_slot_engine_v4.py
engine/quota_slot_worker_v4.py
```

Also protected are Telegram modules, exchange modules, scanner and market
analysis modules, Paper Signal modules, Shadow Release modules, pre-delivery
modules, scoring and validation-control modules, position and production
evidence modules, and every existing runtime data root.

Phase 10 modules may not import protected runtime modules merely to reuse
side-effecting behavior. Pure deterministic patterns may be independently
reimplemented under the Phase 10 namespace.

## 24. Authorized Implementation File Plan

This is a planned surface, not permission to create all files.

Documentation:

```text
docs/phase_10_news_intelligence_design.md
```

Engine:

```text
engine/news_event_contract_v1.py
engine/news_normalization_v1.py
engine/news_source_policy_v1.py
engine/news_review_contract_v1.py
engine/news_prompt_v1.py
engine/news_severity_router_v1.py
engine/news_provider_policy_v1.py
engine/news_provider_state_artifact_v1.py
engine/news_deepseek_adapter_v1.py
engine/news_claude_adapter_v1.py
engine/news_adjudicator_v1.py
engine/news_audit_artifact_v1.py
engine/news_replay_contract_v1.py
engine/news_replay_runner_v1.py
engine/news_intelligence_service_v1.py
```

Tests:

```text
tests/test_news_event_contract_v1.py
tests/test_news_normalization_v1.py
tests/test_news_source_policy_v1.py
tests/test_news_review_contract_v1.py
tests/test_news_prompt_v1.py
tests/test_news_severity_router_v1.py
tests/test_news_provider_policy_v1.py
tests/test_news_provider_state_artifact_v1.py
tests/test_news_deepseek_adapter_v1.py
tests/test_news_claude_adapter_v1.py
tests/test_news_adjudicator_v1.py
tests/test_news_audit_artifact_v1.py
tests/test_news_replay_contract_v1.py
tests/test_news_replay_runner_v1.py
tests/test_news_intelligence_service_v1.py
```

Fixtures:

```text
tests/fixtures/news_intelligence_v1/raw_event_v1.json
tests/fixtures/news_intelligence_v1/normalized_event_v1.json
tests/fixtures/news_intelligence_v1/deepseek_l0_response_v1.json
tests/fixtures/news_intelligence_v1/claude_sonnet_l1_response_v1.json
tests/fixtures/news_intelligence_v1/claude_opus_l2_response_v1.json
tests/fixtures/news_intelligence_v1/replay_bundle_v1.json
tests/fixtures/news_intelligence_v1/prompt_injection_event_v1.json
```

`requirements.txt` is conditionally authorized only in a later dedicated SDK
dependency step after official contract verification. No existing engine or
test file is authorized for modification by this design freeze. Every slice
requires separate authorization.

## 25. Implementation Sequence

1. Event contracts.
2. Normalization.
3. Source eligibility and entity mapping.
4. Review contracts.
5. Prompt assembly and cache identities.
6. Severity router.
7. Provider policy, budget, and circuit state.
8. DeepSeek adapter.
9. Claude adapter.
10. Deterministic adjudicator.
11. Audit artifacts.
12. Replay contracts and runner.
13. Orchestration service.
14. Adversarial and failure fixtures.
15. Isolated provider contract verification.
16. Cost and routing evidence report.
17. Independent audit.
18. Owner lock and checkpoint.

Every slice requires tests first where applicable, bounded scope, no unrelated
refactor, focused regression, full regression before push, a clean commit
subject, and explicit returned evidence.

## 26. Required Test Evidence

Mandatory categories are:

- closed-schema validation;
- deterministic canonicalization and identity stability;
- update lineage and exact deduplication;
- entity ambiguity;
- L0 no-Claude proof;
- L1 Sonnet-only proof;
- direct-L2 Opus-only proof;
- deterministic L1-to-L2 proof;
- no model shopping;
- protected-field rejection;
- prompt-injection containment;
- stable-prefix byte identity and dynamic-suffix separation;
- Claude cache configuration;
- DeepSeek cache hit/miss telemetry;
- absent versus valid-zero telemetry;
- cached/uncached equivalence;
- timeout and transient retry;
- forbidden retry;
- circuit transitions;
- budget concurrency and USD 5 hard-cap enforcement;
- missing usage handling;
- malformed JSON and model identity mismatch;
- provider outage;
- exact idempotency;
- artifact collision, symlink rejection, and root isolation;
- replay network prohibition and cache-metadata preservation;
- findings-array order invariance;
- contradiction-code order invariance;
- evidence-reference order invariance;
- candidate-entity order invariance;
- candidate-symbol order invariance;
- impact-evidence order invariance;
- exact duplicate closed-code collapse;
- exact duplicate finding collapse;
- preservation of conflicting findings as distinct objects;
- provider JSON object-key order invariance;
- raw-provider optional-field absence versus nullable null;
- required-null rejection;
- optional omitted-field canonicalization;
- unknown semantic-field rejection;
- exclusion of provider metadata from `review_result_id`;
- preservation of raw provider ordering in the execution artifact;
- canonical normalized ordering in the semantic artifact;
- raw-to-normalized replay verification;
- `review_result_id` invariance under cache hit versus cache miss;
- `review_result_id` invariance across retry-attempt metadata;
- `review_result_id` invariance under latency changes;
- distinct `review_result_id` values for semantically different prose;
- Unicode code-point lexical sorting;
- invalid canonical-decimal rejection;
- unordered versus `order_semantics: SIGNIFICANT` array behavior;
- normalization failure producing `REVIEW_UNAVAILABLE`;
- proof that normalization failure is non-retryable;
- `review_execution_id` variation when usage or attempt metadata changes;
- `risk_object_id` invariance under cache-metadata changes;
- `risk_object_id` invariance under supporting execution-reference changes;
- proof that `risk_object_id` excludes `audit_snapshot_id` and
  `created_at_utc`;
- no circular identity dependencies;
- exact `audit_snapshot_id` stability;
- exact `replay_bundle_id` stability;
- direct-L2 rejection for every unlisted class;
- versioned critical-event allowlist enforcement;
- every L1 disagreement-matrix combination;
- every direct-L2 and L1-to-L2 disagreement-matrix combination;
- conservative `PASS`-versus-`FAIL` handling;
- unavailable required reviewer producing `REVIEW_UNAVAILABLE`;
- semantic replay without budget/circuit state;
- operational replay with budget/circuit state;
- operational replay of budget exhaustion;
- operational replay of circuit-open denial;
- operational replay of retry eligibility;
- proof that both replay modes remain network-free;
- zero publication effect; and
- forbidden import checks.

Most tests use mocks, fixtures, recorded responses, injected clocks, and
injected transports. Live calls are reserved for a later separately authorized
contract-verification step.

## 27. Phase 10 Exit Gate

Phase 10 may exit only when:

- every planned foundation module is complete;
- deterministic L0/L1/L2 routing is proven;
- DeepSeek, Sonnet, and Opus contracts are verified;
- prompt caching is implemented and audited;
- cache behavior has no authority effect;
- replay is exact and network-free;
- Claude spend is at or below USD 5;
- DeepSeek spend is reported separately;
- actual token, cost, latency, L1, and L2 evidence is reported;
- no unresolved `BLOCKER` or `HIGH` audit finding remains;
- production publication effect is zero;
- no protected Phase 09 or runtime surface changed;
- the owner declares Phase 10 `LOCKED`; and
- a checkpoint PDF is published.

## 28. Deferred Decisions

The following are explicitly deferred:

- live credentials wiring;
- VPS shadow runtime;
- Phase 11 API budget;
- calibration of severity thresholds from real shadow evidence;
- live Master Engine integration;
- production gating;
- Telegram exposure;
- 1-hour Claude cache TTL;
- semantic clustering authority;
- source-scraping infrastructure not required by isolated contracts; and
- automatic production `BLOCK` behavior.

These deferred items are not authorized by this design.

## 29. Final Design Declaration

Governance status:

- Independent Audit Step 03 returned `FAIL`.
- Step 04 applied the first corrective patch.
- Step 05 returned `PASS WITH REQUIRED CORRECTIONS`.
- Step 06 applied the semantic-review normalization corrective patch.
- Final Independent Audit Step 07 returned `PASS`.
- Findings: `F-01 CLOSED`, `F-02 CLOSED`, `F-03 CLOSED`, `F-04 CLOSED`,
  `F-05 CLOSED`, and `F-06 CLOSED`.
- Final counts: `BLOCKER 0`, `HIGH 0`, `MEDIUM 0`, and `LOW 0`.
- Owner decision: `APPROVE DESIGN FREEZE` after the final clean audit.
- Owner approval status: `APPROVED / DESIGN_FROZEN`.
- Approval baseline: `a84375fa85c2f318944adfe57aaabac6e43c219c`.
- Production authority: `NONE`.
- Publication effect: `NONE`.
- Implementation authority: implementation remains separately authorized one
  bounded slice at a time.

```text
PHASE 10 NEWS INTELLIGENCE & EVENT REASONING FOUNDATION
APPROVED / DESIGN_FROZEN

Baseline:
a84375fa85c2f318944adfe57aaabac6e43c219c

DeepSeek for primary structured review.
Claude Sonnet 5 for deterministic L1 review.
Claude Opus 4.8 for deterministic L2 challenge.
Python for routing, budget, failure behavior, and final adjudication.
Prompt caching for cost efficiency only.
Production publication authority remains NONE.

Implementation requires separate bounded authorization.
This design document alone does not authorize unrestricted implementation.
```
