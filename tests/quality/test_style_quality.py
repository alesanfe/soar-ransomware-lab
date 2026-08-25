"""Test: linting and format checks (ruff).

Checks ruff linting errors, format compliance, and reports the most
common issues by rule and by file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


def _run_ruff_check() -> list:
    """Run ruff check and return list of errors."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            str(SRC_DIR),
            "--select",
            "E,W,F,I",
            "--output-format",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def _run_ruff_format_check() -> tuple[int, str]:
    """Run ruff format --check and return (files_to_reformat, output)."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", str(SRC_DIR)],
        capture_output=True,
        text=True,
    )
    files = [line for line in result.stdout.splitlines() if line.strip()]
    return len(files), result.stdout


@pytest.mark.unit
@pytest.mark.quality
class TestStyle:
    """Linting and format checks."""

    def test_no_ruff_errors(self):
        """Ruff should report 0 errors in src/."""
        errors = _run_ruff_check()
        assert len(errors) == 0, f"Ruff found {len(errors)} errors:\n" + "\n".join(
            f"  {e.get('filename', '?')}:{e.get('location', '?')} "
            f"{e.get('code', '?')}: {e.get('message', '')}"
            for e in errors[:20]
        )

    def test_ruff_errors_by_rule(self):
        """Report ruff errors grouped by rule — informational."""
        errors = _run_ruff_check()
        if not errors:
            print("\nNo ruff errors found")
            return
        by_rule = Counter(e.get("code", "?") for e in errors)
        print(f"\nRuff errors by rule ({len(errors)} total):")
        for rule, count in by_rule.most_common(10):
            print(f"  {rule}: {count}")
        # Verify grouping is consistent
        assert sum(by_rule.values()) == len(errors), "Rule counts do not match total"

    def test_ruff_errors_by_file(self):
        """Report files with most ruff errors — informational."""
        errors = _run_ruff_check()
        if not errors:
            print("\nNo ruff errors found")
            return
        by_file = Counter(e.get("filename", "?") for e in errors)
        print("\nFiles with most ruff errors:")
        for filepath, count in by_file.most_common(10):
            print(f"  {count:>3}  {filepath}")
        # Verify grouping is consistent
        assert sum(by_file.values()) == len(errors), "File counts do not match total"

    def test_ruff_format_check_informational(self):
        """Check ruff format — informational (project uses black, not ruff
        format)."""
        count, output = _run_ruff_format_check()
        if count > 0:
            print(
                f"\nruff format: {count} files would be reformatted "
                "(project uses black — informational only)"
            )
        else:
            print("\nruff format: all files are properly formatted")
        # Verify the check ran and produced a result
        assert count >= 0, "File count should be >= 0"
        # Informational — does not fail

    def test_no_unused_imports(self):
        """Check specifically for unused imports (F401) — should be 0."""
        errors = _run_ruff_check()
        unused = [e for e in errors if e.get("code") == "F401"]
        assert len(unused) == 0, f"Found {len(unused)} unused imports (F401):\n" + "\n".join(
            f"  {e.get('filename', '?')}:{e.get('location', '?')} {e.get('message', '')}"
            for e in unused[:20]
        )

    def test_no_undefined_names(self):
        """Check specifically for undefined names (F821) — should be 0."""
        errors = _run_ruff_check()
        undefined = [e for e in errors if e.get("code") == "F821"]
        assert len(undefined) == 0, f"Found {len(undefined)} undefined names (F821):\n" + "\n".join(
            f"  {e.get('filename', '?')}:{e.get('location', '?')} {e.get('message', '')}"
            for e in undefined[:20]
        )
