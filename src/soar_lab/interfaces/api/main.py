"""FastAPI application factory and route registration for the SOAR management API."""

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from soar_lab.common.constants import DEFAULT_API_VERSION
from soar_lab.common.exceptions import (
    AuthError,
    ConfigurationError,
    IntegrationAuthError,
    IntegrationAuthorizationError,
    IntegrationRateLimitError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
)
from soar_lab.common.exceptions import ValidationError as DomainValidationError
from soar_lab.config.logging import get_logger
from soar_lab.config.settings import missing_required_keys
from soar_lab.domain.ports import WebSocketManager
from soar_lab.infrastructure.monitoring.telemetry import init_telemetry
from soar_lab.infrastructure.ws_ticket_store import (
    LOGS_READ_SCOPE,
    WS_CLOSE,
    RedisWsTicketStore,
    TicketIssueError,
    WsTicketStore,
    has_logs_read_scope,
)
from soar_lab.interfaces.api.lifecycle import (
    register_cleanup_task,
    register_kpi_alert_task,
    register_stale_exec_gc,
    register_worker_lifecycle,
)
from soar_lab.interfaces.api.middleware.rate_limit import RedisSlidingWindowStore

from .auth import (
    DefaultDenyAuthMiddleware,
    create_get_current_user,
    require_api_auth,
)
from .middleware import (
    RateLimitMiddleware,
    RateLimitRule,
    SecurityHeadersMiddleware,
    TraceIdMiddleware,
)
from .models import (
    BackupListResponse,
    BackupRequest,
    CreateBackupResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    RestoreBackupResponse,
    RunRequest,
    RunResults,
    VerifyAuthResponse,
)
from .routes_analytics import register_analytics_routes
from .routes_grafana_alerts import register_grafana_alert_routes
from .routes_ingest import register_ingest_routes
from .routes_metrics import register_metrics_route
from .routes_services import register_service_routes
from .routes_soar import register_soar_routes
from .routes_taxii import register_taxii_routes

logger = get_logger(__name__)
security = HTTPBearer()


