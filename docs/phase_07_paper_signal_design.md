# Phase 07 — Paper Signal Design Freeze

Status: DESIGN FROZEN
Baseline: `86eb799fc8b32489603ec737c9199033c13a61bc`
Phase authority: Master Engine Module V2 and Transformation Blueprint V1

## 1. Objective

Observe live signal behavior without capital, exchange-order permissions,
simulated account execution, or automatic position management.

Phase 07 provides deterministic paper-signal observation evidence for:

- official published signals;
- acknowledgment latency;
- entry-zone touch observation;
- target-before-entry observation;
- invalidation-before-entry observation;
- signal expiry and cancellation;
- NO TRADE coverage;
- sample counts per enabled mode;
- critical lifecycle-defect detection.

## 2. Explicit Non-Goals

Phase 07 must not implement:

- exchange order placement;
- simulated broker or order book;
- virtual account balance;
- position sizing;
- leverage or margin;
- portfolio exposure;
- account-risk permission;
- fee or funding ledger attributed to a filled position;
- realized or unrealized account P&L;
- automatic ENTRY;
- automatic CLOSE;
- conversion of entry touch into an executed fill;
- conversion of TP or SL touch into a closed user position.

## 3. Authority Boundaries

### Master Engine

Remains the sole authority for:

- setup;
- side;
- trigger;
- entry zone;
- structural stop;
- take-profit destinations;
- net RR;
- score;
- confidence;
- final strategy verdict.

Phase 07 must not recalculate or modify these fields.

### Signal Lifecycle and Telegram

Existing user-report authority remains unchanged:

- `ENTRY` creates an acknowledged open position;
- `CLOSE` closes an acknowledged open position;
- `SKIP` releases a reservation;
- `STATUS` is read-only.

Only a valid user report may create `ACTIVE` or `CLOSED`.

### Paper Observation

Paper observation records market evidence separately from the position ledger.

It may observe:

- entry-zone touched;
- TP touched before entry;
- SL/invalidation touched before entry;
- signal expiry;
- cancellation;
- acknowledgment timestamps;
- NO TRADE output.

It must not claim that an order was submitted, filled, partially filled,
opened, closed, won, lost, or profitable.

## 4. Canonical Classification

All Phase 07 observation artifacts must use:

- `classification`: `PAPER_SIGNAL`
- `execution_boundary`: `LIVE_MARKET_OBSERVATION_NO_CAPITAL`
- `capital_exposure`: `NONE`
- `order_execution`: `PROHIBITED`
- `position_authority`: `TELEGRAM_USER_REPORT`

Phase 07 evidence is not:

- replay evidence;
- backtest evidence;
- exchange execution evidence;
- account-performance evidence;
- production-release evidence.

## 5. Paper Signal Observation States

The paper observation state is independent from the authoritative
publication and user-position lifecycle.

Allowed paper observation states:

- `OBSERVING`
- `ENTRY_ZONE_TOUCHED`
- `TARGET_REACHED_BEFORE_ENTRY`
- `INVALIDATED_BEFORE_ENTRY`
- `EXPIRED_UNTOUCHED`
- `CANCELLED`
- `OBSERVATION_AMBIGUOUS`
- `TERMINAL`

These states do not replace or mutate existing signal states such as:

- `PUBLISHED_RESERVED`
- `ACTIVE`
- `CLOSED`
- `SKIPPED`
- `EXPIRED`
- `INVALIDATED`

## 6. Touch and Fill Semantics

### Entry touch

An entry touch means a closed market candle intersects the published entry
zone according to the existing lifecycle observation contract.

It must be recorded as:

- `entry_touched_at`
- `entry_touch_candle`
- `entry_touch_source`

It must never be recorded as:

- `filled_at`
- `fill_price`
- `executed_entry`
- `position_opened`

### Fill observation

The roadmap term "fill analysis" means analysis of entry-zone touch and
execution opportunity under observed market data.

It does not mean an exchange or simulated order fill.

Canonical output field:

- `fill_observation_status`

Allowed values:

