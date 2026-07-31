import ast
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import engine.e4_thesis_fingerprint_v1 as subject
from engine.canonical_pair_v1 import normalize_pair
from engine.e3_executable_price_snapshot_v1 import (
    E3ExecutablePriceSnapshotV1,
    build_e3_executable_price_snapshot,
)
from engine.e3_golden_zone_geometry_v1 import (
    E3GoldenZoneGeometryV1,
    build_e3_golden_zone_geometry,
)
from engine.e3_mode_trigger_evidence_v1 import (
    E3ModeTriggerEvidenceV1,
    build_e3_mode_trigger_evidence,
)
from engine.e3_structural_targets_v1 import (
    E3StructuralTargetsV1,
    build_e3_structural_targets,
)
from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import get_mode_profile
from engine.production_candidate_authority_v1 import (
    ProductionCandidateAuthorityV1,
)


IDENTITY_FIELDS = (
    "venue",
    "canonical_pair",
    "mode",
    "side",
    "strategy_version",
    "mode_profile_version",
    "structure_timeframe",
    "structure_generation_id",
    "anchor_low_at",
    "anchor_low_tick",
    "anchor_high_at",
    "anchor_high_tick",
    "golden_zone_low_tick",
    "golden_zone_high_tick",
    "stop_loss_tick",
    "target_policy_version",
    "tp1_destination_id",
    "tp1_tick",
    "tp2_destination_id",
    "tp2_tick",
    "trigger_type",
    "trigger_timeframe",
    "trigger_generation_id",
    "trigger_candle_close_at",
)

EXCLUDED_FIELDS = (
    "signal_id",
    "delivery_id",
    "publication_timestamp",
    "telegram_message_id",
    "current_price",
    "score",
    "llm_result",
    "valid_until",
    "ledger_revision",
)


def _authority(*, strategy_version="master-engine-v4", valid_until="2026-08-01T00:00:00Z"):
    return ProductionCandidateAuthorityV1(
        source_commit="a" * 40,
        source_evaluation_id="evaluation:e4-fingerprint",
        production_evidence_ref={
            "manifest_hash": "b" * 64,
            "manifest_path": "sealed/manifest.json",
        },
        component_versions={"adapter": "v1", "master": "v4"},
        tp2=12528,
        valid_until=valid_until,
        strategy_version=strategy_version,
        source_payload_hash="c" * 64,
    )


