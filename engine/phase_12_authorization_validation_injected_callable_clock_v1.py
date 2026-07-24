from collections.abc import Callable
from dataclasses import dataclass


__all__ = (
    "Phase12AuthorizationValidationInjectedCallableClockV1",
    "build_phase_12_authorization_validation_injected_callable_clock_v1",
)


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class Phase12AuthorizationValidationInjectedCallableClockV1:
    clock: Callable[[], object]


def build_phase_12_authorization_validation_injected_callable_clock_v1(
    *,
    clock: Callable[[], object],
) -> Phase12AuthorizationValidationInjectedCallableClockV1:
    return Phase12AuthorizationValidationInjectedCallableClockV1(clock=clock)
