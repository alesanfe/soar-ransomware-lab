"""Analytics, KPI, and node-timing endpoints for the SOAR API."""

from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from soar_lab.application.use_cases.aggregated_kpis import AggregatedKpisUseCase
from soar_lab.application.use_cases.node_timings import NodeTimingsUseCase
from soar_lab.common.constants import DEFAULT_OPENSEARCH_URL
from soar_lab.config.logging import get_logger

from .models import Metrics
from .route_helpers import MOCK_METRICS_CPU, MOCK_METRICS_DISK, MOCK_METRICS_MEMORY

__all__ = [
    "create_aggregated_kpis_use_case",
    "create_node_timings_use_case",
    "register_analytics_routes",
]

logger = get_logger(__name__)


def create_aggregated_kpis_use_case() -> AggregatedKpisUseCase:
    """Factory that wires real infrastructure adapters to the use case.

    This factory belongs in the interfaces layer (not application)
    because it imports concrete infrastructure adapters. The use case
    class itself remains decoupled and receives dependencies via
    constructor injection.
    """
    from soar_lab.config.settings import create_settings
    from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
    from soar_lab.domain.statistical_calculator import StatisticalCalculator
    from soar_lab.infrastructure.config_provider import (
        InfrastructureConfigProvider,
    )
    from soar_lab.infrastructure.integrations.elasticsearch.client import (
        ElasticsearchClient,
    )

    settings = create_settings()
    config_provider = InfrastructureConfigProvider(settings)
    es = ElasticsearchClient(
        base_url=config_provider.get("elasticsearch_url"), config_provider=config_provider
    )
    statistical_calculator = StatisticalCalculator()
    kpi_analyzer = KPIAnalyzer(statistical_calculator)

    return AggregatedKpisUseCase(
        es_client=es,
        kpi_analyzer=kpi_analyzer,
        statistical_calculator=statistical_calculator,
    )


def create_node_timings_use_case() -> NodeTimingsUseCase:
    """Factory that wires real infrastructure adapters to the use case.

    This factory belongs in the interfaces layer (not application)
    because it imports concrete infrastructure adapters. The use case
    class itself remains decoupled and receives dependencies via
    constructor injection.
    """
    from soar_lab.application.use_cases.node_timing_extractor import (
        NodeTimingExtractor,
    )
    from soar_lab.config.settings import create_settings
    from soar_lab.infrastructure.config_provider import (
        InfrastructureConfigProvider,
    )
    from soar_lab.infrastructure.integrations.elasticsearch.client import (
        ElasticsearchClient,
    )

    settings = create_settings()
    config_provider = InfrastructureConfigProvider(settings)

    extractor = NodeTimingExtractor(
        opensearch_url=config_provider.get("opensearch_url", DEFAULT_OPENSEARCH_URL),
        opensearch_user=config_provider.get("opensearch_user", "admin"),
        opensearch_pass=config_provider.get("opensearch_password", ""),
        elasticsearch_url=config_provider.get("elasticsearch_url"),
        elasticsearch_user=config_provider.get("elasticsearch_user", "elastic"),
        elasticsearch_pass=config_provider.get("elasticsearch_password", ""),
    )

    es = ElasticsearchClient(
        base_url=config_provider.get("elasticsearch_url"),
        config_provider=config_provider,
    )

    return NodeTimingsUseCase(es_client=es, node_timing_extractor=extractor)


def register_analytics_routes(app_instance: FastAPI, get_analytics_service: Any) -> None:
    """Register analytics and KPI endpoints."""

    @app_instance.get("/analytics/metrics", response_model=Metrics)
    async def get_metrics() -> Any:
        """Get system metrics.

        Returns:
            Metrics: System metrics model with alerts, cases, backups counts.

        Raises:
            HTTPException: 500 when retrieving system metrics fails.
        """
        try:
            system_metrics = app_instance.state.system_metrics
            if system_metrics:
                metrics = system_metrics.get_hardware_metrics()
                return Metrics(
                    cpu=metrics.get("cpu", {}).get("percent", 0.0),
                    memory=metrics.get("memory", {}).get("percent", 0.0),
                    disk=metrics.get("disk", {}).get("percent", 0.0),
                    timestamp=datetime.now(UTC),
                )
            return Metrics(
                cpu=MOCK_METRICS_CPU,
                memory=MOCK_METRICS_MEMORY,
                disk=MOCK_METRICS_DISK,
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            logger.exception("Error getting metrics")
            raise HTTPException(status_code=500, detail="Failed to get metrics") from e

    @app_instance.get("/analytics/kpis")
    async def get_kpis(
        log_file_path: str | None = None,
        analytics: Any = Depends(get_analytics_service),
    ) -> Any:
        """Get KPI metrics.

        Args:
            log_file_path: Optional path to a log file used for KPI
            computation; when omitted the analytics service default is used.
            analytics: The analytics service dependency.

        Returns:
            dict: The comprehensive KPI metrics computed by the analytics
            service.

        Raises:
            HTTPException: 500 when KPI retrieval fails.
        """
        try:
            return analytics.get_comprehensive_kpis(log_file_path)
        except Exception as e:
            logger.exception("Error getting KPIs")
            raise HTTPException(status_code=500, detail="Failed to get KPIs") from e

    _register_aggregated_kpis_route(app_instance)
    _register_node_timings_route(app_instance)


def _register_aggregated_kpis_route(app_instance: FastAPI) -> None:
    """Register the aggregated KPIs endpoint."""

    @app_instance.get("/analytics/kpis/aggregated")
    async def get_aggregated_kpis(hours: int = 24) -> Any:
        """Get aggregated KPI metrics from Elasticsearch soar-metrics index.

        Args:
            hours: The lookback window in hours for aggregating metrics.

        Returns:
            dict: Aggregated KPI metrics including ``period_hours``,
            ``timestamp``, ``total_alerts``, ``mttr_statistics``,
            ``by_alert_type`` and ``services``.

        Raises:
            HTTPException: 500 when retrieving or computing aggregated KPIs
            fails.
        """
        try:
            use_case = create_aggregated_kpis_use_case()
            return use_case.execute(hours=hours)
        except Exception as e:
            logger.exception("Error getting aggregated KPIs")
            raise HTTPException(status_code=500, detail="Failed to get aggregated KPIs") from e


def _register_node_timings_route(app_instance: FastAPI) -> None:
    """Register the node-timings endpoint."""

    @app_instance.get("/analytics/node-timings")
    async def get_node_timings(execution_id: str = "", alert_id: str = "", hours: int = 1) -> Any:
        """Get per-node timing breakdown for workflow executions.

        If execution_id is provided, fetches timings for that specific execution.
        Otherwise, returns aggregated node timings from the last `hours` hours.

        Args:
            execution_id: Optional workflow execution identifier to fetch
            timings for a single execution.
            alert_id: Optional alert identifier used alongside execution_id.
            hours: The lookback window in hours for aggregated timings.

        Returns:
            dict: The per-node timing data for the requested execution or the
            aggregated timings over the lookback window.

        Raises:
            HTTPException: 404 when the requested execution is not found, or
            500 when retrieving node timings fails.
        """
        try:
            use_case = create_node_timings_use_case()

            if execution_id:
                timings = use_case.get_execution(execution_id, alert_id)
                if timings:
                    return timings
                raise HTTPException(status_code=404, detail="Execution not found")

            return use_case.get_aggregated(hours=hours)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error getting node timings")
            raise HTTPException(status_code=500, detail="Failed to get node timings") from e
