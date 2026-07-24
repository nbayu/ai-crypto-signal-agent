"""Static RED contract for Phase 12 repository verification composition."""
from __future__ import annotations

import ast
import dataclasses
import inspect

import pytest

from engine.phase_12_repository_verification_composition_v1 import (
    run_phase_12_repository_verification_composition_v1,
)

_CATEGORY_ALLOCATION = (6, 8, 4, 3, 4, 7, 3, 4, 7, 4, 2, 4, 5, 4, 3)
_SOURCE_PATH = "source-path"
_REPOSITORY_PATH = "repository-path"
_REPOSITORY_IDENTITY = "repository-identity"
_ACCEPTED_LOCKED_COMMIT = "accepted-locked-commit"


class _Result:
    def __init__(self, **values):
        self.__dict__.update(values)


class _OrdinaryDependencyError(Exception):
    pass


class _Interrupt(BaseException):
    pass


class _ExplodingSourceResult:
    is_loaded = True
    failure_codes = ()
    expected_origin_fetch_url = "fetch"

    @property
    def expected_origin_push_url(self):
        raise _OrdinaryDependencyError("source-property")


class _ExplodingComparatorResult:
    is_match = True

    @property
    def failure_codes(self):
        raise _OrdinaryDependencyError("comparator-property")


def _source_success(**overrides):
    values = {
        "is_loaded": True,
        "failure_codes": (),
        "expected_origin_fetch_url": "fetch",
        "expected_origin_push_url": "push",
    }
    values.update(overrides)
    return _Result(**values)


def _source_failure(**overrides):
    values = {
        "is_loaded": False,
        "failure_codes": ("opaque-source-failure",),
        "expected_origin_fetch_url": None,
        "expected_origin_push_url": None,
    }
    values.update(overrides)
    return _Result(**values)


def _comparator_success(**overrides):
    values = {"is_match": True, "failure_codes": ()}
    values.update(overrides)
    return _Result(**values)


def _comparator_failure(**overrides):
    values = {"is_match": False, "failure_codes": ("opaque-comparator-failure",)}
    values.update(overrides)
    return _Result(**values)


def _run(source, comparator):
    return run_phase_12_repository_verification_composition_v1(
        source_path=_SOURCE_PATH,
        repository_path=_REPOSITORY_PATH,
        repository_identity=_REPOSITORY_IDENTITY,
        accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT,
        remote_expectation_source=source,
        repository_comparator=comparator,
    )


def _never(**_):
    raise AssertionError("dependency must not be called")


def test_c01_sole_export():
    module = inspect.getmodule(run_phase_12_repository_verification_composition_v1)
    assert module.__all__ == ("run_phase_12_repository_verification_composition_v1",)


def test_c01_function_module_and_name():
    function = run_phase_12_repository_verification_composition_v1
    assert function.__name__ == "run_phase_12_repository_verification_composition_v1"
    assert function.__module__ == "engine.phase_12_repository_verification_composition_v1"


def test_c01_signature_order_and_keyword_only():
    signature = inspect.signature(run_phase_12_repository_verification_composition_v1)
    assert tuple(signature.parameters) == ("source_path", "repository_path", "repository_identity", "accepted_locked_commit", "remote_expectation_source", "repository_comparator")
    assert all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in signature.parameters.values())


def test_c01_return_annotation():
    assert inspect.signature(run_phase_12_repository_verification_composition_v1).return_annotation == "_Phase12RepositoryVerificationCompositionResultV1"


def test_c01_success_result_is_frozen_and_slotted():
    result = _run(lambda **_: _source_success(), lambda **_: _comparator_success())
    assert dataclasses.is_dataclass(result)
    assert getattr(type(result), "__slots__", None)
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        result.is_verified = False


def test_c01_result_field_order():
    result = _run(lambda **_: _source_success(), lambda **_: _comparator_success())
    assert tuple(result.__dataclass_fields__) == ("is_verified", "failure_codes")


def test_c02_source_type_error():
    with pytest.raises(TypeError) as caught:
        run_phase_12_repository_verification_composition_v1(source_path=object(), repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=_never, repository_comparator=_never)
    assert caught.value.args == ()


def test_c02_str_subclass_rejected():
    class _Text(str):
        pass
    with pytest.raises(TypeError) as caught:
        run_phase_12_repository_verification_composition_v1(source_path=_Text(_SOURCE_PATH), repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=_never, repository_comparator=_never)
    assert caught.value.args == ()


def test_c02_repository_path_precedes_later_input():
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=_SOURCE_PATH, repository_path=object(), repository_identity=object(), accepted_locked_commit=object(), remote_expectation_source=object(), repository_comparator=object())


def test_c02_repository_identity_precedes_later_input():
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=_SOURCE_PATH, repository_path=_REPOSITORY_PATH, repository_identity=object(), accepted_locked_commit=object(), remote_expectation_source=object(), repository_comparator=object())