def create_app(
    config_provider,
    path_service=None,
    storage=None,
    alert_repository=None,
    system_metrics=None,
    health_checker=None,
    log_reader=None,
    pytest_parser=None,
    test_runner=None,
    backup_driver=None,
    analytics_service=None,
    backup_service=None,
    test_service=None,
    health_service=None,
    docker_client=None,
    redis_client=None,
    cortex_client=None,
    misp_client=None,
    shuffle_client=None,
    thehive_client=None,
    elasticsearch_client=None,
    websocket_manager: WebSocketManager = None,
    auth_service=None,
    admission_service=None,
) -> FastAPI:
    """Create and configure the FastAPI application with injected.

    dependencies.
    """
    if not config_provider:
        raise ValueError("config_provider is required to create FastAPI app")

    cp = config_provider
    _validate_strict_config(cp)

    api_title = cp.get("API_TITLE", "SOAR Lab Management API")
    api_description = cp.get("API_DESCRIPTION", "API for managing SOAR Ransomware Lab")
    api_version = cp.get("API_VERSION", DEFAULT_API_VERSION)

    # Swagger/OpenAPI UI is only enabled outside lab/dev when explicitly set.
    # API_DOCS_ENABLED=true  -> UI + openapi.json (default in lab)
    # API_DOCS_ENABLED=spec  -> only openapi.json (for CI contract checks)
    # API_DOCS_ENABLED=false -> no docs surface at all
    _docs_enabled = str(cp.get("API_DOCS_ENABLED", "true")).lower()
    _ui_enabled = _docs_enabled in ("1", "true", "on", "yes")
    _spec_enabled = _ui_enabled or _docs_enabled == "spec"

    # Initialize FastAPI app
    app_instance = FastAPI(
        title=api_title,
        description=api_description,
        version=api_version,
        docs_url="/docs" if _ui_enabled else None,
        redoc_url="/redoc" if _ui_enabled else None,
        openapi_url="/openapi.json" if _spec_enabled else None,
    )

    _add_middlewares(app_instance, cp)

    # Middleware can answer 429 on ANY route; operations with path params can
    # 404 (resource lookup), any parameterized op can 400 (domain validation
    # beyond schema), and /soar/* proxy routes surface typed 502s when the
    # downstream service errors — declare all of it so the published spec
    # reflects reality (schemathesis ST103/ST202).
    def custom_openapi():
        if app_instance.openapi_schema:
            return app_instance.openapi_schema
        spec = get_openapi(
            title=app_instance.title,
            version=app_instance.version,
            description=app_instance.description,
            routes=app_instance.routes,
        )

        def _decl(code: str, desc: str) -> dict:
            return {
                "description": desc,
                "content": {"application/json": {"schema": {}}},
            }

        for path, path_item in spec.get("paths", {}).items():
            for operation in path_item.values():
                if not (isinstance(operation, dict) and "responses" in operation):
                    continue
                responses = operation["responses"]
                responses.setdefault("429", _decl("429", "Too Many Requests — rate limit exceeded"))
                params = operation.get("parameters", [])
                if params:
                    # Query and path lookups can 404; any parameterized op
                    # can 400 (domain validation beyond schema).
                    responses.setdefault("404", _decl("404", "Resource not found"))
                    responses.setdefault("400", _decl("400", "Bad Request — domain validation"))
                if path.startswith("/soar/"):
                    responses.setdefault(
                        "502", _decl("502", "Bad Gateway — downstream service error")
                    )
                if path.startswith(("/soar/", "/analytics/")):
                    responses.setdefault(
                        "503", _decl("503", "Service Unavailable — dependency down")
                    )
        app_instance.openapi_schema = spec
        return app_instance.openapi_schema

    app_instance.openapi = custom_openapi

    # Mount static files for docs (only if the directory exists)
    _docs_dir = cp.get("DOCS_DIR", "/app/docs")
    if os.path.isdir(_docs_dir):
        app_instance.mount("/static-docs", StaticFiles(directory=_docs_dir), name="docs")

    _register_exception_handlers(app_instance)

    # Create authenticated dependency with injected auth_service
    if not auth_service:
        raise ValueError("auth_service is required to create FastAPI app")
    app_instance.state.get_current_user = create_get_current_user(auth_service)

    # Store dependencies in app state for use in routes
    for name, dep in {
        "config_provider": cp,
        "path_service": path_service,
        "storage": storage,
        "alert_repository": alert_repository,
        "system_metrics": system_metrics,
        "health_checker": health_checker,
        "log_reader": log_reader,
        "pytest_parser": pytest_parser,
        "test_runner": test_runner,
        "backup_driver": backup_driver,
        "analytics_service": analytics_service,
        "backup_service": backup_service,
        "test_service": test_service,
        "health_service": health_service,
        "docker_client": docker_client,
        "redis_client": redis_client,
        "cortex_client": cortex_client,
        "misp_client": misp_client,
        "shuffle_client": shuffle_client,
        "thehive_client": thehive_client,
        "elasticsearch_client": elasticsearch_client,
        "websocket_manager": websocket_manager,
        "auth_service": auth_service,
        "admission_service": admission_service,
    }.items():
        setattr(app_instance.state, name, dep)

    register_worker_lifecycle(app_instance, cp)
    register_cleanup_task(app_instance, cp)
    register_kpi_alert_task(app_instance, cp)
    register_stale_exec_gc(app_instance, cp)
    init_telemetry(app_instance, cp)

    # Register routes
    _register_routes(app_instance)

    return app_instance


def _validate_strict_config(cp) -> None:
    """CFG-BOOT-001: fail-fast config validation.

    Strict when ``SOAR_CONFIG_STRICT=true`` or the deployment profile is
    production — a SOAR that starts without credentials degrades every
    integration silently at runtime.
    """
    _env_profile = str(cp.get("environment") or os.getenv("SOAR_ENV", "development"))
    _strict_flag = str(os.getenv("SOAR_CONFIG_STRICT", "")).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if _strict_flag or _env_profile.lower() in ("production", "prod"):
        missing = missing_required_keys(cp)
        if missing:
            raise ConfigurationError(
                "Missing required configuration (strict mode): " + ", ".join(missing)
            )


