# F4 rollback runbook

The sealed F4 evidence root contains the exact pre-install host state and
backup bytes. The rollback helper accepts that backup directory and restores
each managed path to its recorded `PRESENT` or `ABSENT` state.

Rollback does not start, restart, enable, reenable, preset, or otherwise
activate the service or timer. After restoring unit bytes, the operator may
run only `systemctl daemon-reload`, then verify that the service and timer
remain inactive and the timer remains disabled.

The remotely locked F4 commit and immutable release are retained. Rollback
does not rewrite Git history or remove sealed evidence.
