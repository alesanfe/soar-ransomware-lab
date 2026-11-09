#!/usr/bin/env python3
"""Test-suite performance report — aggregates per-test phase durations
recorded by ``tests/perf_recorder.py`` into a bottleneck ranking.

Reads one or more ``test-durations-*.json`` files (pytest phase reports:
setup/call/teardown per test) and produces:

- ``tests``: per-test total duration + phase breakdown + outcome.
- ``phase_totals``: aggregate share of wall time per phase — reveals whether
  the suite is dominated by test logic (``call``) or by fixture/setup
  overhead (``setup``+``teardown``).
- ``suites``: totals grouped by directory (``unit``, ``e2e/TC-04``…).
- ``findings``: machine-readable bottleneck rules (see ``detect_findings``).

Usage::

    python scripts/perf/test_perf_report.py reports/perf/test-durations-*.json
    python scripts/perf/test_perf_report.py --top 15 --json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# -- thresholds (seconds / shares) ------------------------------------------
SLOW_TEST_S = 60.0  # one test slower than this is noteworthy
DOMINANT_TEST_SHARE = 0.30  # one test >30% of suite time
SETUP_OVERHEAD_SHARE = 0.40  # setup+teardown >40% of total -> fixture-bound suite
FAILED_SLOW_S = 30.0  # a failed test that also burned >30s wasted real time


def _pct(sorted_vals: list[float], q: float) -> float:
    return sorted_vals[min(int(q * len(sorted_vals)), len(sorted_vals) - 1)]


def load_records(paths: list[str]) -> list[dict[str, Any]]:
    """Merge ``records`` lists from one or more report files."""
    records: list[dict[str, Any]] = []
    for p in paths:
        data = json.loads(Path(p).read_text())
        records.extend(data.get("records", data if isinstance(data, list) else []))
    return records


def _suite_of(nodeid: str) -> str:
    parts = nodeid.replace("\\", "/").split("/")
    # e.g. tests/e2e/TC-04/test_x.py::Test::test -> "e2e/TC-04"
    if "e2e" in parts:
        i = parts.index("e2e")
        return "/".join(parts[i : i + 2]) if len(parts) > i + 1 else "e2e"
    for i, part in enumerate(parts):
        if part in (
            "unit",
            "integration",
            "atomic",
            "contracts",
            "security",
            "architecture",
            "performance",
            "quality",
            "baseline",
        ):
            return part
    return parts[-2] if len(parts) > 1 else "root"


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Group phase records into per-test and per-suite stats."""
    tests: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"setup_s": 0.0, "call_s": 0.0, "teardown_s": 0.0, "outcome": "passed"}
    )
    for r in records:
        t = tests[r["nodeid"]]
        t[f"{r['phase']}_s"] = t.get(f"{r['phase']}_s", 0.0) + r["duration_s"]
        if r["outcome"] in ("failed", "error"):
            t["outcome"] = r["outcome"]
    for t in tests.values():
        t["total_s"] = round(t["setup_s"] + t["call_s"] + t["teardown_s"], 3)

    suites: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"tests": 0, "total_s": 0.0, "setup_s": 0.0, "call_s": 0.0, "teardown_s": 0.0}
    )
    for nodeid, t in tests.items():
        s = suites[_suite_of(nodeid)]
        s["tests"] += 1
        for k in ("total_s", "setup_s", "call_s", "teardown_s"):
            s[k] += t[k]

    total_s = sum(t["total_s"] for t in tests.values())
    phase_totals = {
        ph: round(sum(t[f"{ph}_s"] for t in tests.values()), 3)
        for ph in ("setup", "call", "teardown")
    }
    durations = sorted(t["total_s"] for t in tests.values()) or [0.0]
    return {
        "test_count": len(tests),
        "total_s": round(total_s, 3),
        "p50_s": round(_pct(durations, 0.50), 3),
        "p95_s": round(_pct(durations, 0.95), 3),
        "max_s": round(durations[-1], 3),
        "phase_totals_s": phase_totals,
        "phase_share": {
            k: round(v / total_s, 3) if total_s else 0.0 for k, v in phase_totals.items()
        },
        "tests": dict(sorted(tests.items(), key=lambda kv: kv[1]["total_s"], reverse=True)),
        "suites": dict(sorted(suites.items(), key=lambda kv: kv[1]["total_s"], reverse=True)),
    }


