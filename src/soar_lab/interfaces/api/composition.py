"""Composition Root - Dependency injection configuration.

This module is the composition root where all dependencies are wired together.
It follows the Composition Root pattern from hexagonal architecture.
"""

from fastapi import FastAPI

from scripts.test_service import TestService  # pylint: disable=import-error,no-name-in-module
from soar_lab.application.use_cases.analytics_service import AnalyticsService
from soar_lab.application.use_cases.auth_service import AuthService, set_default_factories
from soar_lab.application.use_cases.backup_service import BackupService
from soar_lab.common.constants import (
    SERVICE_CORTEX,
    SERVICE_ELASTICSEARCH,
    SERVICE_MISP,
    SERVICE_SHUFFLE,
    SERVICE_THEHIVE,
)
from soar_lab.config.logging import setup_logging
from soar_lab.config.settings import create_settings
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.infrastructure.clients import create_docker_client, create_redis_client
from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
from soar_lab.infrastructure.file_log_reader import FileLogReader
from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
from soar_lab.infrastructure.http_client import AioHTTPClient
from soar_lab.infrastructure.integrations.cortex.client import CortexClient
from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient
from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider
from soar_lab.infrastructure.kpi_formatter import CSVKPIFormatter
from soar_lab.infrastructure.log_parser import ExecutionLogParser
from soar_lab.infrastructure.monitoring.health_check_adapter import (
    HTTPHealthCheckAdapter,
)
from soar_lab.infrastructure.monitoring.health_service import HealthService
from soar_lab.infrastructure.monitoring.system_metrics_driver import SystemMetricsDriver
from soar_lab.infrastructure.path_service import PathService
from soar_lab.infrastructure.persistence.sqlite_alert_repository import (
    SqliteAlertRepository,
)
from soar_lab.infrastructure.pytest_output_parser import PytestOutputParser
from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner
from soar_lab.infrastructure.subprocess_runner import SubprocessRunner
from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver
from soar_lab.infrastructure.websocket_manager import ConnectionManager


