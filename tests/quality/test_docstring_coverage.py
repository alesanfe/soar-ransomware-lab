"""Test: docstring coverage (interrogate).

Checks docstring coverage of public modules, classes, and functions.
Reports per-file details and missing docstrings.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
THRESHOLDS = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "quality"
    / "thresholds"
    / "documentation_thresholds.yaml"
)


def _load_thresholds() -> dict:
    if THRESHOLDS.exists():
        with open(THRESHOLDS, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {"min_docstring_coverage": 80}


def _run_interrogate() -> tuple[float, str, int]:
    """Run interrogate and return (coverage_percent, output, returncode)."""
    result = subprocess.run(
        [sys.executable, "-m", "interrogate", "-v", str(SRC_DIR)],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    coverage = 0.0
    for line in output.splitlines():
        if "%" in line and "actual" in line.lower():
            try:
                coverage = float(line.split("%")[0].split()[-1])
            except (ValueError, IndexError):
                pass
    return coverage, output, result.returncode


@pytest.mark.unit
@pytest.mark.quality
class TestDocstringCoverage:
    """Docstring coverage checks."""

    def test_interrogate_coverage(self):
        """Docstring coverage should be >= min threshold."""
        coverage, output, rc = _run_interrogate()
        assert not (
            coverage == 0.0 and rc != 0
        ), "interrogate not available or failed — install interrogate"
        thresholds = _load_thresholds()
        min_cov = thresholds.get("min_docstring_coverage", 80)
        print(f"\nDocstring coverage: {coverage}% (threshold: {min_cov}%)")
        assert coverage >= min_cov, f"Docstring coverage {coverage}% below {min_cov}%"

    def test_missing_docstrings_reported(self):
        """Report files with missing docstrings — informational."""
        coverage, output, rc = _run_interrogate()
        assert not (
            coverage == 0.0 and rc != 0
        ), "interrogate not available or failed — install interrogate"
        # Parse verbose output for files with missing docstrings
        # interrogate verbose format: | Name | Total | Miss | Cover | Cover% |
        missing = []
        for line in output.splitlines():
            if "|" not in line or "---" in line or "Name" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                try:
                    miss_count = int(parts[2])
                    if miss_count > 0:
                        missing.append(line.strip())
                except (ValueError, IndexError):
                    pass
        if missing:
            print(f"\nFiles with missing docstrings ({len(missing)}):")
            for m in missing[:20]:
                print(f"  {m}")
        else:
            print("\nAll public objects have docstrings")
        # Verify coverage < 100% implies missing docstrings
        if coverage < 100.0:
            assert (
                len(missing) > 0
            ), f"Coverage is {coverage}% but no missing docstrings found in output"

    def test_interrogate_returns_summary(self):
        """Interrogate should produce a valid summary line."""
        coverage, output, rc = _run_interrogate()
        assert not (
            rc != 0 and "interrogate" in output.lower() and "not" in output.lower()
        ), "interrogate not installed"
        # Check that output contains a summary
        has_summary = any("actual" in line.lower() and "%" in line for line in output.splitlines())
        assert has_summary, f"interrogate output does not contain summary:\n{output[:500]}"