- `NOT_OBSERVED`
- `ENTRY_ZONE_TOUCHED`
- `TARGET_REACHED_BEFORE_ENTRY`
- `INVALIDATED_BEFORE_ENTRY`
- `EXPIRED_UNTOUCHED`
- `AMBIGUOUS`

The words `FILLED`, `PARTIALLY_FILLED`, and `EXECUTED` are prohibited.

## 7. Acknowledgment Latency

Acknowledgment latency measures the time between official publication and
the first valid Telegram user response.

Supported acknowledgments:

- `ENTRY_REPORTED`
- `SKIP_REPORTED`

Fields:

- `published_at`
- `acknowledged_at`
- `acknowledgment_type`
- `acknowledgment_latency_ms`

Rules:

- latency must be non-negative;
- duplicate reports must not create a second latency record;
- no acknowledgment leaves latency null;
- `CLOSE` is not the publication acknowledgment event;
- transport delivery time and user acknowledgment time must remain separate.

## 8. NO TRADE Coverage

Phase 07 records each evaluation cycle that produces no official alert.

Required aggregate fields per enabled mode:

- `evaluation_cycles`
- `official_alert_cycles`
- `no_trade_cycles`
- `no_trade_coverage_ratio`
- `top_rejection_reasons`

Formula:

`no_trade_coverage_ratio = no_trade_cycles / evaluation_cycles`

The ratio is observational and must not be interpreted as performance or
signal quality.

## 9. Sample Gate

Paper-signal promotion requires:

- at least 100 official paper signals in total;
- at least 30 official paper signals per enabled mode;
- no critical lifecycle defect.

Only successfully published official alerts count as paper signals.

The following do not count toward the official signal sample:

- discovery candidates;
- internal qualified setups;
- ARMED-only setups;
- NO TRADE cycles;
- replay results;
- duplicate deliveries;
- rejected or cancelled pre-publication candidates.

NO TRADE coverage is tracked separately.

## 10. Critical Lifecycle Defects

A critical lifecycle defect includes:

- duplicate observation publication;
- mutation of immutable signal geometry;
- entry touch automatically creating `ACTIVE`;
- TP or SL observation automatically creating `CLOSED`;
- paper evidence claiming an executed order;
- negative acknowledgment latency;
- one signal assigned to multiple modes;
- observation after terminal state changing prior authoritative evidence;
- replay evidence counted as live paper evidence;
- sample counters incremented more than once for one signal;
- malformed or partial artifact published as complete;
- live failure silently replaced with stale success;
- unauthorized writing into replay or production evidence roots.

Any critical lifecycle defect blocks Phase 07 promotion.

## 11. Input Boundary

The Paper Signal observer may consume only:

- immutable published signal identity and geometry;
- existing lifecycle state;
- closed live candles required for observation;
- publication timestamps;
- Telegram acknowledgment events;
- enabled-mode configuration;
- deterministic clock input;
- version metadata.

It must not invoke:

- scanner discovery;
- Master Engine recalculation;
- exchange order APIs;
- account APIs;
- wallet or balance APIs;
- automatic position management.

## 12. Artifact Contract

Each official signal receives at most one canonical paper-observation
record.

Required identity fields:

- `schema_version`
- `paper_observation_id`
- `signal_id`
- `mode`
- `classification`
- `execution_boundary`
- `source_publication_ref`
- `strategy_version`
- `orchestration_policy_version`
- `observer_version`
- `observed_from`
- `observed_until`
- `observation_state`
- `fill_observation_status`
- `entry_touched_at`
- `acknowledgment`
- `terminal_reason`
- `evidence`
- `created_at`
- `content_hash`

Publication requirements:

- canonical serialization;
- deterministic content hash;
- immutable completed record;
- atomic publication;
- fail closed;
- no live fallback to replay data;
- no partial completion marker presented as success;
- verified identical reuse may be allowed;
- conflicting reuse must be rejected.

## 13. Aggregate Progress Contract

The progress artifact must expose:

