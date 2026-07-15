# Phase 08 — Shadow Release Design Freeze

Status: DESIGN FROZEN

Locked baseline: `c9b698fa0cbc4a8cfa5cad4289004cd683103278`

Phase 07 is immutable. This document authorizes no implementation, no test
change, no runtime artifact, no commit, and no capital-enabled behavior.

## 1. Purpose and Non-Authority

Phase 08 adds a **Shadow Release** evidence lane. A shadow run receives a
sealed, serialized capture of one live production evaluation and executes the
same deterministic Master Engine V4 composition with isolated providers and
sinks. It compares that result with the authoritative serialized production
decision and records an immutable audit result.

Shadow Release is observational. It is neither a trading system nor a second
production publisher. It must never:

- place, submit, cancel, or amend an exchange order;
- use exchange credentials, trading permissions, private endpoints, or account
  state;
- allocate capital, size a position, create a fill, or operate a virtual
  brokerage;
- mutate exchange, account, balance, portfolio, position, Telegram ledger,
  production evidence, replay evidence, or Paper Signal evidence;
- invent source identity, market data, lifecycle events, timestamps, or
  intrabar ordering; or
- change Phase 06 replay, Phase 07 Paper Signal, or existing lifecycle
  semantics.

Passing a Phase 08 release-readiness gate is audit evidence only. It does not
authorize a capital deployment, an order permission, or a change to any
production execution authority.

## 2. Proven Repository Semantics

The baseline contains these relevant, already-authoritative behaviors.

1. `engine.master_engine_v4.run_master_engine_v4` calls, in order:
   `scanner`, `run_validated_pipeline_v4`, validated snapshot saver, outcome
   saver, Top-5 watchlist saver, `run_pre_delivery_flow`, and production
   evidence saver.
2. `engine.pre_delivery_flow_v4.run_pre_delivery_flow` reads the Top-5
   watchlist, builds a pre-delivery artifact using closed OHLCV, writes the
   TradingView watchlist, builds a Pine bridge and delivery payload, and saves
   both delivery outputs.
3. The live `/scan` command path is:

   ```text
   Telegram SDK polling
     -> TelegramRuntimeV4 / TelegramTransportV4
     -> TelegramApplicationV4.dispatch("/scan")
     -> run_quota_slot_worker_v4
     -> run_master_engine_worker_v4
     -> run_master_engine_v4
     -> scanner -> validated pipeline -> artifact/predelivery/evidence flow
   ```

   `TelegramApplicationV4` reports command completion; it does not define an
   official signal publication, `signal_id`, or `delivery_id` contract.
4. `engine.stateful_worker_v4` owns only the worker status file and records
   paths returned by the master engine. It is not a signal lifecycle ledger.
5. `engine.replay_runner_v4` proves a useful composition pattern: it calls the
   real master-engine boundary with recorded providers and isolated writers.
   Its classification is `REPLAY` and its protected roots must remain separate
   from Shadow Release.
6. Phase 07 owns the canonical `PAPER_SIGNAL` / `LIVE_MARKET_OBSERVATION_NO_CAPITAL`
   envelope, its source-publication reference, paper observation lifecycle,
   acknowledgment attachment, progress aggregation, and `data/paper_signal`
   artifacts. Shadow Release must not write there or reuse its classification.

### 2.1 Integration fact

The inspected V4 production-adjacent modules do **not** expose a canonical
serialized official-publication envelope containing `signal_id` and
`delivery_id`. The Top-5 and pre-delivery artifacts also do not by themselves
establish Telegram publication delivery. Therefore Phase 08 must not derive
those values from a path, timestamp, process-local counter, rank, or object
identity.

The future Phase 08 integration seam is an explicit caller-supplied,
serialized production-publication capture. Until an authoritative publisher
provides that capture, a run may only represent a serialized `NO_TRADE`
evaluation; it must reject a claimed published-signal run with absent or
synthetic source identity. This is an intentional fail-closed boundary, not a
license to modify the Phase 07 contract.

