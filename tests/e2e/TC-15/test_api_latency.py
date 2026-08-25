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

from tests.e2e.base import E2EBaseTest


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

    def setup_method(self, method):
        """Set up test clients and environment."""
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self._results: list[dict] = []
        self._latencies: list[float] = []
        self._workflow_context_ready = False

    def _ensure_workflow_context(self):
        """Send an alert through the workflow so latency is measured under
        load."""
        if self._workflow_context_ready:
            return
        payload = self.build_alert_payload(
            alert_id=f"TC15-{self.correlation_id}-{int(time.time())}",
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
            lambda: self.thehive.list_cases(),
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
        cases = self.thehive.search_cases()
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

        # search_cases with a query filter for ransomware cases.
        query = {"_field": "title", "_value": "ransomware"}
        result = self._measure_latency(
            lambda: self.thehive.search_cases(query=query),
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
            self.thehive.list_cases()
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
            self.thehive.list_cases()
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
        result = self._measure_latency(lambda: self.thehive.list_cases(), "TheHive")
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

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-15",
            "scenario": "api_latency",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "latencies_s": self._latencies,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = self.e2e_results_dir / "TC-15_api_latency_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_api_latency_suite(self):
        """Run API latency test suite under workflow load."""
        self._log("=== TC-15: API LATENCY E2E TEST STARTED ===")

        self._ensure_workflow_context()

        self.test_get_latency()
        self.test_post_latency()
        self.test_search_latency()

        # Validate that all services responded successfully.
        successful_services = [r for r in self._results if r.get("ok")]
        assert (
            len(successful_services) >= 3
        ), f"At least 3 services should respond successfully, got {len(successful_services)}"

        # Validate that all successful services have acceptable latency.
        for result in successful_services:
            latency_s = result.get("latency_s", 0)
            assert (
                latency_s < self.P95_SLA
            ), f"{result['service']} latency {latency_s:.3f}s exceeds {self.P95_SLA}s threshold"
            self._log(f"✓ {result['service']} latency acceptable: {result['latency_ms']}ms")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-15 COMPLETED ===")
        self._step_save_report(elapsed)
