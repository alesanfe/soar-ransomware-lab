"""Domain ports - Infrastructure interfaces.

These protocols define the contracts for infrastructure operations
like storage, backup, test running, and subprocess execution.
The domain depends only on these abstract interfaces, not on concrete
implementations like filesystem, Docker, or subprocess.
"""

from datetime import datetime
from typing import Any, Protocol

__all__ = [
    "ChecksumService",
    "StorageProvider",
    "BackupStorageProvider",
    "BackupDriver",
    "TestRunner",
    "LogReader",
    "ConfigProvider",
    "SubprocessRunner",
    "LogParser",
    "KPIFormatter",
    "StatisticalCalculatorInterface",
    "SystemMetricsInterface",
    "CacheInterface",
    "PathProviderInterface",
    "TestResultParserInterface",
    "FileSystemInterface",
    "HealthCheckInterface",
    "HTTPClient",
    "SyncHTTPClient",
    "WebSocketManager",
    "TokenProviderInterface",
]


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

    def list_keys(self, prefix: str = "") -> list[str]:
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

    def list_files(self, directory: str, pattern: str = "*") -> list[str]:
        """List files in directory with pattern."""
        ...

    def get_file_info(self, path: str) -> dict[str, Any]:
        """Get file information."""
        ...

    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        ...

    def get_backup_directory(self) -> str:
        """Get backup directory."""
        ...

    def get_base_directory(self) -> str:
        """Get base directory."""
        ...


class BackupStorageProvider(Protocol):
    """Extended storage provider with backup-specific capabilities.

    This protocol extends StorageProvider with methods specifically for
    backup operations, avoiding the use of hasattr() and making the
    contract explicit.
    """

    def store_backup_metadata(self, filename: str, metadata: dict[str, Any]) -> None:
        """Store backup metadata."""
        ...

    def log_restore_operation(self, backup_name: str, metadata: dict[str, Any]) -> None:
        """Log restore operation."""
        ...


class BackupDriver(Protocol):
    """Driver for backup operations.

    Encapsulates the knowledge of backup tools (tar, etc.) so the
    application layer remains OS-agnostic.
    """

    def create(self, source_dir: str, dest_path: str) -> None:
        """Create a backup archive."""
        ...

    def extract(self, archive_path: str, dest_dir: str) -> None:
        """Extract a backup archive."""
        ...


class TestRunner(Protocol):
    """Runner for test suites.

    Encapsulates the knowledge of pytest execution, allowing the
    application to run tests without subprocess details.
    """

    __test__ = False

    def run_suite(self, suite: str, coverage: bool = True) -> dict[str, Any]:
        """Run a test suite and return results."""
        ...

    def get_coverage(self) -> dict[str, float]:
        """Get current test coverage."""
        ...


class LogReader(Protocol):
    """Reader for log files.

    Encapsulates the knowledge of log file locations and parsing,
    allowing the application to read logs without knowing filesystem
    structure.
    """

    def read_log_file(self, log_path: str) -> str:
        """Read log file content."""
        ...

    def get_default_log_path(self) -> str:
        """Get default log file path."""
        ...


class ConfigProvider(Protocol):
    """Provider for configuration values.

    Encapsulates the knowledge of configuration sources, allowing the
    application to access config without knowing about environment
    variables or files.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...

    def get_service_urls(self) -> dict[str, str]:
        """Get service URLs."""
        ...


class SubprocessRunner(Protocol):
    """Runner for subprocess commands.

    Encapsulates the knowledge of subprocess execution, allowing the
    application to run commands without subprocess details.
    """

    def run(self, cmd: list[str], timeout: int | None = None) -> dict[str, Any]:
        """Run command and return result."""
        ...


class LogParser(Protocol):
    """Parser for execution logs.

    Encapsulates the knowledge of log parsing, allowing the application
    to parse logs without knowing format details.
    """

    def parse(self, log_content: str) -> dict[str, list[datetime]]:
        """Parse log content and extract timestamps."""
        ...


class KPIFormatter(Protocol):
    """Formatter for KPI metrics.

    Encapsulates the knowledge of formatting metrics (CSV, JSON, etc.),
    allowing the application to format metrics without knowing format
    details.
    """

    def format_csv(self, metrics: dict[str, Any]) -> str:
        """Format metrics as CSV string."""
        ...


class StatisticalCalculatorInterface(Protocol):
    """Interface for statistical calculations.

    Encapsulates the knowledge of statistical computations, allowing the
    application to perform calculations without depending on concrete
    implementations.
    """

    def calculate_execution_times(
        self, alert_steps: dict[str, list[datetime]]
    ) -> dict[str, list[float]]:
        """Calculate execution times from alert step timestamps."""
        ...


class SystemMetricsInterface(Protocol):
    """Interface for system metrics operations."""

    def get_hardware_metrics(self) -> dict[str, Any]:
        """Get hardware metrics (CPU, memory, disk)."""
        ...

    def get_process_metrics(self) -> dict[str, Any]:
        """Get process metrics."""
        ...


class CacheInterface(Protocol):
    """Interface for caching operations."""

    def setex(self, key: str, time: int, value: str) -> None:
        """Set key with expiration."""
        ...

    def get(self, key: str) -> str:
        """Get key value."""
        ...


class PathProviderInterface(Protocol):
    """Interface for path operations."""

    def get_tests_path(self) -> str:
        """Get tests path."""
        ...

    def get_category_test_path(self, category: str) -> str:
        """Get category test path."""
        ...


class TestResultParserInterface(Protocol):
    """Interface for parsing test results from runner output."""

    def parse(self, output: str) -> dict:
        """Parse test results."""
        ...


class FileSystemInterface(Protocol):
    """Interface for file system operations."""

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
    """Interface for health check operations."""

    async def check_service(self, service_name: str, url: str) -> bool:
        """Check if a service is running by checking HTTP endpoint."""
        ...


class HTTPClient(Protocol):
    """Interface for async HTTP client operations (for FastAPI/async.

    contexts)
    """

    async def get(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> int:
        """Perform a GET request and return status code."""
        ...

    async def get_json(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> dict[str, Any]:
        """Perform a GET request and return JSON response."""
        ...


class SyncHTTPClient(Protocol):
    """Interface for synchronous HTTP client operations (for integrations).

    Used by integration clients (TheHive, Cortex, MISP, Shuffle) that
    operate in synchronous contexts and need retry logic, session
    management, etc.
    """

    def get(self, path: str, **kwargs) -> dict[str, Any]:
        """Perform a GET request and return JSON response."""
        ...

    def post(self, path: str, data: dict | None = None, **kwargs) -> dict[str, Any]:
        """Perform a POST request and return JSON response."""
        ...

    def health_check(self) -> bool:
        """Check if the service is reachable."""
        ...


class WebSocketManager(Protocol):
    """Interface for WebSocket connection management."""

    async def connect(self, websocket: Any) -> None:
        """Connect a WebSocket client."""
        ...

    def disconnect(self, websocket: Any) -> None:
        """Disconnect a WebSocket client."""
        ...

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        ...


class TokenProviderInterface(Protocol):
    """Interface for token operations (JWT, etc.).

    Encapsulates the knowledge of token creation and verification,
    allowing the application to use tokens without depending on specific
    libraries like PyJWT.
    """

    def create_token(
        self, username: str, secret: str, expiration_minutes: int, algorithm: str
    ) -> str:
        """Create a token for the given username."""
        ...

    def verify_token(self, token: str, secret: str, algorithm: str) -> dict[str, Any]:
        """Verify a token and return the payload."""
        ...
