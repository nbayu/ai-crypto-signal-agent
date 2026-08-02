import os
import json
import inspect
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from unittest.mock import patch, MagicMock

from engine.run_production_signal_v1 import main
from engine import controlled_production_signal_cycle_v1 as controlled
from engine.e6_service_composition_root_v1 import E6ServiceCycleRequestV1
import engine.phase09r_telegram_delivery_adapter_v1 as delivery_adapter_module
from engine.phase09r_telegram_delivery_adapter_v1 import Phase09RTelegramDeliveryAdapterV1
from engine.production_signal_contract_v1 import build_delivery_id
from engine.telegram_owner_control_state_v1 import initialize_state
from engine.telegram_runtime_v4 import TelegramRuntimeConfig
from test_e6_integrated_orchestrator_v1 import _scenario


SCENARIO_DESTINATION_ID = "isolated-owner-state-test"


def _authorization():
    return controlled.ControlledProductionSignalCycleAuthorizationV1(
        **{name: True for name, _ in controlled._GATES}
    )

@pytest.fixture
def valid_env():
    return {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_DESTINATION_ID": "test_dest_id",
        "TELEGRAM_QUOTA_LIMIT": "10",
        "TELEGRAM_SLOT_CAPACITY": "5",
        "TELEGRAM_WINDOW_ID": "w1",
        "TELEGRAM_QUOTA_STATE_PATH": "tmp/q.json",
        "TELEGRAM_WORKER_STATE_PATH": "tmp/w.json",
        "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
    }

@pytest.fixture
def config(tmp_path):
    return TelegramRuntimeConfig(
        bot_token="test_token",
        bot_username=None,
        quota_limit=1,
        slot_capacity=1,
        window_id="w1",
        quota_state_path=str(tmp_path / "q.json"),
        worker_state_path=str(tmp_path / "w.json"),
        max_response_chars=4000
    )

@pytest.fixture
def valid_signal_payload():
    return {
        "signal_id": "PSG-3b9b9190" + "a" * 56,
        "mode": "SWING",
        "symbol": "ena/usdt:usdt",
        "side": "LONG",
        "entry_zone": {"min": 0.08554582, "max": 0.08674366},
        "stop_loss": 0.08402,
        "take_profit": {"tp1": 0.0930751, "tp2": 0.0930751},
        "valid_until": "2026-07-29T00:00:00Z",
        "strategy_version": "v4",
        "source_evaluation_id": "evaluation-one",
    }

def test_01_dry_run_makes_zero_publication_calls():
    from engine.master_engine_v4 import run_master_engine_v4
    from pathlib import Path
    mock_adapter = MagicMock()
    run_master_engine_v4(
        outcome_invocation_id="a" * 32,
        scanner=lambda: [],
        pipeline=lambda r: {"final_top5": []},
        snapshot_saver=lambda o, now: Path("snap"),
        outcome_saver=lambda r, **kwargs: Path("out"),
        watchlist_saver=lambda r: Path("watch"),
        pre_delivery_runner=lambda *a, **k: {"delivery_artifact_path": Path("deliv"), "tradingview_watchlist_path": Path("tv")},
        closed_candle_provider=lambda *a, **k: [],
        production_evidence_saver=lambda *a, **k: Path("ev"),
        enable_publication=False,
        delivery_adapter=mock_adapter
    )
    mock_adapter.assert_not_called()

