"""Contract tests for the pure Phase 12 marker metadata validator."""
from __future__ import annotations

import importlib
import inspect

import pytest


MODULE_NAME = (
    "engine.phase_12_activation_mode_accepted_locked_commit_marker_metadata_validator_v1"
)
ERROR_TEXT = "INVALID_ACCEPTED_LOCKED_COMMIT_MARKER_METADATA"
METADATA_FIELDS = (
    "entry_kind",
    "link_count",
    "owner_uid",
    "group_gid",
    "permission_mode",
    "size_bytes",
)
POLICY_FIELDS = (
    "expected_owner_uid",
    "expected_group_gid",
    "required_permission_mode",
    "required_link_count",
    "maximum_size_bytes",
)
RESULT_FIELDS = ("is_valid", "failure_codes")
FAILURE_CODES = (
    "NON_REGULAR_ENTRY",
    "SYMBOLIC_LINK_ENTRY",
    "LINK_COUNT_MISMATCH",
    "OWNER_UID_MISMATCH",
    "GROUP_GID_MISMATCH",
    "PERMISSION_MODE_MISMATCH",
    "MARKER_SIZE_EXCEEDS_MAXIMUM",
)


def api():
    module = importlib.import_module(MODULE_NAME)
    return (
        module.Phase12ActivationAcceptedLockedCommitMarkerMetadataV1,
        module.Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1,
        module.Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1,
        module.Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1,
        module.validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1,
        module,
    )


def metadata(**changes: object):
    metadata_type, _, _, _, _, _ = api()
    values: dict[str, object] = {
        "entry_kind": "regular_file",
        "link_count": 1,
        "owner_uid": 0,
        "group_gid": 987,
        "permission_mode": 0o640,
        "size_bytes": 128,
    }
    values.update(changes)
    return metadata_type(**values)


def policy(**changes: object):
    _, policy_type, _, _, _, _ = api()
    values: dict[str, object] = {
        "expected_owner_uid": 0,
        "expected_group_gid": 987,
        "required_permission_mode": 0o640,
        "required_link_count": 1,
        "maximum_size_bytes": 128,
    }
    values.update(changes)
    return policy_type(**values)


def validates(*, metadata_value=None, policy_value=None):
    _, _, _, _, validator, _ = api()
    return validator(
        metadata=metadata() if metadata_value is None else metadata_value,
        policy=policy() if policy_value is None else policy_value,
    )


def assert_metadata_error(action) -> None:
    _, _, _, error_type, _, _ = api()
    with pytest.raises(error_type) as caught:
        action()
    assert str(caught.value) == ERROR_TEXT
    assert caught.value.args == (ERROR_TEXT,)
    assert repr(caught.value) == "Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1()"


def test_public_surface_and_keyword_only_validator_are_exact() -> None:
    metadata_type, policy_type, result_type, error_type, validator, module = api()
    assert module.__all__ == (
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1",
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1",
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1",
        "Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1",
        "validate_phase_12_activation_accepted_locked_commit_marker_metadata_v1",
    )
    assert metadata_type.__name__ == module.__all__[0]
    assert policy_type.__name__ == module.__all__[1]
    assert result_type.__name__ == module.__all__[2]
    assert error_type.__name__ == module.__all__[3]
    assert validator.__name__ == module.__all__[4]
    signature = inspect.signature(validator)
    assert tuple(signature.parameters) == ("metadata", "policy")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    with pytest.raises(TypeError):
        validator(metadata(), policy())
    public_callables = {
        name for name, value in vars(module).items()
        if name.startswith("validate_") and callable(value)
    }
    assert public_callables == {validator.__name__}


@pytest.mark.parametrize(
    ("factory", "fields", "sanitized_repr"),
    (
        (metadata, METADATA_FIELDS, "Phase12ActivationAcceptedLockedCommitMarkerMetadataV1()"),
        (policy, POLICY_FIELDS, "Phase12ActivationAcceptedLockedCommitMarkerMetadataPolicyV1()"),
    ),
)
def test_input_models_are_frozen_slotted_keyword_only_and_sanitized(
    factory, fields, sanitized_repr: str
) -> None:
    value = factory()
    value_type = type(value)
    signature = inspect.signature(value_type)
    assert tuple(signature.parameters) == fields
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert not hasattr(value, "__dict__")
    assert repr(value) == sanitized_repr
    assert value == factory()
    with pytest.raises((AttributeError, TypeError)):
        setattr(value, fields[0], "forbidden")
    with pytest.raises((AttributeError, TypeError)):
        setattr(value, "extra", "forbidden")
    with pytest.raises(TypeError):
        value_type(*([0] * len(fields)))


