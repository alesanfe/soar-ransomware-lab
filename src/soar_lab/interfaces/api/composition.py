"""Composition Root - Dependency injection configuration.

This module is the composition root where all dependencies are wired together.
It follows the Composition Root pattern from hexagonal architecture.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from soar_lab.application.use_cases.analytics_service import AnalyticsService
from soar_lab.application.use_cases.auth_service import AuthService, set_default_factories
from soar_lab.application.use_cases.backup_service import BackupService
from soar_lab.application.use_cases.test_service import TestService
from soar_lab.config.logging import get_logger, setup_logging
from soar_lab.config.settings import create_settings
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from soar_lab.infrastructure.adapter_registry import (
    INTEGRATION_ADAPTERS,
    build_integration_clients,
)
from soar_lab.infrastructure.auth_defaults import (
    create_default_config_provider_wrapper,
    create_default_token_provider_wrapper,
)
from soar_lab.infrastructure.clients import create_docker_client, create_redis_client
from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
from soar_lab.infrastructure.file_log_reader import FileLogReader
from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
from soar_lab.infrastructure.http_client import AioHTTPClient
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
from soar_lab.interfaces.api.main import create_app as create_injected_app
from soar_lab.security.tls_config import verify_tls

logger = logging.getLogger(__name__)


class CompositionRoot:
    """Composition root for dependency injection."""

    def __init__(self) -> None:
        """Initialize the composition root with all dependencies."""
        settings = create_settings()
        # BL-CFG: validate() was dead code — invoke it at startup so
        # missing required config surfaces as a logged warning at boot
        # instead of a confusing failure on first use. Warn-only (the lab
        # can legitimately run without some integrations).
        try:
            if not settings.validate():
                logger.warning(
                    "Required configuration incomplete — some integrations "
                    "will be unavailable (see missing keys above)"
                )
        except Exception:
            logger.warning("Configuration validation failed to run", exc_info=True)
        self.config_provider = InfrastructureConfigProvider(settings)

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
        # TLS verification defaults ON per service; an env override must be
        # explicit — no insecure default hidden in the composition root.
        # Resolution is centralized in security.tls_config (BL-SEC-003).

        self.health_checker = HTTPHealthCheckAdapter(
            http_client=self.http_client,
            verify_ssl_config=self.config_provider.get(
                "health_check_ssl_config",
                {
                    "misp": verify_tls("misp"),
                    "grafana": verify_tls("grafana"),
                    "thehive": verify_tls("thehive"),
                    "cortex": verify_tls("cortex"),
                    "shuffle-backend": verify_tls("shuffle-backend"),
                    "elasticsearch": verify_tls("elasticsearch"),
                },
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

        set_default_factories(
            config_factory=create_default_config_provider_wrapper,
            token_factory=create_default_token_provider_wrapper,
        )
        self.auth_service = AuthService(self.config_provider, self.token_provider)

        # Create Docker and Redis clients
        self.docker_client = create_docker_client(self.config_provider)
        self.redis_client = create_redis_client(self.config_provider)

        # Create integration clients from the declarative registry (A2) —
        # a new adapter only needs an AdapterSpec row, not edits here.
        self.cortex_client: Any = None
        self.misp_client: Any = None
        self.shuffle_client: Any = None
        self.thehive_client: Any = None
        self.elasticsearch_client: Any = None
        self.integration_clients = build_integration_clients(self.config_provider)
        for service_name, client in self.integration_clients.items():
            setattr(self, f"{service_name}_client", client)

        self._warn_unconfigured_integrations()

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
            soar_clients=self.integration_clients,
        )

    def _warn_unconfigured_integrations(self) -> None:
        """Startup config validation — warn which integrations lack config.

        Missing URLs/keys currently surface only when a call fails at
        runtime. Surfacing them at startup turns a latent misconfig into
        an actionable log line. Non-blocking by design: a lab deployment
        may legitimately run a subset of integrations.
        """
        log = get_logger(__name__)
        missing: list[str] = []
        for spec in INTEGRATION_ADAPTERS:
            if not self.config_provider.get(spec.url_key):
                missing.append(f"{spec.name}({spec.url_key})")
                continue
            if spec.api_key_key and not self.config_provider.get(spec.api_key_key):
                missing.append(f"{spec.name}({spec.api_key_key})")
        if missing:
            log.warning(f"Integrations without config at startup: {', '.join(missing)}")

    def create_fastapi_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        return create_injected_app(
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
            admission_service=None,  # built at startup by _register_worker_lifecycle
        )


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app with all dependencies."""
    return CompositionRoot().create_fastapi_app()
