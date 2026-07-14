# PHASE 06 — REPLAY FRAMEWORK — DESIGN FREEZE

## Status

DESIGN FROZEN — AMENDED; IMPLEMENTATION REQUIRES RED CHARACTERIZATION

## 1. Phase Identity

- Phase: Phase 06 — Replay Framework
- Starting baseline: `3433bd8 feat: add Telegram SDK polling runner`
- Canonical regression baseline: `356 passed`
- Repository: `/home/akbar/projects/ai-crypto-signal-agent`
- Branch: `master`

### Phase Objective

Provide deterministic, network-isolated replay of the canonical
master-engine flow from a versioned recorded input bundle, producing
isolated and comparable replay artifacts without mutating production,
worker, quota, Telegram, delivery, or evidence state.

## Authorized Roadmap Amendment

The locked Phase 05 checkpoint identified “Phase 06 — Production
Deployment & Service Integration” as the anticipated next phase.

The Project Owner has subsequently issued an explicit roadmap amendment
selecting “Phase 06 — Replay Framework” as the authorized Phase 06 scope.

This owner instruction supersedes the checkpoint’s previously named
next-phase title for sequencing purposes only. It does not unlock,
modify, or weaken any Phase 00–05 production, scanner, validation,
stateful-worker, quota-slot, Telegram, delivery, evidence, forward-test,
or live-trading contract.

Production Deployment & Service Integration is deferred to a later
separately authorized phase. Phase 06 is limited to the deterministic,
network-isolated Replay Framework contract defined in this document.

## 3. Replay Classification

The initial Phase 06 classification is locked as:

**Deterministic master-engine replay from recorded boundary inputs.**

The replay begins after live scanner market acquisition. The initial
replay bundle contains recorded scanner-result rows and supplies those
rows through a deterministic scanner-compatible provider.

The replay executes the real validation, ranking, artifact,
pre-delivery, and evidence orchestration required by the canonical
master-engine path. It does not substitute a precomputed final pipeline
result for those semantics.

The initial replay is not:

- a raw OHLCV scanner replay;
- an end-to-end historical market reconstruction;
- proof that a live scan can be reproduced from the available repository
  snapshots.

Raw scanner replay requires a separately authorized phase or design-freeze
amendment with complete recorded market-data inputs and proven
scanner-provider seams.

## 4. Canonical Execution Boundary

The required execution path is:

```text
run_replay_v4(...)
    ↓
run_master_engine_v4(...)
    ↓
canonical validation, ranking, artifact, pre-delivery,
delivery-data, and evidence semantics
```

`run_replay_v4()` must invoke the real `run_master_engine_v4()` exactly
once per accepted replay execution. Replay tests and implementation must
not replace, stub, or mock away the master engine itself.

Recorded scanner-result input is supplied through a deterministic
zero-argument scanner-compatible provider. This preserves the existing
master-engine scanner call contract while preventing live scanner market
acquisition.

Replay must not invoke:

- `run_stateful_worker_v4()` or
  `run_master_engine_worker_v4()`;
- `run_quota_slot_worker_v4()`;
- the Telegram application, transport, runtime, or SDK runner.

Replay must not acquire, reserve, release, read, or write quota state. It
must not create or mutate stateful-worker lifecycle state.

The stateful worker and quota-slot wrapper remain the canonical
operational boundaries for their existing production callers. Their
exclusion from offline replay prevents replay attempts from being
misclassified as production worker attempts or consuming production
admission state.

## 5. Versioned Replay Bundle Contract

The only executable Replay V4 bundle contract is **schema version 2**.
The committed schema version 1 is retained as historical evidence of the
initial contract, but it is legacy and non-executable because it cannot
represent the complete master-engine boundary. Corrected validation and
execution must reject version 1 rather than silently reinterpret it as
version 2.

The minimum schema-version-2 replay bundle contains:

- `schema_version`;
- `fixture_id`;
- replay-ID derivation inputs;
- `source_commit`;
- `recorded_at`;
- `fixed_execution_time`;
- `execution_configuration`;
- `scanner_results`;
- `recorded_open_interest`;
- `recorded_validator_response`;
- `recorded_validator_usage`, when applicable;
- `pre_delivery_closed_candles`;
- expected semantic-contract metadata;
- an optional expected normalized-result hash.

The corrected replay-contract implementation must freeze the exact
schema-version-2 JSON shape before the runner is implemented. The schema
must distinguish source metadata, deterministic execution inputs, and
optional comparison expectations.

Each recorded scanner-result row must represent the complete post-scanner
boundary consumed by the real master-engine validation and downstream
artifact flow. The exact schema must include at least:

- `symbol`;
- `score`;
- `direction`;
- `entry`;
- `stop_loss`;
- `take_profit`;
- `reference_price`;
- `reference_candle_at`;
- `golden_zone`;
- `trend`;
- `bos`;
- `choch`;
- `volume_ratio`;
- `volume_v2_status`.

Recorded scanner values preserve their existing production meanings and
must not be recalculated during replay. `golden_zone` must preserve the
complete existing structure required by pre-delivery and Pine consumers,
including its direction, swing identities and timestamps, levels, entry
zone, take-profit data, and stop-loss data. Phase 06 does not define a
simplified Golden Zone representation.

Unknown scanner-row fields fail closed unless an exact schema amendment
authorizes them. Applicable timestamps must be deterministic and
timezone-aware. Numeric values must be finite, and booleans must not be
accepted as numbers. Replay normalization orders scanner rows by score
descending and symbol ascending as a replay-only deterministic tie rule;
it does not change scanner production ordering or concurrency behavior.

`recorded_open_interest` is required validation-time provider input. It
must contain exactly one entry for every scanner symbol and no extra
symbols. Each entry records finite `current_oi`, `previous_oi`, and
`oi_change_pct` audit values together with the production-compatible
`oi_score` and `data_status` fields consumed by
`build_validation_candidate_v2()`. The schema must use the existing
provider field names for the values passed into candidate construction;
an adapter must not invent a second status vocabulary.

Recorded OI is not scanner OHLCV replay. It must pass through the real
`classify_participation()` semantics. The replay bundle must not inject
`volume_class`, `oi_class`, `participation`, or another final candidate
classification in place of those calculations.

The recorded validator response must contain production-compatible
validation entries for the actual replay candidates. It supplies the
`content` parsed by the real pipeline; it does not supply controlled rows,
ranking results, or a final Top-5 result. Recorded usage may include the
complete current provider shape:

- `prompt_tokens`;
- `completion_tokens`;
- `total_tokens`;
- `cache_hit_tokens`;
- `cache_miss_tokens`.

Every supplied usage value must be a non-negative, non-boolean integer.
`total_tokens` must follow the current production provider contract.
Optional cache fields must follow the current provider's absent-field
normalization and must not be guessed from other token counts. Recorded
validator content and usage must be internally consistent with the exact
candidate set and provider result contract.

The following bundle rules are locked:

- The bundle is immutable during execution.
- Validation completes before any output directory or file is created or
  changed.
- Unknown or incompatible schema versions fail closed.
- Missing required fields fail closed.
- Malformed field types, scanner rows, validator payloads, candle records,
  timestamps, or identity fields fail closed.
- Secret values are prohibited.
- Live provider credentials, API keys, bot tokens, and authorization
  material are prohibited.
- Production paths are prohibited.
- Bundle identity is deterministic and content-derived.
- UUIDs and wall-clock-generated replay identity are prohibited.
- A supplied identity must match its deterministic derivation or fail
  closed.
- Scanner-symbol coverage across recorded OI, validator entries, and
  pre-delivery candles must be exact and internally consistent.
- Missing recorded OI or validator data must never cause a live provider
  fallback.

