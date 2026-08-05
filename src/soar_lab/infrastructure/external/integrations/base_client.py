#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Base HTTP Client
Shared HTTP logic (retries, timeouts, error handling) for all SOAR tool clients.
Implements SyncHTTPClient port for integration layer.
"""

import os
import requests
import time
from requests.adapters import HTTPAdapter
from soar_lab.common.exceptions import IntegrationError
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from urllib3.util.retry import Retry

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import SyncHTTPClient
from soar_lab.resilience.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 0.5

# Integration tests inside Docker often hardcode localhost URLs.
_DOCKER_HOST_MAP = {
    9000: ("thehive:9000", "thehive_api_key"),
    9001: ("cortex:9001", "cortex_api_key"),
    8083: ("misp:443", "misp_api_key"),
    5001: ("soar_shuffle_backend:5001", "shuffle_api_key"),
    9200: ("elasticsearch:9200", None),
    9201: ("elasticsearch:9200", None),
}


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
        base_url, api_key = self._resolve_docker_base_url(base_url, api_key)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = retries
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=(requests.ConnectionError, requests.Timeout),
        )
        self._session = self._build_session(api_key, retries)
        self._session.verify = verify_ssl

    @property
    def session(self) -> requests.Session:
        """Expose the underlying requests Session for test patching."""
        return self._session

    def _build_session(self, api_key: Optional[str], retries: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=DEFAULT_BACKOFF,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self._default_headers(api_key))
        return session

    def _default_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _resolve_docker_base_url(self, base_url: str, api_key: Optional[str]) -> Tuple[str, Optional[str]]:
        """Rewrite localhost / internal service URLs to Docker service names and load real API keys."""
        if not os.path.exists("/.dockerenv"):
            return base_url, api_key
        try:
            parsed = urlparse(base_url)
            # MISP exposes HTTP on port 80 but its REST API requires HTTPS on
            # port 443 (port 80 just redirects). Rewrite internal MISP URLs to
            # HTTPS so POST requests such as /events/restSearch work directly.
            if parsed.hostname in ("misp", "soar_misp") and parsed.port == 80:
                parsed = parsed._replace(scheme="https", netloc=f"{parsed.hostname}:443")
                return urlunparse(parsed), api_key
            if parsed.hostname != "localhost":
                return base_url, api_key
            port = parsed.port
            mapping = _DOCKER_HOST_MAP.get(port)
            if not mapping:
                return base_url, api_key
            netloc, key_name = mapping
            scheme = "https" if port == 8083 else (parsed.scheme or "http")
            parsed = parsed._replace(scheme=scheme, netloc=netloc)
            base_url = urlunparse(parsed)
            if key_name and (not api_key or api_key == "test-key"):
                api_key = self._load_env_key(key_name)
        except Exception:
            pass
        return base_url, api_key

    def _load_env_key(self, key_name: str) -> Optional[str]:
        """Load a real API key from Settings or environment variables."""
        try:
            from soar_lab.config.settings import Settings
            settings = Settings()
            value = settings.get(key_name)
            if value:
                return value
        except Exception:
            pass
        return os.environ.get(key_name.upper())

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Perform a GET request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        def _do_get():
            url = self._url(path)
            # Use Accept: */* for GET requests and suppress Content-Type to avoid
            # TheHive rejecting empty JSON bodies when Accept is application/json.
            session_headers = self._session.headers.copy()
            session_headers['Content-Type'] = None
            session_headers['Accept'] = '*/*'
            try:
                resp = self._session.get(url, timeout=self.timeout, headers=session_headers, **kwargs)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_get)

    def post(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Perform a POST request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        def _do_post():
            url = self._url(path)
            try:
                resp = self._session.post(url, json=data, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_post)

    def put(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Perform a PUT request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        def _do_put():
            url = self._url(path)
            try:
                resp = self._session.put(url, json=data, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_put)

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Perform a DELETE request.

        Raises:
            IntegrationError: On HTTP or connection error.
        """
        def _do_delete():
            url = self._url(path)
            try:
                resp = self._session.delete(url, timeout=self.timeout, **kwargs)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_delete)

    def health_check(self) -> bool:
        """Return True if the service responds to a health endpoint."""
        try:
            self._session.get(self.base_url, timeout=self.timeout)
            return True
        except Exception:
            return False
