"""Pure validation of caller-supplied accepted-locked-commit marker metadata."""
from __future__ import annotations

from dataclasses import dataclass as _dataclass


__all__ = (
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1",
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1",
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1",
    "Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1",
    "validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
)


_ERROR_TEXT = "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA"
_ENTRY_KINDS = ("regular_file", "symbolic_link", "directory", "other")
_FAILURE_CODES = (
    "NON_REGULAR_ENTRY",
    "SYMBOLIC_LINK_ENTRY",
    "LINK_COUNT_MISMATCH",
    "OWNER_UID_MISMATCH",
    "GROUP_GID_MISMATCH",
    "PERMISSION_MODE_MISMATCH",
    "MARKER_SIZE_EXCEEDS_MAXIMUM",
)
_FAILURE_CODE_INDEX = {code: index for index, code in enumerate(_FAILURE_CODES)}


class Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1(Exception):
    """The sanitized public error for malformed metadata-validator input."""

    def __init__(self) -> None:
        super().__init__(_ERROR_TEXT)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1()"


def _invalid() -> Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1:
    return Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1()


def _require_entry_kind(value: object) -> None:
    if type(value) is not str:
        raise _invalid()
    if value not in _ENTRY_KINDS:
        raise _invalid()


def _require_nonnegative_int(value: object) -> None:
    if type(value) is not int:
        raise _invalid()
    if value < 0:
        raise _invalid()


def _require_permission_mode(value: object) -> None:
    if type(value) is not int:
        raise _invalid()
    if value < 0 or value > 0o7777:
        raise _invalid()


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerMetadataV1:
    """Immutable metadata facts supplied by a future filesystem inspector."""

    entry_kind: str
    link_count: int
    owner_uid: int
    group_gid: int
    permission_mode: int
    size_bytes: int

    def __post_init__(self) -> None:
        _require_entry_kind(self.entry_kind)
        _require_nonnegative_int(self.link_count)
        _require_nonnegative_int(self.owner_uid)
        _require_nonnegative_int(self.group_gid)
        _require_permission_mode(self.permission_mode)
        _require_nonnegative_int(self.size_bytes)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1()"

    def __init_subclass__(cls, **kwargs: object) -> None:
        def _subclass_init(instance: object) -> None:
            Phase12ActivationAcceptedLockedCommitMarkerMetadataV1.__init__(
                instance,
                entry_kind="regular_file",
                link_count=0,
                owner_uid=0,
                group_gid=0,
                permission_mode=0,
                size_bytes=0,
            )

        cls.__init__ = _subclass_init


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1:
    """Immutable metadata-validation policy supplied by the caller."""

    expected_owner_uid: int
    expected_group_gid: int
    required_permission_mode: int
    required_link_count: int
    maximum_size_bytes: int

    def __post_init__(self) -> None:
        _require_nonnegative_int(self.expected_owner_uid)
        _require_nonnegative_int(self.expected_group_gid)
        _require_permission_mode(self.required_permission_mode)
        _require_nonnegative_int(self.required_link_count)
        _require_nonnegative_int(self.maximum_size_bytes)

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1()"

    def __init_subclass__(cls, **kwargs: object) -> None:
        def _subclass_init(instance: object) -> None:
            Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1.__init__(
                instance,
                expected_owner_uid=0,
                expected_group_gid=0,
                required_permission_mode=0,
                required_link_count=0,
                maximum_size_bytes=0,
            )

        cls.__init__ = _subclass_init


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1:
    """Immutable, non-authorizing metadata-validation result."""

    is_valid: bool
    failure_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.is_valid) is not bool:
            raise _invalid()
        if type(self.failure_codes) is not tuple:
            raise _invalid()
        previous_index = -1
        for code in self.failure_codes:
            if type(code) is not str:
                raise _invalid()
            index = _FAILURE_CODE_INDEX.get(code)
            if index is None or index <= previous_index:
                raise _invalid()
            previous_index = index
        if self.is_valid:
            if self.failure_codes != ():
                raise _invalid()
        elif self.failure_codes == ():
            raise _invalid()

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1()"


def validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1(
    *,
    metadata: Phase12ActivationAcceptedLockedCommitMarkerMetadataV1,
    policy: Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1,
) -> Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1:
    """Validate metadata facts against policy without any filesystem or trust decision."""
    if type(metadata) is not Phase12ActivationAcceptedLockedCommitMarkerMetadataV1:
        raise _invalid()
    if type(policy) is not Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1:
        raise _invalid()

    failure_codes: list[str] = []
    if metadata.entry_kind != "regular_file":
        failure_codes.append("NON_REGULAR_ENTRY")
    if metadata.entry_kind == "symbolic_link":
        failure_codes.append("SYMBOLIC_LINK_ENTRY")
    if metadata.link_count != policy.required_link_count:
        failure_codes.append("LINK_COUNT_MISMATCH")
    if metadata.owner_uid != policy.expected_owner_uid:
        failure_codes.append("OWNER_UID_MISMATCH")
    if metadata.group_gid != policy.expected_group_gid:
        failure_codes.append("GROUP_GID_MISMATCH")
    if metadata.permission_mode != policy.required_permission_mode:
        failure_codes.append("PERMISSION_MODE_MISMATCH")
    if metadata.size_bytes > policy.maximum_size_bytes:
        failure_codes.append("MARKER_SIZE_EXCEEDS_MAXIMUM")

    return Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1(
        is_valid=not failure_codes,
        failure_codes=tuple(failure_codes),
    )
