"""Test: cyclomatic complexity per function, file, and project (radon cc).

Thresholds from scripts/quality/thresholds/complexity_thresholds.yaml:
  max_complexity_per_function: 20  (fail)
  warn_complexity_per_function: 10 (warn)
  fail_grades: D, E, F
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
THRESHOLDS_FILE = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "quality"
    / "thresholds"
    / "complexity_thresholds.yaml"
)


def _load_thresholds() -> dict:
    """Load complexity thresholds from YAML."""
    import yaml

    with open(THRESHOLDS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_radon_cc() -> dict:
    """Run radon cc on src/ and return JSON data."""
    result = subprocess.run(
        [sys.executable, "-m", "radon", "cc", str(SRC_DIR), "-j"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _get_all_blocks(data: dict) -> list[dict]:
    """Flatten radon cc output into a list of blocks with filepath."""
    blocks = []
    for filepath, file_blocks in data.items():
        for b in file_blocks:
            b["filepath"] = filepath
            blocks.append(b)
    return blocks


@pytest.mark.unit
@pytest.mark.quality
class TestComplexityProject:
    """Project-level complexity checks."""

    def test_no_function_exceeds_max_complexity(self):
        """No function should exceed max_complexity_per_function (20)."""
        thresholds = _load_thresholds()
        max_cx = thresholds["max_complexity_per_function"]
        data = _run_radon_cc()
        blocks = _get_all_blocks(data)
        violators = [b for b in blocks if b.get("complexity", 0) > max_cx]
        assert (
            not violators
        ), f"{len(violators)} functions exceed max complexity {max_cx}:\n" + "\n".join(
            f"  {b['filepath']}:{b.get('lineno', '?')} {b['name']} (cx={b['complexity']})"
            for b in violators[:20]
        )

    def test_no_function_has_fail_grade(self):
        """No function should have grade D, E, or F."""
        thresholds = _load_thresholds()
        fail_grades = set(thresholds["fail_grades"])
        data = _run_radon_cc()
        blocks = _get_all_blocks(data)
        violators = [b for b in blocks if b.get("rank", "A") in fail_grades]
        assert (
            not violators
        ), f"{len(violators)} functions have fail grades {fail_grades}:\n" + "\n".join(
            f"  {b['filepath']}:{b.get('lineno', '?')} {b['name']} "
            f"(grade={b['rank']}, cx={b['complexity']})"
            for b in violators[:20]
        )

    def test_average_complexity_below_threshold(self):
        """Project average complexity should be below max_avg_complexity."""
        thresholds = _load_thresholds()
        max_avg = thresholds["max_avg_complexity"]
        data = _run_radon_cc()
        blocks = _get_all_blocks(data)
        avg = sum(b.get("complexity", 0) for b in blocks) / len(blocks) if blocks else 0
        assert avg <= max_avg, f"Average complexity {avg:.2f} exceeds threshold {max_avg}"

    def test_complexity_grade_distribution(self):
        """Report grade distribution — informational, does not fail."""
        data = _run_radon_cc()
        blocks = _get_all_blocks(data)
        grades = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
        for b in blocks:
            g = b.get("rank", "A")
            grades[g] = grades.get(g, 0) + 1
        total = len(blocks)
        print(f"\nGrade distribution ({total} blocks): {grades}")
        print(f"  A: {grades['A']} ({grades['A'] / total * 100:.1f}%)")
        print(f"  B: {grades['B']} ({grades['B'] / total * 100:.1f}%)")
        print(f"  C: {grades['C']} ({grades['C'] / total * 100:.1f}%)")
        print(f"  D: {grades['D']} ({grades['D'] / total * 100:.1f}%)")
        print(f"  E: {grades['E']} ({grades['E'] / total * 100:.1f}%)")
        print(f"  F: {grades['F']} ({grades['F'] / total * 100:.1f}%)")
        assert total > 0, "No code blocks found"


@pytest.mark.unit
@pytest.mark.quality
class TestComplexityFiles:
    """Per-file complexity checks."""

    def test_top_10_most_complex_functions(self):
        """Report top 10 most complex functions — informational."""
        data = _run_radon_cc()
        blocks = _get_all_blocks(data)
        blocks.sort(key=lambda x: -x.get("complexity", 0))
        print("\nTop 10 most complex functions:")
        for b in blocks[:10]:
            print(
                f"  [{b.get('rank', '?')}] cx={b.get('complexity', 0):>3}  "
                f"{b['filepath']}:{b.get('lineno', '?')} {b.get('name', '?')}"
            )
        assert len(blocks) >= 10, "Expected at least 10 functions"

    def test_no_file_has_excessive_average(self):
        """No file should have average complexity > 15."""
        data = _run_radon_cc()
        file_violators = []
        for filepath, blocks in data.items():
            if not blocks:
                continue
            avg = sum(b.get("complexity", 0) for b in blocks) / len(blocks)
            if avg > 15:
                file_violators.append((filepath, avg))
        assert (
            not file_violators
        ), f"{len(file_violators)} files have average complexity > 15:\n" + "\n".join(
            f"  {f}: avg={a:.2f}" for f, a in file_violators[:20]
        )
