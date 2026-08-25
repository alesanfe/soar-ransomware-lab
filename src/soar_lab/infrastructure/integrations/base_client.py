#!/usr/bin/env python3
"""SOAR Ransomware Lab - Base HTTP Client.

Shared HTTP logic (retries, timeouts, error handling) for all SOAR tool clients.
Implements SyncHTTPClient port for integration layer.
"""

import os
import socket
import time as _time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# DNS cache — work around Docker Desktop's unreliable embedded DNS resolver
# (127.0.0.11). When Orborus spawns many Shuffle worker containers, the DNS
# resolver becomes overwhelmed and returns "Temporary failure in name
# resolution" errors. By caching successful DNS resolutions at the Python
# level, we avoid hitting the flaky resolver repeatedly. On DNS failure, we
# fall back to the last known good IP.
# ---------------------------------------------------------------------------
_DNS_CACHE: dict[tuple[str, int, int], tuple[float, list]] = {}
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_DNS_CACHE_TTL = 300.0  # 5 minutes


def _cached_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    cache_key = (host, port, family)
    cached = _DNS_CACHE.get(cache_key)
    if cached is not None:
        ts, result = cached
        if _time.time() - ts < _DNS_CACHE_TTL:
            return result
    try:
        result = _ORIGINAL_GETADDRINFO(host, port, family, type, proto, flags)
        _DNS_CACHE[cache_key] = (_time.time(), result)
        return result
    except (socket.gaierror, OSError):
        if cached is not None:
            return cached[1]
        raise


# Only patch if we are inside a Docker container (where the DNS issue occurs).
if Path("/.dockerenv").exists():
    socket.getaddrinfo = _cached_getaddrinfo

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    DEFAULT_BACKOFF,
    DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    DEFAULT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
    DEFAULT_POOL_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    SERVICE_MISP,
)
from soar_lab.common.exceptions import IntegrationError
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import SyncHTTPClient
from soar_lab.resilience.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)

_TRACE_ID_HEADER = "X-Request-ID"


def _current_trace_id() -> str | None:
    """Return the active trace ID from request context, if any."""
    try:
        from soar_lab.interfaces.api.middleware import get_trace_id

        return get_trace_id()
    except Exception:
        return None


_TEST_KEY_PLACEHOLDER = "test-key"

# Integration tests inside Docker often hardcode localhost URLs.
_DOCKER_HOST_MAP = {
    9000: ("thehive:9000", "thehive_api_key"),
    9001: ("cortex:9001", "cortex_api_key"),
    8083: ("misp:80", "misp_api_key"),
    5001: ("shuffle-backend:5001", "shuffle_api_key"),
    9200: ("elasticsearch:9200", None),
    9201: ("elasticsearch:9200", None),
}


