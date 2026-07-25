from engine.phase_12_authorization_trust_expectations_v1 import (
    Phase12AuthorizationTrustExpectationsV1,
)

import ast
import dataclasses
import inspect
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_MODULE = "engine.phase_12_authorization_trust_expectations_v1"
_PATH = _ROOT / "engine" / "phase_12_authorization_trust_expectations_v1.py"
_FIELDS = (
    "public_key_path",
    "expected_public_key_fingerprint",
    "expected_signing_key_identifier",
    "revocation_state_path",
    "expected_revocation_artifact_fingerprint",
    "expected_revocation_schema_identifier",
    "expected_revocation_checkpoint_identifier",
    "expected_environment_identifier",
    "expected_deployment_identifier",
)
_COMPOSITION = _ROOT / "engine" / "phase_12_authorization_repository_validation_composition_v1.py"


def _source(path: Path = _PATH) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path = _PATH) -> ast.Module:
    return ast.parse(_source(path))


def _values() -> dict[str, str]:
    return {name: f"value-{index}" for index, name in enumerate(_FIELDS)}


def _make(**changes: str) -> Phase12AuthorizationTrustExpectationsV1:
    values = _values()
    values.update(changes)
    return Phase12AuthorizationTrustExpectationsV1(**values)


def _engine_sources() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in (_ROOT / "engine").glob("*.py")}


def test_c01_01_public_type_has_exact_name():
    assert Phase12AuthorizationTrustExpectationsV1.__name__ == "Phase12AuthorizationTrustExpectationsV1"


def test_c01_02_public_type_is_defined_by_canonical_module():
    assert Phase12AuthorizationTrustExpectationsV1.__module__ == _MODULE


def test_c01_03_public_type_is_not_private():
    assert not Phase12AuthorizationTrustExpectationsV1.__name__.startswith("_")


def test_c02_01_module_all_exports_exact_single_public_type():
    module = inspect.getmodule(Phase12AuthorizationTrustExpectationsV1)
    assert module.__all__ == ("Phase12AuthorizationTrustExpectationsV1",)


def test_c02_02_module_exports_no_builder_adapter_alias_or_wrapper():
    module = inspect.getmodule(Phase12AuthorizationTrustExpectationsV1)
    assert all(token not in " ".join(module.__all__).lower() for token in ("build", "adapter", "alias", "wrapper"))


def test_c02_03_module_has_no_additional_public_surface():
    declarations = [node for node in _tree().body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    assert [node.name for node in declarations] == ["Phase12AuthorizationTrustExpectationsV1"]


def test_c03_01_public_type_has_exact_nine_fields():
    assert len(dataclasses.fields(Phase12AuthorizationTrustExpectationsV1)) == 9


def test_c03_02_public_type_field_names_match_exact_sequence():
    assert tuple(field.name for field in dataclasses.fields(Phase12AuthorizationTrustExpectationsV1)) == _FIELDS


def test_c03_03_public_type_has_no_additional_dataclass_field():
    assert set(Phase12AuthorizationTrustExpectationsV1.__dataclass_fields__) == set(_FIELDS)


def test_c04_01_all_nine_field_annotations_are_exact_str():
    assert Phase12AuthorizationTrustExpectationsV1.__annotations__ == {name: str for name in _FIELDS}


def test_c04_02_annotation_order_matches_field_order():
    assert tuple(Phase12AuthorizationTrustExpectationsV1.__annotations__) == _FIELDS


def test_c04_03_no_field_uses_object_path_mapping_union_or_semantic_wrapper():
    assert all(annotation is str for annotation in Phase12AuthorizationTrustExpectationsV1.__annotations__.values())


def test_c05_01_public_type_is_frozen_dataclass():
    assert Phase12AuthorizationTrustExpectationsV1.__dataclass_params__.frozen is True


def test_c05_02_public_type_is_slotted():
    assert hasattr(Phase12AuthorizationTrustExpectationsV1, "__slots__") and not hasattr(_make(), "__dict__")


def test_c05_03_public_type_constructor_is_keyword_only():
    assert all(parameter.kind is parameter.KEYWORD_ONLY for parameter in inspect.signature(Phase12AuthorizationTrustExpectationsV1).parameters.values())


def test_c06_01_public_type_has_no_field_defaults():
    assert all(field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING for field in dataclasses.fields(Phase12AuthorizationTrustExpectationsV1))


def test_c06_02_public_type_constructor_has_no_variadic_parameters():
    assert all(parameter.kind not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD) for parameter in inspect.signature(Phase12AuthorizationTrustExpectationsV1).parameters.values())


def test_c06_03_direct_construction_is_the_only_public_construction_surface():
    assert all(not name.lower().startswith(("build", "create", "from_", "parse")) for name in vars(inspect.getmodule(Phase12AuthorizationTrustExpectationsV1)) if not name.startswith("_"))


def test_c07_01_reference_fields_preserve_supplied_identity():
    key_path, revocation_path = str("key"), str("revocation")
    value = _make(public_key_path=key_path, revocation_state_path=revocation_path)
    assert value.public_key_path is key_path and value.revocation_state_path is revocation_path


