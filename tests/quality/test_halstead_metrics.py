"""Test: Halstead metrics (radon hal).

Verifies that Halstead metrics are collected and that the aggregate
values are reasonable (volume, difficulty, effort, bugs > 0).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


def _run_radon_hal() -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "radon", "hal", str(SRC_DIR), "-j"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


@pytest.mark.unit
@pytest.mark.quality
class TestHalstead:
    """Halstead metrics checks."""

    def test_halstead_metrics_collected(self):
        """Halstead metrics should be collectable for all source files."""
        data = _run_radon_hal()
        assert isinstance(data, dict), "Expected dict from radon hal"
        assert len(data) > 0, "No Halstead metrics found"

    def test_halstead_totals_are_positive(self):
        """Aggregate Halstead volume, difficulty, and effort should be
        positive."""
        data = _run_radon_hal()
        # Radon hal array: [h1, h2, N1, N2, vocabulary, length, calculated_length,
        #                   volume, difficulty, effort, time, bugs]
        total_volume = 0.0
        total_effort = 0.0
        total_bugs = 0.0
        for filepath, metrics in data.items():
            if isinstance(metrics, dict) and "total" in metrics:
                total = metrics["total"]
                if isinstance(total, list) and len(total) >= 12:
                    total_volume += total[7] if isinstance(total[7], (int, float)) else 0
                    total_effort += total[9] if isinstance(total[9], (int, float)) else 0
                    total_bugs += total[11] if isinstance(total[11], (int, float)) else 0
        assert total_volume > 0, f"Total Halstead volume is {total_volume}, expected > 0"
        assert total_effort > 0, f"Total Halstead effort is {total_effort}, expected > 0"
        assert total_bugs > 0, f"Estimated bugs is {total_bugs}, expected > 0"
        print(
            f"\nHalstead: volume={total_volume:.0f}, "
            f"effort={total_effort:.0f}, bugs={total_bugs:.2f}"
        )

    def test_top_10_effort_functions(self):
        """Report top 10 functions by Halstead effort — informational."""
        data = _run_radon_hal()
        entries = []
        for filepath, metrics in data.items():
            if isinstance(metrics, dict) and "total" in metrics:
                total = metrics["total"]
                if isinstance(total, list) and len(total) >= 12:
                    effort = total[9] if isinstance(total[9], (int, float)) else 0
                    entries.append((filepath, effort))
        entries.sort(key=lambda x: -x[1])
        print("\nTop 10 files by Halstead effort:")
        for f, effort in entries[:10]:
            print(f"  effort={effort:>10.1f}  {f}")
        assert len(entries) > 0, "No Halstead effort data found"
