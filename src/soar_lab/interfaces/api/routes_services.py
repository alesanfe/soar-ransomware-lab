"""Service status, containment, and IoC cache endpoints for the SOAR API."""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from soar_lab.application.use_cases.containment_approval import (
    STATUS_PENDING,
    ContainmentApprovalStore,
)
from soar_lab.config.logging import get_logger

from .auth import require_api_auth
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

    @app_instance.post(
        "/api/v1/contain",
        dependencies=[Depends(require_api_auth)],
        response_model=ContainmentResponse,
    )
    def contain_endpoint(request: ContainmentRequest) -> Any:
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

            if _approvals_required(app_instance) and not _approval_granted(app_instance, request):
                return _park_for_approval(request, app_instance)

            return _execute_containment(request, app_instance)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error in containment endpoint")
            raise HTTPException(status_code=500, detail=f"Containment error: {e}") from e

    @app_instance.post(
        "/api/v1/cache/ioc",
        dependencies=[Depends(require_api_auth)],
        response_model=IocCacheResponse,
    )
    def cache_ioc_endpoint(request: IocCacheRequest) -> Any:
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

    @app_instance.get(
        "/api/v1/contain/approvals",
        dependencies=[Depends(require_api_auth)],
    )
    def list_pending_approvals() -> Any:
        """List containment actions awaiting analyst approval (F4)."""
        store = _approval_store(app_instance)
        return {
            "pending": [
                {
                    "approval_id": r["approval_id"],
                    "created_at": r["created_at"],
                    "request": r["request"],
                }
                for r in store.pending()
            ]
        }

    @app_instance.post(
        "/api/v1/contain/{approval_id}/approve",
        dependencies=[Depends(require_api_auth)],
        response_model=ContainmentResponse,
    )
    def approve_containment(approval_id: str, decided_by: str | None = None) -> Any:
        """Approve a parked containment and execute it (F4).

        The recorded request is executed exactly as if the workflow had
        resubmitted it — the approval gap is the measurable human MTTR.
        """
        record = _approval_store(app_instance).decide(
            approval_id, approve=True, decided_by=decided_by
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="approval not found or no longer pending",
            )
        logger.info(
            "[CONTAINMENT:APPROVED] approval=%s by=%s",
            approval_id,
            decided_by or "unknown",
        )
        request = ContainmentRequest(**record["request"])
        result = _execute_containment(request, app_instance)
        # The analyst-driven execution spends the ticket — a resubmit of
        # the same request with this approval_id must not run it twice.
        _approval_store(app_instance).consume(approval_id, record["request"])
        return result

    @app_instance.post(
        "/api/v1/contain/{approval_id}/reject",
        dependencies=[Depends(require_api_auth)],
    )
    def reject_containment(approval_id: str, decided_by: str | None = None) -> Any:
        """Reject a parked containment (F4)."""
        record = _approval_store(app_instance).decide(
            approval_id, approve=False, decided_by=decided_by
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="approval not found or no longer pending",
            )
        logger.info(
            "[CONTAINMENT:REJECTED] approval=%s by=%s",
            approval_id,
            decided_by or "unknown",
        )
        return {"approval_id": approval_id, "status": record["status"]}


def _execute_containment(request: ContainmentRequest, app_instance: FastAPI) -> ContainmentResponse:
    """Run the containment action (shared by direct calls and approvals)."""
    if request.mode == "enforce":
        return _enforce_containment(request, app_instance)

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


def _approval_store(app_instance: FastAPI) -> ContainmentApprovalStore:
    """Lazily attach the approval store to app state (bounded, in-memory)."""
    store = getattr(app_instance.state, "containment_approvals", None)
    if store is None:
        store = ContainmentApprovalStore()
        app_instance.state.containment_approvals = store
    return store


def _approvals_required(app_instance: FastAPI) -> bool:
    """Whether containment requires analyst approval before acting."""
    cp = getattr(app_instance.state, "config_provider", None)
    raw = None
    if cp is not None and hasattr(cp, "get"):
        raw = cp.get("SOAR_CONTAIN_REQUIRE_APPROVAL")
    if raw is None:
        raw = os.environ.get("SOAR_CONTAIN_REQUIRE_APPROVAL", "0")
    return str(raw) in ("1", "true", "yes")


def _approval_granted(app_instance: FastAPI, request: ContainmentRequest) -> bool:
    """Consume the request's approval ticket — single-use, payload-bound.

    The ticket authorizes only the exact request it was issued for: a
    borrowed ticket (approved for a different payload) or a spent one
    does not grant execution, so the request is parked for a fresh
    approval instead.
    """
    if not request.approval_id:
        return False
    record = _approval_store(app_instance).consume(request.approval_id, request.model_dump())
    return record is not None