The source bundle bytes must not be rewritten, normalized in place, or
otherwise mutated by loading, validation, execution, or comparison.

## 6. Determinism Contract

One fixed replay clock governs the complete replay run. Every replay
timestamp, generated-at value, validated-at value, output identity, and
filename must derive from the frozen replay contract.

The replay framework must provide:

- stable canonical input ordering;
- explicit deterministic behavior for equal-score ties;
- canonical JSON serialization;
- stable semantic hashing;
- deterministic replay filenames;
- deterministic replay output-directory identity;
- identical normalized results for identical valid inputs;
- byte-stable source fixtures;
- stable comparison behavior and mismatch ordering.

Input scanner-result ordering is part of the replay contract. Equal-score
rows must use an explicitly frozen deterministic tie rule or a validated
recorded order. Replay must not inherit concurrent completion order as an
implicit tie breaker.

Repeated execution of the same valid bundle and configuration must not:

- create duplicate timestamp directories;
- create additional semantically equivalent artifacts;
- append nondeterministic identifiers;
- change normalized results or semantic hashes;
- modify the source fixture.

Timestamp normalization, replay identities, directories, and filenames
must never derive from `datetime.now()`, `time.time()`, `uuid4()`, process
timing, concurrent completion timing, or another ambient runtime source.

## 7. Network-Isolation Contract

Replay execution must prove that it does not access:

- Binance;
- CCXT;
- DeepSeek;
- OpenAI;
- Telegram;
- HTTP clients;
- WebSocket clients;
- DNS or arbitrary network sockets;
- live market-data providers;
- live validator providers.

The recorded validator response must be consumed exactly through an
explicit, default-preserving validator injection seam. The production
default remains unchanged for non-replay callers.

Validation-time open-interest input must be consumed through an explicit,
default-preserving provider seam. Replay must not call Binance or HTTP for
OI data, and missing or invalid recorded OI must fail closed without an
ambient-provider fallback. The recorded provider supplies raw
production-compatible OI metrics; real candidate construction and
`classify_participation()` remain authoritative.

Module-level monkeypatching is permitted in characterization tests only.
It is prohibited as the production replay execution mechanism.

Missing, malformed, incomplete, or incompatible recorded input must fail
closed. No live fallback, network retry, credential lookup, or provider
construction is allowed.

## 8. Filesystem and State Isolation

Replay requires a caller-supplied replay output root. Every output must
remain beneath a replay-only directory derived deterministically from that
root and the replay identity.

Replay must not write to existing production artifact directories or to:

- quota state;
- worker state;
- latest production files;
- TradingView production artifacts;
- Pine production artifacts;
- forward-test artifacts;
- production evidence directories;
- Telegram configuration or state.

Invalid bundles, invalid output roots, identity mismatches, and prohibited
path collisions must fail before any write or directory creation.

Files produced by replay must use atomic writes. A partial-output failure
must not expose a completed replay manifest or successful replay state.
Temporary output must be cleaned up or left unmistakably incomplete and
must never be presented as a successful run.

Every replay artifact and manifest must carry an explicit replay
classification. Replay outputs must not be named, formatted, or located in
a manner that could reasonably be mistaken for production evidence,
forward-test evidence, or live delivery output.

## 9. Allowed Phase 06 and Compatibility Files

The new or revised Phase 06 file surface is locked to:

- `engine/replay_contract_v4.py`
- `engine/replay_runner_v4.py`
- `engine/replay_artifact_v4.py`
- `tests/test_replay_contract_v4.py`
- `tests/test_replay_runner_v4.py`
- `tests/test_replay_artifact_v4.py`
- `tests/fixtures/replay_v4/`

The only existing production compatibility files authorized are:

- `engine/validation_payload_v2.py`;
- `engine/validated_pipeline_v4.py`;
- `engine/pre_delivery_flow_v4.py`;
- `engine/top5_watchlist_artifact_v4.py`.

