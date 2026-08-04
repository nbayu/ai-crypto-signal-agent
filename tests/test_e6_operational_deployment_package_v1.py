from __future__ import annotations

import os
from pathlib import Path
import grp
import hashlib
import json
import re
import subprocess

import pytest

from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
)
from engine.e6_activation_configuration_v1 import (
    E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
    _EXPECTED_KEYS,
)
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    build_e6_deployment_state_binding_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deploy/e6_operational_v1"
BIN = PACKAGE / "bin"
SYSTEMD = PACKAGE / "systemd"
COMMIT = "ee332b790e2be56ae309be9af12dabc2427f0ab1"
TREE = "b" * 40
TRUSTED = "007f8dee851655fae76b70dc36c3be59612a7725"
PAYLOAD = {
    "README.md": "0644",
    "bin/ai-crypto-signal-agent-e6-health": "0755",
    "bin/ai-crypto-signal-agent-e6-rollback": "0755",
    "bin/ai-crypto-signal-agent-e6-run-once": "0755",
    "deployment-package-manifest.txt": "0644",
    "systemd/ai-crypto-signal-agent-e6-production.service.in": "0644",
    "systemd/ai-crypto-signal-agent-e6-production.timer": "0644",
    "systemd/ai-crypto-signal-agent-e6.service.in": "0644",
    "systemd/ai-crypto-signal-agent-e6.timer": "0644",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _directives(text: str, name: str) -> list[str]:
    return [line.split("=", 1)[1] for line in text.splitlines() if line.startswith(f"{name}=")]


def _render_profile(text: str, deployment_profile: str) -> str:
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile=deployment_profile, release_commit=COMMIT
    )
    replacements = {
        "@@RELEASE_ROOT@@": binding.release_root,
        "@@E6_SOURCE_COMMIT@@": COMMIT,
        "@@E6_SOURCE_TREE@@": TREE,
        "@@TRUSTED_CHECKPOINT_COMMIT@@": TRUSTED,
        "@@E6_STATE_ROOT@@": binding.state_root,
        "@@E6_OPERATIONAL_ARTIFACT_ROOT@@": binding.operational_artifact_root,
        "@@E6_RUNTIME_ROOT@@": binding.runtime_root,
        "@@E6_CACHE_ROOT@@": binding.cache_root,
        "@@E6_ACCEPTED_RELEASE_MARKER_PATH@@": binding.accepted_marker,
        "@@E6_ACTIVATION_CONFIGURATION_PATH@@": binding.activation_configuration_path,
        "@@E6_CREDENTIAL_METADATA_PATH@@": binding.credential_metadata_path,
        "@@E6_ACTIVE_SIGNAL_LEDGER_PATH@@": binding.active_ledger_path,
        "@@E6_OWNER_CONTROL_STATE_PATH@@": binding.owner_state_path,
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def _render_candidate(text: str) -> str:
    return _render_profile(text, "CANDIDATE_CANARY")


def _fixture_identity() -> tuple[str, str]:
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name, grp.getgrgid(os.getgid()).gr_name


def _write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def _fixture_authority(
    tmp_path: Path, deployment_profile: str = "CANDIDATE_CANARY"
) -> dict[str, str]:
    if deployment_profile == "CANDIDATE_CANARY":
        identity = f"ai-crypto-signal-agent-e6-candidate-{COMMIT}"
        state = tmp_path / "state" / identity
        publication = state / "publication-evidence"
        operational = state / "operational-artifacts"
        control = tmp_path / "control" / COMMIT
        configuration = tmp_path / "config" / COMMIT
    else:
        assert deployment_profile == "PRODUCTION"
        identity = "ai-crypto-signal-agent-e6-production"
        state = tmp_path / "state" / "phase09r1"
        publication = state / "production-signals"
        operational = tmp_path / "state" / "operational-artifacts"
        control = tmp_path / "control" / "production"
        configuration = tmp_path / "config" / "production"
    owner = state / "owner-blueprint"
    runtime = tmp_path / "run" / identity
    cache = tmp_path / "cache" / identity
    return {
        "service_unit": f"{identity}.service",
        "timer_unit": f"{identity}.timer",
        "state_root": str(state),
        "owner_state_root": str(owner),
        "ledger_root": str(owner),
        "active_ledger_path": str(owner / "active-signal-ledger-v2.json"),
        "owner_state_path": str(
            owner / "telegram-owner-control-state-v1.json"
        ),
        "publication_root": str(publication),
        "operational_artifact_root": str(operational),
        "runtime_root": str(runtime),
        "runtime_lock": str(runtime / "e6-operational.lock"),
        "cache_root": str(cache),
        "control_root": str(control),
        "install_pointer": str(control / "installed-release.path"),
        "rollback_pointer": str(control / "rollback-release.path"),
        "accepted_marker": str(control / "accepted-release.marker"),
        "kill_switch": str(control / "kill-switch.active"),
        "configuration_root": str(configuration),
        "activation_configuration_path": str(configuration / "activation-v1.env"),
        "credential_metadata_path": str(configuration / "credentials.metadata"),
    }


def _activation_mapping(
    authority: dict[str, str],
    *,
    release_root: Path,
    deployment_profile: str = "CANDIDATE_CANARY",
) -> dict[str, str]:
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
        "E6_DEPLOYMENT_BINDING_VERSION": E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
        "E6_DEPLOYMENT_PROFILE": deployment_profile,
        "E6_RELEASE_COMMIT": COMMIT,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": TRUSTED,
        "E6_RELEASE_ROOT": str(release_root),
        "E6_SERVICE_UNIT": authority["service_unit"],
        "E6_TIMER_UNIT": authority["timer_unit"],
        "E6_STATE_ROOT": authority["state_root"],
        "E6_OWNER_STATE_ROOT": authority["owner_state_root"],
        "E6_LEDGER_ROOT": authority["ledger_root"],
        "E6_ACTIVE_SIGNAL_LEDGER_PATH": authority["active_ledger_path"],
        "E6_OWNER_CONTROL_STATE_PATH": authority["owner_state_path"],
        "E6_PUBLICATION_ROOT": authority["publication_root"],
        "E6_OPERATIONAL_ARTIFACT_ROOT": authority["operational_artifact_root"],
        "E6_RUNTIME_ROOT": authority["runtime_root"],
        "E6_RUNTIME_LOCK_PATH": authority["runtime_lock"],
        "E6_CACHE_ROOT": authority["cache_root"],
        "E6_LOG_POLICY": "NONE_JOURNALD_ONLY",
        "E6_CONTROL_ROOT": authority["control_root"],
        "E6_RELEASE_REFERENCE_PATH": authority["install_pointer"],
        "E6_ROLLBACK_REFERENCE_PATH": authority["rollback_pointer"],
        "E6_ACCEPTED_RELEASE_MARKER_PATH": authority["accepted_marker"],
        "E6_KILL_SWITCH_PATH": authority["kill_switch"],
        "E6_CONFIGURATION_ROOT": authority["configuration_root"],
        "E6_CREDENTIAL_METADATA_PATH": authority["credential_metadata_path"],
        "E6_ACTIVATION_CONFIGURATION_PATH": authority[
            "activation_configuration_path"
        ],
        "E6_SERVICE_USER": _fixture_identity()[0],
        "E6_SERVICE_GROUP": _fixture_identity()[1],
        "E6_PROVIDER_BINDING_VERSION": E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
        "E6_PROVIDER_BINDING_SHA256": E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
        "E6_RUNTIME_ENABLED": "true",
        "E6_PROVIDER_ENABLED": "true",
        "E6_ACTIVATION_GATE": "true",
        "E6_WORKLOAD_GATE": "true",
        "E6_CREDENTIAL_GATE": "true",
        "E6_NETWORK_GATE": "true",
        "E6_PUBLICATION_GATE": "true",
        "E6_TELEGRAM_PUBLICATION_GATE": "true",
        "E6_AUTOMATIC_RETRY_COUNT": "0",
        "E6_PROVIDER_SUBSTITUTION_ENABLED": "false",
        "E6_PROMPT_REPAIR_ENABLED": "false",
        "E6_STALE_REVIEW_REUSE_ENABLED": "false",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED": "false",
    }
    assert tuple(values) == _EXPECTED_KEYS
    return values


