"""Shuffle client helpers for session management and app installation.

This module provides the session- and client-level utilities used by
``init_shuffle_webhook.py`` to interact with the Shuffle backend API.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

from . import config

logger = logging.getLogger(__name__)

# Default timeout for Shuffle API calls (seconds)
_DEFAULT_TIMEOUT = 30

# Apps that the workflow depends on — name → search keyword
_REQUIRED_APPS: dict[str, str] = {
    "http": "http",
    "Shuffle Tools": "Shuffle Tools",
}


def get_shuffle_client_class() -> type:
    """Return the ShuffleClient class used for test patching.

    In production this returns a simple wrapper class that encapsulates
    the session-based API calls.  Integration tests patch this function
    via ``patch("scripts.setup.init_shuffle_webhook.ShuffleClient")``.
    """
    return _ShuffleClient


class _ShuffleClient:
    """Minimal Shuffle client for backward compatibility with tests.

    The real setup logic uses the functional helpers below
    (``create_shuffle_session``, ``wait_for_shuffle_ready``, etc.). This
    class exists so that ``test_init_shuffle_webhook.py`` can patch
    ``ShuffleClient`` and inject a mock.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.session: requests.Session | None = None
        self.api_key: str = ""

    # The methods below mirror the old class-based API that tests expect.
    def create_workflow(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Use shuffle_setup.create_workflow instead")

    def create_trigger(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError("Use shuffle_setup.create_webhook_trigger instead")

    def get_api_key(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use validate_api_key instead")

    def get_org_id(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use shuffle_setup.ensure_shuffle_environment instead")


def create_shuffle_session() -> requests.Session:
    """Create an authenticated ``requests.Session`` for the Shuffle backend.

    Reads credentials from ``config.SHUFFLE_USER`` /
    ``config.SHUFFLE_PASS`` and logs in via ``POST
    /api/v1/users/login``.
    """
    session = requests.Session()
    session.verify = False
    session.headers.update({HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON})

    logger.info("Authenticating to Shuffle at %s ...", config.SHUFFLE_URL)
    login_resp = session.post(
        f"{config.SHUFFLE_URL}/api/v1/users/login",
        json={"username": config.SHUFFLE_USER, "password": config.SHUFFLE_PASS},
        timeout=_DEFAULT_TIMEOUT,
    )
    login_resp.raise_for_status()
    api_key = login_resp.json().get("api_key", "")
    if api_key:
        session.headers.update({HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {api_key}"})
    return session


def wait_for_shuffle_ready(
    session: requests.Session,
    timeout: int = 120,
    interval: float = 5.0,
) -> None:
    """Poll the Shuffle health endpoint until it responds or timeout expires.

    Raises ``RuntimeError`` if Shuffle does not become ready within
    *timeout* seconds.
    """
    deadline = time.time() + timeout
    last_err: str = ""
    while time.time() < deadline:
        try:
            r = session.get(f"{config.SHUFFLE_URL}/api/v1/users/getinfo", timeout=10)
            if r.status_code == 200:
                logger.info("Shuffle is ready.")
                return
            last_err = f"HTTP {r.status_code}"
        except requests.RequestException as exc:
            last_err = str(exc)
        time.sleep(interval)
    raise RuntimeError(f"Shuffle not ready within {timeout}s: {last_err}")


def validate_api_key(session: requests.Session) -> str:
    """Validate that the session has a working API key.

    First checks whether the Bearer token already present in the session
    works (``GET /api/v1/workflows``).  If it does, the existing key is
    returned **without** calling ``generateapikey``, which would create a
    new random key and desynchronize the DB from ``.env.full``.

    Only when the existing token is missing or rejected does this function
    fall back to ``GET /api/v1/users/generateapikey``.

    Raises ``RuntimeError`` if the key is missing.
    """
    # Fast path: if the session already has a Bearer token, probe it.
    _current = session.headers.get(HEADER_AUTHORIZATION, "")
    if _current:
        try:
            _probe = session.get(
                f"{config.SHUFFLE_URL}/api/v1/workflows",
                timeout=_DEFAULT_TIMEOUT,
            )
            if _probe.status_code == 200:
                _existing = _current.replace(f"{AUTH_BEARER_PREFIX} ", "")
                logger.debug(
                    "validate_api_key: existing Bearer token works"
                    " — not generating a new one"
                )
                return _existing
        except Exception as exc:
            logger.debug(
                "validate_api_key: probe failed (%s) — falling back to generateapikey",
                exc,
            )

    # Fallback: generate a new apikey (this rotates the key in the DB).
    r = session.get(f"{config.SHUFFLE_URL}/api/v1/users/generateapikey", timeout=_DEFAULT_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    api_key = data.get("apikey", data.get("api_key", ""))
    if not api_key:
        raise RuntimeError("Shuffle API key is empty after login.")
    session.headers.update({HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {api_key}"})
    logger.warning(
        "validate_api_key: generated a NEW apikey (%s...) — "
        "run es_fixes.sync_apikey() to keep .env.full in sync",
        api_key[-8:],
    )
    return api_key


def get_app_ids(
    session: requests.Session,
    shuffle_url: str | None = None,
) -> dict[str, str]:
    """Download required official apps and return ``{app_name: app_id}``.

    The workflow depends on at least the *http* app and *Shuffle Tools*.
    If an app is already installed, its existing ID is reused.
    """
    base = shuffle_url or config.SHUFFLE_URL
    r = session.get(f"{base}/api/v1/apps", timeout=_DEFAULT_TIMEOUT)
    r.raise_for_status()
    installed = {a.get("name", ""): a.get("id", "") for a in r.json()}

    app_ids: dict[str, str] = {}
    for app_name, search_kw in _REQUIRED_APPS.items():
        app_id = installed.get(app_name, "")
        if not app_id:
            # Try to download the app from the Shuffle app store
            logger.info("Installing app '%s' ...", app_name)
            search = session.get(
                f"{base}/api/v1/apps/search/{search_kw}",
                timeout=_DEFAULT_TIMEOUT,
            )
            if search.status_code == 200:
                results = search.json()
                if isinstance(results, list) and results:
                    app_data = results[0]
                    download = session.post(
                        f"{base}/api/v1/apps/install",
                        json=app_data,
                        timeout=120,
                    )
                    if download.status_code == 200:
                        app_id = download.json().get("id", "")
        if app_id:
            app_ids[app_name] = app_id
        else:
            logger.warning("Could not obtain app_id for '%s'", app_name)
    return app_ids
