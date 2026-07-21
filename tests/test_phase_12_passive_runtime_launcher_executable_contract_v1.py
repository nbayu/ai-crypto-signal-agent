"""RED contract for a test-only, passive runtime launcher executable."""
from __future__ import annotations

from dataclasses import fields, is_dataclass

import pytest

from engine.phase_12_passive_runtime_launcher_executable_contract_v1 import (
    PassiveRuntimeLauncherAuditEvidenceV1,
    PassiveRuntimeLauncherConfigurationV1,
    PassiveRuntimeLauncherFailureV1,
    PassiveRuntimeLauncherPolicyV1,
    PassiveRuntimeLauncherResultV1,
    PassiveRuntimeLauncherShutdownRequestV1,
    PassiveRuntimeLauncherStateV1,
    PassiveRuntimeLauncherSyntheticSignalV1,
    PassiveRuntimeLauncherTransitionV1,
    build_passive_runtime_launcher_audit_evidence_v1,
    build_passive_runtime_launcher_v1,
    evaluate_passive_runtime_launcher_startup_v1,
    evaluate_passive_runtime_launcher_synthetic_signal_v1,
    main,
    request_passive_runtime_launcher_shutdown_v1,
)


_FAILURES = (
    "POLICY_ID_EMPTY", "POLICY_VERSION_EMPTY", "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED",
    "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED", "SYNTHETIC_SIGNAL_TEST_NOT_AUTHORIZED",
    "EXECUTION_MODE_MISMATCH", "SERVICE_UNIT_MISMATCH", "SERVICE_USER_MISMATCH",
    "SERVICE_GROUP_MISMATCH", "INSTALLATION_PATH_MISMATCH", "WORKING_DIRECTORY_MISMATCH",
    "PYTHON_INTERPRETER_PATH_MISMATCH", "STATE_DIRECTORY_MISMATCH", "CACHE_DIRECTORY_MISMATCH",
    "RUNTIME_DIRECTORY_MISMATCH", "LOG_DESTINATION_MISMATCH", "LOG_DIRECTORY_NOT_ALLOWED",
    "ACTIVATION_GATE_MUST_REMAIN_CLOSED", "CREDENTIAL_GATE_MUST_REMAIN_CLOSED",
    "NETWORK_GATE_MUST_REMAIN_CLOSED", "WORKLOAD_GATE_MUST_REMAIN_CLOSED",
    "FILESYSTEM_READ_NOT_AUTHORIZED", "FILESYSTEM_WRITE_NOT_AUTHORIZED",
    "ENVIRONMENT_READ_NOT_AUTHORIZED", "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED",
    "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED", "CREDENTIAL_LOADING_NOT_AUTHORIZED",
    "CREDENTIAL_VALIDATION_NOT_AUTHORIZED", "SYSTEMD_ACCESS_NOT_AUTHORIZED", "NETWORK_NOT_AUTHORIZED",
    "PROVIDER_TRANSMISSION_NOT_AUTHORIZED", "SCANNER_EXECUTION_NOT_AUTHORIZED",
    "WORKER_START_NOT_AUTHORIZED", "SCHEDULER_START_NOT_AUTHORIZED", "TELEGRAM_START_NOT_AUTHORIZED",
    "DATABASE_MUTATION_NOT_AUTHORIZED", "ARTIFACT_PUBLICATION_NOT_AUTHORIZED",
    "TRADING_NOT_AUTHORIZED", "RUNTIME_ACTIVATION_NOT_AUTHORIZED", "PUBLICATION_NOT_AUTHORIZED",
    "INVALID_STATE_TRANSITION", "UNKNOWN_SYNTHETIC_SIGNAL", "RELOAD_NOT_AUTHORIZED",
    "RAW_CREDENTIAL_EXPOSURE_DETECTED", "PROVIDER_ENDPOINT_EXPOSURE_DETECTED",
    "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED", "RAW_EXCEPTION_EXPOSURE_DETECTED",
)
_STATES = (
    "CREATED", "CONFIGURATION_VALIDATED", "PASSIVE_READY", "SHUTDOWN_REQUESTED",
    "GRACEFUL_SHUTDOWN_COMPLETE", "BLOCKED",
)


