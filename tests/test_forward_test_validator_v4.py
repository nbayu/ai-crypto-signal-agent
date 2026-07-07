import json

from engine.forward_test_validator_v4 import validate_resolved_artifact

import pytest


REFERENCE_CANDLE_AT = "2026-07-06T08:00:00"

TARGET_AT = {
    "h4": "2026-07-06T16:00:00+00:00",
    "h8": "2026-07-06T20:00:00+00:00",
    "h12": "2026-07-07T00:00:00+00:00",
}


def entry_candidate(
    symbol="TEST/USDT:USDT",
    *,
    reference_price=100.0,
    trend="UPTREND",
    python_score=90.0,
    validation_adjustment=0,
    final_rank_score=90.0,
    bos=True,
    choch=False,
    volume_ratio=1.5,
    volume_class="STRONG",
    oi_change_pct=1.0,
    oi_class="STRONG",
    participation="STRONG",
    ai_status="CLEAR",
    false_breakout_risk="LOW",
    confluence="STRONG",
    reason_code="ALIGNED",
):
    return {
        "symbol": symbol,
        "reference_price": reference_price,
        "reference_candle_at": REFERENCE_CANDLE_AT,
        "python_score": python_score,
        "validation_adjustment": validation_adjustment,
        "final_rank_score": final_rank_score,
        "trend": trend,
        "bos": bos,
        "choch": choch,
        "volume_ratio": volume_ratio,
        "volume_class": volume_class,
        "oi_change_pct": oi_change_pct,
        "oi_class": oi_class,
        "participation": participation,
        "ai_validation": {
            "status": ai_status,
            "false_breakout_risk": false_breakout_risk,
            "confluence": confluence,
            "reason_code": reason_code,
        },
    }


def entry_artifact(candidates):
    return {
        "snapshot_type": "v4_outcome_tracker_entry",
        "schema_version": 1,
        "captured_at": "2026-07-06T14:19:11.994572",
        "candidates": candidates,
    }


def horizon_result(horizon, return_pct, *, mfe_pct=4.0, mae_pct=-2.0):
    return {
        "horizon": horizon,
        "target_at": TARGET_AT[horizon],
        "return_price": 100.0 + return_pct,
        "return_pct": return_pct,
        "mfe_price": 104.0,
        "mfe_pct": mfe_pct,
        "mae_price": 98.0,
        "mae_pct": mae_pct,
    }


def resolved_candidate(
    symbol="TEST/USDT:USDT",
    *,
    reference_price=100.0,
    horizons=None,
):
    if horizons is None:
        horizons = {
            "h4": horizon_result("h4", 1.0),
            "h8": horizon_result("h8", 1.0),
            "h12": horizon_result("h12", 1.0),
        }

    return {
        "symbol": symbol,
        "reference_price": reference_price,
        "resolved_horizons": horizons,
    }


def resolved_artifact(entry_name, candidates):
    return {
        "snapshot_type": "v4_forward_outcome_resolution",
        "schema_version": 1,
        "entry_artifact": entry_name,
        "entry_snapshot_type": "v4_outcome_tracker_entry",
        "entry_schema_version": 1,
        "entry_captured_at": "2026-07-06T14:19:11.994572",
        "reference_candle_at": REFERENCE_CANDLE_AT,
        "candidates": candidates,
    }


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2))
    return path


def write_pair(tmp_path, *, entry=None, resolved=None):
    entry_name = "outcome_entry_v4_test.json"
    entry_path = tmp_path / entry_name
    resolved_path = tmp_path / "outcome_resolved_v4_test.json"

    if entry is None:
        entry = entry_artifact([entry_candidate()])

    if resolved is None:
        resolved = resolved_artifact(
            entry_name,
            [resolved_candidate()],
        )

    write_json(entry_path, entry)
    write_json(resolved_path, resolved)

    return resolved_path, entry_path


def assert_single_candidate_report(
    report,
    *,
    status,
    snapshot_status="COMPLETE",
    votes=None,
    present=None,
    missing=None,
):
    candidate = report["candidates"][0]

    assert report["artifact_type"] == "forward_test_validation_report_v4"
    assert report["schema_version"] == 1
    assert report["snapshot_status"] == snapshot_status
    assert report["counts"]["total"] == 1
    assert candidate["validation_status"] == status

    if votes is not None:
        assert candidate["horizon_votes"] == votes

    if present is not None:
        assert candidate["resolved_horizons_present"] == present

    if missing is not None:
        assert candidate["missing_horizons"] == missing


def test_valid_fully_resolved_uptrend_candidate(tmp_path):
    resolved_path, _ = write_pair(tmp_path)

    report = validate_resolved_artifact(resolved_path)

    assert report["source_resolved_artifact"] == str(resolved_path)
    assert report["linked_entry_artifact"] == str(
        tmp_path / "outcome_entry_v4_test.json"
    )
    assert_single_candidate_report(
        report,
        status="VALID",
        votes={
            "h4": "SUPPORT",
            "h8": "SUPPORT",
            "h12": "SUPPORT",
        },
        present=["h4", "h8", "h12"],
        missing=[],
    )


