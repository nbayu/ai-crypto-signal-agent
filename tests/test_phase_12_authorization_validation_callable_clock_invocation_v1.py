from __future__ import annotations

import ast
from collections.abc import Callable
import inspect
from pathlib import Path

import pytest

from engine.phase_12_authorization_validation_callable_clock_invocation_v1 import (
    invoke_phase_12_authorization_validation_callable_clock_v1,
)
import engine.phase_12_authorization_validation_callable_clock_invocation_v1 as invocation_module
from engine.phase_12_authorization_validation_injected_callable_clock_v1 import (
    Phase12AuthorizationValidationInjectedCallableClockV1,
)


class _CounterClock:
    def __init__(self, result: object) -> None:
        self.calls = 0
        self.result = result

    def __call__(self) -> object:
        self.calls += 1
        return self.result


class _BindingLike:
    def __init__(self, clock: Callable[[], object]) -> None:
        self.clock = clock


def _operation_tree() -> ast.Module:
    return ast.parse(inspect.getsource(invocation_module))


def _operation_node() -> ast.FunctionDef:
    return next(
        node for node in _operation_tree().body
        if isinstance(node, ast.FunctionDef)
        and node.name == "invoke_phase_12_authorization_validation_callable_clock_v1"
    )


def _repository_root() -> Path:
    return Path(__file__).parent.parent


def test_c01_01_operation_has_exact_name() -> None:
    assert invoke_phase_12_authorization_validation_callable_clock_v1.__name__ == "invoke_phase_12_authorization_validation_callable_clock_v1"


def test_c01_02_operation_is_defined_by_expected_module() -> None:
    assert invoke_phase_12_authorization_validation_callable_clock_v1.__module__ == "engine.phase_12_authorization_validation_callable_clock_invocation_v1"


def test_c01_03_module_all_has_exact_single_operation() -> None:
    assert invocation_module.__all__ == ("invoke_phase_12_authorization_validation_callable_clock_v1",)


def test_c02_01_operation_has_exact_single_keyword_only_parameter() -> None:
    parameters = tuple(inspect.signature(invoke_phase_12_authorization_validation_callable_clock_v1).parameters.values())
    assert len(parameters) == 1 and parameters[0].name == "clock_binding" and parameters[0].kind is inspect.Parameter.KEYWORD_ONLY and parameters[0].default is inspect.Parameter.empty


def test_c02_02_clock_binding_annotation_is_exact_public_binding_type() -> None:
    assert inspect.get_annotations(invoke_phase_12_authorization_validation_callable_clock_v1, eval_str=True)["clock_binding"] is Phase12AuthorizationValidationInjectedCallableClockV1


def test_c02_03_return_annotation_is_exact_object() -> None:
    assert inspect.get_annotations(invoke_phase_12_authorization_validation_callable_clock_v1, eval_str=True)["return"] is object


def test_c03_01_operation_source_has_exact_direct_clock_field_access() -> None:
    attributes = [node for node in ast.walk(_operation_node()) if isinstance(node, ast.Attribute)]
    assert len(attributes) == 1 and isinstance(attributes[0].value, ast.Name) and attributes[0].value.id == "clock_binding" and attributes[0].attr == "clock"


def test_c03_02_operation_source_has_exact_single_direct_invocation() -> None:
    calls = [node for node in ast.walk(_operation_node()) if isinstance(node, ast.Call)]
    assert len(calls) == 1 and isinstance(calls[0].func, ast.Attribute) and calls[0].args == [] and calls[0].keywords == []


def test_c03_03_operation_source_has_exact_single_direct_return() -> None:
    returns = [node for node in ast.walk(_operation_node()) if isinstance(node, ast.Return)]
    assert len(returns) == 1 and isinstance(returns[0].value, ast.Call)


def test_c04_01_operation_invokes_stored_callable_exactly_once() -> None:
    clock = _CounterClock(object())
    invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(clock))
    assert clock.calls == 1


def test_c04_02_operation_returns_exact_callable_result_by_identity() -> None:
    result, clock = object(), _CounterClock(object())
    clock.result = result
    assert invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(clock)) is result


def test_c04_03_distinct_calls_each_perform_one_independent_invocation() -> None:
    clock = _CounterClock(object())
    invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(clock))
    invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(clock))
    assert clock.calls == 2


def test_c05_01_missing_clock_binding_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        invoke_phase_12_authorization_validation_callable_clock_v1()
    assert "clock_binding" in inspect.signature(invoke_phase_12_authorization_validation_callable_clock_v1).parameters


def test_c05_02_positional_clock_binding_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        invoke_phase_12_authorization_validation_callable_clock_v1(_BindingLike(_CounterClock(object())))
    assert inspect.signature(invoke_phase_12_authorization_validation_callable_clock_v1).parameters["clock_binding"].kind is inspect.Parameter.KEYWORD_ONLY


def test_c05_03_unexpected_keyword_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(_CounterClock(object())), extra=object())
    assert len(inspect.signature(invoke_phase_12_authorization_validation_callable_clock_v1).parameters) == 1


def test_c06_01_missing_clock_attribute_raises_normal_attribute_error() -> None:
    with pytest.raises(AttributeError):
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=object())
    assert not hasattr(object(), "clock")


def test_c06_02_non_callable_clock_value_raises_normal_type_error() -> None:
    with pytest.raises(TypeError):
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(object()))
    assert _BindingLike(object()).clock is not None


def test_c06_03_structurally_valid_binding_like_object_uses_normal_python_behavior() -> None:
    result = object()
    assert invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(lambda: result)) is result