def test_result_model_is_frozen_slotted_tuple_only_and_non_authorizing() -> None:
    _, _, result_type, _, _, _ = api()
    result = result_type(is_valid=False, failure_codes=(FAILURE_CODES[0],))
    signature = inspect.signature(result_type)
    assert tuple(signature.parameters) == RESULT_FIELDS
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert not hasattr(result, "__dict__")
    assert repr(result) == "Phase12ActivationAcceptedLockedCommitMarkerMetadataValidationResultV1()"
    assert result == result_type(is_valid=False, failure_codes=(FAILURE_CODES[0],))
    assert type(result.failure_codes) is tuple
    assert not hasattr(result, "authorized")
    assert not hasattr(result, "source")
    assert not hasattr(result, "path")
    with pytest.raises((AttributeError, TypeError)):
        result.is_valid = True
    with pytest.raises((AttributeError, TypeError)):
        result.extra = "forbidden"
    with pytest.raises(TypeError):
        result_type(False, ())
    assert_metadata_error(lambda: result_type(is_valid=True, failure_codes=[]))


@pytest.mark.parametrize("size", (0, 1, 127, 128))
def test_matching_regular_metadata_is_valid_including_zero_and_maximum_size(size: int) -> None:
    result = validates(metadata_value=metadata(size_bytes=size), policy_value=policy(maximum_size_bytes=128))
    assert result.is_valid is True
    assert result.failure_codes == ()
    assert type(result.failure_codes) is tuple


@pytest.mark.parametrize(
    ("metadata_changes", "policy_changes", "expected"),
    (
        ({"entry_kind": "directory"}, {}, ("NON_REGULAR_ENTRY",)),
        ({"entry_kind": "other"}, {}, ("NON_REGULAR_ENTRY",)),
        ({"entry_kind": "symbolic_link"}, {}, ("NON_REGULAR_ENTRY", "SYMBOLIC_LINK_ENTRY")),
        ({"link_count": 2}, {}, ("LINK_COUNT_MISMATCH",)),
        ({"owner_uid": 1}, {}, ("OWNER_UID_MISMATCH",)),
        ({"group_gid": 1}, {}, ("GROUP_GID_MISMATCH",)),
        ({"permission_mode": 0o600}, {}, ("PERMISSION_MODE_MISMATCH",)),
        ({"size_bytes": 129}, {}, ("MARKER_SIZE_EXCEEDS_MAXIMUM",)),
    ),
)
def test_individual_metadata_failures_have_exact_codes(
    metadata_changes: dict[str, object], policy_changes: dict[str, object], expected: tuple[str, ...]
) -> None:
    result = validates(metadata_value=metadata(**metadata_changes), policy_value=policy(**policy_changes))
    assert result.is_valid is False
    assert result.failure_codes == expected


@pytest.mark.parametrize(
    ("metadata_changes", "policy_changes", "expected"),
    (
        (
            {
                "entry_kind": "symbolic_link",
                "link_count": 2,
                "owner_uid": 1,
                "group_gid": 1,
                "permission_mode": 0o600,
                "size_bytes": 129,
            },
            {},
            FAILURE_CODES,
        ),
        (
            {
                "entry_kind": "directory",
                "link_count": 2,
                "owner_uid": 1,
                "group_gid": 1,
                "permission_mode": 0o600,
                "size_bytes": 129,
            },
            {},
            (
                "NON_REGULAR_ENTRY",
                "LINK_COUNT_MISMATCH",
                "OWNER_UID_MISMATCH",
                "GROUP_GID_MISMATCH",
                "PERMISSION_MODE_MISMATCH",
                "MARKER_SIZE_EXCEEDS_MAXIMUM",
            ),
        ),
        (
            {},
            {
                "expected_owner_uid": 1,
                "expected_group_gid": 1,
                "required_permission_mode": 0o600,
                "required_link_count": 2,
                "maximum_size_bytes": 127,
            },
            (
                "LINK_COUNT_MISMATCH",
                "OWNER_UID_MISMATCH",
                "GROUP_GID_MISMATCH",
                "PERMISSION_MODE_MISMATCH",
                "MARKER_SIZE_EXCEEDS_MAXIMUM",
            ),
        ),
    ),
)
def test_multiple_failures_are_complete_and_in_frozen_order(
    metadata_changes: dict[str, object], policy_changes: dict[str, object], expected: tuple[str, ...]
) -> None:
    result = validates(metadata_value=metadata(**metadata_changes), policy_value=policy(**policy_changes))
    assert result.is_valid is False
    assert result.failure_codes == expected


@pytest.mark.parametrize(
    "value",
    ("regular", "REGULAR_FILE", " regular_file", "regular_file ", b"regular_file", 1, None),
)
def test_entry_kind_requires_exact_frozen_vocabulary(value: object) -> None:
    assert_metadata_error(lambda: metadata(entry_kind=value))


@pytest.mark.parametrize("field", METADATA_FIELDS[1:] + POLICY_FIELDS)
@pytest.mark.parametrize("value", (True, False, -1, "1", 1.0, b"1"))
def test_integer_fields_require_exact_nonnegative_ints(field: str, value: object) -> None:
    if field in METADATA_FIELDS:
        assert_metadata_error(lambda: metadata(**{field: value}))
    else:
        assert_metadata_error(lambda: policy(**{field: value}))


