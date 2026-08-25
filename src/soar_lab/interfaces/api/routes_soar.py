"""SOAR integration route registration for the FastAPI application.

This module contains all endpoints whose paths start with ``/soar/``
along with the dependency helpers used exclusively by those endpoints
(TheHive, Cortex, MISP, Shuffle and Elasticsearch clients).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from soar_lab.common.constants import (
    SERVICE_CORTEX,
    SERVICE_ELASTICSEARCH,
    SERVICE_MISP,
    SERVICE_SHUFFLE,
    SERVICE_THEHIVE,
)
from soar_lab.config.logging import get_logger

__all__ = ["register_soar_routes"]

logger = get_logger(__name__)


def _make_client_getter(app_instance: FastAPI, attr: str, label: str) -> Callable[[], Any]:
    """Create a FastAPI dependency that returns the client from app state."""

    def _get() -> Any:
        client = getattr(app_instance.state, attr)
        if client is None:
            raise HTTPException(status_code=503, detail=f"{label} client not available") from None
        return client

    return _get


def _service_error(service: str, operation: str, exc: BaseException) -> HTTPException:
    """Log and build a 502 HTTPException for a failing integration client."""
    logger.exception("%s %s error", service, operation)
    return HTTPException(status_code=502, detail=f"{service} error: {exc}")


def _register_thehive_routes(app_instance: FastAPI, get_thehive_client: Callable[[], Any]) -> None:
    """Register all TheHive integration endpoints."""

    @app_instance.get("/soar/thehive/cases")
    async def thehive_list_cases(thehive: Any = Depends(get_thehive_client)) -> Any:
        """List all TheHive cases (no 10-item limit).

        Args:
            thehive: The TheHive client dependency.

        Returns:
            dict: A mapping with ``cases`` (the list of cases) and ``count``
            keys.

        Raises:
            HTTPException: 502 when the TheHive client reports an error.
        """
        try:
            cases = thehive.search_cases()
            return {"cases": cases, "count": len(cases)}
        except Exception as e:
            raise _service_error("TheHive", "list_cases", e) from e

    @app_instance.get("/soar/thehive/cases/{case_id}")
    async def thehive_get_case(case_id: str, thehive: Any = Depends(get_thehive_client)) -> Any:
        """Get a single TheHive case by ID.

        Args:
            case_id: The unique identifier of the TheHive case.
            thehive: The TheHive client dependency.

        Returns:
            dict: The TheHive case document.

        Raises:
            HTTPException: 502 when the TheHive client reports an error.
        """
        try:
            return thehive.get_case(case_id)
        except Exception as e:
            raise _service_error("TheHive", "get_case", e) from e

    @app_instance.get("/soar/thehive/cases/{case_id}/observables")
    async def thehive_get_observables(
        case_id: str,
        thehive: Any = Depends(get_thehive_client),
    ) -> Any:
        """List observables attached to a TheHive case.

        Args:
            case_id: The unique identifier of the TheHive case.
            thehive: The TheHive client dependency.

        Returns:
            dict: A mapping with ``case_id``, ``observables`` and ``count``
            keys.

        Raises:
            HTTPException: 502 when the TheHive client reports an error.
        """
        try:
            obs = thehive.get_case_observables(case_id)
            return {"case_id": case_id, "observables": obs, "count": len(obs)}
        except Exception as e:
            raise _service_error("TheHive", "get_observables", e) from e

    @app_instance.get("/soar/thehive/cases/{case_id}/tasks")
    async def thehive_get_tasks(case_id: str, thehive: Any = Depends(get_thehive_client)) -> Any:
        """List tasks for a TheHive case.

        Args:
            case_id: The unique identifier of the TheHive case.
            thehive: The TheHive client dependency.

        Returns:
            dict: A mapping with ``case_id``, ``tasks`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the TheHive client reports an error.
        """
        try:
            tasks = thehive.list_case_tasks(case_id)
            return {"case_id": case_id, "tasks": tasks, "count": len(tasks)}
        except Exception as e:
            raise _service_error("TheHive", "list_tasks", e) from e

    @app_instance.get("/soar/thehive/health")
    async def thehive_health(thehive: Any = Depends(get_thehive_client)) -> Any:
        """TheHive reachability check.

        Args:
            thehive: The TheHive client dependency.

        Returns:
            dict: A mapping with ``service`` and ``reachable`` keys.
        """
        ok = thehive.health_check()
        return {"service": SERVICE_THEHIVE, "reachable": ok}


def _register_cortex_routes(app_instance: FastAPI, get_cortex_client: Callable[[], Any]) -> None:
    """Register all Cortex integration endpoints."""

    @app_instance.get("/soar/cortex/analyzers")
    async def cortex_list_analyzers(
        data_type: str | None = None, cortex: Any = Depends(get_cortex_client)
    ) -> Any:
        """List Cortex analyzers, optionally filtered by data_type.

        Args:
            data_type: Optional data type used to filter the returned
            analyzers.
            cortex: The Cortex client dependency.

        Returns:
            dict: A mapping with ``analyzers`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the Cortex client reports an error.
        """
        try:
            if data_type:
                analyzers = cortex.list_analyzers_by_type(data_type)
            else:
                analyzers = cortex.list_analyzers()
            return {"analyzers": analyzers, "count": len(analyzers)}
        except Exception as e:
            raise _service_error("Cortex", "list_analyzers", e) from e

    @app_instance.get("/soar/cortex/jobs")
    async def cortex_list_jobs(
        start: int = 0,
        count: int = 10,
        cortex: Any = Depends(get_cortex_client),
    ) -> Any:
        """List recent Cortex analyzer jobs.

        Args:
            start: The offset of the first job to return.
            count: The maximum number of jobs to return.
            cortex: The Cortex client dependency.

        Returns:
            dict: A mapping with ``jobs`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the Cortex client reports an error.
        """
        try:
            jobs = cortex.list_jobs(start=start, count=count)
            return {"jobs": jobs, "count": len(jobs)}
        except Exception as e:
            raise _service_error("Cortex", "list_jobs", e) from e

    @app_instance.get("/soar/cortex/jobs/{job_id}")
    async def cortex_get_job(job_id: str, cortex: Any = Depends(get_cortex_client)) -> Any:
        """Get status and result of a Cortex job.

        Args:
            job_id: The unique identifier of the Cortex job.
            cortex: The Cortex client dependency.

        Returns:
            dict: The Cortex job status and result document.

        Raises:
            HTTPException: 502 when the Cortex client reports an error.
        """
        try:
            return cortex.get_job(job_id)
        except Exception as e:
            raise _service_error("Cortex", "get_job", e) from e

    @app_instance.get("/soar/cortex/jobs/{job_id}/report")
    async def cortex_get_job_report(job_id: str, cortex: Any = Depends(get_cortex_client)) -> Any:
        """Get full report of a completed Cortex job.

        Args:
            job_id: The unique identifier of the Cortex job.
            cortex: The Cortex client dependency.

        Returns:
            dict: The full Cortex job report.

        Raises:
            HTTPException: 502 when the Cortex client reports an error.
        """
        try:
            return cortex.get_job_report(job_id)
        except Exception as e:
            raise _service_error("Cortex", "get_job_report", e) from e

    @app_instance.get("/soar/cortex/health")
    async def cortex_health(cortex: Any = Depends(get_cortex_client)) -> Any:
        """Cortex reachability check.

        Args:
            cortex: The Cortex client dependency.

        Returns:
            dict: A mapping with ``service`` and ``reachable`` keys.
        """
        ok = cortex.health_check()
        return {"service": SERVICE_CORTEX, "reachable": ok}


def _register_misp_routes(app_instance: FastAPI, get_misp_client: Callable[[], Any]) -> None:
    """Register all MISP integration endpoints."""

    @app_instance.get("/soar/misp/attributes")
    async def misp_search_attributes(
        value: str | None = None,
        attr_type: str | None = None,
        limit: int = 50,
        misp: Any = Depends(get_misp_client),
    ) -> Any:
        """Search MISP attributes by value and/or type.

        Args:
            value: Optional attribute value to search for.
            attr_type: Optional attribute type to filter by.
            limit: The maximum number of attributes to return.
            misp: The MISP client dependency.

        Returns:
            dict: A mapping with ``attributes`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the MISP client reports an error.
        """
        try:
            attrs = misp.search_attributes(value=value, attr_type=attr_type, limit=limit)
            return {"attributes": attrs, "count": len(attrs)}
        except Exception as e:
            raise _service_error("MISP", "search_attributes", e) from e

    @app_instance.get("/soar/misp/events")
    async def misp_list_events(limit: int = 20, misp: Any = Depends(get_misp_client)) -> Any:
        """List recent MISP events.

        Args:
            limit: The maximum number of events to return.
            misp: The MISP client dependency.

        Returns:
            dict: A mapping with ``events`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the MISP client reports an error.
        """
        try:
            events = misp.list_events(limit=limit)
            return {"events": events, "count": len(events)}
        except Exception as e:
            raise _service_error("MISP", "list_events", e) from e

    @app_instance.get("/soar/misp/events/{event_id}")
    async def misp_get_event(event_id: str, misp: Any = Depends(get_misp_client)) -> Any:
        """Get a specific MISP event by ID.

        Args:
            event_id: The unique identifier of the MISP event.
            misp: The MISP client dependency.

        Returns:
            dict: The MISP event document.

        Raises:
            HTTPException: 502 when the MISP client reports an error.
        """
        try:
            return misp.get_event(event_id)
        except Exception as e:
            raise _service_error("MISP", "get_event", e) from e

    @app_instance.get("/soar/misp/health")
    async def misp_health(misp: Any = Depends(get_misp_client)) -> Any:
        """MISP reachability check.

        Args:
            misp: The MISP client dependency.

        Returns:
            dict: A mapping with ``service`` and ``reachable`` keys.
        """
        ok = misp.health_check()
        return {"service": SERVICE_MISP, "reachable": ok}


def _register_shuffle_routes(app_instance: FastAPI, get_shuffle_client: Callable[[], Any]) -> None:
    """Register all Shuffle integration endpoints."""

    @app_instance.get("/soar/shuffle/workflows")
    async def shuffle_list_workflows(shuffle: Any = Depends(get_shuffle_client)) -> Any:
        """List all Shuffle workflows.

        Args:
            shuffle: The Shuffle client dependency.

        Returns:
            dict: A mapping with ``workflows`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the Shuffle client reports an error.
        """
        try:
            wfs = shuffle.list_workflows()
            return {"workflows": wfs, "count": len(wfs)}
        except Exception as e:
            raise _service_error("Shuffle", "list_workflows", e) from e

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}")
    async def shuffle_get_workflow(
        workflow_id: str,
        shuffle: Any = Depends(get_shuffle_client),
    ) -> Any:
        """Get a specific Shuffle workflow.

        Args:
            workflow_id: The unique identifier of the Shuffle workflow.
            shuffle: The Shuffle client dependency.

        Returns:
            dict: The Shuffle workflow document.

        Raises:
            HTTPException: 502 when the Shuffle client reports an error.
        """
        try:
            return shuffle.get_workflow(workflow_id)
        except Exception as e:
            raise _service_error("Shuffle", "get_workflow", e) from e

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}/executions")
    async def shuffle_get_executions(
        workflow_id: str,
        shuffle: Any = Depends(get_shuffle_client),
    ) -> Any:
        """List executions for a Shuffle workflow.

        Args:
            workflow_id: The unique identifier of the Shuffle workflow.
            shuffle: The Shuffle client dependency.

        Returns:
            dict: A mapping with ``workflow_id``, ``executions`` and ``count``
            keys.

        Raises:
            HTTPException: 502 when the Shuffle client reports an error.
        """
        try:
            execs = shuffle.get_workflow_executions(workflow_id)
            return {"workflow_id": workflow_id, "executions": execs, "count": len(execs)}
        except Exception as e:
            raise _service_error("Shuffle", "get_executions", e) from e

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}/executions/{execution_id}")
    async def shuffle_get_execution(
        workflow_id: str, execution_id: str, shuffle: Any = Depends(get_shuffle_client)
    ) -> Any:
        """Get a specific Shuffle workflow execution.

        Args:
            workflow_id: The unique identifier of the Shuffle workflow.
            execution_id: The unique identifier of the workflow execution.
            shuffle: The Shuffle client dependency.

        Returns:
            dict: The Shuffle workflow execution document.

        Raises:
            HTTPException: 404 when the execution is not found, or 502 when
            the Shuffle client reports an error.
        """
        try:
            ex = shuffle.get_execution(workflow_id, execution_id)
            if ex is None:
                raise HTTPException(status_code=404, detail="Execution not found") from None
            return ex
        except HTTPException:
            raise
        except Exception as e:
            raise _service_error("Shuffle", "get_execution", e) from e

    @app_instance.get("/soar/shuffle/health")
    async def shuffle_health(shuffle: Any = Depends(get_shuffle_client)) -> Any:
        """Shuffle reachability check.

        Args:
            shuffle: The Shuffle client dependency.

        Returns:
            dict: A mapping with ``service`` and ``reachable`` keys.
        """
        ok = shuffle.health_check()
        return {"service": SERVICE_SHUFFLE, "reachable": ok}


def _register_es_routes(app_instance: FastAPI, get_elasticsearch_client: Callable[[], Any]) -> None:
    """Register all Elasticsearch integration endpoints."""

    @app_instance.get("/soar/elasticsearch/count")
    async def es_count(
        index: str | None = None,
        es: Any = Depends(get_elasticsearch_client),
    ) -> Any:
        """Return total document count for the soar-alerts index (or custom.

        index).

        Args:
            index: Optional index name; defaults to the client's configured
            index when omitted.
            es: The Elasticsearch client dependency.

        Returns:
            dict: A mapping with ``index`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the Elasticsearch client reports an error.
        """
        try:
            return {"index": index or es.index, "count": es.count(index=index)}
        except Exception as e:
            raise _service_error("Elasticsearch", "count", e) from e

    @app_instance.get("/soar/elasticsearch/latest")
    async def es_latest(
        size: int = 10, index: str | None = None, es: Any = Depends(get_elasticsearch_client)
    ) -> Any:
        """Return the most recent documents from soar-alerts.

        Args:
            size: The maximum number of documents to return.
            index: Optional index name; defaults to the client's configured
            index when omitted.
            es: The Elasticsearch client dependency.

        Returns:
            dict: A mapping with ``documents`` and ``count`` keys.

        Raises:
            HTTPException: 502 when the Elasticsearch client reports an error.
        """
        try:
            docs = es.get_latest_documents(size=size, index=index)
            return {"documents": docs, "count": len(docs)}
        except Exception as e:
            raise _service_error("Elasticsearch", "latest", e) from e

    @app_instance.get("/soar/elasticsearch/health")
    async def es_health(es: Any = Depends(get_elasticsearch_client)) -> Any:
        """Elasticsearch cluster health.

        Args:
            es: The Elasticsearch client dependency.

        Returns:
            dict: A mapping with ``service``, ``reachable`` and ``status``
            keys on success, or ``service``, ``reachable`` and ``error`` keys
            when the cluster is unreachable.
        """
        try:
            health = es.cluster_health()
            return {
                "service": SERVICE_ELASTICSEARCH,
                "reachable": True,
                "status": health.get("status"),
            }
        except Exception as e:
            return {"service": SERVICE_ELASTICSEARCH, "reachable": False, "error": str(e)}


def _register_status_route(app_instance: FastAPI) -> None:
    """Register the aggregated SOAR status endpoint."""

    @app_instance.get("/soar/status")
    async def soar_status() -> Any:
        """Aggregated health check across all SOAR integration clients.

        Returns:
            dict: Aggregated status with timestamp and per-service reachability.
        """
        results: dict[str, Any] = {"timestamp": datetime.now(UTC).isoformat()}
        for name, client in (
            (SERVICE_THEHIVE, app_instance.state.thehive_client),
            (SERVICE_CORTEX, app_instance.state.cortex_client),
            (SERVICE_MISP, app_instance.state.misp_client),
            (SERVICE_SHUFFLE, app_instance.state.shuffle_client),
            (SERVICE_ELASTICSEARCH, app_instance.state.elasticsearch_client),
        ):
            if client is None:
                results[name] = {"reachable": False, "error": "client not configured"}
            else:
                try:
                    results[name] = {"reachable": client.health_check()}
                except Exception as e:
                    results[name] = {"reachable": False, "error": str(e)}
        results["all_reachable"] = all(
            v.get("reachable", False) for v in results.values() if isinstance(v, dict)
        )
        return results


def register_soar_routes(app_instance: FastAPI) -> None:
    """Register all SOAR integration endpoints on the FastAPI app instance.

    Args:
        app_instance: The FastAPI application instance whose ``state`` holds the
            injected integration clients.
    """
    get_thehive_client = _make_client_getter(app_instance, "thehive_client", "TheHive")
    get_cortex_client = _make_client_getter(app_instance, "cortex_client", "Cortex")
    get_misp_client = _make_client_getter(app_instance, "misp_client", "MISP")
    get_shuffle_client = _make_client_getter(app_instance, "shuffle_client", "Shuffle")
    get_elasticsearch_client = _make_client_getter(
        app_instance, "elasticsearch_client", "Elasticsearch"
    )

    _register_thehive_routes(app_instance, get_thehive_client)
    _register_cortex_routes(app_instance, get_cortex_client)
    _register_misp_routes(app_instance, get_misp_client)
    _register_shuffle_routes(app_instance, get_shuffle_client)
    _register_es_routes(app_instance, get_elasticsearch_client)
    _register_status_route(app_instance)
