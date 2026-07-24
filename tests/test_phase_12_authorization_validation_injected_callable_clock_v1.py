from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, MISSING, fields, is_dataclass
import ast
import inspect
from pathlib import Path

import pytest

from engine.phase_12_authorization_validation_injected_callable_clock_v1 import (
    Phase12AuthorizationValidationInjectedCallableClockV1,
    build_phase_12_authorization_validation_injected_callable_clock_v1,
)
import engine.phase_12_authorization_validation_injected_callable_clock_v1 as clock_module


class _CounterClock:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> object:
        self.calls += 1
        return object()


def _field_annotation() -> object:
    return inspect.get_annotations(
        Phase12AuthorizationValidationInjectedCallableClockV1,
        eval_str=True,
    )["clock"]


def _builder_annotations() -> dict[str, object]:
    return inspect.get_annotations(
        build_phase_12_authorization_validation_injected_callable_clock_v1,
        eval_str=True,
    )


def _module_source() -> str:
    return inspect.getsource(clock_module)


def _module_tree() -> ast.Module:
    return ast.parse(_module_source())


def _builder_node() -> ast.FunctionDef:
    return next(
        node
        for node in _module_tree().body
        if isinstance(node, ast.FunctionDef)
        and node.name == "build_phase_12_authorization_validation_injected_callable_clock_v1"
    )


def _repository_root() -> Path:
    return Path(__file__).parent.parent


def _clock_module_path() -> Path:
    return _repository_root() / "engine" / "phase_12_authorization_validation_injected_callable_clock_v1.py"


def test_c01_01_public_type_has_exact_name() -> None:
    assert Phase12AuthorizationValidationInjectedCallableClockV1.__name__ == (
        "Phase12AuthorizationValidationInjectedCallableClockV1"
    )


def test_c01_02_public_type_is_defined_by_expected_module() -> None:
    assert Phase12AuthorizationValidationInjectedCallableClockV1.__module__ == (
        "engine.phase_12_authorization_validation_injected_callable_clock_v1"
    )


def test_c01_03_public_type_is_a_class() -> None:
    assert inspect.isclass(Phase12AuthorizationValidationInjectedCallableClockV1)


def test_c02_01_builder_has_exact_name() -> None:
    assert build_phase_12_authorization_validation_injected_callable_clock_v1.__name__ == (
        "build_phase_12_authorization_validation_injected_callable_clock_v1"
    )


def test_c02_02_builder_is_defined_by_expected_module() -> None:
    assert build_phase_12_authorization_validation_injected_callable_clock_v1.__module__ == (
        "engine.phase_12_authorization_validation_injected_callable_clock_v1"
    )


def test_c02_03_builder_is_a_function() -> None:
    assert inspect.isfunction(
        build_phase_12_authorization_validation_injected_callable_clock_v1
    )


def test_c03_01_module_all_has_exact_two_names() -> None:
    assert clock_module.__all__ == (
        "Phase12AuthorizationValidationInjectedCallableClockV1",
        "build_phase_12_authorization_validation_injected_callable_clock_v1",
    )


def test_c03_02_module_all_preserves_type_then_builder_order() -> None:
    assert clock_module.__all__[0] == (
        "Phase12AuthorizationValidationInjectedCallableClockV1"
    ) and clock_module.__all__[1] == (
        "build_phase_12_authorization_validation_injected_callable_clock_v1"
    )


def test_c03_03_module_exports_no_additional_public_clock_surface() -> None:
    forbidden = {
        "Protocol",
        "invoke_phase_12_authorization_validation_injected_callable_clock_v1",
        "default_clock",
        "system_clock",
        "runtime_root",
        "dependency_container",
    }
    assert forbidden.isdisjoint(clock_module.__all__)


def test_c04_01_public_type_is_a_dataclass() -> None:
    assert is_dataclass(Phase12AuthorizationValidationInjectedCallableClockV1)


def test_c04_02_clock_field_cannot_be_reassigned() -> None:
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=_CounterClock())
    with pytest.raises(FrozenInstanceError):
        binding.clock = _CounterClock()
    assert binding.clock.calls == 0