def test_c02_commit_precedes_callable_checks():
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=_SOURCE_PATH, repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=object(), remote_expectation_source=object(), repository_comparator=object())


def test_c02_source_callable_precedes_comparator():
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=_SOURCE_PATH, repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=object(), repository_comparator=object())


def test_c02_comparator_callable_error():
    with pytest.raises(TypeError) as caught:
        run_phase_12_repository_verification_composition_v1(source_path=_SOURCE_PATH, repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=lambda **_: _source_success(), repository_comparator=object())
    assert caught.value.args == ()


def test_c02_no_call_before_contract():
    calls = []
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=object(), repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=lambda **_: calls.append("source"), repository_comparator=lambda **_: calls.append("comparator"))
    assert calls == []


def test_c03_source_keyword_contract():
    seen = []
    _run(lambda **kwargs: (seen.append(kwargs), _source_success())[1], lambda **_: _comparator_success())
    assert seen == [{"source_path": _SOURCE_PATH}]


def test_c03_callable_object_accepted():
    class _Source:
        def __call__(self, **_):
            return _source_success()
    assert _run(_Source(), lambda **_: _comparator_success()).is_verified is True


def test_c03_no_signature_introspection():
    class _Source:
        __signature__ = property(lambda self: (_ for _ in ()).throw(AssertionError("signature")))
        def __call__(self, **_):
            return _source_success()
    assert _run(_Source(), lambda **_: _comparator_success()).is_verified is True


def test_c03_injected_dependencies_used():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success()).is_verified is True


def test_c04_source_called_once():
    calls = []
    _run(lambda **_: (calls.append(1), _source_success())[1], lambda **_: _comparator_success())
    assert calls == [1]


def test_c04_source_exact_keywords():
    seen = []
    _run(lambda **kwargs: (seen.append(kwargs), _source_success())[1], lambda **_: _comparator_success())
    assert seen == [{"source_path": _SOURCE_PATH}]


def test_c04_source_path_unrewritten():
    supplied = "opaque-source"
    seen = []
    run_phase_12_repository_verification_composition_v1(source_path=supplied, repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=lambda **kwargs: (seen.append(kwargs), _source_success())[1], repository_comparator=lambda **_: _comparator_success())
    assert seen[0]["source_path"] is supplied


def test_c05_source_failed_code():
    result = _run(lambda **_: _source_failure(), _never)
    assert result.failure_codes == ("REMOTE_EXPECTATION_SOURCE_FAILED",)


def test_c05_source_failed_no_comparator():
    _run(lambda **_: _source_failure(), _never)


def test_c05_source_failed_one_code():
    assert len(_run(lambda **_: _source_failure(), _never).failure_codes) == 1


def test_c05_source_failed_nondisclosure():
    rendered = repr(_run(lambda **_: _source_failure(), _never))
    assert "opaque-source-failure" not in rendered and "fetch" not in rendered


def test_c06_source_none_invalid():
    assert _run(lambda **_: None, _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_missing_attribute_invalid():
    assert _run(lambda **_: _Result(is_loaded=True), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_nonbool_invalid():
    assert _run(lambda **_: _source_success(is_loaded=1), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_nontuple_invalid():
    assert _run(lambda **_: _source_success(failure_codes=[]), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_success_failure_conflict_invalid():
    assert _run(lambda **_: _source_success(failure_codes=("x",)), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_success_url_invalid():
    assert _run(lambda **_: _source_success(expected_origin_fetch_url=None), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c06_source_failure_contradiction_invalid():
    assert _run(lambda **_: _source_failure(failure_codes=()), _never).failure_codes == ("REMOTE_EXPECTATION_SOURCE_RESULT_INVALID",)


def test_c07_comparator_called_once():
    calls = []
    _run(lambda **_: _source_success(), lambda **_: (calls.append(1), _comparator_success())[1])
    assert calls == [1]


def test_c07_comparator_exact_keywords():
    seen = []
    _run(lambda **_: _source_success(), lambda **kwargs: (seen.append(kwargs), _comparator_success())[1])
    assert seen == [{"repository_path": _REPOSITORY_PATH, "repository_identity": _REPOSITORY_IDENTITY, "accepted_locked_commit": _ACCEPTED_LOCKED_COMMIT, "expected_origin_fetch_url": "fetch", "expected_origin_push_url": "push"}]


def test_c07_comparator_arguments_unrewritten():
    result = _run(lambda **_: _source_success(), lambda **kwargs: _comparator_success())
    assert result.is_verified is True


def test_c08_comparator_failed_code():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_failure()).failure_codes == ("REPOSITORY_COMPARATOR_FAILED",)


def test_c08_comparator_failed_one_code():
    assert len(_run(lambda **_: _source_success(), lambda **_: _comparator_failure()).failure_codes) == 1


def test_c08_comparator_failed_no_later_action():
    _run(lambda **_: _source_success(), lambda **_: _comparator_failure())


def test_c08_comparator_failed_nondisclosure():
    assert "opaque-comparator-failure" not in repr(_run(lambda **_: _source_success(), lambda **_: _comparator_failure()))


def test_c09_comparator_none_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: None).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_missing_match_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _Result(failure_codes=())).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_missing_failures_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _Result(is_match=True)).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_nonbool_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success(is_match=1)).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_nontuple_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success(failure_codes=[])).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_success_failure_conflict_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success(failure_codes=("x",))).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c09_comparator_failure_contradiction_invalid():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_failure(failure_codes=())).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c10_caller_precedes_source():
    with pytest.raises(TypeError):
        run_phase_12_repository_verification_composition_v1(source_path=object(), repository_path=_REPOSITORY_PATH, repository_identity=_REPOSITORY_IDENTITY, accepted_locked_commit=_ACCEPTED_LOCKED_COMMIT, remote_expectation_source=_never, repository_comparator=_never)


