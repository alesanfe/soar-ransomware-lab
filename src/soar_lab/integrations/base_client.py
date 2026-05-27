#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Base HTTP Client
Shared HTTP logic (retries, timeouts, error handling) for all SOAR tool clients.
Implements SyncHTTPClient port for integration layer.
"""

import requests
import time
from requests.adapters import HTTPAdapter
from typing import Any, Dict, Optional
from urllib3.util.retry import Retry

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import SyncHTTPClient
from soar_lab.exceptions import IntegrationError

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.5


class BaseHTTPClient(SyncHTTPClient):
    """Synchronous HTTP client with retry logic and uniform error handling.

    Implements SyncHTTPClient port for integration clients.
    Subclass for each external SOAR tool and override *base_url* / *_default_headers*.
    """

    def __init__(
            self,
            base_url: str,
            api_key: Optional[str] = None,
            timeout: int = DEFAULT_TIMEOUT,
            retries: int = DEFAULT_RETRIES,
            verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = self._build_session(api_key, retries)
        self._session.verify = verify_ssl

    def _build_session(self, api_key: Optional[str], retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=DEFAULT_BACKOFF,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self._default_headers(api_key))
        return session

    def _default_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Perform a GET request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        url = self._url(path)
        try:
            resp = self._session.get(url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except requests.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def post(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Perform a POST request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        url = self._url(path)
        try:
            resp = self._session.post(url, json=data, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except requests.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def health_check(self) -> bool:
        """Return True if the service responds to a health endpoint."""
        try:
            self._session.get(self.base_url, timeout=self.timeout)
            return True
        except Exception:
            return False
