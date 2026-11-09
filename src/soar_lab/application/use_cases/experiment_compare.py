"""A/B experiment comparison use case (F1).

Alerts replayed with ``--tag VARIANT`` carry ``experiment_tag``; the
pipeline is otherwise identical, so latency differences between two
variant groups measure the configuration change — the scientific A/B
mode: same dataset, two configs, Δ MTTR with a confidence interval.

The measured latency is alert→case creation (the lab's response KPI):
for each tagged alert we find its linked case (``case.alert_id``) and
take ``case.timestamp - alert.timestamp``. Stats per variant come from
``StatisticalCalculator``; the delta uses Welch's t interval
(unequal variances — the honest choice for A/B).
"""

import math
import statistics
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

from soar_lab.domain.statistical_calculator import StatisticalCalculator

__all__ = ["ExperimentCompareUseCase"]

_TAG_KEYS = ("experiment_tag", "variant")


def _tag_of(alert: dict[str, Any]) -> str | None:
    for key in _TAG_KEYS:
        value = alert.get(key)
        if isinstance(value, str) and value:
            return value
    data = alert.get("data")
    if isinstance(data, dict):
        for key in _TAG_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _welch_ci(delta: float, a: list[float], b: list[float]) -> list[float] | None:
    """95% CI for ``mean(a) - mean(b)`` via Welch's approximation."""
    if len(a) < 2 or len(b) < 2:
        return None
    var = statistics.stdev(a) ** 2 / len(a) + statistics.stdev(b) ** 2 / len(b)
    if var <= 0:
        return None
    se = math.sqrt(var)
    return [round(delta - 1.96 * se, 2), round(delta + 1.96 * se, 2)]


class ExperimentCompareUseCase:
    """Compare response latency between two experiment variants."""

    def __init__(
        self,
        alerts_provider: Callable[[], Iterable[dict[str, Any]]],
        cases_provider: Callable[[], Iterable[dict[str, Any]]],
    ) -> None:
        """Create the use case from repository callables."""
        if alerts_provider is None or cases_provider is None:
            raise ValueError("alerts_provider and cases_provider are required")
        self._alerts_provider = alerts_provider
        self._cases_provider = cases_provider

    def latencies_by_variant(self) -> dict[str, list[float]]:
        """Group alert→case latencies (seconds) by experiment tag."""
        cases_by_alert = self._case_timestamps_by_alert()

        groups: dict[str, list[float]] = {}
        for alert in self._alerts_provider() or []:
            if not isinstance(alert, dict):
                continue
            tag = _tag_of(alert)
            if not tag:
                continue
            alert_ts = _parse_ts(alert.get("timestamp"))
            case_ts = cases_by_alert.get(str(alert.get("alert_id")))
            if alert_ts is None or case_ts is None:
                continue
            latency = (case_ts - alert_ts).total_seconds()
            if latency >= 0:
                groups.setdefault(tag, []).append(latency)
        return groups

    def _case_timestamps_by_alert(self) -> dict[str, datetime]:
        """Index the earliest case timestamp per alert_id."""
        cases_by_alert: dict[str, datetime] = {}
        for case in self._cases_provider() or []:
            if not isinstance(case, dict):
                continue
            alert_id = case.get("alert_id")
            ts = _parse_ts(case.get("timestamp"))
            if alert_id and ts is not None:
                cases_by_alert.setdefault(str(alert_id), ts)
        return cases_by_alert

    def compare(self, variant_a: str, variant_b: str) -> dict[str, Any]:
        """Stats per variant + Δ mean with 95% Welch CI."""
        groups = self.latencies_by_variant()
        a = groups.get(variant_a, [])
        b = groups.get(variant_b, [])
        stats_a = StatisticalCalculator.calculate_statistical_metrics(a)
        stats_b = StatisticalCalculator.calculate_statistical_metrics(b)
        delta = round(stats_a["mean"] - stats_b["mean"], 2)
        return {
            "variant_a": {"name": variant_a, "n": len(a), "stats": stats_a},
            "variant_b": {"name": variant_b, "n": len(b), "stats": stats_b},
            "delta_mean_seconds": delta,
            "delta_ci95": _welch_ci(stats_a["mean"] - stats_b["mean"], a, b),
            "known_variants": sorted(groups),
            "timestamp": datetime.now(UTC).isoformat(),
        }
