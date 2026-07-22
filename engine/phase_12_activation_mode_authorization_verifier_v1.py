"""Pure immutable authorization policy for Phase 12 activation modes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


_APPROVABLE_MODES = frozenset(
    (
        "CREDENTIAL_VALIDATION",
        "TELEGRAM_CONNECTIVITY_VALIDATION",
        "TELEGRAM_START_VALIDATION",
        "CONTROLLED_WORKLOAD",
    )
)
_UTC_ZERO = timedelta(0)


def _utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == _UTC_ZERO
    )


def _identifier(value: object) -> bool:
    return type(value) is str and bool(value)


def _commit(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _configuration_timestamp(value: object) -> datetime | None:
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


@dataclass(frozen=True, kw_only=True)
class Phase12ActivationAuthorizationRecordV1:
    """One immutable authorization record with no operational dependencies."""

    __slots__ = (
        "mode",
        "owner_authorization_id",
        "checkpoint_id",
        "approved_locked_commit",
        "approval_timestamp_utc",
        "expires_at_utc",
        "accepted_locked_commit",
    )

    mode: str
    owner_authorization_id: str
    checkpoint_id: str
    approved_locked_commit: str
    approval_timestamp_utc: datetime
    expires_at_utc: datetime
    accepted_locked_commit: str

    def __repr__(self) -> str:
        return "Phase12ActivationAuthorizationRecordV1()"

    def __post_init__(self) -> None:
        if type(self.mode) is not str or self.mode not in _APPROVABLE_MODES:
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _identifier(self.owner_authorization_id):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _identifier(self.checkpoint_id):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _commit(self.approved_locked_commit):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _commit(self.accepted_locked_commit):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _utc_datetime(self.approval_timestamp_utc):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if not _utc_datetime(self.expires_at_utc):
            raise ValueError("INVALID_AUTHORIZATION_RECORD")
        if self.approval_timestamp_utc >= self.expires_at_utc:
            raise ValueError("INVALID_AUTHORIZATION_RECORD")


@dataclass(frozen=True, slots=True, kw_only=True)
class Phase12ActivationModeAuthorizationVerifierV1:
    """Match one immutable record against coordinator-provided authorization context."""

    records: tuple[Phase12ActivationAuthorizationRecordV1, ...]

    def __post_init__(self) -> None:
        try:
            normalized = tuple(self.records)
        except Exception as error:
            raise ValueError("INVALID_AUTHORIZATION_POLICY") from error
        if any(type(record) is not Phase12ActivationAuthorizationRecordV1 for record in normalized):
            raise ValueError("INVALID_AUTHORIZATION_POLICY")
        object.__setattr__(self, "records", normalized)

    def __call__(
        self,
        *,
        configuration,
        activation_mode,
        owner_authorization_id,
        approval_checkpoint_id,
        approved_locked_commit,
        approved_at,
        expires_at,
        accepted_locked_commit,
        now_utc,
    ) -> bool:
        configuration_mode = configuration.activation_mode
        configuration_owner = configuration.owner_authorization_id
        configuration_checkpoint = configuration.approval_checkpoint_id
        configuration_commit = configuration.approved_locked_commit
        configuration_approved_at = configuration.approved_at
        configuration_expires_at = configuration.expires_at
        if (
            configuration_mode != activation_mode
            or configuration_owner != owner_authorization_id
            or configuration_checkpoint != approval_checkpoint_id
            or configuration_commit != approved_locked_commit
            or configuration_approved_at != approved_at
            or configuration_expires_at != expires_at
        ):
            return False
        if type(activation_mode) is not str or activation_mode not in _APPROVABLE_MODES:
            return False
        if not _identifier(owner_authorization_id) or not _identifier(approval_checkpoint_id):
            return False
        if not _commit(approved_locked_commit) or not _commit(accepted_locked_commit):
            return False
        if approved_locked_commit != accepted_locked_commit:
            return False
        if not _utc_datetime(now_utc):
            return False
        approval_timestamp = _configuration_timestamp(approved_at)
        expiration_timestamp = _configuration_timestamp(expires_at)
        if approval_timestamp is None or expiration_timestamp is None:
            return False
        if approval_timestamp >= expiration_timestamp:
            return False
        if now_utc < approval_timestamp or now_utc >= expiration_timestamp:
            return False
        matches = tuple(
            record
            for record in self.records
            if (
                record.mode == activation_mode
                and record.owner_authorization_id == owner_authorization_id
                and record.checkpoint_id == approval_checkpoint_id
                and record.approved_locked_commit == approved_locked_commit
                and record.accepted_locked_commit == accepted_locked_commit
                and record.approval_timestamp_utc == approval_timestamp
                and record.expires_at_utc == expiration_timestamp
            )
        )
        if len(matches) != 1:
            return False
        return True
