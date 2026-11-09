"""HTTP Client - Infrastructure implementation of the async HTTPClient port.

Single-stack HTTP: the project's only transport implementation is
``requests`` (see ``integrations/base_client.py`` for the sync client).
This adapter exposes an *async* facade over a pooled ``requests.Session``
via ``asyncio.to_thread`` so async consumers (health checks inside the
event loop) share the same transport instead of carrying a parallel
aiohttp stack.
"""

import asyncio
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from soar_lab.config.logging import get_logger

__all__ = ["AioHTTPClient"]

logger = get_logger(__name__)

_POOL_CONNECTIONS = 4
_POOL_MAXSIZE = 4

# requests accepts bool | str for verify (CA bundle path for internal
# lab-CA services — GRAF-D10).
VerifySSL = bool | str


class AioHTTPClient:
    """Async facade over a pooled ``requests.Session``.

    Sessions are pooled per verify-SSL mode: reusing one Session keeps the
    connection pool alive across requests instead of paying a fresh
    TCP+TLS handshake per call. Blocking calls run through
    ``asyncio.to_thread`` so they never stall the event loop. Call
    ``close()`` at application shutdown (the API wires it into the
    FastAPI shutdown hook).
    """

    def __init__(self, default_timeout: int = 5, default_verify_ssl: VerifySSL = True) -> None:
        """Initialize the HTTP client.

        Args:
            default_timeout: Default request timeout in seconds
            default_verify_ssl: Default SSL verification setting — bool
                or a CA bundle path (``requests.verify`` contract)
        """
        self.default_timeout = default_timeout
        self.default_verify_ssl = default_verify_ssl
        self._sessions: dict[VerifySSL, requests.Session] = {}

    def _pooled_session(self, verify_ssl: VerifySSL) -> requests.Session:
        """Return the pooled session for this SSL mode, creating it lazily."""
        session = self._sessions.get(verify_ssl)
        if session is None:
            session = requests.Session()
            session.verify = verify_ssl
            adapter = HTTPAdapter(pool_connections=_POOL_CONNECTIONS, pool_maxsize=_POOL_MAXSIZE)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            self._sessions[verify_ssl] = session
        return session

    async def _session(self, verify_ssl: VerifySSL) -> requests.Session:
        """Return the pooled session (async-compat accessor).

        Kept for backwards compatibility with callers that ``await``
        the session getter.
        """
        return self._pooled_session(verify_ssl)

    async def close(self) -> None:
        """Close all pooled sessions (call at application shutdown)."""
        sessions = list(self._sessions.values())
        self._sessions.clear()

        def _close_all() -> None:
            for session in sessions:
                session.close()

        await asyncio.to_thread(_close_all)

    def _resolve_timeout(self, timeout: float | None) -> float | None:
        """BL-HTTP-005: disambiguate the timeout contract.

        ``None`` (or omitted) means "use the configured default"; ``0``
        or a negative value explicitly disables the timeout
        (``requests`` treats ``timeout=None`` as no timeout) instead of
        being silently coerced to the default by truthiness.
        """
        if timeout is None:
            return self.default_timeout
        if timeout <= 0:
            return None
        return timeout

    def _do_get(self, url: str, timeout: float | None, verify_ssl: VerifySSL) -> requests.Response:
        """Blocking GET — runs in a worker thread via ``asyncio.to_thread``."""
        return self._pooled_session(verify_ssl).get(
            url,
            allow_redirects=True,
            timeout=self._resolve_timeout(timeout),
        )

    async def get(self, url: str, timeout: float | None = None, verify_ssl: VerifySSL = True) -> int:
        """Perform a GET request and return status code.

        Args:
            url: URL to request
            timeout: Request timeout in seconds; ``None`` uses the
                default, ``0``/negative disables the timeout
            verify_ssl: ``True``/``False`` or a CA bundle path to pin

        Returns:
            HTTP status code
        """
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl

        try:
            resp = await asyncio.to_thread(self._do_get, url, timeout, effective_verify_ssl)
            return resp.status_code
        except Exception:
            logger.exception(f"HTTP GET request failed for {url}")
            raise

    async def get_json(
        self, url: str, timeout: float | None = None, verify_ssl: VerifySSL = True
    ) -> dict[str, Any]:
        """Perform a GET request and return JSON response.

        Args:
            url: URL to request
            timeout: Request timeout in seconds; ``None`` uses the
                default, ``0``/negative disables the timeout
            verify_ssl: ``True``/``False`` or a CA bundle path to pin

        Returns:
            JSON response as dict
        """
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl

        try:
            resp = await asyncio.to_thread(self._do_get, url, timeout, effective_verify_ssl)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception(f"HTTP GET JSON request failed for {url}")
            raise

    def _do_post(
        self,
        url: str,
        payload: dict[str, Any] | None,
        headers: dict[str, str] | None,
        timeout: float | None,
        verify_ssl: VerifySSL,
    ) -> requests.Response:
        """Blocking POST — runs in a worker thread via ``asyncio.to_thread``."""
        return self._pooled_session(verify_ssl).post(
            url,
            json=payload,
            headers=headers,
            timeout=self._resolve_timeout(timeout),
        )

    async def post_json(
        self,
        url: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        verify_ssl: VerifySSL = True,
    ) -> tuple[int, dict[str, Any]]:
        """Perform a POST request and return ``(status_code, body)``.

        Unlike :meth:`get_json` this does NOT raise on non-2xx — callers
        that treat HTTP status as a result (webhook forwarding) need the
        status code itself, not an exception. A non-JSON body yields
        ``{}``. Transport errors still propagate as exceptions.
        """
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.default_verify_ssl
        resp = await asyncio.to_thread(
            self._do_post, url, payload, headers, timeout, effective_verify_ssl
        )
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp.status_code, body if isinstance(body, dict) else {}
