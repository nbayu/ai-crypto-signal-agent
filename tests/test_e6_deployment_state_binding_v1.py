from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
import inspect

import pytest

import engine.e6_deployment_state_binding_v1 as module
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    E6DeploymentProfileV1,
    E6DeploymentStateBindingErrorV1,
    build_e6_deployment_state_binding_v1,
)


COMMIT = "ee332b790e2be56ae309be9af12dabc2427f0ab1"


def _binding(profile: E6DeploymentProfileV1 | str = "CANDIDATE_CANARY"):
    return build_e6_deployment_state_binding_v1(
        deployment_profile=profile, release_commit=COMMIT
    )


def test_profile_set_commit_validation_and_immutable_equality() -> None:
    assert tuple(profile.value for profile in E6DeploymentProfileV1) == (
        "CANDIDATE_CANARY",
        "PRODUCTION",
    )
    first = _binding()
    second = _binding(E6DeploymentProfileV1.CANDIDATE_CANARY)
    assert first == second
    assert first.binding_version == E6_DEPLOYMENT_STATE_BINDING_VERSION_V1
    assert first.to_mapping() == second.to_mapping()
    with pytest.raises(FrozenInstanceError):
        first.state_root = "/tmp/detached"  # type: ignore[misc]
    for value in ("UNKNOWN", "candidate_canary", "", object()):
        with pytest.raises(E6DeploymentStateBindingErrorV1):
            build_e6_deployment_state_binding_v1(
                deployment_profile=value, release_commit=COMMIT  # type: ignore[arg-type]
            )
    for value in (COMMIT.upper(), COMMIT[:-1], "g" * 40, "0" * 41, ""):
        with pytest.raises(E6DeploymentStateBindingErrorV1):
            build_e6_deployment_state_binding_v1(
                deployment_profile="CANDIDATE_CANARY", release_commit=value
            )


def test_candidate_current_head_vector_is_exact_and_fully_isolated() -> None:
    value = _binding()
    identity = f"ai-crypto-signal-agent-e6-candidate-{COMMIT}"
    state = f"/var/lib/{identity}"
    owner = f"{state}/owner-blueprint"
    runtime = f"/run/{identity}"
    control = f"/var/lib/ai-crypto-signal-agent-e6-installations/{COMMIT}"
    configuration = f"/etc/ai-crypto-signal-agent/e6-candidates/{COMMIT}"
    assert value.service_unit == f"{identity}.service"
    assert value.timer_unit == f"{identity}.timer"
    assert value.state_root == state
    assert value.owner_state_root == value.ledger_root == owner
    assert value.active_ledger_path == f"{owner}/active-signal-ledger-v2.json"
    assert value.owner_state_path == f"{owner}/telegram-owner-control-state-v1.json"
    assert value.publication_root == f"{state}/publication-evidence"
    assert value.operational_artifact_root == f"{state}/operational-artifacts"
    assert value.runtime_root == runtime
    assert value.runtime_lock == f"{runtime}/e6-operational.lock"
    assert value.cache_root == f"/var/cache/{identity}"
    assert value.control_root == control
    assert value.install_pointer == f"{control}/installed-release.path"
    assert value.rollback_pointer == f"{control}/rollback-release.path"
    assert value.accepted_marker == f"{control}/accepted-release.marker"
    assert value.kill_switch == f"{control}/kill-switch.active"
    assert value.configuration_root == configuration
    assert value.activation_configuration_path == f"{configuration}/activation-v1.env"
    assert value.credential_metadata_path == f"{configuration}/credentials.metadata"
    candidate_authority = "\n".join(str(item) for item in value.to_mapping().values())
    for forbidden in (
        "/var/lib/ai-crypto-signal-agent/phase09r1",
        "/var/lib/ai-crypto-signal-agent/operational-artifacts",
        "/run/ai-crypto-signal-agent/e6-operational.lock",
        "/var/lib/ai-crypto-signal-agent/e6-installed-release.path",
        "ai-crypto-signal-agent-e6.service",
    ):
        assert forbidden not in candidate_authority


