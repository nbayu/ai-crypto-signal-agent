# PHASE 03 — STATEFUL WORKERS DESIGN FREEZE

## Status

DESIGN FREEZE DRAFT

## Baseline

Phase 03 starts from locked Phase 02 baseline:

- Commit: fbc2fa0 docs: document master engine boundary
- Branch: master
- Regression baseline: 188 passed
- Repository state: clean
- Master engine entrypoint: engine.master_engine_v4.run_master_engine_v4()

## Roadmap Scope

Phase 03 implements Stateful Workers only.

It must not implement:

- Phase 04 quota or slot allocation
- Phase 05 Telegram interface
- Scheduling daemon behavior
- Live trading execution
- Strategy scoring changes
- Scanner behavior changes
- Golden Zone calculation changes
- Pre-delivery semantic changes
- Forward test semantic changes

## Design Goal

Introduce a minimal stateful worker layer that records each master engine execution lifecycle in a durable JSON ledger.

The worker state layer exists to support future operator interfaces, schedulers, quota engines, and Telegram command routing without duplicating master engine orchestration.

## Canonical Worker State

A worker run may have one of the following states:

- STARTED
- COMPLETED
- FAILED

## Canonical Worker Event Schema

Each worker event must be a JSON object with the following keys:

- schema_version
- worker_name
- run_id
- state
- started_at
- completed_at
- failed_at
- error
- artifacts

## Required Worker Name

The initial worker name is:

- master_engine_v4

## Storage Boundary

Worker state must be stored under:

- data/worker_state_v4/

The first implementation may write:

- data/worker_state_v4/master_engine_v4_latest.json

Future append-only history may be added only by explicit later phase or RFC.

## Atomic Write Requirement

Worker state writes must be atomic:

1. write to a temporary file;
2. replace the target file with the completed temporary file.

A partially written state file is invalid.

## Master Engine Boundary

The worker must call the existing canonical Phase 02 entrypoint:

- run_master_engine_v4()

The worker must not reimplement:

- scan_market
- run_validated_pipeline_v4
- snapshot saving
- outcome saving
- raw Top 5 saving
- pre-delivery flow
- production evidence saving

## Artifact Capture

On success, the worker state must capture paths returned by run_master_engine_v4():

- snapshot_path
- outcome_path
- watchlist_path
- evidence_path
- delivery_artifact_path
- tradingview_watchlist_path
- pine_bridge_artifact_path
- pine_delivery_payload_path

Paths must be serialized as strings.

## Failure Capture

On failure, the worker state must capture:

- state: FAILED
- failed_at
- error type
- error message

The original exception must be re-raised after the FAILED state is written.

## Import Safety

Importing the worker module must not:

- run the scanner
- call DeepSeek
- write artifacts
- access Binance
- execute master engine
- write worker state

## Test Requirements

Focused tests must prove:

1. worker writes STARTED then COMPLETED on success;
2. worker captures artifact paths from master engine output;
3. worker writes FAILED and re-raises on exception;
4. worker state write is atomic;
5. importing the worker module has no side effects;
6. existing master engine regression remains green.

## Lock Boundary

Phase 03 is locked only when:

- focused worker tests pass;
- canonical regression passes;
- master engine orchestration order remains unchanged;
- repository is clean after commit and push;
- checkpoint PDF is created.

