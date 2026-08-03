from __future__ import annotations

import ast
import builtins
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect

import pytest

import engine.e6_activation_configuration_v1 as module
from engine.e5_technical_review_payload_v1 import (
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
    E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
)
from engine.e6_activation_configuration_v1 import (
    E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
    E6ActivationConfigurationErrorV1,
    E6ActivationConfigurationV1,
    load_e6_activation_configuration_v1,
)
from engine.e6_deployment_state_binding_v1 import (
    E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
    build_e6_deployment_state_binding_v1,
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


def _mapping(profile: str = "CANDIDATE_CANARY", **changes: str) -> dict[str, str]:
    binding = build_e6_deployment_state_binding_v1(
        deployment_profile=profile, release_commit=COMMIT
    )
    values = {
        "E6_ACTIVATION_SCHEMA_VERSION": E6_ACTIVATION_CONFIGURATION_SCHEMA_V1,
        "E6_DEPLOYMENT_BINDING_VERSION": E6_DEPLOYMENT_STATE_BINDING_VERSION_V1,
        "E6_DEPLOYMENT_PROFILE": binding.deployment_profile.value,
        "E6_RELEASE_COMMIT": binding.release_commit,
        "E6_RELEASE_TREE": TREE,
        "E6_TRUSTED_CHECKPOINT_COMMIT": CHECKPOINT,
        "E6_RELEASE_ROOT": binding.release_root,
        "E6_SERVICE_UNIT": binding.service_unit,
        "E6_TIMER_UNIT": binding.timer_unit,
        "E6_STATE_ROOT": binding.state_root,
        "E6_OWNER_STATE_ROOT": binding.owner_state_root,
        "E6_LEDGER_ROOT": binding.ledger_root,
        "E6_ACTIVE_SIGNAL_LEDGER_PATH": binding.active_ledger_path,
        "E6_OWNER_CONTROL_STATE_PATH": binding.owner_state_path,
        "E6_PUBLICATION_ROOT": binding.publication_root,
        "E6_OPERATIONAL_ARTIFACT_ROOT": binding.operational_artifact_root,
        "E6_RUNTIME_ROOT": binding.runtime_root,
        "E6_RUNTIME_LOCK_PATH": binding.runtime_lock,
        "E6_CACHE_ROOT": binding.cache_root,
        "E6_LOG_POLICY": binding.log_policy,
        "E6_CONTROL_ROOT": binding.control_root,
        "E6_RELEASE_REFERENCE_PATH": binding.install_pointer,
        "E6_ROLLBACK_REFERENCE_PATH": binding.rollback_pointer,
        "E6_ACCEPTED_RELEASE_MARKER_PATH": binding.accepted_marker,
        "E6_KILL_SWITCH_PATH": binding.kill_switch,
        "E6_CONFIGURATION_ROOT": binding.configuration_root,
        "E6_CREDENTIAL_METADATA_PATH": binding.credential_metadata_path,
        "E6_ACTIVATION_CONFIGURATION_PATH": binding.activation_configuration_path,
        "E6_SERVICE_USER": binding.service_user,
        "E6_SERVICE_GROUP": binding.service_group,
        "E6_PROVIDER_BINDING_VERSION": E5_PROVIDER_MODEL_PRICE_BINDING_V4_VERSION,
        "E6_PROVIDER_BINDING_SHA256": E5_PROVIDER_MODEL_PRICE_BINDING_V4_SHA256,
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


def test_public_api_is_frozen_slotted_and_holds_one_binding() -> None:
    assert is_dataclass(E6ActivationConfigurationV1)
    assert E6ActivationConfigurationV1.__dataclass_params__.frozen is True
    assert "__dict__" not in E6ActivationConfigurationV1.__slots__
    value = _load()
    assert list(value.to_mapping()) == [field.name for field in fields(value)]
    assert value.deployment_binding.release_commit == value.release_commit == COMMIT
    assert value.release_root == value.deployment_binding.release_root
    assert value.owner_control_state_path == value.deployment_binding.owner_state_path
    with pytest.raises(FrozenInstanceError):
        value.activation_gate = True  # type: ignore[misc]


def test_exact_45_field_schema_and_all_six_gates_remain_independent() -> None:
    assert len(_mapping()) == 45
    value = _load()
    assert tuple(getattr(value, name) for name, _ in GATE_KEYS) == (False,) * 6
    assert value.e6_runtime_enabled is value.provider_enabled is False
    for field, key in GATE_KEYS:
        selected = _load(**{key: "true"})
        assert getattr(selected, field) is True
        assert sum(getattr(selected, name) for name, _ in GATE_KEYS) == 1


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
def test_boolean_syntax_is_exact_lowercase(key: str) -> None:
    assert load_e6_activation_configuration_v1(_mapping(**{key: "true"}))
    for value in ("TRUE", "False", "1", "yes", " true"):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            load_e6_activation_configuration_v1(_mapping(**{key: value}))


def test_missing_unknown_and_malformed_identity_fail_closed() -> None:
    missing = _mapping()
    del missing["E6_PUBLICATION_GATE"]
    unknown = _mapping(E6_ENABLE_ALL="true")
    for value in (missing, unknown, _mapping(E6_RELEASE_TREE="")):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            load_e6_activation_configuration_v1(value)
    for changes in (
        {"E6_RELEASE_COMMIT": "A" * 40},
        {"E6_RELEASE_TREE": "b" * 39},
        {"E6_TRUSTED_CHECKPOINT_COMMIT": "c" * 39},
        {"E6_DEPLOYMENT_PROFILE": "UNKNOWN"},
    ):
        with pytest.raises(E6ActivationConfigurationErrorV1):
            _load(**changes)


@pytest.mark.parametrize(
    "key",
    (
        "E6_DEPLOYMENT_BINDING_VERSION",
        "E6_RELEASE_ROOT",
        "E6_SERVICE_UNIT",
        "E6_TIMER_UNIT",
        "E6_STATE_ROOT",
        "E6_OWNER_STATE_ROOT",
        "E6_LEDGER_ROOT",
        "E6_ACTIVE_SIGNAL_LEDGER_PATH",
        "E6_OWNER_CONTROL_STATE_PATH",
        "E6_PUBLICATION_ROOT",
        "E6_OPERATIONAL_ARTIFACT_ROOT",
        "E6_RUNTIME_ROOT",
        "E6_RUNTIME_LOCK_PATH",
        "E6_CACHE_ROOT",
        "E6_CONTROL_ROOT",
        "E6_RELEASE_REFERENCE_PATH",
        "E6_ROLLBACK_REFERENCE_PATH",
        "E6_ACCEPTED_RELEASE_MARKER_PATH",
        "E6_KILL_SWITCH_PATH",
        "E6_CONFIGURATION_ROOT",
        "E6_CREDENTIAL_METADATA_PATH",
        "E6_ACTIVATION_CONFIGURATION_PATH",
        "E6_SERVICE_USER",
        "E6_SERVICE_GROUP",
    ),
)
def test_every_detached_binding_field_is_rejected(key: str) -> None:
    with pytest.raises(E6ActivationConfigurationErrorV1) as raised:
        _load(**{key: "/tmp/arbitrary"})
    assert raised.value.code in {
        "ACTIVATION_CONFIGURATION_BINDING_INVALID",
        "ACTIVATION_CONFIGURATION_SERVICE_IDENTITY_INVALID",
    }


def test_profile_path_mismatches_fail_in_both_directions() -> None:
    candidate = _mapping()
    production = _mapping("PRODUCTION")
    candidate["E6_STATE_ROOT"] = production["E6_STATE_ROOT"]
    production["E6_STATE_ROOT"] = _mapping()["E6_STATE_ROOT"]
    for value in (candidate, production):
        with pytest.raises(E6ActivationConfigurationErrorV1) as raised:
            load_e6_activation_configuration_v1(value)
        assert raised.value.code == "ACTIVATION_CONFIGURATION_BINDING_INVALID"


def test_provider_binding_and_fixed_safety_invariants_are_unchanged() -> None:
    value = _load()
    assert value.provider_binding_version == "e5-provider-model-price-binding-v4"
    assert value.provider_binding_sha256 == (
        "4a31dbcb7a0c4daed3215dbe8817002c24b2ead30e7092096c992b322e0fe1d9"
    )
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


def test_credential_metadata_is_metadata_only_and_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def forbidden_open(*args: object, **kwargs: object):
        calls.append((args, kwargs))
        raise AssertionError("credential content read")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    value = _load()
    assert value.credential_metadata_path.endswith("credentials.metadata")
    assert calls == []
    secret = "fixture-private-provider-value"
    with pytest.raises(E6ActivationConfigurationErrorV1) as raised:
        _load(E6_RELEASE_TREE=secret)
    assert secret not in str(raised.value) + repr(raised.value)


def test_module_has_no_external_constructor_or_secret_field_surface() -> None:
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
    names = {field.name for field in fields(E6ActivationConfigurationV1)}
    assert not names.intersection({"api_key", "token", "credential_value"})
    for marker in ("os.environ", "getenv(", "systemctl", "create_order"):
        assert marker not in source
