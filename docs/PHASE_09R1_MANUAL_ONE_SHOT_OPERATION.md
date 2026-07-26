# Phase 09R1 Manual One-Shot Operation

## Authority and operating mode

The owner-approved Phase 09R1 operating mode is manual-only one-shot
execution. One service start invokes the real
`engine.run_production_signal_v1` entrypoint exactly once, which executes one bounded production cycle and then exits.

This contract does not authorize a timer, cron job, boot enablement,
automatic restart, automatic retry, recurring cadence, polling loop, or
concurrent invocation. The Phase 09R1 service has no `[Install]` section and
must remain disabled.

The production destination is the owner-controlled private Telegram chat.
The accepted payload format is machine-readable JSON v1. No live trading or
order execution is authorized.

## Locked release and external runtime

The deployed unit must be rendered from
`deploy/systemd/ai-crypto-signal-agent.service.in`. Deployment replaces only:

- `@@PYTHON_BIN@@` with the absolute path of the already validated Python
  interpreter;
- `@@RELEASE_ROOT@@` with the absolute path of one immutable release created
  from an exact locked commit.

The rendered unit must pass `systemd-analyze verify` before installation.
The immutable release is source-only and read-only. It is used only through
`PYTHONPATH`; it is never the working directory and is never declared
writable.

The only runtime root is:

`/var/lib/ai-crypto-signal-agent/phase09r1`

All cwd-relative output and the configured production-signal, quota, slot,
and worker state paths remain beneath that runtime root. Production state
must not be copied from a canary, live gate, repository, or prior release.

The locked manual admission policy uses one quota admission and one slot for
the fixed release window. A change to the window or admission limits requires
a separately reviewed operational-contract change; operators must not
override these values ad hoc.

## Credential contract

The service loads credentials only from these root-owned files:

- `/etc/ai-crypto-signal-agent/phase09r1.env`
- `/etc/ai-crypto-signal-agent/deepseek.env`

The first supplies the supported Telegram token and owner-approved private
destination variables. The second supplies the supported DeepSeek API-key
variable. Credential values and the raw destination must never appear in a
unit, command argument, report, journal excerpt, process listing, repository
file, or release manifest.

## Operator procedure

1. Verify the rendered unit points to the exact immutable release and the
   validated Python interpreter.
2. Verify the credential files are regular, non-symlink, `root:root`, mode
   `0600`, without displaying their contents.
3. Verify the runtime root is external, writable only by the service identity,
   and contains fresh production state for the locked release.
4. Verify the unit is disabled, inactive, has `Type=oneshot`, `Restart=no`,
   exactly one `ExecStart`, and no associated timer.
5. Verify no other service or scanner process is active.
6. Start exactly once:

   `systemctl start ai-crypto-signal-agent.service`

7. Inspect service status and a sanitized journal without exposing credential
   values or the raw destination.
8. Confirm at most one Telegram attempt, one receipt at most, and no duplicate
   publication.
9. Confirm lifecycle release, zero active reservations, zero occupied slots,
   and no runtime artifact outside the external runtime root.
10. Preserve the service, runtime, lifecycle, journal, repository, and release
    evidence.

If Telegram delivery times out or is otherwise ambiguous after it may have
reached Telegram, do not retry and do not start the service again. Preserve
evidence and request owner review.

## Explicit prohibitions

The following command is prohibited:

`systemctl enable ai-crypto-signal-agent.service`

Automatic repeated start, manual retry after ambiguous Telegram delivery,
timer or cron creation, boot activation, automatic restart, automatic retry,
polling, sleeping loops, overlapping invocation, and recurring scheduling are
prohibited.

Phase 12 remains unauthorized. No Phase 10, Phase 11, or Phase 12 import,
launcher, service, deployment mechanism, or operational behavior may be
introduced through this contract.
