"""Pure canonical Phase 12 replay identity derivation."""
from __future__ import annotations
from hashlib import sha256


__all__ = (
    "derive_phase_12_canonical_replay_identity_v1",
)


_PHASE_12_CANONICAL_REPLAY_IDENTITY_DOMAIN_V1 = (
    "AI_CRYPTO_SIGNAL_AGENT_PHASE_12_OWNER_APPROVAL_REPLAY_IDENTITY_V1"
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
    if type(replay_control_value) is not str:
        raise TypeError()
    if replay_control_value == "":
        raise TypeError()
    if type(deployment_identifier) is not str:
        raise TypeError()
    if deployment_identifier == "":
        raise TypeError()
    if type(owner_authorization_id) is not str:
        raise TypeError()
    if owner_authorization_id == "":
        raise TypeError()
    if type(checkpoint_id) is not str:
        raise TypeError()
    if checkpoint_id == "":
        raise TypeError()
    if type(approved_locked_commit) is not str:
        raise TypeError()
    if approved_locked_commit == "":
        raise TypeError()
    if type(environment_identifier) is not str:
        raise TypeError()
    if environment_identifier == "":
        raise TypeError()

    fields = (
        _PHASE_12_CANONICAL_REPLAY_IDENTITY_DOMAIN_V1,
        replay_control_value,
        deployment_identifier,
        owner_authorization_id,
        checkpoint_id,
        approved_locked_commit,
        environment_identifier,
    )
    serialized_parts: list[bytes] = []
    for value in fields:
        encoded = value.encode("utf-8")
        serialized_parts.append(len(encoded).to_bytes(8, "big", signed=False))
        serialized_parts.append(encoded)
    serialized = b"".join(serialized_parts)
    return sha256(serialized).hexdigest()
