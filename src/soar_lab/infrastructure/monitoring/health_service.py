"""Health service for SOAR Lab API."""

from typing import Any

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import HealthCheckInterface, SystemMetricsInterface

logger = get_logger(__name__)


class HealthService:
    """Service for health checks and system metrics with injected.

    dependencies.
    """

    def __init__(
        self,
        health_checker: HealthCheckInterface,
        system_metrics: SystemMetricsInterface,
        soar_clients: dict[str, Any] | None = None,
    ) -> None:
        """Initialize health service with injected dependencies.

        Args:
            health_checker: HealthCheckInterface instance (injected dependency)
            system_metrics: SystemMetricsInterface instance (injected dependency)
            soar_clients: Optional dict of integration clients keyed by service name
                          e.g. {"thehive": TheHiveClient, "cortex": CortexClient, ...}
        """
        self.health_checker = health_checker
        self.system_metrics = system_metrics
        self._soar_clients: dict[str, Any] = soar_clients or {}

    async def check_service(self, service_name: str, service_config: dict[str, str]) -> bool:
        """Check if a service is running by checking HTTP endpoint.

        Args:
            service_name: Name of the service
            service_config: Service configuration dict with 'url' and 'container' keys

        Returns:
            bool: True if service is running, False otherwise
        """
        url = service_config.get("url")
        return await self.health_checker.check_service(service_name, url)

    async def get_all_services_status(
        self, services_config: dict[str, dict[str, str]]
    ) -> dict[str, Any]:
        """Get status of all configured services, including SOAR integration.

        clients.

        Args:
            services_config: Dict mapping service names to their configuration

        Returns:
            Dict mapping service names to their status
        """
        status: dict[str, Any] = {}

        for service_name, service_config in services_config.items():
            try:
                status[service_name] = await self.check_service(service_name, service_config)
            except Exception as e:
                logger.error(f"Error checking service {service_name}: {e}")
                status[service_name] = False

        for client_name, client in self._soar_clients.items():
            if client_name in status:
                continue
            try:
                status[client_name] = client.health_check()
            except Exception as e:
                logger.error(f"Error checking SOAR client {client_name}: {e}")
                status[client_name] = False

        return status

    def get_system_metrics(self) -> dict[str, Any]:
        """Get system metrics (CPU, memory, disk usage).

        Returns:
            Dict with cpu, memory, disk percentages and timestamp
        """
        try:
            # Delegate to injected system metrics dependency
            return self.system_metrics.get_hardware_metrics()
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            raise
