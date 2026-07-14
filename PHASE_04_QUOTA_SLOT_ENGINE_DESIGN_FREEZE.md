# PHASE 04 — QUOTA & SLOT ENGINE — DESIGN FREEZE

## Status

DESIGN FROZEN — IMPLEMENTATION NOT YET AUTHORIZED

## Baseline

- Branch: `master`
- Starting commit: `8736672`
- Starting regression: `192 passed`
- Previous locked phase: Phase 03 — Stateful Workers
- Canonical worker entrypoint:
  `engine.stateful_worker_v4.run_master_engine_worker_v4`

## Purpose

Phase 04 introduces a small admission-control boundary in front of the
Phase 03 stateful worker.

The engine decides whether a requested worker execution may start based
on two independent controls:

1. quota availability;
2. concurrent slot availability.

It must not duplicate or reimplement master-engine, scanner, validation,
pre-delivery, evidence, or worker lifecycle behavior.

## Evidence Constraint

No existing repository document or implementation defines:

- production quota limits;
- production slot capacity;
- quota reset intervals;
- user, chat, account, or operator scope;
- subscription tiers;
- priority scheduling;
- queue behavior.

Therefore Phase 04 must not invent production policy values.

Quota limits, slot capacity, subject identity, and window identity must
be supplied explicitly by callers or injectable policy providers.

## Definitions

### Subject

A stable caller identity against which quota usage is measured.

Examples for future callers may include an operator, Telegram user,
service account, or system process.

Phase 04 does not define how those identities are authenticated.

### Quota Window

A caller-provided stable identifier representing the accounting period.

Examples may include:

- `2026-07-14`;
- `2026-W29`;
- a subscription billing period;
- an externally generated reset-window identifier.

Phase 04 does not calculate calendar or billing windows implicitly.

### Quota Limit

The maximum number of admitted worker executions for one subject within
one quota window.

The limit must be a positive integer supplied explicitly.

### Slot Capacity

The maximum number of simultaneous active worker executions.

The capacity must be a positive integer supplied explicitly.

### Admission

A request is admitted only when:

- its subject has remaining quota in the supplied window; and
- an active slot is available.

Both checks and the resulting state update must occur as one logical
state transition.

### Reservation

A successful admission creates one reservation containing:

- reservation ID;
- subject ID;
- window ID;
- acquired timestamp;
- reservation state.

The reservation is returned to the caller and may be used to release
the slot after worker completion or failure.

## Public Contract

Phase 04 will introduce a dedicated module:

`engine/quota_slot_engine_v4.py`

The intended public surface is:

- `QuotaSlotRejected`
- `read_quota_slot_state(...)`
- `write_quota_slot_state_atomic(...)`
- `acquire_quota_slot_v4(...)`
- `release_quota_slot_v4(...)`

Exact implementation signatures may be refined by tests, but the
behavioral contract in this document is locked.

## Durable State Boundary

Default state path:

`data/quota_slot_v4/quota_slot_state.json`

State schema version:

`1`

The durable state must contain enough information to determine:

- quota usage by subject and window;
- currently active reservations;
- released reservations when needed for deterministic/idempotent
  release behavior.

State writes must use a temporary sibling file followed by atomic
replacement.

Importing the module must not create directories, create files, acquire
slots, release slots, or execute the worker.

## Admission Result

Successful acquisition must return a structured result containing at
least:

- admitted: `true`;
- reservation ID;
- subject ID;
- window ID;
- quota limit;
- quota used;
- quota remaining;
- slot capacity;
- active slot count;
- state path.

Rejected acquisition must fail closed using `QuotaSlotRejected`.

The exception must expose a stable reason code.

Locked rejection reason codes:

- `QUOTA_EXHAUSTED`
- `SLOTS_FULL`
- `INVALID_POLICY`
- `INVALID_REQUEST`
- `STATE_CORRUPT`

Quota exhaustion and slot exhaustion must not invoke the Phase 03
worker.

## Quota Consumption Rule

Quota is consumed when admission succeeds and a reservation is created.

Quota is not refunded when the downstream worker later fails.

Reason:

The quota controls execution attempts and resource use, not successful
market results.

A rejected request does not consume quota.

## Slot Lifecycle

Reservation states:

- `ACTIVE`
- `RELEASED`

A successful acquisition creates an `ACTIVE` reservation.

Release changes that reservation to `RELEASED`.

Release must be idempotent:

- releasing an active reservation releases exactly one slot;
- releasing an already released reservation must not decrement slot
  usage again;
- releasing an unknown reservation must fail closed.

Worker success and worker failure must both result in release when a
future wrapper integrates the engine with the Phase 03 worker.

## Concurrency Boundary

Phase 04 provides durable accounting and logical admission control.

Cross-process locking is not automatically implied by atomic file
replacement alone.

The first implementation must either:

1. implement an explicit lock around read-modify-write; or
2. remain explicitly limited to a single controlling process.

The implementation must not claim multi-process safety unless it is
tested and proven.

## Failure Behavior

Malformed or incompatible state must fail closed.

The engine must not silently reset corrupted state.

Invalid limits, capacity, subject IDs, window IDs, or reservation IDs
must fail before state mutation.

A failed write must not report successful admission or release.

## Phase 03 Integration Boundary

Phase 04 may import and call:

`run_master_engine_worker_v4`

only through a dedicated outer wrapper added after the core admission
contract is proven.

The Phase 03 worker must remain unchanged unless a separately reviewed
compatibility requirement proves modification is necessary.

The future wrapper sequence is locked as:

1. acquire quota and slot;
2. execute `run_master_engine_worker_v4`;
3. release the slot in `finally`;
4. preserve and re-raise worker exceptions.

Quota rejection or slot rejection must occur before worker execution.

## Protected Files

The following behavior is protected:

- `engine/scanner.py`
- scanner helper modules;
- `engine/master_engine_v4.py`
- `engine/run_validated_dry_v4.py`
- `engine/stateful_worker_v4.py`
- `engine/validated_pipeline_v4.py`
- validation semantics;
- pre-delivery flow;
- Pine and TradingView delivery;
- production evidence;
- forward-test behavior;
- Golden Zone calculations.

Phase 04 must not alter their business semantics.

## Required Tests

The Phase 04 implementation must prove:

1. first valid acquisition succeeds;
2. acquisition consumes one quota unit;
3. rejected acquisition does not consume quota;
4. quota exhaustion returns `QUOTA_EXHAUSTED`;
5. full slot capacity returns `SLOTS_FULL`;
6. release frees one active slot;
7. release is idempotent;
8. unknown reservation release fails closed;
9. independent subjects have independent quota usage;
10. independent windows have independent quota usage;
11. invalid policies fail before mutation;
12. malformed state fails closed;
13. state writes are atomic;
14. import has no side effects;
15. rejected admission never calls the worker;
16. future wrapper releases slots after worker success;
17. future wrapper releases slots after worker failure;
18. worker failure is re-raised;
19. Phase 03 worker contract remains unchanged;
20. canonical regression remains green.

## Forbidden Scope

Phase 04 must not implement:

- Telegram commands or bot handlers;
- user authentication;
- subscription plans;
- payment processing;
- hard-coded production quota values;
- hard-coded production slot capacity;
- scheduler daemon behavior;
- priority queues;
- distributed queues;
- Redis or database migration;
- live trading;
- order execution;
- scanner or strategy changes;
- retry policy;
- quota administration UI.

## Lock Decision

Phase 04 is locked as a configurable, durable admission-control layer.

It supplies quota accounting and active-slot reservation mechanics
without inventing business policy and without bypassing the Phase 03
stateful worker boundary.
