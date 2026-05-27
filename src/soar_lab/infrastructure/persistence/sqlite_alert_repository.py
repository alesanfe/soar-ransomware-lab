"""SQLite Alert Repository - Pure CRUD operations.

This repository handles only data persistence operations, following the
Repository pattern and Single Responsibility Principle.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class SqliteAlertRepository:
    """SQLite repository for alerts, cases, and backup data."""

    def __init__(self, db_path: str = None, config_provider: Optional[object] = None,
                 path_service: Optional[object] = None):
        """
        Initialize the SQLite repository.

        Args:
            db_path: Path to SQLite database file
            config_provider: Configuration provider for db_path
            path_service: PathService instance for default path calculation
        """
        if db_path is None:
            if path_service:
                default_path = path_service.base_dir / "artifacts" / "data" / "soar_data.db"
            elif config_provider:
                db_path = config_provider.get('db_path')
                if not db_path:
                    raise ValueError("db_path must be provided via parameter, config_provider, or path_service")
            else:
                # Require explicit config or db_path - no fallback to global settings
                raise ValueError("db_path, config_provider, or path_service must be supplied")

        if db_path is None and path_service:
            db_path = str(default_path)

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    hostname TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    status TEXT DEFAULT 'new'
                )
            ''')

            # Create cases table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    alert_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'open'
                )
            ''')

            # Create backups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_name TEXT UNIQUE NOT NULL,
                    backup_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    file_path TEXT,
                    size_bytes INTEGER,
                    checksum TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            ''')

            # Create test_coverage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_coverage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_category TEXT NOT NULL,
                    coverage_percentage REAL,
                    tests_run INTEGER,
                    tests_passed INTEGER,
                    tests_failed INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    # Alert CRUD operations
    def store_alert(self, alert_data: Dict[str, Any]) -> str:
        """
        Store an alert in the database.
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            Alert ID
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO alerts 
                    (alert_id, alert_type, severity, hostname, data, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    alert_data.get('alert_id'),
                    alert_data.get('alert_type'),
                    alert_data.get('severity'),
                    alert_data.get('hostname'),
                    json.dumps(alert_data.get('data', {})),
                    alert_data.get('status', 'new')
                ))
                conn.commit()
                logger.info(f"Stored alert: {alert_data.get('alert_id')}")
                return alert_data.get('alert_id')

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Alert data or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM alerts WHERE alert_id = ?",
                (alert_id,)
            )
            row = cursor.fetchone()

            if row:
                return {
                    'id': row['id'],
                    'alert_id': row['alert_id'],
                    'alert_type': row['alert_type'],
                    'severity': row['severity'],
                    'hostname': row['hostname'],
                    'timestamp': row['timestamp'],
                    'data': json.loads(row['data']) if row['data'] else {},
                    'status': row['status']
                }
            return None

    def get_alerts(self, limit: int = 100, severity: str = None) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filtering.
        
        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level
            
        Returns:
            List of alert data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if severity:
                cursor.execute(
                    "SELECT * FROM alerts WHERE severity = ? ORDER BY timestamp DESC LIMIT ?",
                    (severity, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )

            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'id': row['id'],
                    'alert_id': row['alert_id'],
                    'alert_type': row['alert_type'],
                    'severity': row['severity'],
                    'hostname': row['hostname'],
                    'timestamp': row['timestamp'],
                    'data': json.loads(row['data']) if row['data'] else {},
                    'status': row['status']
                })
            return alerts

    def count_alerts(self) -> int:
        """
        Count total alerts in database.
        
        Returns:
            Total number of alerts
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alerts")
            return cursor.fetchone()[0]

    # Case CRUD operations
    def store_case(self, case_data: Dict[str, Any]) -> str:
        """
        Store a case in the database.
        
        Args:
            case_data: Case data dictionary
            
        Returns:
            Case ID
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO cases 
                    (case_id, title, description, severity, alert_id, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    case_data.get('case_id'),
                    case_data.get('title'),
                    case_data.get('description'),
                    case_data.get('severity'),
                    case_data.get('alert_id'),
                    case_data.get('status', 'open')
                ))
                conn.commit()
                logger.info(f"Stored case: {case_data.get('case_id')}")
                return case_data.get('case_id')

    def get_cases(self, status: str = None) -> List[Dict[str, Any]]:
        """
        Get cases with optional status filtering.
        
        Args:
            status: Filter by case status
            
        Returns:
            List of case data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT * FROM cases WHERE status = ? ORDER BY timestamp DESC",
                    (status,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM cases ORDER BY timestamp DESC"
                )

            cases = []
            for row in cursor.fetchall():
                cases.append({
                    'id': row['id'],
                    'case_id': row['case_id'],
                    'title': row['title'],
                    'description': row['description'],
                    'severity': row['severity'],
                    'alert_id': row['alert_id'],
                    'timestamp': row['timestamp'],
                    'status': row['status']
                })
            return cases

    def count_cases_by_status(self, status: str) -> int:
        """
        Count cases by status.
        
        Args:
            status: Case status
            
        Returns:
            Number of cases with given status
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM cases WHERE status = ?",
                (status,)
            )
            return cursor.fetchone()[0]

    # Backup CRUD operations
    def store_backup_info(self, backup_data: Dict[str, Any]) -> str:
        """
        Store backup information.
        
        Args:
            backup_data: Backup data dictionary
            
        Returns:
            Backup name
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO backups 
                    (backup_name, backup_type, status, file_path, size_bytes, checksum, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    backup_data.get('backup_name'),
                    backup_data.get('backup_type'),
                    backup_data.get('status'),
                    backup_data.get('file_path'),
                    backup_data.get('size_bytes'),
                    backup_data.get('checksum'),
                    backup_data.get('created_by')
                ))
                conn.commit()
                logger.info(f"Stored backup info: {backup_data.get('backup_name')}")
                return backup_data.get('backup_name')

    def get_backups(self) -> List[Dict[str, Any]]:
        """
        Get all backup information.
        
        Returns:
            List of backup data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backups ORDER BY created_at DESC")

            backups = []
            for row in cursor.fetchall():
                backups.append({
                    'id': row['id'],
                    'backup_name': row['backup_name'],
                    'backup_type': row['backup_type'],
                    'status': row['status'],
                    'file_path': row['file_path'],
                    'size_bytes': row['size_bytes'],
                    'checksum': row['checksum'],
                    'created_at': row['created_at'],
                    'created_by': row['created_by']
                })
            return backups

    # Test coverage operations
    def store_test_coverage(self, coverage_data: Dict[str, Any]) -> None:
        """
        Store test coverage data.
        
        Args:
            coverage_data: Coverage data dictionary
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO test_coverage 
                    (test_category, coverage_percentage, tests_run, tests_passed, tests_failed)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    coverage_data.get('test_category'),
                    coverage_data.get('coverage_percentage'),
                    coverage_data.get('tests_run'),
                    coverage_data.get('tests_passed'),
                    coverage_data.get('tests_failed')
                ))
                conn.commit()
                logger.info(f"Stored test coverage: {coverage_data.get('test_category')}")

    def get_average_test_coverage(self, hours: int = 24) -> Optional[float]:
        """
        Get average test coverage for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Average coverage percentage or None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT AVG(coverage_percentage) FROM test_coverage "
                "WHERE timestamp > datetime('now', '-{} hours')".format(hours)
            )
            result = cursor.fetchone()[0]
            return float(result) if result else None
