import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import engine.master_engine_v4 as master_module
import engine.production_signal_service_v1 as service_module
import engine.run_production_signal_v1 as entrypoint_module
from engine.production_signal_contract_v1 import DELIVERY_FAILED, DELIVERY_SUCCEEDED


SECRET_EXCEPTION = "EXCEPTION_MESSAGE_MARKER_09R1"
SECRET_TOKEN = "TELEGRAM_TOKEN_MARKER_09R1"
SECRET_DESTINATION = "DESTINATION_ID_MARKER_09R1"
SECRET_DEEPSEEK = "DEEPSEEK_KEY_MARKER_09R1"
SECRET_URL = "https://secret-marker.invalid/phase09r1"
SECRET_PAYLOAD = "PAYLOAD_CONTENT_MARKER_09R1"
SECRET_MARKERS = (
    SECRET_EXCEPTION,
    SECRET_TOKEN,
    SECRET_DESTINATION,
    SECRET_DEEPSEEK,
    SECRET_URL,
    SECRET_PAYLOAD,
)


class InjectedSecretError(RuntimeError):
    pass


class SecretFloat:
    def __float__(self):
        raise InjectedSecretError(SECRET_EXCEPTION)


class CountingAdapter:
    def __init__(self, *, receipt=None, failure=None):
        self.rejection_reason = None
        self.malformed_receipt = False
        self.calls = 0
        self.receipt = receipt or {
            "channel": "TELEGRAM",
            "destination_id": SECRET_DESTINATION,
            "external_delivery_id": "message-1",
            "delivered_at": "2026-07-26T12:00:00Z",
        }
        self.failure = failure

    def __call__(self, payload, *, channel, destination_id):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return dict(self.receipt)


@pytest.fixture
def valid_env(tmp_path):
    return {
        "DEEPSEEK_API_KEY": SECRET_DEEPSEEK,
        "TELEGRAM_BOT_TOKEN": SECRET_TOKEN,
        "TELEGRAM_DESTINATION_ID": SECRET_DESTINATION,
        "TELEGRAM_QUOTA_LIMIT": "1",
        "TELEGRAM_SLOT_CAPACITY": "1",
        "TELEGRAM_WINDOW_ID": "phase09r1-test",
        "TELEGRAM_QUOTA_STATE_PATH": str(tmp_path / "quota.json"),
        "TELEGRAM_WORKER_STATE_PATH": str(tmp_path / "worker.json"),
        "TELEGRAM_MAX_MESSAGE_LENGTH": "4000",
        "PRODUCTION_SIGNAL_DIR": str(tmp_path / "publications"),
    }


def _setup(symbol="TEST/USDT"):
    return {
        "symbol": symbol,
        "side": "LONG",
        "entry_zone": {"min": 100.0, "max": 101.0},
        "stop_loss": 95.0,
        "take_profit": {"tp1": 110.0, "tp2": 115.0},
        "valid_until": "2026-12-31T23:59:59Z",
        "strategy_version": "v4",
        "source_payload_hash": hashlib.sha256(b"source").hexdigest(),
    }


def _source_envelope(*, outcome_kind="PUBLISHED_SIGNAL", symbol="TEST/USDT"):
    setups = [] if outcome_kind == "NO_TRADE" else [_setup(symbol)]
    return {
        "schema_version": 1,
        "schema_name": "production-signal-input",
        "source_commit": "1" * 40,
        "source_evaluation_id": "eval-phase09r1-test",
        "mode": "SWING",
        "evaluated_at": "2026-07-26T12:00:00Z",
        "production_evidence_ref": {
            "manifest_hash": "2" * 64,
            "manifest_path": "evidence/manifest.json",
        },
        "outcome_kind": outcome_kind,
        "eligible_setups": setups,
        "component_versions": {"master_engine": "v4"},
    }


