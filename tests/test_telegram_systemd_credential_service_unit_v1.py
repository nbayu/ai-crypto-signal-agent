"""RED text-only contract for the Phase 12 Telegram systemd credential binding."""
from __future__ import annotations

import ast
from pathlib import Path


_UNIT = Path("deploy/systemd/ai-crypto-signal-agent.service")
_TELEGRAM = "LoadCredentialEncrypted=telegram_bot_token:/etc/credstore.encrypted/telegram_bot_token"
_DEEPSEEK = "LoadCredentialEncrypted=deepseek_api_key:/etc/credstore.encrypted/deepseek_api_key"
_ANTHROPIC = "LoadCredentialEncrypted=anthropic_api_key:/etc/credstore.encrypted/anthropic_api_key"
_EXECSTART = (
    "ExecStart=/opt/ai-crypto-signal-agent/.venv/bin/python "
    "-m engine.phase_12_telegram_credential_aware_executable_v1"
)
_HARDENING = {
    "User": "ai-crypto-signal-agent",
    "Group": "ai-crypto-signal-agent",
    "WorkingDirectory": "/opt/ai-crypto-signal-agent",
    "Restart": "no",
    "UMask": "0027",
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


def _lines() -> list[str]:
    return _UNIT.read_text(encoding="utf-8").splitlines()


def _directives(lines: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for line in lines:
        if not line or line.startswith("[") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result.setdefault(key, []).append(value)
    return result


def test_repository_service_unit_exists_and_is_the_only_inspected_artifact() -> None:
    assert _UNIT.is_file()
    assert _UNIT.as_posix() == "deploy/systemd/ai-crypto-signal-agent.service"


def test_telegram_encrypted_credential_is_a_separate_exact_third_binding() -> None:
    lines = _lines()
    encrypted = [line for line in lines if line.startswith("LoadCredentialEncrypted=")]
    assert lines.count(_TELEGRAM) == 1
    assert encrypted == [_DEEPSEEK, _ANTHROPIC, _TELEGRAM]
    assert all("telegram_bot_token" not in line for line in (_DEEPSEEK, _ANTHROPIC))


def test_existing_provider_encrypted_bindings_are_preserved_exactly_once() -> None:
    lines = _lines()
    assert lines.count(_DEEPSEEK) == 1
    assert lines.count(_ANTHROPIC) == 1
    assert _DEEPSEEK != _ANTHROPIC


def test_no_plain_or_environment_telegram_credential_mechanism_exists() -> None:
    lines = _lines()
    forbidden = (
        "LoadCredential=telegram_bot_token:",
        "Environment=TELEGRAM_BOT_TOKEN=",
        "Environment=BOT_TOKEN=",
        "Environment=TELEGRAM_TOKEN=",
        "EnvironmentFile=",
    )
    assert not any(any(item in line for item in forbidden) for line in lines)


def test_execstart_is_one_direct_shell_free_credential_aware_module_invocation() -> None:
    lines = _lines()
    active = [line for line in lines if line.startswith("ExecStart=")]
    assert active == [_EXECSTART]
    command = active[0]
    forbidden = (
        "phase_12_passive_runtime_launcher_executable_contract_v1",
        "one_shot_telegram_identity_probe_operator_v1",
        "telegram_bot_token",
        "CREDENTIALS_DIRECTORY",
        "TELEGRAM_BOT_TOKEN",
        "BOT_TOKEN",
        "TELEGRAM_TOKEN",
        "bash", "sh ", "|", ">", "<", "tee", "curl", "wget", "$", "`",
    )
    assert not any(item in command for item in forbidden)


def test_existing_service_identity_hardening_and_unit_metadata_are_preserved() -> None:
    directives = _directives(_lines())
    for key, expected in _HARDENING.items():
        assert directives.get(key) == [expected]
    assert directives.get("Description") == ["AI Crypto Signal Agent passive production service"]
    assert directives.get("After") == ["network.target"]
    assert directives.get("WantedBy") == ["multi-user.target"]


def test_contract_test_has_no_systemd_control_credential_or_network_surface() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
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
    assert imported == {"ast", "pathlib", "__future__"}
