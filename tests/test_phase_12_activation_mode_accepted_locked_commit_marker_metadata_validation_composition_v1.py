"""Contract for the pure inspector-facts-to-validator-metadata adapter."""

from __future__ import annotations

import importlib
import inspect
import sys

import pytest

from engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_inspector_v1 import (
    Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1,
)
from engine import phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1 as validator_boundary
from engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1 import (
    Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1,
    Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1,
    Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1,
)


MODULE_NAME = (
    "engine.phase_12_activation_mode_accepted_locked_commit_marker_"
    "metadata_validation_composition_v1"
)
FUNCTION_NAME = (
    "compose_phase_12_activation_accepted_locked_commit_marker_"
    "metadata_validation_v1"
)
INSPECTION_FACTS = Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1
POLICY = Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1
RESULT = Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1
VALIDATOR_ERROR = Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1
FIELDS = (
    "entry_kind",
    "link_count",
    "owner_uid",
    "group_gid",
    "permission_mode",
    "size_bytes",
)


def inspection_facts(**changes: object) -> INSPECTION_FACTS:
    values: dict[str, object] = {
        "entry_kind": "regular_file",
        "link_count": 1,
        "owner_uid": 1000,
        "group_gid": 1001,
        "permission_mode": 0o640,
        "size_bytes": 17,
    }
    values.update(changes)
    return INSPECTION_FACTS(**values)


def policy(**changes: object) -> POLICY:
    values: dict[str, object] = {
        "expected_owner_uid": 1000,
        "expected_group_gid": 1001,
        "required_permission_mode": 0o640,
        "required_link_count": 1,
        "maximum_size_bytes": 17,
    }
    values.update(changes)
    return POLICY(**values)


def load_module():
    return importlib.import_module(MODULE_NAME)


def compose(module, *, facts: INSPECTION_FACTS, supplied_policy: POLICY):
    return getattr(module, FUNCTION_NAME)(
        inspection_facts=facts,
        policy=supplied_policy,
    )


def load_with_boundaries(monkeypatch, *, metadata_constructor, validator):
    monkeypatch.setattr(
        validator_boundary,
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1",
        metadata_constructor,
    )
    monkeypatch.setattr(
        validator_boundary,
        "validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
        validator,
    )
    monkeypatch.delitem(sys.modules, MODULE_NAME, raising=False)
    return load_module()


def assert_empty_type_error(action) -> None:
    with pytest.raises(TypeError) as caught:
        action()
    assert type(caught.value) is TypeError
    assert caught.value.args == ()
    assert str(caught.value) == ""
    assert repr(caught.value) == "TypeError()"


def test_exact_one_name_public_surface_without_wrapper_or_error() -> None:
    module = load_module()
    assert module.__all__ == (FUNCTION_NAME,)
    assert {name for name in vars(module) if not name.startswith("_")} == {FUNCTION_NAME}
    assert not hasattr(module, "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationCompositionFactsV1")
    assert not hasattr(module, "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationCompositionErrorV1")


def test_exact_keyword_only_signature_and_annotations() -> None:
    module = load_module()
    function = getattr(module, FUNCTION_NAME)
    signature = inspect.signature(function)
    assert tuple(signature.parameters) == ("inspection_facts", "policy")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["inspection_facts"].annotation is INSPECTION_FACTS
    assert signature.parameters["policy"].annotation is POLICY
    assert signature.return_annotation is RESULT
    with pytest.raises(TypeError):
        function(inspection_facts(), policy())
    with pytest.raises(TypeError):
        function(inspection_facts=inspection_facts(), policy=policy(), path="/forbidden")


def test_inspection_facts_wrong_types_are_rejected_before_boundaries(monkeypatch) -> None:
    class FactsSubclass(INSPECTION_FACTS):
        pass

    class Hostile:
        def __getattribute__(self, name: str):
            raise AssertionError(f"unexpected access: {name}")

    def forbidden_constructor(**kwargs):
        raise AssertionError("metadata construction must not occur")

    def forbidden_validator(**kwargs):
        raise AssertionError("validator must not occur")

    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=forbidden_constructor,
        validator=forbidden_validator,
    )
    invalid_values = (
        FactsSubclass(**dict(zip(FIELDS, ("regular_file", 1, 1000, 1001, 0o640, 17)))),
        Hostile(),
        {field: value for field, value in zip(FIELDS, ("regular_file", 1, 1000, 1001, 0o640, 17))},
        ("regular_file", 1, 1000, 1001, 0o640, 17),
        None,
        object(),
    )
    for invalid_value in invalid_values:
        assert_empty_type_error(
            lambda invalid_value=invalid_value: compose(
                module,
                facts=invalid_value,
                supplied_policy=policy(),
            )
        )


