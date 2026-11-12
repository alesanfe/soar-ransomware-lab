"""Surgical GC of zombie Shuffle executions (RES-01 / TMO-001).

When a Shuffle workflow is interrupted (test failure, container restart,
Orborus crash) its ``workflowexecution`` document stays ``EXECUTING``
forever — Orborus keeps polling it, burns worker slots and eventually
throttles legitimate executions. ``make clean-shuffle`` fixes this but is
a *nuclear* operation (purges every non-FINISHED doc and force-removes
worker containers).

This collector drives a bounded state machine instead::

    EXECUTING --(age > stale_s)--> TIMED_OUT --(api abort)--> CANCELLING
    CANCELLING --(backend no longer executing)--> ABORTED        [terminal]
    CANCELLING --(max confirm attempts)--> ABORTED (forced=true) [terminal]

Every transition is a *conditional* scripted update: the document only
advances if its status still equals the expected previous state. A
late-arriving result that flips the doc to ``FINISHED`` between the scan
and the update makes the transition a no-op — the GC never clobbers a
workflow that actually completed. Timestamps (``timed_out_at``,
``cancel_requested_at``, ``aborted_at``) preserve the audit trail.

Metrics (exposed on ``GET /metrics`` via ``app.state.stale_gc``):

- ``soar_workflow_stuck_total``               counter
- ``soar_workflow_oldest_executing_seconds``  gauge
- ``soar_workflow_timeout_transitions_total`` counter by ``to_state``
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)
from soar_lab.config.logging import get_logger
from soar_lab.security.tls_config import ca_verify

logger = get_logger(__name__)

EXECUTION_INDEX = "workflowexecution"
DEFAULT_STALE_MINUTES = 30
_MAX_STALE_PER_PASS = 500
MAX_CONFIRM_ATTEMPTS = 5

TERMINAL_BACKEND_STATES = frozenset(
    {"FINISHED", "ABORTED", "FAILED", "STOPPED", "SKIPPED"}
)


@dataclass
class GCMetrics:
    """Cumulative counters + gauges for Prometheus exposition."""

    stuck_total: int = 0
    oldest_executing_seconds: float = 0.0
    transitions: dict[str, int] = field(default_factory=dict)
    last_pass: dict[str, Any] = field(default_factory=dict)

    def bump(self, to_state: str, n: int = 1) -> None:
        self.transitions[to_state] = self.transitions.get(to_state, 0) + n


class StaleExecutionGC:
    """Drives the EXECUTING→TIMED_OUT→CANCELLING→ABORTED state machine.

    Parameters
    ----------
    os_url : str
        OpenSearch base URL hosting the ``workflowexecution`` index.
    backend_url : str
        Shuffle backend base URL for the abort/status API calls.
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
        os_auth: tuple[str, str] | None = None,
        verify: bool | str | None = None,
    ) -> None:
        self._os_url = os_url.rstrip("/")
        self._backend_url = backend_url.rstrip("/")
        self._api_key = api_key
        self._stale_s = stale_minutes * 60
        self._http = http if http is not None else requests
        self._os_auth = os_auth if os_auth is not None else (
            os.environ.get(
                "SHUFFLE_OPENSEARCH_USERNAME", os.environ.get("OPENSEARCH_USERNAME", "admin")
            ),
            os.environ.get(
                "SHUFFLE_OPENSEARCH_PASSWORD", os.environ.get("OPENSEARCH_PASSWORD", "")
            ),
        )
        self._verify = verify if verify is not None else ca_verify()
        self.metrics = GCMetrics()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _search(self, status: str, *, older_than: float | None = None,
                now: float | None = None) -> list[dict[str, Any]]:
        """Return docs with ``status == status`` (optionally older
        than a unix-epoch cutoff). Missing index/transport errors → []."""
        must: list[dict[str, Any]] = [
            {
                "bool": {
                    # status is keyword on rollover indices but text+keyword
                    # on the flat `workflowexecution` index — match either.
                    "should": [
                        {"term": {"status": status}},
                        {"term": {"status.keyword": status}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        ]
        if older_than is not None:
            ts = (now if now is not None else time.time()) - older_than
            must.append({"range": {"started_at": {"lt": int(ts)}}})
        body = {
            "size": _MAX_STALE_PER_PASS,
            "_source": ["execution_id", "workflow_id", "workflow",
                        "started_at", "status", "confirm_attempts"],
            "query": {"bool": {"must": must}},
        }
        try:
            r = self._http.post(
                f"{self._os_url}/{EXECUTION_INDEX}/_search",
                json=body,
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                auth=self._os_auth,
                timeout=30,
                verify=self._verify,
            )
        except Exception as exc:
            logger.warning("Stale-exec search failed: %s", exc)
            return []
        if r.status_code in (404,) or r.status_code != 200:
            if r.status_code != 404:
                logger.warning("Stale-exec search HTTP %s", r.status_code)
            return []
        try:
            hits = (r.json() or {}).get("hits", {}).get("hits", [])
        except Exception as exc:
            logger.warning("Stale-exec search malformed body: %s", exc)
            return []
        out = []
        for h in hits:
            src = h.get("_source") or {}
            out.append({
                "doc_id": h.get("_id"),
                "execution_id": src.get("execution_id"),
                "workflow_id": src.get("workflow_id")
                or (src.get("workflow") or {}).get("id"),
                "started_at": src.get("started_at"),
                "confirm_attempts": int(src.get("confirm_attempts") or 0),
            })
        return out

    def find_stale(self, *, now: float | None = None) -> list[dict[str, Any]]:
        """``EXECUTING`` docs older than the stale threshold."""
        return self._search("EXECUTING", older_than=self._stale_s, now=now)

    def oldest_executing_age(self, *, now: float | None = None) -> float:
        """Age in seconds of the oldest ``EXECUTING`` doc (0 when none)."""
        executing = self._search("EXECUTING", now=now)
        if not executing:
            return 0.0
        ref = now if now is not None else time.time()
        starts = [e["started_at"] for e in executing if e.get("started_at")]
        return max(0.0, ref - min(starts)) if starts else 0.0

    # ------------------------------------------------------------------
    # Conditional transitions (late-result reconciliation)
    # ------------------------------------------------------------------

    def _transition(self, doc_id: str, expected: str, to_state: str,
                    extra: dict[str, Any] | None = None) -> bool:
        """Advance ``doc_id`` to ``to_state`` iff status still == expected.

        Scripted conditional update: a doc that moved on externally (e.g.
        a late ``FINISHED``) turns the update into a noop — reconciliation
        without a read-modify-write race on our side.
        """
        script = {
            "source": (
                "if (ctx._source.status == params.expected) {"
                "  ctx._source.status = params.next;"
                "  for (e in params.fields.entrySet()) {"
                "    ctx._source[e.getKey()] = e.getValue();"
                "  }"
                "} else { ctx.op = 'noop'; }"
            ),
            "params": {
                "expected": expected,
                "next": to_state,
                "fields": extra or {},
            },
        }
        try:
            r = self._http.post(
                f"{self._os_url}/{EXECUTION_INDEX}/_update/{doc_id}",
                json={"script": script},
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                auth=self._os_auth,
                timeout=30,
                verify=self._verify,
            )
            if r.status_code != 200:
                logger.warning("GC transition HTTP %s", r.status_code)
                return False
            return (r.json() or {}).get("result") == "updated"
        except Exception as exc:
            logger.warning("GC transition failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Backend interaction
    # ------------------------------------------------------------------

    def _api_abort(self, execution_id: str) -> str:
        """``DELETE /api/v1/executions/<id>`` → ``"ok"`` | ``"gone"`` | ``"failed"``.

        ``gone`` (404 or other 4xx) means the backend already forgot the
        execution — the doc can terminate as ABORTED immediately.
        """
        try:
            r = self._http.delete(
                f"{self._backend_url}/api/v1/executions/{execution_id}",
                headers={HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {self._api_key}"},
                timeout=15,
            )
        except Exception:
            return "failed"
        if r.status_code in (200, 201, 202, 204):
            return "ok"
        if r.status_code == 404 or 400 <= r.status_code < 500:
            return "gone"
        return "failed"

    def _backend_done(self, entry: dict[str, Any]) -> bool:
        """True when Shuffle no longer reports the execution running."""
        wf, eid = entry.get("workflow_id"), entry.get("execution_id")
        if not eid:
            return False
        url = (
            f"{self._backend_url}/api/v1/workflows/{wf}/executions/{eid}"
            if wf else
            f"{self._backend_url}/api/v1/executions/{eid}"
        )
        try:
            r = self._http.get(
                url,
                headers={HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {self._api_key}"},
                timeout=15,
            )
        except Exception:
            return False
        if r.status_code == 404:
            return True
        if r.status_code != 200:
            return False
        try:
            status = str((r.json() or {}).get("status", "")).upper()
        except Exception:
            return False
        return status in TERMINAL_BACKEND_STATES

    # ------------------------------------------------------------------
    # One GC pass
    # ------------------------------------------------------------------

    def collect_once(self, *, now: float | None = None) -> dict[str, Any]:
        """Advance every doc one-or-more states; never raises.

        Returns ``{stale, timed_out, cancelling, aborted, api_failed}``.
        """
        ref = now if now is not None else time.time()
        self.metrics.oldest_executing_seconds = round(
            self.oldest_executing_age(now=ref), 3
        )

        stale = self.find_stale(now=ref)
        self.metrics.stuck_total += len(stale)

        timed_out = cancelling = aborted = api_failed = 0
        for entry in stale:
            doc_id = entry.get("doc_id")
            if not doc_id:
                continue
            if not self._transition(
                doc_id, "EXECUTING", "TIMED_OUT",
                {"timed_out_at": int(ref)},
            ):
                continue  # moved on externally — reconciled, skip
            timed_out += 1
            self.metrics.bump("TIMED_OUT")

            eid = entry.get("execution_id")
            res = self._api_abort(eid) if eid else "failed"
            if res == "failed":
                api_failed += 1
                continue  # stays TIMED_OUT — retried next pass
            if res == "gone":
                # Backend already forgot it — terminal, no CANCELLING wait.
                if self._transition(
                    doc_id, "TIMED_OUT", "ABORTED",
                    {"cancel_requested_at": int(ref), "aborted_at": int(ref)},
                ):
                    aborted += 1
                    self.metrics.bump("ABORTED")
                continue
            if self._transition(
                doc_id, "TIMED_OUT", "CANCELLING",
                {"cancel_requested_at": int(ref), "confirm_attempts": 0},
            ):
                cancelling += 1
                self.metrics.bump("CANCELLING")
                entry["confirm_attempts"] = 0

        # Confirm phase: CANCELLING docs (new + carried over) → ABORTED.
        for entry in self._search("CANCELLING", now=ref):
            doc_id = entry.get("doc_id")
            if not doc_id:
                continue
            attempts = entry.get("confirm_attempts", 0) + 1
            done = self._backend_done(entry)
            forced = not done and attempts >= MAX_CONFIRM_ATTEMPTS
            if done or forced:
                if self._transition(
                    doc_id, "CANCELLING", "ABORTED",
                    {"aborted_at": int(ref), "forced": bool(forced)},
                ):
                    aborted += 1
                    self.metrics.bump("ABORTED")
            else:
                self._transition(
                    doc_id, "CANCELLING", "CANCELLING",
                    {"confirm_attempts": attempts},
                )

        summary = {
            "stale": len(stale),
            "timed_out": timed_out,
            "cancelling": cancelling,
            "aborted": aborted,
            "api_failed": api_failed,
        }
        self.metrics.last_pass = summary
        if stale or aborted:
            logger.info("Stale-exec GC pass: %s", summary)
        return summary