def _build_rate_limit_store(cp):
    """Build the shared sliding-window store when RATE_LIMIT_BACKEND=redis.

    Returns None for the in-memory default or when Redis is unreachable —
    request-time failures fail open inside the middleware.
    """
    if str(cp.get("RATE_LIMIT_BACKEND", "memory")).lower() != "redis":
        return None
    # BL-RATE-005: shared sliding window — N replicas enforce one
    # budget instead of N separate ones. Construction is lazy (no
    # connection until the first command); request-time failures
    # fail open inside the middleware.
    _redis_url = cp.get("RATE_LIMIT_REDIS_URL") or cp.get("REDIS_URL")
    if not _redis_url:
        logger.warning(
            "RATE_LIMIT_BACKEND=redis but no RATE_LIMIT_REDIS_URL/REDIS_URL — "
            "falling back to in-memory"
        )
        return None
    try:
        store = RedisSlidingWindowStore.from_url(_redis_url)
        logger.info("Rate limiter using shared Redis backend")
        return store
    except Exception as exc:
        logger.warning("Redis rate-limit backend unavailable: %s", exc)
        return None


def _build_ws_ticket_store(cp):
    """Build the shared WS-ticket store when WS_TICKET_BACKEND=redis.

    Multi-worker deployments (UVICORN_WORKERS>1) need a ticket issued on
    one worker to be consumable on another — the Redis store provides
    that with atomic GETDEL single-use semantics. Falls back to the
    in-memory store (with a warning) when Redis is unreachable.
    """
    if str(cp.get("WS_TICKET_BACKEND", "memory")).lower() != "redis":
        return WsTicketStore()
    _redis_url = cp.get("WS_TICKET_REDIS_URL") or cp.get("REDIS_URL")
    if not _redis_url:
        logger.warning(
            "WS_TICKET_BACKEND=redis but no WS_TICKET_REDIS_URL/REDIS_URL — "
            "falling back to in-memory"
        )
        return WsTicketStore()
    try:
        store = RedisWsTicketStore.from_url(_redis_url)
        logger.info("WS ticket store using shared Redis backend")
        return store
    except Exception as exc:
        logger.warning("Redis WS-ticket backend unavailable: %s", exc)
        return WsTicketStore()


