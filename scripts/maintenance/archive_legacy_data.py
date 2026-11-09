#!/usr/bin/env python3
"""Archive legacy bind-mount data directories left behind by the named-volume
migrations (GRAF-D6) and the S3 cutover (GRAF-D5).

For each directory under ``runtime/data`` that is no longer mounted by any
container (opensearch, grafana, loki, tempo, prometheus, elasticsearch):

1. Create ``runtime/backups/legacy/<name>-<epoch>.tar.gz``
2. Verify the tarball is readable and lists the same file count
3. Remove the source directory

Run::

    python scripts/maintenance/archive_legacy_data.py            # archive+delete
    python scripts/maintenance/archive_legacy_data.py --dry-run  # report only
    python scripts/maintenance/archive_legacy_data.py --keep     # archive, keep source

Legacy dirs not present are skipped. Active named volumes are untouched —
this only handles leftover Windows bind-mount directories.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tarfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "runtime" / "data"
BACKUP_DIR = REPO_ROOT / "runtime" / "backups" / "legacy"

LEGACY_DIRS = [
    "opensearch",
    "grafana",
    "loki",
    "tempo",
    "prometheus",
    "elasticsearch",
]


def _count_members(tar: tarfile.TarFile) -> int:
    return sum(1 for _ in tar)


def archive_one(src: Path, dest: Path, keep: bool, dry_run: bool) -> bool:
    """Tar ``src`` into ``dest``, verify, optionally remove the source."""
    n_files = sum(1 for p in src.rglob("*") if p.is_file())
    size_mb = sum(p.stat().st_size for p in src.rglob("*") if p.is_file()) / 1e6
    if dry_run:
        logger.info("[dry-run] %s -> %s (%d files, %.1f MB)", src, dest, n_files, size_mb)
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(src, arcname=src.name)

    with tarfile.open(dest, "r:gz") as tar:
        members = _count_members(tar)
    # tarfile counts dirs + files; expect >= file count or abort
    if members < n_files:
        logger.error(
            "VERIFY FAILED %s: tarball has %d members but source had %d files — keeping source",
            src,
            members,
            n_files,
        )
        return False

    logger.info("Archived %s -> %s (%d files, %.1f MB)", src, dest, n_files, size_mb)
    if not keep:
        shutil.rmtree(src)
        logger.info("Removed %s", src)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only")
    parser.add_argument("--keep", action="store_true", help="keep source dirs after archiving")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    epoch = int(time.time())
    failures = 0
    for name in LEGACY_DIRS:
        src = DATA_DIR / name
        if not src.is_dir():
            logger.info("skip %s (absent)", src)
            continue
        dest = BACKUP_DIR / f"{name}-{epoch}.tar.gz"
        if not archive_one(src, dest, args.keep, args.dry_run):
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