@pytest.mark.parametrize("field", ("permission_mode", "required_permission_mode"))
@pytest.mark.parametrize("value", (0o10000, 0o17777, 0o20000))
def test_permission_modes_allow_only_permission_bits(field: str, value: int) -> None:
    if field == "permission_mode":
        assert_metadata_error(lambda: metadata(permission_mode=value))
    else:
        assert_metadata_error(lambda: policy(required_permission_mode=value))


def test_validator_accepts_only_exact_public_model_instances() -> None:
    metadata_type, policy_type, _, _, validator, _ = api()

    class MetadataDuck:
        entry_kind = "regular_file"
        link_count = 1
        owner_uid = 0
        group_gid = 987
        permission_mode = 0o640
        size_bytes = 128

    class PolicyDuck:
        expected_owner_uid = 0
        expected_group_gid = 987
        required_permission_mode = 0o640
        required_link_count = 1
        maximum_size_bytes = 128

    class MetadataSubclass(metadata_type):
        pass

    class PolicySubclass(policy_type):
        pass

    assert_metadata_error(lambda: validator(metadata=MetadataDuck(), policy=policy()))
    assert_metadata_error(lambda: validator(metadata=metadata(), policy=PolicyDuck()))
    assert_metadata_error(lambda: validator(metadata=MetadataSubclass(), policy=policy()))
    assert_metadata_error(lambda: validator(metadata=metadata(), policy=PolicySubclass()))


def test_error_is_fixed_and_does_not_disclose_synthetic_metadata_evidence() -> None:
    evidence = "synthetic-marker-metadata-evidence"
    _, _, _, error_type, _, _ = api()
    with pytest.raises(error_type) as caught:
        metadata(entry_kind=evidence)
    rendered = str(caught.value) + repr(caught.value)
    assert rendered == ERROR_TEXT + "Phase12ActivationAcceptedLockedCommitMarkerMetadataErrorV1()"
    for forbidden in (evidence, "entry_kind", "owner_uid", "group_gid", "permission_mode", "size_bytes"):
        assert forbidden not in rendered


class HostileString(str):
    calls = {"eq": 0, "hash": 0, "str": 0, "repr": 0, "iter": 0, "contains": 0}

    @classmethod
    def reset(cls) -> None:
        for key in cls.calls:
            cls.calls[key] = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls["eq"] += 1
        raise AssertionError("hostile string equality was invoked")

    def __hash__(self) -> int:
        type(self).calls["hash"] += 1
        raise AssertionError("hostile string hashing was invoked")

    def __str__(self) -> str:
        type(self).calls["str"] += 1
        raise AssertionError("hostile string conversion was invoked")

    def __repr__(self) -> str:
        type(self).calls["repr"] += 1
        raise AssertionError("hostile string representation was invoked")

    def __iter__(self):
        type(self).calls["iter"] += 1
        raise AssertionError("hostile string iteration was invoked")

    def __contains__(self, item: object) -> bool:
        type(self).calls["contains"] += 1
        raise AssertionError("hostile string containment was invoked")


class HostileInt(int):
    calls = {"eq": 0, "lt": 0, "gt": 0, "int": 0, "index": 0}

    @classmethod
    def reset(cls) -> None:
        for key in cls.calls:
            cls.calls[key] = 0

    def __eq__(self, other: object) -> bool:
        type(self).calls["eq"] += 1
        raise AssertionError("hostile integer equality was invoked")

    def __lt__(self, other: object) -> bool:
        type(self).calls["lt"] += 1
        raise AssertionError("hostile integer comparison was invoked")

    def __gt__(self, other: object) -> bool:
        type(self).calls["gt"] += 1
        raise AssertionError("hostile integer comparison was invoked")

    def __int__(self) -> int:
        type(self).calls["int"] += 1
        raise AssertionError("hostile integer conversion was invoked")

    def __index__(self) -> int:
        type(self).calls["index"] += 1
        raise AssertionError("hostile integer indexing was invoked")


def test_hostile_string_subclass_is_rejected_without_primitive_interaction() -> None:
    HostileString.reset()
    assert_metadata_error(lambda: metadata(entry_kind=HostileString("regular_file")))
    assert HostileString.calls == {"eq": 0, "hash": 0, "str": 0, "repr": 0, "iter": 0, "contains": 0}


def test_hostile_integer_subclass_is_rejected_without_primitive_interaction() -> None:
    HostileInt.reset()
    assert_metadata_error(lambda: metadata(link_count=HostileInt(1)))
    assert HostileInt.calls == {"eq": 0, "lt": 0, "gt": 0, "int": 0, "index": 0}


def test_module_has_no_effectful_surface_or_marker_source_semantics() -> None:
    _, _, _, _, _, module = api()
    forbidden_globals = {
        "os", "pathlib", "stat", "subprocess", "socket", "logging", "random", "uuid",
        "requests", "tempfile", "sys", "time", "datetime", "open", "lstat",
    }
    assert not forbidden_globals.intersection(vars(module))
    forbidden_names = {
        "read", "reader", "loader", "locator", "source", "authentic", "repository",
        "policy_composition", "executable", "authorization", "parse_phase_12",
    }
    assert not any(name in vars(module) for name in forbidden_names)
    result = validates()
    assert result.is_valid is True
