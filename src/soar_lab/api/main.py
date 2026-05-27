import asyncio
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from typing import Annotated, Dict, Any, Optional

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import WebSocketManager
from soar_lab.exceptions import AuthError
from .auth import create_get_current_user
from .models import (
    LoginRequest, LoginResponse, VerifyAuthResponse, TestRequest, BackupRequest,
    Metrics, TestResults, BackupListResponse, CreateBackupResponse,
    RestoreBackupResponse, HealthResponse, ErrorResponse
)

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
        websocket_manager: WebSocketManager = None,
        auth_service=None
) -> FastAPI:
    """Create and configure the FastAPI application with injected dependencies."""
    if not config_provider:
        raise ValueError("config_provider is required to create FastAPI app")

    cp = config_provider
    api_title = cp.get('API_TITLE', 'SOAR Lab Management API')
    api_description = cp.get('API_DESCRIPTION', 'API for managing SOAR Ransomware Lab')
    api_version = cp.get('API_VERSION', '1.0.0')
    cors_origins = cp.get('CORS_ORIGINS', ['*'])

    # Initialize FastAPI app
    app_instance = FastAPI(
        title=api_title,
        description=api_description,
        version=api_version
    )

    # CORS middleware - configurable via environment variable
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files for docs
    app_instance.mount("/docs", StaticFiles(directory="/app/docs"), name="docs")

    # Global exception handler for consistent error responses
    @app_instance.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTPExceptions with consistent error response format."""
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app_instance.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions with consistent error response format."""
        logger.error(f"Unhandled exception: {exc}")
        return ErrorResponse.create(
            code="internal_error",
            message="An internal server error occurred",
            status_code=500
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
    app_instance.state.websocket_manager = websocket_manager
    app_instance.state.auth_service = auth_service

    # Register routes
    _register_routes(app_instance)

    return app_instance


def _register_routes(app_instance: FastAPI):
    """Register all routes on the FastAPI app instance."""

    # Dependency functions that read from app.state
    def get_storage():
        storage = app_instance.state.storage
        if storage is None:
            raise HTTPException(status_code=503, detail="Storage not available")
        return storage

    def get_config_provider():
        cp = app_instance.state.config_provider
        if cp is None:
            raise HTTPException(status_code=503, detail="Config provider not available")
        return cp

    def get_analytics_service():
        analytics = app_instance.state.analytics_service
        if analytics is None:
            raise HTTPException(status_code=503, detail="Analytics service not available")
        return analytics

    def get_backup_service():
        backup = app_instance.state.backup_service
        if backup is None:
            raise HTTPException(status_code=503, detail="Backup service not available")
        return backup

    def get_test_service():
        test = app_instance.state.test_service
        if test is None:
            raise HTTPException(status_code=503, detail="Test service not available")
        return test

    def get_health_service():
        health = app_instance.state.health_service
        if health is None:
            raise HTTPException(status_code=503, detail="Health service not available")
        return health

    def get_websocket_manager():
        return app_instance.state.websocket_manager

    def get_auth_service():
        return app_instance.state.auth_service

    @app_instance.get("/", response_class=HTMLResponse)
    async def root():
        """Root endpoint - API documentation."""
        try:
            # Try to use storage if available
            storage = app_instance.state.storage
            if storage:
                docs_content = storage.read_file("api-docs.html")
                if docs_content:
                    return docs_content

                # Try alternative path through storage
                docs_content_alt = storage.read_file("/app/api-docs.html")
                if docs_content_alt:
                    return docs_content_alt

            # Fallback to simple HTML
            return _get_fallback_html()
        except Exception as e:
            logger.error(f"Error serving API documentation: {e}")
            return _get_fallback_html()

    @app_instance.get("/health")
    async def health(cp=Depends(get_config_provider)):
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": cp.get('API_VERSION', '1.0.0')
        }

    @app_instance.post("/auth/login", response_model=LoginResponse)
    async def login(request: LoginRequest, auth=Depends(get_auth_service)):
        """Login endpoint - returns JWT token."""
        try:
            if auth.verify_credentials(request.username, request.password):
                token = auth.create_jwt_token(request.username)
                return LoginResponse(token=token, message="Login successful", token_type="bearer")
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @app_instance.post("/auth/verify", response_model=VerifyAuthResponse)
    async def verify_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify JWT token endpoint."""
        try:
            get_current_user = app_instance.state.get_current_user
            user = get_current_user(credentials)
            return VerifyAuthResponse(valid=True, username=user.get("user"))
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid token")

    @app_instance.get("/analytics/metrics", response_model=Metrics)
    async def get_metrics():
        """Get system metrics."""
        try:
            system_metrics = app_instance.state.system_metrics
            if system_metrics:
                metrics = system_metrics.get_hardware_metrics()
                return Metrics(
                    cpu=metrics.get('cpu', {}).get('percent', 0.0),
                    memory=metrics.get('memory', {}).get('percent', 0.0),
                    disk=metrics.get('disk', {}).get('percent', 0.0),
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                # Return mock data if system_metrics not available
                return Metrics(
                    cpu=50.0,
                    memory=60.0,
                    disk=70.0,
                    timestamp=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to get metrics")

    @app_instance.get("/analytics/kpis")
    async def get_kpis(log_file_path: Optional[str] = None, analytics=Depends(get_analytics_service)):
        """Get KPI metrics."""
        try:
            return analytics.get_comprehensive_kpis(log_file_path)
        except Exception as e:
            logger.error(f"Error getting KPIs: {e}")
            raise HTTPException(status_code=500, detail="Failed to get KPIs")

    @app_instance.post("/backup/create", response_model=CreateBackupResponse)
    async def create_backup(request: BackupRequest, backup=Depends(get_backup_service)):
        """Create a backup."""
        try:
            result = backup.create_backup(
                backup_type=request.backup_type,
                source_dir=request.source_dir,
                include_metadata=request.include_metadata
            )
            return CreateBackupResponse(
                backup_name=result.get("backup_name"),
                status=result.get("status"),
                message=result.get("message")
            )
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to create backup")

    @app_instance.get("/backup/list", response_model=BackupListResponse)
    async def list_backups(backup=Depends(get_backup_service)):
        """List all backups."""
        try:
            backups = backup.list_backups()
            return BackupListResponse(backups=backups)
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise HTTPException(status_code=500, detail="Failed to list backups")

    @app_instance.post("/backup/restore", response_model=RestoreBackupResponse)
    async def restore_backup(request: BackupRequest, backup=Depends(get_backup_service)):
        """Restore a backup."""
        try:
            result = backup.restore_backup(
                backup_name=request.backup_name,
                target_dir=request.target_dir
            )
            return RestoreBackupResponse(
                backup_name=result.get("backup_name"),
                status=result.get("status"),
                message=result.get("message")
            )
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to restore backup")

    @app_instance.post("/tests/run", response_model=TestResults)
    async def run_tests(request: TestRequest):
        """Run tests."""
        try:
            test = app_instance.state.test_service
            if test:
                result = await test.run_tests(category=request.category)
                return TestResults(
                    category=result.get("category", request.category),
                    passed=result.get("passed", 0),
                    failed=result.get("failed", 0),
                    skipped=result.get("skipped", 0),
                    coverage=result.get("coverage", 0.0),
                    output=result.get("output", ""),
                    duration=result.get("duration", 0.0)
                )
            else:
                # Return mock data if test service not available
                return TestResults(
                    category=request.category,
                    passed=0,
                    failed=0,
                    skipped=0,
                    coverage=0.0,
                    output="Test service not available",
                    duration=0.0
                )
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            raise HTTPException(status_code=500, detail="Failed to run tests")

    @app_instance.get("/services/status")
    async def get_services_status():
        """Get status of all services."""
        try:
            health = app_instance.state.health_service
            cp = app_instance.state.config_provider
            if health and cp:
                services_config = cp.get_service_urls()
                status = await health.get_all_services_status(services_config)
                # Return the actual service status
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "services": status
                }
            else:
                # Return mock data if health service not available
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0",
                    "services": {}
                }
        except Exception as e:
            logger.error(f"Error getting services status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get services status")

    @app_instance.websocket("/ws/logs")
    async def websocket_logs(websocket: WebSocket, connection_manager=Depends(get_websocket_manager)):
        """WebSocket endpoint for log streaming."""
        if connection_manager is None:
            raise HTTPException(status_code=503, detail="WebSocket manager not available")

        await connection_manager.connect(websocket)

        try:
            while True:
                # Simulate log streaming
                log_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "INFO",
                    "message": "Simulated log entry"
                }
                await websocket.send_json(log_entry)
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
            logger.info("WebSocket client disconnected")


def _get_fallback_html() -> str:
    """Get fallback HTML when API docs are not available."""
    try:
        # Try to read from static file using injected storage
        storage = app_instance.state.storage if hasattr(app_instance, 'state') else None
        if storage:
            fallback_content = storage.read_file("static/fallback.html")
            if fallback_content:
                return fallback_content
    except Exception as e:
        logger.error(f"Error reading fallback HTML: {e}")

    # Return basic HTML as last resort
    return """<html><head><title>SOAR Lab Management API</title></head><body><h1>SOAR Lab Management API</h1><p>API Documentation: <a href="/docs">/docs</a></p><p>Health Check: <a href="/health">/health</a></p></body></html>"""
