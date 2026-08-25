"""Service status, containment, and IoC cache endpoints for the SOAR API."""

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException

from soar_lab.config.logging import get_logger

from .models import (
    ContainmentRequest,
    ContainmentResponse,
    IocCacheRequest,
    IocCacheResponse,
)
from .route_helpers import DEFAULT_API_VERSION

__all__ = ["register_service_routes"]

logger = get_logger(__name__)


def register_service_routes(app_instance: FastAPI) -> None:
    """Register service status, containment, and IoC cache endpoints."""

    @app_instance.get("/services/status")
    async def get_services_status() -> Any:
        """Get status of all services.

        Returns:
            dict: Service name -> status info mapping.

        Raises:
            HTTPException: 500 when retrieving services status fails.
        """
        try:
            health = app_instance.state.health_service
            cp = app_instance.state.config_provider
            if health and cp:
                services_config = cp.get_service_urls()
                status = await health.get_all_services_status(services_config)
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "version": DEFAULT_API_VERSION,
                    "services": status,
                }
            return {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "version": DEFAULT_API_VERSION,
                "services": {},
            }
        except Exception as e:
            logger.exception("Error getting services status")
            raise HTTPException(status_code=500, detail="Failed to get services status") from e

    @app_instance.post("/api/v1/contain", response_model=ContainmentResponse)
    async def contain_endpoint(request: ContainmentRequest) -> Any:
        """Simulated containment endpoint for the SOAR workflow.

        Records a containment action without executing real firewall or endpoint
        commands. Used by the Shuffle workflow when the decision node classifies
        the alert as malicious.

        Args:
            request: The ContainmentRequest describing the alert, case, host
            and containment mode.

        Returns:
            ContainmentResponse: The simulated containment result including
            the actions that would have been performed and a timestamp.

        Raises:
            HTTPException: 500 when an unexpected error occurs during
            containment handling.
        """
        try:
            logger.info(
                "[CONTAINMENT] alert=%s case=%s host=%s mode=%s",
                request.alert_id,
                request.case_id,
                request.hostname,
                request.mode,
            )

            simulated_actions = [
                "network_isolation",
                "process_termination",
                "account_lockdown",
            ]

            return ContainmentResponse(
                status="simulated",
                alert_id=request.alert_id,
                case_id=request.case_id,
                hostname=request.hostname,
                actions=simulated_actions,
                timestamp=datetime.now(UTC).isoformat(),
            )
        except Exception as e:
            logger.exception("Error in containment endpoint")
            raise HTTPException(status_code=500, detail=f"Containment error: {e}") from e

    @app_instance.post("/api/v1/cache/ioc", response_model=IocCacheResponse)
    async def cache_ioc_endpoint(request: IocCacheRequest) -> Any:
        """Cache an IoC key/value in Redis on behalf of the Shuffle workflow.

        Redis speaks the RESP protocol, not HTTP, so Shuffle's generic "http"
        app node cannot POST JSON directly to port 6379 (it gets a
        connection reset). This endpoint proxies the SET through the real
        redis-py client configured on the API service.

        Args:
            request: The IocCacheRequest carrying the key, value and optional
            TTL to cache.

        Returns:
            IocCacheResponse: Whether the cache operation succeeded along with
            the key and a status message.
        """
        redis_client = app_instance.state.redis_client
        if redis_client is None:
            return IocCacheResponse(
                success=False, key=request.key, message="Redis client not available"
            )
        try:
            redis_client.set(request.key, request.value, ex=request.ttl_seconds)
            return IocCacheResponse(success=True, key=request.key, message="cached")
        except Exception as e:
            logger.warning("Error caching IoC %s: %s", request.key, e)
            return IocCacheResponse(success=False, key=request.key, message=str(e))
