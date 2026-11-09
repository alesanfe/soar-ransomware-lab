#!/usr/bin/env python3
"""Unified test-suite summary generator (SOAR-009).

Runs each suite with ``--junitxml`` inside the ``soar_api`` container and
aggregates a consolidated report (Markdown + JSON) under
``reports/test-summary/``. Distinguishes unit / atomic / architecture /
integration / security / contracts / e2e / external suites, counts
passed-failed-skipped-deselected per suite, and records durations.

Usage (host):

    python scripts/reports/test_summary.py              # all local suites
    python scripts/reports/test_summary.py --suite unit # one suite
    python scripts/reports/test_summary.py --from-junit reports/test-summary/junit
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "reports" / "test-summary"
CONTAINER = "soar_api"

# name -> (pytest path inside the container, extra pytest argv)
SUITES: dict[str, tuple[str, tuple[str, ...]]] = {
    "unit": ("tests/unit", ("--no-cov",)),
    "atomic": ("tests/atomic", ("--no-cov",)),
    "architecture": ("tests/architecture", ("--no-cov",)),
    "integration": (
        "tests/integration",
        ("-m", "not requires_external and not requires_docker", "--no-cov"),
    ),
    "security": ("tests/security", ("--no-cov",)),
    "contracts": ("tests/contracts", ("--no-cov",)),
    "external": (
        "tests/integration",
        ("-m", "requires_external or requires_docker", "--no-cov"),
    ),
}


def _run_suite(name: str, junit_dir: Path) -> dict:
    path, extra = SUITES[name]
    xml_name = f"junit-{name}.xml"
    # argv list (no shell): a shell string splits the -m expression on
    # Windows cmd.exe and pytest reads "requires_external" as a file path
    cmd = [
        "docker", "exec", CONTAINER, "python3", "-m", "pytest", path,
        *extra, f"--junitxml=/tmp/{xml_name}", "-q",
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - t0
    subprocess.run(
        ["docker", "cp", f"{CONTAINER}:/tmp/{xml_name}", str(junit_dir / xml_name)],
        capture_output=True,
    )
    result = _parse_junit(junit_dir / xml_name)
    result.update(
        suite=name,
        duration_s=round(duration, 1),
        exit_code=proc.returncode,
        tail="\n".join(proc.stdout.splitlines()[-5:]),
    )
    return result


def _parse_junit(path: Path) -> dict:
    if not path.exists():
        return dict(tests=0, passed=0, failed=0, skipped=0, errors=0)
    root = ET.parse(path).getroot()
    tests = failures = skipped = errors = 0
    for suite in root.iter("testsuite"):
        tests += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        skipped += int(suite.get("skipped", 0))
        errors += int(suite.get("errors", 0))
    return dict(
        tests=tests,
        passed=tests - failures - skipped - errors,
        failed=failures,
        skipped=skipped,
        errors=errors,
    )


def _write_reports(results: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Test summary",
        "",
        "| Suite | Tests | Passed | Failed | Skipped | Errors | Duration (s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['suite']} | {r['tests']} | {r['passed']} | {r['failed']} "
            f"| {r['skipped']} | {r['errors']} | {r.get('duration_s', '-')} |"
        )
    total = {
        k: sum(r[k] for r in results) for k in ("tests", "passed", "failed", "skipped", "errors")
    }
    lines.append(
        f"| **TOTAL** | **{total['tests']}** | **{total['passed']}** "
        f"| **{total['failed']}** | **{total['skipped']}** | **{total['errors']}** | "
        f"**{sum(r.get('duration_s', 0) for r in results):.0f}** |"
    )
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=list(SUITES), help="run one suite")
    parser.add_argument(
        "--from-junit",
        type=Path,
        help="skip execution and aggregate existing junit-*.xml files",
    )
    args = parser.parse_args()

    junit_dir = OUT_DIR / "junit"
    junit_dir.mkdir(parents=True, exist_ok=True)

    if args.from_junit:
        results = []
        for name in SUITES:
            xml = Path(args.from_junit) / f"junit-{name}.xml"
            if xml.exists():
                r = _parse_junit(xml)
                r["suite"] = name
                results.append(r)
    else:
        names = [args.suite] if args.suite else list(SUITES)
        results = [_run_suite(name, junit_dir) for name in names]

    _write_reports(results)
    for r in results:
        status = "PASS" if r["failed"] == 0 and r["errors"] == 0 else "FAIL"
        print(
            f"{status}  {r['suite']:<14} {r['passed']}/{r['tests']} passed, "
            f"{r['skipped']} skipped ({r.get('duration_s', '?')}s)"
        )
    failed = sum(r["failed"] + r["errors"] for r in results)
    print(f"\nReport: {OUT_DIR / 'summary.md'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
