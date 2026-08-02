from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deploy/e6_operational_v1"
BIN = PACKAGE / "bin"
SYSTEMD = PACKAGE / "systemd"
COMMIT = "a" * 40
TREE = "b" * 40
TRUSTED = "c" * 40
STATIC_ACTIVATION_PATH_BINDING = (
    "E6_ACTIVATION_CONFIGURATION_PATH="
    "/etc/ai-crypto-signal-agent/e6-activation-v1.env"
)
HOST_ACCESS_CONTRACT = {
    "/etc/ai-crypto-signal-agent": "root:ai-crypto-signal-agent:0750",
    "/etc/ai-crypto-signal-agent/e6-activation-v1.env": (
        "ai-crypto-signal-agent:ai-crypto-signal-agent:0640"
    ),
    "/etc/ai-crypto-signal-agent/e6-credentials.metadata": (
        "ai-crypto-signal-agent:ai-crypto-signal-agent:0640"
    ),
    "/etc/ai-crypto-signal-agent/phase09r1.env": "root:root:0600",
    "/etc/ai-crypto-signal-agent/deepseek.env": "root:root:0600",
    "/var/lib/ai-crypto-signal-agent/e6-installed-release.path": (
        "root:ai-crypto-signal-agent:0440"
    ),
    "/var/lib/ai-crypto-signal-agent/e6-accepted-release.marker": "root:root:0400",
}

TEN_PATHS = {
    "engine/e6_activation_configuration_v1.py",
    "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once",
    "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-health",
    "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-rollback",
    "deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.service.in",
    "deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.timer",
    "deploy/e6_operational_v1/README.md",
    "deploy/e6_operational_v1/deployment-package-manifest.txt",
    "tests/test_e6_activation_configuration_v1.py",
    "tests/test_e6_operational_deployment_package_v1.py",
}
PACKAGE_PAYLOAD = {
    "README.md": "0644",
    "bin/ai-crypto-signal-agent-e6-health": "0755",
    "bin/ai-crypto-signal-agent-e6-rollback": "0755",
    "bin/ai-crypto-signal-agent-e6-run-once": "0755",
    "deployment-package-manifest.txt": "0644",
    "systemd/ai-crypto-signal-agent-e6.service.in": "0644",
    "systemd/ai-crypto-signal-agent-e6.timer": "0644",
}
CONFIGURATION_KEYS = (
    "E6_ACTIVATION_SCHEMA_VERSION",
    "E6_RELEASE_COMMIT",
    "E6_RELEASE_TREE",
    "E6_TRUSTED_CHECKPOINT_COMMIT",
    "E6_RELEASE_ROOT",
    "E6_RELEASE_REFERENCE_PATH",
    "E6_CREDENTIAL_METADATA_PATH",
    "E6_OWNER_CONTROL_STATE_PATH",
    "E6_SERVICE_USER",
    "E6_SERVICE_GROUP",
    "E6_RUNTIME_ENABLED",
    "E6_PROVIDER_ENABLED",
    "E6_ACTIVATION_GATE",
    "E6_WORKLOAD_GATE",
    "E6_CREDENTIAL_GATE",
    "E6_NETWORK_GATE",
    "E6_PUBLICATION_GATE",
    "E6_TELEGRAM_PUBLICATION_GATE",
    "E6_AUTOMATIC_RETRY_COUNT",
    "E6_PROVIDER_SUBSTITUTION_ENABLED",
    "E6_PROMPT_REPAIR_ENABLED",
    "E6_STALE_REVIEW_REUSE_ENABLED",
    "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED",
)
ROOT_SAFE_IMMUTABILITY_HELPER = """e6_path_has_no_write_mode_bits() {
    local path="$1"
    local mode

    mode="$(stat -Lc '%a' -- "$path" 2>/dev/null)" || return 1
    [[ "$mode" =~ ^[0-7]{3,4}$ ]] || return 1
    (( (8#$mode & 8#222) == 0 ))
}
"""


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _directives(text: str, key: str) -> list[str]:
    prefix = f"{key}="
    return [line[len(prefix) :] for line in text.splitlines() if line.startswith(prefix)]


def _metadata(path: Path) -> tuple[str, str, str]:
    return path.owner(), path.group(), f"{path.stat().st_mode & 0o777:04o}"


def _render(value: str, *, release: Path, commit: str, tree: str, trusted: str) -> str:
    return (
        value.replace("@@RELEASE_ROOT@@", str(release))
        .replace("@@E6_SOURCE_COMMIT@@", commit)
        .replace("@@E6_SOURCE_TREE@@", tree)
        .replace("@@TRUSTED_CHECKPOINT_COMMIT@@", trusted)
    )


def _refresh_hashes(release: Path) -> None:
    manifest = release / ".e6-sha256-manifest"
    manifest.unlink(missing_ok=True)
    lines = []
    for path in sorted(release.rglob("*")):
        if path.is_file() and not path.is_symlink() and path != manifest:
            lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
                f"{path.relative_to(release).as_posix()}\n"
            )
    manifest.write_text("".join(lines), encoding="ascii")


def _make_release(
    tmp_path: Path,
    *,
    commit: str = COMMIT,
    tree: str = TREE,
    trusted: str = TRUSTED,
    replacements: dict[str, str] | None = None,
) -> Path:
    release = tmp_path / commit
    shutil.copytree(PACKAGE, release / "deploy/e6_operational_v1")
    for path in (release / "deploy/e6_operational_v1").rglob("*"):
        if path.is_file():
            rendered = _render(
                path.read_text(encoding="utf-8"),
                release=release,
                commit=commit,
                tree=tree,
                trusted=trusted,
            )
            if replacements:
                for original, replacement in replacements.items():
                    rendered = rendered.replace(original, replacement)
            path.write_text(rendered, encoding="utf-8")
    (release / ".e6-release-manifest").write_text(
        f"SOURCE_COMMIT={commit}\n"
        f"SOURCE_TREE={tree}\n"
        f"TRUSTED_CHECKPOINT_COMMIT={trusted}\n",
        encoding="ascii",
    )
    (release / "TRUSTED_E6_CHECKPOINT_COMMIT").write_text(
        trusted + "\n", encoding="ascii"
    )
    rendered = release / ".e6-rendered"
    rendered.mkdir()
    rendered.joinpath("ai-crypto-signal-agent-e6.service").write_bytes(
        release.joinpath(
            "deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.service.in"
        ).read_bytes()
    )
    _refresh_hashes(release)
    release.chmod(0o555)
    return release


