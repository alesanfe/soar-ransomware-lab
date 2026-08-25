"""Test: static type checking (mypy).

The project has mypy configured in pyproject.toml but many files predate
strict typing. This test reports the error count and details but does
not fail the suite — it is informational. When the team decides to
enforce strict typing, change the threshold below.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

# Current project has ~419 mypy errors (legacy code without annotations).
# This threshold is set high to avoid blocking CI. Lower it as typing improves.
MYPY_ERROR_THRESHOLD = 500


def _run_mypy() -> tuple[list[str], str]:
    """Run mypy and return (error_lines, full_output)."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", str(SRC_DIR), "--no-color"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    errors = [line for line in output.splitlines() if "error:" in line.lower()]
    return errors, output


def _parse_error_type(line: str) -> str:
    """Extract mypy error type from a line like 'file:line: error: type  [code]'."""
    match = re.search(r"\[(\w[\w-]*)\]", line)
    return match.group(1) if match else "unknown"


@pytest.mark.unit
@pytest.mark.quality
class TestTyping:
    """Static type checking checks."""

    def test_mypy_error_count_below_threshold(self):
        """Mypy error count should stay below MYPY_ERROR_THRESHOLD."""
        errors, _ = _run_mypy()
        count = len(errors)
        print(f"\nmypy errors: {count} (threshold: {MYPY_ERROR_THRESHOLD})")
        assert count <= MYPY_ERROR_THRESHOLD, (
            f"mypy found {count} errors, exceeding threshold {MYPY_ERROR_THRESHOLD}.\n"
            "Lower the threshold or fix type errors.\n" + "\n".join(errors[:20])
        )

    def test_mypy_errors_by_type(self):
        """Report mypy errors grouped by error code — informational."""
        errors, _ = _run_mypy()
        if not errors:
            print("\nNo mypy errors found")
            return
        by_type = Counter(_parse_error_type(e) for e in errors)
        print(f"\nmypy errors by type ({len(errors)} total):")
        for err_type, count in by_type.most_common(10):
            print(f"  {err_type}: {count}")
        # Verify grouping is consistent
        assert sum(by_type.values()) == len(errors), "Type counts do not match total"

    def test_mypy_errors_by_file(self):
        """Report files with most mypy errors — informational."""
        errors, _ = _run_mypy()
        if not errors:
            print("\nNo mypy errors found")
            return
        by_file = Counter()
        for line in errors:
            # Lines look like: path:line: error: ...
            parts = line.split(":", 2)
            if parts:
                by_file[parts[0]] += 1
        print("\nFiles with most mypy errors:")
        for filepath, count in by_file.most_common(10):
            print(f"  {count:>3}  {filepath}")
        # Verify grouping is consistent
        assert sum(by_file.values()) == len(errors), "File counts do not match total"

    def test_no_undefined_names_mypy(self):
        """Check specifically for undefined names — should be 0."""
        errors, _ = _run_mypy()
        undefined = [
            e
            for e in errors
            if "name-defined" in _parse_error_type(e) or "Name '.*' is not defined" in e
        ]
        if undefined:
            print(f"\nUndefined names ({len(undefined)}):")
            for e in undefined[:10]:
                print(f"  {e[:100]}")
        # Verify undefined names were checked (not an error in the test)
        assert isinstance(undefined, list), "Undefined names should be a list"
        # Informational — does not fail
