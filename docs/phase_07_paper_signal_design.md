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
