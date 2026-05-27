from .main import create_app
from pathlib import Path
import os

# Allow tests to disable eager instantiation
_SKIP_EAGER_INIT = os.getenv('SOAR_SKIP_EAGER_INIT', '').lower() in ('1', 'true', 'yes')

if not _SKIP_EAGER_INIT:
    # Create a default app instance for uvicorn with working dependencies
    from soar_lab.config.settings import Settings
    from soar_lab.services.auth_service import AuthService
    from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider
    from soar_lab.infrastructure.system_metrics_driver import SystemMetricsDriver
    from soar_lab.infrastructure.http_client import AioHTTPClient
    from soar_lab.infrastructure.health_check_adapter import HTTPHealthCheckAdapter
    from soar_lab.services.health_service import HealthService
    from soar_lab.infrastructure.path_service import PathService
    from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
    from soar_lab.infrastructure.in_memory_alert_repository import InMemoryAlertRepository
    from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner
    from soar_lab.infrastructure.pytest_output_parser import PytestOutputParser
    from soar_lab.services.test_service import TestService

    settings = Settings()
    token_provider = JWTTokenProvider()
    auth_service = AuthService(settings, token_provider)

    # Real services
    system_metrics = SystemMetricsDriver()
    http_client = AioHTTPClient(default_timeout=5, default_verify_ssl=False)
    health_checker = HTTPHealthCheckAdapter(http_client, verify_ssl_config={'thehive': False, 'cortex': False, 'shuffle-backend': False})
    health_service = HealthService(health_checker, system_metrics)

    # Path and storage
    base_dir = Path(settings.get('base_dir', '/app'))
    path_service = PathService(base_dir)
    storage = FilesystemStorage(str(base_dir))

    # Alert repository
    alert_repository = InMemoryAlertRepository()

    # Test service
    test_runner = PytestTestRunner(base_dir, path_service)
    test_parser = PytestOutputParser()
    test_service = TestService(test_runner, test_parser)

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
        test_service=test_service
    )
else:
    app = None

__all__ = ['app', 'create_app']
