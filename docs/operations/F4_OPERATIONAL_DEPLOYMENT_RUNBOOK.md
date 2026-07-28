# F4 operational deployment runbook

F4 installs but does not enable or start automated operation. The immutable
release is built from the remotely locked F4 commit and installed under:

```text
/opt/ai-crypto-signal-agent-releases/<F4 commit>
```

The installer receives that absolute release path. It atomically installs
the rendered oneshot service, disabled timer, local health command, retention
policy, release reference, and trusted CP09 runtime marker. It does not call
`systemctl`.

After installation, the F4 operator may run only:

```text
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/ai-crypto-signal-agent.service \
  /etc/systemd/system/ai-crypto-signal-agent.timer
/usr/local/sbin/ai-crypto-signal-agent-health
```

The required F4 state is:

- service inactive and static or disabled;
- timer inactive and disabled, with no next elapse;
- health status `READY_NOT_ENABLED`;
- no production entrypoint call;
- no service or timer start;
- no timer enablement.

F5 owner authorization is required before any controlled canary or
enablement.

The owner-blueprint release additionally stages
`ai-crypto-signal-agent-telegram-control.service` and its libexec wrapper.
Installation does not daemon-reload, enable, or start either unit. FT3 must
create `/etc/ai-crypto-signal-agent/owner-control.env` as root:root `0600`,
perform the tested state migration, and verify `READY_NOT_ENABLED` before any
explicit owner activation. Autonomous scanner delivery does not consult the
legacy `f4-operational-cycle` quota; legacy quota state remains untouched for
the explicit `/scan` and manual one-shot scope.
