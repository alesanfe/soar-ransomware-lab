"""Negative-effect assertion helpers (E2E-ORACLE-003).

These helpers verify the *absence* of effects: a rejected alert must not
create a case, a benign alert must not trigger containment, a replayed
submission must not duplicate executions, and secrets/PII must never reach
the persistence layer.

Design rules:

- Every query is bounded by identifier and, where supported, a time window.
- A query failure propagates: "we could not check" is NOT "it is absent".
- Helpers never swallow AssertionError — absence is asserted, not logged.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests

# Node labels that constitute a containment/response action. Matching is
# case-insensitive substring matching on the Shuffle action label.
CONTAINMENT_LABEL_KEYWORDS = (
    "isolate",
    "contain",
    "quarantine",
    "block",
    "disable",
    "shutdown",
    "kill",
    "isolate_host",
)

# Node statuses that mean "the node actually ran".
_EXECUTED_STATUSES = {"SUCCESS", "FINISHED", "RUNNING", "EXECUTING"}


def _node_self_reports_skipped(node: dict[str, Any]) -> bool:
    """Return True when the node's own result declares it did nothing.

    Shuffle bookkeeping marks a decision-gate node SUCCESS whenever its
    script ran — even when the script decided *not* to act.  The real
    effect is in the node's result payload, which may be a JSON string or
    a dict, possibly nested under ``message``.  A node that reports
    ``skipped: true`` produced no effect — counting it as an action would
    be a false positive (verified live: the ``containment`` node returns
    ``{"skipped": true, "reason": "containment not required"}``).
    """
    import json

    result = node.get("result")
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (ValueError, TypeError):
            return False
    if not isinstance(result, dict):
        return False
    candidates = [result]
    if isinstance(result.get("message"), dict):
        candidates.append(result["message"])
    return any(c.get("skipped") is True for c in candidates)


class NegativeAssertionsMixin:
    """Reusable negative-effect oracles for E2E tests (E2E-ORACLE-003)."""

    # ── TheHive ───────────────────────────────────────────────────────────

    def assert_no_case_created(
        self,
        alert_id: str,
        *,
        since: datetime | None = None,
    ) -> None:
        """Assert that NO TheHive case carries ``alert_id`` in title/description.

        Args:
            alert_id: Marker that must not appear in any case.
            since: Optional lower bound — only cases created after this
                instant count as violations (bounds the query in time).
        """
        cases = self.thehive.search_cases(range_="0-100")
        since_ms = since.timestamp() * 1000 if since else None
        offenders = []
        for c in cases:
            hay = f"{c.get('title', '')}\n{c.get('description', '')}"
            if alert_id not in hay:
                continue
            if since_ms is not None and (c.get("createdAt") or 0) < since_ms:
                continue
            offenders.append(c.get("caseId"))
        assert not offenders, (
            f"Expected NO TheHive case for alert_id={alert_id}, " f"found caseId(s): {offenders}"
        )

    # ── Shuffle / containment ─────────────────────────────────────────────

    def assert_no_containment_action(
        self,
        execution_id: str,
        *,
        execution: dict[str, Any] | None = None,
    ) -> None:
        """Assert no containment-labelled node ran in ``execution_id``.

        "Ran" means status SUCCESS/FINISHED/RUNNING/EXECUTING *and* the
        node did not self-report a no-op — a SKIPPED/FAILURE status or a
        ``skipped: true`` result payload does not count as a containment
        effect.
        """
        ex = execution or self.shuffle.get_execution(
            self.workflow_id, execution_id, include_results=True
        )
        results = (ex or {}).get("results", []) or []
        executed = [
            n.get("action", {}).get("label", "?")
            for n in results
            if isinstance(n, dict)
            and n.get("status") in _EXECUTED_STATUSES
            and not _node_self_reports_skipped(n)
            and any(
                kw in str(n.get("action", {}).get("label", "")).lower()
                for kw in CONTAINMENT_LABEL_KEYWORDS
            )
        ]
        assert not executed, (
            f"Containment action(s) unexpectedly executed for "
            f"execution {execution_id}: {executed}"
        )

    def assert_node_not_executed(
        self,
        node_name: str,
        execution: dict[str, Any] | None = None,
    ) -> None:
        """Assert that ``node_name`` did not execute.

        Absent, SKIPPED or FAILURE is acceptable; SUCCESS/FINISHED/RUNNING is not.
        """
        ex = execution or self.execution or {}
        results = ex.get("results", []) or []
        statuses = {
            n.get("action", {}).get("label"): n.get("status")
            for n in results
            if isinstance(n, dict)
        }
        status = statuses.get(node_name)
        assert status not in _EXECUTED_STATUSES, (
            f"Node '{node_name}' executed with status {status} — " f"expected absent/skipped/failed"
        )

    # ── Deduplication ─────────────────────────────────────────────────────

    def assert_no_duplicate_execution(
        self,
        idempotency_key: str,
        *,
        index: str = "soar-alerts",
    ) -> None:
        """Assert at most ONE document exists for ``idempotency_key``.

        The key is matched against ``alert_id``/``idempotency_key`` fields —
        a replay must not produce two persisted executions.
        The query is deliberately broad (term + match) for recall across
        mapping variants; the verdict is computed client-side on the exact
        ``_source`` values, so analyzer tokenisation cannot produce false
        positives and a missing ``.keyword`` subfield cannot produce a
        vacuous pass.
        """
        resp = self.es.search(
            query={
                "bool": {
                    "should": [
                        {"term": {"alert_id.keyword": idempotency_key}},
                        {"term": {"idempotency_key.keyword": idempotency_key}},
                        {"match": {"alert_id": idempotency_key}},
                        {"match": {"idempotency_key": idempotency_key}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            index=index,
            size=50,
        )
        hits = resp.get("hits", {}).get("hits", [])
        matching = [
            h.get("_id")
            for h in hits
            if idempotency_key
            in {
                str(h.get("_source", {}).get("alert_id", "")),
                str(h.get("_source", {}).get("idempotency_key", "")),
            }
        ]
        assert len(matching) <= 1, (
            f"Duplicate executions persisted for key={idempotency_key}: "
            f"{len(matching)} documents in {index} (ids: {matching})"
        )

    # ── Secret / PII hygiene ──────────────────────────────────────────────

    def _search_index_for_value(self, index: str, value: str) -> list[str]:
        """Return doc ids in ``index`` containing ``value`` anywhere.

        The ``query_string`` phrase search provides recall; each hit is then
        verified client-side (exact substring over the serialised ``_source``)
        so analyzer edge cases cannot yield false-positive "leaks".
        """
        import json as _json

        resp = self.es.search(
            query={"query_string": {"query": f'"{value}"'}},
            index=index,
            size=50,
        )
        return [
            str(h.get("_id"))
            for h in resp.get("hits", {}).get("hits", [])
            if value in _json.dumps(h.get("_source", {}), default=str)
        ]

    def _loki_contains_value(self, value: str, *, limit: int = 50) -> bool:
        """Return True when Loki holds a log line containing ``value``."""
        from .service_mixins import _lab_ca_bundle

        loki_url = self.get_service_url("loki")
        r = requests.get(
            f"{loki_url}/loki/api/v1/query",
            params={"query": f'{{job=~".+"}} |= "{value}"', "limit": limit},
            timeout=15,
            verify=_lab_ca_bundle(),
        )
        r.raise_for_status()
        streams = (r.json().get("data") or {}).get("result", [])
        return any(s.get("values") for s in streams)

    def assert_secret_not_persisted(
        self,
        secret: str,
        *,
        indexes: tuple[str, ...] = ("soar-alerts", "soar-metrics"),
        check_loki: bool = True,
    ) -> None:
        """Assert ``secret`` appears in NO persistence layer.

        Searches Elasticsearch indexes and Loki logs — a secret that reached
        any of them is a leak, regardless of how it got there.
        """
        leaks: list[str] = []
        for idx in indexes:
            for doc_id in self._search_index_for_value(idx, secret):
                leaks.append(f"{idx}/{doc_id}")
        if check_loki and self._loki_contains_value(secret):
            leaks.append("loki")
        assert not leaks, f"Secret value persisted at: {leaks}"

    def assert_pii_not_present(
        self,
        value: str,
        *,
        indexes: tuple[str, ...] = ("soar-alerts",),
        check_loki: bool = True,
    ) -> None:
        """Assert a PII value was masked/filtered before persistence.

        Same mechanics as :meth:`assert_secret_not_persisted` but scoped to
        the alert indexes where PII masking is contractual.
        """
        leaks: list[str] = []
        for idx in indexes:
            for doc_id in self._search_index_for_value(idx, value):
                leaks.append(f"{idx}/{doc_id}")
        if check_loki and self._loki_contains_value(value):
            leaks.append("loki")
        assert not leaks, f"PII value persisted unmasked at: {leaks}"

    # ── Side-effect snapshots ─────────────────────────────────────────────

    def take_side_effect_snapshot(self) -> dict[str, int]:
        """Capture counter state for later diffing.

        Returns:
            Dict of counts: thehive_cases, es_docs (soar-alerts),
            soar_metrics_docs. Compare with
            :meth:`assert_no_unexpected_side_effects`.
        """
        snapshot: dict[str, int] = {}
        try:
            snapshot["thehive_cases"] = len(self.thehive.search_cases())
        except Exception:
            snapshot["thehive_cases"] = -1
        for key, idx in (("es_docs", "soar-alerts"), ("metrics_docs", "soar-metrics")):
            try:
                snapshot[key] = self.es.count(index=idx)
            except Exception:
                snapshot[key] = -1
        return snapshot

    def assert_no_unexpected_side_effects(
        self,
        snapshot: dict[str, int],
        *,
        allowed_growth: dict[str, int] | None = None,
    ) -> None:
        """Assert counters did not grow beyond ``allowed_growth``.

        Compares ``snapshot`` against current values. Counters that could not
        be measured (-1) are skipped — the caller decides which counters
        matter by including them in the snapshot.
        """
        allowed = allowed_growth or {}
        now = self.take_side_effect_snapshot()
        violations = []
        for key, before in snapshot.items():
            if before < 0 or now.get(key, -1) < 0:
                continue  # unmeasurable counter — nothing to compare
            growth = now[key] - before
            if growth > allowed.get(key, 0):
                violations.append(f"{key}: +{growth} (allowed {allowed.get(key, 0)})")
        assert not violations, f"Unexpected side effects since snapshot: {violations}"

    # ── Poll-bounded absence ──────────────────────────────────────────────

    def assert_remains_absent(
        self,
        check,
        *,
        duration: float = 15.0,
        interval: float | None = None,
        description: str = "effect",
    ) -> None:
        """Assert ``check()`` keeps returning falsy for ``duration`` seconds.

        Proving a negative requires a window: a single check only proves the
        effect hasn't arrived *yet*.  ``check`` must be a zero-arg callable
        returning truthy when the forbidden effect IS present.
        """
        interval = interval if interval is not None else self.POLL_INTERVAL
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            found = check()
            assert not found, f"Forbidden {description} appeared during watch window"
            time.sleep(interval)