## 3. Classification and Boundary Constants

The Phase 08 contract reserves these exact values:

```text
classification:       SHADOW_RELEASE
execution_boundary:   LIVE_PRODUCTION_PATH_OBSERVATION_NO_CAPITAL
capital_exposure:     NONE
order_execution:      PROHIBITED
position_authority:   NONE
```

`position_authority: NONE` means a shadow record has no authority to create or
mutate a position. It may compare a serialized Phase 07 acknowledgment or
Telegram-derived lifecycle event, but does not become `TELEGRAM_USER_REPORT`
and does not call a Telegram ledger.

The following namespaces are disjoint:

| Evidence lane | Classification / authority | May write |
| --- | --- | --- |
| Replay | `REPLAY`, recorded-input master-engine reproduction | replay-only roots |
| Paper Signal | `PAPER_SIGNAL`, live-market observation with Telegram user report authority | `data/paper_signal` only |
| Shadow Release | `SHADOW_RELEASE`, comparison of sealed production-path inputs and outputs | `data/shadow_release` only |
| Telegram delivery | transport and user command interface | its pre-existing state only |
| Future production execution | separately approved capital authority | not authorized by this phase |

No Phase 08 code may convert an artifact from one classification into another,
or count one lane's evidence toward another lane's gate.

## 4. Canonical Live Path and Authorities

### 4.1 Observed path

For an admitted Telegram scan, the canonical live decision path to observe is
the composition in Section 2. The decision boundary is
`run_master_engine_v4`; it is the only existing function that joins scanner
input, validated pipeline, artifact creation, pre-delivery construction, and
production evidence composition.

Shadow Release does not invoke the Telegram SDK, poll Telegram, send a
message, acquire a quota slot, or write worker/quota state. Those actions are
live command transport and admission behavior, not deterministic decision
calculation. The adapter captures their authoritative serialized outcome only
when publication or lifecycle comparison needs it.

### 4.2 Authoritative input capture

One `ShadowInputEnvelopeV1` must be a plain JSON object supplied by the
production-side integration boundary. It contains, at minimum:

- `schema_version`, `classification`, and `execution_boundary`;
- `source_commit`: the full commit hash of the production decision;
- `source_evaluation_id`: opaque authoritative evaluation-cycle identifier;
- `mode`: exactly `SWING`, `INTRADAY`, or `SCALP`;
- `market_identity`: exact `venue`, `symbol`, `interval`, and
  `market_data_source` strings; and `market_input_hash`;
- `captured_at`, `evaluation_started_at`, and `evaluation_completed_at` as
  explicit UTC timestamps;
- serialized scanner result, OI values, validator response and usage, and
  closed-candle inputs required by the actual Master Engine V4/pre-delivery
  path, each with a canonical SHA-256 hash;
- canonical expected production semantic projection and its hash;
- an optional authoritative `source_publication_ref` containing exactly the
  frozen Phase 07 fields (`signal_id`, `delivery_id`, `mode`, `published_at`,
  `source_payload_hash`), plus immutable signal geometry when a signal was
  published;
- an optional serialized lifecycle trace containing only authoritative
  publication, cancellation, Paper Signal observation, and acknowledgment
  events needed for comparison; and
- an explicit `outcome_kind`: `PUBLISHED_SIGNAL` or `NO_TRADE`.

For `PUBLISHED_SIGNAL`, `source_publication_ref` and immutable geometry are
mandatory. For `NO_TRADE`, they are both `null`, and no `signal_id` or
`delivery_id` may be synthesized. A cycle may have one or more published
signals only if the authoritative capture represents each as an independent
envelope with the same `source_evaluation_id` and its own market identity.

The Shadow runner consumes only this envelope, its deterministic explicit
clock values, and component versions. It must deep-copy decoded values before
use. It must not read an ambient cache, global registry, current worker state,
latest artifact path, environment secret, mutable object reference, or live
network result as an identity or decision authority.

