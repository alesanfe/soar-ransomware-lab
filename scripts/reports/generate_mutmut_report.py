#!/usr/bin/env python3
"""Generate a comprehensive mutation testing report (Markdown) from mutmut
output.

This script runs INSIDE the Docker container (soar_api) where mutmut is supported
(Linux fork-based multiprocessing). It:

1. Runs `mutmut run` (or reuses cached results)
2. Runs `mutmut results` to get summary stats
3. Runs `mutmut show all` to get diffs for surviving mutants
4. Parses `mutmut export-cicd-stats` for machine-readable data
5. Generates a detailed Markdown report

Usage (inside the container):
    python scripts/reports/generate_mutmut_report.py [--output-dir reports/mutmut] [--skip-run]

Usage (from host via Makefile):
    make mutation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Helpers ──────────────────────────────────────────────────────────────────


def run_cmd(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as exc:
        return 1, "", str(exc)


def parse_results_summary(stdout: str) -> dict[str, Any]:
    """Parse `mutmut results` output.

    Expected output (mutmut 3.x):
        ⚠️ 0 mutants not seen (need rerun)
        🎉 42 killed mutants
        ⏰ 0 timeout mutants
        🤔 0 suspicious mutants
        🙁 3 survived mutants

    Or plain text:
        killed: 42
        timeout: 0
        suspicious: 0
        survived: 3
        skipped: 0
    """
    stats = {
        "killed": 0,
        "timeout": 0,
        "suspicious": 0,
        "survived": 0,
        "skipped": 0,
        "not_seen": 0,
    }

    # Emoji-based output (mutmut 3.x)
    emoji_map = {
        "🎉": "killed",
        "⏰": "timeout",
        "🤔": "suspicious",
        "🙁": "survived",
        "⚠️": "not_seen",
    }
    for line in stdout.splitlines():
        line_stripped = line.strip()
        for emoji, key in emoji_map.items():
            if emoji in line_stripped:
                # Extract number from line
                match = re.search(r"(\d+)\s+\w+", line_stripped.replace(emoji, "").strip())
                if match:
                    stats[key] = int(match.group(1))
                break
        else:
            # Plain text fallback
            for key in stats:
                pattern = rf"{key}:\s*(\d+)"
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    stats[key] = int(match.group(1))

    total = (
        stats["killed"]
        + stats["timeout"]
        + stats["suspicious"]
        + stats["survived"]
        + stats["skipped"]
    )
    killed_or_timeout = stats["killed"] + stats["timeout"]
    score = (killed_or_timeout / total * 100) if total > 0 else 0
    stats["total"] = total
    stats["mutation_score"] = round(score, 2)
    return stats


def parse_survived_diffs(stdout: str) -> list[dict[str, str]]:
    """Parse `mutmut show all` output to extract surviving mutant diffs.

    Expected output (mutmut 3.x):
        --- src/soar_lab/domain/services/kpi_analyzer.py
        +++ src/soar_lab/domain/services/kpi_analyzer.py
        @@ -135,7 +135,7 @@
        -        if alert_type == "ransomware":
        +        if alert_type != "ransomware":
        ...

    Each block is separated by '---' file headers or blank lines.
    """
    mutants: list[dict[str, str]] = []
    current: dict[str, str] = {}

    lines = stdout.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect file header
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            # Save previous mutant if any
            if current:
                mutants.append(current)
            # Start new mutant
            file_path = line[4:].strip()
            current = {"file": file_path, "diff": line + "\n"}
            i += 2
            # Collect diff lines until next file header or end
            while i < len(lines):
                diff_line = lines[i]
                if (
                    diff_line.startswith("--- ")
                    and i + 1 < len(lines)
                    and lines[i + 1].startswith("+++ ")
                ):
                    break
                current["diff"] += diff_line + "\n"
                i += 1
        else:
            i += 1

    if current:
        mutants.append(current)

    # Extract line numbers and function from diff
    for m in mutants:
        # Try to extract @@ -line,count +line,count @@ context
        match = re.search(r"@@\s+-(\d+),?\d*\s+\+(\d+),?\d*\s+@@", m["diff"])
        if match:
            m["line"] = match.group(1)
        else:
            m["line"] = "?"

        # Extract function name from diff context (after @@)
        match = re.search(r"@@.*@@\s+(.*)", m["diff"])
        if match and match.group(1).strip():
            m["context"] = match.group(1).strip()
        else:
            m["context"] = ""

    return mutants


def parse_cicd_stats(stdout: str) -> dict[str, Any] | None:
    """Parse `mutmut export-cicd-stats` JSON output."""
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def parse_run_output(stdout: str) -> dict[str, Any]:
    """Parse `mutmut run` stdout for progress information.

    Extracts:
    - Baseline test time
    - Total mutants found
    - Final status line
    """
    info: dict[str, Any] = {
        "baseline_time": None,
        "total_mutants_found": None,
        "final_line": "",
    }

    for line in stdout.splitlines():
        # Look for baseline time — mutmut prints it on a separate line
        # like "Running... Done (3.2s)" after "Running tests without mutations"
        time_match = re.search(r"(\d+\.?\d*)\s*s\b", line)
        if time_match and info["baseline_time"] is None:
            # Only capture the first time match (baseline)
            if "done" in line.lower() or "running" in line.lower() or "baseline" in line.lower():
                info["baseline_time"] = float(time_match.group(1))

        # Look for total mutants
        count_match = re.search(
            r"(\d+)\s+mutants?\s+(?:found|generated|checking)", line, re.IGNORECASE
        )
        if count_match:
            info["total_mutants_found"] = int(count_match.group(1))

        # Final status line (contains emoji counts)
        if any(emoji in line for emoji in ["🎉", "⏰", "🤔", "🙁"]):
            info["final_line"] = line.strip()

    return info


# ─── Report generation ────────────────────────────────────────────────────────


def generate_markdown_report(
    stats: dict[str, Any],
    survived_diffs: list[dict[str, str]],
    cicd_stats: dict[str, Any] | None,
    run_info: dict[str, Any],
    output_path: Path,
) -> None:
    """Generate the comprehensive Markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    score = stats["mutation_score"]
    total = stats["total"]
    killed = stats["killed"]
    survived = stats["survived"]
    timeout = stats["timeout"]
    suspicious = stats["suspicious"]
    skipped = stats["skipped"]

    # Determine status
    if score >= 90:
        status = "Excellent"
    elif score >= 80:
        status = "Good"
    elif score >= 70:
        status = "Acceptable"
    elif score >= 60:
        status = "Medium risk"
    elif score >= 50:
        status = "High risk"
    else:
        status = "Critical"

    lines: list[str] = []
    lines.append("# Mutation Testing Report (mutmut)")
    lines.append("")
    lines.append(f"Generated: **{now}**")
    lines.append(
        f"Environment: Docker container `soar_api` ({os.uname().nodename if hasattr(os, 'uname') else 'linux'})"
    )
    lines.append(f"Source mutated: `src/soar_lab/`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── Executive Summary ─────────────────────────────────────────────────────
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| **Mutation Score** | **{score}%** |")
    lines.append(f"| **Status** | **{status}** |")
    lines.append(f"| Total mutants | {total} |")
    lines.append(f"| Killed | {killed} |")
    lines.append(f"| Survived | {survived} |")
    lines.append(f"| Timeout | {timeout} |")
    lines.append(f"| Suspicious | {suspicious} |")
    lines.append(f"| Skipped | {skipped} |")
    if run_info.get("baseline_time"):
        lines.append(f"| Baseline test time | {run_info['baseline_time']}s |")
    if run_info.get("total_mutants_found"):
        lines.append(f"| Mutants found | {run_info['total_mutants_found']} |")
    lines.append("")

    # ─── Score interpretation ──────────────────────────────────────────────────
    lines.append("### Score interpretation")
    lines.append("")
    lines.append("| Score | Status | Meaning |")
    lines.append("|-------|--------|---------|")
    lines.append("| 90-100 | Excellent | Tests catch almost all mutations |")
    lines.append("| 80-89 | Good | Tests catch most mutations |")
    lines.append("| 70-79 | Acceptable | Some gaps in test coverage |")
    lines.append("| 60-69 | Medium risk | Notable gaps in test quality |")
    lines.append("| 50-59 | High risk | Significant test quality issues |")
    lines.append("| 0-49 | Critical | Tests fail to catch most mutations |")
    lines.append("")

    # ─── Mutant status breakdown ───────────────────────────────────────────────
    lines.append("## Mutant Status Breakdown")
    lines.append("")
    lines.append("| Status | Count | Percentage | Description |")
    lines.append("|--------|-------|------------|-------------|")
    if total > 0:
        lines.append(
            f"| 🎉 Killed | {killed} | {killed/total*100:.1f}% | Tests detected the mutation |"
        )
        lines.append(
            f"| 🙁 Survived | {survived} | {survived/total*100:.1f}% | Tests did NOT detect the mutation |"
        )
        lines.append(
            f"| ⏰ Timeout | {timeout} | {timeout/total*100:.1f}% | Test suite hung (infinite loop) |"
        )
        lines.append(
            f"| 🤔 Suspicious | {suspicious} | {suspicious/total*100:.1f}% | Tests took abnormally long |"
        )
        lines.append(
            f"| ⏭️ Skipped | {skipped} | {skipped/total*100:.1f}% | Mutant was not tested |"
        )
    else:
        lines.append("| 🎉 Killed | 0 | - | - |")
        lines.append("| 🙁 Survived | 0 | - | - |")
    lines.append("")

    # ─── Surviving mutants detail ──────────────────────────────────────────────
    lines.append("## Surviving Mutants (Detailed)")
    lines.append("")
    if not survived_diffs:
        lines.append("No surviving mutants found. All mutations were killed by the test suite.")
        lines.append("")
    else:
        lines.append(
            f"Found **{len(survived_diffs)}** surviving mutant(s). These need additional tests to kill them."
        )
        lines.append("")
        # Group by file
        by_file: dict[str, list[dict[str, str]]] = {}
        for m in survived_diffs:
            by_file.setdefault(m["file"], []).append(m)

        lines.append("### By file")
        lines.append("")
        lines.append("| File | Surviving mutants |")
        lines.append("|------|-------------------|")
        for file_path in sorted(by_file, key=lambda f: len(by_file[f]), reverse=True):
            lines.append(f"| `{file_path}` | {len(by_file[file_path])} |")
        lines.append("")

        # Module-level killed rate estimate (survived only — killed count unknown per file)
        lines.append("### Mutant density by module (surviving only)")
        lines.append("")
        lines.append("| Module | Surviving | % of total survived |")
        lines.append("|--------|-----------|---------------------|")
        total_survived = len(survived_diffs)
        for file_path in sorted(by_file, key=lambda f: len(by_file[f]), reverse=True)[:10]:
            count = len(by_file[file_path])
            pct = count / total_survived * 100 if total_survived > 0 else 0
            lines.append(f"| `{file_path}` | {count} | {pct:.1f}% |")
        lines.append("")

        # Detailed diffs
        lines.append("### Diffs")
        lines.append("")
        for idx, m in enumerate(survived_diffs, 1):
            lines.append(f"#### Mutant #{idx}: `{m['file']}:{m['line']}`")
            if m.get("context"):
                lines.append(f"Context: `{m['context']}`")
            lines.append("")
            lines.append("```diff")
            lines.append(m["diff"].rstrip())
            lines.append("```")
            lines.append("")

    # ─── CI/CD stats (if available) ────────────────────────────────────────────
    if cicd_stats:
        lines.append("## CI/CD Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for key, value in cicd_stats.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"| {key} | {value} |")
        lines.append("")

    # ─── Configuration ─────────────────────────────────────────────────────────
    lines.append("## Configuration")
    lines.append("")
    lines.append("Mutmut configuration from `pyproject.toml`:")
    lines.append("")
    lines.append("```toml")
    lines.append("[tool.mutmut]")
    lines.append('source_paths = ["src/soar_lab/"]')
    lines.append('do_not_mutate = ["src/soar_lab/__init__.py", "*/scripts/*", "*/tests/*"]')
    lines.append('runner_command = "python -m pytest -x -q --tb=no -m \'not requires_docker and not requires_external\' --ignore=tests/e2e --ignore=tests/atomic --ignore=tests/quality --ignore=tests/architecture"')
    lines.append("```")
    lines.append("")

    # ─── Performance metrics ───────────────────────────────────────────────────
    if run_info.get("baseline_time") or run_info.get("total_mutants_found"):
        lines.append("## Performance Metrics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        if run_info.get("baseline_time"):
            lines.append(f"| Baseline test time | {run_info['baseline_time']}s |")
            if total > 0:
                estimated_total = run_info["baseline_time"] * total
                lines.append(
                    f"| Estimated total time (baseline x mutants) | {estimated_total:.0f}s ({estimated_total/60:.1f}m) |"
                )
        if run_info.get("total_mutants_found"):
            lines.append(f"| Mutants found | {run_info['total_mutants_found']} |")
            if run_info["total_mutants_found"] != total:
                lines.append(
                    f"| Mutants tested | {total} (skipped: {run_info['total_mutants_found'] - total}) |"
                )
        lines.append("")

    # ─── Recommendations ───────────────────────────────────────────────────────
    lines.append("## Recommendations")
    lines.append("")
    if survived == 0 and total > 0:
        lines.append(
            "- ✅ All mutations were killed. The test suite has excellent mutation coverage."
        )
    elif survived > 0:
        lines.append(f"- ❌ {survived} mutant(s) survived. Add tests to detect these mutations:")
        lines.append("  1. Review each surviving mutant diff above")
        lines.append("  2. Write a test that would fail if the mutation were applied")
        lines.append("  3. Re-run `mutmut run` to verify the new tests kill the mutants")
        lines.append("  4. Use `mutmut show <mutant_id>` to see individual mutant details")
        lines.append("")
        # File-specific recommendations
        if by_file:
            lines.append("  Priority files (most surviving mutants):")
            for file_path in sorted(by_file, key=lambda f: len(by_file[f]), reverse=True)[:5]:
                lines.append(f"  - `{file_path}`: {len(by_file[file_path])} surviving mutant(s)")
    if suspicious > 0:
        lines.append(
            f"- ⚠️ {suspicious} suspicious mutant(s). Tests took abnormally long — possible infinite loop or performance issue."
        )
    if timeout > 0:
        lines.append(
            f"- ⏰ {timeout} timeout mutant(s). The mutation may have caused an infinite loop."
        )
    lines.append("")

    # ─── How to reproduce ──────────────────────────────────────────────────────
    lines.append("## How to reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("# Inside the Docker container (soar_api):")
    lines.append("# mutmut is installed via pyproject.toml [project.optional-dependencies] quality")
    lines.append("python -m mutmut run")
    lines.append("python -m mutmut results")
    lines.append("python -m mutmut show all")
    lines.append("")
    lines.append("# Or from the host:")
    lines.append("make mutation")
    lines.append("```")
    lines.append("")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report generated: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a comprehensive mutation testing report from mutmut."
    )
    parser.add_argument(
        "--output-dir",
        default="reports/mutmut",
        help="Output directory for the report (default: reports/mutmut)",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip `mutmut run` and use existing cached results",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=7200,
        help="Timeout for mutmut run in seconds (default: 7200 = 2h)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Run mutmut (or skip)
    run_info: dict[str, Any] = {}
    if not args.skip_run:
        print("==> Running mutmut (this may take 60-180 minutes)...")
        # mutmut 3.x reads config from [tool.mutmut] in pyproject.toml
        # (paths_to_mutate, runner_command, do_not_mutate)
        rc, stdout, stderr = run_cmd(
            [
                sys.executable,
                "-m",
                "mutmut",
                "run",
            ],
            timeout=args.timeout,
        )
        run_info = parse_run_output(stdout + "\n" + stderr)
        # Save raw output
        (output_dir / "mutmut_run.log").write_text(
            f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}\n",
            encoding="utf-8",
        )
        if rc != 0 and "killed" not in stdout.lower():
            print(f"ERROR: mutmut run failed (exit code {rc})")
            print(f"See {output_dir / 'mutmut_run.log'} for details")
            return rc
        print("==> mutmut run completed")
    else:
        print("==> Skipping mutmut run (using cached results)")

    # Step 2: Get results summary
    print("==> Collecting results summary...")
    rc, results_stdout, _ = run_cmd([sys.executable, "-m", "mutmut", "results"], timeout=60)
    (output_dir / "results.txt").write_text(results_stdout, encoding="utf-8")
    stats = parse_results_summary(results_stdout)
    print(
        f"    Score: {stats['mutation_score']}% | Killed: {stats['killed']} | Survived: {stats['survived']}"
    )

    # Step 3: Get surviving mutant diffs
    print("==> Collecting surviving mutant diffs...")
    rc, show_stdout, _ = run_cmd([sys.executable, "-m", "mutmut", "show", "all"], timeout=120)
    (output_dir / "survived_diffs.txt").write_text(show_stdout, encoding="utf-8")
    survived_diffs = parse_survived_diffs(show_stdout)
    print(f"    Found {len(survived_diffs)} surviving mutant(s) with diffs")

    # Step 4: Get CI/CD stats (if available)
    print("==> Collecting CI/CD stats...")
    rc, cicd_stdout, _ = run_cmd([sys.executable, "-m", "mutmut", "export-cicd-stats"], timeout=30)
    cicd_stats = parse_cicd_stats(cicd_stdout) if rc == 0 and cicd_stdout.strip() else None
    if cicd_stats:
        (output_dir / "cicd_stats.json").write_text(
            json.dumps(cicd_stats, indent=2), encoding="utf-8"
        )

    # Step 5: Generate Markdown report
    print("==> Generating Markdown report...")
    report_path = output_dir / "mutation_report.md"
    generate_markdown_report(
        stats=stats,
        survived_diffs=survived_diffs,
        cicd_stats=cicd_stats,
        run_info=run_info,
        output_path=report_path,
    )

    # Step 6: Save JSON summary
    json_path = output_dir / "mutation_summary.json"
    json_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).isoformat(),
                "stats": stats,
                "survived_count": len(survived_diffs),
                "survived_files": list({m["file"] for m in survived_diffs}),
                "run_info": run_info,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"==> Done! Report: {report_path}")
    print(f"    JSON summary: {json_path}")
    print(f"    Raw results: {output_dir / 'results.txt'}")
    print(f"    Raw diffs: {output_dir / 'survived_diffs.txt'}")
    if cicd_stats:
        print(f"    CI/CD stats: {output_dir / 'cicd_stats.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
