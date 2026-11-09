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
from datetime import UTC, datetime
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

    # mutmut >=3.8 `results` prints one "name: status" line per mutant
    # instead of a summary — count statuses when the summary was absent.
    if not any(stats.values()):
        for line in stdout.splitlines():
            m = re.search(r":\s*([a-z_ ]+?)\s*$", line)
            if not m:
                continue
            status = m.group(1).strip().replace(" ", "_")
            if status == "no_tests":
                stats["not_seen"] += 1  # untested mutants stay out of the score denominator
            elif status in stats:
                stats[status] += 1

    total = (
        stats["killed"]
        + stats["timeout"]
        + stats["suspicious"]
        + stats["survived"]
        + stats["skipped"]
    )
    stats["total"] = total
    _compute_scores(stats)
    return stats


def _compute_scores(stats: dict[str, Any]) -> None:
    """Fill score fields on a stats dict (mutated in place).

    mutation_score    — mutmut's effective score: (killed+timeout)/(total-skipped)
    killed_only_score — strict score: killed/(total-skipped)
    detection_score   — killed/(killed+survived) on resolved mutants, timeouts excluded
    """
    tested = max(stats["total"] - stats["skipped"], 0)
    stats["mutation_score"] = round(
        (stats["killed"] + stats["timeout"]) / tested * 100 if tested else 0, 2
    )
    stats["killed_only_score"] = round(stats["killed"] / tested * 100 if tested else 0, 2)
    resolved = stats["killed"] + stats["survived"]
    stats["detection_score"] = round(stats["killed"] / resolved * 100 if resolved else 0, 2)


