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

### Accepted-locked-commit marker reader

The local, unwired, undeployed reader component is implemented in
`engine.phase_12_activation_mode_accepted_locked_commit_marker_reader_v1`.
It is an explicit caller-path, bounded raw-byte acquisition boundary only. Its
`__all__` contains exactly:

    Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1
    Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1
    read_phase_12_activation_accepted_locked_commit_marker_v1

All implementation-only names are underscore-prefixed. There is no
canonical-path getter, metadata inspector or validator API, parser API,
composition API, authenticity API, policy API, wiring API, or authorization
API in this component.

#### Facts model and reader signature

The exact facts model is:

    @dataclass(frozen=True, slots=True, kw_only=True, repr=False)
    class Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1:
        content_bytes: bytes

It has exactly one field, `content_bytes`, no default, no `__dict__`,
frozen/slotted keyword-only construction, equality by value, and immutable
hash-compatible value semantics. Its fixed sanitized representation is
`Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1()`.

`content_bytes` must be exact built-in `bytes`; non-exact values, including
subclasses, `bytearray`, `memoryview`, and proxies, are rejected before hostile
interaction with empty `TypeError()`. Exact byte strings of lengths 0 through
4096 are accepted. Exact byte strings longer than 4096 are rejected with empty
`ValueError()`. No decoding, copying, trimming, parsing, content mutation, or
newline normalization occurs, and no content appears in an error or repr.

The exact reader signature is:

    read_phase_12_activation_accepted_locked_commit_marker_v1(
        *,
        path: str,
    ) -> Phase12ActivationAcceptedLockedCommitMarkerReadFactsV1

`path` is required and keyword-only. It must be exact built-in `str`, nonempty,
absolute, and NUL-free. A valid caller value is used verbatim: there is no
trimming, normalization, expansion, resolution, canonical-path lookup,
environment lookup, configuration lookup, or fallback. Invalid paths raise the
fixed sanitized reader error code
`INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH` without caller evidence.

#### Bounded I/O and error contract

The reader uses exactly these flags:

    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK

Its lifecycle is exactly one `os.open(path, flags)`, validation that the result
is an exact nonnegative built-in `int` descriptor, one `os.read(fd, 4097)`, and
one `os.close(fd)`. Close is attempted exactly once for every validated
descriptor. There is no preflight; `stat`, `lstat`, builtin `open`, pathlib,
existence check, readlink, retry, read loop, fallback, second open, second read,
or second close.

The reader requests 4097 bytes. Raw exact built-in bytes of lengths 0 through
4096 are returned unchanged. A 4097-byte read result raises
`ACCEPTED_LOCKED_COMMIT_MARKER_READ_TOO_LARGE`. A malformed descriptor, read
result, or otherwise-successful close result raises
`ACCEPTED_LOCKED_COMMIT_MARKER_READ_MALFORMED_RESULT`; exact-type checks occur
before arbitrary interaction with hostile values.

`Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1` is a fixed,
sanitized, immutable error with representation
`Phase12ActivationAcceptedLockedCommitMarkerReadErrorV1()`. Its string is one
of exactly these codes, and it never includes a path, content, errno message,
descriptor, host detail, or other dynamic evidence:

    INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_ABSENT
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_PERMISSION_DENIED
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_SYMBOLIC_LINK_REJECTED
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_COMPONENT_NOT_DIRECTORY
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_OPEN_FAILED
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_FAILED
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_CLOSE_FAILED
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_TOO_LARGE
    ACCEPTED_LOCKED_COMMIT_MARKER_READ_MALFORMED_RESULT

For `os.open`, `FileNotFoundError` or `ENOENT` maps to
`ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_ABSENT`; `PermissionError`, `EACCES`,
or `EPERM` maps to `ACCEPTED_LOCKED_COMMIT_MARKER_READ_PERMISSION_DENIED`;
`ELOOP` maps to `ACCEPTED_LOCKED_COMMIT_MARKER_READ_SYMBOLIC_LINK_REJECTED`;
`ENOTDIR` maps to
`ACCEPTED_LOCKED_COMMIT_MARKER_READ_PATH_COMPONENT_NOT_DIRECTORY`; all other
`OSError` values map to `ACCEPTED_LOCKED_COMMIT_MARKER_READ_OPEN_FAILED`.
Any read `OSError` maps to `ACCEPTED_LOCKED_COMMIT_MARKER_READ_FAILED`; a close
`OSError` after an otherwise successful valid read maps to
`ACCEPTED_LOCKED_COMMIT_MARKER_READ_CLOSE_FAILED`. `os.close` must return exactly
`None`; a non-`None` result is malformed. Ordinary non-`OSError` exceptions and
`BaseException` values from `os.open` propagate unchanged; no descriptor exists
for cleanup in that case.

A prior read outcome wins over a later close failure. Thus a mapped read error,
ordinary read exception, `BaseException` read outcome, oversized result, or
malformed read result remains controlling after one cleanup attempt. Ordinary
and `BaseException` read outcomes propagate unchanged after that cleanup
attempt. Close controls only after an otherwise successful valid read: a
malformed close return maps to `MALFORMED_RESULT`, while ordinary and
`BaseException` close outcomes then propagate unchanged. No suppressed cleanup
evidence is disclosed.

#### Boundaries, separation, and non-goals

Successful reading establishes only bounded acquisition of raw bytes from an
explicit caller-supplied path. It does not establish canonical path selection,
marker existence before the attempt, metadata validity, ownership legitimacy,
permission or file-type safety, freshness, source legitimacy, content validity,
commit-hash interpretation, authenticity, approval, repository equality, policy
satisfaction, or operational authorization. `O_NONBLOCK` does not prove
regular-file safety.

The reader imports or invokes none of the canonical marker-path component,
metadata inspector, metadata validator, marker parser, authorization verifier,
validation coordinator, or credential-aware executable. It performs no
metadata inspection or validation, decoding, parsing, canonical-path selection,
authenticity verification, repository comparison, approval lookup, policy
composition, executable wiring, or service action. Canonical-path-to-reader,
parser, and all higher-level composition remain absent and require separately
authorized gating. The separately documented metadata validation composition
does not involve this reader.

There is no import-time filesystem action, canonical-marker access, environment
or argv lookup, configuration or credential read, logging, subprocess, systemd,
Telegram, network, provider, clock, random, UUID, sleep, mutable registry, or
override mutation. The reader does not create or deploy a marker. This slice is
not a production-readiness claim and does not establish canonical-path-to-reader
composition, metadata composition, parser composition, authenticity,
repository comparison, an approval source, policy composition, executable
wiring, operational authorization, service activation, or production readiness.

#### Contract-test repair provenance and validation evidence

The expected RED contract run collected 25 tests and produced 25 failures in
0.97s, exit 1, solely because the frozen reader module/API was absent
(`EXPECTED_ABSENT_ACCEPTED_LOCKED_COMMIT_MARKER_READER_MODULE_OR_PUBLIC_API`).
It had zero internal errors and zero unexpected failures.

The initial GREEN produced 21 passed and 4 failed in 0.33s; implementation
defects were zero. The four failures were test defects only: direct non-exact
facts construction incorrectly expected the reader error rather than empty
`TypeError()`; direct oversized facts construction incorrectly expected the
reader error rather than empty `ValueError()`; a parser-separation guard rejected
the required `accepted_locked_commit` public-name substring; and a global
monkeypatch guard detected its own literal.

The authorized test-only repair corrected those four expectations/guards while
preserving the distinct direct-model and reader-I/O contracts, precise
parser/content-interpretation separation, and global-monkeypatch safety. The
required public names remain permitted. No contract weakening, skip, xfail,
retry, or bypass occurred; the repaired suite retained exactly 25 tests. The
implementation hash remained unchanged. Repaired isolated GREEN was 25 passed
in 0.29s with zero failures, errors, skips, xfails, retries, and internal errors.

Compilation covered exactly the implementation and contract test once; it
exited 0 with empty stdout and stderr. Both compiled and source hashes remained
unchanged. `py_compile` generated exactly two attributable reader-specific
`.pyc` files; both were removed, and no bytecode remains. This evidence does
not claim that `PYTHONDONTWRITEBYTECODE` prevents `py_compile` output.

The initially proposed focused total of 216 was blocked before execution
because it conflicted with locked adjacent-suite counts; it was provenance, not
a failed regression. The authoritative correlation is marker parser 48,
metadata validator 97, metadata inspector 58, canonical marker path 25, and
marker reader 25: `48 + 97 + 58 + 25 + 25 = 253`. The corrected single focused
run collected and passed 253 tests in 1.12s with zero failures, errors, skips,
xfails, retries, and internal errors; source hashes and adjacent locked tests
remained unchanged.

The durable full repository regression used one pytest and one tee process:

    set -o pipefail
    PYTHONDONTWRITEBYTECODE=1 /opt/ai-crypto-signal-agent/.venv/bin/python -m pytest -q \
      2>&1 | tee /tmp/phase12_marker_reader_full_regression.log
    statuses=("${PIPESTATUS[@]}")

The `PIPESTATUS` array was captured atomically, immediately after the pipeline,
with two elements. Pytest status and tee status were both 0. The prior locked
full count was 4,486; the reader adds 25: `4,486 + 25 = 4,511`. The run passed
4,511 tests in 62.61s with zero failures, errors, skips, xfails, retries, and
internal errors. Its external temporary log was created outside the repository,
evidence was extracted, and the log was removed. Source hashes and all tracked
repository content remained unchanged.

The implementation SHA-256 is
`dd22d4fdd647c4ae92f6ad9784c683d5af682c326f74de8b5e87a33b71d3e7aa`.
The repaired test SHA-256 is
`9339afa2cb7429317d3ebeae565e3b63be59557555dd97c391f9d89d6b15f391`.

Canonical activation configuration remains `CLOSED`. The production verifier
policy remains immutable, empty, and fail-closed, and the accepted-commit
placeholder remains unchanged. The reader is unwired and undeployed; the real
marker path and parent were not inspected or accessed. The service remains
disabled and non-running. No canonical-path-to-reader, reader/parser, authenticity, repository comparison,
approval source, policy-source or production-policy composition, executable
wiring, or operational authorization exists. The pure inspector-facts-to-validator
adapter remains caller-driven, unwired, and non-authorizing. All production gates
remain closed.


### Accepted-locked-commit marker metadata validation composition

The local, unwired, undeployed pure adapter is implemented in
`engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validation_composition_v1`.
Its `__all__` contains exactly:

    compose_phase_12_activation_accepted_locked_commit_marker_metadata_validation_v1

All implementation-only names are underscore-prefixed. There is no composition
facts wrapper, composition error type, registry, cache, override, setter, or
reset API. Its exact required keyword-only signature is:

    compose_phase_12_activation_accepted_locked_commit_marker_metadata_validation_v1(
        *,
        inspection_facts: Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1,
        policy: Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1,
    ) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1

#### Design provenance and input contract

The first design freeze required same-object inspector-facts handoff, no
reconstruction, and no policy input. It was blocked before implementation as
`BLOCKED_METADATA_VALIDATION_COMPOSITION_DESIGN_FREEZE`, not as an
implementation or regression failure. The locked inspector produces exact
`Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1`, while
the locked validator accepts exact
`Phase12ActivationAcceptedLockedCommitMarkerMetadataV1` and rejects inspector
facts as validator metadata. The validator also requires exact
`Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1`; no valid
validator invocation could be frozen under the original constraints.

The accepted revised decision is exactly:

    AUTHORIZE_FIELD_PRESERVING_INSPECTION_FACTS_TO_VALIDATOR_METADATA_ADAPTATION_WITH_EXPLICIT_EXACT_VALIDATOR_POLICY_INPUT

Neither locked API changed. `inspection_facts` must be the exact inspector facts
type and `policy` must be the exact validator policy type. Subclasses, proxies,
mappings, tuples, protocol-compatible values, `None`, and arbitrary objects are
rejected with empty `TypeError()` before metadata construction or validator
invocation. There is no coercion or hostile attribute interaction before exact
type checking.

#### Exact adapter, policy, call, output, and propagation

The adapter constructs exactly one
`Phase12ActivationAcceptedLockedCommitMarkerMetadataV1` with exactly these six
unchanged field transfers:

    entry_kind=inspection_facts.entry_kind
    link_count=inspection_facts.link_count
    owner_uid=inspection_facts.owner_uid
    group_gid=inspection_facts.group_gid
    permission_mode=inspection_facts.permission_mode
    size_bytes=inspection_facts.size_bytes

There are no omitted or extra fields, normalization, coercion, recomputation,
reinterpretation, defaults, or mutation of inspection facts. Same-object
handoff is impossible because the locked source and destination types differ;
it is not claimed. Field-value preservation replaces same-object handoff.

Policy is explicitly caller supplied. The exact original policy object is passed
unchanged: no copy, reconstruction, default, lookup, source, selection,
approval, mutation, or duplicated policy-rule evaluation occurs. The adapter
makes exactly one call:

    validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1(
        metadata=<single constructed metadata object>,
        policy=policy,
    )

The single constructed metadata object and original policy object are passed by
identity. There is no retry, fallback, duplicate validation, pre-validation, or
post-validation reinterpretation. The exact validator result is returned
unchanged by identity, with no wrapper, copy, reconstruction, boolean
extraction, failure-code transformation, or composition-owned result
validation. Hostile monkeypatched validator results are consequently returned
directly.

Validator-domain errors, ordinary `Exception` values from metadata construction
or validator invocation, and `BaseException` values from either boundary
propagate unchanged. There is no wrapping, translation, retry, fallback,
cleanup side effect, or dynamic disclosure.

Only the locked validator owns entry kind, regular-file requirement,
symbolic-link rules, link count, owner UID, group GID, permission mode, size
limit, and every other metadata mismatch rule. The adapter does not duplicate
these checks; `MetadataV1` retains its locked construction invariants.

#### Boundaries, purity, and TOCTOU limitation

The adapter has no path parameter, canonical-path lookup, filesystem API,
metadata-inspector invocation, marker reader, marker parser, authorization
verifier, validation coordinator, or credential-aware executable. It does not
read bytes, decode, trim, parse, or interpret marker content; establish
authenticity, repository equality, approval, a policy source, production-policy
composition, executable wiring, or operational authorization.

Its input is a prior metadata snapshot. Validation is not bound to a later
descriptor or read, does not prove filesystem continuity, does not eliminate
races, and is not a secure inspector-reader transaction. Success does not prove
canonical-path provenance, marker-content validity, authenticity, repository
equality, policy approval, or production readiness.

There is no import-time metadata construction, validator invocation,
filesystem action, configuration/environment/credential access, logging,
subprocess, systemd, Telegram, network/provider activity, clock, random, UUID,
sleep, mutable registry, cache, override, setter, or reset.

#### Validation evidence and operational posture

The expected RED contract run produced 18 failures, zero passes, exit 1, and
zero internal or unexpected failures in 0.67s, solely because the composition
module/API was absent:
`EXPECTED_ABSENT_MARKER_METADATA_VALIDATION_COMPOSITION_MODULE_OR_PUBLIC_API`.
Isolated GREEN collected and passed 18 tests in 0.16s, with zero failures,
errors, skips, xfails, retries, and internal errors.

Compilation covered implementation and contract test once, exited 0 with empty
stdout and stderr, and preserved source hashes. `py_compile` created exactly
two attributable composition-specific `.pyc` files; both were removed, and no
composition-specific bytecode remains. This does not claim that
`PYTHONDONTWRITEBYTECODE` prevents `py_compile` output.

The single combined focused run preserved inspector, validator, and composition
contracts: `58 + 97 + 18 = 173`, with 173 passed in 0.69s. The single durable
full regression preserved tracked repository content and source hashes:
`4,511 + 18 = 4,529`, with 4,529 collected and passed in 55.12s. It used one
pytest process and one tee process, captured `PIPESTATUS` atomically with two
elements, and recorded pytest/tee statuses `0/0`. All isolated, focused, and
full evidence had zero failures, errors, skips, xfails, retries, and internal
errors. The temporary full-regression log was outside the repository, evidence
was extracted, and it was removed.

The implementation SHA-256 is
`e15f5eec5b21ff5bcc6d7881aabf7529175c31ac3687e15aa41954cdc7e229d7`.
The contract-test SHA-256 is
`6b71dd3e2df4454352c22263a1df8e6a8321d9d0f6dd8e1a1bc6d6026152c681`.

Canonical activation configuration remains `CLOSED`. The production verifier
policy remains immutable, empty, and fail-closed; the accepted-commit
placeholder remains unchanged. The real marker path and parent were not
inspected or accessed. This adapter is unwired and undeployed, has no policy
source, makes no production-readiness claim, and leaves the service disabled
and non-running. All production gates remain closed.

This slice does not change inspector or validator APIs; provide same-object
inspector-facts handoff; source, approve, default, or select policy; select a
canonical path; inspect or read a marker; bind a descriptor; eliminate TOCTOU;
parse content; establish content validity, authenticity, repository equality,
approval, production-policy composition, executable wiring, operational
authorization, service activation, or production readiness.

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

## Phase 12 owner approval signature verifier — frozen detailed design

Capability: **owner approval signature verifier**. The future pure component is
`engine.phase_12_activation_owner_approval_signature_verifier_v1.py` and exposes only
`verify_phase_12_activation_owner_approval_signature_v1` through `__all__`.

```python
def verify_phase_12_activation_owner_approval_signature_v1(
    *,
    canonical_payload_bytes: bytes,
    signature_bytes: bytes,
    public_key_bytes: bytes | None,
    expected_signing_key_identifier: str,
    revocation_state_available: bool,
    active_signing_key_identifier: str | None,
    revoked_signing_key_identifiers: tuple[str, ...] | None,
    revocation_state_checkpoint_identifier: str | None,
    expected_environment_identifier: str,
    expected_deployment_identifier: str,
    expected_checkpoint_identifier: str,
    now_utc: datetime | None,
) -> _Phase12OwnerApprovalSignatureVerificationResultV1:
```

All non-sentinel inputs require exact runtime type identity. Available revocation state requires an
exact active ID, a unique exact tuple of revoked IDs, and an exact state-checkpoint ID; unavailable
state requires all three facts to be `None`. The active key may not be listed as revoked. The
function accepts keyword-only canonical payload bytes, detached signature bytes, raw public-key
bytes or `None`, expected signing-key ID, revocation facts, expected environment/deployment/checkpoint
IDs, and aware-UTC `now_utc` or `None`. `None` public key means
`TRUST_MATERIAL_UNAVAILABLE`; unavailable revocation facts mean
`REVOCATION_STATE_UNAVAILABLE`; `now_utc=None` means `CLOCK_EVIDENCE_UNAVAILABLE`.

The canonical payload is ASCII-only UTF-8, at most 2048 bytes, and exactly sixteen LF-terminated
`field=value` lines in this order: `payload_schema_version`,
`signature_algorithm_identifier`, `signing_key_identifier`, `activation_mode`,
`owner_authorization_id`, `checkpoint_id`, `approved_locked_commit`, `accepted_locked_commit`,
`approval_timestamp`, `expiry`, `environment_identifier`, `deployment_identifier`,
`replay_control_value`, `repository_identity`, `repository_commit`, and `approval_scope`.

Each line has exactly one equals delimiter. There is exactly one terminal LF; no BOM, CR, blank
line, comment, duplicate/extra/omitted field, leading/trailing whitespace, free text, or Unicode
normalization. The exact literals are `phase12-owner-approval-signature-v1`,
`PHASE12-ED25519-SHA512-RAW-V1`, `ai-crypto-signal-agent-production-v1`, and
`EXACT_ACTIVATION_ATTEMPT`. Activation mode is exactly one of `CREDENTIAL_VALIDATION`,
`TELEGRAM_CONNECTIVITY_VALIDATION`, `TELEGRAM_START_VALIDATION`, or `CONTROLLED_WORKLOAD`.

The verifier accepts only a raw 32-byte Ed25519 public key and a raw 64-byte detached signature;
it performs no PEM parsing. Its key fingerprint is `sha256(public_key_bytes).hexdigest()` and the
key ID is `ed25519-sha256:<64-lowercase-hex>`. Available caller-supplied revocation state has one
active key ID, a unique immutable tuple of revoked key IDs, and a state checkpoint; unavailable
state has no facts. The verifier neither loads nor establishes provenance for such facts.

Timestamps are exactly `YYYY-MM-DDTHH:MM:SSZ`. A supplied clock must be an aware `datetime` whose
timezone identity is `timezone.utc`. Approval may be at most 60 seconds in the future, expiry is
mandatory, `now_utc >= expiry` is expired, and expiry must be greater than approval time with a
maximum 15-minute lifetime.

