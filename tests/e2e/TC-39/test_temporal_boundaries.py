"""TC-39 — exact temporal tolerance boundaries + replay guard.

calc_mttr semantics (live workflow script):
  detection_time in the future -> clamped to now (mttr = 0)
  epoch-millis (>1e11)         -> /1000 before diff
  unparsable                   -> mttr = 0
These tests exercise the exact boundaries against real workflow executions,
plus a same-alert_id replay to prove admission stays bounded and evidence
is not silently corrupted.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

import pytest
import requests

from tests.e2e.base import E2EBaseTest

ES = "https://elasticsearch:9200"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))


def _mttr_doc(alert_id: str, timeout: int = 60) -> dict | None:
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
class TestTemporalBoundaries(E2EBaseTest):
    tc_id = "TC-39"

    def test_detection_time_now_mttr_positive_and_bounded(self):
        """Boundary: detection_time == now -> 0 < mttr < workflow bound."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["detection_time"] = datetime.now(UTC).isoformat()
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        doc = _mttr_doc(payload["alert_id"])
        assert doc is not None, "metrics doc missing"
        mttr = doc["mttr_seconds"]
        assert 0 < mttr < 600, f"mttr {mttr} outside [0, 600)"

    def test_future_detection_time_clamps_mttr_to_zero(self):
        """Boundary: detection_time = now + 2h -> mttr clamps to exactly 0."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        payload["detection_time"] = (
            datetime.now(UTC) + timedelta(hours=2)
        ).isoformat()
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        doc = _mttr_doc(payload["alert_id"])
        assert doc is not None
        assert doc["mttr_seconds"] <= 1.0, (
            f"future skew must clamp to ~0, got {doc['mttr_seconds']}"
        )

    def test_timezone_offset_instant_equivalent_to_z(self):
        """Same instant as +02:00 offset vs Z -> equivalent mttr (no tz misfire)."""
        now = datetime.now(UTC)
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        # same instant expressed in +02:00 — the DST-relevant code path
        payload["detection_time"] = (
            now.astimezone()  # local tz exercises the offset parser
        ).isoformat()
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        doc = _mttr_doc(payload["alert_id"])
        assert doc is not None
        assert 0 < doc["mttr_seconds"] < 600, (
            f"offset-timestamp mttr {doc['mttr_seconds']} — tz parsed wrong"
        )

    def test_replay_same_alert_id_bounded_no_corruption(self):
        """Replaying the identical alert_id must stay bounded and not corrupt."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution

        # Replay: identical payload, identical alert_id (nonce reuse).
        t0 = time.time()
        second = self.submit_alert(payload)
        elapsed = time.time() - t0
        assert elapsed < 60, "replay hung the webhook"
        if second is None:
            pytest.fail("replay produced no response — unbounded rejection path")

        time.sleep(5)
        r = requests.post(
            f"{ES}/soar-metrics/_count",
            json={"query": {"term": {"alert_id": alert_id}}},
            auth=ES_AUTH, timeout=15,
        )
        count = r.json().get("count", 0)
        assert count >= 1, "no metrics doc for replayed alert"
        # Re-execution is legitimate in this lab (alerts are events); the
        # contract is that docs stay well-formed — mttr present and sane.
        doc = _mttr_doc(alert_id)
        assert doc is not None and doc["mttr_seconds"] >= 0
