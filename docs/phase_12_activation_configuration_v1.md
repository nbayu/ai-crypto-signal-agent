# Phase 12 — Non-Secret Activation Configuration V1

Status: **Implemented locally, focused green, not committed, not deployed**
Production state: **Gates closed**
Service state: **Disabled**
Canonical schema: `phase12-activation-v1`

## Purpose

This seam replaces executable hard-coded gate selection with a typed, non-secret configuration
file. The existing production launcher remains the authority for gate validation. Configuration
defects fail closed before credential lookup. The file carries no credentials and does not itself
authorize service start or enablement, networking, workload, publication, ledger mutation, or
trading.

## Canonical path and metadata

The fixed path is:

```text
/etc/ai-crypto-signal-agent/phase12-activation-v1.conf
```

The parent directory must be owned by `root:ai-crypto-signal-agent` with mode `0750`. The file
must be a regular, non-symlink file owned by `root:ai-crypto-signal-agent`, mode `0640`, with link
count exactly one. Maximum payload size is 4096 bytes, encoded as strict UTF-8 with exactly one
terminal LF. The real canonical file has not been created or deployed.

## Exact file schema

The file contains exactly seven ordered `KEY=VALUE` lines:

```text
schema_version=phase12-activation-v1
activation_mode=<MODE>
owner_authorization_id=<VALUE>
approval_checkpoint_id=<VALUE>
approved_locked_commit=<VALUE>
approved_at=<VALUE>
expires_at=<VALUE>
```

The parser rejects reordered, missing, duplicate, or unknown keys; blank lines; comments;
whitespace around `=`; interpolation or shell expansion; alternate key case; missing or multiple
terminal newlines; invalid UTF-8; and oversized input.

## CLOSED configuration

The canonical closed file is:

```text
schema_version=phase12-activation-v1
activation_mode=CLOSED
owner_authorization_id=NONE
approval_checkpoint_id=NONE
approved_locked_commit=NONE
approved_at=NONE
expires_at=NONE
```

`CLOSED` derives all five configurable gates as `False`.

## Modes and gate matrix

Accepted modes are `CLOSED`, `CREDENTIAL_VALIDATION`, `TELEGRAM_CONNECTIVITY_VALIDATION`,
`TELEGRAM_START_VALIDATION`, and `CONTROLLED_WORKLOAD`. Mode names are case-sensitive;
`PRODUCTION` is unsupported. Raw gate booleans are not accepted in the file.

| Mode | activation | credential | network | workload | telegram_start |
|---|---:|---:|---:|---:|---:|
| `CLOSED` | `False` | `False` | `False` | `False` | `False` |
| `CREDENTIAL_VALIDATION` | `True` | `True` | `False` | `False` | `False` |
| `TELEGRAM_CONNECTIVITY_VALIDATION` | `True` | `True` | `True` | `False` | `False` |
| `TELEGRAM_START_VALIDATION` | `True` | `True` | `True` | `False` | `True` |
| `CONTROLLED_WORKLOAD` | `True` | `True` | `True` | `True` | `True` |

`launcher_implementation_authorized=True` remains a repository-controlled constant and is not
operator-configurable.

## Evidence fields

For `CLOSED`, `owner_authorization_id`, `approval_checkpoint_id`, `approved_locked_commit`,
`approved_at`, and `expires_at` must all be exactly `NONE`.

For non-`CLOSED` modes, the two identifiers match `[a-z0-9][a-z0-9-]{0,63}`, and
`approved_locked_commit` is exactly 40 lowercase hexadecimal characters. Both timestamps use
`YYYY-MM-DDTHH:MM:SSZ` exactly: no numeric offset, fractional seconds, local time, or lowercase
`z`.

These fields are correlation metadata only. They are not signatures, authentication, proof of
owner authorization, proof of credential validity, or production authorization.

## Expiration

Maximum evidence lifetimes are:

| Mode | Maximum lifetime |
|---|---:|
| `CREDENTIAL_VALIDATION` | 15 minutes |
| `TELEGRAM_CONNECTIVITY_VALIDATION` | 15 minutes |
| `TELEGRAM_START_VALIDATION` | 10 minutes |
| `CONTROLLED_WORKLOAD` | 5 minutes |

`approved_at` must not be in the future. `expires_at` must be after `approved_at` and later than
current UTC. Excessive or expired lifetimes fail closed. Every non-`CLOSED` mode requires valid,
non-expired evidence.

## Cross-gate invariants

- Credential access requires activation.
- Network access requires activation and credential authorization.
- Telegram start requires activation, credential, and network authorization.
- Workload requires activation, credential, network, and Telegram-start authorization.
- No gate is valid unless repository-controlled launcher implementation authorization remains true.

## Reader API and safety

