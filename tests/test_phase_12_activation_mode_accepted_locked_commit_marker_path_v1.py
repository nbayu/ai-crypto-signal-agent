"""RED contract for the static Phase 12 canonical marker-path value."""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import pathlib
import types
import typing

import pytest


MODULE_NAME = "engine.phase_12_activation_mode_accepted_locked_commit_marker_path_v1"
PATH_TYPE_NAME = "Phase12ActivationAcceptedLockedCommitMarkerPathV1"
GETTER_NAME = "get_phase_12_activation_accepted_locked_commit_marker_path_v1"
PUBLIC_SURFACE = (PATH_TYPE_NAME, GETTER_NAME)
CANONICAL_PATH = "/var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker"


def api():
    module = importlib.import_module(MODULE_NAME)
    return getattr(module, PATH_TYPE_NAME), getattr(module, GETTER_NAME), module


def marker_path():
    path_type, _, _ = api()
    return path_type(path=CANONICAL_PATH)


def test_exact_public_surface_and_zero_argument_getter_are_frozen() -> None:
    path_type, getter, module = api()
    assert module.__all__ == PUBLIC_SURFACE
    assert path_type.__name__ == PATH_TYPE_NAME
    assert getter.__name__ == GETTER_NAME
    signature = inspect.signature(getter)
    assert tuple(signature.parameters) == ()
    hints = typing.get_type_hints(getter)
    assert hints == {"return": path_type}
    with pytest.raises(TypeError):
        getter(None)
    with pytest.raises(TypeError):
        getter(path=CANONICAL_PATH)
    public_callables = {
        name
        for name, value in vars(module).items()
        if not name.startswith("_") and callable(value)
    }
    assert public_callables == set(PUBLIC_SURFACE)
    forbidden_public_tokens = (
        "error",
        "set",
        "override",
        "provider",
        "reader",
        "inspector",
        "validator",
        "parser",
        "source",
        "policy",
        "wire",
        "authoriz",
    )
    assert not any(
        token in name.lower()
        for name in vars(module)
        if not name.startswith("_")
        for token in forbidden_public_tokens
    )


