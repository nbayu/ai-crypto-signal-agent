# Phase 12 — Non-Secret Activation Configuration V1

Status: **Activation configuration V1 and coordinator integration committed and remotely locked; authorization-verifier, executable-default, and authorization-record parser changes are local, focused green, not committed or deployed**
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

### Authorization-record document parser

The local parser mechanism is implemented in engine/phase_12_activation_mode_authorization_record_parser_v1. It accepts caller-supplied document text only; it does not locate, load, authenticate, or trust a document source.

Public API:

    Phase12ActivationAuthorizationRecordDocumentErrorV1

    parse_phase_12_activation_authorization_record_v1(
        *,
        document: str,
    ) -> Phase12ActivationAuthorizationRecordV1

The document argument is keyword-only. The parser accepts neither file paths nor byte input, returns the existing immutable authorization-record type, and makes no authorization decision.

#### Strict parser document schema

The parser accepts exactly this ordered eight-line schema:

    schema_version=phase12-activation-authorization-record-v1
    mode=<MODE>
    owner_authorization_id=<VALUE>
    checkpoint_id=<VALUE>
    approved_locked_commit=<LOWERCASE_SHA1>
    approval_timestamp_utc=<UTC_Z_TIMESTAMP>
    expires_at_utc=<UTC_Z_TIMESTAMP>
    accepted_locked_commit=<LOWERCASE_SHA1>

The document has exactly eight lines, LF-only line endings, and exactly one terminal LF. Keys use the exact order and casing above. Every line has exactly one delimiter and a nonblank value. Comments, a BOM, CR or CRLF, leading or trailing whitespace, unknown, missing, duplicate, or reordered keys are rejected. This section contains placeholders only; it does not provide authorization evidence.

The schema version is exactly phase12-activation-authorization-record-v1. The only syntactically accepted modes are:

- CREDENTIAL_VALIDATION
- TELEGRAM_CONNECTIVITY_VALIDATION
- TELEGRAM_START_VALIDATION
- CONTROLLED_WORKLOAD

CLOSED, PRODUCTION, malformed modes, and unknown modes are rejected by parser syntax. Identifiers are lowercase alphanumeric and hyphen, length 1 through 64, with no whitespace or control characters.

Both commit fields are lowercase hexadecimal with exactly 40 characters, no prefix, abbreviation, uppercase, or whitespace. Their values may differ syntactically. Equality between approved and accepted commits is verifier policy responsibility, not parser responsibility.

Timestamps require strict UTC Z notation at second precision. Successful parsing returns timezone-aware UTC datetimes; local-time and offset variants are rejected. Calendar-invalid, padded, trailing, missing-Z, equal, and reversed timestamp values are rejected. The approval timestamp must be strictly earlier than the expiration timestamp.

#### Output, errors, and purity

A successful parse returns Phase12ActivationAuthorizationRecordV1 with its seven authorization-evidence fields only. The existing output remains immutable and slotted, has no __dict__, and has a fixed sanitized representation.

A malformed document raises Phase12ActivationAuthorizationRecordDocumentErrorV1 with the fixed text INVALID_AUTHORIZATION_RECORD_DOCUMENT. The error reveals no input content, identifier, checkpoint, commit, timestamp, mode, key, line number, or mismatch reason.

The parser is deterministic: repeated parsing of identical valid text produces equal immutable records. It has no filesystem or file-path access; environment or argv access; Git or subprocess; systemd; credential access; Telegram SDK; network; provider integration; logging; retry; cache; dynamic clock; or mutable registry.

#### Mechanism is not an approval source

The parser mechanism is implemented, but no production record locator, approval-document loader, ownership or permission authentication, trusted approval source, approval record deployment, or authorization-policy composition exists. The parser is not wired into the executable. Parsed records are not composed into the production verifier, whose production policy remains empty and fail-closed.

Parsing a syntactically valid record is not sufficient authorization and grants no operational authorization. The executable has no production approval record, loader, source, or parser wiring; every production-default non-CLOSED request remains fail-closed.

### Accepted-locked-commit marker document parser

The remotely locked syntax-only marker parser is implemented in
engine.phase_12_activation_mode_accepted_locked_commit_marker_parser_v1. It
accepts caller-supplied string text only: there is no file-path or byte-input
API. It returns one immutable marker and performs neither an authorization nor
an authenticity decision. It is implemented, tested, committed, pushed, and remotely locked at `a249fca1b0b7f7dd9644fd2ad015126e18a9d59f`; this remote lock is repository evidence only, not marker deployment or production trust.

