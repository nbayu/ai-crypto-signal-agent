# PHASE 05 — TELEGRAM INTERFACE — DESIGN FREEZE

## Status

DESIGN FROZEN — IMPLEMENTATION NOT YET AUTHORIZED

## Baseline

- Branch: `master`
- Starting commit: `db69d99`
- Starting regression: `250 passed`
- Previous locked phase: Phase 04 — Quota & Slot Engine
- Canonical admission and worker entrypoint:
  `engine.quota_slot_worker_v4.run_quota_slot_worker_v4`

## 1. Phase Objective

Phase 05 introduces a thin Telegram operator interface around the
Phase 04 quota-slot worker boundary. It accepts a Telegram command,
resolves caller identity and injected policy inputs, invokes the
canonical wrapper at most once for an accepted scan, and formats a safe
operator response.

Telegram is not a second orchestration engine. It must not duplicate
scanner, validation, master-engine, stateful-worker, quota, or slot
behavior.

Historical evidence in `FINAL_PRODUCTION_CLOSURE_V4.md` records a
previous gateway/plugin Telegram deployment. That evidence is not a
source-code transport contract and does not authorize relying on a
gateway plugin, its credentials, or its runtime configuration in this
repository.

## 2. Canonical Execution Boundary

Every Telegram-triggered scan must call exactly:

`run_quota_slot_worker_v4(...)`

The Telegram application layer must not directly call or reproduce:

- `engine.scanner` or scanner helpers;
- validated-pipeline internals;
- `run_master_engine_v4` orchestration;
- `run_master_engine_worker_v4` lifecycle handling;
- quota acquisition or release functions;
- pre-delivery, TradingView/Pine, evidence, or forward-test routines.

The Phase 04 wrapper owns acquisition, worker execution, release in
`finally`, and exception precedence. The Telegram layer is only a
caller and formatter of its public result or failure.

## 3. Initial Command Surface

Phase 05 freezes only four initial commands.

| Command | Purpose | Worker execution | Required inputs | Response category | Failure and quota behavior |
| --- | --- | --- | --- | --- | --- |
| `/start` | Introduce the operator interface and direct the user to `/help`. | Never. | Telegram update context only. | `INFO` | Safe generic failure message on local formatting failure; no quota use. |
| `/help` | Describe the frozen command surface and scanner-only boundary. | Never. | Telegram update context only. | `INFO` | Safe generic failure message on local formatting failure; no quota use. |
| `/status` | Report interface readiness and non-secret configuration availability. | Never. | Telegram update context and resolved non-secret runtime configuration. | `STATUS` | Reports unavailable configuration as `NOT_READY`; no state mutation, no quota use. |
| `/scan` | Request one admitted Phase 04 worker execution. | Only after valid command, identity, and policy resolution. | Telegram user identity, chat context, and all injected policy inputs. No scan arguments are defined in the first contract. | `SCAN_SUCCESS`, rejection, or safe failure category. | Quota follows Phase 04: consumed on successful admission, including later worker failure; rejected/invalid requests consume none. |

No aliases, free-form scan parameters, administrative commands,
scheduler commands, payment commands, or user-management commands are
part of this phase.

## 4. Telegram Transport Boundary

Phase 05 has two layers.

1. A pure command/service layer accepts normalized command input,
   identity data, injected policy/configuration, and an injected
   `run_quota_slot_worker_v4` callable. It returns deterministic
   application response objects. It imports no Telegram SDK and makes
   no network calls.
2. A Telegram adapter parses SDK update objects, invokes the pure
   layer, and sends already-formatted plain-text responses. It owns no
   business decision beyond transport parsing and delivery.

Runtime configuration and worker invocation must be dependency
injected. Module import must not create a bot client, open a network
connection, start polling or a webhook, create a directory, or execute
a worker.

## 5. Identity Mapping

For an update with a present numeric Telegram sender ID, Phase 05 maps
the quota subject deterministically as:

`subject_id = "telegram:user:{telegram_user_id}"`

