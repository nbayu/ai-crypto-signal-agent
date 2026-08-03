"""Pure two-profile deployment and mutable-state authority for E6."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
import re
from typing import Final


E6_DEPLOYMENT_STATE_BINDING_VERSION_V1: Final = (
    "e6-deployment-state-binding-v1"
)
E6_SERVICE_USER_V1: Final = "ai-crypto-signal-agent"
E6_SERVICE_GROUP_V1: Final = "ai-crypto-signal-agent"
E6_LOG_POLICY_V1: Final = "NONE_JOURNALD_ONLY"

_COMMIT40 = re.compile(r"[0-9a-f]{40}\Z")
_RELEASES_ROOT: Final = "/opt/ai-crypto-signal-agent-releases"
_LEGACY_STATE_ROOT: Final = "/var/lib/ai-crypto-signal-agent/phase09r1"
_LEGACY_OPERATIONAL_ROOT: Final = (
    "/var/lib/ai-crypto-signal-agent/operational-artifacts"
)
_OLD_E6_RUNTIME_ROOT: Final = "/run/ai-crypto-signal-agent"
_OLD_E6_CONTROL_PATHS: Final = frozenset(
    {
        "/var/lib/ai-crypto-signal-agent/e6-installed-release.path",
        "/var/lib/ai-crypto-signal-agent/e6-rollback-release.path",
        "/var/lib/ai-crypto-signal-agent/e6-accepted-release.marker",
        "/var/lib/ai-crypto-signal-agent/e6-kill-switch.active",
    }
)
_ERROR_CODE: Final = "INVALID_E6_DEPLOYMENT_STATE_BINDING"


class E6DeploymentProfileV1(str, Enum):
    """The complete closed set of E6 deployment-authority profiles."""

    CANDIDATE_CANARY = "CANDIDATE_CANARY"
    PRODUCTION = "PRODUCTION"


class E6DeploymentStateBindingErrorV1(ValueError):
    """Sanitized failure for malformed or internally detached bindings."""

    def __init__(self) -> None:
        self.code = _ERROR_CODE
        super().__init__(_ERROR_CODE)


def _invalid() -> None:
    raise E6DeploymentStateBindingErrorV1() from None


@dataclass(frozen=True, slots=True)
class E6DeploymentOwnershipPolicyV1:
    """Nonsecret owner/group/mode authority for rendered host objects."""

    state_owner: str = E6_SERVICE_USER_V1
    state_group: str = E6_SERVICE_GROUP_V1
    state_root_mode: str = "0750"
    private_directory_mode: str = "0700"
    state_file_mode: str = "0600"
    runtime_root_mode: str = "0750"
    runtime_lock_mode: str = "0600"
    cache_root_mode: str = "0700"
    control_owner: str = "root"
    control_group: str = E6_SERVICE_GROUP_V1
    control_parent_mode: str = "0750"
    pointer_mode: str = "0440"
    marker_owner: str = "root"
    marker_group: str = "root"
    marker_mode: str = "0400"
    configuration_file_mode: str = "0640"
    secret_environment_owner: str = "root"
    secret_environment_group: str = "root"
    secret_environment_mode: str = "0600"

    def __post_init__(self) -> None:
        expected = E6DeploymentOwnershipPolicyV1.__dataclass_fields__
        for name, definition in expected.items():
            if getattr(self, name) != definition.default:
                _invalid()

    def to_mapping(self) -> dict[str, str]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


def _candidate_values(commit: str) -> dict[str, str]:
    identity = f"ai-crypto-signal-agent-e6-candidate-{commit}"
    state = f"/var/lib/{identity}"
    owner = f"{state}/owner-blueprint"
    runtime = f"/run/{identity}"
    control = f"/var/lib/ai-crypto-signal-agent-e6-installations/{commit}"
    configuration = f"/etc/ai-crypto-signal-agent/e6-candidates/{commit}"
    return {
        "release_root": f"{_RELEASES_ROOT}/{commit}",
        "service_unit": f"{identity}.service",
        "timer_unit": f"{identity}.timer",
        "state_root": state,
        "owner_state_root": owner,
        "ledger_root": owner,
        "active_ledger_path": f"{owner}/active-signal-ledger-v2.json",
        "owner_state_path": (
            f"{owner}/telegram-owner-control-state-v1.json"
        ),
        "publication_root": f"{state}/publication-evidence",
        "operational_artifact_root": f"{state}/operational-artifacts",
        "runtime_root": runtime,
        "runtime_lock": f"{runtime}/e6-operational.lock",
        "cache_root": f"/var/cache/{identity}",
        "control_root": control,
        "install_pointer": f"{control}/installed-release.path",
        "rollback_pointer": f"{control}/rollback-release.path",
        "accepted_marker": f"{control}/accepted-release.marker",
        "kill_switch": f"{control}/kill-switch.active",
        "configuration_root": configuration,
        "activation_configuration_path": f"{configuration}/activation-v1.env",
        "credential_metadata_path": f"{configuration}/credentials.metadata",
    }


def _production_values(commit: str) -> dict[str, str]:
    identity = "ai-crypto-signal-agent-e6-production"
    owner = f"{_LEGACY_STATE_ROOT}/owner-blueprint"
    runtime = f"/run/{identity}"
    control = "/var/lib/ai-crypto-signal-agent-e6-production-control"
    configuration = "/etc/ai-crypto-signal-agent/e6-production"
    return {
        "release_root": f"{_RELEASES_ROOT}/{commit}",
        "service_unit": f"{identity}.service",
        "timer_unit": f"{identity}.timer",
        "state_root": _LEGACY_STATE_ROOT,
        "owner_state_root": owner,
        "ledger_root": owner,
        "active_ledger_path": f"{owner}/active-signal-ledger-v2.json",
        "owner_state_path": (
            f"{owner}/telegram-owner-control-state-v1.json"
        ),
        "publication_root": f"{_LEGACY_STATE_ROOT}/production-signals",
        "operational_artifact_root": _LEGACY_OPERATIONAL_ROOT,
        "runtime_root": runtime,
        "runtime_lock": f"{runtime}/e6-operational.lock",
        "cache_root": f"/var/cache/{identity}",
        "control_root": control,
        "install_pointer": f"{control}/installed-release.path",
        "rollback_pointer": f"{control}/rollback-release.path",
        "accepted_marker": f"{control}/accepted-release.marker",
        "kill_switch": f"{control}/kill-switch.active",
        "configuration_root": configuration,
        "activation_configuration_path": f"{configuration}/activation-v1.env",
        "credential_metadata_path": f"{configuration}/credentials.metadata",
    }


def _expected_values(
    profile: E6DeploymentProfileV1, release_commit: str
) -> dict[str, str]:
    if profile is E6DeploymentProfileV1.CANDIDATE_CANARY:
        return _candidate_values(release_commit)
    if profile is E6DeploymentProfileV1.PRODUCTION:
        return _production_values(release_commit)
    _invalid()


@dataclass(frozen=True, slots=True)
class E6DeploymentStateBindingV1:
    """One immutable profile/commit-derived deployment authority object."""

    binding_version: str
    deployment_profile: E6DeploymentProfileV1
    release_commit: str
    release_root: str
    service_unit: str
    timer_unit: str
    state_root: str
    owner_state_root: str
    ledger_root: str
    active_ledger_path: str
    owner_state_path: str
    publication_root: str
    operational_artifact_root: str
    runtime_root: str
    runtime_lock: str
    cache_root: str
    log_policy: str
    control_root: str
    install_pointer: str
    rollback_pointer: str
    accepted_marker: str
    kill_switch: str
    configuration_root: str
    activation_configuration_path: str
    credential_metadata_path: str
    service_user: str
    service_group: str
    ownership_policy: E6DeploymentOwnershipPolicyV1

    def __post_init__(self) -> None:
        try:
            if (
                self.binding_version != E6_DEPLOYMENT_STATE_BINDING_VERSION_V1
                or type(self.deployment_profile) is not E6DeploymentProfileV1
                or type(self.release_commit) is not str
                or _COMMIT40.fullmatch(self.release_commit) is None
                or self.log_policy != E6_LOG_POLICY_V1
                or self.service_user != E6_SERVICE_USER_V1
                or self.service_group != E6_SERVICE_GROUP_V1
                or type(self.ownership_policy) is not E6DeploymentOwnershipPolicyV1
            ):
                _invalid()
            self.ownership_policy.__post_init__()
            expected = _expected_values(
                self.deployment_profile, self.release_commit
            )
            if any(getattr(self, name) != value for name, value in expected.items()):
                _invalid()
            self._validate_authority_boundaries()
        except E6DeploymentStateBindingErrorV1:
            raise
        except Exception:
            _invalid()

    def _validate_authority_boundaries(self) -> None:
        state_paths = (
            self.state_root,
            self.owner_state_root,
            self.ledger_root,
            self.active_ledger_path,
            self.owner_state_path,
            self.publication_root,
            self.operational_artifact_root,
        )
        if self.owner_state_root != self.ledger_root:
            _invalid()
        if not all(
            path == self.state_root or path.startswith(f"{self.state_root}/")
            for path in state_paths
            if path != self.operational_artifact_root
        ):
            _invalid()
        if not self.runtime_lock.startswith(f"{self.runtime_root}/"):
            _invalid()
        if not all(
            path == self.control_root or path.startswith(f"{self.control_root}/")
            for path in (
                self.install_pointer,
                self.rollback_pointer,
                self.accepted_marker,
                self.kill_switch,
            )
        ):
            _invalid()
        if not all(
            path == self.configuration_root
            or path.startswith(f"{self.configuration_root}/")
            for path in (
                self.activation_configuration_path,
                self.credential_metadata_path,
            )
        ):
            _invalid()
        if self.deployment_profile is E6DeploymentProfileV1.CANDIDATE_CANARY:
            forbidden = (
                _LEGACY_STATE_ROOT,
                _LEGACY_OPERATIONAL_ROOT,
                _OLD_E6_RUNTIME_ROOT,
            )
            candidate_paths = (
                *state_paths,
                self.runtime_root,
                self.runtime_lock,
                self.cache_root,
                self.control_root,
                self.configuration_root,
            )
            if any(
                path == root or path.startswith(f"{root}/")
                for path in candidate_paths
                for root in forbidden
            ):
                _invalid()
            if any(path in _OLD_E6_CONTROL_PATHS for path in candidate_paths):
                _invalid()
            if self.service_unit in {
                "ai-crypto-signal-agent.service",
                "ai-crypto-signal-agent-e6.service",
                "ai-crypto-signal-agent-e6-production.service",
            }:
                _invalid()
        else:
            candidate_marker = "ai-crypto-signal-agent-e6-candidate-"
            if any(
                candidate_marker in value
                for value in (
                    self.service_unit,
                    self.timer_unit,
                    self.state_root,
                    self.runtime_root,
                    self.cache_root,
                    self.control_root,
                    self.configuration_root,
                )
            ):
                _invalid()

    def to_mapping(self) -> dict[str, object]:
        """Return deterministic nonsecret data suitable for activation metadata."""

        result: dict[str, object] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, Enum):
                result[field.name] = value.value
            elif isinstance(value, E6DeploymentOwnershipPolicyV1):
                result[field.name] = value.to_mapping()
            else:
                result[field.name] = value
        return result


def build_e6_deployment_state_binding_v1(
    *, deployment_profile: E6DeploymentProfileV1 | str, release_commit: str
) -> E6DeploymentStateBindingV1:
    """Derive one closed binding from only an exact profile and commit."""

    try:
        profile = E6DeploymentProfileV1(deployment_profile)
    except (TypeError, ValueError):
        _invalid()
    if type(release_commit) is not str or _COMMIT40.fullmatch(release_commit) is None:
        _invalid()
    values = _expected_values(profile, release_commit)
    return E6DeploymentStateBindingV1(
        binding_version=E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
        deployment_profile=profile,
        release_commit=release_commit,
        log_policy=E6_LOG_POLICY_V1,
        service_user=E6_SERVICE_USER_V1,
        service_group=E6_SERVICE_GROUP_V1,
        ownership_policy=E6DeploymentOwnershipPolicyV1(),
        **values,
    )


__all__ = (
    "E6_DEPLOYMENT_STATE_BINDING_VERSION_V1",
    "E6_LOG_POLICY_V1",
    "E6_SERVICE_GROUP_V1",
    "E6_SERVICE_USER_V1",
    "E6DeploymentOwnershipPolicyV1",
    "E6DeploymentProfileV1",
    "E6DeploymentStateBindingErrorV1",
    "E6DeploymentStateBindingV1",
    "build_e6_deployment_state_binding_v1",
)
