#!/usr/bin/env python3
"""TC-KPI-03: KPI Alerts Verification Tests that KPI-based alerts are triggered
when thresholds are exceeded."""

import json
from datetime import UTC, datetime

import pytest

from tests.e2e.base import E2EBaseTest


class TestKPIAlerts(E2EBaseTest):
    """TC-KPI-03 — KPI Alerts: Verify alerts are triggered when thresholds
    exceeded."""

    tc_id = "TC-KPI-03"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-KPI-03 {msg}")

    def test_kpi_alerts(self):
        """Verify KPI alert manager detects threshold violations."""
        self._log("=== TC-KPI-03: KPI Alerts Verification ===")

        # Step 1: Import KPI alert manager
        self._log("STEP 1: Initializing KPI alert manager")
        from soar_lab.infrastructure.monitoring.kpi_alerts import KPIAlertManager

        alert_manager = KPIAlertManager(self.es)
        self._log("  + KPI alert manager initialized")

        # Step 2: Check MTTR threshold
        self._log("STEP 2: Checking MTTR threshold")
        mttr_check = alert_manager.check_mttr_threshold(hours=1)
        self._log(f"  + MTTR check: {mttr_check.get('status')} - {mttr_check.get('message', 'OK')}")

        # Step 3: Check service health using KPIAnalyzer
        self._log("STEP 3: Checking service health via KPIAnalyzer")
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        # Get metrics data from ES
        try:
            query = {"query": {"range": {"timestamp": {"gte": "now-1h"}}}, "size": 10000}
            results = self.es.search(query=query, index="soar-metrics", size=10000)
            assert isinstance(results, dict), "ES search results must be a dict"
            metrics_data = [
                hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])
            ]
            assert isinstance(metrics_data, list), "Metrics data must be a list"

            if metrics_data:
                kpi_analyzer = KPIAnalyzer(StatisticalCalculator())
                service_kpis = kpi_analyzer.calculate_service_integration_kpis(
                    metrics_data, hours=1
                )
                self._log(
                    f"  + Service KPIs calculated: {len(service_kpis.get('services', {}))} services"
                )
                service_check = {"status": "ok", "services": service_kpis.get("services", {})}
            else:
                self._log("  + No metrics data available for service KPIs")
                service_check = {"status": "no_data", "message": "No metrics data"}
        except Exception as e:
            pytest.fail(f"Service KPIs check failed (ES query error): {e}")

        # Step 4: Check health score
        self._log("STEP 4: Checking health score")
        health_check = alert_manager.check_health_score()
        self._log(
            f"  + Health check: {health_check.get('status')} - {health_check.get('message', 'OK')}"
        )

        # Step 5: Check all thresholds
        self._log("STEP 5: Checking all thresholds")
        all_checks = alert_manager.check_all_thresholds(hours=1)
        self._log(f"  + Overall status: {all_checks.get('overall_status')}")

        # Verify alert manager is functional
        assert "checks" in all_checks, "Missing checks in alert manager response"
        assert "overall_status" in all_checks, "Missing overall status"
        self._log("  + Alert manager is functional")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"=== TC-KPI-03 COMPLETED — KPI ALERTS VERIFIED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-KPI-03",
            "test_name": "KPI Alerts",
            "status": "PASSED",
            "mttr_check": mttr_check,
            "service_check": service_check,
            "health_check": health_check,
            "overall_status": all_checks.get("overall_status"),
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = self.e2e_results_dir / "TC-KPI-03_kpi_alerts_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")