def _configuration_text(
    *,
    release: Path,
    release_ref: Path,
    credential_metadata: Path,
    owner_state: Path,
    user: str,
    group: str,
    authorized: bool,
    overrides: dict[str, str] | None = None,
) -> str:
    decision = "true" if authorized else "false"
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": "e6-activation-configuration-v1",
        "E6_RELEASE_COMMIT": release.name,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": TRUSTED,
        "E6_RELEASE_ROOT": str(release),
        "E6_RELEASE_REFERENCE_PATH": str(release_ref),
        "E6_CREDENTIAL_METADATA_PATH": str(credential_metadata),
        "E6_OWNER_CONTROL_STATE_PATH": str(owner_state),
        "E6_SERVICE_USER": user,
        "E6_SERVICE_GROUP": group,
        "E6_RUNTIME_ENABLED": decision,
        "E6_PROVIDER_ENABLED": decision,
        "E6_ACTIVATION_GATE": decision,
        "E6_WORKLOAD_GATE": decision,
        "E6_CREDENTIAL_GATE": decision,
        "E6_NETWORK_GATE": decision,
        "E6_PUBLICATION_GATE": decision,
        "E6_TELEGRAM_PUBLICATION_GATE": decision,
        "E6_AUTOMATIC_RETRY_COUNT": "0",
        "E6_PROVIDER_SUBSTITUTION_ENABLED": "false",
        "E6_PROMPT_REPAIR_ENABLED": "false",
        "E6_STALE_REVIEW_REUSE_ENABLED": "false",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED": "false",
    }
    if overrides:
        values.update(overrides)
    return "".join(f"{key}={values[key]}\n" for key in CONFIGURATION_KEYS)


def test_exact_repository_and_package_inventory_manifest_and_modes() -> None:
    assert all((ROOT / path).is_file() for path in TEN_PATHS)
    actual = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file()
    }
    assert actual == set(PACKAGE_PAYLOAD)
    manifest_entries = {}
    for line in _text(PACKAGE / "deployment-package-manifest.txt").splitlines():
        if line.startswith("PAYLOAD="):
            path, kind, mode = line.removeprefix("PAYLOAD=").split("|")
            assert kind == "regular"
            manifest_entries[path] = mode
    assert manifest_entries == PACKAGE_PAYLOAD
    assert list(manifest_entries) == sorted(manifest_entries)
    for relative, mode in PACKAGE_PAYLOAD.items():
        assert f"{(PACKAGE / relative).stat().st_mode & 0o777:04o}" == mode


def test_all_new_files_are_lf_only_final_lf_and_have_no_secret_material() -> None:
    forbidden_material = (
        b"BEGIN " + b"PRIVATE KEY",
        b"s" + b"k-",
        b"x" + b"oxb-",
        b"fixture-private-" + b"provider-value",
    )
    for relative in TEN_PATHS:
        data = (ROOT / relative).read_bytes()
        assert b"\r" not in data
        assert data.endswith(b"\n")
        assert not any(value in data for value in forbidden_material)


def test_documented_placeholders_are_exact_and_complete() -> None:
    documented = {
        "@@RELEASE_ROOT@@",
        "@@E6_SOURCE_COMMIT@@",
        "@@E6_SOURCE_TREE@@",
        "@@TRUSTED_CHECKPOINT_COMMIT@@",
    }
    found = set()
    for path in PACKAGE.rglob("*"):
        if path.is_file():
            found.update(re.findall(r"@@[A-Z0-9_]+@@", _text(path)))
    assert found == documented
    readme = _text(PACKAGE / "README.md")
    assert all(value in readme for value in documented)


def test_shell_syntax_and_static_no_retry_fallback_or_host_mutation_contract() -> None:
    for path in BIN.iterdir():
        subprocess.run(["bash", "-n", str(path)], check=True)
        text = _text(path)
        assert re.search(
            r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|preset|daemon-reload)\b",
            text,
        ) is None
        assert not any(value in text for value in ("curl ", "wget ", "ccxt", "create_order"))
    run_once = _text(BIN / "ai-crypto-signal-agent-e6-run-once")
    assert run_once.count("engine.run_production_signal_v1") == 1
    assert "run_master_engine_v4" not in run_once
    assert re.search(r"^\s*(while|until)\b", run_once, re.MULTILINE) is None
    assert "sleep " not in run_once
    assert "e6-rollback" not in run_once
    assert run_once.count("/usr/bin/timeout") == 1
    health = _text(BIN / "ai-crypto-signal-agent-e6-health")
    assert re.search(r"\b(open|touch|mkdir|mktemp|install|chmod|chown|mv|unlink)\b", health) is None


def test_operational_scripts_use_root_safe_mode_bit_immutability_contract() -> None:
    expected_occurrences = {
        "ai-crypto-signal-agent-e6-health": 3,
        "ai-crypto-signal-agent-e6-run-once": 2,
        "ai-crypto-signal-agent-e6-rollback": 2,
    }
    for filename, occurrence_count in expected_occurrences.items():
        text = _text(BIN / filename)
        assert ROOT_SAFE_IMMUTABILITY_HELPER in text
        assert text.count("e6_path_has_no_write_mode_bits") == occurrence_count
        assert "! -w" not in text
        assert "stat -Lc '%a' -- \"$path\"" in text
        assert '[[ "$mode" =~ ^[0-7]{3,4}$ ]]' in text
        assert "(( (8#$mode & 8#222) == 0 ))" in text


