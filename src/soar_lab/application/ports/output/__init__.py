"""Output ports - contracts for infrastructure required by application use cases.

These ports re-export the abstract interfaces defined in ``domain.ports``
so that application use cases depend on ``application.ports.output``
rather than directly on the domain layer. This keeps the dependency
direction consistent: application may import domain, but the application
layer should reference its own ports package for clarity.

The actual Protocol definitions live in ``domain.ports`` because some
domain services also depend on them (e.g. ``KPIAnalyzer`` needs
``StatisticalCalculatorInterface``). Moving them to application would
force the domain to import from application, violating the dependency
rule of hexagonal architecture.
"""

from soar_lab.domain.ports import (
    AlertRepository,
    BackupDriver,
    BackupRepository,
    BackupStorageProvider,
    CacheInterface,
    CaseRepository,
    ChecksumService,
    ConfigProvider,
    FileSystemInterface,
    HealthCheckInterface,
    HTTPClient,
    IOCGenerator,
    IocRepository,
    KPIFormatter,
    LogParser,
    LogReader,
    MetricRepository,
    PathProviderInterface,
    StatisticalCalculatorInterface,
    StorageProvider,
    SubprocessRunner,
    SyncHTTPClient,
    SystemMetricsInterface,
    TestResultParserInterface,
    TestResultRepository,
    TestRunner,
    TokenProviderInterface,
    WebSocketManager,
)

__all__ = [
    "AlertRepository",
    "BackupDriver",
    "BackupRepository",
    "BackupStorageProvider",
    "CacheInterface",
    "CaseRepository",
    "ChecksumService",
    "ConfigProvider",
    "FileSystemInterface",
    "HTTPClient",
    "HealthCheckInterface",
    "IOCGenerator",
    "IocRepository",
    "KPIFormatter",
    "LogParser",
    "LogReader",
    "MetricRepository",
    "PathProviderInterface",
    "StatisticalCalculatorInterface",
    "StorageProvider",
    "SubprocessRunner",
    "SyncHTTPClient",
    "SystemMetricsInterface",
    "TestResultParserInterface",
    "TestResultRepository",
    "TestRunner",
    "TokenProviderInterface",
    "WebSocketManager",
]
