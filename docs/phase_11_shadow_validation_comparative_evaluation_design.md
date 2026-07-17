# Phase 11 — Shadow Validation & Comparative Evaluation Design Freeze

## 1. Document Identity and Authority

Document identity:

- phase: `PHASE 11 — SHADOW VALIDATION & COMPARATIVE EVALUATION`;
- document version: `1.0`;
- governance status: `DESIGN FROZEN`;
- repository: `ai-crypto-signal-agent`;
- repository baseline: `8aee2dc02b69c30cdfebab307911e131c7daee6f`;
- production effect: `NONE`.

This design is governed by two owner-attested external records:

1. `CP_10_NEWS_INTELLIGENCE_EVENT_REASONING_LOCKED.pdf`, SHA-256
   `c5f084842c38fee8bba8a0032cefec9c0a781e508b8c9eb0224372a871a665d6`;
2. `AI_Crypto_Signal_Agent_Post_Phase_09_Roadmap_Extension_LOCKED_v1.1.pdf`,
   SHA-256
   `c680c6e50153ba12e6ea9d7b20743aeedf3d9b084430c626ba02e72550867580`.

The external records are owner-attested governance authority. Their absence
from Git does not weaken their authority or authorize reinterpretation. Phase
11 depends on `CP-10-LOCKED` and may validate and compare its frozen semantics;
it may not rewrite Phase 10 contracts, routing authority, or outcomes.

The phrase `Operational News Intelligence Integration` is not a separate phase
and does not replace the locked roadmap name or sequence. Operational provider
composition is permitted only as a bounded enabling subsystem inside this
shadow-validation phase.

Committing this document authorizes design only. It authorizes no provider
call, credential use, live news ingestion, production integration, candidate
change, publication, delivery, account access, exchange access, or order.

## 2. Objective, Non-Goals, and Exit Gate

### Objective

Phase 11 designs a shadow-only runtime and comparative evaluation subsystem to
measure whether locked Phase 10 intelligence improves risk awareness without
weakening signal integrity, determinism, reliability, latency, replayability,
security, or cost control. It measures quality, routing, disagreement, latency,
reliability, replayability, and cost against detached Phase 09 control evidence.

### Non-goals

Phase 11 does not authorize:

- production integration or mutation of any production runtime;
- candidate selection, removal, mutation, reranking, or eligibility changes;
- creation, mutation, suppression, or cancellation of `ProductionSignal`;
- publication capacity use or live publication effect;
- Telegram delivery or Telegram runtime startup;
- account, wallet, balance, position, capital, private endpoint, exchange, or
  order access;
- trading, simulated trading, order placement, amendment, or cancellation;
- Phase 12 enablement or silent promotion;
- unrestricted scraping, crawling, feeds, or news ingestion;
- modification of Phase 09 control artifacts or Phase 10 semantic authority;
- using comparative alternatives to shop for a favorable answer.

### Exit gate

Phase 11 may close only when all of the following are true:

- the approved sample plan was declared before sampling and its required class,
  L1, L2, direct-L2, and L1-to-L2 coverage is met or every deficit is explicitly
  reported as an unresolved limitation;
- no unresolved critical integrity, security, authority, isolation, replay, or
  budget defect remains;
- immutable evidence and network-free replay reproduce every deterministic
  result and aggregate claimed by the phase report;
- all reservations, usage, uncertain outcomes, releases, and caps reconcile in
  integer micro-USD and integer token units;
- the locked tiered policy is compared against both DeepSeek-only and
  single-Opus evaluation alternatives on matched cases;
- zero candidate, publication, Telegram, account, exchange, order, and trading
  effect is proven;
- an independent audit has reviewed the evidence and limitations; and
- the Project Owner approves the Phase 12 recommendation. A recommendation is
  not Phase 12 enablement and grants no production authority.

## 3. Authority Hierarchy

Authority is strict and non-substitutable:

1. The Project Owner owns numeric budget approval, model and credential-name
   approval, sample-plan approval, authorization of bounded live probes, and
   any promotion recommendation.
2. The Python deterministic budget controller owns whether a provider call is
   authorized. A provider, transport, operator convenience, or evaluator may
   not bypass a denied or absent reservation.
