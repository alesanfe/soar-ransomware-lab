"""Health Check Adapter for HTTP-based service health checks.

This adapter encapsulates the HTTP client logic for health checks,
allowing the application layer to remain infrastructure-agnostic.
"""

import asyncio
import socket

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import HTTPClient

logger = get_logger(__name__)


class HTTPHealthCheckAdapter:
    """Adapter for HTTP-based health checks using HTTPClient port."""

    def __init__(
        self,
        http_client: HTTPClient,
        verify_ssl_config: dict[str, bool | str] | None = None,
    ) -> None:
        """Initialize the HTTP health check adapter.

        Args:
            http_client: HTTPClient instance (injected dependency)
            verify_ssl_config: Optional dict mapping service names to SSL
                verification settings — ``True``/``False`` or a CA bundle
                path (GRAF-D10 internal TLS pins the lab CA).
        """
        if not http_client:
            raise ValueError("http_client is required for HTTPHealthCheckAdapter")
        self.http_client = http_client
        self.verify_ssl_config = verify_ssl_config or {}

    async def check_service(self, service_name: str, url: str) -> bool:
        """Check if a service is running by checking HTTP endpoint.

        Args:
            service_name: Name of the service
            url: HTTP endpoint to check

        Returns:
            bool: True if service is running, False otherwise
        """
        if not url:
            logger.debug(f"No HTTP URL configured for {service_name}, skipping check")
            return False

        if url.startswith("tcp://"):
            return await self._check_tcp(service_name, url)

        try:
            # Determine SSL verification setting
            verify_ssl = self.verify_ssl_config.get(service_name, True)

            # Use injected HTTP client
            status_code = await self.http_client.get(url, verify_ssl=verify_ssl)
            return status_code < 400
        except Exception as http_error:
            logger.debug(f"HTTP health check failed for {service_name}: {http_error}")
            return False

    async def _check_tcp(self, service_name: str, url: str, timeout: float = 5.0) -> bool:
        """Check raw TCP reachability for non-HTTP services (e.g. ``tcp://redis:6379``).

        Some lab services do not speak HTTP (Redis uses RESP), so an HTTP GET
        produces a false "offline". A successful socket connect proves the
        service is accepting connections.
        """
        host_port = url[len("tcp://") :].rstrip("/")
        host, _, port_s = host_port.rpartition(":")
        try:
            port = int(port_s)
        except ValueError:
            logger.debug(f"Invalid tcp health url for {service_name}: {url}")
            return False

        def _connect() -> bool:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True
            except OSError:
                return False

        try:
            return await asyncio.to_thread(_connect)
        except Exception as tcp_error:
            logger.debug(f"TCP health check failed for {service_name}: {tcp_error}")
            return False