### 4.3 Authoritative outputs

The production-side adapter seals the following expected outputs as canonical
JSON semantic projections, not as filesystem paths:

- validated pipeline result and ordered final candidates;
- outcome snapshot semantic content;
- Top-5 watchlist semantic content;
- pre-delivery artifact, TradingView watchlist content, Pine bridge artifact,
  and Pine delivery payload content;
- authoritative publication status and the serialized source-publication
  reference when present;
- the serialized lifecycle trace when present; and
- hashes for each input and expected output projection.

Absolute paths, writer timestamps, temporary names, copied-file metadata,
worker run IDs, Telegram update IDs, process IDs, and transport attempt IDs
are evidence metadata only. They are never a decision authority.

## 5. Identity, Canonical JSON, and Hashes

All Phase 08 hashing uses UTF-8 JSON with sorted keys, compact separators,
`ensure_ascii=False`, and `allow_nan=False`. SHA-256 digests are lower-case
64-character hexadecimal strings. Non-finite numbers, unknown fields, and
boolean values in integer fields are rejected.

### 5.1 Stable identity

The immutable identity payload is:

```text
{
  "schema_version": 1,
  "source_commit": source_commit,
  "source_evaluation_id": source_evaluation_id,
  "mode": mode,
  "market_identity": market_identity,
  "outcome_kind": outcome_kind,
  "source_publication_ref": source_publication_ref,
  "serialized_input_hash": serialized_input_hash,
  "expected_decision_hash": expected_decision_hash
}
```

```text
shadow_run_id = "SHR-" + sha256(canonical_json(identity_payload))
```

`shadow_run_id` is not a UUID and is not clock-derived. Reuse of an identity
with byte-identical canonical evidence is idempotent. Reuse with any different
canonical payload is a collision and fails closed.

The source `signal_id`, source `delivery_id`, evaluation identity, mode, and
market identity remain opaque authority-owned values. The implementation must
not normalize, renumber, infer, or store process-local aliases for them.

`content_hash` is SHA-256 of the complete completed run payload excluding only
its own `content_hash`. It includes all identity fields, versions, hashes,
comparison result, failure record when applicable, and explicit timestamps.

## 6. Deterministic Shadow Execution and Comparison

### 6.1 Same decision topology

`run_shadow_release_v1` must execute `run_master_engine_v4` with injected
providers and isolated savers, following the Replay V4 dependency-injection
pattern. The injected scanner, OI provider, validator, and closed-candle
provider return only data decoded from `ShadowInputEnvelopeV1`. The injected
savers write only ephemeral staging outputs inside the validated shadow root.

The runner passes the envelope's explicit evaluation completion time as the
master engine's `now_provider`. It must not call the ambient clock for a
semantic field. Operational start and completion timestamps are captured by
the caller and stored as evidence; they do not alter the semantic projection.

### 6.2 Exact-match projection

The runner normalizes the production capture and shadow result to the same
versioned semantic projection before comparison. The projection includes every
decision-bearing field, ordered candidate list, source publication envelope,
publication disposition, lifecycle trace, and content of generated delivery
outputs. Comparison is exact canonical-byte equality of the normalized
projection and is also reported by component hash.

The only permitted non-semantic differences are:

- absolute artifact paths and temporary/staging paths;
- process, worker, quota, and Telegram update identifiers;
- filesystem timestamps and permissions;
- operational `started_at`, `completed_at`, and elapsed duration; and
- explicitly versioned transport-attempt metadata not included in the
  canonical projection.

Any omitted, unknown, reordered decision-bearing, or hash-mismatched field is
a mismatch. There is no tolerance, score threshold, floating-point epsilon,
or "best effort" comparison mode.

### 6.3 Lifecycle comparison

Shadow Release compares serialized authoritative lifecycle evidence; it does
not drive the lifecycle. When present, the comparison preserves these frozen
Phase 07 rules exactly:

