"""Use case for retrieving aggregated KPI metrics from Elasticsearch.

This use case encapsulates the logic of fetching metrics from
Elasticsearch and computing aggregated KPIs, keeping the route handler
free of infrastructure imports.
"""

from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from soar_lab.common.constants import DEFAULT_KPI_SEARCH_SIZE, METRICS_INDEX
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class AggregatedKpisUseCase:
    """Compute aggregated KPI metrics from Elasticsearch soar-metrics index."""

    def __init__(self, es_client: Any, kpi_analyzer: Any, statistical_calculator: Any) -> None:
        """Initialize with injected dependencies.

        Args:
            es_client: Elasticsearch client used to fetch metrics.
            kpi_analyzer: KPI analyzer for computing KPIs by alert type and service.
            statistical_calculator: Calculator for statistical metrics like MTTR.
        """
        self._es = es_client
        self._kpi_analyzer = kpi_analyzer
        self._statistical_calculator = statistical_calculator

    def execute(self, hours: int = 24) -> dict[str, Any]:
        """Fetch and compute aggregated KPIs.

        Args:
            hours: The lookback window in hours for aggregating metrics.

        Returns:
            dict: Aggregated KPI metrics including ``period_hours``,
            ``timestamp``, ``total_alerts``, ``mttr_statistics``,
            ``by_alert_type`` and ``services``.
        """
        metrics_data = self._es.get_latest_documents(
            size=DEFAULT_KPI_SEARCH_SIZE, index=METRICS_INDEX
        )

        if not metrics_data:
            return {
                "period_hours": hours,
                "timestamp": datetime.now(UTC).isoformat(),
                "total_alerts": 0,
                "by_alert_type": {},
                "services": {},
            }

        kpis_by_type = self._kpi_analyzer.calculate_kpis_by_alert_type(metrics_data, hours)
        service_kpis = self._kpi_analyzer.calculate_service_integration_kpis(metrics_data, hours)

        mttr_values = self._extract_mttr_values(metrics_data)
        mttr_stats = {}
        if mttr_values:
            mttr_stats = self._statistical_calculator.calculate_statistical_metrics(mttr_values)

        return {
            "period_hours": hours,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_alerts": len(metrics_data),
            "mttr_statistics": mttr_stats,
            "by_alert_type": kpis_by_type.get("by_alert_type", {}),
            "services": service_kpis.get("services", {}),
        }

    @staticmethod
    def _extract_mttr_values(metrics_data: list[dict[str, Any]]) -> list[float]:
        """Extract MTTR values from metrics data.

        Args:
            metrics_data: List of metric documents from Elasticsearch.

        Returns:
            list[float]: Extracted MTTR values in seconds.
        """
        mttr_values: list[float] = []
        for metric in metrics_data:
            mttr_field = metric.get("mttr_seconds", {})
            if isinstance(mttr_field, dict):
                mttr_str = mttr_field.get("message", "")
                if "MTTR:" in mttr_str:
                    with suppress(ValueError, IndexError):
                        mttr = float(mttr_str.split("MTTR:")[1].split("s")[0].strip())
                        mttr_values.append(mttr)
            elif isinstance(mttr_field, (int, float)):
                mttr_values.append(mttr_field)
        return mttr_values
