"""Analytics, KPI, and node-timing endpoints for the SOAR API."""

import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from requests.exceptions import RequestException

from soar_lab.application.use_cases.aggregated_kpis import AggregatedKpisUseCase
from soar_lab.application.use_cases.attack_coverage import AttackCoverageUseCase
from soar_lab.application.use_cases.experiment_compare import ExperimentCompareUseCase
from soar_lab.application.use_cases.incident_report import IncidentReportUseCase
from soar_lab.application.use_cases.node_timing_extractor import NodeTimingExtractor
from soar_lab.application.use_cases.node_timings import NodeTimingsUseCase
from soar_lab.application.use_cases.sigma_eval import SigmaEvalUseCase
from soar_lab.application.use_cases.slo import evaluate_slos
from soar_lab.application.use_cases.stix_export import StixExportUseCase
from soar_lab.common.constants import DEFAULT_OPENSEARCH_URL
from soar_lab.config.logging import get_logger
from soar_lab.config.settings import create_settings
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
from soar_lab.infrastructure.integrations.elasticsearch.client import ElasticsearchClient

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
    settings = create_settings()
    config_provider = InfrastructureConfigProvider(settings)

    extractor = NodeTimingExtractor(
        opensearch_url=config_provider.get("opensearch_url", DEFAULT_OPENSEARCH_URL),
        opensearch_user=config_provider.get("opensearch_user", "admin"),
        opensearch_pass=config_provider.get("opensearch_password", ""),
        elasticsearch_url=config_provider.get("elasticsearch_url"),
        elasticsearch_user=config_provider.get("elasticsearch_user", "elastic"),
        elasticsearch_pass=config_provider.get("elasticsearch_password", ""),
        http_post=requests.post,
    )

    es = ElasticsearchClient(
        base_url=config_provider.get("elasticsearch_url"),
        config_provider=config_provider,
    )

    return NodeTimingsUseCase(es_client=es, node_timing_extractor=extractor)


