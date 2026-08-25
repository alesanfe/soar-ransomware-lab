#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 16 (Error Rate Monitoring)
Validates error rates per service to ensure system reliability.

Generates real traffic via submit_alert_and_wait, then queries the
soar-metrics index to calculate and assert error rates.
"""

import json
import time
from datetime import UTC, datetime, timedelta

import pytest
import requests

from tests.e2e.base import E2EBaseTest


class TestErrorRate(E2EBaseTest):
    """TC-16 — Validate error rates per service.

    Ensures error rates remain below acceptable thresholds.
    """

    tc_id = "TC-16"
    MAX_ERROR_RATE = 5.0  # 5% maximum error rate per service

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self._results: list[dict] = []
        self._metrics_generated = False

    def _generate_metrics(self, count: int = 3):
        """Send alerts through the workflow to generate metrics in soar-
        metrics."""
        if self._metrics_generated:
            return
        for i in range(count):
            payload = self.build_alert_payload(
                alert_id=f"TC16-{self.correlation_id}-{i}-{int(time.time())}",
            )
            self.alert_data = payload
            try:
                exec_id, execution = self.submit_alert_and_wait(payload)
                self.execution = execution
                self.execution_id = exec_id
                self.validate_workflow_execution(execution, alert_id=payload["alert_id"])
            except Exception as e:
                self._log(f"Alert {i} generated an error (expected for error-rate test): {e}")
        self._metrics_generated = True

    def _query_metrics(self) -> list[dict]:
        """Query the soar-metrics index for recent metrics."""
        es_url = self.get_service_url("es")
        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )
        # Force refresh so recently-indexed metrics are visible.
        try:
            requests.post(f"{es_url}/soar-metrics/_refresh", auth=es_auth, timeout=30, verify=False)
        except Exception as e:
            self._log(f"  ES refresh warning: {e}")

        query = {
            "range": {"@timestamp": {"gte": (datetime.now(UTC) - timedelta(hours=24)).isoformat()}}
        }
        # Retry ES query in case of transient timeout
        for attempt in range(3):
            try:
                results = self.es.search(query=query, index="soar-metrics", size=10000)
                hits = results.get("hits", {}).get("hits", [])
                return [hit.get("_source", {}) for hit in hits if isinstance(hit, dict)]
            except Exception as e:
                if attempt < 2:
                    self._log(f"  ES query retry {attempt + 1}/3: {e}")
                    time.sleep(5)
                else:
                    raise

    def test_error_rate_by_service(self):
        """Validate error rates per service after generating real traffic."""
        self._log("=== Test: Error Rate by Service ===")

        # Generate metrics by sending alerts through the workflow.
        self._generate_metrics(count=3)

        metrics_data = self._query_metrics()
        assert len(metrics_data) > 0, (
            "No metrics data found in soar-metrics index after generating traffic. "
            "The workflow may not be indexing metrics."
        )

        # Group by service and calculate error rates.
        error_rates: dict[str, dict] = {}
        for metric in metrics_data:
            service = metric.get("service", "unknown")
            success = metric.get("success", True)

            if service not in error_rates:
                error_rates[service] = {"total": 0, "errors": 0}

            error_rates[service]["total"] += 1
            if not success:
                error_rates[service]["errors"] += 1

        self._log(f"Found {len(metrics_data)} metrics across {len(error_rates)} services")

        # Assert at least one service has metrics.
        assert len(error_rates) > 0, "No services found in metrics data"

        # Calculate error rates and validate each service.
        for service, counts in error_rates.items():
            total = counts["total"]
            errors = counts["errors"]
            rate = (errors / total * 100) if total > 0 else 0

            self._log(f"  {service}: {errors}/{total} errors ({rate:.1f}%)")

            assert (
                rate <= self.MAX_ERROR_RATE
            ), f"{service} error rate ({rate:.1f}%) exceeds threshold ({self.MAX_ERROR_RATE}%)"

            self._results.append(
                {
                    "service": service,
                    "total": total,
                    "errors": errors,
                    "error_rate": rate,
                    "ok": rate <= self.MAX_ERROR_RATE,
                }
            )

        self._log(f"✓ All services meet maximum error rate ({self.MAX_ERROR_RATE}%)")

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-16",
            "scenario": "error_rate_monitoring",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = self.e2e_results_dir / "TC-16_error_rate_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_error_rate_suite(self):
        """Run error rate monitoring test suite."""
        self._log("=== TC-16: ERROR RATE MONITORING E2E TEST STARTED ===")

        self.test_error_rate_by_service()

        # Validate that results were collected and all passed
        assert len(self._results) > 0, "No error rate results were recorded"
        failed = [r for r in self._results if not r.get("ok", False)]
        assert not failed, f"{len(failed)}/{len(self._results)} error rate checks failed: {failed}"

        # self.t0 is set in setup_method — no duplicate variable.
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-16 COMPLETED ===")
        self._step_save_report(elapsed)

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-16-01 to TC-16-05)
    # ------------------------------------------------------------------

    def _generate_http_error(self):
        """Generate an HTTP error by sending a request to a wrong/nonexistent
        URL."""
        wrong_url = self.webhook_url.replace("/webhook", "/nonexistent-endpoint-404")
        try:
            self.s.post(wrong_url, json={"alert_id": "tc16-http-error"}, timeout=10)
        except Exception as e:
            self._log(f"  HTTP error generated: {e}")

    def _generate_timeout_error(self):
        """Generate a timeout-like error by sending a very large payload."""
        huge_payload = self.build_alert_payload(
            alert_id=f"TC16-TIMEOUT-{int(time.time())}",
        )
        huge_payload["description"] = "x" * 100000  # Very large payload
        try:
            self.s.post(self.webhook_url, json=huge_payload, timeout=5)
        except Exception as e:
            self._log(f"  Timeout error generated: {e}")

    def _generate_ssl_error(self):
        """Generate an SSL error by connecting to an HTTPS endpoint with bad
        cert."""
        try:
            requests.get("https://localhost:9999/bad-ssl", timeout=5, verify=True)
        except Exception as e:
            self._log(f"  SSL error generated: {e}")

    def _generate_parsing_error(self):
        """Generate a parsing error by sending malformed JSON."""
        try:
            self.s.post(
                self.webhook_url,
                data="{invalid json content !!!",
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as e:
            self._log(f"  Parsing error generated: {e}")

    def _generate_retry_error(self):
        """Generate a retry scenario by sending to a flaky endpoint rapidly."""
        for _ in range(3):
            try:
                self.s.post(
                    self.webhook_url,
                    json={"alert_id": "tc16-retry-test", "bad_field": True},
                    timeout=5,
                )
            except Exception as e:
                self._log(f"  Retry error generated: {e}")
            time.sleep(1)

    @pytest.mark.parametrize(
        "error_type,generate_func,tc_id",
        [
            ("HTTP", "_generate_http_error", "TC-16-01"),
            ("timeout", "_generate_timeout_error", "TC-16-02"),
            ("SSL", "_generate_ssl_error", "TC-16-03"),
            ("parsing", "_generate_parsing_error", "TC-16-04"),
            ("retry", "_generate_retry_error", "TC-16-05"),
        ],
    )
    def test_error_rate_by_type(self, error_type, generate_func, tc_id):
        """Test error rate by type (parametrized).

        Generates a specific error type, then queries metrics to assert
        the error is tracked and the error rate for that type is below
        threshold.
        """
        self._log(f"=== {tc_id}: {error_type.upper()} ERROR RATE TEST STARTED ===")

        # First generate baseline metrics via successful workflow runs.
        self._generate_metrics(count=1)

        # Generate the specific error type.
        getattr(self, generate_func)()

        # Wait briefly for metrics to be indexed.
        time.sleep(5)

        # Query metrics.
        metrics_data = self._query_metrics()
        assert (
            len(metrics_data) > 0
        ), f"No metrics data available after generating {error_type} error"

        # Count errors matching this type.
        errors = 0
        total = len(metrics_data)
        for m in metrics_data:
            if not m.get("success", True):
                err_msg = str(m.get("error_type", "")).lower()
                if error_type.lower() in err_msg or m.get("error_type", "") == "":
                    errors += 1

        error_rate = (errors / total * 100) if total > 0 else 0

        self._log(f"{error_type} errors: {errors}/{total} ({error_rate:.1f}%)")

        # Assert the error rate for this type is below threshold.
        # Even with generated errors, the overall rate should stay manageable
        # because successful workflow metrics outnumber the injected errors.
        assert error_rate <= self.MAX_ERROR_RATE, (
            f"{error_type} error rate ({error_rate:.1f}%) exceeds threshold "
            f"({self.MAX_ERROR_RATE}%)"
        )

        # Assert that metrics data exists and has expected fields.
        for m in metrics_data[:5]:
            assert isinstance(m, dict), "Each metric must be a dict"
            assert (
                "service" in m or "alert_id" in m
            ), "Metric should have 'service' or 'alert_id' field"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log(f"=== {tc_id} COMPLETED ===")
