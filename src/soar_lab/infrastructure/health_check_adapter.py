"""Health Check Adapter for HTTP-based service health checks.

This adapter encapsulates the HTTP client logic for health checks,
allowing the application layer to remain infrastructure-agnostic.
"""

from typing import Dict, Any, Optional

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import HTTPClient

logger = get_logger(__name__)


class HTTPHealthCheckAdapter:
    """Adapter for HTTP-based health checks using HTTPClient port."""

    def __init__(self, http_client: HTTPClient, verify_ssl_config: Optional[Dict[str, bool]] = None):
        """
        Initialize the HTTP health check adapter.

        Args:
            http_client: HTTPClient instance (injected dependency)
            verify_ssl_config: Optional dict mapping service names to SSL verification settings
        """
        if not http_client:
            raise ValueError("http_client is required for HTTPHealthCheckAdapter")
        self.http_client = http_client
        self.verify_ssl_config = verify_ssl_config or {}

    async def check_service(self, service_name: str, url: str) -> bool:
        """
        Check if a service is running by checking HTTP endpoint.

        Args:
            service_name: Name of the service
            url: HTTP endpoint to check

        Returns:
            bool: True if service is running, False otherwise
        """
        if not url:
            logger.debug(f"No HTTP URL configured for {service_name}, skipping check")
            return False

        try:
            # Determine SSL verification setting
            verify_ssl = self.verify_ssl_config.get(service_name, True)

            # Use injected HTTP client
            status_code = await self.http_client.get(url, verify_ssl=verify_ssl)
            return status_code < 400
        except Exception as http_error:
            logger.debug(f"HTTP health check failed for {service_name}: {http_error}")
            return False
