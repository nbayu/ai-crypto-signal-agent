from __future__ import annotations

import hashlib
import fcntl
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deploy" / "operational_v1"
BIN = PACKAGE / "bin"
SYSTEMD = PACKAGE / "systemd"
TRUSTED = "e50041f7296bd9e042f749b6a98393b3df9747a1"
TRUSTED_SHA256 = "64fe567ee269739146c30a9111113a07b1fd91d83d46e9e8dbd7fa967f1cbb6f"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _directives(text: str, key: str) -> list[str]:
    prefix = f"{key}="
    return [
        line[len(prefix) :]
        for line in text.splitlines()
        if line.startswith(prefix)
    ]


def test_exact_package_inventory() -> None:
    expected = {
        "bin/ai-crypto-signal-agent-health",
        "bin/ai-crypto-signal-agent-install",
        "bin/ai-crypto-signal-agent-rollback",
        "bin/ai-crypto-signal-agent-run-once",
        "bin/ai-crypto-signal-agent-telegram-control",
        "deployment-package-manifest.txt",
        "monitoring/README.md",
        "systemd/ai-crypto-signal-agent.service.in",
        "systemd/ai-crypto-signal-agent-telegram-control.service.in",
        "systemd/ai-crypto-signal-agent.timer",
        "tmpfiles.d/ai-crypto-signal-agent.conf",
    }
    actual = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file()
    }
    assert actual == expected


def test_shell_files_have_valid_syntax() -> None:
    for name in (
        "ai-crypto-signal-agent-health",
        "ai-crypto-signal-agent-install",
        "ai-crypto-signal-agent-rollback",
        "ai-crypto-signal-agent-run-once",
        "ai-crypto-signal-agent-telegram-control",
    ):
        subprocess.run(["bash", "-n", str(BIN / name)], check=True)


def test_wrapper_has_one_entrypoint_and_no_retry_construct() -> None:
    text = _text(BIN / "ai-crypto-signal-agent-run-once")
    assert text.count("engine.run_production_signal_v1") == 1
    assert re.search(r"^\s*(while|until)\b", text, re.MULTILINE) is None
    assert "sleep " not in text
    assert "retry" not in text.lower()
    assert "flock -n 9" in text
    assert text.count("exec /usr/bin/timeout") == 1
    assert "--kill-after=30s 20m" in text


def test_wrapper_has_fail_closed_trust_release_and_kill_switch_gates() -> None:
    text = _text(BIN / "ai-crypto-signal-agent-run-once")
    for required in (
        ".f4-release-manifest",
        ".f4-sha256-manifest",
        "TRUSTED_CP09_COMMIT",
        "accepted_locked_commit",
        TRUSTED_SHA256,
        "KILL_SWITCH_ACTIVE",
        "OVERLAP_LOCK_HELD",
    ):
        assert required in text


def test_service_contract() -> None:
    text = _text(SYSTEMD / "ai-crypto-signal-agent.service.in")
    assert _directives(text, "Type") == ["oneshot"]
    assert _directives(text, "Restart") == ["no"]
    assert _directives(text, "TimeoutStartSec") == ["20min"]
    assert len(_directives(text, "ExecStart")) == 1
    assert not _directives(text, "ExecStartPre")
    assert not _directives(text, "ExecStartPost")
    assert not _directives(text, "ExecReload")
    assert _directives(text, "LoadCredential") == [
        "accepted_locked_commit:/var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker"
    ]
    assert _directives(text, "RuntimeDirectory") == ["ai-crypto-signal-agent"]
    assert _directives(text, "RuntimeDirectoryMode") == ["0750"]
    assert _directives(text, "RuntimeDirectoryPreserve") == ["no"]
    assert "/run/ai-crypto-signal-agent" in _directives(text, "ReadWritePaths")[0].split()
    assert "[Install]" not in text


def test_timer_contract() -> None:
    text = _text(SYSTEMD / "ai-crypto-signal-agent.timer")
    assert _directives(text, "Unit") == ["ai-crypto-signal-agent.service"]
    assert _directives(text, "OnActiveSec") == ["30min"]
    assert _directives(text, "OnUnitInactiveSec") == ["30min"]
    assert _directives(text, "AccuracySec") == ["1min"]
    assert _directives(text, "Persistent") == ["false"]
    assert not _directives(text, "OnBootSec")
    assert not _directives(text, "OnStartupSec")
    assert not _directives(text, "OnUnitActiveSec")