def test_policy_wrong_types_are_rejected_before_boundaries(monkeypatch) -> None:
    class PolicySubclass(POLICY):
        pass

    class Hostile:
        def __getattribute__(self, name: str):
            raise AssertionError(f"unexpected access: {name}")

    def forbidden_constructor(**kwargs):
        raise AssertionError("metadata construction must not occur")

    def forbidden_validator(**kwargs):
        raise AssertionError("validator must not occur")

    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=forbidden_constructor,
        validator=forbidden_validator,
    )
    invalid_values = (
        PolicySubclass(),
        Hostile(),
        {"maximum_size_bytes": 17},
        (1000, 1001, 0o640, 1, 17),
        None,
        object(),
    )
    for invalid_value in invalid_values:
        assert_empty_type_error(
            lambda invalid_value=invalid_value: compose(
                module,
                facts=inspection_facts(),
                supplied_policy=invalid_value,
            )
        )


def test_invalid_inspection_facts_take_precedence_over_policy(monkeypatch) -> None:
    def forbidden_constructor(**kwargs):
        raise AssertionError("metadata construction must not occur")

    def forbidden_validator(**kwargs):
        raise AssertionError("validator must not occur")

    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=forbidden_constructor,
        validator=forbidden_validator,
    )
    assert_empty_type_error(
        lambda: compose(module, facts=object(), supplied_policy=object())
    )


def test_constructs_one_metadata_object_with_exact_six_unchanged_fields(monkeypatch) -> None:
    constructed: list[dict[str, object]] = []
    metadata_object = object()
    returned = object()
    supplied_facts = inspection_facts()

    def metadata_constructor(**kwargs):
        constructed.append(kwargs)
        return metadata_object

    def validator(**kwargs):
        assert kwargs == {"metadata": metadata_object, "policy": supplied_policy}
        return returned

    supplied_policy = policy()
    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=metadata_constructor,
        validator=validator,
    )
    assert compose(module, facts=supplied_facts, supplied_policy=supplied_policy) is returned
    assert len(constructed) == 1
    assert tuple(constructed[0]) == FIELDS
    assert constructed[0] == {field: getattr(supplied_facts, field) for field in FIELDS}
    assert supplied_facts == inspection_facts()


def test_passes_original_policy_identity_and_calls_validator_once(monkeypatch) -> None:
    metadata_object = object()
    returned = object()
    calls: list[dict[str, object]] = []
    supplied_policy = policy()

    def metadata_constructor(**kwargs):
        return metadata_object

    def validator(**kwargs):
        calls.append(kwargs)
        return returned

    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=metadata_constructor,
        validator=validator,
    )
    assert compose(module, facts=inspection_facts(), supplied_policy=supplied_policy) is returned
    assert calls == [{"metadata": metadata_object, "policy": supplied_policy}]
    assert calls[0]["policy"] is supplied_policy


def test_returns_hostile_monkeypatched_validator_results_directly(monkeypatch) -> None:
    metadata_object = object()
    supplied_policy = policy()
    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=lambda **kwargs: metadata_object,
        validator=lambda **kwargs: None,
    )
    function = getattr(module, FUNCTION_NAME)
    for result in (object(), None, type("ResultLike", (), {})(), "arbitrary-result"):
        monkeypatch.setattr(module, "_validate", lambda **kwargs: result)
        assert function(inspection_facts=inspection_facts(), policy=supplied_policy) is result


def test_validator_domain_error_propagates_unchanged(monkeypatch) -> None:
    expected = VALIDATOR_ERROR()
    module = load_with_boundaries(
        monkeypatch,
        metadata_constructor=lambda **kwargs: object(),
        validator=lambda **kwargs: (_ for _ in ()).throw(expected),
    )
    with pytest.raises(VALIDATOR_ERROR) as caught:
        compose(module, facts=inspection_facts(), supplied_policy=policy())
    assert caught.value is expected


