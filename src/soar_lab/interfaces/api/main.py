import asyncio
import json
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from soar_lab.common.exceptions import AuthError
from typing import Annotated, Dict, Any, Optional

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import WebSocketManager
from .auth import create_get_current_user
from .models import (
    LoginRequest, LoginResponse, VerifyAuthResponse, RunRequest, BackupRequest,
    Metrics, RunResults, BackupListResponse, CreateBackupResponse,
    RestoreBackupResponse, ErrorResponse
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
    elasticsearch_client=None,
    wazuh_client=None,
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

    # Mount static files for docs (only if the directory exists)
    _docs_dir = cp.get('DOCS_DIR', '/app/docs')
    if os.path.isdir(_docs_dir):
        app_instance.mount("/static-docs", StaticFiles(directory=_docs_dir), name="docs")

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
    app_instance.state.elasticsearch_client = elasticsearch_client
    app_instance.state.wazuh_client = wazuh_client
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
                return LoginResponse(token=token, message="Login successful")
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
            return VerifyAuthResponse(valid=True, user=user if isinstance(user, dict) else {"user": str(user)})
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
            result = backup.create()
            return CreateBackupResponse(
                backup_name=result.get("filename") or result.get("backup_name") or result.get("name",
                                                                                              request.backup_name),
                status=result.get("status", "success"),
                message=result.get("message", "Backup created successfully")
            )
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to create backup")

    @app_instance.get("/backup/list", response_model=BackupListResponse)
    async def list_backups(backup=Depends(get_backup_service)):
        """List all backups."""
        try:
            result = backup.list_backups()
            backup_list = result.get("backups", []) if isinstance(result, dict) else result
            return BackupListResponse(backups=backup_list)
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise HTTPException(status_code=500, detail="Failed to list backups")

    @app_instance.post("/backup/restore", response_model=RestoreBackupResponse)
    async def restore_backup(request: BackupRequest, backup=Depends(get_backup_service)):
        """Restore a backup."""
        try:
            result = backup.restore(backup_name=request.backup_name)
            return RestoreBackupResponse(
                backup_name=result.get("backup_name", request.backup_name),
                status=result.get("status", "success"),
                message=result.get("message", "Backup restored successfully")
            )
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise HTTPException(status_code=500, detail="Failed to restore backup")

    @app_instance.post("/tests/run", response_model=RunResults)
    async def run_tests(request: RunRequest):
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
                    duration=result.get("duration", 0.0)
                )
            else:
                # Return mock data if test service not available
                return RunResults(
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

    # ------------------------------------------------------------------
    # Integration client dependency helpers
    # ------------------------------------------------------------------

    def get_thehive_client():
        client = app_instance.state.thehive_client
        if client is None:
            raise HTTPException(status_code=503, detail="TheHive client not available")
        return client

    def get_cortex_client():
        client = app_instance.state.cortex_client
        if client is None:
            raise HTTPException(status_code=503, detail="Cortex client not available")
        return client

    def get_misp_client():
        client = app_instance.state.misp_client
        if client is None:
            raise HTTPException(status_code=503, detail="MISP client not available")
        return client

    def get_shuffle_client():
        client = app_instance.state.shuffle_client
        if client is None:
            raise HTTPException(status_code=503, detail="Shuffle client not available")
        return client

    def get_elasticsearch_client():
        client = app_instance.state.elasticsearch_client
        if client is None:
            raise HTTPException(status_code=503, detail="Elasticsearch client not available")
        return client

    def get_wazuh_client():
        client = app_instance.state.wazuh_client
        if client is None:
            raise HTTPException(status_code=503, detail="Wazuh client not available")
        return client

    # ------------------------------------------------------------------
    # TheHive routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/thehive/cases")
    async def thehive_list_cases(thehive=Depends(get_thehive_client)):
        """List all TheHive cases (no 10-item limit)."""
        try:
            cases = thehive.search_cases()
            return {"cases": cases, "count": len(cases)}
        except Exception as e:
            logger.error(f"TheHive list_cases error: {e}")
            raise HTTPException(status_code=502, detail=f"TheHive error: {e}")

    @app_instance.get("/soar/thehive/cases/{case_id}")
    async def thehive_get_case(case_id: str, thehive=Depends(get_thehive_client)):
        """Get a single TheHive case by ID."""
        try:
            return thehive.get_case(case_id)
        except Exception as e:
            logger.error(f"TheHive get_case error: {e}")
            raise HTTPException(status_code=502, detail=f"TheHive error: {e}")

    @app_instance.get("/soar/thehive/cases/{case_id}/observables")
    async def thehive_get_observables(case_id: str, thehive=Depends(get_thehive_client)):
        """List observables (artifacts) attached to a TheHive case."""
        try:
            obs = thehive.get_case_observables(case_id)
            return {"case_id": case_id, "observables": obs, "count": len(obs)}
        except Exception as e:
            logger.error(f"TheHive get_observables error: {e}")
            raise HTTPException(status_code=502, detail=f"TheHive error: {e}")

    @app_instance.get("/soar/thehive/cases/{case_id}/tasks")
    async def thehive_get_tasks(case_id: str, thehive=Depends(get_thehive_client)):
        """List tasks for a TheHive case."""
        try:
            tasks = thehive.list_case_tasks(case_id)
            return {"case_id": case_id, "tasks": tasks, "count": len(tasks)}
        except Exception as e:
            logger.error(f"TheHive list_tasks error: {e}")
            raise HTTPException(status_code=502, detail=f"TheHive error: {e}")

    @app_instance.get("/soar/thehive/health")
    async def thehive_health(thehive=Depends(get_thehive_client)):
        """TheHive reachability check."""
        ok = thehive.health_check()
        return {"service": "thehive", "reachable": ok}

    @app_instance.get("/analytics/kpis/aggregated")
    async def get_aggregated_kpis(hours: int = 24):
        """Get aggregated KPI metrics from Elasticsearch soar-metrics index."""
        try:
            # Create Elasticsearch client directly
            from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
            from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
            from soar_lab.config.settings import create_settings

            settings = create_settings()
            config_provider = InfrastructureConfigProvider(settings)
            es = ElasticsearchClient(
                base_url=config_provider.get('elasticsearch_url'),
                config_provider=config_provider
            )

            # Fetch metrics from Elasticsearch
            metrics_data = es.get_latest_documents(size=10000, index="soar-metrics")

            if not metrics_data:
                return {
                    "period_hours": hours,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_alerts": 0,
                    "by_alert_type": {},
                    "services": {}
                }

            # Import KPIAnalyzer and StatisticalCalculator
            from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
            from soar_lab.domain.statistical_calculator import StatisticalCalculator

            # Calculate KPIs
            statistical_calculator = StatisticalCalculator()
            kpi_analyzer = KPIAnalyzer(statistical_calculator)

            # Calculate KPIs by alert type
            kpis_by_type = kpi_analyzer.calculate_kpis_by_alert_type(metrics_data, hours)

            # Calculate service integration KPIs
            service_kpis = kpi_analyzer.calculate_service_integration_kpis(metrics_data, hours)

            # Extract MTTR values for overall statistics
            mttr_values = []
            for metric in metrics_data:
                mttr_field = metric.get("mttr_seconds", {})
                if isinstance(mttr_field, dict):
                    mttr_str = mttr_field.get("message", "")
                    if "MTTR:" in mttr_str:
                        try:
                            mttr = float(mttr_str.split("MTTR:")[1].split("s")[0].strip())
                            mttr_values.append(mttr)
                        except (ValueError, IndexError):
                            pass
                elif isinstance(mttr_field, (int, float)):
                    mttr_values.append(mttr_field)

            # Calculate MTTR statistics
            mttr_stats = {}
            if mttr_values:
                mttr_stats = statistical_calculator.calculate_statistical_metrics(mttr_values)

            return {
                "period_hours": hours,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_alerts": len(metrics_data),
                "mttr_statistics": mttr_stats,
                "by_alert_type": kpis_by_type.get("by_alert_type", {}),
                "services": service_kpis.get("services", {})
            }
        except Exception as e:
            logger.error(f"Error getting aggregated KPIs: {e}")
            raise HTTPException(status_code=500, detail="Failed to get aggregated KPIs")

    # ------------------------------------------------------------------
    # Cortex routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/cortex/analyzers")
    async def cortex_list_analyzers(data_type: Optional[str] = None,
                                    cortex=Depends(get_cortex_client)):
        """List Cortex analyzers, optionally filtered by data_type."""
        try:
            if data_type:
                analyzers = cortex.list_analyzers_by_type(data_type)
            else:
                analyzers = cortex.list_analyzers()
            return {"analyzers": analyzers, "count": len(analyzers)}
        except Exception as e:
            logger.error(f"Cortex list_analyzers error: {e}")
            raise HTTPException(status_code=502, detail=f"Cortex error: {e}")

    @app_instance.get("/soar/cortex/jobs")
    async def cortex_list_jobs(start: int = 0, count: int = 10,
                               cortex=Depends(get_cortex_client)):
        """List recent Cortex analyzer jobs."""
        try:
            jobs = cortex.list_jobs(start=start, count=count)
            return {"jobs": jobs, "count": len(jobs)}
        except Exception as e:
            logger.error(f"Cortex list_jobs error: {e}")
            raise HTTPException(status_code=502, detail=f"Cortex error: {e}")

    @app_instance.get("/soar/cortex/jobs/{job_id}")
    async def cortex_get_job(job_id: str, cortex=Depends(get_cortex_client)):
        """Get status and result of a Cortex job."""
        try:
            return cortex.get_job(job_id)
        except Exception as e:
            logger.error(f"Cortex get_job error: {e}")
            raise HTTPException(status_code=502, detail=f"Cortex error: {e}")

    @app_instance.get("/soar/cortex/jobs/{job_id}/report")
    async def cortex_get_job_report(job_id: str, cortex=Depends(get_cortex_client)):
        """Get full report of a completed Cortex job."""
        try:
            return cortex.get_job_report(job_id)
        except Exception as e:
            logger.error(f"Cortex get_job_report error: {e}")
            raise HTTPException(status_code=502, detail=f"Cortex error: {e}")

    @app_instance.get("/soar/cortex/health")
    async def cortex_health(cortex=Depends(get_cortex_client)):
        """Cortex reachability check."""
        ok = cortex.health_check()
        return {"service": "cortex", "reachable": ok}

    # ------------------------------------------------------------------
    # MISP routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/misp/attributes")
    async def misp_search_attributes(value: Optional[str] = None,
                                     attr_type: Optional[str] = None,
                                     limit: int = 50,
                                     misp=Depends(get_misp_client)):
        """Search MISP attributes by value and/or type."""
        try:
            attrs = misp.search_attributes(value=value, attr_type=attr_type, limit=limit)
            return {"attributes": attrs, "count": len(attrs)}
        except Exception as e:
            logger.error(f"MISP search_attributes error: {e}")
            raise HTTPException(status_code=502, detail=f"MISP error: {e}")

    @app_instance.get("/soar/misp/events")
    async def misp_list_events(limit: int = 20, misp=Depends(get_misp_client)):
        """List recent MISP events."""
        try:
            events = misp.list_events(limit=limit)
            return {"events": events, "count": len(events)}
        except Exception as e:
            logger.error(f"MISP list_events error: {e}")
            raise HTTPException(status_code=502, detail=f"MISP error: {e}")

    @app_instance.get("/soar/misp/events/{event_id}")
    async def misp_get_event(event_id: str, misp=Depends(get_misp_client)):
        """Get a specific MISP event by ID."""
        try:
            return misp.get_event(event_id)
        except Exception as e:
            logger.error(f"MISP get_event error: {e}")
            raise HTTPException(status_code=502, detail=f"MISP error: {e}")

    @app_instance.get("/soar/misp/health")
    async def misp_health(misp=Depends(get_misp_client)):
        """MISP reachability check."""
        ok = misp.health_check()
        return {"service": "misp", "reachable": ok}

    # ------------------------------------------------------------------
    # Shuffle routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/shuffle/workflows")
    async def shuffle_list_workflows(shuffle=Depends(get_shuffle_client)):
        """List all Shuffle workflows."""
        try:
            wfs = shuffle.list_workflows()
            return {"workflows": wfs, "count": len(wfs)}
        except Exception as e:
            logger.error(f"Shuffle list_workflows error: {e}")
            raise HTTPException(status_code=502, detail=f"Shuffle error: {e}")

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}")
    async def shuffle_get_workflow(workflow_id: str, shuffle=Depends(get_shuffle_client)):
        """Get a specific Shuffle workflow."""
        try:
            return shuffle.get_workflow(workflow_id)
        except Exception as e:
            logger.error(f"Shuffle get_workflow error: {e}")
            raise HTTPException(status_code=502, detail=f"Shuffle error: {e}")

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}/executions")
    async def shuffle_get_executions(workflow_id: str, shuffle=Depends(get_shuffle_client)):
        """List executions for a Shuffle workflow."""
        try:
            execs = shuffle.get_workflow_executions(workflow_id)
            return {"workflow_id": workflow_id, "executions": execs, "count": len(execs)}
        except Exception as e:
            logger.error(f"Shuffle get_executions error: {e}")
            raise HTTPException(status_code=502, detail=f"Shuffle error: {e}")

    @app_instance.get("/soar/shuffle/workflows/{workflow_id}/executions/{execution_id}")
    async def shuffle_get_execution(workflow_id: str, execution_id: str,
                                    shuffle=Depends(get_shuffle_client)):
        """Get a specific Shuffle workflow execution."""
        try:
            ex = shuffle.get_execution(workflow_id, execution_id)
            if ex is None:
                raise HTTPException(status_code=404, detail="Execution not found")
            return ex
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Shuffle get_execution error: {e}")
            raise HTTPException(status_code=502, detail=f"Shuffle error: {e}")

    @app_instance.get("/soar/shuffle/health")
    async def shuffle_health(shuffle=Depends(get_shuffle_client)):
        """Shuffle reachability check."""
        ok = shuffle.health_check()
        return {"service": "shuffle", "reachable": ok}

    # ------------------------------------------------------------------
    # Elasticsearch routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/elasticsearch/count")
    async def es_count(index: Optional[str] = None, es=Depends(get_elasticsearch_client)):
        """Return total document count for the soar-alerts index (or custom index)."""
        try:
            return {"index": index or es.index, "count": es.count(index=index)}
        except Exception as e:
            logger.error(f"Elasticsearch count error: {e}")
            raise HTTPException(status_code=502, detail=f"Elasticsearch error: {e}")

    @app_instance.get("/soar/elasticsearch/latest")
    async def es_latest(size: int = 10, index: Optional[str] = None,
                        es=Depends(get_elasticsearch_client)):
        """Return the most recent documents from soar-alerts."""
        try:
            docs = es.get_latest_documents(size=size, index=index)
            return {"documents": docs, "count": len(docs)}
        except Exception as e:
            logger.error(f"Elasticsearch latest error: {e}")
            raise HTTPException(status_code=502, detail=f"Elasticsearch error: {e}")

    @app_instance.get("/soar/elasticsearch/health")
    async def es_health(es=Depends(get_elasticsearch_client)):
        """Elasticsearch cluster health."""
        try:
            health = es.cluster_health()
            return {"service": "elasticsearch", "reachable": True, "status": health.get("status")}
        except Exception as e:
            return {"service": "elasticsearch", "reachable": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Wazuh routes
    # ------------------------------------------------------------------

    @app_instance.get("/soar/wazuh/agents")
    async def wazuh_list_agents(status: Optional[str] = None,
                                wazuh=Depends(get_wazuh_client)):
        """List Wazuh agents, optionally filtered by status."""
        try:
            agents = wazuh.list_agents(status=status)
            return {"agents": agents, "count": len(agents)}
        except Exception as e:
            logger.error(f"Wazuh list_agents error: {e}")
            raise HTTPException(status_code=502, detail=f"Wazuh error: {e}")

    @app_instance.get("/soar/wazuh/agents/{agent_id}")
    async def wazuh_get_agent(agent_id: str, wazuh=Depends(get_wazuh_client)):
        """Get details of a specific Wazuh agent."""
        try:
            return wazuh.get_agent(agent_id)
        except Exception as e:
            logger.error(f"Wazuh get_agent error: {e}")
            raise HTTPException(status_code=502, detail=f"Wazuh error: {e}")

    @app_instance.get("/soar/wazuh/agents/{agent_id}/vulnerabilities")
    async def wazuh_agent_vulns(agent_id: str, limit: int = 50,
                                wazuh=Depends(get_wazuh_client)):
        """Return CVEs detected on a Wazuh agent."""
        try:
            vulns = wazuh.list_agent_vulnerabilities(agent_id, limit=limit)
            return {"agent_id": agent_id, "vulnerabilities": vulns, "count": len(vulns)}
        except Exception as e:
            logger.error(f"Wazuh vulnerabilities error: {e}")
            raise HTTPException(status_code=502, detail=f"Wazuh error: {e}")

    @app_instance.get("/soar/wazuh/manager")
    async def wazuh_manager_info(wazuh=Depends(get_wazuh_client)):
        """Return Wazuh manager info (version, type)."""
        try:
            return wazuh.get_manager_info()
        except Exception as e:
            logger.error(f"Wazuh manager info error: {e}")
            raise HTTPException(status_code=502, detail=f"Wazuh error: {e}")

    @app_instance.get("/soar/wazuh/health")
    async def wazuh_health(wazuh=Depends(get_wazuh_client)):
        """Wazuh reachability check."""
        ok = wazuh.health_check()
        return {"service": "wazuh", "reachable": ok}

    @app_instance.get("/soar/status")
    async def soar_status():
        """Aggregated health check across all SOAR integration clients."""
        results: Dict[str, Any] = {"timestamp": datetime.now(timezone.utc).isoformat()}
        for name, client in (
                ("thehive", app_instance.state.thehive_client),
                ("cortex", app_instance.state.cortex_client),
                ("misp", app_instance.state.misp_client),
                ("shuffle", app_instance.state.shuffle_client),
                ("elasticsearch", app_instance.state.elasticsearch_client),
                ("wazuh", app_instance.state.wazuh_client),
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

    @app_instance.websocket("/ws/logs")
    async def websocket_logs(websocket: WebSocket, connection_manager=Depends(get_websocket_manager)):
        """WebSocket endpoint for log streaming."""
        if connection_manager is None:
            await websocket.close(code=1011, reason="WebSocket manager not available")
            return

        await connection_manager.connect(websocket)

        try:
            # Get log reader from app state if available
            log_reader = app_instance.state.log_reader
            if log_reader:
                # Stream real logs
                async for log_entry in log_reader.stream_logs():
                    await websocket.send_json(log_entry)
            else:
                # Fallback to simulated logs if log reader not available
                while True:
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": "INFO",
                        "message": "Log reader not available - simulated log entry"
                    }
                    await websocket.send_json(log_entry)
                    await asyncio.sleep(1)
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
            logger.info("WebSocket client disconnected")


def _get_fallback_html() -> str:
    """Get fallback HTML when API docs are not available."""
    return """<html><head><title>SOAR Lab Management API</title></head><body><h1>SOAR Lab Management API</h1><p>API Documentation: <a href="/docs">/docs</a></p><p>Health Check: <a href="/health">/health</a></p></body></html>"""
