"""FastAPI application package with default app instance and composition root."""

import os
from pathlib import Path

from .main import create_app

# Allow tests to disable eager instantiation
_SKIP_EAGER_INIT = os.getenv("SOAR_SKIP_EAGER_INIT", "").lower() in ("1", "true", "yes")

if not _SKIP_EAGER_INIT:
    # Create a default app instance for uvicorn with working dependencies
    from scripts.test_service import TestService  # pylint: disable=import-error,no-name-in-module
    from soar_lab.application.use_cases.analytics_service import AnalyticsService
    from soar_lab.application.use_cases.auth_service import AuthService
    from soar_lab.application.use_cases.backup_service import BackupService
    from soar_lab.config.settings import Settings
    from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
    from soar_lab.domain.statistical_calculator import StatisticalCalculator
    from soar_lab.infrastructure.file_log_reader import FileLogReader
    from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
    from soar_lab.infrastructure.http_client import AioHTTPClient
    from soar_lab.infrastructure.in_memory_alert_repository import (
        InMemoryAlertRepository,
    )
    from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider
    from soar_lab.infrastructure.kpi_formatter import CSVKPIFormatter
    from soar_lab.infrastructure.log_parser import ExecutionLogParser
    from soar_lab.infrastructure.monitoring.health_check_adapter import (
        HTTPHealthCheckAdapter,
    )
    from soar_lab.infrastructure.monitoring.health_service import HealthService
    from soar_lab.infrastructure.monitoring.system_metrics_driver import (
        SystemMetricsDriver,
    )
    from soar_lab.infrastructure.path_service import PathService
    from soar_lab.infrastructure.pytest_output_parser import PytestOutputParser
    from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner
    from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver
    from soar_lab.infrastructure.websocket_manager import ConnectionManager

    settings = Settings()
    token_provider = JWTTokenProvider()
    # Register default factories for AuthService()
    from soar_lab.application.use_cases.auth_service import set_default_factories
    from soar_lab.infrastructure.auth_defaults import (
        create_default_config_provider_wrapper,
        create_default_token_provider_wrapper,
    )

    set_default_factories(
        config_factory=create_default_config_provider_wrapper,
        token_factory=create_default_token_provider_wrapper,
    )
    auth_service = AuthService(settings, token_provider)

    # Real services
    system_metrics = SystemMetricsDriver()
    http_client = AioHTTPClient(default_timeout=5, default_verify_ssl=False)
    health_checker = HTTPHealthCheckAdapter(
        http_client, verify_ssl_config={"thehive": False, "cortex": False, "shuffle-backend": False}
    )
    health_service = HealthService(health_checker, system_metrics)

    # Path and storage
    base_dir = Path(settings.get("base_dir", "/app"))
    path_service = PathService(base_dir, config_provider=settings)
    storage = FilesystemStorage(str(base_dir), config_provider=settings)

    # Alert repository
    alert_repository = InMemoryAlertRepository()

    # Test service
    test_runner = PytestTestRunner(base_dir, path_service)
    test_parser = PytestOutputParser()
    test_service = TestService(test_runner, test_parser)

    # Analytics service
    log_reader = FileLogReader(path_service)
    log_parser = ExecutionLogParser()
    kpi_formatter = CSVKPIFormatter()
    statistical_calculator = StatisticalCalculator()
    kpi_analyzer = KPIAnalyzer(statistical_calculator)
    analytics_service = AnalyticsService(
        data_repository=alert_repository,
        system_metrics=system_metrics,
        file_system=storage,
        log_reader=log_reader,
        log_parser=log_parser,
        kpi_formatter=kpi_formatter,
        statistical_calculator=statistical_calculator,
        kpi_analyzer=kpi_analyzer,
    )

    # Backup service
    backup_driver = TarBackupDriver()
    backup_service = BackupService(driver=backup_driver, storage=storage)

    # WebSocket manager
    websocket_manager = ConnectionManager()

    app = create_app(
        config_provider=settings,
        auth_service=auth_service,
        system_metrics=system_metrics,
        health_checker=health_checker,
        health_service=health_service,
        path_service=path_service,
        storage=storage,
        alert_repository=alert_repository,
        test_runner=test_runner,
        test_service=test_service,
        analytics_service=analytics_service,
        backup_service=backup_service,
        websocket_manager=websocket_manager,
        log_reader=log_reader,
    )
else:
    app = None

__all__ = ["app", "create_app"]