3. The Python deterministic router owns severity, L0/L1/L2 selection, optional
   L1-to-L2 escalation, and model-policy selection.
4. The deterministic adjudicator owns the news-risk decision from validated
   semantic provider results.
5. Providers are bounded reviewers. They do not own routing, escalation,
   budget, adjudication, candidate eligibility, publication, or trading.
6. The comparative evaluator owns only deterministic measurement over frozen
   evidence. It owns no production decision or authority.

No lower authority may override a higher authority. Free-form provider prose,
availability, price, latency, disagreement, or a preferred answer cannot
change this hierarchy.

## 4. Isolation Architecture

Phase 11 is an isolated sidecar. It consumes explicit immutable news-event
snapshots and may consume detached, read-only Phase 09 comparison artifacts.
It does not run inside or synchronously gate production.

```text
 Owner-approved immutable inputs
 ┌───────────────────────────────┐
 │ ApprovedNewsCaptureV1         │
 │ ShadowSamplePlanV1            │
 │ detached Phase 09 artifact    │
 └───────────────┬───────────────┘
                 │ validate + hash; fail closed
                 v
 ┌──────────────────────────────────────────────────────┐
 │ Phase 11 isolated sidecar                            │
 │                                                      │
 │ Phase 10 pure contracts -> deterministic router      │
 │            │                    │                     │
 │            v                    v                     │
 │ provider runtime <-> budget controller <-> circuit   │
 │            │                                          │
 │            v                                          │
 │ deterministic adjudication -> risk object -> gate     │
 │            │                                          │
 │            v                                          │
 │ comparative evaluator -> replay/evidence persistence  │
 └───────────────┬──────────────────────────────────────┘
                 │ Phase 11 root only
                 v
       data/phase_11_shadow_v1/

 Forbidden dependency and effect boundary
 ────────────────────────────────────────────────────────
 master_engine_v4 | run_scanner.sh | Telegram runtime
 production delivery adapters | Phase 09 write roots
 candidate state | ProductionSignal state | trading state
```

The sidecar SHALL:

- never invoke `engine.master_engine_v4` or any wrapper that invokes it;
- never invoke `run_scanner.sh`;
- never import or start Telegram runtime, polling, or transport;
- never call a production delivery adapter;
- never write to Phase 09 publication, evaluation, production evidence,
  pre-delivery, worker, quota, Telegram, Paper Signal, or Shadow Release roots;
- write only below the configured Phase 11 root;
- reject writable candidate, production-signal, delivery, account, or trading
  objects as input;
- operate on detached canonical values, never mutable production references.

## 5. Input Contracts

All contracts are closed, immutable, versioned, canonical-JSON-compatible, and
fail closed on unknown fields, invalid types, non-finite values, unsupported
versions, ambiguous timestamps, forged hashes, or inconsistent identity chains.
Canonical JSON uses UTF-8, sorted keys, deterministic separators, no NaN or
infinity, and normalized UTC timestamp text. SHA-256 is lowercase hexadecimal.

### ShadowEvaluationInputV1

Required fields:

- `schema_version`, `input_id`, `sample_plan_id`, `capture_id`;
- `event_snapshot_id`, `event_version_id`, `previous_event_version_id`;
- `phase09_control_projection_id` or explicit `null`;
- `point_in_time_utc`, `assembled_at_utc`;
- `fixture_live_classification`;
- `policy_snapshot_hash`, `component_versions`;
- `production_effect = NONE`.

`input_id` is SHA-256 over every semantic field except itself and
`assembled_at_utc`. `assembled_at_utc` is operational evidence and may not
change semantic identity. The input embeds or immutably references one exact
approved capture, sample plan, event snapshot, and optional detached control
projection. Identity mismatch or a point-in-time violation rejects the input
before budget reservation.

### Phase09ControlProjectionV1

Required fields:

- `schema_version`, `control_projection_id`, `source_commit`;
- `source_evaluation_id`, `mode`, `market_identity`;
- `evaluated_at_utc`, `captured_at_utc`;
- `outcome_kind`, detached eligible-setup identities;
- lifecycle, pre-delivery, and publication-disposition projections;
- source artifact content hashes and component versions.

This is a detached comparison projection, not a Phase 09 input or authority.
The projection must be built from explicit immutable evidence, never a mutable
`latest` path, directory order, current production memory, or filesystem time.
`control_projection_id` hashes all fields except itself. It is read-only and
cannot be passed to a delivery adapter.

