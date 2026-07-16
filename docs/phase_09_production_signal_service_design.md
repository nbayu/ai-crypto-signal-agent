# Phase 09 — Production Signal Service Design Freeze

Status: DESIGN FROZEN

Locked baseline: `632a766dfeda42caa984a5e5e70e96c042e12f14`

Phase 08 is immutable. This document authorizes only the Phase 09 surface
defined below. It does not authorize exchange orders, capital deployment,
position sizing, account access, or mutation of prior evidence lanes.

## 1. Objective

Phase 09 introduces an authoritative Production Signal Service that converts
one completed production evaluation into exactly one canonical disposition:

- `PUBLISHED_SIGNAL`; or
- `NO_TRADE`.

For a published signal, the service owns creation of:

- `source_evaluation_id`;
- `signal_id`;
- `delivery_id`;
- `published_at`;
- `source_payload_hash`;
- canonical publication geometry;
- durable publication intent;
- durable delivery outcome; and
- the exact `source_publication_ref` consumed by Phase 07 and Phase 08.

The service is publication authority only. It is not strategy authority,
position authority, exchange authority, or capital authority.

## 2. Proven Existing Boundaries

The repository baseline proves:

1. `run_master_engine_v4` is the canonical decision orchestration boundary.
2. Pre-delivery produces the authoritative list of delivery-eligible setups.
3. Existing production evidence records immutable run directories and artifact
   paths, but does not define official signal publication identity.
4. Stateful worker UUIDs identify execution runs only.
5. Telegram application, transport, runtime, and SDK modules provide command
   and message transport, but do not define official publication identity.
6. Phase 07 validates, observes, acknowledges, and aggregates an already
   authoritative `source_publication_ref`.
7. Phase 08 requires an authoritative serialized publication capture and
   explicitly prohibits synthetic `signal_id` and `delivery_id`.

Therefore Phase 09 must introduce a separate closed publication authority.

## 3. Canonical Classification

Every Phase 09 publication record uses:

```text
classification:       PRODUCTION_SIGNAL
execution_boundary:   LIVE_SIGNAL_PUBLICATION_NO_CAPITAL
capital_exposure:     NONE
order_execution:      PROHIBITED
position_authority:   TELEGRAM_USER_REPORT
```

`TELEGRAM_USER_REPORT` means publication alone does not create an active
position. Existing valid user-report semantics remain the only position-state
authority.

## 4. Explicit Non-Goals

Phase 09 must not:

- place, amend, cancel, or simulate an exchange order;
- access account, wallet, balance, margin, position, or private exchange APIs;
- size a position or calculate account exposure;
- create automatic ENTRY, CLOSE, fill, win, loss, or P&L state;
- mutate Master Engine strategy decisions;
- change setup geometry after publication identity is derived;
- reuse worker UUIDs, timestamps, ranks, paths, process IDs, or Telegram update
  IDs as signal identity;
- read mutable latest artifacts as publication authority;
- write into Replay, Paper Signal, Shadow Release, worker, quota, Telegram
  ledger, or position-ledger roots;
- add automatic retries;
- silently replace a failed publication with stale success; or
- treat delivery attempt as user acknowledgment.

## 5. Authoritative Input

One service invocation accepts one detached plain-JSON production evaluation
envelope.

Required fields:

`schema_version`, `schema_name`, `source_commit`, `source_evaluation_id`,
`mode`, `evaluated_at`, `production_evidence_ref`, `outcome_kind`,
`eligible_setups`, `component_versions`.

Exact constants:

`schema_version: 1`
`schema_name: production-signal-input`
`outcome_kind: PUBLISHED_SIGNAL | NO_TRADE`
`mode: SWING | INTRADAY | SCALP`

The envelope must be supplied explicitly by the caller.

It must not be reconstructed from a mutable `latest.json`, directory ordering,
filesystem modification time, worker state, quota state, Telegram update
identity, process-local memory, or ambient clock values other than the
explicit publication clock.

### 5.1 PUBLISHED_SIGNAL

For `PUBLISHED_SIGNAL`, `eligible_setups` contains exactly one setup; the setup
is copied from an authoritative delivery-eligible production projection;
required geometry is complete; `source_evaluation_id`, mode, symbol, side,
entry zone, stop loss, take profit, validity, strategy version, and source
hashes are mandatory.

One evaluation with multiple eligible setups must be serialized as independent
service inputs sharing the same `source_evaluation_id`, with one setup each.

### 5.2 NO_TRADE

For `NO_TRADE`, `eligible_setups` is empty; no `signal_id` or `delivery_id` is
generated; no delivery adapter is called; one immutable evaluation record is
still published. `NO_TRADE` is not a failed signal, order, or delivery.

## 6. Canonical JSON

All canonical hashing uses:

```python
json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
)
```

The byte encoding is UTF-8.

Non-finite numbers, boolean integer aliases, missing fields, unknown fields,
unsupported enums, and malformed UTC timestamps fail closed.

All SHA-256 hashes are lowercase 64-character hexadecimal strings.

## 7. Identity Rules

### 7.1 Source evaluation identity

`source_evaluation_id` is caller-supplied authoritative identity.