def detect_findings(report: dict[str, Any]) -> list[dict[str, str]]:
    """Machine-readable bottleneck rules over the aggregated report."""
    findings: list[dict[str, str]] = []
    total = report["total_s"] or 1.0

    enough_tests = report["test_count"] >= 5
    for nodeid, t in report["tests"].items():
        share = t["total_s"] / total
        if enough_tests and share >= DOMINANT_TEST_SHARE:
            findings.append(
                {
                    "rule": "dominant_test",
                    "severity": "warning",
                    "test": nodeid,
                    "detail": f"{t['total_s']:.1f}s = {share:.0%} of suite",
                }
            )
        elif t["total_s"] >= SLOW_TEST_S:
            findings.append(
                {
                    "rule": "slow_test",
                    "severity": "info",
                    "test": nodeid,
                    "detail": f"{t['total_s']:.1f}s (setup {t['setup_s']:.1f} / "
                    f"call {t['call_s']:.1f} / teardown {t['teardown_s']:.1f})",
                }
            )
        if t["outcome"] in ("failed", "error") and t["total_s"] >= FAILED_SLOW_S:
            findings.append(
                {
                    "rule": "slow_failure",
                    "severity": "warning",
                    "test": nodeid,
                    "detail": f"failed after {t['total_s']:.1f}s — likely a "
                    "timeout-polling loop; shorten waits or fail fast",
                }
            )

    overhead = report["phase_totals_s"]["setup"] + report["phase_totals_s"]["teardown"]
    if overhead / total >= SETUP_OVERHEAD_SHARE:
        findings.append(
            {
                "rule": "fixture_overhead",
                "severity": "warning",
                "test": "(suite)",
                "detail": f"setup+teardown = {overhead / total:.0%} of wall time — "
                "fixtures are the bottleneck, not test logic",
            }
        )
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "paths",
        nargs="*",
        default=["reports/perf/test-durations-*.json"],
        help="duration JSON files or globs (default: latest in reports/perf)",
    )
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true", help="print full JSON")
    ap.add_argument("--out", default=None, help="write JSON report to path")
    args = ap.parse_args()

    paths: list[str] = []
    for p in args.paths:
        paths.extend(sorted(glob.glob(p)) or ([p] if Path(p).exists() else []))
    if not paths:
        print("No duration reports found — run pytest first.", file=sys.stderr)
        return 2
    # keep only the newest per default glob run
    report = aggregate(load_records(paths))
    report["findings"] = detect_findings(report)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n")

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(
        f"tests={report['test_count']} total={report['total_s']:.1f}s "
        f"p50={report['p50_s']:.2f}s p95={report['p95_s']:.1f}s "
        f"max={report['max_s']:.1f}s"
    )
    print("phase share: " + " ".join(f"{k}={v:.0%}" for k, v in report["phase_share"].items()))
    print(f"\nTop {args.top} slowest tests:")
    for i, (nodeid, t) in enumerate(report["tests"].items()):
        if i >= args.top:
            break
        mark = " *FAIL*" if t["outcome"] != "passed" else ""
        print(
            f"  {t['total_s']:8.1f}s  {nodeid}  "
            f"(s={t['setup_s']:.1f} c={t['call_s']:.1f} t={t['teardown_s']:.1f}){mark}"
        )
    if report["findings"]:
        print("\nFindings:")
        for f in report["findings"]:
            print(f"  [{f['severity']:>7}] {f['rule']}: {f['test']}\n          {f['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
