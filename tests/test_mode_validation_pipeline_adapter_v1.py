"""Focused tests for the pure mode-validation pipeline adapter."""

import dataclasses
import hashlib
import json

import pytest

from engine.mode_data_plan_v1 import build_mode_audit_lineage
from engine.mode_profile_v1 import all_mode_profiles
from engine.mode_router_v1 import (
    ModeRouteResultV1,
    route_mode_scan,
)
from engine.mode_validation_pipeline_adapter_v1 import (
    CONTROLLED_TOP10,
    FINAL_TOP5,
    MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION,
    MODE_VALIDATION_PIPELINE_POLICY_VERSION,
    MODE_VALIDATION_PIPELINE_RESULT_SCHEMA_VERSION,
    ModeValidatedCandidateV1,
    ModeValidationPipelineResultV1,
    ModeValidationPipelineValidationError,
    run_mode_validation_pipeline,
)


MODES = tuple(profile.mode for profile in all_mode_profiles())
IDENTITY_KEYS = {
    "schema_version",
    "policy_version",
    "candidate_id",
    "symbol",
    "mode",
    "mode_lineage_sha256",
    "payload_json",
    "payload_sha256",
    "pipeline_stage",
    "pipeline_rank",
}
_DEFAULT_PIPELINE = object()


def _route(
    *,
    mode=None,
    count=1,
    payload_factory=None,
):
    selected_mode = MODES[0] if mode is None else mode

    def scanner(*, request):
        rows = []
        for index in range(count):
            payload = (
                {
                    "score": 100 - index,
                    "nested": {"values": [index]},
                }
                if payload_factory is None
                else payload_factory(index, request)
            )
            rows.append(
                {
                    "candidate_id": f"candidate-{index + 1}",
                    "mode": request.mode,
                    "symbol": f"ASSET{index + 1}/USDT",
                    "mode_lineage_sha256": (
                        request.mode_audit_lineage.lineage_sha256
                    ),
                    "payload": payload,
                }
            )
        return rows

    return route_mode_scan(
        mode=selected_mode,
        due_window_id="window-2026.07.30T06:30+00",
        scanner=scanner,
    )


def _pipeline_output(rows, *, final_indexes=(0,)):
    controlled = []
    for index, row in enumerate(rows[:10]):
        controlled_row = dict(row)
        controlled_row["pipeline_score"] = 100.0 - index
        controlled.append(controlled_row)
    final = [
        dict(controlled[index])
        for index in final_indexes
        if index < len(controlled)
    ]
    return {
        "controlled_top10": controlled,
        "final_top5": final,
        "usage": {"tokens": 17, "cached": False},
    }


def _run(route=None, pipeline=_DEFAULT_PIPELINE):
    selected_route = _route() if route is None else route
    selected_pipeline = (
        _pipeline_output
        if pipeline is _DEFAULT_PIPELINE
        else pipeline
    )
    return run_mode_validation_pipeline(
        route_result=selected_route,
        pipeline=selected_pipeline,
    )


def _assert_invalid(route, pipeline):
    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        _run(route, pipeline)


def test_dataclasses_are_exactly_frozen_slotted_and_immutable():
    result = _run()
    candidate = result.controlled_top10[0]

    assert [field.name for field in dataclasses.fields(candidate)] == [
        "schema_version",
        "policy_version",
        "candidate_id",
        "mode",
        "symbol",
        "mode_lineage_sha256",
        "pipeline_stage",
        "pipeline_rank",
        "payload_json",
        "payload_sha256",
    ]
    assert [field.name for field in dataclasses.fields(result)] == [
        "schema_version",
        "policy_version",
        "mode",
        "due_window_id",
        "mode_lineage_sha256",
        "input_route_sha256",
        "pipeline_invocation_count",
        "retry_count",
        "input_candidate_count",
        "controlled_candidate_count",
        "final_candidate_count",
        "controlled_top10",
        "final_top5",
        "usage_json",
        "usage_sha256",
    ]
    assert "__dict__" not in ModeValidatedCandidateV1.__slots__
    assert "__dict__" not in ModeValidationPipelineResultV1.__slots__
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.mode = MODES[-1]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.mode = MODES[-1]
    with pytest.raises(TypeError):
        result.controlled_top10[0] = candidate

    replaced = dataclasses.replace(
        result,
        controlled_top10=list(result.controlled_top10),
        final_top5=list(result.final_top5),
    )
    assert type(replaced.controlled_top10) is tuple
    assert type(replaced.final_top5) is tuple


