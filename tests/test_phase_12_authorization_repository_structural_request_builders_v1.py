"""Substantive RED contract for Phase 12 structural request builders."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import inspect

import engine.phase_12_authorization_repository_validation_composition_v1 as target
from engine.phase_12_authorization_repository_validation_composition_v1 import (
    build_phase_12_authorization_request_v1,
    build_phase_12_authorization_trust_expectations_v1,
    build_phase_12_validation_context_v1,
    build_phase_12_accepted_marker_request_v1,
    build_phase_12_repository_verification_request_v1,
    build_phase_12_replay_request_v1,
    run_phase_12_authorization_repository_validation_composition_v1,
)

_NAMES = (
    "build_phase_12_authorization_request_v1",
    "build_phase_12_authorization_trust_expectations_v1",
    "build_phase_12_validation_context_v1",
    "build_phase_12_accepted_marker_request_v1",
    "build_phase_12_repository_verification_request_v1",
    "build_phase_12_replay_request_v1",
    "run_phase_12_authorization_repository_validation_composition_v1",
)
_BUILDERS = (
    ("authorization", build_phase_12_authorization_request_v1, "_Phase12AuthorizationRequestV1", ("document", "canonical_payload_bytes", "signature_bytes", "activation_mode", "owner_authorization_id", "approval_checkpoint_id", "approved_locked_commit", "approved_at", "expires_at", "accepted_locked_commit_expectation")),
    ("trust", build_phase_12_authorization_trust_expectations_v1, "_Phase12AuthorizationTrustExpectationsV1", ("public_key_path", "expected_public_key_fingerprint", "expected_signing_key_identifier", "revocation_state_path", "expected_revocation_artifact_fingerprint", "expected_revocation_schema_identifier", "expected_revocation_checkpoint_identifier", "expected_environment_identifier", "expected_deployment_identifier")),
    ("context", build_phase_12_validation_context_v1, "_Phase12ValidationContextV1", ("configuration", "now_utc")),
    ("marker", build_phase_12_accepted_marker_request_v1, "_Phase12AcceptedMarkerRequestV1", ("path", "expected_metadata_policy")),
    ("repository", build_phase_12_repository_verification_request_v1, "_Phase12RepositoryVerificationRequestV1", ("source_path", "repository_path")),
    ("replay", build_phase_12_replay_request_v1, "_Phase12ReplayRequestV1", ("path", "expected_schema_identifier", "expected_deployment_identifier")),
)

def _entry(name: str):
    return next(entry for entry in _BUILDERS if entry[0] == name)

def _values(name: str):
    return {field: object() for field in _entry(name)[3]}

def _build(name: str):
    _, builder, _, _ = _entry(name)
    values = _values(name)
    return builder(**values), values

def _signature(name: str):
    return inspect.signature(_entry(name)[1])

def _source(name: str) -> str:
    return inspect.getsource(_entry(name)[1])

def _assert_signature(name: str) -> None:
    signature = _signature(name)
    parameters = tuple(signature.parameters.values())
    assert tuple(parameter.name for parameter in parameters) == _entry(name)[3]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters)
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters)
    assert all(parameter.kind not in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD} for parameter in parameters)
    assert str(signature.return_annotation).strip("'") == "object"

def _assert_type_and_fields(name: str) -> None:
    value, supplied = _build(name)
    assert type(value) is getattr(target, _entry(name)[2])
    assert tuple(field.name for field in fields(value)) == _entry(name)[3]
    assert all(getattr(value, field) is supplied[field] for field in supplied)

def _assert_direct(name: str) -> None:
    source = _source(name)
    assert source.count("return ") == 1
    assert f"return {_entry(name)[2]}(" in source
    assert "if " not in source and "try:" not in source and "except" not in source

def _safe_requests():
    authorization = build_phase_12_authorization_request_v1(document="d", canonical_payload_bytes=b"p", signature_bytes=b"s", activation_mode="m", owner_authorization_id="o", approval_checkpoint_id="c", approved_locked_commit="a", approved_at="t", expires_at="e", accepted_locked_commit_expectation="a")
    trust = build_phase_12_authorization_trust_expectations_v1(public_key_path="p", expected_public_key_fingerprint="f", expected_signing_key_identifier="k", revocation_state_path="r", expected_revocation_artifact_fingerprint="rf", expected_revocation_schema_identifier="rs", expected_revocation_checkpoint_identifier="rc", expected_environment_identifier="env", expected_deployment_identifier="dep")
    context = build_phase_12_validation_context_v1(configuration=object(), now_utc=object())
    marker = build_phase_12_accepted_marker_request_v1(path="m", expected_metadata_policy=object())
    repository = build_phase_12_repository_verification_request_v1(source_path="s", repository_path="r")
    replay = build_phase_12_replay_request_v1(path="p", expected_schema_identifier="schema", expected_deployment_identifier="dep")
    return authorization, trust, context, marker, repository, replay

def _invalid_authorization(**_: object) -> object:
    return object()

def _noop(**_: object) -> object:
    return object()

def _downstream_type_accepts() -> None:
    authorization, trust, context, marker, repository, replay = _safe_requests()
    result = run_phase_12_authorization_repository_validation_composition_v1(authorization_request=authorization, trust_expectations=trust, accepted_marker_request=marker, repository_verification_request=repository, replay_request=replay, validation_context=context, authorization_validation=_invalid_authorization, accepted_marker_composition=_noop, repository_verification_composition=_noop, remote_expectation_source=_noop, repository_comparator=_noop, replay_guard=_noop)
    assert result.failure_codes == ("AUTHORIZATION_VALIDATION_RESULT_INVALID",)

def test_c01_01() -> None:
    assert callable(run_phase_12_authorization_repository_validation_composition_v1)

def test_c01_02() -> None:
    assert run_phase_12_authorization_repository_validation_composition_v1.__name__ == "run_phase_12_authorization_repository_validation_composition_v1"

def test_c01_03() -> None:
    assert len(inspect.signature(run_phase_12_authorization_repository_validation_composition_v1).parameters) == 12

def test_c02_01() -> None:
    assert target.__all__ == _NAMES

def test_c02_02() -> None:
    assert tuple(target.__all__[:6]) == tuple(entry[1].__name__ for entry in _BUILDERS)

def test_c02_03() -> None:
    assert len(target.__all__) == 7 and target.__all__[-1] == run_phase_12_authorization_repository_validation_composition_v1.__name__

def test_c03_01() -> None:
    assert tuple(_signature("authorization").parameters) == _entry("authorization")[3]

def test_c03_02() -> None:
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in _signature("authorization").parameters.values())

def test_c03_03() -> None:
    _assert_signature("authorization")

def test_c04_01() -> None:
    assert tuple(_signature("trust").parameters) == _entry("trust")[3]

def test_c04_02() -> None:
    assert all(p.default is inspect.Parameter.empty for p in _signature("trust").parameters.values())

def test_c04_03() -> None:
    _assert_signature("trust")

def test_c05_01() -> None:
    assert tuple(_signature("context").parameters) == ("configuration", "now_utc")

def test_c05_02() -> None:
    assert str(_signature("context").return_annotation).strip("'") == "object"

def test_c05_03() -> None:
    _assert_signature("context")

def test_c06_01() -> None:
    assert tuple(_signature("marker").parameters) == ("path", "expected_metadata_policy")

def test_c06_02() -> None:
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in _signature("marker").parameters.values())

def test_c06_03() -> None:
    _assert_signature("marker")

def test_c07_01() -> None:
    assert tuple(_signature("repository").parameters) == ("source_path", "repository_path")

def test_c07_02() -> None:
    assert all(p.default is inspect.Parameter.empty for p in _signature("repository").parameters.values())

def test_c07_03() -> None:
    _assert_signature("repository")

def test_c08_01() -> None:
    assert tuple(_signature("replay").parameters) == ("path", "expected_schema_identifier", "expected_deployment_identifier")

def test_c08_02() -> None:
    assert str(_signature("replay").return_annotation).strip("'") == "object"

def test_c08_03() -> None:
    _assert_signature("replay")

def test_c09_01() -> None:
    _assert_type_and_fields("authorization")

def test_c09_02() -> None:
    _assert_type_and_fields("trust")

def test_c09_03() -> None:
    _assert_type_and_fields("context")

def test_c10_01() -> None:
    _assert_type_and_fields("marker")

def test_c10_02() -> None:
    _assert_type_and_fields("repository")

def test_c10_03() -> None:
    _assert_type_and_fields("replay")

def test_c11_01() -> None:
    value, _ = _build("authorization")
    try: value.document = object()
    except FrozenInstanceError as error: assert type(error) is FrozenInstanceError
    else: assert False

def test_c11_02() -> None:
    value, _ = _build("marker")
    assert not hasattr(value, "__dict__")

def test_c11_03() -> None:
    value, _ = _build("replay")
    try: value.path = object()
    except FrozenInstanceError as error: assert type(error) is FrozenInstanceError
    else: assert False

def test_c12_01() -> None:
    _downstream_type_accepts()

def test_c12_02() -> None:
    authorization, trust, context, marker, repository, replay = _safe_requests()
    assert type(authorization) is getattr(target, "_Phase12AuthorizationRequestV1") and type(trust) is getattr(target, "_Phase12AuthorizationTrustExpectationsV1") and type(context) is getattr(target, "_Phase12ValidationContextV1")

def test_c12_03() -> None:
    authorization, trust, context, marker, repository, replay = _safe_requests()
    assert type(marker) is getattr(target, "_Phase12AcceptedMarkerRequestV1") and type(repository) is getattr(target, "_Phase12RepositoryVerificationRequestV1") and type(replay) is getattr(target, "_Phase12ReplayRequestV1")

def test_c13_01() -> None:
    assert "if " not in _source("authorization")

def test_c13_02() -> None:
    assert "if " not in _source("trust") and "if " not in _source("context")

def test_c13_03() -> None:
    assert "if " not in _source("marker") and "if " not in _source("repository") and "if " not in _source("replay")

def test_c14_01() -> None:
    try: build_phase_12_authorization_request_v1()
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c14_02() -> None:
    try: build_phase_12_authorization_trust_expectations_v1()
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c14_03() -> None:
    try: build_phase_12_replay_request_v1()
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c15_01() -> None:
    try: build_phase_12_validation_context_v1(object(), object())
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c15_02() -> None:
    try: build_phase_12_accepted_marker_request_v1(path=object(), expected_metadata_policy=object(), extra=object())
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c15_03() -> None:
    try: build_phase_12_repository_verification_request_v1(object(), repository_path=object())
    except TypeError as error: assert type(error) is TypeError
    else: assert False

def test_c16_01() -> None:
    assert "try:" not in _source("authorization") and "except" not in _source("authorization")

def test_c16_02() -> None:
    assert "try:" not in _source("trust") and "except" not in _source("trust")

def test_c16_03() -> None:
    assert "try:" not in _source("context") and "except" not in _source("context")

def test_c17_01() -> None:
    assert "try:" not in _source("marker") and "except" not in _source("marker")

def test_c17_02() -> None:
    assert "try:" not in _source("repository") and "except" not in _source("repository")

def test_c17_03() -> None:
    assert "try:" not in _source("replay") and "except" not in _source("replay")

def test_c18_01() -> None:
    assert all(not name.startswith("_Phase12") for name in target.__all__)

def test_c18_02() -> None:
    assert not any("Protocol" in name for name in target.__all__)

def test_c18_03() -> None:
    assert not any("Result" in name or "RequestV1" in name for name in target.__all__)

def test_c19_01() -> None:
    source = inspect.getsource(run_phase_12_authorization_repository_validation_composition_v1)
    assert "type(authorization_request) is not _Phase12AuthorizationRequestV1" in source

def test_c19_02() -> None:
    source = inspect.getsource(run_phase_12_authorization_repository_validation_composition_v1)
    assert "type(replay_request) is not _Phase12ReplayRequestV1" in source

def test_c19_03() -> None:
    assert tuple(inspect.signature(run_phase_12_authorization_repository_validation_composition_v1).parameters) == ("authorization_request", "trust_expectations", "accepted_marker_request", "repository_verification_request", "replay_request", "validation_context", "authorization_validation", "accepted_marker_composition", "repository_verification_composition", "remote_expectation_source", "repository_comparator", "replay_guard")

def test_c20_01() -> None:
    assert all(token not in _source("authorization") for token in ("open(", "subprocess", "os.", "Path("))

def test_c20_02() -> None:
    source = _source("trust")
    assert "expected_environment_identifier" in source
    assert all(token not in source for token in ("import os", "os.getenv", "os.environ", "getenv(", "environ["))

def test_c20_03() -> None:
    assert all(token not in _source("replay") for token in ("network", "clock", "service", "telegram"))

def test_c21_01() -> None:
    assert all("Protocol" not in _source(name) for name in ("authorization", "trust", "context"))

def test_c21_02() -> None:
    assert all("class " not in _source(name) for name in ("marker", "repository", "replay"))

def test_c21_03() -> None:
    assert all("bundle" not in _source(name).lower() for name in ("authorization", "trust", "context", "marker", "repository", "replay"))

def test_c22_01() -> None:
    _assert_direct("authorization")

def test_c22_02() -> None:
    _assert_direct("trust")

def test_c22_03() -> None:
    _assert_direct("context")

def test_c23_01() -> None:
    import engine.phase_12_authorization_validation_repository_orchestration_composition_v1 as orchestration
    orchestration_source = inspect.getsource(orchestration)
    downstream_source = inspect.getsource(target)
    assert "run_phase_12_authorization_repository_validation_composition_v1" in orchestration_source
    assert "phase_12_authorization_validation_repository_orchestration_composition_v1" not in downstream_source

def test_c23_02() -> None:
    import engine.phase_12_authorization_validation_repository_orchestration_composition_v1 as orchestration
    assert "build_phase_12_authorization_request_v1" not in inspect.getsource(orchestration)

def test_c23_03() -> None:
    assert "run_phase_12_authorization_repository_validation_composition_v1" in target.__all__

def test_c24_01() -> None:
    value, _ = _build("authorization")
    assert not hasattr(value, "is_validated")

def test_c24_02() -> None:
    value, _ = _build("trust")
    assert not hasattr(value, "is_verified")

def test_c24_03() -> None:
    value, _ = _build("replay")
    assert not hasattr(value, "is_recorded")

def test_c25_01() -> None:
    assert all(_entry(name)[1].__annotations__.get("return") in {object, "object"} for name in ("authorization", "trust", "context", "marker", "repository", "replay"))

def test_c25_02() -> None:
    _assert_direct("marker")

def test_c25_03() -> None:
    _assert_direct("repository")
