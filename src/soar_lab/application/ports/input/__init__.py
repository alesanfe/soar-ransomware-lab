"""Input ports - use case interfaces for hexagonal architecture.

These protocols define the contracts that input adapters (HTTP routes,
CLI commands, event consumers) use to invoke application use cases.
Input adapters depend on these abstract interfaces, not on concrete
use case implementations, enabling substitution and testing.
"""

from typing import Any, Protocol


class AnalyticsUseCase(Protocol):
    """Input port for analytics and KPI computation."""

    def get_comprehensive_kpis(self, log_file_path: str | None = None) -> dict[str, Any]:
        """Return comprehensive KPI metrics."""
        ...


class BackupUseCase(Protocol):
    """Input port for backup operations."""

    def create(self) -> dict[str, Any]:
        """Create a backup and return result metadata."""
        ...

    def list_backups(self) -> dict[str, Any]:
        """List available backups."""
        ...

    def restore(self, backup_name: str) -> dict[str, Any]:
        """Restore a backup by name."""
        ...


class AuthServiceInterface(Protocol):
    """Input port for authentication operations."""

    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify user credentials."""
        ...

    def create_jwt_token(self, username: str) -> str:
        """Create a JWT token for a user."""
        ...


class TestExecutionUseCase(Protocol):
    """Input port for test execution."""

    async def run_tests(self, category: str = "unit") -> dict[str, Any]:
        """Run tests for a category and return results."""
        ...


class NodeTimingUseCase(Protocol):
    """Input port for node timing extraction."""

    def process_execution(self, execution_id: str, alert_id: str = "") -> dict[str, Any] | None:
        """Process a single execution and return timing data."""
        ...


__all__ = [
    "AnalyticsUseCase",
    "AuthServiceInterface",
    "BackupUseCase",
    "NodeTimingUseCase",
    "TestExecutionUseCase",
]
