#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 16 (Error Rate Monitoring)
Validates error rates per service to ensure system reliability.
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


class TestErrorRate:
    """
    TC-16 — Validate error rates per service.
    Ensures error rates remain below acceptable thresholds.
    """

    def setup_method(self, method):
        """Set up test clients and environment"""
        t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()
        es_url = env.get("ES_URL") or env.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        es = ElasticsearchClient(base_url=es_url)

        self.t0 = t0
        self.es = es
        self._results = []


    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-16 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_error_rate_by_service(self):
        """Validate error rates per service."""
        self._log("=== Test: Error Rate by Service ===")

        # Query metrics from Elasticsearch
        query = {
            "range": {
                "@timestamp": {
                    "gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                }
            }
        }

        results = self.es.search(query=query, index="soar-metrics", size=10000)
        metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

        if not metrics_data:
            pytest.skip("No metrics data available in soar-metrics index")

        # Group by service
        error_rates = {}
        for metric in metrics_data:
            service = metric.get("service", "unknown")
            success = metric.get("success", True)

            if service not in error_rates:
                error_rates[service] = {"total": 0, "errors": 0}

            error_rates[service]["total"] += 1
            if not success:
                error_rates[service]["errors"] += 1

        self._log(f"Found {len(metrics_data)} metrics across {len(error_rates)} services")

        # Calculate error rates and validate
        max_error_rate = 5.0  # 5% maximum error rate

        for service, counts in error_rates.items():
            total = counts["total"]
            errors = counts["errors"]
            rate = (errors / total * 100) if total > 0 else 0

            self._log(f"  {service}: {errors}/{total} errors ({rate:.1f}%)")

            assert rate <= max_error_rate, f"{service} error rate ({rate:.1f}%) exceeds threshold ({max_error_rate}%)"

            self._results.append({
                "service": service,
                "total": total,
                "errors": errors,
                "error_rate": rate,
                "ok": rate <= max_error_rate
            })

        self._log(f"✓ All services meet maximum error rate ({max_error_rate}%)")

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-16",
            "scenario": "error_rate_monitoring",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = ARTIFACTS_DIR / "results" / "TC-16_error_rate_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_error_rate_suite(self):
        """Run error rate monitoring test suite."""
        self._log("=== TC-16: ERROR RATE MONITORING E2E TEST STARTED ===")

        self.test_error_rate_by_service()

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-16 COMPLETED ===")
        self._step_save_report(elapsed)

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-16-01 to TC-16-05)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("error_type,error_filter,tc_id", [
        ("HTTP", lambda e: e.startswith("HTTP"), "TC-16-01"),
        ("timeout", lambda e: "timeout" in e.lower(), "TC-16-02"),
        ("SSL", lambda e: "ssl" in e.lower(), "TC-16-03"),
        ("parsing", lambda e: "parse" in e.lower(), "TC-16-04"),
        ("retry", lambda e: "retry" in e.lower(), "TC-16-05"),
    ])
    def test_error_rate_by_type(self, error_type, error_filter, tc_id):
        """
        Test error rate by type (parametrized).

        Verifications:
          - Errors are tracked by type
          - Error rate is below threshold (5%)
          - Specific error types are monitored
        """
        self._log(f"=== {tc_id}: {error_type.upper()} ERROR RATE TEST STARTED ===")

        query = {
            "range": {
                "@timestamp": {
                    "gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
                }
            }
        }

        results = self.es.search(query=query, index="soar-metrics", size=10000)
        metrics_data = [hit.get("_source", {}) for hit in results.get("hits", {}).get("hits", [])]

        if not metrics_data:
            pytest.skip("No metrics data available")

        errors = sum(1 for m in metrics_data if not m.get("success", True) and error_filter(m.get("error_type", "")))
        total = len(metrics_data)
        error_rate = (errors / total * 100) if total > 0 else 0

        self._log(f"{error_type} errors: {errors}/{total} ({error_rate:.1f}%)")
        assert error_rate <= 5.0, f"{error_type} error rate ({error_rate:.1f}%) exceeds threshold"

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log(f"=== {tc_id} COMPLETED ===")
