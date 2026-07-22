"""Contract tests for the pure Phase 12 activation-mode authorization verifier."""
from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import importlib
import inspect

import pytest

from engine.phase_12_activation_configuration_v1 import (
    Phase12ActivationConfigurationV1,
)


_MODULE_NAME = "engine.phase_12_activation_mode_authorization_verifier_v1"
_COMMIT = "a" * 40
_OTHER_COMMIT = "b" * 40
_APPROVAL = datetime(2026, 7, 22, 12, 0, 0, tzinfo=timezone.utc)
_EXPIRY = _APPROVAL + timedelta(minutes=5)
_NOW = _APPROVAL + timedelta(minutes=1)
_APPROVED_AT = "2026-07-22T12:00:00Z"
_EXPIRES_AT = "2026-07-22T12:05:00Z"
_MODES = (
    "CREDENTIAL_VALIDATION",
    "TELEGRAM_CONNECTIVITY_VALIDATION",
    "TELEGRAM_START_VALIDATION",
    "CONTROLLED_WORKLOAD",
)
_GATES = {
    "CREDENTIAL_VALIDATION": (True, True, False, False, False),
    "TELEGRAM_CONNECTIVITY_VALIDATION": (True, True, True, False, False),
    "TELEGRAM_START_VALIDATION": (True, True, True, False, True),
    "CONTROLLED_WORKLOAD": (True, True, True, True, True),
}


def _public_types() -> tuple[type[object], type[object], object]:
    module = importlib.import_module(_MODULE_NAME)
    return (
        module.Phase12ActivationAuthorizationRecordV1,
        module.Phase12ActivationModeAuthorizationVerifierV1,
        module,
    )


def _configuration(mode: str = "CREDENTIAL_VALIDATION") -> Phase12ActivationConfigurationV1:
    gates = _GATES[mode]
    return Phase12ActivationConfigurationV1(
        schema_version="phase12-activation-v1",
        activation_mode=mode,
        owner_authorization_id="owner-authorization-v1",
        approval_checkpoint_id="checkpoint-v1",
        approved_locked_commit=_COMMIT,
        approved_at=_APPROVED_AT,
        expires_at=_EXPIRES_AT,
        activation_gate_open=gates[0],
        credential_gate_open=gates[1],
        network_gate_open=gates[2],
        workload_gate_open=gates[3],
        telegram_start_authorized=gates[4],
    )


def _record(**overrides: object) -> object:
    record_type, _, _ = _public_types()
    values: dict[str, object] = {
        "mode": "CREDENTIAL_VALIDATION",
        "owner_authorization_id": "owner-authorization-v1",
        "checkpoint_id": "checkpoint-v1",
        "approved_locked_commit": _COMMIT,
        "approval_timestamp_utc": _APPROVAL,
        "expires_at_utc": _EXPIRY,
        "accepted_locked_commit": _COMMIT,
    }
    values.update(overrides)
    return record_type(**values)


def _verifier(records: object = ()) -> object:
    _, verifier_type, _ = _public_types()
    return verifier_type(records=records)


def _verify(
    verifier: object,
    *,
    configuration: object | None = None,
    activation_mode: object = "CREDENTIAL_VALIDATION",
    owner_authorization_id: object = "owner-authorization-v1",
    approval_checkpoint_id: object = "checkpoint-v1",
    approved_locked_commit: object = _COMMIT,
    approved_at: object = _APPROVED_AT,
    expires_at: object = _EXPIRES_AT,
    accepted_locked_commit: object = _COMMIT,
    now_utc: object = _NOW,
) -> object:
    return verifier(
        configuration=_configuration() if configuration is None else configuration,
        activation_mode=activation_mode,
        owner_authorization_id=owner_authorization_id,
        approval_checkpoint_id=approval_checkpoint_id,
        approved_locked_commit=approved_locked_commit,
        approved_at=approved_at,
        expires_at=expires_at,
        accepted_locked_commit=accepted_locked_commit,
        now_utc=now_utc,
    )