### ApprovedNewsCaptureV1

Required fields:

- `schema_version`, `capture_id`, `source_identity`;
- canonical source URI and publisher identity;
- source credibility and source-policy identifiers;
- publication, capture, and point-in-time UTC timestamps;
- raw content hash, bounded content envelope, content type, and language;
- event identity, event version, prior-version identity, and lineage reason;
- `fixture_live_classification = FIXTURE | RECORDED_LIVE_CAPTURE`;
- capture-approval identity and capture-policy version.

`RECORDED_LIVE_CAPTURE` means only that source material was captured from a
live source under a separately approved capture mechanism. It does not grant
provider-call or production authority. Publication time must not exceed capture
time; capture time must not exceed point-in-time time; a prior version must
share the stable event identity and precede the new version. URI credentials,
fragments, unbounded bodies, mutable URLs without a content hash, and unknown
source identities fail closed. `capture_id` is SHA-256 over all semantic
capture fields except itself.

### ShadowSamplePlanV1

Required fields:

- `schema_version`, `sample_plan_id`, `plan_version`, `approved_by`;
- `approved_at_utc`, `sampling_start_utc`, `sampling_end_utc`;
- exact class vocabulary and `target_count_by_class`;
- minimum total cases, minimum L1, minimum L2, minimum direct-L2, and minimum
  L1-to-L2 counts;
- fixture versus recorded-live-capture limits;
- inclusion, exclusion, deduplication, and lineage rules;
- underrepresented-class rules and stop conditions;
- maximum total cases and maximum eligible live-provider cases;
- budget-policy identity and policy snapshot hash.

Every count is a non-negative, non-boolean integer; required minima and maxima
must be internally satisfiable. `sample_plan_id` hashes the complete semantic
plan except its identity. Once sampling begins, the plan is immutable. A new
plan version requires owner approval and a separate cohort; it cannot expand an
active sample opportunistically.

All timestamps are explicit ISO-8601 UTC values. Ambient clock values may be
used only when injected and recorded for operational timestamps; they may not
repair missing point-in-time evidence or alter semantic identities.

## 6. Provider Runtime Composition

The provider runtime is a Phase 11 composition boundary outside Phase 10
provider contracts. It SHALL NOT import or reuse
`engine.deepseek_validator_v4`, construct a production scanner, or inherit
production environment behavior.

The boundary receives:

- an exact validated Phase 10 provider payload;
- an exact route and model-policy decision;
- `Phase11ProviderRuntimePolicyV1`;
- a durable valid `RESERVED` budget-reservation identity;
- injected credential resolver, transport, timeout policy, circuit controller,
  clock, and response recorder.

`Phase11ProviderRuntimePolicyV1` freezes explicit provider names, exact model
IDs, model-policy IDs, allowed routes, credential environment names, endpoints,
API versions, transport versions, prompt/schema versions, and response limits.
Aliases, prefixes, `latest`, provider-default models, dynamic discovery, and
unknown model identifiers are rejected.

Credentials may be resolved only from the exact owner-approved environment
names listed in the active policy. Secrets SHALL remain in process-local
transport configuration, be redacted from exceptions, and never enter requests
persisted for audit, canonical identities, logs, artifacts, replay bundles, or
comparison output. The runtime records requested and returned provider/model
identity and rejects substitutions.

There is no implicit fallback, provider discovery, model shopping, or
availability-driven reroute. The runtime may not construct or dispatch a
request unless budget state confirms a valid reservation for the exact run,
provider, model, route, token limits, attempt number, and worst-case cost.

## 7. Routing Paths

The locked runtime policy is preserved exactly:

```text
L0: DeepSeek -> deterministic adjudication
    Claude call prohibited

L1: DeepSeek -> Claude Sonnet -> deterministic adjudication

L2: DeepSeek -> Claude Opus -> deterministic adjudication

Optional L1-to-L2:
    DeepSeek -> Claude Sonnet -> deterministic policy requires escalation
             -> Claude Opus -> deterministic adjudication
```