def test_c07_02_expectation_fields_preserve_supplied_identity():
    fingerprint, signing_identifier = str("fingerprint"), str("signer")
    value = _make(expected_public_key_fingerprint=fingerprint, expected_signing_key_identifier=signing_identifier)
    assert value.expected_public_key_fingerprint is fingerprint and value.expected_signing_key_identifier is signing_identifier


def test_c07_03_all_nine_fields_preserve_supplied_identities():
    values = {name: str(f"identity-{index}") for index, name in enumerate(_FIELDS)}
    value = Phase12AuthorizationTrustExpectationsV1(**values)
    assert all(getattr(value, name) is supplied for name, supplied in values.items())


def test_c08_01_equal_field_values_produce_equal_instances():
    assert _make() == _make()


def test_c08_02_different_field_values_produce_unequal_instances():
    assert _make() != _make(expected_deployment_identifier="different")


def test_c08_03_repr_contains_exact_public_type_and_field_names():
    representation = repr(_make())
    assert representation.startswith("Phase12AuthorizationTrustExpectationsV1(") and all(name in representation for name in _FIELDS)


def test_c09_01_missing_required_field_raises_normal_type_error():
    values = _values()
    del values["public_key_path"]
    try: Phase12AuthorizationTrustExpectationsV1(**values)
    except TypeError: return
    raise AssertionError("missing field did not raise TypeError")


def test_c09_02_positional_construction_raises_normal_type_error():
    try: Phase12AuthorizationTrustExpectationsV1(*_values().values())
    except TypeError: return
    raise AssertionError("positional construction did not raise TypeError")


def test_c09_03_unexpected_keyword_raises_normal_type_error():
    try: Phase12AuthorizationTrustExpectationsV1(**_values(), unexpected="value")
    except TypeError: return
    raise AssertionError("unexpected keyword did not raise TypeError")


def test_c10_01_public_type_source_has_no_post_init_or_validation():
    assert all(token not in _source() for token in ("__post_init__", "validate", "_require"))


def test_c10_02_public_type_source_has_no_coercion_normalization_or_parsing():
    assert all(token not in _source().lower() for token in ("str(", "coerc", "normaliz", "parse"))


def test_c10_03_unusual_str_subclass_values_are_stored_unchanged():
    class UnusualString(str):
        __slots__ = ()
    supplied = UnusualString("unusual")
    assert _make(public_key_path=supplied).public_key_path is supplied


def test_c11_01_canonical_module_has_no_filesystem_or_path_access():
    assert all(token not in _source() for token in ("Path(", "open(", ".read_", ".resolve("))


def test_c11_02_canonical_module_has_no_key_revocation_repository_or_marker_access():
    assert all(token not in _source().lower() for token in ("load_", "repository", "marker", "read_text"))


def test_c11_03_construction_does_not_open_resolve_or_inspect_reference_values():
    assert all(token not in inspect.getsource(Phase12AuthorizationTrustExpectationsV1) for token in ("open(", "resolve(", "exists(", "stat("))


def test_c12_01_canonical_module_imports_only_standard_library_dataclass_dependency():
    imports = [node for node in _tree().body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 1 and isinstance(imports[0], ast.ImportFrom) and imports[0].module == "dataclasses" and [item.name for item in imports[0].names] == ["dataclass"]


def test_c12_02_canonical_module_imports_no_phase_12_consumer_or_composition_module():
    assert "phase_12_" not in _source()


def test_c12_03_canonical_module_imports_no_runtime_service_provider_telegram_or_network_module():
    assert all(token not in _source().lower() for token in ("runtime", "service", "provider", "telegram", "network", "socket"))


def test_c13_01_old_private_type_definition_is_retired():
    assert "class _Phase12AuthorizationTrustExpectationsV1" not in _source(_COMPOSITION)


def test_c13_02_no_second_nine_field_trust_expectation_dataclass_exists():
    assert sum("class Phase12AuthorizationTrustExpectationsV1" in source for source in _engine_sources().values()) == 1


def test_c13_03_no_dual_private_and_public_type_ownership_exists():
    assert "_Phase12AuthorizationTrustExpectationsV1" not in "\n".join(_engine_sources().values())


def test_c14_01_old_private_builder_is_retired():
    assert "build_phase_12_authorization_trust_expectations_v1" not in _source(_COMPOSITION)


def test_c14_02_no_builder_reconstructs_or_wraps_the_canonical_type():
    assert "Phase12AuthorizationTrustExpectationsV1(" not in _source(_COMPOSITION)


def test_c14_03_no_conversion_or_bridge_operation_exists():
    assert all(token not in _source(_COMPOSITION).lower() for token in ("convert", "bridge", "adapter", "wrapper"))


def test_c15_01_no_private_name_alias_exists():
    assert "_Phase12AuthorizationTrustExpectationsV1" not in _source()


def test_c15_02_no_fallback_import_or_module_getattr_exists():
    assert all(token not in _source() for token in ("try:", "__getattr__", "ImportError"))


def test_c15_03_no_sys_modules_hook_or_compatibility_container_exists():
    assert all(token not in _source() for token in ("sys.modules", "meta_path", "compat"))


def test_c16_01_bounded_composition_requires_exact_public_canonical_type():
    assert "type(trust_expectations) is not Phase12AuthorizationTrustExpectationsV1" in _source(_COMPOSITION)


def test_c16_02_exact_type_check_uses_no_isinstance_protocol_union_or_mapping():
    operation = next(node for node in _tree(_COMPOSITION).body if isinstance(node, ast.FunctionDef) and node.name == "run_phase_12_authorization_repository_validation_composition_v1")
    parameter = next(item for item in operation.args.kwonlyargs if item.arg == "trust_expectations")
    guard = next(node.test for node in operation.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Call) and isinstance(node.test.left.func, ast.Name) and node.test.left.func.id == "type" and len(node.test.left.args) == 1 and isinstance(node.test.left.args[0], ast.Name) and node.test.left.args[0].id == "trust_expectations")
    assert isinstance(parameter.annotation, ast.Name) and parameter.annotation.id == "Phase12AuthorizationTrustExpectationsV1" and isinstance(guard.ops[0], ast.IsNot) and isinstance(guard.comparators[0], ast.Name) and guard.comparators[0].id == "Phase12AuthorizationTrustExpectationsV1"


