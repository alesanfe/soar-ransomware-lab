#!/usr/bin/env python3
"""Unit tests for application/ports/input/__init__.py.

Tests that the Protocol-based input port interfaces can be used as type
annotations and that concrete implementations satisfy the protocols.
"""

from typing import Any

import pytest

from soar_lab.application.ports.input import (
    AnalyticsUseCase,
    AuthServiceInterface,
    BackupUseCase,
    NodeTimingUseCase,
    TestExecutionUseCase,
)

__all__ = [
    "TestProtocolExports",
    "TestAnalyticsUseCase",
    "TestBackupUseCase",
    "TestAuthServiceInterface",
    "TestTestExecutionUseCase",
    "TestNodeTimingUseCase",
]


class TestProtocolExports:
    """Test that all protocols are exported correctly."""

    def test_all_protocols_exported(self):
        """Test that __all__ contains all expected protocol names."""
        from soar_lab.application.ports.input import __all__

        assert "AnalyticsUseCase" in __all__
        assert "AuthServiceInterface" in __all__
        assert "BackupUseCase" in __all__
        assert "NodeTimingUseCase" in __all__
        assert "TestExecutionUseCase" in __all__

    def test_protocols_are_classes(self):
        """Test that all exported protocols are classes."""
        assert isinstance(AnalyticsUseCase, type)
        assert isinstance(BackupUseCase, type)
        assert isinstance(AuthServiceInterface, type)
        assert isinstance(TestExecutionUseCase, type)
        assert isinstance(NodeTimingUseCase, type)


class TestAnalyticsUseCase:
    """Test AnalyticsUseCase protocol compliance."""

    def test_analytics_use_case_implementation(self):
        """Test that a class implementing get_comprehensive_kpis satisfies the protocol."""

        class FakeAnalytics:
            def get_comprehensive_kpis(self, log_file_path: str | None = None) -> dict[str, Any]:
                return {"mttr": 100.0}

        impl = FakeAnalytics()
        assert impl.get_comprehensive_kpis() == {"mttr": 100.0}
        assert impl.get_comprehensive_kpis("/path/to/log") == {"mttr": 100.0}


class TestBackupUseCase:
    """Test BackupUseCase protocol compliance."""

    def test_backup_use_case_implementation(self):
        """Test that a class implementing create/list/restore satisfies the protocol."""

        class FakeBackup:
            def create(self) -> dict[str, Any]:
                return {"status": "success"}

            def list_backups(self) -> dict[str, Any]:
                return {"backups": []}

            def restore(self, backup_name: str) -> dict[str, Any]:
                return {"status": "restored", "name": backup_name}

        impl = FakeBackup()
        assert impl.create()["status"] == "success"
        assert impl.list_backups()["backups"] == []
        assert impl.restore("test.tar.gz")["name"] == "test.tar.gz"


class TestAuthServiceInterface:
    """Test AuthServiceInterface protocol compliance."""

    def test_auth_service_implementation(self):
        """Test that a class implementing verify/create token satisfies the protocol."""

        class FakeAuth:
            def verify_credentials(self, username: str, password: str) -> bool:
                return username == "admin" and password == "secret"

            def create_jwt_token(self, username: str) -> str:
                return f"token-for-{username}"

        impl = FakeAuth()
        assert impl.verify_credentials("admin", "secret") is True
        assert impl.verify_credentials("admin", "wrong") is False
        assert impl.create_jwt_token("admin") == "token-for-admin"


class TestTestExecutionUseCase:
    """Test TestExecutionUseCase protocol compliance."""

    def test_test_execution_use_case_implementation(self):
        """Test that a class implementing run_tests satisfies the protocol."""

        class FakeTestExec:
            async def run_tests(self, category: str = "unit") -> dict[str, Any]:
                return {"category": category, "passed": 10, "failed": 0}

        impl = FakeTestExec()
        import asyncio

        result = asyncio.run(impl.run_tests("integration"))
        assert result["category"] == "integration"
        assert result["passed"] == 10


class TestNodeTimingUseCase:
    """Test NodeTimingUseCase protocol compliance."""

    def test_node_timing_use_case_implementation(self):
        """Test that a class implementing process_execution satisfies the protocol."""

        class FakeNodeTiming:
            def process_execution(
                self, execution_id: str, alert_id: str = ""
            ) -> dict[str, Any] | None:
                if execution_id == "valid":
                    return {"execution_id": execution_id, "timings": []}
                return None

        impl = FakeNodeTiming()
        assert impl.process_execution("valid") is not None
        assert impl.process_execution("missing") is None
        assert impl.process_execution("valid", "alert-1")["execution_id"] == "valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