def test_service_and_nonpersistent_timer_contracts_are_exact(tmp_path: Path) -> None:
    service = _text(SYSTEMD / "ai-crypto-signal-agent-e6.service.in")
    required_environment_files = [
        "/etc/ai-crypto-signal-agent/e6-activation-v1.env",
        "/etc/ai-crypto-signal-agent/phase09r1.env",
        "/etc/ai-crypto-signal-agent/deepseek.env",
    ]
    assert _directives(service, "Type") == ["oneshot"]
    assert _directives(service, "Restart") == ["no"]
    assert _directives(service, "TimeoutStartSec") == ["20min"]
    assert _directives(service, "User") == ["ai-crypto-signal-agent"]
    assert _directives(service, "Group") == ["ai-crypto-signal-agent"]
    assert _directives(service, "WorkingDirectory") == [
        "/var/lib/ai-crypto-signal-agent/phase09r1"
    ]
    assert _directives(service, "EnvironmentFile") == required_environment_files
    assert not any(value.startswith("-") for value in required_environment_files)
    assert _directives(service, "Environment").count(
        STATIC_ACTIVATION_PATH_BINDING
    ) == 1
    assert _directives(service, "LoadCredential") == [
        "accepted_e6_release_commit:"
        "/var/lib/ai-crypto-signal-agent/e6-accepted-release.marker"
    ]
    assert _directives(service, "ExecStart") == [
        "@@RELEASE_ROOT@@/deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once"
    ]
    release = _make_release(tmp_path / "rendered-service")
    rendered_service = _text(
        release / ".e6-rendered/ai-crypto-signal-agent-e6.service"
    )
    assert _directives(rendered_service, "EnvironmentFile") == required_environment_files
    assert _directives(rendered_service, "Environment").count(
        STATIC_ACTIVATION_PATH_BINDING
    ) == 1
    assert _directives(rendered_service, "LoadCredential") == _directives(
        service, "LoadCredential"
    )
    assert not any(
        value.startswith("-")
        for value in _directives(rendered_service, "EnvironmentFile")
    )
    for forbidden in (
        "/etc/ai-crypto-signal-agent/owner-control.env",
        "DEEPSEEK_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "TELEGRAM_BOT_TOKEN=",
        "TELEGRAM_DESTINATION_ID=",
    ):
        assert forbidden not in rendered_service
    assert "run_master_engine_v4" not in service
    assert _directives(service, "User") == ["ai-crypto-signal-agent"]
    assert _directives(service, "Group") == ["ai-crypto-signal-agent"]
    assert _directives(service, "Restart") == ["no"]
    assert "[Install]" not in service
    timer = _text(SYSTEMD / "ai-crypto-signal-agent-e6.timer")
    assert _directives(timer, "Unit") == ["ai-crypto-signal-agent-e6.service"]
    assert _directives(timer, "OnActiveSec") == ["30min"]
    assert _directives(timer, "OnUnitInactiveSec") == ["30min"]
    assert _directives(timer, "AccuracySec") == ["1min"]
    assert _directives(timer, "Persistent") == ["false"]
    assert not any(_directives(timer, key) for key in ("OnBootSec", "OnStartupSec", "OnUnitActiveSec"))


def test_host_access_contract_is_exact_nonsecret_and_documented() -> None:
    assert len(CONFIGURATION_KEYS) == 23
    assert "E6_ACTIVATION_CONFIGURATION_PATH" not in CONFIGURATION_KEYS
    readme = _text(PACKAGE / "README.md")
    for path, metadata in HOST_ACCESS_CONTRACT.items():
        assert path in readme
        assert metadata in readme
    assert STATIC_ACTIVATION_PATH_BINDING in readme
    assert "schema remains exactly 23 keys" in readme
    assert "direct service-user file readability" in readme
    assert "${CREDENTIALS_DIRECTORY}/accepted_e6_release_commit" in readme
    assert "no second canary, cutover, or activation" in readme


def _make_run_once_fixture(
    tmp_path: Path, *, authorized: bool = True, overrides: dict[str, str] | None = None
) -> tuple[Path, dict[str, str], dict[str, Path]]:
    runtime = tmp_path / "runtime"
    credentials = tmp_path / "credentials"
    metadata = tmp_path / "metadata"
    for path in (runtime, credentials, metadata):
        path.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o750)
    invocation = tmp_path / "invocation"
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"$E6_FAKE_INVOCATION\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    user = tmp_path.owner()
    group = tmp_path.group()
    lock = runtime / "e6-operational.lock"
    kill = tmp_path / "kill-switch.active"
    replacements = {
        'readonly LOCK_PATH="/run/ai-crypto-signal-agent/e6-operational.lock"': f'readonly LOCK_PATH="{lock}"',
        'readonly KILL_SWITCH_PATH="/var/lib/ai-crypto-signal-agent/e6-kill-switch.active"': f'readonly KILL_SWITCH_PATH="{kill}"',
        'readonly PYTHON_BIN="/opt/ai-crypto-signal-agent-phase09r1/.venv/bin/python"': f'readonly PYTHON_BIN="{fake_python}"',
        'readonly SERVICE_USER="ai-crypto-signal-agent"': f'readonly SERVICE_USER="{user}"',
        'readonly SERVICE_GROUP="ai-crypto-signal-agent"': f'readonly SERVICE_GROUP="{group}"',
    }
    release = _make_release(tmp_path / "release-parent", replacements=replacements)
    release_ref = metadata / "installed-release.path"
    credential_metadata = metadata / "credentials.metadata"
    owner_state = metadata / "owner-state.json"
    configuration = metadata / "activation.env"
    release_ref.write_text(f"{release}\n", encoding="ascii")
    release_ref.chmod(0o440)
    credential_metadata.write_text("metadata-only\n", encoding="ascii")
    owner_state.write_text("{}\n", encoding="ascii")
    credential_metadata.chmod(0o640)
    owner_state.chmod(0o600)
    configuration.write_text(
        _configuration_text(
            release=release,
            release_ref=release_ref,
            credential_metadata=credential_metadata,
            owner_state=owner_state,
            user=user,
            group=group,
            authorized=authorized,
            overrides=overrides,
        ),
        encoding="ascii",
    )
    configuration.chmod(0o640)
    credentials.joinpath("accepted_e6_release_commit").write_text(
        release.name + "\n", encoding="ascii"
    )
    environment = {
        **os.environ,
        "CREDENTIALS_DIRECTORY": str(credentials),
        "E6_ACTIVATION_CONFIGURATION_PATH": str(configuration),
        "E6_FAKE_INVOCATION": str(invocation),
    }
    paths = {"invocation": invocation, "lock": lock, "kill": kill, "configuration": configuration}
    wrapper = release / "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-run-once"
    return wrapper, environment, paths