@pytest.mark.parametrize("mode", MODES)
def test_all_canonical_modes_reattach_exact_route_identity(mode):
    route = _route(mode=mode)
    result = _run(route)
    routed = route.candidates[0]
    controlled = result.controlled_top10[0]
    final = result.final_top5[0]

    assert result.schema_version == (
        MODE_VALIDATION_PIPELINE_RESULT_SCHEMA_VERSION
    )
    assert result.policy_version == (
        MODE_VALIDATION_PIPELINE_POLICY_VERSION
    )
    assert result.mode == mode
    assert result.mode_lineage_sha256 == (
        build_mode_audit_lineage(mode).lineage_sha256
    )
    for candidate in (controlled, final):
        assert candidate.schema_version == (
            MODE_VALIDATED_CANDIDATE_SCHEMA_VERSION
        )
        assert candidate.policy_version == (
            MODE_VALIDATION_PIPELINE_POLICY_VERSION
        )
        assert candidate.candidate_id == routed.candidate_id
        assert candidate.mode == routed.mode
        assert candidate.symbol == routed.symbol
        assert candidate.mode_lineage_sha256 == (
            routed.mode_lineage_sha256
        )


def test_pipeline_is_called_once_with_detached_rows_and_injected_symbol():
    route = _route()
    calls = []

    def pipeline(rows):
        calls.append(rows)
        assert type(rows) is list
        assert rows == [
            {
                "nested": {"values": [0]},
                "score": 100,
                "symbol": "ASSET1/USDT",
            }
        ]
        assert not (
            set(rows[0])
            & (IDENTITY_KEYS - {"symbol"})
        )
        rows[0]["nested"]["values"].append(99)
        return _pipeline_output(rows)

    result = _run(route, pipeline)

    assert len(calls) == 1
    assert route.candidates[0].payload_copy() == {
        "nested": {"values": [0]},
        "score": 100,
    }
    assert result.pipeline_invocation_count == 1
    assert result.retry_count == 0


def test_pipeline_exception_is_sanitized_without_retry():
    calls = []

    def pipeline(rows):
        calls.append(rows)
        raise RuntimeError("secret provider detail")

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ) as captured:
        _run(_route(), pipeline)

    assert "secret" not in str(captured.value)
    assert len(calls) == 1


def test_empty_route_still_invokes_pipeline_exactly_once():
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return {
            "controlled_top10": (),
            "final_top5": [],
            "usage": {},
        }

    result = _run(_route(count=0), pipeline)

    assert calls == [[]]
    assert result.input_candidate_count == 0
    assert result.controlled_candidate_count == 0
    assert result.final_candidate_count == 0
    assert result.controlled_top10 == ()
    assert result.final_top5 == ()


@pytest.mark.parametrize("pipeline", (None, 7, "callable"))
def test_non_callable_pipeline_is_rejected(pipeline):
    _assert_invalid(_route(), pipeline)


def test_non_exact_route_result_type_is_rejected_without_call():
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    with pytest.raises(ModeValidationPipelineValidationError):
        run_mode_validation_pipeline(
            route_result=object(),
            pipeline=pipeline,
        )

    assert calls == []


def test_non_exact_nested_routed_candidate_is_rejected_without_call():
    route = _route()
    object.__setattr__(route, "candidates", (object(),))
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize(
    "output",
    (
        {"controlled_top10": [], "final_top5": []},
        {
            "controlled_top10": [],
            "final_top5": [],
            "usage": {},
            "extra": None,
        },
        [],
    ),
)
def test_pipeline_output_requires_exact_top_level_dict_keys(output):
    _assert_invalid(_route(count=0), lambda rows: output)


