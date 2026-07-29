"""Focused deterministic tests for the pure mode router."""

import ast
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

from engine.mode_data_plan_v1 import (
    build_mode_audit_lineage,
    build_mode_data_plan,
)
from engine.mode_profile_v1 import (
    all_mode_profiles,
    get_mode_profile,
)
from engine.mode_router_v1 import (
    MODE_ROUTER_POLICY_VERSION,
    MODE_ROUTE_RESULT_SCHEMA_VERSION,
    MODE_SCAN_REQUEST_SCHEMA_VERSION,
    ModeRouteResultV1,
    ModeRouterValidationError,
    build_mode_scan_request,
    route_mode_scan,
)


MODES = tuple(profile.mode for profile in all_mode_profiles())


def _request(mode=None):
    selected = MODES[0] if mode is None else mode
    return build_mode_scan_request(
        mode=selected,
        due_window_id="window-2026.07.30T00:00+00",
    )


def _candidate(
    request,
    *,
    candidate_id="candidate-1",
    mode=None,
    lineage=None,
    payload=None,
):
    return {
        "candidate_id": candidate_id,
        "mode": request.mode if mode is None else mode,
        "symbol": "BTC/USDT",
        "mode_lineage_sha256": (
            request.mode_audit_lineage.lineage_sha256
            if lineage is None
            else lineage
        ),
        "payload": (
            {"active": True, "rank": 7, "tags": ["a", "b"]}
            if payload is None
            else payload
        ),
    }


@pytest.mark.parametrize("mode", MODES)
def test_build_request_uses_exact_canonical_contracts(mode):
    request = _request(mode)

    assert request.schema_version == MODE_SCAN_REQUEST_SCHEMA_VERSION
    assert request.router_policy_version == MODE_ROUTER_POLICY_VERSION
    assert request.mode == mode
    assert request.mode_profile is get_mode_profile(mode)
    assert request.mode_data_plan == build_mode_data_plan(mode)
    assert request.mode_audit_lineage == build_mode_audit_lineage(mode)
    with pytest.raises(dataclasses.FrozenInstanceError):
        request.mode = MODES[0]


@pytest.mark.parametrize(
    "field_name",
    ("mode_data_plan", "mode_audit_lineage"),
)
def test_request_rejects_equality_spoofed_owned_contracts(field_name):
    request = _request(MODES[0])

    class EqualitySpoof:
        def __init__(self, **attributes):
            self.__dict__.update(attributes)

        def __eq__(self, other):
            return True

    if field_name == "mode_data_plan":
        spoof = EqualitySpoof(
            mode=request.mode,
            profile_policy_version=request.mode_profile.policy_version,
            policy_version=request.mode_data_plan.policy_version,
        )
    else:
        spoof = EqualitySpoof(
            mode=request.mode,
            mode_profile_version=request.mode_profile.policy_version,
            mode_data_plan_version=request.mode_data_plan.policy_version,
        )

    with pytest.raises(
        ModeRouterValidationError,
        match=r"^invalid mode route$",
    ):
        dataclasses.replace(
            request,
            **{field_name: spoof},
        )