Phase 09 validates and preserves it exactly. It must not normalize, renumber,
infer, or replace it.

### 7.2 Signal identity

The immutable signal identity payload is:

```json
{
  "schema_version": 1,
  "source_commit": source_commit,
  "source_evaluation_id": source_evaluation_id,
  "mode": mode,
  "symbol": symbol,
  "signal_geometry_hash": signal_geometry_hash,
  "source_payload_hash": source_payload_hash
}
```

`signal_id = "PSG-" + sha256(canonical_json(identity_payload))`

The signal identity is deterministic and not clock-derived.

### 7.3 Delivery identity

The immutable delivery identity payload is:

```json
{
  "schema_version": 1,
  "signal_id": signal_id,
  "channel": channel,
  "destination_id": destination_id,
  "publication_payload_hash": publication_payload_hash
}
```

`delivery_id = "PDL-" + sha256(canonical_json(identity_payload))`

The destination value is an opaque caller-supplied identifier. Secrets and bot
tokens must never be included.

### 7.4 Publication timestamp

`published_at` is an explicit caller-provided UTC timestamp.

It represents the authoritative publication attempt time recorded by the
service. It is distinct from evaluation time, transport completion time, user
acknowledgment time, ENTRY/CLOSE reports, and filesystem timestamps.

## 8. Canonical Publication Contract

A completed published-signal record contains exactly:

`schema_version`, `schema_name`, `classification`, `execution_boundary`,
`capital_exposure`, `order_execution`, `position_authority`, `source_commit`,
`source_evaluation_id`, `mode`, `outcome_kind`, `signal_id`, `delivery_id`,
`published_at`, `channel`, `destination_id`, `signal_geometry`,
`signal_geometry_hash`, `publication_payload`, `publication_payload_hash`,
`source_payload_hash`, `source_publication_ref`, `delivery_state`,
`delivery_receipt`, `failure`, `component_versions`, `content_hash`.

Exact constants:

`schema_version: 1`
`schema_name: production-signal-publication`
`outcome_kind: PUBLISHED_SIGNAL`

`source_publication_ref` contains exactly the frozen Phase 07 fields:

`signal_id`, `delivery_id`, `mode`, `published_at`, `source_payload_hash`.

The service must validate its own generated reference with the Phase 07
contract before publication completes.

## 9. Signal Geometry

Canonical geometry contains exactly:

`symbol`, `side`, `entry_zone`, `stop_loss`, `take_profit`, `valid_until`.

Rules: `side` is `LONG` or `SHORT`; entry-zone bounds are finite numbers and
ordered; stop and targets are finite numbers; validity is an ISO-8601 UTC
timestamp; geometry is deep-copied; geometry becomes immutable once `signal_id`
is derived; formatting for Telegram is not part of geometry authority.

## 10. Publication Payload

The publication payload is a closed structured JSON object, not preformatted
transport text.

It contains `signal_id`, `mode`, `symbol`, `side`, `entry_zone`, `stop_loss`,
`take_profit`, `valid_until`, `strategy_version`, and `source_evaluation_id`.

The renderer may convert this object into Telegram text, but the renderer must
not add, remove, recalculate, or reinterpret decision-bearing values.

## 11. Delivery State Machine

Allowed states: `INTENT_PERSISTED`, `DELIVERY_SUCCEEDED`, `DELIVERY_FAILED`.

Transition:

```text
validated input
    -> persist INTENT_PERSISTED
    -> invoke delivery adapter exactly once
        -> DELIVERY_SUCCEEDED
        -> DELIVERY_FAILED
```

No automatic retry exists in Phase 09.

A repeated invocation with the same canonical delivery identity returns the
existing byte-identical completed record and must not call the delivery adapter
again. Reuse of the same identity with different canonical content is an
identity collision and fails closed.

### 11.1 Delivery receipt

On success, the adapter returns a detached JSON receipt containing only:

`channel`, `destination_id`, `external_delivery_id`, `delivered_at`.

`external_delivery_id` is transport metadata. It is not `signal_id`,
`delivery_id`, acknowledgment identity, or position authority.

### 11.2 Failure

On delivery failure, the intent remains durable; the completed record becomes
`DELIVERY_FAILED`; failure text is sanitized; no token, key, path, traceback,
or provider payload may be persisted; no Paper Signal observation is created;
no Shadow Release published-signal capture may claim success; and the same
invocation remains idempotent and does not retry automatically.

## 12. Failure Taxonomy

Allowed primary failure codes:

`INPUT_CONTRACT_REJECTED`, `SOURCE_AUTHORITY_MISSING`,
`COMPONENT_VERSION_UNSUPPORTED`, `IDENTITY_COLLISION`,
`ROOT_ISOLATION_VIOLATION`, `CONCURRENCY_CONFLICT`,
`INTENT_PUBLICATION_FAILED`, `DELIVERY_ADAPTER_FAILED`,
`COMPLETION_PUBLICATION_FAILED`, `SOURCE_REFERENCE_REJECTED`.

Each failure contains exactly `primary_code`, `component`, and `message`.
Messages must be stable and sanitized.

## 13. Artifact Root

