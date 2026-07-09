#!/usr/bin/env python3
"""
Unit tests for soar_lab.domain.statistical_calculator
"""

import pytest
from datetime import datetime, timedelta

from soar_lab.domain.statistical_calculator import StatisticalCalculator


class TestStatisticalCalculator:
    """Test StatisticalCalculator pure domain logic"""

    def test_calculate_statistical_metrics_empty_list(self):
        """Test with empty list returns zeros"""
        result = StatisticalCalculator.calculate_statistical_metrics([])
        assert result['mean'] == 0
        assert result['median'] == 0
        assert result['std_dev'] == 0
        assert result['min'] == 0
        assert result['max'] == 0
        assert result['total_executions'] == 0
        assert result['p50'] == 0
        assert result['p90'] == 0
        assert result['mttr_seconds'] == 0
        assert result['mttr_minutes'] == 0

    def test_calculate_statistical_metrics_single_value(self):
        """Test with single value"""
        result = StatisticalCalculator.calculate_statistical_metrics([5.0])
        assert result['mean'] == 5.0
        assert result['median'] == 5.0
        assert result['std_dev'] == 0
        assert result['min'] == 5.0
        assert result['max'] == 5.0

    def test_calculate_statistical_metrics_multiple_values(self):
        """Test with multiple values"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result['mean'] == 3.0
        assert result['median'] == 3.0
        assert result['min'] == 1.0
        assert result['max'] == 5.0
        assert result['std_dev'] > 0

    def test_calculate_statistical_metrics_invalid_times(self):
        """Test with invalid times (all filtered out)"""
        values = [0.0, -1.0, 4000.0]  # All invalid
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result['total_executions'] == 0
        assert result['mean'] == 0.0

    def test_calculate_statistical_metrics_mixed_valid_invalid(self):
        """Test with mixed valid and invalid times"""
        values = [0.0, 1.0, 2.0, 3600.0, 3.0]  # 0, 3600 invalid
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result['total_executions'] == 3  # Only 1.0, 2.0, 3.0 valid
        assert result['mean'] == 2.0

    def test_calculate_statistical_metrics_percentiles(self):
        """Test percentile calculations"""
        values = list(range(100))
        result = StatisticalCalculator.calculate_statistical_metrics(values)
        assert result['p50'] == pytest.approx(49.5, rel=0.1)
        assert result['p90'] == pytest.approx(89, rel=0.1)

    def test_calculate_statistical_metrics_returns_dict(self):
        """Test returns dictionary with expected keys"""
        result = StatisticalCalculator.calculate_statistical_metrics([1.0, 2.0, 3.0])
        expected_keys = ['mean', 'median', 'std_dev', 'min', 'max', 'p50', 'p90', 'total_executions', 'mttr_seconds',
                         'mttr_minutes']
        for key in expected_keys:
            assert key in result

    def test_calculate_health_score_excellent(self):
        """Test health score calculation for excellent status"""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=10,
            memory_percent=20,
            disk_percent=30,
            test_coverage=90
        )
        assert result['overall_score'] >= 80
        assert result['status'] == "excellent"
        assert result['components']['cpu'] == 90
        assert result['components']['memory'] == 80
        assert result['components']['disk'] == 70
        assert result['components']['tests'] == 90

    def test_calculate_health_score_good(self):
        """Test health score calculation for good status"""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=30,
            memory_percent=40,
            disk_percent=50,
            test_coverage=70
        )
        assert 60 <= result['overall_score'] < 80
        assert result['status'] == "good"

    def test_calculate_health_score_warning(self):
        """Test health score calculation for warning status"""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=50,
            memory_percent=60,
            disk_percent=70,
            test_coverage=60
        )
        assert 40 <= result['overall_score'] < 60
        assert result['status'] == "warning"

    def test_calculate_health_score_critical(self):
        """Test health score calculation for critical status"""
        result = StatisticalCalculator.calculate_health_score(
            cpu_percent=90,
            memory_percent=95,
            disk_percent=98,
            test_coverage=10
        )
        assert result['overall_score'] < 40
        assert result['status'] == "critical"

    def test_calculate_execution_times_valid_data(self):
        """Test execution times calculation with valid data"""
        now = datetime.now()
        alert_steps = {
            'Alert received': [now, now + timedelta(seconds=10)],
            'Containment executed': [now + timedelta(seconds=5), now + timedelta(seconds=15)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 2
        assert result[0] == 5.0
        assert result[1] == 5.0

    def test_calculate_execution_times_missing_alerts(self):
        """Test execution times calculation with missing alerts"""
        alert_steps = {
            'Alert received': [],
            'Containment executed': [datetime.now()]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []

    def test_calculate_execution_times_missing_containment(self):
        """Test execution times calculation with missing containment"""
        alert_steps = {
            'Alert received': [datetime.now()],
            'Containment executed': []
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []

    def test_calculate_execution_times_mismatched_lengths(self):
        """Test execution times calculation with mismatched lengths"""
        now = datetime.now()
        alert_steps = {
            'Alert received': [now, now + timedelta(seconds=10), now + timedelta(seconds=20)],
            'Containment executed': [now + timedelta(seconds=5)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 1  # Only one pair
        assert result[0] == 5.0

    def test_calculate_execution_times_negative_delta(self):
        """Test execution times calculation with negative delta (filtered out)"""
        now = datetime.now()
        alert_steps = {
            'Alert received': [now + timedelta(seconds=10)],
            'Containment executed': [now + timedelta(seconds=5)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert result == []  # Negative delta filtered out

    def test_calculate_execution_times_started_passed_pairs(self):
        """Test execution times calculation with STARTED/PASSED pairs"""
        now = datetime.now()
        alert_steps = {
            'STEP 1 STARTED': [now, now + timedelta(seconds=10)],
            'STEP 1 PASSED': [now + timedelta(seconds=5), now + timedelta(seconds=15)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 2
        assert result[0] == 5.0
        assert result[1] == 5.0

    def test_calculate_execution_times_step1_keys_fallback(self):
        """Test execution times calculation with step1 keys fallback"""
        now = datetime.now()
        alert_steps = {
            'Sending alert': [now, now + timedelta(seconds=10), now + timedelta(seconds=20)]
        }
        result = StatisticalCalculator.calculate_execution_times(alert_steps)
        assert len(result) == 2  # Inter-arrival times

    def test_calculate_statistical_metrics_p90_idx_edge_case(self):
        """Test p90 calculation with edge case where p90_idx could be negative"""
        # This tests line 61 where p90_idx < 0 check happens
        result = StatisticalCalculator.calculate_statistical_metrics([1.0])
        assert result['p90'] == 1.0  # With single value, p90 should be that value
