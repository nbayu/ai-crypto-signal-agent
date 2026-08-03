# E6 operational deployment package v2

This package renders one immutable E6 release through the pure
`e6-deployment-state-binding-v1` authority. A deployment binding is derived
only from `DEPLOYMENT_PROFILE` plus one exact lowercase 40-hex release commit.
It does not inspect Git, accept arbitrary path overrides, or contain secret
values.

## Authority progression

The only supported operational progression is:

`CURRENT_LEGACY`
→ `R41_DISABLED_VERSIONED_CANDIDATE`
→ `R42_ONE_CANARY`
→ `R44_PRODUCTION_PROFILE_CUTOVER`
→ `ROLLBACK`

R41 installs only a disabled, inactive `CANDIDATE_CANARY`. R42 may authorize
exactly one candidate invocation while legacy production remains the sole
authoritative publisher and scheduler. The `PRODUCTION` profile is reserved
for a separately authorized R44 writer freeze and cutover. No script in this
package automatically stops, starts, enables, disables, presets, or reloads a
legacy unit.

## Candidate canary profile

For `<commit40>`, the renderer produces:

- `ai-crypto-signal-agent-e6-candidate-<commit40>.service` and matching timer;
- `/var/lib/ai-crypto-signal-agent-e6-candidate-<commit40>` state;
- `/run/ai-crypto-signal-agent-e6-candidate-<commit40>` runtime and lock;
- `/var/cache/ai-crypto-signal-agent-e6-candidate-<commit40>` cache;
- `/var/lib/ai-crypto-signal-agent-e6-installations/<commit40>` control and
  release pointers; and
- `/etc/ai-crypto-signal-agent/e6-candidates/<commit40>` nonsecret activation
  and credential-metadata files.

The old E6 installation is preserved as non-authoritative operational evidence.
Candidate owner state, active ledger, publication evidence, dispatch evidence,
audit, E4 history, and provider-usage state start empty and non-authoritative.
They are candidate-confined and disposable. Candidate state is never imported
or promoted into production. The older disabled canonical E6 installation and
its evidence are preserved; the versioned candidate unit names do not replace
`ai-crypto-signal-agent-e6.service` or `ai-crypto-signal-agent-e6.timer`.

## Production profile

The production unit identities are stable and separate:

- `ai-crypto-signal-agent-e6-production.service`;
- `ai-crypto-signal-agent-e6-production.timer`;
- `/run/ai-crypto-signal-agent-e6-production` runtime;
- `/var/cache/ai-crypto-signal-agent-e6-production` cache; and
- `/var/lib/ai-crypto-signal-agent-e6-production-control` release control.

At R44, after an exact writer freeze, the profile rebinds the existing
authoritative state in place:

- `/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json`;
- `/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/active-signal-ledger-v2.json`;
- `/var/lib/ai-crypto-signal-agent/phase09r1/production-signals`; and
- `/var/lib/ai-crypto-signal-agent/operational-artifacts`.

There is no raw live-state copy, empty production initialization, candidate
state promotion, owner-state reset, active-ledger reset, slot reset, pair-lock
reset, or publication-history replacement. Rollback retains valid
post-cutover owner and ledger transitions in the same authoritative location.
Same-day accepted Claude canary usage requires deterministic reconciliation
from accepted evidence before production authority; raw candidate usage state
is not promoted.

## Ownership and modes

Candidate state and runtime roots are
`ai-crypto-signal-agent:ai-crypto-signal-agent:0750`. Private mutable
directories are `0700`; mutable files and the runtime lock are `0600`; the
cache is `0700`. Control and configuration parents are
`root:ai-crypto-signal-agent:0750`; install and rollback pointers are `0440`;
the accepted marker is `root:root:0400`; activation and credential metadata are
`ai-crypto-signal-agent:ai-crypto-signal-agent:0640`. Logs use journald only.

Provider and Telegram secret environment files remain external
`root:root:0600` read-only inputs. The package validates only their metadata;
secret contents never enter activation metadata, unit arguments, health
output, the package manifest, or release identity.

## Rendering and launch

The candidate service and timer templates use deterministic `@@...@@`
placeholders supplied from the validated binding. The production templates use
stable production identities and the same immutable release placeholder. The
run-once wrapper re-derives every path and unit from the activation profile and
commit, compares every supplied field, verifies immutable release bytes, and
uses a nonblocking profile-specific lock. Automatic retry is zero.

Systemd is only the UTC minute heartbeat:

- `OnCalendar=*-*-* *:*:00 UTC`;
- `AccuracySec=1s`; and
- `Persistent=false`.

Python remains the due-window and mode scheduling authority. A healthy process
exit 0 may mean `NO_WORK`, `NO_TRADE`, or `NO_MODE_JOB_DUE`.

## Health and rollback

Health requires `--deployment-profile` and `--release-commit`. Candidate health
checks exact versioned units, immutable release parity, binding parity,
ownership/modes, empty candidate owner/ledger state, an absent or unheld
candidate lock, disabled/inactive candidate units, and continuing legacy timer
authority. It performs no run-once, service cycle, provider call, Telegram
send, publication, lifecycle transition, slot/pair-lock mutation, or order.

Rollback requires the same exact profile and bound commit. Candidate rollback
can change only its commit-versioned control namespace. Production rollback
changes only production release-control evidence while preserving in-place
authoritative state. Neither path touches legacy units, old canonical E6 units,
or the old `/var/lib/ai-crypto-signal-agent/e6-installed-release.path`.

Provider execution, Telegram delivery, canary execution, production activation,
and scheduler cutover remain separate owner-authorized gates. No arbitrary
environment or path override is supported.
