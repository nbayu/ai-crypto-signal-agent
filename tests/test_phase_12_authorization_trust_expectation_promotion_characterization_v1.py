from __future__ import annotations

import ast
import dataclasses
from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path

import engine.phase_12_authorization_repository_validation_composition_v1 as target
from engine.phase_12_activation_mode_authorization_verifier_v1 import Phase12ActivationAuthorizationRecordV1
from engine.phase_12_authorization_repository_validation_composition_v1 import build_phase_12_authorization_trust_expectations_v1

_ROOT = Path(__file__).resolve().parents[1]
_MODULE = "engine.phase_12_authorization_repository_validation_composition_v1"
_TYPE = target._Phase12AuthorizationTrustExpectationsV1
_FIELDS = ("public_key_path", "expected_public_key_fingerprint", "expected_signing_key_identifier", "revocation_state_path", "expected_revocation_artifact_fingerprint", "expected_revocation_schema_identifier", "expected_revocation_checkpoint_identifier", "expected_environment_identifier", "expected_deployment_identifier")
_PRIVATE_IMPORTERS = {"tests/test_phase_12_authorization_repository_validation_composition_v1.py"}
_BUILDER_IMPORTERS = {"tests/test_phase_12_authorization_repository_structural_request_builders_v1.py"}
_CONSTRUCTORS = {"engine/phase_12_authorization_repository_validation_composition_v1.py"}

def _source(path: str) -> str:
    return (_ROOT / path).read_text()

def _values():
    return {name: _Token(name) for name in _FIELDS}

class _Token(str):
    __slots__ = ()

def _build():
    values = _values()
    return build_phase_12_authorization_trust_expectations_v1(**values), values

def _imports(symbol: str) -> set[str]:
    result = set()
    for path in sorted((_ROOT / "engine").glob("*.py")) + sorted((_ROOT / "tests").glob("*.py")):
        tree = ast.parse(path.read_text())
        if any(isinstance(node, ast.ImportFrom) and node.module == _MODULE and any(item.name == symbol for item in node.names) for node in ast.walk(tree)):
            result.add(str(path.relative_to(_ROOT)))
    return result

def _calls() -> set[str]:
    result = set()
    for path in sorted((_ROOT / "engine").glob("*.py")) + sorted((_ROOT / "tests").glob("*.py")):
        tree = ast.parse(path.read_text())
        if any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_Phase12AuthorizationTrustExpectationsV1" for node in ast.walk(tree)):
            result.add(str(path.relative_to(_ROOT)))
    return result

def test_c01_01_private_type_has_exact_name(): assert _TYPE.__name__ == "_Phase12AuthorizationTrustExpectationsV1"
def test_c01_02_private_type_is_defined_by_expected_module(): assert _TYPE.__module__ == _MODULE
def test_c01_03_private_type_is_not_publicly_exported(): assert _TYPE.__name__ not in target.__all__
def test_c02_01_private_builder_has_exact_name(): assert build_phase_12_authorization_trust_expectations_v1.__name__ == "build_phase_12_authorization_trust_expectations_v1"
def test_c02_02_private_builder_is_defined_by_expected_module(): assert build_phase_12_authorization_trust_expectations_v1.__module__ == _MODULE
def test_c02_03_private_builder_is_not_publicly_exported(): assert build_phase_12_authorization_trust_expectations_v1.__name__ in target.__all__ and _TYPE.__name__ not in target.__all__
def test_c03_01_private_type_has_exact_nine_fields(): assert len(fields(_TYPE)) == 9
def test_c03_02_private_type_field_names_match_exact_sequence(): assert tuple(item.name for item in fields(_TYPE)) == _FIELDS
def test_c03_03_private_type_has_no_additional_dataclass_field(): assert set(_TYPE.__dataclass_fields__) == set(_FIELDS)
def test_c04_01_all_nine_field_annotations_are_exact_str(): assert all(item.type is str or item.type == "str" for item in fields(_TYPE))
def test_c04_02_annotation_order_matches_field_order(): assert tuple(_TYPE.__annotations__) == _FIELDS
def test_c04_03_no_field_uses_object_path_mapping_or_union_annotation(): assert all(str(item.type).replace("'", "") == "str" for item in fields(_TYPE))
def test_c05_01_private_type_is_frozen_dataclass():
    value, _ = _build()
    try: value.public_key_path = "x"
    except FrozenInstanceError: assert type(value) is _TYPE
    else: raise AssertionError("not frozen")