Validation order is fixed: caller API shape; canonical framing and grammar; schema; algorithm;
trust-material availability; public-key construction; fingerprint; signed/expected/active key IDs;
revocation availability and revocation; signature framing; Ed25519 verification; signed commit
equality; signed environment/deployment/checkpoint/scope; then clock and lifetime checks. The
verifier checks `approved_locked_commit == accepted_locked_commit`, but performs no Git access or
repository comparison.

The immutable result contract is `is_valid`, `failure_codes`, and `verified_approval`. There is
exactly one first-precedence failure code and authenticated facts are present only on success. The
stable code ordering is `UNKNOWN_PAYLOAD_SCHEMA`, `UNKNOWN_SIGNATURE_ALGORITHM`,
`UNKNOWN_SIGNING_KEY_ID`, `TRUST_MATERIAL_UNAVAILABLE`, `REVOCATION_STATE_UNAVAILABLE`,
`SIGNING_KEY_REVOKED`, `MALFORMED_CANONICAL_PAYLOAD`, `MALFORMED_SIGNATURE`,
`SIGNATURE_MISMATCH`, `APPROVAL_TIMESTAMP_IN_FUTURE`, `APPROVAL_EXPIRED`,
`CLOCK_EVIDENCE_UNAVAILABLE`, `WRONG_ENVIRONMENT`, `WRONG_DEPLOYMENT`, `WRONG_CHECKPOINT`,
`REPOSITORY_IDENTITY_MISMATCH`, `REPOSITORY_COMMIT_MISMATCH`, `REPLAY_STATE_UNAVAILABLE`,
`REPLAY_STATE_ROLLBACK_DETECTED`, `CHECKPOINT_ALREADY_CONSUMED`, `REPLAY_STATE_CONFLICT`,
`AMBIGUOUS_APPROVAL`, `MALFORMED_PUBLIC_KEY`, `PUBLIC_KEY_FINGERPRINT_MISMATCH`,
`WRONG_APPROVAL_SCOPE`, `EXCESSIVE_APPROVAL_LIFETIME`, and
`APPROVED_ACCEPTED_COMMIT_MISMATCH`. Repository/replay/ambiguity codes are reserved and never
emitted by this pure verifier.

Cryptography is exactly `Ed25519PublicKey.from_public_bytes(public_key_bytes)` followed by
`key.verify(signature_bytes, canonical_payload_bytes)`. `InvalidSignature` maps only to
`SIGNATURE_MISMATCH`; public-key construction `ValueError` maps only to `MALFORMED_PUBLIC_KEY`;
unexpected `Exception` and every `BaseException` propagate unchanged.

The verifier authenticates and returns checkpoint/replay fields but does not read/mutate replay
state, consume checkpoints, or claim replay prevention. It does not prove key or revocation

## Phase 12 owner verification public-key loader — frozen detailed design

Capability: **owner verification public-key loader**. The future component is
`engine.phase_12_owner_verification_public_key_loader_v1.py`, exposes only
`load_phase_12_owner_verification_public_key_v1` through `__all__`, and has this exact interface:

```python
def load_phase_12_owner_verification_public_key_v1(
    *,
    path: str,
    expected_public_key_fingerprint: str,
    expected_signing_key_identifier: str,
) -> _Phase12OwnerVerificationPublicKeyLoadResultV1:
```

Every caller value has exact runtime type identity. `path` is a nonempty normalized absolute `str`
with no NUL, empty interior component, `.` or `..` component, or trailing slash; `/` itself is
invalid. Invalid path form returns `PATH_TYPE_INVALID`. The expected fingerprint is exactly 64
lowercase hexadecimal characters. The expected key ID is exactly
`ed25519-sha256:<64-lowercase-hex>`. Wrong caller types or malformed expected facts raise empty
`TypeError()`. The loader owns no canonical production path and does not infer or open any path
unless a later caller supplies it.

The only accepted source is one canonical PEM SubjectPublicKeyInfo Ed25519 public-key block, at
most 4096 nonempty bytes. Certificates, private keys, encrypted material, OpenSSH keys, raw bytes,
multiple blocks, trailing or leading bytes, alternate line endings, and noncanonical wrapping are
rejected. The output is raw 32-byte Ed25519 public-key `bytes`.

Traversal starts at `/` using directory descriptors. Every parent component is opened with
`os.open` using `O_RDONLY`, `O_DIRECTORY`, `O_CLOEXEC`, and `O_NOFOLLOW`; it must be a non-symlink
directory with UID zero and no group/other write bit. The leaf is opened relative to its final
directory descriptor using `O_RDONLY`, `O_CLOEXEC`, `O_NOFOLLOW`, and `O_NONBLOCK`. It must be a
regular non-symlink file with UID zero, exactly one hard link, `st_mode & 0o022 == 0`, unconstrained
group identity, at most 4096 bytes, and nonempty. No convenience full-path read is permitted.

The loader performs `fstat` before a bounded `os.read` loop and again afterwards. It compares
`st_dev`, `st_ino`, `st_mode`, `st_uid`, `st_gid`, `st_nlink`, `st_size`, `st_mtime_ns`, and
`st_ctime_ns`; it then re-stats the leaf name with `follow_symlinks=False` and requires the same
device/inode. Any changed, substituted, or unstable descriptor is rejected. These checks reduce
but cannot eliminate privileged races after the final check, root-account compromise, mount-level
replacement, or later path changes; they do not establish deployment authenticity.

Cryptography is exactly:

```python
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key
```

`load_pem_public_key(file_bytes)` maps `ValueError` to `MALFORMED_PUBLIC_KEY_CONTAINER` and
`UnsupportedAlgorithm` to `UNSUPPORTED_PUBLIC_KEY_TYPE`. A parser-call `TypeError` propagates as
an implementation defect; unrelated `Exception` and every `BaseException` propagate unchanged.
The decoded object must satisfy `isinstance(decoded, Ed25519PublicKey)`; no duck typing is allowed,
and every successfully parsed non-Ed25519 key is `UNSUPPORTED_PUBLIC_KEY_TYPE`. Canonicality is
enforced by exact equality with:

```python
decoded.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
```

Raw export is exactly `decoded.public_bytes(Encoding.Raw, PublicFormat.Raw)` and must be exact
`bytes` of length 32 or is `MALFORMED_PUBLIC_KEY`. The fingerprint is
`sha256(raw_public_key_bytes).hexdigest()` and the derived key ID is
`"ed25519-sha256:" + fingerprint`; both must equal caller expectations.

The private frozen, slotted, keyword-only result has fields `is_loaded`, `failure_codes`,
`raw_public_key_bytes`, and `derived_signing_key_identifier`. Success is true, has no codes, and
contains the exact raw bytes and key ID. Failure is false, has exactly one first-precedence code,
and contains neither bytes nor identifier. Result repr and failure output disclose no raw key,
PEM, path, fingerprint, or key ID.

Frozen failure order is: `PATH_TYPE_INVALID`, `TRUST_MATERIAL_UNAVAILABLE`,
`TRUST_MATERIAL_PARENT_DIRECTORY_MISMATCH`, `TRUST_MATERIAL_NOT_REGULAR_FILE`,
`TRUST_MATERIAL_SYMLINK_REJECTED`, `TRUST_MATERIAL_OWNER_MISMATCH`,
`TRUST_MATERIAL_MODE_MISMATCH`, `TRUST_MATERIAL_HARD_LINK_REJECTED`,
`TRUST_MATERIAL_TOO_LARGE`, `TRUST_MATERIAL_EMPTY`, `TRUST_MATERIAL_CHANGED_DURING_READ`,
`MALFORMED_PUBLIC_KEY_CONTAINER`, `UNSUPPORTED_PUBLIC_KEY_TYPE`, `MALFORMED_PUBLIC_KEY`,
`PUBLIC_KEY_FINGERPRINT_MISMATCH`, and `PUBLIC_KEY_IDENTIFIER_MISMATCH`.

Validation precedence is caller API shape; path form; parent traversal/open; leaf open; leaf
metadata; bounded read plus descriptor/name-restat mutation checks; PEM `ValueError` then
`UnsupportedAlgorithm`; `isinstance` key type; canonical PEM equality; raw export; fingerprint;
key ID; success. Only frozen expected `OSError` cases are mapped. The component proves only that
the observed descriptor met these checks and decoded/matched caller expectations. It does not prove
owner approval, out-of-band verification, provisioning authenticity, root integrity, post-read path
stability, revocation freshness, signature authorization, repository equality, policy legitimacy, or
operational authorization.

Composition is loader result → raw 32-byte public key → pure owner approval signature verifier.
The loader does not load approval/revocation artifacts, read replay state, compare repositories,
compose policy, decide activation, or authorize operation. It performs bounded read-only filesystem
work only: no writes, permission/ownership changes, installation, configuration or credential
access, Git, clock lookup, network/provider/Telegram, subprocess/systemd, trust-material logging,
mutable cache/registry/setter/override, key/signature generation, or activation.

The future RED contract has exactly 60 tests: 4 public-surface/signature/type; 12
path/symlink/parent/metadata; 9 bounded-read/mutation; 8 strict PEM/container/key-type; 8
raw-key/fingerprint/key-ID; 7 exception/precedence; 6 immutable-result/no-bytes-on-failure; and 6
side-effect/non-overclaim tests. Future file scope is exactly this document,
`tests/test_phase_12_owner_verification_public_key_loader_v1.py`, and
`engine/phase_12_owner_verification_public_key_loader_v1.py`; the future implementation subject is
`feat: add phase 12 owner verification public-key loader`.

## Phase 12 owner signing-key revocation-state source — frozen detailed design

Capability: **owner signing-key revocation-state source**. Future module: `engine/phase_12_owner_signing_key_revocation_state_source_v1.py`; function-only surface: `__all__ = ("load_phase_12_owner_signing_key_revocation_state_v1",)`. Exact function: `load_phase_12_owner_signing_key_revocation_state_v1(*, path: str, expected_artifact_fingerprint: str, expected_schema_identifier: str, expected_checkpoint_identifier: str, active_signing_key_identifier: str) -> _Phase12OwnerSigningKeyRevocationStateLoadResultV1`. Every caller value has exact `str` identity; malformed expected facts raise empty `TypeError()`. Fingerprint is `[0-9a-f]{64}`, expected schema is exactly `PHASE12-OWNER-SIGNING-KEY-REVOCATION-STATE-V1`, expected checkpoint is `phase12-revocation-checkpoint-[0-9a-f]{16}`, and active key is `ed25519-sha256:[0-9a-f]{64}`. Path is nonempty normalized absolute, has no NUL, empty interior component, `.` or `..`, trailing slash, or root form; invalid form is `PATH_TYPE_INVALID`; no canonical path is owned. The private frozen, slotted, keyword-only result fields are `is_loaded`, `failure_codes`, `schema_identifier`, `checkpoint_identifier`, `revoked_signing_key_identifiers`, and `artifact_fingerprint`; success has facts and ordered immutable IDs, failure has one code and no partial state, and the fixed repr discloses neither path, bytes, schema, checkpoint, IDs, fingerprint, nor active key.

The unsigned root-owned local artifact is bound only by `sha256(exact_artifact_bytes).hexdigest()` equality to caller expectation; no owner-intent, authenticity, freshness, or authorization claim is made. Parent flags are `O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW`; leaf flags are `O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK`. Traversal starts at `/`, is descriptor-relative, closes every descriptor, never uses convenience reads, and requires each parent to be a UID-zero directory with `st_mode & 0o022 == 0`. Leaf is regular, UID zero, no group/other write bit, hard-link count one, and `0 < st_size <= 65536`; group is unconstrained. Parent/leaf `ENOENT`/`EACCES` map unavailable, parent `ENOTDIR` maps parent mismatch, and initial parent/leaf `ELOOP` maps symlink rejection. Bounded reads total at most 65537 bytes: overflow is `REVOCATION_STATE_TOO_LARGE`, empty is `REVOCATION_STATE_EMPTY`; exactly one leaf `fstat` occurs before and after read and compares only `st_dev`, `st_ino`, `st_mode`, `st_uid`, `st_gid`, `st_nlink`, `st_size`, `st_mtime_ns`, and `st_ctime_ns` (no float timestamps). Descriptor-relative non-following name restat requires regular same device/inode; post-read replacement/symlink is changed-during-read. Unexpected exceptions and `BaseException` propagate.

## Phase 12 owner approval durable replay guard v1 — frozen detailed design

### Capability, module, and caller surface

Capability: **owner approval durable replay guard**. It owns only local durable replay check-and-record facts. It is not an approval authority, replay oracle, activation authority, global replay-prevention authority, or production-authorization authority.

Future module: `engine.phase_12_owner_approval_durable_replay_guard_v1`; implementation file: `engine/phase_12_owner_approval_durable_replay_guard_v1.py`; future test file: `tests/test_phase_12_owner_approval_durable_replay_guard_v1.py`. Its sole public export is:

```python
__all__ = ("check_and_record_phase_12_owner_approval_replay_v1",)
```

```python
def check_and_record_phase_12_owner_approval_replay_v1(
    *,
    path: str,
    replay_identity: str,
    expected_schema_identifier: str,
    expected_deployment_identifier: str,
) -> _Phase12OwnerApprovalDurableReplayGuardResultV1:
```

There is no separate public check, insert, query, initialize, repair, migrate, delete, reset, or list operation. All four inputs require exact runtime `str` identity. Malformed caller-owned expected facts raise empty `TypeError()`. `replay_identity` is `[0-9a-f]{64}`; `expected_schema_identifier` is exactly `PHASE12-OWNER-APPROVAL-REPLAY-STORE-V1`; `expected_deployment_identifier` is `phase12-replay-deployment-[0-9a-f]{16}`. Invalid path form returns `PATH_TYPE_INVALID`.

`path` is nonempty and normalized absolute with exactly one leading slash. `/` itself is invalid; NUL, empty interior components, `.`, `..`, and a trailing slash are invalid. The guard receives a caller-selected path and owns no canonical production-path constant.

The replay identity is the caller-supplied lowercase SHA-256 digest of the exact canonical signed 16-field approval-payload bytes. The guard receives only that digest: it neither receives nor reconstructs payload bytes, verifies a signature or provenance, or claims collision impossibility. Byte-identical approvals intentionally have the same identity.

Replay mutation is permitted only after upstream composition has established canonical authorization parsing, semantic authorization verification, public-key loading, revocation-state loading, owner signature verification, checkpoint equality, and repository identity plus accepted locked-commit comparison. The guard neither redoes nor imports those components. Failed upstream parse, semantic, key, revocation, signature, checkpoint, or repository attempts are not recorded.

### Filesystem, URI, and race-bounded store access

The deployment class is `ROOT_OWNED_LOCAL_MUTABLE_SQLITE_STORE`. Root anchor and every parent open descriptor-relatively with `os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW`. The root anchor must be a UID-zero directory with no group/other write bit. Each traversed path parent must be a UID-zero non-symlink directory with exact permission bits `0o700`. The existing database leaf is pre-opened with `os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK`; it must be a non-symlink regular file, UID zero, exact mode `0o600`, and hard-link count exactly one. Group identity is unconstrained. Every descriptor remains open through the operation and closes on every result or propagated exception. No directory, database, or schema creation is allowed.

Before SQLite connects, the guard traverses from `/`, validates held parent and leaf descriptors, then retraverses from `/` and requires matching parent identities and matching leaf `st_dev` and `st_ino`. SQLite connects through the original normalized path with existing-only URI semantics. After transaction completion it retraverses again and compares path/descriptor identity plus `st_dev`, `st_ino`, `st_mode`, `st_uid`, `st_gid`, and `st_nlink`. Database size and timestamps are not compared because SQLite may legitimately change them. This detects persistent ordinary replacement and permission drift; it does not claim protection from a privileged swap-and-restore adversary.

```python
sqlite3.connect(
    f"file:{quote(path, safe='/')}?mode=rw",
    uri=True,
    timeout=5.0,
    isolation_level=None,
    detect_types=0,
    check_same_thread=True,
    factory=sqlite3.Connection,
    cached_statements=0,
)
```

The guard uses one dedicated connection per operation, existing-only non-creating semantics, and disabled extension loading. Connection-factory substitution, `ATTACH`, UDFs, and alternate backends are forbidden.

Apply and validate PRAGMAs in this exact order: `foreign_keys=ON` (`1`), `journal_mode=DELETE` (`delete`), `synchronous=FULL` (`2`), `temp_store=MEMORY` (`2`), `trusted_schema=OFF` (`0`), and `busy_timeout=5000` (`5000`); then read and require `page_size == 4096` and `max_page_count == 262144`. Unsupported `trusted_schema` is `REPLAY_STORE_CONNECTION_POLICY_MISMATCH`; it must not silently weaken policy. `max_page_count` is validation-only during guard execution. WAL, persistent WAL/shared-memory sidecars, manual fsync, and manual filesystem mutation are forbidden; SQLite's transient DELETE-mode rollback journal is the sole allowed sidecar.

### Exact SQLite schema and validation

The pre-provisioned store has exactly this schema:

```sql
CREATE TABLE phase_12_owner_approval_replay_metadata_v1 (
    singleton INTEGER NOT NULL PRIMARY KEY CHECK (singleton = 1),
    schema_identifier TEXT NOT NULL
        CHECK (
            schema_identifier =
            'PHASE12-OWNER-APPROVAL-REPLAY-STORE-V1'
        ),
    deployment_identifier TEXT NOT NULL CHECK (
        length(deployment_identifier) = 42
        AND substr(deployment_identifier, 1, 26) =
            'phase12-replay-deployment-'
        AND substr(deployment_identifier, 27)
            NOT GLOB '*[^0-9a-f]*'
    )
) WITHOUT ROWID;

CREATE TABLE phase_12_owner_approval_replay_consumed_v1 (
    replay_identity TEXT NOT NULL PRIMARY KEY CHECK (
        length(replay_identity) = 64
        AND replay_identity NOT GLOB '*[^0-9a-f]*'
    )
) WITHOUT ROWID;
```

The metadata table contains exactly one singleton-`1` row whose schema is exact and whose deployment identifier equals caller expectation. The consumed table contains only `replay_identity`. No timestamp, payload, signature, key, authorization record, checkpoint, commit, environment, scope, status, sequence, operator, or secret is stored.

Only those two application tables are allowed: no application-defined index, view, trigger, foreign key, or additional application table. The primary-key index surfaced by `PRAGMA index_list` is allowed only when `unique=1`, `origin='pk'`, `partial=0`, and its exact primary-key column matches its table. Introspection uses fixed queries and bounded `fetchmany` limits, never unbounded `fetchall` against attacker-controlled schema output. `PRAGMA quick_check(1)` must yield exactly one `ok` row.

### Atomic operation, capacity, and crash semantics

The exact operation order is:

1. caller type and grammar;
2. path grammar;
3. root, parent, and leaf descriptor validation;
4. pre-connection path/descriptor identity check;
5. existing-only SQLite open;
6. connection-policy and PRAGMA validation;
7. `BEGIN IMMEDIATE`;
8. in-transaction path/descriptor identity recheck;
9. `sqlite_schema` validation;
10. table-column and primary-key validation;
11. metadata singleton validation;
12. schema identifier validation;
13. deployment identifier validation;
14. `quick_check(1)`;
15. replay-identity lookup;
16. if already present, `ROLLBACK` and return already consumed;
17. otherwise require consumed row count `< 1000000`;
18. require `page_count < 262144`;
19. insert exactly one replay identity;
20. `COMMIT`;
21. post-commit path/descriptor identity recheck;
22. close resources; and
23. return success.

Already-consumed truth precedes capacity checks. `BEGIN IMMEDIATE`, SQLite writer locking, and the `replay_identity` primary key own atomicity across threads, local processes, repeated starts, and simultaneous activation attempts. Busy or locked longer than 5000 ms fails closed and there is no internal retry.

Successful first use requires completed `COMMIT` under DELETE journaling and FULL synchronous mode; no result is successful before that boundary. Replay identities remain permanently consumed. There is no pruning, expiry, row deletion, administrative reuse, rollback after a successful commit, or history-removing compaction. The exact row limit is `1000000`, page size is `4096`, and maximum page count is `262144`; capacity fails closed without history deletion.

A commit exception is `REPLAY_DURABILITY_NOT_CONFIRMED`: the identity may have persisted and is never treated as cleanly absent. A confirmed commit followed by path/metadata identity drift is `REPLAY_STORE_CHANGED_DURING_OPERATION`; a close failure after confirmed commit is `REPLAY_DURABILITY_NOT_CONFIRMED`. Future same-identity calls resolve status only through this same guard. Downstream policy, wiring, activation, operator abort, crash, or restart never restores reuse.

Malformed databases, unsupported schema or objects, metadata/deployment/page-policy mismatch, quick-check failure, permission or hard-link drift, path replacement, partial state, and corruption all fail closed. Repair, migration, recreation, replacement, automatic restoration, and empty-store fallback are forbidden. Recovery is a separate owner-authorized offline procedure that preserves complete consumed history and the same deployment identifier; the guard cannot prove backup completeness.

