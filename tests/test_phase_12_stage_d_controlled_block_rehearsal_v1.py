import pytest

def test_stage_d_controlled_block_rehearsal():
    from engine.phase_12_activation_configuration_v1 import _GATES
    assert "STAGE_D_CONTROLLED_BLOCK" in _GATES
