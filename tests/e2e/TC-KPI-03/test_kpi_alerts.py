#!/usr/bin/env python3
"""TC-KPI-03: KPI Alerts Verification Tests that KPI-based alerts are triggered
when thresholds are exceeded."""

import json
from datetime import UTC, datetime, timedelta

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
            query = {"range": {"@timestamp": {"gte": "now-1h"}}}
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

        # Step 6: THRESHOLD-VIOLATION oracle — the manager must actually
        # FIRE when a real violation exists, not merely shape its answer.
        # Inject a synthetic metric doc with an absurd MTTR (1e9s pulls the
        # hourly average above the 120s threshold unless there are ~10⁷
        # documents) and a bottom health score (that check reads the
        # latest metric_type=health_score doc → deterministic).
        self._log("STEP 6: Verifying threshold violation triggers an alert")
        marker = self.uid("KPI03-VIOLATION")
        # Injection must VIOLATE the threshold while staying inside the
        # analyzer's validity bound (mttr_seconds <= hours*3600 — larger
        # values are discarded as corrupt documents, which is what made
        # the old 1e9 probe a no-op). The check averages every mttr doc
        # in the window — count the real population first and inject at
        # least as many probes, so the mean is dominated regardless of
        # how much legitimate data accumulated (avg >= ~1500s > 120s).
        window_q = {
            "range": {"@timestamp": {"gte": (datetime.now(UTC) - timedelta(hours=1)).isoformat()}}
        }
        try:
            res = self.es.search(query=window_q, index="soar-metrics", size=1)
            real_count = res.get("hits", {}).get("total", {}).get("value", 0)
        except Exception:
            real_count = 0
        n_probes = max(10, int(real_count))
        self._log(f"  Injecting {n_probes} MTTR probes (window has ~{real_count} docs)")
        injected_mttr = []
        for i in range(n_probes):
            mttr_doc = {
                "@timestamp": datetime.now(UTC).isoformat(),
                "alert_id": f"{marker}-{i}",
                "metric_type": "mttr",
                "mttr_seconds": 3000.0,
                "service": "kpi03-probe",
                "success": True,
            }
            injected_mttr.append(mttr_doc)
        health_doc = {
            "@timestamp": datetime.now(UTC).isoformat(),
            "alert_id": marker,
            "metric_type": "health_score",
            "score": 1,
            "service": "kpi03-probe",
        }
        probe_doc_ids = []
        for doc in injected_mttr:
            resp = self.es.index_document(doc, index="soar-metrics", refresh=True)
            doc_id = resp.get("_id")
            assert doc_id, f"Index response missing _id: {resp}"
            probe_doc_ids.append(doc_id)
            self.register_resource("elasticsearch_documents", f"soar-metrics/_doc/{doc_id}")
        r2 = self.es.index_document(health_doc, index="soar-metrics", refresh=True)
        doc_id = r2.get("_id")
        assert doc_id, f"Index response missing _id: {r2}"
        probe_doc_ids.append(doc_id)
        self.register_resource("elasticsearch_documents", f"soar-metrics/_doc/{doc_id}")

        mttr_check = alert_manager.check_mttr_threshold(hours=1)
        assert mttr_check.get("status") == "alert", (
            f"Injected mttr_seconds=3000×10 must trigger an alert, "
            f"got status={mttr_check.get('status')}: {mttr_check}"
        )
        assert mttr_check.get("value", 0) > mttr_check.get(
            "threshold", 0
        ), "Alert must carry value > threshold"
        self._log(f"  + MTTR violation fired: {mttr_check.get('message')}")

        health_check = alert_manager.check_health_score()
        assert health_check.get("status") == "alert", (
            f"Injected health_score=1 must trigger an alert, "
            f"got status={health_check.get('status')}: {health_check}"
        )
        self._log(f"  + Health-score violation fired: {health_check.get('message')}")

        all_checks = alert_manager.check_all_thresholds(hours=1)
        assert (
            all_checks.get("overall_status") == "alert"
        ), "overall_status must be 'alert' while injected violations exist"
        self._log("  + Alert manager fires on real threshold violations")

        # Isolation: probes are oracle inputs, not report data — delete them
        # explicitly (E2E_PRESERVE_REPORT_DATA would otherwise keep them) so
        # 10×3000s values cannot skew downstream percentile/KPI tests
        # reading the same soar-metrics index.
        deleted = 0
        for pid in probe_doc_ids:
            try:
                self.es.delete_document(pid, index="soar-metrics")
                deleted += 1
            except Exception as e:
                self._log(f"  ! probe cleanup failed for {pid}: {e}")
        try:
            self.es.indices.refresh("soar-metrics")
        except Exception:
            pass
        self._log(f"  + Injected probes removed: {deleted}/{len(probe_doc_ids)}")

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
            "violation_oracle": "injected-violations-fired",
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = self.e2e_results_dir / "TC-KPI-03_kpi_alerts_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")