def test_run_once_requires_bound_activation_path_and_credential_copy(
    tmp_path: Path,
) -> None:
    wrapper, environment, paths = _make_run_once_fixture(tmp_path, authorized=True)
    for configured_path in (None, ""):
        rejected_environment = environment.copy()
        if configured_path is None:
            rejected_environment.pop("E6_ACTIVATION_CONFIGURATION_PATH")
        else:
            rejected_environment["E6_ACTIVATION_CONFIGURATION_PATH"] = configured_path
        rejected = subprocess.run(
            [str(wrapper)],
            env=rejected_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert rejected.returncode == 78
        assert "E6_LAUNCH_BLOCKED=ACTIVATION_CONFIGURATION_FILE" in rejected.stderr
        assert not paths["invocation"].exists()

    source = _text(BIN / "ai-crypto-signal-agent-e6-run-once")
    assert "/etc/ai-crypto-signal-agent/phase09r1.env" not in source
    assert "/etc/ai-crypto-signal-agent/deepseek.env" not in source
    assert "/var/lib/ai-crypto-signal-agent/e6-accepted-release.marker" not in source
    assert '${CREDENTIALS_DIRECTORY:-}' in source
    assert 'accepted_e6_release_commit' in source


def test_run_once_defaults_and_partial_authorization_block_before_invocation(tmp_path: Path) -> None:
    wrapper, environment, paths = _make_run_once_fixture(tmp_path / "default", authorized=False)
    denied = subprocess.run([str(wrapper)], env=environment, text=True, capture_output=True, check=False)
    assert denied.returncode == 78
    assert "E6_RUNTIME_DISABLED" in denied.stderr
    assert not paths["invocation"].exists()
    assert not paths["lock"].exists()

    wrapper, environment, paths = _make_run_once_fixture(
        tmp_path / "partial",
        authorized=True,
        overrides={"E6_TELEGRAM_PUBLICATION_GATE": "false"},
    )
    partial = subprocess.run([str(wrapper)], env=environment, text=True, capture_output=True, check=False)
    assert partial.returncode == 78
    assert "TELEGRAM_PUBLICATION_GATE_CLOSED" in partial.stderr
    assert not paths["invocation"].exists()


def test_run_once_authorized_fake_invokes_e6_cli_once_and_removes_lock(tmp_path: Path) -> None:
    wrapper, environment, paths = _make_run_once_fixture(tmp_path, authorized=True)
    result = subprocess.run([str(wrapper)], env=environment, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert paths["invocation"].read_text(encoding="utf-8").splitlines() == [
        "-m engine.run_production_signal_v1"
    ]
    assert not paths["lock"].exists()


def test_run_once_release_write_mode_bits_fail_closed_before_invocation(tmp_path: Path) -> None:
    for mode in (0o755, 0o575, 0o557):
        wrapper, environment, paths = _make_run_once_fixture(
            tmp_path / f"mode-{mode:o}", authorized=True
        )
        wrapper.parents[3].chmod(mode)
        rejected = subprocess.run(
            [str(wrapper)], env=environment, text=True, capture_output=True, check=False
        )
        assert rejected.returncode == 78, f"{mode:o}: {rejected.stdout}{rejected.stderr}"
        assert "RELEASE_NOT_IMMUTABLE" in rejected.stderr
        assert not paths["invocation"].exists()
        assert not paths["lock"].exists()


def test_run_once_kill_switch_and_overlap_lock_block_without_retry(tmp_path: Path) -> None:
    wrapper, environment, paths = _make_run_once_fixture(tmp_path / "kill", authorized=True)
    paths["kill"].write_text("active\n", encoding="ascii")
    killed = subprocess.run([str(wrapper)], env=environment, text=True, capture_output=True, check=False)
    assert killed.returncode == 75
    assert "KILL_SWITCH_ACTIVE" in killed.stderr
    assert not paths["invocation"].exists()

    wrapper, environment, paths = _make_run_once_fixture(tmp_path / "lock", authorized=True)
    with paths["lock"].open("w", encoding="ascii") as held:
        paths["lock"].chmod(0o600)
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        blocked = subprocess.run([str(wrapper)], env=environment, text=True, capture_output=True, check=False)
    assert blocked.returncode == 75
    assert "OVERLAP_LOCK_HELD" in blocked.stderr
    assert not paths["invocation"].exists()


def _make_health_fixture(
    tmp_path: Path, *, authorized: bool = False
) -> tuple[Path, dict[str, str], dict[str, Path]]:
    runtime = tmp_path / "runtime"
    units = tmp_path / "units"
    metadata = tmp_path / "metadata"
    fake_bin = tmp_path / "fake-bin"
    for path in (runtime, units, metadata, fake_bin):
        path.mkdir(parents=True)
    metadata.chmod(0o750)
    user = tmp_path.owner()
    group = tmp_path.group()
    release_ref = runtime / "installed-release.path"
    marker = runtime / "accepted-release.marker"
    kill = runtime / "kill-switch.active"
    lock = runtime / "operational.lock"
    service = units / "ai-crypto-signal-agent-e6.service"
    timer = units / "ai-crypto-signal-agent-e6.timer"
    configuration = metadata / "activation.env"
    credential_metadata = metadata / "credentials.metadata"
    telegram_environment = metadata / "phase09r1.env"
    provider_environment = metadata / "deepseek.env"
    owner_state = metadata / "owner-state.json"
    rollback_ref = runtime / "rollback-release.path"
    replacements = {
        'readonly RELEASE_REF="/var/lib/ai-crypto-signal-agent/e6-installed-release.path"': f'readonly RELEASE_REF="{release_ref}"',
        'readonly RUNTIME_MARKER="/var/lib/ai-crypto-signal-agent/e6-accepted-release.marker"': f'readonly RUNTIME_MARKER="{marker}"',
        'readonly KILL_SWITCH="/var/lib/ai-crypto-signal-agent/e6-kill-switch.active"': f'readonly KILL_SWITCH="{kill}"',
        'readonly LOCK_PATH="/run/ai-crypto-signal-agent/e6-operational.lock"': f'readonly LOCK_PATH="{lock}"',
        'readonly SERVICE_UNIT="/etc/systemd/system/ai-crypto-signal-agent-e6.service"': f'readonly SERVICE_UNIT="{service}"',
        'readonly TIMER_UNIT="/etc/systemd/system/ai-crypto-signal-agent-e6.timer"': f'readonly TIMER_UNIT="{timer}"',
        'readonly CONFIGURATION_DIRECTORY="/etc/ai-crypto-signal-agent"': f'readonly CONFIGURATION_DIRECTORY="{metadata}"',
        'readonly ACTIVATION_CONFIGURATION="/etc/ai-crypto-signal-agent/e6-activation-v1.env"': f'readonly ACTIVATION_CONFIGURATION="{configuration}"',
        'readonly CREDENTIAL_METADATA="/etc/ai-crypto-signal-agent/e6-credentials.metadata"': f'readonly CREDENTIAL_METADATA="{credential_metadata}"',
        'readonly TELEGRAM_ENVIRONMENT="/etc/ai-crypto-signal-agent/phase09r1.env"': f'readonly TELEGRAM_ENVIRONMENT="{telegram_environment}"',
        'readonly PROVIDER_ENVIRONMENT="/etc/ai-crypto-signal-agent/deepseek.env"': f'readonly PROVIDER_ENVIRONMENT="{provider_environment}"',
        'readonly OWNER_CONTROL_STATE="/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json"': f'readonly OWNER_CONTROL_STATE="{owner_state}"',
        'readonly ROLLBACK_REF="/var/lib/ai-crypto-signal-agent/e6-rollback-release.path"': f'readonly ROLLBACK_REF="{rollback_ref}"',
        'readonly ROOT_USER="root"': f'readonly ROOT_USER="{user}"',
        'readonly ROOT_GROUP="root"': f'readonly ROOT_GROUP="{group}"',
        'readonly SERVICE_USER="ai-crypto-signal-agent"': f'readonly SERVICE_USER="{user}"',
        'readonly SERVICE_GROUP="ai-crypto-signal-agent"': f'readonly SERVICE_GROUP="{group}"',
    }
    release = _make_release(tmp_path / "release-parent", replacements=replacements)
    release_ref.write_text(f"{release}\n", encoding="ascii")
    release_ref.chmod(0o440)
    marker.write_text(release.name + "\n", encoding="ascii")
    marker.chmod(0o400)
    service.write_bytes(release.joinpath(".e6-rendered/ai-crypto-signal-agent-e6.service").read_bytes())
    timer.write_bytes(release.joinpath("deploy/e6_operational_v1/systemd/ai-crypto-signal-agent-e6.timer").read_bytes())
    configuration.write_text(
        _configuration_text(
            release=release,
            release_ref=release_ref,
            credential_metadata=credential_metadata,
            owner_state=owner_state,
            user=user,
            group=group,
            authorized=authorized,
        ),
        encoding="ascii",
    )
    configuration.chmod(0o640)
    credential_metadata.write_text("fixture-secret-must-not-be-output\n", encoding="ascii")
    credential_metadata.chmod(0o640)
    telegram_environment.write_text("telegram-secret-must-not-be-output\n", encoding="ascii")
    telegram_environment.chmod(0o600)
    provider_environment.write_text("provider-secret-must-not-be-output\n", encoding="ascii")
    provider_environment.chmod(0o600)
    owner_state.write_text(
        '{"schema_name":"telegram-owner-control-state","schema_version":1}\n',
        encoding="ascii",
    )
    owner_state.chmod(0o600)
    fake_systemctl = fake_bin / "systemctl"
    fake_systemctl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1:$2" in
  is-active:ai-crypto-signal-agent-e6.service) printf '%s\n' "$MOCK_SERVICE_ACTIVE" ;;
  is-enabled:ai-crypto-signal-agent-e6.service) printf '%s\n' "$MOCK_SERVICE_ENABLED" ;;
  is-active:ai-crypto-signal-agent-e6.timer) printf '%s\n' "$MOCK_TIMER_ACTIVE" ;;
  is-enabled:ai-crypto-signal-agent-e6.timer) printf '%s\n' "$MOCK_TIMER_ENABLED" ;;
  show:ai-crypto-signal-agent-e6.timer)
    if [[ "$*" == *NextElapseUSecMonotonic* ]]; then
      printf '%s\n' "$MOCK_TIMER_NEXT"
    elif [[ "$*" == *SubState* ]]; then
      printf '%s\n' "$MOCK_TIMER_SUBSTATE"
    else
      exit 64
    fi
    ;;
  *) exit 64 ;;
