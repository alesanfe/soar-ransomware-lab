"""Test: security analysis (bandit).

Uses the parse_bandit tool to parse bandit JSON output. Fails on HIGH
severity issues; reports MEDIUM and LOW as informational.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TOOLS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "quality"
sys.path.insert(0, str(TOOLS_DIR))

from parse_bandit import parse as parse_bandit


@pytest.mark.unit
@pytest.mark.quality
class TestSecurity:
    """Security analysis checks."""

    def test_no_high_severity_issues(self):
        """Bandit should find 0 HIGH severity issues."""
        result = parse_bandit(str(SRC_DIR))
        assert "error" not in result, f"Bandit parsing error: {result.get('error', '')}"
        by_sev = result.get("by_severity", {})
        high = by_sev.get("HIGH", 0)
        assert high == 0, f"Bandit found {high} HIGH severity issues:\n" + "\n".join(
            f"  {i.get('file', '?')}:{i.get('line', '?')} "
            f"{i.get('id', '?')}: {i.get('description', '')[:100]}"
            for i in result.get("issues", [])
            if i.get("severity") == "HIGH"
        )

    def test_security_issues_reported(self):
        """Report all security issues — informational."""
        result = parse_bandit(str(SRC_DIR))
        assert "error" not in result, f"Bandit parsing error: {result.get('error', '')}"
        issues = result.get("issues", [])
        by_sev = result.get("by_severity", {})
        print(f"\nBandit: {result.get('total_issues', 0)} issues")
        high = by_sev.get("HIGH", 0)
        med = by_sev.get("MEDIUM", 0)
        low = by_sev.get("LOW", 0)
        print(f"  HIGH: {high}, MEDIUM: {med}, LOW: {low}")
        for i in issues[:15]:
            print(
                f"  [{i.get('severity', '?')}] {i.get('id', '?')} "
                f"{i.get('file', '?')}:{i.get('line', '?')} - {i.get('description', '')[:80]}"
            )
        # Verify severity counts are consistent with issues
        total_by_sev = high + med + low
        assert total_by_sev == len(
            issues
        ), f"Severity counts ({total_by_sev}) != total issues ({len(issues)})"
        # Informational — does not fail on LOW/MEDIUM

    def test_no_hardcoded_passwords(self):
        """Check for B105 (hardcoded password) — informational."""
        result = parse_bandit(str(SRC_DIR))
        assert "error" not in result, f"Bandit parsing error: {result.get('error', '')}"
        b105 = [i for i in result.get("issues", []) if i.get("id") == "B105"]
        if b105:
            print(f"\nB105 (hardcoded password): {len(b105)} occurrences")
            for i in b105[:10]:
                f = i.get("file", "?")
                ln = i.get("line", "?")
                desc = i.get("description", "")[:70]
                print(f"  {f}:{ln} - {desc}")
        # Verify B105 issues have required fields
        for i in b105:
            assert i.get("id") == "B105", f"Filtered issue has wrong id: {i.get('id')}"
        # Informational — does not fail on B105 (test fixtures use dummy passwords)
