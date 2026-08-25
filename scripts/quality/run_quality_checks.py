#!/usr/bin/env python3
"""Run all quality checks and generate reports.

Usage:
    python scripts/quality/run_quality_checks.py                    # run all checks
    python scripts/quality/run_quality_checks.py --file src/foo.py  # analyze single file
    python scripts/quality/run_quality_checks.py --only complexity  # run one category
    python scripts/quality/run_quality_checks.py --only security
    python scripts/quality/run_quality_checks.py --only coverage
    python scripts/quality/run_quality_checks.py --only typing
    python scripts/quality/run_quality_checks.py --report-only       # skip slow checks

Categories: complexity, maintainability, halstead, raw, coverage,
            linting, pylint, typing, documentation, dead_code, security,
            dependency_audit, architecture, score

Note: Mutation testing (mutmut) is NOT run here. Use `make mutation` on-demand.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure scripts/quality/ is importable (parse_*.py, generate_report.py, etc.)
SCRIPTS_QUALITY_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_QUALITY_DIR))

from calculate_quality_score import calculate
from generate_report import generate_json, generate_markdown
from parse_bandit import parse as parse_bandit
from parse_coverage import parse as parse_coverage
from parse_pylint import parse as parse_pylint
from parse_radon import (
    get_complexity_summary,
    get_maintainability_summary,
    parse_halstead,
    parse_raw,
)
from parse_ruff import parse as parse_ruff
from parse_vulture import parse as parse_vulture

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent / "reports" / "quality"


def run_mypy(path: str = "src/") -> dict:
    """Run mypy and return structured results."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", path, "--report", "json", "--no-color"],
        capture_output=True,
        text=True,
    )
    # mypy JSON report is written to a file, parse stderr for summary
    error_count = 0
    for line in result.stdout.splitlines():
        if "error:" in line.lower():
            error_count += 1
    return {
        "error_count": error_count,
        "exit_code": result.returncode,
        "output": result.stdout[:2000] if result.stdout else "",
    }


def run_interrogate(path: str = "src/") -> dict:
    """Run interrogate for docstring coverage."""
    result = subprocess.run(
        [sys.executable, "-m", "interrogate", "-v", path],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    # Parse coverage percentage from the RESULT line:
    #   "RESULT: PASSED (minimum: 80.0%, actual: 85.0%)"
    coverage = 0.0
    import re

    match = re.search(r"actual:\s*([\d.]+)%", output)
    if match:
        try:
            coverage = float(match.group(1))
        except ValueError:
            pass
    # Parse covered/total from the TOTAL row:
    #   "| TOTAL | 1018 | 54 | 964 | 94.7% |"
    total = 0
    covered = 0
    total_match = re.search(r"\|\s*TOTAL\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", output)
    if total_match:
        total = int(total_match.group(1))
        covered = int(total_match.group(2))
    return {
        "coverage_percent": round(coverage, 2),
        "covered": covered,
        "total": total,
        "exit_code": result.returncode,
        "output": output[:1000],
    }


def run_pip_audit() -> dict:
    """Run pip-audit for dependency vulnerabilities."""
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--format", "json"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"error": "Failed to parse pip-audit output", "raw": result.stdout[:500]}
    deps = data.get("dependencies", [])
    vulnerabilities = []
    for dep in deps:
        for vuln in dep.get("vulns", []):
            vulnerabilities.append(
                {
                    "package": dep.get("name", "?"),
                    "version": dep.get("version", "?"),
                    "id": vuln.get("id", "?"),
                    "description": vuln.get("description", "")[:200],
                    "fix_versions": vuln.get("fix_versions", []),
                }
            )
    return {
        "total_vulnerabilities": len(vulnerabilities),
        "vulnerabilities": vulnerabilities[:50],
    }


def run_import_linter() -> dict:
    """Run import-linter for architecture rules."""
    try:
        import click.testing
        from importlinter.cli import lint_imports_command

        runner = click.testing.CliRunner()
        result = runner.invoke(lint_imports_command, ["--ci"])
        output = result.output
        exit_code = result.exit_code
    except Exception:
        # Fallback: try console scripts
        for cmd in (["lint-imports", "--ci"], [sys.executable, "-m", "lint_imports", "--ci"]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True)
                output = r.stdout + r.stderr
                exit_code = r.returncode
                break
            except FileNotFoundError:
                continue
        else:
            return {
                "violation_count": 0,
                "exit_code": 0,
                "output": "import-linter not available",
            }
    if "no contracts" in output.lower() or "config" in output.lower():
        return {
            "violation_count": 0,
            "exit_code": 0,
            "output": "import-linter not configured — no contracts defined",
        }
    violations = 0
    if exit_code != 0:
        for line in output.splitlines():
            if "Contracts" in line and "broken" in line.lower():
                violations += 1
    return {
        "violation_count": violations,
        "exit_code": exit_code,
        "output": output[:2000],
    }


def run_detect_secrets() -> dict:
    """Run detect-secrets scan."""
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "src/"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"error": "Failed to parse detect-secrets output"}
    results = data.get("results", {})
    total = sum(len(v) for v in results.values())
    return {
        "total_secrets": total,
        "files_with_secrets": list(results.keys())[:20],
    }