def test_owner_control_unit_contract() -> None:
    text = _text(SYSTEMD / "ai-crypto-signal-agent-telegram-control.service.in")
    assert _directives(text, "Type") == ["simple"]
    assert _directives(text, "Restart") == ["on-failure"]
    assert _directives(text, "RestartSec") == ["5s"]
    assert _directives(text, "RuntimeDirectory") == ["ai-crypto-signal-agent-telegram-control"]
    assert _directives(text, "LoadCredentialEncrypted") == [
        "telegram_bot_token:/etc/credstore.encrypted/telegram_bot_token"
    ]
    assert _directives(text, "ExecStart") == [
        "@@RELEASE_ROOT@@/deploy/operational_v1/bin/"
        "ai-crypto-signal-agent-telegram-control"
    ]
    assert "/usr/local/libexec/ai-crypto-signal-agent-telegram-control" not in text
    assert "WantedBy=multi-user.target" in text


def test_scanner_service_has_no_static_operational_quota_gate() -> None:
    text = _text(SYSTEMD / "ai-crypto-signal-agent.service.in")
    assert "f4-operational-cycle" not in text
    assert "TELEGRAM_QUOTA_LIMIT" not in text
    assert "TELEGRAM_SLOT_CAPACITY" not in text


def test_installer_and_rollback_never_operate_systemd() -> None:
    for name in ("ai-crypto-signal-agent-install", "ai-crypto-signal-agent-rollback"):
        text = _text(BIN / name)
        assert "systemctl " not in text
        assert "daemon-reload" not in text


def test_installer_leaves_runtime_directory_to_systemd() -> None:
    text = _text(BIN / "ai-crypto-signal-agent-install")
    assert "install -d" in text
    assert "/run/ai-crypto-signal-agent" not in text


def test_health_output_does_not_emit_environment_values() -> None:
    text = _text(BIN / "ai-crypto-signal-agent-health")
    assert "cat \"$TELEGRAM_ENV\"" not in text
    assert "cat \"$PROVIDER_ENV\"" not in text
    assert "SECRET_VALUE_EXPOSURE_COUNT=0" in text
    assert "HEALTH_STATUS=%s" in text
    assert "READY_NOT_ENABLED" in text
    assert "READY_AND_AUTOMATION_ENABLED" in text
    assert "HEALTH_STATUS=NOT_READY" in text
    assert re.search(r"\bsystemctl\s+(start|restart|enable|disable|preset)\b", text) is None


def test_trusted_binding_bytes() -> None:
    data = (ROOT / "TRUSTED_CP09_COMMIT").read_bytes()
    assert data == (TRUSTED + "\n").encode("ascii")
    assert hashlib.sha256(data).hexdigest() == TRUSTED_SHA256


def test_retention_is_narrow_and_thirty_days() -> None:
    text = _text(PACKAGE / "tmpfiles.d" / "ai-crypto-signal-agent.conf")
    assert "/var/lib/ai-crypto-signal-agent/operational-artifacts" in text
    assert " 30d " in text
    assert "journald" not in text.lower()


def _make_release(tmp_path: Path) -> Path:
    commit = "a" * 40
    release = tmp_path / commit
    shutil.copytree(ROOT, release, symlinks=True)
    manifest = (
        f"SOURCE_COMMIT={commit}\n"
        f"SOURCE_TREE={'b' * 40}\n"
        f"TRUSTED_CP09_COMMIT={TRUSTED}\n"
    )
    (release / ".f4-release-manifest").write_text(manifest, encoding="ascii")
    lines = []
    for path in sorted(release.rglob("*")):
        if path.is_file() and not path.is_symlink() and path.name != ".f4-sha256-manifest":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(release).as_posix()}\n")
    (release / ".f4-sha256-manifest").write_text("".join(lines), encoding="ascii")
    return release