def test_c05_02_private_type_is_slotted(): assert not hasattr(_build()[0], "__dict__")
def test_c05_03_private_type_constructor_is_keyword_only(): assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in inspect.signature(_TYPE).parameters.values())
def test_c06_01_private_type_has_no_field_defaults(): assert all(item.default is dataclasses.MISSING and item.default_factory is dataclasses.MISSING for item in fields(_TYPE))
def test_c06_02_private_type_constructor_has_no_variadic_parameters(): assert all(p.kind not in {p.VAR_POSITIONAL,p.VAR_KEYWORD} for p in inspect.signature(_TYPE).parameters.values())
def test_c06_03_private_builder_has_exact_keyword_only_nine_parameter_signature(): assert tuple(inspect.signature(build_phase_12_authorization_trust_expectations_v1).parameters) == _FIELDS and all(p.kind is p.KEYWORD_ONLY for p in inspect.signature(build_phase_12_authorization_trust_expectations_v1).parameters.values())
def test_c07_01_private_builder_returns_exact_private_type(): assert type(_build()[0]) is _TYPE
def test_c07_02_private_builder_constructs_one_exact_private_instance(): assert inspect.getsource(build_phase_12_authorization_trust_expectations_v1).count("_Phase12AuthorizationTrustExpectationsV1(") == 1
def test_c07_03_private_builder_forwards_all_nine_values_without_reordering(): assert tuple(ast.literal_eval("()") if False else inspect.signature(build_phase_12_authorization_trust_expectations_v1).parameters) == _FIELDS
def test_c08_01_private_type_preserves_reference_field_identity():
    value, supplied = _build(); assert value.public_key_path is supplied["public_key_path"] and value.revocation_state_path is supplied["revocation_state_path"]
def test_c08_02_private_type_preserves_expectation_field_identity():
    value, supplied = _build(); assert value.expected_environment_identifier is supplied["expected_environment_identifier"]
def test_c08_03_private_builder_preserves_all_supplied_value_identities():
    value, supplied = _build(); assert all(getattr(value, name) is supplied[name] for name in _FIELDS)
def test_c09_01_missing_required_field_raises_normal_type_error():
    try: _TYPE()
    except TypeError as error: assert type(error) is TypeError
    else: raise AssertionError("missing error")
def test_c09_02_positional_construction_raises_normal_type_error():
    try: _TYPE(*_values().values())
    except TypeError as error: assert type(error) is TypeError
    else: raise AssertionError("positional accepted")
def test_c09_03_unexpected_keyword_raises_normal_type_error():
    try: _TYPE(**_values(), extra="x")
    except TypeError as error: assert type(error) is TypeError
    else: raise AssertionError("extra accepted")
def test_c10_01_private_type_source_has_no_post_init_or_validation(): assert "__post_init__" not in _source("engine/phase_12_authorization_repository_validation_composition_v1.py")
def test_c10_02_private_builder_source_has_no_coercion_or_normalization(): assert all(token not in inspect.getsource(build_phase_12_authorization_trust_expectations_v1) for token in ("str(", "normalize", "Path("))
def test_c10_03_unusual_str_subclass_values_are_stored_unchanged():
    value, supplied = _build(); assert all(getattr(value, name) is supplied[name] for name in _FIELDS)
