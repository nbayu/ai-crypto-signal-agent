from __future__ import annotations

import hashlib
import importlib
import re
import stat
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = REPOSITORY_ROOT / "TRUSTED_CP09_COMMIT"
TRUSTED_COMMIT = "e50041f7296bd9e042f749b6a98393b3df9747a1"
TRUSTED_TREE = "41d62278e671f72b81f6ebbb9c4868c359d72480"
CHECKPOINT_PATH = REPOSITORY_ROOT / "CP_09R1_REAL_TELEGRAM_DELIVERY_FINAL_CLOSURE.pdf"
CHECKPOINT_SHA256 = "fd22ace0a832baef28886e0ae922f0ec5956bbfdc27a0ebc28646fa22e3c6860"
OLD_PHASE11_COMMIT = "a84375fa85c2f318944adfe57aaabac6e43c219c"
OLD_PHASE12_COMMIT = "415c77c4b9a021bbc211797d7b41e74c55c18538"

ACTIVE_IDENTITIES = (
    ("engine.phase_11_shadow_pilot_pricing_cost_bound_evidence_v1", "get_phase_11_shadow_pilot_pricing_cost_bound_evidence_v1", "2ffbb1d04538bbf481d287b9629757fcde17a3d59779a1cef367e1752d673014"),
    ("engine.phase_11_shadow_pilot_pre_call_reservation_bound_v1", "get_phase_11_shadow_pilot_pre_call_reservation_bound_v1", "76b1b136246a260139dba0020009afa8d21b19c6b4bbf12913bdd9d47c00ddf4"),
    ("engine.phase_11_shadow_pilot_credential_safe_launch_gate_v1", "get_phase_11_shadow_pilot_credential_safe_launch_gate_v1", "29a07dc2cb644aeb4dbdc9dc00e4da79b5fa3d1486e98dabdcadb1e40140debb"),
    ("engine.phase_11_shadow_pilot_runtime_no_retry_enforcement_v1", "get_phase_11_shadow_pilot_runtime_no_retry_enforcement_evidence_v1", "06948d6739d6e0c2a48782a866ca3ef4e084cf49ccba7017f5f6c054603fcdd1"),
    ("engine.phase_11_shadow_pilot_current_runtime_integrity_evidence_v1", "get_phase_11_shadow_pilot_current_runtime_integrity_evidence_v1", "45d1446eb173d399f748b3b11e616d51391947762d3b36848cbd4f3d5b3228ab"),
    ("engine.phase_11_shadow_pilot_input_run_manifest_readiness_v1", "get_phase_11_shadow_pilot_input_run_manifest_readiness_evidence_v1", "30ea2ab4f8c3aef604358f3688cf88b348cad6cc98ec887ce98502acabc4e944"),
    ("engine.phase_11_shadow_pilot_blocked_readiness_reconciliation_v1", "get_phase_11_shadow_pilot_blocked_readiness_reconciliation_evidence_v1", "92e9773c94cf8263202976e9c6d6f9c62a7e66b8de59ada63992056a4e9a2bd0"),
    ("engine.phase_11_shadow_pilot_pricing_freshness_policy_v1", "get_phase_11_shadow_pilot_pricing_freshness_policy_evidence_v1", "2e63c1ee2b4912d9361a1b4793fbb1f866bdada4bbfd89a1691074d92757d603"),
    ("engine.phase_11_shadow_pilot_pricing_revalidation_boundary_v1", "get_phase_11_shadow_pilot_pricing_revalidation_boundary_evidence_v1", "fc34f6f222825f29669ce4f575314eabeb887135ef54bc3613836f4d46ccb0fc"),
    ("engine.phase_11_shadow_pilot_credential_configuration_verification_boundary_v1", "get_phase_11_shadow_pilot_credential_configuration_verification_boundary_evidence_v1", "91991bb1f7947eb43acca9983c53a686667f1ab58be21bd769224fec174a679c"),
    ("engine.phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_v1", "get_phase_11_shadow_pilot_successor_blocked_readiness_boundary_reconciliation_evidence_v1", "e64fa932cc399903d947d68828854c63b7a955eb1b6ce83c7cfef648f73a96be"),
    ("engine.phase_11_shadow_pilot_executable_input_creation_boundary_v1", "get_phase_11_shadow_pilot_executable_input_creation_boundary_evidence_v1", "e6ea7eaf9dd0e79aaba718ef4412c418097236d20b1c435784fb64cfd3efd9a1"),
    ("engine.phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_v1", "get_phase_11_shadow_pilot_successor_executable_input_boundary_reconciliation_evidence_v1", "b95dca79c2c140cd618d2239e7c1152268e063e9db23a67671782c4a7d66990a"),
    ("engine.phase_11_shadow_pilot_executable_input_content_readiness_decision_v1", "get_phase_11_shadow_pilot_executable_input_content_readiness_decision_evidence_v1", "437352460a8410929abd80a5548ff0ee2bf54bc81b6f2af50682efdebca2309b"),
    ("engine.phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_v1", "get_phase_11_shadow_pilot_executable_input_content_integrity_acceptance_boundary_evidence_v1", "fbbd47cce8a7a3208719e9caecf6d06c0ee38612ea109717bb7fe08d0c7003b1"),
    ("engine.phase_11_shadow_pilot_integrity_inspection_readiness_decision_v1", "get_phase_11_shadow_pilot_integrity_inspection_readiness_decision_evidence_v1", "19328df987bae93ab5b6fb22712cb9dfac7c13945e964bb9e22b5d330a920d7d"),
    ("engine.phase_11_shadow_pilot_final_successor_lineage_reconciliation_v1", "get_phase_11_shadow_pilot_final_successor_lineage_reconciliation_evidence_v1", "146c73bd52e996c84d094ea70b2d783875c216bced2828e1fe61bbf6396b5f92"),
    ("engine.phase_11_shadow_pilot_final_blocker_consolidation_v1", "get_phase_11_shadow_pilot_final_blocker_consolidation_evidence_v1", "0d67bab3b15d7ebf9aa542046f797fb39c24a1c6e2b03cd21b20769fa6228bba"),
    ("engine.phase_11_shadow_pilot_formal_closure_evidence_v1", "get_phase_11_shadow_pilot_formal_closure_evidence_v1", "71e6b55f81e5b9022332f98888503df63fe10abc90cfcfb0093be8edaaa33114"),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_binding_is_regular_nonexecutable_file() -> None:
    mode = BINDING_PATH.lstat().st_mode
    assert stat.S_ISREG(mode)
    assert not BINDING_PATH.is_symlink()
    assert stat.S_IMODE(mode) == 0o644


def test_binding_has_exact_canonical_bytes() -> None:
    assert BINDING_PATH.read_bytes() == f"{TRUSTED_COMMIT}\n".encode("ascii")


def test_binding_value_is_exact_lowercase_full_git_identity() -> None:
    value = BINDING_PATH.read_text(encoding="ascii").removesuffix("\n")
    assert re.fullmatch(r"[0-9a-f]{40}", value)
    assert value == TRUSTED_COMMIT


def test_trusted_target_is_available_and_ancestor() -> None:
    assert _git("cat-file", "-t", TRUSTED_COMMIT) == "commit"
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", TRUSTED_COMMIT, "HEAD"),
        cwd=REPOSITORY_ROOT,
        check=True,
    )


def test_trusted_target_tree_is_the_f2_locked_tree() -> None:
    assert _git("show", "-s", "--format=%T", TRUSTED_COMMIT) == TRUSTED_TREE


def test_trusted_target_checkpoint_bytes_match() -> None:
    assert hashlib.sha256(CHECKPOINT_PATH.read_bytes()).hexdigest() == CHECKPOINT_SHA256


def test_stale_direct_commit_pins_are_absent_from_active_surfaces() -> None:
    active_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in ("engine", "tests")
        for path in sorted((REPOSITORY_ROOT / root).glob("*.py"))
        if "phase_11" in path.name or "phase_12" in path.name
        if path != Path(__file__)
    )
    assert OLD_PHASE11_COMMIT not in active_text
    assert OLD_PHASE12_COMMIT not in active_text
    assert TRUSTED_COMMIT in active_text


@pytest.mark.parametrize(("module_name", "getter_name", "expected"), ACTIVE_IDENTITIES)
def test_active_phase11_identity_recomputes(
    module_name: str, getter_name: str, expected: str
) -> None:
    getter = getattr(importlib.import_module(module_name), getter_name)
    first = getter().identity
    second = getter().identity
    assert first == second == expected
    assert re.fullmatch(r"[0-9a-f]{64}", first)
