"""Pure adapter from inspector facts to locked validator metadata."""

from engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_inspector_v1 import (
    Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1 as _InspectionFactsV1,
)
from engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1 import (
    Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1 as _PolicyV1,
    Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1 as _ResultV1,
    Phase12ActivationAcceptedLockedCommitMarkerMetadataV1 as _MetadataV1,
    validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1 as _validate,
)


__all__ = (
    "compose_phase_12_activation_accepted_locked_commit_marker_metadata_validation_v1",
)


def compose_phase_12_activation_accepted_locked_commit_marker_metadata_validation_v1(
    *,
    inspection_facts: _InspectionFactsV1,
    policy: _PolicyV1,
) -> _ResultV1:
    """Adapt one immutable inspection snapshot for one explicit policy validation."""
    if type(inspection_facts) is not _InspectionFactsV1:
        raise TypeError()
    if type(policy) is not _PolicyV1:
        raise TypeError()

    metadata = _MetadataV1(
        entry_kind=inspection_facts.entry_kind,
        link_count=inspection_facts.link_count,
        owner_uid=inspection_facts.owner_uid,
        group_gid=inspection_facts.group_gid,
        permission_mode=inspection_facts.permission_mode,
        size_bytes=inspection_facts.size_bytes,
    )
    return _validate(metadata=metadata, policy=policy)