def _invoke_main(monkeypatch, capsys, valid_env, run_master, adapter):
    constructor_calls = []

    def build_adapter(
        config,
        *,
        available_slots_provider=None,
        message_binding_recorder=None,
    ):
        constructor_calls.append(
            {
                "config": config,
                "available_slots_provider": available_slots_provider,
                "message_binding_recorder": message_binding_recorder,
            }
        )
        return adapter

    monkeypatch.setattr(
        entrypoint_module,
        "Phase09RTelegramDeliveryAdapterV1",
        build_adapter,
    )
    monkeypatch.setattr(entrypoint_module, "run_master_engine_v4", run_master)
    with patch.dict(os.environ, valid_env, clear=True):
        exit_code = entrypoint_module.main()
    assert len(constructor_calls) == 1
    assert constructor_calls[0]["available_slots_provider"] is None
    assert constructor_calls[0]["message_binding_recorder"] is None
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


def _assert_single_event(stderr, *, stage, code, boundary):
    lines = stderr.splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert list(event) == [
        "event",
        "schema_version",
        "exit_code",
        "failure_code",
        "failure_stage",
        "exception_class",
        "telegram_boundary_reached",
    ]
    assert set(event) == {
        "event",
        "schema_version",
        "exit_code",
        "failure_code",
        "failure_stage",
        "exception_class",
        "telegram_boundary_reached",
    }
    assert event["event"] == "PHASE09R_EXIT7"
    assert event["schema_version"] == 1
    assert event["exit_code"] == 7
    assert event["failure_stage"] == stage
    assert event["failure_code"] == code
    assert event["exception_class"]
    assert event["telegram_boundary_reached"] == boundary
    assert event["telegram_boundary_reached"] in {"NO", "YES", "UNKNOWN"}
    assert stderr.endswith("\n")
    return event


def _master_fakes(tmp_path, final_top5, evidence_path):
    return {
        "scanner": lambda: [],
        "pipeline": lambda results: {"final_top5": final_top5},
        "snapshot_saver": lambda out, now: tmp_path / "snapshot.json",
        "outcome_saver": lambda out, **kwargs: tmp_path / "outcome.json",
        "watchlist_saver": lambda out: tmp_path / "watchlist.json",
        "pre_delivery_runner": lambda *args, **kwargs: {
            "delivery_artifact_path": tmp_path / "delivery.json",
            "tradingview_watchlist_path": tmp_path / "watchlist.txt",
        },
        "production_evidence_saver": lambda **kwargs: evidence_path,
        "now_provider": lambda: datetime(2026, 7, 26, 12, 0, 0),
    }


def _service_master(source, publication_root):
    def run_master(**kwargs):
        result = service_module.run_production_signal_service_v1(
            source_envelope=source,
            publication_root=publication_root,
            channel="TELEGRAM",
            destination_id=SECRET_DESTINATION,
            published_at=source["evaluated_at"],
            delivery_adapter=kwargs["delivery_adapter"],
            component_versions={"master_engine": "v4"},
        )
        return {"production_signal_out": result}

    return run_master


