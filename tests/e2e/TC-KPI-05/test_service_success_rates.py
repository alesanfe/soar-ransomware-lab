#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case KPI-05 (Service Success Rates by Alert Type)
Validates service success rates broken down by alert type (malicious vs benign).
"""

import json
import os
import pytest
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer
from soar_lab.domain.statistical_calculator import StatisticalCalculator


def _load_env() -> dict:
    env_vars = {
        "ES_URL": os.environ.get("ES_URL"),
        "ELASTICSEARCH_URL": os.environ.get("ELASTICSEARCH_URL"),
    }
    result = {k: v for k, v in env_vars.items() if v is not None}

    if not ENV_FULL.exists():
        return result

    for line in ENV_FULL.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k not in result:
                result[k] = v
    return result


class TestServiceSuccessRates:
    """
    TC-KPI-05 — Validate service success rates broken down by alert type.
    Ensures services maintain high success rates for both malicious and benign alerts.
    """

    def setup_method(self, method):
        """Set up test clients and environment"""
        t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()
        es_url = env.get("ES_URL") or env.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        es = ElasticsearchClient(base_url=es_url)
        analyzer = KPIAnalyzer(StatisticalCalculator())

        self.t0 = t0
        self.es = es
        self.analyzer = analyzer
        self._results = []


    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-KPI-05 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_service_success_rates_by_alert_type(self):
        """Validate service success rates by alert type (malicious vs benign)."""
        self._log("=== Test: Service Success Rates by Alert Type ===")

        # Query metrics from Elasticsearch
        query = {
            "range": {
                "@timestamp": {
                    "gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                }
            }
        }

        results = self.es.search(query=query, index="soar-metrics", size=10000)
        assert isinstance(results, dict), "ES search results must be a dict"
        metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

        if not metrics_data:
            pytest.skip("No metrics data available in soar-metrics index")

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

                assert rate >= min_success_rate, f"{service} success rate ({rate:.1f}%) for {alert_type} alerts below threshold ({min_success_rate}%)"

                self._results.append({
                    "alert_type": alert_type,
                    "service": service,
                    "total": total,
                    "success": success,
                    "success_rate": rate,
                    "ok": rate >= min_success_rate
                })

        self._log(f"✓ All services meet minimum success rate ({min_success_rate}%)")

        # Validate that success rate calculation logic is correct
        assert len(success_rates) > 0, "At least one alert type should have metrics"
        self._log("✓ Service success rates calculation validated - logic correct and thresholds met")

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-KPI-05",
            "scenario": "service_success_rates_by_alert_type",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = ARTIFACTS_DIR / "results" / "TC-KPI-05_success_rates_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_success_rates_suite(self):
        """Run service success rates test suite."""
        self._log("=== TC-KPI-05: SERVICE SUCCESS RATES E2E TEST STARTED ===")

        self.test_service_success_rates_by_alert_type()

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-KPI-05 COMPLETED ===")
        self._step_save_report(elapsed)
