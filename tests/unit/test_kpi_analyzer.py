#!/usr/bin/env python3
"""
Unit tests for kpi_analyzer.py
"""

import pytest
from unittest.mock import Mock

from soar_lab.services.kpi_analyzer import KPIAnalyzer


class TestKPIAnalyzer:
    """Test KPIAnalyzer"""

    def test_initialization_success(self):
        """Test successful initialization with statistical_calculator"""
        mock_stat_calc = Mock()
        
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        assert analyzer._statistical_calculator == mock_stat_calc

    def test_requires_statistical_calculator(self):
        """Test that statistical_calculator is required"""
        with pytest.raises(ValueError, match="statistical_calculator is required"):
            KPIAnalyzer(statistical_calculator=None)

    def test_calculate_performance_kpis(self):
        """Test calculating performance KPIs"""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        test_results = [
            {"status": "passed", "coverage_percent": 80, "duration_seconds": 5},
            {"status": "passed", "coverage_percent": 90, "duration_seconds": 3},
            {"status": "failed", "coverage_percent": 70, "duration_seconds": 2}
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
        """Test calculating performance KPIs with empty results"""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        result = analyzer.calculate_performance_kpis([], hours=24)
        
        assert result["total_tests"] == 0
        assert result["passed_tests"] == 0
        assert result["success_rate"] == 0
        assert result["average_coverage"] == 0
        assert result["average_duration_seconds"] == 0

    def test_calculate_performance_kpis_missing_fields(self):
        """Test calculating performance KPIs with missing fields"""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        test_results = [
            {"status": "passed"},
            {"coverage_percent": 80},
            {"duration_seconds": 5}
        ]
        
        result = analyzer.calculate_performance_kpis(test_results, hours=24)
        
        assert result["total_tests"] == 3
        assert result["passed_tests"] == 1
        assert result["average_coverage"] == 26.67
        assert result["average_duration_seconds"] == 1.67

    def test_calculate_health_score(self):
        """Test calculating health score"""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_health_score.return_value = {
            "overall_score": 85,
            "status": "good"
        }
        
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        result = analyzer.calculate_health_score(
            cpu_percent=50,
            memory_percent=60,
            disk_percent=70,
            test_coverage=85.5
        )
        
        assert result["overall_score"] == 85
        assert result["status"] == "good"
        assert "timestamp" in result
        mock_stat_calc.calculate_health_score.assert_called_once_with(
            cpu_percent=50,
            memory_percent=60,
            disk_percent=70,
            test_coverage=85.5
        )

    def test_calculate_mttr_metrics(self):
        """Test calculating MTTR metrics"""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_statistical_metrics.return_value = {
            "mean": 120.5,
            "median": 100,
            "p90": 200
        }
        
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        execution_times = [100, 120, 150, 200]
        result = analyzer.calculate_mttr_metrics(execution_times)
        
        assert result["mean"] == 120.5
        assert result["median"] == 100
        assert result["p90"] == 200
        mock_stat_calc.calculate_statistical_metrics.assert_called_once_with(execution_times)

    def test_calculate_mttr_metrics_empty(self):
        """Test calculating MTTR metrics with empty list"""
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_statistical_metrics.return_value = {
            "mean": 0,
            "median": 0,
            "p90": 0
        }
        
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        result = analyzer.calculate_mttr_metrics([])
        
        assert result["mean"] == 0
        mock_stat_calc.calculate_statistical_metrics.assert_called_once_with([])

    def test_calculate_comprehensive_kpis(self):
        """Test calculating comprehensive KPIs"""
        mock_stat_calc = Mock()
        analyzer = KPIAnalyzer(statistical_calculator=mock_stat_calc)
        
        mttr_metrics = {"mean": 120.5}
        performance_kpis = {"success_rate": 90}
        health_score = {"overall_score": 85}
        
        result = analyzer.calculate_comprehensive_kpis(
            mttr_metrics=mttr_metrics,
            performance_kpis=performance_kpis,
            health_score=health_score
        )
        
        assert result["mttr"] == mttr_metrics
        assert result["performance"] == performance_kpis
        assert result["health"] == health_score
        assert "timestamp" in result