### Failure, result, side-effect, and trust boundaries

The exact stable failure set is:

```text
PATH_TYPE_INVALID
REPLAY_STORE_UNAVAILABLE
REPLAY_STORE_PARENT_DIRECTORY_MISMATCH
REPLAY_STORE_SYMLINK_REJECTED
REPLAY_STORE_OWNER_MISMATCH
REPLAY_STORE_MODE_MISMATCH
REPLAY_STORE_NOT_REGULAR_FILE
REPLAY_STORE_HARD_LINK_REJECTED
REPLAY_STORE_CHANGED_DURING_OPERATION
REPLAY_STORE_OPEN_FAILED
REPLAY_STORE_BUSY
REPLAY_STORE_CONNECTION_POLICY_MISMATCH
REPLAY_STORE_PAGE_POLICY_MISMATCH
REPLAY_STORE_SCHEMA_MISMATCH
REPLAY_STORE_DEPLOYMENT_MISMATCH
REPLAY_STORE_UNSUPPORTED_OBJECT
REPLAY_STORE_CORRUPT
REPLAY_STORE_CAPACITY_EXCEEDED
REPLAY_IDENTITY_ALREADY_CONSUMED
REPLAY_RECORD_FAILED
REPLAY_DURABILITY_NOT_CONFIRMED
```

Busy/locked maps to `REPLAY_STORE_BUSY`; primary-key conflict maps to `REPLAY_IDENTITY_ALREADY_CONSUMED`; `CANTOPEN` maps to `REPLAY_STORE_OPEN_FAILED`; and `CORRUPT`/`NOTADB` map to `REPLAY_STORE_CORRUPT`. Unknown ordinary exceptions and every `BaseException` propagate unchanged; implementation must not broadly catch `Exception`. First failure precedence is exactly the numbered operation order above, with insertion conflict between insert and commit.

The private frozen, slotted, keyword-only result fields are `is_recorded`, `was_already_consumed`, `failure_codes`, `replay_identity`, `schema_identifier`, and `deployment_identifier`. Success is recorded with no codes and all facts. Already-consumed has false/true status, `(REPLAY_IDENTITY_ALREADY_CONSUMED,)`, and all facts. Every other failure has false/false status, one code, and no replay/store facts. A fixed repr reveals only both booleans and failure count; it does not disclose path, replay identity, deployment identifier, SQL, metadata, or approval facts.

Allowed side effects are descriptor and bounded SQLite metadata reads, one existing-store open, fixed PRAGMA execution, SQLite locks, the transient DELETE rollback journal, one replay-identity insert, FULL synchronous commit, identity rechecks, and resource closure. Forbidden are database or directory creation, schema creation/migration, repair/replacement, chmod/chown/mkdir/rename/unlink, manual fsync, WAL, ATTACH, VACUUM, deletion/pruning, Git, network, configuration, credentials, marker, public-key, revocation, subprocess, systemd, logging, mutable cache, policy population, activation, and any operational-authorization claim.

Future composition is authorization parsing → semantic verification → public-key loading → revocation-state loading → signature verification → repository and locked-commit comparison → durable replay check-and-record → production-policy decision → executable/service activation. The guard imports or calls none of those upstream or downstream components. Success proves only local durable replay recording under the frozen store/filesystem/transaction/metadata rules. It does not prove caller provenance, signature or approval validity, host/root integrity, hardware flush honesty, backup completeness, cross-host/global replay prevention, repository correctness, policy legitimacy, activation success, production authorization, or production readiness.

### Future RED and commit boundaries

The RED contract has exactly 108 static tests, without parametrization, dynamic generation, skip, or xfail: 6 public surface/signature/result/repr; 10 caller types/grammars; 8 path grammar; 9 parent traversal/metadata; 8 database leaf metadata; 4 existing-only open; 7 PRAGMA policy; 9 schema/object introspection; 5 metadata/deployment; 5 quick-check/corruption; 5 first-use; 4 already-consumed; 4 row/page capacity; 4 concurrent insertion; 3 busy/locking; 4 commit ambiguity; 3 post-operation identity drift; 3 immutable result shapes; 3 exception propagation; and 4 purity/trust-boundary tests. Fixtures use only pytest-managed SQLite stores and deterministic descriptor/metadata seams, with exactly one Linux fork-context multiprocess concurrency test. No real operational path or root privilege is required.

The future cumulative scope is exactly this document, `tests/test_phase_12_owner_approval_durable_replay_guard_v1.py`, and `engine/phase_12_owner_approval_durable_replay_guard_v1.py`. Future subjects are exactly: `docs: freeze phase 12 owner approval durable replay guard design`, `test: define phase 12 owner approval durable replay guard`, and `feat: add phase 12 owner approval durable replay guard`. A fixture-repair commit is forbidden unless a specific committed test contradiction is later proven. This frozen design authorizes no implementation, test creation, path access, policy population, wiring, activation, or production action; all production gates remain closed.


## Phase 12 repository identity and accepted locked-commit comparator v1 — frozen detailed design

### Capability, module, and caller contract

Capability: **repository identity and accepted locked-commit comparator**. It owns only bounded inspection of one local Git repository, comparison of caller-owned expected facts with selected local facts, and immutable result construction. It is not a repository, source-authenticity, remote-freshness, release, deployment, or production-authorization authority.

Module: `engine.phase_12_repository_identity_locked_commit_comparator_v1`. Implementation file: `engine/phase_12_repository_identity_locked_commit_comparator_v1.py`. Future test file: `tests/test_phase_12_repository_identity_locked_commit_comparator_v1.py`.

```python
__all__ = ("compare_phase_12_repository_identity_and_locked_commit_v1",)

def compare_phase_12_repository_identity_and_locked_commit_v1(
    *,
    repository_path: str,
    repository_identity: str,
    accepted_locked_commit: str,
    expected_origin_fetch_url: str,
    expected_origin_push_url: str,
) -> _Phase12RepositoryIdentityLockedCommitComparatorResultV1:
```

There is no public inspect, resolve, validate, query, Git-runner, status, remote, or cleanup operation. All five inputs require `type(value) is str`; malformed caller facts raise empty `TypeError()`. `repository_identity` is `[a-z0-9][a-z0-9-]{0,63}` and `accepted_locked_commit` is `[0-9a-f]{40}`. Repository failures return immutable results.

URLs support only strict ASCII SSH scp-like `git@<lowercase-host>:<owner>/<repository>.git`: nonempty host/owner/repository, terminal `.git`, no whitespace/control/NUL/newline/query/fragment/trailing slash/alternate scheme/credentials beyond literal `git@`. Comparison is exact and case-sensitive; no URL is hard-coded or rewritten.

### Path, filesystem identity, and topology

`repository_path` is nonempty normalized absolute, has exactly one leading slash, is not `/`, and has no NUL, empty interior, `.`/`..`, or trailing slash. It is caller-owned; no canonical path exists. Open `/` and all parents with `os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW`, retain descriptors through completion, and treat `/` only as a traversal anchor. Repository root and direct `.git` must be non-symlink directories, UID 0, and not group/other writable; group is unconstrained, no exact mode or recursive tree audit applies.

Snapshot `st_dev`, `st_ino`, `st_mode`, `st_uid`, and `st_gid` for repository root and direct `.git` before Git observations and recheck afterward. Persistent drift returns `REPOSITORY_CHANGED_DURING_OPERATION`. Do not check nlink, recursively snapshot the tree, or claim protection from privileged swap-and-restore attacks.

Require ordinary non-bare worktree, top-level exactly `repository_path`, direct real `.git`, absolute Git dir equal to direct `.git`, common dir equal to Git dir, and no linked worktree/gitfile/submodule-style gitfile/separate common directory.

### Private Git runner, environment, and isolation

Use only `/usr/bin/git` through a private binary-mode bounded `subprocess.Popen` runner: `shell=False`, fixed argv, `cwd=repository_path`, `stdin=subprocess.DEVNULL`, `stdout=subprocess.PIPE`, `stderr=subprocess.PIPE`, `close_fds=True`, `start_new_session=True`. No TTY, retry, caller Git argv, Python Git library, direct object parsing, or alternate backend. Drain pipes with 65536-byte caps, strict UTF-8, exact output grammars, 5-second command deadline, and 60-second monotonic operation deadline. On timeout terminate process group, bounded-drain, kill if needed, wait/reap, and close descriptors. Timeout, signal exit, overflow, invalid UTF-8, malformed output, and unexpected nonzero exit fail closed; unbounded `subprocess.run(..., capture_output=True)` is forbidden.

The exact non-inherited environment is `PATH=/usr/bin:/bin`, `LANG=C`, `LC_ALL=C`, `HOME=/nonexistent`, `XDG_CONFIG_HOME=/nonexistent`, `GIT_CONFIG_NOSYSTEM=1`, `GIT_ATTR_NOSYSTEM=1`, `GIT_OPTIONAL_LOCKS=0`, `GIT_TERMINAL_PROMPT=0`, `GIT_PAGER=cat`, `PAGER=cat`, `GIT_EXTERNAL_DIFF=`, `GIT_CONFIG_COUNT=0`, and `GIT_NO_REPLACE_OBJECTS=1`. Exclude Git directory/worktree/common-dir/index/object/alternate/namespace/shallow/discovery overrides, SSH agent, proxies, credentials, pager/editor/tracing, user and system config overrides.

Read local config only using `git config --local --no-includes`. Reject local `include.path`, `includeIf.*`, `url.*.insteadOf`, and `url.*.pushInsteadOf`; `git remote get-url` is forbidden. Status/index commands add fixed `-c core.fsmonitor=false -c core.untrackedCache=false -c core.preloadIndex=false -c submodule.recurse=false`. No hooks, diff/textconv, filters, LFS, fsmonitor, pager, editor, credentials, network, lazy fetch, maintenance, or repository/index mutation is allowed.

### Exact 28-command allowlist

The deterministic allowlist and output contracts are exactly:

1. `git rev-parse --is-inside-work-tree` → `true\n`.
2. `git rev-parse --show-toplevel` → one normalized absolute line equal to `repository_path`.
3. `git rev-parse --absolute-git-dir` → one normalized absolute line equal to `repository_path/.git`.
4. `git rev-parse --git-common-dir` → one normalized absolute line equal to `repository_path/.git`.
5. `git rev-parse --is-bare-repository` → `false\n`.
6. `git config --local --no-includes --name-only --get-regexp '^(include|includeIf)\.'` → only exit 1 and empty output.
7. `git config --local --no-includes --name-only --get-regexp '^url\..*\.(insteadOf|pushInsteadOf)$'` → only exit 1 and empty output.
8. `git rev-parse --show-object-format` → `sha1\n`.
9. `git rev-parse --is-shallow-repository` → `false\n`.
10. Descriptor-relative existence check for `.git/objects/info/alternates` → absent only.
11. `git config --local --no-includes --get extensions.partialClone` → only exit 1 and empty output.
12. `git config --local --no-includes --get-regexp '^remote\..*\.promisor$'` → only exit 1 and empty output.
13. `git config --local --no-includes --get-regexp '^remote\..*\.partialclonefilter$'` → only exit 1 and empty output.
14. `git for-each-ref --format=%(refname) refs/replace/` → empty output.
15. `git config --local --no-includes --bool --get core.sparseCheckout` → absent or `false`; `true` rejects.
16. `git -c core.fsmonitor=false -c core.untrackedCache=false -c core.preloadIndex=false -c submodule.recurse=false ls-files -v -z` → bounded tags; lowercase assume-unchanged and `S` skip-worktree reject.
17. `git -c core.fsmonitor=false -c core.untrackedCache=false -c core.preloadIndex=false -c submodule.recurse=false ls-files --stage -z` → bounded stage grammar; intent-to-add and mode `160000` reject.
18. `git config --local --no-includes --get-regexp '^submodule\.'` → only exit 1 and empty output.
19. `git symbolic-ref --quiet HEAD` → `refs/heads/master\n`; exit 1 is detached HEAD.
20. `git cat-file -t --end-of-options <accepted_locked_commit>` → `commit\n`.
21. `git rev-parse --verify --end-of-options <accepted_locked_commit>^{commit}` → accepted hash plus LF.
22. `git rev-parse --verify refs/remotes/origin/master^{commit}` → accepted hash plus LF.
23. `git rev-parse --verify HEAD^{commit}` → accepted hash plus LF.
24. `git config --local --no-includes --get remote.origin.url` → exactly one strict fetch URL plus LF.
25. `git config --local --no-includes --get remote.origin.pushurl` → exactly one strict push URL plus LF.
26. `git symbolic-ref --quiet refs/remotes/origin/HEAD` → `refs/remotes/origin/master\n`.
27. `git -c core.fsmonitor=false -c core.untrackedCache=false -c core.preloadIndex=false -c submodule.recurse=false status --porcelain=v2 -z --untracked-files=all --ignore-submodules=none` → empty stdout.
28. Final descriptor-relative root and `.git` snapshot recheck → exact initial five-field snapshots.

Only specified optional absence exits are accepted. Required HEAD, object, origin URL/push URL, origin/master, and origin/HEAD absence fails closed.

### Object, refs, cleanliness, and history

V1 is SHA-1 only; SHA-256 fails closed pending a new comparator/marker contract. Accepted commit must be full lowercase 40-hex, locally present, type `commit`, exactly resolve to itself, and exactly equal HEAD. No abbreviation, arbitrary revision, ancestor semantics, tag relevance, or signature verification. Subject and parent are not inputs, predicates, or result facts.

HEAD must symbolically be `refs/heads/master`; detached HEAD fails. Local origin/master must equal the accepted commit and symbolic origin/HEAD must target origin/master. These are local observations only and do not prove remote freshness. Exactly one explicit local fetch and push URL must equal caller values; missing, empty, duplicate, include-derived, rewritten, or fallback values fail. URLs are not returned.

NUL porcelain-v2 output must be empty. Any changed, renamed, unmerged, untracked, staged, unstaged, conflict, intent-to-add, or submodule status is `REPOSITORY_DIRTY`. Ignored files may exist but are not requested, parsed, or inspected. Assume-unchanged, skip-worktree, sparse state, registered submodules, shallow state, replace refs, alternates, and promisor/partial-clone state reject. Required object/ref validation is bounded; no `git fsck`, full-history traversal, or complete object-db integrity claim.

### Observation order, result, and errors

Exact first-precedence order: caller grammar; path grammar; root/parent traversal; repository/.git metadata; initial snapshots; worktree/top-level/Git-dir/common-dir/bare topology; config isolation; object format; shallow; alternates; promisor/partial clone; replace refs; sparse; index flags/intent-to-add; submodules; symbolic branch; accepted object type; accepted resolution; HEAD equality; fetch URL; push URL; origin/master; origin/HEAD; cleanliness; final snapshots; success.

Private result `_Phase12RepositoryIdentityLockedCommitComparatorResultV1` is frozen, slotted, keyword-only, with fields in exact order: `is_match`, `failure_codes`, `repository_identity`, `repository_top_level`, `head_commit`, `branch_name`, `origin_master_commit`, `origin_head_target`, `object_format`, `is_clean`. Success is true with no codes and all facts. Failure is false with one code and all facts `None`. Repr exposes only match state and failure count.

The exact 33 stable codes are:

```
PATH_TYPE_INVALID
REPOSITORY_UNAVAILABLE
REPOSITORY_PATH_MISMATCH
REPOSITORY_SYMLINK_REJECTED
REPOSITORY_OWNER_MISMATCH
REPOSITORY_MODE_MISMATCH
REPOSITORY_NOT_GIT_WORKTREE
REPOSITORY_GIT_DIR_MISMATCH
REPOSITORY_LINKED_WORKTREE_REJECTED
REPOSITORY_OBJECT_FORMAT_UNSUPPORTED
REPOSITORY_ACCEPTED_COMMIT_INVALID
REPOSITORY_OBJECT_MISSING
REPOSITORY_OBJECT_TYPE_MISMATCH
REPOSITORY_DETACHED_HEAD
REPOSITORY_BRANCH_MISMATCH
REPOSITORY_HEAD_MISMATCH
REPOSITORY_REMOTE_MISSING
REPOSITORY_REMOTE_URL_MISMATCH
REPOSITORY_ORIGIN_MASTER_MISMATCH
REPOSITORY_ORIGIN_HEAD_MISMATCH
REPOSITORY_DIRTY
REPOSITORY_SPARSE_CHECKOUT_REJECTED
REPOSITORY_INDEX_FLAG_REJECTED
REPOSITORY_SUBMODULE_REJECTED
REPOSITORY_SHALLOW_REJECTED
REPOSITORY_REPLACE_REFS_PRESENT
REPOSITORY_ALTERNATES_REJECTED
REPOSITORY_PROMISOR_REJECTED
REPOSITORY_CHANGED_DURING_OPERATION
REPOSITORY_COMMAND_FAILED
REPOSITORY_COMMAND_TIMEOUT
REPOSITORY_OUTPUT_TOO_LARGE
REPOSITORY_OUTPUT_INVALID
```

Expected process/filesystem/Git conditions map only through these codes. Unknown ordinary Python exceptions and every `BaseException` propagate unchanged; broad `Exception` catching is forbidden.

### Composition, trust, RED, and future scope

Allowed effects are bounded metadata reads, existing root/parent/repository/`.git` descriptor opens, fixed local read-only Git subprocesses, monotonic deadline reads, immutable result construction, and cleanup. Git/index mutation or locks; fetch/pull/push/checkout/reset/clean/add/commit/stash/merge/rebase/tag/branch/config mutation; hooks; diff/textconv; filters; LFS; fsmonitor; maintenance; GC; fsck; lazy fetch; credentials; network; marker/key/revocation/replay access; policy/wiring/activation; logging; cache; and authorization claims are prohibited.

Composition is authorization parsing → semantic verification → public-key loading → revocation-state loading → signature verification → repository comparator → durable replay check-and-record → production-policy decision → executable/service activation. The comparator verifies no caller provenance, reads no marker, and imports/calls none of the marker, authorization, key, revocation, signature, replay, policy, executable, or service components. Success proves selected local facts at observation time only; it does not prove freshness, hosting identity, authorship, signatures, source trust, whole-db integrity, host integrity, ignored-file safety, reproducibility, deployment equivalence, activation, authorization, or readiness.

`expected_origin_fetch_url` and `expected_origin_push_url` are required API facts, but their source is intentionally undefined. Existing marker and approval components do not provide them. This design authorizes no marker/approval/config field, hard-coded URL, caller-fact source, or wiring; a separately approved source is required before composition. Design, RED, and isolated implementation can proceed independently.

The RED contract has exactly 163 unique top-level static tests, with no parametrization, dynamic generation, skip, or xfail: 6 public surface/result; 12 caller type/grammar; 9 path grammar; 10 path symlink/metadata; 9 `.git` topology; 8 bounded runner; 7 environment; 8 command order; 6 output bounds; 5 timeouts; 7 malformed output; 4 object format; 5 accepted object/type/resolution; 5 branch/detached; 5 origin URLs; 5 origin refs; 7 cleanliness; 5 sparse/index; 4 submodules; 3 shallow; 4 replace refs; 4 alternates; 5 promisor/partial clone; 4 filesystem drift; 4 exception propagation; 7 prohibited effects; 5 trust non-overclaim. Fixtures use deterministic fake-process seams and only bounded pytest-managed local offline repositories. No root privilege, network, operational path, or production repository mutation.

Future cumulative scope is exactly this document, `tests/test_phase_12_repository_identity_locked_commit_comparator_v1.py`, and `engine/phase_12_repository_identity_locked_commit_comparator_v1.py`. Future subjects are exactly `docs: freeze phase 12 repository identity and locked-commit comparator design`, `test: define phase 12 repository identity and locked-commit comparator`, and `feat: add phase 12 repository identity and locked-commit comparator`. Fixture-repair commits are forbidden absent a proven committed contradiction.

This frozen design authorizes no implementation, test creation, caller-fact source, path access, policy population, wiring, activation, or production action. All production gates remain closed.


## Phase 12 repository remote expectation source v1 — frozen detailed design

### Capability, module, and public surface

Capability: **repository remote expectation source**. It owns only loading expected origin fetch and push URL policy facts, validating their filesystem, schema, and URL grammar, and constructing one immutable result. It does not inspect Git; compare repository state; verify approval/signatures; inspect marker, key, revocation, replay, comparator, or policy state; wire components; activate services; or claim repository, URL, hosting, or production authority.

Module: `engine.phase_12_repository_remote_expectation_source_v1`. Implementation file: `engine/phase_12_repository_remote_expectation_source_v1.py`. Future test file: `tests/test_phase_12_repository_remote_expectation_source_v1.py`.

