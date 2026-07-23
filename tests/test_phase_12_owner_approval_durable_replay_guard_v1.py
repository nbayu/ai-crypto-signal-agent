"""Static RED contract for the Phase 12 owner approval durable replay guard.

The production module is deliberately imported directly and must remain absent in this RED step.
"""
from __future__ import annotations

import inspect
import multiprocessing
from dataclasses import is_dataclass

import pytest

import engine.phase_12_owner_approval_durable_replay_guard_v1 as guard


def _call(**overrides: object) -> object:
    values: dict[str, object] = {
        "path": "/tmp/phase12-red-replay-store.db",
        "replay_identity": "0" * 64,
        "expected_schema_identifier": "PHASE12-OWNER-APPROVAL-REPLAY-STORE-V1",
        "expected_deployment_identifier": "phase12-replay-deployment-" + "0" * 16,
    }
    values.update(overrides)
    return guard.check_and_record_phase_12_owner_approval_replay_v1(**values)


def _failure(result: object, code: str) -> bool:
    return (
        result.is_recorded is False
        and result.was_already_consumed is False
        and result.failure_codes == (code,)
        and result.replay_identity is None
        and result.schema_identifier is None
        and result.deployment_identifier is None
    )


def _source() -> str:
    return inspect.getsource(guard)


def _contains(token: str) -> bool:
    return token in _source()


def _ordered(first: str, second: str) -> bool:
    source = _source()
    return source.index(first) < source.index(second)


def test_public_01() -> None:
    assert guard.__all__ == ("check_and_record_phase_12_owner_approval_replay_v1",)

def test_public_02() -> None:
    signature = inspect.signature(guard.check_and_record_phase_12_owner_approval_replay_v1)
    assert tuple(signature.parameters) == ("path", "replay_identity", "expected_schema_identifier", "expected_deployment_identifier")
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values())

def test_public_03() -> None:
    assert is_dataclass(guard._Phase12OwnerApprovalDurableReplayGuardResultV1)

def test_public_04() -> None:
    assert hasattr(guard._Phase12OwnerApprovalDurableReplayGuardResultV1, "__slots__")

def test_public_05() -> None:
    assert _contains("kw_only=True")

def test_public_06() -> None:
    result = guard._Phase12OwnerApprovalDurableReplayGuardResultV1(is_recorded=False, was_already_consumed=False, failure_codes=(), replay_identity=None, schema_identifier=None, deployment_identifier=None)
    assert "failure_count" in repr(result)

def test_caller_01() -> None:
    with pytest.raises(TypeError) as caught: _call(path=1)
    assert str(caught.value) == ""

def test_caller_02() -> None:
    with pytest.raises(TypeError) as caught: _call(replay_identity=1)
    assert str(caught.value) == ""

def test_caller_03() -> None:
    with pytest.raises(TypeError) as caught: _call(expected_schema_identifier=1)
    assert str(caught.value) == ""

def test_caller_04() -> None:
    with pytest.raises(TypeError) as caught: _call(expected_deployment_identifier=1)
    assert str(caught.value) == ""

def test_caller_05() -> None:
    with pytest.raises(TypeError): _call(replay_identity="A" * 64)

def test_caller_06() -> None:
    with pytest.raises(TypeError): _call(replay_identity="0" * 63)

def test_caller_07() -> None:
    with pytest.raises(TypeError): _call(expected_schema_identifier="OTHER")

def test_caller_08() -> None:
    with pytest.raises(TypeError): _call(expected_deployment_identifier="phase12-replay-deployment-" + "A" * 16)

def test_caller_09() -> None:
    assert _contains("phase12-replay-deployment-")

def test_caller_10() -> None:
    assert _contains("[0-9a-f]{64}")

def test_path_01() -> None:
    assert _failure(_call(path=""), "PATH_TYPE_INVALID")

def test_path_02() -> None:
    assert _failure(_call(path="/"), "PATH_TYPE_INVALID")

def test_path_03() -> None:
    assert _failure(_call(path="relative/store.db"), "PATH_TYPE_INVALID")

def test_path_04() -> None:
    assert _failure(_call(path="//double/store.db"), "PATH_TYPE_INVALID")