```python
load_phase_12_activation_configuration(
    *,
    configuration_path: str,
    now_utc: datetime,
    file_opener=_open_regular_configuration,
) -> Phase12ActivationConfigurationV1
```

The returned configuration is frozen, slotted, immutable, and structurally comparable. Loading
uses one opener invocation and one bounded read, with no retry, cache, or directory enumeration.
Descriptor-based no-follow handling enforces the filesystem contract. Ordinary failures expose
sanitized fixed codes; `BaseException` subclasses propagate. The reader has no logging,
environment enumeration, credential, SDK, network, or systemd-control dependency.

## Parser-only preflight

The parser-only CLI contract is:

```text
python -m engine.phase_12_activation_configuration_v1 \
  --check \
  --configuration-path <path>
```

Valid configuration:

```json
{"activation_configuration_result":"VALID"}
```

Exit status: `0`.

Invalid configuration:

```json
{"activation_configuration_result":"FAILURE"}
```

Exit status: `1`.

Unexpected ordinary failure:

```json
{"activation_configuration_result":"UNEXPECTED_FAILURE"}
```

Exit status: `70`.

This is parser-only. It performs no credential access, launcher call, SDK/network/runtime action,
or dynamic error/configuration disclosure. It has not been authorized against the canonical real
file.

## Executable integration

The credential-aware executable uses the fixed canonical path; it is not supplied by argv,
environment, `EnvironmentFile`, or `CREDENTIALS_DIRECTORY`.

Execution order is:

1. CLI argument validation.
2. UTC current-time acquisition.
3. Activation configuration load.
4. `CREDENTIALS_DIRECTORY` lookup.
5. Credential-locator validation.
6. Deferred credential-bridge construction.
7. Launcher dependency construction.
8. Launcher invocation.
9. Launcher tuple pass-through.

## Executable results

Configuration defect:

```json
{"executable_result":"ACTIVATION_CONFIGURATION_FAILURE"}
```

Exit status: `1`.

Unexpected ordinary executable or configuration failure:

```json
{"executable_result":"UNEXPECTED_FAILURE"}
```

Exit status: `70`.

After valid configuration, locator defects retain the existing fixed
`CREDENTIAL_LOCATOR_FAILURE` result. Valid launcher outcomes are returned unchanged. Dynamic
configuration values, evidence fields, paths, and exception internals are never emitted.

## Reachability and fail-closed behavior

A configuration defect prevents locator lookup, credential-bridge construction, launcher, SDK,
and network reachability. With valid `CLOSED` or partial modes, the launcher may return `BLOCKED`
before credential resolution. `CONTROLLED_WORKLOAD` permits the existing launcher to reach its
credential/composition seams under fakes and contracts, but does not itself authorize operational
use or persistent production operation.

No non-`CLOSED` configuration has been provisioned or operationally validated.

## Systemd integration

No systemd unit modification is required. The unit continues to invoke
`engine.phase_12_telegram_credential_aware_executable_v1`; the configuration path is
code-controlled. Credentials remain delivered only through `LoadCredentialEncrypted`. Gate values
and configuration contents are not carried in `Environment` or argv. `Restart=no` remains
unchanged, and the service remains disabled.

## Future operator workflow

This workflow is documented for a separately authorized future step and has not been executed:

1. Require the service to be inactive and disabled.
2. Prepare a root-owned temporary file inside the target parent.
3. Write the complete configuration atomically.
4. Set ownership `root:ai-crypto-signal-agent` and mode `0640`.
5. Run parser-only preflight against the temporary file.
6. Atomically rename it into the canonical path.
7. `fsync` the parent.
8. Run parser-only preflight against the canonical path.
9. Obtain separate owner adjudication before any service action.
10. Never update configuration while an invocation is active.

Deletion or absence fails closed.

## Rollback

Rollback is an atomic replacement with a validated `CLOSED` configuration. Alternatively, absence
causes configuration failure on the next invocation. Rollback does not reset systemd failed state
and does not automatically start, stop, reload, enable, or disable the service.

## Current validation evidence

- Activation-reader focused suite: 74 passed.
- Combined activation-reader and executable focused suite: 103 passed in 3.62s.
- Full repository regression: 4104 passed in 53.43s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.
- No real configuration file was accessed.
- No credential access occurred.
- No service or systemd mutation occurred.
- No Telegram, network, runtime, or production action occurred.
- Service remained disabled.
- Production gates remained closed.

## Production boundary

This implementation does not authorize creating or deploying a non-`CLOSED` configuration, service
start, service enablement, `reset-failed`, Telegram connectivity, polling, message sending,
workload execution, provider execution, signal publication, ledger mutation, trading, or persistent
production operation. Every operational action requires a later separately authorized step.
