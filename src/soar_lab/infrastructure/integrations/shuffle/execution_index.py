"""OpenSearch-backed read adapter for Shuffle workflow executions (SOAR-01).

The Shuffle REST API does not reliably list executions for this stack
(org-scoped auth), but every execution is indexed in OpenSearch as a
``workflowexecution-*`` document containing the full per-node ``results``
array — including the ``calc_decision`` node output that carries the
verdict and its human-readable ``factors``. This adapter exposes that
index to the decision-explainer use case.
"""

from __future__ import annotations

from typing import Any

import requests
import urllib3

from soar_lab.common.constants import CONTENT_TYPE_JSON, HEADER_CONTENT_TYPE
from soar_lab.common.opensearch import id_terms_filter
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EXECUTION_INDEX = "workflowexecution*"


class ShuffleExecutionIndex:
    """Read-only access to Shuffle ``workflowexecution-*`` documents."""

    def __init__(self, os_url: str, http: Any = None) -> None:
        self._os_url = os_url.rstrip("/")
        self._http = http if http is not None else requests

    def _search(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            r = self._http.post(
                f"{self._os_url}/{EXECUTION_INDEX}/_search",
                json=body,
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                timeout=30,
                verify=False,
            )
        except Exception as exc:
            logger.warning("Execution-index search failed: %s", exc)
            return []
        if r.status_code != 200:
            logger.warning("Execution-index search HTTP %s", r.status_code)
            return []
        return (r.json() or {}).get("hits", {}).get("hits", [])

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        """Return the ``_source`` document for one execution, or None."""
        hits = self._search(
            {
                "size": 1,
                "query": id_terms_filter("execution_id", [execution_id]),
            }
        )
        return hits[0].get("_source") if hits else None

    def recent_executions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the ``limit`` most recent execution documents."""
        hits = self._search(
            {
                "size": max(1, min(limit, 100)),
                "sort": [{"started_at": {"order": "desc"}}],
                "query": {"match_all": {}},
            }
        )
        return [h.get("_source") or {} for h in hits]
