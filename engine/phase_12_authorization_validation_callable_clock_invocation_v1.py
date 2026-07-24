from engine.phase_12_authorization_validation_injected_callable_clock_v1 import (
    Phase12AuthorizationValidationInjectedCallableClockV1,
)


def invoke_phase_12_authorization_validation_callable_clock_v1(
    *,
    clock_binding: Phase12AuthorizationValidationInjectedCallableClockV1,
) -> object:
    return clock_binding.clock()


__all__ = (
    "invoke_phase_12_authorization_validation_callable_clock_v1",
)