The chat ID is retained only as transport/request context for response
routing and audit-safe application context; it does not create a
separate quota subject. A user's quota therefore follows that user
across chats.

If a command has no usable sender ID, the pure layer returns
`INVALID_INPUT` and does not invoke the worker. This design defines no
authorization, allowlist, subscription, billing, database, or identity
verification policy.

## 6. Quota and Slot Policy Inputs

The pure service receives, rather than invents, the following inputs:

- `subject_id`: derived using the deterministic mapping above;
- `window_id`: stable accounting-window identifier provided by injected
  runtime policy;
- `quota_limit`: positive integer provided by injected runtime policy;
- `slot_capacity`: positive integer provided by injected runtime
  policy;
- `quota_state_path`: configured Phase 04 state location;
- `worker_state_path`: configured Phase 03 worker state location.

The Phase 05 service validates that required inputs are present enough
to call the boundary, but the Phase 04 engine remains authoritative for
policy and request validation. Phase 05 must not hard-code commercial,
production, user-tier, or capacity values.

## 7. Status Semantics

`/status` is a non-mutating readiness command. The first implementation
reports only deterministic, non-secret interface readiness information,
such as whether required non-secret configuration values were supplied
and whether a scan boundary has been injected.

It must not:

- invoke `run_quota_slot_worker_v4`;
- acquire or release a quota slot;
- consume quota;
- create or update quota or worker state;
- invoke market-data, scanner, validation, or delivery code.

The initial contract does not read quota or worker JSON state. A future
read-only state summary requires a separate reviewed contract with
corruption handling and safe field selection.

## 8. Scan Semantics

The locked high-level sequence for `/scan` is:

`Telegram request -> validate command/request -> resolve identity and policy -> call run_quota_slot_worker_v4() -> normalize result or failure -> format Telegram-safe response`

For each accepted command, the service invokes the wrapper no more than
once. It passes the resolved policy inputs unchanged to the wrapper and
does not retry after a worker, release, transport, or formatting failure.

Telegram update deduplication is not included in initial Phase 05. The
service guarantees at most one wrapper invocation per pure dispatch call;
it does not claim exactly-once worker execution across duplicate Telegram
deliveries, transport retries, process restarts, or SDK behavior. A future
deduplication mechanism requires a separate durable-state and retention
contract.

The Phase 04 wrapper controls the inner sequence:

`acquire -> stateful worker -> release in finally`

Transport delivery occurs only after the service has a response object.
A Telegram send failure must not lead to a second worker invocation.

## 9. Response Contract

Before transport formatting, the pure layer returns a deterministic
application response object containing at least:

- `category`: stable response category;
- `command`: normalized command name;
- `message`: safe, deterministic plain-text summary;
- `scan`: optional safe scan summary only when available.

It must not include bot tokens, secrets, raw tracebacks, unrestricted
exception representations, filesystem paths, reservation IDs unless
explicitly approved later, or raw master-engine payloads.

The initial category mapping is:

| Condition | Category | User-facing message intent |
| --- | --- | --- |
| `/start` or `/help` success | `INFO` | Command guidance. |
| `/status` ready | `STATUS` | Interface readiness only. |
| `/status` not ready | `NOT_READY` | Required configuration is unavailable; no secret names or values. |
| `/scan` wrapper success | `SCAN_SUCCESS` | Scan completed; include only a deliberately selected safe summary. |
| Unknown command, missing sender, or malformed request | `INVALID_INPUT` | Command or request cannot be processed. |
| `QuotaSlotRejected` / `QUOTA_EXHAUSTED` | `QUOTA_EXHAUSTED` | Current window quota is unavailable. |
| `QuotaSlotRejected` / `SLOTS_FULL` | `SLOTS_FULL` | Scanner capacity is currently busy. |
| `QuotaSlotRejected` / `STATE_CORRUPT` | `STATE_UNAVAILABLE` | Admission state is unavailable; try later or contact an operator. |
| Other `QuotaSlotRejected` reason | `ADMISSION_REJECTED` | Scan cannot be admitted. |
| Worker exception | `WORKER_FAILED` | Scan execution failed after admission; no raw exception text. |
| Release exception after worker success | `RELEASE_FAILED` | Scan completed but admission release handling failed; no retry. |
| Worker exception with a chained release exception | `WORKER_AND_RELEASE_FAILED` | Scan execution failed and release handling also failed; no retry. |
| Any unexpected application error | `INTERNAL_ERROR` | Request could not be completed. |

