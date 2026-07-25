import pytest
from engine.phase_12_activation_configuration_v1 import Phase12ActivationConfigurationErrorV1, _configuration_from_text
from datetime import datetime, timezone

def test_closed_remains_valid():
    config_text = "schema_version=phase12-activation-v1\nactivation_mode=CLOSED\nowner_authorization_id=NONE\napproval_checkpoint_id=NONE\napproved_locked_commit=NONE\napproved_at=NONE\nexpires_at=NONE\n"
    res = _configuration_from_text(config_text, now_utc=datetime.now(timezone.utc))
    assert res.activation_mode == "CLOSED"

def test_stage_a_observe_is_accepted():
    config_text = "schema_version=phase12-activation-v1\nactivation_mode=STAGE_A_OBSERVE\nowner_authorization_id=testowner\napproval_checkpoint_id=testcheckpoint\napproved_locked_commit=" + "a"*40 + "\napproved_at=2026-07-25T00:00:00Z\nexpires_at=2026-07-25T23:59:59Z\n"
    try:
        res = _configuration_from_text(config_text, now_utc=datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc))
        assert res.activation_mode == "STAGE_A_OBSERVE"
    except Phase12ActivationConfigurationErrorV1 as e:
        assert False, f"Stage A Observe config rejected: {e.code}"
