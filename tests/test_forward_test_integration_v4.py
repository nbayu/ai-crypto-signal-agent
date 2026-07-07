import json

import pytest

import engine.forward_test_integration_v4 as integration


def build_manifest(tmp_path, outcome_entry="outcome.json"):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "snapshot_type": "v4_production_evidence",
                "schema_version": 1,
                "created_at": "2026-07-07T20:00:00",
                "artifacts": {
                    "validated_snapshot": "validated.json",
                    "outcome_entry": outcome_entry,
                    "raw_top5": "raw_top5.json",
                    "pre_delivery": "pre_delivery.json",
                    "tradingview_watchlist": "watchlist.txt",
                },
            }
        )
    )
    return manifest


def test_integration_uses_exact_manifest_outcome_entry(
    tmp_path,
    monkeypatch,
):
    manifest = build_manifest(
        tmp_path,
        outcome_entry="data/v4_outcomes/outcome_entry_v4_exact.json",
    )

    calls = []

    def fake_run(entry_path, now_utc=None):
        calls.append((str(entry_path), now_utc))
        return {
            "resolution": {"changed": True},
            "validation": {"snapshot_status": "PARTIAL"},
        }

    monkeypatch.setattr(
        integration,
        "run_forward_test_v4",
        fake_run,
    )

    result = integration.run_forward_test_from_production_evidence(
        manifest
    )

    assert calls == [
        (
            "data/v4_outcomes/outcome_entry_v4_exact.json",
            None,
        )
    ]

    assert result["production_evidence_path"] == str(
        manifest
    )
    assert result["outcome_entry_path"] == (
        "data/v4_outcomes/outcome_entry_v4_exact.json"
    )
    assert result["forward_test"] == {
        "resolution": {"changed": True},
        "validation": {"snapshot_status": "PARTIAL"},
    }


@pytest.mark.parametrize(
    "mutation",
    [
        lambda manifest: manifest.update(
            snapshot_type="wrong"
        ),
        lambda manifest: manifest.update(
            schema_version=2
        ),
        lambda manifest: manifest.pop("artifacts"),
        lambda manifest: manifest["artifacts"].pop(
            "outcome_entry"
        ),
    ],
)
def test_integration_rejects_invalid_production_evidence(
    tmp_path,
    mutation,
):
    manifest_path = build_manifest(tmp_path)

    manifest = json.loads(
        manifest_path.read_text()
    )
    mutation(manifest)
    manifest_path.write_text(
        json.dumps(manifest)
    )

    with pytest.raises(ValueError):
        integration.run_forward_test_from_production_evidence(
            manifest_path
        )


def test_integration_does_not_discover_latest_artifact(
    tmp_path,
    monkeypatch,
):
    manifest = build_manifest(
        tmp_path,
        outcome_entry="exact-entry.json",
    )

    called = []

    def fake_run(entry_path, now_utc=None):
        called.append(str(entry_path))
        return {
            "resolution": {},
            "validation": {},
        }

    monkeypatch.setattr(
        integration,
        "run_forward_test_v4",
        fake_run,
    )

    integration.run_forward_test_from_production_evidence(
        manifest
    )

    assert called == ["exact-entry.json"]


def test_integration_rejects_malformed_json(
    tmp_path,
):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{not-json")

    with pytest.raises(
        ValueError,
        match="Invalid production evidence JSON",
    ):
        integration.run_forward_test_from_production_evidence(
            manifest
        )


def test_integration_rejects_non_object_manifest(
    tmp_path,
):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")

    with pytest.raises(
        ValueError,
        match="Production evidence must be an object",
    ):
        integration.run_forward_test_from_production_evidence(
            manifest
        )


@pytest.mark.parametrize(
    "outcome_entry",
    [
        None,
        123,
        [],
        {},
        "",
        "   ",
    ],
)
def test_integration_rejects_invalid_outcome_entry_path(
    tmp_path,
    outcome_entry,
):
    manifest = build_manifest(
        tmp_path,
        outcome_entry=outcome_entry,
    )

    with pytest.raises(
        ValueError,
        match="Invalid production evidence outcome_entry",
    ):
        integration.run_forward_test_from_production_evidence(
            manifest
        )


def test_integration_forwards_now_utc_exactly(
    tmp_path,
    monkeypatch,
):
    from datetime import datetime, timezone

    manifest = build_manifest(
        tmp_path,
        outcome_entry="exact-entry.json",
    )

    now_utc = datetime(
        2026,
        7,
        8,
        12,
        10,
        tzinfo=timezone.utc,
    )

    calls = []

    def fake_run(entry_path, now_utc=None):
        calls.append(
            (
                str(entry_path),
                now_utc,
            )
        )
        return {
            "resolution": {},
            "validation": {},
        }

    monkeypatch.setattr(
        integration,
        "run_forward_test_v4",
        fake_run,
    )

    integration.run_forward_test_from_production_evidence(
        manifest,
        now_utc=now_utc,
    )

    assert calls == [
        (
            "exact-entry.json",
            now_utc,
        )
    ]