def load_cicd_stats_file(path: Path) -> dict[str, Any] | None:
    """Load mutmut >=3.8 `mutants/mutmut-cicd-stats.json` (authoritative counts).

    `mutmut results` omits killed mutants entirely, so line counting under-reports;
    the stats file written during `mutmut run` has exact per-status counts.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    stats = {
        "killed": int(raw.get("killed", 0)),
        "timeout": int(raw.get("timeout", 0)),
        "suspicious": int(raw.get("suspicious", 0)),
        "survived": int(raw.get("survived", 0)),
        "skipped": int(raw.get("skipped", 0)),
        "not_seen": int(raw.get("no_tests", 0)) + int(raw.get("not_checked", 0)),
    }
    stats["total"] = int(
        raw.get(
            "total",
            stats["killed"]
            + stats["timeout"]
            + stats["suspicious"]
            + stats["survived"]
            + stats["skipped"]
            + stats["not_seen"],
        )
    )
    _compute_scores(stats)
    return stats


# ─── Equivalent mutant analysis ──────────────────────────────────────────────
#
# Surviving mutants that were manually triaged and proven equivalent (the
# mutation cannot produce an observable behavior difference). Keyed by the
# mangled function name + mutant suffix appearing in `mutmut results` output.
EQUIVALENT_MUTANT_REASONS: list[tuple[str, str]] = [
    (
        "generate_secret_key__mutmut_1",
        "`length=33` gives `33 // 2 == 16`, identical to `32 // 2` — token_hex output unchanged.",
    ),
    (
        "generate_api_key__mutmut_26",
        "lowercase exclusion `"
        "XX0Ol1IXX"
        "`: the registered mutant function produces the original alphabet when invoked directly (verified) — no observable difference.",
    ),
    (
        "generate_api_key__mutmut_34",
        "digit filter `"
        "0Ol1I"
        "` → `"
        "XX0Ol1IXX"
        "`: 'X' is not a digit — filtered digit set identical.",
    ),
    (
        "generate_api_key__mutmut_35",
        "digit filter `"
        "0Ol1I"
        "` → `"
        "0ol1i"
        "`: only digits matter in the filter; '0' and '1' still excluded — identical set.",
    ),
    (
        "generate_api_key__mutmut_36",
        "digit filter `"
        "0Ol1I"
        "` → `"
        "0OL1I"
        "`: '0' and '1' still excluded — filtered digit set identical.",
    ),
    (
        "sanitize_html__mutmut_20",
        "`len >= max` truncates `html[:max]` — when len == max the result is identical.",
    ),
    (
        "sanitize_js__mutmut_13",
        "`len >= max` truncates `value[:max]` — when len == max the result is identical.",
    ),
    (
        "decode__mutmut_8",
        "Python codec names are case-insensitive — `" "UTF-8" "` ≡ `" "utf-8" "`.",
    ),
    (
        "_TimeoutContextǁ__init____mutmut_3",
        "`_old_handler = ''` is overwritten by `__enter__` before `__exit__` ever reads it.",
    ),
    (
        "_TimeoutContextǁ__exit____mutmut_2",
        "`and`→`or`: differs only when `_signum is None` while `_old_handler` is set — `__enter__` leaves both unset together, so the state is unreachable.",
    ),
    (
        "TimeoutHandlerǁrun__mutmut_2",
        "`timeout=None` falls back through `default_timeout or self.timeout` — same value as `self.timeout`.",
    ),
    (
        "TimeoutHandlerǁrun__mutmut_4",
        "dropping the `timeout` kwarg falls back to the same handler default — identical deadline.",
    ),
    (
        "TimeoutHandlerǁexecute_with_timeout__mutmut_4",
        "`result = ''` is overwritten by the worker target or never read on the error path.",
    ),
    (
        "RetryPolicyǁ_should_retry__mutmut_3",
        "`getattr(..., True)`→`None`: `X is False` is False for both defaults — same branch always.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_5",
        "`last_error = ''` initial value is unreachable — the loop always assigns before the tail raise.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_8",
        "`range(max_retries+2)` is dominated by `attempt == max_retries → raise` — extra iteration never runs.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_19",
        "`last_error = None` — trailing raise is unreachable (loop exits via `return`/`raise`).",
    ),
    (
        "RetryPolicyǁexecute__mutmut_36",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_37",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_38",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_39",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_40",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_41",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "RetryPolicyǁexecute__mutmut_42",
        "trailing-raise variant — loop never exits normally, code is unreachable.",
    ),
    (
        "summary_stats__mutmut_130",
        "iqr = q3−q1 where percentile() already rounds to 2 decimals — `round(x,3)` ≡ `round(x,4)`.",
    ),
    (
        "generate_ioc__mutmut_1",
        "`alert_id='XXXX'` — the parameter is never referenced in the returned dict.",
    ),
]


def classify_equivalent_mutants(results_stdout: str) -> dict[str, str]:
    """Map surviving mutant names → equivalence rationale when known."""
    classified: dict[str, str] = {}
    for line in results_stdout.splitlines():
        if not line.strip().endswith(": survived"):
            continue
        name = line.strip()[: -len(": survived")].strip()
        for key, reason in EQUIVALENT_MUTANT_REASONS:
            if key.replace("ǁ", "ǁ") in name:
                classified[name] = reason
                break
    return classified


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
    equivalents: dict[str, str] | None = None,
) -> None:
    """Generate the comprehensive Markdown report."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    score = stats["mutation_score"]
    total = stats["total"]
    killed = stats["killed"]
    survived = stats["survived"]
    timeout = stats["timeout"]
    suspicious = stats["suspicious"]
    skipped = stats["skipped"]
    no_tests = stats.get("not_seen", 0)
    killed_only = stats.get("killed_only_score", score)
    detection = stats.get("detection_score", score)

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
    lines.append("Source mutated: `src/soar_lab/`")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── Executive Summary ─────────────────────────────────────────────────────
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| **Mutation Score (effective)** | **{score}%** |")
    lines.append(f"| **Status** | **{status}** |")
    lines.append(f"| Detection score (killed/(killed+survived)) | {detection}% |")
    lines.append(f"| Killed-only score (timeouts excluded from kills) | {killed_only}% |")
    lines.append(f"| Total mutants | {total} |")
    lines.append(f"| Killed | {killed} |")
    lines.append(f"| Survived | {survived} |")
    lines.append(f"| Timeout | {timeout} |")
    lines.append(f"| Suspicious | {suspicious} |")
    lines.append(f"| Skipped | {skipped} |")
    lines.append(f"| No tests (untested) | {no_tests} |")
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
        lines.append(
            f"| 🫥 No tests | {no_tests} | {no_tests/total*100:.1f}% | No test covered the mutant |"
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

    # ─── Equivalent mutant analysis ────────────────────────────────────────────
    if equivalents is not None:
        lines.append("## Equivalent Mutant Analysis")
        lines.append("")
        unclassified = stats["survived"] - len(equivalents)
        lines.append(
            f"Of the **{stats['survived']}** surviving mutants, "
            f"**{len(equivalents)}** were manually triaged as *equivalent* — the mutation "
            "cannot produce an observable behavior difference, so no test can kill them."
        )
        lines.append("")
        if equivalents:
            lines.append("| Survivor | Why it is equivalent |")
            lines.append("|----------|----------------------|")
            for name, reason in sorted(equivalents.items()):
                short = name.split("xǁ")[-1] if "xǁ" in name else name
                lines.append(f"| `{short}` | {reason} |")
            lines.append("")
        if unclassified > 0:
            lines.append(
                f"⚠️ **{unclassified}** surviving mutant(s) are NOT classified as equivalent "
                "and need tests or further analysis."
            )
            lines.append("")
        else:
            lines.append(
                "All surviving mutants are accounted for as equivalent. "
                "The effective test-detection rate is therefore "
                f"{detection}% of *killable* mutants."
            )
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
    lines.append(
        'source_paths = ["src/soar_lab/security/", "src/soar_lab/resilience/", "src/soar_lab/domain/"]'
    )
    lines.append(
        'pytest_add_cli_args = ["-q", "--tb=no", "--timeout=30", "--no-cov", "-o", "addopts=",'
        ' "-o", "pythonpath=.", "-p", "no:cacheprovider"]'
    )
    lines.append('pytest_add_cli_args_test_selection = ["tests/unit/"]')
    lines.append(
        'do_not_mutate = ["src/soar_lab/__init__.py", "*/scripts/*", "*/tests/*", "*/ports/*"]'
    )
    lines.append('also_copy = ["scripts/", "src/", "detections/", ".env.example"]')
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
        if equivalents is not None and len(equivalents) >= survived:
            lines.append(
                f"- ✅ {survived} mutant(s) survived, all classified as *equivalent* "
                "(see Equivalent Mutant Analysis) — no actionable test gaps remain."
            )
        else:
            lines.append(
                f"- ❌ {survived} mutant(s) survived. Add tests to detect these mutations:"
            )
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
        # keys: paths_to_mutate, runner_command, do_not_mutate
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
    # `mutmut results` omits killed mutants — prefer the stats file written
    # during the run when it exists (exact counts, includes killed).
    file_stats = load_cicd_stats_file(Path("mutants") / "mutmut-cicd-stats.json")
    if file_stats and file_stats["total"] > 0:
        stats = file_stats
    print(
        f"    Score: {stats['mutation_score']}% | Killed: {stats['killed']} | Survived: {stats['survived']}"
    )

    # Step 3: Get surviving mutant diffs
    print("==> Collecting surviving mutant diffs...")
    rc, show_stdout, _ = run_cmd([sys.executable, "-m", "mutmut", "show", "all"], timeout=120)
    if not parse_survived_diffs(show_stdout):
        # mutmut >=3.8 has no "show all" — diff each survivor individually.
        names = [
            m.group(1).strip()
            for m in (
                re.match(r"\s*(.+?):\s*survived\s*$", ln) for ln in results_stdout.splitlines()
            )
            if m
        ]
        chunks = []
        for name in names:
            _, one, _ = run_cmd([sys.executable, "-m", "mutmut", "show", name], timeout=30)
            chunks.append(one)
        show_stdout = "\n".join(chunks)
    (output_dir / "survived_diffs.txt").write_text(show_stdout, encoding="utf-8")
    survived_diffs = parse_survived_diffs(show_stdout)
    print(f"    Found {len(survived_diffs)} surviving mutant(s) with diffs")
    equivalents = classify_equivalent_mutants(results_stdout)
    if equivalents:
        print(f"    Classified {len(equivalents)} survivor(s) as equivalent mutants")

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
        equivalents=equivalents,
    )

    # Step 6: Save JSON summary
    json_path = output_dir / "mutation_summary.json"
    json_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(UTC).isoformat(),
                "stats": stats,
                "survived_count": len(survived_diffs),
                "survived_files": list({m["file"] for m in survived_diffs}),
                "equivalent_mutants": equivalents,
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
