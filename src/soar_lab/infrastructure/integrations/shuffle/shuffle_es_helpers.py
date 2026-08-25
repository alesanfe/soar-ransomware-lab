#!/usr/bin/env python3
"""Elasticsearch / OpenSearch helper functions for the Shuffle SOAR client.

These utilities handle direct queries against Shuffle's internal
OpenSearch datastore (the ``workflowexecution-000001`` index) so the
client can bypass the Shuffle API's 100-entry execution-history cap.
Credential resolution for that datastore lives here too.  They are split
out of ``shuffle_helpers.py`` to keep each module focused and its
maintainability index high.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from soar_lab.common.constants import (
    DEFAULT_OPENSEARCH_HOST_URL,
    DEFAULT_OPENSEARCH_URL,
    DEFAULT_SHUFFLE_PROBE_TIMEOUT,
    SHUFFLE_EXECUTION_INDEX,
)
from soar_lab.config.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient

logger = get_logger(__name__)

# OpenSearch index that stores every Shuffle workflow execution.
_EXECUTION_INDEX = SHUFFLE_EXECUTION_INDEX


def read_env_credentials() -> tuple[str, str, str]:
    """Read OpenSearch URL/username/password from env vars and ``.env.full``.

    The lookup checks process environment variables first, then falls back to
    a ``.env.full`` file in the working directory or the repository root.

    Returns:
        A ``(url, username, password)`` tuple; entries are empty strings when
        the corresponding value is not found.
    """
    es_url = os.environ.get("SHUFFLE_OPENSEARCH_URL", "")
    es_user = os.environ.get(
        "SHUFFLE_OPENSEARCH_USERNAME", os.environ.get("OPENSEARCH_USERNAME", "")
    )
    es_pass = os.environ.get(
        "SHUFFLE_OPENSEARCH_PASSWORD", os.environ.get("OPENSEARCH_PASSWORD", "")
    )

    env_files = [Path(".env.full"), Path(__file__).parent.parent.parent.parent / ".env.full"]
    key_map = {
        "SHUFFLE_OPENSEARCH_URL": "url",
        "OPENSEARCH_USERNAME": "user",
        "OPENSEARCH_PASSWORD": "pass",  # nosec B105  # key name, not a secret
        "SHUFFLE_OPENSEARCH_USERNAME": "user",
        "SHUFFLE_OPENSEARCH_PASSWORD": "pass",  # nosec B105  # key name, not a secret
    }
    for env_file in env_files:
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            target = key_map.get(key.strip())
            if not target:
                continue
            val = val.strip()
            if target == "url" and not es_url:
                es_url = val
            elif target == "user" and not es_user:
                es_user = val
            elif target == "pass" and not es_pass:
                es_pass = val
    return es_url, es_user, es_pass


def get_es_connection() -> tuple[str, tuple[str, str] | None, bool]:
    """Resolve the OpenSearch URL and credentials for Shuffle's internal.

    datastore.

    Shuffle stores workflow executions, users and hooks in its own OpenSearch
    index (``workflowexecution-000001``), separate from the project's
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
    return es_url, auth, False


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
    try:
        es_url, auth, verify = get_es_connection()
        source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
        if include_results:
            source.append("results")
        query: dict[str, Any] = {
            "query": {"terms": {"execution_id": [execution_id]}},
            "sort": [{"started_at": {"order": "desc"}}],
            "size": 1,
            "_source": source,
        }
        resp = requests.get(
            f"{es_url}/{_EXECUTION_INDEX}/_search",
            json=query,
            auth=auth,
            timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT,
            verify=verify,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            return dict(hits[0].get("_source", {}))
    except Exception as exc:
        logger.debug("get_execution ES lookup failed: %s", exc)
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
    try:
        es_url, auth, verify = get_es_connection()
        must: list[dict[str, Any]] = [{"term": {"workflow_id": workflow_id}}]
        if execution_ids:
            must.append({"terms": {"execution_id": execution_ids}})
        if execution_ids:
            source = [
                "execution_id",
                "status",
                "workflow_id",
                "results",
                "started_at",
                "completed_at",
            ]
        else:
            source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
        query: dict[str, Any] = {
            "query": {"bool": {"must": must}},
            "sort": [{"started_at": {"order": "desc"}}],
            "size": len(execution_ids) if execution_ids else 1000,
            "_source": source,
        }
        resp = requests.get(
            f"{es_url}/{_EXECUTION_INDEX}/_search",
            json=query,
            auth=auth,
            timeout=DEFAULT_SHUFFLE_PROBE_TIMEOUT,
            verify=verify,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            return [hit["_source"] for hit in hits]
    except Exception as exc:
        logger.debug("ES execution lookup failed: %s", exc)
    return None