No other new file or existing production-module change is authorized
without another documented design-freeze amendment. In particular,
`engine/master_engine_v4.py` requires no signature or sequencing change;
its existing outer scanner, pipeline, saver, pre-delivery, evidence, and
clock dependency seams are sufficient.

Modification remains explicitly prohibited for:

- `engine/scanner.py` and scanner helpers;
- `engine/stateful_worker_v4.py`;
- `engine/quota_slot_worker_v4.py` and quota-slot core;
- Telegram application, transport, runtime, and SDK modules;
- `engine/production_evidence_v4.py`;
- forward-test modules;
- live-trading or exchange-execution modules.

## 10. Conditional Compatibility Changes

Only the following default-preserving compatibility seams, backed by RED
characterization tests, may be added.

`engine/validation_payload_v2.py` may change only to support:

```python
build_validation_candidate_v2(
    candidate,
    *,
    oi_provider=None,
)
```

`engine/validated_pipeline_v4.py` may pass that dependency through and
accept the recorded validator provider through:

```python
build_validation_payload_v4(
    results,
    *,
    oi_provider=None,
)

run_validated_pipeline_v4(
    results,
    *,
    validator=None,
    oi_provider=None,
)
```

When omitted, `oi_provider` and `validator` must resolve the existing
module-global live defaults at call time. Existing callers and
monkeypatch-based tests must remain compatible. The real candidate
builder, participation classifier, validator parser, normalization,
validation control, semantic guard, ranking, and final Top-5 selection
must execute. Provider exceptions retain existing propagation behavior.
No final candidate, controlled result, or final pipeline result may be
injected.

`engine/pre_delivery_flow_v4.py` may accept only the smallest saver seams
needed for isolated output, conceptually:

```python
run_pre_delivery_flow(
    ...,
    delivery_artifact_saver=None,
    tradingview_exporter=None,
    pine_delivery_saver=None,
)
```

Exact names must follow repository conventions at implementation time.
Omitted dependencies resolve the current production functions at call
time and preserve current production paths. Existing step order remains
unchanged. Real lifecycle and supersession logic execute with the
recorded closed-candle provider. Saver failures propagate, and no later
saver may run after an earlier saver fails.

`engine/top5_watchlist_artifact_v4.py` may accept only a fixed-clock
builder seam, conceptually:

```python
build_top5_watchlist_artifact(
    final_top5,
    *,
    now_provider=None,
)
```

The omitted clock preserves current ambient production behavior. Replay
injects a clock derived from `ReplayBundleV4.fixed_execution_time` so
`generated_at` is deterministic. Formatting, fields, and path-writing
behavior remain unchanged, and no replay branch may be added to the
builder.

Each compatibility change must:

- preserve the current live default;
- remain backward compatible;
- be isolated in its own commit;
- add no replay-specific branching to unrelated production logic;
- avoid duplicating production orchestration;
- introduce only explicit dependency, clock, saver, or output-root seams;
- retain existing public behavior when the new optional seam is not used.
- resolve optional production dependencies at call time so existing
  module-global monkeypatch seams continue to work.

No scanner provider refactor is authorized in the initial Phase 06 scope.
The master engine's existing scanner-callable seam is sufficient for the
recorded scanner-result classification locked by this phase.

## 11. Protected Boundaries

The following are locked unchanged:

- scanner calculations and thresholds;
- scanner concurrency behavior;
- scanner output field meaning;
- semantic validation rules;
- ranking rules;
- master-engine step order;
- stateful-worker lifecycle schema;
- quota accounting and slot behavior;
- Telegram commands and identity contract;
- pre-delivery eligibility semantics;
- TradingView and Pine formatting semantics;
- production evidence meaning;
- forward-test meaning;
- live-trading authorization boundaries.

Replay compatibility work must not change trading logic, scoring,
thresholds, rejection behavior, validation decisions, delivery eligibility,
artifact field meaning, or production exception behavior.

## 12. Required Failure Behavior

Replay must fail closed for:

- invalid schema;
- missing bundle fields;
- unsupported schema version;
- legacy schema version 1 presented for execution;
- malformed scanner rows;
- missing, malformed, or symbol-incomplete recorded OI;
- invalid recorded validator response;
- missing pre-delivery candles;
- output-root collision with prohibited paths;
- semantic-hash mismatch;
- replay-identity mismatch;
- attempted live provider access;
- attempted production-path write;
- partial output failure.

Validation and isolation failures must expose stable replay-level reason
codes without leaking secrets, credentials, unrestricted exception
representations, or production filesystem details.

No retry is required in Phase 06. No fallback to live providers is
permitted. No partial replay output may be presented as a successful
completed run.

## 13. Required Test Matrix

Phase 06 tests must prove:

1. missing-module RED evidence before implementation;
2. bundle-schema validation;
3. unsupported-version rejection;
4. corruption rejection;
5. import safety;
6. no network calls;
7. no live validator construction;
8. recorded validator response is consumed exactly once;
9. recorded pre-delivery candles are consumed;
10. the real master engine is invoked exactly once;
11. real validation control is exercised;
12. the real semantic guard is exercised;
13. the master engine is not mocked away;
14. no stateful-worker call occurs;
15. no quota-slot call occurs;
16. no Telegram call occurs;
17. no production path is mutated;
18. no source fixture is mutated;
19. replay identity is deterministic;
20. filenames are deterministic;
21. normalized results are deterministic;
22. semantic hashing is stable;
23. repeated execution is idempotent;
24. duplicate replay artifacts are not created;
25. equal-score ordering behavior is explicit and deterministic;
26. semantic mismatches are reported exactly and deterministically;
27. schema version 1 is not silently accepted as the corrected complete
    replay boundary;
28. schema version 2 contains complete pipeline-compatible scanner rows;
29. recorded OI has exact scanner-symbol coverage;
30. the recorded OI provider drives the real participation classifier;
31. recorded validator content covers the actual candidates;
32. cache usage metadata follows the current provider contract;
33. omitted dependencies preserve current live provider behavior;
34. injected providers are called exactly once according to the real flow;
35. provider exceptions propagate unchanged;
36. injected pre-delivery savers preserve existing order;
37. saver failure prevents every later saver invocation;
38. the fixed clock controls replay-visible Top-5 generation time;
39. no live network method or socket is called;
40. `run_master_engine_v4()` remains unchanged and is invoked exactly once
    by the future replay runner;
41. the full canonical regression remains green.

The integration tests must exercise the real master-engine orchestration,
real validation control, real semantic guard, and real pre-delivery
semantics. Tests may inject only boundary data providers, clocks, output
destinations, and external-response providers necessary for determinism and
isolation.

Tests must not claim integration coverage by replacing the master engine,
returning a precomputed final pipeline result, or monkeypatching away all
canonical logic.

## 14. Non-Goals

Phase 06 explicitly prohibits:

- raw OHLCV scanner replay;
- full historical market reconstruction;
- scanner provider refactoring;
- backtesting;
- strategy optimization;
- profitability measurement;
- forward-outcome resolution;
- live market-data access;
- live DeepSeek or OpenAI access;
- quota or load testing;
- stateful-worker replay;
- Telegram replay;
- production deployment;
- scheduling;
- background queues;
- retries;
- databases;
- distributed replay;
- automatic trading;
- exchange order execution;
- treating replay output as production evidence.

## 15. Commit Plan

The amended Phase 06 commit sequence is locked as:

1. `docs: freeze replay framework design`
2. `feat: add replay bundle contract`
3. `docs: amend replay boundary compatibility`
4. `test: characterize replay provider seams`
5. `refactor: inject validation replay providers`
6. `refactor: inject replay-safe delivery seams`
7. `feat: correct replay bundle boundary contract`
8. `test: define master engine replay orchestration`
9. `feat: add deterministic replay runner`
10. `test: lock replay isolation and idempotency`
11. `feat: add replay artifact comparison`