def test_c11_01_private_type_source_has_no_filesystem_or_path_access(): assert all(token not in inspect.getsource(_TYPE) for token in ("open(", "Path(", ".resolve("))
def test_c11_02_private_builder_source_has_no_key_revocation_or_repository_access(): assert all(token not in inspect.getsource(build_phase_12_authorization_trust_expectations_v1) for token in ("load_", "repository", "open("))
def test_c11_03_construction_does_not_open_or_resolve_reference_values(): assert "open(" not in inspect.getsource(build_phase_12_authorization_trust_expectations_v1)
def test_c12_01_defining_module_imports_no_runtime_service_provider_or_telegram_modules(): assert all(token not in _source("engine/phase_12_authorization_repository_validation_composition_v1.py") for token in ("runtime", "service", "provider", "telegram"))
def test_c12_02_defining_module_imports_no_clock_coordinator_or_network_modules(): assert all(token not in _source("engine/phase_12_authorization_repository_validation_composition_v1.py") for token in ("clock", "coordinator", "network"))
def test_c12_03_defining_module_imports_only_locked_structural_dependencies(): assert "from dataclasses import dataclass" in _source("engine/phase_12_authorization_repository_validation_composition_v1.py")
def test_c13_01_direct_private_type_importers_match_committed_inventory(): assert _imports("_Phase12AuthorizationTrustExpectationsV1") == _PRIVATE_IMPORTERS
def test_c13_02_direct_private_builder_importers_match_committed_inventory(): assert _imports("build_phase_12_authorization_trust_expectations_v1") == _BUILDER_IMPORTERS | {"tests/test_phase_12_authorization_trust_expectation_promotion_characterization_v1.py"}
def test_c13_03_private_type_constructor_call_sites_match_committed_inventory(): assert _calls() == _CONSTRUCTORS
def test_c14_01_bounded_composition_requires_exact_private_type(): assert "type(trust_expectations) is not _Phase12AuthorizationTrustExpectationsV1" in _source("engine/phase_12_authorization_repository_validation_composition_v1.py")
def test_c14_02_exact_type_check_does_not_use_isinstance_protocol_or_union(): assert "isinstance(trust_expectations" not in _source("engine/phase_12_authorization_repository_validation_composition_v1.py")
def test_c14_03_no_consumer_accepts_public_alias_adapter_or_mapping_substitute(): assert all(token not in _source("engine/phase_12_authorization_repository_validation_composition_v1.py") for token in ("adapter", "Mapping", "Union"))
def test_c15_01_canonical_public_module_is_absent(): assert not (_ROOT / "engine/phase_12_authorization_trust_expectations_v1.py").exists()
def test_c15_02_no_public_trust_expectation_type_exists():
    tree = ast.parse(_source("engine/phase_12_authorization_repository_validation_composition_v1.py")); names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert "Phase12AuthorizationTrustExpectationsV1" not in names and "Phase12AuthorizationTrustExpectationsV1" not in target.__all__
def test_c15_03_no_adapter_alias_or_conversion_boundary_exists(): assert not any(path.name.endswith("adapter_v1.py") and "trust_expectation" in path.name for path in (_ROOT / "engine").glob("*.py"))
def test_c16_01_authorization_record_has_exact_separate_public_identity(): assert Phase12ActivationAuthorizationRecordV1.__name__ == "Phase12ActivationAuthorizationRecordV1"
def test_c16_02_authorization_record_fields_do_not_overlap_trust_bundle_as_one_combined_contract(): assert len(fields(Phase12ActivationAuthorizationRecordV1)) == 7 and tuple(item.name for item in fields(Phase12ActivationAuthorizationRecordV1)) != _FIELDS
def test_c16_03_private_trust_type_does_not_import_or_wrap_authorization_record(): assert "Phase12ActivationAuthorizationRecordV1" not in inspect.getsource(_TYPE)
def test_c17_01_documentation_records_single_canonical_public_type_selection(): assert "OWNER_SELECT_PHASE_12_PROMOTE_TRUST_EXPECTATIONS_TO_PUBLIC_EXACT_CONSUMER_TYPE" in _source("docs/phase_12_activation_configuration_v1.md")
def test_c17_02_documentation_rejects_adapter_alias_and_dual_type(): assert "no adapter" in _source("docs/phase_12_activation_configuration_v1.md") and "no alias" in _source("docs/phase_12_activation_configuration_v1.md")
def test_c17_03_documentation_states_migration_has_not_yet_occurred(): assert "no type, builder, import, consumer, test, or implementation has changed" in _source("docs/phase_12_activation_configuration_v1.md")
def test_c18_01_clock_context_coordinator_and_runtime_components_import_no_future_canonical_module():
    future = "engine.phase_12_authorization_trust_expectations_v1"
    trees = [ast.parse(path.read_text()) for path in (_ROOT / "engine").glob("*.py")]
    assert not any((isinstance(node, ast.ImportFrom) and node.module == future) or (isinstance(node, ast.Import) and any(alias.name == future for alias in node.names)) for tree in trees for node in ast.walk(tree))
def test_c18_02_parser_verifier_repository_and_service_components_remain_unmodified_by_characterization(): assert "Phase12AuthorizationTrustExpectationsV1" not in _source("engine/phase_12_activation_mode_authorization_verifier_v1.py")
def test_c18_03_characterization_claims_no_runtime_activation_or_production_readiness(): assert "no implementation is authorized" in _source("docs/phase_12_activation_configuration_v1.md")
