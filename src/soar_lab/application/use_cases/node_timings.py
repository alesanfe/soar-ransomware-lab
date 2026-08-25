"""Use case for retrieving per-node timing data for workflow executions.

This use case encapsulates the logic of fetching node timings from
Elasticsearch/OpenSearch, keeping the route handler free of
infrastructure imports.
"""

import time
from datetime import UTC, datetime
from typing import Any

from soar_lab.common.constants import DEFAULT_ANALYTICS_SEARCH_SIZE, METRICS_INDEX
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class NodeTimingsUseCase:
    """Retrieve per-node timing breakdowns for workflow executions."""

    def __init__(self, es_client: Any, node_timing_extractor: Any) -> None:
        """Initialize with injected dependencies.

        Args:
            es_client: Elasticsearch client used for aggregated searches.
            node_timing_extractor: Extracts timings for a single execution.
        """
        self._es = es_client
        self._extractor = node_timing_extractor

    def get_execution(self, execution_id: str, alert_id: str = "") -> dict[str, Any] | None:
        """Get timings for a single execution.

        Args:
            execution_id: The workflow execution identifier.
            alert_id: Optional alert identifier associated with the execution.

        Returns:
            dict | None: The timing data, or None if not found.
        """
        result: dict[str, Any] | None = self._extractor.process_execution(execution_id, alert_id)
        return result

    def get_aggregated(self, hours: int = 1) -> dict[str, Any]:
        """Get aggregated node timings over a lookback window.

        Args:
            hours: The lookback window in hours.

        Returns:
            dict: Aggregated timing data with ``period_hours``,
            ``timestamp``, ``total_executions`` and ``executions``.
        """
        now_ms = int(time.time() * 1000)
        hours_ago_ms = now_ms - hours * 3600 * 1000
        result = self._es.search(
            query={
                "bool": {
                    "must": [{"term": {"metric_type": "node_timings"}}],
                    "filter": [{"range": {"@timestamp": {"gte": hours_ago_ms}}}],
                }
            },
            index=METRICS_INDEX,
            size=DEFAULT_ANALYTICS_SEARCH_SIZE,
        )
        hits = result.get("hits", {}).get("hits", [])
        aggregated = []
        for h in hits:
            src = h.get("_source", {})
            aggregated.append(
                {
                    "alert_id": src.get("alert_id", ""),
                    "execution_id": src.get("execution_id", ""),
                    "workflow_duration_s": src.get("workflow_duration_s", 0),
                    "total_nodes": src.get("total_nodes", 0),
                    "slowest_nodes": src.get("slowest_nodes", []),
                    "nodes": src.get("nodes", {}),
                }
            )
        return {
            "period_hours": hours,
            "timestamp": datetime.now(UTC).isoformat(),
            "total_executions": len(aggregated),
            "executions": aggregated,
        }