Commits 1 and 2 already exist as:

- `10dbb12 docs: freeze replay framework design`;
- `d36963b feat: add replay bundle contract`.

The corrected bundle commit must preserve schema-version governance and
default behavior outside replay. It changes the executable schema to
version 2. Version 1 remains legacy and non-executable and must be
rejected by corrected execution validation. No implementation may
silently reinterpret a version-1 payload as version 2.

The final checkpoint PDF is not a repository commit unless separately
authorized by the Project Owner.

## 16. Phase Lock Criteria

Phase 06 may lock only when:

- replay-bundle schema version 2 is frozen as the only executable
  boundary and version 1 is rejected as legacy/non-executable;
- scanner rows, recorded OI, validator content, validator usage, and
  candle coverage are complete and mutually consistent;
- `run_replay_v4()` invokes the real master engine exactly once;
- real validation and pre-delivery semantics execute;
- replay execution is network-isolated;
- no live provider fallback exists;
- no worker, quota, Telegram, or production state changes;
- invalid bundles fail before output mutation;
- identical runs produce identical normalized results and semantic hashes;
- repeated runs do not create duplicate artifacts;
- replay output is visibly distinct from production evidence;
- raw scanner replay is not claimed;
- focused tests pass;
- the canonical regression passes;
- the repository is clean;
- the commit chain is linear;
- `HEAD`, `origin/master`, and `origin/HEAD` are synchronized;
- adversarial and final compliance audits return PASS.

## 17. Documented Limitations

- Existing repository snapshots do not contain sufficient raw market inputs
  for truthful scanner replay.
- Initial Phase 06 begins from recorded scanner-result rows.
- The committed schema version 1 contract is incomplete for the actual
  pipeline and is retained only as legacy development history; it is not
  executable replay input.
- Validation-time OI is a separate recorded provider input and does not
  make Phase 06 a raw scanner or OHLCV replay.
- Replay equivalence applies only to the frozen replay boundary.
- Replay does not prove live-market reproducibility.
- Replay does not measure trading performance.
- Replay does not grant production or live-trading authorization.

These limitations are part of the public replay contract and must remain
visible in replay manifests, operator documentation, and compliance review.

## 18. Replay Boundary Compatibility Amendment

The Step 07 deterministic provider-seam audit compared the committed
Replay V4 bundle contract with the real master-engine, validation-payload,
validated-pipeline, pre-delivery, Top-5, and evidence boundaries. It found
that schema version 1 could not represent a complete executable replay:
its scanner rows omitted required pipeline and Golden Zone fields, it had
no validation-time OI provider input, and its recorded validator response
and usage did not match the candidates and complete provider result shape.

This amendment corrects Phase 06 replay input completeness. It does not
expand Phase 06 into raw OHLCV scanner replay, alter scanner calculations,
or change master-engine sequencing. It does not authorize stateful-worker,
quota-slot, Telegram, deployment, forward-test, production-evidence, or
live-trading changes. Existing Phase 00–05 behavior remains protected.

The committed Replay V4 contract implementation, tests, and fixture must
be revised in a separately reviewed compatibility commit. That correction
must implement schema version 2 as the only executable replay contract.
Schema version 1 is legacy/non-executable and must be rejected rather than
silently upgraded or reinterpreted.

### 18.1 Complete Recorded Scanner Boundary

Schema version 2 records the complete post-scanner boundary consumed by
the real master-engine flow. At minimum each row contains `symbol`,
`score`, `direction`, `entry`, `stop_loss`, `take_profit`,
`reference_price`, `reference_candle_at`, `golden_zone`, `trend`, `bos`,
`choch`, `volume_ratio`, and `volume_v2_status`.

The exact scanner-row schema is closed. Unknown fields fail unless a later
schema amendment authorizes them. Values retain existing production
meanings and are not recomputed. Relevant timestamps are deterministic and
timezone-aware, numeric values are finite with booleans rejected, and
replay-only normalization is score descending then symbol ascending.