def test_request_owned_contracts_cannot_be_caller_mutated():
    request = _request(MODES[0])

    for owned_contract in (
        request.mode_profile,
        request.mode_data_plan,
        request.mode_audit_lineage,
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            owned_contract.mode = MODES[-1]


@pytest.mark.parametrize(
    ("field_name", "nested_field"),
    (
        ("mode_data_plan", "policy_version"),
        ("mode_audit_lineage", "schema_version"),
    ),
)
def test_request_rejects_canonical_types_with_spoofed_nested_fields(
    field_name,
    nested_field,
):
    request = _request(MODES[0])

    class EqualitySpoof:
        def __eq__(self, other):
            return True

    owned_contract = getattr(request, field_name)
    spoofed_contract = dataclasses.replace(
        owned_contract,
        **{nested_field: EqualitySpoof()},
    )

    with pytest.raises(
        ModeRouterValidationError,
        match=r"^invalid mode route$",
    ):
        dataclasses.replace(
            request,
            **{field_name: spoofed_contract},
        )


@pytest.mark.parametrize(
    ("object_name", "field_name"),
    (
        ("request", "schema_version"),
        ("request", "router_policy_version"),
        ("candidate", "schema_version"),
        ("result", "schema_version"),
        ("result", "router_policy_version"),
    ),
)
def test_router_contract_versions_reject_equality_spoofs(
    object_name,
    field_name,
):
    class EqualitySpoof:
        def __eq__(self, other):
            return True

    request = _request(MODES[0])
    result = route_mode_scan(
        mode=request.mode,
        due_window_id=request.due_window_id,
        scanner=lambda *, request: [_candidate(request)],
    )
    objects = {
        "request": request,
        "candidate": result.candidates[0],
        "result": result,
    }

    with pytest.raises(
        ModeRouterValidationError,
        match=r"^invalid mode route$",
    ):
        dataclasses.replace(
            objects[object_name],
            **{field_name: EqualitySpoof()},
        )


def test_route_api_arguments_are_required_keyword_only():
    for function in (build_mode_scan_request, route_mode_scan):
        parameters = inspect.signature(function).parameters
        assert parameters["mode"].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters["mode"].default is inspect.Parameter.empty
        assert (
            parameters["due_window_id"].kind
            is inspect.Parameter.KEYWORD_ONLY
        )
        assert (
            parameters["due_window_id"].default
            is inspect.Parameter.empty
        )
    scanner_parameter = inspect.signature(
        route_mode_scan
    ).parameters["scanner"]
    assert scanner_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert scanner_parameter.default is inspect.Parameter.empty


@pytest.mark.parametrize(
    "bad_mode",
    ("swing", "UNKNOWN", "", True, 1, None),
)
def test_invalid_mode_fails_before_scanner_call(bad_mode):
    calls = []

    def scanner(*, request):
        calls.append(request)
        return []

    with pytest.raises(
        ModeRouterValidationError,
        match=r"^invalid mode route$",
    ):
        route_mode_scan(
            mode=bad_mode,
            due_window_id="window-1",
            scanner=scanner,
        )

    assert calls == []


def test_scanner_is_called_once_with_only_request_keyword():
    calls = []

    def scanner(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    result = route_mode_scan(
        mode=MODES[0],
        due_window_id="window-1",
        scanner=scanner,
    )

    assert len(calls) == 1
    assert calls[0][0] == ()
    assert set(calls[0][1]) == {"request"}
    assert calls[0][1]["request"].mode == MODES[0]
    assert result.scanner_invocation_count == 1
    assert result.retry_count == 0


@pytest.mark.parametrize("mode", MODES)
def test_scanner_receives_each_exact_requested_mode(mode):
    received = []

    def scanner(*, request):
        received.append(request.mode)
        return []

    route_mode_scan(
        mode=mode,
        due_window_id=f"window-{mode.lower()}",
        scanner=scanner,
    )

    assert received == [mode]


def test_empty_candidates_are_valid_without_fallback():
    result = route_mode_scan(
        mode=MODES[-1],
        due_window_id="empty-window",
        scanner=lambda *, request: [],
    )

    assert result.mode == MODES[-1]
    assert result.candidates == ()


@pytest.mark.parametrize("candidate_count", (1, 3))
def test_candidate_order_is_preserved(candidate_count):
    def scanner(*, request):
        return [
            _candidate(
                request,
                candidate_id=f"candidate-{index}",
            )
            for index in range(candidate_count)
        ]

    result = route_mode_scan(
        mode=MODES[1],
        due_window_id="ordered-window",
        scanner=scanner,
    )

    assert tuple(
        candidate.candidate_id for candidate in result.candidates
    ) == tuple(
        f"candidate-{index}" for index in range(candidate_count)
    )


@pytest.mark.parametrize("field", ("mode", "mode_lineage_sha256"))
def test_candidate_mode_and_lineage_must_match_request(field):
    def scanner(*, request):
        candidate = _candidate(request)
        candidate[field] = (
            MODES[-1]
            if field == "mode"
            else "0" * 64
        )
        return [candidate]

    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="mismatch-window",
            scanner=scanner,
        )


def test_cross_mode_candidate_borrowing_fails_closed():
    borrowed = _request(MODES[-1])

    def scanner(*, request):
        return [
            _candidate(
                borrowed,
                mode=borrowed.mode,
                lineage=borrowed.mode_audit_lineage.lineage_sha256,
            )
        ]

    with pytest.raises(
        ModeRouterValidationError,
        match=r"^invalid mode route$",
    ):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="cross-mode-window",
            scanner=scanner,
        )


