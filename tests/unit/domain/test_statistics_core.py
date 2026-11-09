#!/usr/bin/env python3
"""M-001 canonical statistical core + M-009 outlier bounds + M-010
distributions + property-style invariants (M-043-lite)."""

import math
import statistics as _st

import pytest

from soar_lab.domain.statistics import (
    iqr_outlier_bounds,
    mad_outlier_bounds,
    percentile,
    percentiles,
    summary_stats,
)


class TestCanonicalPercentile:
    def test_linear_interpolation(self):
        # Canonical convention: numpy default / statistics.quantiles inclusive
        assert percentile([1, 2, 3, 4, 5], 50) == 3.0
        assert percentile([1, 2, 3, 4], 50) == 2.5
        assert percentile([10, 20], 90) == pytest.approx(19.0)

    def test_empty_and_single(self):
        assert percentile([], 90) == 0.0
        assert percentile([7.5], 99) == 7.5

    def test_bounds_validation(self):
        with pytest.raises(ValueError):
            percentile([1, 2], -1)
        with pytest.raises(ValueError):
            percentile([1, 2], 101)

    def test_matches_statistics_quantiles(self):
        data = [3.2, 1.1, 7.7, 4.4, 9.9, 2.2, 5.5]
        q = _st.quantiles(data, n=100, method="inclusive")
        assert percentile(data, 50) == pytest.approx(q[49], abs=0.011)

    def test_ordering_invariant(self):
        data = [float(x) for x in range(1, 51)]
        assert percentile(data, 50) <= percentile(data, 90) <= percentile(data, 99)
        assert percentile(data, 90) <= max(data)


class TestSummaryStats:
    def test_empty(self):
        r = summary_stats([])
        assert r["n"] == 0 and r["p90"] == 0.0

    def test_full_fields(self):
        r = summary_stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        for k in (
            "n",
            "mean",
            "median",
            "std",
            "mad",
            "iqr",
            "min",
            "max",
            "skewness",
            "kurtosis",
            "p50",
            "p75",
            "p90",
            "p95",
            "p99",
        ):
            assert k in r
        assert r["n"] == 10 and r["median"] == 5.5

    def test_nan_safe_small_n(self):
        r = summary_stats([5.0])
        assert r["std"] == 0.0 and r["skewness"] == 0.0


class TestOutlierBounds:
    def test_iqr_fences(self):
        data = [10, 11, 12, 13, 14, 15, 1000]
        lo, hi = iqr_outlier_bounds(data)
        assert 1000 > hi and 10 >= lo

    def test_mad_fences(self):
        data = [10, 11, 12, 13, 14, 15, 1000]
        lo, hi = mad_outlier_bounds(data)
        assert 1000 > hi

    def test_small_sample_unbounded(self):
        assert iqr_outlier_bounds([1, 2]) == (-float("inf"), float("inf"))

    def test_zero_mad_unbounded(self):
        lo, hi = mad_outlier_bounds([5, 5, 5, 5, 5])
        assert lo == -float("inf")


class TestMetamorphic:
    def test_duplicate_samples_keep_ordering(self):
        """M-044: duplicating every sample must not break percentiles."""
        base = [1.0, 5.0, 9.0, 13.0, 17.0]
        doubled = [x for x in base for _ in range(2)]
        assert percentile(doubled, 90) >= percentile(doubled, 50)
        assert abs(percentile(doubled, 50) - percentile(base, 50)) < 2.0


