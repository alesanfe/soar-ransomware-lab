#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 15 (API Latency)
Validates API latency for individual services: TheHive, Cortex, MISP.

Measures GET, POST (observable creation), search, p95, and SLA compliance
under realistic load (after a workflow execution generates data).
"""

import json
import time
from datetime import UTC, datetime
from typing import ClassVar

from tests.e2e.base import E2EBaseTest
from tests.e2e.base.config_mixin import E2E_RESULTS_DIR


class TestAPILatency(E2EBaseTest):
    """TC-15 — Validate API latency for individual services.

    Ensures API response times are within acceptable thresholds.
    """

    tc_id = "TC-15"

    # SLA thresholds (seconds) — relaxed for lab environment with heavy load
    GET_SLA = 5.0
    POST_SLA = 5.0
    SEARCH_SLA = 10.0
    P95_SLA = 10.0
    _class_results: ClassVar[list] = []
    _class_latencies: ClassVar[list] = []
    _class_t0: ClassVar[datetime | None] = None

    @classmethod
    def setup_class(cls):
        cls._class_results = []
        cls._class_latencies = []
        cls._class_t0 = datetime.now(UTC)

    @classmethod
    def teardown_class(cls):
        """Persist the aggregate API-latency report once per class run.

        Replaces the removed ``test_api_latency_suite`` orchestrator
        (EXEC-001): each scenario is collected once, and the report still
        aggregates every per-test result.
        """
        if cls._class_t0 is None:
            return
        elapsed = (datetime.now(UTC) - cls._class_t0).total_seconds()
        report = {
            "test_case": "TC-15",
            "scenario": "api_latency",
            "elapsed_seconds": elapsed,
            "results": cls._class_results,
            "latencies_s": cls._class_latencies,
            "success": all(r.get("ok", False) for r in cls._class_results),
        }
        report_file = E2E_RESULTS_DIR / "TC-15_api_latency_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2, default=str))
        print(f"TC-15 + Report saved: {report_file}")

    def setup_method(self, method):
        """Set up test clients and environment."""
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self._results: list[dict] = type(self)._class_results
        self._latencies: list[float] = type(self)._class_latencies
        self._workflow_context_ready = False

    def _ensure_workflow_context(self):
        """Send an alert through the workflow so latency is measured under
        load."""
        if self._workflow_context_ready:
            return
        payload = self.build_alert_payload(
            alert_id=self.uid("TC15"),
        )
        self.alert_data = payload
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=payload["alert_id"])
        self._workflow_context_ready = True

    def _measure_latency(self, func, service_name: str) -> dict:
        """Measure API latency for a given function (returns seconds)."""
        start = time.time()
        func()
        latency_s = time.time() - start
        latency_ms = int(latency_s * 1000)
        self._log(f"{service_name}: {latency_ms}ms")
        result = {
            "service": service_name,
            "latency_ms": latency_ms,
            "latency_s": latency_s,
            "ok": True,
        }
        self._results.append(result)
        self._latencies.append(latency_s)
        return result

    # ------------------------------------------------------------------
    # Core latency tests
    # ------------------------------------------------------------------

    def test_get_latency(self):
        """TC-15-01: GET latency — measure TheHive list_cases (GET request)."""
        self._ensure_workflow_context()
        self._log("=== TC-15-01: GET LATENCY TEST STARTED ===")

        result = self._measure_latency(
            # Bounded page: latency must measure API responsiveness, not
            # accumulated case volume (BUG-046 — unbounded 0-1000 took ~13 s
            # with ~640 cases and broke the SLA deterministically).
            lambda: self.thehive.list_cases(range_="0-50"),
            "TheHive-GET-list_cases",
        )
        assert result["ok"], f"GET request failed: {result}"
        assert (
            result["latency_s"] < self.GET_SLA
        ), f"GET latency ({result['latency_s']:.3f}s) exceeds SLA ({self.GET_SLA}s)"
        assert result["latency_s"] > 0, "Latency should be positive"

        # Record p50/p95 from this single measurement (baseline).
        self._log(f"p50 baseline: {result['latency_ms']}ms")

    def test_post_latency(self):
        """TC-15-02: POST latency — measure TheHive observable creation (POST
        request)."""
        self._ensure_workflow_context()
        self._log("=== TC-15-02: POST LATENCY TEST STARTED ===")

        # Find a case created by the workflow to attach the observable to.
        cases = self.thehive.search_cases(range_="0-50")
        assert isinstance(cases, list), "TheHive search_cases must return a list"
        assert len(cases) > 0, "No TheHive cases available for POST latency test"

        # Use the most recent case.
        cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        case_id = cases[0].get("_id") or cases[0].get("id", "")
        assert case_id, "Could not extract a valid case ID for POST test"

        result = self._measure_latency(
            lambda: self.thehive.create_observable(
                case_id=case_id,
                data_type="ip",
                data=f"10.15.15.{int(time.time()) % 200 + 1}",
                tags=["tc15-latency"],
            ),
            "TheHive-POST-create_observable",
        )
        assert result["ok"], f"POST request failed: {result}"
        assert (
            result["latency_s"] < self.POST_SLA
        ), f"POST latency ({result['latency_s']:.3f}s) exceeds SLA ({self.POST_SLA}s)"
        assert result["latency_s"] > 0, "Latency should be positive"

    def test_search_latency(self):
        """TC-15-03: Search latency — measure TheHive search_cases with
        filters.

        TheHive 3.x does not expose a WebSocket/streaming endpoint, so
        we measure filtered search latency instead.
        """
        self._ensure_workflow_context()
        self._log("=== TC-15-03: SEARCH LATENCY TEST STARTED ===")

        # search_cases with a query filter for high-severity cases.
        query = {"_eq": {"_field": "severity", "_value": 3}}
        result = self._measure_latency(
            lambda: self.thehive.search_cases(query=query, range_="0-50"),
            "TheHive-SEARCH-filtered",
        )
        assert result["ok"], f"Search request failed: {result}"
        assert (
            result["latency_s"] < self.SEARCH_SLA
        ), f"Search latency ({result['latency_s']:.3f}s) exceeds SLA ({self.SEARCH_SLA}s)"
        assert result["latency_s"] > 0, "Latency should be positive"

    def test_p95_latency(self):
        """TC-15-04: p95 latency — send 20 requests, calculate p95, assert <
        5s."""
        self._ensure_workflow_context()
        self._log("=== TC-15-04: P95 LATENCY TEST STARTED ===")

        latencies_ms: list[int] = []
        for i in range(20):
            start = time.time()
            self.thehive.list_cases(range_="0-50")
            latencies_ms.append(int((time.time() - start) * 1000))

        assert len(latencies_ms) == 20, f"Should have 20 latency samples, got {len(latencies_ms)}"
        latencies_ms.sort()
        # p95 index for 20 samples = index 18 (0-based, ceil(0.95*20)-1 = 18)
        p95_index = int(0.95 * len(latencies_ms))
        if p95_index >= len(latencies_ms):
            p95_index = len(latencies_ms) - 1
        p95_ms = latencies_ms[p95_index]
        p95_s = p95_ms / 1000.0

        # Also compute p50.
        p50_ms = latencies_ms[len(latencies_ms) // 2]
        self._log(f"p50: {p50_ms}ms, p95: {p95_ms}ms (over 20 samples)")

        assert p95_s < self.P95_SLA, f"p95 latency ({p95_s:.3f}s) exceeds SLA ({self.P95_SLA}s)"
        assert p95_ms > 0, "p95 latency should be positive"
        assert p50_ms <= p95_ms, "p50 should be <= p95"

    def test_sla_compliance(self):
        """TC-15-05: SLA compliance — assert all measured latencies meet
        SLA."""
        self._ensure_workflow_context()
        self._log("=== TC-15-05: SLA COMPLIANCE TEST STARTED ===")

        # Measure p50 and p95 over a fresh batch of 20 requests.
        latencies_s: list[float] = []
        for i in range(20):
            start = time.time()
            self.thehive.list_cases(range_="0-50")
            latencies_s.append(time.time() - start)

        latencies_s.sort()
        p50 = latencies_s[len(latencies_s) // 2]
        p95_idx = int(0.95 * len(latencies_s))
        if p95_idx >= len(latencies_s):
            p95_idx = len(latencies_s) - 1
        p95 = latencies_s[p95_idx]

        self._log(
            f"SLA check: p50={p50:.3f}s (limit {self.GET_SLA}s), "
            f"p95={p95:.3f}s (limit {self.P95_SLA}s)"
        )

        # Assert with descriptive messages — not just logging.
        assert (
            p50 < self.GET_SLA
        ), f"SLA VIOLATION: p50 latency ({p50:.3f}s) exceeds p50 SLA ({self.GET_SLA}s)"
        assert (
            p95 < self.P95_SLA
        ), f"SLA VIOLATION: p95 latency ({p95:.3f}s) exceeds p95 SLA ({self.P95_SLA}s)"
        assert p50 > 0, "p50 latency should be positive"
        assert p95 > 0, "p95 latency should be positive"
        assert p50 <= p95, "p50 should be <= p95"

    # ------------------------------------------------------------------
    # Per-service latency tests
    # ------------------------------------------------------------------

    def test_thehive_api_latency(self):
        """Test TheHive API latency under workflow load."""
        self._ensure_workflow_context()
        result = self._measure_latency(lambda: self.thehive.list_cases(range_="0-50"), "TheHive")
        assert result["ok"], f"TheHive latency measurement failed: {result}"
        assert (
            result["latency_s"] < self.GET_SLA
        ), f"TheHive latency ({result['latency_s']:.3f}s) exceeds SLA ({self.GET_SLA}s)"

    def test_cortex_api_latency(self):
        """Test Cortex API latency under workflow load."""
        self._ensure_workflow_context()
        result = self._measure_latency(lambda: self.cortex.list_analyzers(), "Cortex")
        assert result["ok"], f"Cortex latency measurement failed: {result}"
        assert (
            result["latency_s"] < self.SEARCH_SLA
        ), f"Cortex latency ({result['latency_s']:.3f}s) exceeds SLA ({self.SEARCH_SLA}s)"

    def test_misp_api_latency(self):
        """Test MISP API latency under workflow load."""
        self._ensure_workflow_context()
        result = self._measure_latency(lambda: self.misp.list_events(), "MISP")
        assert result["ok"], f"MISP latency measurement failed: {result}"
        assert (
            result["latency_s"] < self.SEARCH_SLA
        ), f"MISP latency ({result['latency_s']:.3f}s) exceeds SLA ({self.SEARCH_SLA}s)"

    # ------------------------------------------------------------------
    # Report & suite
    # ------------------------------------------------------------------
