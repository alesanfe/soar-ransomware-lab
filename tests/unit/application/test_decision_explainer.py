"""Unit tests for DecisionExplainer (SOAR-01 explainable decisions)."""

from __future__ import annotations

import json

from soar_lab.application.use_cases.decision_explainer import (
    DecisionExplainer,
    extract_decision,
)

DECISION_PAYLOAD = {
    "score": 85,
    "verdict": "malicious",
    "decision": "contain",
    "factors": ["webhook.confidence=90", "alert_type.ransomware(+25)", "misp.iocs=5(+15)"],
    "misp_ioc_count": 5,
}


def _doc(status="FINISHED", decision_payload=DECISION_PAYLOAD, eid="e-1"):
    results = []
    if decision_payload is not None:
        results.append(
            {
                "action": {"label": "calc_decision"},
                "result": json.dumps({"success": True, "message": decision_payload}),
            }
        )
    return {
        "execution_id": eid,
        "status": status,
        "workflow_id": "wf-1",
        "workflow": {"name": "SOAR-Ransomware-Response"},
        "started_at": 100,
        "completed_at": 200,
        "results": results,
    }


class FakeIndex:
    def __init__(self, docs=None):
        self.docs = {d["execution_id"]: d for d in (docs or [])}

    def get_execution(self, execution_id):
        return self.docs.get(execution_id)

    def recent_executions(self, limit=20):
        return list(self.docs.values())[:limit]


class TestExtractDecision:
    def test_extracts_message_payload(self):
        out = extract_decision(_doc())
        assert out["verdict"] == "malicious"
        assert out["score"] == 85
        assert "alert_type.ransomware(+25)" in out["factors"]

    def test_no_decision_node_returns_none(self):
        assert extract_decision(_doc(decision_payload=None)) is None

    def test_missing_results_returns_none(self):
        assert extract_decision({"execution_id": "e"}) is None

    def test_malformed_result_json_returns_none(self):
        doc = _doc()
        doc["results"] = [{"action": {"label": "calc_decision"}, "result": "{not json"}]
        assert extract_decision(doc) is None

    def test_result_without_verdict_ignored(self):
        doc = _doc()
        doc["results"] = [
            {
                "action": {"label": "calc_decision"},
                "result": json.dumps({"success": True, "message": {"partial": True}}),
            }
        ]
        assert extract_decision(doc) is None

    def test_decision_label_variant_accepted(self):
        doc = _doc()
        doc["results"] = [
            {
                "action": {"label": "decision"},
                "result": json.dumps({"success": True, "message": DECISION_PAYLOAD}),
            }
        ]
        assert extract_decision(doc)["verdict"] == "malicious"


class TestDecisionExplainer:
    def test_explain_returns_shaped_record(self):
        ex = DecisionExplainer(FakeIndex([_doc()]))
        rec = ex.explain("e-1")
        assert rec["execution_id"] == "e-1"
        assert rec["status"] == "FINISHED"
        assert rec["workflow_name"] == "SOAR-Ransomware-Response"
        assert rec["decision"]["verdict"] == "malicious"

    def test_explain_unknown_execution_returns_none(self):
        ex = DecisionExplainer(FakeIndex([]))
        assert ex.explain("nope") is None

    def test_running_execution_has_null_decision(self):
        ex = DecisionExplainer(FakeIndex([_doc(status="EXECUTING", decision_payload=None)]))
        rec = ex.explain("e-1")
        assert rec["status"] == "EXECUTING"
        assert rec["decision"] is None

    def test_recent_shapes_all(self):
        docs = [_doc(eid="e-1"), _doc(eid="e-2", decision_payload=None)]
        out = DecisionExplainer(FakeIndex(docs)).recent(20)
        assert len(out) == 2
        assert out[0]["decision"]["verdict"] == "malicious"
        assert out[1]["decision"] is None