def test_valid_fully_resolved_downtrend_candidate(tmp_path):
    entry = entry_artifact([
        entry_candidate(trend="DOWNTREND"),
    ])
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [
            resolved_candidate(
                horizons={
                    "h4": horizon_result("h4", -1.0),
                    "h8": horizon_result("h8", -2.0),
                    "h12": horizon_result("h12", -3.0),
                },
            )
        ],
    )
    resolved_path, _ = write_pair(
        tmp_path,
        entry=entry,
        resolved=resolved,
    )

    report = validate_resolved_artifact(resolved_path)

    assert_single_candidate_report(
        report,
        status="VALID",
        votes={
            "h4": "SUPPORT",
            "h8": "SUPPORT",
            "h12": "SUPPORT",
        },
    )


@pytest.mark.parametrize(
    ("returns", "expected_votes", "expected_status"),
    [
        (
            {"h4": 1.0, "h8": 2.0, "h12": -1.0},
            {"h4": "SUPPORT", "h8": "SUPPORT", "h12": "OPPOSE"},
            "VALID",
        ),
        (
            {"h4": 1.0, "h8": -1.0, "h12": -2.0},
            {"h4": "SUPPORT", "h8": "OPPOSE", "h12": "OPPOSE"},
            "INVALID",
        ),
        (
            {"h4": 1.0, "h8": -1.0, "h12": 0.0},
            {"h4": "SUPPORT", "h8": "OPPOSE", "h12": "FLAT"},
            "INCONCLUSIVE",
        ),
        (
            {"h4": 0.0, "h8": 0.0, "h12": 0.0},
            {"h4": "FLAT", "h8": "FLAT", "h12": "FLAT"},
            "INCONCLUSIVE",
        ),
        (
            {"h12": 1.0},
            {"h12": "SUPPORT"},
            "VALID",
        ),
        (
            {"h12": -1.0},
            {"h12": "OPPOSE"},
            "INVALID",
        ),
        (
            {"h12": 0.0},
            {"h12": "FLAT"},
            "INCONCLUSIVE",
        ),
    ],
)
def test_directional_vote_verdicts(
    tmp_path,
    returns,
    expected_votes,
    expected_status,
):
    horizons = {
        horizon: horizon_result(horizon, return_pct)
        for horizon, return_pct in returns.items()
    }
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate(horizons=horizons)],
    )
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    report = validate_resolved_artifact(resolved_path)

    assert_single_candidate_report(
        report,
        status=expected_status,
        votes=expected_votes,
        present=list(returns),
        missing=[
            horizon
            for horizon in ["h4", "h8", "h12"]
            if horizon not in returns
        ],
    )


@pytest.mark.parametrize(
    "horizons",
    [
        {
            "h4": horizon_result("h4", 1.0),
            "h8": horizon_result("h8", -1.0),
        },
        {},
    ],
)
def test_candidate_pending_until_h12_exists(tmp_path, horizons):
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate(horizons=horizons)],
    )
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    report = validate_resolved_artifact(resolved_path)

    assert_single_candidate_report(
        report,
        status="PENDING",
        snapshot_status="PARTIAL",
        votes={
            horizon: vote
            for horizon, vote in {
                "h4": "SUPPORT",
                "h8": "OPPOSE",
            }.items()
            if horizon in horizons
        },
        present=list(horizons),
        missing=[
            horizon
            for horizon in ["h4", "h8", "h12"]
            if horizon not in horizons
        ],
    )
    assert report["counts"] == {
        "total": 1,
        "pending": 1,
        "valid": 0,
        "invalid": 0,
        "inconclusive": 0,
    }


def test_partial_snapshot_status_and_deterministic_counts(tmp_path):
    entry = entry_artifact([
        entry_candidate("A/USDT:USDT"),
        entry_candidate("B/USDT:USDT"),
        entry_candidate("C/USDT:USDT"),
        entry_candidate("D/USDT:USDT"),
    ])
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [
            resolved_candidate(
                "A/USDT:USDT",
                horizons={"h12": horizon_result("h12", 1.0)},
            ),
            resolved_candidate(
                "B/USDT:USDT",
                horizons={"h12": horizon_result("h12", -1.0)},
            ),
            resolved_candidate(
                "C/USDT:USDT",
                horizons={"h12": horizon_result("h12", 0.0)},
            ),
            resolved_candidate(
                "D/USDT:USDT",
                horizons={"h4": horizon_result("h4", 1.0)},
            ),
        ],
    )
    resolved_path, _ = write_pair(
        tmp_path,
        entry=entry,
        resolved=resolved,
    )

    report = validate_resolved_artifact(resolved_path)

    assert report["snapshot_status"] == "PARTIAL"
    assert report["counts"] == {
        "total": 4,
        "pending": 1,
        "valid": 1,
        "invalid": 1,
        "inconclusive": 1,
    }


