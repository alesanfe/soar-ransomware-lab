#!/usr/bin/env python3
"""Endpoint tests for routes_analytics — use cases mocked at module level."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

MOD = "soar_lab.interfaces.api.routes_analytics"


def _app(repo=None, **state):
    from soar_lab.interfaces.api.routes_analytics import register_analytics_routes

    app = FastAPI()
    register_analytics_routes(app, lambda: Mock())
    app.state.alert_repository = repo
    for k, v in state.items():
        setattr(app.state, k, v)
    return TestClient(app, raise_server_exceptions=False)


class TestMetricsKpis:
    def test_metrics_mock_fallback(self):
        c = _app()
        c.app.state.system_metrics = None
        r = c.get("/analytics/metrics")
        assert r.status_code == 200
        assert set(r.json()) == {"cpu", "memory", "disk", "timestamp"}

    def test_metrics_hardware_path(self):
        sm = Mock()
        sm.get_hardware_metrics.return_value = {
            "cpu": {"percent": 11.0},
            "memory": {"percent": 22.0},
            "disk": {"percent": 33.0},
        }
        c = _app()
        c.app.state.system_metrics = sm
        r = c.get("/analytics/metrics")
        assert r.json()["cpu"] == 11.0

    def test_metrics_error_500(self):
        sm = Mock()
        sm.get_hardware_metrics.side_effect = RuntimeError("x")
        c = _app()
        c.app.state.system_metrics = sm
        assert c.get("/analytics/metrics").status_code == 500

    def test_kpis_overlay_uses_coverage_artifact(self, tmp_path):
        cov = tmp_path / "coverage.json"
        cov.write_text('{"totals": {"percent_covered": 87.5}}', encoding="utf-8")
        ps = Mock()
        ps.coverage_file = cov
        analytics = Mock()
        analytics.get_comprehensive_kpis.return_value = {
            "performance": {"total_tests": 0, "average_coverage": 0}
        }
        c = _app(path_service=ps)
        c.app.dependency_overrides = {}
        # re-register with our analytics provider
        from soar_lab.interfaces.api.routes_analytics import register_analytics_routes

        app = FastAPI()
        register_analytics_routes(app, lambda: analytics)
        app.state.path_service = ps
        r = TestClient(app).get("/analytics/kpis")
        assert r.status_code == 200
        assert r.json()["performance"]["average_coverage"] == 87.5
        assert r.json()["performance"]["coverage_source"] == "last_run_artifact"

    def test_kpis_overlay_noop_without_artifact(self):
        analytics = Mock()
        analytics.get_comprehensive_kpis.return_value = {
            "performance": {"total_tests": 0, "average_coverage": 0}
        }
        from soar_lab.interfaces.api.routes_analytics import register_analytics_routes

        app = FastAPI()
        register_analytics_routes(app, lambda: analytics)
        r = TestClient(app).get("/analytics/kpis")
        assert r.status_code == 200
        assert r.json()["performance"]["average_coverage"] == 0

    def test_kpis_500(self):
        analytics = Mock()
        analytics.get_comprehensive_kpis.side_effect = RuntimeError("x")
        from soar_lab.interfaces.api.routes_analytics import register_analytics_routes

        app = FastAPI()
        register_analytics_routes(app, lambda: analytics)
        assert TestClient(app).get("/analytics/kpis").status_code == 500


class TestAggregatedAndSlo:
    def test_aggregated_503_and_500(self):
        uc = Mock()
        uc.execute.side_effect = requests.ConnectionError("down")
        with patch(f"{MOD}.create_aggregated_kpis_use_case", return_value=uc):
            assert _app().get("/analytics/kpis/aggregated").status_code == 503
        uc.execute.side_effect = RuntimeError("boom")
        with patch(f"{MOD}.create_aggregated_kpis_use_case", return_value=uc):
            assert _app().get("/analytics/kpis/aggregated").status_code == 500

    def test_aggregated_and_slo_success(self):
        uc = Mock()
        uc.execute.return_value = {"period_hours": 24}
        with (
            patch(f"{MOD}.create_aggregated_kpis_use_case", return_value=uc),
            patch(f"{MOD}.evaluate_slos", return_value={"all_met": True}),
        ):
            c = _app()
            assert c.get("/analytics/kpis/aggregated?hours=2").json()["period_hours"] == 24
            assert c.get("/analytics/slo").json()["all_met"] is True

    def test_slo_request_exception_503(self):
        uc = Mock()
        uc.execute.side_effect = requests.ConnectionError("x")
        with patch(f"{MOD}.create_aggregated_kpis_use_case", return_value=uc):
            assert _app().get("/analytics/slo").status_code == 503


class TestNodeTimings:
    def test_execution_found_not_found_and_aggregated(self):
        uc = Mock()
        uc.get_execution.side_effect = [None, {"nodes": []}]
        uc.get_aggregated.return_value = {"agg": True}
        with patch(f"{MOD}.create_node_timings_use_case", return_value=uc):
            c = _app()
            assert c.get("/analytics/node-timings?execution_id=e1").status_code == 404
            assert c.get("/analytics/node-timings?execution_id=e1").json() == {"nodes": []}
            assert c.get("/analytics/node-timings?hours=3").json() == {"agg": True}

    def test_503_and_500(self):
        uc = Mock()
        uc.get_aggregated.side_effect = requests.ConnectionError("d")
        with patch(f"{MOD}.create_node_timings_use_case", return_value=uc):
            assert _app().get("/analytics/node-timings").status_code == 503
        uc.get_aggregated.side_effect = RuntimeError("x")
        with patch(f"{MOD}.create_node_timings_use_case", return_value=uc):
            assert _app().get("/analytics/node-timings").status_code == 500


class TestRepositoryEndpoints:
    def _repo(self):
        return Mock(get_alerts=Mock(return_value=[]), get_alert=Mock(return_value=None))

    def test_repository_unavailable_503s(self):
        c = _app(repo=None)
        assert c.get("/analytics/attack-coverage").status_code == 503
        assert c.get("/analytics/incident-report/a1").status_code == 503
        assert c.get("/analytics/experiment/compare?variant_a=x&variant_b=y").status_code == 503
        assert c.get("/api/v1/stix/bundle").status_code == 503
        assert c.get("/analytics/sigma/matches").status_code == 503

    def test_attack_coverage_formats_and_error(self):
        repo = self._repo()
        uc = Mock()
        uc.navigator_layer.return_value = {"layer": 1}
        uc.heatmap.return_value = {"heat": 1}
        uc.coverage.return_value = {"cov": 1}
        with patch(f"{MOD}.AttackCoverageUseCase", return_value=uc):
            c = _app(repo=repo)
            assert c.get("/analytics/attack-coverage?format=navigator").json() == {"layer": 1}
            assert c.get("/analytics/attack-coverage?format=heatmap&limit=5").json() == {"heat": 1}
            uc.coverage.assert_not_called()  # not yet — summary path next
            assert c.get("/analytics/attack-coverage").json() == {"cov": 1}
            uc.coverage.side_effect = RuntimeError("x")
            assert c.get("/analytics/attack-coverage").status_code == 500

    def test_incident_report_json_md_404_500(self):
        repo = self._repo()
        uc = Mock()
        uc.build.return_value = {"report": 1}
        uc.build_markdown.return_value = "# report"
        with patch(f"{MOD}.IncidentReportUseCase", return_value=uc):
            c = _app(repo=repo)
            assert c.get("/analytics/incident-report/a1").json() == {"report": 1}
            r = c.get("/analytics/incident-report/a1?format=markdown")
            assert r.headers["content-type"].startswith("text/markdown")
            uc.build.return_value = None
            assert c.get("/analytics/incident-report/a1").status_code == 404
            uc.build_markdown.return_value = None
            assert c.get("/analytics/incident-report/a1?format=markdown").status_code == 404
            uc.build.side_effect = RuntimeError("x")
            assert c.get("/analytics/incident-report/a1").status_code == 500

    def test_experiment_compare_ok_and_500(self):
        repo = self._repo()
        uc = Mock()
        uc.compare.return_value = {"delta": 0.5}
        with patch(f"{MOD}.ExperimentCompareUseCase", return_value=uc):
            c = _app(repo=repo)
            r = c.get("/analytics/experiment/compare?variant_a=a&variant_b=b")
            assert r.json() == {"delta": 0.5}
            uc.compare.side_effect = RuntimeError("x")
            assert c.get("/analytics/experiment/compare?variant_a=a&variant_b=b").status_code == 500

    def test_stix_bundle_ok_bounded_and_500(self):
        repo = self._repo()
        uc = Mock()
        uc.build_bundle.return_value = {"type": "bundle", "objects": []}
        with patch(f"{MOD}.StixExportUseCase", return_value=uc):
            c = _app(repo=repo)
            assert c.get("/api/v1/stix/bundle?limit=999999").json()["type"] == "bundle"
            uc.build_bundle.assert_called_with(limit=10000)
            uc.build_bundle.side_effect = RuntimeError("x")
            assert c.get("/api/v1/stix/bundle").status_code == 500

    def test_sigma_matches_ok_and_500(self, tmp_path):
        repo = self._repo()
        cp = Mock()
        cp.get.return_value = str(tmp_path)
        uc = Mock()
        uc.scan.return_value = {"rules": 2}
        with (
            patch(f"{MOD}.SigmaEvalUseCase") as sig,
            patch.object(sig, "load_rules", return_value=[]) as lr,
        ):
            sig.load_rules = lr
            sig.return_value = uc
            c = _app(repo=repo, config_provider=cp)
            r = c.get("/analytics/sigma/matches?limit=5")
            assert r.status_code == 200
            uc.scan.side_effect = RuntimeError("x")
            assert c.get("/analytics/sigma/matches").status_code == 500