def test_c16_03_relevant_consumers_import_the_canonical_public_type_directly():
    source = _source(_COMPOSITION)
    assert "from engine.phase_12_authorization_trust_expectations_v1 import Phase12AuthorizationTrustExpectationsV1" in source


def test_c17_01_authorization_record_retains_exact_separate_public_identity():
    source = _source(_ROOT / "engine" / "phase_12_activation_mode_authorization_verifier_v1.py")
    assert "class Phase12ActivationAuthorizationRecordV1" in source


def test_c17_02_authorization_record_fields_are_not_merged_into_trust_expectations():
    source = _source(_ROOT / "engine" / "phase_12_activation_mode_authorization_verifier_v1.py")
    assert "class Phase12ActivationAuthorizationRecordV1" in source and "Phase12ActivationAuthorizationRecordV1" not in _source()


def test_c17_03_canonical_trust_type_does_not_import_wrap_or_validate_authorization_record():
    assert all(token not in _source() for token in ("Phase12ActivationAuthorizationRecordV1", "authorization_record", "validate"))


def test_c18_01_clock_context_coordinator_and_runtime_modules_do_not_define_the_canonical_type():
    sources = _engine_sources()
    assert all("class Phase12AuthorizationTrustExpectationsV1" not in source for name, source in sources.items() if any(token in name for token in ("clock", "context", "coordinator", "runtime")))


def test_c18_02_parser_verifier_repository_service_and_telegram_modules_do_not_own_the_canonical_type():
    sources = _engine_sources()
    assert all("class Phase12AuthorizationTrustExpectationsV1" not in source for name, source in sources.items() if any(token in name for token in ("parser", "verifier", "repository", "service", "telegram")))


def test_c18_03_no_operational_component_imports_private_compatibility_surface():
    assert "_Phase12AuthorizationTrustExpectationsV1" not in "\n".join(_engine_sources().values())


def test_c19_01_public_type_claims_only_immutable_structural_storage():
    assert set(Phase12AuthorizationTrustExpectationsV1.__slots__) == set(_FIELDS)


def test_c19_02_public_type_claims_no_reference_validity_authorization_or_eligibility():
    tree = _tree()
    public_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Phase12AuthorizationTrustExpectationsV1")
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    fields = [node for node in public_class.body if isinstance(node, ast.AnnAssign)]
    assert len(fields) == 9 and all(isinstance(node.target, ast.Name) and node.target.id in _FIELDS and isinstance(node.annotation, ast.Name) and node.annotation.id == "str" for node in fields) and all(isinstance(node, ast.AnnAssign) for node in public_class.body) and len(imports) == 1 and isinstance(imports[0], ast.ImportFrom) and imports[0].module == "dataclasses" and [item.name for item in imports[0].names] == ["dataclass"]


def test_c19_03_public_type_claims_no_runtime_activation_deployment_or_production_readiness():
    source = _source().lower()
    assert all(token not in source for token in ("runtime", "activation", "production", "readiness")) and source.count("deployment") == 1


def test_c20_01_canonical_type_can_be_passed_to_exact_type_consumer_without_adapter():
    assert type(_make()) is Phase12AuthorizationTrustExpectationsV1 and "adapter" not in _source(_COMPOSITION).lower()


def test_c20_02_migration_preserves_exact_nine_field_structural_semantics():
    assert tuple(_make().__dataclass_fields__) == _FIELDS and len(_make().__dataclass_fields__) == 9


def test_c20_03_migration_introduces_no_source_commit_result_or_runtime_ownership():
    assert all(token not in _source().lower() for token in ("source", "commit", "result", "runtime"))
