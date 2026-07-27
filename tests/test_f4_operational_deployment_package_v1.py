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
        "deployment-package-manifest.txt",
        "monitoring/README.md",
        "systemd/ai-crypto-signal-agent.service.in",
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
    assert "[Install]" not in text


def test_timer_contract() -> None:
    text = _text(SYSTEMD / "ai-crypto-signal-agent.timer")
    assert _directives(text, "Unit") == ["ai-crypto-signal-agent.service"]
    assert _directives(text, "OnUnitInactiveSec") == ["30min"]
    assert _directives(text, "AccuracySec") == ["1min"]
    assert _directives(text, "Persistent") == ["false"]
    assert not _directives(text, "OnBootSec")
    assert not _directives(text, "OnStartupSec")


def test_installer_and_rollback_never_operate_systemd() -> None:
    for name in ("ai-crypto-signal-agent-install", "ai-crypto-signal-agent-rollback"):
        text = _text(BIN / name)
        assert "systemctl " not in text
        assert "daemon-reload" not in text


def test_health_output_does_not_emit_environment_values() -> None:
    text = _text(BIN / "ai-crypto-signal-agent-health")
    assert "cat \"$TELEGRAM_ENV\"" not in text
    assert "cat \"$PROVIDER_ENV\"" not in text
    assert "SECRET_VALUE_EXPOSURE_COUNT=0" in text
    assert "HEALTH_STATUS=READY_NOT_ENABLED" in text


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


def _make_inert_wrapper_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    release = _make_release(tmp_path)
    wrapper = release / "deploy/operational_v1/bin/ai-crypto-signal-agent-run-once"
    lock_path = tmp_path / "runtime" / "operational.lock"
    kill_switch = tmp_path / "runtime" / "kill-switch.active"
    lock_path.parent.mkdir()
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
    timer = destdir / "etc/systemd/system/ai-crypto-signal-agent.timer"
    marker = destdir / "var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker"
    assert service.is_file()
    assert timer.is_file()
    assert marker.read_bytes() == (TRUSTED + "\n").encode("ascii")
    assert "@@RELEASE_ROOT@@" not in service.read_text()

    backup = tmp_path / "backup"
    backup.mkdir()
    prior_service = b"[Service]\nType=oneshot\n"
    (backup / "ai-crypto-signal-agent.service.before").write_bytes(prior_service)
    os.chmod(backup / "ai-crypto-signal-agent.service.before", 0o644)
    (backup / "host-rollback-state.txt").write_text(
        "\n".join(
            (
                "SERVICE_STATE=PRESENT",
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
