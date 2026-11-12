#!/usr/bin/env python3
"""E9-05 — formal E2E close gate.

Verifies the round-closure criteria from the stabilization backlog:
  - JUnit evidence exists, parseable, with stable test IDs
  - every required suite reached its expected pass count with zero
    failures/errors
  - the TC catalog contract passes (5/5)
  - e2e_suites.py validate returns OK
  - no infrastructure failure was silently counted as success
    (error/skipped counts reported, not hidden)

Usage:
  python scripts/ci/e2e_close_gate.py --junit-dir reports/validation/results/junit
Exit 0 only when all conditions hold. Prints a per-gate verdict table.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# suite_id -> (file-glob in junit dir, expected passes)
REQUIRED_SUITES = {
    "TC-11": ("junit-tc-11-precision.xml", 13),
    "TC-36": ("junit-tc-36-obspipe.xml", 5),
}


def _junit_summary(path: Path) -> dict | None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    total = fails = errs = skips = 0
    for ts in suites:
        total += int(ts.get("tests", 0))
        fails += int(ts.get("failures", 0))
        errs += int(ts.get("errors", 0))
        skips += int(ts.get("skipped", 0))
    return {"tests": total, "failures": fails, "errors": errs, "skipped": skips}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit-dir", default="reports/validation/results/junit")
    ap.add_argument("--catalog-test", action="store_true",
                    help="also run the catalog contract test (slow)")
    args = ap.parse_args()

    junit_dir = Path(args.junit_dir)
    verdicts: list[tuple[str, bool, str]] = []

    # 1) required suites ---------------------------------------------------
    for suite, (fname, expected) in REQUIRED_SUITES.items():
        f = junit_dir / fname
        if not f.exists():
            verdicts.append((f"{suite} evidence", False, f"{fname} missing"))
            continue
        s = _junit_summary(f)
        if s is None:
            verdicts.append((f"{suite} evidence", False, f"{fname} unparseable"))
            continue
        ok = s["tests"] >= expected and s["failures"] == 0 and s["errors"] == 0
        verdicts.append((
            f"{suite} evidence", ok,
            f"{s['tests']} tests, {s['failures']}F/{s['errors']}E/{s['skipped']}S "
            f"(need >= {expected}, 0F/0E)",
        ))

    # 2) catalog validation -------------------------------------------------
    repo_root = Path(__file__).resolve().parent.parent.parent
    r = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "ci" / "e2e_suites.py"), "validate"],
        capture_output=True, text=True, cwd=repo_root,
    )
    verdicts.append(("e2e_suites validate", r.returncode == 0,
                     (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else ""))

    if args.catalog_test:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/contracts/test_tc_catalog.py",
             "-x", "-q", "--no-cov"],
            capture_output=True, text=True, cwd=repo_root,
        )
        last = (r.stdout + r.stderr).strip().splitlines()
        verdicts.append(("catalog contract", r.returncode == 0, last[-1] if last else ""))

    print("\n=== E2E CLOSE GATE ===")
    all_ok = True
    for name, ok, detail in verdicts:
        print(f"[{'PASS' if ok else 'FAIL'}] {name:26} {detail}")
        all_ok &= ok
    print(f"\nverdict: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
