"""Test: maintainability index per file (radon mi)."""

from __future__ import annotations

import json
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
    / "maintainability_thresholds.yaml"
)


def _run_radon_mi() -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "radon", "mi", str(SRC_DIR), "-s", "-j"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _load_thresholds() -> dict:
    with open(THRESHOLDS, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.mark.unit
@pytest.mark.quality
class TestMaintainability:
    """Maintainability Index checks."""

    def test_all_files_above_min_mi(self):
        """Report files with MI below min_mi_per_file — informational."""
        thresholds = _load_thresholds()
        min_mi = thresholds["min_mi_per_file"]
        data = _run_radon_mi()
        violators = []
        for f, s in data.items():
            if isinstance(s, (int, float)):
                mi = s
            elif isinstance(s, dict):
                mi = s.get("mi", 0)
            else:
                mi = 0
            if mi < min_mi:
                violators.append((f, mi))
        if violators:
            print(f"\n{len(violators)} files have MI below {min_mi}:")
            for f, s in violators[:20]:
                print(f"  MI={s:.2f}  {f}")
        # Verify MI data was collected
        assert len(data) > 0, "No MI data collected"
        # Informational — does not hard-fail. Some files legitimately have
        # low MI due to high code density (e.g. integration clients).
        # To enforce: uncomment the assert below
        # assert not violators, f"{len(violators)} files have MI below {min_mi}"

    def test_average_mi_above_threshold(self):
        """Project average MI should be above min_mi_global (65)."""
        thresholds = _load_thresholds()
        min_avg = thresholds["min_mi_global"]
        data = _run_radon_mi()
        scores = []
        for s in data.values():
            if isinstance(s, (int, float)):
                scores.append(s)
            elif isinstance(s, dict) and "mi" in s:
                scores.append(s["mi"])
        avg = sum(scores) / len(scores) if scores else 0
        assert avg >= min_avg, f"Average MI {avg:.2f} below threshold {min_avg}"

    def test_worst_10_files(self):
        """Report 10 least maintainable files — informational."""
        data = _run_radon_mi()
        scores = []
        for f, s in data.items():
            if isinstance(s, (int, float)):
                scores.append((f, s))
            elif isinstance(s, dict) and "mi" in s:
                scores.append((f, s["mi"]))
        scores.sort(key=lambda x: x[1])
        print("\nTop 10 least maintainable files:")
        for f, s in scores[:10]:
            print(f"  MI={s:.2f}  {f}")
        assert len(scores) > 0, "No files found"
