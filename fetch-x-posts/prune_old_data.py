"""Delete fetch-x-posts data older than N days, except user timelines.

Pruned under the news project's data dir:
  - x_search/<query>/            whole folder, when its newest file is older than the cutoff
  - x_home_feed/<feed>/home_*    individual snapshots older than the cutoff
user_tweets/ (account timeline scraping) is never touched.

Age is file mtime. Prints a JSON report to stdout; exit 0 unless the data dir is invalid.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / "projects" / "news" / "data"
DEFAULT_DAYS = 7


def newest_mtime(folder: Path) -> float:
    """Newest mtime among files under folder (the folder's own mtime if empty)."""
    mtimes = [p.stat().st_mtime for p in folder.rglob("*") if p.is_file()]
    return max(mtimes, default=folder.stat().st_mtime)


def prune(data_dir: Path, days: float, dry_run: bool = False) -> dict:
    cutoff = time.time() - days * 86400
    removed_dirs: list[str] = []
    removed_files: list[str] = []

    search_root = data_dir / "x_search"
    if search_root.is_dir():
        for query_dir in sorted(search_root.iterdir()):
            if query_dir.is_dir() and newest_mtime(query_dir) < cutoff:
                removed_dirs.append(str(query_dir))
                if not dry_run:
                    shutil.rmtree(query_dir)

    home_root = data_dir / "x_home_feed"
    if home_root.is_dir():
        for snap in sorted(home_root.glob("*/home_*.jsonl")):
            if snap.stat().st_mtime < cutoff:
                removed_files.append(str(snap))
                if not dry_run:
                    snap.unlink()

    return {
        "data_dir": str(data_dir),
        "days": days,
        "dry_run": dry_run,
        "removed_dirs": removed_dirs,
        "removed_files": removed_files,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help=f"news data dir (default {DEFAULT_DATA_DIR})")
    ap.add_argument("--days", type=float, default=DEFAULT_DAYS, help=f"retention in days (default {DEFAULT_DAYS})")
    ap.add_argument("--dry-run", action="store_true", help="report what would be deleted without deleting")
    args = ap.parse_args(argv)

    if not args.data_dir.is_dir():
        print(json.dumps({"error": f"data dir not found: {args.data_dir}"}))
        return 2
    report = prune(args.data_dir, args.days, args.dry_run)
    print(json.dumps({**report, "removed_dir_count": len(report["removed_dirs"]),
                      "removed_file_count": len(report["removed_files"])}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