def test_c04_03_frozen_instance_rejects_new_attribute_assignment() -> None:
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=_CounterClock())
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        binding.extra = object()
    assert binding.clock.calls == 0


def test_c05_01_public_type_declares_slots() -> None:
    assert Phase12AuthorizationValidationInjectedCallableClockV1.__slots__ == ("clock",)


def test_c05_02_instance_has_no_dict() -> None:
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=_CounterClock())
    assert not hasattr(binding, "__dict__")


def test_c05_03_unknown_attribute_cannot_be_added() -> None:
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=_CounterClock())
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        setattr(binding, "unexpected", object())
    assert binding.clock.calls == 0


def test_c06_01_direct_construction_accepts_clock_keyword() -> None:
    clock = _CounterClock()
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock)
    assert binding.clock is clock


def test_c06_02_direct_construction_rejects_positional_clock() -> None:
    with pytest.raises(TypeError):
        Phase12AuthorizationValidationInjectedCallableClockV1(_CounterClock())
    assert Phase12AuthorizationValidationInjectedCallableClockV1.__dataclass_params__.frozen


def test_c06_03_direct_construction_requires_clock_keyword() -> None:
    with pytest.raises(TypeError):
        Phase12AuthorizationValidationInjectedCallableClockV1()
    assert len(fields(Phase12AuthorizationValidationInjectedCallableClockV1)) == 1


def test_c07_01_dataclass_has_exactly_one_field() -> None:
    assert len(fields(Phase12AuthorizationValidationInjectedCallableClockV1)) == 1


def test_c07_02_only_field_is_named_clock() -> None:
    assert tuple(field.name for field in fields(Phase12AuthorizationValidationInjectedCallableClockV1)) == (
        "clock",
    )


def test_c07_03_clock_field_has_no_default_or_factory() -> None:
    clock_field = fields(Phase12AuthorizationValidationInjectedCallableClockV1)[0]
    assert clock_field.default is MISSING and clock_field.default_factory is MISSING


def test_c08_01_clock_field_annotation_is_exact_callable_object() -> None:
    assert _field_annotation() == Callable[[], object]


def test_c08_02_clock_annotation_has_zero_argument_contract() -> None:
    assert _field_annotation().__args__[0] == []


def test_c08_03_clock_annotation_has_object_return_without_datetime_semantics() -> None:
    annotation = _field_annotation()
    assert annotation.__args__[1] is object and "datetime" not in str(annotation).lower()


def test_c09_01_builder_has_exact_single_keyword_only_parameter() -> None:
    parameters = tuple(
        inspect.signature(
            build_phase_12_authorization_validation_injected_callable_clock_v1
        ).parameters.values()
    )
    assert len(parameters) == 1 and parameters[0].name == "clock" and parameters[0].kind is inspect.Parameter.KEYWORD_ONLY


def test_c09_02_builder_clock_annotation_is_exact_callable_object() -> None:
    assert _builder_annotations()["clock"] == Callable[[], object]


def test_c09_03_builder_return_annotation_is_exact_public_binding_type() -> None:
    assert _builder_annotations()["return"] is Phase12AuthorizationValidationInjectedCallableClockV1


def test_c10_01_builder_clock_has_no_default() -> None:
    parameter = inspect.signature(
        build_phase_12_authorization_validation_injected_callable_clock_v1
    ).parameters["clock"]
    assert parameter.default is inspect.Parameter.empty


def test_c10_02_builder_has_no_var_positional_parameter() -> None:
    parameters = inspect.signature(
        build_phase_12_authorization_validation_injected_callable_clock_v1
    ).parameters.values()
    assert all(parameter.kind is not inspect.Parameter.VAR_POSITIONAL for parameter in parameters)


def test_c10_03_builder_has_no_var_keyword_parameter() -> None:
    parameters = inspect.signature(
        build_phase_12_authorization_validation_injected_callable_clock_v1
    ).parameters.values()
    assert all(parameter.kind is not inspect.Parameter.VAR_KEYWORD for parameter in parameters)


def test_c11_01_builder_returns_exact_public_binding_type() -> None:
    binding = build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert type(binding) is Phase12AuthorizationValidationInjectedCallableClockV1


