#!/usr/bin/env python3
"""Unit tests for kpi_analyzer.py."""

from unittest.mock import Mock

import pytest

from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer


class TestKPIAnalyzer:
    """Test KPIAnalyzer."""

    def test_initialization_success(self):
        """Test successful initialization with statistical_calculator."""
        mock_stat_calc = Mock()

        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        assert analyzer._statistical_calculator == mock_stat_calc

    def test_requires_statistical_calculator(self):
        """Test that statistical_calculator is required."""
        with pytest.raises(
            ValueError, match=r"^statistical_calculator is required for KPIAnalyzer$"
        ):
            KPIAnalyzer(statistical_calculator=None)

    def test_calculate_performance_kpis(self):
        """Test calculating performance KPIs."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        test_results = [
            {"status": "passed", "coverage_percent": 80, "duration_seconds": 5},
            {"status": "passed", "coverage_percent": 90, "duration_seconds": 3},
            {"status": "failed", "coverage_percent": 70, "duration_seconds": 2},
        ]

        result = analyzer.calculate_performance_kpis(test_results, hours=24)

        assert result["period_hours"] == 24
        assert result["total_tests"] == 3
        assert result["passed_tests"] == 2
        assert result["success_rate"] == 66.67
        assert result["average_coverage"] == 80.0
        assert result["average_duration_seconds"] == 3.33
        assert "timestamp" in result

    def test_calculate_performance_kpis_empty(self):
        """Test calculating performance KPIs with empty results."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        result = analyzer.calculate_performance_kpis([], hours=24)

        assert result["total_tests"] == 0
        assert result["passed_tests"] == 0
        assert result["success_rate"] == 0
        assert result["average_coverage"] == 0
        assert result["average_duration_seconds"] == 0

    def test_calculate_performance_kpis_missing_fields(self):
        """Test calculating performance KPIs with missing fields."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        test_results = [{"status": "passed"}, {"coverage_percent": 80}, {"duration_seconds": 5}]

        result = analyzer.calculate_performance_kpis(test_results, hours=24)

        assert result["total_tests"] == 3
        assert result["passed_tests"] == 1
        assert result["average_coverage"] == 26.67
        assert result["average_duration_seconds"] == 1.67

    def test_calculate_health_score(self):
        """Test calculating health score."""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_health_score.return_value = {"overall_score": 85, "status": "good"}

        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        result = analyzer.calculate_health_score(
            cpu_percent=50, memory_percent=60, disk_percent=70, test_coverage=85.5
        )

        assert result["overall_score"] == 85
        assert result["status"] == "good"
        assert "timestamp" in result
        mock_stat_calc.calculate_health_score.assert_called_once_with(
            cpu_percent=50, memory_percent=60, disk_percent=70, test_coverage=85.5
        )

    def test_calculate_mttr_metrics(self):
        """Test calculating MTTR metrics."""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_statistical_metrics.return_value = {
            "mean": 120.5,
            "median": 100,
            "p90": 200,
        }

        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        execution_times = [100, 120, 150, 200]
        result = analyzer.calculate_mttr_metrics(execution_times)

        assert result["mean"] == 120.5
        assert result["median"] == 100
        assert result["p90"] == 200
        mock_stat_calc.calculate_statistical_metrics.assert_called_once_with(execution_times)

    def test_calculate_mttr_metrics_empty(self):
        """Test calculating MTTR metrics with empty list."""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_statistical_metrics.return_value = {
            "mean": 0,
            "median": 0,
            "p90": 0,
        }

        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        result = analyzer.calculate_mttr_metrics([])

        assert result["mean"] == 0
        mock_stat_calc.calculate_statistical_metrics.assert_called_once_with([])

    def test_calculate_comprehensive_kpis(self):
        """Test calculating comprehensive KPIs."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        mttr_metrics = {"mean": 120.5}
        performance_kpis = {"success_rate": 90}
        health_score = {"overall_score": 85}

        result = analyzer.calculate_comprehensive_kpis(
            mttr_metrics=mttr_metrics, performance_kpis=performance_kpis, health_score=health_score
        )

        assert result["mttr"] == mttr_metrics
        assert result["performance"] == performance_kpis
        assert result["health"] == health_score
        assert "timestamp" in result

    def test_calculate_kpis_by_alert_type(self):
        """Test calculating KPIs by alert type."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        metrics_data = [
            {"alert_type": "malware", "mttr_seconds": 120.5, "severity": 4},
            {"alert_type": "malware", "mttr_seconds": 150.0, "severity": 2},
            {"alert_type": "phishing", "mttr_seconds": 90.0, "severity": 1},
            {"alert_type": "phishing", "mttr_seconds": 110.0, "severity": 2},
        ]

        result = analyzer.calculate_kpis_by_alert_type(metrics_data, hours=24)

        assert result["period_hours"] == 24
        assert "by_alert_type" in result
        assert "malware" in result["by_alert_type"]
        assert "phishing" in result["by_alert_type"]
        assert result["by_alert_type"]["malware"]["count"] == 2
        assert result["by_alert_type"]["malware"]["avg_mttr_seconds"] == 135.25
        assert result["by_alert_type"]["malware"]["critical_count"] == 1
        assert result["by_alert_type"]["phishing"]["count"] == 2
        assert result["by_alert_type"]["phishing"]["avg_mttr_seconds"] == 100.0
        assert "timestamp" in result

    def test_calculate_kpis_by_alert_type_with_dict_mttr(self):
        """Test calculating KPIs by alert type with dict MTTR field."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        metrics_data = [
            {"alert_type": "malware", "mttr_seconds": {"message": "MTTR: 120.5s"}, "severity": 3},
            {"alert_type": "malware", "mttr_seconds": {"message": "MTTR: 150.0s"}, "severity": 2},
        ]

        result = analyzer.calculate_kpis_by_alert_type(metrics_data, hours=24)

        assert result["by_alert_type"]["malware"]["count"] == 2
        assert result["by_alert_type"]["malware"]["avg_mttr_seconds"] == 135.25

    def test_calculate_kpis_by_alert_type_invalid_mttr_format(self):
        """Test calculating KPIs by alert type with invalid MTTR format."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        metrics_data = [
            {"alert_type": "malware", "mttr_seconds": {"message": "Invalid format"}, "severity": 3},
            {"alert_type": "malware", "mttr_seconds": {"message": "No MTTR here"}, "severity": 2},
        ]

        result = analyzer.calculate_kpis_by_alert_type(metrics_data, hours=24)

        # Should handle invalid format gracefully (mttr = 0)
        assert result["by_alert_type"]["malware"]["count"] == 2
        assert result["by_alert_type"]["malware"]["avg_mttr_seconds"] == 0

    def test_calculate_kpis_by_alert_type_empty(self):
        """Test calculating KPIs by alert type with empty data."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        result = analyzer.calculate_kpis_by_alert_type([], hours=24)

        assert result["period_hours"] == 24
        assert result["by_alert_type"] == {}
        assert "timestamp" in result

    def test_calculate_service_integration_kpis(self):
        """Test calculating service integration KPIs."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        metrics_data = [
            {
                "thehive_case_id": "case-001",
                "cortex_hash_job": "job-001",
                "cortex_ip_job": "job-002",
                "misp_results": "results-001",
            },
            {
                "thehive_case_id": None,
                "cortex_hash_job": None,
                "cortex_ip_job": None,
                "misp_results": None,
            },
        ]

        result = analyzer.calculate_service_integration_kpis(metrics_data, hours=24)

        assert result["period_hours"] == 24
        assert "services" in result
        assert "thehive" in result["services"]
        assert "cortex" in result["services"]
        assert "misp" in result["services"]
        assert "elasticsearch" in result["services"]
        assert result["services"]["thehive"]["success_count"] == 1
        assert result["services"]["thehive"]["failure_count"] == 1
        assert result["services"]["cortex"]["success_count"] == 1
        assert result["services"]["cortex"]["failure_count"] == 1
        assert result["services"]["misp"]["success_count"] == 1
        assert result["services"]["misp"]["failure_count"] == 1
        assert result["services"]["elasticsearch"]["success_count"] == 2
        assert result["services"]["elasticsearch"]["failure_count"] == 0
        assert "timestamp" in result

    def test_calculate_service_integration_kpis_empty(self):
        """Test calculating service integration KPIs with empty data."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        result = analyzer.calculate_service_integration_kpis([], hours=24)

        assert result["period_hours"] == 24
        assert result["services"]["thehive"]["success_count"] == 0
        assert result["services"]["thehive"]["failure_count"] == 0
        assert result["services"]["cortex"]["success_count"] == 0
        assert result["services"]["cortex"]["failure_count"] == 0
        assert result["services"]["misp"]["success_count"] == 0
        assert result["services"]["misp"]["failure_count"] == 0
        assert result["services"]["elasticsearch"]["success_count"] == 0
        assert result["services"]["elasticsearch"]["failure_count"] == 0
        assert "timestamp" in result

    def test_calculate_service_integration_kpis_workflow_execution(self):
        """Test calculating service integration KPIs with workflow_execution
        metric type."""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)

        metrics_data = [{"metric_type": "workflow_execution"}]

        result = analyzer.calculate_service_integration_kpis(metrics_data, hours=24)

        # Only the canonical set of services is tracked
        expected_services = {"thehive", "cortex", "misp", "elasticsearch"}
        assert set(result["services"].keys()) == expected_services


