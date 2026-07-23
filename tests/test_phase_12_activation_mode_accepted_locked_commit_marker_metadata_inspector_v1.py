"""RED contract for one caller-supplied marker metadata inspection boundary."""
from __future__ import annotations

import errno
import importlib
import inspect
import os
import pathlib
import types
import typing

import pytest


MODULE_NAME = (
    "engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_inspector_v1"
)
FACTS_NAME = "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1"
ERROR_NAME = "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionErrorV1"
INSPECTOR_NAME = "inspect_phase_12_activation_accepted_locked_commit_marker_metadata_v1"
PUBLIC_SURFACE = (FACTS_NAME, ERROR_NAME, INSPECTOR_NAME)
FACT_FIELDS = (
    "entry_kind",
    "link_count",
    "owner_uid",
    "group_gid",
    "permission_mode",
    "size_bytes",
)
ERRORS = {
    "path": "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH",
    "absent": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_ABSENT",
    "denied": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PERMISSION_DENIED",
    "loop": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_SYMBOLIC_LINK_LOOP",
    "not_directory": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_PATH_COMPONENT_NOT_DIRECTORY",
    "filesystem": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_FILESYSTEM_INSPECTION_FAILED",
    "malformed": "ACCEPTED_LOCKED_COMMIT_MARKER_METADATA_MALFORMED_RESULT",
}


def api():
    module = importlib.import_module(MODULE_NAME)
    return (
        getattr(module, FACTS_NAME),
        getattr(module, ERROR_NAME),
        getattr(module, INSPECTOR_NAME),
        module,
    )


def result(
    *,
    mode: int = 0o100640,
    link_count: int = 1,
    owner_uid: int = 0,
    group_gid: int = 987,
    size_bytes: int = 128,
):
    return types.SimpleNamespace(
        st_mode=mode,
        st_nlink=link_count,
        st_uid=owner_uid,
        st_gid=group_gid,
        st_size=size_bytes,
    )


def facts(**changes: object):
    facts_type, _, _, _ = api()
    values: dict[str, object] = {
        "entry_kind": "regular_file",
        "link_count": 1,
        "owner_uid": 0,
        "group_gid": 987,
        "permission_mode": 0o640,
        "size_bytes": 128,
    }
    values.update(changes)
    return facts_type(**values)


def assert_error(action, expected: str) -> None:
    _, error_type, _, _ = api()
    with pytest.raises(error_type) as caught:
        action()
    error = caught.value
    assert str(error) == expected
    assert error.args == (expected,)
    assert repr(error) == f"{ERROR_NAME}()"
    if hasattr(error, "__dict__"):
        assert error.__dict__ == {}


def install_lstat(monkeypatch, outcome):
    module = importlib.import_module(MODULE_NAME)
    calls: list[object] = []

    def fake_lstat(value: object):
        calls.append(value)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("forbidden filesystem effect")

    module_local_os = types.SimpleNamespace(
        lstat=fake_lstat,
        stat=forbidden,
        open=forbidden,
    )
    monkeypatch.setattr(module, "os", module_local_os)
    return calls


def inspect_with(monkeypatch, outcome, path: str = "/controlled/marker"):
    _, _, inspector, _ = api()
    calls = install_lstat(monkeypatch, outcome)
    return inspector(path=path), calls