def test_metadata_constructor_ordinary_and_base_exceptions_propagate(monkeypatch) -> None:
    for expected in (RuntimeError("metadata"), KeyboardInterrupt()):
        module = load_with_boundaries(
            monkeypatch,
            metadata_constructor=lambda **kwargs: (_ for _ in ()).throw(expected),
            validator=lambda **kwargs: (_ for _ in ()).throw(AssertionError("no validator")),
        )
        with pytest.raises(type(expected)) as caught:
            compose(module, facts=inspection_facts(), supplied_policy=policy())
        assert caught.value is expected


def test_validator_ordinary_and_base_exceptions_propagate(monkeypatch) -> None:
    for expected in (RuntimeError("validator"), SystemExit()):
        module = load_with_boundaries(
            monkeypatch,
            metadata_constructor=lambda **kwargs: object(),
            validator=lambda **kwargs: (_ for _ in ()).throw(expected),
        )
        with pytest.raises(type(expected)) as caught:
            compose(module, facts=inspection_facts(), supplied_policy=policy())
        assert caught.value is expected


def test_composition_has_no_metadata_rule_duplication() -> None:
    module = load_module()
    source = inspect.getsource(module)
    for token in (
        "NON_REGULAR_ENTRY",
        "SYMBOLIC_LINK_ENTRY",
        "LINK_COUNT_MISMATCH",
        "OWNER_UID_MISMATCH",
        "GROUP_GID_MISMATCH",
        "PERMISSION_MODE_MISMATCH",
        "MARKER_SIZE_EXCEEDS_MAXIMUM",
    ):
        assert token not in source


def test_composition_does_not_invoke_inspector_or_other_marker_boundaries() -> None:
    module = load_module()
    source = inspect.getsource(module)
    for token in (
        "inspect_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
        "accepted_locked_commit_marker_path_v1",
        "accepted_locked_commit_marker_reader_v1",
        "accepted_locked_commit_marker_parser_v1",
        "authorization_verifier_v1",
        "validation_coordinator_v1",
        "credential_aware_executable_v1",
    ):
        assert token not in source


def test_composition_has_no_filesystem_or_external_effect_surface() -> None:
    module = load_module()
    source = inspect.getsource(module)
    for token in (
        "builtins.open",
        "os.open",
        "os.read",
        "os.close",
        "os.stat",
        "os.lstat",
        "os.readlink",
        "os.scandir",
        "os.listdir",
        "pathlib",
        "subprocess",
        "logging",
        "systemctl",
        "telegram",
        "socket",
        "requests",
        "environ",
        "time.",
        "random",
        "uuid",
        "sleep(",
    ):
        assert token not in source


def test_source_guard_is_precise_and_allows_required_dependency_names() -> None:
    module = load_module()
    source = inspect.getsource(module)
    assert "Phase12ActivationAcceptedLockedCommitMarkerMetadataInspectionFactsV1" in source
    assert "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1" in source
    assert "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1" in source
    assert "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1" in source
    assert "validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1" in source


def test_source_has_no_toctou_or_production_readiness_claim() -> None:
    module = load_module()
    source = inspect.getsource(module).lower()
    for token in (
        "descriptor binding",
        "filesystem continuity",
        "race elimination",
        "secure inspector-reader",
        "authenticity",
        "repository equality",
        "operational authorization",
        "production readiness",
    ):
        assert token not in source


def test_no_composition_owned_policy_source_or_path_api() -> None:
    module = load_module()
    function = getattr(module, FUNCTION_NAME)
    signature = inspect.signature(function)
    assert "path" not in signature.parameters
    assert "policy_source" not in signature.parameters
    assert "configuration" not in signature.parameters
    assert "environment" not in inspect.getsource(module)


def test_contract_test_uses_only_narrow_module_local_boundaries() -> None:
    load_module()
    source = inspect.getsource(sys.modules[__name__])
    forbidden_global_patch = "monkeypatch.setattr(" + "os."
    assert forbidden_global_patch not in source