def test_production_binding_is_stable_and_retains_authoritative_state() -> None:
    value = _binding("PRODUCTION")
    assert value.service_unit == "ai-crypto-signal-agent-e6-production.service"
    assert value.timer_unit == "ai-crypto-signal-agent-e6-production.timer"
    assert value.state_root == "/var/lib/ai-crypto-signal-agent/phase09r1"
    assert value.owner_state_root == f"{value.state_root}/owner-blueprint"
    assert value.active_ledger_path.endswith("/active-signal-ledger-v2.json")
    assert value.owner_state_path.endswith("/telegram-owner-control-state-v1.json")
    assert value.publication_root == f"{value.state_root}/production-signals"
    assert value.runtime_root == "/run/ai-crypto-signal-agent-e6-production"
    assert value.runtime_lock == f"{value.runtime_root}/e6-operational.lock"
    assert value.cache_root == "/var/cache/ai-crypto-signal-agent-e6-production"
    assert value.control_root == "/var/lib/ai-crypto-signal-agent-e6-production-control"
    assert "candidate" not in "\n".join(
        str(item) for item in value.to_mapping().values()
    ).lower()
    assert "ai-crypto-signal-agent-e6.service" not in {
        value.service_unit,
        value.timer_unit,
    }


def test_direct_dataclass_path_or_unit_override_fails_closed() -> None:
    value = _binding()
    for changes in (
        {"state_root": "/tmp/arbitrary"},
        {"active_ledger_path": "/tmp/ledger.json"},
        {"owner_state_path": "/tmp/owner.json"},
        {"runtime_root": "/run/ai-crypto-signal-agent"},
        {"runtime_lock": "/run/ai-crypto-signal-agent/e6-operational.lock"},
        {"service_unit": "ai-crypto-signal-agent-e6.service"},
        {"release_commit": "f" * 40},
    ):
        with pytest.raises(E6DeploymentStateBindingErrorV1):
            replace(value, **changes)


def test_candidate_production_legacy_and_old_e6_namespaces_are_disjoint() -> None:
    candidate = _binding()
    production = _binding("PRODUCTION")
    candidate_values = {
        candidate.service_unit,
        candidate.timer_unit,
        candidate.state_root,
        candidate.runtime_root,
        candidate.runtime_lock,
        candidate.cache_root,
        candidate.control_root,
        candidate.configuration_root,
    }
    production_values = {
        production.service_unit,
        production.timer_unit,
        production.state_root,
        production.runtime_root,
        production.runtime_lock,
        production.cache_root,
        production.control_root,
        production.configuration_root,
    }
    assert candidate_values.isdisjoint(production_values)
    assert candidate_values.isdisjoint(
        {
            "ai-crypto-signal-agent.service",
            "ai-crypto-signal-agent.timer",
            "ai-crypto-signal-agent-e6.service",
            "ai-crypto-signal-agent-e6.timer",
            "/run/ai-crypto-signal-agent",
            "/run/ai-crypto-signal-agent/e6-operational.lock",
            "/var/lib/ai-crypto-signal-agent/e6-installed-release.path",
        }
    )
    assert len(
        {
            candidate.runtime_lock,
            production.runtime_lock,
            "/run/ai-crypto-signal-agent/e6-operational.lock",
            "/run/ai-crypto-signal-agent/phase09r1-operational.lock",
        }
    ) == 4


def test_ownership_policy_is_exact_and_contains_no_secret_value_surface() -> None:
    policy = _binding().ownership_policy.to_mapping()
    assert policy == {
        "state_owner": "ai-crypto-signal-agent",
        "state_group": "ai-crypto-signal-agent",
        "state_root_mode": "0750",
        "private_directory_mode": "0700",
        "state_file_mode": "0600",
        "runtime_root_mode": "0750",
        "runtime_lock_mode": "0600",
        "cache_root_mode": "0700",
        "control_owner": "root",
        "control_group": "ai-crypto-signal-agent",
        "control_parent_mode": "0750",
        "pointer_mode": "0440",
        "marker_owner": "root",
        "marker_group": "root",
        "marker_mode": "0400",
        "configuration_file_mode": "0640",
        "secret_environment_owner": "root",
        "secret_environment_group": "root",
        "secret_environment_mode": "0600",
    }
    assert not {"api_key", "token", "secret_value"}.intersection(policy)


def test_binding_module_is_pure_and_has_no_external_or_current_identity_source() -> None:
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported.intersection(
        {"os", "pathlib", "random", "socket", "subprocess", "requests", "httpx"}
    )
    for marker in (
        "os.environ",
        "getenv(",
        "git ",
        "datetime",
        "hostname",
        "ee332b790e2be56ae309be9af12dabc2427f0ab1",
    ):
        assert marker not in source
