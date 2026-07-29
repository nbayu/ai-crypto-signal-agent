# E1 Source and Runtime Baseline Binding

## Document identity

- Roadmap: `POST_F5_FAST_TRACK_ROADMAP_EVALUATION_V1_0`
- Gate: `E1_DESIGN_FREEZE_AND_EVIDENCE_BINDING`
- Record state: `BASELINE_BOUND_OPEN_DECISIONS_PENDING`
- Created UTC: `2026-07-29T16:01:28Z`

## Development source authority

- Development base commit: `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`
- Development base tree: `cf57b96d250e181049d492f6a255bbed0fcdb11e`
- Base subject: `fix(signal): persist published signals for owner decisions`
- Source relationship:
  - scanner runtime commit `d263fbf2c218db846a46e015f4efbc30a14e4641`
  - historical healthy release `62cce8f3996c1059fb13cae2a20bd010c546c1ff`
  - development base `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`
- Required ancestry:
  `d263fbf2c218db846a46e015f4efbc30a14e4641 -> 62cce8f3996c1059fb13cae2a20bd010c546c1ff -> bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`

The fast-track development branch starts from `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`.
It preserves the post-activation published-signal registration fix and
the current Telegram owner-controller source.

## Observed production runtime topology

Production was observed as a healthy composite runtime:

- scheduled scanner unit launcher release:
  `d263fbf2c218db846a46e015f4efbc30a14e4641`
- effective scanner Python source:
  `d263fbf2c218db846a46e015f4efbc30a14e4641`
- Telegram owner-controller release:
  `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`
- retained historical healthy release:
  `62cce8f3996c1059fb13cae2a20bd010c546c1ff`
- trusted CP09 binding:
  `e50041f7296bd9e042f749b6a98393b3df9747a1`

This composite runtime is an observed operational fact. It is not silently
rewritten into a single-release claim.

## Production state observed during E1 audit

- scanner: natural scheduled cycle; no manual invocation requested;
- timer: enabled and operational;
- Telegram controller: active, running, restart count zero;
- active-signal ledger schema: version 2;
- active ledger state at observation:
  - one `ENTRY_ACTIVE`;
  - two `PUBLISHED_PENDING_ENTRY`;
  - all observed records were SWING;
- no audit command changed ledger or Telegram control state;
- no exchange order or automated-trading action was requested.

Runtime state values are observational and may change naturally after this
record. They are not frozen as configuration values.

## Compatibility decision

The development baseline is `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`, not the older scanner launcher
commit, because it:

1. is the authoritative fetched remote master;
2. directly descends from the retained historical release;
3. preserves Telegram update idempotency;
4. preserves owner-controller behavior;
5. adds published-signal registration required for owner decision binding;
6. leaves the inspected master-engine source unchanged relative to the
   historical activated release.

The incident-specific KMNO reconciliation module remains historical remediation.
It must not become a reusable normal signal lifecycle path.

## Current rollback boundary

Until E6 controlled activation, production remains unchanged.

The pre-fast-track rollback topology is the exact observed composite binding:

- scanner service launcher: `d263fbf2c218db846a46e015f4efbc30a14e4641`;
- Telegram controller: `bd28269dc49073e7e2c4c4bdb17266a6fe1f4c31`;
- timer remains enabled on its existing cadence;
- immutable release `62cce8f3996c1059fb13cae2a20bd010c546c1ff` remains retained;
- production ledger and owner-control state are not migrated during E1-E5.

Exact unit-file hashes, release inventory identities, installation procedure,
and rollback commands must be sealed before E6 activation.

## Non-negotiable invariants

1. Only owner-confirmed `ENTRY_ACTIVE` consumes one style slot.
2. One canonical pair may have at most one owner-confirmed active entry
   globally across modes and sides.
3. Telegram remains human-readable.
4. Entry, skip, and close remain manual owner decisions.
5. Automated scanning and automated signal delivery remain supported.
6. Automated trading and exchange-order execution remain prohibited.
7. No historical replay, long-cycle wait, or repeated live retry becomes an
   activation gate.
8. Historical immutable releases and evidence are never rewritten.
9. Python retains final deterministic publication authority.
10. LLMs may not create a candidate, alter geometry, or execute trading.

## Gate sequence

`E1 -> E2 -> E3 -> E4 -> E5 -> E6`

No gate is added, skipped, or silently reordered.

## E1 status

Completed evidence binding:

- local repository identity;
- authoritative remote identity;
- commit ancestry;
- post-activation delta;
- immutable release identities;
- effective scanner source provenance;
- effective controller source provenance;
- production no-mutation proof.

Still pending before E1 closure:

- D1 thesis fingerprint and lifecycle reset contract;
- D2 target/TP contract;
- D3 fresh-price, spread, age, and slippage contract;
- D4 exact trigger rules;
- D5 mode evaluation and armed-monitoring cadence;
- D6 DeepSeek decision effects;
- D7 Claude escalation and budget policy;
- D8 provider-failure publication policy;
- threat and failure model;
- exact release and rollback design.

No E2 implementation is authorized by this record.