class TestKPIMutationHardening:
    def _analyzer(self):
        from soar_lab.domain.statistical_calculator import StatisticalCalculator

        return KPIAnalyzer(StatisticalCalculator())

    def test_init_requires_calculator(self):
        with pytest.raises(
            ValueError, match=r"^statistical_calculator is required for KPIAnalyzer$"
        ):
            KPIAnalyzer(None)

    def test_performance_kpis_exact(self):
        results = [
            {"status": "passed", "coverage_percent": 80, "duration_seconds": 10},
            {"status": "failed", "coverage_percent": 60, "duration_seconds": 20},
            {"status": "passed", "coverage_percent": 100, "duration_seconds": 30},
        ]
        r = KPIAnalyzer.calculate_performance_kpis(results)
        assert r["period_hours"] == 24
        assert r["total_tests"] == 3
        assert r["passed_tests"] == 2
        assert r["success_rate"] == 66.67
        assert r["average_coverage"] == 80.0
        assert r["average_duration_seconds"] == 20.0
        from datetime import datetime

        assert datetime.fromisoformat(r["timestamp"]).tzinfo is not None

    def test_performance_kpis_empty(self):
        r = KPIAnalyzer.calculate_performance_kpis([], hours=48)
        assert r["total_tests"] == 0 and r["passed_tests"] == 0
        assert r["success_rate"] == 0 and r["period_hours"] == 48

    def test_kpis_by_alert_type_exact(self):
        metrics = [
            {"alert_type": "ransomware", "mttr_seconds": 100, "severity": 4},
            {"alert_type": "ransomware", "mttr_seconds": 200, "severity": 2},
            {"alert_type": "benign", "mttr_seconds": 50, "severity": 1},
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["period_hours"] == 24
        rw = r["by_alert_type"]["ransomware"]
        assert rw == {
            "count": 2,
            "avg_mttr_seconds": 150.0,
            "avg_severity": 3.0,
            "critical_count": 1,
            "critical_rate": 50.0,
        }
        b = r["by_alert_type"]["benign"]
        assert b["count"] == 1 and b["critical_count"] == 0 and b["critical_rate"] == 0

    def test_kpis_by_alert_type_mttr_dict_message(self):
        metrics = [{"alert_type": "x", "mttr_seconds": {"message": "MTTR: 42.5s"}, "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 42.5

    def test_kpis_by_alert_type_mttr_bad_message_zero(self):
        metrics = [{"alert_type": "x", "mttr_seconds": {"message": "no mttr"}, "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 0

    def test_kpis_by_alert_type_zero_and_over_window_excluded(self):
        metrics = [
            {"alert_type": "x", "mttr_seconds": 0, "severity": 1},
            {"alert_type": "x", "mttr_seconds": 24 * 3600 + 1, "severity": 1},
            {"alert_type": "x", "mttr_seconds": 24 * 3600, "severity": 1},
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 24 * 3600

    def test_kpis_by_alert_type_missing_alert_type_unknown(self):
        r = KPIAnalyzer.calculate_kpis_by_alert_type([{"mttr_seconds": 10, "severity": 1}])
        assert "unknown" in r["by_alert_type"]

    def test_critical_boundary_severity_4(self):
        metrics = [{"alert_type": "x", "mttr_seconds": 1, "severity": 4}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["critical_count"] == 1

    def test_service_success_classification(self):
        assert KPIAnalyzer._check_service_success("ok") is True
        assert KPIAnalyzer._check_service_success({"success": True}) is True
        assert KPIAnalyzer._check_service_success({"success": False}) is False
        assert KPIAnalyzer._check_service_success({}) is False
        assert KPIAnalyzer._check_service_success(42) is False
        assert KPIAnalyzer._check_service_success(None) is False

    def test_cortex_success_either_job(self):
        assert KPIAnalyzer._check_cortex_success({"cortex_hash_job": "id1"}) is True
        assert KPIAnalyzer._check_cortex_success({"cortex_ip_job": "id2"}) is True
        assert KPIAnalyzer._check_cortex_success({}) is False
        assert KPIAnalyzer._check_cortex_success({"cortex_hash_job": {"success": False}}) is False

    def test_classify_metric_exact(self):
        m = {
            "thehive_case_id": "c1",
            "cortex_ip_job": "j1",
            "misp_results": {"success": True},
        }
        assert KPIAnalyzer._classify_metric_services(m) == {
            "thehive": "success",
            "cortex": "success",
            "misp": "success",
            "elasticsearch": "success",
        }

    def test_classify_metric_all_failure(self):
        assert KPIAnalyzer._classify_metric_services({}) == {
            "thehive": "failure",
            "cortex": "failure",
            "misp": "failure",
            "elasticsearch": "success",
        }

    def test_service_integration_kpis_exact(self):
        metrics = [
            {
                "thehive_case_id": "c1",
                "cortex_hash_job": "j",
                "misp_results": {"success": True},
            },
            {"thehive_case_id": "", "misp_results": {"success": False}},
        ]
        r = KPIAnalyzer.calculate_service_integration_kpis(metrics)
        assert r["period_hours"] == 24
        sv = r["services"]
        assert sv["thehive"] == {
            "success_count": 1,
            "failure_count": 1,
            "total": 2,
            "success_rate_percent": 50.0,
        }
        assert sv["cortex"]["success_count"] == 1
        assert sv["cortex"]["failure_count"] == 1
        assert sv["misp"]["success_count"] == 1
        assert sv["elasticsearch"]["success_count"] == 2
        assert sv["elasticsearch"]["failure_count"] == 0
        assert sv["elasticsearch"]["success_rate_percent"] == 100.0

    def test_comprehensive_kpis_structure(self):
        r = KPIAnalyzer.calculate_comprehensive_kpis({"m": 1}, {"p": 2}, {"h": 3})
        assert r["mttr"] == {"m": 1}
        assert r["performance"] == {"p": 2}
        assert r["health"] == {"h": 3}
        from datetime import datetime

        assert datetime.fromisoformat(r["timestamp"]).tzinfo is not None

    def test_health_score_adds_timestamp(self):
        a = self._analyzer()
        r = a.calculate_health_score(10, 10, 10, 100)
        assert "timestamp" in r
        # cpu/mem/disk scores = 90 each; overall = 90*0.3+90*0.3+90*0.2+100*0.2 = 92
        assert r["overall_score"] == 92.0
        assert r["status"] == "excellent"

    def test_mttr_delegates(self):
        a = self._analyzer()
        r = a.calculate_mttr_metrics([10, 20])
        assert r["total_executions"] == 2
        assert r["mean"] == 15

    def test_performance_kpis_single_test(self):
        r = KPIAnalyzer.calculate_performance_kpis(
            [{"status": "passed", "coverage_percent": 50, "duration_seconds": 5}]
        )
        assert r["total_tests"] == 1
        assert r["passed_tests"] == 1
        assert r["success_rate"] == 100.0  # kills total>0 -> >1
        assert r["average_coverage"] == 50 and r["average_duration_seconds"] == 5

    def test_health_score_timestamp_is_utc(self):
        a = self._analyzer()
        r = a.calculate_health_score(10, 10, 10, 100)
        from datetime import datetime

        ts = datetime.fromisoformat(r["timestamp"])
        assert ts.tzinfo is not None  # kills now(UTC)->now(None) and ts=None

    def test_kpis_missing_fields_use_defaults(self):
        r = KPIAnalyzer.calculate_kpis_by_alert_type([{"alert_type": "x"}])
        e = r["by_alert_type"]["x"]
        assert e["count"] == 1
        assert e["avg_mttr_seconds"] == 0  # missing mttr_seconds -> 0 -> excluded
        assert e["avg_severity"] == 0  # missing severity -> 0
        assert e["critical_count"] == 0

    def test_kpis_mttr_dict_without_message_key(self):
        metrics = [{"alert_type": "x", "mttr_seconds": {"other": "v"}, "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 0

    def test_kpis_mttr_prefix_message(self):
        # "noise MTTR:42.5s": split("MTTR:")[1] works; split(None)[1] fails
        metrics = [
            {"alert_type": "x", "mttr_seconds": {"message": "noise MTTR:42.5s"}, "severity": 1}
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 42.5

    def test_kpis_mttr_non_numeric_type_stays_zero(self):
        metrics = [{"alert_type": "x", "mttr_seconds": "weird", "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 0

    def test_kpis_mttr_one_included(self):
        metrics = [{"alert_type": "x", "mttr_seconds": 1, "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 1  # 0 < mttr, not 1 <

    def test_kpis_two_criticals_increment(self):
        metrics = [
            {"alert_type": "x", "mttr_seconds": 1, "severity": 4},
            {"alert_type": "x", "mttr_seconds": 1, "severity": 4},
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["critical_count"] == 2  # +=1, not =1

    def test_kpis_avg_severity_single(self):
        metrics = [{"alert_type": "x", "mttr_seconds": 1, "severity": 3}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_severity"] == 3.0  # count>0, not >1

    def test_kpis_round_precision_three_metrics(self):
        metrics = [
            {"alert_type": "x", "mttr_seconds": 100, "severity": 4},
            {"alert_type": "x", "mttr_seconds": 100, "severity": 1},
            {"alert_type": "x", "mttr_seconds": 101, "severity": 1},
        ]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        e = r["by_alert_type"]["x"]
        assert e["avg_mttr_seconds"] == 100.33  # round 2, not 3
        assert e["avg_severity"] == 2.0
        assert e["critical_rate"] == 33.33  # 1/3*100 -> 33.33, not 33.333

    def test_cortex_ip_job_truthy_but_unsuccessful(self):
        # `and` evaluates check; `or` returns truthy job -> wrong True
        assert KPIAnalyzer._check_cortex_success({"cortex_ip_job": {"success": False}}) is False

    def test_service_integration_single_metric_rates(self):
        r = KPIAnalyzer.calculate_service_integration_kpis(
            [{"thehive_case_id": "c1", "cortex_hash_job": "j", "misp_results": "ok"}]
        )
        for svc in ("thehive", "cortex", "misp", "elasticsearch"):
            assert r["services"][svc] == {
                "success_count": 1,
                "failure_count": 0,
                "total": 1,
                "success_rate_percent": 100.0,
            }

    def test_kpis_mttr_unparseable_message_stays_zero(self):
        # "MTTR:abc" -> float fails -> except -> mttr=0 (excluded)
        metrics = [{"alert_type": "x", "mttr_seconds": {"message": "MTTR:abc s"}, "severity": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["avg_mttr_seconds"] == 0

    def test_kpis_by_alert_type_timestamp_is_utc(self):
        from datetime import datetime

        r = KPIAnalyzer.calculate_kpis_by_alert_type([{"alert_type": "x", "severity": 1}])
        ts = datetime.fromisoformat(r["timestamp"])
        assert ts.tzinfo is not None

    def test_service_integration_timestamp_is_utc(self):
        from datetime import datetime

        r = KPIAnalyzer.calculate_service_integration_kpis([])
        ts = datetime.fromisoformat(r["timestamp"])
        assert ts.tzinfo is not None

    def test_service_integration_empty_zero_rate(self):
        r = KPIAnalyzer.calculate_service_integration_kpis([])
        for svc in ("thehive", "cortex", "misp", "elasticsearch"):
            assert r["services"][svc]["success_rate_percent"] == 0  # not 1

    def test_service_integration_round_2dp(self):
        metrics = [
            {"thehive_case_id": "c1"},
            {"thehive_case_id": "c2"},
            {"other": 1},
        ]
        r = KPIAnalyzer.calculate_service_integration_kpis(metrics)
        assert r["services"]["thehive"]["success_rate_percent"] == 66.67

    def test_kpis_critical_rate_single(self):
        metrics = [{"alert_type": "x", "severity": 4, "mttr_seconds": 1}]
        r = KPIAnalyzer.calculate_kpis_by_alert_type(metrics)
        assert r["by_alert_type"]["x"]["critical_rate"] == 100.0  # count>0, not >1