Public API:

    Phase12ActivationAcceptedLockedCommitMarkerV1
    Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1

    parse_phase_12_activation_accepted_locked_commit_marker_v1(
        *,
        document: str,
    ) -> Phase12ActivationAcceptedLockedCommitMarkerV1

The marker has exactly two fields, schema_version and accepted_locked_commit.
It is immutable, frozen, slotted, keyword-only, and has no __dict__. Equality
is based on those two fields only. Its fixed sanitized representation is
Phase12ActivationAcceptedLockedCommitMarkerV1(); it contains no file path,
ownership, permissions, source metadata, authenticity, policy, or
authorization state.

#### Strict marker schema

The parser accepts exactly this ordered two-line document:

    schema_version=phase12-activation-accepted-locked-commit-marker-v1
    accepted_locked_commit=<LOWERCASE_SHA1>

It requires exactly two logical lines, exact key order and casing, exactly one
delimiter per line, LF-only endings, and exactly one terminal LF. Leading or
trailing blank lines, comments, a BOM, CR or CRLF, NUL or other control
characters, whitespace padding, blank values, and missing, duplicate, unknown,
or reordered keys are rejected.

The schema version is exactly
phase12-activation-accepted-locked-commit-marker-v1. The commit value is
exactly 40 lowercase hexadecimal characters (0-9 and a-f), with no uppercase,
prefix, abbreviation, whitespace, or control character.

#### Output, error, purity, and trust boundary

Malformed input raises
Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1 with the fixed text
INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_DOCUMENT. It reveals no document content,
commit, key, line number, mismatch reason, source, or filesystem detail.

Repeated parsing of identical valid text yields equal immutable markers. The
parser has no filesystem or marker-path access; environment or argv access; Git
or subprocess; systemd; credential access; Telegram SDK; network; provider
imports; logging; random or UUID; sleep; dynamic clock; retry; cache; or mutable
registry.

This slice owns marker-document syntax only. No marker document or canonical marker path is deployed, and no marker locator or reader exists. The separately bounded metadata inspector has no marker-reader, parser, source, trust, or authorization role. There is no trusted deployment release marker, accepted-commit production source, repository-HEAD or Git comparison, or deployment-authenticity decision. The executable static placeholder remains unchanged, the parser is operationally unwired, no verifier policy is populated, and parsing a syntactically valid marker string does not grant authorization.

### Accepted-locked-commit marker metadata validator

The pure local validator module is
`engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1`.
It validates already-supplied immutable metadata facts against already-supplied
immutable policy only. It is local, uncommitted, unpushed, undeployed, and
operationally unwired.

Public API:

    Phase12ActivationAcceptedLockedCommitMarkerMetadataV1
    Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1
    Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1
    Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1

    validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1(
        *,
        metadata: Phase12ActivationAcceptedLockedCommitMarkerMetadataV1,
        policy: Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1,
    ) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1

The frozen, slotted, keyword-only metadata model has no defaults and exactly
these ordered fields: `entry_kind`, `link_count`, `owner_uid`, `group_gid`,
`permission_mode`, and `size_bytes`. The equally frozen, slotted,
keyword-only policy model has no defaults and exactly: `expected_owner_uid`,
`expected_group_gid`, `required_permission_mode`, `required_link_count`, and
`maximum_size_bytes`. Both have fixed sanitized representations and exact
primitive validation.

The immutable result model has exactly `is_valid` and `failure_codes`.
`failure_codes` is an immutable tuple of known, unique codes in canonical
order. `is_valid=True` requires `()`, while `is_valid=False` requires at least
one code. The result reveals no path, UID, GID, mode, size, source, content,
commit, exception, or authorization evidence.

#### Exact-type decision and validation semantics

The accepted repair decision is **EXACT_TYPE_REJECTION_TAKES_PRECEDENCE**.
`entry_kind` accepts only exact `str`; numeric fields accept only exact `int`,
with `bool` rejected. Primitive subclasses and proxies are rejected before
equality, hashing, formatting, conversion, iteration, containment, or ordering
comparison can run. Metadata and policy subclasses may be declared for
adversarial testing, but subclass instances are rejected by validator exact
identity checks; there is no `isinstance` widening.

