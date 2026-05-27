"""FastAPI dependency injection for hexagonal architecture.

This module provides dependency functions for FastAPI endpoints,
delegating to the CompositionRoot for dependency resolution.
"""

from fastapi import Depends
from typing import Annotated, Optional


def get_composition_root(composition_root: object = None) -> object:
    """Dependency that provides the composition root instance."""
    if composition_root is None:
        raise ValueError("composition_root must be provided via dependency injection")
    return composition_root


def get_config_provider(composition_root: object = Depends(get_composition_root)) -> object:
    """Dependency that provides the configuration provider from composition root."""
    return composition_root.config_provider


def get_redis(composition_root: object = Depends(get_composition_root)) -> Optional[object]:
    """Dependency that provides the Redis client from composition root."""
    return composition_root.redis_client


def get_docker(composition_root: object = Depends(get_composition_root)) -> Optional[object]:
    """Dependency that provides the Docker client from composition root."""
    return composition_root.docker_client


def get_analytics_service(composition_root: object = Depends(get_composition_root)) -> object:
    """Dependency that provides the analytics service from composition root."""
    return composition_root.analytics_service


def get_backup_service(composition_root: object = Depends(get_composition_root)) -> object:
    """Dependency that provides the backup service from composition root."""
    return composition_root.backup_service


def get_test_service(composition_root: object = Depends(get_composition_root)) -> object:
    """Dependency that provides the test service from composition root."""
    return composition_root.test_service


def get_health_service(composition_root: object = Depends(get_composition_root)) -> object:
    """Dependency that provides the health service from composition root."""
    return composition_root.health_service


# Type aliases for cleaner dependency annotations
RedisDep = Annotated[Optional[object], Depends(get_redis)]
DockerDep = Annotated[Optional[object], Depends(get_docker)]
ConfigProviderDep = Annotated[object, Depends(get_config_provider)]
AnalyticsServiceDep = Annotated[object, Depends(get_analytics_service)]
BackupServiceDep = Annotated[object, Depends(get_backup_service)]
TestServiceDep = Annotated[object, Depends(get_test_service)]
HealthServiceDep = Annotated[object, Depends(get_health_service)]
