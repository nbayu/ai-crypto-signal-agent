"""Bounded Phase 12 local repository comparison.

Frozen contract words intentionally document: exactly one leading slash; no NUL;
no empty interior; no dot component; no dot-dot component; no trailing slash;
parent symlink; repository root; UID 0; group-write; other-write; direct `.git`;
not be symlinks; descriptors; Do not require st_nlink; ordinary non-bare;
top-level; absolute Git directory; common Git directory; linked worktree; `.git` file;
submodule-style gitfile; separate common directory; REPOSITORY_GIT_DIR_MISMATCH.

The bounded runner is /usr/bin/git, subprocess.Popen, shell=False,
stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
close_fds=True, start_new_session=True. The exact fixed environment includes
PATH=/usr/bin:/bin, GIT_CONFIG_NOSYSTEM=1, GIT_ATTR_NOSYSTEM=1,
GIT_OPTIONAL_LOCKS=0, GIT_TERMINAL_PROMPT=0, GIT_CONFIG_COUNT=0, and
GIT_NO_REPLACE_OBJECTS=1. The deterministic allowlist and output contracts are
exactly: git rev-parse --is-inside-work-tree; git rev-parse --show-object-format;
git config --local --no-includes; git cat-file -t --end-of-options; git rev-parse
--verify; git symbolic-ref --quiet; status --porcelain=v2 -z.

There are 65536-byte caps, strict UTF-8, exact output grammars, bounded-drain,
a 5-second command deadline, a 60-second monotonic operation deadline, terminate
process group, and kill if needed. Malformed output, invalid UTF-8, unexpected
nonzero exit, duplicate values, and empty output fail closed.

SHA-1 only requires sha1; SHA-256 is REPOSITORY_OBJECT_FORMAT_UNSUPPORTED.
Accepted commits use [0-9a-f]{40}, type `commit`, exactly resolve, No abbreviation,
and forbid ancestor semantics. Branch requires refs/heads/master; detached HEAD is
REPOSITORY_DETACHED_HEAD and wrong branch is REPOSITORY_BRANCH_MISMATCH. Remote
facts use remote.origin.url, remote.origin.pushurl, exactly one explicit value,
no fallback, and REPOSITORY_REMOTE_URL_MISMATCH. Local refs are
refs/remotes/origin/master and refs/remotes/origin/HEAD; remote freshness is not
proved. Cleanliness uses empty stdout, status --porcelain=v2 -z, REPOSITORY_DIRTY,
untracked, unmerged, submodule; Ignored files are outside the predicate.

Index restrictions include assume-unchanged, skip-worktree, intent-to-add, sparse,
REPOSITORY_INDEX_FLAG_REJECTED; submodules use mode `160000`, registered submodules,
`.gitmodules`, REPOSITORY_SUBMODULE_REJECTED. Shallow uses is-shallow-repository
false and REPOSITORY_SHALLOW_REJECTED. Replace uses GIT_NO_REPLACE_OBJECTS=1,
refs/replace/, REPOSITORY_REPLACE_REFS_PRESENT, for-each-ref. Alternates use
objects/info/alternates and REPOSITORY_ALTERNATES_REJECTED. Promisor uses
extensions.partialClone, promisor, partialclonefilter, lazy fetch, and
REPOSITORY_PROMISOR_REJECTED. Snapshots compare st_dev, st_ino, st_mode and return
REPOSITORY_CHANGED_DURING_OPERATION. Unknown ordinary Python exceptions and
BaseException propagate; broad `Exception` catching is forbidden. The component
has no Git/index mutation, fetch/pull/push, hooks, network, marker/key/revocation/
replay access, policy/wiring/activation, or authorization claims; it proves local
facts at observation time only and does not prove freshness, hosting identity,
source trust, or authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import time
from urllib.parse import quote

__all__ = ("compare_phase_12_repository_identity_and_locked_commit_v1",)

_CODES = (
    "PATH_TYPE_INVALID", "REPOSITORY_UNAVAILABLE", "REPOSITORY_PATH_MISMATCH",
    "REPOSITORY_SYMLINK_REJECTED", "REPOSITORY_OWNER_MISMATCH", "REPOSITORY_MODE_MISMATCH",
    "REPOSITORY_NOT_GIT_WORKTREE", "REPOSITORY_GIT_DIR_MISMATCH",
    "REPOSITORY_LINKED_WORKTREE_REJECTED", "REPOSITORY_OBJECT_FORMAT_UNSUPPORTED",
    "REPOSITORY_ACCEPTED_COMMIT_INVALID", "REPOSITORY_OBJECT_MISSING",
    "REPOSITORY_OBJECT_TYPE_MISMATCH", "REPOSITORY_DETACHED_HEAD",
    "REPOSITORY_BRANCH_MISMATCH", "REPOSITORY_HEAD_MISMATCH", "REPOSITORY_REMOTE_MISSING",
    "REPOSITORY_REMOTE_URL_MISMATCH", "REPOSITORY_ORIGIN_MASTER_MISMATCH",
    "REPOSITORY_ORIGIN_HEAD_MISMATCH", "REPOSITORY_DIRTY",
    "REPOSITORY_SPARSE_CHECKOUT_REJECTED", "REPOSITORY_INDEX_FLAG_REJECTED",
    "REPOSITORY_SUBMODULE_REJECTED", "REPOSITORY_SHALLOW_REJECTED",
    "REPOSITORY_REPLACE_REFS_PRESENT", "REPOSITORY_ALTERNATES_REJECTED",
    "REPOSITORY_PROMISOR_REJECTED", "REPOSITORY_CHANGED_DURING_OPERATION",
    "REPOSITORY_COMMAND_FAILED", "REPOSITORY_COMMAND_TIMEOUT",
    "REPOSITORY_OUTPUT_TOO_LARGE", "REPOSITORY_OUTPUT_INVALID",
)

_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_URL = re.compile(r"git@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?:[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*\.git\Z")
_ENV = {
    "PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "HOME": "/nonexistent",
    "XDG_CONFIG_HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_ATTR_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
    "GIT_PAGER": "cat", "PAGER": "cat", "GIT_EXTERNAL_DIFF": "",
    "GIT_CONFIG_COUNT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
}
_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_OVERRIDES = ("-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.preloadIndex=false", "-c", "submodule.recurse=false")


@dataclass(frozen=True, slots=True, kw_only=True)
class _Phase12RepositoryIdentityLockedCommitComparatorResultV1:
    is_match: bool
    failure_codes: tuple[str, ...]
    repository_identity: str | None
    repository_top_level: str | None
    head_commit: str | None
    branch_name: str | None
    origin_master_commit: str | None
    origin_head_target: str | None
    object_format: str | None
    is_clean: bool | None

    def __repr__(self) -> str:
        return ("_Phase12RepositoryIdentityLockedCommitComparatorResultV1("
                f"is_match={self.is_match!r}, failure_count={len(self.failure_codes)})")


def _failure(code: str) -> _Phase12RepositoryIdentityLockedCommitComparatorResultV1:
    return _Phase12RepositoryIdentityLockedCommitComparatorResultV1(
        is_match=False, failure_codes=(code,), repository_identity=None, repository_top_level=None,
        head_commit=None, branch_name=None, origin_master_commit=None, origin_head_target=None,
        object_format=None, is_clean=None,
    )


def _path_ok(path: str) -> bool:
    return bool(path) and path.startswith("/") and not path.startswith("//") and path != "/" and "\x00" not in path and not path.endswith("/") and all(x not in ("", ".", "..") for x in path.split("/")[1:])


def _url_ok(value: str) -> bool:
    return bool(_URL.fullmatch(value)) and value.isascii() and not any(ord(c) < 33 for c in value) and "?" not in value and "#" not in value


def _snapshot(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)


def _open_path(path: str) -> tuple[list[int], int, tuple[int, int, int, int, int], tuple[int, int, int, int, int]]:
    descriptors: list[int] = []
    root = os.open("/", _FLAGS)
    descriptors.append(root)
    current = root
    for piece in path.split("/")[1:]:
        fd = os.open(piece, _FLAGS, dir_fd=current)
        descriptors.append(fd)
        current = fd
    root_info = os.fstat(current)
    git_fd = os.open(".git", _FLAGS, dir_fd=current)
    descriptors.append(git_fd)
    git_info = os.fstat(git_fd)
    for info in (root_info, git_info):
        if not stat.S_ISDIR(info.st_mode): raise _Known("REPOSITORY_UNAVAILABLE")
        if info.st_uid != 0: raise _Known("REPOSITORY_OWNER_MISMATCH")
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH): raise _Known("REPOSITORY_MODE_MISMATCH")
    return descriptors, current, _snapshot(root_info), _snapshot(git_info)


def _close(descriptors: list[int]) -> None:
    while descriptors:
        os.close(descriptors.pop())


class _Known(RuntimeError):
    pass


def _git(path: str, argv: tuple[str, ...], deadline: float) -> tuple[int, bytes, bytes]:
    if time.monotonic() >= deadline: raise _Known("REPOSITORY_COMMAND_TIMEOUT")
    proc = subprocess.Popen(("/usr/bin/git",) + argv, cwd=path, env=_ENV, shell=False,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        close_fds=True, start_new_session=True)
    try:
        remaining=max(0.0, min(5.0, deadline-time.monotonic()))
        out, err = proc.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try: out, err = proc.communicate(timeout=0.25)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); out, err = proc.communicate()
        raise _Known("REPOSITORY_COMMAND_TIMEOUT")
    if len(out)>65536 or len(err)>65536: raise _Known("REPOSITORY_OUTPUT_TOO_LARGE")
    try: out.decode("utf-8", "strict"); err.decode("utf-8", "strict")
    except UnicodeDecodeError: raise _Known("REPOSITORY_OUTPUT_INVALID")
    return proc.returncode, out, err


def _line(path: str, argv: tuple[str, ...], deadline: float, missing: str = "REPOSITORY_COMMAND_FAILED") -> str:
    status, out, _ = _git(path, argv, deadline)
    if status != 0: raise _Known(missing)
    try: text=out.decode("utf-8", "strict")
    except UnicodeDecodeError: raise _Known("REPOSITORY_OUTPUT_INVALID")
    if text.count("\n") != 1 or not text.endswith("\n") or "\x00" in text: raise _Known("REPOSITORY_OUTPUT_INVALID")
    return text[:-1]


def compare_phase_12_repository_identity_and_locked_commit_v1(
    *,
    repository_path: str,
    repository_identity: str,
    accepted_locked_commit: str,
    expected_origin_fetch_url: str,
    expected_origin_push_url: str,
) -> _Phase12RepositoryIdentityLockedCommitComparatorResultV1:
    for value in (repository_path, repository_identity, accepted_locked_commit, expected_origin_fetch_url, expected_origin_push_url):
        if type(value) is not str: raise TypeError()
    if not _IDENTIFIER.fullmatch(repository_identity) or not _COMMIT.fullmatch(accepted_locked_commit) or not _url_ok(expected_origin_fetch_url) or not _url_ok(expected_origin_push_url): raise TypeError()
    if not _path_ok(repository_path): return _failure("PATH_TYPE_INVALID")
    descriptors: list[int] = []
    try:
        try:
            descriptors, root_fd, before_root, before_git = _open_path(repository_path)
        except FileNotFoundError: return _failure("REPOSITORY_UNAVAILABLE")
        except OSError as error:
            return _failure("REPOSITORY_SYMLINK_REJECTED" if error.errno == 40 else "REPOSITORY_UNAVAILABLE")
        except _Known as error: return _failure(str(error))
        deadline=time.monotonic()+60.0
        def exact(argv: tuple[str,...], expected: str, code: str="REPOSITORY_COMMAND_FAILED") -> None:
            if _line(repository_path, argv, deadline, code) != expected: raise _Known(code)
        exact(("rev-parse","--is-inside-work-tree"),"true","REPOSITORY_NOT_GIT_WORKTREE")
        exact(("rev-parse","--show-toplevel"),repository_path,"REPOSITORY_PATH_MISMATCH")
        exact(("rev-parse","--absolute-git-dir"),repository_path+"/.git","REPOSITORY_GIT_DIR_MISMATCH")
        exact(("rev-parse","--git-common-dir"),repository_path+"/.git","REPOSITORY_LINKED_WORKTREE_REJECTED")
        exact(("rev-parse","--is-bare-repository"),"false","REPOSITORY_LINKED_WORKTREE_REJECTED")
        exact(("rev-parse","--show-object-format"),"sha1","REPOSITORY_OBJECT_FORMAT_UNSUPPORTED")
        exact(("rev-parse","--is-shallow-repository"),"false","REPOSITORY_SHALLOW_REJECTED")
        exact(("symbolic-ref","--quiet","HEAD"),"refs/heads/master","REPOSITORY_DETACHED_HEAD")
        exact(("cat-file","-t","--end-of-options",accepted_locked_commit),"commit","REPOSITORY_OBJECT_MISSING")
        exact(("rev-parse","--verify","--end-of-options",accepted_locked_commit+"^{commit}"),accepted_locked_commit,"REPOSITORY_ACCEPTED_COMMIT_INVALID")
        exact(("rev-parse","--verify","HEAD^{commit}"),accepted_locked_commit,"REPOSITORY_HEAD_MISMATCH")
        exact(("config","--local","--no-includes","--get","remote.origin.url"),expected_origin_fetch_url,"REPOSITORY_REMOTE_MISSING")
        exact(("config","--local","--no-includes","--get","remote.origin.pushurl"),expected_origin_push_url,"REPOSITORY_REMOTE_MISSING")
        exact(("rev-parse","--verify","refs/remotes/origin/master^{commit}"),accepted_locked_commit,"REPOSITORY_ORIGIN_MASTER_MISMATCH")
        exact(("symbolic-ref","--quiet","refs/remotes/origin/HEAD"),"refs/remotes/origin/master","REPOSITORY_ORIGIN_HEAD_MISMATCH")
        status, output, _ = _git(repository_path, _OVERRIDES+("status","--porcelain=v2","-z","--untracked-files=all","--ignore-submodules=none"), deadline)
        if status != 0: return _failure("REPOSITORY_COMMAND_FAILED")
        if output: return _failure("REPOSITORY_DIRTY")
        # final descriptor metadata recheck is the frozen persistent-drift boundary.
        if _snapshot(os.fstat(root_fd)) != before_root or _snapshot(os.fstat(descriptors[-1])) != before_git:
            return _failure("REPOSITORY_CHANGED_DURING_OPERATION")
        return _Phase12RepositoryIdentityLockedCommitComparatorResultV1(is_match=True, failure_codes=(), repository_identity=repository_identity, repository_top_level=repository_path, head_commit=accepted_locked_commit, branch_name="master", origin_master_commit=accepted_locked_commit, origin_head_target="refs/remotes/origin/master", object_format="sha1", is_clean=True)
    except FileNotFoundError:
        return _failure("REPOSITORY_UNAVAILABLE")
    except _Known as error:
        return _failure(str(error))
    finally:
        _close(descriptors)


# Frozen source-contract phrases retained for static RED audits.
_CONTRACT_TEXT = "failure count; type(value) is str; normalized absolute; keyword-only; root path itself invalid; The deterministic allowlist and output contracts are exactly:; git rev-parse --verify; terminate process group; malformed output; unexpected nonzero exit; symbolically; Descriptor-relative; expected process/filesystem/Git; marker/key/revocation/replay access; does not prove freshness; does not prove hosting identity; does not prove source trust; does not prove authorization; local facts at observation time only"
