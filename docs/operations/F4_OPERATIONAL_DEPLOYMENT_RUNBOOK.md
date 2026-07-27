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