The only authorized Phase 09 root is `data/production_signal/`.

Layout:

```text
data/production_signal/
  publications/
  evaluations/
  .locks/
```

Published signals: `publications/<signal_id>/<delivery_id>.json`
`NO_TRADE` evaluations: `evaluations/<mode>__<source_evaluation_id>.json`
Locks: `.locks/<delivery_id>.lock`

The publisher must validate root ancestry, reject symlinks and non-regular
destinations, remain inside the validated root, write canonical
newline-terminated JSON, fsync file and directory, use atomic replacement,
support byte-identical idempotency, reject collisions, serialize cooperating
publishers with a root-local identity lock, and remove temporary files and
released lock files.

## 14. Protected Roots

Phase 09 must reject attempts to publish under or alias these roots:

`replay`, `replay_artifacts`, `production_evidence_v4`,
`validated_snapshots_v4`, `v4_outcomes`, `top5_watchlist_v4`, `pre_delivery_v4`,
`pine_delivery_v4`, `telegram_state`, `worker_state_v4`, `quota_slot_v4`,
`position_ledger`, `paper_signal`, `shadow_release`.

Phase 09 reads detached source data only. It does not mutate those roots.

## 15. Delivery Adapter Boundary

The delivery adapter is injected and callable.

Canonical logical signature:

`deliver(publication_payload, *, channel, destination_id) -> delivery_receipt`

The contract implementation must not import Telegram SDK, HTTP clients,
exchange clients, or environment loaders. Phase 09 core tests use fake
adapters only.

A future integration adapter may invoke Telegram, but it remains transport and
must not create publication identity or modify publication geometry.

## 16. Service Boundary

Canonical logical signature:

```python
run_production_signal_service_v1(
    *,
    source_envelope,
    publication_root,
    channel,
    destination_id,
    published_at,
    delivery_adapter,
    component_versions,
)
```

The service validates and deep-copies input, derives canonical hashes and
identities, builds publication intent, persists intent before external
delivery, invokes the adapter at most once, builds success or failure
completion, publishes immutable completion evidence, validates
`source_publication_ref`, and returns detached publication evidence and
artifact path.

For `NO_TRADE`, the service publishes one evaluation record and never calls the
adapter.

## 17. Authorized Phase 09 Modules

Initial authorized implementation surface:

`docs/phase_09_production_signal_service_design.md`

`engine/production_signal_contract_v1.py`
`engine/production_signal_artifact_v1.py`
`engine/production_signal_service_v1.py`

`tests/test_production_signal_contract_v1.py`
`tests/test_production_signal_artifact_v1.py`
`tests/test_production_signal_service_v1.py`

No existing implementation module is authorized for modification in the
initial surface.

Any compatibility seam with Master Engine, worker, Telegram application,
transport, runtime, SDK, Phase 07, or Phase 08 requires separate evidence and
explicit authorization after the isolated service surface is complete.

## 18. RED/GREEN Sequence

Freeze this design document. RED contract tests:
`tests/test_production_signal_contract_v1.py`. GREEN contract:
`engine/production_signal_contract_v1.py`. RED artifact tests:
`tests/test_production_signal_artifact_v1.py`. GREEN artifact publisher:
`engine/production_signal_artifact_v1.py`. RED service tests:
`tests/test_production_signal_service_v1.py`. GREEN service:
`engine/production_signal_service_v1.py`. Focused integration and
protected-boundary audit. Full canonical regression. Compatibility-seam
decision. Final scope, history, push, and lock audit.

Every RED commit must fail only because the next authorized production module
does not yet exist or does not yet satisfy the frozen contract.

## 19. Required Test Coverage

### Contract

Tests must cover exact schema and enum validation, canonical JSON, non-finite
rejection, UTC timestamps, exact fields and unknown-field rejection,
deterministic `signal_id`, deterministic `delivery_id`, geometry validation,
detached input/output, source-reference compatibility with Phase 07,
`NO_TRADE` prohibition on signal/delivery identity, and secret and
forbidden-field rejection.

### Artifact

Tests must cover authorized root only, canonical bytes and trailing newline,
atomic publication, fsync path, regular-file validation, symlink and ancestry
rejection, protected-root rejection, byte-identical idempotency, identity
collision, root-local lock, concurrent publication behavior, temporary-file
cleanup, and no mutation of source payload.

### Service

Tests must cover intent persisted before adapter call, exactly one adapter call,
successful receipt, sanitized adapter failure, no automatic retry, completed
idempotent reuse without adapter call, collision rejection, `NO_TRADE` without
adapter call, source-reference validation, no Telegram SDK import, no
exchange/account/order import, no writes outside the Phase 09 root, and no
position state mutation.

## 20. Promotion Boundary

Phase 09 completion proves only canonical production signal publication
authority, deterministic signal and delivery identities, durable publication
intent and delivery outcome, fail-closed idempotency, Phase 07/08
source-reference compatibility, and no-capital production alert delivery.

It does not authorize capital, exchange execution, simulated brokerage,
automatic positions, portfolio accounting, retries, high availability,
deployment rollout, or any post-Phase-09 roadmap extension.