- total official paper signals;
- count by mode;
- enabled modes;
- minimum required total;
- minimum required per enabled mode;
- NO TRADE coverage by mode;
- terminal observation distribution;
- acknowledgment coverage and latency summary;
- critical lifecycle defect count;
- promotion readiness.

Promotion readiness is true only when:

- total sample is at least 100;
- every enabled mode has at least 30;
- critical lifecycle defect count is zero.

The artifact must not report:

- win rate;
- profit factor;
- account drawdown;
- realized P&L;
- equity curve;
- portfolio return.

Those require separately governed validation authority.

## 14. Protected Surfaces

Phase 07 must not modify the behavior or contract of:

- scanner and discovery modules;
- Master Engine strategy rules;
- setup lifecycle semantics;
- quota and slot rules;
- Telegram state transitions;
- replay classification and replay artifact paths;
- production evidence classification;
- deployment;
- exchange execution;
- TradingView Pine behavior;
- user-position ledger authority.

Compatibility seams may be added only when:

- they are dependency-injection boundaries;
- existing production behavior remains unchanged;
- existing regressions remain green;
- the seam is documented and directly tested.

## 15. Failure Policy

All Phase 07 failures must fail closed.

Prohibited:

- retry that duplicates evidence;
- stale-success masking;
- converting observation failure into success;
- falling back to replay data;
- publishing incomplete artifacts;
- leaking absolute sensitive paths in public error text;
- mutating authoritative lifecycle state after observer failure.

## 16. Test Requirements

Required RED contract families:

1. Schema and enum validation.
2. Entry touch is not a fill.
3. Entry touch does not create `ACTIVE`.
4. TP/SL observation does not create `CLOSED`.
5. Acknowledgment latency and duplicate-event idempotency.
6. NO TRADE coverage calculation.
7. Sample counting and enabled-mode minimums.
8. Critical-defect promotion blocking.
9. Classification and execution-boundary integrity.
10. Replay/live evidence separation.
11. Artifact atomicity and conflicting reuse rejection.
12. Input immutability and aliasing protection.
13. Protected-surface regression.
14. Deterministic aggregate progress output.

## 17. Implementation Order

Implementation must proceed in this order:

1. freeze schema and enums;
2. write RED contract tests;
3. implement immutable observation model;
4. implement live closed-candle observer;
5. implement acknowledgment recorder;
6. implement NO TRADE coverage;
7. implement progress and promotion gate;
8. implement artifact publication;
9. run focused regression;
10. run canonical regression;
11. external architecture audit;
12. critical code and vulnerability audit;
13. owner review;
14. lock and checkpoint.

## 18. Final Frozen Claim

Phase 07 observes official signals against live market data without capital
and records deterministic paper-signal evidence.

It does not execute or simulate exchange orders, own account risk, claim
fills, mutate user-position authority, or establish profitability.

Any expansion into virtual brokerage, portfolio accounting, automatic
execution, or account-performance reporting requires a separate RFC and
owner approval.

## 19. Contract Amendment V1 — Exact Schema and Transition Rules

Status: FROZEN AMENDMENT
Purpose: Close implementation ambiguity before RED contract tests.
This amendment does not expand Phase 07 scope.

### 19.1 Schema Versions

The canonical observation schema uses:

- `schema_version`: integer `1`
- `schema_name`: `paper-signal-observation`
- `observer_version`: non-empty version string

The canonical aggregate schema uses:

- `schema_version`: integer `1`
- `schema_name`: `paper-signal-progress`

Unknown schema versions must be rejected.

Boolean values must not be accepted where an integer is required.

### 19.2 Canonical Mode Enum

Allowed mode values are exactly:

- `SWING`
- `INTRADAY`
- `SCALP`

Mode comparison is case-sensitive.

Every observation belongs to exactly one mode.

A source publication whose signal identity is already associated with a
different mode must be rejected as a conflicting identity.

### 19.3 Source Publication Identity

Phase 07 does not create or reinterpret official publication identity.

A valid source publication reference contains exactly:

- `signal_id`
- `delivery_id`
- `mode`
- `published_at`
- `source_payload_hash`

Rules:

- all string fields must be non-empty;
- `published_at` must be an ISO-8601 UTC timestamp;
- `source_payload_hash` must be a lowercase 64-character SHA-256 hex value;
- the observer must not recalculate entry, stop, target, score, or confidence;
- identical source identity may be reused idempotently;
- the same `signal_id` with different source identity must be rejected.

`signal_id` and `delivery_id` remain opaque authority-owned identifiers.
Phase 07 must not derive or renumber them.

### 19.4 Paper Observation Identifier

`paper_observation_id` is deterministic.

It is derived as:

```text
identity_payload = {
  "schema_version": 1,
  "signal_id": source_publication_ref.signal_id,
  "delivery_id": source_publication_ref.delivery_id,
  "mode": source_publication_ref.mode,
  "source_payload_hash": source_publication_ref.source_payload_hash
}

paper_observation_id =
  "PSO-" + sha256(canonical_json(identity_payload)).hexdigest()
```

Canonical JSON rules:

UTF-8;
sorted object keys;
compact separators;
no NaN or Infinity;
no insignificant whitespace.

### 19.5 Observation Time Boundary

The observer consumes explicit deterministic timestamps.

Required fields:

observed_from
observed_until

Rules:

both are ISO-8601 UTC timestamps;
observed_until >= observed_from;
observed_from >= published_at;
the observer must not call the ambient system clock when deterministic
time is supplied;
completed observation evidence must not contain future candles relative
to observed_until.

### 19.6 Validity and Expiry Authority

Phase 07 does not define new mode-specific expiry durations.

The observation validity boundary is copied from the authoritative source
publication:

valid_until

Rules:

valid_until must be an ISO-8601 UTC timestamp;
expiry occurs when deterministic observation time is later than
valid_until;
the observer must not extend or shorten validity;
if an authoritative cancellation or invalidation was recorded earlier,
that event takes precedence over expiry.

### 19.7 Entry Touch Candle Contract

entry_touch_candle is either null or an object containing exactly:

symbol
interval
open_time
close_time
open
high
low
close
is_closed
source

Validation rules:

timestamps are ISO-8601 UTC;
close_time > open_time;
is_closed must be exactly true;
OHLC values must be finite numeric values;
high >= max(open, close, low);
low <= min(open, close, high);
symbol, interval, and source must be non-empty strings;
the candle symbol must match the source signal symbol;
candle ordering must be deterministic by close_time, then open_time;
open or incomplete candles must be rejected.

An entry touch exists when a valid closed candle range intersects the
immutable published entry zone.

It remains an observation only and must not create a fill or position.

### 19.8 Evidence Contract

evidence is an immutable object containing:

signal_geometry_hash
closed_candle_hashes
observation_event_hashes

Rules:

signal_geometry_hash is one lowercase SHA-256 hex string;
candle and event hashes are arrays of lowercase SHA-256 hex strings;
array order is deterministic and chronological;
duplicates are rejected;
the arrays may be empty;
raw mutable provider objects must not be retained by reference;
evidence cannot contain account, order, balance, or position-size data.

### 19.9 Acknowledgment Contract

acknowledgment is either null or an object containing exactly:

event_id
event_type
published_at
acknowledged_at
acknowledgment_latency_ms
source

Allowed event_type values:

ENTRY_REPORTED
SKIP_REPORTED

Rules:

event_id and source must be non-empty strings;
timestamps must be ISO-8601 UTC;
acknowledged_at >= published_at;
latency equals the exact integer millisecond difference;
latency must be non-negative;
booleans are invalid latency values;
the first valid acknowledgment is canonical;
duplicate identical events are idempotent;
a conflicting second acknowledgment must be rejected;
CLOSE_REPORTED is not a publication acknowledgment.

The acknowledgment object does not mutate the authoritative position
ledger.

### 19.10 Cancellation Contract

Phase 07 may record cancellation only from an explicit authoritative source
event.

Required cancellation fields:

event_id
reason_code
cancelled_at
source

Rules:

all strings must be non-empty;
cancelled_at must be ISO-8601 UTC;
cancelled_at >= published_at;
cancellation cannot be inferred from observer failure;
cancellation cannot be synthesized from replay evidence;
repeated identical events are idempotent;
conflicting cancellation events must be rejected.

The observer may independently classify market evidence as
TARGET_REACHED_BEFORE_ENTRY or INVALIDATED_BEFORE_ENTRY, but it must not
rewrite the authoritative publication lifecycle.

### 19.11 Observation State Transitions

Initial state:

OBSERVING

Allowed terminal transitions:

OBSERVING -> ENTRY_ZONE_TOUCHED
OBSERVING -> TARGET_REACHED_BEFORE_ENTRY
OBSERVING -> INVALIDATED_BEFORE_ENTRY
OBSERVING -> EXPIRED_UNTOUCHED
OBSERVING -> CANCELLED
OBSERVING -> OBSERVATION_AMBIGUOUS

All states other than OBSERVING are terminal within the canonical
completed observation record.

TERMINAL is an aggregate category only. It is not serialized as the
primary observation_state.

Terminal observations are immutable.

A later market candle must not rewrite an already completed canonical
observation.

### 19.12 Event Precedence

For closed candles ordered chronologically:

Process only candles whose close time is within the observation window.
Ignore candles before published_at.
An explicit authoritative cancellation event takes effect at its own
timestamp.
Before entry touch:
target touch first produces TARGET_REACHED_BEFORE_ENTRY;
invalidation touch first produces INVALIDATED_BEFORE_ENTRY;
entry-zone touch first produces ENTRY_ZONE_TOUCHED.
If entry and target or invalidation are first touched in the same closed
candle, produce OBSERVATION_AMBIGUOUS.
If target and invalidation are both first touched in the same candle
before entry, produce OBSERVATION_AMBIGUOUS.
If no earlier terminal event exists and validity expires, produce
EXPIRED_UNTOUCHED.

No intrabar ordering may be invented.

### 19.13 Fill Observation Mapping

The mapping is exact:

observation_state	fill_observation_status
OBSERVING	NOT_OBSERVED
ENTRY_ZONE_TOUCHED	ENTRY_ZONE_TOUCHED
TARGET_REACHED_BEFORE_ENTRY	TARGET_REACHED_BEFORE_ENTRY
INVALIDATED_BEFORE_ENTRY	INVALIDATED_BEFORE_ENTRY
EXPIRED_UNTOUCHED	EXPIRED_UNTOUCHED
CANCELLED	NOT_OBSERVED
OBSERVATION_AMBIGUOUS	AMBIGUOUS

No other mapping is permitted.

### 19.14 Content Hash Contract

content_hash is computed from the complete canonical observation payload
excluding only the content_hash field itself.

Included fields therefore include:

schema identity;
paper observation identity;
source publication reference;
classification and boundary fields;
immutable copied geometry;
observation window;
observation state;
fill observation status;
touch candle;
acknowledgment;
cancellation;
terminal reason;
evidence;
version metadata;
created_at.

created_at is an explicit deterministic input. It must not be generated
from the ambient clock inside canonical serialization.

Hash algorithm:

sha256(canonical_json(payload_without_content_hash))

Non-finite values must be rejected before hashing.

### 19.15 Evaluation Cycle Contract

A paper evaluation-cycle record contains:

schema_version: integer 1
source_evaluation_id
mode
evaluated_at
official_alert_signal_ids
rejection_reasons
content_hash

Rules:

source_evaluation_id is an opaque non-empty identifier supplied by the
authoritative evaluation caller;
identity key is (mode, source_evaluation_id);
evaluated_at must be ISO-8601 UTC;
official signal IDs are unique and deterministically sorted;
rejection reasons are normalized non-empty strings with deterministic
counts;
one evaluation cycle is either an official-alert cycle or a NO TRADE
cycle, never both;
official-alert cycle means at least one unique official signal ID;
NO TRADE cycle means zero official signal IDs;
duplicate identical cycles are idempotent;
conflicting reuse of the same identity key is rejected.

