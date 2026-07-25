import pytest
from engine.phase_12_activation_configuration_v1 import _configuration_from_text
from datetime import datetime, timezone

def test_stage_d_controlled_block_is_accepted():
    config_text = "schema_version=phase12-activation-v1\nactivation_mode=STAGE_D_CONTROLLED_BLOCK\nowner_authorization_id=testowner\napproval_checkpoint_id=testcheckpoint\napproved_locked_commit=" + "a"*40 + "\napproved_at=2026-07-25T00:00:00Z\nexpires_at=2026-07-25T23:59:59Z\n"
    # Will fail until Stage D is implemented
    res = _configuration_from_text(config_text, now_utc=datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc))
    assert res.activation_mode == "STAGE_D_CONTROLLED_BLOCK"
# Add drill tests
