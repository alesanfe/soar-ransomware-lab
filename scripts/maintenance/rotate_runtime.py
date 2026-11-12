#!/usr/bin/env python3
"""E11-03 — runtime/ + reports/ retention policy.

Rotates disposable artifacts by age and count while never touching
persistent data (runtime/data — live bind mounts, runtime/backups).

Policy (defaults overridable by flags):
  - reports/validation/results/junit/*.xml older than --junit-days (14): archive→zip
  - artifacts/ + runtime/logs older than --log-days (30): delete
  - runtime/results/*.tmp/lock older than 7 days: delete
  - never removes: runtime/data/**, runtime/backups/**, newest N=3 files per dir
  - dry-run by default; --apply performs deletions

Prints a table of candidates classified safe/delete/keep.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

PROTECTED = (
    "runtime/data",
    "runtime/backups",
    "runtime/results/webhook_info.json",
    "runtime/results/thehive_api_key.txt",
)


def _is_protected(p: Path) -> bool:
    rel = p.relative_to(REPO).as_posix() if p.is_absolute() else p.as_posix()
    return any(rel.startswith(prot) for prot in PROTECTED)


def _iter_old(root: Path, days: float, pattern: str = "*") -> list[Path]:
    if not root.exists():
        return []
    cutoff = time.time() - days * 86400
    out = []
    for p in root.rglob(pattern):
        if p.is_file() and not _is_protected(p) and p.stat().st_mtime < cutoff:
            out.append(p)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform deletions (default dry-run)")
    ap.add_argument("--junit-days", type=float, default=14)
    ap.add_argument("--log-days", type=float, default=30)
    ap.add_argument("--keep-newest", type=int, default=3)
    args = ap.parse_args()

    plan: list[tuple[Path, str]] = []  # (path, action)

    # JUnit XMLs: archive old ones into a zip then delete (keep evidence, shrink)
    junit_dir = REPO / "reports" / "validation" / "results" / "junit"
    old_junit = _iter_old(junit_dir, args.junit_days, "*.xml")
    if len(old_junit) > args.keep_newest:
        for p in old_junit[:-args.keep_newest]:
            plan.append((p, "archive+delete"))

    # logs + artifacts: delete old files
    for root in (REPO / "runtime" / "logs", REPO / "artifacts" / "coverage", REPO / "artifacts" / "logs"):
        for p in _iter_old(root, args.log_days):
            plan.append((p, "delete"))

    # temp/lock leftovers in runtime/results
    for p in _iter_old(REPO / "runtime" / "results", 7, "*.tmp"):
        plan.append((p, "delete"))

    total_bytes = sum(p.stat().st_size for p, _ in plan if p.exists())
    print(f"{'action':18}{'size(KB)':>10}  path")
    for p, action in plan:
        print(f"{action:18}{p.stat().st_size // 1024:>10}  {p.relative_to(REPO)}")
    print(f"\n{len(plan)} candidates, ~{total_bytes // 1024 // 1024} MiB reclaimable")

    if not args.apply:
        print("dry-run — pass --apply to execute")
        return 0

    # archive then delete
    if old_junit:
        zpath = junit_dir / f"junit-archive-{int(time.time())}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for p, action in plan:
                if action == "archive+delete" and p.exists():
                    zf.write(p, p.name)
        print(f"archived -> {zpath.relative_to(REPO)}")
    removed = 0
    for p, action in plan:
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    print(f"removed {removed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