@pytest.mark.parametrize(
    ("controlled", "final"),
    (
        ({}, []),
        ([], {}),
        ("rows", []),
        ([], "rows"),
    ),
)
def test_controlled_and_final_require_list_or_tuple(
    controlled,
    final,
):
    _assert_invalid(
        _route(count=0),
        lambda rows: {
            "controlled_top10": controlled,
            "final_top5": final,
            "usage": {},
        },
    )


@pytest.mark.parametrize(
    "usage",
    (
        [],
        (),
        {"bad": (1, 2)},
        {"bad": object()},
        {"bad": float("nan")},
        {1: "non-string-key"},
    ),
)
def test_usage_requires_an_exact_canonical_json_dict(usage):
    _assert_invalid(
        _route(count=0),
        lambda rows: {
            "controlled_top10": [],
            "final_top5": [],
            "usage": usage,
        },
    )


def test_usage_rejects_dict_subclasses():
    class DictSubclass(dict):
        pass

    _assert_invalid(
        _route(count=0),
        lambda rows: {
            "controlled_top10": [],
            "final_top5": [],
            "usage": DictSubclass(),
        },
    )


def test_duplicate_input_symbols_fail_before_pipeline_invocation():
    route = _route(count=2)
    object.__setattr__(
        route.candidates[1],
        "symbol",
        route.candidates[0].symbol,
    )
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


def test_duplicate_input_candidate_ids_remain_rejected():
    route = _route(count=2)
    object.__setattr__(
        route.candidates[1],
        "candidate_id",
        route.candidates[0].candidate_id,
    )
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize(
    "invalid_due_window_id",
    (" ", "window/with/slash", "w" * 129),
)
def test_tampered_route_due_window_id_uses_router_identity_rules(
    invalid_due_window_id,
):
    route = _route()
    object.__setattr__(
        route,
        "due_window_id",
        invalid_due_window_id,
    )
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize(
    "invalid_candidate_id",
    (" ", "candidate/with/slash", "c" * 129),
)
def test_tampered_routed_candidate_id_uses_router_identity_rules(
    invalid_candidate_id,
):
    route = _route()
    object.__setattr__(
        route.candidates[0],
        "candidate_id",
        invalid_candidate_id,
    )
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize(
    "invalid_symbol",
    (" ASSET1/USDT", "ASSET1/USDT ", "S" * 129),
)
def test_tampered_routed_symbol_uses_router_identity_rules(
    invalid_symbol,
):
    route = _route()
    object.__setattr__(
        route.candidates[0],
        "symbol",
        invalid_symbol,
    )
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize("identity_key", sorted(IDENTITY_KEYS))
def test_routed_payload_identity_collision_fails_before_pipeline(
    identity_key,
):
    def payload_factory(index, request):
        values = {
            "schema_version": "payload-schema",
            "policy_version": "payload-policy",
            "candidate_id": "payload-candidate",
            "symbol": "PAYLOAD/USDT",
            "mode": request.mode,
            "mode_lineage_sha256": (
                request.mode_audit_lineage.lineage_sha256
            ),
            "payload_json": "{}",
            "payload_sha256": "0" * 64,
            "pipeline_stage": CONTROLLED_TOP10,
            "pipeline_rank": 1,
        }
        return {identity_key: values[identity_key]}

    route = _route(payload_factory=payload_factory)
    calls = []

    def pipeline(rows):
        calls.append(rows)
        return _pipeline_output(rows)

    _assert_invalid(route, pipeline)
    assert calls == []


@pytest.mark.parametrize(
    "bad_row",
    (
        {"symbol": "UNKNOWN/USDT"},
        {"score": 1},
    ),
)
def test_unknown_or_missing_controlled_symbol_is_rejected(bad_row):
    _assert_invalid(
        _route(),
        lambda rows: {
            "controlled_top10": [bad_row],
            "final_top5": [],
            "usage": {},
        },
    )


