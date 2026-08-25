"""In-memory AlertRepository for unit tests.

This adapter provides a volatile implementation of AlertRepository that
requires no database, no disk, and no I/O operations. Perfect for fast,
isolated unit tests.
"""

from typing import Any

__all__ = ["InMemoryAlertRepository"]


class InMemoryAlertRepository:
    """In-memory implementation of AlertRepository for testing."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def store(self, alert: dict[str, Any]) -> str:
        """Store an alert in memory."""
        alert_id = alert["alert_id"]
        self._store[alert_id] = alert.copy()
        return alert_id

    def find_by_id(self, alert_id: str) -> dict[str, Any] | None:
        """Find an alert by ID."""
        return self._store.get(alert_id)

    def find_by_type(self, alert_type: str) -> list[dict[str, Any]]:
        """Find all alerts of a specific type."""
        return [a for a in self._store.values() if a.get("alert_type") == alert_type]

    def find_by_severity(self, severity: str) -> list[dict[str, Any]]:
        """Find all alerts with a specific severity."""
        return [a for a in self._store.values() if a.get("severity") == severity]

    def update_status(self, alert_id: str, status: str) -> bool:
        """Update the status of an alert."""
        if alert_id in self._store:
            self._store[alert_id]["status"] = status
            return True
        return False

    def clear(self) -> None:
        """Clear all alerts (useful for test isolation)."""
        self._store.clear()

    def get_test_results(self, hours: int = 24) -> list[dict[str, Any]]:
        """Return test results (empty when none stored in memory)."""
        return []

    def get_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        """Return all alerts within the last N hours."""
        return list(self._store.values())

    def count_alerts(self) -> int:
        """Return total number of alerts."""
        return len(self._store)

    def count_alerts_by_status(self, status: str) -> int:
        """Return count of alerts with a given status."""
        return sum(1 for a in self._store.values() if a.get("status") == status)

    def count_cases(self) -> int:
        """Return total number of cases (0 in memory-only repo)."""
        return 0

    def count_cases_by_status(self, status: str) -> int:
        """Return count of cases with a given status (0 in memory-only.

        repo).
        """
        return 0

    def count_backups_by_status(self, status: str) -> int:
        """Return count of backups with a given status (0 in memory-only.

        repo).
        """
        return 0

    def get_average_test_coverage(self, hours: int = 24) -> float:
        """Return average test coverage (0.0 when no data available)."""
        return 0.0