def test_master_setup_failure_is_sanitized_before_adapter(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    setup = _setup()
    setup["entry_zone"]["min"] = SecretFloat()
    publication_root = Path(valid_env["PRODUCTION_SIGNAL_DIR"])

    def run_master(**kwargs):
        return master_module.run_master_engine_v4(
            **kwargs,
            **_master_fakes(
                tmp_path,
                [setup],
                tmp_path / "unused-evidence.json",
            ),
        )

    exit_code, stdout, stderr = _invoke_main(
        monkeypatch, capsys, valid_env, run_master, adapter
    )
    assert exit_code == 7
    assert stdout == ""
    event = _assert_single_event(
        stderr,
        stage="ELIGIBLE_SETUP_CONSTRUCTION",
        code="MASTER_ENGINE_SETUP_CONSTRUCTION_FAILED",
        boundary="NO",
    )
    assert event["exception_class"] == "InjectedSecretError"
    assert SECRET_EXCEPTION not in stderr
    assert adapter.calls == 0
    assert not publication_root.exists()
    assert not Path(valid_env["TELEGRAM_QUOTA_STATE_PATH"]).exists()


def test_source_envelope_failure_is_sanitized_before_adapter(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    evidence_path = tmp_path / SECRET_EXCEPTION / "evidence.json"

    def run_master(**kwargs):
        return master_module.run_master_engine_v4(
            **kwargs,
            **_master_fakes(tmp_path, [_setup()], evidence_path),
        )

    exit_code, stdout, stderr = _invoke_main(
        monkeypatch, capsys, valid_env, run_master, adapter
    )
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage="SOURCE_ENVELOPE_CONSTRUCTION",
        code="MASTER_ENGINE_SOURCE_ENVELOPE_FAILED",
        boundary="NO",
    )
    assert SECRET_EXCEPTION not in stderr
    assert adapter.calls == 0


def test_intent_persistence_failure_is_sanitized_without_delivery(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    root = tmp_path / "intent-persist"

    def fail_intent(**kwargs):
        raise InjectedSecretError(SECRET_EXCEPTION)

    monkeypatch.setattr(service_module, "publish_publication_intent", fail_intent)
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(_source_envelope(), root),
        adapter,
    )
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage="PUBLICATION_INTENT_PERSIST",
        code="PUBLICATION_INTENT_PERSIST_FAILED",
        boundary="NO",
    )
    assert adapter.calls == 0
    assert not root.exists()
    assert SECRET_EXCEPTION not in stdout + stderr


def test_completion_persistence_failure_is_yes_and_never_retries(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    root = tmp_path / "completion-persist"

    def fail_completion(**kwargs):
        raise InjectedSecretError(
            "|".join(
                (
                    SECRET_EXCEPTION,
                    SECRET_TOKEN,
                    SECRET_DESTINATION,
                    SECRET_DEEPSEEK,
                    SECRET_URL,
                    SECRET_PAYLOAD,
                )
            )
        )

    monkeypatch.setattr(
        service_module,
        "publish_completed_publication",
        fail_completion,
    )
    source = _source_envelope(symbol=SECRET_PAYLOAD)
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(source, root),
        adapter,
    )
    assert exit_code == 7
    _assert_single_event(
        stderr,
        stage="PUBLICATION_COMPLETION_PERSIST",
        code="PUBLICATION_COMPLETION_PERSIST_FAILED",
        boundary="YES",
    )
    assert adapter.calls == 1
    for marker in SECRET_MARKERS:
        assert marker not in stdout
        assert marker not in stderr


def test_final_readback_failure_is_yes_and_never_retries(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    root = tmp_path / "readback"

    def fail_readback(**kwargs):
        raise InjectedSecretError(SECRET_EXCEPTION)

    monkeypatch.setattr(service_module, "read_publication_artifact", fail_readback)
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(_source_envelope(), root),
        adapter,
    )
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(
        stderr,
        stage="PUBLICATION_READBACK",
        code="PUBLICATION_READBACK_FAILED",
        boundary="YES",
    )
    assert adapter.calls == 1
    assert SECRET_EXCEPTION not in stderr


@pytest.mark.parametrize(
    ("run_out", "stage", "code"),
    [
        (
            {},
            "PRODUCTION_SIGNAL_OUT_MISSING",
            "PRODUCTION_SIGNAL_OUT_MISSING",
        ),
        (
            {"production_signal_out": ["not", "a", "mapping"]},
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
        ),
        (
            {"production_signal_out": {"publication": []}},
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
            "PRODUCTION_SIGNAL_OUT_MALFORMED",
        ),
        (
            {"production_signal_out": {"status": "UNRECOGNIZED"}},
            "UNKNOWN_PRODUCTION_SIGNAL_OUTCOME",
            "UNKNOWN_PRODUCTION_SIGNAL_OUTCOME",
        ),
    ],
)
def test_entrypoint_outcome_classification(
    run_out,
    stage,
    code,
    monkeypatch,
    capsys,
    valid_env,
):
    adapter = CountingAdapter()
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        lambda **kwargs: run_out,
        adapter,
    )
    assert exit_code == 7
    assert stdout == ""
    _assert_single_event(stderr, stage=stage, code=code, boundary="UNKNOWN")
    assert adapter.calls == 0
    assert "Traceback" not in stderr


