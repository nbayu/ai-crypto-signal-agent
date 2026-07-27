import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "deploy/systemd/ai-crypto-signal-agent.service.in"
POLICY = ROOT / "docs/PHASE_09R1_MANUAL_ONE_SHOT_OPERATION.md"
RUNTIME_ROOT = "/var/lib/ai-crypto-signal-agent/phase09r1"


def _unit_text():
    return UNIT.read_text(encoding="utf-8")


def _policy_text():
    return POLICY.read_text(encoding="utf-8")


def _directives(text, name):
    prefix = f"{name}="
    return [
        line.strip()[len(prefix):]
        for line in text.splitlines()
        if line.strip().startswith(prefix)
    ]


def test_contract_file_scope_and_no_timer():
    assert UNIT.is_file()
    assert POLICY.is_file()
    assert not list((ROOT / "deploy").rglob("*.timer"))


def test_unit_identity_and_exact_entrypoint():
    text = _unit_text()
    exec_starts = _directives(text, "ExecStart")
    assert exec_starts == [
        "@@PYTHON_BIN@@ -m engine.run_production_signal_v1"
    ]
    assert len(exec_starts) == 1
    assert "phase_10" not in text.lower()
    assert "phase_11" not in text.lower()
    assert "phase_12" not in text.lower()
    assert "/opt/ai-crypto-signal-agent" not in text
    assert "/opt/ai-crypto-signal-agent-phase09r1" not in text


def test_unit_is_manual_oneshot_without_enablement_or_retry():
    text = _unit_text()
    lower = text.lower()
    assert _directives(text, "Type") == ["oneshot"]
    assert _directives(text, "Restart") == ["no"]
    assert "[Install]" not in text
    assert "WantedBy=" not in text
    assert "ExecStartPre=" not in text
    assert "ExecStartPost=" not in text
    assert "RestartSec=" not in text
    assert "StartLimit" not in text
    assert not re.search(r"\b(poll|sleep|while|loop|cron|timer)\b", lower)


def test_runtime_is_external_and_release_is_source_only():
    text = _unit_text()
    assert _directives(text, "WorkingDirectory") == [RUNTIME_ROOT]
    assert _directives(text, "Environment").count(
        f"PRODUCTION_SIGNAL_DIR={RUNTIME_ROOT}/production-signals"
    ) == 1
    assert (
        f"TELEGRAM_QUOTA_STATE_PATH={RUNTIME_ROOT}/quota-slot-state/q.json"
        in _directives(text, "Environment")
    )
    assert (
        f"TELEGRAM_WORKER_STATE_PATH={RUNTIME_ROOT}/quota-slot-state/w.json"
        in _directives(text, "Environment")
    )
    assert _directives(text, "Environment").count(
        "PYTHONPATH=@@RELEASE_ROOT@@"
    ) == 1
    assert "@@RELEASE_ROOT@@" not in "\n".join(
        _directives(text, "ReadWritePaths")
    )
    assert _directives(text, "ReadWritePaths") == [RUNTIME_ROOT]
    assert _directives(text, "ProtectSystem") == ["strict"]


def test_required_runtime_configuration_is_explicit_and_bounded():
    environment = set(_directives(_unit_text(), "Environment"))
    assert "TELEGRAM_QUOTA_LIMIT=1" in environment
    assert "TELEGRAM_SLOT_CAPACITY=1" in environment
    assert "TELEGRAM_WINDOW_ID=phase09r1-manual-one-shot" in environment
    assert "TELEGRAM_MAX_MESSAGE_LENGTH=4000" in environment


def test_credential_files_are_exact_and_not_passed_to_execstart():
    text = _unit_text()
    assert _directives(text, "EnvironmentFile") == [
        "/etc/ai-crypto-signal-agent/phase09r1.env",
        "/etc/ai-crypto-signal-agent/deepseek.env",
    ]
    exec_start = _directives(text, "ExecStart")[0]
    assert "TELEGRAM_BOT_TOKEN" not in text
    assert "TELEGRAM_DESTINATION_ID" not in text
    assert "DEEPSEEK_API_KEY" not in text
    assert "token" not in exec_start.lower()
    assert "destination" not in exec_start.lower()
    assert "api_key" not in exec_start.lower()
    assert not re.search(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b", text)
    assert "Authorization:" not in text
    assert "PRIVATE KEY" not in text


def test_only_authorized_render_placeholders_exist():
    text = _unit_text()
    placeholders = re.findall(r"@@[A-Z0-9_]+@@", text)
    assert set(placeholders) == {"@@PYTHON_BIN@@", "@@RELEASE_ROOT@@"}
    assert placeholders.count("@@PYTHON_BIN@@") == 1
    assert placeholders.count("@@RELEASE_ROOT@@") == 1
    assert _directives(text, "ExecStart")[0].startswith("@@PYTHON_BIN@@ ")
    assert "PYTHONPATH=@@RELEASE_ROOT@@" in _directives(text, "Environment")


def test_rendered_unit_passes_systemd_analyze_verify_when_available(tmp_path):
    analyzer = shutil.which("systemd-analyze")
    if analyzer is None:
        pytest.skip("systemd-analyze is not available on this host")
    release = tmp_path / "immutable-release"
    release.mkdir()
    rendered = (
        _unit_text()
        .replace("@@PYTHON_BIN@@", str(Path(sys.executable).resolve()))
        .replace("@@RELEASE_ROOT@@", str(release.resolve()))
    )
    candidate = tmp_path / "ai-crypto-signal-agent.service"
    candidate.write_text(rendered, encoding="utf-8")
    result = subprocess.run(
        [analyzer, "verify", str(candidate)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"systemd-analyze verify failed with exit code {result.returncode}"
    )


def test_existing_security_hardening_is_preserved():
    text = _unit_text()
    expected = {
        "NoNewPrivileges": "true",
        "PrivateTmp": "true",
        "ProtectSystem": "strict",
        "ProtectHome": "true",
        "ProtectKernelTunables": "true",
        "ProtectKernelModules": "true",
        "ProtectKernelLogs": "true",
        "ProtectControlGroups": "true",
        "RestrictSUIDSGID": "true",
        "LockPersonality": "true",
        "RestrictRealtime": "true",
        "MemoryDenyWriteExecute": "true",
        "RemoveIPC": "true",
        "SystemCallArchitectures": "native",
    }
    for name, value in expected.items():
        assert _directives(text, name) == [value]
    assert _directives(text, "UMask") == ["0077"]


def test_policy_agrees_with_manual_service_contract():
    text = _policy_text()
    lower = text.lower()
    required_phrases = (
        "manual-only one-shot",
        "one bounded production cycle",
        "machine-readable json v1",
        "/etc/ai-crypto-signal-agent/phase09r1.env",
        "/etc/ai-crypto-signal-agent/deepseek.env",
        RUNTIME_ROOT,
        "systemctl start ai-crypto-signal-agent.service",
        "systemctl enable ai-crypto-signal-agent.service",
        "do not retry",
        "phase 12 remains unauthorized",
    )
    for phrase in required_phrases:
        assert phrase.lower() in lower
    for prohibition in (
        "timer",
        "cron",
        "boot enablement",
        "automatic restart",
        "automatic retry",
        "recurring cadence",
        "concurrent invocation",
    ):
        assert prohibition in lower
    assert "@@PYTHON_BIN@@" in text
    assert "@@RELEASE_ROOT@@" in text