def test_exact_public_surface_and_signature_are_frozen() -> None:
    facts_type, error_type, inspector, module = api()
    assert module.__all__ == PUBLIC_SURFACE
    assert facts_type.__name__ == FACTS_NAME
    assert error_type.__name__ == ERROR_NAME
    assert inspector.__name__ == INSPECTOR_NAME
    signature = inspect.signature(inspector)
    assert tuple(signature.parameters) == ("path",)
    parameter = signature.parameters["path"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Signature.empty
    hints = typing.get_type_hints(inspector)
    assert hints == {"path": str, "return": facts_type}
    with pytest.raises(TypeError):
        inspector("/controlled/marker")
    with pytest.raises(TypeError):
        inspector()
    with pytest.raises(TypeError):
        inspector(marker_path="/controlled/marker")
    public_callables = {
        name for name, value in vars(module).items() if not name.startswith("_") and callable(value)
    }
    assert public_callables == set(PUBLIC_SURFACE)
    assert not any(
        token in name
        for name in vars(module)
        for token in (
            "canonical",
            "reader",
            "source",
            "validator",
            "authentic",
            "policy",
            "authorization",
        )
    )


def test_facts_model_is_exact_immutable_slotted_keyword_only_and_sanitized() -> None:
    value = facts()
    value_type = type(value)
    signature = inspect.signature(value_type)
    assert tuple(signature.parameters) == FACT_FIELDS
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values())
    assert all(parameter.default is inspect.Signature.empty for parameter in signature.parameters.values())
    assert not hasattr(value, "__dict__")
    assert repr(value) == f"{FACTS_NAME}()"
    assert value == facts()
    assert value.entry_kind == "regular_file"
    assert value.link_count == 1
    assert value.owner_uid == 0
    assert value.group_gid == 987
    assert value.permission_mode == 0o640
    assert value.size_bytes == 128
    for forbidden in (
        "path", "errno", "exception", "inode", "device", "timestamp", "source", "commit", "policy", "authorized",
    ):
        assert not hasattr(value, forbidden)
    with pytest.raises((AttributeError, TypeError)):
        value.size_bytes = 1
    with pytest.raises((AttributeError, TypeError)):
        value.extra = "forbidden"
    with pytest.raises(TypeError):
        value_type(*([0] * len(FACT_FIELDS)))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("entry_kind", "regular"),
        ("entry_kind", b"regular_file"),
        ("link_count", True),
        ("link_count", -1),
        ("owner_uid", 1.0),
        ("group_gid", "1"),
        ("permission_mode", 0o10000),
        ("size_bytes", -1),
    ),
)
def test_facts_constructor_rejects_malformed_primitives(field: str, value: object) -> None:
    assert_error(lambda: facts(**{field: value}), ERRORS["malformed"])


class HostilePath(str):
    calls = {name: 0 for name in ("eq", "hash", "str", "repr", "fspath", "iter", "contains", "len", "lt")}

    @classmethod
    def reset(cls) -> None:
        for key in cls.calls:
            cls.calls[key] = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls["eq"] += 1
        raise AssertionError("path equality")

    def __hash__(self) -> int:
        type(self).calls["hash"] += 1
        raise AssertionError("path hashing")

    def __str__(self) -> str:
        type(self).calls["str"] += 1
        raise AssertionError("path stringification")

    def __repr__(self) -> str:
        type(self).calls["repr"] += 1
        raise AssertionError("path representation")

    def __fspath__(self) -> str:
        type(self).calls["fspath"] += 1
        raise AssertionError("path conversion")

    def __iter__(self):
        type(self).calls["iter"] += 1
        raise AssertionError("path iteration")

    def __contains__(self, item: object) -> bool:
        type(self).calls["contains"] += 1
        raise AssertionError("path containment")

    def __len__(self) -> int:
        type(self).calls["len"] += 1
        raise AssertionError("path length")

    def __lt__(self, other: object) -> bool:
        type(self).calls["lt"] += 1
        raise AssertionError("path comparison")


class HostilePathProxy:
    def __fspath__(self) -> str:
        raise AssertionError("proxy conversion")


class HostileInt(int):
    calls = {name: 0 for name in ("eq", "hash", "int", "index", "lt", "and")}

    @classmethod
    def reset(cls) -> None:
        for key in cls.calls:
            cls.calls[key] = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls["eq"] += 1
        raise AssertionError("integer equality")

    def __hash__(self) -> int:
        type(self).calls["hash"] += 1
        raise AssertionError("integer hash")

    def __int__(self) -> int:
        type(self).calls["int"] += 1
        raise AssertionError("integer conversion")

    def __index__(self) -> int:
        type(self).calls["index"] += 1
        raise AssertionError("integer indexing")

    def __lt__(self, other: object) -> bool:
        type(self).calls["lt"] += 1
        raise AssertionError("integer comparison")

    def __and__(self, other: object) -> int:
        type(self).calls["and"] += 1
        raise AssertionError("integer masking")