The accepted entry-kind vocabulary is `regular_file`, `symbolic_link`,
`directory`, and `other`. Counts, identifiers, and sizes are nonnegative;
permission modes are limited to `0` through `0o7777`.

All applicable mismatches are accumulated without short-circuiting in this
fixed order:

1. `NON_REGULAR_ENTRY`
2. `SYMBOLIC_LINK_ENTRY`
3. `LINK_COUNT_MISMATCH`
4. `OWNER_UID_MISMATCH`
5. `GROUP_GID_MISMATCH`
6. `PERMISSION_MODE_MISMATCH`
7. `MARKER_SIZE_EXCEEDS_MAXIMUM`

A symbolic link yields both entry-kind codes; `directory` and `other` yield
only `NON_REGULAR_ENTRY` from entry-kind evaluation. A size equal to the
maximum is valid, and a zero-byte regular file may be metadata-valid. Marker
syntax and content emptiness are outside this validator.

Malformed primitives, malformed public-model construction, and wrong validator
model types raise only
`Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1` with fixed text
`INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA`. No malformed value, field,
path, UID, GID, permission, size, source, commit, or dynamic evidence is
disclosed. There is no retry, fallback, partial result, logging, or cache.

This validator does not own canonical path selection or normalization,
stat/lstat or metadata acquisition, filesystem inspection, file opening,
bounded reads, decoding, marker parsing, accepted-commit source construction,
authenticity verification, repository revision comparison, approval-record
loading, policy composition, executable wiring, or authorization. It performs
no real filesystem metadata validation by default.

### Accepted-locked-commit marker metadata inspector

The local, unwired, undeployed metadata inspector is implemented in
`engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_inspector_v1`.
It acquires immutable metadata facts for one caller-supplied path only. It does
not select a canonical path, open or read marker content, parse a marker,
validate a metadata policy, construct an accepted-commit source, establish
authenticity, compare repository state, or authorize activation.

Public surface:

    Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1
    Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1

    inspect_phase_12_activation_accepted_locked_commit_marker_metadata_v1(
        *,
        path: str,
    ) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1

#### Path and filesystem boundary

Only an exact built-in `str` path is accepted. It must be nonempty, absolute,
and NUL-free. Subclasses, bytes, `pathlib.Path`, `os.PathLike`, proxies,
relative values, empty values, and NUL-containing values are rejected before
arbitrary interaction. Absolute non-normalized strings are forwarded verbatim:
repeated separators, `.` components, `..` components, a leading `//`, and a
trailing slash are not trimmed, normalized, expanded, resolved, canonicalized,
or rewritten. This component selects no canonical marker path.

The only filesystem operation is exactly:

    os.lstat(path)

Malformed paths cause zero calls; every other invocation causes exactly one.
The final symlink is inspected rather than followed. There is no `os.stat`,
preflight, fallback, retry, second metadata lookup, directory enumeration,
open, content read, decoding, or partial result.

#### Inspector-owned facts and mapping

`Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1` is
frozen, slotted, keyword-only, immutable, and has a fixed sanitized
representation. Its exact ordered fields are:

1. `entry_kind`
2. `link_count`
3. `owner_uid`
4. `group_gid`
5. `permission_mode`
6. `size_bytes`

The facts model is inspector-owned. It is field-compatible with the validator
facts only; it is not the validator-owned model.

The inspector reads only `st_mode`, `st_nlink`, `st_uid`, `st_gid`, and
`st_size`. Each must be an exact, nonnegative built-in `int`. It rejects bool,
int subclasses, floats, strings, proxies, coercible objects, negative values,
and missing attributes. There is no coercion, defaulting, synthesis, or partial
facts.

Entry kind is calculated exactly as:

    file_type = st_mode & 0o170000

- `0o100000` maps to `regular_file`.
- `0o120000` maps to `symbolic_link`.
- `0o040000` maps to `directory`.
- Every other value maps to `other`.

Permission mode is calculated exactly as:

    permission_mode = st_mode & 0o7777

File-type bits are excluded; conventional permission and special bits are
retained.

#### Errors, exceptions, and separation

The fixed public error representation is:

    Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1()

Its only error texts are:

- `INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_ABSENT`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PERMISSION_DENIED`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_SYMBOLIC_LINK_LOOP`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_COMPONENT_NOT_DIRECTORY`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_FILESYSTEM_INSPECTION_FAILED`
- `ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_MALFORMED_RESULT`