def test_duplicate_candidate_ids_are_rejected():
    def scanner(*, request):
        return [
            _candidate(request, candidate_id="duplicate"),
            _candidate(request, candidate_id="duplicate"),
        ]

    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="duplicate-window",
            scanner=scanner,
        )


@pytest.mark.parametrize("operation", ("missing", "additional"))
def test_candidate_fields_must_be_exact(operation):
    def scanner(*, request):
        candidate = _candidate(request)
        if operation == "missing":
            candidate.pop("symbol")
        else:
            candidate["extra"] = None
        return [candidate]

    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="fields-window",
            scanner=scanner,
        )


@pytest.mark.parametrize(
    "bad_output",
    (
        {"candidate_id": "mapping"},
        "string",
        {"set"},
        7,
        None,
    ),
)
def test_non_sequence_scanner_outputs_are_rejected(bad_output):
    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="output-window",
            scanner=lambda *, request: bad_output,
        )


def test_generator_and_iterator_outputs_are_rejected():
    for output_factory in (
        lambda: (item for item in ()),
        lambda: iter(()),
    ):
        with pytest.raises(ModeRouterValidationError):
            route_mode_scan(
                mode=MODES[0],
                due_window_id="iterator-window",
                scanner=lambda *, request: output_factory(),
            )


def test_scanner_exception_is_sanitized_and_not_retried():
    calls = []

    def scanner(*, request):
        calls.append(request)
        raise RuntimeError("secret candidate payload")

    with pytest.raises(ModeRouterValidationError) as captured:
        route_mode_scan(
            mode=MODES[0],
            due_window_id="exception-window",
            scanner=scanner,
        )

    assert str(captured.value) == "invalid mode route"
    assert "secret" not in str(captured.value)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "payload",
    (
        [],
        "scalar",
        b"bytes",
        {"set": {1}},
        {"custom": object()},
        {1: "non-string-key"},
        {"tuple": (1, 2)},
        {"mode": "wrong"},
        {"mode_lineage_sha256": "0" * 64},
    ),
)
def test_malformed_or_noncanonical_payloads_fail_closed(payload):
    def scanner(*, request):
        return [_candidate(request, payload=payload)]

    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="payload-window",
            scanner=scanner,
        )


@pytest.mark.parametrize(
    "nonfinite",
    (float("nan"), float("inf"), float("-inf")),
)
def test_nonfinite_payload_numbers_fail_closed(nonfinite):
    def scanner(*, request):
        return [_candidate(request, payload={"value": nonfinite})]

    with pytest.raises(ModeRouterValidationError):
        route_mode_scan(
            mode=MODES[0],
            due_window_id="nonfinite-window",
            scanner=scanner,
        )


def test_payload_mutation_cannot_change_candidate_or_hash():
    payload = {"active": True, "nested": {"values": [1, 2]}}

    def scanner(*, request):
        return [_candidate(request, payload=payload)]

    result = route_mode_scan(
        mode=MODES[0],
        due_window_id="mutation-window",
        scanner=scanner,
    )
    candidate = result.candidates[0]
    original_json = candidate.payload_json
    original_hash = candidate.payload_sha256

    payload["active"] = False
    payload["nested"]["values"].append(3)
    copy = candidate.payload_copy()
    copy["nested"]["values"].append(4)

    assert candidate.payload_json == original_json
    assert candidate.payload_sha256 == original_hash
    assert candidate.payload_copy()["active"] is True
    assert candidate.payload_copy()["nested"]["values"] == [1, 2]


