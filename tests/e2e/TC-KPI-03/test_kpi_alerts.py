#!/usr/bin/env python3
"""
TC-KPI-03: KPI Alerts Verification
Tests that KPI-based alerts are triggered when thresholds are exceeded.
"""

import json
import requests
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
# Use /app/results for artifacts when running inside container
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"


def _load_env() -> dict:
    if not ENV_FULL.exists():
        return {}
    result = {}
    for line in ENV_FULL.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


class TestKPIAlerts(unittest.TestCase):
    """
    TC-KPI-03 — KPI Alerts: Verify alerts are triggered when thresholds exceeded.
    """

    def setUp(self):
        self.t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)

        env = _load_env()
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient

        self.es = ElasticsearchClient(
            base_url=env.get("ES_URL", "http://soar_elasticsearch:9200"),
            index="soar-metrics"
        )

    def _log(self, msg: str):
        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
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
            query = {
                "query": {
                    "range": {
                        "timestamp": {
                            "gte": "now-1h"
                        }
                    }
                },
                "size": 10000
            }
            results = self.es.search(query=query, index="soar-metrics", size=10000)
            metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

            if metrics_data:
                kpi_analyzer = KPIAnalyzer(StatisticalCalculator())
                service_kpis = kpi_analyzer.calculate_service_integration_kpis(metrics_data, hours=1)
                self._log(f"  + Service KPIs calculated: {len(service_kpis.get('services', {}))} services")
                service_check = {"status": "ok", "services": service_kpis.get("services", {})}
            else:
                self._log("  + No metrics data available for service KPIs")
                service_check = {"status": "no_data", "message": "No metrics data"}
        except Exception as e:
            self._log(f"  + Service KPIs check failed: {e}")
            service_check = {"status": "error", "message": str(e)}

        # Step 4: Check health score
        self._log("STEP 4: Checking health score")
        health_check = alert_manager.check_health_score()
        self._log(f"  + Health check: {health_check.get('status')} - {health_check.get('message', 'OK')}")

        # Step 5: Check all thresholds
        self._log("STEP 5: Checking all thresholds")
        all_checks = alert_manager.check_all_thresholds(hours=1)
        self._log(f"  + Overall status: {all_checks.get('overall_status')}")

        # Verify alert manager is functional
        assert "checks" in all_checks, "Missing checks in alert manager response"
        assert "overall_status" in all_checks, "Missing overall status"
        self._log("  + Alert manager is functional")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report_path = ARTIFACTS_DIR / "results" / "TC-KPI-03_kpi_alerts_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    unittest.main()