class CompositionRoot:
    """Composition root for dependency injection."""

    def __init__(self) -> None:
        """Initialize the composition root with all dependencies."""
        settings = create_settings()
        self.config_provider = InfrastructureConfigProvider(settings)

        from pathlib import Path

        _log_dir_str = self.config_provider.get("log_dir", "")
        setup_logging(
            log_level=self.config_provider.get("log_level", "INFO"),
            log_format=self.config_provider.get("log_format", "text"),
            log_dir=Path(_log_dir_str) if _log_dir_str else None,
        )

        base_dir_str = self.config_provider.get("base_dir")
        if not base_dir_str:
            raise ValueError("base_dir must be provided in config_provider")
        base_dir = Path(base_dir_str)
        self.path_service = PathService(base_dir=base_dir, config_provider=self.config_provider)

        # Ensure required directories exist (moved from Settings to PathService)
        self.path_service.ensure_directories()

        self.storage = FilesystemStorage(config_provider=self.config_provider)
        self.alert_repository = SqliteAlertRepository(
            config_provider=self.config_provider, path_service=self.path_service
        )
        self.system_metrics = SystemMetricsDriver()
        self.http_client = AioHTTPClient()
        self.health_checker = HTTPHealthCheckAdapter(
            http_client=self.http_client,
            verify_ssl_config=self.config_provider.get(
                "health_check_ssl_config", {"misp": False, "grafana": False}
            ),
        )
        self.log_parser = ExecutionLogParser()
        self.kpi_formatter = CSVKPIFormatter()
        self.log_reader = FileLogReader(self.path_service)
        self.pytest_parser = PytestOutputParser()
        self.test_runner = PytestTestRunner(repo_root=base_dir, path_service=self.path_service)
        self.backup_driver = TarBackupDriver()
        self.subprocess_runner = SubprocessRunner()
        self.websocket_manager = ConnectionManager()
        self.statistical_calculator = StatisticalCalculator()
        self.kpi_analyzer = KPIAnalyzer(self.statistical_calculator)
        self.token_provider = JWTTokenProvider()
        # Register default factories so AuthService() can be called without
        # explicit providers (used by tests and the eager-init path).
        from soar_lab.infrastructure.auth_defaults import (
            create_default_config_provider_wrapper,
            create_default_token_provider_wrapper,
        )

        set_default_factories(
            config_factory=create_default_config_provider_wrapper,
            token_factory=create_default_token_provider_wrapper,
        )
        self.auth_service = AuthService(self.config_provider, self.token_provider)

        # Create Docker and Redis clients
        self.docker_client = create_docker_client(self.config_provider)
        self.redis_client = create_redis_client(self.config_provider)

        # Create integration clients
        self.cortex_client = CortexClient(
            base_url=self.config_provider.get("cortex_url"),
            api_key=self.config_provider.get("cortex_api_key"),
            config_provider=self.config_provider,
        )
        self.shuffle_client = ShuffleClient(
            base_url=self.config_provider.get("shuffle_url"),
            api_key=self.config_provider.get("shuffle_api_key"),
            config_provider=self.config_provider,
        )
        self.thehive_client = TheHiveClient(
            base_url=self.config_provider.get("thehive_url"),
            api_key=self.config_provider.get("thehive_api_key"),
            config_provider=self.config_provider,
        )
        self.misp_client = MISPClient(
            base_url=self.config_provider.get("misp_url"),
            api_key=self.config_provider.get("misp_api_key"),
            config_provider=self.config_provider,
        )
        self.elasticsearch_client = ElasticsearchClient(
            base_url=self.config_provider.get("elasticsearch_url"),
            config_provider=self.config_provider,
        )

        # Create services
        self.analytics_service = AnalyticsService(
            data_repository=self.alert_repository,
            system_metrics=self.system_metrics,
            file_system=self.storage,
            log_reader=self.log_reader,
            log_parser=self.log_parser,
            kpi_formatter=self.kpi_formatter,
            statistical_calculator=self.statistical_calculator,
            kpi_analyzer=self.kpi_analyzer,
        )
        self.backup_service = BackupService(driver=self.backup_driver, storage=self.storage)
        self.test_service = TestService(
            runner=self.test_runner,
            parser=self.pytest_parser,
        )
        self.health_service = HealthService(
            health_checker=self.health_checker,
            system_metrics=self.system_metrics,
            soar_clients={
                SERVICE_THEHIVE: self.thehive_client,
                SERVICE_CORTEX: self.cortex_client,
                SERVICE_MISP: self.misp_client,
                SERVICE_SHUFFLE: self.shuffle_client,
                SERVICE_ELASTICSEARCH: self.elasticsearch_client,
            },
        )

    def create_fastapi_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        from soar_lab.interfaces.api.main import create_app

        return create_app(
            config_provider=self.config_provider,
            path_service=self.path_service,
            storage=self.storage,
            alert_repository=self.alert_repository,
            system_metrics=self.system_metrics,
            health_checker=self.health_checker,
            log_reader=self.log_reader,
            pytest_parser=self.pytest_parser,
            test_runner=self.test_runner,
            backup_driver=self.backup_driver,
            analytics_service=self.analytics_service,
            backup_service=self.backup_service,
            test_service=self.test_service,
            health_service=self.health_service,
            docker_client=self.docker_client,
            redis_client=self.redis_client,
            cortex_client=self.cortex_client,
            misp_client=self.misp_client,
            shuffle_client=self.shuffle_client,
            thehive_client=self.thehive_client,
            elasticsearch_client=self.elasticsearch_client,
            websocket_manager=self.websocket_manager,
            auth_service=self.auth_service,
        )


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app with all dependencies."""
    composition = CompositionRoot()
    return composition.create_fastapi_app()