def _real_chain(mode="SWING", side="LONG", *, strategy_version="master-engine-v4", valid_until="2026-08-01T00:00:00Z"):
    anchor_low_at = (
        "2026-07-30T00:00:00Z"
        if side == "LONG"
        else "2026-07-30T01:00:00Z"
    )
    anchor_high_at = (
        "2026-07-30T01:00:00Z"
        if side == "LONG"
        else "2026-07-30T00:00:00Z"
    )
    geometry = build_e3_golden_zone_geometry(
        mode=mode,
        mode_lineage_sha256=build_mode_audit_lineage(mode).lineage_sha256,
        canonical_symbol="BTC/USDT:USDT",
        side=side,
        structure_generation_id="structure:g1",
        anchor_low_at=anchor_low_at,
        anchor_low_tick=9000,
        anchor_high_at=anchor_high_at,
        anchor_high_tick=12000,
        tick_size="1",
    )
    targets = build_e3_structural_targets(
        geometry=geometry,
        ordered_destinations=(
            (
                "STRUCTURE",
                "destination:tp1",
                12146 if side == "LONG" else 8854,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
            (
                "LIQUIDITY",
                "destination:tp2",
                12528 if side == "LONG" else 8472,
                geometry.structure_timeframe,
                geometry.structure_generation_id,
            ),
        ),
    )
    inside_tick = geometry.golden_zone_low_tick + (
        geometry.golden_zone_high_tick - geometry.golden_zone_low_tick
    ) // 2
    snapshot = build_e3_executable_price_snapshot(
        geometry=geometry,
        venue="BINANCE_USDM",
        quote_generation_id=f"quote:e4-{mode.lower()}-{side.lower()}",
        exchange_timestamp="2026-07-30T00:15:00Z",
        best_bid_tick=inside_tick - 1 if side == "LONG" else inside_tick,
        best_ask_tick=inside_tick if side == "LONG" else inside_tick + 1,
        last_price_tick=inside_tick,
        mark_price_tick=inside_tick,
        modeled_adverse_slippage_bps=0,
        tick_size=geometry.tick_size,
    )
    profile = get_mode_profile(mode)
    trigger = build_e3_mode_trigger_evidence(
        geometry=geometry,
        mode=geometry.mode,
        mode_lineage_sha256=geometry.mode_lineage_sha256,
        canonical_symbol=geometry.canonical_symbol,
        side=geometry.side,
        structure_timeframe=geometry.structure_timeframe,
        structure_generation_id=geometry.structure_generation_id,
        trigger_timeframe=profile.trigger_timeframe,
        trigger_rule=profile.trigger_rule,
        trigger_candle_close_at="2026-07-30T00:15:00Z",
        trigger_candle_closed=True,
        trigger_rule_satisfied=True,
        evaluation_timestamp="2026-07-30T00:15:00Z",
    )
    authority = _authority(
        strategy_version=strategy_version,
        valid_until=valid_until,
    )
    result = subject.build_e4_thesis_fingerprint(
        geometry=geometry,
        structural_targets=targets,
        executable_price_snapshot=snapshot,
        mode_trigger_evidence=trigger,
        production_candidate_authority=authority,
    )
    return {
        "geometry": geometry,
        "targets": targets,
        "snapshot": snapshot,
        "trigger": trigger,
        "authority": authority,
        "result": result,
    }


def _constructor_values(result):
    return {
        field.name: getattr(result, field.name)
        for field in dataclasses.fields(result)
    }


def _dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def test_exact_public_constants_and_ordered_field_policies():
    assert subject.__all__ == (
        "THESIS_FINGERPRINT_VERSION",
        "THESIS_IDENTITY_FIELDS",
        "THESIS_EXCLUDED_FIELDS",
        "E4ThesisFingerprintV1",
        "build_e4_thesis_fingerprint",
    )
    assert subject.THESIS_FINGERPRINT_VERSION == "thesis-fingerprint-v1"
    assert subject.THESIS_IDENTITY_FIELDS == IDENTITY_FIELDS
    assert subject.THESIS_EXCLUDED_FIELDS == EXCLUDED_FIELDS
    assert len(IDENTITY_FIELDS) == 24
    assert len(EXCLUDED_FIELDS) == 9
    assert set(IDENTITY_FIELDS).isdisjoint(EXCLUDED_FIELDS)


def test_result_is_frozen_slotted_and_has_exact_methods_and_fields():
    result = _real_chain()["result"]
    expected_fields = ("fingerprint_version", *IDENTITY_FIELDS, "identity_sha256")
    assert subject.E4ThesisFingerprintV1.__dataclass_params__.frozen is True
    assert tuple(field.name for field in dataclasses.fields(result)) == expected_fields
    assert not hasattr(result, "__dict__")
    assert {
        name
        for name, value in vars(subject.E4ThesisFingerprintV1).items()
        if callable(value) and not name.startswith("_")
    } == {"to_identity_mapping", "to_mapping", "canonical_identity_json"}
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.mode = "SCALP"


def test_builder_is_keyword_only_and_has_exact_scalar_dependencies():
    signature = inspect.signature(subject.build_e4_thesis_fingerprint)
    assert tuple(signature.parameters) == (
        "geometry",
        "structural_targets",
        "executable_price_snapshot",
        "mode_trigger_evidence",
        "production_candidate_authority",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


@pytest.mark.parametrize(
    ("mode", "side"),
    (
        ("SWING", "LONG"),
        ("SWING", "SHORT"),
        ("INTRADAY", "LONG"),
        ("INTRADAY", "SHORT"),
        ("SCALP", "LONG"),
        ("SCALP", "SHORT"),
    ),
)
def test_six_real_mode_side_chains(mode, side):
    chain = _real_chain(mode, side)
    result = chain["result"]
    assert type(chain["geometry"]) is E3GoldenZoneGeometryV1
    assert type(chain["targets"]) is E3StructuralTargetsV1
    assert type(chain["snapshot"]) is E3ExecutablePriceSnapshotV1
    assert type(chain["trigger"]) is E3ModeTriggerEvidenceV1
    assert type(chain["authority"]) is ProductionCandidateAuthorityV1
    assert result.mode == mode
    assert result.side == side
    assert result.canonical_pair == "BTC/USDT"
    assert result.trigger_type == chain["trigger"].trigger_rule
    assert result.trigger_timeframe == get_mode_profile(mode).trigger_timeframe
    assert len(result.identity_sha256) == 64
    assert result.identity_sha256 == result.identity_sha256.lower()


def test_mapping_serialization_and_exact_canonical_sha256_preimage():
    result = _real_chain()["result"]
    identity = result.to_identity_mapping()
    preimage = {
        "fingerprint_version": "thesis-fingerprint-v1",
        "identity": identity,
    }
    expected_json = json.dumps(
        preimage,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert tuple(identity) == IDENTITY_FIELDS
    assert result.canonical_identity_json() == expected_json
    assert result.identity_sha256 == hashlib.sha256(
        expected_json.encode("utf-8")
    ).hexdigest()
    assert tuple(result.to_mapping()) == (
        "fingerprint_version",
        *IDENTITY_FIELDS,
        "identity_sha256",
    )
    detached = result.to_mapping()
    detached["mode"] = "SCALP"
    assert result.mode == "SWING"


def test_deterministic_replay_and_mapping_order_invariance():
    first = _real_chain()["result"]
    second = _real_chain()["result"]
    reversed_identity = dict(reversed(tuple(first.to_identity_mapping().items())))
    reordered_json = json.dumps(
        {
            "identity": reversed_identity,
            "fingerprint_version": first.fingerprint_version,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert first == second
    assert first.identity_sha256 == second.identity_sha256
    assert reordered_json == first.canonical_identity_json()
    assert hashlib.sha256(reordered_json.encode("utf-8")).hexdigest() == (
        first.identity_sha256
    )


def test_exact_cross_contract_projections_and_identity_categories():
    chain = _real_chain()
    result = chain["result"]
    geometry = chain["geometry"]
    targets = chain["targets"]
    trigger = chain["trigger"]
    assert result.canonical_pair == normalize_pair(geometry.canonical_symbol)
    assert result.trigger_type == trigger.trigger_rule
    assert result.target_policy_version == targets.policy_version
    assert result.venue == chain["snapshot"].venue
    assert result.strategy_version == chain["authority"].strategy_version
    assert set(result.to_identity_mapping()) == set(IDENTITY_FIELDS)
    assert not any(
        name.endswith("_sha256")
        for name in result.to_identity_mapping()
    )


@pytest.mark.parametrize(
    ("change", "expected_field"),
    (
        ({"strategy_version": "master-engine-v5"}, "strategy_version"),
        ({"mode": "INTRADAY"}, "mode"),
        ({"side": "SHORT"}, "side"),
    ),
)
def test_material_identity_changes_change_sha256(change, expected_field):
    baseline = _real_chain()["result"]
    arguments = {
        "mode": change.get("mode", "SWING"),
        "side": change.get("side", "LONG"),
        "strategy_version": change.get(
            "strategy_version",
            "master-engine-v4",
        ),
    }
    changed = _real_chain(**arguments)["result"]
    assert getattr(baseline, expected_field) != getattr(changed, expected_field)
    assert baseline.identity_sha256 != changed.identity_sha256


@pytest.mark.parametrize(
    ("field", "first_value", "second_value"),
    (
        ("signal_id", "PSG-one", "PSG-two"),
        ("delivery_id", "PDL-one", "PDL-two"),
        (
            "publication_timestamp",
            "2026-07-30T00:15:00Z",
            "2026-07-30T00:16:00Z",
        ),
        ("telegram_message_id", 1, 2),
        ("current_price", 10000, 10001),
        ("score", 80, 90),
        ("llm_result", {"decision": "A"}, {"decision": "B"}),
        (
            "valid_until",
            "2026-08-01T00:00:00Z",
            "2026-08-02T00:00:00Z",
        ),
        ("ledger_revision", 1, 2),
    ),
)
def test_each_excluded_field_is_fingerprint_invariant(
    field,
    first_value,
    second_value,
):
    first_valid_until = (
        first_value
        if field == "valid_until"
        else "2026-08-01T00:00:00Z"
    )
    second_valid_until = (
        second_value
        if field == "valid_until"
        else "2026-08-01T00:00:00Z"
    )
    first = _real_chain(valid_until=first_valid_until)["result"]
    second = _real_chain(valid_until=second_valid_until)["result"]
    first_envelope = {field: first_value}
    second_envelope = {field: second_value}
    assert first_envelope != second_envelope
    assert field not in dataclasses.asdict(first)
    assert field not in first.to_identity_mapping()
    assert field not in json.loads(first.canonical_identity_json())["identity"]
    assert first == second
    assert first.identity_sha256 == second.identity_sha256


@pytest.mark.parametrize("kind", ("missing", "extra"))
def test_missing_or_extra_constructor_identity_key_fails_closed(kind):
    values = _constructor_values(_real_chain()["result"])
    if kind == "missing":
        values.pop("venue")
    else:
        values["unexpected_identity"] = "forbidden"
    with pytest.raises(TypeError):
        subject.E4ThesisFingerprintV1(**values)


@pytest.mark.parametrize(
    "field",
    (
        "anchor_low_tick",
        "anchor_high_tick",
        "golden_zone_low_tick",
        "golden_zone_high_tick",
        "stop_loss_tick",
        "tp1_tick",
        "tp2_tick",
    ),
)
def test_bool_as_tick_and_non_integer_tick_fail_closed(field):
    result = _real_chain()["result"]
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        dataclasses.replace(result, **{field: True})
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        dataclasses.replace(result, **{field: "100"})


@pytest.mark.parametrize(
    "field",
    ("anchor_low_at", "anchor_high_at", "trigger_candle_close_at"),
)
def test_malformed_timestamp_fails_closed(field):
    result = _real_chain()["result"]
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        dataclasses.replace(result, **{field: "2026-07-30 00:00:00"})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("fingerprint_version", "thesis-fingerprint-v2"),
        ("venue", ""),
        ("strategy_version", "   "),
        ("canonical_pair", "btc/usdt"),
        ("mode", "DAY"),
        ("side", "BUY"),
        ("trigger_generation_id", "trg-invalid"),
        ("identity_sha256", "0" * 64),
    ),
)
def test_direct_constructor_semantic_corruption_fails_closed(field, value):
    result = _real_chain()["result"]
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        dataclasses.replace(result, **{field: value})


def test_dependency_identity_mismatch_and_lookalikes_fail_closed():
    first = _real_chain("SWING", "LONG")
    second = _real_chain("INTRADAY", "LONG")
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        subject.build_e4_thesis_fingerprint(
            geometry=first["geometry"],
            structural_targets=second["targets"],
            executable_price_snapshot=first["snapshot"],
            mode_trigger_evidence=first["trigger"],
            production_candidate_authority=first["authority"],
        )
    with pytest.raises(ValueError, match="^invalid E4 thesis fingerprint$"):
        subject.build_e4_thesis_fingerprint(
            geometry=object(),
            structural_targets=first["targets"],
            executable_price_snapshot=first["snapshot"],
            mode_trigger_evidence=first["trigger"],
            production_candidate_authority=first["authority"],
        )


def test_source_has_exact_project_imports_and_zero_external_effect_authority():
    source_path = Path(subject.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    project_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and isinstance(node.module, str)
        and node.module.startswith("engine.")
    }
    assert project_imports == {
        "engine.canonical_pair_v1",
        "engine.e3_executable_price_snapshot_v1",
        "engine.e3_golden_zone_geometry_v1",
        "engine.e3_mode_trigger_evidence_v1",
        "engine.e3_structural_targets_v1",
        "engine.production_candidate_authority_v1",
    }
    forbidden_roots = {
        "aiohttp",
        "asyncio",
        "ccxt",
        "httpx",
        "multiprocessing",
        "os",
        "pathlib",
        "random",
        "redis",
        "requests",
        "secrets",
        "socket",
        "sqlite3",
        "subprocess",
        "threading",
        "time",
        "urllib",
        "uuid",
    }
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert imported_roots.isdisjoint(forbidden_roots)

    calls = {
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (name := _dotted_name(node.func)) is not None
    }
    forbidden_calls = {
        "open",
        "eval",
        "exec",
        "compile",
        "__import__",
        "datetime.now",
        "datetime.utcnow",
        "date.today",
        "time.time",
        "random.random",
        "uuid.uuid4",
        "os.getenv",
    }
    assert calls.isdisjoint(forbidden_calls)
    assert not any(
        call.endswith(
            (
                ".send",
                ".publish",
                ".create_order",
                ".place_order",
                ".write_text",
                ".write_bytes",
                ".commit",
            )
        )
        for call in calls
    )
    assert all(
        not isinstance(
            node,
            (
                ast.AsyncFunctionDef,
                ast.Await,
                ast.Yield,
                ast.YieldFrom,
            ),
        )
        for node in ast.walk(tree)
    )