def _park_for_approval(request: ContainmentRequest, app_instance: FastAPI) -> ContainmentResponse:
    """Record the request as pending and return a 202-style response."""
    store = _approval_store(app_instance)
    try:
        record = store.create(request.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    logger.info(
        "[CONTAINMENT:PENDING] approval=%s alert=%s host=%s",
        record["approval_id"],
        request.alert_id,
        request.hostname,
    )
    return ContainmentResponse(
        status=STATUS_PENDING,
        alert_id=request.alert_id,
        case_id=request.case_id,
        hostname=request.hostname,
        actions=[],
        timestamp=datetime.now(UTC).isoformat(),
        approval_id=record["approval_id"],
    )


def _container_snapshot(container: Any) -> dict[str, Any]:
    """Return a small verifiable snapshot of a container's network state."""
    container.reload()
    attrs = container.attrs
    networks = sorted((attrs.get("NetworkSettings") or {}).get("Networks") or {})
    state = attrs.get("State") or {}
    return {"networks": networks, "paused": bool(state.get("Paused"))}


def _resolve_enforce_target(request: ContainmentRequest, app_instance: FastAPI):
    """Validate the enforcement request and return the target container.

    Raises 403 when enforcement is disabled or the target is not an
    allowlisted victim, 400 without a target, 503 without Docker and
    404 when the container does not exist.
    """
    if os.environ.get("SOAR_CONTAIN_ENFORCE", "0") != "1":
        raise HTTPException(
            status_code=403,
            detail="Containment enforcement disabled (SOAR_CONTAIN_ENFORCE != 1)",
        )
    if not request.target_container:
        raise HTTPException(
            status_code=400,
            detail="mode='enforce' requires target_container",
        )
    client = getattr(app_instance.state, "docker_client", None)
    if client is None:
        raise HTTPException(status_code=503, detail="Docker client unavailable")

    name = request.target_container
    try:
        container = client.containers.get(name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"container '{name}' not found") from e

    labels = (container.attrs.get("Config") or {}).get("Labels") or {}
    prefix = os.environ.get("SOAR_CONTAIN_ALLOW_PREFIX", "victim_")
    allowlisted = labels.get("soar.victim") == "true" or (bool(prefix) and name.startswith(prefix))
    if not allowlisted or name.startswith("soar_") or name == "api":
        raise HTTPException(
            status_code=403,
            detail=f"container '{name}' is not an allowlisted victim",
        )
    return client, container, name


def _apply_containment_actions(client: Any, container: Any, name: str, before: dict) -> list[str]:
    """Disconnect every attached network and pause the container."""
    actions: list[str] = []
    for net in before["networks"]:
        try:
            client.networks.get(net).disconnect(container, force=True)
            actions.append(f"network_disconnect:{net}")
        except Exception as e:
            logger.warning("disconnect %s from %s failed: %s", name, net, e)
    try:
        container.pause()
        actions.append("container_pause")
    except Exception as e:
        logger.warning("pause %s failed: %s", name, e)
    return actions


def _enforce_containment(request: ContainmentRequest, app_instance: FastAPI) -> ContainmentResponse:
    """Execute a real, verifiable containment against a lab victim container.

    Enabled only when ``SOAR_CONTAIN_ENFORCE=1``. The target must be a
    container carrying the ``soar.victim=true`` label or matching the
    ``SOAR_CONTAIN_ALLOW_PREFIX`` name prefix (default ``victim_``), so
    lab infrastructure (``soar_*``) can never be contained by accident.

    Real actions: disconnect the container from every attached network
    and pause it (real process suspension). Returns before/after docker
    state as evidence so the change is externally verifiable.
    """
    client, container, name = _resolve_enforce_target(request, app_instance)

    before = _container_snapshot(container)
    actions = _apply_containment_actions(client, container, name, before)

    after = _container_snapshot(container)
    logger.info(
        "[CONTAINMENT:ENFORCED] alert=%s target=%s actions=%s",
        request.alert_id,
        name,
        actions,
    )
    return ContainmentResponse(
        status="enforced",
        alert_id=request.alert_id,
        case_id=request.case_id,
        hostname=request.hostname,
        actions=actions,
        timestamp=datetime.now(UTC).isoformat(),
        evidence={"target": name, "before": before, "after": after},
    )
