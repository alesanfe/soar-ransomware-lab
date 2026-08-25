"""Test: global quality score calculation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "quality"
sys.path.insert(0, str(TOOLS_DIR))

from calculate_quality_score import calculate


@pytest.mark.unit
@pytest.mark.quality
class TestQualityScore:
    """Quality score calculation checks."""

    def test_score_calculation_with_good_metrics(self):
        """Score should be high when all metrics are good."""
        metrics = {
            "maintainability": {"average_mi": 90},
            "coverage": {"global_line_coverage": 95},
            "complexity": {"average_complexity": 3},
            "linting": {"total_errors": 0},
            "typing": {"error_count": 0},
            "security": {"by_severity": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}},
            "documentation": {"coverage_percent": 85},
            "architecture": {"violation_count": 0},
        }
        result = calculate(metrics)
        assert result["score"] >= 80, f"Expected score >= 80, got {result['score']}"
        assert result["classification"] in ("Excellent", "Good"), f"Got {result['classification']}"

    def test_score_calculation_with_bad_metrics(self):
        """Score should be low when metrics are bad."""
        metrics = {
            "maintainability": {"average_mi": 30},
            "coverage": {"global_line_coverage": 40},
            "complexity": {"average_complexity": 25},
            "linting": {"total_errors": 50},
            "typing": {"error_count": 20},
            "security": {"by_severity": {"HIGH": 5, "MEDIUM": 10, "LOW": 3}},
            "documentation": {"coverage_percent": 20},
            "architecture": {"violation_count": 15},
        }
        result = calculate(metrics)
        assert result["score"] < 50, f"Expected score < 50, got {result['score']}"
        assert result["classification"] == "Critical", f"Got {result['classification']}"

    def test_score_weights_sum_to_one(self):
        """Score weights should sum to 1.0."""
        metrics = {}
        result = calculate(metrics)
        total_weight = sum(result["weights"].values())
        assert abs(total_weight - 1.0) < 0.001, f"Weights sum to {total_weight}, expected 1.0"
