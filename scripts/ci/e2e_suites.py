#!/usr/bin/env python3
"""Discover, validate and run E2E suites in deterministic order."""

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

E2E_DIR = Path("tests/e2e")
MAKEFILE = Path("Makefile.win")


def discover_suites():
    suites = []
    if not E2E_DIR.is_dir():
        return suites
    for d in sorted(E2E_DIR.iterdir()):
        if d.is_dir() and re.match(r"^TC-((KPI-)?\d+)$", d.name):
            suites.append(d.name)
    return suites


def suite_to_target(suite):
    if suite.startswith("TC-KPI-"):
        return f"test-e2e-kpi{suite.split(chr(45))[-1].zfill(2)}"
    return f"test-e2e-tc{suite.split(chr(45))[-1].zfill(2)}"


def cmd_list(_args):
    suites = discover_suites()
    print(f"{'#':<5} {'Suite':<12} {'Target':<24} {'Files'}")
    for i, s in enumerate(suites, 1):
        target = suite_to_target(s)
        files = sorted(p.name for p in (E2E_DIR / s).glob("test_*.py"))
        print(f"{i:<5} {s:<12} {target:<24} {', '.join(files)}")
    print(f"\nTotal suites: {len(suites)}")


def cmd_validate(_args):
    suites = discover_suites()
    makefile_text = MAKEFILE.read_text(encoding="utf-8")
    targets = set(re.findall(r"^(test-e2e[-a-z0-9]+):", makefile_text, re.MULTILINE))
    expected = {suite_to_target(s) for s in suites}
    errors = 0

    missing = expected - targets
    if missing:
        errors += 1
        logger.error(f"ERROR: Missing targets: {sorted(missing)}")

    extra = (
        targets
        - expected
        - {
            "test-e2e",
            "test-e2e-list",
            "test-e2e-validate-targets",
            "test-e2e-report",
            "test-e2e-kpi",
            "test-e2e-new-features",
            "test-e2e-tc01-full-workflow",
            "test-e2e-tc01-ioc",
            "test-performance",
        }
    )
    if extra:
        errors += 1
        logger.error(f"ERROR: Targets not matching any suite: {sorted(extra)}")

    target_to_suite = {suite_to_target(s): s for s in suites}
    for t in expected:
        suite = target_to_suite[t]
        if not (E2E_DIR / suite).is_dir():
            errors += 1
            logger.error(f"ERROR: Target {t} points to missing dir tests/e2e/{suite}")

    order = [suite_to_target(s) for s in suites]
    kpi_seen = False
    for t in order:
        if "kpi" in t:
            kpi_seen = True
        elif kpi_seen:
            errors += 1
            logger.error(f"ERROR: Non-KPI target {t} appears after KPI targets")
            break

    if not re.search(r"^test-performance:\s*test-e2e-tc04", makefile_text, re.MULTILINE):
        errors += 1
        logger.error("ERROR: test-performance does not point to test-e2e-tc04")

    if errors:
        print(f"\nValidation FAILED: {errors} issue(s)")
        sys.exit(1)
    print("Validation OK")


def _prepare_suites():
    suites = discover_suites()
    start = int(os.environ.get("E2E_SUITE_START", "0"))
    if start:
        logger.info(f"Skipping first {start} suite(s); starting from {suites[start]}")
        suites = suites[start:]
    return suites


def _run_suite(make_cmd, target, s):
    logger.info(f"\n=== Running {target} ({s}) ===")
    env = os.environ.copy()
    # The top-level test-e2e target already ran sync-src once.
    env["E2E_SYNC"] = ""
    return subprocess.run([make_cmd, target], env=env)


def cmd_run(_args):
    """Run suites sequentially and stop on the first failure."""
    suites = _prepare_suites()
    make_cmd = os.environ.get("MAKE", "make")
    for s in suites:
        target = suite_to_target(s)
        result = _run_suite(make_cmd, target, s)
        if result.returncode != 0:
            logger.error(f"\nSuite {target} FAILED")
            sys.exit(1)
    print("\nAll suites passed")


def cmd_report(_args):
    """Run all suites and report every failure at the end."""
    suites = _prepare_suites()
    make_cmd = os.environ.get("MAKE", "make")
    failed = []
    for s in suites:
        target = suite_to_target(s)
        result = _run_suite(make_cmd, target, s)
        if result.returncode != 0:
            logger.error(f"\nSuite {target} FAILED")
            failed.append(target)
    if failed:
        print(f"\n{len(failed)} suite(s) failed: {', '.join(failed)}")
        sys.exit(1)
    print("\nAll suites passed")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("validate")
    sub.add_parser("run")
    sub.add_parser("report")
    args = parser.parse_args()
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