esac
""",
        encoding="utf-8",
    )
    fake_systemctl.chmod(0o755)
    fake_stat = fake_bin / "stat"
    fake_stat.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
path="${!#}"
if [[ "$path" == "$MOCK_CONFIG_DIRECTORY_PATH" && -n "${MOCK_CONFIG_DIRECTORY_STAT:-}" ]]; then
  printf '%s\n' "$MOCK_CONFIG_DIRECTORY_STAT"
elif [[ "$path" == "$MOCK_RELEASE_REFERENCE_PATH" && -n "${MOCK_RELEASE_REFERENCE_STAT:-}" ]]; then
  printf '%s\n' "$MOCK_RELEASE_REFERENCE_STAT"
elif [[ "$path" == "$MOCK_ACCEPTED_MARKER_PATH" && -n "${MOCK_ACCEPTED_MARKER_STAT:-}" ]]; then
  printf '%s\n' "$MOCK_ACCEPTED_MARKER_STAT"
elif [[ "$path" == "$MOCK_TELEGRAM_ENVIRONMENT_PATH" && -n "${MOCK_TELEGRAM_ENVIRONMENT_STAT:-}" ]]; then
  printf '%s\n' "$MOCK_TELEGRAM_ENVIRONMENT_STAT"
elif [[ "$path" == "$MOCK_PROVIDER_ENVIRONMENT_PATH" && -n "${MOCK_PROVIDER_ENVIRONMENT_STAT:-}" ]]; then
  printf '%s\n' "$MOCK_PROVIDER_ENVIRONMENT_STAT"
else
  exec /usr/bin/stat "$@"
fi
""",
        encoding="utf-8",
    )
    fake_stat.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "MOCK_SERVICE_ACTIVE": "inactive",
        "MOCK_SERVICE_ENABLED": "static",
        "MOCK_TIMER_ACTIVE": "inactive",
        "MOCK_TIMER_ENABLED": "disabled",
        "MOCK_TIMER_SUBSTATE": "dead",
        "MOCK_TIMER_NEXT": "0",
        "MOCK_CONFIG_DIRECTORY_PATH": str(metadata),
        "MOCK_RELEASE_REFERENCE_PATH": str(release_ref),
        "MOCK_ACCEPTED_MARKER_PATH": str(marker),
        "MOCK_TELEGRAM_ENVIRONMENT_PATH": str(telegram_environment),
        "MOCK_PROVIDER_ENVIRONMENT_PATH": str(provider_environment),
    }
    health = release / "deploy/e6_operational_v1/bin/ai-crypto-signal-agent-e6-health"
    paths = {
        "release": release,
        "configuration": configuration,
        "credential_metadata": credential_metadata,
        "configuration_directory": metadata,
        "release_ref": release_ref,
        "marker": marker,
        "telegram_environment": telegram_environment,
        "provider_environment": provider_environment,
        "kill": kill,
        "lock": lock,
        "service": service,
        "timer": timer,
    }
    return health, environment, paths