def _refresh_release_hashes(release: Path) -> None:
    manifest = release / ".f4-sha256-manifest"
    manifest.unlink(missing_ok=True)
    lines = []
    for path in sorted(release.rglob("*")):
        if path.is_file() and not path.is_symlink() and path != manifest:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(release).as_posix()}\n")
    manifest.write_text("".join(lines), encoding="ascii")


def _make_health_fixture(tmp_path: Path) -> tuple[Path, dict[str, str], dict[str, Path]]:
    release = _make_release(tmp_path)
    runtime = tmp_path / "runtime"
    units = tmp_path / "systemd"
    credentials = tmp_path / "credentials"
    fake_bin = tmp_path / "bin"
    for path in (runtime, units, credentials, fake_bin, release / ".f4-rendered"):
        path.mkdir(parents=True, exist_ok=True)

    release_ref = runtime / "installed-release.path"
    marker = runtime / "accepted-locked-commit.marker"
    kill_switch = runtime / "kill-switch.active"
    lock_path = runtime / "operational.lock"
    service = units / "ai-crypto-signal-agent.service"
    timer = units / "ai-crypto-signal-agent.timer"
    control_unit = units / "ai-crypto-signal-agent-telegram-control.service"
    telegram_env = credentials / "phase09r1.env"
    provider_env = credentials / "deepseek.env"
    owner_env = credentials / "owner-control.env"
    control_state = runtime / "telegram-owner-control-state-v1.json"

    release_ref.write_text(f"{release}\n", encoding="ascii")
    marker.write_bytes((TRUSTED + "\n").encode("ascii"))
    service_bytes = (
        SYSTEMD / "ai-crypto-signal-agent.service.in"
    ).read_text(encoding="utf-8").replace("@@RELEASE_ROOT@@", str(release)).replace(
        "@@F4_COMMIT@@", release.name
    ).encode("utf-8")
    service.write_bytes(service_bytes)
    (release / ".f4-rendered/ai-crypto-signal-agent.service").write_bytes(service_bytes)
    timer.write_bytes((SYSTEMD / "ai-crypto-signal-agent.timer").read_bytes())
    control_unit.write_text(
        (SYSTEMD / "ai-crypto-signal-agent-telegram-control.service.in")
        .read_text(encoding="utf-8")
        .replace("@@RELEASE_ROOT@@", str(release)),
        encoding="utf-8",
    )
    telegram_env.write_text(
        "TELEGRAM_BOT_TOKEN=synthetic-token\nTELEGRAM_DESTINATION_ID=synthetic-destination\n",
        encoding="ascii",
    )
    provider_env.write_text("DEEPSEEK_API_KEY=synthetic-provider-key\n", encoding="ascii")
    owner_env.write_text("TELEGRAM_OWNER_USER_ID=100\nTELEGRAM_OWNER_CHAT_ID=200\n", encoding="ascii")
    control_state.write_text(
        '{"last_update_id":-1,"processed_commands":{},"processed_updates":{},"revision":0,'
        '"schema_name":"telegram-owner-control-state","schema_version":1,'
        '"signal_message_bindings":{},"updated_at":"2026-07-28T00:00:00Z"}\n',
        encoding="ascii",
    )
    telegram_env.chmod(0o600)
    provider_env.chmod(0o600)
    owner_env.chmod(0o600)
    control_state.chmod(0o600)

    fake_systemctl = fake_bin / "systemctl"
    fake_systemctl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$1:$2" in
  is-active:ai-crypto-signal-agent-telegram-control.service) printf '%s\\n' "$MOCK_CONTROL_ACTIVE" ;;
  is-enabled:ai-crypto-signal-agent-telegram-control.service) printf '%s\\n' "$MOCK_CONTROL_ENABLED" ;;
  is-active:ai-crypto-signal-agent.service) printf '%s\\n' "$MOCK_SERVICE_ACTIVE" ;;
  is-enabled:ai-crypto-signal-agent.service) printf '%s\\n' "$MOCK_SERVICE_ENABLED" ;;
  is-active:ai-crypto-signal-agent.timer) printf '%s\\n' "$MOCK_TIMER_ACTIVE" ;;
  is-enabled:ai-crypto-signal-agent.timer) printf '%s\\n' "$MOCK_TIMER_ENABLED" ;;
  show:ai-crypto-signal-agent.timer)
    [[ "$*" == *SubState* ]] && printf '%s\\n' "$MOCK_TIMER_SUBSTATE" || exit 64
    ;;
  *) exit 64 ;;