```python
__all__ = (
    "load_phase_12_repository_remote_expectation_source_v1",
)

def load_phase_12_repository_remote_expectation_source_v1(
    *,
    source_path: str,
) -> _Phase12RepositoryRemoteExpectationSourceResultV1:
```

There is no other public parse, validate, inspect, read, open, resolve, normalize, fetch-URL, or push-URL helper. `type(source_path) is str`; malformed type or grammar raises empty `TypeError()`. The path is nonempty normalized absolute, has exactly one leading slash, is not `/`, and has no NUL, empty interior component, `.` component, `..` component, or trailing slash. Caller input is not normalized automatically.

### Descriptor, metadata, and one-read boundary

Open `/` directly. Open every parent descriptor-relatively with `os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW`, retaining all descriptors until completion. Open the leaf exactly once with `os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW`; do not reopen by path. Parent or leaf symlink failures are `SOURCE_SYMLINK_REJECTED`; ordinary missing, inaccessible, non-directory-parent, open, `fstat`, or read availability failures are `SOURCE_UNAVAILABLE`.

Initial leaf validation order is regular file, UID exactly `0`, `stat.S_IMODE(st_mode)` exactly `0o644`, `st_nlink` exactly `1`, and `st_size` from `1` through `4096` inclusive. These fail respectively as `SOURCE_TYPE_INVALID`, `SOURCE_OWNER_MISMATCH`, `SOURCE_MODE_MISMATCH`, `SOURCE_LINK_COUNT_INVALID`, and `SOURCE_SIZE_INVALID`. Parent UID/mode and parent link counts are not constrained.

Snapshot initially and finally exactly `st_dev`, `st_ino`, `st_mode`, `st_uid`, `st_gid`, `st_nlink`, and `st_size`; a final mismatch is `SOURCE_CHANGED_DURING_READ`. Do not add mtime, ctime, block-count, or other metadata, and do not claim protection from privileged swap-and-restore attacks.

Perform exactly one `os.read(source_fd, 4097)`: no loop, retry, second content read, mmap, or path reopen. A 4097-byte result is `SOURCE_SIZE_INVALID`; a zero/short/partial result inconsistent with initial `st_size`, including interrupted read without retry, is `SOURCE_CHANGED_DURING_READ`; an expected read `OSError` is `SOURCE_UNAVAILABLE`; only `1..4096` bytes matching initial `st_size` continue. Partial kernel reads fail closed.

### Canonical file format and URL grammar

Decode strictly as UTF-8 with no replacement; BOM or invalid UTF-8 is `SOURCE_ENCODING_INVALID`. Require exactly one terminal `0x0A`; missing LF, CRLF, extra LF, bytes after terminal LF, leading whitespace, and trailing whitespace before LF are `SOURCE_SCHEMA_INVALID`.

The exact accepted bytes are:

```text
{"schema_version":1,"expected_origin_fetch_url":"...","expected_origin_push_url":"..."}\n
```

Use `json.dumps(value, ensure_ascii=True, separators=(",", ":"))`, construct insertion order exactly `schema_version`, `expected_origin_fetch_url`, `expected_origin_push_url`, append one LF, and require reserialized UTF-8 bytes to equal original bytes exactly. Reject alternate whitespace, formatting, escaping, order, or serialization.

Use deterministic duplicate detection through `object_pairs_hook` or an exact equivalent. Require one top-level object of exactly three ordered pairs, exact case-sensitive keys, no duplicate/unknown/missing keys, `type(schema_version) is int and schema_version == 1` (reject bool), and `type(value) is str` for both URLs. Arrays, null, booleans, nested objects, alternate number forms, escaped keys, duplicate keys, surrogate escapes, and noncanonical valid JSON are `SOURCE_SCHEMA_INVALID`.

The exact comparator-compatible full-string ASCII grammar for each URL is:

```text
git@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?:[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\.git
```

It requires literal `git@`, lowercase host, exactly one owner/repository slash, nonempty owner/repository, terminal `.git`, and case preservation for owner/repository. It rejects whitespace, controls, NUL, query, fragment, alternate scheme/user, embedded credential, DNS resolution, SSH, and network access. Fetch and push grammar failures are `SOURCE_FETCH_URL_INVALID` and `SOURCE_PUSH_URL_INVALID`. Both fields are mandatory and separate; equal values are allowed, while fallback, normalization, rewriting, and frozen actual URL values are forbidden.

### Result, failures, effects, and composition

Private result `_Phase12RepositoryRemoteExpectationSourceResultV1` is `@dataclass(frozen=True, slots=True, kw_only=True)` with exact field order `is_loaded`, `failure_codes`, `expected_origin_fetch_url`, `expected_origin_push_url`. Success has `is_loaded=True`, `failure_codes=()`, and both URLs; failure has `is_loaded=False`, exactly one code, and both fields `None`. Repr exposes only load state and failure count, never path, URLs, file bytes, metadata, or exception details.

The exact 13 codes are:

```text
PATH_TYPE_INVALID
SOURCE_UNAVAILABLE
SOURCE_SYMLINK_REJECTED
SOURCE_OWNER_MISMATCH
SOURCE_MODE_MISMATCH
SOURCE_TYPE_INVALID
SOURCE_LINK_COUNT_INVALID
SOURCE_SIZE_INVALID
SOURCE_ENCODING_INVALID
SOURCE_SCHEMA_INVALID
SOURCE_FETCH_URL_INVALID
SOURCE_PUSH_URL_INVALID
SOURCE_CHANGED_DURING_READ
```

Exact first-precedence order is caller type/path grammar; root/parent traversal; source availability; source type; owner; mode; link count; initial size; bounded one-read outcome; UTF-8/BOM; terminal LF/canonical serialization; JSON duplicate/key/order/schema; fetch URL; push URL; final snapshot; success. Unknown ordinary exceptions and every `BaseException` propagate unchanged; broad `Exception` catching is forbidden. Close failures never mask a selected result or propagated exception; otherwise an expected close `OSError` is `SOURCE_UNAVAILABLE`.

Allowed effects are bounded metadata reads, symlink-safe descriptor opens, one bounded descriptor read, immutable result construction, and descriptor cleanup. File creation/mutation, chmod/chown, environment reads, Git, subprocesses, network, DNS, SSH, credential access, logging, mutable cache, marker/approval/key/revocation/replay access, comparator invocation, policy population, and activation are prohibited.

Future composition is authorization parsing → semantic verification → public-key loading → revocation-state loading → owner signature verification → repository remote expectation source → repository comparator → durable replay check-and-record → production-policy decision → executable/service activation. The source receives only `source_path`, not repository identity, accepted commit, repository path, Git facts, approval/marker/replay/comparator state, and does not verify source-path provenance.

Success proves only selected local source-file filesystem, canonical-schema, URL-grammar, and stable-metadata facts. It does not prove URL ownership, hosting identity, availability/freshness, SSH authenticity, credentials, repository identity/content, source trustworthiness, production authorization, or readiness.

### Operational dependencies, RED, scope, and authorization

Actual URL values remain undefined. The operational policy file remains absent; its creation/population, source-path ownership, deployment placement, comparator wiring, and production-policy population are separately unauthorized. These dependencies do not block isolated source implementation.

The RED contract has exactly 101 unique top-level static tests, with no parametrization, dynamic generation, skip, xfail, `sys.modules` mutation, implementation substitute, operational source path, Git, subprocess, or network. Allocation is: 6 public surface/result; 9 caller type/path; 8 parent/leaf symlink; 11 owner/mode/type/link/size; 8 descriptor lifetime/one-read; 6 UTF-8/BOM; 7 terminal LF/canonical serialization; 7 duplicate/unknown keys; 6 schema version/key order; 6 fetch URL grammar; 6 push URL grammar; 5 metadata drift; 4 exception propagation; 7 prohibited effects; 5 trust non-overclaim. Use deterministic fake-filesystem seams and only bounded pytest-managed temporary files for genuine descriptor behavior, with no root privilege requirement.

Future cumulative scope is exactly this document, `tests/test_phase_12_repository_remote_expectation_source_v1.py`, and `engine/phase_12_repository_remote_expectation_source_v1.py`. Exact subjects are `docs: freeze phase 12 repository remote expectation source design`, `test: define phase 12 repository remote expectation source`, and `feat: add phase 12 repository remote expectation source`. Fixture-repair commits are forbidden absent a proven committed contradiction.

This detailed design authorizes no test, implementation, policy file, URL population, source-path wiring, comparator wiring, activation, or production action. Documentation mutation is authorized only by the corresponding design-freeze step; all production gates remain closed.


## Phase 12 repository verification composition v1 — frozen detailed design

### Capability, module, and sole public surface

Repository verification composition is a dedicated independent v1 capability. It invokes an injected repository remote expectation source, validates its bounded result shape, forwards its two URL facts into an injected repository comparator, validates the comparator's bounded outcome shape, and returns one immutable least-disclosing composition result. It does not establish path provenance, URL ownership/freshness, approval or marker validity, replay state, production policy, activation, production authorization, or readiness.

Module: engine.phase_12_repository_verification_composition_v1. Future implementation: engine/phase_12_repository_verification_composition_v1.py. Future tests: tests/test_phase_12_repository_verification_composition_v1.py. This document is the design record. The exact sole public surface is:

~~~python
__all__ = (
    "run_phase_12_repository_verification_composition_v1",
)

def run_phase_12_repository_verification_composition_v1(
    *,
    source_path: str,
    repository_path: str,
    repository_identity: str,
    accepted_locked_commit: str,
    remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
    repository_comparator: _Phase12RepositoryComparatorCallableV1,
) -> _Phase12RepositoryVerificationCompositionResultV1:
~~~

No other public helper, alias, validate, compare, load, replay, policy, or activation operation exists.

### Caller contract and injected protocols

Validate exactly in this order: source_path, repository_path, repository_identity, accepted_locked_commit, remote_expectation_source, repository_comparator. Each fact requires type(value) is str, rejecting str subclasses; each dependency requires callable(value). Any violation raises empty TypeError() before any invocation. Do not duplicate dependency-owned path, identity, or commit grammars.

Private non-runtime-checkable Protocols are _Phase12RemoteExpectationSourceCallableV1 with __call__(*, source_path: str) -> object and _Phase12RepositoryComparatorCallableV1 with __call__(*, repository_path: str, repository_identity: str, accepted_locked_commit: str, expected_origin_fetch_url: str, expected_origin_push_url: str) -> object. Runtime validation is callable() only; signature introspection is prohibited; dependencies remain explicitly injected.

### Source invocation, validation, and URL lifetime

Invoke exactly once as remote_expectation_source(source_path=source_path), with no positional argument, extra keyword, transformation, retry, loop, fallback, or cache. Preflight required attributes is_loaded, failure_codes, expected_origin_fetch_url, and expected_origin_push_url using inspect.getattr_static so a missing attribute is distinguishable from an existing property exception.

Source success is exact bool is_loaded is True, exact tuple failure_codes == (), and both URLs exact str. A valid unsuccessful source result has exact bool false, a nonempty exact tuple of exact str entries, and both URLs None. None, missing attributes, wrong types, success with failures or absent/non-str URLs, failure with empty failures or URLs, non-string failures, and every contradiction are malformed. Complete shape validation precedes unsuccessful classification: contradictory/malformed shape wins even if is_loaded is false.

Missing attributes map to REMOTE_EXPECTATION_SOURCE_RESULT_INVALID. A valid unsuccessful result maps to REMOTE_EXPECTATION_SOURCE_FAILED. Raw source codes are never returned. Unknown ordinary existing-property exceptions and every BaseException propagate unchanged. No comparator or later action follows source failure, malformed result, or exception. URLs are local-only, forwarded once to the comparator, never logged, cached, stored, or passed to replay, policy, or activation, and become unreachable on return or propagation.

### Comparator invocation and bounded outcome validation

Only after valid source success invoke exactly once as repository_comparator(repository_path=repository_path, repository_identity=repository_identity, accepted_locked_commit=accepted_locked_commit, expected_origin_fetch_url=expected_origin_fetch_url, expected_origin_push_url=expected_origin_push_url). There are no positional arguments, extra keywords, rewriting, normalization, retry, loop, fallback, or cache.

Inspect only outcome attributes is_match and failure_codes; the comparator's eight evidence fields remain deliberately uninspected. Success is exact bool is_match is True and exact tuple failure_codes == (). A valid unsuccessful result has exact bool false and a nonempty exact tuple of exact str entries. None, missing outcome attributes, wrong types, false with empty failures, true with nonempty failures, non-string failure entries, and contradictory shapes are malformed; full shape validation precedes unsuccessful classification.

Missing attributes map to REPOSITORY_COMPARATOR_RESULT_INVALID; valid unsuccessful results map to REPOSITORY_COMPARATOR_FAILED; raw comparator codes are never returned. Existing-property ordinary exceptions and every BaseException propagate unchanged. No replay or later action follows comparator failure, malformed result, or exception.

### Immutable result, precedence, exception, and effect boundary

_Phase12RepositoryVerificationCompositionResultV1 is @dataclass(frozen=True, slots=True, kw_only=True), with exact field order is_verified: bool then failure_codes: tuple[str, ...]. Success is is_verified=True and failure_codes=(). Failure is is_verified=False and exactly one permitted code. The exact four-code set is REMOTE_EXPECTATION_SOURCE_FAILED, REMOTE_EXPECTATION_SOURCE_RESULT_INVALID, REPOSITORY_COMPARATOR_FAILED, and REPOSITORY_COMPARATOR_RESULT_INVALID. There is no caller failure code. Repr reveals only is_verified and failure_count, never paths, identity, accepted commit, URLs, results/codes, exception details, Git output, or metadata.

Exact first-failure precedence is source-path type; repository-path type; repository-identity type; accepted-commit type; source callable; comparator callable; source invocation exception propagation; source complete-shape validation; source unsuccessful translation; comparator invocation exception propagation; comparator complete-shape validation; comparator unsuccessful translation; success. First failure only; no aggregation. Caller violations raise empty TypeError(). Unknown ordinary invocation/property exceptions and every BaseException propagate unchanged; broad Exception catches, exception text copying, and cleanup that masks propagation are prohibited.

Allowed effects are exact caller/callable checks, static attribute-presence checks, result attribute reads, one source call, one conditional comparator call, and immutable result construction. Permitted imports are future annotations, dataclasses, typing, and inspect.getattr_static. Direct os, pathlib, subprocess, socket, SSL, URL/HTTP clients, Git libraries, environment/current-directory access, logging, mutable cache, filesystem access, marker/approval/key/revocation/replay/policy access, service control, and activation are prohibited. Filesystem and Git behavior may occur only inside injected remotely locked dependencies.

### Composition, trust, policy, and operational dependencies

Future higher-level order is authorization parsing → semantic verification → public-key loading → revocation-state loading → signature verification → accepted locked-commit marker composition → repository verification composition → durable replay guard → production-policy decision → activation. This component receives already verified caller facts, runs before replay, and proves only valid dependency success shapes plus exact caller-fact and URL forwarding.

It does not prove path provenance, URL ownership, remote freshness, hosting identity, DNS/SSH authenticity, availability, code safety, broader owner intent, production authorization, or readiness. Repository verification success is only a mandatory Boolean prerequisite for future policy evaluation. This component neither populates nor decides policy and exposes no URLs/paths to policy.

Actual source_path and repository_path, deployment placement, policy file, URL values, approval/marker orchestration, replay integration, policy integration, and activation integration remain undefined or unwired; validation coordinator v1 remains unchanged. These external dependencies do not block isolated implementation.

### Future RED contract, scope, and authorization

The RED contract is exactly 68 unique top-level static tests: 6 sole public surface/immutable result; 8 keyword-only caller facts and validation order; 4 injected callable contracts; 3 exact source invocation; 4 source unsuccessful short-circuit; 7 source malformed handling; 3 comparator argument flow; 4 comparator unsuccessful short-circuit; 7 comparator malformed handling; 4 first-failure precedence; 2 no replay/policy/activation; 4 least-disclosing result/repr; 5 exception propagation; 4 prohibited-effect boundary; 3 trust/policy assertions.

Tests use unique top-level functions only: no parametrization, dynamic generation, skip, xfail, sys.modules mutation, import hook, implementation substitute, real policy file, operational path, Git repository, subprocess, network, or replay state. Use deterministic fake dependency results and call recorders only.

Future cumulative scope is exactly this document, tests/test_phase_12_repository_verification_composition_v1.py, and engine/phase_12_repository_verification_composition_v1.py. Exact subjects are docs: freeze phase 12 repository verification composition design; test: define phase 12 repository verification composition; feat: add phase 12 repository verification composition. Fixture-repair commits are forbidden absent a specific committed contradiction.

This documentation commit authorizes no test, implementation, operational-path definition, policy-file creation, URL population, source/comparator wiring, replay/policy integration, coordinator modification, executable wiring, activation, or production action. All production gates remain closed.


## Phase 12 authorization repository validation composition v1 — frozen detailed design

### Capability, module, and sole public surface

Authorization repository validation composition v1 is a dedicated independent capability. It invokes one bounded authorization-validation callable, one bounded accepted-marker composition callable, the remotely locked repository-verification composition, and the remotely locked durable replay guard. It forwards injected remote-expectation-source and repository-comparator seams unchanged to repository composition and returns one immutable least-disclosing policy-prerequisite result.

It does not decide production policy; activate services; create configuration or policy files; derive or discover operational paths; invoke remote source or repository comparator directly; inspect URLs or comparator facts; retry or roll back replay; establish path provenance, URL ownership/freshness, production authorization, or production readiness.

Module: `engine.phase_12_authorization_repository_validation_composition_v1`. Future implementation: `engine/phase_12_authorization_repository_validation_composition_v1.py`. Future tests: `tests/test_phase_12_authorization_repository_validation_composition_v1.py`. This document is the design record. The exact sole public surface is:

~~~python
__all__ = (
    "run_phase_12_authorization_repository_validation_composition_v1",
)

def run_phase_12_authorization_repository_validation_composition_v1(
    *,
    authorization_request: _Phase12AuthorizationRequestV1,
    trust_expectations: _Phase12AuthorizationTrustExpectationsV1,
    accepted_marker_request: _Phase12AcceptedMarkerRequestV1,
    repository_verification_request: _Phase12RepositoryVerificationRequestV1,
    replay_request: _Phase12ReplayRequestV1,
    validation_context: _Phase12ValidationContextV1,
    authorization_validation: _Phase12AuthorizationValidationCallableV1,
    accepted_marker_composition: _Phase12AcceptedMarkerCompositionCallableV1,
    repository_verification_composition: _Phase12RepositoryVerificationCompositionCallableV1,
    remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
    repository_comparator: _Phase12RepositoryComparatorCallableV1,
    replay_guard: _Phase12ReplayGuardCallableV1,
) -> _Phase12AuthorizationRepositoryValidationCompositionResultV1:
~~~

No additional public class, function, protocol, constant, alias, or helper exists.

### Private bundles, caller contract, and callable protocols

The six private input bundles are each `@dataclass(frozen=True, slots=True, kw_only=True, repr=False)`. They are passive immutable carriers: no normalization, ambient discovery, callable field, default factory, or value validation occurs in construction. Each has a fixed repr revealing only its class name and field count. Values, including documents, signatures, paths, key expectations, and metadata policy, never appear in repr. The public caller boundary rejects subclasses through exact type checks.

The exact bundle field orders and annotations are:

~~~python
class _Phase12AuthorizationRequestV1:
    document: str
    canonical_payload_bytes: bytes
    signature_bytes: bytes
    activation_mode: str
    owner_authorization_id: str
    approval_checkpoint_id: str
    approved_locked_commit: str
    approved_at: str
    expires_at: str
    accepted_locked_commit_expectation: str

class _Phase12AuthorizationTrustExpectationsV1:
    public_key_path: str
    expected_public_key_fingerprint: str
    expected_signing_key_identifier: str
    revocation_state_path: str
    expected_revocation_artifact_fingerprint: str
    expected_revocation_schema_identifier: str
    expected_revocation_checkpoint_identifier: str
    expected_environment_identifier: str
    expected_deployment_identifier: str

class _Phase12AcceptedMarkerRequestV1:
    path: str
    expected_metadata_policy: object

class _Phase12RepositoryVerificationRequestV1:
    source_path: str
    repository_path: str

class _Phase12ReplayRequestV1:
    path: str
    expected_schema_identifier: str
    expected_deployment_identifier: str

class _Phase12ValidationContextV1:
    configuration: object
    now_utc: object
~~~

The trust bundle uses distinct expected environment, deployment, and checkpoint facts because the locked signature verifier has distinct context expectations; no undefined singular signature-context field is introduced. The marker metadata-policy object is caller supplied and forwarded only to the bounded marker callable. Bundle fields are never used for path discovery.