def _configuration_text(values: dict[str, str]) -> str:
    return "".join(f"{key}={values[key]}\n" for key in _EXPECTED_KEYS)


def _release_manifest(release: Path) -> None:
    _write(
        release / ".e6-release-manifest",
        f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\n"
        f"TRUSTED_CHECKPOINT_COMMIT={TRUSTED}\n",
        0o444,
    )
    included = [
        path
        for path in sorted(release.rglob("*"))
        if path.is_file() and path.name != ".e6-sha256-manifest"
    ]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(release).as_posix()}\n"
        for path in included
    ]
    _write(release / ".e6-sha256-manifest", "".join(lines), 0o444)
    release.chmod(0o555)


def _replace_fixture_authority(
    source: str, *, authority: dict[str, str], tmp_path: Path
) -> str:
    user, group = _fixture_identity()
    replacements = {
        '@@TRUSTED_CHECKPOINT_COMMIT@@': TRUSTED,
        'readonly SERVICE_USER="ai-crypto-signal-agent"': f'readonly SERVICE_USER="{user}"',
        'readonly SERVICE_GROUP="ai-crypto-signal-agent"': f'readonly SERVICE_GROUP="{group}"',
        'readonly ROOT_USER="root"': f'readonly ROOT_USER="{user}"',
        'readonly ROOT_GROUP="root"': f'readonly ROOT_GROUP="{group}"',
        'state_root="/var/lib/$identity"': f'state_root="{tmp_path}/state/$identity"',
        'runtime_root="/run/$identity"': f'runtime_root="{authority["runtime_root"]}"',
        'cache_root="/var/cache/$identity"': f'cache_root="{authority["cache_root"]}"',
        'control_root="/var/lib/ai-crypto-signal-agent-e6-installations/$source_commit"': f'control_root="{tmp_path}/control/$source_commit"',
        'control_root="/var/lib/ai-crypto-signal-agent-e6-installations/$release_commit"': f'control_root="{tmp_path}/control/$release_commit"',
        'configuration_root="/etc/ai-crypto-signal-agent/e6-candidates/$source_commit"': f'configuration_root="{tmp_path}/config/$source_commit"',
        'configuration_root="/etc/ai-crypto-signal-agent/e6-candidates/$release_commit"': f'configuration_root="{tmp_path}/config/$release_commit"',
        'state_root="/var/lib/ai-crypto-signal-agent/phase09r1"': f'state_root="{authority["state_root"]}"',
        'operational_root="/var/lib/ai-crypto-signal-agent/operational-artifacts"': f'operational_root="{authority["operational_artifact_root"]}"',
        'control_root="/var/lib/ai-crypto-signal-agent-e6-production-control"': f'control_root="{authority["control_root"]}"',
        'configuration_root="/etc/ai-crypto-signal-agent/e6-production"': f'configuration_root="{authority["configuration_root"]}"',
        '"root:root:400"': f'"{user}:{group}:400"',
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source


def _run_once_fixture(tmp_path: Path) -> dict[str, object]:
    authority = _fixture_authority(tmp_path)
    release = tmp_path / "releases" / COMMIT
    script_path = (
        release
        / "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once"
    )
    invoked = tmp_path / "python-invoked"
    python_stub = tmp_path / "python-stub"
    _write(
        python_stub,
        '#!/usr/bin/env bash\nprintf "%s\\n" "$*" > "$TEST_INVOKED"\n',
        0o755,
    )
    source = _replace_fixture_authority(
        _text(BIN / "ai-crypto-signal-agent-e6-run-once"),
        authority=authority,
        tmp_path=tmp_path,
    ).replace(
        'readonly PYTHON_BIN="/opt/ai-crypto-signal-agent-phase09r1/.venv/bin/python"',
        f'readonly PYTHON_BIN="{python_stub}"',
    )
    _write(script_path, source, 0o755)
    _write(release / "TRUSTED_E6_CHECKPOINT_COMMIT", f"{TRUSTED}\n", 0o444)

    for key, mode in (
        ("state_root", 0o750),
        ("owner_state_root", 0o700),
        ("publication_root", 0o700),
        ("operational_artifact_root", 0o700),
        ("runtime_root", 0o750),
        ("cache_root", 0o700),
        ("control_root", 0o750),
        ("configuration_root", 0o750),
    ):
        path = Path(authority[key])
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)
    _write(Path(authority["install_pointer"]), f"{release}\n", 0o440)
    _write(
        Path(authority["accepted_marker"]),
        "host-marker-content-is-never-runtime-authority\n",
        0o400,
    )
    _write(Path(authority["credential_metadata_path"]), "metadata-only\n", 0o640)
    _write(Path(authority["owner_state_path"]), "{}\n", 0o600)
    _write(Path(authority["active_ledger_path"]), "{}\n", 0o600)
    configuration = _activation_mapping(authority, release_root=release)
    _write(
        Path(authority["activation_configuration_path"]),
        _configuration_text(configuration),
        0o640,
    )
    _release_manifest(release)

    credentials_directory = tmp_path / "systemd-credentials"
    credentials_directory.mkdir(mode=0o700)
    accepted_release_credential = (
        credentials_directory / "accepted_e6_release_commit"
    )
    _write(accepted_release_credential, f"{COMMIT}\n", 0o400)
    environment = dict(os.environ)
    environment.update(
        {
            "E6_ACTIVATION_CONFIGURATION_PATH": authority[
                "activation_configuration_path"
            ],
            "ACTIVE_SIGNAL_LEDGER_PATH": authority["active_ledger_path"],
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": authority["owner_state_path"],
            "CREDENTIALS_DIRECTORY": str(credentials_directory),
            "TEST_INVOKED": str(invoked),
        }
    )
    return {
        "authority": authority,
        "release": release,
        "script_path": script_path,
        "invoked": invoked,
        "credentials_directory": credentials_directory,
        "accepted_release_credential": accepted_release_credential,
        "environment": environment,
    }