def test_hostile_nonexact_paths_are_rejected_without_interaction_or_lstat(monkeypatch) -> None:
    _, _, inspector, _ = api()
    HostilePath.reset()
    calls = install_lstat(monkeypatch, result())
    assert_error(lambda: inspector(path=HostilePath("/controlled/marker")), ERRORS["path"])
    assert HostilePath.calls == {name: 0 for name in HostilePath.calls}
    assert calls == []
    assert_error(lambda: inspector(path=HostilePathProxy()), ERRORS["path"])
    assert calls == []


@pytest.mark.parametrize("value", (None, b"/controlled/marker", pathlib.Path("/controlled/marker"), 1, "", "relative", "a/b", "/bad\x00path"))
def test_invalid_paths_are_rejected_before_lstat(monkeypatch, value: object) -> None:
    _, _, inspector, _ = api()
    calls = install_lstat(monkeypatch, result())
    assert_error(lambda: inspector(path=value), ERRORS["path"])
    assert calls == []


@pytest.mark.parametrize("path", ("//controlled//./marker/../", "/controlled//marker", "/controlled/./marker", "/controlled/part/../marker", "/controlled/marker/"))
def test_absolute_non_normalized_paths_are_passed_verbatim_to_lstat(monkeypatch, path: str) -> None:
    inspected, calls = inspect_with(monkeypatch, result(), path)
    assert inspected == facts()
    assert calls == [path]


def test_only_one_lstat_is_used_with_no_stat_open_or_fallback(monkeypatch) -> None:
    inspected, calls = inspect_with(monkeypatch, result())
    assert inspected == facts()
    assert calls == ["/controlled/marker"]


@pytest.mark.parametrize(
    ("mode", "entry_kind"),
    (
        (0o100640, "regular_file"),
        (0o120777, "symbolic_link"),
        (0o040750, "directory"),
        (0o010640, "other"),
        (0o140640, "other"),
        (0o020640, "other"),
        (0o160640, "other"),
        (0o107777, "regular_file"),
    ),
)
def test_exact_file_type_bitmask_mapping(monkeypatch, mode: int, entry_kind: str) -> None:
    inspected, calls = inspect_with(monkeypatch, result(mode=mode))
    assert inspected.entry_kind == entry_kind
    assert calls == ["/controlled/marker"]


def test_symbolic_link_is_reported_without_following_or_authorization(monkeypatch) -> None:
    inspected, calls = inspect_with(monkeypatch, result(mode=0o120777, size_bytes=19))
    assert inspected.entry_kind == "symbolic_link"
    assert inspected.size_bytes == 19
    assert calls == ["/controlled/marker"]
    assert not hasattr(inspected, "authorized")
    assert not hasattr(inspected, "trusted")


@pytest.mark.parametrize(
    ("mode", "expected"),
    (
        (0o100000, 0o0000),
        (0o100640, 0o0640),
        (0o104000, 0o4000),
        (0o102000, 0o2000),
        (0o101000, 0o1000),
        (0o107777, 0o7777),
        (0o107640, 0o7640),
    ),
)
def test_permission_mode_is_exact_mask(monkeypatch, mode: int, expected: int) -> None:
    inspected, calls = inspect_with(monkeypatch, result(mode=mode))
    assert inspected.permission_mode == expected
    assert calls == ["/controlled/marker"]


def test_link_owner_group_and_size_are_untransformed(monkeypatch) -> None:
    inspected, calls = inspect_with(
        monkeypatch,
        result(link_count=3, owner_uid=44, group_gid=55, size_bytes=0),
    )
    assert inspected.link_count == 3
    assert inspected.owner_uid == 44
    assert inspected.group_gid == 55
    assert inspected.size_bytes == 0
    assert calls == ["/controlled/marker"]