def test_public_types_and_keyword_only_apis_are_exact() -> None:
    record_type, verifier_type, _ = _public_types()
    assert record_type.__name__ == "Phase12ActivationAuthorizationRecordV1"
    assert verifier_type.__name__ == "Phase12ActivationModeAuthorizationVerifierV1"
    assert tuple(inspect.signature(record_type).parameters) == (
        "mode",
        "owner_authorization_id",
        "checkpoint_id",
        "approved_locked_commit",
        "approval_timestamp_utc",
        "expires_at_utc",
        "accepted_locked_commit",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in inspect.signature(record_type).parameters.values()
    )
    assert tuple(inspect.signature(verifier_type).parameters) == ("records",)
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in inspect.signature(verifier_type).parameters.values()
    )
    assert tuple(inspect.signature(verifier_type.__call__).parameters) == (
        "self",
        "configuration",
        "activation_mode",
        "owner_authorization_id",
        "approval_checkpoint_id",
        "approved_locked_commit",
        "approved_at",
        "expires_at",
        "accepted_locked_commit",
        "now_utc",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for name, parameter in inspect.signature(verifier_type.__call__).parameters.items()
        if name != "self"
    )


def test_record_is_immutable_slotted_and_contains_only_authorization_evidence() -> None:
    record = _record()
    assert not hasattr(record, "__dict__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        record.mode = "CONTROLLED_WORKLOAD"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        record.extra = "forbidden"
    assert "credential" not in repr(record).lower()
    assert "token" not in repr(record).lower()


def test_verifier_normalizes_records_to_an_immutable_tuple() -> None:
    record = _record()
    supplied = [record]
    verifier = _verifier(supplied)
    supplied.append(_record(mode="CONTROLLED_WORKLOAD"))
    assert verifier.records == (record,)
    assert isinstance(verifier.records, tuple)


def test_empty_policy_rejects_every_non_closed_mode() -> None:
    verifier = _verifier()
    for mode in _MODES:
        assert _verify(
            verifier,
            configuration=_configuration(mode),
            activation_mode=mode,
        ) is False


@pytest.mark.parametrize("mode", _MODES)
def test_one_exact_record_authorizes_each_accepted_non_closed_mode(mode: str) -> None:
    verifier = _verifier((_record(mode=mode),))
    assert _verify(
        verifier,
        configuration=_configuration(mode),
        activation_mode=mode,
    ) is True


def test_zero_and_duplicate_exact_matches_fail_closed() -> None:
    record = _record()
    assert _verify(_verifier()) is False
    assert _verify(_verifier((record, record))) is False


def test_unrelated_records_do_not_prevent_one_exact_match() -> None:
    exact = _record()
    unrelated = _record(owner_authorization_id="other-owner-v1")
    assert _verify(_verifier((unrelated, exact))) is True


@pytest.mark.parametrize(
    ("configuration_field", "callable_value"),
    (
        ("activation_mode", "CONTROLLED_WORKLOAD"),
        ("owner_authorization_id", "other-owner-v1"),
        ("approval_checkpoint_id", "other-checkpoint-v1"),
        ("approved_locked_commit", _OTHER_COMMIT),
        ("approved_at", "2026-07-22T12:01:00Z"),
        ("expires_at", "2026-07-22T12:06:00Z"),
    ),
)
def test_configuration_and_callable_evidence_must_correlate(
    configuration_field: str, callable_value: object
) -> None:
    verifier = _verifier((_record(),))
    configuration = replace(_configuration(), **{configuration_field: callable_value})
    assert _verify(verifier, configuration=configuration) is False


@pytest.mark.parametrize(
    "accepted_locked_commit",
    (None, "", _OTHER_COMMIT, _COMMIT[:12]),
)
def test_accepted_commit_must_be_separate_complete_and_equal(
    accepted_locked_commit: object,
) -> None:
    assert _verify(
        _verifier((_record(),)), accepted_locked_commit=accepted_locked_commit
    ) is False


def test_record_commit_fields_must_agree_with_configuration_and_accepted_context() -> None:
    assert _verify(_verifier((_record(accepted_locked_commit=_OTHER_COMMIT),))) is False
    assert _verify(_verifier((_record(approved_locked_commit=_OTHER_COMMIT),))) is False


def test_time_window_is_inclusive_at_approval_and_exclusive_at_expiry() -> None:
    verifier = _verifier((_record(),))
    assert _verify(verifier, now_utc=_APPROVAL) is True
    assert _verify(verifier, now_utc=_APPROVAL - timedelta(microseconds=1)) is False
    assert _verify(verifier, now_utc=_EXPIRY) is False
    assert _verify(verifier, now_utc=_EXPIRY + timedelta(microseconds=1)) is False


def test_naive_or_noncanonical_timestamp_evidence_fails_closed() -> None:
    naive = datetime(2026, 7, 22, 12, 0, 0)
    assert _verify(_verifier((_record(),)), now_utc=naive) is False
    with pytest.raises(ValueError):
        _record(approval_timestamp_utc=naive)
    with pytest.raises(ValueError):
        _record(expires_at_utc=naive)
    assert _verify(
        _verifier((_record(),)),
        configuration=replace(_configuration(), approved_at="2026-07-22T12:00:00"),
    ) is False


@pytest.mark.parametrize(
    "overrides",
    (
        {"mode": "CLOSED"},
        {"mode": "PRODUCTION"},
        {"mode": "credential_validation"},
        {"mode": " CREDENTIAL_VALIDATION"},
        {"mode": 1},
        {"owner_authorization_id": ""},
        {"owner_authorization_id": 1},
        {"checkpoint_id": ""},
        {"checkpoint_id": 1},
        {"approved_locked_commit": ""},
        {"approved_locked_commit": "short"},
        {"accepted_locked_commit": ""},
        {"accepted_locked_commit": "short"},
        {"approval_timestamp_utc": "2026-07-22T12:00:00Z"},
        {"expires_at_utc": "2026-07-22T12:05:00Z"},
        {"approval_timestamp_utc": _EXPIRY},
        {"expires_at_utc": _APPROVAL},
    ),
)
def test_malformed_record_policy_is_rejected_at_construction(
    overrides: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        _record(**overrides)


def test_non_record_policy_member_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError):
        _verifier((object(),))


@pytest.mark.parametrize(
    "mode",
    ("CLOSED", "PRODUCTION", "credential_validation", " CREDENTIAL_VALIDATION", 1),
)
def test_closed_unknown_and_malformed_callable_modes_are_denied(mode: object) -> None:
    assert _verify(_verifier((_record(),)), activation_mode=mode) is False


def test_repeated_calls_are_boolean_deterministic_and_do_not_grant_by_cache() -> None:
    verifier = _verifier((_record(),))
    results = [_verify(verifier), _verify(verifier)]
    assert results == [True, True]
    assert all(type(result) is bool for result in results)
    assert _verify(_verifier()) is False


class _OrdinaryFailureConfiguration:
    @property
    def activation_mode(self) -> object:
        raise RuntimeError("synthetic ordinary failure")


class _BaseInterrupt(BaseException):
    pass


class _BaseFailureConfiguration:
    @property
    def activation_mode(self) -> object:
        raise _BaseInterrupt()


def test_unexpected_external_exceptions_propagate_for_outer_boundary_mapping() -> None:
    verifier = _verifier((_record(),))
    with pytest.raises(RuntimeError):
        _verify(verifier, configuration=_OrdinaryFailureConfiguration())
    with pytest.raises(_BaseInterrupt):
        _verify(verifier, configuration=_BaseFailureConfiguration())


def test_source_is_pure_and_exposes_no_dynamic_output_or_effect_surface() -> None:
    _, _, module = _public_types()
    source = inspect.getsource(module)
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not imported.intersection(
        {"os", "subprocess", "logging", "socket", "requests", "httpx", "telegram"}
    )
    for forbidden in ("open(", "environ", "argv", "systemctl", "uuid", "random", "sleep("):
        assert forbidden not in source
    assert "return True" in source and "return False" in source