Only the Python deterministic router may select the route. Optional L1-to-L2
requires a closed reason code in an owner-approved immutable escalation policy,
a new Opus budget reservation, and preserved input/event identity. Sonnet,
Opus, DeepSeek, transports, or provider prose may not self-escalate.

A retry reuses the same provider, exact model, payload bytes, prompt/schema
versions, logical-review identity, and route. Retrying through another provider
or model to seek a successful or favorable answer is prohibited.

## 8. Budget Control Design

Money uses integer micro-USD; tokens and call counts use non-negative,
non-boolean integers. Floating-point money is prohibited.

### Phase11BudgetPolicyV1

Required fields include policy identity/version, owner approval evidence,
currency unit, total cap, per-provider caps, per-model caps, per-run cap,
maximum call count, provider/model call caps, maximum input/output/cache tokens,
maximum attempts, pricing-policy identity, approved routes, effective interval,
and hard-stop rules. Its identity hashes all semantic fields.

### BudgetReservationV1

Required fields include reservation identity, ledger identity/version, run and
attempt identities, provider/model/route, pricing version, maximum input/output
and cache exposure, worst-case retry exposure, reserved micro-USD, reservation
timestamp, state, and transition hash. States are `RESERVED`, `COMMITTED`,
`RELEASED`, or `UNCERTAIN`; transitions are append-only.

### ProviderUsageRecordV1

Required fields include run/request/attempt identity, exact provider/model,
provider-native usage hash, normalized input/output/cache token fields, usage
mapping version, estimated maximum cost, actual cost when resolvable, pricing
version, usage status, and binding to the reservation. Missing or malformed
usage is `UNRESOLVED`, never zero.

### BudgetLedgerV1

The ledger is an append-only, collision-rejecting sequence of policy,
reservation, commit, release, uncertainty, and reconciliation records. It
derives reserved, committed, uncertain, released, and safely available amounts
for total, provider, model, run, and call-count scopes.

Required semantics:

- the Project Owner approves the total and all subordinate caps;
- a worst-case reservation is durable before every call attempt;
- actual usage is committed only after validated usage mapping;
- a deterministic no-call path releases its unused reservation;
- an uncertain transport outcome remains conservatively reserved or committed
  at the approved worst case until evidence supports deterministic
  reconciliation;
- insufficient safely available budget denies the call before transport;
- exhaustion never implies approval, fallback, or cap extension;
- call-count and token caps are enforced independently of money caps;
- the controller hard-stops before any potential overrun;
- later pricing changes require a new immutable pricing policy and never
  rewrite historical cost.

The numerical Phase 11 budget is not approved by this design. No live provider
call may occur until a later owner budget gate supplies and approves exact
numeric caps.

## 9. Timeout, Retry, and Circuit Policy

`Phase11ExecutionControlPolicyV1` freezes positive integer connection-timeout
seconds, response-timeout seconds, maximum attempts, retryable failure codes,
circuit thresholds, open duration, and half-open rules per exact provider and
model. Values must be owner approved before live use and recorded in every run.

Maximum attempts are fixed at two: one initial attempt and at most one retry.
There is no loop controlled by provider prose, exception text, wall-clock
convenience, or an unbounded counter.

Retry eligibility is limited to closed pre-complete-response transport classes:

- connection establishment failure;
- approved rate-limit response;
- approved transient provider/server response;
- transport interruption before a complete response; and
- response timeout before a complete response.

Schema failure, malformed JSON, unknown fields, identity/model mismatch,
authority violation, invalid signature/hash, budget denial, circuit denial,
provider refusal, completed semantic response, and persistence failure are not
retryable. A retry requires a distinct attempt reservation.

Circuit state is deterministic and scoped independently by provider, exact
model ID, endpoint-policy version, and circuit-policy version. Provider-wide
state may additionally block every model for a closed provider-failure class;
model-specific failures must not silently contaminate other models.

An approved count of consecutive eligible failures opens the circuit. Open
state denies calls before reservation or deterministically releases a prepared
reservation. After the frozen open interval, exactly one owner-policy-eligible
half-open probe may reserve budget and execute. Concurrent half-open probes are
prohibited. Failure reopens; validated success closes. Budget denial never
forces a probe, fallback, or state reset.