def test_complete_snapshot_status_when_no_candidates_are_pending(tmp_path):
    entry = entry_artifact([
        entry_candidate("A/USDT:USDT"),
        entry_candidate("B/USDT:USDT"),
    ])
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [
            resolved_candidate(
                "A/USDT:USDT",
                horizons={"h12": horizon_result("h12", 1.0)},
            ),
            resolved_candidate(
                "B/USDT:USDT",
                horizons={"h12": horizon_result("h12", -1.0)},
            ),
        ],
    )
    resolved_path, _ = write_pair(
        tmp_path,
        entry=entry,
        resolved=resolved,
    )

    report = validate_resolved_artifact(resolved_path)

    assert report["snapshot_status"] == "COMPLETE"
    assert report["counts"] == {
        "total": 2,
        "pending": 0,
        "valid": 1,
        "invalid": 1,
        "inconclusive": 0,
    }


def test_mfe_and_mae_are_diagnostic_and_do_not_change_verdict(tmp_path):
    base_resolved_path, _ = write_pair(tmp_path)
    base_report = validate_resolved_artifact(base_resolved_path)

    changed_tmp = tmp_path / "changed"
    changed_tmp.mkdir()
    changed_resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [
            resolved_candidate(
                horizons={
                    "h4": horizon_result("h4", 1.0, mfe_pct=-99.0, mae_pct=99.0),
                    "h8": horizon_result("h8", 1.0, mfe_pct=0.0, mae_pct=0.0),
                    "h12": horizon_result("h12", 1.0, mfe_pct=99.0, mae_pct=-99.0),
                },
            )
        ],
    )
    changed_path, _ = write_pair(changed_tmp, resolved=changed_resolved)

    changed_report = validate_resolved_artifact(changed_path)

    assert changed_report["candidates"][0]["validation_status"] == (
        base_report["candidates"][0]["validation_status"]
    )
    assert changed_report["candidates"][0]["horizon_votes"] == (
        base_report["candidates"][0]["horizon_votes"]
    )


def test_non_directional_entry_metadata_does_not_change_verdict(tmp_path):
    base_resolved_path, _ = write_pair(tmp_path)
    base_report = validate_resolved_artifact(base_resolved_path)

    changed_tmp = tmp_path / "changed"
    changed_tmp.mkdir()
    changed_entry = entry_artifact([
        entry_candidate(
            python_score=1.0,
            validation_adjustment=-10,
            final_rank_score=0.0,
            bos=False,
            choch=True,
            volume_ratio=0.0,
            volume_class="WEAK",
            oi_change_pct=-5.0,
            oi_class="WEAK",
            participation="WEAK",
            ai_status="HIGH_RISK",
            false_breakout_risk="HIGH",
            confluence="WEAK",
            reason_code="WEAK_PARTICIPATION",
        )
    ])
    changed_path, _ = write_pair(changed_tmp, entry=changed_entry)

    changed_report = validate_resolved_artifact(changed_path)

    assert changed_report["candidates"][0]["validation_status"] == (
        base_report["candidates"][0]["validation_status"]
    )
    assert changed_report["candidates"][0]["horizon_votes"] == (
        base_report["candidates"][0]["horizon_votes"]
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda resolved: resolved.pop("snapshot_type"),
        lambda resolved: resolved.update({"snapshot_type": "wrong"}),
        lambda resolved: resolved.update({"schema_version": 2}),
        lambda resolved: resolved.pop("entry_artifact"),
        lambda resolved: resolved["candidates"][0].pop("resolved_horizons"),
    ],
)
def test_malformed_resolved_schema_is_rejected(tmp_path, mutate):
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate()],
    )
    mutate(resolved)
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda entry: entry.pop("snapshot_type"),
        lambda entry: entry.update({"snapshot_type": "wrong"}),
        lambda entry: entry.update({"schema_version": 2}),
        lambda entry: entry["candidates"][0].pop("trend"),
        lambda entry: entry["candidates"][0]["ai_validation"].pop("status"),
    ],
)
def test_malformed_linked_entry_is_rejected(tmp_path, mutate):
    entry = entry_artifact([entry_candidate()])
    mutate(entry)
    resolved_path, _ = write_pair(tmp_path, entry=entry)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    "entry_file_name",
    [
        "missing_entry.json",
        "nested/outcome_entry_v4_test.json",
    ],
)
def test_missing_linked_entry_artifact_is_rejected(tmp_path, entry_file_name):
    resolved = resolved_artifact(
        entry_file_name,
        [resolved_candidate()],
    )
    resolved_path = write_json(
        tmp_path / "outcome_resolved_v4_test.json",
        resolved,
    )

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    ("entry", "resolved"),
    [
        (
            entry_artifact([entry_candidate()]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [
                    resolved_candidate("A/USDT:USDT"),
                    resolved_candidate("B/USDT:USDT"),
                ],
            ),
        ),
        (
            entry_artifact([
                entry_candidate("A/USDT:USDT"),
                entry_candidate("B/USDT:USDT"),
            ]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [
                    resolved_candidate("B/USDT:USDT"),
                    resolved_candidate("A/USDT:USDT"),
                ],
            ),
        ),
        (
            entry_artifact([entry_candidate("ENTRY/USDT:USDT")]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [resolved_candidate("RESOLVED/USDT:USDT")],
            ),
        ),
        (
            entry_artifact([entry_candidate(reference_price=100.0)]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [resolved_candidate(reference_price=101.0)],
            ),
        ),
    ],
)
def test_resolved_entry_identity_mismatch_is_rejected(
    tmp_path,
    entry,
    resolved,
):
    resolved_path, _ = write_pair(
        tmp_path,
        entry=entry,
        resolved=resolved,
    )

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    ("entry", "resolved"),
    [
        (
            entry_artifact([
                entry_candidate("DUP/USDT:USDT"),
                entry_candidate("DUP/USDT:USDT"),
            ]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [
                    resolved_candidate("DUP/USDT:USDT"),
                    resolved_candidate("DUP/USDT:USDT"),
                ],
            ),
        ),
        (
            entry_artifact([
                entry_candidate("A/USDT:USDT"),
                entry_candidate("B/USDT:USDT"),
            ]),
            resolved_artifact(
                "outcome_entry_v4_test.json",
                [
                    resolved_candidate("A/USDT:USDT"),
                    resolved_candidate("A/USDT:USDT"),
                ],
            ),
        ),
    ],
)
def test_duplicate_candidate_symbols_are_rejected(tmp_path, entry, resolved):
    resolved_path, _ = write_pair(
        tmp_path,
        entry=entry,
        resolved=resolved,
    )

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