class BaseHTTPClient(SyncHTTPClient):
    """Synchronous HTTP client with retry logic and uniform error handling.

    Implements SyncHTTPClient port for integration clients. Subclass for
    each external SOAR tool and override *base_url* /
    *_default_headers*.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the HTTP client with base URL, optional API key and retry.

        config.

        Args:
            base_url: Base URL of the remote service (e.g. ``http://thehive:9000``).
            api_key: Optional Bearer token for Authorization header.
            timeout: Per-request timeout in seconds.
            retries: Maximum number of retry attempts on transient errors.
            verify_ssl: Whether to verify TLS certificates (default True).
        """
        base_url, api_key = self._resolve_docker_base_url(base_url, api_key)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = retries
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=DEFAULT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
            expected_exception=(requests.ConnectionError, requests.Timeout, IntegrationError),
        )
        self._session = self._build_session(api_key, retries)
        self._session.verify = verify_ssl

    @property
    def session(self) -> requests.Session:
        """Expose the underlying requests Session for test patching.

        Returns:
            requests.Session: The configured session used by this client.
        """
        return self._session

    def _build_session(self, api_key: str | None, retries: int) -> requests.Session:
        """Create a requests Session with retry adapter and auth headers.

        Args:
            api_key: Optional Bearer token added to default headers.
            retries: Number of retries for the urllib3 Retry adapter.

        Returns:
            requests.Session: Configured session with auth and retry.
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=DEFAULT_BACKOFF,
            status_forcelist=(429, 500, 502, 503, 504),
        )
        adapter = HTTPAdapter(
            pool_connections=DEFAULT_POOL_SIZE,
            pool_maxsize=DEFAULT_POOL_SIZE,
            max_retries=retry,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self._default_headers(api_key))
        return session

    def _default_headers(self, api_key: str | None) -> dict[str, str]:
        """Build default HTTP headers, adding Bearer auth if api_key is set.

        Args:
            api_key: Optional Bearer token.

        Returns:
            dict: Headers with Content-Type, Accept and optional Authorization.
        """
        headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON, HEADER_ACCEPT: CONTENT_TYPE_JSON}
        if api_key:
            headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX} {api_key}"
        return headers

    def _resolve_docker_base_url(
        self, base_url: str, api_key: str | None
    ) -> tuple[str, str | None]:
        """Rewrite localhost / internal service URLs to Docker service names.

        and load real API keys.
        """
        if not Path("/.dockerenv").exists():
            return base_url, api_key
        try:
            parsed = urlparse(base_url)
            # MISP exposes HTTP on port 80 but its REST API requires HTTPS on
            # port 443 (port 80 just redirects). Rewrite internal MISP URLs to
            # HTTPS so POST requests such as /events/restSearch work directly.
            if parsed.hostname in (SERVICE_MISP, "soar_misp") and parsed.port == 80:
                parsed = parsed._replace(scheme="https", netloc=f"{parsed.hostname}:443")
                return urlunparse(parsed), api_key
            if parsed.hostname != "localhost":
                return base_url, api_key
            port = parsed.port
            if port is None:
                return base_url, api_key
            mapping = _DOCKER_HOST_MAP.get(port)
            if not mapping:
                return base_url, api_key
            netloc, key_name = mapping
            scheme = "https" if port == 8083 else (parsed.scheme or "http")
            parsed = parsed._replace(scheme=scheme, netloc=netloc)
            base_url = urlunparse(parsed)
            if key_name and (not api_key or api_key == _TEST_KEY_PLACEHOLDER):
                api_key = self._load_env_key(key_name)
        except Exception as _e:
            logger.debug("Docker host resolution failed: %s", _e)
        return base_url, api_key

    def _load_env_key(self, key_name: str) -> str | None:
        """Load a real API key from Settings or environment variables."""
        try:
            from soar_lab.config.settings import Settings

            settings = Settings()
            value = settings.get(key_name)
            if value:
                return str(value)
        except Exception as _e:
            logger.debug("Could not load env key %s: %s", key_name, _e)
        return os.environ.get(key_name.upper())

    def _url(self, path: str) -> str:
        """Join the base URL with a path, stripping leading slashes.

        Args:
            path: Relative path to append to base_url.

        Returns:
            str: Fully-qualified URL.
        """
        return f"{self.base_url}/{path.lstrip('/')}"

    def _trace_headers(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build headers with trace ID propagation if a request scope is active.

        Args:
            extra: Optional pre-existing headers to merge into.

        Returns:
            dict: Headers dict with ``X-Request-ID`` set when a trace ID
            is available in the current context.
        """
        headers: dict[str, Any] = dict(extra) if extra else {}
        trace_id = _current_trace_id()
        if trace_id is not None and _TRACE_ID_HEADER not in headers:
            headers[_TRACE_ID_HEADER] = trace_id
        return headers

    def get(self, path: str, **kwargs: Any) -> Any:
        """Perform a GET request.

        Args:
            path: Relative path under ``base_url``.
            **kwargs: Extra keyword arguments forwarded to ``requests.get``.

        Returns:
            Any: Parsed JSON response, or ``{}`` if empty.

        Raises:
            IntegrationError: On HTTP or connection error.
        """

        def _do_get() -> Any:
            """Execute the actual GET request through the circuit breaker."""
            url = self._url(path)
            # Suppress Content-Type for GET requests: TheHive 3.5 rejects GET
            # requests that carry Content-Type: application/json with no body
            # ("Invalid Json: No content to map due to end-of-input").  Setting
            # the header to None tells requests to omit it from the final
            # request headers (popping from a copy is insufficient because
            # requests merges session headers with per-request headers).
            session_headers: dict[str, Any] = dict(self._session.headers)
            session_headers[HEADER_CONTENT_TYPE] = None
            session_headers["Accept"] = "*/*"
            # Merge any caller-provided headers from kwargs
            caller_headers = kwargs.pop("headers", None)
            if caller_headers:
                session_headers.update(caller_headers)
            session_headers = self._trace_headers(session_headers)
            try:
                resp = self._session.get(
                    url, timeout=self.timeout, headers=session_headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_get)

    def post(self, path: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Perform a POST request.

        Args:
            path: Relative path under ``base_url``.
            data: Optional JSON body dict to send.
            **kwargs: Extra keyword arguments forwarded to ``requests.post``.

        Returns:
            Any: Parsed JSON response, or ``{}`` if empty.

        Raises:
            IntegrationError: On HTTP or connection error.
        """

        def _do_post() -> Any:
            """Execute the actual POST request through the circuit breaker."""
            url = self._url(path)
            # Merge trace headers with any caller-provided headers
            caller_headers = kwargs.pop("headers", None)
            trace_headers = self._trace_headers(caller_headers)
            try:
                resp = self._session.post(
                    url, json=data, timeout=self.timeout, headers=trace_headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_post)

    def put(self, path: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Perform a PUT request.

        Args:
            path: Relative path under ``base_url``.
            data: Optional JSON body dict to send.
            **kwargs: Extra keyword arguments forwarded to ``requests.put``.

        Returns:
            Any: Parsed JSON response, or ``{}`` if empty.

        Raises:
            IntegrationError: On HTTP or connection error.
        """

        def _do_put() -> Any:
            """Execute the actual PUT request through the circuit breaker."""
            url = self._url(path)
            caller_headers = kwargs.pop("headers", None)
            trace_headers = self._trace_headers(caller_headers)
            try:
                resp = self._session.put(
                    url, json=data, timeout=self.timeout, headers=trace_headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_put)

    def patch(self, path: str, data: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Perform a PATCH request.

        Args:
            path: Relative path under ``base_url``.
            data: Optional JSON body dict to send.
            **kwargs: Extra keyword arguments forwarded to ``requests.patch``.

        Returns:
            dict: Parsed JSON response, or ``{}`` if empty.

        Raises:
            IntegrationError: On HTTP or connection error.
        """

        def _do_patch() -> dict[str, Any]:
            """Execute the actual PATCH request through the circuit breaker."""
            url = self._url(path)
            caller_headers = kwargs.pop("headers", None)
            trace_headers = self._trace_headers(caller_headers)
            try:
                resp = self._session.patch(
                    url, json=data, timeout=self.timeout, headers=trace_headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return dict(self.circuit_breaker.call(_do_patch))

    def delete(self, path: str, **kwargs: Any) -> Any:
        """Perform a DELETE request.

        Args:
            path: Relative path under ``base_url``.
            **kwargs: Extra keyword arguments forwarded to ``requests.delete``.

        Returns:
            Any: Parsed JSON response, or ``{}`` if empty.

        Raises:
            IntegrationError: On HTTP or connection error.
        """

        def _do_delete() -> Any:
            """Execute the actual DELETE request through the circuit.

            breaker.
            """
            url = self._url(path)
            caller_headers = kwargs.pop("headers", None)
            trace_headers = self._trace_headers(caller_headers)
            try:
                resp = self._session.delete(
                    url, timeout=self.timeout, headers=trace_headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.HTTPError as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
            except requests.RequestException as exc:
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc

        return self.circuit_breaker.call(_do_delete)

    def health_check(self) -> bool:
        """Return True if the service responds to a health endpoint.

        Returns:
            bool: True if ``base_url`` responds, False on any error.
        """
        try:
            self._session.get(self.base_url, timeout=self.timeout)
            return True
        except Exception:
            return False