def test_health_accepts_exact_disabled_and_active_states_only(tmp_path: Path) -> None:
    health, environment, _paths = _make_health_fixture(tmp_path / "disabled-zero")
    disabled = subprocess.run([str(health)], env=environment, text=True, capture_output=True, check=False)
    assert disabled.returncode == 0, disabled.stdout + disabled.stderr
    assert "HEALTH_STATUS=READY_NOT_ENABLED" in disabled.stdout
    assert "SERVICE_UNIT_MATCH=YES" in disabled.stdout
    assert "ROLLBACK_READINESS=YES" in disabled.stdout
    assert "ROLLBACK_STATE=NOT_CONFIGURED" in disabled.stdout
    assert "HEALTH_REASON=" not in disabled.stdout
    assert "SECRET_VALUE_EXPOSURE_COUNT=0" in disabled.stdout
    assert "AUTOMATED_EXCHANGE_TRADING_ENABLED=NO" in disabled.stdout
    assert "CONFIGURATION_DIRECTORY_ACCESS_VALID=YES" in disabled.stdout
    assert "INSTALLED_RELEASE_REFERENCE_METADATA_VALID=YES" in disabled.stdout
    assert "ACCEPTED_RELEASE_MARKER_METADATA_VALID=YES" in disabled.stdout
    assert "SECRET_ENVIRONMENT_METADATA_VALID=YES" in disabled.stdout
    assert "fixture-secret-must-not-be-output" not in disabled.stdout + disabled.stderr
    assert "telegram-secret-must-not-be-output" not in disabled.stdout + disabled.stderr
    assert "provider-secret-must-not-be-output" not in disabled.stdout + disabled.stderr

    health, environment, _paths = _make_health_fixture(tmp_path / "disabled-infinity")
    environment["MOCK_TIMER_NEXT"] = "infinity"
    disabled_infinity = subprocess.run(
        [str(health)], env=environment, text=True, capture_output=True, check=False
    )
    assert disabled_infinity.returncode == 0, disabled_infinity.stdout + disabled_infinity.stderr
    assert "HEALTH_STATUS=READY_NOT_ENABLED" in disabled_infinity.stdout

    health, environment, _paths = _make_health_fixture(tmp_path / "disabled-finite")
    environment["MOCK_TIMER_NEXT"] = "2800000000"
    disabled_finite = subprocess.run(
        [str(health)], env=environment, text=True, capture_output=True, check=False
    )
    assert disabled_finite.returncode == 1
    assert "SERVICE_TIMER_ACTIVATION_STATE_CONTRADICTORY" in disabled_finite.stdout

    health, environment, _paths = _make_health_fixture(tmp_path / "active", authorized=True)
    environment.update(
        MOCK_TIMER_ACTIVE="active",
        MOCK_TIMER_ENABLED="enabled",
        MOCK_TIMER_SUBSTATE="waiting",
        MOCK_TIMER_NEXT="2800000000",
    )
    active = subprocess.run([str(health)], env=environment, text=True, capture_output=True, check=False)
    assert active.returncode == 0, active.stdout + active.stderr
    assert "HEALTH_STATUS=READY_AND_AUTOMATION_ENABLED" in active.stdout

    health, environment, _paths = _make_health_fixture(
        tmp_path / "active-infinity", authorized=True
    )
    environment.update(
        MOCK_TIMER_ACTIVE="active",
        MOCK_TIMER_ENABLED="enabled",
        MOCK_TIMER_SUBSTATE="waiting",
        MOCK_TIMER_NEXT="infinity",
    )
    active_infinity = subprocess.run(
        [str(health)], env=environment, text=True, capture_output=True, check=False
    )
    assert active_infinity.returncode == 1
    assert "SERVICE_TIMER_ACTIVATION_STATE_CONTRADICTORY" in active_infinity.stdout

    health, environment, _paths = _make_health_fixture(tmp_path / "partial")
    environment.update(MOCK_TIMER_ACTIVE="active", MOCK_TIMER_ENABLED="enabled", MOCK_TIMER_SUBSTATE="waiting", MOCK_TIMER_NEXT="2800000000")
    partial = subprocess.run([str(health)], env=environment, text=True, capture_output=True, check=False)
    assert partial.returncode == 1
    assert "HEALTH_STATUS=NOT_READY" in partial.stdout
    assert "SERVICE_TIMER_ACTIVATION_STATE_CONTRADICTORY" in partial.stdout