def _health_fixture(
    tmp_path: Path,
    *,
    deployment_profile: str,
    state_overrides: dict[str, tuple[str, str, str]] | None = None,
    activation_profile_override: str | None = None,
    service_unit_matches: bool = True,
    state_schema_valid: bool = True,
    runtime_lock_mode: int | None = None,
) -> dict[str, object]:
    authority = _fixture_authority(tmp_path, deployment_profile)
    release = tmp_path / "releases" / COMMIT
    units = tmp_path / "units"
    telegram_environment = tmp_path / "telegram.env"
    provider_environment = tmp_path / "provider.env"
    source = _replace_fixture_authority(
        _text(BIN / "ai-crypto-signal-agent-e6-health"),
        authority=authority,
        tmp_path=tmp_path,
    )
    source = source.replace(
        'readonly TELEGRAM_ENVIRONMENT="/etc/ai-crypto-signal-agent/phase09r1.env"',
        f'readonly TELEGRAM_ENVIRONMENT="{telegram_environment}"',
    ).replace(
        'readonly PROVIDER_ENVIRONMENT="/etc/ai-crypto-signal-agent/deepseek.env"',
        f'readonly PROVIDER_ENVIRONMENT="{provider_environment}"',
    ).replace(
        'service_path="/etc/systemd/system/$service_unit"',
        f'service_path="{units}/$service_unit"',
    ).replace(
        'timer_path="/etc/systemd/system/$timer_unit"',
        f'timer_path="{units}/$timer_unit"',
    ).replace(
        '"/opt/ai-crypto-signal-agent-releases/$release_commit"',
        f'"{tmp_path}/releases/$release_commit"',
    )
    health = tmp_path / "health"
    _write(health, source, 0o755)

    for key, mode in (
        ("state_root", 0o750),
        ("owner_state_root", 0o700),
        ("publication_root", 0o700),
        ("operational_artifact_root", 0o700),
        ("cache_root", 0o700),
        ("control_root", 0o750),
        ("configuration_root", 0o750),
    ):
        path = Path(authority[key])
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(mode)

    owner_document = {
        "schema_name": (
            "telegram-owner-control-state"
            if state_schema_valid
            else "invalid-owner-state"
        ),
        "schema_version": 1,
        "revision": 0,
        "updated_at": "2026-08-03T00:00:00Z",
        "last_update_id": -1,
        "processed_updates": {},
        "processed_commands": {},
        "signal_message_bindings": {},
    }
    ledger_document = {
        "schema_name": "active-signal-ledger",
        "schema_version": 2,
        "ledger_revision": 0,
        "created_at": "2026-08-03T00:00:00Z",
        "updated_at": "2026-08-03T00:00:00Z",
        "capacity_policy": {},
        "signals": {},
        "transitions": {},
        "publication_transactions": {},
    }
    _write(
        Path(authority["owner_state_path"]),
        json.dumps(owner_document, separators=(",", ":")) + "\n",
        0o600,
    )
    _write(
        Path(authority["active_ledger_path"]),
        json.dumps(ledger_document, separators=(",", ":")) + "\n",
        0o600,
    )
    _write(Path(authority["install_pointer"]), f"{release}\n", 0o440)
    _write(Path(authority["accepted_marker"]), f"{COMMIT}\n", 0o400)
    _write(Path(authority["credential_metadata_path"]), "metadata-only\n", 0o640)
    _write(telegram_environment, "not-read\n", 0o600)
    _write(provider_environment, "not-read\n", 0o600)
    if runtime_lock_mode is not None:
        _write(Path(authority["runtime_lock"]), "not-locked\n", runtime_lock_mode)
    configuration = _activation_mapping(
        authority,
        release_root=release,
        deployment_profile=deployment_profile,
    )
    if activation_profile_override is not None:
        configuration["E6_DEPLOYMENT_PROFILE"] = activation_profile_override
    _write(
        Path(authority["activation_configuration_path"]),
        _configuration_text(configuration),
        0o640,
    )

    if deployment_profile == "CANDIDATE_CANARY":
        service_template = "ai-crypto-signal-agent-e6.service.in"
        timer_template = "ai-crypto-signal-agent-e6.timer"
    else:
        service_template = "ai-crypto-signal-agent-e6-production.service.in"
        timer_template = "ai-crypto-signal-agent-e6-production.timer"
    rendered_service = _render_profile(
        _text(SYSTEMD / service_template), deployment_profile
    )
    rendered_timer = _render_profile(
        _text(SYSTEMD / timer_template), deployment_profile
    )
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile=deployment_profile, release_commit=COMMIT
    )
    rendered_service = rendered_service.replace(
        binding.accepted_marker, authority["accepted_marker"]
    )
    rendered = release / ".e6-rendered"
    _write(rendered / authority["service_unit"], rendered_service, 0o444)
    _write(rendered / authority["timer_unit"], rendered_timer, 0o444)
    _write(
        release
        / "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once",
        _text(BIN / "ai-crypto-signal-agent-e6-run-once"),
        0o555,
    )
    _release_manifest(release)
    installed_service = rendered_service
    if not service_unit_matches:
        installed_service += "# identity-mismatch\n"
    _write(units / authority["service_unit"], installed_service, 0o644)
    _write(units / authority["timer_unit"], rendered_timer, 0o644)

    candidate_timer_1 = (
        "ai-crypto-signal-agent-e6-candidate-"
        f"{'d' * 40}.timer"
    )
    candidate_timer_2 = (
        "ai-crypto-signal-agent-e6-candidate-"
        f"{'e' * 40}.timer"
    )
    state_keys = {
        "profile_service": authority["service_unit"],
        "profile_timer": authority["timer_unit"],
        "legacy_service": "ai-crypto-signal-agent.service",
        "legacy_timer": "ai-crypto-signal-agent.timer",
        "old_e6_timer": "ai-crypto-signal-agent-e6.timer",
        "candidate_timer_1": candidate_timer_1,
        "candidate_timer_2": candidate_timer_2,
    }
    if deployment_profile == "CANDIDATE_CANARY":
        states = {
            "profile_service": ("inactive", "static", "dead"),
            "profile_timer": ("inactive", "disabled", "dead"),
            "legacy_service": ("inactive", "static", "dead"),
            "legacy_timer": ("active", "enabled", "waiting"),
            "old_e6_timer": ("inactive", "disabled", "dead"),
            "candidate_timer_1": ("inactive", "disabled", "dead"),
            "candidate_timer_2": ("inactive", "disabled", "dead"),
        }
    else:
        states = {
            "profile_service": ("inactive", "static", "dead"),
            "profile_timer": ("active", "enabled", "waiting"),
            "legacy_service": ("inactive", "static", "dead"),
            "legacy_timer": ("inactive", "disabled", "dead"),
            "old_e6_timer": ("inactive", "disabled", "dead"),
            "candidate_timer_1": ("inactive", "disabled", "dead"),
            "candidate_timer_2": ("inactive", "disabled", "dead"),
        }
    states.update(state_overrides or {})

    mock_bin = tmp_path / "mock-bin"
    systemctl = mock_bin / "systemctl"
    script_lines = [
        "#!/usr/bin/env bash",
        'if [[ "$1" == list-unit-files ]]; then',
        f"  echo '{candidate_timer_1} disabled enabled'",
        f"  echo '{candidate_timer_2} disabled enabled'",
        "  exit 0",
        "fi",
        'case "$1:$2" in',
    ]
    for key, unit in state_keys.items():
        active, enabled, substate = states[key]
        script_lines.extend(
            (
                f"is-active:{unit}) echo {active} ;;",
                f"is-enabled:{unit}) echo {enabled} ;;",
                f"show:{unit}) echo {substate} ;;",
            )
        )
    script_lines.extend(("*) exit 1 ;;", "esac"))
    _write(systemctl, "\n".join(script_lines) + "\n", 0o755)

    state_preimage = {
        path: path.read_bytes()
        for path in sorted(Path(authority["state_root"]).rglob("*"))
        if path.is_file()
    }
    environment = dict(os.environ)
    environment["PATH"] = f"{mock_bin}:{environment['PATH']}"
    result = subprocess.run(
        [
            str(health),
            "--deployment-profile",
            deployment_profile,
            "--release-commit",
            COMMIT,
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "authority": authority,
        "result": result,
        "state_preimage": state_preimage,
    }


def test_exact_package_inventory_manifest_and_modes() -> None:
    actual = {
        path.relative_to(PACKAGE).as_posix(): f"0{path.stat().st_mode & 0o777:o}"
        for path in PACKAGE.rglob("*")
        if path.is_file()
    }
    assert actual == PAYLOAD
    manifest_entries = {}
    for line in _text(PACKAGE / "deployment-package-manifest.txt").splitlines():
        if line.startswith("PAYLOAD="):
            path, kind, mode = line.removeprefix("PAYLOAD=").split("|")
            assert kind == "regular"
            manifest_entries[path] = mode
    assert manifest_entries == PAYLOAD
    assert list(manifest_entries) == sorted(manifest_entries)


def test_package_files_are_lf_only_final_lf_and_nonsecret() -> None:
    for relative in PAYLOAD:
        data = (PACKAGE / relative).read_bytes()
        assert data.endswith(b"\n")
        assert b"\r" not in data
    combined = "\n".join(_text(PACKAGE / relative) for relative in PAYLOAD)
    for marker in (
        "DEEPSEEK_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "TELEGRAM_BOT_TOKEN=",
        "Authorization: Bearer",
        "BEGIN OPENSSH PRIVATE KEY",
        "46.250.228.53",
        COMMIT,
    ):
        assert marker not in combined


def test_shell_syntax_and_zero_retry_no_remote_command_contract() -> None:
    for name in (
        "ai-crypto-signal-agent-e6-run-once",
        "ai-crypto-signal-agent-e6-health",
        "ai-crypto-signal-agent-e6-rollback",
    ):
        result = subprocess.run(
            ["bash", "-n", str(BIN / name)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    combined = "\n".join(_text(path) for path in BIN.iterdir())
    assert "AUTOMATIC_RETRY_COUNT=0" in combined
    assert not re.search(r"\b(ssh|scp|sftp|rsync|curl|wget|apt|pip|npm)\b", combined)
    assert not re.search(r"systemctl\s+(start|restart|enable|disable|preset)", combined)


def test_candidate_service_rendering_is_exact_and_has_no_shared_writable_path() -> None:
    template = _text(SYSTEMD / "ai-crypto-signal-agent-e6.service.in")
    rendered = _render_candidate(template)
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile="CANDIDATE_CANARY", release_commit=COMMIT
    )
    assert "@@" not in rendered
    assert _directives(rendered, "WorkingDirectory") == [binding.state_root]
    assert _directives(rendered, "RuntimeDirectory") == [
        f"ai-crypto-signal-agent-e6-candidate-{COMMIT}"
    ]
    assert _directives(rendered, "CacheDirectory") == [
        f"ai-crypto-signal-agent-e6-candidate-{COMMIT}"
    ]
    assert _directives(rendered, "ReadWritePaths") == [
        " ".join(
            (
                binding.state_root,
                binding.operational_artifact_root,
                binding.runtime_root,
                binding.cache_root,
            )
        )
    ]
    assert _directives(rendered, "EnvironmentFile") == [
        binding.activation_configuration_path,
        "/etc/ai-crypto-signal-agent/phase09r1.env",
        "/etc/ai-crypto-signal-agent/deepseek.env",
    ]
    assert _directives(rendered, "User") == ["ai-crypto-signal-agent"]
    assert _directives(rendered, "Group") == ["ai-crypto-signal-agent"]
    assert _directives(rendered, "SupplementaryGroups") == []
    assert _directives(rendered, "LoadCredential") == [
        f"accepted_e6_release_commit:{binding.accepted_marker}"
    ]
    assert "accepted_e6_release_commit=" not in rendered
    assert _directives(rendered, "ExecStart") == [
        f"{binding.release_root}/deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once"
    ]
    for forbidden in (
        "/var/lib/ai-crypto-signal-agent/phase09r1",
        "/var/lib/ai-crypto-signal-agent/operational-artifacts",
        "/run/ai-crypto-signal-agent ",
    ):
        assert forbidden not in _directives(rendered, "ReadWritePaths")[0]
    assert "[Install]" not in template
    for relation in ("Requires=", "PartOf=", "Alias=", "Also="):
        assert relation not in template


def test_candidate_timer_targets_only_matching_versioned_service() -> None:
    template = _text(SYSTEMD / "ai-crypto-signal-agent-e6.timer")
    rendered = _render_candidate(template)
    assert _directives(rendered, "Unit") == [
        f"ai-crypto-signal-agent-e6-candidate-{COMMIT}.service"
    ]
    assert _directives(rendered, "OnCalendar") == ["*-*-* *:*:00 UTC"]
    assert _directives(rendered, "AccuracySec") == ["1s"]
    assert _directives(rendered, "Persistent") == ["false"]
    assert "Unit=ai-crypto-signal-agent-e6.service" not in rendered
    for key in ("OnActiveSec", "OnUnitActiveSec", "RandomizedDelaySec"):
        assert _directives(rendered, key) == []


def test_stable_production_templates_rebind_state_without_candidate_namespace() -> None:
    service = _text(
        SYSTEMD / "ai-crypto-signal-agent-e6-production.service.in"
    )
    timer = _text(SYSTEMD / "ai-crypto-signal-agent-e6-production.timer")
    assert _directives(service, "WorkingDirectory") == [
        "/var/lib/ai-crypto-signal-agent/phase09r1"
    ]
    assert _directives(service, "RuntimeDirectory") == [
        "ai-crypto-signal-agent-e6-production"
    ]
    assert _directives(service, "CacheDirectory") == [
        "ai-crypto-signal-agent-e6-production"
    ]
    assert _directives(service, "User") == ["ai-crypto-signal-agent"]
    assert _directives(service, "Group") == ["ai-crypto-signal-agent"]
    assert _directives(service, "SupplementaryGroups") == []
    assert _directives(service, "LoadCredential") == [
        "accepted_e6_release_commit:"
        "/var/lib/ai-crypto-signal-agent-e6-production-control/"
        "accepted-release.marker"
    ]
    assert "accepted_e6_release_commit=" not in service
    assert "candidate-" not in service.lower()
    assert "[Install]" not in service
    assert _directives(timer, "Unit") == [
        "ai-crypto-signal-agent-e6-production.service"
    ]
    assert _directives(timer, "OnCalendar") == ["*-*-* *:*:00 UTC"]
    assert _directives(timer, "AccuracySec") == ["1s"]
    assert _directives(timer, "Persistent") == ["false"]
    assert "ai-crypto-signal-agent-e6.service" not in service + timer


def test_run_once_rederives_profile_authority_and_uses_only_profile_lock() -> None:
    script = _text(BIN / "ai-crypto-signal-agent-e6-run-once")
    for marker in (
        "case \"$deployment_profile\" in",
        "CANDIDATE_CANARY)",
        "PRODUCTION)",
        'runtime_lock="$runtime_root/e6-operational.lock"',
        'exec 9>"$runtime_lock"',
        "E6_DEPLOYMENT_BINDING_VERSION",
        "E6_ACTIVE_SIGNAL_LEDGER_PATH",
        "E6_OWNER_CONTROL_STATE_PATH",
        "E6_RUNTIME_LOCK_PATH",
        'credentials_directory="${CREDENTIALS_DIRECTORY:-}"',
        'accepted_release_credential="${credentials_directory}/accepted_e6_release_commit"',
        'mapfile -t accepted_release_credential_lines < "$accepted_release_credential"',
    ):
        assert marker in script
    assert script.count(
        'mapfile -t accepted_release_credential_lines < "$accepted_release_credential"'
    ) == 1
    assert '$(cat "$accepted_marker")' not in script
    assert '< "$accepted_marker"' not in script
    assert '"root:root:400"' in script
    assert 'readonly LOCK_PATH="/run/ai-crypto-signal-agent/e6-operational.lock"' not in script
    assert "/var/lib/ai-crypto-signal-agent/e6-installed-release.path" not in script
    assert "while true" not in script
    assert "retry" not in script.lower() or "AUTOMATIC_RETRY_COUNT" in script


def test_candidate_run_once_fixture_uses_only_bound_paths_and_one_python_call(
    tmp_path: Path,
) -> None:
    fixture = _run_once_fixture(tmp_path)
    authority = fixture["authority"]
    script_path = fixture["script_path"]
    invoked = fixture["invoked"]
    environment = fixture["environment"]
    user, group = _fixture_identity()
    result = subprocess.run(
        [str(script_path)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert invoked.read_text(encoding="utf-8").strip() == (
        "-m engine.run_production_signal_v1"
    )
    assert not Path(authority["runtime_lock"]).exists()
    assert user and group

    invoked.unlink()
    _write(Path(authority["kill_switch"]), "blocked\n", 0o400)
    blocked = subprocess.run(
        [str(script_path)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked.returncode == 75
    assert "KILL_SWITCH_ACTIVE" in blocked.stderr
    assert not invoked.exists()


@pytest.mark.parametrize(
    "failure_case",
    (
        "credentials_directory_absent",
        "credentials_directory_relative",
        "credential_absent",
        "credential_symlink",
        "credential_unreadable",
        "credential_blank",
        "credential_multiple_lines",
        "credential_uppercase",
        "credential_non_hex",
        "credential_commit_mismatch",
    ),
)
def test_run_once_credential_copy_failures_are_closed_and_sanitized(
    tmp_path: Path, failure_case: str
) -> None:
    fixture = _run_once_fixture(tmp_path)
    script_path = fixture["script_path"]
    invoked = fixture["invoked"]
    credential = fixture["accepted_release_credential"]
    environment = fixture["environment"].copy()
    sensitive_value = ""

    if failure_case == "credentials_directory_absent":
        environment.pop("CREDENTIALS_DIRECTORY")
        expected_code = "CREDENTIALS_DIRECTORY_INVALID"
    elif failure_case == "credentials_directory_relative":
        environment["CREDENTIALS_DIRECTORY"] = "relative-credentials"
        expected_code = "CREDENTIALS_DIRECTORY_INVALID"
    elif failure_case == "credential_absent":
        credential.unlink()
        expected_code = "ACCEPTED_RELEASE_CREDENTIAL_INVALID"
    elif failure_case == "credential_symlink":
        credential.unlink()
        target = tmp_path / "credential-target"
        _write(target, f"{COMMIT}\n", 0o400)
        credential.symlink_to(target)
        expected_code = "ACCEPTED_RELEASE_CREDENTIAL_INVALID"
    elif failure_case == "credential_unreadable":
        credential.chmod(0o000)
        expected_code = "ACCEPTED_RELEASE_CREDENTIAL_INVALID"
    else:
        values = {
            "credential_blank": "\n",
            "credential_multiple_lines": f"{COMMIT}\n{COMMIT}\n",
            "credential_uppercase": f"{COMMIT.upper()}\n",
            "credential_non_hex": f"{'g' * 40}\n",
            "credential_commit_mismatch": f"{'d' * 40}\n",
        }
        sensitive_value = values[failure_case].strip()
        credential.unlink()
        _write(credential, values[failure_case], 0o400)
        expected_code = "ACCEPTED_RELEASE_CREDENTIAL_INVALID"

    result = subprocess.run(
        [str(script_path)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 78
    assert result.stdout == ""
    assert result.stderr.strip() == f"E6_LAUNCH_BLOCKED={expected_code}"
    assert not invoked.exists()
    if sensitive_value:
        assert sensitive_value not in result.stdout + result.stderr


def test_health_is_profile_bound_read_only_and_cannot_invoke_effect_paths() -> None:
    health = _text(BIN / "ai-crypto-signal-agent-e6-health")
    for marker in (
        "--deployment-profile",
        "--release-commit",
        "CANDIDATE_STATE_VALID_EMPTY",
        'grep -q \'"signals":{}\' "$active_ledger"',
        'grep -q \'"signal_message_bindings":{}\' "$owner_state"',
        "PROFILE_UNITS_DISABLED_INACTIVE",
        "PRODUCTION_STATE_AUTHORITY_VALID",
        "PRODUCTION_TIMER_ACTIVE",
        "CANDIDATE_TIMER_INACTIVITY",
        "OLD_E6_TIMER_INACTIVITY",
        "AUTHORITATIVE_SCHEDULER_EXACTLY_ONE",
        "OPERATIONAL_LOCK_ABSENT_OR_UNHELD",
        "HEALTH_STATUS=PASS_DISABLED_NOT_ACTIVATED",
        "HEALTH_STATUS=PASS_ACTIVE_PRODUCTION",
        "PRODUCTION_HEALTH_STATUS=PASS_ACTIVE_PRODUCTION",
        "LOADCREDENTIAL_ROW_PARITY",
        "SYSTEMD_CREDENTIAL_RUNTIME_SOURCE",
        "DIRECT_HOST_MARKER_RUNTIME_READ_COUNT=0",
        "SYSTEMD_CREDENTIAL_RUNTIME_READ_COUNT=1",
        "SERVICE_CONTROL_COMMAND_COUNT=0",
        "STATE_MUTATION_COUNT=0",
    ):
        assert marker in health
    for command in (
        "engine.run_production_signal_v1",
        "run_e6_service_cycle_v1",
        "mark_entry_active",
        "reserve_slot",
        "pair_lock",
        "create_order",
        "curl ",
    ):
        assert command not in health
    assert 'exec "$launcher_path"' not in health
    assert 'bash "$launcher_path"' not in health
    assert re.search(r"\b(touch|mkdir|mktemp|install|chmod|chown|mv|unlink)\b", health) is None
    assert re.search(
        r"systemctl\s+(start|stop|restart|enable|disable|preset)", health
    ) is None


def test_candidate_health_fixture_passes_disabled_inactive_without_mutation(
    tmp_path: Path,
) -> None:
    fixture = _health_fixture(
        tmp_path, deployment_profile="CANDIDATE_CANARY"
    )
    result = fixture["result"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HEALTH_STATUS=PASS_DISABLED_NOT_ACTIVATED" in result.stdout
    assert "AUTHORITATIVE_SCHEDULER_COUNT=1" in result.stdout
    assert "AUTHORITATIVE_SCHEDULER=ai-crypto-signal-agent.timer" in result.stdout
    assert "SERVICE_CYCLE_INVOCATION_COUNT=0" in result.stdout
    assert "AUTOMATIC_RETRY_COUNT=0" in result.stdout
    assert all(
        path.read_bytes() == content
        for path, content in fixture["state_preimage"].items()
    )


@pytest.mark.parametrize(
    ("state_overrides", "expected_reason"),
    (
        (
            {"profile_timer": ("active", "disabled", "running")},
            "PROFILE_UNIT_AUTHORITY_INVALID",
        ),
        (
            {"legacy_timer": ("inactive", "disabled", "dead")},
            "LEGACY_PRODUCTION_AUTHORITY_INVALID",
        ),
        (
            {"legacy_service": ("active", "static", "running")},
            "LEGACY_SERVICE_AUTHORITY_INVALID",
        ),
    ),
)
def test_candidate_health_rejects_scheduler_authority_drift(
    tmp_path: Path,
    state_overrides: dict[str, tuple[str, str, str]],
    expected_reason: str,
) -> None:
    result = _health_fixture(
        tmp_path,
        deployment_profile="CANDIDATE_CANARY",
        state_overrides=state_overrides,
    )["result"]
    assert result.returncode == 1
    assert f"HEALTH_REASON={expected_reason}" in result.stdout
    assert "HEALTH_STATUS=NOT_READY" in result.stdout


def test_production_health_fixture_passes_active_single_scheduler_without_mutation(
    tmp_path: Path,
) -> None:
    fixture = _health_fixture(tmp_path, deployment_profile="PRODUCTION")
    result = fixture["result"]
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "PROFILE_UNIT_AUTHORITY=ACTIVE_PRODUCTION_VALID",
        "LEGACY_PRODUCTION_AUTHORITY=TRANSFERRED_TO_E6_PRODUCTION",
        "HEALTH_STATUS=PASS_ACTIVE_PRODUCTION",
        "PRODUCTION_HEALTH_STATUS=PASS_ACTIVE_PRODUCTION",
        "AUTHORITATIVE_SCHEDULER_COUNT=1",
        "AUTHORITATIVE_SCHEDULER=ai-crypto-signal-agent-e6-production.timer",
        "LOADCREDENTIAL_ROW_PARITY=PASS",
        "SYSTEMD_CREDENTIAL_RUNTIME_SOURCE=YES",
        "DIRECT_HOST_MARKER_RUNTIME_READ_COUNT=0",
        "SYSTEMD_CREDENTIAL_RUNTIME_READ_COUNT=1",
        "SERVICE_CONTROL_COMMAND_COUNT=0",
        "SERVICE_CYCLE_INVOCATION_COUNT=0",
        "STATE_MUTATION_COUNT=0",
    ):
        assert marker in result.stdout
    assert all(
        path.read_bytes() == content
        for path, content in fixture["state_preimage"].items()
    )


@pytest.mark.parametrize(
    ("state_overrides", "expected_reason"),
    (
        (
            {"profile_timer": ("active", "disabled", "waiting")},
            "PRODUCTION_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"profile_timer": ("inactive", "enabled", "waiting")},
            "PRODUCTION_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"profile_timer": ("active", "enabled", "running")},
            "PRODUCTION_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"legacy_timer": ("active", "disabled", "waiting")},
            "LEGACY_TIMER_AUTHORITY_NOT_TRANSFERRED",
        ),
        (
            {"legacy_timer": ("active", "enabled", "waiting")},
            "SCHEDULER_AUTHORITY_COUNT_MULTIPLE",
        ),
        (
            {"legacy_service": ("active", "static", "running")},
            "LEGACY_SERVICE_AUTHORITY_INVALID",
        ),
        (
            {"profile_timer": ("inactive", "disabled", "dead")},
            "SCHEDULER_AUTHORITY_COUNT_ZERO",
        ),
        (
            {"candidate_timer_1": ("active", "disabled", "running")},
            "CANDIDATE_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"candidate_timer_1": ("inactive", "enabled", "waiting")},
            "CANDIDATE_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"old_e6_timer": ("active", "disabled", "running")},
            "OLD_E6_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"old_e6_timer": ("inactive", "enabled", "waiting")},
            "OLD_E6_TIMER_AUTHORITY_INVALID",
        ),
        (
            {"profile_service": ("failed", "static", "failed")},
            "PRODUCTION_SERVICE_AUTHORITY_INVALID",
        ),
    ),
)
def test_production_health_rejects_scheduler_authority_drift(
    tmp_path: Path,
    state_overrides: dict[str, tuple[str, str, str]],
    expected_reason: str,
) -> None:
    result = _health_fixture(
        tmp_path,
        deployment_profile="PRODUCTION",
        state_overrides=state_overrides,
    )["result"]
    assert result.returncode == 1
    assert f"HEALTH_REASON={expected_reason}" in result.stdout
    assert "HEALTH_STATUS=NOT_READY" in result.stdout


@pytest.mark.parametrize(
    ("fixture_options", "expected_reason"),
    (
        ({"service_unit_matches": False}, "SERVICE_UNIT_IDENTITY_MISMATCH"),
        (
            {"activation_profile_override": "CANDIDATE_CANARY"},
            "ACTIVATION_BINDING_INVALID",
        ),
    ),
)
def test_production_health_rejects_profile_or_unit_identity_drift(
    tmp_path: Path,
    fixture_options: dict[str, object],
    expected_reason: str,
) -> None:
    result = _health_fixture(
        tmp_path,
        deployment_profile="PRODUCTION",
        **fixture_options,
    )["result"]
    assert result.returncode == 1
    assert f"HEALTH_REASON={expected_reason}" in result.stdout
    assert "HEALTH_STATUS=NOT_READY" in result.stdout


@pytest.mark.parametrize(
    ("fixture_options", "expected_reason"),
    (
        ({"state_schema_valid": False}, "PRODUCTION_STATE_AUTHORITY_INVALID"),
        ({"runtime_lock_mode": 0o644}, "OPERATIONAL_LOCK_HELD_OR_INVALID"),
    ),
)
def test_production_health_rejects_state_or_lock_authority_drift(
    tmp_path: Path,
    fixture_options: dict[str, object],
    expected_reason: str,
) -> None:
    result = _health_fixture(
        tmp_path,
        deployment_profile="PRODUCTION",
        **fixture_options,
    )["result"]
    assert result.returncode == 1
    assert f"HEALTH_REASON={expected_reason}" in result.stdout
    assert "HEALTH_STATUS=NOT_READY" in result.stdout


def test_rollback_is_profile_closed_and_never_touches_state_or_old_e6_pointer() -> None:
    rollback = _text(BIN / "ai-crypto-signal-agent-e6-rollback")
    assert "--deployment-profile" in rollback
    assert "--release-commit" in rollback
    assert 'control_relative="var/lib/ai-crypto-signal-agent-e6-installations/$release_commit"' in rollback
    assert 'control_relative="var/lib/ai-crypto-signal-agent-e6-production-control"' in rollback
    assert "/var/lib/ai-crypto-signal-agent/e6-installed-release.path" not in rollback
    assert "/var/lib/ai-crypto-signal-agent/phase09r1" not in rollback
    assert "STATE_AUTHORITY_RETAINED_IN_PLACE=YES" in rollback
    assert "CANARY_STATE_PROMOTION_COUNT=0" in rollback
    assert not re.search(r"systemctl\s+", rollback)


def test_candidate_rollback_fixture_mutates_only_versioned_control_namespace(
    tmp_path: Path,
) -> None:
    user, group = _fixture_identity()
    source = _replace_fixture_authority(
        _text(BIN / "ai-crypto-signal-agent-e6-rollback"),
        authority=_fixture_authority(tmp_path),
        tmp_path=tmp_path,
    )
    rollback = tmp_path / "rollback"
    _write(rollback, source, 0o755)

    def make_release(commit: str) -> Path:
        release = tmp_path / "releases" / commit
        _write(release / "payload", f"{commit}\n", 0o444)
        _write(
            release / ".e6-release-manifest",
            f"SOURCE_COMMIT={commit}\nSOURCE_TREE={TREE}\n"
            f"TRUSTED_CHECKPOINT_COMMIT={TRUSTED}\n",
            0o444,
        )
        digest = hashlib.sha256((release / "payload").read_bytes()).hexdigest()
        _write(release / ".e6-sha256-manifest", f"{digest}  payload\n", 0o444)
        release.chmod(0o555)
        return release

    current = make_release(COMMIT)
    target = make_release("d" * 40)
    host = tmp_path / "host"
    control = host / "var/lib/ai-crypto-signal-agent-e6-installations" / COMMIT
    control.mkdir(parents=True)
    _write(control / "installed-release.path", f"{current}\n", 0o440)
    legacy_pointer = host / "var/lib/ai-crypto-signal-agent/e6-installed-release.path"
    state_sentinel = host / "var/lib/ai-crypto-signal-agent/phase09r1/sentinel"
    _write(legacy_pointer, "old-e6-evidence\n", 0o440)
    _write(state_sentinel, "production-authority\n", 0o600)

    result = subprocess.run(
        [
            str(rollback),
            "--deployment-profile",
            "CANDIDATE_CANARY",
            "--release-commit",
            COMMIT,
            "--target-release",
            str(target),
            "--destdir",
            str(host),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (control / "installed-release.path").read_text() == f"{target}\n"
    assert (control / "rollback-release.path").read_text() == f"{current}\n"
    assert "STATE_AUTHORITY_RETAINED_IN_PLACE=YES" in (
        control / "rollback-evidence.txt"
    ).read_text()
    assert legacy_pointer.read_text() == "old-e6-evidence\n"
    assert state_sentinel.read_text() == "production-authority\n"
    assert user and group


def test_manifest_and_readme_freeze_two_profile_authority_and_reentry() -> None:
    manifest = _text(PACKAGE / "deployment-package-manifest.txt")
    readme = _text(PACKAGE / "README.md")
    normalized_readme = " ".join(readme.split())
    for marker in (
        "DEPLOYMENT_BINDING_VERSION=e6-deployment-state-binding-v1",
        "DEPLOYMENT_PROFILES=CANDIDATE_CANARY,PRODUCTION",
        "CANDIDATE_STATE_AUTHORITY=empty-nonauthoritative-never-promoted",
        "PRODUCTION_STATE_AUTHORITY=rebound-in-place-under-r44-freeze",
        "OLD_E6_DISPOSITION=preserve",
        "AUTOMATIC_RETRY_COUNT=0",
    ):
        assert marker in manifest
    for marker in (
        "CURRENT_LEGACY",
        "R41_DISABLED_VERSIONED_CANDIDATE",
        "R42_ONE_CANARY",
        "R44_PRODUCTION_PROFILE_CUTOVER",
        "old E6 installation",
        "Candidate state is never imported or promoted",
        "writer freeze",
        "Same-day accepted Claude canary usage requires deterministic reconciliation",
        "No arbitrary environment or path override is supported",
    ):
        assert marker in normalized_readme


def test_no_automatic_rollback_activation_publication_or_trading_authority() -> None:
    combined = "\n".join(_text(PACKAGE / path) for path in PAYLOAD)
    for marker in (
        "systemctl start",
        "systemctl restart",
        "systemctl enable",
        "systemctl preset",
        "mark_entry_active(",
        "reserve_slot(",
        "create_order(",
    ):
        assert marker not in combined
    assert "AUTOMATED_EXCHANGE_TRADING=disabled" in combined


def test_run_once_release_trust_identity_validation(tmp_path: Path) -> None:
    fixture = _run_once_fixture(tmp_path)
    env = fixture["environment"]
    script = str(fixture["script_path"])

    # 1. Accepted case: static checkpoint equals manifest checkpoint, all identities correct
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    assert not res.stderr

    # 2. Rejected case: trusted checkpoint mismatch (modify manifest)
    manifest = Path(fixture["release"]) / ".e6-release-manifest"
    manifest.chmod(0o644)
    manifest.write_text(f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\nTRUSTED_CHECKPOINT_COMMIT=1111111111111111111111111111111111111111\n")
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 78
    assert "E6_LAUNCH_BLOCKED=RELEASE_TRUST_IDENTITY" in res.stderr

    # 3. Rejected case: missing checkpoint field
    manifest.write_text(f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\n")
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 78
    assert "E6_LAUNCH_BLOCKED=RELEASE_TRUST_IDENTITY" in res.stderr

    # 4. Rejected case: malformed checkpoint (length 39)
    manifest.write_text(f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\nTRUSTED_CHECKPOINT_COMMIT={'0'*39}\n")
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 78
    assert "E6_LAUNCH_BLOCKED=RELEASE_TRUST_IDENTITY" in res.stderr

    # 5. Rejected case: uppercase noncanonical hash
    manifest.write_text(f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\nTRUSTED_CHECKPOINT_COMMIT={TRUSTED.upper()}\n")
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 78
    assert "E6_LAUNCH_BLOCKED=RELEASE_TRUST_IDENTITY" in res.stderr

    # 6. Rejected case: literal @@TRUSTED_CHECKPOINT_COMMIT@@ remains in packaged launcher
    manifest.write_text(f"SOURCE_COMMIT={COMMIT}\nSOURCE_TREE={TREE}\nTRUSTED_CHECKPOINT_COMMIT={TRUSTED}\n")
    source = Path(script).read_text().replace(TRUSTED, "@@TRUSTED_CHECKPOINT_COMMIT@@")
    Path(script).write_text(source)
    res = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
    assert res.returncode == 78
    assert "E6_LAUNCH_BLOCKED=RELEASE_TRUST_IDENTITY" in res.stderr