esac
""",
        encoding="utf-8",
    )
    fake_systemctl.chmod(0o755)

    fake_busctl = fake_bin / "busctl"
    fake_busctl.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$5" in
  NextElapseUSecMonotonic)
    [[ "$MOCK_TIMER_NEXT_MONOTONIC" == ABSENT ]] || printf '%s\\n' "$MOCK_TIMER_NEXT_MONOTONIC"
    ;;
  NextElapseUSecRealtime) printf '%s\\n' "$MOCK_TIMER_NEXT_REALTIME" ;;
  *) exit 64 ;;
esac
""",
        encoding="utf-8",
    )
    fake_busctl.chmod(0o755)
    fake_clock = fake_bin / "monotonic-clock"
    fake_clock.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$MOCK_CURRENT_MONOTONIC\"\n",
        encoding="utf-8",
    )
    fake_clock.chmod(0o755)

    health = tmp_path / "ai-crypto-signal-agent-health"
    health_text = _text(BIN / "ai-crypto-signal-agent-health")
    health_text = health_text.replace(
        'readonly SERVICE_USER="ai-crypto-signal-agent"',
        f'readonly SERVICE_USER="{runtime.owner()}"',
    ).replace(
        'readonly SERVICE_GROUP="ai-crypto-signal-agent"',
        f'readonly SERVICE_GROUP="{runtime.group()}"',
    )
    replacements = {
        "/var/lib/ai-crypto-signal-agent/installed-release.path": str(release_ref),
        "/var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker": str(marker),
        "/var/lib/ai-crypto-signal-agent/kill-switch.active": str(kill_switch),
        "/run/ai-crypto-signal-agent/operational.lock": str(lock_path),
        "/etc/systemd/system/ai-crypto-signal-agent.service": str(service),
        "/etc/systemd/system/ai-crypto-signal-agent.timer": str(timer),
        "/etc/ai-crypto-signal-agent/phase09r1.env": str(telegram_env),
        "/etc/ai-crypto-signal-agent/deepseek.env": str(provider_env),
        "/etc/systemd/system/ai-crypto-signal-agent-telegram-control.service": str(control_unit),
        "/etc/ai-crypto-signal-agent/owner-control.env": str(owner_env),
        "/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json": str(control_state),
    }
    for original, replacement in replacements.items():
        health_text = health_text.replace(original, replacement)
    health_text = health_text.replace("/usr/bin/python3", str(fake_clock))
    health.write_text(health_text, encoding="utf-8")
    health.chmod(0o755)

    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "MOCK_SERVICE_ACTIVE": "inactive",
        "MOCK_SERVICE_ENABLED": "static",
        "MOCK_TIMER_ACTIVE": "inactive",
        "MOCK_TIMER_ENABLED": "disabled",
        "MOCK_TIMER_SUBSTATE": "dead",
        "MOCK_CONTROL_ACTIVE": "inactive",
        "MOCK_CONTROL_ENABLED": "disabled",
        "MOCK_TIMER_NEXT_MONOTONIC": "t 18446744073709551615",
        "MOCK_TIMER_NEXT_REALTIME": "t 0",
        "MOCK_CURRENT_MONOTONIC": "1000000000",
    }
    paths = {
        "release": release,
        "manifest": release / ".f4-release-manifest",
        "marker": marker,
        "kill_switch": kill_switch,
        "lock": lock_path,
        "timer": timer,
        "release_timer": release / "deploy/operational_v1/systemd/ai-crypto-signal-agent.timer",
        "control_unit": control_unit,
        "telegram_env": telegram_env,
    }
    return health, environment, paths