Terminal outcomes are closed and shadow-only: `REVIEW_TIMEOUT`,
`TRANSPORT_FAILED`, `PROVIDER_UNAVAILABLE`, `PROVIDER_CIRCUIT_OPEN`,
`BUDGET_DENIED`, `INVALID_PROVIDER_RESPONSE`, or `REVIEW_UNAVAILABLE`.

## 10. Shadow Execution Record

`ShadowExecutionRecordV1` is a closed immutable completed or terminal-failure
record containing:

- execution-record, input, event snapshot, event version, sample-plan, and
  optional Phase 09 control identities;
- source commit and component versions;
- exact provider, requested/returned model, transport, prompt, schema,
  normalization, mapping, router, adjudication, risk, gate, budget, pricing,
  usage-mapping, timeout, retry, and circuit-policy versions;
- selected route, route identity, and escalation reason codes;
- request envelope hashes and raw/normalized response artifact hashes;
- normalized token usage, estimated maximum cost, actual/reconciled cost, and
  reservation/ledger references;
- connection, provider, and end-to-end latency in integer microseconds;
- attempt count, retry decisions, timeout outcomes, and before/after circuit
  states;
- provider semantic verdict identities;
- deterministic adjudication result and identity;
- `NewsRiskObject` identity and `SignalGateDecision` identity;
- terminal failure class and stable reason codes, if any;
- explicit no-production-effect proof;
- explicit UTC start, attempt, response, completion, and persistence timestamps;
- record content hash and prior-record hash where an append-only chain applies.

No-production-effect proof records that forbidden modules were not composed,
no production adapter was called, no production root was opened for write, and
no candidate or production-signal reference was accepted. The proof is
evidence, not a grant of authority.

Bounded free-form provider prose may be stored only in a separately hashed raw
response artifact after secret scanning. It does not enter route, budget,
adjudication, risk, gate, comparison, or authority identity.

## 11. Comparative Evaluation Contracts

### ComparativeEvaluationCaseV1

One case binds an exact input and sample-plan identity to matched evidence for:

- `A_LOCKED_TIERED_POLICY`;
- `B_DEEPSEEK_ONLY`;
- `C_SINGLE_OPUS`.

It contains case identity, inclusion class, point-in-time boundary, execution or
replay references for each available branch, ground-truth/assessment evidence
when approved, missing-branch reasons, and component versions. Branches use the
same canonical event evidence and cannot import facts observed after the case
point-in-time.

### ComparativeEvaluationResultV1

One result records deterministic per-branch risk/gate projections, agreement
matrix, latency, usage, cost, failures, mapping/lineage results, hold/reject
deltas, quality labels, and reason codes. Its identity binds the case and all
branch evidence hashes. Missing evidence remains explicit and is never imputed
as agreement, zero cost, or success.

### EvaluationAggregateV1

The aggregate binds one immutable sample plan and the complete ordered set of
case/result identities. It records denominators, missingness, per-class and
overall metrics, confidence/uncertainty annotations approved by policy, budget
reconciliation, integrity checks, and zero-production-effect totals. Reordering
or omitting a case changes aggregate identity.

Alternatives B and C are evaluation branches only. They may use authorized
recorded responses or separately budgeted shadow calls, but may not change,
replace, tune, or feed back into the locked tiered runtime policy during the
sample.

## 12. Comparison Metrics

Every metric declares its numerator, denominator, eligible population, unit,
missing-data rule, class breakdown, and branch. Zero denominators produce
`NOT_EVALUABLE`, not zero.

Required metrics are:

- event detection latency where publication and capture times are available;
- normalization delay and end-to-end review latency;
- L0, L1, and L2 rate;
- direct-L2 and L1-to-L2 rate;
- pairwise and three-way model disagreement;
- unresolved ambiguity rate;
- mapping accuracy against approved labeled evidence;
- duplicate suppression and update-lineage correctness;
- source-conflict handling correctness;
- `GREEN`, `AMBER`, `RED`, and `BLOCK` distribution;
- false-block rate against approved materiality/outcome labels;
- missed-material-event rate;
- unnecessary-escalation rate under the locked routing criteria;
- provider outage and circuit-open behavior;
- schema-failure and retry rate;
- cost per eligible event, cost per L1, and cost per L2;
- projected monthly cost using a predeclared eligible-event-volume assumption;
- shadow hold/reject delta relative to the detached Phase 09 control;
- live-publication impact, which must equal exactly zero.

