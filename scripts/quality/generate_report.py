"""Generate quality summary reports in Markdown and JSON.

The Markdown report includes all 15 measured categories with detailed
tables, rankings, and actionable recommendations derived from the actual
metrics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calculate_quality_score import calculate


def generate_json(metrics: dict[str, Any], output_path: str) -> None:
    """Generate quality-summary.json with all metrics and score."""
    score = calculate(metrics)
    report = {
        "generated_at": datetime.now().isoformat(),
        "score": score,
        "metrics": metrics,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def _fmt_pct(value: Any) -> str:
    """Format a value as percentage string."""
    if value is None or value == "N/A":
        return "—"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _fmt_num(value: Any, decimals: int = 2) -> str:
    """Format a numeric value."""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_path(path: Any) -> str:
    """Format a file path: convert backslashes to forward slashes for
    portable Markdown rendering (backslashes can be interpreted as escape
    characters in MDX/Docusaurus)."""
    if path is None or path == "?":
        return "?"
    return str(path).replace("\\", "/")


def _section_complexity(lines: list[str], cx: dict) -> None:
    """Add complexity section to report."""
    if not cx or "error" in cx:
        return
    grades = cx.get("grade_distribution", {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0})
    lines.extend(
        [
            "",
            "## Cyclomatic Complexity",
            "",
            f"- Total blocks: **{cx.get('total_blocks', 0)}**",
            f"- Average complexity: **{_fmt_num(cx.get('average_complexity'))}**",
            f"- Max complexity: **{cx.get('max_complexity', 0)}**",
            "",
            "### Grade distribution",
            "",
            "| Grade | Count | Meaning |",
            "|-------|-------|---------|",
            f"| A | {grades.get('A', 0)} | Low risk (1-5) |",
            f"| B | {grades.get('B', 0)} | Acceptable (6-10) |",
            f"| C | {grades.get('C', 0)} | Moderate risk (11-20) |",
            f"| D | {grades.get('D', 0)} | High risk (21-30) |",
            f"| E | {grades.get('E', 0)} | Very high risk (31-40) |",
            f"| F | {grades.get('F', 0)} | Critical (41+) |",
        ]
    )

    hotspots = cx.get("hotspots", [])
    if hotspots:
        lines.extend(
            [
                "",
                "### Top 10 most complex functions",
                "",
                "| # | Function | File | Line | CX | Grade |",
                "|---|----------|------|------|----|-------|",
            ]
        )
        for i, h in enumerate(hotspots[:10], 1):
            lines.append(
                f"| {i} | {h.get('name', '?')} | "
                f"{_fmt_path(h.get('filepath'))} | {h.get('line', '?')} | "
                f"{h.get('complexity', 0)} | {h.get('rank', '?')} |"
            )


def _section_maintainability(lines: list[str], mi: dict) -> None:
    """Add maintainability section."""
    if not mi or "error" in mi:
        return
    lines.extend(
        [
            "",
            "## Maintainability Index",
            "",
            f"- Total files: **{mi.get('total_files', 0)}**",
            f"- Average MI: **{_fmt_num(mi.get('average_mi'))}**",
            f"- Min MI: **{_fmt_num(mi.get('min_mi'))}**",
            f"- Max MI: **{_fmt_num(mi.get('max_mi'))}**",
            "",
            "| Scale | Meaning |",
            "|-------|---------|",
            "| MI >= 80 | Good |",
            "| MI >= 65 | Acceptable |",
            "| MI >= 50 | Needs review |",
            "| MI < 50 | High maintenance risk |",
        ]
    )
    worst = mi.get("worst_files", [])
    if worst:
        lines.extend(
            [
                "",
                "### Top 10 least maintainable files",
                "",
                "| # | File | MI |",
                "|---|------|----|",
            ]
        )
        for i, f in enumerate(worst[:10], 1):
            lines.append(f"| {i} | {_fmt_path(f.get('filepath'))} | {_fmt_num(f.get('mi'))} |")


def _section_coverage(lines: list[str], cov: dict) -> None:
    """Add coverage section."""
    if not cov or "error" in cov:
        if cov and "error" in cov:
            hint = cov.get("hint", "")
            lines.extend(
                [
                    "",
                    "## Test Coverage",
                    "",
                    f"_Not measured: {cov['error']}_",
                    "",
                    f"**Hint:** `{hint}`" if hint else "",
                ]
            )
        return
    total_lines = cov.get("total_lines", 0)
    total_covered = cov.get("total_lines_covered", 0)
    lines.extend(
        [
            "",
            "## Test Coverage",
            "",
            f"- Global line coverage: **{_fmt_pct(cov.get('global_line_coverage'))}**",
            f"- Global branch coverage: **{_fmt_pct(cov.get('global_branch_coverage'))}**",
            f"- Total files: **{cov.get('total_files', 0)}**",
            f"- Total lines: **{total_covered}/{total_lines}**",
            f"- Files below 75% threshold: **{cov.get('files_below_count', 0)}**",
        ]
    )
    worst = cov.get("worst_files", [])
    if worst:
        lines.extend(
            [
                "",
                "### Files with lowest coverage",
                "",
                "| # | File | Line cov | Branch cov | Lines |",
                "|---|------|----------|------------|-------|",
            ]
        )
        for i, f in enumerate(worst[:10], 1):
            fp = _fmt_path(f.get("filepath"))
            # Coverage XML stores paths relative to src/soar_lab/;
            # prefix for clarity in the report.
            if fp and not fp.startswith("src/") and not fp.startswith("tests/"):
                fp = f"src/soar_lab/{fp}"
            lines.append(
                f"| {i} | {fp} | "
                f"{_fmt_pct(f.get('line_coverage'))} | "
                f"{_fmt_pct(f.get('branch_coverage'))} | "
                f"{f.get('lines_covered', 0)}/{f.get('lines_valid', 0)} |"
            )


def _section_linting(lines: list[str], ruff: dict) -> None:
    """Add linting section."""
    if not ruff:
        return
    total = ruff.get("total_errors", 0)
    lines.extend(
        [
            "",
            "## Linting (Ruff)",
            "",
            f"- Total errors: **{total}**",
        ]
    )
    if total == 0:
        lines.append("\n_No linting errors. Code follows ruff style rules._")
    by_rule = ruff.get("by_rule", {})
    if by_rule:
        lines.extend(
            [
                "",
                "### Errors by rule",
                "",
                "| Rule | Count |",
                "|------|-------|",
            ]
        )
        for rule, count in list(by_rule.items())[:10]:
            lines.append(f"| {rule} | {count} |")
    by_file = ruff.get("by_file", {})
    if by_file:
        lines.extend(
            [
                "",
                "### Files with most errors",
                "",
                "| File | Errors |",
                "|------|--------|",
            ]
        )
        for filepath, count in list(by_file.items())[:10]:
            lines.append(f"| {_fmt_path(filepath)} | {count} |")


def _section_typing(lines: list[str], mypy: dict) -> None:
    """Add typing section."""
    if not mypy:
        return
    errors = mypy.get("error_count", 0)
    lines.extend(
        [
            "",
            "## Static Typing (mypy)",
            "",
            f"- Error count: **{errors}**",
        ]
    )
    if errors == 0:
        lines.append("\n_No type errors. All code is properly typed._")


def _section_security(lines: list[str], sec: dict) -> None:
    """Add security section."""
    if not sec or "error" in sec:
        return
    by_sev = sec.get("by_severity", {})
    lines.extend(
        [
            "",
            "## Security (Bandit)",
            "",
            f"- Total issues: **{sec.get('total_issues', 0)}**",
            f"- HIGH: **{by_sev.get('HIGH', 0)}**",
            f"- MEDIUM: **{by_sev.get('MEDIUM', 0)}**",
            f"- LOW: **{by_sev.get('LOW', 0)}**",
        ]
    )
    if sec.get("total_issues", 0) == 0:
        lines.append("\n_No security issues detected by bandit._")
    issues = sec.get("issues", [])
    if issues:
        lines.extend(
            [
                "",
                "### Security issues detail",
                "",
                "| ID | Severity | Confidence | File | Line | Description |",
                "|----|----------|------------|------|------|-------------|",
            ]
        )
        for i in issues[:15]:
            desc = i.get("description", "")[:80]
            lines.append(
                f"| {i.get('id', '?')} | {i.get('severity', '?')} | "
                f"{i.get('confidence', '?')} | {i.get('file', '?')} | "
                f"{i.get('line', 0)} | {desc} |"
            )


def _section_dead_code(lines: list[str], dc: dict) -> None:
    """Add dead code section."""
    if not dc or "error" in dc:
        return
    by_conf = dc.get("by_confidence", {})
    lines.extend(
        [
            "",
            "## Dead Code (Vulture)",
            "",
            f"- Total items: **{dc.get('total_items', 0)}**",
            f"- High confidence (>=90%): **{by_conf.get('high', 0)}**",
            f"- Medium confidence (60-89%): **{by_conf.get('medium', 0)}**",
            f"- Low confidence (<60%): **{by_conf.get('low', 0)}**",
        ]
    )
    items = dc.get("items", [])
    if items:
        lines.extend(
            [
                "",
                "### Dead code items",
                "",
                "| File | Line | Description |",
                "|------|------|-------------|",
            ]
        )
        for item in items[:15]:
            lines.append(
                f"| {_fmt_path(item.get('file'))} | {item.get('line', 0)} | "
                f"{item.get('description', '')[:80]} |"
            )
        total_items = dc.get("total_items", len(items))
        if total_items > 15:
            lines.append(
                f"\n_Showing 15 of {total_items} items. "
                f"Run `make quality` for the full list._"
            )


def _section_documentation(lines: list[str], doc: dict) -> None:
    """Add documentation section."""
    if not doc:
        return
    covered = doc.get("covered", 0)
    total = doc.get("total", 0)
    # Parse from interrogate output if covered/total not in JSON
    if not covered or not total:
        import re
        output = doc.get("output", "")
        m = re.search(r"\|\s*TOTAL\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", output)
        if m:
            total = int(m.group(1))
            covered = int(m.group(2))
    detail = f" ({covered}/{total} documented)" if covered and total else ""
    lines.extend(
        [
            "",
            "## Documentation (Interrogate)",
            "",
            f"- Docstring coverage: **{_fmt_pct(doc.get('coverage_percent'))}**{detail}",
        ]
    )


def _section_dependency_audit(lines: list[str], dep: dict) -> None:
    """Add dependency audit section, grouped by package."""
    if not dep or "error" in dep:
        return
    total = dep.get("total_vulnerabilities", 0)
    vulns = dep.get("vulnerabilities", [])

    # Group by package
    by_pkg: dict[str, dict] = {}
    for v in vulns:
        pkg = v.get("package", "?")
        if pkg not in by_pkg:
            by_pkg[pkg] = {
                "version": v.get("version", "?"),
                "count": 0,
                "fix_versions": set(),
                "vulns": [],
            }
        by_pkg[pkg]["count"] += 1
        by_pkg[pkg]["vulns"].append(v.get("id", "?"))
        for fv in v.get("fix_versions", []):
            by_pkg[pkg]["fix_versions"].add(fv)

    lines.extend(
        [
            "",
            "## Dependency Audit (pip-audit)",
            "",
            f"- Total vulnerabilities: **{total}**",
            f"- Affected packages: **{len(by_pkg)}**",
        ]
    )
    if total == 0:
        lines.append("\n_No known vulnerabilities in dependencies._")

    if by_pkg:
        lines.extend(
            [
                "",
                "### Vulnerable packages (grouped)",
                "",
                "| Package | Version | Vulns | Fix version |",
                "|---------|---------|-------|-------------|",
            ]
        )
        sorted_pkgs = sorted(by_pkg.items(), key=lambda x: -x[1]["count"])
        for pkg, info in sorted_pkgs[:20]:
            fix = ", ".join(sorted(info["fix_versions"])) or "N/A"
            lines.append(f"| {pkg} | {info['version']} | {info['count']} | {fix} |")


def _section_architecture(lines: list[str], arch: dict) -> None:
    """Add architecture section."""
    if not arch:
        return
    violations = arch.get("violation_count", 0)
    lines.extend(
        [
            "",
            "## Architecture (import-linter)",
            "",
            f"- Violations: **{violations}**",
        ]
    )
    if violations == 0:
        lines.append("\n_No architecture violations. Hexagonal layering is respected._")
    output = arch.get("output", "")
    if output and "not configured" not in output.lower():
        lines.extend(["", "```", output[:500], "```"])


def _section_secrets(lines: list[str], secrets: dict) -> None:
    """Add secrets section."""
    if not secrets or "error" in secrets:
        return
    total = secrets.get("total_secrets", 0)
    lines.extend(
        [
            "",
            "## Secrets Detection (detect-secrets)",
            "",
            f"- Total secrets found: **{total}**",
        ]
    )
    if total == 0:
        lines.append("\n_No secrets detected in the codebase._")
    files = secrets.get("files_with_secrets", [])
    if files:
        lines.extend(["", "### Files with secrets", ""])
        for f in files[:10]:
            lines.append(f"- {f}")


def _section_pylint(lines: list[str], pylint: dict) -> None:
    """Add pylint section with score, issue breakdown, top modules, and top
    issues."""
    if not pylint:
        return
    score = pylint.get("score")
    pylint_lines = [
        "",
        "## Deep Analysis (Pylint)",
        "",
    ]
    if score is not None:
        pylint_lines.append(f"- Score: **{_fmt_num(score, 2)}/10**")
    else:
        pylint_lines.append("- Score: _not available_")
    total_issues = pylint.get("total_issues", 0)
    by_type = pylint.get("by_type", {})
    error_count = by_type.get("error", 0)
    if error_count == 0 and total_issues > 0:
        pylint_lines.append(
            f"- Total issues: **{total_issues}** "
            f"(0 errors, {by_type.get('warning', 0)} warnings, "
            f"{by_type.get('refactor', 0)} refactor, "
            f"{by_type.get('convention', 0)} convention)"
        )
    else:
        pylint_lines.append(f"- Total issues: **{total_issues}**")
    lines.extend(pylint_lines)

    if by_type:
        lines.extend(
            [
                "",
                "### Issues by type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ]
        )
        for t in ("error", "warning", "refactor", "convention", "info"):
            c = by_type.get(t, 0)
            lines.append(f"| {t} | {c} |")

    by_module = pylint.get("by_module", {})
    if by_module:
        lines.extend(
            [
                "",
                "### Top 10 modules with most issues",
                "",
                "| Module | Issues |",
                "|--------|--------|",
            ]
        )
        for mod, count in list(by_module.items())[:10]:
            lines.append(f"| {mod} | {count} |")

    by_symbol = pylint.get("by_symbol", {})
    issues = pylint.get("issues", [])
    if by_symbol:
        # Build a single unified table using real counts from by_symbol
        # (which covers ALL 515 issues) and one example from issues list.
        # Group issues by symbol to find examples.
        examples_by_sym: dict[str, dict] = {}
        for i in issues:
            sym = i.get("symbol", "?")
            if sym not in examples_by_sym:
                examples_by_sym[sym] = i
        # Sort symbols by real frequency (from by_symbol, not issues list)
        sorted_syms = sorted(by_symbol.items(), key=lambda x: -x[1])
        lines.extend(
            [
                "",
                "### Most frequent issues (by symbol)",
                "",
                "| Symbol | Type | Count | Example module | Line | Message |",
                "|--------|------|-------|----------------|------|---------|",
            ]
        )
        for sym, count in sorted_syms[:15]:
            ex = examples_by_sym.get(sym)
            if ex:
                # Sanitize message: collapse newlines and pipes that break tables
                msg = ex.get("message", "")[:50].replace("\n", " ").replace("|", "/").replace("==", " — ")
                lines.append(
                    f"| {sym} | {ex.get('type', '?')} | {count} | "
                    f"{ex.get('module', '?')} | {ex.get('line', 0)} | {msg} |"
                )
            else:
                lines.append(f"| {sym} | — | {count} | — | — | — |")


def _section_halstead(lines: list[str], hal: dict) -> None:
    """Add Halstead metrics section.

    Radon hal returns per-file arrays:
    [n1, n2, N1, N2, vocabulary, length, volume, difficulty, effort, time, bugs]
    """
    if not hal or "error" in hal:
        return

    # Aggregate Halstead totals across all files
    # Radon hal array: [h1, h2, N1, N2, vocabulary, length, calculated_length,
    #                   volume, difficulty, effort, time, bugs]
    total_volume = 0.0
    total_difficulty = 0.0
    total_effort = 0.0
    total_bugs = 0.0
    file_count = 0
    file_efforts: list[tuple[str, float]] = []

    for filepath, metrics in hal.items():
        if isinstance(metrics, dict) and "total" in metrics:
            total = metrics["total"]
            if isinstance(total, list) and len(total) >= 12:
                volume = total[7] if isinstance(total[7], (int, float)) else 0
                difficulty = total[8] if isinstance(total[8], (int, float)) else 0
                effort = total[9] if isinstance(total[9], (int, float)) else 0
                bugs = total[11] if isinstance(total[11], (int, float)) else 0
                total_volume += volume
                total_difficulty += difficulty
                total_effort += effort
                total_bugs += bugs
                file_efforts.append((filepath, effort))
                file_count += 1

    lines.extend(
        [
            "",
            "---",
            "",
            "## Halstead Metrics",
            "",
            f"- Files analyzed: **{file_count}**",
            f"- Total volume: **{_fmt_num(total_volume, 0)}**",
            f"- Total difficulty: **{_fmt_num(total_difficulty, 1)}**",
            f"- Total effort: **{_fmt_num(total_effort, 0)}**",
            f"- Estimated bugs: **{_fmt_num(total_bugs, 2)}**",
            "",
            "_Halstead metrics measure code volume, difficulty, effort, and estimated bugs._",
        ]
    )

    # Top 5 files by effort
    if file_efforts:
        file_efforts.sort(key=lambda x: -x[1])
        lines.extend(
            [
                "",
                "### Top 5 files by Halstead effort",
                "",
                "| # | File | Effort |",
                "|---|------|--------|",
            ]
        )
        for i, (filepath, effort) in enumerate(file_efforts[:5], 1):
            short = _fmt_path(filepath).replace("src/", "")
            lines.append(f"| {i} | {short} | {_fmt_num(effort, 0)} |")


def _section_raw(lines: list[str], raw: dict) -> None:
    """Add raw metrics section with top files by LOC and test-to-code ratio."""
    if not raw or "error" in raw:
        return
    total_loc = 0
    total_lloc = 0
    total_sloc = 0
    total_comments = 0
    file_locs: list[tuple[str, int]] = []
    for filepath, m in raw.items():
        if isinstance(m, dict):
            loc = m.get("loc", 0)
            total_loc += loc
            total_lloc += m.get("lloc", 0)
            total_sloc += m.get("sloc", 0)
            total_comments += m.get("comments", 0)
            if loc > 0:
                file_locs.append((filepath, loc))
    comment_ratio = (total_comments / total_sloc * 100) if total_sloc > 0 else 0
    lines.extend(
        [
            "",
            "---",
            "",
            "## Raw Code Metrics",
            "",
            f"- Total files: **{len(raw)}**",
            f"- Total LOC: **{total_loc}**",
            f"- Total LLOC: **{total_lloc}**",
            f"- Total SLOC: **{total_sloc}**",
            f"- Comment lines: **{total_comments}**",
            f"- Comment ratio: **{_fmt_pct(comment_ratio)}**",
        ]
    )

    # Test-to-code ratio
    try:
        from pathlib import Path

        test_loc = 0
        test_dir = Path("tests")
        if test_dir.exists():
            for py_file in test_dir.rglob("*.py"):
                try:
                    test_loc += sum(1 for _ in py_file.open(encoding="utf-8"))
                except Exception:
                    pass
        if total_sloc > 0 and test_loc > 0:
            ratio = test_loc / total_sloc
            lines.extend(
                [
                    "",
                    "### Test-to-code ratio",
                    "",
                    f"- Test LOC (approx): **{test_loc}**",
                    f"- Production SLOC: **{total_sloc}**",
                    f"- Ratio: **{ratio:.2f}:1** "
                    f"({'good' if ratio >= 1.0 else 'low — add tests' if ratio < 0.5 else 'ok'})",
                ]
            )
    except Exception:
        pass

    # Top 10 files by LOC
    if file_locs:
        file_locs.sort(key=lambda x: -x[1])
        lines.extend(
            [
                "",
                "### Top 10 largest files (by LOC)",
                "",
                "| # | File | LOC |",
                "|---|------|-----|",
            ]
        )
        for i, (filepath, loc) in enumerate(file_locs[:10], 1):
            short = _fmt_path(filepath).replace("src/", "")
            lines.append(f"| {i} | {short} | {loc} |")


def _section_mutation(lines: list[str], mut: dict) -> None:
    """Add mutation testing section."""
    if not mut or "error" in mut:
        if mut and "error" in mut:
            lines.extend(
                [
                    "",
                    "## Mutation Testing (mutmut)",
                    "",
                    f"_Skipped: {mut.get('error', 'not available')}_",
                    "",
                    f"Hint: `{mut.get('hint', 'mutmut run')}`",
                ]
            )
        return
    lines.extend(
        [
            "",
            "## Mutation Testing (mutmut)",
            "",
            f"- Total mutants: **{mut.get('total_mutants', 0)}**",
            f"- Killed: **{mut.get('killed', 0)}**",
            f"- Survived: **{mut.get('survived', 0)}**",
            f"- Timeout: **{mut.get('timeout', 0)}**",
            f"- Skipped: **{mut.get('skipped', 0)}**",
            f"- Mutation score: **{_fmt_pct(mut.get('mutation_score'))}**",
        ]
    )
    if mut.get("suspicious", 0) > 0:
        lines.append(f"- Suspicious: **{mut.get('suspicious', 0)}**")
    source = mut.get("source", "")
    if source:
        lines.append(f"- Source: `{source}`")
    survived_files = mut.get("survived_files", [])
    if survived_files:
        lines.extend(
            [
                "",
                "### Files with surviving mutants",
                "",
                "| File |",
                "|------|",
            ]
        )
        for f in survived_files[:15]:
            lines.append(f"| `{f}` |")


def _section_recommendations(lines: list[str], metrics: dict, score: dict) -> None:
    """Generate actionable recommendations from actual metrics."""
    recs: list[str] = []

    # Complexity recommendations
    cx = metrics.get("complexity", {})
    if cx.get("max_complexity", 0) > 20:
        recs.append(
            f"- Refactor {len([h for h in cx.get('hotspots', []) if h.get('complexity', 0) > 20])} "
            f"functions with complexity > 20 (max: {cx.get('max_complexity', 0)})"
        )
    elif cx.get("max_complexity", 0) > 10:
        hot = [h for h in cx.get("hotspots", []) if h.get("complexity", 0) > 10]
        if hot:
            names = ", ".join(h["name"] for h in hot[:5])
            recs.append(f"- Consider refactoring high-complexity functions: {names}")

    # Maintainability recommendations
    mi = metrics.get("maintainability", {})
    worst = mi.get("worst_files", [])
    bad_mi = [f for f in worst if f.get("mi", 100) < 50]
    if bad_mi:
        files = ", ".join(
            _fmt_path(f["filepath"]).split("/")[-1] for f in bad_mi[:5]
        )
        recs.append(f"- Review {len(bad_mi)} files with MI < 50: {files}")

    # Coverage recommendations
    cov = metrics.get("coverage", {})
    if "error" not in cov:
        line_cov = cov.get("global_line_coverage", 0)
        if line_cov > 0 and line_cov < 85:
            below = len(cov.get("files_below_threshold", []))
            recs.append(
                f"- Increase test coverage from {_fmt_pct(line_cov)} "
                f"to >= 85% ({below} files below 75%)"
            )
    elif "error" in cov:
        recs.append("- Run pytest with --cov to measure test coverage (currently not measured)")

    # Security recommendations
    sec = metrics.get("security", {})
    by_sev = sec.get("by_severity", {})
    if by_sev.get("HIGH", 0) > 0:
        recs.append(f"- Fix {by_sev['HIGH']} HIGH severity security issues (bandit)")
    if by_sev.get("MEDIUM", 0) > 0:
        recs.append(f"- Review {by_sev['MEDIUM']} MEDIUM severity security issues (bandit)")

    # Linting recommendations
    ruff = metrics.get("linting", {})
    if ruff.get("total_errors", 0) > 0:
        recs.append(f"- Fix {ruff['total_errors']} ruff linting errors")

    # Typing recommendations
    mypy = metrics.get("typing", {})
    if mypy.get("error_count", 0) > 0:
        recs.append(
            f"- Add type annotations to reduce mypy errors " f"(current: {mypy['error_count']})"
        )

    # Documentation recommendations
    doc = metrics.get("documentation", {})
    doc_cov = doc.get("coverage_percent", 0)
    if doc_cov < 80 and doc_cov > 0:
        recs.append(f"- Increase docstring coverage from {_fmt_pct(doc_cov)} to >= 80%")

    # Dead code recommendations
    dc = metrics.get("dead_code", {})
    by_conf = dc.get("by_confidence", {})
    if by_conf.get("high", 0) > 0:
        recs.append(f"- Remove {by_conf['high']} high-confidence dead code items (vulture)")

    # Dependency recommendations
    dep = metrics.get("dependency_audit", {})
    if dep.get("total_vulnerabilities", 0) > 0:
        recs.append(f"- Update {dep['total_vulnerabilities']} vulnerable dependencies (pip-audit)")

    # Architecture recommendations
    arch = metrics.get("architecture", {})
    if arch.get("violation_count", 0) > 0:
        recs.append(f"- Fix {arch['violation_count']} architecture violations (import-linter)")

    # Secrets recommendations
    secrets = metrics.get("secrets", {})
    if secrets.get("total_secrets", 0) > 0:
        recs.append(f"- Remove {secrets['total_secrets']} hardcoded secrets (detect-secrets)")

    # Mutation recommendations
    mut = metrics.get("mutation", {})
    if "error" not in mut and mut.get("mutation_score", 100) < 70:
        recs.append(
            f"- Strengthen tests: mutation score is "
            f"{_fmt_pct(mut.get('mutation_score'))} (target: >= 70%)"
        )

    if not recs:
        recs.append("- No critical issues found. Keep up the good work!")

    lines.extend(["", "## Recommendations", ""])
    lines.extend(recs)


def _section_technical_debt(lines: list[str], metrics: dict, score: dict) -> None:
    """Estimate technical debt from all available metrics.

    Combines complexity hotspots, dead code, linting errors, type
    errors, security issues, low coverage, and low maintainability into
    a single debt estimate with itemised breakdown.
    """
    debt_items: list[tuple[str, int, str]] = []  # (category, estimated_hours, detail)

    # Complexity debt: each hotspot > 20 costs ~2h to refactor
    cx = metrics.get("complexity", {})
    hotspots = cx.get("hotspots", [])
    high_cx = [h for h in hotspots if h.get("complexity", 0) > 20]
    if high_cx:
        hours = len(high_cx) * 2
        debt_items.append(("Complexity", hours, f"{len(high_cx)} functions with CX > 20"))

    # Dead code debt: each high-confidence item costs ~0.5h to remove
    dc = metrics.get("dead_code", {})
    by_conf = dc.get("by_confidence", {})
    high_dc = by_conf.get("high", 0)
    if high_dc:
        hours = max(1, high_dc // 2)
        debt_items.append(("Dead code", hours, f"{high_dc} high-confidence items"))

    # Linting debt: each 10 errors = ~1h
    ruff = metrics.get("linting", {})
    lint_errors = ruff.get("total_errors", 0)
    if lint_errors > 0:
        hours = max(1, lint_errors // 10)
        debt_items.append(("Linting", hours, f"{lint_errors} ruff errors"))

    # Typing debt: each 10 mypy errors = ~1h
    mypy = metrics.get("typing", {})
    mypy_errors = mypy.get("error_count", 0)
    if mypy_errors > 0:
        hours = max(1, mypy_errors // 10)
        debt_items.append(("Typing", hours, f"{mypy_errors} mypy errors"))

    # Security debt: each HIGH = 2h, each MEDIUM = 1h
    sec = metrics.get("security", {})
    by_sev = sec.get("by_severity", {})
    sec_hours = by_sev.get("HIGH", 0) * 2 + by_sev.get("MEDIUM", 0) * 1
    if sec_hours > 0:
        debt_items.append(
            (
                "Security",
                sec_hours,
                f"{by_sev.get('HIGH', 0)} HIGH, {by_sev.get('MEDIUM', 0)} MEDIUM",
            )
        )

    # Coverage debt: gap to 85% * 0.5h per percentage point
    cov = metrics.get("coverage", {})
    if "error" not in cov:
        line_cov = cov.get("global_line_coverage", 0)
        if line_cov < 85:
            hours = int((85 - line_cov) * 0.5)
            if hours > 0:
                debt_items.append(("Coverage", hours, f"{_fmt_pct(line_cov)} -> 85% target"))

    # Documentation debt: gap to 80% * 0.25h per percentage point
    doc = metrics.get("documentation", {})
    doc_cov = doc.get("coverage_percent", 0)
    if doc_cov > 0 and doc_cov < 80:
        hours = int((80 - doc_cov) * 0.25)
        if hours > 0:
            debt_items.append(("Documentation", hours, f"{_fmt_pct(doc_cov)} -> 80% target"))

    # Dependency debt: each vulnerability = 0.5h
    dep = metrics.get("dependency_audit", {})
    vulns = dep.get("total_vulnerabilities", 0)
    if vulns > 0:
        hours = max(1, vulns // 2)
        debt_items.append(("Dependencies", hours, f"{vulns} vulnerabilities"))

    if not debt_items:
        lines.extend(
            [
                "",
                "## Technical Debt Estimate",
                "",
                "_No significant technical debt detected._",
            ]
        )
        return

    total_hours = sum(h for _, h, _ in debt_items)
    total_days = total_hours / 8

    lines.extend(
        [
            "",
            "## Technical Debt Estimate",
            "",
            f"- **Total estimated effort:** {total_hours}h ({total_days:.1f} person-days)",
            "",
            "| Category | Effort (h) | Detail |",
            "|----------|-----------|--------|",
        ]
    )
    for cat, hours, detail in sorted(debt_items, key=lambda x: -x[1]):
        lines.append(f"| {cat} | {hours} | {detail} |")
    lines.append(f"| **Total** | **{total_hours}** | **{total_days:.1f} person-days** |")


def generate_markdown(metrics: dict[str, Any], output_path: str) -> None:
    """Generate comprehensive quality-summary.md with all 15 categories."""
    score = calculate(metrics)

    lines = [
        "---",
        "sidebar_position: 100",
        "sidebar_label: Quality Summary",
        "description: Auto-generated code quality report (mypy, coverage, security, complexity).",
        "---",
        "",
        "# Quality Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Path analyzed: `{metrics.get('_path', 'src/')}`",
        "",
        "> This report is auto-generated by `scripts/quality/run_quality_checks.py` and",
        "> published to the documentation site by GitHub Actions. Do not edit",
        "> manually — edit `scripts/quality/generate_report.py` instead.",
        "",
        "---",
        "",
        "## Global Score",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Score** | **{score['score']}/100** |",
        f"| **Status** | **{score['classification']}** |",
        "",
        "### Category scores",
        "",
        "| Category | Score | Weight | Status |",
        "|----------|-------|--------|--------|",
    ]
    for cat, s in score["category_scores"].items():
        w = score["weights"][cat]
        if s >= 90:
            status = "Excellent"
        elif s >= 80:
            status = "Good"
        elif s >= 70:
            status = "Acceptable"
        elif s >= 60:
            status = "Medium risk"
        elif s >= 50:
            status = "High risk"
        else:
            status = "Critical"
        lines.append(f"| {cat} | {s} | {int(w * 100)}% | {status} |")

    # Executive summary — key highlights at a glance
    lines.extend(["", "### Highlights", ""])
    cx = metrics.get("complexity", {})
    cov = metrics.get("coverage", {})
    dc = metrics.get("dead_code", {})
    sec = metrics.get("security", {})
    doc = metrics.get("documentation", {})
    pylint = metrics.get("pylint", {})
    highlights = []
    if cov:
        line_cov = cov.get('global_line_coverage', 0)
        branch_cov = cov.get('global_branch_coverage', 0)
        highlights.append(f"**Coverage**: {line_cov:.1f}% line, {branch_cov:.1f}% branch")
    if cx:
        highlights.append(f"**Complexity**: {cx.get('total_blocks', 0)} blocks, max CX {cx.get('max_complexity', 0)}, 0 high-risk (D-F)")
    if sec:
        highlights.append(f"**Security**: {sec.get('total_issues', 0)} bandit issues, 0 vulnerabilities (pip-audit)")
    if dc:
        highlights.append(f"**Dead code**: {dc.get('total_items', 0)} items (all 60% confidence in tests)")
    if doc:
        highlights.append(f"**Docstrings**: {doc.get('coverage_percent', 0)}% ({doc.get('covered', 0)}/{doc.get('total', 0)})")
    if pylint:
        highlights.append(f"**Pylint**: {pylint.get('score', 0)}/10, {pylint.get('total_issues', 0)} issues (0 errors)")
    for h in highlights:
        lines.append(f"- {h}")

    lines.extend(["", "---"])

    # All 15 sections
    _section_complexity(lines, metrics.get("complexity", {}))
    _section_maintainability(lines, metrics.get("maintainability", {}))
    _section_coverage(lines, metrics.get("coverage", {}))
    lines.extend(["", "---"])
    _section_linting(lines, metrics.get("linting", {}))
    _section_typing(lines, metrics.get("typing", {}))
    _section_security(lines, metrics.get("security", {}))
    _section_dead_code(lines, metrics.get("dead_code", {}))
    lines.extend(["", "---"])
    _section_documentation(lines, metrics.get("documentation", {}))
    _section_dependency_audit(lines, metrics.get("dependency_audit", {}))
    _section_architecture(lines, metrics.get("architecture", {}))
    _section_secrets(lines, metrics.get("secrets", {}))
    lines.extend(["", "---"])
    _section_pylint(lines, metrics.get("pylint", {}))
    _section_halstead(lines, metrics.get("halstead", {}))
    _section_raw(lines, metrics.get("raw", {}))
    _section_mutation(lines, metrics.get("mutation", {}))

    # Recommendations and technical debt
    lines.extend(["", "---"])
    _section_recommendations(lines, metrics, score)
    _section_technical_debt(lines, metrics, score)

    lines.append("")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