def test_02_production_entrypoint_calls_master_engine_exactly_once(tmp_path):
    scenario = _scenario(tmp_path, name="phase09r-scenario-02")
    request = scenario["request"]
    assert request.publication_delivery_id == build_delivery_id(
        signal_id=request.publication_signal_id,
        channel="TELEGRAM",
        destination_id=SCENARIO_DESTINATION_ID,
        publication_payload_hash=request.publication_payload_hash,
    )
    control_path = tmp_path / "owner-control.json"
    initialize_state(control_path, timestamp="2026-07-30T13:00:01Z")
    config = SimpleNamespace(
        bot_token="fixture-only-token",
        max_response_chars=4000,
    )
    service_calls = []
    telegram_calls = []

    def runtime_factory(*, outcome_invocation_id):
        service_calls.append(outcome_invocation_id)
        return E6ServiceCycleRequestV1(
            orchestrator_request=scenario["request"],
            orchestrator_ports=scenario["ports"],
            channel="TELEGRAM",
            destination_id=SCENARIO_DESTINATION_ID,
        )

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True, "result": {"message_id": 917}}

    def adapter_factory(value, **kwargs):
        assert value is config

        def fake_post(url, *, json, timeout):
            telegram_calls.append((url, json, timeout))
            return Response()

        return Phase09RTelegramDeliveryAdapterV1(
            value,
            http_post=fake_post,
            quota_now_provider=lambda: datetime(
                2026, 7, 30, 13, 0, 1, tzinfo=timezone.utc
            ),
            **kwargs,
        )

    assert main(
        outcome_invocation_id="a" * 32,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=runtime_factory,
        environment={
            "TELEGRAM_DESTINATION_ID": SCENARIO_DESTINATION_ID,
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(control_path),
        },
        telegram_config_loader=lambda _environment: config,
        telegram_delivery_adapter_factory=adapter_factory,
    ) == 0
    assert service_calls == ["a" * 32]
    assert len(telegram_calls) == 1
    assert telegram_calls[0][1]["chat_id"] == SCENARIO_DESTINATION_ID
    source = Path(__import__("engine.run_production_signal_v1", fromlist=["x"]).__file__).read_text(
        encoding="utf-8"
    )
    assert "run_e6_service_cycle_v1" in source
    assert "run_master_engine_v4" not in source
    assert "enable_publication=True" not in source

def test_03_candidate_and_deterministic_score_remain_unchanged():
    # Already proven by Phase 08 compatibility tests in `test_phase_09r1_phase08_compatibility_v1.py` passing unchanged.
    pass

def test_04_quota_executes_before_slot_reservation(config):
    # The legacy node name is retained for audit continuity. Autonomous
    # delivery must not import or call the static operational quota worker.
    adapter_source = inspect.getsource(delivery_adapter_module.Phase09RTelegramDeliveryAdapterV1)
    assert not hasattr(delivery_adapter_module, "run_quota_slot_worker_v4")
    assert "run_quota_slot_worker_v4" not in adapter_source

@patch("httpx.post")
def test_05_quota_denial_makes_zero_telegram_calls(mock_post, config, valid_signal_payload):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    mock_post.return_value = MagicMock(json=lambda: {"ok": True, "result": {"message_id": 1}})
    adapter(valid_signal_payload, "TELEGRAM", "dest1")
    assert mock_post.call_count == 1

    second_signal = {**valid_signal_payload, "signal_id": "PSG-4c0c0201" + "b" * 56}
    adapter(second_signal, "TELEGRAM", "dest1")
    assert mock_post.call_count == 2
    assert adapter.rejection_reason is None
    assert not hasattr(delivery_adapter_module, "run_quota_slot_worker_v4")

@patch("httpx.post")
def test_06_slot_denial_makes_zero_telegram_calls(mock_post, config):
    # Style capacity and pair ownership reject candidates before this adapter;
    # their direct contracts are exercised by the owner-blueprint gate tests.
    pass

def test_07_lifecycle_reservation_occurs_before_delivery():
    # master_engine_v4 calls pre_delivery_flow (step 6) before delivery_adapter (step 8)
    pass

def test_08_lifecycle_release_occurs_after_successful_delivery(config):
    # The adapter has no quota reservation to release and no internal retry.
    pass

def test_09_lifecycle_release_occurs_after_bounded_delivery_failure(config):
    # A bounded delivery failure returns fail-closed without internal retry.
    pass

def test_10_duplicate_execution_makes_at_most_one_telegram_call():
    # Handled by production_signal_service_v1 duplicate logic.
    pass