def test_path_model_is_exact_immutable_slotted_keyword_only_and_sanitized() -> None:
    path_type, _, _ = api()
    value = marker_path()
    assert dataclasses.is_dataclass(path_type)
    signature = inspect.signature(path_type)
    assert tuple(signature.parameters) == ("path",)
    parameter = signature.parameters["path"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Signature.empty
    assert tuple(field.name for field in dataclasses.fields(path_type)) == ("path",)
    assert not hasattr(value, "__dict__")
    assert repr(value) == f"{PATH_TYPE_NAME}()"
    assert value == marker_path()
    assert hash(value) == hash(marker_path())
    with pytest.raises((AttributeError, TypeError)):
        value.path = "/other"
    with pytest.raises((AttributeError, TypeError)):
        value.extra = "forbidden"
    with pytest.raises(TypeError):
        path_type(CANONICAL_PATH)


def test_direct_construction_accepts_only_the_exact_canonical_plain_string() -> None:
    path_type, _, _ = api()
    value = path_type(path=CANONICAL_PATH)
    assert type(value) is path_type
    assert type(value.path) is str
    assert value.path == CANONICAL_PATH


@pytest.mark.parametrize(
    "value",
    (
        "",
        "/var/lib/ai-crypto-signal-agent/",
        "/var/lib/ai-crypto-signal-agent/./accepted-locked-commit.marker",
        "/var/lib/ai-crypto-signal-agent/../ai-crypto-signal-agent/accepted-locked-commit.marker",
        "//var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker",
        "/var//lib/ai-crypto-signal-agent/accepted-locked-commit.marker",
        "/var/lib/ai-crypto-signal-agent/accepted-locked-commit.marker\x00",
        "/different/accepted-locked-commit.marker",
    ),
)
def test_every_other_plain_string_is_rejected_without_disclosure(value: str) -> None:
    path_type, _, _ = api()
    with pytest.raises(ValueError) as caught:
        path_type(path=value)
    assert type(caught.value) is ValueError
    assert caught.value.args == ()
    assert str(caught.value) == ""
    assert repr(caught.value) == "ValueError()"
    if value:
        assert value not in str(caught.value)
        assert value not in repr(caught.value)
        assert value not in caught.value.args


@pytest.mark.parametrize(
    "value",
    (None, b"", 0, True, 1.5, pathlib.Path(CANONICAL_PATH), object()),
)
def test_nonexact_string_values_are_type_rejected_without_disclosure(value: object) -> None:
    path_type, _, _ = api()
    with pytest.raises(TypeError) as caught:
        path_type(path=value)
    assert caught.value.args == ()
    assert str(caught.value) == ""
    assert repr(caught.value) == "TypeError()"


def test_hostile_string_subclass_is_rejected_before_arbitrary_interaction() -> None:
    path_type, _, _ = api()
    counters = {name: 0 for name in ("eq", "str", "repr", "hash", "contains", "len")}

    class HostileString(str):
        def __eq__(self, other: object) -> bool:
            counters["eq"] += 1
            raise AssertionError("unexpected equality")

        def __str__(self) -> str:
            counters["str"] += 1
            raise AssertionError("unexpected conversion")

        def __repr__(self) -> str:
            counters["repr"] += 1
            raise AssertionError("unexpected representation")

        def __hash__(self) -> int:
            counters["hash"] += 1
            raise AssertionError("unexpected hashing")

        def __contains__(self, item: object) -> bool:
            counters["contains"] += 1
            raise AssertionError("unexpected containment")

        def __len__(self) -> int:
            counters["len"] += 1
            raise AssertionError("unexpected length")

    with pytest.raises(TypeError) as caught:
        path_type(path=HostileString(CANONICAL_PATH))
    assert caught.value.args == ()
    assert counters == {name: 0 for name in counters}


def test_getter_returns_new_equal_immutable_values_without_state_change() -> None:
    _, getter, module = api()
    before = tuple(vars(module))
    first = getter()
    second = getter()
    assert type(first) is type(second)
    assert first == second
    assert first is not second
    assert hash(first) == hash(second)
    assert first.path == CANONICAL_PATH
    assert second.path == CANONICAL_PATH
    assert tuple(vars(module)) == before


def test_canonical_literal_is_strictly_lexical_without_filesystem_inference() -> None:
    path_type, _, module = api()
    assert type(module._CANONICAL_PATH) is str
    assert module._CANONICAL_PATH == CANONICAL_PATH
    value = path_type(path=module._CANONICAL_PATH)
    assert value.path == CANONICAL_PATH
    assert CANONICAL_PATH.startswith("/")
    assert not CANONICAL_PATH.startswith("//")
    assert "\x00" not in CANONICAL_PATH
    assert not CANONICAL_PATH.endswith("/")
    components = CANONICAL_PATH.split("/")
    assert components[0] == ""
    assert all(component not in ("", ".", "..") for component in components[1:])


def test_private_static_source_has_no_external_dependency_or_mutable_override() -> None:
    _, getter, module = api()
    assert module._CANONICAL_PATH == CANONICAL_PATH
    assert not hasattr(module, "CANONICAL_PATH")
    forbidden_names = (
        "set_path",
        "override",
        "reset",
        "registry",
        "cache",
        "environment",
        "argv",
        "config",
        "credential",
        "provider",
        "network",
        "clock",
        "random",
        "uuid",
        "sleep",
    )
    standard_dunder_metadata = {
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__file__",
        "__cached__",
        "__builtins__",
    }
    assert not any(
        forbidden in name.lower()
        for name in vars(module)
        if name not in standard_dunder_metadata
        for forbidden in forbidden_names
    )
    first = getter()
    second = getter()
    assert first.path == second.path == CANONICAL_PATH


def test_module_source_has_no_forbidden_import_or_effect_surface() -> None:
    _, getter, module = api()
    source = inspect.getsource(module)
    forbidden_fragments = (
        "import os",
        "from os",
        "import pathlib",
        "from pathlib",
        "import subprocess",
        "from subprocess",
        "import logging",
        "from logging",
        "import time",
        "from time",
        "import random",
        "from random",
        "import uuid",
        "from uuid",
        "import socket",
        "from socket",
        "import requests",
        "from requests",
        "environ",
        "sys.argv",
        "l" "stat(",
        "s" "tat(",
        "o" "pen(",
        "read" "link",
        "listdir",
        "scandir",
        "mkdir",
        "makedirs",
        "touch(",
        "unlink(",
        "rmdir(",
        "validator",
        "inspector",
        "parser",
        "authorization",
        "authentic",
        "policy",
        "source",
    )
    assert not any(fragment in source for fragment in forbidden_fragments)
    assert getter().path == CANONICAL_PATH


def test_inspector_parser_validator_reader_and_executable_are_separate() -> None:
    _, _, module = api()
    source = inspect.getsource(module)
    forbidden_modules = (
        "phase_12_activation_mode_accepted_locked_commit_marker_metadata_inspector_v1",
        "phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1",
        "phase_12_activation_mode_accepted_locked_commit_marker_parser_v1",
        "phase_12_activation_mode_authorization_verifier_v1",
        "phase_12_activation_mode_validation_coordinator_v1",
        "phase_12_telegram_credential_aware_executable_v1",
    )
    assert not any(name in source for name in forbidden_modules)
    assert not any(isinstance(value, types.ModuleType) for value in vars(module).values())


def test_no_public_error_or_combined_locator_operation_exists() -> None:
    path_type, getter, module = api()
    assert getter().__class__ is path_type
    forbidden_tokens = (
        "error",
        "inspect",
        "parse",
        "read",
        "source",
        "validate",
        "authoriz",
        "policy",
        "wire",
    )
    assert not any(
        token in name.lower()
        for name in module.__all__
        for token in forbidden_tokens
    )
