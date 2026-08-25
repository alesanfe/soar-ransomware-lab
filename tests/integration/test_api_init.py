#!/usr/bin/env python3
"""
Integration tests for soar_lab.api.__init__
Tests real instantiation without mocks - verifies production behavior
"""

import os
from pathlib import Path

import pytest


@pytest.mark.requires_external
class TestAPIInitReal:
    """Test real API initialization with actual dependencies."""

    def test_eager_instantiation_with_real_dependencies(self):
        """Test that app instantiates eagerly with real dependencies when
        SOAR_SKIP_EAGER_INIT is not set."""
        # This test must run in a subprocess to avoid the module being already imported
        # with SOAR_SKIP_EAGER_INIT=1 from conftest.py
        import subprocess
        import sys

        test_code = """
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / 'src'))

# Ensure BASE_DIR is set
os.environ['BASE_DIR'] = str(Path.cwd())

# Ensure SOAR_SKIP_EAGER_INIT is NOT set
os.environ.pop('SOAR_SKIP_EAGER_INIT', None)

# Patch StaticFiles to allow non-existent directories (for testing)
from fastapi import staticfiles
original_staticfiles = staticfiles.StaticFiles

class MockStaticFiles:
    def __init__(self, directory, name=None):
        self.directory = directory
        self.name = name

staticfiles.StaticFiles = MockStaticFiles

# Import the module - this should trigger eager instantiation
from soar_lab.api import app

# Verify app is instantiated
assert app is not None, "app should be instantiated when SOAR_SKIP_EAGER_INIT is not set"

# Verify app has expected attributes
assert hasattr(app, 'routes'), "app should have routes"
assert hasattr(app, 'state'), "app should have state"

# Verify at least some routes are registered
routes = [route.path for route in app.routes]
assert len(routes) > 0, "app should have routes registered"

print("SUCCESS: Eager instantiation works with real dependencies")
"""

        env = os.environ.copy()
        env.pop("SOAR_SKIP_EAGER_INIT", None)

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

        assert (
            result.returncode == 0
        ), f"Eager instantiation failed: {result.stderr}\n{result.stdout}"
        assert "SUCCESS" in result.stdout, "Test did not complete successfully"

    def test_skip_eager_instantiation_when_flag_set(self):
        """Test that app is None when SOAR_SKIP_EAGER_INIT is set."""
        import subprocess
        import sys

        test_code = """
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / 'src'))

# Ensure BASE_DIR is set
os.environ['BASE_DIR'] = str(Path.cwd())

# Set SOAR_SKIP_EAGER_INIT
os.environ['SOAR_SKIP_EAGER_INIT'] = '1'

# Import the module - this should skip eager instantiation
from soar_lab.api import app

# Verify app is None
assert app is None, "app should be None when SOAR_SKIP_EAGER_INIT is set"

print("SUCCESS: Skip eager instantiation works")
"""

        env = os.environ.copy()
        env["SOAR_SKIP_EAGER_INIT"] = "1"

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

        assert (
            result.returncode == 0
        ), f"Skip eager instantiation failed: {result.stderr}\n{result.stdout}"
        assert "SUCCESS" in result.stdout, "Test did not complete successfully"

    def test_create_app_factory_works(self):
        """Test that create_app factory function works with real
        dependencies."""
        import subprocess
        import sys

        test_code = """
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / 'src'))

# Ensure BASE_DIR is set
os.environ['BASE_DIR'] = str(Path.cwd())

# Patch StaticFiles to allow non-existent directories (for testing)
from fastapi import staticfiles
original_staticfiles = staticfiles.StaticFiles

class MockStaticFiles:
    def __init__(self, directory, name=None):
        self.directory = directory
        self.name = name

staticfiles.StaticFiles = MockStaticFiles

# Import factory and dependencies
from soar_lab.interfaces.api.main import create_app
from soar_lab.config.settings import Settings
from soar_lab.application.use_cases.auth_service import AuthService
from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider
from soar_lab.infrastructure.monitoring.system_metrics_driver import SystemMetricsDriver
from soar_lab.infrastructure.http_client import AioHTTPClient
from soar_lab.infrastructure.monitoring.health_check_adapter import HTTPHealthCheckAdapter
from soar_lab.infrastructure.monitoring.health_service import HealthService
from soar_lab.infrastructure.path_service import PathService
from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
from soar_lab.infrastructure.in_memory_alert_repository import InMemoryAlertRepository
from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner
from soar_lab.infrastructure.pytest_output_parser import PytestOutputParser
from scripts.test_service import TestService

# Create real dependencies
settings = Settings()
token_provider = JWTTokenProvider()
auth_service = AuthService(settings, token_provider)

system_metrics = SystemMetricsDriver()
http_client = AioHTTPClient(default_timeout=5, default_verify_ssl=False)
health_checker = HTTPHealthCheckAdapter(
    http_client,
    verify_ssl_config={'thehive': False, 'cortex': False, 'shuffle-backend': False},
)
health_service = HealthService(health_checker, system_metrics)

base_dir = Path(settings.get('base_dir', '/app'))
path_service = PathService(base_dir)
storage = FilesystemStorage(str(base_dir))

alert_repository = InMemoryAlertRepository()

test_runner = PytestTestRunner(base_dir, path_service)
test_parser = PytestOutputParser()
test_service = TestService(test_runner, test_parser)

# Create app using factory
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

# Verify app was created
assert app is not None, "create_app should return an app instance"
assert hasattr(app, 'routes'), "app should have routes"

print("SUCCESS: create_app factory works with real dependencies")
"""

        env = os.environ.copy()
        env.pop("SOAR_SKIP_EAGER_INIT", None)

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )

        assert (
            result.returncode == 0
        ), f"create_app factory failed: {result.stderr}\n{result.stdout}"
        assert "SUCCESS" in result.stdout, "Test did not complete successfully"
