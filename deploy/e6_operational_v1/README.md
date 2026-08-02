# E6 operational activation package

This repository package has been created locally for review. It has not been
transferred, installed, enabled, started, deployed, canaried, cut over, rolled
back on a host, or activated. Merely reading these files performs no runtime or
host action.

## Exact Slice-09 repository paths

1. `engine/e6_activation_configuration_v1.py`
2. `deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once`
3. `deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-health`
4. `deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-rollback`
5. `deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.service.in`
6. `deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.timer`
7. `deploy/e6_operational_v1/README.md`
8. `deploy/e6_operational_v1/deployment-package-manifest.txt`
9. `tests/test_e6_activation_configuration_v1.py`
10. `tests/test_e6_operational_deployment_package_v1.py`

The package must be rendered into an immutable release directory whose basename
is its 40-character source commit. `.e6-release-manifest`,
`.e6-sha256-manifest`, `TRUSTED_E6_CHECKPOINT_COMMIT`, the installed release
reference, and the accepted-release marker must agree before a run is possible.
The documented render placeholders are `@@RELEASE_ROOT@@`,
`@@E6_SOURCE_COMMIT@@`, `@@E6_SOURCE_TREE@@`, and
`@@TRUSTED_CHECKPOINT_COMMIT@@`. No other placeholder is supported.

## Default-deny activation

The activation configuration is non-secret metadata. Credential metadata paths,
owners, groups, and modes may be checked; credential contents must never be read
or emitted by this package. E6 runtime and provider use are disabled by default.
These six gates are independent and false by default:

- `activation_gate`
- `workload_gate`
- `credential_gate`
- `network_gate`
- `publication_gate`
- `telegram_publication_gate`

No gate implies another. There is no enable-all option, provider substitution,
prompt repair, stale-review reuse, retry, legacy publication fallback, or
automated exchange-trading authority.

## Package roles

The run-once wrapper validates release bytes, checkpoint binding, activation
metadata, the kill switch, and a nonblocking overlap lock before invoking
`engine.run_production_signal_v1` exactly once. It implements no provider or
Telegram transport and performs no automatic rollback.

The health verifier is read-only. It classifies only an exact installed-but-
disabled state and an exact enabled/active/waiting timer state. It does not
create a lock or modify service state. Partial or contradictory state is not
ready.

The rollback tool is manual-only. It validates immutable current and target
releases and operates only on the explicit destination root. It preserves the
previous verified release reference and supports an exact idempotent replay. No
service-control operation is part of the transaction.

The service is a hardened `Type=oneshot` unit with `Restart=no` and a 20-minute
timeout. The timer uses the established 30-minute inactive cadence,
`Persistent=false`, and therefore has no boot catch-up. The overlap lock remains
the non-overlap authority. Nothing in this package enables or starts either
unit.

Publication creates only `PUBLISHED_PENDING_ENTRY` owner state. It does not
synthesize an owner decision. Owner-confirmed `ENTRY_ACTIVE` remains the sole
authority that consumes a slot or pair lock. Automated trading and exchange
orders are prohibited.

## Required future sequence

1. Slice 10: read-only final candidate audit.
2. Slice 11: exactly one final full regression.
3. Slice 12: owner-controlled canary and release.

Separate owner authorization is required before transfer, installation, any
service control, rollback execution, deployment, canary, cutover, or activation.