The complete existing Golden Zone structure required by pre-delivery and
Pine consumers must be preserved. This amendment does not define or permit
a simplified replacement.

### 18.2 Recorded Validation-Time Open Interest

Schema version 2 requires `recorded_open_interest` with exactly one entry
per scanner symbol and no additional symbols. Each entry preserves finite
`current_oi`, `previous_oi`, and `oi_change_pct` audit values and the
production-compatible `oi_score` and `data_status` values exposed to the
existing candidate builder.

The provider is called deterministically according to existing candidate
construction. No Binance, HTTP, ambient-provider, retry, or fallback path
is permitted. Recorded OI passes through real
`classify_participation()` semantics; a final participation classification
must not be injected. Missing or malformed OI fails before replay output
mutation. This is recorded validation-time provider input, not scanner
OHLCV replay.

### 18.3 Recorded Validator Compatibility

Recorded validator content must contain entries for the actual replay
candidates and retain the production content shape consumed by the real
parser. Real reason normalization, semantic consistency checks, validation
control, ranking, and final Top-5 construction must execute. A final
validated result may not be injected.

When recorded usage is present it may include `prompt_tokens`,
`completion_tokens`, `total_tokens`, `cache_hit_tokens`, and
`cache_miss_tokens`. Values are non-negative, non-boolean integers,
`total_tokens` follows the actual provider contract, and absent optional
cache fields follow current production normalization rather than guessed
values. Live DeepSeek or OpenAI fallback remains prohibited.

### 18.4 Authorized Default-Preserving Seams

The amendment narrowly authorizes:

- `engine/validation_payload_v2.py` for an optional call-time
  `oi_provider` in `build_validation_candidate_v2()`;
- `engine/validated_pipeline_v4.py` for optional call-time `validator`
  and `oi_provider` pass-through;
- `engine/pre_delivery_flow_v4.py` for call-time delivery-artifact,
  TradingView-exporter, and Pine-delivery saver dependencies;
- `engine/top5_watchlist_artifact_v4.py` for a call-time `now_provider`
  used only by the pure Top-5 builder.

Omitted dependencies preserve current module-global production defaults,
paths, exception behavior, and monkeypatch compatibility. No replay branch,
final-result injection, scanner change, caching, retry, or fallback is
authorized.

`engine/master_engine_v4.py` requires no change. Its existing outer
dependency seams compose the recorded scanner provider, recorded validator
and OI pipeline, recorded candle provider, fixed clock, replay-only savers,
and replay evidence dependency while retaining the real master-engine call
and step order.

### 18.5 Replay Artifact and Evidence Classification

Replay must not call `save_production_evidence()`. The master-engine
evidence call point remains exercised through an injected replay-only
dependency classified exactly as:

```text
classification = "REPLAY"
boundary = "MASTER_ENGINE_RECORDED_INPUT"
```

Replay output uses a deterministic replay identity beneath a
caller-supplied replay root. It must not use `production_run_v4` naming,
production evidence directory structures or manifests, production
`latest.json` aliases, or any location that could be mistaken for
production evidence. Publication occurs only after successful execution
and semantic verification, and every manifest states explicitly that the
output is not production evidence.

### 18.6 Amendment Resolution and Remaining Exclusions

This amendment resolves the incomplete scanner-row schema, missing
validation-time OI, incomplete validator response and usage contract,
previously unauthorized validation-payload seam, incomplete Golden Zone
contract, pre-delivery saver authorization, and Top-5 fixed-clock
authorization.

It does not authorize raw scanner replay, historical OHLCV reconstruction,
scanner refactoring, general atomic hardening of production savers, lazy
scanner or CCXT import redesign, production deployment, stateful-worker
replay, quota replay, Telegram replay, forward-test execution, automatic
trading, or exchange order execution.
