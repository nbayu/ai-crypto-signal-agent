import json

from engine.production_evidence_v4 import (
    save_production_evidence,
)


def test_save_creates_immutable_production_run_bundle(
    tmp_path,
):
    validated = tmp_path / "validated.json"
    outcome = tmp_path / "outcome.json"
    raw_top5 = tmp_path / "latest.json"
    pre_delivery = tmp_path / "delivery.json"
    tradingview = tmp_path / "watchlist.txt"

    validated.write_text("validated")
    outcome.write_text("outcome")
    raw_top5.write_text('{"raw": true}')
    pre_delivery.write_text('{"eligible": true}')
    tradingview.write_text("BINANCE:AAAUSDT.P")

    evidence_root = tmp_path / "evidence"

    manifest_path = save_production_evidence(
        created_at="2026-07-07T20:00:00",
        validated_snapshot_path=validated,
        outcome_entry_path=outcome,
        raw_top5_path=raw_top5,
        pre_delivery_path=pre_delivery,
        tradingview_watchlist_path=tradingview,
        directory=evidence_root,
    )

    assert manifest_path.name == "manifest.json"
    assert manifest_path.parent.parent == evidence_root
    assert manifest_path.parent.name.startswith(
        "production_run_v4_"
    )

    manifest = json.loads(
        manifest_path.read_text()
    )

    assert manifest["snapshot_type"] == (
        "v4_production_evidence"
    )
    assert manifest["schema_version"] == 1
    assert manifest["created_at"] == (
        "2026-07-07T20:00:00"
    )

    artifacts = manifest["artifacts"]

    assert artifacts["validated_snapshot"] == str(
        validated
    )
    assert artifacts["outcome_entry"] == str(
        outcome
    )

    raw_copy = manifest_path.parent / "raw_top5.json"
    delivery_copy = (
        manifest_path.parent / "pre_delivery.json"
    )
    tradingview_copy = (
        manifest_path.parent
        / "tradingview_watchlist.txt"
    )

    assert artifacts["raw_top5"] == str(raw_copy)
    assert artifacts["pre_delivery"] == str(
        delivery_copy
    )
    assert artifacts["tradingview_watchlist"] == str(
        tradingview_copy
    )

    assert raw_copy.read_text() == '{"raw": true}'
    assert delivery_copy.read_text() == (
        '{"eligible": true}'
    )
    assert tradingview_copy.read_text() == (
        "BINANCE:AAAUSDT.P"
    )


def test_bundle_preserves_evidence_after_sources_change(
    tmp_path,
):
    validated = tmp_path / "validated.json"
    outcome = tmp_path / "outcome.json"
    raw_top5 = tmp_path / "latest.json"
    pre_delivery = tmp_path / "delivery.json"
    tradingview = tmp_path / "watchlist.txt"

    validated.write_text("validated")
    outcome.write_text("outcome")
    raw_top5.write_text("raw-before")
    pre_delivery.write_text("delivery-before")
    tradingview.write_text("watchlist-before")

    manifest_path = save_production_evidence(
        created_at="2026-07-07T20:00:00",
        validated_snapshot_path=validated,
        outcome_entry_path=outcome,
        raw_top5_path=raw_top5,
        pre_delivery_path=pre_delivery,
        tradingview_watchlist_path=tradingview,
        directory=tmp_path / "evidence",
    )

    raw_top5.write_text("raw-after")
    pre_delivery.write_text("delivery-after")
    tradingview.write_text("watchlist-after")

    run_directory = manifest_path.parent

    assert (
        run_directory / "raw_top5.json"
    ).read_text() == "raw-before"
    assert (
        run_directory / "pre_delivery.json"
    ).read_text() == "delivery-before"
    assert (
        run_directory / "tradingview_watchlist.txt"
    ).read_text() == "watchlist-before"


def test_final_report_exposes_production_evidence_path():
    from engine.final_reporter_v4 import (
        render_final_report_v4,
    )

    out = {
        "controlled_top10": [],
        "final_top5": [],
        "usage": {},
    }

    report = render_final_report_v4(
        out,
        snapshot_path="snapshot.json",
        evidence_path="manifest.json",
    )

    assert "SNAPSHOT SAVED: snapshot.json" in report
    assert (
        "PRODUCTION EVIDENCE SAVED: manifest.json"
        in report
    )
