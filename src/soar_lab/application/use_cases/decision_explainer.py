"""Explainable decisions (SOAR-01): extract the calc_decision verdict.

The workflow's ``calc_decision`` node emits a JSON result containing the
score, verdict, decision and the human-readable ``factors`` list
(``alert_type.ransomware(+25)``, ``misp_ioc_count``, ...). This use case
extracts that payload from an execution document so the API can answer
*why* a verdict was reached — the explainability gap in SOAR-01.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

DECISION_NODE_LABELS = ("calc_decision", "decision")


class ExecutionIndexPort(Protocol):
    """Port for reading Shuffle execution documents."""

    def get_execution(self, execution_id: str) -> dict[str, Any] | None: ...

    def recent_executions(self, limit: int = 20) -> list[dict[str, Any]]: ...


def extract_decision(execution_doc: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the ``calc_decision`` payload from an execution document.

    Returns the parsed ``message`` dict (score/verdict/decision/factors/…)
    or ``None`` when the node has not run yet or its result is malformed.
    """
    results = execution_doc.get("results")
    if not isinstance(results, list):
        return None
    for entry in results:
        if not isinstance(entry, dict):
            continue
        label = (entry.get("action") or {}).get("label")
        if label not in DECISION_NODE_LABELS:
            continue
        raw = entry.get("result")
        if not isinstance(raw, str):
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        message = parsed.get("message") if isinstance(parsed, dict) else None
        if isinstance(message, dict) and "verdict" in message:
            return message
    return None


class DecisionExplainer:
    """Use case: answer *why* a workflow reached its verdict."""

    def __init__(self, index: ExecutionIndexPort) -> None:
        self._index = index

    def explain(self, execution_id: str) -> dict[str, Any] | None:
        """Return the decision record for one execution.

        Returns ``None`` when the execution does not exist.
        """
        doc = self._index.get_execution(execution_id)
        if doc is None:
            return None
        return self._shape(doc)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return decision records for the most recent executions.

        ``decision`` is ``null`` for executions still pre-verdict.
        """
        return [self._shape(doc) for doc in self._index.recent_executions(limit)]

    @staticmethod
    def _shape(doc: dict[str, Any]) -> dict[str, Any]:
        workflow = doc.get("workflow") or {}
        return {
            "execution_id": doc.get("execution_id"),
            "status": doc.get("status"),
            "workflow_id": doc.get("workflow_id"),
            "workflow_name": workflow.get("name") if isinstance(workflow, dict) else None,
            "started_at": doc.get("started_at"),
            "completed_at": doc.get("completed_at"),
            "decision": extract_decision(doc),
        }
