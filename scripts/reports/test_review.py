#!/usr/bin/env python3
"""Test Review Methodology — SOAR Ransomware Lab.

Genera un informe exhaustivo del estado de la suite de tests aplicando
una metodología estructurada de revisión en 7 dimensiones:

    D1 — Cobertura estructural:    qué porcentaje del código está cubierto
    D2 — Cobertura lógica:         qué porcentaje de mutantes son killed
    D3 — Pirámide de tests:        proporción unit/integration/e2e
    D4 — Salud de tests:           tests flaky, skipped, xfail, timeouts
    D5 — Aislamiento:              tests que dependen de Docker/servicios
    D6 — Complejidad de tests:     tests demasiado largos o complejos
    D7 — Duplicación:              tests duplicados o redundantes

Uso:
    python scripts/reports/test_review.py [--output-dir reports/test-review]
    python scripts/reports/test_review.py --with-coverage   # requiere coverage.xml
    python scripts/reports/test_review.py --with-mutation   # requiere mutmut results
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Helpers ──────────────────────────────────────────────────────────────────


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"
SRC_DIR = PROJECT_ROOT / "src" / "soar_lab"
QUALITY_DIR = PROJECT_ROOT / "quality" / "checks"


def _rel(path: Path) -> str:
    """Return a forward-slash relative path for portable Markdown rendering."""
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def count_test_functions(filepath: Path) -> int:
    """Count `def test_*` functions in a Python file using AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="replace"))
        return sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    except SyntaxError:
        return 0


def count_assertions(filepath: Path) -> int:
    """Count assert statements in a test file using AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="replace"))
        return sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        )
    except SyntaxError:
        return 0


def get_test_markers(filepath: Path) -> list[str]:
    """Extract pytest markers used in a test file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    markers: set[str] = set()
    # @pytest.mark.NAME
    for m in re.finditer(r"@pytest\.mark\.(\w+)", content):
        markers.add(m.group(1))
    # pytestmark = [pytest.mark.NAME]
    for m in re.finditer(r"pytest\.mark\.(\w+)", content):
        markers.add(m.group(1))
    return sorted(markers)