Detection latency is unavailable rather than fabricated when source publication
time is not reliable. Cost projections present assumptions and sensitivity
bounds and do not become budget authority. Quality labels must be point-in-time,
versioned, and independent of provider prose.

## 13. Sample Plan and Coverage

The sample plan freezes these classes before sampling:

- clean/routine;
- moderate ambiguity;
- critical ambiguity;
- source disagreement;
- mapping ambiguity;
- exploit/security;
- delisting;
- legal/regulatory;
- solvency/exchange risk;
- suspected manipulation;
- systemic/cross-market;
- malformed provider output;
- timeout/outage;
- budget exhaustion;
- duplicate/update lineage;
- prompt-injection/adversarial content.

For every class, `target_count_by_class` is a required positive integer unless
the owner-approved plan marks the class `SIMULATION_ONLY`, in which case a
positive fixture target remains required. The plan also freezes minimum L1,
L2, direct-L2, and L1-to-L2 counts, minimum recorded-live versus fixture counts,
maximum sample count, and maximum live-call-eligible count.

Stop conditions include budget hard stop, call-count/token cap, critical
security or authority defect, identity-chain failure, evidence-root integrity
failure, unreconciled budget uncertainty that prevents safe availability,
unauthorized model/credential configuration, or owner suspension. Reaching a
time boundary or maximum count closes sampling without inventing missing
coverage.

An underrepresented class remains a declared coverage deficit. It may be filled
only by already authorized selection rules, recorded historical evidence, or
predeclared deterministic fixtures. It may not be substituted with another
class, relabeled after results are known, or trigger opportunistic ingestion or
sample-plan expansion. Any later owner-approved plan version forms a separately
reported cohort.

Numeric sample counts remain owner-configurable at the later sample-plan gate,
but required fields, positive-integer validation, internal consistency,
immutability after start, class vocabulary, and deficit treatment are frozen by
this design.

## 14. Replay and Evidence

`Phase11ReplayBundleV1` contains:

- exact normalized input and event/capture lineage;
- sample-plan and policy/config snapshots;
- prompt/schema and provider/model identity snapshots;
- recorded request hash and provider response envelope;
- usage, cost, attempt, circuit, and integer timing records;
- validated semantic provider result;
- deterministic router, adjudication, risk, and gate results;
- comparison case/result;
- artifact content hashes, identity chain, and bundle manifest hash.

Replay uses recorded evidence only. It makes no provider call, loads no
credential, reads no live endpoint or pricing, uses no current provider state,
and writes no production root. Injected replay clocks reproduce recorded
operational values while semantic computations remain clock-independent.

Replay must reproduce every deterministic identity and output byte-for-byte or
emit `REPLAY_MISMATCH`. It verifies every content hash, policy binding,
provider/model binding, lineage link, ordering rule, and manifest relationship.
Missing, substituted, reordered, or altered evidence is tampering and fails
closed.

## 15. Persistence Roots

The default isolated root is `data/phase_11_shadow_v1/` with proposed sub-roots:

```text
data/phase_11_shadow_v1/inputs/
data/phase_11_shadow_v1/executions/
data/phase_11_shadow_v1/provider_usage/
data/phase_11_shadow_v1/budget_ledger/
data/phase_11_shadow_v1/circuit_state/
data/phase_11_shadow_v1/replay_bundles/
data/phase_11_shadow_v1/evaluation_results/
data/phase_11_shadow_v1/aggregate_reports/
```

Every writer must validate that the resolved destination remains beneath the
configured Phase 11 root and that no path component is a symlink. Writes are
intent-first where a side effect may occur, use same-directory temporary files,
fsync-compatible durability, atomic rename, immutable completion records, and
directory synchronization where supported.

Canonical identity determines destination. Byte-identical repeats are
idempotent. An existing identity with different bytes is a collision and fails
closed; files are never silently replaced. Partial intents are recovered only
through a deterministic recovery record that proves whether no call, an
uncertain call, or a completed call occurred. Recovery cannot fabricate usage
or release uncertain budget.

Secret fields and values are prohibited recursively. Artifacts use bounded
sizes and sanitized stable failure codes. Retention policy is versioned,
owner-approved, and scoped only to Phase 11; expiry may archive or delete only
after integrity, budget, audit, and replay obligations are satisfied. This
design does not change any existing production-root contract.

