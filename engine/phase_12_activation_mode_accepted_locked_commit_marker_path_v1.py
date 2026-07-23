"""Static canonical accepted-locked-commit marker path value."""

from dataclasses import dataclass as _dataclass


__all__ = (
    "Phase12ActivationAcceptedLockedCommitMarkerPathV1",
    "get_phase_12_activation_accepted_locked_commit_marker_path_v1",
)


_CANONICAL_PATH = "/var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker"


@_dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12ActivationAcceptedLockedCommitMarkerPathV1:
    """Immutable canonical marker path."""

    path: str

    def __post_init__(self) -> None:
        if type(self.path) is not str:
            raise TypeError()
        if self.path != _CANONICAL_PATH:
            raise ValueError()

    def __repr__(self) -> str:
        return "Phase12ActivationAcceptedLockedCommitMarkerPathV1()"


def get_phase_12_activation_accepted_locked_commit_marker_path_v1(
) -> Phase12ActivationAcceptedLockedCommitMarkerPathV1:
    """Return one fresh immutable canonical marker-path value."""
    return Phase12ActivationAcceptedLockedCommitMarkerPathV1(path=_CANONICAL_PATH)
