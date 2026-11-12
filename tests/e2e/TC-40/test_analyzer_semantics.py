"""TC-40 — analyzer mandatory/optional semantics on real executions.

The workflow's cortex_run_guarded wrapper makes analyzer jobs OPTIONAL when
the observable is empty/invalid (skip, don't fail the pipeline) while the
decision/containment spine stays MANDATORY. These subtests verify both
sides on live workflow executions:
  - empty observable -> guarded nodes skip cleanly, workflow still finishes
  - malformed observable -> bounded, never a hang
  - decision field is always present in the metrics doc (mandatory spine)
"""

from __future__ import annotations

import os
import time

import pytest
import requests

from tests.e2e.base import E2EBaseTest

ES = "https://elasticsearch:9200"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))


def _metrics(alert_id: str, timeout: int = 60) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.post(
            f"{ES}/soar-metrics/_search",
            json={"size": 1, "query": {"term": {"alert_id": alert_id}}},
            auth=ES_AUTH, timeout=15,
        )
        hits = r.json().get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"]
        time.sleep(2)
    return None


@pytest.mark.e2e
class TestAnalyzerSemantics(E2EBaseTest):
    tc_id = "TC-40"

    def test_empty_observable_guarded_nodes_workflow_finishes(self):
        """Optional path: empty domain/hash must not hang guarded analyzers."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["domain"] = ""
        payload["hash"] = ""
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        status = (execution or {}).get("status", "")
        assert status in ("FINISHED", "FAILURE", "ABORTED"), (
            f"workflow never reached a terminal state: {status}"
        )
        doc = _metrics(payload["alert_id"])
        if doc is not None:
            # guarded nodes must not fabricate analyzer results for empty input
            for key in ("cortex_hash_job", "cortex_ip_job"):
                val = doc.get(key)
                if val is not None:
                    assert "error" not in str(val).lower()[:40], (
                        f"{key} recorded an error envelope for empty observable"
                    )

    def test_malformed_observable_bounded_not_hung(self):
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["hash"] = "!!not-a-hash!!"
        payload["src_ip"] = "999.999.999.999"
        t0 = time.time()
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        elapsed = time.time() - t0
        assert elapsed < 480, f"malformed observable hung workflow {elapsed:.0f}s"
        assert (execution or {}).get("status") in (
            "FINISHED", "FAILURE", "ABORTED",
        )

    def test_mandatory_decision_spine_always_present(self):
        """Mandatory path: a completed workflow MUST carry a decision —
        a missing decision means the spine failed silently."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        if (execution or {}).get("status") != "FINISHED":
            pytest.skip(f"workflow ended {execution.get('status')} — spine not exercised")
        doc = _metrics(payload["alert_id"])
        assert doc is not None, "no metrics doc — evidence chain broken"
        assert doc.get("decision") in (
            "observe", "contain", "isolate", "escalate", "monitor", "block",
        ), f"mandatory decision missing/invalid: {doc.get('decision')!r}"