def test_unsupported_trend_is_rejected(tmp_path):
    entry = entry_artifact([
        entry_candidate(trend="SIDEWAYS"),
    ])
    resolved_path, _ = write_pair(tmp_path, entry=entry)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    "bad_value",
    [
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
@pytest.mark.parametrize(
    "field",
    [
        "return_price",
        "return_pct",
        "mfe_price",
        "mfe_pct",
        "mae_price",
        "mae_pct",
    ],
)
def test_null_and_non_finite_numeric_outcomes_are_rejected(
    tmp_path,
    field,
    bad_value,
):
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate()],
    )
    resolved["candidates"][0]["resolved_horizons"]["h12"][field] = bad_value
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


def test_target_at_contract_mismatch_is_rejected(tmp_path):
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate()],
    )
    resolved["candidates"][0]["resolved_horizons"]["h12"]["target_at"] = (
        "2026-07-07T04:00:00+00:00"
    )
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


@pytest.mark.parametrize(
    "horizons",
    [
        {"h16": horizon_result("h12", 1.0)},
        {"h12": {**horizon_result("h12", 1.0), "horizon": "h8"}},
        {"h12": {"horizon": "h12"}},
        {"h12": "not-a-dict"},
    ],
)
def test_unknown_or_malformed_horizon_is_rejected(tmp_path, horizons):
    resolved = resolved_artifact(
        "outcome_entry_v4_test.json",
        [resolved_candidate(horizons=horizons)],
    )
    resolved_path, _ = write_pair(tmp_path, resolved=resolved)

    with pytest.raises(ValueError):
        validate_resolved_artifact(resolved_path)


def test_validator_has_no_scanner_binance_deepseek_pipeline_or_resolver_dependency(
    tmp_path,
    monkeypatch,
):
    forbidden_modules = [
        "engine.scanner",
        "engine.binance_client",
        "engine.deepseek_validator_v4",
        "engine.validated_pipeline_v4",
        "engine.forward_outcome_resolver_v4",
    ]

    for module_name in forbidden_modules:
        monkeypatch.setitem(
            __import__("sys").modules,
            module_name,
            ForbiddenModule(module_name),
        )

    resolved_path, _ = write_pair(tmp_path)

    report = validate_resolved_artifact(resolved_path)

    assert report["counts"] == {
        "total": 1,
        "pending": 0,
        "valid": 1,
        "invalid": 0,
        "inconclusive": 0,
    }


class ForbiddenModule:
    def __init__(self, module_name):
        self.module_name = module_name

    def __getattr__(self, name):
        raise AssertionError(
            f"Forbidden dependency used: {self.module_name}.{name}"
        )
