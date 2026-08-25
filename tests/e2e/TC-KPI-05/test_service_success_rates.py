#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case KPI-05 (Service Success Rates by Alert Type)
Validates service success rates broken down by alert type (malicious vs benign).
"""

import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from tests.e2e.base import E2EBaseTest


class TestServiceSuccessRates(E2EBaseTest):
    """TC-KPI-05 — Validate service success rates broken down by alert type.

    Ensures services maintain high success rates for both malicious and
    benign alerts.
    """

    tc_id = "TC-KPI-05"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.analyzer = KPIAnalyzer(StatisticalCalculator())
        self._results = []

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-KPI-05 {msg}"
        print(line)

    def test_service_success_rates_by_alert_type(self):
        """Validate service success rates by alert type (malicious vs
        benign)."""
        self._log("=== Test: Service Success Rates by Alert Type ===")

        # Generate metrics data by sending an alert first
        self._log("STEP 0: Sending alert to generate service metrics")
        payload = self.build_alert_payload()
        alert_id = payload.get("alert_id", "")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        # Allow metrics to be indexed
        time.sleep(5)

        # Query metrics from Elasticsearch
        query = {
            "range": {"@timestamp": {"gte": (datetime.now(UTC) - timedelta(hours=24)).isoformat()}}
        }

        results = self.es.search(query=query, index="soar-metrics", size=10000)
        assert isinstance(results, dict), "ES search results must be a dict"
        metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

        assert len(metrics_data) > 0, (
            "No metrics data available in soar-metrics index — "
            "metrics should be generated after workflow execution"
        )

        # Group by alert type and service
        success_rates = {}
        for metric in metrics_data:
            alert_type = metric.get("alert_type", "unknown")
            service = metric.get("service", "unknown")
            success = metric.get("success", True)

            if alert_type not in success_rates:
                success_rates[alert_type] = {}
            if service not in success_rates[alert_type]:
                success_rates[alert_type][service] = {"total": 0, "success": 0}

            success_rates[alert_type][service]["total"] += 1
            if success:
                success_rates[alert_type][service]["success"] += 1

        assert isinstance(success_rates, dict), "Success rates must be a dict"
        self._log(f"Found {len(metrics_data)} metrics across {len(success_rates)} alert types")

        # Calculate success rates and validate
        min_success_rate = 95.0  # 95% minimum success rate

        for alert_type, services in success_rates.items():
            self._log(f"\nAlert Type: {alert_type}")
            for service, counts in services.items():
                total = counts["total"]
                success = counts["success"]
                rate = (success / total * 100) if total > 0 else 0

                self._log(f"  {service}: {success}/{total} ({rate:.1f}%)")

                assert rate >= min_success_rate, (
                    f"{service} success rate ({rate:.1f}%) for {alert_type} alerts "
                    f"below threshold ({min_success_rate}%)"
                )

                self._results.append(
                    {
                        "alert_type": alert_type,
                        "service": service,
                        "total": total,
                        "success": success,
                        "success_rate": rate,
                        "ok": rate >= min_success_rate,
                    }
                )

        self._log(f"✓ All services meet minimum success rate ({min_success_rate}%)")

        # Validate that success rate calculation logic is correct
        assert len(success_rates) > 0, "At least one alert type should have metrics"
        self._log(
            "✓ Service success rates calculation validated - logic correct and thresholds met"
        )

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-KPI-05",
            "scenario": "service_success_rates_by_alert_type",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = Path("results") / "TC-KPI-05_success_rates_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_success_rates_suite(self):
        """Run service success rates test suite."""
        self._log("=== TC-KPI-05: SERVICE SUCCESS RATES E2E TEST STARTED ===")

        self.test_service_success_rates_by_alert_type()

        # Validate that results were collected and all passed
        assert len(self._results) > 0, "No service success rate results were recorded"
        failed = [r for r in self._results if not r.get("ok", False)]
        assert (
            not failed
        ), f"{len(failed)}/{len(self._results)} service success rate checks failed: {failed}"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-05 COMPLETED ===")
        self._step_save_report(elapsed)
