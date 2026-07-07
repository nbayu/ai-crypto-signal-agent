from datetime import datetime, timezone

import engine.run_forward_test_v4 as runner


def test_runner_resolves_then_validates(monkeypatch):
    calls = []

    now_utc = datetime(
        2026,
        7,
        7,
        12,
        0,
        tzinfo=timezone.utc,
    )

    def fake_resolve(entry_path, now_utc=None):
        calls.append(
            (
                "resolve",
                str(entry_path),
                now_utc,
            )
        )

        return {
            "entry_path": str(entry_path),
            "resolution_path": "resolved.json",
            "changed": True,
            "resolved_horizons_added": 3,
        }

    def fake_validate(resolved_path):
        calls.append(
            (
                "validate",
                str(resolved_path),
            )
        )

        return {
            "artifact_type":
                "forward_test_validation_report_v4",
            "schema_version": 1,
            "snapshot_status": "PARTIAL",
        }

    monkeypatch.setattr(
        runner,
        "resolve_entry_artifact",
        fake_resolve,
    )
    monkeypatch.setattr(
        runner,
        "validate_resolved_artifact",
        fake_validate,
    )

    result = runner.run_forward_test_v4(
        "entry.json",
        now_utc=now_utc,
    )

    assert calls == [
        (
            "resolve",
            "entry.json",
            now_utc,
        ),
        (
            "validate",
            "resolved.json",
        ),
    ]

    assert list(result.keys()) == [
        "resolution",
        "validation",
    ]

    assert result["resolution"] == {
        "entry_path": "entry.json",
        "resolution_path": "resolved.json",
        "changed": True,
        "resolved_horizons_added": 3,
    }

    assert result["validation"] == {
        "artifact_type":
            "forward_test_validation_report_v4",
        "schema_version": 1,
        "snapshot_status": "PARTIAL",
    }