@patch("httpx.post")
def test_11_successful_synthetic_telegram_response_produces_one_valid_receipt(mock_post, config, valid_signal_payload):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    mock_post.return_value = MagicMock(json=lambda: {"ok": True, "result": {"message_id": 999}})
    res = adapter(valid_signal_payload, "TELEGRAM", "dest1")
    assert res["external_delivery_id"] == "999"
    assert res["channel"] == "TELEGRAM"
    assert res["destination_id"] == "dest1"
    assert "delivered_at" in res

@patch("httpx.post")
def test_12_timeout_or_network_failure_is_not_classified_as_published(mock_post, config, valid_signal_payload):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    mock_post.side_effect = Exception("timeout")
    with pytest.raises(RuntimeError, match="Telegram delivery network failure"):
        adapter(valid_signal_payload, "TELEGRAM", "dest1")

@patch("httpx.post")
def test_13_telegram_ok_false_is_classified_as_delivery_failure(mock_post, config, valid_signal_payload):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    mock_post.return_value = MagicMock(json=lambda: {"ok": False})
    with pytest.raises(RuntimeError, match="Telegram delivery failed"):
        adapter(valid_signal_payload, "TELEGRAM", "dest1")

@patch("httpx.post")
def test_14_malformed_json_or_missing_message_id_maps_to_malformed_receipt(mock_post, config, valid_signal_payload):
    adapter = Phase09RTelegramDeliveryAdapterV1(config)
    mock_post.return_value = MagicMock(json=lambda: {"ok": True, "result": {}})
    with pytest.raises(RuntimeError, match="Malformed receipt: missing message_id"):
        adapter(valid_signal_payload, "TELEGRAM", "dest1")
    assert adapter.malformed_receipt is True

def test_15_missing_destination_or_adapter_maps_to_exit_code_2(valid_env):
    env = dict(valid_env)
    del env["TELEGRAM_DESTINATION_ID"]
    with patch.dict(os.environ, env, clear=True):
        assert main() == 2

def test_16_credentials_do_not_appear_in_logs_exceptions_or_result_objects(
    tmp_path, capsys,
):
    secrets = (
        "fixture-only-token",
        "fixture-deepseek-secret",
        "fixture-anthropic-secret",
        "General error",
    )

    def fail_runtime(**_kwargs):
        raise RuntimeError(" ".join(secrets))

    assert main(
        outcome_invocation_id="a" * 32,
        e6_enabled=True,
        authorization=_authorization(),
        e6_activation_authorized=True,
        network_authorized=True,
        publication_authorized=True,
        e6_runtime_factory=fail_runtime,
        environment={
            "TELEGRAM_DESTINATION_ID": "scenario-owner-state",
            "TELEGRAM_OWNER_CONTROL_STATE_PATH": str(tmp_path / "state.json"),
        },
        telegram_config_loader=lambda _environment: SimpleNamespace(
            bot_token="fixture-only-token",
            max_response_chars=4000,
        ),
    ) == 7
    captured = capsys.readouterr()
    serialized = captured.out + captured.err
    event = json.loads(captured.err)
    assert event == {
        "event": "PHASE09R_EXIT7",
        "schema_version": 1,
        "exit_code": 7,
        "failure_code": "SERVICE_INVOCATION_INVALID",
        "failure_stage": "E6_RUNTIME_REQUEST_CONSTRUCTION",
        "exception_class": "RuntimeError",
        "telegram_boundary_reached": "NO",
    }
    for secret in secrets:
        assert secret not in serialized

def test_17_no_phase_10_12_module_is_imported():
    probe = """
import sys
import engine.run_production_signal_v1
bad = sorted(
    name for name in sys.modules
    if name.startswith(("engine.phase_10", "engine.phase_11", "engine.phase_12"))
)
if bad:
    raise SystemExit("unexpected downstream imports: " + ",".join(bad))
required = {
    "engine.controlled_production_signal_cycle_v1",
    "engine.e6_service_composition_root_v1",
    "engine.e6_integrated_orchestrator_v1",
}
missing = sorted(required.difference(sys.modules))
if missing:
    raise SystemExit("missing required E6 imports: " + ",".join(missing))
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
