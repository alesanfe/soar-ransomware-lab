"""SQLite Alert Repository - Pure CRUD operations.

This repository handles only data persistence operations, following the
Repository pattern and Single Responsibility Principle.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from soar_lab.common.constants import DEFAULT_ALERT_QUERY_LIMIT
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import ConfigProvider

logger = get_logger(__name__)


class SqliteAlertRepository:
    """SQLite repository for alerts, cases, and backup data."""

    def __init__(
        self,
        db_path: str | None = None,
        config_provider: ConfigProvider | None = None,
        path_service: object | None = None,
    ) -> None:
        """Initialize the SQLite repository.

        Args:
            db_path: Path to SQLite database file
            config_provider: Configuration provider for db_path
            path_service: PathService instance for default path calculation
        """
        if db_path is None:
            if path_service:
                db_path = str(path_service.base_dir / "runtime" / "data" / "soar_data.db")
            elif config_provider:
                db_path = config_provider.get("db_path")
                if not db_path:
                    raise ValueError(
                        "db_path must be provided via parameter, config_provider, or path_service"
                    )
            else:
                # Require explicit config or db_path - no fallback to global settings
                raise ValueError("db_path, config_provider, or path_service must be supplied")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with production pragmas applied.

        - ``journal_mode=WAL``: readers never block the single writer and
          crash recovery is journal-based (persisted per-database).
        - ``busy_timeout=5000``: writers wait on locks instead of failing
          instantly with ``database is locked`` under concurrency.
        - ``foreign_keys=ON``: relational integrity enforced at the driver.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    hostname TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    status TEXT DEFAULT 'new'
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    alert_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'open'
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_name TEXT UNIQUE NOT NULL,
                    backup_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    file_path TEXT,
                    size_bytes INTEGER,
                    checksum TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )"""
            )
            # Create test_coverage table
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS test_coverage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_category TEXT NOT NULL,
                    coverage_percentage REAL,
                    tests_run INTEGER,
                    tests_passed INTEGER,
                    tests_failed INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )"""
            )

            # Lookup indexes — alert lists/KPIs filter and order by these.
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON alerts(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_severity ON alerts(severity)")

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    # Alert CRUD operations
    def store_alert(self, alert_data: dict[str, Any]) -> str:
        """Store an alert in the database.

        Args:
            alert_data: Alert data dictionary

        Returns:
            Alert ID

        Raises:
            ValueError: When ``alert_id`` is missing — inserting a NULL key
                would silently corrupt the table (NULLs bypass UNIQUE).
        """
        if not alert_data.get("alert_id"):
            raise ValueError("alert_data['alert_id'] is required")
        with self.lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO alerts (alert_id, alert_type,
                severity, hostname, data, status) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    alert_type=excluded.alert_type,
                    severity=excluded.severity,
                    hostname=excluded.hostname,
                    data=excluded.data,
                    status=excluded.status""",
                (
                    alert_data.get("alert_id"),
                    alert_data.get("alert_type"),
                    alert_data.get("severity"),
                    alert_data.get("hostname"),
                    json.dumps(alert_data.get("data", {})),
                    alert_data.get("status", "new"),
                ),
            )
            conn.commit()
            logger.info(f"Stored alert: {alert_data.get('alert_id')}")
            return alert_data.get("alert_id")

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        """Get an alert by ID.

        Args:
            alert_id: Alert ID

        Returns:
            Alert data or None if not found
        """
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "alert_id": row["alert_id"],
                    "alert_type": row["alert_type"],
                    "severity": row["severity"],
                    "hostname": row["hostname"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"]) if row["data"] else {},
                    "status": row["status"],
                }
            return None

    def get_alerts(
        self, limit: int = DEFAULT_ALERT_QUERY_LIMIT, severity: str = None
    ) -> list[dict[str, Any]]:
        """Get alerts with optional filtering.

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level

        Returns:
            List of alert data
        """
        limit = max(0, limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if severity:
                cursor.execute(
                    "SELECT * FROM alerts WHERE severity = ? ORDER BY timestamp DESC LIMIT ?",
                    (severity, limit),
                )
            else:
                cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))

            return [
                {
                    "id": row["id"],
                    "alert_id": row["alert_id"],
                    "alert_type": row["alert_type"],
                    "severity": row["severity"],
                    "hostname": row["hostname"],
                    "timestamp": row["timestamp"],
                    "data": json.loads(row["data"]) if row["data"] else {},
                    "status": row["status"],
                }
                for row in cursor.fetchall()
            ]

    def count_alerts(self) -> int:
        """Count total alerts in database.

        Returns:
            Total number of alerts
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts")
            return cursor.fetchone()[0]

    # Case CRUD operations
    def store_case(self, case_data: dict[str, Any]) -> str:
        """Store a case in the database.

        Args:
            case_data: Case data dictionary

        Returns:
            Case ID

        Raises:
            ValueError: When ``case_id`` is missing (NULL would bypass UNIQUE).
        """
        if not case_data.get("case_id"):
            raise ValueError("case_data['case_id'] is required")
        with self.lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cases (case_id, title, description,
                severity, alert_id, status) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    severity=excluded.severity,
                    alert_id=excluded.alert_id,
                    status=excluded.status""",
                (
                    case_data.get("case_id"),
                    case_data.get("title"),
                    case_data.get("description"),
                    case_data.get("severity"),
                    case_data.get("alert_id"),
                    case_data.get("status", "open"),
                ),
            )
            conn.commit()
            logger.info(f"Stored case: {case_data.get('case_id')}")
            return case_data.get("case_id")

    def get_cases(
        self, status: str = None, limit: int = DEFAULT_ALERT_QUERY_LIMIT
    ) -> list[dict[str, Any]]:
        """Get cases with optional status filtering.

        Args:
            status: Filter by case status
            limit: Maximum number of cases to return

        Returns:
            List of case data
        """
        limit = max(0, limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT * FROM cases WHERE status = ? ORDER BY timestamp DESC LIMIT ?",
                    (status, limit),
                )
            else:
                cursor.execute("SELECT * FROM cases ORDER BY timestamp DESC LIMIT ?", (limit,))

            return [
                {
                    "id": row["id"],
                    "case_id": row["case_id"],
                    "title": row["title"],
                    "description": row["description"],
                    "severity": row["severity"],
                    "alert_id": row["alert_id"],
                    "timestamp": row["timestamp"],
                    "status": row["status"],
                }
                for row in cursor.fetchall()
            ]

    def count_cases_by_status(self, status: str) -> int:
        """Count cases by status.

        Args:
            status: Case status

        Returns:
            Number of cases with given status
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cases WHERE status = ?", (status,))
            return cursor.fetchone()[0]

    # Backup CRUD operations
    def store_backup_info(self, backup_data: dict[str, Any]) -> str:
        """Store backup information.

        Args:
            backup_data: Backup data dictionary

        Returns:
            Backup name
        """
        with self.lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO backups (backup_name,
                    backup_type, status, file_path, size_bytes, checksum,
                    created_by) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(backup_name) DO UPDATE SET
                        backup_type=excluded.backup_type,
                        status=excluded.status,
                        file_path=excluded.file_path,
                        size_bytes=excluded.size_bytes,
                        checksum=excluded.checksum,
                        created_by=excluded.created_by""",
                    (
                        backup_data.get("backup_name"),
                        backup_data.get("backup_type"),
                        backup_data.get("status"),
                        backup_data.get("file_path"),
                        backup_data.get("size_bytes"),
                        backup_data.get("checksum"),
                        backup_data.get("created_by"),
                    ),
                )
                conn.commit()
                logger.info(f"Stored backup info: {backup_data.get('backup_name')}")
                return backup_data.get("backup_name")

    def get_backups(self, limit: int = DEFAULT_ALERT_QUERY_LIMIT) -> list[dict[str, Any]]:
        """Get all backup information.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup data
        """
        limit = max(0, limit)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backups ORDER BY created_at DESC LIMIT ?", (limit,))

            return [
                {
                    "id": row["id"],
                    "backup_name": row["backup_name"],
                    "backup_type": row["backup_type"],
                    "status": row["status"],
                    "file_path": row["file_path"],
                    "size_bytes": row["size_bytes"],
                    "checksum": row["checksum"],
                    "created_at": row["created_at"],
                    "created_by": row["created_by"],
                }
                for row in cursor.fetchall()
            ]

    # Test coverage operations
    def store_test_coverage(self, coverage_data: dict[str, Any]) -> None:
        """Store test coverage data.

        Args:
            coverage_data: Coverage data dictionary
        """
        with self.lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO test_coverage (test_category,
                    coverage_percentage, tests_run, tests_passed, tests_failed)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        coverage_data.get("test_category"),
                        coverage_data.get("coverage_percentage"),
                        coverage_data.get("tests_run"),
                        coverage_data.get("tests_passed"),
                        coverage_data.get("tests_failed"),
                    ),
                )
                conn.commit()
                logger.info(f"Stored test coverage: {coverage_data.get('test_category')}")

    def get_average_test_coverage(self, hours: int | str = 24) -> float | None:
        """Get average test coverage for the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            Average coverage percentage or None
        """
        hours = int(hours)  # coerce — a non-numeric modifier silently
        # disables the datetime filter instead of raising
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT AVG(coverage_percentage) FROM test_coverage "
                "WHERE timestamp > datetime('now', ?)",
                (f"-{hours} hours",),
            )
            result = cursor.fetchone()[0]
            return float(result) if result is not None else None

    def count_alerts_by_status(self, status: str) -> int:
        """Count alerts by status."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = ?", (status,))
            return cursor.fetchone()[0]

    def count_cases(self) -> int:
        """Count total cases."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cases")
            return cursor.fetchone()[0]

    def count_backups_by_status(self, status: str) -> int:
        """Count backups by status."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM backups WHERE status = ?", (status,))
            return cursor.fetchone()[0]

    def get_test_results(self, hours: int | str = 24) -> list[dict[str, Any]]:
        """Return test coverage rows from the last N hours."""
        hours = int(hours)  # coerce — a non-numeric modifier silently
        # truncates the window instead of failing clearly
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM test_coverage WHERE timestamp > datetime('now', ?) "
                "ORDER BY timestamp DESC",
                (f"-{hours} hours",),
            )
            return [
                {
                    "id": row["id"],
                    "test_category": row["test_category"],
                    "coverage_percentage": row["coverage_percentage"],
                    "tests_run": row["tests_run"],
                    "tests_passed": row["tests_passed"],
                    "tests_failed": row["tests_failed"],
                    "timestamp": row["timestamp"],
                }
                for row in cursor.fetchall()
            ]

    def close(self) -> None:
        """Close the database connection (no-op for this implementation as.

        connections are short-lived).
        """
        # Connections are managed with context managers in each method
        # This method is provided for API compatibility

    def __del__(self) -> None:
        """Cleanup when the repository is garbage collected."""
        self.close()
