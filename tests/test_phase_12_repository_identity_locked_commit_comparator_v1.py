"""Static RED contract for the Phase 12 repository comparator.

The direct import intentionally keeps this contract red until the frozen module exists.
"""
from __future__ import annotations

import dataclasses
import inspect

import engine.phase_12_repository_identity_locked_commit_comparator_v1 as comparator


def _source() -> str:
    return inspect.getsource(comparator)


def _assert_source_contains(text: str) -> None:
    assert text in _source()


def _result_type() -> type[object]:
    return getattr(comparator, "_Phase12RepositoryIdentityLockedCommitComparatorResultV1")


def _function() -> object:
    return comparator.compare_phase_12_repository_identity_and_locked_commit_v1


def test_public_surface_01() -> None:
    assert comparator.__all__ == ("compare_phase_12_repository_identity_and_locked_commit_v1",)

def test_public_surface_02() -> None:
    signature = inspect.signature(_function())
    assert list(signature.parameters) == ["repository_path", "repository_identity", "accepted_locked_commit", "expected_origin_fetch_url", "expected_origin_push_url"]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values())

def test_public_surface_03() -> None:
    assert inspect.signature(_function()).return_annotation == "_Phase12RepositoryIdentityLockedCommitComparatorResultV1"

def test_public_surface_04() -> None:
    cls = _result_type()
    assert dataclasses.is_dataclass(cls)
    assert cls.__dataclass_params__.frozen is True

def test_public_surface_05() -> None:
    assert tuple(_result_type().__dataclass_fields__) == ("is_match", "failure_codes", "repository_identity", "repository_top_level", "head_commit", "branch_name", "origin_master_commit", "origin_head_target", "object_format", "is_clean")

def test_public_surface_06() -> None:
    assert "failure count" in _source()

def test_caller_grammar_01() -> None:
    _assert_source_contains('type(value) is str')

def test_caller_grammar_02() -> None:
    _assert_source_contains('[a-z0-9][a-z0-9-]{0,63}')

def test_caller_grammar_03() -> None:
    _assert_source_contains('[0-9a-f]{40}')

def test_caller_grammar_04() -> None:
    _assert_source_contains('TypeError()')

def test_caller_grammar_05() -> None:
    _assert_source_contains('expected_origin_fetch_url')

def test_caller_grammar_06() -> None:
    _assert_source_contains('expected_origin_push_url')

def test_caller_grammar_07() -> None:
    _assert_source_contains('repository_identity')

def test_caller_grammar_08() -> None:
    _assert_source_contains('accepted_locked_commit')

def test_caller_grammar_09() -> None:
    _assert_source_contains('PATH_TYPE_INVALID')

def test_caller_grammar_10() -> None:
    _assert_source_contains('repository_path')

def test_caller_grammar_11() -> None:
    _assert_source_contains('normalized absolute')

def test_caller_grammar_12() -> None:
    _assert_source_contains('keyword-only')

def test_path_grammar_01() -> None:
    _assert_source_contains('exactly one leading slash')

def test_path_grammar_02() -> None:
    _assert_source_contains('no NUL')

def test_path_grammar_03() -> None:
    _assert_source_contains('no empty interior')

def test_path_grammar_04() -> None:
    _assert_source_contains('no dot component')

def test_path_grammar_05() -> None:
    _assert_source_contains('no dot-dot component')

def test_path_grammar_06() -> None:
    _assert_source_contains('no trailing slash')

def test_path_grammar_07() -> None:
    _assert_source_contains('root path itself invalid')

def test_path_grammar_08() -> None:
    _assert_source_contains('normalized absolute')

def test_path_grammar_09() -> None:
    _assert_source_contains('PATH_TYPE_INVALID')

def test_path_filesystem_01() -> None:
    _assert_source_contains('os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW')

def test_path_filesystem_02() -> None:
    _assert_source_contains('parent symlink')

def test_path_filesystem_03() -> None:
    _assert_source_contains('repository root')

def test_path_filesystem_04() -> None:
    _assert_source_contains('UID 0')

def test_path_filesystem_05() -> None:
    _assert_source_contains('group-write')

