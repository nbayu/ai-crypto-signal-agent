from __future__ import annotations

import ast
import builtins
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect

import pytest

import engine.e6_activation_configuration_v1 as module
from engine.e6_activation_configuration_v1 import (
    E6ActivationConfigurationErrorV1,
    E6ActivationConfigurationV1,
    load_e6_activation_configuration_v1,
)


COMMIT = "a" * 40
TREE = "b" * 40
CHECKPOINT = "c" * 40
GATE_KEYS = (
    ("activation_gate", "E6_ACTIVATION_GATE"),
    ("workload_gate", "E6_WORKLOAD_GATE"),
    ("credential_gate", "E6_CREDENTIAL_GATE"),
    ("network_gate", "E6_NETWORK_GATE"),
    ("publication_gate", "E6_PUBLICATION_GATE"),
    ("telegram_publication_gate", "E6_TELEGRAM_PUBLICATION_GATE"),
)


def _mapping(**changes: str) -> dict[str, str]:
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": "e6-activation-configuration-v1",
        "E6_RELEASE_COMMIT": COMMIT,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": CHECKPOINT,
        "E6_RELEASE_ROOT": f"/opt/ai-crypto-signal-agent-releases/{COMMIT}",
        "E6_RELEASE_REFERENCE_PATH": "/var/lib/ai-crypto-signal-agent/e6-installed-release.path",
        "E6_CREDENTIAL_METADATA_PATH": "/etc/ai-crypto-signal-agent/e6-credentials.metadata",
        "E6_OWNER_CONTROL_STATE_PATH": "/var/lib/ai-crypto-signal-agent/phase09r1/owner-blueprint/telegram-owner-control-state-v1.json",
        "E6_SERVICE_USER": "ai-crypto-signal-agent",
        "E6_SERVICE_GROUP": "ai-crypto-signal-agent",
        "E6_RUNTIME_ENABLED": "false",
        "E6_PROVIDER_ENABLED": "false",
        "E6_ACTIVATION_GATE": "false",
        "E6_WORKLOAD_GATE": "false",
        "E6_CREDENTIAL_GATE": "false",
        "E6_NETWORK_GATE": "false",
        "E6_PUBLICATION_GATE": "false",
        "E6_TELEGRAM_PUBLICATION_GATE": "false",
        "E6_AUTOMATIC_RETRY_COUNT": "0",
        "E6_PROVIDER_SUBSTITUTION_ENABLED": "false",
        "E6_PROMPT_REPAIR_ENABLED": "false",
        "E6_STALE_REVIEW_REUSE_ENABLED": "false",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED": "false",
    }
    values.update(changes)
    return values


def _load(**changes: str) -> E6ActivationConfigurationV1:
    return load_e6_activation_configuration_v1(_mapping(**changes))


def test_public_api_is_frozen_slotted_deterministic_and_serializable() -> None:
    assert is_dataclass(E6ActivationConfigurationV1)
    assert E6ActivationConfigurationV1.__dataclass_params__.frozen is True
    assert "__dict__" not in E6ActivationConfigurationV1.__slots__
    value = _load()
    assert list(value.to_mapping()) == [field.name for field in fields(value)]
    assert value.to_mapping() == value.to_mapping()
    with pytest.raises(FrozenInstanceError):
        value.activation_gate = True  # type: ignore[misc]


def test_all_six_gates_are_separate_and_false_by_default() -> None:
    value = _load()
    assert tuple(getattr(value, name) for name, _ in GATE_KEYS) == (False,) * 6
    assert value.e6_runtime_enabled is False
    assert value.provider_enabled is False


@pytest.mark.parametrize("field,key", GATE_KEYS)
def test_each_gate_accepts_exact_true_without_implying_another(
    field: str, key: str,
) -> None:
    value = _load(**{key: "true"})
    assert getattr(value, field) is True
    assert sum(getattr(value, name) for name, _ in GATE_KEYS) == 1
    assert value.e6_runtime_enabled is False
    assert value.provider_enabled is False


