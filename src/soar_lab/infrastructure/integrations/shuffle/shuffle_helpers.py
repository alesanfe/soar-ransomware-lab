#!/usr/bin/env python3
"""Helper functions for the Shuffle SOAR client.

These utilities handle password resolution, apikey healing, keepalive
bookkeeping and execution-lookup fallbacks.  They are kept out of
``client.py`` so the public :class:`ShuffleClient` API stays focused and
the module maintainability index stays high.

The Elasticsearch/OpenSearch-specific helpers (credential resolution and
direct datastore queries) live in :mod:`shuffle_es_helpers` and are re-
exported here so the public API of this module stays unchanged.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    DEFAULT_SHUFFLE_POOL_SIZE,
    DEFAULT_SHUFFLE_PROBE_TIMEOUT,
    DEFAULT_SHUFFLE_QUICK_TIMEOUT,
    DEFAULT_SHUFFLE_TIMEOUT,
    DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT,
    DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT,
    HEADER_AUTHORIZATION,
)
from soar_lab.common.exceptions import IntegrationError
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers import (
    _EXECUTION_INDEX,
    es_lookup_execution,
    es_workflow_executions,
    get_es_connection,
    read_env_credentials,
)

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient

logger = get_logger(__name__)


def load_password() -> str:
    """Read ``SHUFFLE_DEFAULT_PASSWORD`` from the environment or ``.env.full``.

    Returns:
        The password string, or an empty string when it cannot be resolved.
    """
    pw = os.environ.get("SHUFFLE_DEFAULT_PASSWORD", "")
    if pw:
        return pw
    try:
        candidates = (Path(".env.full"), Path(__file__).parent.parent.parent.parent / ".env.full")
        for env_file in candidates:
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    if "SHUFFLE_DEFAULT_PASSWORD" in line and "=" in line:
                        return line.split("=", 1)[1].strip()
    except Exception as exc:
        logger.debug("Could not load Shuffle password: %s", exc)
    return ""


def do_login(client: ShuffleClient) -> bool:
    """POST ``/api/v1/login`` once for the given client.

    Args:
        client: The :class:`ShuffleClient` whose session should be warmed.

    Returns:
        ``True`` when the login responds with HTTP 200, ``False`` otherwise.
    """
    username = os.environ.get("SHUFFLE_DEFAULT_USERNAME", "admin")
    password = load_password()
    if not (username and password):
        return False
    try:
        resp = requests.post(
            client._url("/api/v1/login"),
            json={"username": username, "password": password},
            timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT,
            verify=client._session.verify,
        )
        logger.debug("Shuffle login: HTTP %s", resp.status_code)
        return resp.status_code == 200
    except Exception as exc:
        logger.debug("Shuffle login error: %s", exc)
        return False


def set_org_id_header(client: ShuffleClient) -> None:
    """Read ``active_org.id`` from OpenSearch and set it as the ``Org-Id``.

    header.

    Shuffle's Bearer-token auth flow looks up the org_id from the
    request (via the ``Org-Id`` header, or else the user's
    ``active_org``).  When its in-memory cache is cold it re-reads the
    user from ES, then verifies org membership.  Sending an explicit
    ``Org-Id`` header bypasses the org-inference and makes the
    membership check deterministic.

    """
    if client._session.headers.get("Org-Id"):
        return
    try:
        es_url, auth, verify = get_es_connection()
        resp = requests.get(
            f"{es_url}/users/_search",
            auth=auth,
            timeout=DEFAULT_SHUFFLE_QUICK_TIMEOUT,
            verify=verify,
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                org_id = hits[0]["_source"].get("active_org", {}).get("id", "")
                if org_id:
                    client._session.headers["Org-Id"] = org_id
                    logger.debug("Shuffle Org-Id header set from OpenSearch: %s", org_id)
    except Exception as exc:
        logger.debug("Could not set Org-Id header: %s", exc)


def fetch_real_apikey() -> str:
    """Return the real apikey from OpenSearch (the Shuffle API redacts it).

    Reads the active user's apikey directly from the OpenSearch users index
    and falls back gracefully to an empty string when OpenSearch is not
    accessible.

    Returns:
        The apikey string, or ``""`` when it cannot be retrieved.
    """
    try:
        es_url, auth, verify = get_es_connection()
        resp = requests.get(
            f"{es_url}/users/_search?size=1",
            auth=auth,
            timeout=DEFAULT_SHUFFLE_QUICK_TIMEOUT,
            verify=verify,
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                key = hits[0]["_source"].get("apikey", "")
                if key:
                    logger.debug("fetch_real_apikey from OpenSearch: %s...", str(key)[:8])
                    return str(key)
    except Exception as exc:
        logger.debug("fetch_real_apikey error: %s", exc)
    return ""


def warm_cache(client: ShuffleClient) -> None:
    """Heal a stale apikey, set the Org-Id header, then confirm the Bearer.

    token.

    Args:
        client: The :class:`ShuffleClient` whose auth cache should be warmed.
    """
    set_org_id_header(client)

    # Detect stale apikey: try Bearer GET first.
    bearer_ok = False
    try:
        probe = client._session.get(
            client._url("/api/v1/workflows"), timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT
        )
        bearer_ok = probe.status_code == 200
    except Exception as exc:
        logger.debug("Bearer token probe failed: %s", exc)

    if not bearer_ok:
        # Bearer token is stale; fetch the real apikey via login+session.
        real_key = fetch_real_apikey()
        current = client._session.headers.get(HEADER_AUTHORIZATION, "").replace(
            f"{AUTH_BEARER_PREFIX} ", ""
        )
        if real_key and real_key != current:
            logger.debug(
                "Shuffle apikey healed from %s... to %s...",
                client._session.headers.get(HEADER_AUTHORIZATION, "")[-8:],
                real_key[-8:],
            )
            client._session.headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX} {real_key}"
        # One login to warm the in-memory cache for the (now correct) apikey.
        do_login(client)
        # Confirm the healed token works.
        try:
            confirm = client._session.get(
                client._url("/api/v1/workflows"), timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT
            )
            logger.debug("Shuffle auth after apikey heal: HTTP %s", confirm.status_code)
        except Exception as exc:
            logger.debug("Warm cache confirmation failed: %s", exc)


def keepalive_loop(
    client: ShuffleClient,
    stop_event: threading.Event,
    interval: int = 25,
) -> None:
    """Background loop that keeps Shuffle's in-memory user cache alive.

    Args:
        client: The :class:`ShuffleClient` whose session should be pinged.
        stop_event: Event that, when set, terminates the loop.
        interval: Seconds between keepalive pings.
    """
    while not stop_event.wait(interval):
        try:
            client._session.get(
                client._url("/api/v1/workflows"), timeout=DEFAULT_SHUFFLE_QUICK_TIMEOUT
            )
        except Exception as exc:
            logger.debug("Keepalive request failed: %s", exc)


def match_execution(data: Any, execution_id: str) -> dict[str, Any] | None:
    """Extract a matching execution dict from an API response, or ``None``.

    Args:
        data: Raw API response (expected to be a dict, optionally wrapped in
            a ``{"data": ...}`` envelope).
        execution_id: The execution identifier to match against.

    Returns:
        The matched execution dict, or ``None`` when no match is found.
    """
    if not isinstance(data, dict):
        return None
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if execution_id not in (data.get("execution_id"), data.get("id")):
        return None
    return dict(data)


def api_lookup_execution(
    client: ShuffleClient, workflow_id: str, execution_id: str
) -> dict[str, Any] | None:
    """API fallback: try the direct execution endpoints in order.

    Args:
        client: The :class:`ShuffleClient` whose session should be used.
        workflow_id: Shuffle workflow UUID for the nested endpoint variant.
        execution_id: Execution UUID to retrieve.

    Returns:
        The matched execution dict (preferring one that carries ``results``),
        or ``None`` when no endpoint returns a match.
    """
    candidate: dict[str, Any] | None = None
    for path in (
        f"/api/v1/executions/{execution_id}",
        f"/api/v1/workflows/{workflow_id}/executions/{execution_id}",
    ):
        try:
            resp = client._session.get(client._url(path), timeout=client.timeout)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            matched = match_execution(data, execution_id)
            if matched:
                if matched.get("results") is not None:
                    return matched
                candidate = matched
        except requests.HTTPError:
            continue
        except Exception as exc:
            logger.debug("get_execution API fallback failed for %s: %s", path, exc)
            continue
    return candidate


def list_lookup_execution(
    client: ShuffleClient, workflow_id: str, execution_id: str
) -> dict[str, Any] | None:
    """Last resort: scan the workflow executions list for a matching ID.

    Args:
        client: The :class:`ShuffleClient` whose list endpoint should be queried.
        workflow_id: Shuffle workflow UUID to list executions for.
        execution_id: Execution UUID to find within the list.

    Returns:
        The matching execution dict, or ``None`` when not found.
    """
    try:
        executions = client.get_workflow_executions(workflow_id, execution_ids=[execution_id])
        for ex in executions:
            if isinstance(ex, dict) and execution_id in (ex.get("execution_id"), ex.get("id")):
                return ex
    except Exception as exc:
        logger.debug("get_execution list fallback failed: %s", exc)
    return None


def api_workflow_executions(
    client: ShuffleClient,
    workflow_id: str,
    retries: int,
    retry_delay: float,
) -> list[dict[str, Any]]:
    """Fetch workflow executions via the Shuffle API with simple retry logic.

    Args:
        client: The :class:`ShuffleClient` whose session should be used.
        workflow_id: Shuffle workflow UUID.
        retries: Number of retries on transient API errors.
        retry_delay: Seconds to wait between retries.

    Returns:
        List of execution dicts, or an empty list.

    Raises:
        IntegrationError: When the API request ultimately fails.
    """
    url = client._url(
        f"/api/v1/workflows/{workflow_id}/executions"
        f"?limit=DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT"
    )
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client._session.get(url, timeout=client.timeout)
            resp.raise_for_status()
            result = resp.json() if resp.content else []
            return result if isinstance(result, list) else []
        except requests.RequestException as exc:
            if attempt < retries:
                time.sleep(retry_delay)
                last_exc = exc
                continue
            raise IntegrationError(client.__class__.__name__, str(exc)) from exc
    if last_exc:
        raise IntegrationError(client.__class__.__name__, str(last_exc)) from last_exc
    return []


__all__ = [
    "DEFAULT_SHUFFLE_POOL_SIZE",
    "DEFAULT_SHUFFLE_PROBE_TIMEOUT",
    "DEFAULT_SHUFFLE_QUICK_TIMEOUT",
    "DEFAULT_SHUFFLE_TIMEOUT",
    "DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT",
    "DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT",
    "_EXECUTION_INDEX",
    "api_lookup_execution",
    "api_workflow_executions",
    "do_login",
    "es_lookup_execution",
    "es_workflow_executions",
    "fetch_real_apikey",
    "get_es_connection",
    "keepalive_loop",
    "list_lookup_execution",
    "load_password",
    "match_execution",
    "read_env_credentials",
    "set_org_id_header",
    "warm_cache",
]