def test_c07_01_callable_exception_instance_propagates_unchanged() -> None:
    error = RuntimeError("clock")
    def raising_clock() -> object:
        raise error
    with pytest.raises(RuntimeError) as captured:
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert captured.value is error


def test_c07_02_operation_does_not_translate_callable_exception() -> None:
    error = ValueError("unchanged")
    def raising_clock() -> object:
        raise error
    with pytest.raises(ValueError) as captured:
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert captured.value is error


def test_c07_03_operation_does_not_retry_after_callable_exception() -> None:
    attempts, error = [], RuntimeError("one")
    def raising_clock() -> object:
        attempts.append(object())
        raise error
    with pytest.raises(RuntimeError):
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert len(attempts) == 1


def test_c08_01_custom_base_exception_propagates_unchanged() -> None:
    class _ClockBaseException(BaseException):
        __slots__ = ()
    error = _ClockBaseException()
    def raising_clock() -> object:
        raise error
    with pytest.raises(_ClockBaseException) as captured:
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert captured.value is error


def test_c08_02_keyboard_interrupt_propagates_unchanged() -> None:
    error = KeyboardInterrupt()
    def raising_clock() -> object:
        raise error
    with pytest.raises(KeyboardInterrupt) as captured:
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert captured.value is error


def test_c08_03_system_exit_propagates_unchanged() -> None:
    error = SystemExit(7)
    def raising_clock() -> object:
        raise error
    with pytest.raises(SystemExit) as captured:
        invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(raising_clock))
    assert captured.value is error


def test_c09_01_operation_source_has_no_binding_or_callable_validation() -> None:
    names = {node.id for node in ast.walk(_operation_node()) if isinstance(node, ast.Name)}
    assert {"isinstance", "callable", "hasattr", "getattr"}.isdisjoint(names)


def test_c09_02_operation_source_has_no_retry_fallback_or_duplicate_acquisition() -> None:
    node = _operation_node()
    assert len(node.body) == 1 and not any(isinstance(child, (ast.For, ast.While, ast.Try)) for child in ast.walk(node))


def test_c09_03_operation_source_has_no_cache_conversion_wrapper_or_result_storage() -> None:
    names = {node.id.lower() for node in ast.walk(_operation_node()) if isinstance(node, ast.Name)}
    assert {"cache", "memoize", "copy", "convert", "wrapper", "proxy", "adapter", "partial"}.isdisjoint(names)


def test_c10_01_module_source_has_no_system_time_or_environment_access() -> None:
    names = {node.id.lower() for node in ast.walk(_operation_tree()) if isinstance(node, ast.Name)}
    assert {"datetime", "date", "time", "getenv", "environ"}.isdisjoint(names)


def test_c10_02_module_source_has_no_filesystem_git_repository_replay_subprocess_or_network_access() -> None:
    names = {node.id.lower() for node in ast.walk(_operation_tree()) if isinstance(node, ast.Name)}
    assert {"open", "path", "subprocess", "git", "repository", "replay", "socket", "request"}.isdisjoint(names)


def test_c10_03_module_source_has_no_context_coordinator_runtime_service_provider_telegram_or_activation_access() -> None:
    names = {node.id.lower() for node in ast.walk(_operation_tree()) if isinstance(node, ast.Name)}
    assert {"context", "coordinator", "runtime", "service", "provider", "telegram", "activation"}.isdisjoint(names)


def test_c11_01_invocation_module_imports_only_locked_public_binding_dependency() -> None:
    imports = [(node.module, [alias.name for alias in node.names]) for node in _operation_tree().body if isinstance(node, ast.ImportFrom)]
    assert imports == [("engine.phase_12_authorization_validation_injected_callable_clock_v1", ["Phase12AuthorizationValidationInjectedCallableClockV1"])]


def test_c11_02_locked_binding_module_imports_no_invocation_module() -> None:
    source = (_repository_root() / "engine" / "phase_12_authorization_validation_injected_callable_clock_v1.py").read_text()
    assert "phase_12_authorization_validation_callable_clock_invocation_v1" not in source


def test_c11_03_locked_consumers_import_no_invocation_module() -> None:
    target = "phase_12_authorization_validation_callable_clock_invocation_v1"
    paths = ["phase_12_authorization_repository_validation_composition_v1.py", "phase_12_authorization_validation_repository_orchestration_composition_v1.py", "phase_12_bounded_authorization_validation_composition_v1.py", "phase_12_bounded_authorization_validation_callable_adapter_v1.py", "phase_12_activation_mode_validation_coordinator_v1.py"]
    assert all(target not in (_repository_root() / "engine" / path).read_text() for path in paths)


def test_c12_01_public_contract_claims_only_exactly_once_opaque_invocation() -> None:
    annotations = inspect.get_annotations(invoke_phase_12_authorization_validation_callable_clock_v1, eval_str=True)
    assert annotations == {"clock_binding": Phase12AuthorizationValidationInjectedCallableClockV1, "return": object}


def test_c12_02_public_contract_does_not_claim_temporal_authorization_runtime_or_production_validity() -> None:
    public_text = " ".join(filter(None, (invocation_module.__doc__, inspect.getdoc(invoke_phase_12_authorization_validation_callable_clock_v1)))).lower()
    assert not any(term in public_text for term in ("datetime", "timezone", "freshness", "authorization validity", "runtime readiness", "production"))


def test_c12_03_returned_object_can_be_forwarded_later_without_invocation_module_wiring_consumers() -> None:
    result = object()
    returned = invoke_phase_12_authorization_validation_callable_clock_v1(clock_binding=_BindingLike(lambda: result))
    assert returned is result and "phase_12_bounded_authorization_validation_composition_v1" not in inspect.getsource(invocation_module)
