#!/usr/bin/env python3
"""Clean old TheHive cases to prevent Elasticsearch performance degradation.

TheHive uses an internal Elasticsearch index for cases and observables.
When hundreds of cases accumulate from repeated E2E test runs, TheHive's
ES queries slow down and eventually time out (30s SocketTimeoutException),
causing workflow nodes like ``thehive_obs_hash`` to return HTTP 500.

This script deletes all TheHive cases (or keeps the last ``--keep`` cases)
so that each E2E run starts from a clean baseline.

Usage (inside container):
    python /app/scripts/maintenance/clean_thehive_cases.py [--keep N]

Usage (from host via Makefile):
    make clean-thehive
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Load .env.full for credentials
from dotenv import load_dotenv

_env_full = Path("/app/.env.full") if Path("/app/.env.full").exists() else Path(
    __file__
).resolve().parent.parent.parent / ".env.full"
if _env_full.exists():
    load_dotenv(str(_env_full), override=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old TheHive cases")
    parser.add_argument(
        "--keep",
        type=int,
        default=0,
        help="Number of most recent cases to keep (default: 0 = delete all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List cases that would be deleted without actually deleting them",
    )
    args = parser.parse_args()

    from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient

    thehive_url = os.environ.get("THEHIVE_URL", "http://thehive:9000")
    thehive_key = os.environ.get("THEHIVE_API_KEY", "")

    if not thehive_key:
        print("ERROR: THEHIVE_API_KEY not set in environment")
        return 1

    client = TheHiveClient(
        base_url=thehive_url,
        api_key=thehive_key,
        verify_ssl=False,
    )

    try:
        cases = client.search_cases(range_="0-1000")
    except Exception as exc:
        print(f"ERROR: Failed to list TheHive cases: {exc}")
        return 1

    if not cases:
        print("No TheHive cases found — nothing to clean.")
        return 0

    print(f"Found {len(cases)} TheHive case(s).")

    # Sort by caseId (numeric, ascending) so we can keep the most recent
    def _case_id(c: dict) -> int:
        try:
            return int(c.get("caseId", 0))
        except (ValueError, TypeError):
            return 0

    cases.sort(key=_case_id)

    if args.keep > 0 and len(cases) > args.keep:
        to_delete = cases[: -args.keep]
        print(f"Keeping {args.keep} most recent case(s), deleting {len(to_delete)}.")
    else:
        to_delete = cases
        print(f"Deleting all {len(to_delete)} case(s).")

    if args.dry_run:
        for c in to_delete:
            cid = c.get("id", c.get("_id", "?"))
            title = c.get("title", "?")
            print(f"  [DRY-RUN] Would delete case #{_case_id(c)} (id={cid}): {title}")
        return 0

    deleted = 0
    failed = 0
    for c in to_delete:
        cid = c.get("id", c.get("_id", ""))
        if not cid:
            continue
        try:
            client.delete_case(cid)
            deleted += 1
            # Small delay to avoid overwhelming TheHive's ES
            if deleted % 10 == 0:
                print(f"  ... deleted {deleted}/{len(to_delete)}")
                time.sleep(0.5)
        except Exception as exc:
            print(f"  WARN: Failed to delete case {cid}: {exc}")
            failed += 1

    print(f"Cleanup complete: {deleted} deleted, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