Errors reveal no path, errno, OS text, metadata value, field name, exception
detail, or host identity. Expected `OSError` conditions map to these sanitized
fixed errors, and native missing metadata attributes map to malformed result.
Unexpected ordinary exceptions propagate unchanged; `KeyboardInterrupt`,
`SystemExit`, and other `BaseException` values also propagate unchanged. There
is no broad `BaseException` catch, retry, fallback, logging, caching, or
partial fact.

The inspector does not import the metadata validator, construct or return the
validator facts model, invoke validation, evaluate policy, or produce an
authorization result. A future separately authorized composition boundary may
convert inspector facts into validator facts and invoke validation; no such
composition exists now.

#### Validation evidence and current posture

Accepted evidence for this bounded slice is:

- Expected RED: 58 failures caused solely by absent module/API.
- Isolated GREEN: 58 passed in 0.29s.
- Compilation: implementation and contract test passed.
- Combined focused regression: 460 passed in 8.81s.
- Full repository regression: 4,461 passed in 50.72s.
- Exact count correlation: 4,403 + 58 = 4,461.
- Failures, errors, skips, xfails, and retries: 0.

The first full-regression terminal result was indeterminate because terminal
evidence was lost; it was not a test failure. A separately authorized durable
recapture produced the accepted 4,461-pass evidence above.

Canonical activation configuration remains `CLOSED`. The production verifier
policy remains immutable, empty, and fail-closed, and the accepted-commit
placeholder remains unchanged. No canonical marker path exists, no real marker
was inspected, no marker content reader or accepted-commit source exists,
authenticity is not established, repository equality is not verified, and no
approval source, policy composition, executable wiring, or operational
authorization exists. The service remains disabled and all production gates
remain closed.

This slice does not introduce canonical path selection, marker deployment,
content reading or parsing, authenticity, repository-lock equality, approval
authority, policy population, inspector-to-validator composition, executable
integration, service activation, or production readiness.

### Canonical accepted-locked-commit marker path

The local, unwired, undeployed canonical marker-path component is implemented in
`engine.phase_12_activation_mode_accepted_locked_commit_marker_path_v1`. It
owns one project-defined marker location and returns it only as an immutable
value. It has no public error type, setter, override, registry, reader,
inspector, validator, source, policy, wiring, or authorization API.

Public surface:

    Phase12ActivationAcceptedLockedCommitMarkerPathV1

    get_phase_12_activation_accepted_locked_commit_marker_path_v1(
    ) -> Phase12ActivationAcceptedLockedCommitMarkerPathV1

#### Model, construction, and canonical literal

The exact model is:

    @dataclass(frozen=True, slots=True, kw_only=True, repr=False)
    class Phase12ActivationAcceptedLockedCommitMarkerPathV1:
        path: str

It has exactly one field, `path`, no default, no `__dict__`, frozen/slotted
keyword-only construction, equality by value, and immutable hash-compatible
value semantics. Its fixed sanitized representation is
`Phase12ActivationAcceptedLockedCommitMarkerPathV1()`.

`type(path)` must be the exact built-in `str`. A non-exact string type raises
empty `TypeError()` before hostile-subclass interaction. An exact string other
than the frozen literal raises empty `ValueError()`. Only the exact literal is
accepted, so no invalid public instance can be constructed. Errors and reprs
contain no supplied path or dynamic evidence.

The sole private source-code literal is:

    /var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker

It is an intentionally visible, non-secret project-owned value exposed through
`.path`. It is outside the Git working tree and separate from configuration and
credential files. Defining it does not establish that the marker or its parent
directory exists; neither has been created or inspected.

The literal is an exact built-in `str`, nonempty, absolute, NUL-free, has one
leading slash, and has no leading double slash, repeated separator, trailing
slash, `.` component, or `..` component. There is no normalization, trimming,
expansion, resolution, rewriting, environment lookup, or fallback. These
strict lexical rules apply only to this project-owned literal; they do not
alter the remotely locked metadata inspector, which accepts caller-supplied
absolute non-normalized paths verbatim.

#### Getter, effects, and separation

The zero-argument getter constructs a new immutable object each call. Repeated
values are equal, repeated identities are distinct, and the exact literal is
always returned deterministically. There is no I/O, cache mutation, clock,
randomness, logging, or external lookup.

