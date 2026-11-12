#!/usr/bin/env python3
"""Mutation-hardening tests for statistical_calculator, statistics and
retry — exact percentile math, filter bounds, delay formulas."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.domain.statistics import percentile
from soar_lab.resilience.retry import RetryPolicy, RetryStrategy


class TestPercentile:
    def test_linear_interpolation(self):
        # canonical: k=(n-1)*p/100 over sorted data
        assert percentile([1, 2, 3, 4], 50) == 2.5
        assert percentile([1, 2, 3, 4], 90) == 3.7
        assert percentile([10], 99) == 10
        assert percentile([], 50) == 0.0

    def test_pct_bounds(self):
        with pytest.raises(ValueError, match="pct must be in"):
            percentile([1], -1)
        with pytest.raises(ValueError):
            percentile([1], 101)


class TestStatisticalMetrics:
    def test_empty_shape(self):
        out = StatisticalCalculator.calculate_statistical_metrics([])
        assert out == {
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

    def test_filter_bounds(self):
        # 0, negative and >=3600 are excluded
        out = StatisticalCalculator.calculate_statistical_metrics(
            [0, -5, 3600, 3601, 100.0, 200.0]
        )
        assert out["total_executions"] == 2
        assert out["mean"] == 150.0
        assert out["min"] == 100.0 and out["max"] == 200.0
        # all invalid -> zeros
        assert StatisticalCalculator.calculate_statistical_metrics([0, 3600])[
            "total_executions"
        ] == 0

    def test_exact_values(self):
        out = StatisticalCalculator.calculate_statistical_metrics(
            [10.0, 20.0, 30.0, 40.0]
        )
        assert out["mean"] == 25.0
        assert out["median"] == 25.0
        assert out["p50"] == 25.0
        assert out["p90"] == 37.0
        assert out["mttr_seconds"] == 25.0
        assert out["mttr_minutes"] == round(25.0 / 60, 2)
        assert out["std_dev"] == round(__import__("statistics").stdev([10, 20, 30, 40]), 2)

    def test_single_value_std_zero(self):
        out = StatisticalCalculator.calculate_statistical_metrics([5.0])
        assert out["std_dev"] == 0.0 and out["total_executions"] == 1


class TestHealthScore:
    def test_weights_and_status(self):
        out = StatisticalCalculator.calculate_health_score(0, 0, 0, 100)
        # 100*.3+100*.3+100*.2+100*.2 = 100
        assert out["overall_score"] == 100.0 and out["status"] == "excellent"
        out = StatisticalCalculator.calculate_health_score(50, 50, 50, 60)
        # 50*.3+50*.3+50*.2+60*.2 = 52 -> warning
        assert out["overall_score"] == 52.0 and out["status"] == "warning"
        out = StatisticalCalculator.calculate_health_score(0, 0, 0, 0)
        assert out["overall_score"] == 80.0 and out["status"] == "excellent"
        out = StatisticalCalculator.calculate_health_score(100, 100, 100, 0)
        assert out["overall_score"] == 0.0 and out["status"] == "critical"
        out = StatisticalCalculator.calculate_health_score(10, 10, 10, 80)
        # 90*.3+90*.3+90*.2+80*.2 = 88 -> excellent
        assert out["status"] == "excellent"
        out = StatisticalCalculator.calculate_health_score(30, 30, 30, 60)
        # 70*.3+70*.3+70*.2+60*.2 = 68 -> good
        assert out["status"] == "good"
        c = out["components"]
        assert c == {"cpu": 70, "memory": 70, "disk": 70, "tests": 60}

    def test_over_100_clamped(self):
        out = StatisticalCalculator.calculate_health_score(150, 150, 150, 0)
        assert out["components"]["cpu"] == 0


class TestExecutionTimes:
    def test_paired_path(self):
        t0 = datetime(2024, 1, 1)
        steps = {
            "Alert received": [t0, t0 + timedelta(seconds=5)],
            "Containment executed": [t0 + timedelta(seconds=10)],
        }
        out = StatisticalCalculator.calculate_execution_times(steps)
        assert out == [10.0]  # only min(len) pairs; negative filtered

    def test_non_positive_delta_skipped(self):
        t0 = datetime(2024, 1, 1)
        steps = {
            "Alert received": [t0 + timedelta(seconds=10)],
            "Containment executed": [t0],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == []

    def test_started_passed_fallback(self):
        t0 = datetime(2024, 1, 1)
        steps = {
            "Step1 STARTED": [t0],
            "Step1 PASSED": [t0 + timedelta(seconds=30)],
        }
        assert StatisticalCalculator.calculate_execution_times(steps) == [30.0]

    def test_no_pairs_empty(self):
        assert StatisticalCalculator.calculate_execution_times({}) == []
        assert StatisticalCalculator.calculate_execution_times({"x": []}) == []

    def test_inter_arrival(self):
        t0 = datetime(2024, 1, 1)
        steps = {"s": [t0, t0 + timedelta(seconds=10), t0 + timedelta(seconds=25)]}
        out = StatisticalCalculator.inter_arrival_times(steps, ["s"])
        assert out == [10.0, 15.0]


class TestRetryPolicy:
    def test_mutual_exclusion(self):
        with pytest.raises(ValueError, match="only one of"):
            RetryPolicy(max_retries=2, max_attempts=3)
        assert RetryPolicy(max_attempts=4).max_retries == 3
        assert RetryPolicy().max_retries == 3
        assert RetryPolicy(delay=2.0).base_delay == 2.0

    def test_to_tuple(self):
        assert RetryPolicy._to_tuple(ValueError) == (ValueError,)
        assert RetryPolicy._to_tuple([ValueError, KeyError]) == (ValueError, KeyError)

    def test_should_retry(self):
        p = RetryPolicy(
            retryable_errors=[ValueError],
            non_retryable_errors=[KeyError],
        )
        assert p._should_retry(ValueError()) is True
        assert p._should_retry(KeyError()) is False
        assert p._should_retry(TypeError()) is False

        class NoRetry(Exception):
            retryable = False

        assert p._should_retry(NoRetry()) is False
        # default policy retries any Exception
        assert RetryPolicy()._should_retry(RuntimeError()) is True

    def test_delay_formulas(self):
        assert RetryPolicy(base_delay=2.0, strategy=RetryStrategy.FIXED)._calculate_delay(3) == 2.0
        for s in (RetryStrategy.EXPONENTIAL, RetryStrategy.EXPONENTIAL_BACKOFF):
            assert RetryPolicy(base_delay=2.0, strategy=s)._calculate_delay(3) == 16.0
        assert RetryPolicy(
            base_delay=2.0, strategy=RetryStrategy.LINEAR_BACKOFF
        )._calculate_delay(3) == 8.0
        p = RetryPolicy(
            base_delay=2.0, strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER
        )
        assert p._calculate_delay(2) == 8.0  # jitter_factor 0 -> exact

    def test_jitter_bounds(self):
        p = RetryPolicy(
            base_delay=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            jitter_factor=1.0,
        )
        for _ in range(50):
            d = p._jittered_delay(3)
            assert 0.0 <= d <= 32.0  # 16 +/- 100%

    def test_execute_success_first_try(self):
        p = RetryPolicy()
        assert p.execute(lambda: "ok") == "ok"

    def test_execute_retries_then_raises(self):
        p = RetryPolicy(max_retries=2, base_delay=0)
        calls = []

        def fail():
            calls.append(1)
            raise ValueError("boom")

        with pytest.raises(ValueError):
            p.execute(fail)
        assert len(calls) == 3  # initial + 2 retries

    def test_execute_non_retryable_no_retry(self):
        p = RetryPolicy(max_retries=3, base_delay=0, non_retryable_errors=[KeyError])
        calls = []

        def fail():
            calls.append(1)
            raise KeyError("no")

        with pytest.raises(KeyError):
            p.execute(fail)
        assert len(calls) == 1

    def test_execute_on_retry_and_timeout(self):
        seen = []
        p = RetryPolicy(
            max_retries=3, base_delay=0, on_retry=lambda n, e: seen.append(n)
        )
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("x")
            return "ok"

        assert p.execute(flaky) == "ok"
        assert seen == [1, 2]

        p2 = RetryPolicy(max_retries=5, base_delay=0.2, timeout=0.05)
        with pytest.raises(TimeoutError, match="Retry timeout exceeded"):
            p2.execute(lambda: (_ for _ in ()).throw(ValueError("x")))