- publication identity and immutable geometry;
- entry eligibility and entry-zone touch;
- authoritative cancellation and its timestamp;
- target-before-entry, invalidation-before-entry, expiry, and ambiguous
  same-candle behavior;
- no invented TP/SL intrabar ordering;
- `ENTRY_REPORTED` or `SKIP_REPORTED` acknowledgment identity and exact
  millisecond latency; and
- `NO_TRADE` as a cycle with no official publication, not as a failed or
  simulated order.

`ENTRY_ZONE_TOUCHED` is not a fill. TP/SL observations are not closes.
Acknowledgment comparison never writes to Telegram or a position ledger.
Terminal Paper Signal observations remain immutable; Shadow Release only
compares a supplied serialized copy and writes its own evidence.

### 6.4 Result and failure classes

A completed run has one of `MATCH`, `MISMATCH`, or `FAILED`.

`MISMATCH` uses exactly one primary code and zero or more secondary codes:

- `DECISION_MISMATCH` — validated pipeline/final candidate semantics differ;
- `PUBLICATION_MISMATCH` — publication disposition, source identity, geometry,
  pre-delivery, TradingView, Pine bridge, or delivery payload differs;
- `LIFECYCLE_MISMATCH` — a supplied lifecycle event/state differs;
- `NO_TRADE_MISMATCH` — the official-alert versus NO-TRADE disposition differs;
- `NONDETERMINISM_DETECTED` — two executions of the same sealed envelope have
  different normalized shadow projections; or
- `EVIDENCE_HASH_MISMATCH` — supplied or generated canonical hashes disagree.

`FAILED` uses exactly one primary code:

- `INPUT_CONTRACT_REJECTED`;
- `SOURCE_AUTHORITY_MISSING`;
- `COMPONENT_VERSION_UNSUPPORTED`;
- `SHADOW_EXECUTION_FAILED`;
- `ARTIFACT_PUBLICATION_FAILED`;
- `ROOT_ISOLATION_VIOLATION`;
- `IDENTITY_COLLISION`; or
- `CONCURRENCY_CONFLICT`.

Any attempted protected import, forbidden call, root escape, symlink, or
mutation attempt is a critical `FAILED` record. Failure text must be a stable
safe classification and component name; it must not embed credentials,
absolute secret locations, or raw exception traces. A failure cannot be
relabelled as a stale success.

## 7. Evidence and Duration Rules

A completed artifact contains exactly the versioned run envelope, identity,
classification/boundary fields, source commit and component versions, explicit
start/completion timestamps, outcome, hashes, per-component comparison result,
and either `failure: null` or a classified failure evidence object.

`started_at <= completed_at` is required. `operational_duration_ms` equals the
exact integer millisecond difference between them; sub-millisecond values are
rejected. This duration is operational evidence only. The deterministic
evaluation duration is separately the exact difference between
`evaluation_started_at` and `evaluation_completed_at` captured in the source
envelope. Neither duration participates in `expected_decision_hash`.

Evidence completeness requires all of the following:

- a valid sealed input hash and expected-decision hash;
- a valid normalized shadow-decision hash;
- source commit and versions for Master Engine, validated pipeline,
  pre-delivery, Shadow contract/runner/comparator, and Phase 07 observer when
  lifecycle comparison is present;
- every required input/output component hash;
- explicit publication or NO-TRADE disposition;
- an exact comparison record for every expected component; and
- classified failure evidence when the outcome is `FAILED`.

An incomplete record is not a completed artifact and does not count toward
any gate.

## 8. Artifact Publication, Root Isolation, and Concurrency

The only authorized Phase 08 root is `data/shadow_release`, with these
subdirectories:

```text
data/shadow_release/runs/
data/shadow_release/progress/
data/shadow_release/.locks/
```

Completed run artifacts are named `runs/<shadow_run_id>.json`. Progress is
also immutable and content-addressed:
`progress/SHP-<sha256-of-progress-identity>.json`. There is no mutable
"latest" evidence file.