def test_path_05() -> None:
    assert _failure(_call(path="/tmp/\x00store.db"), "PATH_TYPE_INVALID")

def test_path_06() -> None:
    assert _failure(_call(path="/tmp//store.db"), "PATH_TYPE_INVALID")

def test_path_07() -> None:
    assert _failure(_call(path="/tmp/./store.db"), "PATH_TYPE_INVALID")

def test_path_08() -> None:
    assert _failure(_call(path="/tmp/store.db/"), "PATH_TYPE_INVALID")

def test_parent_01() -> None:
    assert _contains("os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW")

def test_parent_02() -> None:
    assert _contains("0o700")

def test_parent_03() -> None:
    assert _contains("stat.S_ISDIR")

def test_parent_04() -> None:
    assert _contains("st_uid")

def test_parent_05() -> None:
    assert _contains("REPLAY_STORE_PARENT_DIRECTORY_MISMATCH")

def test_parent_06() -> None:
    assert _contains("REPLAY_STORE_SYMLINK_REJECTED")

def test_parent_07() -> None:
    assert _contains("dir_fd=")

def test_parent_08() -> None:
    assert _contains("os.close")

def test_parent_09() -> None:
    assert _contains("REPLAY_STORE_OWNER_MISMATCH")

def test_leaf_01() -> None:
    assert _contains("os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK")

def test_leaf_02() -> None:
    assert _contains("stat.S_ISREG")

def test_leaf_03() -> None:
    assert _contains("0o600")

def test_leaf_04() -> None:
    assert _contains("st_nlink")

def test_leaf_05() -> None:
    assert _contains("REPLAY_STORE_NOT_REGULAR_FILE")

def test_leaf_06() -> None:
    assert _contains("REPLAY_STORE_MODE_MISMATCH")

def test_leaf_07() -> None:
    assert _contains("REPLAY_STORE_HARD_LINK_REJECTED")

def test_leaf_08() -> None:
    assert _contains("REPLAY_STORE_CHANGED_DURING_OPERATION")

def test_open_01() -> None:
    assert _contains("?mode=rw")

def test_open_02() -> None:
    assert _contains("uri=True")

def test_open_03() -> None:
    assert _contains("timeout=5.0")

def test_open_04() -> None:
    assert _contains("isolation_level=None")

def test_pragma_01() -> None:
    assert _ordered("foreign_keys=ON", "journal_mode=DELETE")

def test_pragma_02() -> None:
    assert _ordered("journal_mode=DELETE", "synchronous=FULL")

def test_pragma_03() -> None:
    assert _ordered("synchronous=FULL", "temp_store=MEMORY")

def test_pragma_04() -> None:
    assert _ordered("temp_store=MEMORY", "trusted_schema=OFF")

def test_pragma_05() -> None:
    assert _ordered("trusted_schema=OFF", "busy_timeout=5000")

def test_pragma_06() -> None:
    assert _contains("page_size") and _contains("4096")

def test_pragma_07() -> None:
    assert _contains("max_page_count") and _contains("262144")

def test_schema_01() -> None:
    assert _contains("phase_12_owner_approval_replay_metadata_v1")

def test_schema_02() -> None:
    assert _contains("phase_12_owner_approval_replay_consumed_v1")

def test_schema_03() -> None:
    assert _contains("WITHOUT ROWID")

def test_schema_04() -> None:
    assert _contains("singleton INTEGER")

def test_schema_05() -> None:
    assert _contains("replay_identity TEXT")

def test_schema_06() -> None:
    assert _contains("sqlite_schema")

def test_schema_07() -> None:
    assert _contains("PRAGMA index_list")

def test_schema_08() -> None:
    assert _contains("fetchmany")

def test_schema_09() -> None:
    assert _contains("REPLAY_STORE_UNSUPPORTED_OBJECT")

def test_metadata_01() -> None:
    assert _contains("metadata")

def test_metadata_02() -> None:
    assert _contains("PHASE12-OWNER-APPROVAL-REPLAY-STORE-V1")