def _run_health_case(tmp_path: Path, state: dict[str, str], mutation: str | None = None) -> subprocess.CompletedProcess[str]:
    health, environment, paths = _make_health_fixture(tmp_path)
    environment.update(state)
    if state.get("MOCK_TIMER_ENABLED") == "enabled":
        environment["MOCK_CONTROL_ACTIVE"] = state.get("MOCK_CONTROL_ACTIVE", "active")
        environment["MOCK_CONTROL_ENABLED"] = state.get("MOCK_CONTROL_ENABLED", "enabled")
    held_lock = None
    if mutation == "persistent":
        for path in (paths["timer"], paths["release_timer"]):
            path.write_text(path.read_text().replace("Persistent=false", "Persistent=true"))
    elif mutation == "cadence":
        for path in (paths["timer"], paths["release_timer"]):
            path.write_text(path.read_text().replace("OnUnitInactiveSec=30min", "OnUnitInactiveSec=5min"))
    elif mutation == "release":
        paths["manifest"].write_text(
            paths["manifest"].read_text().replace(f"SOURCE_COMMIT={paths['release'].name}", f"SOURCE_COMMIT={'c' * 40}")
        )
    elif mutation == "marker":
        paths["marker"].write_bytes(("0" * 40 + "\n").encode("ascii"))
    elif mutation == "credential":
        paths["telegram_env"].write_text("TELEGRAM_BOT_TOKEN=\nTELEGRAM_DESTINATION_ID=synthetic\n")
    elif mutation == "kill":
        paths["kill_switch"].write_text("active\n")
    elif mutation == "lock":
        held_lock = paths["lock"].open("w", encoding="ascii")
        paths["lock"].chmod(0o600)
        fcntl.flock(held_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        return subprocess.run(
            [str(health)],
            check=False,
            env=environment,
            text=True,
            capture_output=True,
        )
    finally:
        if held_lock is not None:
            held_lock.close()


def test_health_state_machine_accepts_two_exact_states_and_rejects_partial_states(tmp_path: Path) -> None:
    enabled = {
        "MOCK_TIMER_ACTIVE": "active",
        "MOCK_TIMER_ENABLED": "enabled",
        "MOCK_TIMER_SUBSTATE": "waiting",
        "MOCK_TIMER_NEXT_MONOTONIC": "t 2800000000",
        "MOCK_TIMER_NEXT_REALTIME": "t 0",
        "MOCK_CURRENT_MONOTONIC": "1000000000",
    }
    positive_cases = (
        ("disabled", {}, "READY_NOT_ENABLED"),
        ("enabled_zero_realtime", enabled, "READY_AND_AUTOMATION_ENABLED"),
        ("enabled_both_clocks", {**enabled, "MOCK_TIMER_NEXT_REALTIME": "t 9999999999"}, "READY_AND_AUTOMATION_ENABLED"),
        ("microsecond_boundary", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 1000000001"}, "READY_AND_AUTOMATION_ENABLED"),
    )
    assert len(positive_cases) == 4
    for name, state, expected in positive_cases:
        result = _run_health_case(tmp_path / name, state)
        assert result.returncode == 0, result.stdout + result.stderr
        assert f"HEALTH_STATUS={expected}" in result.stdout

    negative_cases = (
        ("monotonic_zero", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 0"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_MISSING"),
        ("monotonic_absent", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "ABSENT"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_MISSING"),
        ("monotonic_infinite", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 18446744073709551615"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_MISSING"),
        ("monotonic_malformed", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "not-a-number"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_MALFORMED"),
        ("monotonic_equal_now", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 1000000000"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_NOT_IN_FUTURE"),
        ("monotonic_past", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 999999999"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_NOT_IN_FUTURE"),
        ("realtime_only", {**enabled, "MOCK_TIMER_NEXT_MONOTONIC": "t 0", "MOCK_TIMER_NEXT_REALTIME": "t 9999999999"}, None, "TIMER_MONOTONIC_NEXT_ELAPSE_MISSING"),
        ("enabled_inactive", {**enabled, "MOCK_TIMER_ACTIVE": "inactive"}, None, "TIMER_ENABLED_BUT_NOT_ACTIVE"),
        ("active_disabled", {**enabled, "MOCK_TIMER_ENABLED": "disabled"}, None, "TIMER_ACTIVE_BUT_NOT_ENABLED"),
        ("elapsed", {**enabled, "MOCK_TIMER_SUBSTATE": "elapsed"}, None, "TIMER_UNEXPECTED_SUBSTATE"),
        ("failed", {**enabled, "MOCK_TIMER_SUBSTATE": "failed"}, None, "TIMER_UNEXPECTED_SUBSTATE"),
        ("persistent", enabled, "persistent", "TIMER_PERSISTENT_CONTRACT_MISMATCH"),
        ("cadence", enabled, "cadence", "TIMER_CADENCE_MISMATCH"),
        ("service_active", {"MOCK_SERVICE_ACTIVE": "active"}, None, "SERVICE_NOT_INACTIVE"),
        ("release_mismatch", {}, "release", "RELEASE_IDENTITY_MISMATCH"),
        ("marker_mismatch", {}, "marker", "RUNTIME_MARKER_MISMATCH"),
        ("credential_failure", {}, "credential", "CREDENTIAL_READINESS_FAILED"),
        ("kill_switch", {}, "kill", "KILL_SWITCH_ACTIVE"),
        ("overlap_lock", {}, "lock", "OVERLAP_LOCK_RESIDUAL"),
    )
    assert len(negative_cases) == 19
    for name, state, mutation, expected_reason in negative_cases:
        result = _run_health_case(tmp_path / name, state, mutation)
        assert result.returncode != 0, name
        assert "HEALTH_STATUS=NOT_READY" in result.stdout, name
        assert f"HEALTH_REASON={expected_reason}" in result.stdout, result.stdout


def test_health_rejects_scanner_controller_split_release(tmp_path: Path) -> None:
    health, environment, paths = _make_health_fixture(tmp_path)
    old_release = "/opt/ai-crypto-signal-agent-releases/d263fbf2c218db846a46e015f4efbc30a14e4641"
    paths["control_unit"].write_text(
        paths["control_unit"].read_text(encoding="utf-8").replace(
            str(paths["release"]), old_release,
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [str(health)], check=False, env=environment, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "SCANNER_CONTROLLER_RELEASE_PARITY=NO" in result.stdout
    assert "HEALTH_REASON=SCANNER_CONTROLLER_RELEASE_SPLIT" in result.stdout


def test_install_renders_scanner_and_controller_to_same_release(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    destdir = tmp_path / "host"
    subprocess.run(
        [
            str(BIN / "ai-crypto-signal-agent-install"),
            "--release-root", str(release), "--destdir", str(destdir),
        ],
        check=True, text=True, capture_output=True,
    )
    scanner = (
        destdir / "etc/systemd/system/ai-crypto-signal-agent.service"
    ).read_text(encoding="utf-8")
    controller = (
        destdir
        / "etc/systemd/system/ai-crypto-signal-agent-telegram-control.service"
    ).read_text(encoding="utf-8")
    scanner_exec = next(line for line in scanner.splitlines() if line.startswith("ExecStart="))
    controller_exec = next(line for line in controller.splitlines() if line.startswith("ExecStart="))
    assert scanner_exec == (
        f"ExecStart={release}/deploy/operational_v1/bin/ai-crypto-signal-agent-run-once"
    )
    assert controller_exec == (
        f"ExecStart={release}/deploy/operational_v1/bin/ai-crypto-signal-agent-telegram-control"
    )
    assert scanner.count(f"ConditionPathExists={release}/.f4-release-manifest") == 1
    assert controller.count(f"ConditionPathExists={release}/.f4-release-manifest") == 1


def _make_inert_wrapper_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    release = _make_release(tmp_path)
    wrapper = release / "deploy/operational_v1/bin/ai-crypto-signal-agent-run-once"
    lock_path = tmp_path / "runtime" / "operational.lock"
    kill_switch = tmp_path / "runtime" / "kill-switch.active"
    lock_path.parent.mkdir()
    lock_path.parent.chmod(0o750)
    invocation_record = tmp_path / "entrypoint-invocations"
    inert = release / "inert-entrypoint"
    inert.write_text(
        "#!/usr/bin/env bash\nprintf x >> " + str(invocation_record) + "\n",
        encoding="utf-8",
    )
    inert.chmod(0o755)
    text = wrapper.read_text(encoding="utf-8")
    text = text.replace(
        'readonly LOCK_PATH="/run/ai-crypto-signal-agent/operational.lock"',
        f'readonly LOCK_PATH="{lock_path}"',
    )
    text = text.replace(
        'readonly KILL_SWITCH_PATH="/var/lib/ai-crypto-signal-agent/kill-switch.active"',
        f'readonly KILL_SWITCH_PATH="{kill_switch}"',
    )
    text = text.replace(
        'exec /usr/bin/timeout --signal=TERM --kill-after=30s 20m "$PYTHON_BIN" -m engine.run_production_signal_v1',
        'exec "$release_root/inert-entrypoint"',
    )
    wrapper.write_text(text, encoding="utf-8")
    wrapper.chmod(0o755)
    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / "accepted_locked_commit").write_bytes((TRUSTED + "\n").encode("ascii"))
    _refresh_release_hashes(release)
    return wrapper, credentials, lock_path, invocation_record


def test_install_and_rollback_dry_fixture(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    destdir = tmp_path / "host"
    subprocess.run(
        [
            str(BIN / "ai-crypto-signal-agent-install"),
            "--release-root",
            str(release),
            "--destdir",
            str(destdir),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    service = destdir / "etc/systemd/system/ai-crypto-signal-agent.service"
    control_service = (
        destdir
        / "etc/systemd/system/ai-crypto-signal-agent-telegram-control.service"
    )
    copied_control_wrapper = (
        destdir / "usr/local/libexec/ai-crypto-signal-agent-telegram-control"
    )
    historical_host_wrapper = Path(
        "/usr/local/libexec/ai-crypto-signal-agent-telegram-control"
    )
    historical_release_root = historical_host_wrapper.parent.joinpath(
        "../../.."
    ).resolve()
    assert historical_release_root == Path("/")
    assert not (historical_release_root / ".f4-release-manifest").is_file()
    timer = destdir / "etc/systemd/system/ai-crypto-signal-agent.timer"
    marker = destdir / "var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker"
    assert service.is_file()
    assert timer.is_file()
    assert control_service.is_file()
    assert not copied_control_wrapper.exists()
    assert marker.read_bytes() == (TRUSTED + "\n").encode("ascii")
    assert "@@RELEASE_ROOT@@" not in service.read_text()

    release_wrapper = (
        release
        / "deploy/operational_v1/bin/ai-crypto-signal-agent-telegram-control"
    )
    expected_exec_start = f"ExecStart={release_wrapper}"
    control_service_bytes = control_service.read_bytes()
    control_service_text = control_service_bytes.decode("utf-8")
    assert expected_exec_start in control_service_text
    assert "@@RELEASE_ROOT@@" not in control_service_text
    assert (
        "/usr/local/libexec/ai-crypto-signal-agent-telegram-control"
        not in control_service_text
    )
    assert release_wrapper.resolve().parents[3] == release.resolve()
    assert (
        release_wrapper.resolve().parents[3] / ".f4-release-manifest"
    ).is_file()

    subprocess.run(
        [
            str(BIN / "ai-crypto-signal-agent-install"),
            "--release-root",
            str(release),
            "--destdir",
            str(destdir),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert control_service.read_bytes() == control_service_bytes
    assert not copied_control_wrapper.exists()

    backup = tmp_path / "backup"
    backup.mkdir()
    prior_service = b"[Service]\nType=oneshot\n"
    (backup / "ai-crypto-signal-agent.service.before").write_bytes(prior_service)
    os.chmod(backup / "ai-crypto-signal-agent.service.before", 0o644)
    (backup / "host-rollback-state.txt").write_text(
        "\n".join(
            (
                "SERVICE_STATE=PRESENT",
                "CONTROL_SERVICE_STATE=ABSENT",
                "TIMER_STATE=ABSENT",
                "HEALTH_STATE=ABSENT",
                "RETENTION_STATE=ABSENT",
                "MARKER_STATE=ABSENT",
                "RELEASE_REF_STATE=ABSENT",
                "",
            )
        ),
        encoding="ascii",
    )
    subprocess.run(
        [
            str(BIN / "ai-crypto-signal-agent-rollback"),
            "--backup-root",
            str(backup),
            "--destdir",
            str(destdir),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert service.read_bytes() == prior_service
    assert not control_service.exists()
    assert not copied_control_wrapper.exists()
    assert not timer.exists()
    assert not marker.exists()


def test_installation_does_not_create_kill_switch(tmp_path: Path) -> None:
    release = _make_release(tmp_path)
    destdir = tmp_path / "host"
    subprocess.run(
        [
            str(BIN / "ai-crypto-signal-agent-install"),
            "--release-root",
            str(release),
            "--destdir",
            str(destdir),
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert not (destdir / "var/lib/ai-crypto-signal-agent/kill-switch.active").exists()


def test_wrapper_calls_only_inert_entrypoint_exactly_once(tmp_path: Path) -> None:
    wrapper, credentials, _, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    subprocess.run(
        [str(wrapper)],
        check=True,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert invocation_record.read_bytes() == b"x"


def test_wrapper_kill_switch_blocks_before_entrypoint(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    kill_switch = lock_path.parent / "kill-switch.active"
    kill_switch.write_text("active\n", encoding="ascii")
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 75
    assert "KILL_SWITCH_ACTIVE" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_overlap_lock_blocks_before_entrypoint(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    with lock_path.open("w", encoding="ascii") as held:
        lock_path.chmod(0o600)
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(
            [str(wrapper)],
            check=False,
            env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
            text=True,
            capture_output=True,
        )
    assert result.returncode == 75
    assert "OVERLAP_LOCK_HELD" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_reacquires_after_inert_holder_exits(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    with lock_path.open("w", encoding="ascii") as held:
        lock_path.chmod(0o600)
        fcntl.flock(held.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert invocation_record.read_bytes() == b"x"


def test_wrapper_missing_runtime_directory_fails_closed(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    lock_path.parent.rmdir()
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_DIRECTORY" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_rejects_wrong_runtime_directory_owner(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    if os.geteuid() != 0:
        return
    os.chown(lock_path.parent, os.getuid() + 1, os.getgid())
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_DIRECTORY_IDENTITY" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_rejects_wrong_runtime_directory_mode(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    lock_path.parent.chmod(0o550)
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_DIRECTORY_IDENTITY" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_rejects_symlink_lock_path(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    target = tmp_path / "symlink-target"
    target.write_text("unchanged", encoding="ascii")
    lock_path.symlink_to(target)
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_FILE_STATE" in result.stderr
    assert target.read_text(encoding="ascii") == "unchanged"
    assert not invocation_record.exists()


def test_wrapper_rejects_incompatible_existing_lock(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    lock_path.write_text("", encoding="ascii")
    lock_path.chmod(0o600)
    if os.geteuid() == 0:
        os.chown(lock_path, os.getuid() + 1, os.getgid())
    else:
        lock_path.chmod(0o640)
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_FILE_IDENTITY" in result.stderr
    assert not invocation_record.exists()


def test_wrapper_rejects_non_directory_runtime_path(tmp_path: Path) -> None:
    wrapper, credentials, lock_path, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    lock_path.parent.rmdir()
    lock_path.parent.write_text("not-a-directory", encoding="ascii")
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "LOCK_DIRECTORY" in result.stderr
    assert not invocation_record.exists()


def test_health_lock_check_never_creates_lock_file(tmp_path: Path) -> None:
    health, environment, paths = _make_health_fixture(tmp_path)
    result = subprocess.run(
        [str(health)],
        check=False,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OPERATIONAL_LOCK_STATE_VALID=YES" in result.stdout
    assert "OVERLAP_LOCK_RESIDUAL=NO" in result.stdout
    assert not paths["lock"].exists()


def test_wrapper_malformed_marker_fails_closed(tmp_path: Path) -> None:
    wrapper, credentials, _, invocation_record = _make_inert_wrapper_fixture(tmp_path)
    (credentials / "accepted_locked_commit").write_bytes((TRUSTED.upper() + "\n").encode("ascii"))
    result = subprocess.run(
        [str(wrapper)],
        check=False,
        env={**os.environ, "CREDENTIALS_DIRECTORY": str(credentials)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 78
    assert "RUNTIME_MARKER_BYTES" in result.stderr
    assert not invocation_record.exists()


def test_scripts_do_not_contain_enable_or_start_commands() -> None:
    for path in BIN.iterdir():
        text = path.read_text(encoding="utf-8")
        assert re.search(r"\bsystemctl\s+(start|restart|enable|reenable|preset)\b", text) is None
