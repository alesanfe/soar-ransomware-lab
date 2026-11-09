#!/usr/bin/env python3
"""Elasticsearch / OpenSearch helper functions for the Shuffle SOAR client.

These utilities handle direct queries against Shuffle's internal
OpenSearch datastore (the ``workflowexecution`` index) so the
client can bypass the Shuffle API's 100-entry execution-history cap.
Credential resolution for that datastore lives here too.  They are split
out of ``shuffle_helpers.py`` to keep each module focused and its
maintainability index high.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
from requests.adapters import HTTPAdapter

from soar_lab.common.constants import (
    DEFAULT_OPENSEARCH_HOST_URL,
    DEFAULT_OPENSEARCH_URL,
    DEFAULT_SHUFFLE_PROBE_TIMEOUT,
    DEFAULT_SHUFFLE_QUICK_TIMEOUT,
    SHUFFLE_EXECUTION_INDEX,
)
from soar_lab.common.opensearch import id_terms_filter
from soar_lab.common.runtime import repo_root, resolve_secret
from soar_lab.common.trace_context import get_trace_id
from soar_lab.config.logging import get_logger
from soar_lab.security.tls_config import verify_tls

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient

logger = get_logger(__name__)

# OpenSearch index that stores every Shuffle workflow execution.
_EXECUTION_INDEX = SHUFFLE_EXECUTION_INDEX

# BL-HTTP-006: one pooled session for every OpenSearch datastore query —
# raw ``requests.get()`` created a fresh TCP(+TLS) handshake per call.
_ES_SESSION: requests.Session | None = None
_ES_SESSION_LOCK = threading.Lock()


def _es_session() -> requests.Session:
    """Return the shared pooled session for OpenSearch queries.

    Auth and TLS verification stay per-request (``auth=``/``verify=``
    kwargs) so one session safely serves every credential combination.
    The current request's trace ID is propagated per call (BL-HTTP-008).
    """
    global _ES_SESSION
    if _ES_SESSION is None:
        with _ES_SESSION_LOCK:
            if _ES_SESSION is None:

                session = requests.Session()
                adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8)
                # nosemgrep: request-session-with-http -- mount prefix, not a request
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                _ES_SESSION = session

    trace_id = get_trace_id()
    if trace_id:
        _ES_SESSION.headers["X-Request-ID"] = trace_id
    else:
        _ES_SESSION.headers.pop("X-Request-ID", None)
    return _ES_SESSION


def read_env_credentials() -> tuple[str, str, str]:
    """Read OpenSearch URL/username/password from env vars and ``.env.full``.

    Environment wins; the ``.env.full`` fallback resolves against the
    repository root (``common.runtime.repo_root()``, never the CWD) and
    parses strictly ``KEY=value`` per key — comments, partial names and
    quote-wrapped values handled by the shared ``dotenv_lookup``.

    Returns:
        A ``(url, username, password)`` tuple; entries are empty strings when
        the corresponding value is not found.
    """
    env_file = repo_root() / ".env.full"
    # Tiered resolution (env -> Docker secrets -> dotenv) via the central
    # resolver; the specific SHUFFLE_* names alias to the generic
    # OPENSEARCH_* ones within each tier.
    es_url = resolve_secret("SHUFFLE_OPENSEARCH_URL", env_file=env_file)
    es_user = resolve_secret(
        "SHUFFLE_OPENSEARCH_USERNAME", "OPENSEARCH_USERNAME", env_file=env_file
    )
    es_pass = resolve_secret(
        "SHUFFLE_OPENSEARCH_PASSWORD", "OPENSEARCH_PASSWORD", env_file=env_file
    )
    return es_url, es_user, es_pass


def get_es_connection() -> tuple[str, tuple[str, str] | None, bool]:
    """Resolve the OpenSearch URL and credentials for Shuffle's internal.

    datastore.

    Shuffle stores workflow executions, users and hooks in its own OpenSearch
    index (``workflowexecution``), separate from the project's
    Elasticsearch indices (``soar-alerts``, ``soar-metrics``).

    Returns:
    A ``(url, auth, verify_ssl)`` tuple where ``auth`` is a
    ``(user, pass)`` tuple or ``None`` when credentials are absent and
    ``verify_ssl`` is always ``False`` for the internal datastore.

    """
    es_url, es_user, es_pass = read_env_credentials()

    if not es_url:
        # Inside Docker the OpenSearch service is available as 'opensearch:9200';
        # on the host use the mapped port from .env.full or the standard default.
        in_docker = Path("/.dockerenv").exists()
        es_url = DEFAULT_OPENSEARCH_URL if in_docker else DEFAULT_OPENSEARCH_HOST_URL

    auth = (es_user, es_pass) if es_user and es_pass else None
    # The internal datastore ships a self-signed cert, so verification stays
    # off by default — but SHUFFLE_OPENSEARCH_VERIFY_TLS=1 now hardens it
    # without a code change (BL-SEC-004).

    return es_url, auth, verify_tls("shuffle-opensearch", default=False)


def _es_search(query: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Run a ``_search`` against the executions index and return raw hits.

    Shared transport for the two execution lookups — POST (not GET-with-
    body, which some proxies drop), pooled session, ``None`` on failure
    so callers can fall back to the Shuffle API.
    """
    try:
        es_url, auth, verify = get_es_connection()
        resp = _es_session().post(
            f"{es_url}/{_EXECUTION_INDEX}/_search",
            json=query,
            auth=auth,
            timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT,
            verify=verify,
        )
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])
    except Exception as exc:
        logger.debug("ES execution search failed: %s", exc)
        return None


