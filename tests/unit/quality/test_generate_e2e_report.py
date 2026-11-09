#!/usr/bin/env python3
"""Unit tests for scripts/reports/generate_e2e_report.py.

BUG-029: ``mttd_median`` used ``sorted(v)[len(v)//2]`` — the upper-middle
element — instead of the true median (mean of the two central values for
even-length samples), silently overstating MTTD.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "generate_e2e_report", ROOT / "scripts" / "reports" / "generate_e2e_report.py"
)
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def _mttd_payload(diffs: list[float]) -> dict:
    """soar-alerts hits producing the given MTTD diffs (seconds)."""
    hits = []
    for i, diff in enumerate(diffs):
        ts = f"2024-01-01T00:{i:02d}:00"
        dt = f"2024-01-01T00:{i:02d}:{int(diff):02d}"
        hits.append({"_source": {"detection_time": dt, "timestamp": ts}})
    return {"hits": {"hits": hits}}


class TestMttdMedian:
    def test_even_sample_uses_true_median(self):
        """[10,20,30,40] -> real median 25.0, not upper element 30."""

        def fake_es_post(index, body):
            if index == "soar-alerts" and "detection_time" in str(body):
                return _mttd_payload([10, 20, 30, 40])
            return {}

        with patch.object(report, "_es_post", side_effect=fake_es_post):
            result = report.fetch_security_metrics()
        assert result["mttd_median"] == 25.0

    def test_odd_sample_unaffected(self):
        def fake_es_post(index, body):
            if index == "soar-alerts" and "detection_time" in str(body):
                return _mttd_payload([10, 20, 30])
            return {}

        with patch.object(report, "_es_post", side_effect=fake_es_post):
            result = report.fetch_security_metrics()
        assert result["mttd_median"] == 20