def _frozen(record: object) -> None:
    assert is_dataclass(record)
    assert type(record).__dataclass_params__.frozen
    assert "__dict__" not in type(record).__slots__


def _policy(**overrides: object) -> PassiveRuntimeLauncherPolicyV1:
    values = dict(
        policy_id="passive-launcher-policy-v1", policy_version="V1",
        launcher_module="engine.phase_12_passive_runtime_launcher_executable_contract_v1",
        launcher_mode="PASSIVE_TEST_MODE", expected_service_unit="ai-crypto-signal-agent.service",
        expected_service_user="ai-crypto-signal-agent", expected_service_group="ai-crypto-signal-agent",
        expected_installation_path="/opt/ai-crypto-signal-agent",
        expected_working_directory="/opt/ai-crypto-signal-agent",
        expected_python_interpreter="/opt/ai-crypto-signal-agent/.venv/bin/python",
        passive_test_execution_authorized=True, synthetic_signal_tests_authorized=True,
        launcher_implementation_authorized=True, real_signal_registration_authorized=False,
        filesystem_read_authorized=False, filesystem_write_authorized=False,
        environment_read_authorized=False, credential_access_authorized=False,
        credential_loading_authorized=False, credential_validation_authorized=False,
        systemd_access_authorized=False, network_authorized=False,
        provider_transmission_authorized=False, scanner_execution_authorized=False,
        worker_start_authorized=False, scheduler_start_authorized=False,
        telegram_start_authorized=False, database_mutation_authorized=False,
        artifact_publication_authorized=False, trading_authorized=False,
        runtime_activation_authorized=False, publication_authorized=False, fail_closed=True,
    )
    return PassiveRuntimeLauncherPolicyV1(**(values | overrides))


def _configuration(**overrides: object) -> PassiveRuntimeLauncherConfigurationV1:
    values = dict(
        launcher_id="passive-launcher-v1", invocation_id="passive-invocation-v1",
        execution_mode="PASSIVE_TEST_MODE", service_unit="ai-crypto-signal-agent.service",
        service_user="ai-crypto-signal-agent", service_group="ai-crypto-signal-agent",
        installation_path="/opt/ai-crypto-signal-agent",
        working_directory="/opt/ai-crypto-signal-agent",
        python_interpreter="/opt/ai-crypto-signal-agent/.venv/bin/python",
        state_directory_classification="/var/lib/ai-crypto-signal-agent",
        cache_directory_classification="/var/cache/ai-crypto-signal-agent",
        runtime_directory_classification="/run/ai-crypto-signal-agent",
        log_destination="JOURNALD_ONLY", log_directory="NONE", credential_gate_open=False,
        network_gate_open=False, workload_gate_open=False, activation_gate_open=False,
        credential_exposure_detected=False, endpoint_exposure_detected=False,
        authorization_exposure_detected=False, real_process_control_requested=False,
        passive_configuration_complete=True,
    )
    return PassiveRuntimeLauncherConfigurationV1(**(values | overrides))


def _signal(**overrides: object) -> PassiveRuntimeLauncherSyntheticSignalV1:
    return PassiveRuntimeLauncherSyntheticSignalV1(
        signal_id="synthetic-signal-v1", signal_classification="SYNTHETIC_SIGTERM",
        **overrides,
    )


def _shutdown(**overrides: object) -> PassiveRuntimeLauncherShutdownRequestV1:
    return PassiveRuntimeLauncherShutdownRequestV1(
        request_id="shutdown-request-v1", shutdown_classification="SYNTHETIC_GRACEFUL_SHUTDOWN",
        **overrides,
    )