def test_successful_delivery_preserves_completed_publication(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    root = tmp_path / "success"
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(_source_envelope(), root),
        adapter,
    )
    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""
    assert adapter.calls == 1
    artifacts = list((root / "publications").rglob("*.json"))
    assert len(artifacts) == 1
    publication = json.loads(artifacts[0].read_text())
    assert publication["delivery_state"] == DELIVERY_SUCCEEDED
    assert publication["delivery_receipt"]["external_delivery_id"] == "message-1"


def test_no_trade_preserves_evaluation_without_adapter(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()
    root = tmp_path / "no-trade"
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(
            _source_envelope(outcome_kind="NO_TRADE"),
            root,
        ),
        adapter,
    )
    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""
    assert adapter.calls == 0
    evaluations = list((root / "evaluations").glob("*.json"))
    assert len(evaluations) == 1
    evaluation = json.loads(evaluations[0].read_text())
    assert evaluation["outcome_kind"] == "NO_TRADE"
    assert evaluation["delivery_state"] is None


def test_delivery_failed_remains_exit5_without_observability(
    tmp_path, monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter(
        failure=InjectedSecretError(
            "|".join((SECRET_EXCEPTION, SECRET_TOKEN, SECRET_PAYLOAD))
        )
    )
    root = tmp_path / "delivery-failed"
    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        _service_master(_source_envelope(), root),
        adapter,
    )
    assert exit_code == 5
    assert stdout == ""
    assert stderr == ""
    assert adapter.calls == 1
    artifacts = list((root / "publications").rglob("*.json"))
    assert len(artifacts) == 1
    publication = json.loads(artifacts[0].read_text())
    assert publication["delivery_state"] == DELIVERY_FAILED
    assert publication["delivery_receipt"] is None
    assert publication["failure"] == {
        "primary_code": "DELIVERY_ADAPTER_FAILED",
        "component": "delivery_adapter",
        "message": "delivery adapter failed",
    }


@pytest.mark.parametrize(
    ("adapter_field", "adapter_value", "expected_exit"),
    [
        ("rejection_reason", "QUOTA_EXHAUSTED", 5),
        ("rejection_reason", "SLOTS_FULL", 5),
        ("malformed_receipt", True, 6),
    ],
)
def test_quota_slot_and_malformed_receipt_exit_codes_are_unchanged(
    adapter_field,
    adapter_value,
    expected_exit,
    monkeypatch,
    capsys,
    valid_env,
):
    adapter = CountingAdapter()

    def run_master(**kwargs):
        setattr(adapter, adapter_field, adapter_value)
        return {
            "production_signal_out": {
                "publication": {"delivery_state": DELIVERY_FAILED}
            }
        }

    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        run_master,
        adapter,
    )
    assert exit_code == expected_exit
    assert adapter.calls == 0
    assert stdout == ""
    assert stderr == ""


def test_configuration_exit2_has_no_observability(capsys):
    with patch.dict(os.environ, {}, clear=True):
        assert entrypoint_module.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_unclassified_exception_event_schema_and_secret_leak_barrier(
    monkeypatch, capsys, valid_env
):
    adapter = CountingAdapter()

    def run_master(**kwargs):
        raise InjectedSecretError("|".join(SECRET_MARKERS))

    exit_code, stdout, stderr = _invoke_main(
        monkeypatch,
        capsys,
        valid_env,
        run_master,
        adapter,
    )
    assert exit_code == 7
    event = _assert_single_event(
        stderr,
        stage="MASTER_ENGINE_UNCLASSIFIED",
        code="MASTER_ENGINE_UNCLASSIFIED",
        boundary="UNKNOWN",
    )
    assert event["exception_class"] == "InjectedSecretError"
    assert stdout == ""
    for marker in SECRET_MARKERS:
        assert marker not in stdout
        assert marker not in stderr