The exact keyword-only caller-validation order is: authorization-request exact type; trust-expectations exact type; accepted-marker-request exact type; repository-verification-request exact type; replay-request exact type; validation-context exact type; authorization-validation callable; accepted-marker-composition callable; repository-verification-composition callable; remote-expectation-source callable; repository-comparator callable; replay-guard callable; repository request `source_path` exact `str`; repository request `repository_path` exact `str`; replay request `path` exact `str`; replay request `expected_schema_identifier` exact `str`; replay request `expected_deployment_identifier` exact `str`. The first violation raises empty `TypeError()`. `isinstance`, subclass acceptance, and callable-signature introspection are prohibited. No dependency is invoked before all seventeen checks pass.

The six private non-runtime-checkable Protocols are exactly:

~~~python
class _Phase12AuthorizationValidationCallableV1(Protocol):
    def __call__(self, *, authorization_request: _Phase12AuthorizationRequestV1,
                 trust_expectations: _Phase12AuthorizationTrustExpectationsV1,
                 validation_context: _Phase12ValidationContextV1) -> object: ...

class _Phase12AcceptedMarkerCompositionCallableV1(Protocol):
    def __call__(self, *, accepted_marker_request: _Phase12AcceptedMarkerRequestV1) -> object: ...

class _Phase12RepositoryVerificationCompositionCallableV1(Protocol):
    def __call__(self, *, source_path: str, repository_path: str,
                 repository_identity: str, accepted_locked_commit: str,
                 remote_expectation_source: _Phase12RemoteExpectationSourceCallableV1,
                 repository_comparator: _Phase12RepositoryComparatorCallableV1) -> object: ...

class _Phase12RemoteExpectationSourceCallableV1(Protocol):
    def __call__(self, *, source_path: str) -> object: ...

class _Phase12RepositoryComparatorCallableV1(Protocol):
    def __call__(self, *, repository_path: str, repository_identity: str,
                 accepted_locked_commit: str, expected_origin_fetch_url: str,
                 expected_origin_push_url: str) -> object: ...

class _Phase12ReplayGuardCallableV1(Protocol):
    def __call__(self, *, path: str, replay_identity: str,
                 expected_schema_identifier: str,
                 expected_deployment_identifier: str) -> object: ...
~~~

Runtime validation uses `callable()` only. There are no positional calls, retry, loop, fallback, cache, or adapter.

### Authorization, marker, repository, and replay composition

Authorization validation is invoked exactly once:

~~~python
authorization_validation(
    authorization_request=authorization_request,
    trust_expectations=trust_expectations,
    validation_context=validation_context,
)
~~~

Its required attributes are `is_validated`, `failure_codes`, `repository_identity`, `deployment_identifier`, and `replay_identity`. Success is exact bool true, exact empty failure tuple, and exact-string repository, deployment, and replay identities; returned deployment identity must exactly equal `replay_request.expected_deployment_identifier`. A valid unsuccessful result is exact bool false, a nonempty exact tuple of exact-string failures, and all three facts `None`. Every other, missing, wrong, or contradictory shape, including deployment mismatch, is malformed. Valid unsuccessful maps to `AUTHORIZATION_VALIDATION_FAILED`; malformed maps to `AUTHORIZATION_VALIDATION_RESULT_INVALID`. Raw dependency codes remain private, and no marker or later dependency runs after authorization failure, malformed result, or exception.

After authorization success, accepted-marker composition is invoked exactly once:

~~~python
accepted_marker_composition(
    accepted_marker_request=accepted_marker_request,
)
~~~

Its required attributes are `is_validated`, `failure_codes`, and `accepted_locked_commit`. Success is exact bool true, exact empty failure tuple, and exact-string accepted commit. A valid unsuccessful result is exact bool false, a nonempty exact tuple of exact-string failures, and `accepted_locked_commit is None`. All other shapes are malformed. Valid unsuccessful maps to `ACCEPTED_MARKER_VALIDATION_FAILED`; malformed maps to `ACCEPTED_MARKER_VALIDATION_RESULT_INVALID`. Raw marker codes remain private. No repository or replay call follows marker failure, malformed result, or exception.

After marker success, invoke remotely locked repository-verification composition exactly once with its exact six arguments:

~~~python
repository_verification_composition(
    source_path=repository_verification_request.source_path,
    repository_path=repository_verification_request.repository_path,
    repository_identity=authorization_result.repository_identity,
    accepted_locked_commit=marker_result.accepted_locked_commit,
    remote_expectation_source=remote_expectation_source,
    repository_comparator=repository_comparator,
)
~~~

There are no positional or extra keywords and no rewriting or normalization. Remote source and comparator seams are forwarded unchanged, stored in no bundle, and never invoked directly here. URLs, comparator facts, Git output, and repository metadata are never inspected. No adapter is introduced.

Repository result requires only `is_verified` and `failure_codes`. Success is exact bool true and exact empty tuple. A valid unsuccessful result is exact bool false and a nonempty exact tuple of exact-string failures. Every other shape is malformed. Valid unsuccessful maps to `REPOSITORY_VERIFICATION_FAILED`; malformed maps to `REPOSITORY_VERIFICATION_RESULT_INVALID`. No replay call follows repository failure, malformed result, or exception.

After repository success, invoke replay guard exactly once:

~~~python
replay_guard(
    path=replay_request.path,
    replay_identity=authorization_result.replay_identity,
    expected_schema_identifier=replay_request.expected_schema_identifier,
    expected_deployment_identifier=replay_request.expected_deployment_identifier,
)
~~~

Replay required attributes are `is_recorded`, `was_already_consumed`, `failure_codes`, `replay_identity`, `schema_identifier`, and `deployment_identifier`. Success is exact bool `True`/`False`, exact empty tuple, and all three bounded facts exactly equal supplied inputs. Valid already-consumed is exact bool `False`/`True`, exactly `("REPLAY_IDENTITY_ALREADY_CONSUMED",)`, and all three bounded facts equal supplied inputs; it maps to `REPLAY_ALREADY_CONSUMED`. Other valid unsuccessful result is exact bool `False`/`False`, a one-entry exact-string failure tuple whose code differs from `REPLAY_IDENTITY_ALREADY_CONSUMED`, and all three bounded facts `None`; it maps to `REPLAY_CHECK_AND_RECORD_FAILED`. Every other missing, wrong, contradictory, or mismatched shape maps to `REPLAY_RESULT_INVALID`. Complete structure validation precedes already-consumed and other-failure classification. Raw replay codes and all replay/store details remain private.

For all four dependency results, `inspect.getattr_static` checks required-attribute presence only. Missing attributes map to the stage invalid-result code; normal property access follows preflight. Unknown ordinary property or invocation exceptions and every `BaseException` propagate unchanged. Broad `Exception` catches, exception text copying, and cleanup that masks propagation are prohibited.

### Result, precedence, replay safety, and effect boundary

The exact short-circuit order is: all seventeen caller checks; authorization invocation exception; authorization complete-shape validation; authorization unsuccessful translation; marker invocation exception; marker complete-shape validation; marker unsuccessful translation; repository invocation exception; repository complete-shape validation; repository unsuccessful translation; replay invocation exception; replay complete-shape validation; replay already-consumed translation; replay other-failure translation; success construction. Malformed or contradictory results take invalid-result precedence. First failure only; no aggregation; no later dependency call after an earlier failure, malformed result, or exception.

`_Phase12AuthorizationRepositoryValidationCompositionResultV1` is `@dataclass(frozen=True, slots=True, kw_only=True)` with exact field order `is_validated: bool`, then `failure_codes: tuple[str, ...]`. Success is `is_validated=True` and `failure_codes=()`. Failure is `is_validated=False` and exactly one permitted code. The exact nine-code set is `AUTHORIZATION_VALIDATION_FAILED`, `AUTHORIZATION_VALIDATION_RESULT_INVALID`, `ACCEPTED_MARKER_VALIDATION_FAILED`, `ACCEPTED_MARKER_VALIDATION_RESULT_INVALID`, `REPOSITORY_VERIFICATION_FAILED`, `REPOSITORY_VERIFICATION_RESULT_INVALID`, `REPLAY_CHECK_AND_RECORD_FAILED`, `REPLAY_RESULT_INVALID`, and `REPLAY_ALREADY_CONSUMED`. Fixed repr reveals only `is_validated` and `failure_count`; it reveals neither code values nor bundle, authorization, path, identity, commit, key, signature, URL, repository, comparator, replay, dependency-result, or exception facts.

Replay is the only mutation and repository verification is final non-mutating check. Exactly one replay call occurs only on sole valid pre-replay path. No dependency call, cleanup callback, logging, retry, rollback, or compensating action occurs after replay. Result construction is trivial and deterministic. If it unexpectedly raises after replay commit, exception propagates, replay remains consumed, and caller must not automatically retry.

Permitted imports are only future annotations, dataclasses, `inspect.getattr_static`, and `typing.Protocol`. Allowed effects are caller checks, bundle-field reads, static presence checks, normal result-property reads, one authorization call, one conditional marker call, one conditional repository call, unchanged seam forwarding, one conditional replay mutation, and immutable result construction. Direct filesystem, Git, subprocess, environment/current-directory, credential, network/DNS/SSH/HTTP, logging, mutable cache, policy, coordinator, activation, service, Telegram, provider, retry, fallback, adapter, and file mutation outside injected replay guard are prohibited.

### Trust, policy, RED contract, scope, and authorization

Success proves only exact valid authorization, marker, repository, and replay successes together with exact verified-fact and seam forwarding. It does not prove operational-path provenance, URL ownership/freshness, infrastructure health, repository code safety, broader owner intent, policy approval, activation, production authorization, or readiness. Future policy may receive only overall Boolean validation success or this bounded result; policy versioning, implementation, runtime wiring, and activation remain separately unauthorized.

RED contract is exactly 113 unique top-level static tests across twenty categories with allocation `7/12/13/7/3/7/3/2/6/3/5/5/3/4/9/5/7/4/5/3`: 7 public surface/immutable result; 12 six bundles/bounded repr; 13 twelve-parameter API/caller validation; 7 six protocols/no signature introspection; 3 authorization invocation/bundle flow; 7 authorization malformed/unsuccessful handling; 3 authorization short-circuit; 2 marker invocation/bundle flow; 6 marker malformed/unsuccessful handling; 3 marker short-circuit; 5 repository six-argument invocation/fact-and-seam forwarding; 5 repository malformed/unsuccessful handling; 3 repository short-circuit; 4 replay inputs/count/position; 9 replay success/already-consumed/malformed/other failure; 5 first-failure precedence; 7 least-disclosing result/exception propagation; 4 replay-only mutation/post-commit safety; 5 prohibited direct access/no policy-coordinator-activation action; and 3 trust/policy non-overclaim.

Tests use unique top-level functions, deterministic local fakes, descriptors, and call recorders only. Parametrization, dynamic generation, skip, xfail, `sys.modules` mutation, import hooks, implementation substitutes, operational paths, real policy files, Git repositories, subprocesses, network, and real replay stores are prohibited.

Future cumulative scope is exactly this document, `tests/test_phase_12_authorization_repository_validation_composition_v1.py`, and `engine/phase_12_authorization_repository_validation_composition_v1.py`. Exact subjects are `docs: freeze phase 12 authorization repository validation composition design`, `test: define phase 12 authorization repository validation composition`, and `feat: add phase 12 authorization repository validation composition`. Fixture-repair commits are forbidden absent a specific committed contradiction.

Cumulative owner-policy correction count is three; committed contradiction, unresolved owner-decision, and unresolved technical-decision counts are zero. This documentation commit authorizes no test, implementation, adapter creation, operational path population, policy-file creation, URL population, dependency invocation, replay consumption, policy population, coordinator modification, runtime wiring, activation, or production action. All production gates remain closed.

## Phase 12 canonical replay identity derivation v1 — frozen detailed design

### Capability, module, and public surface

Canonical replay identity derivation v1 is a separate pure capability. It validates six exact verified strings, serializes a fixed domain label and the six facts, computes one deterministic SHA-256 digest, and returns one lowercase 64-hex replay identity. It does not authenticate inputs; verify signatures, deployment, environment, repository, or marker facts; inspect or mutate replay state; decide policy or activation; or access filesystem, Git, subprocesses, environment/current directory, network, credentials, services, Telegram, or providers.

Module: `engine.phase_12_canonical_replay_identity_derivation_v1`. Future implementation: `engine/phase_12_canonical_replay_identity_derivation_v1.py`. Future tests: `tests/test_phase_12_canonical_replay_identity_derivation_v1.py`. This document is the design record. The exact sole public surface is:

~~~python
__all__ = (
    "derive_phase_12_canonical_replay_identity_v1",
)

def derive_phase_12_canonical_replay_identity_v1(
    *,
    replay_control_value: str,
    deployment_identifier: str,
    owner_authorization_id: str,
    checkpoint_id: str,
    approved_locked_commit: str,
    environment_identifier: str,
) -> str:
~~~

There is no other public class, function, constant, helper, alias, result type, default, variadic argument, positional call, mapping, or object bundle. The six keyword-only parameters, annotations, and order are immutable.

### Caller contract, domain, and serialization

The exact twelve caller checks are: exact `str` then nonempty `replay_control_value`; exact `str` then nonempty `deployment_identifier`; exact `str` then nonempty `owner_authorization_id`; exact `str` then nonempty `checkpoint_id`; exact `str` then nonempty `approved_locked_commit`; and exact `str` then nonempty `environment_identifier`. The first violation raises empty `TypeError()`. `isinstance`, subclass acceptance, aggregate validation, normalization, and encoding before all twelve checks are prohibited.

The private fixed, non-exported, V1-immutable constant is:

~~~python
_PHASE_12_CANONICAL_REPLAY_IDENTITY_DOMAIN_V1 = (
    "AI_CRYPTO_SIGNAL_AGENT_PHASE_12_OWNER_APPROVAL_REPLAY_IDENTITY_V1"
)
~~~

The exact seven-field sequence is domain label, replay control value, deployment identifier, owner authorization identifier, checkpoint identifier, approved locked commit, and environment identifier. For every field, encode once as UTF-8 and append exactly `len(encoded).to_bytes(8, "big", signed=False) + encoded`. Serialized bytes are the direct concatenation of all seven prefixed fields: no delimiter, trailing bytes, JSON, repr, pickle, struct, map, platform encoding, reusable public serializer, trimming, Unicode normalization, case folding, integer conversion, or path normalization. A local ephemeral list of bytes is permitted only as transient construction state, never as a global or persistent mutable cache.

The exact imports are:

~~~python
from __future__ import annotations
from hashlib import sha256
~~~

No other import is permitted. The exact one-construction, one-hexdigest invocation is `sha256(serialized).hexdigest()`, returned directly. No redundant output validation, truncation, uppercasing, prefix, suffix, separator, base64, salt, nonce, HMAC, secret key, or random value exists. Standard-library SHA-256 hexdigest therefore returns exact `str`, 64 characters, lowercase `0-9a-f` only.

### Exceptions, effects, disclosure, and trust

Wrong type and empty field each raise empty `TypeError()`. UTF-8 encoding exceptions, unsigned eight-byte length-conversion `OverflowError`, SHA-256 construction or hexdigest ordinary exceptions, and every `BaseException` propagate unchanged. There is no `try`/`except`, `finally`, conversion, aggregation, cleanup callback, or exception text disclosure.

Allowed effects are the caller checks, local tuple/list/bytes construction, UTF-8 encoding, unsigned length conversion, concatenation, one SHA-256 computation, and direct string return. Direct filesystem, Git, subprocess, environment/current-directory, credential, network/DNS/SSH/HTTP, logging, cache, persistent state, replay store/mutation, marker/repository, policy, coordinator, runtime, activation, service, Telegram, provider, dependency injection, callback, retry, fallback, or alternate algorithm behavior is prohibited.

The sole output is replay identity: no result class or repr object, logging, input reflection, serialized bytes, digest bytes, domain metadata, or runtime input value in errors/comments/logs. The fixed domain label may appear in source comments and documentation. Identical exact strings give identical identity; changed bytes or code points change serialized input; eight-byte prefixes prevent field-boundary ambiguity; byte-distinct Unicode, whitespace, and case remain distinct; empty fields are rejected; and field order is immutable. SHA-256 is described as collision-resistant, never collision-impossible.

The derivation authenticates nothing and assumes its strings were already verified. It verifies no signature, deployment/environment consistency, repository identity, marker state, replay state, policy, or activation. Success proves only deterministic V1 application to six supplied exact strings.

### Future integration, versioning, and RED contract

Future bounded authorization validation injects this capability as dependency six after parser, semantic verifier, public-key loader, revocation source, signature verifier, complete signature-result validation, all cross-stage equality checks, and deployment consistency. It passes only successful signature facts: replay control value, deployment identifier, owner authorization identifier, checkpoint identifier, approved locked commit, and environment identifier. It calls derivation exactly once; never after an earlier failure, malformed result, or exception; never retries, falls back, or selects another algorithm. The higher-level composition validates exact `str`, length 64, and `0-9a-f`, then forwards the value unchanged into its locked five-attribute result. This module neither imports nor knows that downstream result class.

V1 field set/order, domain label, UTF-8 encoding, eight-byte unsigned big-endian prefix, and SHA-256 algorithm are immutable. Any change requires a new versioned capability. Silent migration, dual algorithms, fallback, replay-store migration in this slice, and duplicate implementation elsewhere are prohibited. Bounded authorization validation remains blocked until this derivation slice is pushed and remotely locked.

The RED contract is exactly 85 unique explicit top-level static tests with allocation `7/24/2/2/3/3/4/2/3/6/2/3/2/3/3/3/5/2/4/2`: public surface/signature 7; caller validation/precedence 24; domain constant 2; field order 2; UTF-8 3; eight-byte prefixes 3; known vectors/determinism 4; lowercase grammar 2; boundary ambiguity 3; per-field sensitivity 6; Unicode distinction 2; whitespace/case significance 3; no normalization 2; no nondeterminism/HMAC/secret 3; imports 3; hash invocation 3; exception/no-broad-catch 5; least disclosure 2; prohibited access 4; versioning/trust non-overclaim 2.

Tests require the sole export/signature, six wrong-type and six empty-field checks, twelve precedence checks, no-positional and subclass rejection, exact private constant and seven-field serialization, independent expected vectors including one hard-coded offline vector, determinism, grammar, ambiguity, every-field sensitivity, Unicode/whitespace/case behavior, import/hash/source inspections, static overflow contract without unsafe allocation, exception identity propagation, and non-overclaim. Minimal monkeypatching of module-level `sha256` is permitted only for exact invocation count and exception-instance propagation. Parametrization, generation, loop-created tests, skip, xfail, `sys.modules` mutation, import hooks, implementation substitutes, operational paths, real policy files, credentials/secrets, real replay store, subprocess, network, massive allocation, timing, probabilistic testing, and monkeypatching real filesystem/environment/network/replay/policy/coordinator/runtime are prohibited.

Before implementation, isolated collection fails only with `ModuleNotFoundError` for `engine.phase_12_canonical_replay_identity_derivation_v1`: pytest 2, tee 0, zero collected/executed, and no secondary, syntax, fixture, warning, skip, or xfail outcome. After implementation, exactly 85 tests pass with no skip, xfail, xpass, or warning, and compilation passes.

Future scope is exactly this document, `tests/test_phase_12_canonical_replay_identity_derivation_v1.py`, and `engine/phase_12_canonical_replay_identity_derivation_v1.py`. Exact subjects are `docs: freeze phase 12 canonical replay identity derivation design`, `test: define phase 12 canonical replay identity derivation`, and `feat: add phase 12 canonical replay identity derivation`. No fixture repair occurs absent a proven committed contradiction.

Owner-policy and detailed-design correction counts are zero; committed contradictions, unresolved owner decisions, and unresolved technical decisions are zero. This documentation commit authorizes no test, implementation, hashing execution, dependency invocation, replay consumption, path/URL/policy population, coordinator modification, runtime wiring, activation, or production action. All production gates remain closed.

## Phase 12 bounded authorization validation composition v1 — corrected frozen detailed design

### Capability, public surface, and object-shaped contract

Bounded authorization validation composition v1 is the orchestration-only capability `engine.phase_12_bounded_authorization_validation_composition_v1`, implemented at `engine/phase_12_bounded_authorization_validation_composition_v1.py`, tested at `tests/test_phase_12_bounded_authorization_validation_composition_v1.py`, and documented here. Its sole public surface is:

~~~python
__all__ = (
    "run_phase_12_bounded_authorization_validation_composition_v1",
)

