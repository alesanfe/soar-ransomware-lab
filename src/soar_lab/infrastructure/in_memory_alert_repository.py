"""In-memory AlertRepository for unit tests.

This adapter provides a volatile implementation of AlertRepository
that requires no database, no disk, and no I/O operations.
Perfect for fast, isolated unit tests.
"""

from typing import List, Dict, Any, Optional


class InMemoryAlertRepository:
    """In-memory implementation of AlertRepository for testing."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def store(self, alert: Dict[str, Any]) -> str:
        """Store an alert in memory."""
        alert_id = alert['alert_id']
        self._store[alert_id] = alert.copy()
        return alert_id

    def find_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Find an alert by ID."""
        return self._store.get(alert_id)

    def find_by_type(self, alert_type: str) -> List[Dict[str, Any]]:
        """Find all alerts of a specific type."""
        return [a for a in self._store.values() if a.get('alert_type') == alert_type]

    def find_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Find all alerts with a specific severity."""
        return [a for a in self._store.values() if a.get('severity') == severity]

    def update_status(self, alert_id: str, status: str) -> bool:
        """Update the status of an alert."""
        if alert_id in self._store:
            self._store[alert_id]['status'] = status
            return True
        return False

    def clear(self) -> None:
        """Clear all alerts (useful for test isolation)."""
        self._store.clear()