def test_identical_input_produces_identical_mappings_and_hashes():
    def scanner(*, request):
        return [
            _candidate(
                request,
                payload={"z": 1, "a": [True, None, "x"]},
            )
        ]

    first = route_mode_scan(
        mode=MODES[1],
        due_window_id="repeat-window",
        scanner=scanner,
    )
    second = route_mode_scan(
        mode=MODES[1],
        due_window_id="repeat-window",
        scanner=scanner,
    )

    assert first.to_mapping() == second.to_mapping()
    assert (
        json.dumps(
            first.to_mapping(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        == json.dumps(
            second.to_mapping(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    assert (
        first.candidates[0].payload_sha256
        == second.candidates[0].payload_sha256
    )


def test_modes_have_distinct_lineage_identities():
    hashes = {
        _request(mode).mode_audit_lineage.lineage_sha256
        for mode in MODES
    }

    assert len(hashes) == len(MODES)


def test_result_counters_reject_boolean_integer_aliases():
    result = route_mode_scan(
        mode=MODES[0],
        due_window_id="counter-window",
        scanner=lambda *, request: [],
    )

    for field_name, bad_value in (
        ("scanner_invocation_count", True),
        ("scanner_invocation_count", 0),
        ("scanner_invocation_count", 2),
        ("retry_count", False),
        ("retry_count", 1),
    ):
        with pytest.raises(ModeRouterValidationError):
            dataclasses.replace(
                result,
                **{field_name: bad_value},
            )


def test_result_containers_are_immutable_and_mappings_are_fresh():
    caller_candidates = []
    request = _request(MODES[0])
    caller_candidates.append(
        route_mode_scan(
            mode=MODES[0],
            due_window_id="immutable-window",
            scanner=lambda *, request: [_candidate(request)],
        ).candidates[0]
    )
    result = ModeRouteResultV1(
        schema_version=MODE_ROUTE_RESULT_SCHEMA_VERSION,
        router_policy_version=MODE_ROUTER_POLICY_VERSION,
        mode=request.mode,
        due_window_id=request.due_window_id,
        mode_lineage_sha256=request.mode_audit_lineage.lineage_sha256,
        scanner_invocation_count=1,
        retry_count=0,
        candidates=caller_candidates,
    )
    caller_candidates.clear()

    assert len(result.candidates) == 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.mode = MODES[-1]
    with pytest.raises(TypeError):
        result.candidates[0] = result.candidates[0]

    first = result.to_mapping()
    second = result.to_mapping()
    first["candidates"].clear()
    second["candidates"][0]["candidate_id"] = "changed"

    assert len(result.candidates) == 1
    assert result.candidates[0].candidate_id == "candidate-1"
    assert first is not second


def test_engine_source_is_pure_and_has_no_mode_literals():
    source_path = (
        Path(__file__).parents[1]
        / "engine"
        / "mode_router_v1.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    allowed_imports = {
        "__future__",
        "collections",
        "dataclasses",
        "hashlib",
        "json",
        "re",
        "typing",
        "engine",
    }
    prohibited_dependencies = {
        "scanner",
        "master_engine",
        "binance",
        "ccxt",
        "requests",
        "httpx",
        "socket",
        "telegram",
        "subprocess",
        "pathlib",
        "os",
        "threading",
        "asyncio",
        "time",
    }
    prohibited_calls = {
        "open",
        "sleep",
        "system",
        "run",
        "Popen",
        "connect",
        "send_message",
        "create_order",
        "place_order",
        "fetch_ohlcv",
        "fetch_balance",
    }
    imports = set()
    calls = set()
    string_literals = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
            assert node.module not in {
                "engine.scanner",
                "engine.master_engine_v4",
            }
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        ):
            string_literals.add(node.value)

    assert imports <= allowed_imports
    assert not imports & prohibited_dependencies
    assert not calls & prohibited_calls
    assert not set(MODES) & string_literals
