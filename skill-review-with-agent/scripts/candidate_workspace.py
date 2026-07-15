"""Manage a disposable, Git-free workspace for mutable skill reviews.

The comparison commands always exit zero and report equality in stdout.
Operational failures (invalid trees, live drift, failed apply/rollback) exit
nonzero. Tree equality covers path presence, entry type, permission bits, and
file contents. Symlinks and special files are rejected so reviewer writes
cannot escape the disposable candidate tree. Every entry is safety-checked
before junk entries (.DS_Store, __pycache__, .pytest_cache) are filtered from
comparisons and copies, so ignored names cannot hide unsafe entries. Round
snapshots remove that junk before recording the exact candidate restore point.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import NamedTuple
import uuid


MARKER_NAME = ".skill-review-workspace.json"
REVIEW_LOG_NAME = "review.md"
IGNORED_NAMES = frozenset({".DS_Store", "__pycache__", ".pytest_cache"})


class WorkspaceError(RuntimeError):
    """Raised when a workspace operation cannot be completed safely."""


class TreeEntry(NamedTuple):
    kind: str
    mode: int
    digest: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(root: Path) -> dict[str, TreeEntry]:
    root = root.expanduser()
    if root.is_symlink():
        raise WorkspaceError(f"tree root must not be a symlink: {root}")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise WorkspaceError(f"tree root is not a directory: {root}")

    entries: dict[str, TreeEntry] = {
        ".": TreeEntry("directory", stat.S_IMODE(root.stat().st_mode), "")
    }

    def visit(directory: Path, prefix: str, *, included: bool) -> None:
        with os.scandir(directory) as scan:
            children = sorted(scan, key=lambda child: child.name)
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            child_path = Path(child.path)
            child_stat = child.stat(follow_symlinks=False)
            mode = stat.S_IMODE(child_stat.st_mode)
            child_included = included and child.name not in IGNORED_NAMES
            if stat.S_ISLNK(child_stat.st_mode):
                raise WorkspaceError(
                    f"symlinks are unsupported in mutable skill trees: {relative}"
                )
            if stat.S_ISDIR(child_stat.st_mode):
                if child_included:
                    entries[relative] = TreeEntry("directory", mode, "")
                visit(child_path, relative, included=child_included)
            elif stat.S_ISREG(child_stat.st_mode):
                if child_included:
                    entries[relative] = TreeEntry("file", mode, _sha256(child_path))
            else:
                raise WorkspaceError(
                    f"special files are unsupported in mutable skill trees: {relative}"
                )

    visit(root, "", included=True)
    return entries


def _describe(entry: TreeEntry) -> str:
    suffix = f" sha256={entry.digest[:12]}" if entry.kind == "file" else ""
    return f"{entry.kind} mode={entry.mode:04o}{suffix}"


def _tree_changes(left: Path, right: Path) -> list[str]:
    left_manifest = _manifest(left)
    right_manifest = _manifest(right)
    changes: list[str] = []
    for relative in sorted(set(left_manifest) | set(right_manifest)):
        left_entry = left_manifest.get(relative)
        right_entry = right_manifest.get(relative)
        if left_entry is None:
            changes.append(f"A {relative}: {_describe(right_entry)}")
            continue
        if right_entry is None:
            changes.append(f"D {relative}: {_describe(left_entry)}")
            continue
        details: list[str] = []
        if left_entry.kind != right_entry.kind:
            details.append(f"type {left_entry.kind} -> {right_entry.kind}")
        if left_entry.mode != right_entry.mode:
            details.append(f"mode {left_entry.mode:04o} -> {right_entry.mode:04o}")
        if left_entry.digest != right_entry.digest:
            details.append(
                f"content {left_entry.digest[:12]} -> {right_entry.digest[:12]}"
            )
        if details:
            changes.append(f"M {relative}: {', '.join(details)}")
    return changes


def _print_changes(changes: list[str], *, label: str = "TREE_EQUAL") -> None:
    print(f"{label}: {'yes' if not changes else 'no'}")
    for change in changes:
        print(change)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _prune_ignored(root: Path) -> None:
    _manifest(root)
    root = root.expanduser().resolve(strict=True)

    def visit(directory: Path) -> None:
        with os.scandir(directory) as scan:
            children = sorted(scan, key=lambda child: child.name)
        for child in children:
            child_path = Path(child.path)
            if child.name in IGNORED_NAMES:
                _remove_path(child_path)
            elif child.is_dir(follow_symlinks=False):
                visit(child_path)

    visit(root)


def _copy_tree(source: Path, destination: Path) -> None:
    _manifest(source)
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError(f"copy destination already exists: {destination}")
    shutil.copytree(
        source,
        destination,
        copy_function=shutil.copy2,
        ignore=shutil.ignore_patterns(*IGNORED_NAMES),
    )
    changes = _tree_changes(source, destination)
    if changes:
        _remove_path(destination)
        raise WorkspaceError(
            "tree copy did not preserve the source exactly:\n" + "\n".join(changes)
        )


def _write_json(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _workspace_path(raw: str) -> Path:
    workspace = Path(raw).expanduser().resolve(strict=True)
    if not workspace.is_dir():
        raise WorkspaceError(f"workspace is not a directory: {workspace}")
    return workspace


def _live_skill_path(raw: str) -> Path:
    live = Path(raw).expanduser().resolve(strict=True)
    if not live.is_dir() or not (live / "SKILL.md").is_file():
        raise WorkspaceError(f"live path is not a skill directory: {live}")
    return live


def _load_workspace(
    raw: str, *, validate_candidate: bool = True
) -> tuple[Path, Path, Path]:
    workspace = _workspace_path(raw)
    marker = workspace / MARKER_NAME
    if not marker.is_file() or marker.is_symlink():
        raise WorkspaceError(f"workspace marker is missing or unsafe: {marker}")
    data = json.loads(marker.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise WorkspaceError(f"workspace marker is invalid: {marker}")
    original = workspace / "original"
    candidate = workspace / "candidate"
    _manifest(original)
    if validate_candidate:
        _manifest(candidate)
    return workspace, original, candidate


def _round_paths(workspace: Path, round_number: int) -> tuple[Path, Path, Path]:
    return (
        workspace / f"round-{round_number}-before",
        workspace / f"round-{round_number}-review.before",
        workspace / f"round-{round_number}-state.json",
    )


def command_setup(arguments: argparse.Namespace) -> None:
    workspace = _workspace_path(arguments.workspace)
    live = _live_skill_path(arguments.live)
    marker = workspace / MARKER_NAME
    original = workspace / "original"
    candidate = workspace / "candidate"
    for path in (marker, original, candidate):
        if path.exists() or path.is_symlink():
            raise WorkspaceError(f"workspace path already exists: {path}")

    try:
        _copy_tree(live, original)
        _copy_tree(original, candidate)
        _write_json(marker, {"version": 1})
    except Exception:
        _remove_path(original)
        _remove_path(candidate)
        _remove_path(marker)
        raise
    print(f"WORKSPACE_READY: yes\nLIVE: {live}\nWORKSPACE: {workspace}")


def command_round_snapshot(arguments: argparse.Namespace) -> None:
    workspace, _, candidate = _load_workspace(arguments.workspace)
    before, log_backup, state = _round_paths(workspace, arguments.round)
    review_log = workspace / REVIEW_LOG_NAME
    for path in (before, log_backup, state):
        if path.exists() or path.is_symlink():
            raise WorkspaceError(f"round snapshot path already exists: {path}")

    if review_log.is_symlink():
        raise WorkspaceError(f"review log must not be a symlink: {review_log}")
    review_log_existed = review_log.exists()
    if review_log_existed and (not review_log.is_file() or review_log.is_symlink()):
        raise WorkspaceError(f"review log is not a regular file: {review_log}")
    try:
        _prune_ignored(candidate)
        _copy_tree(candidate, before)
        if review_log_existed:
            shutil.copy2(review_log, log_backup)
        _write_json(state, {"review_log_existed": review_log_existed})
    except Exception:
        _remove_path(before)
        _remove_path(log_backup)
        _remove_path(state)
        raise
    print(f"ROUND_SNAPSHOT_READY: yes\nROUND: {arguments.round}")


def command_round_restore(arguments: argparse.Namespace) -> None:
    workspace, _, candidate = _load_workspace(
        arguments.workspace, validate_candidate=False
    )
    before, log_backup, state = _round_paths(workspace, arguments.round)
    if (
        not before.is_dir()
        or before.is_symlink()
        or not state.is_file()
        or state.is_symlink()
    ):
        raise WorkspaceError(f"round {arguments.round} snapshot is incomplete")
    state_data = json.loads(state.read_text(encoding="utf-8"))
    review_log_existed = state_data.get("review_log_existed")
    if not isinstance(review_log_existed, bool):
        raise WorkspaceError(f"round {arguments.round} state is invalid")
    if review_log_existed and (not log_backup.is_file() or log_backup.is_symlink()):
        raise WorkspaceError(f"round {arguments.round} log backup is invalid")

    _remove_path(candidate)
    _copy_tree(before, candidate)
    review_log = workspace / REVIEW_LOG_NAME
    _remove_path(review_log)
    if review_log_existed:
        shutil.copy2(log_backup, review_log)
    print(f"ROUND_RESTORED: yes\nROUND: {arguments.round}")


def command_round_diff(arguments: argparse.Namespace) -> None:
    workspace, _, candidate = _load_workspace(arguments.workspace)
    before, _, _ = _round_paths(workspace, arguments.round)
    if not before.is_dir():
        raise WorkspaceError(f"round {arguments.round} snapshot is missing")
    _print_changes(_tree_changes(before, candidate))


def command_pending_diff(arguments: argparse.Namespace) -> None:
    _, original, candidate = _load_workspace(arguments.workspace)
    _print_changes(_tree_changes(original, candidate))


def command_live_diff(arguments: argparse.Namespace) -> None:
    _, original, _ = _load_workspace(arguments.workspace)
    live = _live_skill_path(arguments.live)
    _print_changes(_tree_changes(original, live), label="LIVE_UNCHANGED")


def command_compare(arguments: argparse.Namespace) -> None:
    left = Path(arguments.left).expanduser().resolve(strict=True)
    right = Path(arguments.right).expanduser().resolve(strict=True)
    _print_changes(_tree_changes(left, right))


def _rollback_installed(live: Path, backup: Path) -> None:
    failed = live.parent / f".{live.name}.skill-review-failed-{uuid.uuid4().hex}"
    if live.exists() or live.is_symlink():
        os.rename(live, failed)
    os.rename(backup, live)
    _remove_path(failed)


def _apply_candidate(live: Path, original: Path, candidate: Path) -> None:
    initial_drift = _tree_changes(original, live)
    if initial_drift:
        _print_changes(initial_drift, label="LIVE_UNCHANGED")
        raise WorkspaceError("live skill changed after workspace setup; do not apply")

    token = uuid.uuid4().hex
    stage = live.parent / f".{live.name}.skill-review-stage-{token}"
    backup = live.parent / f".{live.name}.skill-review-backup-{token}"
    lock_key = hashlib.sha256(str(live).encode("utf-8")).hexdigest()
    lock_directory = Path(tempfile.gettempdir()) / "skill-review-with-agent-locks"
    lock_directory.mkdir(mode=0o700, exist_ok=True)
    lock_path = lock_directory / f"{lock_key}.lock"
    installed = False
    moved_live = False

    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise WorkspaceError(f"another apply holds the lock: {lock_path}") from error
        try:
            _copy_tree(candidate, stage)
            final_drift = _tree_changes(original, live)
            if final_drift:
                _print_changes(final_drift, label="LIVE_UNCHANGED")
                raise WorkspaceError("live skill changed immediately before apply")

            os.rename(live, backup)
            moved_live = True
            backup_drift = _tree_changes(original, backup)
            if backup_drift:
                os.rename(backup, live)
                moved_live = False
                _print_changes(backup_drift, label="LIVE_UNCHANGED")
                raise WorkspaceError("live skill changed during the apply handoff")

            os.rename(stage, live)
            installed = True
            installed_changes = _tree_changes(candidate, live)
            backup_drift = _tree_changes(original, backup)
            if installed_changes or backup_drift:
                _rollback_installed(live, backup)
                installed = False
                moved_live = False
                details = installed_changes or backup_drift
                raise WorkspaceError(
                    "applied tree failed verification and was rolled back:\n"
                    + "\n".join(details)
                )

            _remove_path(backup)
            moved_live = False
        except Exception:
            _remove_path(stage)
            if backup.exists():
                if installed:
                    _rollback_installed(live, backup)
                elif moved_live and not live.exists():
                    os.rename(backup, live)
            raise
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def command_apply(arguments: argparse.Namespace) -> None:
    _, original, candidate = _load_workspace(arguments.workspace)
    live = _live_skill_path(arguments.live)
    pending = _tree_changes(original, candidate)
    _print_changes(pending, label="CANDIDATE_CHANGED")
    if not pending:
        print("APPLIED: no — candidate matches the original")
        return
    _apply_candidate(live, original, candidate)
    post_apply = _tree_changes(candidate, live)
    if post_apply:
        raise WorkspaceError(
            "post-apply verification failed:\n" + "\n".join(post_apply)
        )
    print("APPLIED: yes")


def _positive_round(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("round must be at least 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create, compare, restore, and safely apply a disposable skill-review "
            "candidate without relying on Git."
        )
    )
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser(
        "setup",
        help="copy a live skill into pristine original/ and editable candidate/ trees",
    )
    setup.add_argument("live", help="path to the live skill directory")
    setup.add_argument("workspace", help="existing empty temp workspace")
    setup.set_defaults(function=command_setup)

    snapshot = commands.add_parser(
        "round-snapshot",
        help="snapshot candidate/ and review.md before a mutable reviewer call",
    )
    snapshot.add_argument("workspace")
    snapshot.add_argument("round", type=_positive_round)
    snapshot.set_defaults(function=command_round_snapshot)

    restore = commands.add_parser(
        "round-restore",
        help="restore candidate/ and review.md exactly to a round snapshot",
    )
    restore.add_argument("workspace")
    restore.add_argument("round", type=_positive_round)
    restore.set_defaults(function=command_round_restore)

    round_diff = commands.add_parser(
        "round-diff",
        help="report all path, type, mode, and content changes made in a round",
    )
    round_diff.add_argument("workspace")
    round_diff.add_argument("round", type=_positive_round)
    round_diff.set_defaults(function=command_round_diff)

    pending = commands.add_parser(
        "pending-diff",
        help="report all changes from original/ to candidate/",
    )
    pending.add_argument("workspace")
    pending.set_defaults(function=command_pending_diff)

    live_diff = commands.add_parser(
        "live-diff",
        help="report whether the live skill still matches original/",
    )
    live_diff.add_argument("workspace")
    live_diff.add_argument("live", help="pinned path to the live skill directory")
    live_diff.set_defaults(function=command_live_diff)

    compare = commands.add_parser(
        "compare",
        help="compare any two safe directory trees without using exit status as data",
    )
    compare.add_argument("left")
    compare.add_argument("right")
    compare.set_defaults(function=command_compare)

    apply = commands.add_parser(
        "apply",
        help="apply candidate/ after drift checks, staged replacement, and rollback",
    )
    apply.add_argument("workspace")
    apply.add_argument("live", help="pinned path to the live skill directory")
    apply.set_defaults(function=command_apply)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        arguments.function(arguments)
    except (WorkspaceError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
