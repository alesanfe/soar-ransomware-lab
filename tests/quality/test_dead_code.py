"""Test: dead code detection (vulture).

Uses the parse_vulture tool to parse vulture output. Fails on high-
confidence (>=90%) dead code; reports medium/low as informational.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
TOOLS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "quality"
sys.path.insert(0, str(TOOLS_DIR))

from parse_vulture import parse as parse_vulture


@pytest.mark.unit
@pytest.mark.quality
class TestDeadCode:
    """Dead code detection checks."""

    def test_no_high_confidence_dead_code(self):
        """Vulture should find 0 items with confidence >= 90%."""
        result = parse_vulture(str(SRC_DIR))
        assert "error" not in result, f"Vulture parsing error: {result.get('error', '')}"
        by_conf = result.get("by_confidence", {})
        high = by_conf.get("high", 0)
        assert high == 0, f"Vulture found {high} high-confidence dead code items:\n" + "\n".join(
            f"  {i.get('file', '?')}:{i.get('line', '?')} {i.get('description', '')[:80]}"
            for i in result.get("items", [])
            if "90%" in i.get("description", "")
        )

    def test_dead_code_reported(self):
        """Report dead code items — informational."""
        result = parse_vulture(str(SRC_DIR))
        assert "error" not in result, f"Vulture parsing error: {result.get('error', '')}"
        total = result.get("total_items", 0)
        by_conf = result.get("by_confidence", {})
        print(f"\nVulture: {total} items")
        print(f"  High (>=90%): {by_conf.get('high', 0)}")
        print(f"  Medium (60-89%): {by_conf.get('medium', 0)}")
        print(f"  Low (<60%): {by_conf.get('low', 0)}")
        for item in result.get("items", [])[:15]:
            f = item.get("file", "?")
            ln = item.get("line", "?")
            desc = item.get("description", "")[:70]
            print(f"  {f}:{ln} {desc}")
        # Verify confidence counts are consistent
        total_by_conf = by_conf.get("high", 0) + by_conf.get("medium", 0) + by_conf.get("low", 0)
        assert (
            total_by_conf == total
        ), f"Confidence counts ({total_by_conf}) != total items ({total})"
        # Informational — does not fail on medium/low confidence