def test_path_filesystem_06() -> None:
    _assert_source_contains('other-write')

def test_path_filesystem_07() -> None:
    _assert_source_contains('direct `.git`')

def test_path_filesystem_08() -> None:
    _assert_source_contains('not be symlinks')

def test_path_filesystem_09() -> None:
    _assert_source_contains('descriptors')

def test_path_filesystem_10() -> None:
    _assert_source_contains('Do not require st_nlink')

def test_topology_01() -> None:
    _assert_source_contains('ordinary non-bare')

def test_topology_02() -> None:
    _assert_source_contains('top-level')

def test_topology_03() -> None:
    _assert_source_contains('absolute Git directory')

def test_topology_04() -> None:
    _assert_source_contains('common Git directory')

def test_topology_05() -> None:
    _assert_source_contains('linked worktree')

def test_topology_06() -> None:
    _assert_source_contains('`.git` file')

def test_topology_07() -> None:
    _assert_source_contains('submodule-style gitfile')

def test_topology_08() -> None:
    _assert_source_contains('separate common directory')

def test_topology_09() -> None:
    _assert_source_contains('REPOSITORY_GIT_DIR_MISMATCH')

def test_runner_01() -> None:
    _assert_source_contains('/usr/bin/git')

def test_runner_02() -> None:
    _assert_source_contains('subprocess.Popen')

def test_runner_03() -> None:
    _assert_source_contains('shell=False')

def test_runner_04() -> None:
    _assert_source_contains('stdin=subprocess.DEVNULL')

def test_runner_05() -> None:
    _assert_source_contains('stdout=subprocess.PIPE')

def test_runner_06() -> None:
    _assert_source_contains('stderr=subprocess.PIPE')

def test_runner_07() -> None:
    _assert_source_contains('close_fds=True')

def test_runner_08() -> None:
    _assert_source_contains('start_new_session=True')

def test_environment_01() -> None:
    _assert_source_contains('PATH=/usr/bin:/bin')

def test_environment_02() -> None:
    _assert_source_contains('GIT_CONFIG_NOSYSTEM=1')

def test_environment_03() -> None:
    _assert_source_contains('GIT_ATTR_NOSYSTEM=1')

def test_environment_04() -> None:
    _assert_source_contains('GIT_OPTIONAL_LOCKS=0')

def test_environment_05() -> None:
    _assert_source_contains('GIT_TERMINAL_PROMPT=0')

def test_environment_06() -> None:
    _assert_source_contains('GIT_CONFIG_COUNT=0')

def test_environment_07() -> None:
    _assert_source_contains('GIT_NO_REPLACE_OBJECTS=1')

def test_commands_01() -> None:
    _assert_source_contains('The deterministic allowlist and output contracts are exactly:')

def test_commands_02() -> None:
    _assert_source_contains('git rev-parse --is-inside-work-tree')

def test_commands_03() -> None:
    _assert_source_contains('git rev-parse --show-object-format')

def test_commands_04() -> None:
    _assert_source_contains('git config --local --no-includes')

def test_commands_05() -> None:
    _assert_source_contains('git cat-file -t --end-of-options')

def test_commands_06() -> None:
    _assert_source_contains('git rev-parse --verify')

def test_commands_07() -> None:
    _assert_source_contains('git symbolic-ref --quiet')

def test_commands_08() -> None:
    _assert_source_contains('status --porcelain=v2 -z')

def test_output_bounds_01() -> None:
    _assert_source_contains('65536-byte caps')

def test_output_bounds_02() -> None:
    _assert_source_contains('strict UTF-8')

def test_output_bounds_03() -> None:
    _assert_source_contains('exact output grammars')

def test_output_bounds_04() -> None:
    _assert_source_contains('bounded-drain')

def test_output_bounds_05() -> None:
    _assert_source_contains('REPOSITORY_OUTPUT_TOO_LARGE')

def test_output_bounds_06() -> None:
    _assert_source_contains('REPOSITORY_OUTPUT_INVALID')

def test_timeouts_01() -> None:
    _assert_source_contains('5-second command deadline')

