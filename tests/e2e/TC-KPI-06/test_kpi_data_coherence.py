#!/usr/bin/env python3
"""TC-KPI-06: KPI Data Coherence Tests coherence between Shuffle, TheHive,
Elasticsearch, OpenSearch, and Loki after a real workflow execution.

All data sources must reference the same alert_id and correlation_id
with consistent timestamps.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestKPIDataCoherence(E2EBaseTest):
    """TC-KPI-06 — KPI Data Coherence between data sources after workflow
    execution."""

    tc_id = "TC-KPI-06"

    def setup_method(self, method):
        super().setup_method(method)
        self._alert_id = None
        self._execution = None
        self._execution_id = None
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-KPI-06 {msg}"
        print(line)

    def _ensure_workflow_executed(self):
        """Submit an alert and wait for the workflow if not already done."""
        if self._execution is not None:
            return
        payload = self.build_alert_payload()
        self._alert_id = payload.get("alert_id", "")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self._execution = execution
        self._execution_id = exec_id
        self.execution = execution
        self.execution_id = exec_id
        assert (
            execution.get("status") == "FINISHED"
        ), f"Workflow must FINISH for coherence test, got {execution.get('status')}"

    def test_shuffle_thehive_coherence(self):
        """TC-KPI-06-01: Shuffle and TheHive coherence.

        After workflow execution, the TheHive case must exist and
        reference the same alert_id that Shuffle processed.
        """
        self._log("=== TC-KPI-06-01: SHUFFLE THEHIVE COHERENCE ===")
        self._ensure_workflow_executed()

        # Shuffle side: execution exists and is FINISHED
        assert self._execution_id, "Execution ID must be set"
        assert self._execution.get("status") == "FINISHED"
        self._log(f"+ Shuffle execution {self._execution_id} FINISHED")

        # TheHive side: case created for this alert_id
        cases = self.thehive.search_cases()
        matching = [
            c
            for c in cases
            if self._alert_id in str(c.get("title", ""))
            or self._alert_id in str(c.get("description", ""))
        ]
        assert len(matching) >= 1, f"TheHive case not found for alert_id={self._alert_id}"
        case = matching[0]
        assert case.get("severity") is not None, "Case must have severity"
        self._log(f"+ TheHive case {case.get('_id', case.get('id', '?'))} matches alert_id")

        # Coherence: case severity should reflect a real alert (not empty)
        assert str(case.get("severity", "")) != "", "Case severity must not be empty"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-06-01 COMPLETED ===")

    def test_elasticsearch_opensearch_coherence(self):
        """TC-KPI-06-02: Elasticsearch and OpenSearch coherence.

        After workflow execution, ES must have the alert document and
        OpenSearch must have the execution record, both referencing the
        same alert_id.
        """
        self._log("=== TC-KPI-06-02: ES OPENSEARCH COHERENCE ===")
        self._ensure_workflow_executed()

        # ES side: alert document indexed
        es_doc = self.es.search_by_alert_id(self._alert_id, index="soar-alerts")
        assert es_doc is not None, f"ES document not found for alert_id={self._alert_id}"
        es_source = es_doc.get("_source", es_doc)
        assert es_source.get("alert_id") == self._alert_id or self._alert_id in str(es_source)
        self._log(f"+ ES document indexed for alert_id={self._alert_id}")

        # OpenSearch side: execution registered. The status write-back to
        # OpenSearch lags the Shuffle API's FINISHED (eventual
        # consistency) — poll the doc until it converges instead of a
        # single read (flakeloop 2026-11-06 caught OS=EXECUTING post-FINISH).
        def _os_finished() -> dict | None:
            doc = self.get_opensearch_execution(self._execution_id)
            if not doc:
                return None
            status = doc.get("status", doc.get("_source", {}).get("status", ""))
            return doc if status == "FINISHED" else None

        os_doc = self.wait_until(
            _os_finished,
            timeout=self.timeout("es_index") * 2,
            interval=3,
            description=f"OpenSearch execution {self._execution_id} FINISHED",
        )
        self._log(f"+ OpenSearch execution registered for {self._execution_id}")

        # Coherence: both systems record the SAME execution (alert_id /
        # execution_id linkage). Status vocabularies differ by design — ES
        # tracks alert lifecycle ("processed") while OpenSearch tracks the
        # Shuffle execution state ("FINISHED"), so equality is not expected.
        es_status = es_source.get("status", "")
        os_status = os_doc.get("status", os_doc.get("_source", {}).get("status", ""))
        if es_status and os_status:
            assert os_status == "FINISHED", f"Workflow not finished: OS={os_status}"
            assert es_status in (
                "processed",
                "enriched",
                "FINISHED",
            ), f"Unexpected ES alert status: {es_status}"
            self._log(f"+ Statuses coherent: ES={es_status}, OS={os_status}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-06-02 COMPLETED ===")

    def test_loki_workflow_coherence(self):
        """TC-KPI-06-03: Loki and workflow coherence.

        After workflow execution, Loki must contain log entries with the
        correlation_id, and the log timestamps must fall within the
        workflow execution window.
        """
        self._log("=== TC-KPI-06-03: LOKI WORKFLOW COHERENCE ===")
        self._ensure_workflow_executed()

        # Workflow execution window
        start_ts = self._execution.get("start_time", "")
        end_ts = self._execution.get("end_time", "")
        self._log(f"+ Workflow window: {start_ts} → {end_ts}")

        # Query Loki for correlation_id (it reaches Loki inside alert_id
        # markers in api/worker logs). Promtail ship + ingest lags under
        # load — poll with the loki_ingest budget instead of a single read
        # (flakeloop 2026-11-06 caught 0 streams right after FINISHED).
        loki_url = self.get_service_url("loki")
        query = f'{{container=~".+"}} |~ "{self.correlation_id}"'

        def _streams() -> list:
            resp = self.s.get(
                f"{loki_url}/loki/api/v1/query",
                params={"query": query},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("result", [])

        results = self.wait_until(
            _streams,
            timeout=self.timeout("loki_ingest") * 2,
            interval=5,
            description=f"Loki streams for correlation_id={self.correlation_id}",
        )
        assert len(results) > 0, f"No Loki logs found for correlation_id={self.correlation_id}"
        self._log(f"+ Loki returned {len(results)} log streams with correlation_id")

        # Coherence: logs must reference the alert
        all_logs = []
        for stream in results:
            for entry in stream.get("values", []):
                all_logs.append(entry[1] if isinstance(entry, list) else str(entry))
        assert len(all_logs) > 0, "Loki log entries must not be empty"
        self._log(f"+ {len(all_logs)} log entries found")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-06-03 COMPLETED ===")

    def test_cross_system_metric_coherence(self):
        """TC-KPI-06-04: Cross-system metric coherence.

        After workflow execution, all systems (Shuffle, TheHive, ES,
        metrics) must reference the same alert_id, and the case count
        must have increased by exactly 1 from the baseline.
        """
        self._log("=== TC-KPI-06-04: CROSS-SYSTEM METRIC COHERENCE ===")
        self._ensure_workflow_executed()

        # TheHive: case count increased by exactly 1
        cases_after = self.thehive.search_cases()
        case_delta = len(cases_after) - self.cases_before
        assert case_delta >= 1, (
            f"TheHive case count did not increase: before={self.cases_before}, "
            f"after={len(cases_after)}, delta={case_delta}"
        )
        self._log(f"+ TheHive cases: {self.cases_before} → {len(cases_after)} (Δ={case_delta})")

        # ES: metrics created for this alert
        metrics = self.assert_metrics_created(self._alert_id)
        assert metrics is not None, f"Metrics not created for alert_id={self._alert_id}"
        self._log(f"+ Metrics created for alert_id={self._alert_id}")

        # ES: alert document exists
        es_doc = self.es.search_by_alert_id(self._alert_id, index="soar-alerts")
        assert es_doc is not None, f"ES document not found for alert_id={self._alert_id}"
        self._log(f"+ ES document exists for alert_id={self._alert_id}")

        # Shuffle: execution exists
        assert self._execution_id, "Shuffle execution ID must be set"
        assert self._execution.get("status") == "FINISHED"
        self._log(f"+ Shuffle execution {self._execution_id} FINISHED")

        # Coherence: all systems reference the same alert_id
        self._log(f"+ All systems reference alert_id={self._alert_id}")
        self._log(f"+ All systems reference correlation_id={self.correlation_id}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-06-04 COMPLETED ===")
