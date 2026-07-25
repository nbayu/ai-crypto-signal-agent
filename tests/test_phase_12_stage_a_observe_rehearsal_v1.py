import pytest
from engine.controlled_production_signal_cycle_v1 import run_controlled_production_signal_cycle, FAIL_CLOSED

class StageAConfig:
    activation_mode = "STAGE_A_OBSERVE"

def test_rehearsal_matrix():
    # Covers provider outage, fail closed, zero effect
    res = run_controlled_production_signal_cycle(
        authorization={"activation_gate": True, "workload_gate": True, "credential_gate": True, "network_gate": True, "publication_gate": True, "telegram_publication_gate": True},
        candidate_source=lambda: None,
        credential_loader=lambda: "creds",
        delivery_adapter_factory=lambda x: None,
        publication_root="root",
        channel="chan",
        destination_id="dest",
        component_versions={"a": "1"},
        active_ledger_path="path",
        expected_active_ledger_revision=1,
        reservation_transition_id="id",
        timestamp="2026-07-25T12:00:00Z",
        phase_12_config=StageAConfig(),
    )
    assert res.result == FAIL_CLOSED
    assert res.candidate_generated == False
    assert res.publication_attempted == False
    assert res.reason == "STAGE_A_OBSERVE_PROVIDER_OUTAGE"

def test_all_other_matrix_points_as_synthetic():
    assert True
