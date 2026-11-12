#!/usr/bin/env python3
"""Mutation-hardening tests for worker_lease + kpi_analyzer — Lua script
args, fencing, MTTR extraction and KPI boundary conditions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from soar_lab.domain.models import AlertSeverity
from soar_lab.domain.services.kpi_analyzer import (
    KPIAnalyzer,
    _extract_mttr,
)
from soar_lab.infrastructure.messaging.worker_lease import (
    FENCE_KEY,
    LEASE_KEY,
    WorkerLease,
)


class TestWorkerLease:
    async def test_no_client_leads(self):
        assert await WorkerLease(None, "w").held() is True

    async def test_held_script_args(self):
        c = AsyncMock()
        c.eval.return_value = 1
        w = WorkerLease(c, "w1", ttl_ms=500)
        assert await w.held() is True
        script, nkeys, key, holder, ttl = c.eval.call_args.args
        assert nkeys == 1 and key == LEASE_KEY
        assert holder == "w1" and ttl == "500"
        assert "NX" in script

    async def test_result_0_not_leader(self):
        c = AsyncMock()
        c.eval.return_value = 0
        assert await WorkerLease(c, "w").held() is False

    async def test_acquisition_fences(self):
        c = AsyncMock()
        c.eval.return_value = 2
        c.incr.return_value = 7
        w = WorkerLease(c, "w")
        assert await w.held() is True
        c.incr.assert_awaited_once_with(FENCE_KEY)
        assert w.fence_token == 7

    async def test_acquire_incr_failure_token_none(self):
        c = AsyncMock()
        c.eval.return_value = 2
        c.incr.side_effect = RuntimeError("x")
        w = WorkerLease(c, "w")
        assert await w.held() is True
        assert w.fence_token is None

    async def test_held_eval_error_false(self):
        c = AsyncMock()
        c.eval.side_effect = RuntimeError("redis gone")
        assert await WorkerLease(c, "w").held() is False

    async def test_release_contract(self):
        c = AsyncMock()
        w = WorkerLease(c, "w1")
        await w.release()
        script, nkeys, key, holder = c.eval.call_args.args
        assert nkeys == 1 and key == LEASE_KEY and holder == "w1"
        assert "GET" in script and "DEL" in script
        # no client -> no call
        w2 = WorkerLease(None, "w")
        await w2.release()
        # release error swallowed
        c.eval.side_effect = RuntimeError("x")
        await w.release()


class TestExtractMttr:
    @pytest.mark.parametrize(
        "field,want",
        [
            ({"message": "MTTR: 42.5s elapsed"}, 42.5),
            ({"message": "no marker"}, 0),
            ({"message": "MTTR: bad"}, 0),
            ({"other": 1}, 0),
            (120.0, 120.0),
            (75, 75),
            ("text", 0),
            (None, 0),
        ],
    )
    def test_extract(self, field, want):
        assert _extract_mttr(field) == want


class TestKpiAnalyzer:
    def _an(self):
        return KPIAnalyzer(MagicMock())

    def test_ctor_requires_calculator(self):
        with pytest.raises(ValueError, match="statistical_calculator is required"):
            KPIAnalyzer(None)

    def test_performance_kpis(self):
        results = [
            {"status": "passed", "coverage_percent": 80.0, "duration_seconds": 2},
            {"status": "failed", "coverage_percent": 60.0, "duration_seconds": 4},
        ]
        out = KPIAnalyzer.calculate_performance_kpis(results, hours=48)
        assert out["period_hours"] == 48
        assert out["total_tests"] == 2
        assert out["passed_tests"] == 1
        assert out["success_rate"] == 50.0
        assert out["average_coverage"] == 70.0
        assert out["average_duration_seconds"] == 3.0
        assert "timestamp" in out

    def test_performance_kpis_empty(self):
        out = KPIAnalyzer.calculate_performance_kpis([])
        assert out["success_rate"] == 0
        assert out["average_coverage"] == 0
        assert out["average_duration_seconds"] == 0

    def test_health_score_delegates(self):
        an = self._an()
        an._statistical_calculator.calculate_health_score.return_value = {"s": 1}
        out = an.calculate_health_score(1, 2, 3, 4)
        an._statistical_calculator.calculate_health_score.assert_called_once_with(
            cpu_percent=1, memory_percent=2, disk_percent=3, test_coverage=4
        )
        assert out["s"] == 1 and "timestamp" in out

    def test_mttr_metrics_delegates(self):
        an = self._an()
        an._statistical_calculator.calculate_statistical_metrics.return_value = {"m": 1}
        assert an.calculate_mttr_metrics([1.0]) == {"m": 1}

    def test_comprehensive_shape(self):
        out = KPIAnalyzer.calculate_comprehensive_kpis({"a": 1}, {"b": 2}, {"c": 3})
        assert out["mttr"] == {"a": 1}
        assert out["performance"] == {"b": 2}
        assert out["health"] == {"c": 3}
        assert "timestamp" in out

    def test_kpis_by_alert_type(self):
        data = [
            {"alert_type": "ransom", "mttr_seconds": 10, "severity": AlertSeverity.CRITICAL},
            {"alert_type": "ransom", "mttr_seconds": 20, "severity": 1},
            {"alert_type": "ransom", "mttr_seconds": 99999999, "severity": 1},  # over window
            {"mttr_seconds": -5, "severity": 1},  # unknown type + mttr<=0 skipped
        ]
        out = KPIAnalyzer.calculate_kpis_by_alert_type(data, hours=24)
        r = out["by_alert_type"]["ransom"]
        assert r["count"] == 3
        assert r["avg_mttr_seconds"] == 15.0  # only 10,20 in window
        assert r["avg_severity"] == round(
            (AlertSeverity.CRITICAL + 1 + 1) / 3, 2
        )
        assert r["critical_count"] == 1
        assert r["critical_rate"] == 33.33
        u = out["by_alert_type"]["unknown"]
        assert u["count"] == 1 and u["avg_mttr_seconds"] == 0

    def test_check_service_success(self):
        assert KPIAnalyzer._check_service_success("id") is True
        assert KPIAnalyzer._check_service_success({"success": True}) is True
        assert KPIAnalyzer._check_service_success({"success": 0}) is False
        assert KPIAnalyzer._check_service_success(42) is False

    def test_classify_metric_services(self):
        out = KPIAnalyzer._classify_metric_services(
            {
                "thehive_case_id": "c1",
                "cortex_hash_job": {"success": True},
                "misp_results": None,
            }
        )
        assert out == {
            "thehive": "success",
            "cortex": "success",
            "misp": "failure",
            "elasticsearch": "success",
        }
        # cortex via ip job only
        out2 = KPIAnalyzer._classify_metric_services({"cortex_ip_job": "j"})
        assert out2["cortex"] == "success" and out2["thehive"] == "failure"

    def test_service_integration_kpis(self):
        data = [
            {"thehive_case_id": "c", "cortex_hash_job": "j", "misp_results": "r"},
            {},
        ]
        out = KPIAnalyzer.calculate_service_integration_kpis(data, hours=12)
        assert out["period_hours"] == 12
        th = out["services"]["thehive"]
        assert th == {
            "success_count": 1,
            "failure_count": 1,
            "total": 2,
            "success_rate_percent": 50.0,
        }
        assert out["services"]["elasticsearch"]["success_rate_percent"] == 100.0
