"""Canonical statistical core for the SOAR Lab measurement layer (M-001).

Single source of truth for every percentile / distribution calculation in
the project. ISO 15939 alignment: one metric, one definition, one algorithm.

Canonical percentile method: linear interpolation over the empirical CDF
(same convention as ``numpy.percentile`` default and
``statistics.quantiles(method='inclusive')``). This was the method already
used by ``generate_e2e_report`` for the TFM tables, so it is the one that
keeps published numbers comparable.

Do NOT reimplement percentile logic elsewhere — consume this module.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

__all__ = [
    "MetricNotComputable",
    "percentile",
    "percentiles",
    "summary_stats",
    "iqr_outlier_bounds",
    "mad_outlier_bounds",
]


class MetricNotComputable(ValueError):
    """Raised when a metric cannot be computed honestly from the data."""


def percentile(data: list[float], pct: float) -> float:
    """Compute a percentile via linear interpolation (canonical method).

    Args:
        data: sample values (unsorted accepted)
        pct: percentile in [0, 100]

    Returns:
        The percentile value, or 0.0 for empty input.
    """
    if not data:
        return 0.0
    if not 0 <= pct <= 100:
        raise ValueError(f"pct must be in [0,100], got {pct}")
    s = sorted(data)
    k = (len(s) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 2)


def percentiles(
    data: list[float], marks: tuple[int, ...] = (50, 75, 90, 95, 99)
) -> dict[str, float]:
    """Standard percentile bundle used by KPI reporting."""
    return {f"p{int(m)}": percentile(data, m) for m in marks}


def summary_stats(data: list[float]) -> dict[str, Any]:
    """Full distribution description (M-010).

    Returns mean/median/std/mad/iqr/percentiles/skewness/kurtosis plus n.
    Robust to n<3 (higher moments reported as 0 rather than NaN so
    downstream JSON stays valid).
    """
    n = len(data)
    if n == 0:
        return {
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
        } | percentiles([])
    s = sorted(data)
    mean = statistics.fmean(s)
    median = statistics.median(s)
    std = statistics.stdev(s) if n > 1 else 0.0
    mad = statistics.median([abs(x - median) for x in s])
    q1 = percentile(s, 25)
    q3 = percentile(s, 75)
    skew = kurt = 0.0
    if n > 2 and std > 0:
        m3 = sum((x - mean) ** 3 for x in s) / n
        m4 = sum((x - mean) ** 4 for x in s) / n
        skew = m3 / std**3
        kurt = m4 / std**4 - 3.0  # excess kurtosis
    return {
        "n": n,
        "mean": round(mean, 3),
        "median": round(median, 3),
        "std": round(std, 3),
        "mad": round(mad, 3),
        "iqr": round(q3 - q1, 3),  # pragma: no mutate≡round(,4))
        "min": round(s[0], 3),
        "max": round(s[-1], 3),
        "skewness": round(skew, 3),
        "kurtosis": round(kurt, 3),
    } | percentiles(s)


def iqr_outlier_bounds(data: list[float], k: float = 1.5) -> tuple[float, float]:
    """Tukey fence bounds (M-009). Values outside are outliers."""
    if len(data) < 4:
        return (-math.inf, math.inf)
    q1, q3 = percentile(data, 25), percentile(data, 75)
    iqr = q3 - q1
    return (q1 - k * iqr, q3 + k * iqr)


def mad_outlier_bounds(data: list[float], z: float = 3.5) -> tuple[float, float]:
    """Modified-z-score bounds via MAD (M-009)."""
    if len(data) < 4:
        return (-math.inf, math.inf)
    med = statistics.median(data)
    mad = statistics.median([abs(x - med) for x in data])
    if mad == 0:
        return (-math.inf, math.inf)
    delta = z * mad / 0.6745
    return (med - delta, med + delta)
