"""Domain ports - pure interfaces for hexagonal architecture.

These protocols define the contracts between the domain logic and infrastructure
adapters. The domain depends only on these abstract interfaces, not on concrete
implementations like SQLite, filesystem, or Docker.
"""

from datetime import datetime
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

    def store(self, test_result: Dict[str, Any]) -> None:
        """Store test results."""
        ...

    def find(self, category: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Find test results by category and time window."""
        ...


class ChecksumService(Protocol):
    """Service for computing file checksums."""

    def compute(self, file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        ...


class StorageProvider(Protocol):
    """Storage provider for file operations.

    This abstraction allows redirecting file I/O to memory during tests,
    making the core logic independent of the filesystem.
    """

    def write(self, key: str, data: bytes) -> None:
        """Write data to a key."""
        ...

    def read(self, key: str) -> bytes:
        """Read data from a key."""
        ...

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with a prefix."""
        ...

    def delete(self, key: str) -> None:
        """Delete a key."""
        ...

    def join_path(self, *parts: str) -> str:
        """Join path parts in an OS-agnostic way."""
        ...

    # Extended methods for backup service
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists."""
        ...

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        ...

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists."""
        ...

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        ...

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory with pattern."""
        ...

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        ...

    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        ...

    def store_backup_metadata(self, filename: str, metadata: Dict[str, Any]) -> None:
        """Store backup metadata."""
        ...

    def log_restore_operation(self, backup_name: str, metadata: Dict[str, Any]) -> None:
        """Log restore operation."""
        ...

    def get_backup_directory(self) -> str:
        """Get backup directory."""
        ...

    def get_base_directory(self) -> str:
        """Get base directory."""
        ...


class BackupDriver(Protocol):
    """Driver for backup operations.

    Encapsulates the knowledge of backup tools (tar, etc.)
    so the application layer remains OS-agnostic.
    """

    def create(self, source_dir: str, dest_path: str) -> None:
        """Create a backup archive."""
        ...

    def extract(self, archive_path: str, dest_dir: str) -> None:
        """Extract a backup archive."""
        ...


class TestRunner(Protocol):
    """Runner for test suites.

    Encapsulates the knowledge of pytest execution,
    allowing the application to run tests without subprocess details.
    """

    def run_suite(self, suite: str, coverage: bool = True) -> Dict[str, Any]:
        """Run a test suite and return results."""
        ...

    def get_coverage(self) -> Dict[str, float]:
        """Get current test coverage."""
        ...


class AlertTransporter(Protocol):
    """Transport for sending alerts to external systems.

    Encapsulates the knowledge of HTTP/webhook transport,
    allowing the application to send alerts without knowing about requests.
    """

    def send(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Send an alert payload and return result."""
        ...


class LogReader(Protocol):
    """Reader for log files.

    Encapsulates the knowledge of log file locations and parsing,
    allowing the application to read logs without knowing filesystem structure.
    """

    def read_log_file(self, log_path: str) -> str:
        """Read log file content."""
        ...

    def get_default_log_path(self) -> str:
        """Get default log file path."""
        ...


class ConfigProvider(Protocol):
    """Provider for configuration values.

    Encapsulates the knowledge of configuration sources,
    allowing the application to access config without knowing about environment variables or files.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...

    def get_service_urls(self) -> Dict[str, str]:
        """Get service URLs."""
        ...


class SubprocessRunner(Protocol):
    """Runner for subprocess commands.

    Encapsulates the knowledge of subprocess execution,
    allowing the application to run commands without subprocess details.
    """

    def run(self, cmd: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
        """Run command and return result."""
        ...


class LogParser(Protocol):
    """Parser for execution logs.

    Encapsulates the knowledge of log parsing,
    allowing the application to parse logs without knowing format details.
    """

    def parse(self, log_content: str) -> Dict[str, List[datetime]]:
        """Parse log content and extract timestamps."""
        ...


class KPIFormatter(Protocol):
    """Formatter for KPI metrics.

    Encapsulates the knowledge of formatting metrics (CSV, JSON, etc.),
    allowing the application to format metrics without knowing format details.
    """

    def format_csv(self, metrics: Dict[str, Any]) -> str:
        """Format metrics as CSV string."""
        ...


class IOCGenerator(Protocol):
    """Generator for Indicators of Compromise (IOCs).

    Encapsulates the knowledge of IOC generation,
    allowing the application to generate IOCs without knowing generation logic.
    """

    def generate_malicious_hash(self, seed: Any = None) -> str:
        """Generate a simulated malicious SHA256 hash."""
        ...

    def generate_benign_hash(self, seed: Any = None) -> str:
        """Generate a simulated benign SHA256 hash."""
        ...

    def generate_ip_addresses(self, count: int = 5) -> List[str]:
        """Generate random private IP addresses."""
        ...

    def generate_domains(self, count: int = 5) -> List[str]:
        """Generate random domains."""
        ...

    def generate_urls(self, count: int = 5) -> List[str]:
        """Generate random URLs."""
        ...

    def create_ioc_package(self, count: int = 5) -> Dict[str, Any]:
        """Create a JSON package of simulated IOCs."""
        ...


class SystemMetricsInterface(Protocol):
    """Interface for system metrics operations"""

    def get_hardware_metrics(self) -> Dict[str, Any]:
        """Get hardware metrics (CPU, memory, disk)."""
        ...

    def get_process_metrics(self) -> Dict[str, Any]:
        """Get process metrics."""
        ...


class CacheInterface(Protocol):
    """Interface for caching operations"""

    def setex(self, key: str, time: int, value: str) -> None:
        """Set key with expiration."""
        ...

    def get(self, key: str) -> str:
        """Get key value."""
        ...


class PathProviderInterface(Protocol):
    """Interface for path operations"""

    def get_tests_path(self) -> str:
        """Get tests path."""
        ...

    def get_category_test_path(self, category: str) -> str:
        """Get category test path."""
        ...


class TestResultParserInterface(Protocol):
    """Interface for parsing test results from runner output"""

    def parse(self, output: str) -> dict:
        """Parse test results."""
        ...


class FileSystemInterface(Protocol):
    """Interface for file system operations"""

    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists."""
        ...

    def write_file(self, path: str, content: str) -> None:
        """Write file content."""
        ...

    def read_file(self, path: str) -> str:
        """Read file content."""
        ...


class HealthCheckInterface(Protocol):
    """Interface for health check operations"""

    async def check_service(self, service_name: str, url: str) -> bool:
        """Check if a service is running by checking HTTP endpoint."""
        ...


class HTTPClient(Protocol):
    """Interface for HTTP client operations"""

    async def get(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> int:
        """Perform a GET request and return status code."""
        ...

    async def get_json(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> Dict[str, Any]:
        """Perform a GET request and return JSON response."""
        ...


class WebSocketManager(Protocol):
    """Interface for WebSocket connection management"""

    def connect(self, websocket: Any) -> None:
        """Connect a WebSocket client."""
        ...

    def disconnect(self, websocket: Any) -> None:
        """Disconnect a WebSocket client."""
        ...

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        ...