def run_phase_12_bounded_authorization_validation_composition_v1(
    *,
    authorization_request: object,
    trust_expectations: object,
    validation_context: object,
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1,
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1,
    public_key_loader: _Phase12PublicKeyLoaderCallableV1,
    revocation_state_source: _Phase12RevocationStateSourceCallableV1,
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1,
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1,
) -> _Phase12BoundedAuthorizationValidationCompositionResultV1:
~~~

The exact parameter names, order, annotations, keyword-only boundary, no defaults, no variadics, and no positional calling are immutable. There is no additional public class, function, constant, Protocol, bundle, alias, helper, or result type.

The exact caller-owned object-shaped inputs are `authorization_request`, `trust_expectations`, and `validation_context`. Attribute presence uses `from inspect import getattr_static`; normal reads occur only after presence succeeds for exact value checks. No property is executed during presence checks. Downstream private request classes, a shared contract module, adapters, conversion classes, and public bundle classes are prohibited.

`authorization_request` checks, in exact order, are `document`, `canonical_payload_bytes`, `signature_bytes`, `activation_mode`, `owner_authorization_id`, `approval_checkpoint_id`, `approved_locked_commit`, `approved_at`, `expires_at`, and `accepted_locked_commit_expectation`. `canonical_payload_bytes` and `signature_bytes` are exact `bytes`; each other field is exact nonempty `str`. `trust_expectations` checks, each exact nonempty `str`, are `public_key_path`, `expected_public_key_fingerprint`, `expected_signing_key_identifier`, `revocation_state_path`, `expected_revocation_artifact_fingerprint`, `expected_revocation_schema_identifier`, `expected_revocation_checkpoint_identifier`, `expected_environment_identifier`, and `expected_deployment_identifier`. `validation_context` checks `configuration` then `now_utc`: configuration is present and non-`None`; `now_utc` is present and forwarded unchanged. There is no `isinstance`, normalization, ambient discovery, time lookup, or environment lookup.

The six callable seams, in exact order, are `authorization_record_parser`, `semantic_authorization_verifier`, `public_key_loader`, `revocation_state_source`, `owner_approval_signature_verifier`, and `canonical_replay_identity_derivation`. Runtime validation is `callable(value)` only. Private, typing-only, non-exported Protocols are `_Phase12AuthorizationRecordParserCallableV1`, `_Phase12SemanticAuthorizationVerifierCallableV1`, `_Phase12PublicKeyLoaderCallableV1`, `_Phase12RevocationStateSourceCallableV1`, `_Phase12OwnerApprovalSignatureVerifierCallableV1`, and `_Phase12CanonicalReplayIdentityDerivationCallableV1`, each mirroring its committed keyword-only API. There is no signature inspection, runtime Protocol check, direct primitive callable import, retry, fallback, default, variadic, or alternate implementation.

The only private result is `_Phase12BoundedAuthorizationValidationCompositionResultV1`, `@dataclass(frozen=True, slots=True, kw_only=True, repr=False)`, with exactly `is_validated: bool`, `failure_codes: tuple[str, ...]`, `repository_identity: str | None`, `deployment_identifier: str | None`, and `replay_identity: str | None`. Success is exactly `True`, `()`, and three exact strings; failure is exactly `False`, one composition-owned code, and three `None` values. No other fact, result, or disclosure exists.

Caller precedence is authorization-request shape/values, trust-expectations shape/values, validation-context shape/values, then the six callables in listed order. Any caller violation is empty `TypeError()` and no dependency is called until every caller check passes.

### Imports, stages, and corrected timestamps

Permitted imports are exactly `from __future__ import annotations`, `from dataclasses import dataclass`, `from inspect import getattr_static`, `from typing import Protocol`, and `Phase12ActivationAuthorizationRecordDocumentErrorV1` from `engine.phase_12_activation_mode_authorization_record_parser_v1`. Direct primitive callable imports, hashlib, filesystem, Git, subprocess, environment, network, logging, replay, repository, marker, policy, coordinator, runtime, activation, service, Telegram, provider, adapter, retry, and fallback imports are prohibited.

The exact parser call is `authorization_record_parser(document=authorization_request.document)`. Its complete required facts are `mode`, `owner_authorization_id`, `checkpoint_id`, `approved_locked_commit`, `accepted_locked_commit`, `approval_timestamp_utc`, and `expires_at_utc`; the first five are exact nonempty `str`, and the final two are exact UTC `datetime`. Missing/malformed shape is `AUTHORIZATION_RECORD_PARSE_RESULT_INVALID`. Only `Phase12ActivationAuthorizationRecordDocumentErrorV1` is caught and becomes `AUTHORIZATION_RECORD_PARSE_FAILED`; no exception text is exposed, while all other ordinary exceptions and every `BaseException` propagate unchanged.

The corrected timestamp contract is immutable. Caller expectations are `authorization_request.approved_at` and `authorization_request.expires_at`, exact nonempty `str`. Parser facts are `parser_result.approval_timestamp_utc` and `parser_result.expires_at_utc`, exact UTC `datetime`. Signature verified approval facts are `verified_approval.approval_timestamp_utc` and `verified_approval.expiry_utc`, exact UTC `datetime`. Signature-result attributes named `approved_at` or `expires_at` must never be documented, required, or tested.

The exact parser projection is:

~~~python
canonical_parser_approval_timestamp = (
    parser_result.approval_timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
)
canonical_parser_expiry_timestamp = (
    parser_result.expires_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
)
~~~

Parser UTC shape is validated before this projection. There is no caller-string parsing, timezone conversion, fractional seconds, alternate format, or normalization. Semantic verifier parameters are exactly `approved_at` and `expires_at`, forwarded as `approved_at=canonical_parser_approval_timestamp` and `expires_at=canonical_parser_expiry_timestamp`; it also receives `validation_context.configuration`, parsed mode/owner/checkpoint/approved commit, `authorization_request.accepted_locked_commit_expectation`, and `validation_context.now_utc`. Semantic result is exact `bool`: non-bool is `SEMANTIC_AUTHORIZATION_RESULT_INVALID`, `False` is `SEMANTIC_AUTHORIZATION_FAILED`, malformed precedes rejection, and neither permits a later call.

The key loader receives the exact locked public-key path, fingerprint, and signing-key identifier. Its complete result is `is_loaded`, `failure_codes`, `raw_public_key_bytes`, and `derived_signing_key_identifier`; malformed is `PUBLIC_KEY_LOADING_RESULT_INVALID`, valid unsuccessful is `PUBLIC_KEY_LOADING_FAILED`. The revocation source receives its four trust facts and the validated derived signing-key identifier. Its complete result is `is_loaded`, `failure_codes`, `schema_identifier`, `checkpoint_identifier`, `revoked_signing_key_identifiers`, and `artifact_fingerprint`; malformed is `REVOCATION_STATE_LOADING_RESULT_INVALID`, valid unsuccessful is `REVOCATION_STATE_LOADING_FAILED`.

The signature verifier receives exact canonical payload/signature bytes, validated raw key bytes, expected signing-key identifier, validated revocation facts, expected environment/deployment/checkpoint, and `now_utc` through its committed keyword-only mapping. Its outer result is `is_valid`, `failure_codes`, and `verified_approval`. Required verified facts are `repository_identity`, `deployment_identifier`, `replay_control_value`, `owner_authorization_id`, `checkpoint_id`, `approved_locked_commit`, `accepted_locked_commit`, `approval_timestamp_utc`, `expiry_utc`, `activation_mode`, `environment_identifier`, and `signing_key_identifier`. It does not expose `approved_at` or `expires_at`. Missing/malformed result, including timestamps, is `OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID`; valid unsuccessful is `OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED`.

### Corrected equality, derivation, failures, and safety

The exact seventeen-item equality order is: (1) caller activation mode = parser mode; (2) caller owner ID = parser owner ID; (3) caller checkpoint = parser checkpoint; (4) caller approved commit = parser approved commit; (5) caller `approved_at` = canonical parser approval timestamp; (6) caller `expires_at` = canonical parser expiry timestamp; (7) caller accepted-commit expectation = parser accepted commit; (8) parser mode = verified signature mode; (9) parser owner ID = verified signature owner ID; (10) parser checkpoint = verified signature checkpoint; (11) parser approved commit = verified signature approved commit; (12) parser accepted commit = verified signature accepted commit; (13) parser approval UTC datetime = verified `approval_timestamp_utc`; (14) parser expiry UTC datetime = verified `expiry_utc`; (15) validated loaded signing-key ID = verified signing-key ID; (16) expected environment = verified environment; (17) expected deployment = verified deployment. There is no direct caller-to-signature timestamp comparison, no unsupported comparison, and no normalization. Mismatches 1–16 are `AUTHORIZATION_FACT_MISMATCH`; item 17 is `DEPLOYMENT_CONSISTENCY_MISMATCH` before replay derivation. Accepted-commit checks prove authorization-fact consistency only, invoke no marker, and do not prove marker validity.

Replay derivation is exactly one conditional call after every prior stage and comparison:

~~~python
canonical_replay_identity_derivation(
    replay_control_value=verified_approval.replay_control_value,
    deployment_identifier=verified_approval.deployment_identifier,
    owner_authorization_id=verified_approval.owner_authorization_id,
    checkpoint_id=verified_approval.checkpoint_id,
    approved_locked_commit=verified_approval.approved_locked_commit,
    environment_identifier=verified_approval.environment_identifier,
)
~~~

No direct hashlib/local duplicate derivation, retry, fallback, or alternate algorithm exists. Result is exact `str`, length 64, characters `0-9a-f`; otherwise return `REPLAY_IDENTITY_RESULT_INVALID` without normalization.

The exact private ordered thirteen-code set is `AUTHORIZATION_RECORD_PARSE_FAILED`, `AUTHORIZATION_RECORD_PARSE_RESULT_INVALID`, `SEMANTIC_AUTHORIZATION_FAILED`, `SEMANTIC_AUTHORIZATION_RESULT_INVALID`, `PUBLIC_KEY_LOADING_FAILED`, `PUBLIC_KEY_LOADING_RESULT_INVALID`, `REVOCATION_STATE_LOADING_FAILED`, `REVOCATION_STATE_LOADING_RESULT_INVALID`, `OWNER_APPROVAL_SIGNATURE_VERIFICATION_FAILED`, `OWNER_APPROVAL_SIGNATURE_VERIFICATION_RESULT_INVALID`, `AUTHORIZATION_FACT_MISMATCH`, `DEPLOYMENT_CONSISTENCY_MISMATCH`, and `REPLAY_IDENTITY_RESULT_INVALID`. Each failure contains exactly one private code and no raw dependency code.

Total precedence is caller validation; parser sanitized exception; parser malformed; semantic malformed; semantic rejection; key malformed; key unsuccessful; revocation malformed; revocation unsuccessful; signature malformed; signature unsuccessful; first mismatch among equality items 1–16; deployment mismatch; replay result invalid; success. It is first-failure-only, malformed-before-unsuccessful, with zero later calls, aggregation, retry, rollback, or compensation. Shape inspection is static presence then normal reads with exact primitive/tuple/bytes/UTC-datetime checks, no truthiness, partial acceptance, repr, or stringification. Unknown ordinary exceptions and every `BaseException` propagate unchanged; there is no broad catch or exception-text disclosure.

Allowed effects are caller/callable checks, six injected calls, shape reads, canonical timestamp projection, equality checks, replay grammar validation, and immutable result construction. Direct filesystem, Git, subprocess, environment/current-directory, credentials, network, logging, cache, persistence, replay mutation, marker/repository validation, policy, coordinator, runtime, activation, service, Telegram, provider, adapter, retry, fallback, direct hashing, and unauthorized mutation are prohibited. The final result exposes only its five fields, never documents, payloads, signatures, key/revocation material, replay control value, dependency results/codes, paths, fingerprints, configuration, timestamps, exception text, or replay serialization.

Success proves only parser success, semantic acceptance, key/revocation expectation success, signature verification, the corrected seventeen-item consistency model, deployment consistency, replay identity derivation, and exact bounded result construction. It does not prove marker/repository validity, replay availability/acceptance/non-consumption, policy approval, activation, production authorization/readiness, path provenance, or infrastructure health.

### RED contract, scope, and authorization boundary

The RED contract is exactly 155 unique explicit top-level static tests with allocation `6/15/8/9/5/6/8/8/8/9/12/12/5/5/4/7/6/5/4/4/5/4`: surface 6; object-shaped contracts 15; seams 8; caller precedence 9; parser 5; parser failure/malformed 6; semantic 8; key 8; revocation 8; signature 9; forwarding 12; equality 12; deployment 5; derivation 5; replay validation 4; total precedence 7; short-circuit 6; result 5; disclosure 4; exception 4; prohibited access 5; trust 4. Fixtures/assertions use caller `approved_at`/`expires_at`, parser `approval_timestamp_utc`/`expires_at_utc`, and verified signature `approval_timestamp_utc`/`expiry_utc` only. Parametrization, generation, skip, xfail, `sys.modules` mutation, import hooks, implementation substitutes, operational values, real dependencies, network, subprocess, timing, and probabilistic assertions are prohibited.

Before implementation, isolated collection fails solely for absent `engine.phase_12_bounded_authorization_validation_composition_v1`: pytest 2, tee 0, zero collected/executed, and no secondary/syntax/fixture/warning/skip/xfail result. After implementation, exactly 155 pass with zero skips, xfails, xpasses, or warnings, and compilation passes.

Scope is exactly this document, `tests/test_phase_12_bounded_authorization_validation_composition_v1.py`, and `engine/phase_12_bounded_authorization_validation_composition_v1.py`. Commit subjects are `docs: freeze phase 12 bounded authorization validation composition design`, `test: define phase 12 bounded authorization validation composition`, and `feat: add phase 12 bounded authorization validation composition`; no fixture repair occurs absent a proven committed contradiction. This component is later injected as `authorization_validation` into `engine.phase_12_authorization_repository_validation_composition_v1`; that locked component is unchanged here, no adapter is created, and integration is separately assessed only after this slice is remotely locked.

Owner-policy correction count is zero; detailed-design correction count is one; committed contradictions, unresolved owner decisions, and unresolved technical decisions are zero. This documentation commit authorizes no test, implementation, hashing, dependency invocation, replay consumption, path/URL/policy population, coordinator modification, runtime wiring, activation, or production action. All production gates remain closed.

## Phase 12 authorization validation callable adapter v1 — frozen detailed design

### Capability, integration purpose, and public surface

Capability: authorization validation callable adapter v1. Module: `engine.phase_12_bounded_authorization_validation_callable_adapter_v1`. Implementation: `engine/phase_12_bounded_authorization_validation_callable_adapter_v1.py`. Tests: `tests/test_phase_12_bounded_authorization_validation_callable_adapter_v1.py`. Documentation: this file.

The adapter only binds the six primitive callable seams required by `run_phase_12_bounded_authorization_validation_composition_v1` and exposes the locked downstream callable shape:

```python
authorization_validation(
    authorization_request=authorization_request,
    trust_expectations=trust_expectations,
    validation_context=validation_context,
)
```

Direct upstream injection is incompatible because its six keyword-only seams would be missing. Structural input and five-field result compatibility are complete. No conversion, reshaping, exception translation, upstream mutation, or downstream mutation is required.

```python
__all__ = (
    "build_phase_12_bounded_authorization_validation_callable_adapter_v1",
)

def build_phase_12_bounded_authorization_validation_callable_adapter_v1(
    *,
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1,
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1,
    public_key_loader: _Phase12PublicKeyLoaderCallableV1,
    revocation_state_source: _Phase12RevocationStateSourceCallableV1,
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1,
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1,
) -> _Phase12BoundedAuthorizationValidationCallableAdapterV1:
```

This is the sole public surface: exact order, keyword-only boundary, private Protocol annotations, private callable-adapter result annotation, and no defaults, variadics, public class, Protocol, result type, alias, constant, helper, or bundle.

### Imports, private protocols, and immutable callable binding

Permitted imports are exactly `from __future__ import annotations`, `from dataclasses import dataclass`, `from typing import Protocol`, and:

```python
from engine.phase_12_bounded_authorization_validation_composition_v1 import (
    run_phase_12_bounded_authorization_validation_composition_v1,
)
```

No other import is permitted unless solely annotation-required and proven necessary. Downstream private Protocol/class imports, upstream private Protocol/result imports, reflection, `functools.partial`, filesystem, Git, subprocess, environment/cwd, network, logging, replay, repository, marker, policy, coordinator, runtime, activation, service, Telegram, provider, cache, serialization, retry, fallback, and direct primitive imports are prohibited.

Exactly six private typing-only Protocols are defined: `_Phase12AuthorizationRecordParserCallableV1`, `_Phase12SemanticAuthorizationVerifierCallableV1`, `_Phase12PublicKeyLoaderCallableV1`, `_Phase12RevocationStateSourceCallableV1`, `_Phase12OwnerApprovalSignatureVerifierCallableV1`, and `_Phase12CanonicalReplayIdentityDerivationCallableV1`. Their keyword-only signatures mirror the locked parser, semantic verifier, public-key loader, revocation source, signature verifier, and replay-derivation contracts. They are not exported, runtime-checkable, or used in runtime checks.

Exactly one private callable representation exists:

```python
@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class _Phase12BoundedAuthorizationValidationCallableAdapterV1:
    authorization_record_parser: _Phase12AuthorizationRecordParserCallableV1
    semantic_authorization_verifier: _Phase12SemanticAuthorizationVerifierCallableV1
    public_key_loader: _Phase12PublicKeyLoaderCallableV1
    revocation_state_source: _Phase12RevocationStateSourceCallableV1
    owner_approval_signature_verifier: _Phase12OwnerApprovalSignatureVerifierCallableV1
    canonical_replay_identity_derivation: _Phase12CanonicalReplayIdentityDerivationCallableV1
```

These are the exact ordered fields, with no additional field, default, post-init mutation, public alias, custom repr/equality/hash, serialization, mutable state, closure, partial, registry, ambient discovery, copying, wrapper-per-seam, or tuple/dictionary bundle.

### Builder, forwarding, result, and exception contract

The builder validates exactly once with `callable(value)`, in this order: authorization record parser; semantic authorization verifier; public key loader; revocation state source; owner approval signature verifier; canonical replay identity derivation. The first invalid seam raises empty `TypeError()`. There is no invocation-time seam revalidation, `isinstance`, `inspect.signature`, runtime Protocol check, trial invocation, normalization, wrapping, default, or fallback resolution. After all checks it constructs exactly one private adapter using the six supplied callables unchanged.

Its exact callable method is:

```python
def __call__(
    self,
    *,
    authorization_request: object,
    trust_expectations: object,
    validation_context: object,
) -> object:
    return run_phase_12_bounded_authorization_validation_composition_v1(
        authorization_request=authorization_request,
        trust_expectations=trust_expectations,
        validation_context=validation_context,
        authorization_record_parser=self.authorization_record_parser,
        semantic_authorization_verifier=self.semantic_authorization_verifier,
        public_key_loader=self.public_key_loader,
        revocation_state_source=self.revocation_state_source,
        owner_approval_signature_verifier=self.owner_approval_signature_verifier,
        canonical_replay_identity_derivation=self.canonical_replay_identity_derivation,
    )
```

All three invocation inputs and six bound seams are forwarded unchanged under these exact nine keyword names; there is exactly one upstream invocation. The adapter owns no structural input validation, result validation/access, class check, reconstruction, reshaping, code translation, normalization, logging, or side effect. It returns the exact upstream result object unchanged, with no wrapping, copying, tuple conversion, dataclass reconstruction, or disclosure augmentation.

Invalid builder seams raise empty `TypeError()`. Upstream `TypeError`, ordinary exceptions, and every `BaseException` propagate unchanged; structured unsuccessful and malformed-dependency failure results return unchanged. There is no catch clause, broad catch, exception inspection/text access, translation, retry, rollback, fallback, or compensating action.

### Locked boundaries and trust

`engine.phase_12_bounded_authorization_validation_composition_v1` remains immutable: no optional/default seams, public dependency bundle, overload, reduced entry point, global registry, ambient lookup, or adapter awareness. `engine.phase_12_authorization_repository_validation_composition_v1` remains immutable and retains its exact three-argument invocation above: no new parameters, private Protocol/result-validator/failure-code/test change, or adapter-specific branch. No shared contract or reverse-private import exists.

The adapter may only check six callables during construction, bind them immutably, forward three inputs and six seams, make one upstream call, and return its result unchanged. Direct filesystem, Git, subprocess, environment/cwd, credentials, parser/semantic/key/revocation/signature/replay behavior, replay store, repository, marker, policy, coordinator, runtime, activation, service, Telegram, provider, logging, cache, mutable globals, serialization, retry, fallback, hidden defaults, and operational mutation are prohibited.

Construction proves only that six supplied values were callable. Invocation proves only unchanged forwarding, one upstream call, and unchanged result return. It does not independently prove authorization/semantic/key/revocation/signature validity, repository identity, marker validity, replay acceptance/non-consumption, production policy approval, activation, runtime readiness, infrastructure/provider health, Telegram delivery, service availability, or operational-path provenance.

