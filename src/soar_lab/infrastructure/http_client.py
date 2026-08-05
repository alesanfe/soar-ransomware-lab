"""HTTP Client - Infrastructure implementation of HTTPClient port.

This adapter provides an aiohttp-based implementation of the HTTPClient port,
allowing the application layer to make HTTP requests without knowing about aiohttp.
"""

import aiohttp
import ssl
from typing import Dict, Any

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class AioHTTPClient:
    """aiohttp-based implementation of HTTPClient port."""

    def __init__(self, default_timeout: int = 5, default_verify_ssl: bool = True):
        """
        Initialize the HTTP client.

        Args:
            default_timeout: Default request timeout in seconds
            default_verify_ssl: Default SSL verification setting
        """
        self.default_timeout = default_timeout
        self.default_verify_ssl = default_verify_ssl

    async def get(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> int:
        """
        Perform a GET request and return status code.

        Args:
            url: URL to request
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates

        Returns:
            HTTP status code
        """
        effective_timeout = timeout if timeout else self.default_timeout
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl

        try:
            ssl_context = None
            connector = None
            if not effective_verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=effective_timeout)
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    return response.status
        except Exception as e:
            logger.error(f"HTTP GET request failed for {url}: {e}")
            raise

    async def get_json(self, url: str, timeout: int = 5, verify_ssl: bool = True) -> Dict[str, Any]:
        """
        Perform a GET request and return JSON response.

        Args:
            url: URL to request
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates

        Returns:
            JSON response as dict
        """
        effective_timeout = timeout if timeout else self.default_timeout
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl

        try:
            ssl_context = None
            connector = None
            if not effective_verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=effective_timeout)
            ) as session:
                async with session.get(url, allow_redirects=True) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"HTTP GET JSON request failed for {url}: {e}")
            raise
