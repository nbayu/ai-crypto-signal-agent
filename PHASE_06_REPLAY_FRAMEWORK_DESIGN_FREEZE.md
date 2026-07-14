# PHASE 06 — REPLAY FRAMEWORK — DESIGN FREEZE

## Status

DESIGN FROZEN — IMPLEMENTATION NOT YET AUTHORIZED

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

The minimum conceptual replay bundle contains:

- `schema_version`;
- `fixture_id`;
- replay-ID derivation inputs;
- `source_commit`;
- `recorded_at`;
- `fixed_execution_time`;
- `execution_configuration`;
- `scanner_results`;
- `recorded_validator_response`;
- `recorded_validator_usage`, when applicable;
- `pre_delivery_closed_candles`;
- expected semantic-contract metadata;
- an optional expected normalized-result hash.

The implementation design must freeze an exact JSON schema before the
runner is implemented. The schema must distinguish source metadata,
deterministic execution inputs, and optional comparison expectations.

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

## 9. Allowed New Files

The planned Phase 06 file surface is locked to:

- `engine/replay_contract_v4.py`
- `engine/replay_runner_v4.py`
- `engine/replay_artifact_v4.py`
- `tests/test_replay_contract_v4.py`
- `tests/test_replay_runner_v4.py`
- `tests/test_replay_artifact_v4.py`
- `tests/fixtures/replay_v4/`

Additional new files require a documented design-freeze amendment before
implementation.

## 10. Conditional Compatibility Changes

Only default-preserving compatibility seams, backed by characterization
tests, may be added to:

- `engine/validated_pipeline_v4.py`;
- artifact saver modules directly used by `run_master_engine_v4()`;
- pre-delivery modules directly used by `run_master_engine_v4()`;
- production-evidence composition dependencies directly required for
  isolated replay output.

Each compatibility change must:

- preserve the current live default;
- remain backward compatible;
- be isolated in its own commit;
- add no replay-specific branching to unrelated production logic;
- avoid duplicating production orchestration;
- introduce only explicit dependency, clock, saver, or output-root seams;
- retain existing public behavior when the new optional seam is not used.

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
- malformed scanner rows;
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
27. the full canonical regression remains green.

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

The planned Phase 06 commit sequence is locked as:

1. `docs: freeze replay framework design`
2. `test: define replay bundle contract`
3. `feat: add replay bundle validation`
4. `test: characterize deterministic provider seams`
5. `refactor: add replay-safe dependency injection seams`
6. `test: define master engine replay orchestration`
7. `feat: add deterministic replay runner`
8. `test: lock replay isolation and idempotency`
9. `feat: add replay artifact comparison`

The final checkpoint PDF is not a repository commit unless separately
authorized by the Project Owner.

## 16. Phase Lock Criteria

Phase 06 may lock only when:

- the replay-bundle schema is versioned and frozen;
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
- Replay equivalence applies only to the frozen replay boundary.
- Replay does not prove live-market reproducibility.
- Replay does not measure trading performance.
- Replay does not grant production or live-trading authorization.

These limitations are part of the public replay contract and must remain
visible in replay manifests, operator documentation, and compliance review.
