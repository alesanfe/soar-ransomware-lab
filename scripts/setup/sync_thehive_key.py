#!/usr/bin/env python3
"""Sync the TheHive API key renewed by ``init_thehive.py`` back to .env.full.

``init_thehive.py`` runs inside ``soar_api`` where no .env file is writable,
so it persists a renewed key to ``runtime/results/thehive_api_key.txt``
(host-mounted). This host-side helper copies that key into ``.env.full``
(and the container env copy) when it differs from the configured value —
then deletes the marker so a stale key is never re-applied.

Usage: ``python scripts/setup/sync_thehive_key.py`` (run after init_thehive).
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
KEY_FILE = REPO_ROOT / "runtime" / "results" / "thehive_api_key.txt"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not KEY_FILE.exists():
        logger.info("No renewed TheHive key pending — nothing to sync.")
        return 0
    api_key = KEY_FILE.read_text(encoding="utf-8").strip()
    if len(api_key) <= 10:
        logger.warning("Marker file %s does not look like an API key — ignoring.", KEY_FILE)
        return 0

    try:
        from scripts.setup import env_files
    except ImportError:
        import env_files  # type: ignore[no-redef]

    env_file = REPO_ROOT / ".env.full"
    current = ""
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("THEHIVE_API_KEY="):
                current = line.split("=", 1)[1].strip()
                break
    if current == api_key:
        logger.info("THEHIVE_API_KEY already in sync.")
    else:
        env_files.update_env_files({"THEHIVE_API_KEY": api_key}, env_file=str(env_file))
        logger.info("THEHIVE_API_KEY synced to .env.full (restart api/thehive consumers to apply).")

    try:
        KEY_FILE.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