# Map category names to check functions
CHECKS = {
    "complexity": lambda path: get_complexity_summary(path),
    "maintainability": lambda path: get_maintainability_summary(path),
    "halstead": lambda path: parse_halstead(path),
    "raw": lambda path: parse_raw(path),
    "coverage": lambda _: parse_coverage(),
    "linting": lambda path: parse_ruff(path),
    "pylint": lambda path: parse_pylint(path),
    "typing": lambda path: run_mypy(path),
    "documentation": lambda path: run_interrogate(path),
    "dead_code": lambda path: parse_vulture(path),
    "security": lambda path: parse_bandit(path),
    "dependency_audit": lambda _: run_pip_audit(),
    "architecture": lambda _: run_import_linter(),
    "secrets": lambda _: run_detect_secrets(),
}

# Slow checks that can be skipped with --report-only
# Note: mutation (mutmut) is NOT included here — use `make mutation` on-demand.
# coverage is NOT slow — it just parses a pre-generated XML file.
SLOW_CHECKS = {"pylint", "typing"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run quality checks for SOAR Ransomware Lab")
    parser.add_argument("--file", default="src/", help="Path to analyze (default: src/)")
    parser.add_argument(
        "--only",
        choices=list(CHECKS.keys()) + ["score", "all"],
        default="all",
        help="Run only one category of checks",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip slow checks (pylint, mypy, coverage)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPORTS_DIR),
        help="Directory for reports (default: reports/quality/)",
    )
    args = parser.parse_args()

    path = args.file
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SOAR Ransomware Lab — Quality Checks")
    print(f"Path: {path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    metrics: dict = {"_path": path}
    categories_to_run = [args.only] if args.only != "all" else list(CHECKS.keys())

    for category in categories_to_run:
        if category == "score":
            continue
        if args.report_only and category in SLOW_CHECKS:
            logger.info(f"\n[SKIP] {category} (slow check, --report-only)")
            continue
        logger.info(f"\n[RUN] {category}...")
        try:
            result = CHECKS[category](path)
            metrics[category] = result
            if "error" in result:
                logger.error(f"  ERROR: {result['error']}")
            else:
                # Print summary
                if category == "complexity":
                    print(
                        f"  Blocks: {result.get('total_blocks', 0)}, "
                        f"Avg: {result.get('average_complexity', 0)}, "
                        f"Max: {result.get('max_complexity', 0)}"
                    )
                    print(f"  Grades: {result.get('grade_distribution', {})}")
                elif category == "maintainability":
                    print(
                        f"  Files: {result.get('total_files', 0)}, "
                        f"Avg MI: {result.get('average_mi', 0)}"
                    )
                elif category == "linting":
                    print(f"  Errors: {result.get('total_errors', 0)}")
                elif category == "security":
                    print(
                        f"  Issues: {result.get('total_issues', 0)}, "
                        f"By severity: {result.get('by_severity', {})}"
                    )
                elif category == "dead_code":
                    print(f"  Items: {result.get('total_items', 0)}")
                elif category == "documentation":
                    print(f"  Coverage: {result.get('coverage_percent', 0)}%")
                elif category == "typing":
                    print(f"  Errors: {result.get('error_count', 0)}")
                elif category == "coverage":
                    if "error" not in result:
                        print(
                            f"  Line: {result.get('global_line_coverage', 0)}%, "
                            f"Branch: {result.get('global_branch_coverage', 0)}%"
                        )
                elif category == "dependency_audit":
                    print(f"  Vulnerabilities: {result.get('total_vulnerabilities', 0)}")
                elif category == "architecture":
                    print(f"  Violations: {result.get('violation_count', 0)}")
                elif category == "secrets":
                    print(f"  Secrets found: {result.get('total_secrets', 0)}")
        except Exception as exc:
            logger.error(f"  FAILED: {exc}")
            metrics[category] = {"error": str(exc)}

    # Calculate score
    print("\n" + "=" * 70)
    logger.info("[RUN] Calculating quality score...")
    score = calculate(metrics)
    metrics["score"] = score
    print(f"  Score: {score['score']}/100 — {score['classification']}")
    print(f"  Category scores: {score['category_scores']}")

    # Generate reports
    logger.info("\n[RUN] Generating reports...")
    json_path = output_dir / "quality-summary.json"
    md_path = output_dir / "quality-summary.md"
    generate_json(metrics, str(json_path))
    generate_markdown(metrics, str(md_path))
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    # Save individual reports
    for category in ("complexity", "maintainability"):
        if category in metrics and "error" not in metrics[category]:
            cat_path = output_dir / f"{category}-report.json"
            with open(cat_path, "w", encoding="utf-8") as f:
                json.dump(metrics[category], f, indent=2, ensure_ascii=False)
            print(f"  {category}: {cat_path}")

    if "security" in metrics and "error" not in metrics["security"]:
        sec_path = output_dir / "security-report.json"
        with open(sec_path, "w", encoding="utf-8") as f:
            json.dump(metrics["security"], f, indent=2, ensure_ascii=False)
        print(f"  security: {sec_path}")

    if "dependency_audit" in metrics and "error" not in metrics["dependency_audit"]:
        dep_path = output_dir / "dependency-audit.json"
        with open(dep_path, "w", encoding="utf-8") as f:
            json.dump(metrics["dependency_audit"], f, indent=2, ensure_ascii=False)
        print(f"  dependency-audit: {dep_path}")

    if "architecture" in metrics:
        arch_path = output_dir / "architecture-report.json"
        with open(arch_path, "w", encoding="utf-8") as f:
            json.dump(metrics["architecture"], f, indent=2, ensure_ascii=False)
        print(f"  architecture: {arch_path}")

    print("\n" + "=" * 70)
    print(f"Done. Score: {score['score']}/100 — {score['classification']}")
    print("=" * 70)

    # Exit code: 0 if score >= 70, 1 otherwise
    return 0 if score["score"] >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
