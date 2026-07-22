"""Contract tests for the pure Phase 12 accepted-commit marker parser."""
from __future__ import annotations

import builtins
import importlib
import importlib.resources
import inspect
import os
import pathlib
import tempfile

import pytest


MODULE_NAME = "engine.phase_12_activation_mode_accepted_locked_commit_marker_parser_v1"
ERROR_TEXT = "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_DOCUMENT"
SCHEMA_VERSION = "phase12-activation-accepted-locked-commit-marker-v1"
COMMIT = "a" * 40
OTHER_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def api():
    module = importlib.import_module(MODULE_NAME)
    return (
        module.Phase12ActivationAcceptedLockedCommitMarkerV1,
        module.Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1,
        module.parse_phase_12_activation_accepted_locked_commit_marker_v1,
        module,
    )


def document(**changes: object) -> str:
    values: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "accepted_locked_commit": COMMIT,
    }
    values.update(changes)
    return "".join(f"{key}={value}\n" for key, value in values.items())


def rejects(value: object) -> None:
    _, error_type, parser, _ = api()
    with pytest.raises(error_type) as caught:
        parser(document=value)
    assert str(caught.value) == ERROR_TEXT
    assert caught.value.args == (ERROR_TEXT,)


def test_public_surface_and_keyword_only_api_are_exact() -> None:
    marker_type, error_type, parser, module = api()
    assert marker_type.__name__ == "Phase12ActivationAcceptedLockedCommitMarkerV1"
    assert error_type.__name__ == "Phase12ActivationAcceptedLockedCommitMarkerDocumentErrorV1"
    assert parser.__name__ == "parse_phase_12_activation_accepted_locked_commit_marker_v1"
    signature = inspect.signature(parser)
    assert tuple(signature.parameters) == ("document",)
    assert signature.parameters["document"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.return_annotation is not inspect.Signature.empty
    parser_names = {
        name for name, value in vars(module).items()
        if name.startswith("parse_") and callable(value)
    }
    assert parser_names == {parser.__name__}
    with pytest.raises(TypeError):
        parser(document())


def test_valid_marker_maps_exactly_to_the_existing_public_marker_type() -> None:
    marker_type, _, parser, _ = api()
    marker = parser(document=document(accepted_locked_commit=OTHER_COMMIT))
    assert type(marker) is marker_type
    assert marker.schema_version == SCHEMA_VERSION
    assert marker.accepted_locked_commit == OTHER_COMMIT
    signature = inspect.signature(marker_type)
    assert tuple(signature.parameters) == (
        "schema_version",
        "accepted_locked_commit",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )


def test_marker_is_frozen_slotted_keyword_only_and_sanitized() -> None:
    marker_type, _, parser, _ = api()
    marker = parser(document=document())
    assert not hasattr(marker, "__dict__")
    assert repr(marker) == "Phase12ActivationAcceptedLockedCommitMarkerV1()"
    with pytest.raises((AttributeError, TypeError)):
        marker.accepted_locked_commit = OTHER_COMMIT
    with pytest.raises((AttributeError, TypeError)):
        marker.extra = "forbidden"
    with pytest.raises(TypeError):
        marker_type(SCHEMA_VERSION, COMMIT)


def test_marker_equality_and_repeat_parsing_are_deterministic_and_non_authorizing() -> None:
    _, _, parser, _ = api()
    first = parser(document=document())
    second = parser(document=document())
    different = parser(document=document(accepted_locked_commit=OTHER_COMMIT))
    assert first == second
    assert first != different
    assert not hasattr(first, "authorized")
    assert not hasattr(first, "policy")
    assert not hasattr(first, "source_path")


@pytest.mark.parametrize(
    "value",
    (
        None,
        b"",
        "",
        document().rstrip("\n"),
        document() + "\n",
        document().replace("\n", "\r\n"),
        document().replace("\n", "\r"),
        "\ufeff" + document(),
        document().replace("accepted_locked_commit=", "accepted_locked_commit=\x00"),
        document().replace("accepted_locked_commit=", "accepted_locked_commit=\x01"),
        "schema_version=" + SCHEMA_VERSION + "\n",
        "\n" + document(),
        document() + "#comment=x\n",
        document() + "unknown=value\n",
    ),
)
def test_document_type_line_and_control_rejections(value: object) -> None:
    rejects(value)


@pytest.mark.parametrize(
    "value",
    (
        document().replace("schema_version=", "Schema_version="),
        document().replace("accepted_locked_commit=", "Accepted_locked_commit="),
        document().replace("schema_version=", "schema_version ="),
        document().replace("accepted_locked_commit=", "accepted_locked_commit ="),
        document().replace("schema_version=" + SCHEMA_VERSION, "schema_version="),
        document().replace("accepted_locked_commit=" + COMMIT, "accepted_locked_commit="),
        document().replace("schema_version=" + SCHEMA_VERSION, "schema_version=" + SCHEMA_VERSION + " "),
        document().replace("accepted_locked_commit=" + COMMIT, "accepted_locked_commit=" + COMMIT + " "),
        document().replace("schema_version=" + SCHEMA_VERSION, "schema_version=" + SCHEMA_VERSION + "=x"),
        document().replace("accepted_locked_commit=" + COMMIT, "accepted_locked_commit=" + COMMIT + "=x"),
        document().replace("schema_version=" + SCHEMA_VERSION + "\naccepted_locked_commit=" + COMMIT, "accepted_locked_commit=" + COMMIT + "\nschema_version=" + SCHEMA_VERSION),
        document().replace("accepted_locked_commit", "schema_version", 1),
    ),
)
def test_schema_order_key_delimiter_and_blank_rejections(value: str) -> None:
    rejects(value)


@pytest.mark.parametrize(
    "version",
    (
        "phase12-activation-accepted-locked-commit-marker-v2",
        "PHASE12-ACTIVATION-ACCEPTED-LOCKED-COMMIT-MARKER-V1",
        "phase12-activation-accepted-locked-commit-marker-v1-extra",
        "x-phase12-activation-accepted-locked-commit-marker-v1",
        "alias",
    ),
)
def test_schema_version_rejections(version: str) -> None:
    rejects(document(schema_version=version))


@pytest.mark.parametrize(
    "commit",
    (
        "a" * 39,
        "a" * 41,
        "A" * 40,
        "g" * 40,
        "sha1:" + "a" * 40,
        "a" * 12,
        " " + "a" * 39,
        "a" * 39 + " ",
        "",
    ),
)
def test_accepted_commit_syntax_rejections(commit: str) -> None:
    rejects(document(accepted_locked_commit=commit))


def test_fixed_error_does_not_disclose_marker_evidence_or_return_partial_output() -> None:
    _, error_type, parser, _ = api()
    evidence = "synthetic-marker-evidence"
    malformed = document(accepted_locked_commit=evidence)
    with pytest.raises(error_type) as caught:
        parser(document=malformed)
    rendered = str(caught.value) + repr(caught.value)
    assert rendered == ERROR_TEXT + repr(caught.value)
    assert evidence not in rendered
    assert "accepted_locked_commit" not in rendered


class HostileString(str):
    def split(self, *args: object, **kwargs: object):
        raise RuntimeError("hostile-marker")


class BaseHostileString(str):
    def split(self, *args: object, **kwargs: object):
        raise KeyboardInterrupt()


def test_unexpected_ordinary_exception_propagates_unchanged() -> None:
    _, _, parser, _ = api()
    with pytest.raises(RuntimeError, match="^hostile-marker$"):
        parser(document=HostileString(document()))


def test_base_exception_propagates_unchanged() -> None:
    _, _, parser, _ = api()
    with pytest.raises(KeyboardInterrupt):
        parser(document=BaseHostileString(document()))


class ForbiddenFilesystemAccess:
    def __call__(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("marker parser attempted filesystem access")


def test_parser_has_no_effectful_surface_source_loader_or_authentication_decision(monkeypatch) -> None:
    marker_type, _, parser, module = api()
    forbidden_globals = {
        "os", "pathlib", "subprocess", "socket", "logging", "random", "uuid",
        "requests", "tempfile", "sys", "time", "datetime",
    }
    assert not forbidden_globals.intersection(vars(module))
    blocked = ForbiddenFilesystemAccess()
    monkeypatch.setattr(builtins, "open", blocked)
    monkeypatch.setattr(os, "open", blocked)
    monkeypatch.setattr(pathlib.Path, "open", blocked)
    monkeypatch.setattr(pathlib.Path, "read_text", blocked)
    monkeypatch.setattr(pathlib.Path, "read_bytes", blocked)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", blocked)
    monkeypatch.setattr(tempfile, "TemporaryFile", blocked)
    monkeypatch.setattr(tempfile, "mkstemp", blocked)
    monkeypatch.setattr(tempfile, "mkdtemp", blocked)
    monkeypatch.setattr(importlib.resources, "files", blocked)
    marker = parser(document=document())
    assert type(marker) is marker_type
    assert not hasattr(marker, "owner")
    assert not hasattr(marker, "permissions")
    assert not hasattr(marker, "authentic")