## 16. Security and Untrusted Input

All source text and provider output is untrusted data, never instruction or
authority. Controls include:

- prompt-injection delimiters, fixed system authority, bounded evidence fields,
  and explicit statements that embedded instructions are inert;
- Unicode and line-ending normalization without semantic invention;
- strict JSON decoding, exact schemas, closed enums, depth/size/count limits,
  and rejection of duplicate keys and non-finite numbers;
- explicit schema-version allowlists and no automatic schema migration;
- requested/returned provider and model identity matching;
- recomputation of event, version, capture, request, response, and result hashes
  to reject forged identities;
- request/logical-review binding and consumed-response tracking to prevent
  unauthorized response replay;
- credential allowlists, process-local secret handling, redaction, secret
  scanning, and prohibition from serialized evidence;
- escaped or structured logs with bounded stable codes to prevent log
  injection;
- normalized relative artifact names, resolved-root containment, and symlink
  rejection to prevent path traversal;
- pre-call payload byte/token hard limits and bounded response reads;
- exclusion of provider prose from route, escalation, budget, adjudication,
  risk, gate, comparison, and authority identities.

A provider response that says to escalate, publish, trade, change policy,
ignore budget, reveal credentials, or execute code remains inert untrusted text.

## 17. Failure Taxonomy

Terminal failure classes are exact and deterministic:

- `VALIDATION_FAILURE`: malformed, incomplete, unsupported, or inconsistent
  input before execution;
- `UNAUTHORIZED_INVOCATION`: missing owner/runtime authority or forbidden
  composition/action;
- `BUDGET_DENIED`: absent, invalid, exhausted, or insufficient reservation;
- `TIMEOUT`: approved connection or response deadline exceeded;
- `TRANSPORT_FAILURE`: bounded transport failure not classified as timeout;
- `PROVIDER_UNAVAILABLE`: provider-declared or validated availability failure;
- `CIRCUIT_OPEN`: provider/model circuit denied execution;
- `MALFORMED_RESPONSE`: unreadable, unbounded, or invalid JSON response;
- `SCHEMA_MISMATCH`: response fails the exact approved schema/version;
- `IDENTITY_MISMATCH`: event, payload, request, provider, model, response, or
  lineage identity differs from authority;
- `ADJUDICATION_FAILURE`: validated semantic inputs cannot produce the frozen
  deterministic result;
- `PERSISTENCE_FAILURE`: intent, atomic write, durability, containment, or
  collision invariant fails;
- `REPLAY_MISMATCH`: replay hash, identity, or deterministic output differs;
- `COMPARISON_FAILURE`: matched-case or aggregate invariants cannot be proven.

Each record contains one primary class and ordered secondary reason codes.
Exception prose, secrets, raw content, and filesystem paths are excluded from
stable failures. Every terminal failure remains shadow-only, produces no
candidate or production effect, and fails closed. An unavailable review never
becomes `GREEN`, approval, publication, or an implicit alternative-model call.

## 18. Proposed Implementation File Tree

The following is a proposal only. This commit creates none of these files:

```text
engine/phase11_shadow_input_contract_v1.py
engine/phase11_sample_plan_contract_v1.py
engine/phase11_provider_runtime_v1.py
engine/phase11_budget_control_v1.py
engine/phase11_circuit_state_v1.py
engine/phase11_shadow_execution_v1.py
engine/phase11_shadow_artifact_v1.py
engine/phase11_replay_contract_v1.py
engine/phase11_replay_runner_v1.py
engine/phase11_comparative_evaluation_v1.py
engine/phase11_evaluation_aggregate_v1.py

tests/test_phase11_shadow_input_contract_v1.py
tests/test_phase11_sample_plan_contract_v1.py
tests/test_phase11_provider_runtime_v1.py
tests/test_phase11_budget_control_v1.py
tests/test_phase11_circuit_state_v1.py
tests/test_phase11_shadow_execution_v1.py
tests/test_phase11_shadow_artifact_v1.py
tests/test_phase11_replay_contract_v1.py
tests/test_phase11_replay_runner_v1.py
tests/test_phase11_comparative_evaluation_v1.py
tests/test_phase11_evaluation_aggregate_v1.py

tests/fixtures/phase11_shadow_v1/
```