The publisher must:

1. reject a missing, non-directory, or symlinked root or ancestor;
2. reject an output path that does not resolve under the configured shadow
   root;
3. reject roots named or located beneath `replay`, `replay_artifacts`,
   `production_evidence`, `production_evidence_v4`, `production_run_v4`,
   `validated_snapshots_v4`, `v4_outcomes`, `top5_watchlist_v4`,
   `pre_delivery_v4`, `pine_delivery_v4`, `telegram_state`,
   `worker_state_v4`, `quota_slot_v4`, `position_ledger`, or `paper_signal`;
4. serialize canonical JSON plus one newline;
5. acquire a shadow-root-local publication lock for the identity, recheck an
   existing final regular file, and permit reuse only if its bytes are exactly
   identical;
6. reject a different byte sequence for the same final identity;
7. write a same-directory temporary regular file, flush and fsync it, then
   atomically replace the final path while the identity lock is held; fsync the
   directory; and
8. remove temporary files on every exception and fail closed.

The identity lock serializes cooperating concurrent publishers. A publisher
that cannot acquire or validate it fails with `CONCURRENCY_CONFLICT`; it must
not silently overwrite a completed record. On restart, only a valid completed
final file is reusable. Stale temporary files are ignored for evidence and may
be removed only after validating they are regular files under the shadow root.

Artifacts containing `MATCH`, `MISMATCH`, or `FAILED` are immutable completed
evidence. Retrying the same sealed input therefore reuses its identical result;
a new source input or expected projection receives a new identity rather than
rewriting history.

## 9. Security and Protected Dependencies

Phase 08 modules may import only standard-library facilities, the explicit
Master Engine V4 decision/pre-delivery dependencies required by the injected
composition, and Phase 07 pure validators/observer functions for serialized
lifecycle comparison. They must not import:

- `ccxt`, exchange SDKs, Binance clients, trading API clients, or private
  endpoint wrappers;
- account, wallet, balance, portfolio, position, order, execution, or broker
  modules;
- Telegram transport/runtime/SDK modules or Telegram state/ledger code;
- `engine.replay_runner_v4` or replay artifact publishers;
- Phase 07 artifact publishers; or
- production evidence savers, default Master Engine savers, worker writers, or
  quota-state writers.

The source must contain no calls or names for order placement/submission/
cancellation, exchange credentials or API secrets, private keys, position
sizing, virtual balance, realized or unrealized P&L, equity curves, portfolio
returns, account mutation, or Telegram ledger mutation.

The runner calls `run_master_engine_v4` only with every provider and saver
explicitly injected. Calling it with defaults is prohibited because defaults
write live production roots and may call live data providers. Shadow execution
must not call `scan_market`, `get_closed_ohlcv_for_pre_delivery`, or any live
provider directly.

## 10. Release-Readiness Gate

The future immutable progress builder derives, never accepts, readiness from
completed run artifacts. For an enabled mode set in canonical `SWING`,
`INTRADAY`, `SCALP` order, `shadow_release_readiness` is true only if all of
the following are true:

```text
successful_match_total >= 100
successful_match_count_by_enabled_mode >= 30 for every enabled mode
unique_evaluation_cycles_by_enabled_mode >= 30 for every enabled mode
observed_runtime_span_days >= 14
mismatch_count == 0
critical_defect_count == 0
evidence_incomplete_count == 0
```

`observed_runtime_span_days` is the integer floor of the interval from the
earliest successful source `evaluation_completed_at` to the latest successful
one, measured in UTC. It is not wall-clock process runtime. `NO_TRADE` cycles
count toward evaluation-cycle coverage but not toward successful published
shadow runs. A duplicate identity counts once. A `FAILED` run never counts as
a match; a `MISMATCH`, root-isolation violation, nondeterminism finding, or
attempted forbidden mutation is critical.