A separately assessed future orchestration/runtime owner may construct the adapter; it discovers no dependency, does not invoke or wire downstream, and runtime-owner assessment remains blocked until this adapter is remotely locked. Production activation remains unauthorized.

### RED contract, scope, accounting, and authorization boundary

The RED contract is exactly 67 unique explicit top-level static `test_` functions, with allocation `4/4/6/4/4/4/4/4/3/3/3/3/3/2/2/3/2/3/3/3`: sole surface 4; builder signature 4; seam-validation order 6; empty TypeError 4; callable representation 4; returned signature 4; three-input forwarding 4; six-seam forwarding 4; one invocation 3; unchanged result 3; ordinary exception 3; BaseException 3; no catch/translation 3; upstream immutability 2; downstream immutability 2; no conversion 3; no reshaping 2; prohibited access 3; mutable globals/hidden defaults 3; trust 3. Tests are explicit, unique, non-parametrized, non-generated, deterministic, with no skips, xfails, import hooks, `sys.modules` mutation, substitute implementation, conditional import, real dependency, operational path/URL/credential/production value, timing, or probabilistic assertion.

Before implementation, the isolated test file fails solely with `ModuleNotFoundError` for `engine.phase_12_bounded_authorization_validation_callable_adapter_v1`: pytest 2, tee 0, zero collected/executed, no secondary/syntax/fixture error, and zero warnings. After implementation, exactly 67 pass with zero failed/skipped/xfail/xpass/warnings and compilation passes.

Scope is exactly this document, `tests/test_phase_12_bounded_authorization_validation_callable_adapter_v1.py`, and `engine/phase_12_bounded_authorization_validation_callable_adapter_v1.py`. Commit subjects are `docs: freeze phase 12 bounded authorization validation callable adapter design`, `test: define phase 12 bounded authorization validation callable adapter`, and `feat: add phase 12 bounded authorization validation callable adapter`; upstream and downstream remain unchanged.

Direct callable compatibility is no; structural input/result compatibility is yes; downstream/upstream mutation, shared contract, conversion, and result reshaping are no; adapter and new component requirements are yes. Owner-policy and detailed-design correction counts are zero; committed contradictions, unresolved owner decisions, and unresolved technical decisions are zero. This documentation commit authorizes no test, implementation, adapter creation, dependency invocation, replay consumption, fetch, push, path/URL/policy population, wiring, activation, or production action. All production gates remain closed.

## Phase 12 authorization validation repository orchestration composition v1 — frozen detailed design

Capability: authorization validation repository orchestration composition v1. Module: `engine.phase_12_authorization_validation_repository_orchestration_composition_v1`. Implementation: `engine/phase_12_authorization_validation_repository_orchestration_composition_v1.py`. Tests: `tests/test_phase_12_authorization_validation_repository_orchestration_composition_v1.py`. Sole export is `run_phase_12_authorization_validation_repository_orchestration_composition_v1`.

The sole keyword-only `-> object` operation has this exact order: `authorization_request`, `trust_expectations`, `validation_context`, `accepted_marker_request`, `repository_verification_request`, `replay_request`, `authorization_record_parser`, `semantic_authorization_verifier`, `public_key_loader`, `revocation_state_source`, `owner_approval_signature_verifier`, `canonical_replay_identity_derivation`, `accepted_marker_composition`, `repository_verification_composition`, `remote_expectation_source`, `repository_comparator`, `replay_guard`. The six structural values are opaque caller-owned objects: no attribute inspection, class requirement, conversion, copying, normalization, private import/construction, serialization, or duplicate locked validation.

Imports are annotations, `Protocol`, and direct public imports of `build_phase_12_bounded_authorization_validation_callable_adapter_v1` and `run_phase_12_authorization_repository_validation_composition_v1`. Eleven local private typing-only Protocols mirror the six authorization and five downstream seams. No private cross-module import, runtime Protocol check, shared contract, reflection, partial, operational primitive, filesystem, Git, network, logging, cache, serialization, retry, fallback, coordinator, runtime, or activation import is allowed.

Only downstream seams are prevalidated with `callable()` in exact order: `accepted_marker_composition`, `repository_verification_composition`, `remote_expectation_source`, `repository_comparator`, `replay_guard`; first invalid raises empty `TypeError()`. The locked adapter builder exclusively validates the six primitive seams. Exactly once construct the adapter from the six seams unchanged, then exactly once invoke downstream with unchanged structural inputs, constructed `authorization_validation`, and unchanged five downstream seams. No wrapper, lambda, partial, closure, copying, registry, cache, ambient lookup, result access/validation/reconstruction/reshaping, conversion, normalization, code translation, or disclosure augmentation exists.

First failure is downstream callable validation, adapter construction, downstream invocation, bounded authorization, marker, repository/comparator, replay guard, then unchanged downstream result. Exceptions and BaseException propagate unchanged; structured downstream failures return unchanged. No catch, translation, retry, fallback, rollback, compensation, aggregation, or duplicated domain validation exists. Repository/deployment/replay identity remain downstream-owned; accepted-commit consistency, marker validation, and repository comparison remain separate locked claims. Upstream, adapter, downstream, coordinator, and tests remain immutable.

Allowed effects are five callable checks, one builder call, forwarding, one downstream call, unchanged return. Direct operational access and mutation are prohibited. Runtime wiring remains separate; activation is unauthorized. The RED contract is exactly 100 explicit tests with allocation `4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4/4` across the 25 frozen categories; RED is sole absent-module error, GREEN is 100 passing tests and clean compilation. Scope is this document plus `tests/test_phase_12_authorization_validation_repository_orchestration_composition_v1.py` and `engine/phase_12_authorization_validation_repository_orchestration_composition_v1.py`; commits are docs, RED, implementation. Corrections, contradictions, and unresolved decisions are zero; no mutation beyond this documentation commit is authorized.

## Phase 12 authorization repository structural request builders v1 — frozen detailed design

### Capability identity

Capability: authorization repository structural request builders v1. Module and implementation: `engine.phase_12_authorization_repository_validation_composition_v1`. Implementation file: `engine/phase_12_authorization_repository_validation_composition_v1.py`. Dedicated tests: `tests/test_phase_12_authorization_repository_structural_request_builders_v1.py`. Documentation: `docs/phase_12_activation_configuration_v1.md`. Side-effect class: pure immutable request construction.

### Correction and preservation boundary

This separately documented, RED-defined, audited, remotely locked bounded correction creates only a public construction boundary for six existing private exact-type request objects. It does not reopen or weaken the completed orchestration slice or authorize runtime, configuration, coordinator, service, provider, Telegram, policy, or activation ownership. `_Phase12AuthorizationRequestV1`, `_Phase12AuthorizationTrustExpectationsV1`, `_Phase12ValidationContextV1`, `_Phase12AcceptedMarkerRequestV1`, `_Phase12RepositoryVerificationRequestV1`, and `_Phase12ReplayRequestV1` remain private, unexported, frozen, slotted, keyword-only, repr-suppressed, identity-preserved, and unchanged in module, fields/order/annotations, constructor behavior, and downstream acceptance. They are not renamed, promoted, aliased, duplicated, moved, wrapped, subclassed, or exported.

`run_phase_12_authorization_repository_validation_composition_v1` remains byte-for-byte unchanged: name, signature, annotations, parameter order, exact private-type and callable checks, first-failure precedence, authorization/marker/repository/replay order, results, exceptions, identity/trust ownership, and side-effect boundary.

### Exact future public export

```python
__all__ = (
    "build_phase_12_authorization_request_v1",
    "build_phase_12_authorization_trust_expectations_v1",
    "build_phase_12_validation_context_v1",
    "build_phase_12_accepted_marker_request_v1",
    "build_phase_12_repository_verification_request_v1",
    "build_phase_12_replay_request_v1",
    "run_phase_12_authorization_repository_validation_composition_v1",
)
```

No other function, class, Protocol, alias, constant, helper, bundle, adapter, result type, or private request type is public.

### Exact six public builders

All builders are keyword-only, have no defaults or variadics, use the existing private-dataclass field annotations, return `object`, directly construct exactly one matching private object, and forward every value unchanged by matching keyword. There is no inspection, conversion, normalization, copying, parsing, verification, timestamp/accepted-commit/path/policy validation, operational access, helper, common factory, dispatch, loop, registry, mapping, bundle, wrapper, proxy, lambda, partial, closure, cache, mutable state, or hidden default.

1. `build_phase_12_authorization_request_v1(*, document: str, canonical_payload_bytes: bytes, signature_bytes: bytes, activation_mode: str, owner_authorization_id: str, approval_checkpoint_id: str, approved_locked_commit: str, approved_at: str, expires_at: str, accepted_locked_commit_expectation: str) -> object` returns `_Phase12AuthorizationRequestV1`.
2. `build_phase_12_authorization_trust_expectations_v1(*, public_key_path: str, expected_public_key_fingerprint: str, expected_signing_key_identifier: str, revocation_state_path: str, expected_revocation_artifact_fingerprint: str, expected_revocation_schema_identifier: str, expected_revocation_checkpoint_identifier: str, expected_environment_identifier: str, expected_deployment_identifier: str) -> object` returns `_Phase12AuthorizationTrustExpectationsV1`.
3. `build_phase_12_validation_context_v1(*, configuration: object, now_utc: object) -> object` returns `_Phase12ValidationContextV1`.
4. `build_phase_12_accepted_marker_request_v1(*, path: str, expected_metadata_policy: object) -> object` returns `_Phase12AcceptedMarkerRequestV1`.
5. `build_phase_12_repository_verification_request_v1(*, source_path: str, repository_path: str) -> object` returns `_Phase12RepositoryVerificationRequestV1`.
6. `build_phase_12_replay_request_v1(*, path: str, expected_schema_identifier: str, expected_deployment_identifier: str) -> object` returns `_Phase12ReplayRequestV1`.

### Validation, exception, return, and exact-type acceptance

Builders rely only on Python signature binding and existing private dataclass construction; the private dataclasses add no constructor-time validation. Missing, unexpected, and positional calls raise normal Python signature `TypeError`. Construction, ordinary, and `BaseException` failures propagate unchanged. There are no catches, translation, inspection, retry, fallback, rollback, compensation, aggregation, custom errors, or secret disclosure. Builders return the exact private frozen/slotted object with no public Protocol/shared type/request type/alias/tuple/mapping/proxy/result wrapper. Callers forward it unchanged. The following checks remain unchanged and builder objects must pass them: `type(authorization_request) is _Phase12AuthorizationRequestV1`; `type(trust_expectations) is _Phase12AuthorizationTrustExpectationsV1`; `type(validation_context) is _Phase12ValidationContextV1`; `type(accepted_marker_request) is _Phase12AcceptedMarkerRequestV1`; `type(repository_verification_request) is _Phase12RepositoryVerificationRequestV1`; `type(replay_request) is _Phase12ReplayRequestV1`.

### Operational, trust, and locked-component boundary

Builders do not access filesystem, Git, subprocess, environment/cwd, credentials, authorization/key/revocation/marker/repository/replay/policy contents, network, clock, coordinator, runtime, service, provider, Telegram, activation, logging, cache, or serialization. Success proves only exact keyword-only acceptance, construction of one existing private immutable request, and field assignment; it proves no authorization, key, revocation, marker, repository, replay, path, configuration, policy, runtime, activation, service, infrastructure, provider, or Telegram condition. No change is permitted to the orchestration/tests, bounded authorization validation, callable adapter, marker/repository/remote-expectation/comparator/replay components, activation coordinator, or their tests.

### RED, GREEN, scope, and runtime prerequisite effect

RED is exactly 75 explicit unique top-level `test_` functions, allocation `3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3/3`, across preserved run operation/export; six signatures; private construction/forwarding/immutability/acceptance; validation and call-shape errors; exception propagation; private export/run-operation/operational/shared-contract/runtime/orchestration immutability; trust; and future runtime composability. No parametrization, generation, skips, xfails, import substitution, operational values, or real dependency invocation. RED imports the existing module and directly imports absent `build_phase_12_authorization_request_v1`: sole collection `ImportError`, pytest 2, tee 0, collected/executed 0, zero warnings. GREEN is 75 passed with no failures/skips/xfails/xpasses/warnings and virtualenv compilation passing.

Exact scope: `docs/phase_12_activation_configuration_v1.md`, `tests/test_phase_12_authorization_repository_structural_request_builders_v1.py`, and `engine/phase_12_authorization_repository_validation_composition_v1.py`. Exact commits: `docs: freeze phase 12 authorization repository structural request builder design`; `test: define phase 12 authorization repository structural request builders`; `feat: add phase 12 authorization repository structural request builders`. Remote lock unlocks only public construction of six opaque requests; runtime composition, configuration schema/references, operational binding, replay/time ownership, result handoff, coordinator/service integration, policy, provider, Telegram, and activation remain separate unauthorized prerequisites. Canonical configuration remains CLOSED and all production gates remain closed.

### Authorization validation injected callable clock boundary v1

Capability: `authorization validation injected callable clock boundary v1`. Module: `engine.phase_12_authorization_validation_injected_callable_clock_v1`; implementation: `engine/phase_12_authorization_validation_injected_callable_clock_v1.py`; tests: `tests/test_phase_12_authorization_validation_injected_callable_clock_v1.py`; documentation: this file. Side-effect class: pure immutable callable-clock binding. Owner policy is `C=C2`, `D=D4`, `E=E2`: expectations are public/domain-specific, the coordinator remains the CLOSED fail-closed authority, time ownership is injected callable, references and result exposure remain deferred, and trust non-guarantees are accepted.

The sole public type is `Phase12AuthorizationValidationInjectedCallableClockV1`, declared `@dataclass(frozen=True, slots=True, kw_only=True, repr=False)`, with normal dataclass equality/hash semantics and permitted direct construction. Its sole first-and-only field is `clock: Callable[[], object]`, without default, factory, descriptor, property, metadata, validation, or conversion. The sole public builder is `build_phase_12_authorization_validation_injected_callable_clock_v1(*, clock: Callable[[], object]) -> Phase12AuthorizationValidationInjectedCallableClockV1`; it directly returns exactly one `Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock)`. `Callable` is imported from `collections.abc`; this is a zero-argument opaque-object contract, not datetime, async, Protocol, Optional, Union, timezone, or temporal-validity contract.

`__all__` is exactly `("Phase12AuthorizationValidationInjectedCallableClockV1", "build_phase_12_authorization_validation_injected_callable_clock_v1")`. Binding forwards the callable unchanged by identity and contains no helper, factory, wrapper, proxy, adapter, registry, loop, mapping construction, partial, closure, decoration, inspection, copy, normalization, conversion, cache, memoization, or callable validation. Python signature binding and frozen dataclass construction are the only validation. Missing, unexpected, and positional calls retain normal `TypeError`; constructor, ordinary, and every `BaseException` propagate unchanged, with no try/except, translation, retry, fallback, rollback, compensation, aggregation, or custom error.

Construction, repr, equality, hashing, export inspection, and annotation inspection never invoke the callable. This slice produces no `now_utc`; invocation and any returned-object interpretation remain separately unauthorized. It prohibits datetime/time acquisition, environment, filesystem, paths, subprocess, Git, repository/replay/network, coordinator/runtime/service/provider/Telegram/activation, logging, serialization, caching, and global state. It proves only exact binding, one immutable object, identity storage, and zero invocation; it proves no clock correctness/safety/availability, returned-object or temporal validity, runtime/authorization/configuration/policy/activation, or infrastructure health.

A future invocation slice may call the stored callable once and forward the opaque result unchanged to `build_phase_12_validation_context_v1` and the locked coordinator; no private import, duplicate acquisition, default/global clock, consumer wiring, or locked-consumer modification occurs here. All existing authorization, request-builder, orchestration, adapter, coordinator, parser, key, revocation, signature, marker, repository, comparator, replay components and tests remain immutable.

RED first imports absent `Phase12AuthorizationValidationInjectedCallableClockV1` from absent module `engine.phase_12_authorization_validation_injected_callable_clock_v1`: sole `ModuleNotFoundError`, pytest 2, tee 0, collected/executed 0, warnings 0. GREEN is 60 unique explicit substantive tests, 20 categories x 3: type; builder; exports; frozen; slots; keyword-only; one field; `Callable[[], object]`; signature; defaults/variadics; direct construction; identity; zero invocation; no inspection/wrapping; call shape; ordinary exceptions; BaseException; no operational access; locked immutability; trust/future composability. No parametrization, generation, placeholders, assert-True-only/pass/ellipsis, skip/xfail, import hooks, `sys.modules` mutation, substitute implementation, real clock, or operational dependency.

Exact scope is this documentation file, `tests/test_phase_12_authorization_validation_injected_callable_clock_v1.py`, and `engine/phase_12_authorization_validation_injected_callable_clock_v1.py`. The original plan was three commits: `docs: freeze phase 12 authorization validation injected callable clock design`, `test: define phase 12 authorization validation injected callable clock`, and `feat: add phase 12 authorization validation injected callable clock`.

The accepted implementation provenance is four linear commits: `docs: freeze phase 12 authorization validation injected callable clock design`; `test: define phase 12 authorization validation injected callable clock`; `test: correct phase 12 authorization validation injected callable clock assertions`; and `feat: add phase 12 authorization validation injected callable clock`. The substantive RED contract was valid in scope and allocation, but three assertions produced false negatives during isolated GREEN. C08 was corrected to structurally inspect `collections.abc.Callable[[], object]` with `typing.get_origin` and `typing.get_args`; C14 was corrected to inspect one parsed AST while preserving direct `clock=clock` forwarding. All 60 names and the C01--C20 allocation remained unchanged, as did the other 57 test bodies and the implementation contract. Corrected isolated GREEN passed 60 tests. History rewrite was prohibited, so the correction was a separate linear test commit.

This provenance correction is itself committed separately after implementation because pre-push audit found the stale plan after implementation history already existed; documentation must describe actual committed provenance, and amend, squash, rebase, reset, and history rewrite remain prohibited. The final five-commit local provenance is: `docs: freeze phase 12 authorization validation injected callable clock design`; `test: define phase 12 authorization validation injected callable clock`; `test: correct phase 12 authorization validation injected callable clock assertions`; `feat: add phase 12 authorization validation injected callable clock`; and `docs: correct phase 12 authorization validation injected callable clock provenance`.

The capability contract is unchanged: `Callable[[], object]`, one immutable public binding type, one keyword-only public builder, sole `clock` field, direct identity forwarding, zero invocation, no datetime or temporal widening, no validation or exception translation, exact two-name export, no operational access, no invocation operation, and no consumer wiring. Accepted evidence remains isolated 60 passed, focused proven 14-file surface 1030 passed with unsupported 1671 and 1731 focused counts retired, and canonical full 5825 passed; evidence logs were hashed and removed. This documentation correction creates neither test nor implementation. The boundary binds no reference, expectation, request, validation context, runtime root, result handoff, service, provider, Telegram, deployment, activation, or production action. Next likely prerequisite is `authorization-validation callable clock invocation v1`, not authorized. The coordinator remains CLOSED authority, canonical configuration remains CLOSED, and all production gates remain closed.

### Authorization validation callable clock invocation v1

Capability: `authorization validation callable clock invocation v1`. Module: `engine.phase_12_authorization_validation_callable_clock_invocation_v1`; implementation: `engine/phase_12_authorization_validation_callable_clock_invocation_v1.py`; tests: `tests/test_phase_12_authorization_validation_callable_clock_invocation_v1.py`; documentation: this file. Its side-effect classification is exactly one invocation of a caller-owned stored callable.

#### Prerequisite and public dependency

The remotely locked injected callable-clock binding already owns `Callable[[], object]`. Invoking that bound callable is independently meaningful and uniquely minimal: it requires no protected reference, expectation schema, configuration-state contract, validation-context construction, coordinator, runtime root, consumer wiring, or temporal semantics. The future implementation imports only `Phase12AuthorizationValidationInjectedCallableClockV1` from `engine.phase_12_authorization_validation_injected_callable_clock_v1`; it imports no private binding detail, raw callable public input, Protocol, structural adapter, or runtime dependency container.

The sole public export is exactly:

~~~python
__all__ = (
    "invoke_phase_12_authorization_validation_callable_clock_v1",
)
~~~

The sole public operation is exactly:

~~~python
def invoke_phase_12_authorization_validation_callable_clock_v1(
    *,
    clock_binding: Phase12AuthorizationValidationInjectedCallableClockV1,
) -> object:
    return clock_binding.clock()
~~~

It has exactly one keyword-only parameter named `clock_binding`, no default, no positional public form, and no variadic parameter. Its public signature prohibits raw callable input; no `isinstance` or custom runtime validation is added, so structurally invalid values retain ordinary Python attribute behavior.