def test_duplicate_controlled_symbol_is_rejected():
    route = _route(count=2)

    def pipeline(rows):
        first = dict(rows[0])
        return {
            "controlled_top10": [first, dict(first)],
            "final_top5": [],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


@pytest.mark.parametrize(
    "identity_key",
    sorted(IDENTITY_KEYS - {"symbol"}),
)
def test_controlled_row_identity_field_spoofing_is_rejected(
    identity_key,
):
    def pipeline(rows):
        row = dict(rows[0])
        row[identity_key] = "spoofed"
        return {
            "controlled_top10": [row],
            "final_top5": [],
            "usage": {},
        }

    _assert_invalid(_route(), pipeline)


@pytest.mark.parametrize(
    "bad_final",
    (
        {"symbol": "UNKNOWN/USDT"},
        {"score": 100},
    ),
)
def test_unknown_or_missing_final_symbol_is_rejected(bad_final):
    route = _route()

    def pipeline(rows):
        controlled = [dict(rows[0])]
        return {
            "controlled_top10": controlled,
            "final_top5": [bad_final],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_duplicate_final_symbol_is_rejected():
    route = _route(count=2)

    def pipeline(rows):
        controlled = [dict(row) for row in rows]
        return {
            "controlled_top10": controlled,
            "final_top5": [
                dict(controlled[0]),
                dict(controlled[0]),
            ],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_final_row_must_be_contained_in_controlled_rows():
    route = _route(count=11)

    def pipeline(rows):
        return {
            "controlled_top10": [
                dict(row) for row in rows[:10]
            ],
            "final_top5": [dict(rows[10])],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_altered_final_payload_is_rejected():
    route = _route(count=2)

    def pipeline(rows):
        controlled = [dict(row) for row in rows]
        final = dict(controlled[0])
        final["score"] = -1
        return {
            "controlled_top10": controlled,
            "final_top5": [final],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_reordered_final_rows_are_rejected():
    route = _route(count=2)

    def pipeline(rows):
        controlled = [dict(row) for row in rows]
        return {
            "controlled_top10": controlled,
            "final_top5": [
                dict(controlled[1]),
                dict(controlled[0]),
            ],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_controlled_count_must_equal_minimum_of_input_and_ten():
    _assert_invalid(
        _route(count=2),
        lambda rows: {
            "controlled_top10": [dict(rows[0])],
            "final_top5": [],
            "usage": {},
        },
    )


def test_controlled_count_is_capped_at_ten():
    route = _route(count=12)
    result = _run(route)

    assert result.input_candidate_count == 12
    assert result.controlled_candidate_count == 10
    assert len(result.controlled_top10) == 10

    _assert_invalid(
        route,
        lambda rows: {
            "controlled_top10": [
                dict(row) for row in rows[:11]
            ],
            "final_top5": [],
            "usage": {},
        },
    )


def test_final_count_is_capped_at_five():
    route = _route(count=6)

    def pipeline(rows):
        controlled = [dict(row) for row in rows]
        return {
            "controlled_top10": controlled,
            "final_top5": [
                dict(row) for row in controlled
            ],
            "usage": {},
        }

    _assert_invalid(route, pipeline)


def test_stages_and_ranks_are_exact_and_contiguous():
    route = _route(count=7)

    def pipeline(rows):
        return _pipeline_output(
            rows,
            final_indexes=(0, 2, 5),
        )

    result = _run(route, pipeline)

    assert [
        candidate.pipeline_stage
        for candidate in result.controlled_top10
    ] == [CONTROLLED_TOP10] * 7
    assert [
        candidate.pipeline_rank
        for candidate in result.controlled_top10
    ] == list(range(1, 8))
    assert [
        candidate.pipeline_stage
        for candidate in result.final_top5
    ] == [FINAL_TOP5] * 3
    assert [
        candidate.pipeline_rank
        for candidate in result.final_top5
    ] == [1, 2, 3]


def test_caller_mutation_cannot_change_returned_candidates():
    route = _route()
    output = None

    def pipeline(rows):
        nonlocal output
        output = _pipeline_output(rows)
        return output

    result = _run(route, pipeline)
    original_mapping = result.to_mapping()
    output["controlled_top10"][0]["score"] = -1
    output["controlled_top10"][0]["nested"]["values"].append(88)
    output["final_top5"].clear()
    copied_payload = result.controlled_top10[0].payload_copy()
    copied_payload["nested"]["values"].append(77)

    assert result.to_mapping() == original_mapping


def test_caller_mutation_cannot_change_canonical_usage():
    usage = {"nested": {"tokens": [1, 2]}}

    def pipeline(rows):
        output = _pipeline_output(rows)
        output["usage"] = usage
        return output

    result = _run(_route(), pipeline)
    original_json = result.usage_json
    original_hash = result.usage_sha256
    usage["nested"]["tokens"].append(3)
    copied = result.usage_copy()
    copied["nested"]["tokens"].append(4)

    assert result.usage_json == original_json
    assert result.usage_sha256 == original_hash
    assert result.usage_copy() == {"nested": {"tokens": [1, 2]}}


def test_deterministic_replay_produces_identical_mapping_and_hashes():
    first = _run(_route(mode=MODES[1], count=3))
    second = _run(_route(mode=MODES[1], count=3))

    assert first.to_mapping() == second.to_mapping()
    expected_route_json = json.dumps(
        _route(mode=MODES[1], count=3).to_mapping(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    assert first.input_route_sha256 == hashlib.sha256(
        expected_route_json.encode("utf-8")
    ).hexdigest()


def test_spoofed_result_lineage_is_rejected():
    result = _run()

    with pytest.raises(ModeValidationPipelineValidationError):
        dataclasses.replace(
            result,
            mode_lineage_sha256="0" * 64,
        )


def test_result_rejects_mutated_controlled_candidate_schema_version():
    result = _run()
    candidate = result.controlled_top10[0]
    object.__setattr__(
        candidate,
        "schema_version",
        "wrong-candidate-schema",
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            controlled_top10=tuple(result.controlled_top10),
        )


def test_result_rejects_mutated_controlled_candidate_policy_version():
    class StringSubclass(str):
        pass

    result = _run()
    candidate = result.controlled_top10[0]
    object.__setattr__(
        candidate,
        "policy_version",
        StringSubclass(MODE_VALIDATION_PIPELINE_POLICY_VERSION),
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            controlled_top10=tuple(result.controlled_top10),
        )


def test_result_rejects_mutated_final_candidate_schema_version():
    result = _run()
    candidate = result.final_top5[0]
    object.__setattr__(
        candidate,
        "schema_version",
        "wrong-candidate-schema",
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            final_top5=tuple(result.final_top5),
        )


def test_result_rejects_mutated_final_candidate_policy_version():
    class EqualitySpoof:
        def __eq__(self, other):
            return True

    result = _run()
    candidate = result.final_top5[0]
    object.__setattr__(
        candidate,
        "policy_version",
        EqualitySpoof(),
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            final_top5=tuple(result.final_top5),
        )


def test_direct_candidate_replacement_rejects_invalid_candidate_id():
    candidate = _run().controlled_top10[0]

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            candidate,
            candidate_id="candidate/with/slash",
        )


def test_direct_candidate_replacement_rejects_invalid_symbol():
    candidate = _run().controlled_top10[0]

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            candidate,
            symbol=" ASSET1/USDT",
        )


def test_direct_result_replacement_rejects_invalid_due_window_id():
    result = _run()

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            due_window_id="window/with/slash",
        )


def test_result_rejects_duplicate_controlled_candidate_ids():
    result = _run(
        _route(count=2),
        lambda rows: _pipeline_output(
            rows,
            final_indexes=(),
        ),
    )
    first, second = result.controlled_top10
    duplicate_id_second = dataclasses.replace(
        second,
        candidate_id=first.candidate_id,
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            controlled_top10=(first, duplicate_id_second),
        )


def test_result_rejects_duplicate_final_candidate_ids():
    result = _run(
        _route(count=2),
        lambda rows: _pipeline_output(
            rows,
            final_indexes=(0, 1),
        ),
    )
    first, second = result.final_top5
    duplicate_id_second = dataclasses.replace(
        second,
        candidate_id=first.candidate_id,
    )

    with pytest.raises(
        ModeValidationPipelineValidationError,
        match=r"^invalid mode validation pipeline$",
    ):
        dataclasses.replace(
            result,
            final_top5=(first, duplicate_id_second),
        )


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    (
        ("pipeline_invocation_count", True),
        ("pipeline_invocation_count", 0),
        ("pipeline_invocation_count", 2),
        ("retry_count", False),
        ("retry_count", 1),
        ("input_candidate_count", True),
        ("input_candidate_count", 2),
        ("controlled_candidate_count", True),
        ("controlled_candidate_count", 0),
        ("final_candidate_count", False),
        ("final_candidate_count", 2),
    ),
)
def test_incorrect_result_count_fields_are_rejected(
    field_name,
    bad_value,
):
    result = _run()

    with pytest.raises(ModeValidationPipelineValidationError):
        dataclasses.replace(
            result,
            **{field_name: bad_value},
        )


def test_payload_copy_excludes_every_adapter_owned_identity_field():
    result = _run()

    for candidate in (
        *result.controlled_top10,
        *result.final_top5,
    ):
        payload = candidate.payload_copy()
        assert set(payload).isdisjoint(IDENTITY_KEYS)
        assert payload == {
            "nested": {"values": [0]},
            "pipeline_score": 100.0,
            "score": 100,
        }


@pytest.mark.parametrize(
    "bad_row",
    (
        {"symbol": "ASSET1/USDT", "value": float("nan")},
        {"symbol": "ASSET1/USDT", "value": float("inf")},
        {"symbol": "ASSET1/USDT", "value": object()},
        {"symbol": "ASSET1/USDT", "value": (1, 2)},
        {"symbol": "ASSET1/USDT", 7: "bad-key"},
    ),
)
def test_pipeline_rows_reject_noncanonical_json_values(bad_row):
    _assert_invalid(
        _route(),
        lambda rows: {
            "controlled_top10": [bad_row],
            "final_top5": [],
            "usage": {},
        },
    )


def test_pipeline_rows_reject_dict_subclasses():
    class DictSubclass(dict):
        pass

    row = DictSubclass(
        symbol="ASSET1/USDT",
        score=100,
    )
    _assert_invalid(
        _route(),
        lambda rows: {
            "controlled_top10": [row],
            "final_top5": [],
            "usage": {},
        },
    )


def test_bool_string_subclass_and_equality_spoofs_fail_closed():
    result = _run()
    candidate = result.controlled_top10[0]

    class StringSubclass(str):
        pass

    class EqualitySpoof:
        def __eq__(self, other):
            return True

    for field_name, bad_value in (
        ("pipeline_rank", True),
        ("candidate_id", StringSubclass("candidate-1")),
        ("policy_version", EqualitySpoof()),
    ):
        with pytest.raises(ModeValidationPipelineValidationError):
            dataclasses.replace(
                candidate,
                **{field_name: bad_value},
            )

    for field_name, bad_value in (
        ("retry_count", False),
        ("mode", StringSubclass(MODES[0])),
        ("policy_version", EqualitySpoof()),
    ):
        with pytest.raises(ModeValidationPipelineValidationError):
            dataclasses.replace(
                result,
                **{field_name: bad_value},
            )

    route = _route()
    object.__setattr__(route, "mode", EqualitySpoof())
    _assert_invalid(route, _pipeline_output)

    _assert_invalid(
        _route(),
        lambda rows: {
            "controlled_top10": [
                {
                    "symbol": StringSubclass("ASSET1/USDT"),
                    "score": 100,
                }
            ],
            "final_top5": [],
            "usage": {},
        },
    )
