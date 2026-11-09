#!/usr/bin/env python3
"""Flaky-test tracker (T5).

Reads one or more pytest JUnit XML reports (from repeated runs —
``pytest --junitxml=run1.xml``, ``pytest --junitxml=run2.xml`` ...) and
flags:

- **flip-flop tests**: failed in ≥1 run and passed in ≥1 run — the
  definition of flaky.
- **slow drift**: tests whose duration grew >2× between runs.

Usage::

    python scripts/ci/flaky_report.py reports/junit/run*.xml
    python scripts/ci/flaky_report.py --json reports/junit/*.xml

Exit 1 when at least one flip-flop is found (gate-able).
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def _parse(path: Path) -> dict[str, tuple[str, float]]:
    """name -> (status, duration)."""
    out: dict[str, tuple[str, float]] = {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return out
    for case in root.iter("testcase"):
        name = f"{case.get('classname')}::{case.get('name')}"
        status = "passed"
        for tag in ("failure", "error", "skipped"):
            if case.find(tag) is not None:
                status = tag
                break
        out[name] = (status, float(case.get("time") or 0))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", help="JUnit XML paths/globs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths: list[Path] = []
    for pattern in args.reports:
        paths.extend(Path(p) for p in glob.glob(pattern))
    if len(paths) < 2:
        print("Need ≥2 JUnit reports to compare — run pytest twice.")
        return 1

    runs = [_parse(p) for p in paths]
    all_tests: dict[str, list[str]] = defaultdict(list)
    durations: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        for name, (status, dur) in run.items():
            all_tests[name].append(status)
            durations[name].append(dur)

    flip_flops = sorted(
        name
        for name, statuses in all_tests.items()
        if "passed" in statuses
        and any(s in ("failure", "error") for s in statuses)
    )
    drifters = sorted(
        name
        for name, ds in durations.items()
        if len(ds) >= 2 and min(ds) > 0.05 and max(ds) > 2 * min(ds)
    )

    if args.json:
        print(json.dumps({"flip_flops": flip_flops, "slow_drift": drifters},
                         indent=2))
    else:
        print(f"Compared {len(paths)} runs over {len(all_tests)} tests")
        print(f"Flip-flop (flaky): {len(flip_flops)}")
        for n in flip_flops:
            print(f"  FLAKY {n}  statuses={all_tests[n]}")
        print(f"Slow drift (>2x):  {len(drifters)}")
        for n in drifters[:20]:
            print(f"  DRIFT {n}  times={durations[n]}")
    return 1 if flip_flops else 0


if __name__ == "__main__":
    sys.exit(main())