class TestGoldenOutputs:
    """Mutation-hardening: exact-value assertions on canonical stats."""

    DATA = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    def test_percentile_exact_values(self):
        assert percentile(self.DATA, 50) == 55.0
        assert percentile(self.DATA, 95) == 95.5
        assert percentile(self.DATA, 25) == 32.5
        assert percentile(self.DATA, 0) == 10
        assert percentile(self.DATA, 100) == 100

    def test_percentile_interpolates_linearly(self):
        # k = (4-1)*0.5 = 1.5 -> midpoint of s[1], s[2]
        assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5

    def test_percentile_rejects_out_of_range(self):
        import pytest

        with pytest.raises(ValueError, match=r"in \[0,100\]"):
            percentile([1.0], -1)
        with pytest.raises(ValueError, match=r"in \[0,100\]"):
            percentile([1.0], 101)

    def test_percentiles_bundle_keys_and_values(self):
        assert percentiles(self.DATA) == {
            "p50": 55.0,
            "p75": 77.5,
            "p90": 91.0,
            "p95": 95.5,
            "p99": 99.1,
        }

    def test_summary_stats_exact(self):
        assert summary_stats(self.DATA) == {
            "n": 10,
            "mean": 55.0,
            "median": 55.0,
            "std": 30.277,
            "mad": 25.0,
            "iqr": 45.0,
            "min": 10,
            "max": 100,
            "skewness": 0.0,
            "kurtosis": -1.562,
            "p50": 55.0,
            "p75": 77.5,
            "p90": 91.0,
            "p95": 95.5,
            "p99": 99.1,
        }

    def test_summary_stats_small_n(self):
        r = summary_stats([1, 2, 3])
        assert r["n"] == 3 and r["std"] == 1.0 and r["mad"] == 1
        assert r["kurtosis"] == -2.333 and r["skewness"] == 0.0

    def test_iqr_bounds_exact(self):
        lo, hi = iqr_outlier_bounds(self.DATA)
        assert lo == -35.0 and hi == 145.0

    def test_iqr_bounds_short_data(self):
        import math

        lo, hi = iqr_outlier_bounds([1, 2, 3])
        assert lo == -math.inf and hi == math.inf

    def test_iqr_bounds_k_scales_fence(self):
        lo, hi = iqr_outlier_bounds(self.DATA, k=3.0)
        assert lo == pytest.approx(32.5 - 3 * 45.0)
        assert hi == pytest.approx(77.5 + 3 * 45.0)

    def test_mad_bounds_exact(self):
        lo, hi = mad_outlier_bounds(self.DATA)
        delta = 3.5 * 25.0 / 0.6745
        assert lo == pytest.approx(55.0 - delta)
        assert hi == pytest.approx(55.0 + delta)

    def test_mad_bounds_zero_mad(self):
        import math

        lo, hi = mad_outlier_bounds([5, 5, 5, 5])
        assert lo == -math.inf and hi == math.inf

    def test_summary_stats_empty_exact(self):
        assert summary_stats([]) == {
            "n": 0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "mad": 0.0,
            "iqr": 0.0,
            "min": 0.0,
            "max": 0.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    def test_summary_stats_n2_exact(self):
        # n=2 kills `n > 1`->`n > 2` on stdev and `n > 2`->`>= 2` on moments
        assert summary_stats([1.0, 2.0]) == {
            "n": 2,
            "mean": 1.5,
            "median": 1.5,
            "std": 0.707,
            "mad": 0.5,
            "iqr": 0.5,
            "min": 1.0,
            "max": 2.0,
            "skewness": 0.0,
            "kurtosis": 0.0,
            "p50": 1.5,
            "p75": 1.75,
            "p90": 1.9,
            "p95": 1.95,
            "p99": 1.99,
        }

    def test_summary_stats_asymmetric_moments(self):
        # skew/kurt nonzero -> kills m3/m4 arithmetic mutants
        r = summary_stats([1.0, 2.0, 3.0, 4.0, 10.0])
        assert r == {
            "n": 5,
            "mean": 4.0,
            "median": 3.0,
            "std": 3.536,
            "mad": 1.0,
            "iqr": 2.0,
            "min": 1.0,
            "max": 10.0,
            "skewness": 0.815,
            "kurtosis": -1.216,
            "p50": 3.0,
            "p75": 4.0,
            "p90": 7.6,
            "p95": 8.8,
            "p99": 9.76,
        }

    def test_summary_stats_constant_data_no_division(self):
        # std == 0 -> moments stay 0 (kills `std > 0`->`>= 0` which divides by 0)
        r = summary_stats([5.0, 5.0, 5.0, 5.0])
        assert r["skewness"] == 0.0 and r["kurtosis"] == 0.0
        assert r["std"] == 0.0

    def test_percentile_three_decimal_values(self):
        # values with >2 decimals distinguish round(x,2) from round(x,3)
        assert percentile([0.1, 0.2, 0.3, 0.4], 95) == 0.39
        assert percentile([0.1, 0.2, 0.3, 0.4], 99) == 0.4

    def test_summary_stats_precision_3_decimals(self):
        # 3-decimal rounding kills round(...,3) -> round(...,4)/round(...,None)
        r = summary_stats([0.1111111, 0.5555555])
        assert r["mean"] == 0.333
        assert r["median"] == 0.333
        assert r["min"] == 0.111
        assert r["max"] == 0.556

    def test_mad_uses_three_decimal_rounding(self):
        # raw mad = 0.09445 -> round(x,3)=0.094 kills round(x,4)=0.0944
        r = summary_stats([0.1111, 0.2, 0.3, 1.0])
        assert r["mad"] == 0.094

    def test_iqr_bounds_len_four_computed(self):
        lo, hi = iqr_outlier_bounds([1, 2, 3, 100])
        assert lo != -math.inf and hi != math.inf  # len==4 IS computed (< 4)

    def test_mad_bounds_len_four_computed(self):
        lo, hi = mad_outlier_bounds([1, 2, 3, 100])
        assert lo != -math.inf and hi != math.inf

    def test_bounds_below_four_are_infinite(self):
        for fn in (iqr_outlier_bounds, mad_outlier_bounds):
            lo, hi = fn([1, 2, 3])
            assert lo == -math.inf and hi == math.inf  # (-inf, not +inf)