def fetch_first_user_source() -> dict[str, Any] | None:
    """Return the first document in Shuffle's ``users`` index, or ``None``.

    Bounded to ``size=1`` — the callers only need the active user, so a
    naked ``_search`` (which fetches up to the index default of 10 and
    grows unbounded as users accumulate) wasted bandwidth per call.
    """
    try:
        es_url, auth, verify = get_es_connection()
        resp = _es_session().get(
            f"{es_url}/users/_search?size=1",
            auth=auth,
            timeout=DEFAULT_SHUFFLE_QUICK_TIMEOUT,
            verify=verify,
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                return dict(hits[0].get("_source", {}))
    except Exception as exc:
        logger.debug("users index lookup failed: %s", exc)
    return None


def es_lookup_execution(
    client: ShuffleClient, execution_id: str, include_results: bool
) -> dict[str, Any] | None:
    """Fast path: targeted OpenSearch query to avoid parsing the results blob.

    Args:
        client: The :class:`ShuffleClient` (reserved for logging context).
        execution_id: Execution UUID to look up.
        include_results: When ``True`` include the (potentially huge) ``results``
            field in the source projection.

    Returns:
        The matching execution dict, or ``None`` when not found in OpenSearch.
    """
    source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
    if include_results:
        source.append("results")
    query: dict[str, Any] = {
        "query": id_terms_filter("execution_id", [execution_id]),
        "sort": [{"started_at": {"order": "desc"}}],
        "size": 1,
        "_source": source,
    }
    hits = _es_search(query)
    if hits:
        return dict(hits[0].get("_source", {}))
    return None


def es_workflow_executions(
    workflow_id: str, execution_ids: list[str] | None = None
) -> list[dict[str, Any]] | None:
    """Query OpenSearch for a workflow's execution history.

    The Shuffle API caps execution history at 100 entries; OpenSearch keeps
    every execution.  Only the ``results`` blob is omitted unless the query is
    narrowed to specific execution IDs (fetching it for many executions can
    return multi-MB responses and hang the JSON decoder).

    Args:
        workflow_id: Shuffle workflow UUID to query.
        execution_ids: Optional list of execution IDs to restrict the query to.

    Returns:
        A list of execution dicts (most recent first), or ``None`` when
        OpenSearch is unavailable so the caller can fall back to the API.
    """
    must: list[dict[str, Any]] = [id_terms_filter("workflow_id", [workflow_id])]
    source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
    if execution_ids:
        must.append(id_terms_filter("execution_id", execution_ids))
        source.append("results")
    query: dict[str, Any] = {
        "query": {"bool": {"must": must}},
        "sort": [{"started_at": {"order": "desc"}}],
        "size": len(execution_ids) if execution_ids else 1000,
        "_source": source,
    }
    hits = _es_search(query)
    if hits:
        return [hit["_source"] for hit in hits]
    return None