@pytest.mark.parametrize(
    "key",
    (
        "E6_RUNTIME_ENABLED",
        "E6_PROVIDER_ENABLED",
        "E6_ACTIVATION_GATE",
        "E6_WORKLOAD_GATE",
        "E6_CREDENTIAL_GATE",
        "E6_NETWORK_GATE",
        "E6_PUBLICATION_GATE",
        "E6_TELEGRAM_PUBLICATION_GATE",
    ),
)
def test_exact_lowercase_boolean_syntax_accepts_true_and_false(key: str) -> None:
    assert load_e6_activation_configuration_v1(_mapping(**{key: "true"})).to_mapping()
    assert load_e6_activation_configuration_v1(_mapping(**{key: "false"})).to_mapping()


@pytest.mark.parametrize("value", ("TRUE", "False", "1", "0", "yes", "", " true"))
def test_permissive_boolean_syntax_is_rejected(value: str) -> None:
    with pytest.raises(E6ActivationConfigurationErrorV1) as raised:
        _load(E6_NETWORK_GATE=value)
    assert raised.value.code in {
        "ACTIVATION_CONFIGURATION_BOOLEAN_INVALID",
        "ACTIVATION_CONFIGURATION_VALUE_INVALID",
    }


def test_missing_unknown_blank_and_conflicting_aliases_fail_closed() -> None:
    missing = _mapping()
    del missing["E6_PUBLICATION_GATE"]
    unknown = _mapping(E6_ENABLE_ALL="true")
    blank = _mapping(E6_RELEASE_TREE="")
    conflicting = _mapping(NETWORK_GATE="true")
    for value in (missing, unknown, blank, conflicting):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            load_e6_activation_configuration_v1(value)


def test_release_checkpoint_and_metadata_paths_are_exactly_validated() -> None:
    value = _load()
    assert value.release_commit == COMMIT
    assert value.release_tree == TREE
    assert value.trusted_checkpoint_commit == CHECKPOINT
    assert value.credential_metadata_path.endswith("e6-credentials.metadata")
    for changes in (
        {"E6_RELEASE_COMMIT": "A" * 40},
        {"E6_RELEASE_TREE": "b" * 39},
        {"E6_RELEASE_ROOT": "/opt/wrong-name"},
        {"E6_CREDENTIAL_METADATA_PATH": "relative/path"},
        {"E6_RELEASE_REFERENCE_PATH": "/var/lib/../tmp/ref"},
        {"E6_SERVICE_USER": "root"},
    ):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            _load(**changes)


def test_credential_metadata_is_never_opened_or_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def forbidden_open(*args: object, **kwargs: object):
        calls.append((args, kwargs))
        raise AssertionError("credential content read")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    value = _load()
    assert value.credential_metadata_path == _mapping()["E6_CREDENTIAL_METADATA_PATH"]
    assert calls == []


def test_safety_invariants_are_fixed_and_independently_enforced() -> None:
    value = _load()
    assert value.automatic_retry_count == 0
    assert value.provider_substitution_enabled is False
    assert value.prompt_repair_enabled is False
    assert value.stale_review_reuse_enabled is False
    assert value.automated_exchange_trading_enabled is False
    for key in (
        "E6_PROVIDER_SUBSTITUTION_ENABLED",
        "E6_PROMPT_REPAIR_ENABLED",
        "E6_STALE_REVIEW_REUSE_ENABLED",
        "E6_AUTOMATED_EXCHANGE_TRADING_ENABLED",
    ):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            _load(**{key: "true"})
    with pytest.raises(E6ActivationConfigurationErrorV1):
        _load(E6_AUTOMATIC_RETRY_COUNT="1")


def test_errors_and_model_have_no_secret_or_client_surface() -> None:
    secret = "fixture-private-" + "provider-value"
    values = _mapping(E6_RELEASE_TREE=secret)
    with pytest.raises(E6ActivationConfigurationErrorV1) as raised:
        load_e6_activation_configuration_v1(values)
    assert secret not in str(raised.value) + repr(raised.value)
    names = {field.name for field in fields(E6ActivationConfigurationV1)}
    assert not names.intersection(
        {
            "token",
            "api_key",
            "credential_value",
            "provider_client",
            "telegram_client",
            "exchange_client",
        }
    )


def test_module_import_and_construction_have_no_external_effect_surface() -> None:
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
        {"os", "socket", "subprocess", "requests", "httpx", "telegram"}
    )
    for marker in (
        "os.environ",
        "getenv(",
        "systemctl",
        "mark_entry_active",
        "reserve_slot",
        "pair_lock",
        "create_order",
    ):
        assert marker not in source
