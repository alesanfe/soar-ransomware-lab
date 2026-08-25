"""Domain ports - pure interfaces for hexagonal architecture.

These protocols define the contracts between the domain logic and infrastructure
adapters. The domain depends only on these abstract interfaces, not on concrete
implementations like SQLite, filesystem, or Docker.

This module re-exports all ports from submodules for backward compatibility.
"""

# Re-export infrastructure ports
from .infrastructure import (
    BackupDriver,
    BackupStorageProvider,
    CacheInterface,
    ChecksumService,
    ConfigProvider,
    FileSystemInterface,
    HealthCheckInterface,
    HTTPClient,
    KPIFormatter,
    LogParser,
    LogReader,
    PathProviderInterface,
    StatisticalCalculatorInterface,
    StorageProvider,
    SubprocessRunner,
    SyncHTTPClient,
    SystemMetricsInterface,
    TestResultParserInterface,
    TestRunner,
    TokenProviderInterface,
    WebSocketManager,
)

# Re-export integration ports
from .integrations import (
    AlertTransporter,
    IOCGenerator,
)

# Re-export repository ports
from .repositories import (
    AlertRepository,
    BackupRepository,
    CaseRepository,
    IocRepository,
    MetricRepository,
    TestResultRepository,
)

__all__ = [
    # Repositories
    "AlertRepository",
    "IocRepository",
    "MetricRepository",
    "CaseRepository",
    "BackupRepository",
    "TestResultRepository",
    # Infrastructure
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
    # Integrations
    "IOCGenerator",
    "AlertTransporter",
]
