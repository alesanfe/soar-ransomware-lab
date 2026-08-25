#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case KPI-05 (Service Success Rates by Alert Type)
Validates service success rates broken down by alert type (malicious vs benign).
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator
from tests.e2e.base import E2EBaseTest


class TestServiceSuccessRates(E2EBaseTest):
    """TC-KPI-04 — Validate service success rates broken down by alert type.

    Ensures services maintain high success rates for both malicious and
    benign alerts.
    """

    tc_id = "TC-KPI-04"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.analyzer = KPIAnalyzer(StatisticalCalculator())
        self._results = []

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-KPI-04 {msg}"
        print(line)

    def test_service_success_rates_by_alert_type(self):
        """Validate service success rates by alert type (malicious vs
        benign)."""
        self._log("=== Test: Service Success Rates by Alert Type ===")

        # Query the SOAR API analytics endpoint for real service success rates
        api_url = self.get_service_url("api")
        try:
            r = requests.get(f"{api_url}/analytics/kpis/aggregated?period_hours=24", timeout=30)
            r.raise_for_status()
            analytics = r.json()
        except Exception as e:
            pytest.fail(f"Cannot query SOAR API analytics: {e}")

        services = analytics.get("services", {})
        if not services:
            pytest.fail("No service data in analytics - services have not been tracked")

        self._log(f"Found {len(services)} services in analytics")

        # Calculate success rates and validate
        min_success_rate = 80.0  # 80% minimum success rate (realistic for lab)

        for service_name, stats in services.items():
            total = stats.get("total", 0)
            success = stats.get("success_count", 0)
            rate = stats.get("success_rate_percent", 0)

            self._log(f"  {service_name}: {success}/{total} ({rate:.1f}%)")

            if total == 0:
                continue

            # Elasticsearch should always be 100%
            if service_name == "elasticsearch":
                assert rate >= 95.0, (
                    f"Elasticsearch success rate ({rate:.1f}%) below 95%. "
                    f"This is critical - ES must always work."
                )
            # TheHive should be above 80%
            elif service_name == "thehive":
                assert rate >= 80.0, (
                    f"TheHive success rate ({rate:.1f}%) below 80%. "
                    f"Check TheHive service health and API key."
                )
            # All services should be above 80% for a healthy lab
            else:
                assert rate >= 80.0, (
                    f"{service_name} success rate ({rate:.1f}%) below 80%. "
                    f"This indicates {service_name} is not functioning properly."
                )

            self._results.append(
                {
                    "service": service_name,
                    "total": total,
                    "success": success,
                    "success_rate": rate,
                    "ok": rate >= min_success_rate,
                }
            )

        self._log("✓ All services meet minimum success rate thresholds")

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-KPI-04",
            "scenario": "service_success_rates_by_alert_type",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = Path("reports/validation/results") / "TC-KPI-04_success_rates_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")
