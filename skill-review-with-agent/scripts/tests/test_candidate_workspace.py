import os
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).parents[1] / "candidate_workspace.py"


def run_helper(
    *arguments: object, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *(str(argument) for argument in arguments)],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"helper failed with {result.returncode}\nstdout:\n{result.stdout}"
            f"\nstderr:\n{result.stderr}"
        )
    return result


def make_skill(root: Path) -> Path:
    skill = root / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# Test skill\n", encoding="utf-8")
    return skill


def setup_workspace(tmp_path: Path) -> tuple[Path, Path]:
    live = make_skill(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_helper("setup", live, workspace)
    return live, workspace


def test_tree_comparison_detects_empty_files_and_modes(tmp_path: Path) -> None:
    live = make_skill(tmp_path)
    os.chmod(live / "SKILL.md", 0o600)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_helper("setup", live, workspace)

    candidate = workspace / "candidate"
    (candidate / "empty.py").touch()
    os.chmod(candidate / "empty.py", 0o640)
    os.chmod(candidate / "SKILL.md", 0o700)

    result = run_helper("pending-diff", workspace)

    assert result.returncode == 0
    assert "TREE_EQUAL: no" in result.stdout
    assert "A empty.py: file mode=0640" in result.stdout
    assert "mode 0600 -> 0700" in result.stdout


def test_round_restore_is_exact_for_candidate_and_log(tmp_path: Path) -> None:
    _, workspace = setup_workspace(tmp_path)
    candidate = workspace / "candidate"

    run_helper("round-snapshot", workspace, 1)
    (candidate / "SKILL.md").write_text("changed\n", encoding="utf-8")
    (candidate / "added.txt").write_text("added\n", encoding="utf-8")
    (workspace / "review.md").write_text("partial\n", encoding="utf-8")
    run_helper("round-restore", workspace, 1)

    restored = run_helper("pending-diff", workspace)
    assert "TREE_EQUAL: yes" in restored.stdout
    assert not (workspace / "review.md").exists()

    (workspace / "review.md").write_text("before\n", encoding="utf-8")
    run_helper("round-snapshot", workspace, 2)
    (workspace / "review.md").write_text("after\n", encoding="utf-8")
    run_helper("round-restore", workspace, 2)
    assert (workspace / "review.md").read_text(encoding="utf-8") == "before\n"


def test_round_restore_recovers_from_unsafe_candidate_symlink(tmp_path: Path) -> None:
    live, workspace = setup_workspace(tmp_path)
    run_helper("round-snapshot", workspace, 1)
    candidate = workspace / "candidate"
    (candidate / "escape").symlink_to(live / "SKILL.md")

    failed_comparison = run_helper("round-diff", workspace, 1, check=False)
    assert failed_comparison.returncode != 0

    run_helper("round-restore", workspace, 1)
    assert not (candidate / "escape").exists()
    assert "TREE_EQUAL: yes" in run_helper("pending-diff", workspace).stdout


def test_ignored_symlinks_are_rejected_and_restorable(tmp_path: Path) -> None:
    live, workspace = setup_workspace(tmp_path)
    candidate = workspace / "candidate"

    run_helper("round-snapshot", workspace, 1)
    (candidate / ".DS_Store").symlink_to(live / "SKILL.md")
    failed_comparison = run_helper("round-diff", workspace, 1, check=False)
    assert failed_comparison.returncode != 0
    assert "symlinks are unsupported" in failed_comparison.stderr
    run_helper("round-restore", workspace, 1)

    run_helper("round-snapshot", workspace, 2)
    ignored_directory = candidate / ".pytest_cache"
    ignored_directory.mkdir()
    (ignored_directory / "escape").symlink_to(live / "SKILL.md")
    failed_nested_comparison = run_helper("round-diff", workspace, 2, check=False)
    assert failed_nested_comparison.returncode != 0
    assert "symlinks are unsupported" in failed_nested_comparison.stderr
    run_helper("round-restore", workspace, 2)

    assert not (candidate / ".DS_Store").exists()
    assert not (candidate / ".pytest_cache").exists()
    assert "TREE_EQUAL: yes" in run_helper("pending-diff", workspace).stdout


def test_round_snapshot_normalizes_ignored_junk(tmp_path: Path) -> None:
    _, workspace = setup_workspace(tmp_path)
    candidate = workspace / "candidate"
    (candidate / ".DS_Store").write_bytes(b"finder junk")
    (candidate / "nested" / "__pycache__").mkdir(parents=True)
    (candidate / "nested" / "__pycache__" / "module.pyc").write_bytes(b"cache")
    (candidate / ".pytest_cache").mkdir()
    (candidate / ".pytest_cache" / "state").write_text("junk\n", encoding="utf-8")

    run_helper("round-snapshot", workspace, 1)
    before = workspace / "round-1-before"

    for root in (candidate, before):
        assert not (root / ".DS_Store").exists()
        assert not (root / "nested" / "__pycache__").exists()
        assert not (root / ".pytest_cache").exists()

    (candidate / "SKILL.md").write_text("changed\n", encoding="utf-8")
    run_helper("round-restore", workspace, 1)
    assert "TREE_EQUAL: yes" in run_helper("compare", before, candidate).stdout


def test_junk_entries_are_invisible_and_never_installed(tmp_path: Path) -> None:
    live = make_skill(tmp_path)
    pycache = live / "__pycache__"
    pycache.mkdir()
    (pycache / "stale.pyc").write_bytes(b"junk")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_helper("setup", live, workspace)

    candidate = workspace / "candidate"
    assert not (candidate / "__pycache__").exists()
    (candidate / ".DS_Store").write_bytes(b"finder junk")
    (candidate / ".pytest_cache").mkdir()
    (live / ".DS_Store").write_bytes(b"finder junk on live")

    assert "TREE_EQUAL: yes" in run_helper("pending-diff", workspace).stdout
    assert "LIVE_UNCHANGED: yes" in run_helper("live-diff", workspace, live).stdout

    (candidate / "SKILL.md").write_text("# Updated\n", encoding="utf-8")
    result = run_helper("apply", workspace, live)

    assert "APPLIED: yes" in result.stdout
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "# Updated\n"
    assert not (live / ".pytest_cache").exists()
    assert not list(live.rglob("*.pyc"))


def test_round_restore_keeps_log_when_backup_is_invalid(tmp_path: Path) -> None:
    _, workspace = setup_workspace(tmp_path)
    (workspace / "review.md").write_text("round 1\n", encoding="utf-8")
    run_helper("round-snapshot", workspace, 1)
    (workspace / "round-1-review.before").unlink()

    result = run_helper("round-restore", workspace, 1, check=False)

    assert result.returncode != 0
    assert "log backup is invalid" in result.stderr
    assert (workspace / "review.md").read_text(encoding="utf-8") == "round 1\n"


def test_apply_rejects_live_drift_without_touching_it(tmp_path: Path) -> None:
    live, workspace = setup_workspace(tmp_path)
    (workspace / "candidate" / "SKILL.md").write_text(
        "candidate\n", encoding="utf-8"
    )
    (live / "SKILL.md").write_text("user edit\n", encoding="utf-8")

    result = run_helper("apply", workspace, live, check=False)

    assert result.returncode != 0
    assert "live skill changed" in result.stderr
    assert (live / "SKILL.md").read_text(encoding="utf-8") == "user edit\n"


def test_apply_installs_additions_deletions_contents_and_modes(tmp_path: Path) -> None:
    live = make_skill(tmp_path)
    (live / "delete.txt").write_text("remove me\n", encoding="utf-8")
    (live / "tool.py").write_text("print('old')\n", encoding="utf-8")
    os.chmod(live / "tool.py", 0o600)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    run_helper("setup", live, workspace)

    candidate = workspace / "candidate"
    (candidate / "delete.txt").unlink()
    (candidate / "empty.py").touch()
    (candidate / "tool.py").write_text("print('new')\n", encoding="utf-8")
    os.chmod(candidate / "tool.py", 0o700)

    result = run_helper("apply", workspace, live)

    assert "APPLIED: yes" in result.stdout
    assert not (live / "delete.txt").exists()
    assert (live / "empty.py").is_file()
    assert (live / "empty.py").stat().st_size == 0
    assert (live / "tool.py").read_text(encoding="utf-8") == "print('new')\n"
    assert (live / "tool.py").stat().st_mode & 0o777 == 0o700
    assert "TREE_EQUAL: yes" in run_helper("compare", candidate, live).stdout
    assert not list(live.parent.glob(f".{live.name}.skill-review-*"))