This gate produces a reviewable audit state only. It expressly does not grant
capital exposure, trading permissions, simulated brokerage, or production
deployment authority.

## 11. Smallest Authorized Implementation Surface

The first implementation must add only the following Phase 08 modules and
their direct tests:

```text
engine/shadow_release_contract_v1.py
engine/shadow_release_runner_v1.py
engine/shadow_release_artifact_v1.py
engine/shadow_release_progress_v1.py

tests/test_shadow_release_contract_v1.py
tests/test_shadow_release_runner_v1.py
tests/test_shadow_release_artifact_v1.py
tests/test_shadow_release_progress_v1.py
```

- `contract` validates exact envelope shapes, canonical JSON, identities,
  hashes, timestamps, mode/market identity, and failure classes.
- `runner` performs only injected-provider Master Engine composition and exact
  semantic comparison; it never opens a network connection or defaults to a
  production writer.
- `artifact` publishes immutable canonical run/progress evidence under the
  isolated root with the rules in Section 8.
- `progress` deduplicates completed runs, calculates coverage and defects, and
  derives the Section 10 gate.

No changes to `master_engine_v4`, Telegram modules, Replay modules, Paper
Signal modules, lifecycle modules, or production artifact modules are
authorized by this design. The future production-side serialized-capture
adapter is a separate, owner-approved integration change once the official
publisher authority exists; it is deliberately outside this first surface.

## 12. RED/GREEN Commit Plan

The implementation sequence is intentionally narrow and reviewable:

1. **RED — Shadow contract tests:** add only
   `tests/test_shadow_release_contract_v1.py`, asserting exact classification,
   identity, source authority, canonical hashes, NO-TRADE behavior, and
   rejection of hidden/unknown fields. Commit only after it fails because the
   reserved module is absent.
2. **GREEN — Shadow contract:** add only
   `engine/shadow_release_contract_v1.py`; make the RED suite pass.
3. **RED — Runner/comparison tests:** add only
   `tests/test_shadow_release_runner_v1.py`, using serialized fixtures and
   injected dependencies to cover exact match, every mismatch class,
   nondeterminism, Phase 07 lifecycle comparison, and proof that no default
   production dependency is called.
4. **GREEN — Runner:** add only `engine/shadow_release_runner_v1.py`; make the
   runner suite pass without changing existing modules.
5. **RED — Artifact tests:** add only
   `tests/test_shadow_release_artifact_v1.py`, covering canonical bytes,
   atomic publication, symlink/protected-root rejection, collision,
   idempotent reuse, cleanup, restart, and concurrent identity locking.
6. **GREEN — Artifact publisher:** add only
   `engine/shadow_release_artifact_v1.py`; make the artifact suite pass.
7. **RED — Progress/gate tests:** add only
   `tests/test_shadow_release_progress_v1.py`, asserting deduplication,
   per-mode and duration gates, NO-TRADE coverage, mismatch/critical blocks,
   and the non-authorization statement.
8. **GREEN — Progress:** add only `engine/shadow_release_progress_v1.py`; make
   the progress suite pass.
9. **Closure audit:** run the new focused tests, the Phase 07 regression suite,
   and the full canonical suite; audit imports, forbidden semantics, output
   roots, immutable baseline files, and clean diff before any later integration
   proposal.

Every RED commit must contain no production implementation. Every GREEN commit
must be confined to the corresponding reserved module and any necessary direct
test correction. Any need to alter an immutable Phase 07 contract, the live
publisher, or a protected production surface blocks this plan pending a new
design amendment and owner approval.

## 13. Design Lock

This document freezes Phase 08 Step 02 semantics. In particular, it freezes
the distinction between sealed production-path comparison and both Paper
Signal observation and replay. It also records the current missing official
publication capture as a fail-closed integration prerequisite.

No implementation may reinterpret that prerequisite as permission to create
synthetic `signal_id`/`delivery_id` values, to observe a mutable latest file,
or to add a capital capability.