This component is responsible only for owning the canonical literal and
returning it as a sanitized immutable value. It does not create directories or
marker files; test existence; inspect metadata; call `stat`, `lstat`, or `readlink`; follow
symlinks; enumerate parent directories; open or read content; parse a marker; invoke the metadata inspector,
validator, or parser; build a reader/source; establish authenticity; compare
repository state; load approval; compose policy; wire executables; authorize
activation; or mutate or activate services.

There is no import-time or call-time filesystem access, environment or argv
lookup, configuration or credential read, subprocess, systemd, network,
Telegram, provider, time, random, UUID, mutable-registry, or override state.
The component does not import or invoke the metadata inspector; that inspector
remains caller-path-only. A future separately authorized composition boundary
may obtain `.path` and pass it explicitly to the inspector. A future reader or
source may consume the path only through explicit caller input or such a
separately authorized boundary. Path selection and content reading remain
separate concerns.

#### Contract-test repair provenance

The initial isolated GREEN invocation produced 23 passed and 2 failed in
0.38s; implementation-related failures were zero. Both failures were contract
test defects: an impossible `"" not in ""` assertion after requiring an empty
sanitized `ValueError` message, and classification of standard Python
`__cached__` import metadata as a project-owned mutable cache.

The authorized test-only repair removed only the impossible empty-string
assertion while retaining the exact empty `ValueError()` contract and
nondisclosure checks for nonempty invalid values. It explicitly permits
standard dunder import metadata while preserving prohibitions on project-owned
cache, registry, override, setter, and reset behavior. The implementation hash
remained unchanged.

#### Validation evidence and current posture

Accepted evidence for this bounded slice is:

- Expected RED: 25 failed in 0.66s, solely because the frozen module/API was
  absent; internal errors and unexpected failures were zero.
- Initial GREEN: 23 passed and 2 contract-test defects failed in 0.38s; no
  implementation-related failure occurred.
- Repaired isolated GREEN: 25 passed in 0.21s; failures, errors, skips,
  xfails, retries, and internal errors were zero.
- Compilation: implementation and test passed; source hashes were unchanged.
- Combined focused regression: 485 passed in 7.94s, with exact correlation
  `74 + 60 + 48 + 97 + 58 + 25 + 49 + 55 + 19 = 485`; failures, errors,
  skips, xfails, retries, and internal errors were zero.
- The first full repository execution produced 4,486 passed in 48.56s with
  pytest status 0, but tee status was unavailable because `PIPESTATUS` was not
  captured atomically. That evidence was indeterminate, not a test failure.
- A durable recapture produced 4,486 passed in 49.32s with PIPESTATUS count 2,
  pytest status 0, tee status 0, and exact correlation
  `4,461 + 25 = 4,486`; failures, errors, skips, xfails, retries, and internal
  errors were zero.

The implementation SHA-256 is
`4e7abf88e62ec57e9d4e98408778d2cf8f61b673b4dfa2d8d93caca20224332a`.
The repaired test SHA-256 is
`3a5ebeba0998258397118503009d24894181516fdcc1477b8c0c28223d82b6ec`.

Canonical activation configuration remains `CLOSED`. The production verifier
policy remains immutable, empty, and fail-closed, and the accepted-commit
placeholder remains unchanged. The path component is unwired and undeployed;
no real marker or parent-directory inspection occurred. No reader, source,
composition, authenticity, repository comparison, approval, policy, wiring, or
operational authorization exists. The service remains disabled and all
production gates remain closed.

This slice does not establish marker or parent-directory existence, deployment,
ownership or permissions, metadata validity, content validity, accepted-commit
authenticity, repository equality, approval authority, a nonempty production
policy, executable wiring, operational authorization, service activation, or
production readiness.

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

Prior remotely locked authorization-verifier and executable-default regression evidence:

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

Authorization-record parser combined focused regression:

- Activation configuration reader: 74 passed.
- Authorization-record parser: 60 passed.
- Activation-mode authorization verifier: 49 passed.
- Activation-mode validation coordinator: 55 passed.
- Credential-aware executable: 19 passed.
- Total: 257 passed in 7.74s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

Authorization-record parser full repository regression:

- 4,258 passed in 53.37s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

The preceding authorization-record parser evidence is separately attributed to
the remotely locked authorization-record parser slice. It is not
accepted-locked-commit marker-parser regression evidence.

Accepted-locked-commit marker parser focused regression:

- 48 passed in 0.17s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

Accepted-locked-commit marker parser combined focused regression:

- Activation configuration reader: 74 passed.
- Authorization-record parser: 60 passed.
- Accepted-locked-commit marker parser: 48 passed.
- Authorization verifier: 49 passed.
- Mode-validation coordinator: 55 passed.
- Credential-aware executable: 19 passed.
- Total: 305 passed in 10.24s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

Accepted-locked-commit marker parser full repository regression:

- 4,306 passed in 51.33s.
- Failures: 0.
- Errors: 0.
- Skips: 0.
- Xfails: 0.
- Retries: 0.

The full repository count increased by exactly 48 from the prior 4,258 baseline because the new marker-parser suite contributes 48 tests. The marker-parser implementation and tests are committed, pushed, and remotely locked at `a249fca1b0b7f7dd9644fd2ad015126e18a9d59f`; they remain undeployed and operationally unwired. No marker document, canonical marker path, metadata inspector, source, reader, authenticity decision, policy composition, or operational authorization exists. No configuration, credential, Git, systemd, Telegram, network, runtime, or production action occurred.

Accepted-locked-commit marker metadata validator regression evidence:

- Isolated metadata-validator suite: 97 passed in 0.39s.
- Compilation: implementation and test compiled successfully; source hashes remained unchanged.
- Combined focused Phase 12 regression:
  - Activation configuration reader: 74 passed.
  - Authorization-record parser: 60 passed.
  - Accepted-locked-commit marker parser: 48 passed.
  - Marker metadata validator: 97 passed.
  - Authorization verifier: 49 passed.
  - Validation coordinator: 55 passed.
  - Credential-aware executable: 19 passed.
  - Total: 402 passed in 5.10s.
- Full repository regression: 4,403 passed in 48.65s.
- Failures, errors, skips, xfails, and retries: 0.

Count correlation for this validator slice:

- Previous remotely locked full baseline: 4,306.
- New validator contract tests: 97.
- Current total: 4,403.
- Exact delta: +97.

The preceding isolated marker-parser (48 passed in 0.17s), combined focused
(305 passed in 10.24s), and full repository (4,306 passed in 51.33s) evidence
remains separately attributed to the accepted-locked-commit marker-parser
slice; it is not metadata-validator regression evidence.

The coordinator commit remains remotely locked at
`cac05b1b63ee60e65bfe9f383f19d686cc422632`; the canonical `CLOSED` configuration remains deployed
and parser-validated, and the service remains disabled. The verifier and executable-default changes
are focused and full-regression green, but remain local, uncommitted, unpushed, and undeployed. The
production authorization policy remains empty, no approval record exists, and no non-`CLOSED` mode
is authorized. No service execution occurred, and no real credential, Telegram, network, runtime,
or production validation occurred.

Capability status for the current Phase 12 slices:

- Non-CLOSED authorization mechanism: **IMPLEMENTED_AND_TESTED**.
- Authorization-record document parser: **IMPLEMENTED_AND_REMOTELY_LOCKED**.
- Accepted-locked-commit marker parser: **IMPLEMENTED_AND_REMOTELY_LOCKED**.
- Marker document deployment: **MISSING**.
- Marker canonical path: **MISSING**.
- Marker locator: **MISSING**.
- Marker metadata inspector: **MISSING**.
- Marker metadata validator: **IMPLEMENTED_AND_REGRESSION_VALIDATED_LOCAL**.
- Marker reader/source: **MISSING**.
- Accepted-commit authenticity: **MISSING**.
- Production approval-record loader: **MISSING**.
- Production approval-record source: **MISSING / NOT AUTHORIZED**.
- Authorization-policy composition: **MISSING**.
- Production verifier policy: **IMPLEMENTED_BUT_EMPTY_FAIL_CLOSED**.
- Validator deployment: **LOCAL_UNCOMMITTED_UNPUSHED_UNDEPLOYED**.
- Marker parser deployment: **REMOTELY_LOCKED_BUT_UNWIRED_AND_UNDEPLOYED**.
- Operational authorization: **NOT_GRANTED**.

Fail-closed current state: no marker document, canonical marker path, metadata acquisition, real filesystem metadata validation, marker content read, source object, authenticity decision, approval record, policy composition, or executable wiring exists. The accepted-commit placeholder remains unchanged, the production policy remains empty, no mode is operationally authorized, canonical configuration remains `CLOSED`, the service remains disabled, and all production gates remain closed. The remotely locked parser and local validator are both unwired and do not establish production trust.

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
