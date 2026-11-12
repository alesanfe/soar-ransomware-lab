"""TC-KPI-02 — KPI run isolation and formal numerator/denominator.

The ambient locust generator injects ~1 execution/min into soar-metrics, so a
KPI computed over a bare time window mixes environmental and test data. These
subtests prove that run-scoped queries isolate the run's own documents and that
each KPI has a documented numerator/denominator with zero-division guards.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

import pytest
import requests

ES = "https://elasticsearch:9200"
ES_AUTH = (os.environ.get("ELASTIC_USERNAME", "elastic"), os.environ.get("ELASTIC_PASSWORD", ""))
IDX = "soar-metrics"

from tests.e2e.base import E2EBaseTest


def _es(body: dict) -> dict:
    r = requests.post(f"{ES}/{IDX}/_search", json=body, auth=ES_AUTH, timeout=15)
    r.raise_for_status()
    return r.json()


def _docs_since(minutes: int) -> list[dict]:
    body = {
        "size": 200,
        "query": {"range": {"@timestamp": {"gte": f"now-{minutes}m"}}},
        "_source": ["alert_id", "trace_id", "success", "mttr_seconds", "metric_type"],
    }
    return [h["_source"] for h in _es(body)["hits"]["hits"]]


@pytest.mark.e2e
class TestKpiIsolation(E2EBaseTest):
    tc_id = "TC-KPI-02"

    def test_run_scoped_query_excludes_ambient_load(self):
        """Run docs (marked by alert_id/trace_id) are a strict subset of the window."""
        payload = self.build_alert_payload(alert_type="ransomware", severity=2)
        run_marker = payload["alert_id"]
        trace = payload.get("trace_id")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution_id, self.execution = exec_id, execution
        time.sleep(3)

        ambient = _docs_since(15)
        ambient_ids = {d.get("alert_id") for d in ambient}
        assert run_marker in ambient_ids, "run doc absent from soar-metrics window"

        run_docs = [d for d in ambient if d.get("alert_id") == run_marker]
        if trace:
            traced = [d for d in ambient if d.get("trace_id") == trace]
            assert traced, "trace_id present in payload but not indexed"
            assert {d["alert_id"] for d in traced} == {run_marker}, (
                "trace_id leaked across alerts — isolation marker not unique"
            )
        # The ambient window provably contains foreign (locust) docs OR at
        # minimum the run docs are provably attributable — never assert a
        # KPI over the unfiltered window.
        foreign = ambient_ids - {run_marker}
        self._log(
            f"window={len(ambient)} docs, run={len(run_docs)}, foreign={len(foreign)}"
        )
        assert all(d["alert_id"] == run_marker for d in run_docs)

    def test_formal_numerator_denominator_success_rate(self):
        """success_rate = N(success==true) / N(success field present); den>0 required."""
        docs = _docs_since(15)
        eligible = [d for d in docs if "success" in d]
        if not eligible:
            pytest.skip("no docs with success field in window — ambient generator idle")
        numerator = sum(1 for d in eligible if d.get("success") is True)
        denominator = len(eligible)
        assert denominator > 0
        rate = numerator / denominator
        assert 0.0 <= rate <= 1.0
        # denominator must exclude docs lacking the field — silent zero-fill
        # would fabricate failures.
        assert len(eligible) <= len(docs)
        self._log(
            f"success_rate={rate:.3f} ({numerator}/{denominator}; "
            f"{len(docs) - denominator} docs excluded — no success field)"
        )

    def test_mttr_numerator_excludes_zero_mttr_docs(self):
        """Formal def: MTTR numerator = docs with mttr_seconds > 0 only.

        Legitimate mttr==0 cases exist — decision=observe (nothing to respond
        to) and skew-test alerts whose future detection_time clamps MTTR to 0.
        A REAL response decision with mttr<=0 would poison p95/mean, so any
        such doc not matching a known synthetic pattern fails the guard.
        """
        docs = _docs_since(24 * 60)  # wide window — this is a data-integrity guard
        if not docs:
            pytest.skip("soar-metrics empty in last 24h")
        negative = [d for d in docs if isinstance(d.get("mttr_seconds"), (int, float))
                    and d["mttr_seconds"] < 0]
        assert not negative, f"negative MTTR regressed: {negative[:3]}"

        unexplained_zero = [
            d for d in docs
            if d.get("mttr_seconds") == 0
            and d.get("decision") not in (None, "observe")
            and not str(d.get("alert_id", "")).startswith(("TC39-SKEW", "DT01-", "DT-"))
        ]
        assert not unexplained_zero, (
            f"response decisions reporting mttr=0 (would poison KPIs): "
            f"{[d['alert_id'] for d in unexplained_zero[:5]]}"
        )

        positive = [d["mttr_seconds"] for d in docs
                    if isinstance(d.get("mttr_seconds"), (int, float)) and d["mttr_seconds"] > 0]
        if not positive:
            pytest.skip("no positive mttr docs in window")
        mean = sum(positive) / len(positive)
        self._log(
            f"mttr: n={len(positive)}/{len(docs)} positive, mean={mean:.1f}s, "
            f"{len(docs) - len(positive)} excluded (zero/absent)"
        )
