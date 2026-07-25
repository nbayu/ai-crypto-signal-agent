from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class Phase12AuthorizationTrustExpectationsV1:
    public_key_path: str
    expected_public_key_fingerprint: str
    expected_signing_key_identifier: str
    revocation_state_path: str
    expected_revocation_artifact_fingerprint: str
    expected_revocation_schema_identifier: str
    expected_revocation_checkpoint_identifier: str
    expected_environment_identifier: str
    expected_deployment_identifier: str


__all__ = (
    "Phase12AuthorizationTrustExpectationsV1",
)