def _assert_passive_authority(record: object) -> None:
    assert record.passive_test_execution_authorized is True
    assert record.synthetic_signal_tests_authorized is True
    assert record.launcher_implementation_authorized is True
    assert record.real_signal_registration_authorized is False
    assert record.filesystem_read_authorized is False
    assert record.filesystem_write_authorized is False
    assert record.environment_read_authorized is False
    assert record.credential_access_authorized is False
    assert record.credential_loading_authorized is False
    assert record.credential_validation_authorized is False
    assert record.systemd_access_authorized is False
    assert record.network_authorized is False
    assert record.provider_transmission_authorized is False
    assert record.scanner_execution_authorized is False
    assert record.worker_start_authorized is False
    assert record.scheduler_start_authorized is False
    assert record.telegram_start_authorized is False
    assert record.database_mutation_authorized is False
    assert record.artifact_publication_authorized is False
    assert record.trading_authorized is False
    assert record.runtime_activation_authorized is False
    assert record.publication_authorized is False
    assert record.fail_closed is True


def test_public_contract_records_are_frozen_slotted_and_redacted() -> None:
    records = (_policy(), _configuration(), _signal(), _shutdown())
    for record in records:
        _frozen(record)
    for record_type in (
        PassiveRuntimeLauncherStateV1, PassiveRuntimeLauncherTransitionV1,
        PassiveRuntimeLauncherResultV1, PassiveRuntimeLauncherFailureV1,
        PassiveRuntimeLauncherAuditEvidenceV1,
    ):
        assert hasattr(record_type, "__dataclass_fields__")
    forbidden = ("credential_value", "credential_path", "environment_value", "provider_endpoint",
                 "authorization_header", "token_value", "process_id", "hostname", "account_identity")
    names = tuple(name.lower() for record in records for name in tuple(item.name for item in fields(record)))
    assert not any(token in name for name in names for token in forbidden)


def test_build_and_startup_follow_the_complete_passive_state_machine() -> None:
    created = build_passive_runtime_launcher_v1(policy=_policy(), configuration=_configuration())
    _frozen(created)
    assert created.state_code == "CREATED"
    result = evaluate_passive_runtime_launcher_startup_v1(
        policy=_policy(), configuration=_configuration(), current_state=created,
    )
    _frozen(result)
    assert result.ready is True
    assert result.result_classification == "PASSIVE_RUNTIME_LAUNCHER_READY_IN_TEST_MODE"
    assert result.current_state.state_code == "PASSIVE_READY"
    assert tuple(item.to_state for item in result.transitions) == (
        "CONFIGURATION_VALIDATED", "PASSIVE_READY",
    )
    assert result.failure_codes == ()
    _assert_passive_authority(result)


