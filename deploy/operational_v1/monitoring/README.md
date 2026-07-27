# F4 local monitoring

Run `/usr/local/sbin/ai-crypto-signal-agent-health` as root for the
credential-metadata, immutable-release, unit, trusted-marker, kill-switch,
overlap-lock, and disk-readiness assessment.

The health command recognizes exactly two healthy terminal states:

- `HEALTH_STATUS=READY_NOT_ENABLED` requires the service to be inactive,
  the timer to be disabled and inactive, and no next timer elapse.
- `HEALTH_STATUS=READY_AND_AUTOMATION_ENABLED` requires the service to be
  inactive and the timer to be enabled, active, waiting, and scheduled for
  its next elapse with `Persistent=false`. Because both schedule directives
  are monotonic, readiness uses a finite future `NextElapseUSecMonotonic`;
  `NextElapseUSecRealtime=0` is valid. The current monotonic time comes from
  Python's `time.clock_gettime_ns(time.CLOCK_MONOTONIC)`. The first cycle is
  anchored by `OnActiveSec=30min` after timer activation; subsequent cycles
  are anchored by `OnUnitInactiveSec=30min` after service inactivity.

Both states require the same immutable-release, trusted-marker, unit,
credential, kill-switch, overlap-lock, disk, no-retry, and no-trading
checks. Every partial, inconsistent, or unknown state reports
`HEALTH_STATUS=NOT_READY` with sanitized reason codes. F4 installation must
leave and verify `READY_NOT_ENABLED`; later owner-authorized automation may
use `READY_AND_AUTOMATION_ENABLED`.

For sanitized unit metadata, use:

```text
systemctl show ai-crypto-signal-agent.service \
  -p ActiveState -p SubState -p Result -p NRestarts
```

For journal review, restrict output to the unit and do not copy environment
files, provider responses, Telegram responses, tokens, or destination
identifiers into tickets or evidence.

F4 performs no alerting network call. Operational artifacts under
`/var/lib/ai-crypto-signal-agent/operational-artifacts` have a 30-day
age-based retention policy.