def _add_middlewares(app_instance: FastAPI, cp) -> None:
    """Attach middleware in registration order (last added = outermost).

    Order: CORS -> TraceId -> RateLimit -> DefaultDenyAuth -> SecurityHeaders.
    """
    # CORS middleware - configurable via environment variable
    cors_origins = cp.get("CORS_ORIGINS", ["*"])
    app_instance.add_middleware(
        CORSMiddleware,
        # nosemgrep: wildcard-cors -- env-configurable; lab default serves local UIs
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trace ID middleware — injects X-Request-ID for end-to-end correlation
    app_instance.add_middleware(TraceIdMiddleware)

    # Rate limiting — sliding window per client (token or IP). Exempts
    # health/docs/static so probes and UIs are not throttled.
    _rate_limit_enabled = str(cp.get("RATE_LIMIT_ENABLED", "true")).lower() not in (
        "0",
        "false",
        "off",
        "no",
    )
    app_instance.add_middleware(
        RateLimitMiddleware,
        per_minute=int(cp.get("RATE_LIMIT_PER_MINUTE", 100)),
        rules=[
            RateLimitRule("/auth", int(cp.get("RATE_LIMIT_AUTH_PER_MINUTE", 10))),
            RateLimitRule("/api/v1/contain", int(cp.get("RATE_LIMIT_CONTAIN_PER_MINUTE", 30))),
        ],
        exempt_paths=("/", "/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"),
        enabled=_rate_limit_enabled,
        store=_build_rate_limit_store(cp),
    )

    # AUTH-001: default-deny — every HTTP route outside the public
    # whitelist must authenticate. Middleware-level so future routes
    # cannot silently ship unauthenticated.
    app_instance.add_middleware(DefaultDenyAuthMiddleware)

    # SEC-HEADERS: added LAST so it is the outermost middleware — every
    # response (including 401/403/429/500 raised by inner middleware)
    # gets the hardened header set. HSTS is opt-out for plain-HTTP dev.
    _hsts = str(cp.get("SECURITY_HSTS_ENABLED", "true")).lower() not in (
        "0",
        "false",
        "off",
        "no",
    )
    app_instance.add_middleware(SecurityHeadersMiddleware, hsts_enabled=_hsts)


def _register_exception_handlers(app_instance: FastAPI) -> None:
    """Global exception handlers for consistent error responses."""

    @app_instance.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTPExceptions with consistent error response format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    # BL-ERR-003: domain/infra errors must not collapse into a bare 500 —
    # a downstream outage is a 503/504/502, a validation failure a 422,
    # an auth problem 401/403. Anything else is a genuine internal error.
    error_status: tuple[tuple[type[Exception], int, str], ...] = (
        (IntegrationTimeoutError, 504, "integration_timeout"),
        (IntegrationUnavailableError, 503, "integration_unavailable"),
        (IntegrationRateLimitError, 503, "integration_rate_limited"),
        (IntegrationAuthError, 502, "integration_auth_failed"),
        (IntegrationAuthorizationError, 502, "integration_forbidden"),
        (DomainValidationError, 422, "validation_failed"),
        (AuthError, 401, "auth_failed"),
    )

    @app_instance.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions with consistent error response format."""
        logger.exception("Unhandled exception: %s", exc)
        for exc_type, status_code, code in error_status:
            if isinstance(exc, exc_type):
                resolved = exc.status_code if isinstance(exc, AuthError) else status_code
                return ErrorResponse.create(
                    code=code,
                    message=(
                        "A downstream service error occurred" if status_code >= 500 else str(exc)
                    ),
                    status_code=resolved,
                )
        return ErrorResponse.create(
            code="internal_error", message="An internal server error occurred", status_code=500
        )


def _register_routes(app_instance: FastAPI) -> None:
    """Register all routes on the FastAPI app instance.

    Core routes (root, health, auth, backup, tests, websocket) are defined
    inline.  Analytics, service-status and SOAR integration routes are
    delegated to the dedicated ``routes_*`` modules to avoid duplication.
    """

    # ------------------------------------------------------------------
    # Dependency helpers (read from app.state)
    # ------------------------------------------------------------------
    def get_config_provider() -> object:
        """Return the config provider from app state or raise 503."""
        cp = app_instance.state.config_provider
        if cp is None:
            raise HTTPException(status_code=503, detail="Config provider not available")
        return cp

    def get_analytics_service() -> object:
        """Return the analytics service from app state or raise 503."""
        analytics = app_instance.state.analytics_service
        if analytics is None:
            raise HTTPException(status_code=503, detail="Analytics service not available")
        return analytics

    def get_backup_service() -> object:
        """Return the backup service from app state or raise 503."""
        backup = app_instance.state.backup_service
        if backup is None:
            raise HTTPException(status_code=503, detail="Backup service not available")
        return backup

    def get_websocket_manager() -> WebSocketManager | None:
        """Return the WebSocket manager from app state."""
        return app_instance.state.websocket_manager

    def _ws_ticket_store(app: FastAPI):

        store = getattr(app.state, "ws_ticket_store", None)
        if store is None:
            store = _build_ws_ticket_store(app.state.config_provider)
            app.state.ws_ticket_store = store
        return store

    def _ws_user_counts(app: FastAPI) -> dict:
        counts = getattr(app.state, "ws_user_counts", None)
        if counts is None:
            counts = {}
            app.state.ws_user_counts = counts
        return counts

    def get_auth_service() -> object | None:
        """Return the auth service from app state."""
        return app_instance.state.auth_service

    # ------------------------------------------------------------------
    # Core routes (not in routes_*.py)
    # ------------------------------------------------------------------
    @app_instance.get("/", response_class=HTMLResponse)
    async def root() -> HTMLResponse:
        """Root endpoint - API documentation."""
        try:
            storage = app_instance.state.storage
            if storage:
                docs_content = storage.read_file("api-docs.html")
                if docs_content:
                    return _filter_docs_portal(docs_content, app_instance.docs_url is not None)
                docs_content_alt = storage.read_file("/app/api-docs.html")
                if docs_content_alt:
                    return _filter_docs_portal(docs_content_alt, app_instance.docs_url is not None)
            return _get_fallback_html()
        except Exception:
            logger.exception("Error serving API documentation")
            return _get_fallback_html()

    @app_instance.get("/health")
    @app_instance.get("/health/live")
    async def health(cp: object = Depends(get_config_provider)) -> dict:
        """Liveness probe — the process is up and serving."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": cp.get("API_VERSION", DEFAULT_API_VERSION),
        }

    @app_instance.get("/health/ready")
    async def readiness(
        cp: object = Depends(get_config_provider),
    ) -> dict:
        """BL-ARCH-003/004: readiness probe — check real dependencies.

        Verifies storage writability and, when alert ingestion is
        enabled, the admission queue. Returns 503 with per-check detail
        when any dependency is unavailable, so orchestrators stop
        routing traffic instead of discovering the outage as failed
        requests.
        """
        checks: dict[str, dict[str, Any]] = {}

        def _timed(fn) -> dict[str, Any]:
            """Run a probe and report status + wall-clock latency."""
            start = time.monotonic()
            try:
                detail = fn()
                return {
                    "status": "ok",
                    "detail": detail,
                    "latency_ms": round((time.monotonic() - start) * 1000, 1),
                }
            except Exception as exc:
                return {
                    "status": "fail",
                    "detail": type(exc).__name__,
                    "latency_ms": round((time.monotonic() - start) * 1000, 1),
                }

        storage = getattr(app_instance.state, "storage", None)
        checks["storage"] = _timed(
            lambda: (
                "probe-absent"
                if storage is None or storage.get_file_info("__ready_probe__") is None
                else "probe-present"
            )
        )

        ingest_enabled = str(cp.get("ALERT_INGEST_ENABLED", "true")).lower() not in (
            "0",
            "false",
            "off",
            "no",
        )
        if ingest_enabled:
            service = getattr(app_instance.state, "admission_service", None)
            queue = getattr(service, "queue", None)
            if queue is None:
                checks["admission_queue"] = {
                    "status": "fail",
                    "detail": "not-configured",
                    "latency_ms": 0.0,
                }
            else:
                checks["admission_queue"] = _timed(lambda: (queue.metrics(), "reachable")[1])

        ready = all(c["status"] == "ok" for c in checks.values())
        payload = {
            "status": "ready" if ready else "not_ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "checks": checks,
        }
        if not ready:
            raise HTTPException(status_code=503, detail=payload)
        return payload

    @app_instance.post("/auth/login", response_model=LoginResponse)
    async def login(
        request: LoginRequest,
        auth: object = Depends(get_auth_service),
    ) -> LoginResponse:
        """Login endpoint - returns JWT token."""
        try:
            if auth.verify_credentials(request.username, request.password):
                token = auth.create_jwt_token(request.username)
                return LoginResponse(token=token, message="Login successful")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e

    @app_instance.post("/auth/verify", response_model=VerifyAuthResponse)
    async def verify_auth(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> VerifyAuthResponse:
        """Verify JWT token endpoint."""
        try:
            get_current_user = app_instance.state.get_current_user
            user = get_current_user(credentials)
            return VerifyAuthResponse(
                valid=True, user=user if isinstance(user, dict) else {"user": str(user)}
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid token") from exc

    @app_instance.post(
        "/backup/create",
        dependencies=[Depends(require_api_auth)],
        response_model=CreateBackupResponse,
    )
    async def create_backup(
        request: BackupRequest,
        backup: object = Depends(get_backup_service),
    ) -> CreateBackupResponse:
        """Create a backup."""
        try:
            result = backup.create()
            return CreateBackupResponse(
                backup_name=result.get("filename")
                or result.get("backup_name")
                or result.get("name", request.backup_name),
                status=result.get("status", "success"),
                message=result.get("message", "Backup created successfully"),
            )
        except Exception as e:
            logger.exception("Error creating backup")
            raise HTTPException(status_code=500, detail="Failed to create backup") from e

    @app_instance.get(
        "/backup/list",
        dependencies=[Depends(require_api_auth)],
        response_model=BackupListResponse,
    )
    async def list_backups(backup: object = Depends(get_backup_service)) -> BackupListResponse:
        """List all backups."""
        try:
            result = backup.list_backups()
            backup_list = result.get("backups", []) if isinstance(result, dict) else result
            return BackupListResponse(backups=backup_list)
        except Exception as e:
            logger.exception("Error listing backups")
            raise HTTPException(status_code=500, detail="Failed to list backups") from e

    @app_instance.post(
        "/backup/restore",
        dependencies=[Depends(require_api_auth)],
        response_model=RestoreBackupResponse,
    )
    async def restore_backup(
        request: BackupRequest,
        backup: object = Depends(get_backup_service),
    ) -> RestoreBackupResponse:
        """Restore a backup."""
        try:
            result = backup.restore(backup_name=request.backup_name)
            return RestoreBackupResponse(
                backup_name=result.get("backup_name", request.backup_name),
                status=result.get("status", "success"),
                message=result.get("message", "Backup restored successfully"),
            )
        except Exception as e:
            logger.exception("Error restoring backup")
            raise HTTPException(status_code=500, detail="Failed to restore backup") from e

    @app_instance.post(
        "/tests/run",
        dependencies=[Depends(require_api_auth)],
        response_model=RunResults,
    )
    async def run_tests(request: RunRequest) -> RunResults:
        """Run tests."""
        try:
            test = app_instance.state.test_service
            if test:
                result = await test.run_tests(category=request.category)
                return RunResults(
                    category=result.get("category", request.category),
                    passed=result.get("passed", 0),
                    failed=result.get("failed", 0),
                    skipped=result.get("skipped", 0),
                    coverage=result.get("coverage", 0.0),
                    output=result.get("output", ""),
                    duration=result.get("duration", 0.0),
                )
            return RunResults(
                category=request.category,
                passed=0,
                failed=0,
                skipped=0,
                coverage=0.0,
                output="Test service not available",
                duration=0.0,
            )
        except Exception as e:
            logger.exception("Error running tests")
            raise HTTPException(status_code=500, detail="Failed to run tests") from e

    @app_instance.post("/auth/ws-ticket")
    async def issue_ws_ticket(
        user_info: dict = Depends(require_api_auth),
    ) -> dict[str, object]:
        """Issue a single-use, 30 s ticket for ``/ws/logs`` (WEB-AUTH-001).

        Requires the same auth as mutating endpoints (JWT or service token)
        plus the ``logs:read`` scope (WEB-AUTH-003). Rate-limited by pending
        tickets per identity.
        """
        identity = user_info.get("user") or user_info.get("service") or "unknown"
        if not has_logs_read_scope(user_info):
            raise HTTPException(status_code=403, detail="logs:read scope required")
        store = _ws_ticket_store(app_instance)
        try:
            ticket = await run_in_threadpool(store.issue, user=str(identity), scope=LOGS_READ_SCOPE)
        except TicketIssueError:
            raise HTTPException(
                status_code=429,
                detail="Too many pending tickets",
                headers={"Retry-After": "5"},
            ) from None
        logger.info("WS ticket issued for user=%s", identity)
        return {"ticket": ticket, "expires_in": int(store.ttl)}

    @app_instance.websocket("/ws/logs")
    async def websocket_logs(
        websocket: WebSocket,
        connection_manager: WebSocketManager | None = Depends(get_websocket_manager),
    ) -> None:
        """Websocket endpoint for log streaming.

        Requires ``?ticket=<single-use ticket>`` from POST /auth/ws-ticket
        (WEB-AUTH-001). Close codes: 4401 missing/invalid/reused, 4403
        unauthorized, 4408 expired, 4429 per-user limit (WEB-AUTH-002/004).
        """
        if connection_manager is None:
            await websocket.close(code=1011, reason="WebSocket manager not available")
            return

        store = _ws_ticket_store(app_instance)
        cp = getattr(app_instance.state, "config_provider", None)
        auth_on = cp is None or str(cp.get("API_REQUIRE_AUTH", "true")).lower() not in (
            "0",
            "false",
            "off",
            "no",
        )

        user = "anonymous"
        if auth_on:
            result = await run_in_threadpool(store.consume, websocket.query_params.get("ticket"))
            if not result.ok:
                code = (
                    WS_CLOSE["expired"]
                    if result.reason == "expired"
                    else WS_CLOSE["unauthenticated"]
                )
                await websocket.close(code=code, reason="ticket required")
                logger.info("WS /ws/logs rejected: %s", result.reason)
                return
            user = result.user or "unknown"

            # Per-user connection limit (WEB-AUTH-004): max 3 live sockets.
            counts = _ws_user_counts(app_instance)
            if counts.get(user, 0) >= 3:
                await websocket.close(code=WS_CLOSE["limit"], reason="connection limit")
                return

        # Charge the slot only once the socket is live — a connect that
        # raises must not leak one of the user's three concurrent slots.
        await connection_manager.connect(websocket)
        if auth_on:
            counts[user] = counts.get(user, 0) + 1

        try:
            log_reader = app_instance.state.log_reader
            if log_reader:
                async for log_entry in log_reader.stream_logs():
                    await websocket.send_json(log_entry)
            else:
                while True:
                    log_entry = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "INFO",
                        "message": "Log reader not available - simulated log entry",
                    }
                    await websocket.send_json(log_entry)
                    await asyncio.sleep(1)
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        finally:
            connection_manager.disconnect(websocket)
            if auth_on:
                counts = _ws_user_counts(app_instance)
                counts[user] = max(0, counts.get(user, 1) - 1)

    # ------------------------------------------------------------------
    # Delegated route modules
    # ------------------------------------------------------------------
    register_analytics_routes(app_instance, get_analytics_service)
    register_service_routes(app_instance)
    register_soar_routes(app_instance)
    register_ingest_routes(app_instance)
    register_taxii_routes(app_instance)
    register_metrics_route(app_instance)
    register_grafana_alert_routes(app_instance)


def _filter_docs_portal(html: str, ui_enabled: bool) -> str:
    """Remove links to disabled doc UIs from the static portal page.

    When ``API_DOCS_ENABLED=spec`` the interactive Swagger/ReDoc UIs are
    not mounted — the portal must not advertise dead links. Cards are
    identified by their href so the filter is robust to markup drift.
    """
    if ui_enabled:
        return html
    for href in ('href="/docs"', 'href="/redoc"'):
        start = html.find(f'<a class="service-card" {href}')
        if start == -1:
            continue
        end = html.find("</a>", start)
        if end != -1:
            html = html[:start] + html[end + len("</a>") :]
    return html


def _get_fallback_html() -> str:
    """Get fallback HTML when API docs are not available."""
    return """<html><head><title>SOAR Lab Management
           API</title></head><body><h1>SOAR Lab Management API</h1><p>API
           Documentation: <a href="/docs">/docs</a></p><p>Health Check: <a
           href="/health">/health</a></p></body></html>"""
