"""Surgical GC of zombie Shuffle executions (RES-01).

When a Shuffle workflow is interrupted (test failure, container restart,
Orborus crash) its ``workflowexecution`` document stays ``EXECUTING``
forever — Orborus keeps polling it, burns worker slots and eventually
throttles legitimate executions. ``make clean-shuffle`` fixes this but is
a *nuclear* operation (purges every non-FINISHED doc and force-removes
worker containers).

This collector performs the surgical version instead: only executions
whose ``EXECUTING`` status is older than ``stale_minutes`` (default 30,
conservative — nothing legitimate exceeds the workflow timeout) are
marked ``ABORTED`` in OpenSearch and best-effort aborted through the
Shuffle REST API. The execution record is preserved for audit.
"""

from __future__ import annotations

import time
from typing import Any

import requests
import urllib3

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EXECUTION_INDEX = "workflowexecution"
DEFAULT_STALE_MINUTES = 30
_MAX_STALE_PER_PASS = 500


class StaleExecutionGC:
    """Marks stale ``EXECUTING`` Shuffle executions as ``ABORTED``.

    Parameters
    ----------
    os_url : str
        OpenSearch base URL hosting the ``workflowexecution-*`` index.
    backend_url : str
        Shuffle backend base URL for the abort API call.
    api_key : str
        Shuffle API key (``Authorization: Bearer``).
    stale_minutes : float
        Age threshold — EXECUTING docs older than this are zombies.
    http : Any
        requests-compatible module/session (injectable for tests).
    """

    def __init__(
        self,
        os_url: str,
        backend_url: str,
        api_key: str,
        stale_minutes: float = DEFAULT_STALE_MINUTES,
        http: Any = None,
    ) -> None:
        self._os_url = os_url.rstrip("/")
        self._backend_url = backend_url.rstrip("/")
        self._api_key = api_key
        self._stale_s = stale_minutes * 60
        self._http = http if http is not None else requests

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def find_stale(self, *, now: float | None = None) -> list[dict[str, Any]]:
        """Return ``EXECUTING`` docs older than the stale threshold.

        Each entry: ``{"doc_id", "execution_id", "started_at"}``.
        Missing index or empty result yields ``[]``.
        """
        cutoff = (now if now is not None else time.time()) - self._stale_s
        body = {
            "size": _MAX_STALE_PER_PASS,
            "_source": ["execution_id", "started_at", "status"],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"status": "EXECUTING"}},
                        {"range": {"started_at": {"lt": int(cutoff)}}},
                    ]
                }
            },
        }
        try:
            r = self._http.post(
                f"{self._os_url}/{EXECUTION_INDEX}/_search",
                json=body,
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                timeout=30,
                verify=False,
            )
        except Exception as exc:
            logger.warning("Stale-exec search failed: %s", exc)
            return []
        if r.status_code == 404:
            return []
        if r.status_code != 200:
            logger.warning("Stale-exec search HTTP %s", r.status_code)
            return []
        try:
            hits = (r.json() or {}).get("hits", {}).get("hits", [])
        except Exception as exc:
            # A 200 with a non-JSON body (proxy splash, truncated reply) is
            # transport noise — never raises means this degrades to [] too.
            logger.warning("Stale-exec search malformed body: %s", exc)
            return []
        stale = []
        for h in hits:
            src = h.get("_source") or {}
            stale.append(
                {
                    "doc_id": h.get("_id"),
                    "execution_id": src.get("execution_id"),
                    "started_at": src.get("started_at"),
                }
            )
        return stale

    # ------------------------------------------------------------------
    # Remediation
    # ------------------------------------------------------------------

    def mark_aborted(self, doc_ids: list[str]) -> int:
        """Set ``status=ABORTED`` on the given OpenSearch docs.

        Returns the number of documents updated. The doc is preserved —
        unlike ``clean-shuffle``'s delete — so the audit trail survives.
        """
        if not doc_ids:
            return 0
        body = {
            "query": {"ids": {"values": doc_ids}},
            "script": {
                "source": "ctx._source.status = params.status",
                "params": {"status": "ABORTED"},
            },
        }
        try:
            r = self._http.post(
                f"{self._os_url}/{EXECUTION_INDEX}/_update_by_query",
                json=body,
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                timeout=30,
                verify=False,
            )
            if r.status_code != 200:
                logger.warning("Stale-exec mark HTTP %s", r.status_code)
                return 0
            return int((r.json() or {}).get("updated", 0))
        except Exception as exc:
            logger.warning("Stale-exec mark failed: %s", exc)
            return 0

    def _api_abort(self, execution_id: str) -> bool:
        """Best-effort ``DELETE /api/v1/executions/<id>`` on Shuffle.

        2xx or 404 (already gone) count as success — the goal is freeing
        the Orborus worker slot either way.
        """
        try:
            r = self._http.delete(
                f"{self._backend_url}/api/v1/executions/{execution_id}",
                headers={HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {self._api_key}"},
                timeout=15,
            )
            return r.status_code in (200, 201, 202, 204, 404)
        except Exception:
            return False

    def collect_once(self, *, now: float | None = None) -> dict[str, Any]:
        """One GC pass: find stale execs → abort via API → mark ABORTED.

        Returns a summary dict ``{stale, marked_aborted, api_aborted,
        api_failed}``; never raises — the periodic task must not die on a
        transient OpenSearch/Shuffle outage.
        """
        stale = self.find_stale(now=now)
        if not stale:
            return {"stale": 0, "marked_aborted": 0, "api_aborted": 0, "api_failed": 0}

        api_aborted = 0
        api_failed = 0
        doc_ids: list[str] = []
        for entry in stale:
            eid = entry.get("execution_id")
            if eid and self._api_abort(eid):
                api_aborted += 1
            else:
                api_failed += 1
            if entry.get("doc_id"):
                doc_ids.append(entry["doc_id"])

        marked = self.mark_aborted(doc_ids)
        if marked or api_aborted:
            logger.info(
                "Stale-exec GC: stale=%d marked_aborted=%d api_aborted=%d api_failed=%d",
                len(stale),
                marked,
                api_aborted,
                api_failed,
            )
        return {
            "stale": len(stale),
            "marked_aborted": marked,
            "api_aborted": api_aborted,
            "api_failed": api_failed,
        }