def test_c11_02_builder_source_contains_one_direct_binding_construction() -> None:
    calls = [node for node in ast.walk(_builder_node()) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Phase12AuthorizationValidationInjectedCallableClockV1"]
    assert len(calls) == 1 and calls[0].keywords[0].arg == "clock"


def test_c11_03_builder_source_contains_one_direct_return() -> None:
    returns = [node for node in ast.walk(_builder_node()) if isinstance(node, ast.Return)]
    assert len(returns) == 1 and isinstance(returns[0].value, ast.Call)


def test_c12_01_direct_construction_preserves_callable_identity() -> None:
    clock = _CounterClock()
    assert Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock).clock is clock


def test_c12_02_builder_preserves_callable_identity() -> None:
    clock = _CounterClock()
    assert build_phase_12_authorization_validation_injected_callable_clock_v1(clock=clock).clock is clock


def test_c12_03_distinct_callables_remain_distinct_after_binding() -> None:
    first, second = _CounterClock(), _CounterClock()
    assert Phase12AuthorizationValidationInjectedCallableClockV1(clock=first).clock is first and Phase12AuthorizationValidationInjectedCallableClockV1(clock=second).clock is second and first is not second


def test_c13_01_direct_construction_invokes_clock_zero_times() -> None:
    clock = _CounterClock()
    Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock)
    assert clock.calls == 0


def test_c13_02_builder_invokes_clock_zero_times() -> None:
    clock = _CounterClock()
    build_phase_12_authorization_validation_injected_callable_clock_v1(clock=clock)
    assert clock.calls == 0


def test_c13_03_repr_equality_and_hash_do_not_invoke_clock() -> None:
    clock = _CounterClock()
    binding = Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock)
    assert "_CounterClock" not in repr(binding) and binding == binding and hash(binding) == hash(binding) and clock.calls == 0


def test_c14_01_builder_source_does_not_inspect_callable_signature() -> None:
    calls = {ast.unparse(node.func) for node in ast.walk(_builder_node()) if isinstance(node, ast.Call)}
    assert "inspect.signature" not in calls and "callable" not in calls


def test_c14_02_builder_source_does_not_wrap_adapt_or_partially_apply_clock() -> None:
    names = {node.id.lower() for node in ast.walk(_builder_node()) if isinstance(node, ast.Name)}
    assert {"partial", "proxy", "adapter", "lambda"}.isdisjoint(names) and not any(isinstance(node, ast.Lambda) for node in ast.walk(_builder_node())) and not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in ast.walk(_builder_node()) if node is not _builder_node())


def test_c14_03_builder_source_does_not_copy_convert_normalize_cache_or_memoize_clock() -> None:
    names = {node.id.lower() for node in ast.walk(_builder_node()) if isinstance(node, ast.Name)}
    assert {"copy", "deepcopy", "convert", "normalize", "cache", "memoize", "registry", "dict", "mapping", "dispatch", "getattr", "globals", "locals"}.isdisjoint(names) and len(_builder_node().body) == 1


def test_c15_01_builder_missing_clock_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        build_phase_12_authorization_validation_injected_callable_clock_v1()
    assert inspect.signature(build_phase_12_authorization_validation_injected_callable_clock_v1).parameters["clock"].default is inspect.Parameter.empty


def test_c15_02_builder_positional_clock_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        build_phase_12_authorization_validation_injected_callable_clock_v1(_CounterClock())
    assert inspect.signature(build_phase_12_authorization_validation_injected_callable_clock_v1).parameters["clock"].kind is inspect.Parameter.KEYWORD_ONLY


def test_c15_03_builder_unexpected_keyword_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock(), extra=object())
    assert len(inspect.signature(build_phase_12_authorization_validation_injected_callable_clock_v1).parameters) == 1


def test_c16_01_constructor_exception_object_propagates_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    error, attempts = RuntimeError("constructor failure"), []
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        attempts.append(clock)
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(RuntimeError) as captured:
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert captured.value is error and len(attempts) == 1


def test_c16_02_builder_does_not_translate_constructor_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    error = ValueError("unchanged")
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(ValueError) as captured:
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert captured.value is error


def test_c16_03_builder_does_not_retry_after_constructor_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    error, attempts = RuntimeError("one attempt"), []
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        attempts.append(clock)
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(RuntimeError):
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert len(attempts) == 1