def test_health_rejects_service_missing_required_environment_file(tmp_path: Path) -> None:
    required_host_environment_files = (
        "/etc/ai-crypto-signal-agent/phase09r1.env",
        "/etc/ai-crypto-signal-agent/deepseek.env",
    )
    for environment_file in required_host_environment_files:
        health, environment, paths = _make_health_fixture(
            tmp_path / Path(environment_file).stem
        )
        service = paths["service"]
        service.write_text(
            service.read_text(encoding="utf-8").replace(
                f"EnvironmentFile={environment_file}\n", ""
            ),
            encoding="utf-8",
        )
        rejected = subprocess.run(
            [str(health)],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert rejected.returncode == 1
        assert "SERVICE_UNIT_MATCH=NO" in rejected.stdout
        assert "HEALTH_STATUS=NOT_READY" in rejected.stdout

    service_variants = {
        "missing-static-binding": lambda text: text.replace(
            f"Environment={STATIC_ACTIVATION_PATH_BINDING}\n", ""
        ),
        "duplicate-static-binding": lambda text: text.replace(
            f"Environment={STATIC_ACTIVATION_PATH_BINDING}\n",
            f"Environment={STATIC_ACTIVATION_PATH_BINDING}\n" * 2,
        ),
        "altered-static-binding": lambda text: text.replace(
            STATIC_ACTIVATION_PATH_BINDING,
            "E6_ACTIVATION_CONFIGURATION_PATH=/etc/ai-crypto-signal-agent/wrong.env",
        ),
        "reordered-static-binding": lambda text: text.replace(
            f"Environment={STATIC_ACTIVATION_PATH_BINDING}\n"
            f"Environment=E6_SOURCE_COMMIT={COMMIT}\n",
            f"Environment=E6_SOURCE_COMMIT={COMMIT}\n"
            f"Environment={STATIC_ACTIVATION_PATH_BINDING}\n",
        ),
    }
    for name, mutate in service_variants.items():
        health, environment, paths = _make_health_fixture(tmp_path / name)
        service = paths["service"]
        original = service.read_text(encoding="utf-8")
        changed = mutate(original)
        assert changed != original
        service.write_text(changed, encoding="utf-8")
        rejected = subprocess.run(
            [str(health)], env=environment, text=True, capture_output=True, check=False
        )
        assert rejected.returncode == 1
        assert "SERVICE_UNIT_MATCH=NO" in rejected.stdout
        assert "HEALTH_STATUS=NOT_READY" in rejected.stdout


def test_health_rejects_each_host_access_metadata_defect_without_secret_read(
    tmp_path: Path,
) -> None:
    cases = (
        "configuration-parent-old-group",
        "configuration-parent-wrong-mode",
        "configuration-parent-symlink",
        "release-reference-old-metadata",
        "release-reference-wrong-group",
        "release-reference-wrong-mode",
        "release-reference-symlink",
        "accepted-marker-wrong-owner",
        "accepted-marker-wrong-group",
        "accepted-marker-wrong-mode",
        "telegram-environment-wrong-owner",
        "telegram-environment-wrong-mode",
        "provider-environment-wrong-group",
        "provider-environment-wrong-mode",
    )
    for case in cases:
        health, environment, paths = _make_health_fixture(tmp_path / case)
        user = tmp_path.owner()
        group = tmp_path.group()
        if case == "configuration-parent-old-group":
            environment["MOCK_CONFIG_DIRECTORY_STAT"] = f"{user}:root:750"
        elif case == "configuration-parent-wrong-mode":
            paths["configuration_directory"].chmod(0o700)
        elif case == "configuration-parent-symlink":
            configuration_directory = paths["configuration_directory"]
            real_directory = configuration_directory.with_name("metadata-real")
            configuration_directory.rename(real_directory)
            configuration_directory.symlink_to(real_directory, target_is_directory=True)
        elif case == "release-reference-old-metadata":
            environment["MOCK_RELEASE_REFERENCE_STAT"] = f"{user}:root:400"
        elif case == "release-reference-wrong-group":
            environment["MOCK_RELEASE_REFERENCE_STAT"] = f"{user}:wrong:440"
        elif case == "release-reference-wrong-mode":
            paths["release_ref"].chmod(0o400)
        elif case == "release-reference-symlink":
            release_ref = paths["release_ref"]
            real_reference = release_ref.with_name("installed-release-real.path")
            release_ref.rename(real_reference)
            release_ref.symlink_to(real_reference)
        elif case == "accepted-marker-wrong-owner":
            environment["MOCK_ACCEPTED_MARKER_STAT"] = f"wrong:{group}:400"
        elif case == "accepted-marker-wrong-group":
            environment["MOCK_ACCEPTED_MARKER_STAT"] = f"{user}:wrong:400"
        elif case == "accepted-marker-wrong-mode":
            paths["marker"].chmod(0o440)
        elif case == "telegram-environment-wrong-owner":
            environment["MOCK_TELEGRAM_ENVIRONMENT_STAT"] = f"wrong:{group}:600"
        elif case == "telegram-environment-wrong-mode":
            paths["telegram_environment"].chmod(0o640)
        elif case == "provider-environment-wrong-group":
            environment["MOCK_PROVIDER_ENVIRONMENT_STAT"] = f"{user}:wrong:600"
        elif case == "provider-environment-wrong-mode":
            paths["provider_environment"].chmod(0o640)
        rejected = subprocess.run(
            [str(health)], env=environment, text=True, capture_output=True, check=False
        )
        assert rejected.returncode == 1, case
        assert "HEALTH_STATUS=NOT_READY" in rejected.stdout, case
        assert "fixture-secret-must-not-be-output" not in rejected.stdout + rejected.stderr
        assert "telegram-secret-must-not-be-output" not in rejected.stdout + rejected.stderr
        assert "provider-secret-must-not-be-output" not in rejected.stdout + rejected.stderr
        assert "AUTOMATIC_RETRY_COUNT=0" in rejected.stdout
        assert "AUTOMATED_EXCHANGE_TRADING_ENABLED=NO" in rejected.stdout


def test_health_rejects_identity_timer_credential_kill_and_lock_defects_read_only(tmp_path: Path) -> None:
    health, environment, paths = _make_health_fixture(tmp_path / "lock-absent")
    before = {path: path.read_bytes() for path in paths.values() if path.is_file()}
    result = subprocess.run([str(health)], env=environment, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert not paths["lock"].exists()
    assert "fixture-secret-must-not-be-output" not in result.stdout + result.stderr
    assert all(path.read_bytes() == value for path, value in before.items())

    cases = (
        "writable-release-owner",
        "writable-release-group",
        "writable-release-other",
        "persistent",
        "credential",
        "kill",
        "lock",
    )
    writable_modes = {
        "writable-release-owner": 0o755,
        "writable-release-group": 0o575,
        "writable-release-other": 0o557,
    }
    for case in cases:
        health, environment, paths = _make_health_fixture(tmp_path / case)
        held = None
        if case in writable_modes:
            paths["release"].chmod(writable_modes[case])
        elif case == "persistent":
            paths["timer"].write_text(
                paths["timer"].read_text().replace("Persistent=false", "Persistent=true")
            )
        elif case == "credential":
            paths["credential_metadata"].chmod(0o600)
        elif case == "kill":
            paths["kill"].write_text("active\n", encoding="ascii")
        elif case == "lock":
            held = paths["lock"].open("w", encoding="ascii")
            paths["lock"].chmod(0o600)
            fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            rejected = subprocess.run([str(health)], env=environment, text=True, capture_output=True, check=False)
        finally:
            if held is not None:
                held.close()
        assert rejected.returncode == 1, case
        assert "HEALTH_STATUS=NOT_READY" in rejected.stdout, case


def _make_rollback_release(parent: Path, commit: str, trusted: str = TRUSTED) -> Path:
    return _make_release(parent, commit=commit, trusted=trusted)


def _make_rollback_script(tmp_path: Path) -> Path:
    rollback = tmp_path / "e6-rollback"
    rollback.write_text(
        _text(BIN / "ai-crypto-signal-agent-e6-rollback")
        .replace("@@TRUSTED_CHECKPOINT_COMMIT@@", TRUSTED)
        .replace('readonly ROOT_USER="root"', f'readonly ROOT_USER="{tmp_path.owner()}"')
        .replace('readonly ROOT_GROUP="root"', f'readonly ROOT_GROUP="{tmp_path.group()}"')
        .replace(
            'readonly SERVICE_GROUP="ai-crypto-signal-agent"',
            f'readonly SERVICE_GROUP="{tmp_path.group()}"',
        ),
        encoding="utf-8",
    )
    rollback.chmod(0o755)
    return rollback


def test_manual_rollback_requires_trusted_immutable_target_and_is_idempotent(tmp_path: Path) -> None:
    current = _make_rollback_release(tmp_path / "current", "d" * 40)
    target = _make_rollback_release(tmp_path / "target", "e" * 40)
    host = tmp_path / "host"
    state = host / "var/lib/ai-crypto-signal-agent"
    state.mkdir(parents=True)
    current_ref = state / "e6-installed-release.path"
    current_ref.write_text(f"{current}\n", encoding="ascii")
    current_ref.chmod(0o440)
    accepted_marker = state / "e6-accepted-release.marker"
    accepted_marker.write_text(current.name + "\n", encoding="ascii")
    accepted_marker.chmod(0o400)
    accepted_before = (accepted_marker.read_bytes(), _metadata(accepted_marker))
    rollback = _make_rollback_script(tmp_path)

    first = subprocess.run(
        [str(rollback), "--target-release", str(target), "--destdir", str(host)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    assert "E6_ROLLBACK=COMPLETE" in first.stdout
    assert current_ref.read_text() == f"{target}\n"
    rollback_ref = state / "e6-rollback-release.path"
    evidence = state / "e6-rollback-evidence.txt"
    assert rollback_ref.read_text() == f"{current}\n"
    assert f"FROM_RELEASE={current}" in evidence.read_text()
    expected_user = tmp_path.owner()
    expected_group = tmp_path.group()
    assert _metadata(current_ref) == (expected_user, expected_group, "0440")
    assert _metadata(rollback_ref) == (expected_user, expected_group, "0400")
    assert _metadata(evidence) == (expected_user, expected_group, "0400")
    assert accepted_before == (accepted_marker.read_bytes(), _metadata(accepted_marker))
    before = (
        current_ref.read_bytes(),
        _metadata(current_ref),
        rollback_ref.read_bytes(),
        _metadata(rollback_ref),
        evidence.read_bytes(),
        _metadata(evidence),
    )

    replay = subprocess.run(
        [str(rollback), "--target-release", str(target), "--destdir", str(host)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert replay.returncode == 0
    assert "E6_ROLLBACK=IDEMPOTENT_REPLAY" in replay.stdout
    assert before == (
        current_ref.read_bytes(),
        _metadata(current_ref),
        rollback_ref.read_bytes(),
        _metadata(rollback_ref),
        evidence.read_bytes(),
        _metadata(evidence),
    )
    assert accepted_before == (accepted_marker.read_bytes(), _metadata(accepted_marker))


def test_manual_rollback_rejects_missing_writable_symlink_and_untrusted_targets(tmp_path: Path) -> None:
    current = _make_rollback_release(tmp_path / "current", "d" * 40)
    host = tmp_path / "host"
    state = host / "var/lib/ai-crypto-signal-agent"
    state.mkdir(parents=True)
    current_ref = state / "e6-installed-release.path"
    current_ref.write_text(f"{current}\n")
    current_ref.chmod(0o440)
    rollback = _make_rollback_script(tmp_path)
    writable_targets = []
    for mode in (0o755, 0o575, 0o557):
        writable = _make_rollback_release(tmp_path / f"writable-{mode:o}", "e" * 40)
        writable.chmod(mode)
        writable_targets.append(writable)
    untrusted = _make_rollback_release(tmp_path / "untrusted", "f" * 40, "0" * 40)
    link = tmp_path / "target-link"
    link.symlink_to(untrusted, target_is_directory=True)
    legacy = tmp_path / "legacy" / ("1" * 40)
    legacy.mkdir(parents=True)
    legacy.chmod(0o555)
    current_before = (current_ref.read_bytes(), _metadata(current_ref))
    for target in (tmp_path / "missing", *writable_targets, link, untrusted, legacy):
        rejected = subprocess.run(
            [str(rollback), "--target-release", str(target), "--destdir", str(host)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert rejected.returncode == 65
        assert current_before == (current_ref.read_bytes(), _metadata(current_ref))
    assert current_ref.read_text() == f"{current}\n"
    assert not state.joinpath("e6-rollback-release.path").exists()


def test_manual_rollback_atomic_current_reference_failure_preserves_current(
    tmp_path: Path,
) -> None:
    current = _make_rollback_release(tmp_path / "current", "d" * 40)
    target = _make_rollback_release(tmp_path / "target", "e" * 40)
    host = tmp_path / "host"
    state = host / "var/lib/ai-crypto-signal-agent"
    state.mkdir(parents=True)
    current_ref = state / "e6-installed-release.path"
    current_ref.write_text(f"{current}\n", encoding="ascii")
    current_ref.chmod(0o440)
    before = (current_ref.read_bytes(), _metadata(current_ref))
    rollback = _make_rollback_script(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "${!#}" == "$FAIL_DESTINATION" ]]; then
  exit 74
fi
exec /usr/bin/mv "$@"
""",
        encoding="utf-8",
    )
    fake_mv.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "FAIL_DESTINATION": str(current_ref),
    }
    failed = subprocess.run(
        [str(rollback), "--target-release", str(target), "--destdir", str(host)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert failed.returncode != 0
    assert before == (current_ref.read_bytes(), _metadata(current_ref))


def test_package_has_no_automatic_rollback_service_control_or_trading_authority() -> None:
    run_once = _text(BIN / "ai-crypto-signal-agent-e6-run-once")
    health = _text(BIN / "ai-crypto-signal-agent-e6-health")
    service = _text(SYSTEMD / "ai-crypto-signal-agent-e6.service.in")
    timer = _text(SYSTEMD / "ai-crypto-signal-agent-e6.timer")
    assert "ai-crypto-signal-agent-e6-rollback" not in run_once + health + service + timer
    all_text = "\n".join(_text(path) for path in PACKAGE.rglob("*") if path.is_file())
    assert re.search(
        r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|preset|daemon-reload)\b",
        all_text,
    ) is None
    assert "create_order" not in all_text
    assert "mark_entry_active" not in all_text
    assert "AUTOMATED_EXCHANGE_TRADING=disabled" in all_text