@pytest.mark.parametrize(
    ("policy_overrides", "configuration_overrides", "failure_code"),
    (
        ({"policy_id": ""}, {}, "POLICY_ID_EMPTY"),
        ({"policy_version": ""}, {}, "POLICY_VERSION_EMPTY"),
        ({"launcher_implementation_authorized": False}, {}, "LAUNCHER_IMPLEMENTATION_NOT_AUTHORIZED"),
        ({"passive_test_execution_authorized": False}, {}, "PASSIVE_TEST_EXECUTION_NOT_AUTHORIZED"),
        ({"synthetic_signal_tests_authorized": False}, {}, "SYNTHETIC_SIGNAL_TEST_NOT_AUTHORIZED"),
        ({}, {"execution_mode": "ACTIVE"}, "EXECUTION_MODE_MISMATCH"),
        ({}, {"service_unit": "other.service"}, "SERVICE_UNIT_MISMATCH"),
        ({}, {"service_user": "other-user"}, "SERVICE_USER_MISMATCH"),
        ({}, {"service_group": "other-group"}, "SERVICE_GROUP_MISMATCH"),
        ({}, {"installation_path": "/opt/other"}, "INSTALLATION_PATH_MISMATCH"),
        ({}, {"working_directory": "/opt/other"}, "WORKING_DIRECTORY_MISMATCH"),
        ({}, {"python_interpreter": "/opt/other/bin/python"}, "PYTHON_INTERPRETER_PATH_MISMATCH"),
        ({}, {"state_directory_classification": "/var/lib/other"}, "STATE_DIRECTORY_MISMATCH"),
        ({}, {"cache_directory_classification": "/var/cache/other"}, "CACHE_DIRECTORY_MISMATCH"),
        ({}, {"runtime_directory_classification": "/run/other"}, "RUNTIME_DIRECTORY_MISMATCH"),
        ({}, {"log_destination": "FILE"}, "LOG_DESTINATION_MISMATCH"),
        ({}, {"log_directory": "/var/log/other"}, "LOG_DIRECTORY_NOT_ALLOWED"),
        ({}, {"activation_gate_open": True}, "ACTIVATION_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"credential_gate_open": True}, "CREDENTIAL_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"network_gate_open": True}, "NETWORK_GATE_MUST_REMAIN_CLOSED"),
        ({}, {"workload_gate_open": True}, "WORKLOAD_GATE_MUST_REMAIN_CLOSED"),
        ({"filesystem_read_authorized": True}, {}, "FILESYSTEM_READ_NOT_AUTHORIZED"),
        ({"filesystem_write_authorized": True}, {}, "FILESYSTEM_WRITE_NOT_AUTHORIZED"),
        ({"environment_read_authorized": True}, {}, "ENVIRONMENT_READ_NOT_AUTHORIZED"),
        ({"real_signal_registration_authorized": True}, {}, "REAL_SIGNAL_REGISTRATION_NOT_AUTHORIZED"),
        ({"credential_access_authorized": True}, {}, "CREDENTIAL_VALUE_ACCESS_NOT_AUTHORIZED"),
        ({"credential_loading_authorized": True}, {}, "CREDENTIAL_LOADING_NOT_AUTHORIZED"),
        ({"credential_validation_authorized": True}, {}, "CREDENTIAL_VALIDATION_NOT_AUTHORIZED"),
        ({"systemd_access_authorized": True}, {}, "SYSTEMD_ACCESS_NOT_AUTHORIZED"),
        ({"network_authorized": True}, {}, "NETWORK_NOT_AUTHORIZED"),
        ({"provider_transmission_authorized": True}, {}, "PROVIDER_TRANSMISSION_NOT_AUTHORIZED"),
        ({"scanner_execution_authorized": True}, {}, "SCANNER_EXECUTION_NOT_AUTHORIZED"),
        ({"worker_start_authorized": True}, {}, "WORKER_START_NOT_AUTHORIZED"),
        ({"scheduler_start_authorized": True}, {}, "SCHEDULER_START_NOT_AUTHORIZED"),
        ({"telegram_start_authorized": True}, {}, "TELEGRAM_START_NOT_AUTHORIZED"),
        ({"database_mutation_authorized": True}, {}, "DATABASE_MUTATION_NOT_AUTHORIZED"),
        ({"artifact_publication_authorized": True}, {}, "ARTIFACT_PUBLICATION_NOT_AUTHORIZED"),
        ({"trading_authorized": True}, {}, "TRADING_NOT_AUTHORIZED"),
        ({"runtime_activation_authorized": True}, {}, "RUNTIME_ACTIVATION_NOT_AUTHORIZED"),
        ({"publication_authorized": True}, {}, "PUBLICATION_NOT_AUTHORIZED"),
        ({}, {"credential_exposure_detected": True}, "RAW_CREDENTIAL_EXPOSURE_DETECTED"),
        ({}, {"endpoint_exposure_detected": True}, "PROVIDER_ENDPOINT_EXPOSURE_DETECTED"),
        ({}, {"authorization_exposure_detected": True}, "AUTHORIZATION_MATERIAL_EXPOSURE_DETECTED"),
        ({}, {"real_process_control_requested": True}, "RAW_EXCEPTION_EXPOSURE_DETECTED"),
    ),
)
def test_startup_rejections_are_fail_closed_and_deterministically_ordered(
    policy_overrides: dict[str, object], configuration_overrides: dict[str, object], failure_code: str,
) -> None:
    result = evaluate_passive_runtime_launcher_startup_v1(
        policy=_policy(**policy_overrides), configuration=_configuration(**configuration_overrides),
        current_state=build_passive_runtime_launcher_v1(policy=_policy(), configuration=_configuration()),
    )
    _frozen(result)
    assert result.ready is False
    assert result.current_state.state_code == "BLOCKED"
    assert failure_code in result.failure_codes
    assert tuple(item.failure_code for item in result.failures) == result.failure_codes
    assert tuple(sorted(result.failure_codes, key=_FAILURES.index)) == result.failure_codes
    _assert_passive_authority(result)