def test_c17_01_constructor_base_exception_propagates_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoundaryBaseException(BaseException):
        __slots__ = ()
    error, attempts = _BoundaryBaseException(), []
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        attempts.append(clock)
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(_BoundaryBaseException) as captured:
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert captured.value is error and len(attempts) == 1


def test_c17_02_builder_does_not_catch_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    error = KeyboardInterrupt()
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(KeyboardInterrupt) as captured:
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert captured.value is error


def test_c17_03_builder_does_not_catch_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    error = SystemExit(7)
    def raising_constructor(*, clock: Callable[[], object]) -> object:
        raise error
    monkeypatch.setattr(clock_module, "Phase12AuthorizationValidationInjectedCallableClockV1", raising_constructor)
    with pytest.raises(SystemExit) as captured:
        build_phase_12_authorization_validation_injected_callable_clock_v1(clock=_CounterClock())
    assert captured.value is error


def test_c18_01_module_source_has_no_system_time_acquisition() -> None:
    calls = {ast.unparse(node.func).split(".")[-1] for node in ast.walk(_module_tree()) if isinstance(node, ast.Call)}
    assert {"now", "utcnow", "today", "time", "monotonic", "perf_counter", "process_time"}.isdisjoint(calls)


def test_c18_02_module_source_has_no_environment_filesystem_git_network_or_subprocess_access() -> None:
    names = {node.id for node in ast.walk(_module_tree()) if isinstance(node, ast.Name)}
    assert {"getenv", "environ", "open", "read_text", "write_text", "resolve", "expanduser", "run", "Popen", "socket", "request"}.isdisjoint(names)


def test_c18_03_module_source_has_no_runtime_service_provider_telegram_or_activation_access() -> None:
    names = {node.id.lower() for node in ast.walk(_module_tree()) if isinstance(node, ast.Name)}
    assert {"coordinator", "runtime", "service", "provider", "telegram", "activation", "logging", "serialize", "cache"}.isdisjoint(names)


def test_c19_01_clock_module_imports_no_locked_orchestration_component() -> None:
    imports = {alias.name.lower() for node in _module_tree().body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not any(any(term in imported for term in {"orchestration", "coordinator", "request", "marker", "repository", "comparator", "replay", "parser", "verifier", "key", "revocation"}) for imported in imports)


def test_c19_02_locked_components_import_no_clock_boundary() -> None:
    target = "phase_12_authorization_validation_injected_callable_clock_v1"
    sources = [path.read_text() for path in (_repository_root() / "engine").glob("*.py") if path != _clock_module_path()]
    assert all(target not in source for source in sources)


def test_c19_03_clock_boundary_has_no_dependency_on_request_marker_repository_replay_or_coordinator_modules() -> None:
    names = {node.id.lower() for node in ast.walk(_module_tree()) if isinstance(node, ast.Name)}
    assert {"request", "marker", "repository", "replay", "coordinator"}.isdisjoint(names)


def test_c20_01_public_contract_claims_only_opaque_callable_binding() -> None:
    annotations = _builder_annotations()
    assert annotations["clock"] == Callable[[], object] and annotations["return"] is Phase12AuthorizationValidationInjectedCallableClockV1


def test_c20_02_public_contract_does_not_claim_datetime_temporal_or_runtime_guarantees() -> None:
    public_text = " ".join(filter(None, (clock_module.__doc__, inspect.getdoc(Phase12AuthorizationValidationInjectedCallableClockV1), inspect.getdoc(build_phase_12_authorization_validation_injected_callable_clock_v1)))).lower()
    forbidden = {"datetime", "timezone", "freshness", "monotonicity", "determinism", "temporal validity", "authorization validity", "configuration eligibility", "runtime readiness", "production approval", "activation", "infrastructure health"}
    assert not any(claim in public_text for claim in forbidden)


def test_c20_03_stored_callable_is_publicly_available_for_later_single_acquisition() -> None:
    clock = _CounterClock()
    binding = build_phase_12_authorization_validation_injected_callable_clock_v1(clock=clock)
    assert binding.clock is clock and clock.calls == 0