The pure layer may retain exception identity only for internal caller
control flow or logging hooks injected by a future reviewed runtime. It
never serializes that identity into a Telegram response.

The Phase 04 wrapper preserves a worker exception as primary when release
also fails and chains the release exception as its cause. The pure layer
uses that defined shape to distinguish `WORKER_AND_RELEASE_FAILED` from
an ordinary `WORKER_FAILED` response, without exposing either exception.

## 10. Message Formatting Constraints

Telegram output must be deterministic plain text. The adapter uses no
Markdown/HTML parse mode in the initial contract, avoiding transport
escaping ambiguity.

Messages must be bounded by a required injected positive integer named
`max_response_chars`. Runtime validation requires it to be greater than
the fixed plain-text marker `\n[truncated]`. Formatting first builds a
safe message with no secrets or raw payloads; if it exceeds the bound, it
returns the leading `max_response_chars - len("\n[truncated]")` characters
followed by that marker. The resulting message therefore never exceeds the
configured bound and is deterministic.

Formatting must not depend on TradingView/Pine rendering, mutate a
watchlist, make live-trading claims, imply order execution, or expose
unreviewed fields from scanner/master-engine output.

## 11. Configuration and Secrets

Runtime configuration is supplied outside source control and injected
into the runtime entrypoint. The future configuration boundary includes:

- Telegram bot token;
- optional approved chat/user configuration, only if a later Phase 05
  decision explicitly includes an allowlist;
- quota window, limit, and slot-capacity policy provider;
- quota and worker state paths;
- transport timeout settings;
- `max_response_chars` response-length setting.

Before a runtime entrypoint constructs a client or starts polling, it
must validate all required runtime configuration and fail closed when it
is invalid or absent. Validation includes a non-blank bot token, a
configured policy provider that supplies a non-blank `window_id` and
positive integer quota/slot values, configured state paths, a valid
`max_response_chars`, and valid positive transport settings when the
selected SDK uses them. This validation must not invoke a worker, create
state, or derive a quota window from local system time.

No token or secret may be committed, logged, placed in a response object,
returned to a user, or embedded in a fixture. The initial phase does not
include authorization, an allowlist, a user database, subscriptions, or
payments; optional approval configuration is deferred unless separately
designed.

## 12. Failure and Exception Policy

Phase 04 rejection reason codes remain meaningful at the application
boundary and are mapped to the safe categories above. The original
exception identity is preserved inside the wrapper's own contract, but
Telegram users see only a stable safe message.

The adapter treats send failures as transport failures after application
completion. It reports or logs them only through a future approved
operator mechanism and must never rerun the worker, reacquire quota, or
retry a scan automatically.

## 13. Import-Safety Contract

Importing any Phase 05 application, adapter, configuration, or runtime
module must not:

- create a Telegram client;
- open a network connection;
- start polling or a webhook server;
- create a state directory or state file;
- execute a worker;
- acquire or release a quota slot;
- mutate quota or worker state.

Only an explicit runtime-entrypoint call may construct a transport client
or start a transport loop, after configuration has been supplied.

## 14. Dependency Decision

Current `requirements.txt` contains no Telegram SDK. The repository's
historical Telegram evidence describes an external gateway/plugin and
does not establish a Python SDK dependency or adapter API.

`python-telegram-bot` provides a high-level async application framework,
while `aiogram` is also async and framework-oriented. Either would add a
new transport dependency and an async runtime decision without improving
the pure command contract.

