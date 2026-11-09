#!/usr/bin/env python3
"""Dependency freshness gate (SC5 — minimum release age).

For every requirement declared in ``pyproject.toml``, resolves the newest
PyPI version inside the allowed specifier and fails if that version is
younger than ``--min-age-days``. This reproduces the "minimumReleaseAge"
guard that npm/pnpm provide natively, which pip lacks.

Rationale: a non-trivial share of supply-chain attacks are caught and
yanked within the first few days of a release. Auto-resolving to a
release published hours ago means CI can pull an unvetted artifact.

Usage::

    python scripts/ci/check_dep_freshness.py [--min-age-days 7] [--report-only]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests
from packaging.requirements import Requirement
from packaging.version import Version

PYPI_JSON = "https://pypi.org/pypi/{name}/json"


def _iter_requirements(pyproject: Path, extras: list[str]) -> list[Requirement]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data["project"]
    specs = list(project.get("dependencies", []))
    for extra in extras:
        specs += project.get("optional-dependencies", {}).get(extra, [])
    reqs: list[Requirement] = []
    for spec in specs:
        try:
            reqs.append(Requirement(spec))
        except Exception:
            continue
    return reqs


def _newest_release(req: Requirement) -> tuple[Version, datetime] | None:
    resp = requests.get(PYPI_JSON.format(name=req.name), timeout=15)
    if resp.status_code != 200:
        return None
    releases = resp.json().get("releases", {})
    best: tuple[Version, datetime] | None = None
    for ver_str, files in releases.items():
        if not files:
            continue
        try:
            ver = Version(ver_str)
        except Exception:
            continue
        if ver.is_prerelease or not req.specifier.contains(ver_str, prereleases=False):
            continue
        upload = min(f["upload_time_iso_8601"] for f in files)
        ts = datetime.fromisoformat(upload.replace("Z", "+00:00"))
        if best is None or ver > best[0]:
            best = (ver, ts)
    return best


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-age-days", type=int, default=7)
    parser.add_argument("--extras", nargs="*", default=["dev", "test", "quality"])
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()

    cutoff = datetime.now(UTC) - timedelta(days=args.min_age_days)
    fresh: list[str] = []
    checked = 0
    for req in _iter_requirements(args.pyproject, args.extras):
        best = _newest_release(req)
        checked += 1
        if best is None:
            print(f"SKIP  {req.name}: no matching release on PyPI")
            continue
        ver, ts = best
        if ts > cutoff:
            fresh.append(f"{req.name}=={ver} released {ts.date()} "
                         f"(< {args.min_age_days}d old)")
            print(f"FRESH {req.name}=={ver} uploaded {ts.date()}")
    print(f"\nChecked {checked} requirements; {len(fresh)} resolve to a "
          f"release younger than {args.min_age_days} days.")
    if fresh and not args.report_only:
        print("\nFresh releases that CI would auto-resolve — review or pin:")
        for item in fresh:
            print(f"  - {item}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