@pytest.mark.parametrize(
    "malformed",
    (
        types.SimpleNamespace(st_nlink=1, st_uid=0, st_gid=0, st_size=0),
        result(mode=True),
        result(link_count=HostileInt(1)),
        result(owner_uid=1.0),
        result(group_gid="1"),
        result(size_bytes=-1),
    ),
)
def test_malformed_metadata_maps_to_fixed_error_without_partial_facts(monkeypatch, malformed) -> None:
    _, _, inspector, _ = api()
    calls = install_lstat(monkeypatch, malformed)
    if isinstance(getattr(malformed, "st_nlink", None), HostileInt):
        HostileInt.reset()
    assert_error(lambda: inspector(path="/controlled/marker"), ERRORS["malformed"])
    assert calls == ["/controlled/marker"]
    if isinstance(getattr(malformed, "st_nlink", None), HostileInt):
        assert HostileInt.calls == {name: 0 for name in HostileInt.calls}


class ExplosiveMetadata:
    @property
    def st_mode(self) -> int:
        raise RuntimeError("unexpected-metadata-access")


@pytest.mark.parametrize(
    ("exception", "expected"),
    (
        (FileNotFoundError("hidden"), ERRORS["absent"]),
        (OSError(errno.ENOENT, "hidden"), ERRORS["absent"]),
        (PermissionError("hidden"), ERRORS["denied"]),
        (OSError(errno.EACCES, "hidden"), ERRORS["denied"]),
        (OSError(errno.EPERM, "hidden"), ERRORS["denied"]),
        (OSError(errno.ELOOP, "hidden"), ERRORS["loop"]),
        (OSError(errno.ENOTDIR, "hidden"), ERRORS["not_directory"]),
        (OSError(errno.EIO, "hidden"), ERRORS["filesystem"]),
    ),
)
def test_expected_filesystem_failures_have_exact_sanitized_mapping(monkeypatch, exception, expected: str) -> None:
    _, _, inspector, _ = api()
    calls = install_lstat(monkeypatch, exception)
    assert_error(lambda: inspector(path="/controlled/marker"), expected)
    assert calls == ["/controlled/marker"]


def test_unexpected_exception_and_base_exceptions_propagate_unchanged(monkeypatch) -> None:
    _, _, inspector, _ = api()
    calls = install_lstat(monkeypatch, RuntimeError("unexpected-lstat"))
    with pytest.raises(RuntimeError, match="^unexpected-lstat$"):
        inspector(path="/controlled/marker")
    assert calls == ["/controlled/marker"]
    calls = install_lstat(monkeypatch, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        inspector(path="/controlled/marker")
    assert calls == ["/controlled/marker"]
    calls = install_lstat(monkeypatch, SystemExit(9))
    with pytest.raises(SystemExit):
        inspector(path="/controlled/marker")
    assert calls == ["/controlled/marker"]
    calls = install_lstat(monkeypatch, BaseException("fatal"))
    with pytest.raises(BaseException, match="^fatal$"):
        inspector(path="/controlled/marker")
    assert calls == ["/controlled/marker"]
    calls = install_lstat(monkeypatch, ExplosiveMetadata())
    with pytest.raises(RuntimeError, match="^unexpected-metadata-access$"):
        inspector(path="/controlled/marker")
    assert calls == ["/controlled/marker"]


def test_validator_separation_disclosure_boundary_and_forbidden_effect_surface(monkeypatch) -> None:
    _, _, inspector, module = api()
    forbidden_names = {
        "validator",
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1",
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1",
        "validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
        "pathlib",
        "subprocess",
        "socket",
        "logging",
        "random",
        "uuid",
        "requests",
        "sys",
        "time",
        "datetime",
        "open",
        "stat",
    }
    assert not forbidden_names.intersection(vars(module))
    assert not any(
        isinstance(value, types.ModuleType)
        and value.__name__ == "engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1"
        for value in vars(module).values()
    )
    inspected, calls = inspect_with(monkeypatch, result())
    assert type(inspected).__name__ == FACTS_NAME
    assert calls == ["/controlled/marker"]
    assert not hasattr(inspected, "source")
    assert not hasattr(inspected, "authorization")