def test_metadata_03() -> None:
    assert _contains("REPLAY_STORE_SCHEMA_MISMATCH")

def test_metadata_04() -> None:
    assert _contains("REPLAY_STORE_DEPLOYMENT_MISMATCH")

def test_metadata_05() -> None:
    assert _contains("deployment_identifier")

def test_integrity_01() -> None:
    assert _contains("quick_check(1)")

def test_integrity_02() -> None:
    assert _contains("REPLAY_STORE_CORRUPT")

def test_integrity_03() -> None:
    assert _contains("REPLAY_STORE_PAGE_POLICY_MISMATCH")

def test_integrity_04() -> None:
    assert _contains("REPLAY_STORE_CONNECTION_POLICY_MISMATCH")

def test_integrity_05() -> None:
    assert _contains("trusted_schema")

def test_first_use_01() -> None:
    assert _ordered("BEGIN IMMEDIATE", "INSERT")

def test_first_use_02() -> None:
    assert _ordered("INSERT", "COMMIT")

def test_first_use_03() -> None:
    assert _contains("is_recorded=True")

def test_first_use_04() -> None:
    assert _contains("failure_codes=()")

def test_first_use_05() -> None:
    assert _contains("REPLAY_RECORD_FAILED")

def test_consumed_01() -> None:
    assert _contains("REPLAY_IDENTITY_ALREADY_CONSUMED")

def test_consumed_02() -> None:
    assert _ordered("SELECT", "ROLLBACK")

def test_consumed_03() -> None:
    assert _contains("was_already_consumed=True")

def test_consumed_04() -> None:
    assert _contains("already")

def test_capacity_01() -> None:
    assert _contains("1000000")

def test_capacity_02() -> None:
    assert _contains("262144")

def test_capacity_03() -> None:
    assert _contains("COUNT(*)")

def test_capacity_04() -> None:
    assert _contains("REPLAY_STORE_CAPACITY_EXCEEDED")

def test_concurrency_01() -> None:
    context = multiprocessing.get_context("fork")
    assert context.get_start_method() == "fork"
    assert _contains("BEGIN IMMEDIATE")

def test_concurrency_02() -> None:
    assert _contains("PRIMARY KEY")

def test_concurrency_03() -> None:
    assert _contains("check_same_thread=True")

def test_concurrency_04() -> None:
    assert _contains("REPLAY_IDENTITY_ALREADY_CONSUMED")

def test_busy_01() -> None:
    assert _contains("5000")

def test_busy_02() -> None:
    assert _contains("REPLAY_STORE_BUSY")

def test_busy_03() -> None:
    assert "sleep(" not in _source()

def test_ambiguity_01() -> None:
    assert _contains("REPLAY_DURABILITY_NOT_CONFIRMED")

def test_ambiguity_02() -> None:
    assert _contains("COMMIT")

def test_ambiguity_03() -> None:
    assert _contains("close")

def test_ambiguity_04() -> None:
    assert _contains("ambiguous") or _contains("may have persisted")

def test_drift_01() -> None:
    assert _contains("st_dev") and _contains("st_ino")

def test_drift_02() -> None:
    assert _contains("st_mode") and _contains("st_nlink")

def test_drift_03() -> None:
    assert _contains("REPLAY_STORE_CHANGED_DURING_OPERATION")

def test_result_01() -> None:
    assert _contains("frozen=True")

def test_result_02() -> None:
    assert _contains("slots=True")

def test_result_03() -> None:
    assert _contains("replay_identity: str | None")

def test_exceptions_01() -> None:
    assert _contains("sqlite_errorcode") or _contains("sqlite_errorname")

def test_exceptions_02() -> None:
    assert _contains("sqlite3.OperationalError")

def test_exceptions_03() -> None:
    assert _contains("BaseException")

def test_purity_01() -> None:
    assert "subprocess" not in _source()

def test_purity_02() -> None:
    assert "requests" not in _source() and "urllib.request" not in _source()

def test_purity_03() -> None:
    assert "systemctl" not in _source() and "telegram" not in _source().lower()

def test_purity_04() -> None:
    assert "phase_12_activation_owner_approval_signature_verifier_v1" not in _source()