def test_synthetic_sigterm_sigint_hup_unknown_and_shutdown_are_deterministic() -> None:
    ready = evaluate_passive_runtime_launcher_startup_v1(
        policy=_policy(), configuration=_configuration(),
        current_state=build_passive_runtime_launcher_v1(policy=_policy(), configuration=_configuration()),
    )
    term = evaluate_passive_runtime_launcher_synthetic_signal_v1(
        policy=_policy(), current_state=ready.current_state, synthetic_signal=_signal(),
    )
    interrupt = evaluate_passive_runtime_launcher_synthetic_signal_v1(
        policy=_policy(), current_state=ready.current_state,
        synthetic_signal=_signal(signal_classification="SYNTHETIC_SIGINT"),
    )
    assert term.current_state.state_code == "SHUTDOWN_REQUESTED"
    assert interrupt.current_state.state_code == "SHUTDOWN_REQUESTED"
    assert term.failure_codes == ()
    hup = evaluate_passive_runtime_launcher_synthetic_signal_v1(
        policy=_policy(), current_state=ready.current_state,
        synthetic_signal=_signal(signal_classification="SYNTHETIC_SIGHUP"),
    )
    unknown = evaluate_passive_runtime_launcher_synthetic_signal_v1(
        policy=_policy(), current_state=ready.current_state,
        synthetic_signal=_signal(signal_classification="SYNTHETIC_UNKNOWN_SIGNAL"),
    )
    assert "RELOAD_NOT_AUTHORIZED" in hup.failure_codes
    assert "UNKNOWN_SYNTHETIC_SIGNAL" in unknown.failure_codes
    complete = request_passive_runtime_launcher_shutdown_v1(
        policy=_policy(), current_state=term.current_state, shutdown_request=_shutdown(),
    )
    repeated = request_passive_runtime_launcher_shutdown_v1(
        policy=_policy(), current_state=complete.current_state, shutdown_request=_shutdown(),
    )
    assert complete.current_state.state_code == "GRACEFUL_SHUTDOWN_COMPLETE"
    assert repeated.current_state == complete.current_state
    _assert_passive_authority(complete)


def test_invalid_transition_and_main_are_passive_and_side_effect_free() -> None:
    created = build_passive_runtime_launcher_v1(policy=_policy(), configuration=_configuration())
    invalid = request_passive_runtime_launcher_shutdown_v1(
        policy=_policy(), current_state=created, shutdown_request=_shutdown(),
    )
    assert invalid.current_state.state_code == "BLOCKED"
    assert invalid.failure_codes == ("INVALID_STATE_TRANSITION",)
    result = main(policy=_policy(), configuration=_configuration(), current_state=created)
    _frozen(result)
    assert result.current_state.state_code == "PASSIVE_READY"
    _assert_passive_authority(result)


def test_audit_evidence_is_redacted_immutable_and_aligned() -> None:
    created = build_passive_runtime_launcher_v1(policy=_policy(), configuration=_configuration())
    result = evaluate_passive_runtime_launcher_startup_v1(
        policy=_policy(), configuration=_configuration(), current_state=created,
    )
    evidence = build_passive_runtime_launcher_audit_evidence_v1(
        audit_id="passive-launcher-audit-v1", policy=_policy(), configuration=_configuration(),
        result=result, requested_transition="PASSIVE_STARTUP", synthetic_signal=None,
        shutdown_classification="NONE",
    )
    _frozen(evidence)
    assert evidence.audit_id == "passive-launcher-audit-v1"
    assert evidence.current_state == "PASSIVE_READY"
    assert evidence.failure_codes == ()
    _assert_passive_authority(evidence)


def test_failure_record_shape_and_state_vocabulary_are_frozen() -> None:
    assert tuple(item.name for item in fields(PassiveRuntimeLauncherFailureV1)) == (
        "failure_code", "safe_message", "retryable",
    )
    assert PassiveRuntimeLauncherStateV1.supported_state_codes == _STATES
