# F4 local monitoring

Run `/usr/local/sbin/ai-crypto-signal-agent-health` as root for the
credential-metadata, immutable-release, unit, trusted-marker, kill-switch,
overlap-lock, and disk-readiness assessment.

The F4-ready result is `HEALTH_STATUS=READY_NOT_ENABLED`. It requires the
service and timer to be inactive and the timer to be disabled.

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
