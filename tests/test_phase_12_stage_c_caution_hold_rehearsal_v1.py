import pytest
from engine.controlled_production_signal_cycle_v1 import run_controlled_production_signal_cycle

def test_stage_c_caution_hold_rehearsal():
    from engine.phase_12_activation_configuration_v1 import _GATES
    assert "STAGE_C_CAUTION_HOLD" in _GATES