def get_skip_reasons(filepath: Path) -> list[str]:
    """Extract skip/xfail reasons from a test file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    reasons: list[str] = []
    # pytest.skip("reason"), @pytest.mark.skip(reason="..."), @pytest.mark.xfail(reason="...")
    for m in re.finditer(r'(?:pytest\.skip|skip\(reason=|xfail\(reason=)\s*\(\s*["\']([^"\']+)', content):
        reasons.append(m.group(1))
    return reasons


def get_function_length(node: ast.FunctionDef) -> int:
    """Get the number of lines in a function."""
    if hasattr(node, "end_lineno") and node.end_lineno:
        return node.end_lineno - node.lineno + 1
    return 0


def get_long_tests(filepath: Path, threshold: int = 50) -> list[dict[str, Any]]:
    """Find test functions longer than threshold lines."""
    long_tests: list[dict[str, Any]] = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                length = get_function_length(node)
                if length > threshold:
                    long_tests.append({
                        "name": node.name,
                        "line": node.lineno,
                        "length": length,
                        "file": _rel(filepath),
                    })
    except SyntaxError:
        pass
    return long_tests


# ─── Dimension analyzers ──────────────────────────────────────────────────────


def analyze_pyramid() -> dict[str, Any]:
    """D3 — Pirámide de tests: proporción unit/integration/e2e."""
    categories: dict[str, dict[str, int]] = {}

    # Scan tests/ directory
    for subdir in sorted(TESTS_DIR.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        if subdir.name in ("__pycache__", "conftest", "tests"):
            # Skip nested tests/tests/ (artifact from pytest cache or symlinks)
            continue
        cat = subdir.name
        test_files = list(subdir.rglob("test_*.py"))
        # Filter out any files under a nested tests/ directory
        test_files = [f for f in test_files if "tests/tests/" not in str(f).replace("\\", "/")]
        test_count = sum(count_test_functions(f) for f in test_files)
        categories[cat] = {
            "files": len(test_files),
            "tests": test_count,
        }

    # Add quality tests
    quality_files = list(QUALITY_DIR.glob("test_*.py"))
    categories["quality"] = {
        "files": len(quality_files),
        "tests": sum(count_test_functions(f) for f in quality_files),
    }

    total = sum(c["tests"] for c in categories.values())

    # Classify into pyramid layers
    unit_layer = categories.get("unit", {}).get("tests", 0) + categories.get("atomic", {}).get("tests", 0)
    integration_layer = categories.get("integration", {}).get("tests", 0)
    e2e_layer = categories.get("e2e", {}).get("tests", 0)
    other_layer = total - unit_layer - integration_layer - e2e_layer

    # Ideal pyramid: 70% unit, 20% integration, 10% e2e
    ideal = {"unit": 70, "integration": 20, "e2e": 10}
    actual = {
        "unit": round(unit_layer / total * 100, 1) if total else 0,
        "integration": round(integration_layer / total * 100, 1) if total else 0,
        "e2e": round(e2e_layer / total * 100, 1) if total else 0,
        "other": round(other_layer / total * 100, 1) if total else 0,
    }

    # Score: how close to ideal
    deviation = sum(abs(actual.get(k, 0) - ideal.get(k, 0)) for k in ideal) / 2
    score = max(0, 100 - deviation)

    return {
        "categories": categories,
        "total": total,
        "pyramid": {
            "unit": unit_layer,
            "integration": integration_layer,
            "e2e": e2e_layer,
            "other": other_layer,
        },
        "percentages": actual,
        "ideal": ideal,
        "deviation": round(deviation, 1),
        "score": round(score, 1),
    }


def analyze_health() -> dict[str, Any]:
    """D4 — Salud de tests: skipped, xfail, flaky indicators."""
    skipped_count = 0
    xfail_count = 0
    skip_reasons: Counter = Counter()
    files_with_skip: list[str] = []

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        # Count skip decorators and calls
        skips = len(re.findall(r"@pytest\.mark\.skip\b", content))
        skips += len(re.findall(r"pytest\.skip\(", content))
        xfails = len(re.findall(r"@pytest\.mark\.xfail\b", content))

        if skips > 0:
            skipped_count += skips
            files_with_skip.append(_rel(f))
        if xfails > 0:
            xfail_count += xfails

        # Collect skip reasons
        for reason in get_skip_reasons(f):
            skip_reasons[reason] += 1

    return {
        "skipped_total": skipped_count,
        "xfail_total": xfail_count,
        "files_with_skip": files_with_skip,
        "skip_reasons": dict(skip_reasons.most_common(10)),
    }


def analyze_isolation() -> dict[str, Any]:
    """D5 — Aislamiento: tests que dependen de Docker/servicios externos."""
    docker_deps = 0
    external_deps = 0
    files_docker: list[str] = []
    files_external: list[str] = []

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        markers = get_test_markers(f)
        rel = _rel(f)

        if "requires_docker" in markers:
            docker_deps += count_test_functions(f)
            files_docker.append(rel)
        if "requires_external" in markers:
            external_deps += count_test_functions(f)
            files_external.append(rel)

    return {
        "requires_docker": {
            "count": docker_deps,
            "files": files_docker,
        },
        "requires_external": {
            "count": external_deps,
            "files": files_external,
        },
    }


def analyze_complexity() -> dict[str, Any]:
    """D6 — Complejidad de tests: funciones demasiado largas."""
    long_tests: list[dict[str, Any]] = []
    assertions_per_file: list[dict[str, Any]] = []

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        long = get_long_tests(f, threshold=50)
        long_tests.extend(long)

        test_count = count_test_functions(f)
        assert_count = count_assertions(f)
        if test_count > 0:
            assertions_per_file.append({
                "file": _rel(f),
                "tests": test_count,
                "assertions": assert_count,
                "avg_assertions": round(assert_count / test_count, 1) if test_count else 0,
            })

    # Sort by length
    long_tests.sort(key=lambda t: t["length"], reverse=True)

    # Files with low assertion density (potential weak tests)
    weak_tests = [a for a in assertions_per_file if a["avg_assertions"] < 1.5 and a["tests"] >= 3]
    weak_tests.sort(key=lambda a: a["avg_assertions"])

    return {
        "long_tests": long_tests[:20],  # Top 20
        "long_tests_count": len(long_tests),
        "weak_tests": weak_tests[:15],  # Top 15
        "weak_tests_count": len(weak_tests),
    }


def analyze_duplication() -> dict[str, Any]:
    """D7 — Duplicación: nombres de tests duplicados."""
    test_names: dict[str, list[str]] = defaultdict(list)

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            seen_in_file: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    # Avoid counting the same name twice in the same file
                    # (parameterized tests, helper methods, etc.)
                    if node.name not in seen_in_file:
                        seen_in_file.add(node.name)
                        test_names[node.name].append(_rel(f))
        except SyntaxError:
            pass

    duplicates = {
        name: files for name, files in test_names.items()
        if len(files) > 1
    }

    return {
        "total_unique_names": len(test_names),
        "duplicated_names": len(duplicates),
        "duplicates": dict(sorted(duplicates.items())[:20]),
    }


def analyze_coverage(coverage_xml: Path | None = None) -> dict[str, Any]:
    """D1 — Cobertura estructural desde coverage.xml."""
    if coverage_xml is None or not coverage_xml.exists():
        return {"available": False, "message": "coverage.xml not found. Run with --with-coverage."}

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(coverage_xml)
        root = tree.getroot()

        line_rate = float(root.get("line-rate", 0))
        branch_rate = float(root.get("branch-rate", 0))

        # Per-package coverage
        packages = []
        for pkg in root.findall(".//package"):
            name = pkg.get("name", "")
            pkg_line = float(pkg.get("line-rate", 0))
            pkg_branch = float(pkg.get("branch-rate", 0))
            # Check if package has any branch lines
            has_branches = any(
                ln.get("branch") == "true" for ln in pkg.iter("line")
            )
            packages.append({
                "package": name,
                "line_coverage": round(pkg_line * 100, 1),
                "branch_coverage": round(pkg_branch * 100, 1) if has_branches else None,
            })

        packages.sort(key=lambda p: p["line_coverage"])

        return {
            "available": True,
            "line_coverage": round(line_rate * 100, 1),
            "branch_coverage": round(branch_rate * 100, 1),
            "total_files": sum(1 for _ in root.iter("class")),
            "total_lines": int(root.get("lines-valid", 0) or 0),
            "covered_lines": int(root.get("lines-covered", 0) or 0),
            "packages": packages,
            "worst_packages": packages[:10],
            "best_packages": packages[-5:],
        }
    except Exception as exc:
        return {"available": False, "message": f"Error parsing coverage.xml: {exc}"}


def analyze_mutation(mutation_json: Path | None = None) -> dict[str, Any]:
    """D2 — Cobertura lógica desde mutmut results."""
    if mutation_json is None or not mutation_json.exists():
        return {"available": False, "message": "mutation_summary.json not found. Run 'make mutation' first."}

    try:
        data = json.loads(mutation_json.read_text(encoding="utf-8"))
        stats = data.get("stats", {})
        return {
            "available": True,
            "mutation_score": stats.get("mutation_score", 0),
            "killed": stats.get("killed", 0),
            "survived": stats.get("survived", 0),
            "timeout": stats.get("timeout", 0),
            "suspicious": stats.get("suspicious", 0),
            "total": stats.get("total", 0),
            "survived_files": data.get("survived_files", []),
        }
    except Exception as exc:
        return {"available": False, "message": f"Error parsing mutation_summary.json: {exc}"}


# ─── Report generation ────────────────────────────────────────────────────────


def generate_report(
    pyramid: dict[str, Any],
    health: dict[str, Any],
    isolation: dict[str, Any],
    complexity: dict[str, Any],
    duplication: dict[str, Any],
    coverage: dict[str, Any],
    mutation: dict[str, Any],
    output_path: Path,
) -> None:
    """Generate the comprehensive Markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = []

    lines.append("# Test Review Report — SOAR Ransomware Lab")
    lines.append("")
    lines.append(f"Generated: **{now}**")
    lines.append(f"Methodology: 7-dimension structured test review")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── Overall score ─────────────────────────────────────────────────────────
    scores = {
        "D3_Pyramid": pyramid["score"],
    }
    if coverage.get("available"):
        scores["D1_Coverage"] = coverage["line_coverage"]
    if mutation.get("available"):
        scores["D2_Mutation"] = mutation["mutation_score"]

    # Health score: penalize skips and xfails
    total_tests = pyramid["total"]
    skip_penalty = (health["skipped_total"] / total_tests * 100) if total_tests else 0
    xfail_penalty = (health["xfail_total"] / total_tests * 100) if total_tests else 0
    scores["D4_Health"] = round(max(0, 100 - skip_penalty * 5 - xfail_penalty * 2), 1)

    # Isolation score: lower docker/external dependency is better
    docker_ratio = (isolation["requires_docker"]["count"] / total_tests * 100) if total_tests else 0
    external_ratio = (isolation["requires_external"]["count"] / total_tests * 100) if total_tests else 0
    scores["D5_Isolation"] = round(max(0, 100 - docker_ratio * 0.3 - external_ratio * 0.5), 1)

    # Complexity score: penalize long tests
    long_ratio = (complexity["long_tests_count"] / total_tests * 100) if total_tests else 0
    scores["D6_Complexity"] = round(max(0, 100 - long_ratio * 2), 1)

    # Duplication score
    dup_ratio = (duplication["duplicated_names"] / duplication["total_unique_names"] * 100) if duplication["total_unique_names"] else 0
    scores["D7_Duplication"] = round(max(0, 100 - dup_ratio * 3), 1)

    overall = round(sum(scores.values()) / len(scores), 1) if scores else 0

    if overall >= 90:
        status = "Excellent"
    elif overall >= 80:
        status = "Good"
    elif overall >= 70:
        status = "Acceptable"
    elif overall >= 60:
        status = "Medium risk"
    else:
        status = "High risk"

    lines.append("## Overall Score")
    lines.append("")
    lines.append("| Dimension | Score | Status |")
    lines.append("|-----------|-------|--------|")
    # D2 is always shown (even when not available) for completeness
    if not mutation.get("available"):
        lines.append("| D2 Mutation | — | Not available |")
    for dim, score in sorted(scores.items()):
        dim_label = dim.replace("_", " ")
        if score >= 90:
            s = "Excellent"
        elif score >= 80:
            s = "Good"
        elif score >= 70:
            s = "Acceptable"
        elif score >= 60:
            s = "Medium"
        else:
            s = "Critical"
        lines.append(f"| {dim_label} | {score} | {s} |")
    lines.append(f"| **Overall** | **{overall}** | **{status}** |")
    lines.append("")
    lines.extend(["", "---", ""])

    # ─── D1: Coverage ──────────────────────────────────────────────────────────
    lines.append("## D1 — Structural Coverage")
    lines.append("")
    if coverage.get("available"):
        lines.append(f"- **Line coverage**: {coverage['line_coverage']}%")
        lines.append(f"- **Branch coverage**: {coverage['branch_coverage']}%")
        if coverage.get("total_files"):
            lines.append(f"- **Files analyzed**: {coverage['total_files']}")
        if coverage.get("total_lines"):
            lines.append(
                f"- **Lines covered**: {coverage.get('covered_lines', 0)}/{coverage['total_lines']}"
            )
        lines.append("")
        lines.append("### Worst packages (by line coverage)")
        lines.append("")
        lines.append("| Package | Line % | Branch % |")
        lines.append("|---------|--------|----------|")
        for pkg in coverage.get("worst_packages", [])[:10]:
            br = pkg["branch_coverage"]
            br_str = f"{br}%" if br is not None else "—"
            lines.append(f"| `{pkg['package']}` | {pkg['line_coverage']}% | {br_str} |")
        lines.append("")
    else:
        lines.append(f"> ⚠️ {coverage.get('message', 'Not available')}")
        lines.append("")

    # ─── D2: Mutation ──────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D2 — Logic Coverage (Mutation Testing)")
    lines.append("")
    if mutation.get("available"):
        lines.append(f"- **Mutation score**: {mutation['mutation_score']}%")
        lines.append(f"- **Killed**: {mutation['killed']}")
        lines.append(f"- **Survived**: {mutation['survived']}")
        lines.append(f"- **Timeout**: {mutation['timeout']}")
        lines.append(f"- **Suspicious**: {mutation['suspicious']}")
        lines.append(f"- **Total mutants**: {mutation['total']}")
        if mutation.get("survived_files"):
            lines.append("")
            lines.append("### Files with surviving mutants")
            lines.append("")
            for f in mutation["survived_files"]:
                lines.append(f"- `{f}`")
        lines.append("")
    else:
        lines.append(f"> ⚠️ {mutation.get('message', 'Not available')}")
        lines.append("> Run `make mutation` inside Docker to generate mutation testing data.")
        lines.append("")

    # ─── D3: Pyramid ───────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D3 — Test Pyramid")
    lines.append("")
    lines.append(f"- **Total tests**: {pyramid['total']}")
    lines.append(f"- **Pyramid score**: {pyramid['score']}/100 (deviation: {pyramid['deviation']}%)")
    lines.append("")
    lines.append("### Distribution by layer")
    lines.append("")
    lines.append("| Layer | Tests | Actual % | Ideal % |")
    lines.append("|-------|-------|----------|---------|")
    p = pyramid["pyramid"]
    pct = pyramid["percentages"]
    ideal = pyramid["ideal"]
    lines.append(f"| Unit (unit + atomic) | {p['unit']} | {pct['unit']}% | {ideal['unit']}% |")
    lines.append(f"| Integration | {p['integration']} | {pct['integration']}% | {ideal['integration']}% |")
    lines.append(f"| E2E | {p['e2e']} | {pct['e2e']}% | {ideal['e2e']}% |")
    lines.append(f"| Other | {p['other']} | {pct['other']}% | — |")
    lines.append("")
    lines.append("### Distribution by category")
    lines.append("")
    lines.append("| Category | Files | Tests |")
    lines.append("|----------|-------|-------|")
    for cat in sorted(pyramid["categories"]):
        c = pyramid["categories"][cat]
        if c["files"] > 0 or c["tests"] > 0:
            lines.append(f"| {cat} | {c['files']} | {c['tests']} |")
    lines.append("")

    # ─── D4: Health ────────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D4 — Test Health")
    lines.append("")
    lines.append(f"- **Skipped tests**: {health['skipped_total']}")
    lines.append(f"- **XFail tests**: {health['xfail_total']}")
    lines.append(f"- **Files with skips**: {len(health['files_with_skip'])}")
    lines.append(
        f"\n_Static analysis via AST/regex — only `@pytest.mark.skip` "
        f"and `pytest.skip()` calls are detected. Conditional skips "
        f"inside test bodies may not be counted._"
    )
    lines.append("")
    if health["skip_reasons"]:
        lines.append("### Top skip reasons")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|-------|")
        for reason, count in health["skip_reasons"].items():
            lines.append(f"| {reason[:80]} | {count} |")
        lines.append("")

    # ─── D5: Isolation ─────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D5 — Test Isolation")
    lines.append("")
    docker = isolation["requires_docker"]
    external = isolation["requires_external"]
    lines.append(f"- **Requires Docker**: {docker['count']} tests in {len(docker['files'])} files")
    lines.append(f"- **Requires external services**: {external['count']} tests in {len(external['files'])} files")
    lines.append("")
    if docker["files"]:
        lines.append("### Files requiring Docker")
        lines.append("")
        for f in docker["files"][:15]:
            lines.append(f"- `{f}`")
        if len(docker["files"]) > 15:
            lines.append(f"- ... and {len(docker['files']) - 15} more")
        lines.append("")

    if external["files"]:
        lines.append("### Files requiring external services")
        lines.append("")
        for f in external["files"][:15]:
            lines.append(f"- `{f}`")
        if len(external["files"]) > 15:
            lines.append(f"- ... and {len(external['files']) - 15} more")
        lines.append("")

    # ─── D6: Complexity ────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D6 — Test Complexity")
    lines.append("")
    lines.append(f"- **Long tests (>50 lines)**: {complexity['long_tests_count']}")
    lines.append(f"- **Weak tests (<1.5 assertions avg)**: {complexity['weak_tests_count']}")
    lines.append("")
    if complexity["long_tests"]:
        lines.append("### Top 10 longest test functions")
        lines.append("")
        lines.append("| Test | File | Line | Length |")
        lines.append("|------|------|------|--------|")
        for t in complexity["long_tests"][:10]:
            lines.append(f"| `{t['name']}` | `{t['file']}` | {t['line']} | {t['length']} |")
        lines.append("")
    if complexity["weak_tests"]:
        lines.append("### Files with low assertion density (potential weak tests)")
        lines.append("")
        lines.append("| File | Tests | Assertions | Avg/test |")
        lines.append("|------|-------|------------|----------|")
        for t in complexity["weak_tests"][:10]:
            lines.append(f"| `{t['file']}` | {t['tests']} | {t['assertions']} | {t['avg_assertions']} |")
        lines.append("")
    lines.append(
        "_Static analysis via AST — assertion counts are based on `assert` "
        "statements in the source code, not runtime execution._"
    )
    lines.append("")

    # ─── D7: Duplication ───────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## D7 — Test Duplication")
    lines.append("")
    lines.append(f"- **Unique test names**: {duplication['total_unique_names']}")
    lines.append(f"- **Duplicated names**: {duplication['duplicated_names']}")
    lines.append("")
    if duplication["duplicates"]:
        lines.append("### Duplicated test names")
        lines.append("")
        lines.append("| Test name | Files |")
        lines.append("|-----------|-------|")
        for name, files in list(duplication["duplicates"].items())[:15]:
            files_str = ", ".join(f"`{f}`" for f in files[:3])
            if len(files) > 3:
                files_str += f" +{len(files) - 3} more"
            lines.append(f"| `{name}` | {files_str} |")
        total_dups = duplication["duplicated_names"]
        if total_dups > 15:
            lines.append(f"\n_Showing 15 of {total_dups} duplicated names._")
        lines.append("")

    # ─── Recommendations ───────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## Recommendations")
    lines.append("")
    recs: list[str] = []

    if coverage.get("available") and coverage["line_coverage"] < 80:
        recs.append(f"- ❌ **D1 Coverage**: Line coverage is {coverage['line_coverage']}% (target: 80%). Focus on worst packages.")
    elif coverage.get("available"):
        recs.append(f"- ✅ **D1 Coverage**: Line coverage is {coverage['line_coverage']}%.")

    if mutation.get("available") and mutation["survived"] > 0:
        recs.append(f"- ❌ **D2 Mutation**: {mutation['survived']} mutant(s) survived. Add tests to kill them.")
    elif mutation.get("available"):
        recs.append("- ✅ **D2 Mutation**: All mutants killed.")

    if pyramid["deviation"] > 15:
        recs.append(f"- ⚠️ **D3 Pyramid**: Deviation from ideal is {pyramid['deviation']}%. ")
        if pct["unit"] < 60:
            recs.append(f"  Unit tests are only {pct['unit']}% (ideal: 70%). Add more unit tests.")
        if pct["e2e"] > 20:
            recs.append(f"  E2E tests are {pct['e2e']}% (ideal: 10%). Consider converting some to integration tests.")
    else:
        recs.append(f"- ✅ **D3 Pyramid**: Distribution is close to ideal (deviation: {pyramid['deviation']}%).")

    if health["skipped_total"] > total_tests * 0.05:
        recs.append(f"- ⚠️ **D4 Health**: {health['skipped_total']} tests are skipped ({health['skipped_total']/total_tests*100:.1f}%). Review if they can be re-enabled.")
    else:
        recs.append(f"- ✅ **D4 Health**: Only {health['skipped_total']} skipped tests.")

    if docker["count"] > total_tests * 0.3:
        recs.append(f"- ⚠️ **D5 Isolation**: {docker['count']} tests require Docker ({docker['count']/total_tests*100:.1f}%). Consider mocking more services.")
    else:
        recs.append(f"- ✅ **D5 Isolation**: {docker['count']} tests require Docker ({docker['count']/total_tests*100:.1f}%).")

    if complexity["long_tests_count"] > 10:
        recs.append(f"- ⚠️ **D6 Complexity**: {complexity['long_tests_count']} tests are >50 lines. Consider refactoring into smaller tests.")
    else:
        recs.append(f"- ✅ **D6 Complexity**: {complexity['long_tests_count']} long tests.")

    if complexity["weak_tests_count"] > 5:
        recs.append(f"- ⚠️ **D6 Complexity**: {complexity['weak_tests_count']} files have low assertion density (<1.5 avg). Add more assertions to strengthen tests.")

    if duplication["duplicated_names"] > 0:
        recs.append(f"- ⚠️ **D7 Duplication**: {duplication['duplicated_names']} test names are duplicated across files. Consider renaming for clarity.")
    else:
        recs.append("- ✅ **D7 Duplication**: No duplicated test names.")

    if not coverage.get("available"):
        recs.append("- ℹ️ **D1 Coverage**: Run with `--with-coverage` to analyze structural coverage.")
    if not mutation.get("available"):
        recs.append("- ℹ️ **D2 Mutation**: Run `make mutation` in Docker to analyze logic coverage.")

    lines.extend(recs)
    lines.append("")

    # ─── Methodology explanation ───────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## Methodology")
    lines.append("")
    lines.append("This report evaluates the test suite across 7 dimensions:")
    lines.append("")
    lines.append("| Dimension | What it measures | Ideal | Tool |")
    lines.append("|-----------|------------------|-------|------|")
    lines.append("| D1 — Structural coverage | % of code lines/branches executed | ≥80% line, ≥70% branch | coverage.py |")
    lines.append("| D2 — Logic coverage (mutation) | % of mutations killed by tests | ≥90% | mutmut |")
    lines.append("| D3 — Test pyramid | Proportion unit/integration/e2e | 70/20/10 | AST analysis |")
    lines.append("| D4 — Test health | Skipped, xfail, flaky tests | <5% skipped | AST + regex |")
    lines.append("| D5 — Isolation | Tests depending on Docker/external | <30% Docker | pytest markers |")
    lines.append("| D6 — Complexity | Long tests, low assertion density | <10 long, >2 avg assertions | AST analysis |")
    lines.append("| D7 — Duplication | Duplicated test names | 0 duplicates | AST analysis |")
    lines.append("")
    lines.append("### Scoring")
    lines.append("")
    lines.append("Each dimension produces a 0-100 score. The overall score is the arithmetic mean.")
    lines.append("Dimensions D1 and D2 are optional (require external data sources).")
    lines.append("")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report generated: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a comprehensive test review report (7-dimension methodology)."
    )
    parser.add_argument(
        "--output-dir",
        default="reports/test-review",
        help="Output directory (default: reports/test-review)",
    )
    parser.add_argument(
        "--with-coverage",
        action="store_true",
        help="Include D1 structural coverage analysis (requires reports/coverage/coverage.xml)",
    )
    parser.add_argument(
        "--with-mutation",
        action="store_true",
        help="Include D2 mutation testing analysis (requires reports/mutmut/mutation_summary.json)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("==> Analyzing D3 — Test Pyramid...")
    pyramid = analyze_pyramid()
    print(f"    Total tests: {pyramid['total']} | Score: {pyramid['score']}")

    print("==> Analyzing D4 — Test Health...")
    health = analyze_health()
    print(f"    Skipped: {health['skipped_total']} | XFail: {health['xfail_total']}")

    print("==> Analyzing D5 — Test Isolation...")
    isolation = analyze_isolation()
    print(f"    Docker: {isolation['requires_docker']['count']} | External: {isolation['requires_external']['count']}")

    print("==> Analyzing D6 — Test Complexity...")
    complexity = analyze_complexity()
    print(f"    Long tests: {complexity['long_tests_count']} | Weak tests: {complexity['weak_tests_count']}")

    print("==> Analyzing D7 — Test Duplication...")
    duplication = analyze_duplication()
    print(f"    Unique names: {duplication['total_unique_names']} | Duplicated: {duplication['duplicated_names']}")

    coverage = {"available": False}
    if args.with_coverage:
        print("==> Analyzing D1 — Structural Coverage...")
        coverage = analyze_coverage(PROJECT_ROOT / "reports" / "coverage" / "coverage.xml")
        if coverage.get("available"):
            print(f"    Line: {coverage['line_coverage']}% | Branch: {coverage['branch_coverage']}%")
        else:
            print(f"    {coverage.get('message', 'Not available')}")

    mutation = {"available": False}
    if args.with_mutation:
        print("==> Analyzing D2 — Mutation Testing...")
        mutation = analyze_mutation(PROJECT_ROOT / "reports" / "mutmut" / "mutation_summary.json")
        if mutation.get("available"):
            print(f"    Score: {mutation['mutation_score']}% | Survived: {mutation['survived']}")
        else:
            print(f"    {mutation.get('message', 'Not available')}")

    print("==> Generating report...")
    report_path = output_dir / "test_review_report.md"
    generate_report(
        pyramid=pyramid,
        health=health,
        isolation=isolation,
        complexity=complexity,
        duplication=duplication,
        coverage=coverage,
        mutation=mutation,
        output_path=report_path,
    )

    # Save JSON summary
    json_path = output_dir / "test_review_summary.json"
    json_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).isoformat(),
                "pyramid": pyramid,
                "health": {
                    "skipped_total": health["skipped_total"],
                    "xfail_total": health["xfail_total"],
                    "skip_reasons": health["skip_reasons"],
                },
                "isolation": {
                    "requires_docker": isolation["requires_docker"]["count"],
                    "requires_external": isolation["requires_external"]["count"],
                },
                "complexity": {
                    "long_tests_count": complexity["long_tests_count"],
                    "weak_tests_count": complexity["weak_tests_count"],
                },
                "duplication": {
                    "total_unique_names": duplication["total_unique_names"],
                    "duplicated_names": duplication["duplicated_names"],
                },
                "coverage": coverage if coverage.get("available") else None,
                "mutation": mutation if mutation.get("available") else None,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"==> Done! Report: {report_path}")
    print(f"    JSON summary: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