Runtime composition, budget control, circuit state, shadow execution,
persistence, replay, comparative evaluation, and aggregation remain separate.
Phase 11 modules depend on frozen Phase 10 value contracts through explicit
adapters and consume detached Phase 09 projections. Phase 10 contracts and the
Phase 09 production runtime do not depend on Phase 11.

## 19. Test Strategy

Implementation is RED-first. Contract tests are written and observed failing
before the corresponding implementation slice. Required suites cover:

- closed schemas, canonical identities, timestamp/lineage rules, immutability,
  and forged identity rejection;
- exact provider/model/credential-name allowlists and alias rejection;
- secret and credential exclusion from requests-at-rest, logs, errors,
  identities, artifacts, and replay;
- durable reserve-before-call proof and rejection when reservation is absent;
- total/provider/model/run/call/token hard budget stops and uncertain-outcome
  reconciliation;
- connection/response timeout, one-retry maximum, non-retryable failures,
  provider/model circuits, and single half-open probes;
- L0 no-Claude enforcement, L1/L2 correctness, deterministic L1-to-L2 reasons,
  and provider non-authority;
- prohibition of fallback, model shopping, favorable-answer retries, and
  production DeepSeek runtime reuse;
- zero master-engine, scanner-script, Telegram, delivery, production-root,
  candidate, signal, account, exchange, order, and trading effect;
- atomic persistence, idempotency, collision rejection, partial-write recovery,
  root containment, and symlink/path traversal rejection;
- replay network isolation, deterministic reproduction, and tamper detection;
- matched-case comparison, missing-data behavior, denominators, metrics,
  aggregation, and monthly-cost projection;
- malformed JSON, schema drift, oversized payloads, prompt injection, malicious
  prose, log injection, replay attacks, and model/identity substitution.

Most tests use deterministic fakes, fixtures, injected clocks/transports, and
recorded responses. Network access is prohibited in unit, contract, replay,
failure-injection, and comparative-calculation tests. Live probes require the
separate gate below and are not part of ordinary regression.

## 20. Live-Call Gate

**No live provider call may occur merely because this design is committed.**

A later step must separately provide all of the following:

- an owner-approved numeric Phase 11 total budget and every subordinate cap;
- exact approved provider and model IDs, endpoints, API versions, and pricing
  policy;
- exact approved credential environment names, without credential values in
  Git or evidence;
- an owner-approved immutable `ShadowSamplePlanV1`;
- explicit call-count, token, per-run, per-provider, per-model, and cost stop
  conditions;
- successful mock, replay, security, budget, timeout, circuit, persistence, and
  failure-injection evidence;
- a clean independent preflight audit; and
- explicit Project Owner authorization to begin bounded live probes.

Absence, ambiguity, expiry, mismatch, or failure of any gate item means no live
call. Approval of one probe, model, route, cohort, or cap does not approve
another.

## 21. Step Plan

The bounded proposed sequence is:

```text
design
  -> RED tests
  -> contracts
  -> runtime controls
  -> isolated orchestrator
  -> persistence/replay
  -> comparative evaluator
  -> mock validation
  -> owner budget gate
  -> bounded live probes
  -> sampling
  -> evidence report
  -> independent audit
  -> closure
```

Each arrow is a separate authorization boundary. No step silently authorizes
the next. Design, mock validation, or a green regression cannot substitute for
the owner budget gate or explicit live-probe authorization.

## 22. Lock Declaration

This document freezes Phase 11 scope, authority hierarchy, sidecar isolation,
input and evidence contracts, provider-composition boundary, deterministic
budget semantics, routing paths, timeout/retry/circuit semantics, execution
record, comparative alternatives, metrics, sample coverage, persistence roots,
network-free replay, security controls, failure taxonomy, test strategy,
live-call gate, step sequence, and exit criteria.

Production effect remains `NONE`.

This design does not authorize implementation, live calls, credentials,
unrestricted ingestion, production integration, candidate mutation,
publication, Telegram delivery, account or exchange access, orders, trading, or
Phase 12 enablement. Any change to a frozen semantic requires a new version,
explicit owner approval, tests, evidence, and audit; version 1.0 is not modified
in place.
