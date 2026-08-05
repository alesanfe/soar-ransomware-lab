"""Domain ports - Repository interfaces.

These protocols define the contracts for data persistence.
The domain depends only on these abstract interfaces, not on concrete
implementations like SQLite or filesystem.
"""

from typing import Protocol, List, Dict, Any, Optional


class AlertRepository(Protocol):
    """Repository for storing and retrieving alerts."""

    def store(self, alert: Dict[str, Any]) -> str:
        """Store an alert and return its ID."""
        ...

    def find_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Find a single alert by ID."""
        ...

    def find_by_type(self, alert_type: str) -> List[Dict[str, Any]]:
        """Find all alerts of a specific type."""
        ...

    def find_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Find all alerts with a specific severity."""
        ...

    def update_status(self, alert_id: str, status: str) -> bool:
        """Update the status of an alert."""
        ...


class IocRepository(Protocol):
    """Repository for storing and retrieving IOCs (Indicators of Compromise)."""

    def store(self, ioc: Dict[str, Any]) -> str:
        """Store an IOC and return its value."""
        ...

    def find_by_type(self, ioc_type: str) -> List[Dict[str, Any]]:
        """Find all IOCs of a specific type."""
        ...


class MetricRepository(Protocol):
    """Repository for storing and retrieving metrics."""

    def store(
        self,
        name: str,
        value: float,
        unit: str = None,
        source: str = None,
        tags: Dict[str, str] = None
    ) -> None:
        """Store a metric."""
        ...

    def find(self, name: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Find metrics by name and time window."""
        ...


class CaseRepository(Protocol):
    """Repository for storing and retrieving cases."""

    def store(self, case: Dict[str, Any]) -> str:
        """Store a case and return its ID."""
        ...

    def find_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Find a single case by ID."""
        ...


class BackupRepository(Protocol):
    """Repository for backup metadata."""

    def store(self, backup: Dict[str, Any]) -> str:
        """Store backup metadata and return its name."""
        ...

    def update_status(
        self,
        backup_name: str,
        status: str,
        file_path: str = None,
        size_bytes: int = None,
        checksum: str = None
    ) -> None:
        """Update backup status and metadata."""
        ...


class TestResultRepository(Protocol):
    """Repository for test results."""

    __test__ = False

    def store(self, test_result: Dict[str, Any]) -> None:
        """Store test results."""
        ...

    def find(self, category: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Find test results by category and time window."""
        ...
