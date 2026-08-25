"""FastAPI application factory and route registration for the SOAR management API."""

import asyncio
import os
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from soar_lab.common.constants import DEFAULT_API_VERSION
from soar_lab.common.exceptions import AuthError
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import WebSocketManager

from .auth import create_get_current_user
from .middleware import TraceIdMiddleware
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
from .routes_services import register_service_routes
from .routes_soar import register_soar_routes

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
) -> FastAPI:
    """Create and configure the FastAPI application with injected.

    dependencies.
    """
    if not config_provider:
        raise ValueError("config_provider is required to create FastAPI app")

    cp = config_provider
    api_title = cp.get("API_TITLE", "SOAR Lab Management API")
    api_description = cp.get("API_DESCRIPTION", "API for managing SOAR Ransomware Lab")
    api_version = cp.get("API_VERSION", DEFAULT_API_VERSION)
    cors_origins = cp.get("CORS_ORIGINS", ["*"])

    # Initialize FastAPI app
    app_instance = FastAPI(title=api_title, description=api_description, version=api_version)

    # CORS middleware - configurable via environment variable
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trace ID middleware — injects X-Request-ID for end-to-end correlation
    app_instance.add_middleware(TraceIdMiddleware)

    # Mount static files for docs (only if the directory exists)
    _docs_dir = cp.get("DOCS_DIR", "/app/docs")
    if os.path.isdir(_docs_dir):
        app_instance.mount("/static-docs", StaticFiles(directory=_docs_dir), name="docs")

    # Global exception handler for consistent error responses
    @app_instance.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTPExceptions with consistent error response format."""
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app_instance.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions with consistent error response format."""
        logger.error(f"Unhandled exception: {exc}")
        return ErrorResponse.create(
            code="internal_error", message="An internal server error occurred", status_code=500
        )

    # Create authenticated dependency with injected auth_service
    if not auth_service:
        raise ValueError("auth_service is required to create FastAPI app")
    app_instance.state.get_current_user = create_get_current_user(auth_service)

    # Store dependencies in app state for use in routes
    app_instance.state.config_provider = cp
    app_instance.state.path_service = path_service
    app_instance.state.storage = storage
    app_instance.state.alert_repository = alert_repository
    app_instance.state.system_metrics = system_metrics
    app_instance.state.health_checker = health_checker
    app_instance.state.log_reader = log_reader
    app_instance.state.pytest_parser = pytest_parser
    app_instance.state.test_runner = test_runner
    app_instance.state.backup_driver = backup_driver
    app_instance.state.analytics_service = analytics_service
    app_instance.state.backup_service = backup_service
    app_instance.state.test_service = test_service
    app_instance.state.health_service = health_service
    app_instance.state.docker_client = docker_client
    app_instance.state.redis_client = redis_client
    app_instance.state.cortex_client = cortex_client
    app_instance.state.misp_client = misp_client
    app_instance.state.shuffle_client = shuffle_client
    app_instance.state.thehive_client = thehive_client
    app_instance.state.elasticsearch_client = elasticsearch_client
    app_instance.state.websocket_manager = websocket_manager
    app_instance.state.auth_service = auth_service

    # Register routes
    _register_routes(app_instance)

    return app_instance


def _register_routes(app_instance: FastAPI) -> None:
    """Register all routes on the FastAPI app instance.

    Core routes (root, health, auth, backup, tests, websocket) are defined
    inline.  Analytics, service-status and SOAR integration routes are
    delegated to the dedicated ``routes_*`` modules to avoid duplication.
    """

    # ------------------------------------------------------------------
    # Dependency helpers (read from app.state)
    # ------------------------------------------------------------------
    def get_storage() -> object:
        """Return the storage adapter from app state or raise 503."""
        storage = app_instance.state.storage
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")
        return storage

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

    def get_test_service() -> object:
        """Return the test service from app state or raise 503."""
        test = app_instance.state.test_service
        if test is None:
            raise HTTPException(status_code=503, detail="Test service not available")
        return test

    def get_websocket_manager() -> WebSocketManager | None:
        """Return the WebSocket manager from app state."""
        return app_instance.state.websocket_manager

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
                    return docs_content
                docs_content_alt = storage.read_file("/app/api-docs.html")
                if docs_content_alt:
                    return docs_content_alt
            return _get_fallback_html()
        except Exception as e:
            logger.error(f"Error serving API documentation: {e}")
            return _get_fallback_html()

    @app_instance.get("/health")
    async def health(cp: object = Depends(get_config_provider)) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "version": cp.get("API_VERSION", DEFAULT_API_VERSION),
        }

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

    @app_instance.post("/backup/create", response_model=CreateBackupResponse)
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
            logger.error(f"Error creating backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to create backup") from e

    @app_instance.get("/backup/list", response_model=BackupListResponse)
    async def list_backups(backup: object = Depends(get_backup_service)) -> BackupListResponse:
        """List all backups."""
        try:
            result = backup.list_backups()
            backup_list = result.get("backups", []) if isinstance(result, dict) else result
            return BackupListResponse(backups=backup_list)
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise HTTPException(status_code=500, detail="Failed to list backups") from e

    @app_instance.post("/backup/restore", response_model=RestoreBackupResponse)
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
            logger.error(f"Error restoring backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to restore backup") from e

    @app_instance.post("/tests/run", response_model=RunResults)
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
            logger.error(f"Error running tests: {e}")
            raise HTTPException(status_code=500, detail="Failed to run tests") from e

    @app_instance.websocket("/ws/logs")
    async def websocket_logs(
        websocket: WebSocket,
        connection_manager: WebSocketManager | None = Depends(get_websocket_manager),
    ) -> None:
        """WebSocket endpoint for log streaming."""
        if connection_manager is None:
            await websocket.close(code=1011, reason="WebSocket manager not available")
            return

        await connection_manager.connect(websocket)

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
            connection_manager.disconnect(websocket)
            logger.info("WebSocket client disconnected")

    # ------------------------------------------------------------------
    # Delegated route modules
    # ------------------------------------------------------------------
    register_analytics_routes(app_instance, get_analytics_service)
    register_service_routes(app_instance)
    register_soar_routes(app_instance)


def _get_fallback_html() -> str:
    """Get fallback HTML when API docs are not available."""
    return """<html><head><title>SOAR Lab Management
           API</title></head><body><h1>SOAR Lab Management API</h1><p>API
           Documentation: <a href="/docs">/docs</a></p><p>Health Check: <a
           href="/health">/health</a></p></body></html>"""