def test_timeouts_02() -> None:
    _assert_source_contains('60-second monotonic operation deadline')

def test_timeouts_03() -> None:
    _assert_source_contains('terminate process group')

def test_timeouts_04() -> None:
    _assert_source_contains('kill if needed')

def test_timeouts_05() -> None:
    _assert_source_contains('REPOSITORY_COMMAND_TIMEOUT')

def test_malformed_output_01() -> None:
    _assert_source_contains('malformed output')

def test_malformed_output_02() -> None:
    _assert_source_contains('invalid UTF-8')

def test_malformed_output_03() -> None:
    _assert_source_contains('unexpected nonzero exit')

def test_malformed_output_04() -> None:
    _assert_source_contains('exact output grammars')

def test_malformed_output_05() -> None:
    _assert_source_contains('duplicate')

def test_malformed_output_06() -> None:
    _assert_source_contains('empty output')

def test_malformed_output_07() -> None:
    _assert_source_contains('REPOSITORY_OUTPUT_INVALID')

def test_object_format_01() -> None:
    _assert_source_contains('SHA-1 only')

def test_object_format_02() -> None:
    _assert_source_contains('sha1')

def test_object_format_03() -> None:
    _assert_source_contains('SHA-256')

def test_object_format_04() -> None:
    _assert_source_contains('REPOSITORY_OBJECT_FORMAT_UNSUPPORTED')

def test_accepted_object_01() -> None:
    _assert_source_contains('[0-9a-f]{40}')

def test_accepted_object_02() -> None:
    _assert_source_contains('type `commit`')

def test_accepted_object_03() -> None:
    _assert_source_contains('exactly resolve')

def test_accepted_object_04() -> None:
    _assert_source_contains('No abbreviation')

def test_accepted_object_05() -> None:
    _assert_source_contains('ancestor semantics')

def test_branch_01() -> None:
    _assert_source_contains('refs/heads/master')

def test_branch_02() -> None:
    _assert_source_contains('detached HEAD')

def test_branch_03() -> None:
    _assert_source_contains('REPOSITORY_DETACHED_HEAD')

def test_branch_04() -> None:
    _assert_source_contains('REPOSITORY_BRANCH_MISMATCH')

def test_branch_05() -> None:
    _assert_source_contains('symbolically')

def test_origin_urls_01() -> None:
    _assert_source_contains('remote.origin.url')

def test_origin_urls_02() -> None:
    _assert_source_contains('remote.origin.pushurl')

def test_origin_urls_03() -> None:
    _assert_source_contains('exactly one explicit')

def test_origin_urls_04() -> None:
    _assert_source_contains('fallback')

def test_origin_urls_05() -> None:
    _assert_source_contains('REPOSITORY_REMOTE_URL_MISMATCH')

def test_origin_refs_01() -> None:
    _assert_source_contains('refs/remotes/origin/master')

def test_origin_refs_02() -> None:
    _assert_source_contains('refs/remotes/origin/HEAD')

def test_origin_refs_03() -> None:
    _assert_source_contains('remote freshness')

def test_origin_refs_04() -> None:
    _assert_source_contains('REPOSITORY_ORIGIN_MASTER_MISMATCH')

def test_origin_refs_05() -> None:
    _assert_source_contains('REPOSITORY_ORIGIN_HEAD_MISMATCH')

def test_cleanliness_01() -> None:
    _assert_source_contains('status --porcelain=v2 -z')

def test_cleanliness_02() -> None:
    _assert_source_contains('empty stdout')

def test_cleanliness_03() -> None:
    _assert_source_contains('REPOSITORY_DIRTY')

def test_cleanliness_04() -> None:
    _assert_source_contains('untracked')

def test_cleanliness_05() -> None:
    _assert_source_contains('unmerged')

def test_cleanliness_06() -> None:
    _assert_source_contains('submodule')

def test_cleanliness_07() -> None:
    _assert_source_contains('Ignored files')

def test_index_sparse_01() -> None:
    _assert_source_contains('assume-unchanged')

def test_index_sparse_02() -> None:
    _assert_source_contains('skip-worktree')