def register_analytics_routes(app_instance: FastAPI, get_analytics_service: Any) -> None:
    """Register analytics and KPI endpoints."""

    @app_instance.get("/analytics/metrics", response_model=Metrics)
    def get_metrics() -> Any:
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
    def get_kpis(
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
            kpis = analytics.get_comprehensive_kpis(log_file_path)
            _overlay_last_coverage(app_instance, kpis)
            return kpis
        except Exception as e:
            logger.exception("Error getting KPIs")
            raise HTTPException(status_code=500, detail="Failed to get KPIs") from e

    _register_aggregated_kpis_route(app_instance)
    _register_node_timings_route(app_instance)
    _register_attack_coverage_route(app_instance)
    _register_incident_report_route(app_instance)
    _register_experiment_compare_route(app_instance)
    _register_stix_export_route(app_instance)
    _register_sigma_route(app_instance)


def _overlay_last_coverage(app_instance: FastAPI, kpis: Any) -> None:
    """Hydrate ``performance.average_coverage`` from the last coverage artifact.

    ``average_coverage`` only reflects test runs executed through
    ``/tests/run`` this session — after a restart it reports 0 even though a
    coverage report exists on disk (``runtime/coverage/coverage.json``). When
    no runs are recorded, surface the artifact's ``totals.percent_covered`` so
    the dashboard shows real data instead of a blank card.
    """
    try:
        perf = kpis.get("performance") if isinstance(kpis, dict) else None
        if not perf or perf.get("total_tests"):
            return
        path_service = getattr(app_instance.state, "path_service", None)
        coverage_file = getattr(path_service, "coverage_file", None)
        if coverage_file is None or not coverage_file.exists():
            return
        data = json.loads(coverage_file.read_text(encoding="utf-8"))
        covered = (data.get("totals") or {}).get("percent_covered")
        if covered is not None:
            perf["average_coverage"] = round(float(covered), 2)
            perf["coverage_source"] = "last_run_artifact"
    except Exception:
        logger.debug("Coverage artifact overlay skipped", exc_info=True)


def _register_aggregated_kpis_route(app_instance: FastAPI) -> None:
    """Register the aggregated KPIs endpoint."""

    @app_instance.get("/analytics/kpis/aggregated")
    def get_aggregated_kpis(
        hours: Annotated[int, Query(ge=0, le=8760)] = 24,
    ) -> Any:
        """Get aggregated KPI metrics from Elasticsearch soar-metrics index.

        Args:
            hours: The lookback window in hours for aggregating metrics.

        Returns:
            dict: Aggregated KPI metrics including ``period_hours``,
            ``timestamp``, ``total_alerts``, ``mttr_statistics``,
            ``by_alert_type`` and ``services``.

        Raises:
            HTTPException: 503 metrics store unavailable, 500 on other
            failures.
        """
        try:
            use_case = create_aggregated_kpis_use_case()
            return use_case.execute(hours=hours)
        except RequestException as e:
            logger.warning("Metrics store unreachable: %s", e)
            raise HTTPException(status_code=503, detail="Metrics store unavailable") from e
        except Exception as e:
            logger.exception("Error getting aggregated KPIs")
            raise HTTPException(status_code=500, detail="Failed to get aggregated KPIs") from e

    @app_instance.get("/analytics/slo")
    def get_slo_compliance(
        hours: Annotated[int, Query(ge=0, le=8760)] = 24,
    ) -> Any:
        """Evaluate declared SLOs (config/slo.yaml) against live KPIs (O2).

        Grafana-consumable compliance payload: per-SLO target vs actual
        plus aggregate ``all_met``.

        Raises:
            HTTPException: 503 metrics store unavailable, 500 when SLO
            evaluation fails.
        """
        try:
            use_case = create_aggregated_kpis_use_case()
            payload = use_case.execute(hours=hours)
            return evaluate_slos(payload)
        except RequestException as e:
            logger.warning("Metrics store unreachable: %s", e)
            raise HTTPException(status_code=503, detail="Metrics store unavailable") from e
        except Exception as e:
            logger.exception("Error evaluating SLOs")
            raise HTTPException(status_code=500, detail="Failed to evaluate SLOs") from e


def _register_node_timings_route(app_instance: FastAPI) -> None:
    """Register the node-timings endpoint."""

    @app_instance.get("/analytics/node-timings")
    def get_node_timings(
        execution_id: str = "",
        alert_id: str = "",
        hours: Annotated[int, Query(ge=0, le=8760)] = 1,
    ) -> Any:
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
        except RequestException as e:
            logger.warning("Execution store unreachable: %s", e)
            raise HTTPException(status_code=503, detail="Execution store unavailable") from e
        except Exception as e:
            logger.exception("Error getting node timings")
            raise HTTPException(status_code=500, detail="Failed to get node timings") from e


_MAX_COVERAGE_ALERTS = 50_000


def _register_attack_coverage_route(app_instance: FastAPI) -> None:
    """Register the ATT&CK coverage endpoint."""

    @app_instance.get("/analytics/attack-coverage")
    def get_attack_coverage(
        format: Literal[  # pylint: disable=redefined-builtin
            "summary", "navigator", "heatmap"
        ] = "summary",
        limit: int = 5000,
    ) -> Any:
        """Get MITRE ATT&CK technique coverage over stored alerts.

        Args:
            format: ``summary`` for aggregated counts, ``heatmap`` for the
            coverage×response matrix per technique, ``navigator`` for a
            MITRE ATT&CK Navigator layer document (importable via
            "Open Existing Layer" at attack-navigator).
            limit: Max alerts analysed (bounded server-side).

        Returns:
            dict: Coverage summary or Navigator layer JSON.

        Raises:
            HTTPException: 422 on bad format (schema), 503 when no alert
            repository is wired, 500 on unexpected failure.
        """
        repository = getattr(app_instance.state, "alert_repository", None)
        if repository is None or not hasattr(repository, "get_alerts"):
            raise HTTPException(status_code=503, detail="Alert repository unavailable")

        try:
            use_case = AttackCoverageUseCase(alerts_provider=repository.get_alerts)
            bounded = max(1, min(limit, _MAX_COVERAGE_ALERTS))
            if format == "navigator":
                return use_case.navigator_layer()
            if format == "heatmap":
                return use_case.heatmap(limit=bounded)
            return use_case.coverage(limit=bounded)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error computing ATT&CK coverage")
            raise HTTPException(status_code=500, detail="Failed to compute ATT&CK coverage") from e


def _register_incident_report_route(app_instance: FastAPI) -> None:
    """IR4: post-incident report endpoint — JSON or markdown."""

    @app_instance.get("/analytics/incident-report/{alert_id}")
    def get_incident_report(
        alert_id: str,
        format: Literal["json", "markdown"] = "json",  # pylint: disable=redefined-builtin
    ) -> Any:
        """Generate a post-incident report for a single alert.

        Args:
            alert_id: Stored alert identifier.
            format: ``json`` for the structured report, ``markdown``
                for a rendered markdown document.

        Raises:
            HTTPException: 422 bad format (schema), 404 unknown alert,
            503 repository unavailable.
        """
        repository = getattr(app_instance.state, "alert_repository", None)
        if repository is None or not hasattr(repository, "get_alert"):
            raise HTTPException(status_code=503, detail="Alert repository unavailable")

        try:
            use_case = IncidentReportUseCase(
                alert_provider=repository.get_alert,
                cases_provider=getattr(repository, "get_cases", None),
                test_results_provider=getattr(repository, "get_test_results", None),
            )
            if format == "markdown":
                md = use_case.build_markdown(alert_id)
                if md is None:
                    raise HTTPException(status_code=404, detail="Alert not found")
                return PlainTextResponse(md, media_type="text/markdown")
            report = use_case.build(alert_id)
            if report is None:
                raise HTTPException(status_code=404, detail="Alert not found")
            return report
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error building incident report")
            raise HTTPException(status_code=500, detail="Failed to build incident report") from e


def _register_experiment_compare_route(app_instance: FastAPI) -> None:
    """F1: A/B experiment comparison endpoint."""

    @app_instance.get("/analytics/experiment/compare")
    def compare_experiments(variant_a: str, variant_b: str) -> Any:
        """Compare alert→case latency between two tagged variant runs.

        Replays done with ``replay_dataset.py --tag X`` stamp
        ``experiment_tag`` on each alert; this endpoint splits the
        stored corpus by tag, joins each alert to its case and reports
        per-variant latency stats plus Δ mean with 95% Welch CI.

        Raises:
            HTTPException: 503 repository unavailable, 500 on failure.
        """
        repository = getattr(app_instance.state, "alert_repository", None)
        if repository is None or not hasattr(repository, "get_alerts"):
            raise HTTPException(status_code=503, detail="Alert repository unavailable")
        try:
            use_case = ExperimentCompareUseCase(
                alerts_provider=repository.get_alerts,
                cases_provider=getattr(repository, "get_cases", None),
            )
            return use_case.compare(variant_a, variant_b)
        except Exception as e:
            logger.exception("Error comparing experiment variants")
            raise HTTPException(
                status_code=500, detail="Failed to compare experiment variants"
            ) from e


def _register_stix_export_route(app_instance: FastAPI) -> None:
    """F6: STIX 2.1 bundle export endpoint."""

    @app_instance.get("/api/v1/stix/bundle")
    def get_stix_bundle(limit: int = 1000) -> Any:
        """Export stored alerts as a STIX 2.1 bundle.

        One ``indicator`` per IoC (SHA-256/IPv4/domain) plus one
        ``grouping`` per alert — ingestible by MISP, TAXII clients and
        CTI platforms. IDs are deterministic (uuid5) so re-exports are
        diff-stable. Bounded to ``limit`` most recent alerts.

        Raises:
            HTTPException: 503 repository unavailable, 500 on failure.
        """
        repository = getattr(app_instance.state, "alert_repository", None)
        if repository is None or not hasattr(repository, "get_alerts"):
            raise HTTPException(status_code=503, detail="Alert repository unavailable")
        try:
            use_case = StixExportUseCase(alerts_provider=repository.get_alerts)
            bounded = max(1, min(limit, 10000))
            return use_case.build_bundle(limit=bounded)
        except Exception as e:
            logger.exception("Error building STIX bundle")
            raise HTTPException(status_code=500, detail="Failed to build STIX bundle") from e


def _register_sigma_route(app_instance: FastAPI) -> None:
    """F5: sigma-lite detection scan endpoint."""

    @app_instance.get("/analytics/sigma/matches")
    def get_sigma_matches(limit: int = 5000) -> Any:
        """Evaluate Sigma rules (``detections/sigma/``) over stored alerts.

        Per-rule match counts and rates — the lab's configurable
        detection layer. ``SIGMA_RULES_DIR`` overrides the rules
        directory; unsupported-rule features report ``error`` rather
        than silently mis-evaluating.

        Raises:
            HTTPException: 503 repository unavailable, 500 on failure.
        """
        repository = getattr(app_instance.state, "alert_repository", None)
        if repository is None or not hasattr(repository, "get_alerts"):
            raise HTTPException(status_code=503, detail="Alert repository unavailable")
        cp = getattr(app_instance.state, "config_provider", None)
        rules_dir = "detections/sigma"
        if cp is not None and hasattr(cp, "get"):
            rules_dir = str(cp.get("SIGMA_RULES_DIR", rules_dir))
        try:
            use_case = SigmaEvalUseCase(SigmaEvalUseCase.load_rules(rules_dir))
            bounded = max(1, min(limit, 10000))
            return use_case.scan(repository.get_alerts() or [], limit=bounded)
        except Exception as e:
            logger.exception("Error scanning with Sigma rules")
            raise HTTPException(status_code=500, detail="Failed to run Sigma scan") from e