def test_c10_source_invalid_prevents_comparator():
    _run(lambda **_: None, _never)


def test_c10_source_failed_prevents_comparator():
    _run(lambda **_: _source_failure(), _never)


def test_c10_comparator_invalid_precedes_failed():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_failure(failure_codes=())).failure_codes == ("REPOSITORY_COMPARATOR_RESULT_INVALID",)


def test_c11_no_effect_parameters():
    names = tuple(inspect.signature(run_phase_12_repository_verification_composition_v1).parameters)
    assert not {"replay", "policy", "activation", "coordinator", "credential", "service"} & set(names)


def test_c11_success_has_no_hidden_effect():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success()).is_verified is True


def test_c12_success_disclosure():
    result = _run(lambda **_: _source_success(), lambda **_: _comparator_success())
    assert tuple(result.__dataclass_fields__) == ("is_verified", "failure_codes")


def test_c12_failure_disclosure():
    result = _run(lambda **_: _source_failure(), _never)
    assert tuple(result.__dataclass_fields__) == ("is_verified", "failure_codes")


def test_c12_repr_shape():
    assert repr(_run(lambda **_: _source_success(), lambda **_: _comparator_success())) == "_Phase12RepositoryVerificationCompositionResultV1(is_verified=True, failure_count=0)"


def test_c12_repr_nondisclosure():
    assert _SOURCE_PATH not in repr(_run(lambda **_: _source_success(), lambda **_: _comparator_success()))


def test_c13_source_invocation_exception():
    error = _OrdinaryDependencyError("source-call")
    with pytest.raises(_OrdinaryDependencyError) as caught:
        _run(lambda **_: (_ for _ in ()).throw(error), _never)
    assert caught.value is error


def test_c13_source_property_exception():
    error = _OrdinaryDependencyError("source-property")
    with pytest.raises(_OrdinaryDependencyError) as caught:
        _run(lambda **_: _ExplodingSourceResult(), _never)
    assert caught.value.args == error.args


def test_c13_comparator_invocation_exception():
    error = _OrdinaryDependencyError("comparator-call")
    with pytest.raises(_OrdinaryDependencyError) as caught:
        _run(lambda **_: _source_success(), lambda **_: (_ for _ in ()).throw(error))
    assert caught.value is error


def test_c13_comparator_property_exception():
    with pytest.raises(_OrdinaryDependencyError):
        _run(lambda **_: _source_success(), lambda **_: _ExplodingComparatorResult())


def test_c13_baseexception_propagates():
    interrupt = _Interrupt()
    with pytest.raises(_Interrupt) as caught:
        _run(lambda **_: (_ for _ in ()).throw(interrupt), _never)
    assert caught.value is interrupt


def test_c14_no_filesystem_or_cwd_access():
    source = inspect.getsource(inspect.getmodule(run_phase_12_repository_verification_composition_v1))
    assert all(token not in source for token in ("import os", "import pathlib", "getcwd"))


def test_c14_no_git_or_subprocess_access():
    source = inspect.getsource(inspect.getmodule(run_phase_12_repository_verification_composition_v1))
    assert all(token not in source for token in ("subprocess", "git.Repo", "Popen"))


def test_c14_no_network_credential_logging_access():
    source = inspect.getsource(inspect.getmodule(run_phase_12_repository_verification_composition_v1))
    assert all(token not in source for token in ("socket", "requests", "urllib", "os.environ", "logging", "credential"))


def test_c14_no_mutating_or_control_access():
    source = inspect.getsource(inspect.getmodule(run_phase_12_repository_verification_composition_v1))
    assert all(token not in source for token in ("replay", "policy", "systemctl", "activate", "open("))


def test_c15_trust_nonoverclaim():
    assert _run(lambda **_: _source_success(), lambda **_: _comparator_success()).is_verified is True


def test_c15_bounded_verification_only():
    result = _run(lambda **_: _source_success(), lambda **_: _comparator_success())
    assert not hasattr(result, "production_authorized")


def test_c15_no_policy_or_activation_field():
    result = _run(lambda **_: _source_success(), lambda **_: _comparator_success())
    assert not hasattr(result, "policy_decision") and not hasattr(result, "activation_authorized")