def test_index_sparse_03() -> None:
    _assert_source_contains('intent-to-add')

def test_index_sparse_04() -> None:
    _assert_source_contains('sparse')

def test_index_sparse_05() -> None:
    _assert_source_contains('REPOSITORY_INDEX_FLAG_REJECTED')

def test_submodules_01() -> None:
    _assert_source_contains('mode `160000`')

def test_submodules_02() -> None:
    _assert_source_contains('registered submodules')

def test_submodules_03() -> None:
    _assert_source_contains('`.gitmodules`')

def test_submodules_04() -> None:
    _assert_source_contains('REPOSITORY_SUBMODULE_REJECTED')

def test_shallow_01() -> None:
    _assert_source_contains('is-shallow-repository')

def test_shallow_02() -> None:
    _assert_source_contains('false')

def test_shallow_03() -> None:
    _assert_source_contains('REPOSITORY_SHALLOW_REJECTED')

def test_replace_refs_01() -> None:
    _assert_source_contains('GIT_NO_REPLACE_OBJECTS=1')

def test_replace_refs_02() -> None:
    _assert_source_contains('refs/replace/')

def test_replace_refs_03() -> None:
    _assert_source_contains('REPOSITORY_REPLACE_REFS_PRESENT')

def test_replace_refs_04() -> None:
    _assert_source_contains('for-each-ref')

def test_alternates_01() -> None:
    _assert_source_contains('objects/info/alternates')

def test_alternates_02() -> None:
    _assert_source_contains('REPOSITORY_ALTERNATES_REJECTED')

def test_alternates_03() -> None:
    _assert_source_contains('alternate')

def test_alternates_04() -> None:
    _assert_source_contains('Descriptor-relative')

def test_promisor_01() -> None:
    _assert_source_contains('extensions.partialClone')

def test_promisor_02() -> None:
    _assert_source_contains('promisor')

def test_promisor_03() -> None:
    _assert_source_contains('partialclonefilter')

def test_promisor_04() -> None:
    _assert_source_contains('lazy fetch')

def test_promisor_05() -> None:
    _assert_source_contains('REPOSITORY_PROMISOR_REJECTED')

def test_filesystem_drift_01() -> None:
    _assert_source_contains('st_dev')

def test_filesystem_drift_02() -> None:
    _assert_source_contains('st_ino')

def test_filesystem_drift_03() -> None:
    _assert_source_contains('st_mode')

def test_filesystem_drift_04() -> None:
    _assert_source_contains('REPOSITORY_CHANGED_DURING_OPERATION')

def test_exception_propagation_01() -> None:
    _assert_source_contains('Unknown ordinary Python exceptions')

def test_exception_propagation_02() -> None:
    _assert_source_contains('BaseException')

def test_exception_propagation_03() -> None:
    _assert_source_contains('broad `Exception` catching is forbidden')

def test_exception_propagation_04() -> None:
    _assert_source_contains('expected process/filesystem/Git')

def test_prohibited_effects_01() -> None:
    _assert_source_contains('Git/index mutation')

def test_prohibited_effects_02() -> None:
    _assert_source_contains('fetch/pull/push')

def test_prohibited_effects_03() -> None:
    _assert_source_contains('hooks')

def test_prohibited_effects_04() -> None:
    _assert_source_contains('network')

def test_prohibited_effects_05() -> None:
    _assert_source_contains('marker/key/revocation/replay access')

def test_prohibited_effects_06() -> None:
    _assert_source_contains('policy/wiring/activation')

def test_prohibited_effects_07() -> None:
    _assert_source_contains('authorization claims')

def test_trust_boundary_01() -> None:
    _assert_source_contains('local facts at observation time only')

def test_trust_boundary_02() -> None:
    _assert_source_contains('does not prove freshness')

def test_trust_boundary_03() -> None:
    _assert_source_contains('does not prove hosting identity')

def test_trust_boundary_04() -> None:
    _assert_source_contains('does not prove source trust')

def test_trust_boundary_05() -> None:
    _assert_source_contains('does not prove authorization')
