# Phase 12 — Non-Secret Activation Configuration V1

Status: **Activation configuration V1 and coordinator integration committed and remotely locked; authorization-verifier and executable-default changes are local, focused green, not committed or deployed**
Production state: **Canonical configuration is `CLOSED`; all configurable gates are closed**
Service state: **Loaded, disabled, failed/failed (`MainPID=0`, `NRestarts=0)**
Canonical schema: `phase12-activation-v1`

## Purpose

This seam replaces executable hard-coded gate selection with a typed, non-secret configuration
file. The coordinator owns mode-specific validation dispatch; the existing production launcher
remains the authority for `CONTROLLED_WORKLOAD` preparation and gate validation. Configuration
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
terminal LF. The canonical `CLOSED` file is deployed, metadata-compliant, and parser-validated; no
non-`CLOSED` configuration has been deployed. One separately authorized installed-service `CLOSED`
validation completed with `{"launcher_result":"BLOCKED"}`. The service remains disabled; no
credential or network validation has been operationally executed.

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
or dynamic error/configuration disclosure. It was used in the separately authorized deployment and
validation of the canonical `CLOSED` file; this documentation step does not run it.

## Coordinator architecture and executable dispatch

The local, uncommitted coordinator module is
`engine.phase_12_activation_mode_validation_coordinator_v1`. It receives an already validated
activation configuration, verifies separate authorization for every non-`CLOSED` mode before any
effect-bearing dependency, owns exact mode dispatch, prevents implicit fallthrough, and applies a
fixed sanitized result taxonomy. It has no retry or cache; ordinary `Exception` failures are
sanitized and `BaseException` propagates according to the frozen implementation policy.

The coordinator is outside the unchanged production launcher. The credential-aware executable
forwards dependencies and returns coordinator tuples unchanged; it does not independently execute
mode-specific validation or directly dispatch the five configuration gates into the launcher. For
`CONTROLLED_WORKLOAD`, the coordinator delegates preparation/composition to the existing production
launcher exactly once. `launcher_implementation_authorized` remains repository-controlled.

The executable uses the fixed canonical path; it is not supplied by argv, environment,
`EnvironmentFile`, or `CREDENTIALS_DIRECTORY`. Its high-level order is:

1. CLI argument validation.
2. UTC current-time acquisition.
3. Activation configuration load.
4. For `CLOSED`, direct coordinator dispatch before credential-locator lookup.
5. For non-`CLOSED` modes, secure credential-locator prerequisite construction.
6. Deferred credential-reader construction.
7. Exactly one coordinator invocation.
8. Unchanged coordinator tuple return.

The executable supplies the coordinator with the validated configuration, separately trusted
accepted locked-commit context, authorization verifier, deferred credential reader, lexical
validator, identity-client factory, authenticated identity probe, application initializer,
application shutdown seam, and production-launcher dependency. It does not make an independent
authorization decision, invoke the production launcher separately, or use Git, argv, or an
activation environment variable to obtain the accepted commit. Current effect-bearing production
defaults are fail-closed; no concrete Telegram identity-probe or start-validation adapter is
implemented or deployed.

### Activation-mode authorization verifier

The local verifier module is `engine.phase_12_activation_mode_authorization_verifier_v1`. Its
public types are `Phase12ActivationAuthorizationRecordV1` and
`Phase12ActivationModeAuthorizationVerifierV1`.

The verifier is a pure, deterministic, immutable callable policy object. It receives `now_utc`
from its caller and returns only a boolean authorization decision. It performs no filesystem,
environment, Git, subprocess, systemd, credential, SDK, or network access. The coordinator remains
responsible for effect ordering, fixed authorization-failure result mapping, unexpected ordinary
failure mapping, BaseException behavior, and preventing effect-bearing dependency reachability
before authorization.

An authorization record has keyword-only construction and exactly these evidence fields:

- `mode`
- `owner_authorization_id`
- `checkpoint_id`
- `approved_locked_commit`
- `approval_timestamp_utc`
- `expires_at_utc`
- `accepted_locked_commit`

Records are immutable and slotted, have no dynamic attributes, and contain no credentials, tokens,
provider keys, endpoints, or runtime dependencies. Their representation is fixed and sanitized: it
reveals no field values. Record contents must not be rendered, logged, or emitted.

## Mode behavior and effect boundaries

### `CLOSED`

The coordinator returns:

```json
{"launcher_result":"BLOCKED"}
```

Exit status: `1`. It performs no authorization verification, locator lookup, credential read,
lexical validation, SDK/client construction, identity probe, application initialization or
shutdown, production-launcher call, or workload effect.

### `CREDENTIAL_VALIDATION`

Separate authorization is verified first. After success, the coordinator resolves the deferred
credential at most once and performs local lexical validation only. This does not claim Telegram
authentication, live-bot ownership, or Bot API reachability. It does not construct an SDK/client
or perform network, application, launcher, polling, worker, publication, ledger, or trading work.

Success:

```json
{"activation_mode_validation_result":"CREDENTIAL_VALID"}
```

Exit status: `0`. Controlled failure:

```json
{"activation_mode_validation_result":"CREDENTIAL_INVALID"}
```

Exit status: `1`.

### `TELEGRAM_CONNECTIVITY_VALIDATION`

Separate authorization, deferred credential resolution, and lexical validation occur before one
injected client construction and exactly one injected authenticated identity probe. The coordinator
does not poll, send a message, process updates, initialize an application, invoke the launcher,
or perform worker, provider, publication, ledger, trading, or persistent work.

Success:

```json
{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_VALID"}
```

Exit status: `0`. Controlled failure:

```json
{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_FAILURE"}
```

Exit status: `1`. The client and probe are injected seams only. No concrete production Telegram
identity-probe adapter is implemented, deployed, or operationally authorized.

### `TELEGRAM_START_VALIDATION`

Separate authorization, credential validation, and the injected identity probe precede bounded
injected application initialization. When initialization establishes a resource, injected shutdown
occurs exactly once as required by the coordinator contract. Polling initialization and persistence,
update processing, message dispatch, launcher invocation, worker/provider execution, publication,
ledger mutation, and trading are forbidden.

Success:

```json
{"activation_mode_validation_result":"TELEGRAM_START_VALID"}
```

Exit status: `0`. Controlled failure:

```json
{"activation_mode_validation_result":"TELEGRAM_START_FAILURE"}
```

Exit status: `1`. These are injected seams only: no concrete production start-validation adapter is
implemented, deployed, or operationally authorized.

### `CONTROLLED_WORKLOAD`

Separate authorization is verified first. The coordinator invokes the existing production launcher
exactly once and returns its tuple unchanged; the executable does not invoke it separately. The
current launcher remains preparation/composition only. This does not authorize polling, worker
execution, provider execution, publication, ledger mutation, trading, or persistent production
operation.

### Effect-capability matrix

`ALLOWED` below means only that the coordinator contract permits the listed injected seam. It does
not mean a concrete production adapter exists, that an operational action has been authorized, or
that a service should be started. `FORBIDDEN` is an explicit mode boundary.

| Capability | CLOSED | CREDENTIAL_VALIDATION | TELEGRAM_CONNECTIVITY_VALIDATION | TELEGRAM_START_VALIDATION | CONTROLLED_WORKLOAD |
|---|---|---|---|---|---|
| Activation configuration read | ALLOWED | ALLOWED | ALLOWED | ALLOWED | ALLOWED |
| Authorization verification | FORBIDDEN | ALLOWED | ALLOWED | ALLOWED | ALLOWED |
| Locator lookup | FORBIDDEN | ALLOWED | ALLOWED | ALLOWED | ALLOWED |
| Credential read | FORBIDDEN | ALLOWED | ALLOWED | ALLOWED | launcher-owned preparation only |
| Lexical validation | FORBIDDEN | ALLOWED | ALLOWED | ALLOWED | launcher-owned preparation only |
| SDK/client construction | FORBIDDEN | FORBIDDEN | ALLOWED (injected seam) | ALLOWED (injected seam) | launcher-owned preparation only |
| Authenticated identity probe | FORBIDDEN | FORBIDDEN | ALLOWED (one injected probe) | ALLOWED (one injected probe) | FORBIDDEN |
| Application initialization | FORBIDDEN | FORBIDDEN | FORBIDDEN | ALLOWED (injected seam) | FORBIDDEN |
| Application shutdown | FORBIDDEN | FORBIDDEN | FORBIDDEN | ALLOWED when initialization requires it | FORBIDDEN |
| Polling initialization | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Polling persistence | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Update processing | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Worker execution | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Provider execution | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Message dispatch | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Signal publication | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Ledger mutation | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Trading | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Persistent service operation | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |

## Authorization and credential boundary

A valid non-`CLOSED` configuration is not sufficient authorization. Before credential resolution,
client construction, network probe, application initialization, or launcher invocation, the
coordinator requires a separate authorization verifier and accepted locked-commit context.
Authorization rejection returns:

```json
{"executable_result":"ACTIVATION_MODE_AUTHORIZATION_FAILURE"}
```

Exit status: `1`. Authorization evidence and the accepted commit context are not emitted or logged,
are not taken from argv or activation environment variables, and remain separate from configuration
correlation metadata. Current production defaults fail closed.

### Exact authorization policy

The verifier returns `True` only when exactly one record matches all required evidence: an accepted
non-`CLOSED` mode, owner authorization ID, checkpoint ID, configuration-approved locked commit,
approval timestamp, expiration timestamp, separately supplied accepted locked commit, and the
current UTC validity window. The validity rule is exactly:

`approval_timestamp_utc <= now_utc < expires_at_utc`

It denies zero matches, duplicate exact matches, `CLOSED`, `PRODUCTION`, malformed or unknown
modes, empty or mismatched evidence, partial or prefix commit matches, naive timestamps, a time
before approval, a time at or after expiration, and malformed policy members. Configuration
evidence alone never authorizes a mode.

Authorization requires agreement among the configuration-approved locked commit, the separately
trusted accepted locked-commit context, the record-approved locked commit, and the record-accepted
locked commit. No live Git lookup occurs; accepted commit evidence is not read from environment or
argv, and it is not printed or logged. Configuration correlation metadata is not approval.

The executable injects the verifier through its existing keyword-only dependency seam and uses one
immutable verifier with an empty record tuple as its production default. No production authorization
record or record source exists. Therefore every production-default non-`CLOSED` request remains
rejected with:

```json
{"executable_result":"ACTIVATION_MODE_AUTHORIZATION_FAILURE"}
```

Exit status: `1`. Replacing the former raw always-false helper with this empty verifier does not open
a gate. The executable forwards configuration evidence and accepted-commit context to the
coordinator; it does not perform policy matching itself. CLOSED-before-locator behavior, deferred
credential reading, and unchanged coordinator-tuple pass-through remain preserved. No environment,
argv, filesystem, Git, systemd, credential, SDK, or network approval source is added.

Expected ordinary mismatches return `False` and the verifier emits no result tuple. Unexpected
ordinary exceptions propagate to the coordinator/executable boundary, which maps them to:

```json
{"executable_result":"UNEXPECTED_FAILURE"}
```

Exit status: `70`. BaseException propagates unchanged under the frozen boundary policy. There is no
retry, cache, fallback approval, first-match selection for duplicates, or dynamic mismatch reason.

For a non-`CLOSED` mode requiring credential capability, the executable validates only the secure
`CREDENTIALS_DIRECTORY` locator and constructs a deferred reader. It does not read credential
content before coordinator authorization. The coordinator resolves the reader at most once; a
non-string or empty result is rejected before lexical validation. Lexical validation does not prove
Telegram authentication. Credential values never appear in output, logs, documentation examples,
or exceptions.

## Result taxonomy

| Condition | Fixed result | Exit |
|---|---|---:|
| Activation configuration failure | `{"executable_result":"ACTIVATION_CONFIGURATION_FAILURE"}` | `1` |
| Credential locator failure | `{"executable_result":"CREDENTIAL_LOCATOR_FAILURE"}` | `1` |
| Authorization failure | `{"executable_result":"ACTIVATION_MODE_AUTHORIZATION_FAILURE"}` | `1` |
| CLOSED | `{"launcher_result":"BLOCKED"}` | `1` |
| Credential success | `{"activation_mode_validation_result":"CREDENTIAL_VALID"}` | `0` |
| Credential controlled failure | `{"activation_mode_validation_result":"CREDENTIAL_INVALID"}` | `1` |
| Connectivity success | `{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_VALID"}` | `0` |
| Connectivity controlled failure | `{"activation_mode_validation_result":"TELEGRAM_CONNECTIVITY_FAILURE"}` | `1` |
| Start success | `{"activation_mode_validation_result":"TELEGRAM_START_VALID"}` | `0` |
| Start controlled failure | `{"activation_mode_validation_result":"TELEGRAM_START_FAILURE"}` | `1` |
| Unexpected ordinary failure | `{"executable_result":"UNEXPECTED_FAILURE"}` | `70` |

Success outcomes exit `0`; controlled failures exit `1`; unexpected ordinary failures exit `70`.
`BaseException` propagates according to the frozen implementation policy. There is no retry and no
dynamic exception, credential, path, authorization, configuration, or evidence detail in results.

## Systemd integration

No systemd unit modification is required. The unit continues to invoke
`engine.phase_12_telegram_credential_aware_executable_v1`; the configuration path is
code-controlled. Credentials remain delivered only through `LoadCredentialEncrypted`. Gate values
and configuration contents are not carried in `Environment` or argv. `Restart=no` remains
unchanged, and the service remains disabled.

## Future operator workflow

The canonical `CLOSED` deployment used this atomic pattern in a separately authorized step. The
following workflow remains frozen for a future non-`CLOSED` update and is not authorized by this
document:

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

Previously committed activation-configuration evidence for the remotely locked baseline:

- Activation-reader focused suite: 74 passed.
- Activation-reader plus prior executable focused suite: 103 passed in 3.62s.
- Prior full repository regression: 4104 passed in 53.43s.
- Failures, errors, skips, xfails, and retries: 0.

Previously accepted coordinator and executable-integration regression evidence:

- Activation configuration reader: 74 passed.
- Coordinator: 55 passed.
- Executable: 18 passed.
- Combined focused: 147 passed in 4.43s.
- Full repository regression: 4148 passed in 46.41s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

The coordinator and executable integration are focused and full-regression green and remotely
locked, but are not deployed to the installed service. The canonical `CLOSED` configuration is
deployed and parser-validated, and the one separately authorized installed-service `CLOSED`
validation produced `{"launcher_result":"BLOCKED"}`. No non-`CLOSED` configuration was
operationally deployed or validated, and no real credential, Telegram, network, runtime, workload,
publication, ledger, trading, or production validation was executed for the coordinator change. The
service remains disabled and production gates remain closed.

Current local authorization-verifier and executable-default regression evidence:

- Activation configuration reader: 74 passed.
- Authorization verifier: 49 passed.
- Mode-validation coordinator: 55 passed.
- Executable: 19 passed.
- Combined focused: 197 passed in 3.72s.
- Full repository regression: 4198 passed in 44.28s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

The coordinator commit remains remotely locked at
`cac05b1b63ee60e65bfe9f383f19d686cc422632`; the canonical `CLOSED` configuration remains deployed
and parser-validated, and the service remains disabled. The verifier and executable-default changes
are focused and full-regression green, but remain local, uncommitted, unpushed, and undeployed. The
production authorization policy remains empty, no approval record exists, and no non-`CLOSED` mode
is authorized. No service execution occurred, and no real credential, Telegram, network, runtime,
or production validation occurred.

Capability status for this local slice:

- Non-CLOSED authorization mechanism: **IMPLEMENTED_AND_TESTED**.
- Production authorization policy: **IMPLEMENTED_BUT_EMPTY_FAIL_CLOSED**.
- Production approval-record source: **MISSING / NOT AUTHORIZED**.
- Operational authorization: **NOT GRANTED**.

## Rollout and rollback policy

Configuration begins and ends as `CLOSED`. At most one non-`CLOSED` mode may be deployed in one
separately authorized step, with strict expiry and parser preflight. The service remains disabled;
any authorized observation uses one start only, no retry, bounded journal evidence, and immediate
atomic rollback to `CLOSED`. There is no automatic escalation between modes and no `reset-failed`
unless separately authorized.

## Production boundary

This change does not authorize deployment of a non-`CLOSED` configuration; credential validation
against real credentials; Telegram identity probing; Telegram application initialization; polling;
message sending; update processing; worker or provider execution; publication; ledger mutation;
trading; service start or enablement; `reset-failed`; or persistent production operation. Every
such operational action requires a later separate authorization.

The authorization-verifier slice also does not authorize approval-record deployment, non-`CLOSED`
configuration deployment, real credential reading, Telegram connectivity or start validation,
service execution, polling, update handling, worker/provider execution, publication, ledger
mutation, trading, controlled workload execution, or production activation. Every operational
approval remains a later separately authorized step.