#### Exact invocation, return, validation, and exception ownership

The operation performs one direct `clock_binding.clock` field access, one exact callable invocation, and one direct return. It creates no local conversion, wrapper, result type, intermediate semantic object, helper, or shared factory. Each successful operation call invokes the stored callable exactly once: there is no invocation before entry, duplicate acquisition, retry, fallback, cache, memoization, prefetch, global storage, or result storage. The returned object is preserved unchanged by identity.

The return contract is exactly `object`, with no datetime, timezone-awareness, freshness, monotonicity, ordering, temporal-validity, determinism, authorization-validity, configuration-eligibility, runtime-readiness, activation-readiness, or production-readiness guarantee. No temporal-value schema exists.

Validation ownership is normal Python signature binding, normal attribute access, and normal callable invocation only. There is no `isinstance`, `callable()` validation, binding/result/null/datetime/timezone/semantic validation. Missing `clock_binding`, positional invocation, and unexpected keywords retain normal `TypeError`; a missing `clock` attribute retains normal `AttributeError`; a non-callable `clock` value retains normal `TypeError`. A callable ordinary `Exception` and every callable `BaseException` propagate as the exact instance. There is no try, except, translation, retry, fallback, rollback, compensation, aggregation, or custom error.

No binding alias, Protocol, helper, result wrapper, default/system clock, dependency container, runtime root, or consumer adapter is exported.

#### Operational, dependency, trust, and consumer boundary

There is no direct access to `datetime.now`, `datetime.utcnow`, `date.today`, `time.time`, `time.monotonic`, `perf_counter`, `process_time`, environment variables, filesystem/paths, subprocess, Git, repository, replay, network, request builders, validation context, coordinator, runtime, service, provider, Telegram, activation, deployment, or production state. The only permitted side effect is exactly one invocation of the caller-owned stored callable.

The implementation imports no validation context, coordinator, authorization parser/verifier, repository orchestration, request builder, runtime/service, provider, or Telegram module. Its positive guarantees are only that Python accepted the public call, the binding's stored callable was accessed and invoked exactly once, and the exact returned object was returned unchanged. It guarantees neither callable correctness/safety nor returned-object, temporal, authorization, configuration, runtime, production, infrastructure, network, service, provider, or Telegram health.

A later separately authorized slice may forward the returned opaque object unchanged to validation-context `now_utc` or activation-coordinator `now_utc`. This slice does not build validation context, call the coordinator, perform either handoff, duplicate acquisition, store the result, or create runtime state. The injected clock binding and its corrected tests, authorization/repository validation composition, repository orchestration, bounded composition, callable adapter, activation coordinator, structural request builders, parser, verifier, key, revocation, marker, repository, comparator, replay, runtime, service, provider, Telegram modules, and their existing tests remain immutable.

#### RED and substantive test contract

Future RED imports absent `invoke_phase_12_authorization_validation_callable_clock_v1` from absent `engine.phase_12_authorization_validation_callable_clock_invocation_v1`: one `ModuleNotFoundError`, pytest exit 2, tee exit 0, collected/executed 0, errors 1, failures/skips/xfails/xpasses/warnings 0, and no secondary error.

The future dedicated contract is exactly 36 unique explicit top-level tests: 12 categories x 3 tests. The categories are: public operation identity and exact export; exact signature and annotations; direct field access/invocation/return; exactly-once cardinality and returned-object identity; keyword-only and invalid public call shapes; missing-field and non-callable-field ownership; ordinary Exception propagation; BaseException propagation; no validation/retry/fallback/cache/conversion; no operational access; locked-component immutability; and trust non-overclaim with future composability without wiring. There is no parametrization, dynamic generation, alias, placeholder, `assert True`, pass, ellipsis, empty body, skip, xfail, import hook, `sys.modules` mutation, substitute implementation, real system clock, or operational dependency invocation. Tests use deterministic synthetic bindings/callables, exactly-once counters, and identity sentinels only.

#### Scope, commits, and prerequisite effect

The original planned provenance was three commits: `docs: freeze phase 12 authorization validation callable clock invocation design`; `test: define phase 12 authorization validation callable clock invocation`; and `feat: add phase 12 authorization validation callable clock invocation`.

The invocation slice scope remains exactly this documentation file, `tests/test_phase_12_authorization_validation_callable_clock_invocation_v1.py`, and `engine/phase_12_authorization_validation_callable_clock_invocation_v1.py`, plus the separately corrected locked binding test `tests/test_phase_12_authorization_validation_injected_callable_clock_v1.py`; no capability, test, implementation, regression, or authority contract changed.

The actual accepted implementation provenance is four commits:

1. `c69f3c4618550bba1908be1f18dd902420df27bc` — `docs: freeze phase 12 authorization validation callable clock invocation design`.
2. `a9ab5176fdd449d7f010810db9a317f84993742d` — `test: define phase 12 authorization validation callable clock invocation`.
3. `59a072b4654353d78e2e26cd6bcccc8d888f820d` — `feat: add phase 12 authorization validation callable clock invocation`.
4. `5aecd266e15c8ce15c8fd54f62ba861e72df3ae1` — `test: permit authorized phase 12 callable clock invocation dependency`.

The fourth commit corrects the sole focused false negative, `test_c19_02_locked_components_import_no_clock_boundary`. The invocation implementation correctly imports `Phase12AuthorizationValidationInjectedCallableClockV1` from `engine.phase_12_authorization_validation_injected_callable_clock_v1`, but the prior C19-02 assertion prohibited every external engine importer. C19-02 now permits exactly one external importer, `engine/phase_12_authorization_validation_callable_clock_invocation_v1.py`, and requires exactly one non-aliased import of only `Phase12AuthorizationValidationInjectedCallableClockV1`. Wildcard, private, additional-symbol, alias-based, consumer, coordinator, runtime, service, provider, Telegram, and unrelated-engine imports remain prohibited. The implementation and invocation tests required no correction; C19-01 and C19-03 and the other 59 binding-test bodies remain unchanged. The binding test count remains 60 and the invocation test count remains 36.

Accepted regression evidence is: isolated invocation 36 passed; corrected binding suite 60 passed; invocation reconfirmation 36 passed; corrected focused regression 1066 passed; and corrected canonical full regression 5861 passed, each with zero failures, errors, skips, xfails, xpasses, or warnings. The corrected focused evidence hash is `1cad30600e45a272ebc680fb1500325261dea3387ca8ffe18c0d4942bbc0de7b`; the corrected full evidence hash is `6fad08914dd8cfa24efd6e5815582be7e9d2dd1bed77f740705744cc1e761141`; evidence logs were hashed and removed.

This documentation-provenance correction is committed separately because the stale three-commit record was discovered after corrected regressions and actual history already contained the fourth test-correction commit. Documentation must describe actual committed provenance; amend, squash, merge, rebase, reset, cherry-pick, and history rewrite remain prohibited. The final five-commit local invocation-slice subject sequence is: `docs: freeze phase 12 authorization validation callable clock invocation design`; `test: define phase 12 authorization validation callable clock invocation`; `feat: add phase 12 authorization validation callable clock invocation`; `test: permit authorized phase 12 callable clock invocation dependency`; and `docs: correct phase 12 authorization validation callable clock invocation provenance`.

This capability invokes the caller-owned bound callable exactly once and returns its opaque object unchanged. It binds no protected reference, creates no expectation schema, changes no coordinator authority, builds no validation context, performs no temporal handoff, maps no authorization request, creates no runtime composition, exposes no result handoff, and authorizes no service, provider, Telegram, activation, deployment, or production action. Likely later prerequisites are validation-context temporal-value handoff v1 and coordinator temporal-value handoff v1; both remain unselected and unauthorized. The coordinator remains CLOSED authority, canonical configuration remains CLOSED, and all production gates remain closed.

## Phase 12 authorization trust-expectation boundary migration design study

Owner selection: `OWNER_SELECT_PHASE_12_TRUST_EXPECTATION_BOUNDARY_MIGRATION_DESIGN_ONLY`. This is a documentation-only architectural study. It selects neither an adapter nor a public-type promotion and authorizes no implementation, test, consumer change, exact-type relaxation, reference access, runtime composition, or production activity.

### Locked architecture and separate authorization record

The current trust-expectation type is private:

~~~python
_Phase12AuthorizationTrustExpectationsV1(
    *,
    public_key_path: str,
    expected_public_key_fingerprint: str,
    expected_signing_key_identifier: str,
    revocation_state_path: str,
    expected_revocation_artifact_fingerprint: str,
    expected_revocation_schema_identifier: str,
    expected_revocation_checkpoint_identifier: str,
    expected_environment_identifier: str,
    expected_deployment_identifier: str,
)
~~~

It remains frozen, slotted, keyword-only, repr-suppressed, private, and identity-preserving, with no defaults or variadics. Its exact field order is the order above. `public_key_path` and `revocation_state_path` are opaque reference values; the other seven fields are public domain expectations. The existing builder `build_phase_12_authorization_trust_expectations_v1` constructs exactly one private instance and forwards all supplied values unchanged. It performs no validation, normalization, parsing, comparison, path/reference access, or dependency invocation. Normal Python signature binding owns missing, positional, and unexpected-call errors; no ordinary `Exception` or `BaseException` is caught or translated.

`Phase12ActivationAuthorizationRecordV1` remains a distinct public, validated authorization-record type with fields `mode`, `owner_authorization_id`, `checkpoint_id`, `approved_locked_commit`, `approval_timestamp_utc`, `expires_at_utc`, and `accepted_locked_commit`. It is not a trust-expectation schema. Neither migration path may merge, wrap, replace, weaken, or change that record or its consumers.

The current exact consumer rule is:

~~~python
type(trust_expectations) is _Phase12AuthorizationTrustExpectationsV1
~~~

It is enforced by `engine/phase_12_authorization_repository_validation_composition_v1.py`; its structural request-builder tests assert the exact private type, field order, identity forwarding, and downstream acceptance. The bounded authorization-validation composition depends on the nine attribute names and validates them later as exact nonempty `str` values. The authorization-validation orchestration composes the existing boundary without becoming a public trust-contract owner. The locked documentation also prohibits public bundle classes, adapters, conversion classes, shared contracts, aliases, promotion, duplication, and export of the private type.

### Path A — public schema plus sole private-boundary adapter

The proposed public type is `Phase12PublicAuthorizationTrustExpectationsV1` in `engine.phase_12_public_authorization_trust_expectations_v1`. It would be a standard-library-only immutable nine-field schema with the exact current order and annotations. The proposed sole bridge is `adapt_phase_12_public_authorization_trust_expectations_to_private_boundary_v1` in `engine.phase_12_public_authorization_trust_expectations_private_boundary_adapter_v1`.

The bridge would depend inward only on the public schema and `_Phase12AuthorizationTrustExpectationsV1`, construct exactly one private value, and forward each field by identity. It would perform no reference read, validation, normalization, parsing, comparison, exception translation, repository/verifier/coordinator/runtime call, or other operational action. Existing exact-type consumers could remain unchanged because they would receive the private value. The public schema would import no private, runtime, coordinator, repository, service, provider, Telegram, or production module; only the bridge could import the private structural type.

This path creates two structurally identical definitions and therefore has field-order, annotation, and drift risk. A future adapter contract would have to mechanically assert exact nine-name order, annotations, one construction, and identity forwarding. It preserves current consumer compatibility but is not an additive three-file slice under the current lock: documentation prohibitions against adapters, public bundle types, duplication, and conversion must first be deliberately revised, and new public-schema, adapter, dependency-direction, exact-type-consumer, no-reference-access, no-validation, and trust-non-overclaim tests are required. Existing composition, builder, bounded-composition, orchestration, authorization-record, configuration, coordinator, clock, and runtime implementation files would remain protected unless a later proven contradiction requires a narrowly authorized correction.

### Path B — one canonical public exact consumer type

The proposed canonical public name is also `Phase12PublicAuthorizationTrustExpectationsV1`. This path would promote or replace the private exact consumer type so that one public type is canonical and every exact-type consumer accepts it. It removes duplicate-definition drift, but is a locked-boundary migration rather than an additive slice.

The study does not select whether the canonical type remains in `engine.phase_12_authorization_repository_validation_composition_v1` or moves to a dedicated public contract module; that choice controls import direction and circular-import risk. A public compatibility alias is not assumed: the locked no-alias and no-promotion rules currently prohibit one, and committed evidence identifies no external consumer for which compatibility can be claimed. The migration must therefore be atomic within the repository: characterize current behavior, introduce the canonical type, migrate exact-type checks and private-name assertions, retire the private name without an alias unless separately justified, then run focused and canonical regressions.

Affected migration evidence includes the defining composition module, its exact-type check, `tests/test_phase_12_authorization_repository_structural_request_builders_v1.py`, `tests/test_phase_12_authorization_repository_validation_composition_v1.py`, the bounded-composition and orchestration dependency tests, and this documentation. The authorization record, configuration, coordinator, clock binding/invocation, validation-context builder, parser, verifier, key, marker, replay, revocation, repository, comparator, runtime, service, provider, and Telegram components remain protected. This path has wider compatibility and regression exposure, but it makes the public contract the sole field owner without adding validation, semantic guarantees, reference access, or operational authority.

### Comparison, unresolved canonical ownership, and future ordering

Path A minimizes changes to existing exact-type consumers and offers an explicit compatibility bridge, but retains duplicate-field maintenance risk and requires a targeted architectural relaxation. Path B removes duplicate ownership but requires a controlled exact-type consumer migration, private-name retirement, and broader regression characterization. Both paths can remain pure, keep the two reference values opaque, preserve normal Python/dataclass error ownership, avoid exception translation, and leave the coordinator and canonical configuration CLOSED. Neither path may claim reference existence, validity, safety, authorization validity, eligibility, runtime readiness, or production readiness.

Committed evidence does not prove that preserving current consumers is safer than eliminating duplicate ownership, nor does it establish an external compatibility requirement. The canonical ownership decision is therefore `OWNER_DECISION_STILL_REQUIRED_AFTER_DESIGN`. The next authorized step must be one explicit owner choice between the future adapter path and the future canonical-public-type promotion path; no implementation is authorized by this study.

If the owner later selects Path A, the future phases are: documentation design freeze; public-schema RED and implementation; adapter RED and implementation; only then any proven locked-assertion correction; focused regression; canonical full regression; provenance correction if necessary; pre-push audit; and remote lock. If the owner later selects Path B, the future phases are: documentation migration freeze; migration-characterization RED; canonical public type introduction; consumer migration; private-type retirement; only then any proven locked-assertion correction; focused and canonical full regressions; provenance correction if necessary; pre-push audit; and remote lock. Neither ordering authorizes history rewrite, reference ownership, source ownership, accepted-commit ownership, result exposure, runtime composition, or production action.

### Owner-selected canonical public promotion contract

Owner selection: `OWNER_SELECT_PHASE_12_PROMOTE_TRUST_EXPECTATIONS_TO_PUBLIC_EXACT_CONSUMER_TYPE`. Promotion is selected over the adapter path. The rationale is single canonical ownership: a public/private pair with identical nine fields would create duplicate field-order and annotation drift, while committed evidence identifies no external compatibility requirement that justifies retaining a private alias or bridge. This remains future work only; no type, builder, import, consumer, test, or implementation has changed in this step.

The future canonical identity is `Phase12AuthorizationTrustExpectationsV1` in the dedicated inward-only module `engine.phase_12_authorization_trust_expectations_v1` (`engine/phase_12_authorization_trust_expectations_v1.py`). A dedicated module is selected because `engine.phase_12_authorization_repository_validation_composition_v1` is a composition and private-request-builder owner; exposing the public contract there would couple domain construction to composition internals. The canonical module imports only `dataclasses.dataclass`, exports exactly:

~~~python
__all__ = (
    "Phase12AuthorizationTrustExpectationsV1",
)
~~~

Direct keyword-only dataclass construction is the sole public construction surface. The future type is exactly `@dataclass(frozen=True, slots=True, kw_only=True)` with the existing nine ordered `str` fields, no defaults, variadics, `__post_init__`, helper, property, alternate constructor, mapping conversion, serialization behavior, validation, coercion, normalization, parsing, comparison, reference/path access, or operational behavior. Natural dataclass equality and repr are accepted. Caller-assigned values retain ordinary assignment identity. The two reference fields remain opaque, and protected-reference ownership remains deferred.

The migration is atomic within its canonical implementation-and-consumer-migration commit. `engine.phase_12_authorization_repository_validation_composition_v1` will import the public type, retire `_Phase12AuthorizationTrustExpectationsV1`, retire `build_phase_12_authorization_trust_expectations_v1` as redundant, remove that builder from `__all__`, migrate its Protocol and function annotations, and replace its exact check with `type(trust_expectations) is Phase12AuthorizationTrustExpectationsV1`. No `isinstance`, Protocol, duck-typed, mapping, subclass, union, private/public dual-type, adapter, conversion layer, fallback import, module `__getattr__`, `sys.modules` manipulation, compatibility container, or alias is permitted. No file is deleted: retirement is symbol removal from the current composition module. No committed point may contain two independently defined canonical nine-field types.

The exact known migration references are: the current defining composition module; `tests/test_phase_12_authorization_repository_structural_request_builders_v1.py`, which imports the builder and asserts the private type through its builder matrix; and `tests/test_phase_12_authorization_repository_validation_composition_v1.py`, which directly imports the private type. The defining module also contains the private Protocol annotation, function annotation, constructor call, and exact-type check. The documentation statements at the current locked architecture and bounded-composition sections that require privacy, no promotion, no aliases, no adapters, no public bundle types, no shared contract, or no conversion require a deliberately scoped future update. `engine.phase_12_bounded_authorization_validation_composition_v1.py` and `engine.phase_12_authorization_validation_repository_orchestration_composition_v1.py` depend on the nine attributes but do not own the private type; they are protected unless a future characterization proves a directly affected assertion.

The future dependency graph is one-way: composition and its tests import the dedicated canonical contract; the canonical contract imports no composition, request-builder, repository, validator, coordinator, clock, runtime, service, provider, Telegram, network, activation, deployment, or production module. This creates no circular import. `Phase12ActivationAuthorizationRecordV1` remains separate, validated, and entirely outside migration scope.

Existing structural-builder tests characterize the current exact field order, keyword-only builder surface, private construction, identity preservation, immutability, normal call-shape errors, no validation, and downstream acceptance. A dedicated future characterization file, `tests/test_phase_12_authorization_trust_expectation_promotion_characterization_v1.py`, is required before RED to enumerate the private-type consumer inventory, no-alias/no-adapter lock, exact type check, and single-canonical-type retirement conditions. The next RED then imports absent `Phase12AuthorizationTrustExpectationsV1` from absent `engine.phase_12_authorization_trust_expectations_v1`: one `ModuleNotFoundError`, pytest exit 2, tee exit 0, zero collected/executed, one error, and zero failures, skips, xfails, xpasses, or warnings.

The future file inventory is: ADD `engine/phase_12_authorization_trust_expectations_v1.py`, `tests/test_phase_12_authorization_trust_expectation_promotion_characterization_v1.py`, and `tests/test_phase_12_authorization_trust_expectations_v1.py`; MODIFY `engine/phase_12_authorization_repository_validation_composition_v1.py`, `tests/test_phase_12_authorization_repository_structural_request_builders_v1.py`, `tests/test_phase_12_authorization_repository_validation_composition_v1.py`, and this documentation; DELETE no file; PROTECTED_UNCHANGED the authorization record, configuration, coordinator, callable clock binding/invocation, validation-context builder, bounded composition, orchestration, parser, verifier, key, marker, replay, revocation, repository, comparator, runtime, service, provider, and Telegram modules unless later evidence proves a narrowly affected assertion.

Future commit classes are linear: (1) this owner-decision documentation freeze; (2) `test: characterize phase 12 authorization trust expectation promotion`; (3) `test: define phase 12 public canonical trust expectations`; (4) `feat: promote phase 12 authorization trust expectations to public canonical type`, containing the atomic canonical introduction, consumer migration, and private type/builder retirement; (5) only a proven narrow locked-test correction; (6) provenance documentation correction if needed; (7) focused and canonical full regressions with evidence cleanup; (8) final pre-push audit; and (9) separately authorized push and remote lock. No push occurs before characterization, RED, atomic migration, all required regressions, and any provenance correction pass.

The next authorized step is to define and commit the dedicated migration-characterization tests. The future migration creates one public structural type, preserves exact nine-field and exact-type semantics, eliminates duplicate private ownership, adds no adapter, and changes no authorization-record or CLOSED authority. It does not authorize reference access, source acquisition, accepted-commit ownership, result exposure, runtime composition, service, provider, Telegram, network, activation, deployment, or production action.