### 19.16 NO TRADE Aggregate Rules

For each enabled mode:

evaluation_cycles =
  count(unique accepted evaluation-cycle identities)

official_alert_cycles =
  count(cycles with at least one official signal ID)

no_trade_cycles =
  count(cycles with zero official signal IDs)

evaluation_cycles =
  official_alert_cycles + no_trade_cycles

When evaluation_cycles == 0:

no_trade_coverage_ratio = null

Otherwise:

no_trade_coverage_ratio =
  no_trade_cycles / evaluation_cycles

The aggregate ratio must be deterministically serialized and must not use
NaN or Infinity.

### 19.17 Official Signal Sample Counting

The canonical official sample identity is:

(mode, signal_id, delivery_id)

Rules:

count only accepted official source publications;
count each identity exactly once;
an identical duplicate is idempotent;
conflicting identity reuse is rejected;
canceled, skipped, expired, touched, or acknowledged signals remain part
of the official published sample;
replay-classified inputs never count;
evaluation cycles and NO TRADE records never count as official signals.

### 19.18 Progress Schema

The progress artifact contains exactly:

schema_version
schema_name
classification
execution_boundary
enabled_modes
official_signal_total
official_signal_count_by_mode
minimum_required_total
minimum_required_per_enabled_mode
evaluation_coverage_by_mode
observation_state_distribution
acknowledgment_summary
critical_lifecycle_defect_count
promotion_readiness
generated_at
content_hash

Rules:

enabled_modes is unique and ordered SWING, INTRADAY, SCALP;
disabled modes do not require a 30-signal minimum;
official total equals the sum of mode counts;
defect count is a non-negative integer and rejects booleans;
promotion readiness is derived, never caller supplied;
generated_at is an explicit deterministic input;
prohibited performance fields must be rejected.

### 19.19 Promotion Readiness Formula

promotion_readiness =
  official_signal_total >= 100
  AND every enabled mode has official_signal_count >= 30
  AND critical_lifecycle_defect_count == 0

At least one mode must be enabled.

Meeting the numerical gate does not authorize Shadow Release automatically.
It only marks the Phase 07 sample gate as satisfied for later audit and
owner review.

### 19.20 Artifact Roots and Isolation

Authorized Phase 07 roots are:

data/paper_signal/observations
data/paper_signal/evaluation_cycles
data/paper_signal/progress

The implementation must:

resolve and validate the configured paper root;
reject symlink ancestry;
reject replay roots;
reject production evidence roots;
reject paths outside the configured paper root;
publish completed artifacts atomically;
allow verified byte-identical reuse;
reject conflicting reuse.

Phase 07 must not write beneath:

replay artifact roots;
validated production snapshot roots;
production evidence roots;
delivery artifact roots;
Telegram state stores;
position ledger stores.

### 19.21 Exact RED Test Modules

The frozen RED test surface is:

tests/test_paper_signal_contract_v1.py
tests/test_paper_signal_observer_v1.py
tests/test_paper_signal_acknowledgment_v1.py
tests/test_paper_signal_progress_v1.py
tests/test_paper_signal_artifact_v1.py

Initial production module names are reserved as:

engine/paper_signal_contract_v1.py
engine/paper_signal_observer_v1.py
engine/paper_signal_acknowledgment_v1.py
engine/paper_signal_progress_v1.py
engine/paper_signal_artifact_v1.py

Tests must import these names directly.

No compatibility alias or alternate Phase 07 module family may be created
without a new design amendment.

### 19.22 Amendment Lock

This amendment closes the unresolved schema, identity, transition, time,
hash, evaluation-cycle, aggregation, and artifact-root contracts discovered
during the Step 05 audit.

RED tests may now assert these contracts exactly.

The amendment does not authorize implementation before the RED contract
suite is reviewed, committed, and proven to fail solely because the reserved
Phase 07 production modules do not yet exist.
