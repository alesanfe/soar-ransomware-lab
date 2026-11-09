#!/usr/bin/env python3
"""Unit tests for soar_lab.domain.statistical_calculator."""

from datetime import UTC, datetime, timedelta

import pytest

from soar_lab.domain.statistical_calculator import StatisticalCalculator


class TestStatisticalCalculator:
    """Test StatisticalCalculator pure domain logic."""

    def test_calculate_statistical_metrics_empty_list(self):
        """Test with empty list returns zeros."""
        result = StatisticalCalculator.calculate_statistical_metrics([])
        assert result["mean"] == 0
        assert result["median"] == 0
        assert result["std_dev"] == 0
        assert result["min"] == 0
        assert result["max"] == 0
        assert result["total_executions"] == 0
        assert result["p50"] == 0
        assert result["p90"] == 0
        assert result["mttr_seconds"] == 0
        assert result["mttr_minutes"] == 0

    def test_calculate_statistical_metrics_single_value(self):
        """Test with single value."""
        result = StatisticalCalculator.calculate_statistical_metrics([5.0])
        assert result["mean"] == 5.0
        assert result["median"] == 5.0
        assert result["std_dev"] == 0
        assert result["min"] == 5.0
        assert result["max"] == 5.0

    def test_calculate_statistical_metrics_multiple_values(self):
        """Test with multiple values."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result["mean"] == 3.0
        assert result["median"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["std_dev"] > 0

    def test_calculate_statistical_metrics_invalid_times(self):
        """Test with invalid times (all filtered out)"""
        values = [0.0, -1.0, 4000.0]  # All invalid
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result["total_executions"] == 0
        assert result["mean"] == 0.0

    def test_calculate_statistical_metrics_mixed_valid_invalid(self):
        """Test with mixed valid and invalid times."""
        values = [0.0, 1.0, 2.0, 3600.0, 3.0]  # 0, 3600 invalid
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result["total_executions"] == 3  # Only 1.0, 2.0, 3.0 valid
        assert result["mean"] == 2.0

    def test_calculate_statistical_metrics_percentiles(self):
        """Test percentile calculations."""
        values = list(range(100))
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result["p50"] == pytest.approx(49.5, rel=0.1)
        assert result["p90"] == pytest.approx(89, rel=0.1)

    def test_calculate_statistical_metrics_returns_dict(self):
        """Test returns dictionary with expected keys."""
        result = StatisticalCalculator.calculate_statistical_metrics([1.0, 2.0, 3.0])
        expected_keys = [
            "mean",
            "median",
            "std_dev",
            "min",
            "max",
            "p50",
            "p90",
            "total_executions",
            "mttr_seconds",
            "mttr_minutes",
        ]
        for key in expected_keys:
            assert key in result

    def test_calculate_health_score_excellent(self):
        """Test health score calculation for excellent status."""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=10, memory_percent=20, disk_percent=30, test_coverage=90
        )
        assert result["overall_score"] >= 80
        assert result["status"] == "excellent"
        assert result["components"]["cpu"] == 90
        assert result["components"]["memory"] == 80
        assert result["components"]["disk"] == 70
        assert result["components"]["tests"] == 90

    def test_calculate_health_score_good(self):
        """Test health score calculation for good status."""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=30, memory_percent=40, disk_percent=50, test_coverage=70
        )
        assert 60 <= result["overall_score"] < 80
        assert result["status"] == "good"

    def test_calculate_health_score_warning(self):
        """Test health score calculation for warning status."""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=50, memory_percent=60, disk_percent=70, test_coverage=60
        )
        assert 40 <= result["overall_score"] < 60
        assert result["status"] == "warning"

    def test_calculate_health_score_critical(self):
        """Test health score calculation for critical status."""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=90, memory_percent=95, disk_percent=98, test_coverage=10
        )
        assert result["overall_score"] < 40
        assert result["status"] == "critical"

    def test_calculate_execution_times_valid_data(self):
        """Test execution times calculation with valid data."""
        now = datetime.now(UTC)
        alert_steps = {
            "Alert received": [now, now + timedelta(seconds=10)],
            "Containment executed": [now + timedelta(seconds=5), now + timedelta(seconds=15)],
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 2
        assert result[0] == 5.0
        assert result[1] == 5.0

    def test_calculate_execution_times_missing_alerts(self):
        """Test execution times calculation with missing alerts."""
        alert_steps = {"Alert received": [], "Containment executed": [datetime.now(UTC)]}
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []

    def test_calculate_execution_times_missing_containment(self):
        """Test execution times calculation with missing containment."""
        alert_steps = {"Alert received": [datetime.now(UTC)], "Containment executed": []}
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []

    def test_calculate_execution_times_mismatched_lengths(self):
        """Test execution times calculation with mismatched lengths."""
        now = datetime.now(UTC)
        alert_steps = {
            "Alert received": [now, now + timedelta(seconds=10), now + timedelta(seconds=20)],
            "Containment executed": [now + timedelta(seconds=5)],
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 1  # Only one pair
        assert result[0] == 5.0

    def test_calculate_execution_times_negative_delta(self):
        """Test execution times calculation with negative delta (filtered
        out)"""
        now = datetime.now(UTC)
        alert_steps = {
            "Alert received": [now + timedelta(seconds=10)],
            "Containment executed": [now + timedelta(seconds=5)],
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []  # Negative delta filtered out

    def test_calculate_execution_times_started_passed_pairs(self):
        """Test execution times calculation with STARTED/PASSED pairs."""
        now = datetime.now(UTC)
        alert_steps = {
            "STEP 1 STARTED": [now, now + timedelta(seconds=10)],
            "STEP 1 PASSED": [now + timedelta(seconds=5), now + timedelta(seconds=15)],
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 2
        assert result[0] == 5.0
        assert result[1] == 5.0

    def test_calculate_execution_times_step1_keys_not_computable(self):
        """M-005 regression: step1-only keys yield NO execution times.

        The old fallback measured inter-ARRIVAL deltas and reported them as
        execution times — a semantically wrong MTTR. Now the metric is
        honestly uncomputable (empty), never silently substituted.
        """
        now = datetime.now(UTC)
        alert_steps = {
            "Sending alert": [now, now + timedelta(seconds=10), now + timedelta(seconds=20)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []

    def test_inter_arrival_times_available_as_named_api(self):
        """The arrival-rate helper still exists, explicitly named (M-005)."""
        now = datetime.now(UTC)
        steps = {"Sending alert": [now, now + timedelta(seconds=10), now + timedelta(seconds=20)]}
        arrival = StatisticalCalculator.inter_arrival_times(steps, ["Sending alert"])
        assert len(arrival) == 2

    def test_calculate_statistical_metrics_p90_idx_edge_case(self):
        """Test p90 calculation with edge case where p90_idx could be
        negative."""
        # This tests line 61 where p90_idx < 0 check happens
        result = StatisticalCalculator.calculate_statistical_metrics([1.0])
        assert result["p90"] == 1.0  # With single value, p90 should be that value


class TestGoldenStatisticalMetrics:
    """Mutation-hardening: exact output dicts kill round()/key/arith mutants."""

    DATA = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    def test_metrics_exact_dict(self):
        assert StatisticalCalculator.calculate_statistical_metrics(self.DATA) == {
            "total_executions": 10,
            "mean": 55,
            "median": 55.0,
            "p50": 55.0,
            "p90": 91.0,
            "p95": 95.5,
            "p99": 99.1,
            "min": 10,
            "max": 100,
            "std_dev": 30.28,
            "mttr_seconds": 55,
            "mttr_minutes": 0.92,
        }

    def test_metrics_filters_invalid_times(self):
        # 0, negatives, and >3600 dropped from the sample
        r = StatisticalCalculator.calculate_statistical_metrics([0, -5, 3700, 10, 20])
        assert r["total_executions"] == 2
        assert r["mean"] == 15

    def test_metrics_all_invalid_returns_empty_shape(self):
        r = StatisticalCalculator.calculate_statistical_metrics([0, -1, 4000])
        assert r["total_executions"] == 0
        assert r["mean"] == 0.0 and r["p99"] == 0.0

    def test_metrics_single_value(self):
        r = StatisticalCalculator.calculate_statistical_metrics([5.0])
        assert r["total_executions"] == 1
        assert r["std_dev"] == 0.0
        assert r["mean"] == 5

    def test_health_score_exact(self):
        assert StatisticalCalculator.calculate_health_score(20, 30, 40, 90) == {
            "overall_score": 75.0,
            "status": "good",
            "components": {"cpu": 80, "memory": 70, "disk": 60, "tests": 90},
        }

    def test_health_score_status_boundaries(self):
        assert StatisticalCalculator.calculate_health_score(0, 0, 0, 100)["status"] == ("excellent")
        assert StatisticalCalculator.calculate_health_score(40, 40, 40, 0)["status"] == ("warning")
        assert StatisticalCalculator.calculate_health_score(100, 100, 100, 0)["status"] == (
            "critical"
        )

    def test_health_score_clamps_negative(self):
        r = StatisticalCalculator.calculate_health_score(150, 150, 150, 0)
        assert r["components"]["cpu"] == 0
        assert r["components"]["memory"] == 0
        assert r["components"]["disk"] == 0

    def test_execution_times_paired(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1, 0, 0, 0)
        steps = {
            "Alert received": [t0, t0 + timedelta(minutes=10)],
            "Containment executed": [
                t0 + timedelta(seconds=30),
                t0 + timedelta(minutes=10, seconds=45),
            ],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [30.0, 45.0]

    def test_execution_times_negative_delta_dropped(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1, 0, 0, 0)
        steps = {
            "Alert received": [t0],
            "Containment executed": [t0 - timedelta(seconds=5)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_execution_times_started_passed(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1, 0, 0, 0)
        steps = {
            "Step STARTED ingest": [t0],
            "Step PASSED ingest": [t0 + timedelta(seconds=12)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [12.0]

    def test_execution_times_uncomputable(self):
        from datetime import datetime

        steps = {"Something else": [datetime(2024, 1, 1)]}
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_inter_arrival_exact(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1, 0, 0, 0)
        steps = {
            "Step1": [t0, t0 + timedelta(seconds=10), t0 + timedelta(seconds=25)],
        }
        assert StatisticalCalculator.inter_arrival_times(steps, ["Step1"]) == [10.0, 15.0]

    def test_metrics_fractional_values_kill_round_mutants(self):
        assert StatisticalCalculator.calculate_statistical_metrics([1.0, 2.0, 4.0]) == {
            "total_executions": 3,
            "mean": 2.33,
            "median": 2.0,
            "p50": 2.0,
            "p90": 3.6,
            "p95": 3.8,
            "p99": 3.96,
            "min": 1.0,
            "max": 4.0,
            "std_dev": 1.53,
            "mttr_seconds": 2.33,
            "mttr_minutes": 0.04,
        }

    def test_metrics_empty_exact(self):
        assert StatisticalCalculator.calculate_statistical_metrics([]) == {
            "total_executions": 0,
            "mean": 0.0,
            "median": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std_dev": 0.0,
            "mttr_seconds": 0.0,
            "mttr_minutes": 0.0,
        }

    def test_metrics_stdev_two_valid_times(self):
        # len>1 computes stdev (kills `>1`->`>2`)
        r = StatisticalCalculator.calculate_statistical_metrics([1.0, 3.0])
        assert r["std_dev"] == 1.41
        assert r["total_executions"] == 2

    def test_health_score_status_boundary_80(self):
        r = StatisticalCalculator.calculate_health_score(20, 20, 20, 80)
        assert r["overall_score"] == 80.0 and r["status"] == "excellent"

    def test_health_score_status_boundary_60(self):
        r = StatisticalCalculator.calculate_health_score(40, 40, 40, 60)
        assert r["overall_score"] == 60.0 and r["status"] == "good"

    def test_health_score_status_boundary_40(self):
        r = StatisticalCalculator.calculate_health_score(60, 60, 60, 40)
        assert r["overall_score"] == 40.0 and r["status"] == "warning"

    def test_health_score_fractional_components(self):
        r = StatisticalCalculator.calculate_health_score(33.3, 33.3, 33.3, 33.3)
        assert r["overall_score"] == 60.02
        assert r["components"] == {
            "cpu": 66.7,
            "memory": 66.7,
            "disk": 66.7,
            "tests": 33.3,
        }

    def test_execution_times_only_containment_falls_through(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1)
        steps = {
            "Containment executed": [t0 + timedelta(seconds=30)],
            "Step STARTED x": [t0],
            "Step PASSED x": [t0 + timedelta(seconds=7)],
        }
        # `and` is required: empty alert_times must NOT short-circuit to paired
        assert StatisticalCalculator.calculate_execution_times(steps) == [7.0]

    def test_execution_times_failed_key_counts_as_end(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1)
        steps = {
            "Step STARTED x": [t0],
            "Step FAILED x": [t0 + timedelta(seconds=9)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [9.0]

    def test_paired_times_continues_past_bad_pair(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1)
        steps = {
            "Alert received": [t0, t0, t0],
            "Containment executed": [
                t0 + timedelta(seconds=10),
                "garbage",  # TypeError -> continue, not break
                t0 + timedelta(seconds=20),
            ],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [10.0, 20.0]

    def test_paired_times_zero_delta_excluded(self):
        from datetime import datetime

        t0 = datetime(2024, 1, 1)
        steps = {"Alert received": [t0], "Containment executed": [t0]}
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_inter_arrival_zero_delta_excluded(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1)
        steps = {"S": [t0, t0, t0 + timedelta(seconds=5)]}
        assert StatisticalCalculator.inter_arrival_times(steps, ["S"]) == [5.0]

    def test_inter_arrival_window_boundary(self):
        from datetime import datetime, timedelta

        t0 = datetime(2024, 1, 1)
        steps = {"S": [t0, t0 + timedelta(seconds=3600), t0 + timedelta(seconds=3601)]}
        # first delta (3600) excluded by <3600; second (1s) is included
        assert StatisticalCalculator.inter_arrival_times(steps, ["S"]) == [1.0]

    def test_golden_metrics_all_keys_2dp(self):
        # 3-decimal inputs kill round(x,2)->round(x,3) on median/p50/min/max too
        r = StatisticalCalculator.calculate_statistical_metrics([1.234, 2.345, 3.456])
        assert r["mean"] == 2.35
        assert r["median"] == 2.35  # kills round(...,3) -> 2.345 and round(...,None)
        assert r["p50"] == 2.35
        assert r["min"] == 1.23
        assert r["max"] == 3.46
        assert r["p90"] == 3.23
        assert r["p95"] == 3.34
        assert r["p99"] == 3.43

    def test_health_score_components_2dp(self):
        # percent=33.333 -> score 66.667 -> round2=66.67 kills round(...,3)
        r = StatisticalCalculator.calculate_health_score(33.333, 33.333, 33.333, 33.333)
        assert r["components"]["cpu"] == 66.67
        assert r["components"]["memory"] == 66.67
        assert r["components"]["disk"] == 66.67
        assert r["components"]["tests"] == 33.33
        assert r["overall_score"] == 60.0

    @staticmethod
    def _t(seconds, base=None):
        return (base or datetime.now(UTC)) + timedelta(seconds=seconds)

    def test_paired_delta_one_included(self):
        base = datetime.now(UTC)
        steps = {
            "Alert received": [self._t(0, base)],
            "Containment executed": [self._t(1.0, base)],
        }
        r = StatisticalCalculator.calculate_execution_times(steps)
        assert r == [1.0]  # delta > 0, not > 1

    def test_paired_delta_zero_excluded(self):
        base = datetime.now(UTC)
        steps = {
            "Alert received": [self._t(0, base)],
            "Containment executed": [self._t(0, base)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_execution_times_missing_keys_empty(self):
        # .get(...,[]) -> original []; ->None crashes
        assert StatisticalCalculator.calculate_execution_times({}) == []
        assert (
            StatisticalCalculator.calculate_execution_times({"Alert received": [self._t(0)]}) == []
        )

    def test_started_passed_requires_both(self):
        steps = {"STEP_STARTED": [self._t(0)]}  # no PASSED/FAILED key
        r = StatisticalCalculator.calculate_execution_times(steps)
        assert r == []  # `and`, not `or`

    def test_started_passed_zero_delta_excluded(self):
        base = datetime.now(UTC)
        steps = {"A_STARTED": [self._t(5, base)], "A_PASSED": [self._t(5, base)]}
        r = StatisticalCalculator.calculate_execution_times(steps)
        assert r == []  # >0, not >=0

    def test_started_passed_one_second_included(self):
        base = datetime.now(UTC)
        steps = {"A_STARTED": [self._t(5, base)], "A_PASSED": [self._t(6, base)]}
        r = StatisticalCalculator.calculate_execution_times(steps)
        assert r == [1.0]