Decision: defer selection and installation of either SDK until the pure
application layer has RED/GREEN coverage. The later adapter decision must
prefer the smaller integration that preserves synchronous pure-service
testing, explicit startup, injected transport methods, and no import-time
network behavior. No dependency changes are authorized by this freeze.

## 15. Proposed File Structure

The smallest proposed Phase 05 file set is:

- `engine/telegram_command_service_v4.py`: pure command dispatch,
  identity mapping, policy resolution boundary, response normalization;
- `engine/telegram_adapter_v4.py`: SDK-specific update parsing and
  response sending only;
- `engine/run_telegram_v4.py`: explicit runtime entrypoint that loads
  injected runtime configuration and starts the selected transport;
- `tests/test_telegram_command_service_v4.py`: pure-service contracts;
- `tests/test_telegram_adapter_v4.py`: adapter parsing/formatting with
  fake SDK objects;
- `tests/test_run_telegram_v4.py`: explicit-start and import-safety
  contracts.

No placeholder files, default polling behavior, or transport dependency
are created until their respective RED tests are approved.

## 16. Protected Files and Behaviors

Phase 05 must preserve all Phase 00–04 contracts, including:

- `engine/scanner.py` and every scanner helper;
- validated pipeline and semantic validation behavior;
- DeepSeek routing behavior;
- master-engine orchestration;
- stateful-worker lifecycle and durable event contract;
- quota-slot core and outer wrapper semantics;
- pre-delivery behavior;
- TradingView/Pine artifacts;
- production evidence;
- forward-test semantics;
- live-trading permissions and scanner-only boundary.

## 17. Forbidden Phase 05 Scope

Phase 05 must not implement:

- Telegram scheduler or recurring jobs;
- background queues;
- webhook deployment or VPS service setup;
- payment processing or subscription management;
- production user database;
- exchange order execution or automatic trading;
- TradingView watchlist mutation;
- Pine Script modification;
- modification of Phase 04 admission semantics;
- scanner, strategy, validation, delivery, evidence, or forward-test
  changes.

## 18. Test Strategy

Phase 05 must begin with RED tests, then implement the smallest layer
needed to satisfy them. Required coverage includes:

1. pure command dispatch for `/start`, `/help`, `/status`, and `/scan`;
2. deterministic Telegram user-to-subject identity mapping;
3. `/status` non-mutation and no worker invocation;
4. `/scan` invoking the quota-slot wrapper no more than once;
5. quota and slot rejection mapping;
6. corrupt quota state, worker failure, and release failure mapping;
7. worker-state path and injected policy forwarding;
8. Telegram adapter parsing with fake update/message objects;
9. deterministic safe plain-text formatting and response bounds;
10. import safety for every Phase 05 module;
11. secret redaction and absence of tokens in responses/fixtures;
12. no network calls in unit tests;
13. canonical full regression preservation.

Tests use `tmp_path`, injected clocks, injected policy values, injected
worker callables, and fake transport objects. They must not require a
real Telegram token, live bot, real SDK network call, market-data call,
or master-engine execution.

## 19. Commit Plan

Future implementation uses separate atomic commits in this order:

1. `docs: freeze Telegram interface design`;
2. `feat: add pure Telegram command service`;
3. `feat: add Telegram transport adapter` (including the approved SDK
   dependency only if still necessary);
4. `feat: add Telegram runtime entrypoint and configuration boundary`;
5. `test/fix: finalize Telegram interface contracts`.

This document authorizes none of those implementation commits.

## 20. Lock Decision and Entry Criteria

Phase 05 is locked as a pure, deterministic operator-command service
over the existing Phase 04 quota-slot worker, followed later by a thin
transport adapter and an explicit runtime entrypoint.

Implementation may begin only when all of the following are approved:

- this design freeze is committed as its own documentation change;
- RED tests for the pure command layer define safe response objects and
  `/status` non-mutation;
- policy and identity inputs are injectable with no production values in
  source;
- no SDK is installed before the pure layer is proven;
- the Phase 04 wrapper remains the only scan execution boundary;
- import-safety and full-regression expectations are included in the
  implementation plan.
