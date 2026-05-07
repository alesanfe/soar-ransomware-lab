#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for KPI Calculator
Tests individual KPI calculation functions in isolation
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from calc_kpis import (
    validate_log_file,
    parse_log_file,
    calculate_execution_times,
    calculate_metrics,
    save_metrics,
    print_metrics_summary
)


class TestKPICalculatorAtomic(unittest.TestCase):
    """Atomic tests for individual KPI calculation functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_log_file = os.path.join(self.temp_dir, "test_kpi.log")
        
        # Create sample log data
        self.sample_log_entries = [
            "2025-01-15 10:00:00 - INFO - Alert received: ALERT-001",
            "2025-01-15 10:05:00 - INFO - Case created: CASE-001",
            "2025-01-15 10:10:00 - INFO - Containment initiated",
            "2025-01-15 10:15:00 - INFO - Containment completed",
            "2025-01-15 10:20:00 - INFO - Alert resolved",
            "2025-01-15 11:00:00 - INFO - Alert received: ALERT-002",
            "2025-01-15 11:05:00 - INFO - Case created: CASE-002",
            "2025-01-15 11:30:00 - INFO - Alert resolved (no containment)",
        ]
        
        with open(self.test_log_file, 'w') as f:
            for entry in self.sample_log_entries:
                f.write(entry + '\n')

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_log_file):
            os.remove(self.test_log_file)
        os.rmdir(self.temp_dir)

    def test_validate_log_file_valid(self):
        """Test log file validation with valid file"""
        # Create a valid log file
        valid_log = os.path.join(self.temp_dir, "valid.log")
        with open(valid_log, 'w') as f:
            f.write("Test log entry\n")
        
        # Temporarily change LOG_PATH to our test file
        import calc_kpis
        original_path = calc_kpis.LOG_PATH
        calc_kpis.LOG_PATH = Path(valid_log)
        
        try:
            result = validate_log_file()
            self.assertEqual(result, Path(valid_log))
        finally:
            calc_kpis.LOG_PATH = original_path
        
        os.remove(valid_log)

    def test_validate_log_file_nonexistent(self):
        """Test log file validation with nonexistent file"""
        # Temporarily change LOG_PATH to nonexistent file
        import calc_kpis
        original_path = calc_kpis.LOG_PATH
        calc_kpis.LOG_PATH = Path("nonexistent.log")
        
        try:
            with self.assertRaises(FileNotFoundError):
                validate_log_file()
        finally:
            calc_kpis.LOG_PATH = original_path

    def test_parse_log_file_valid_format(self):
        """Test log file parsing with valid format"""
        # Create log with expected format
        valid_log = os.path.join(self.temp_dir, "valid_format.log")
        log_content = [
            "[2025-01-15 10:00:00] STEP: Alert received",
            "[2025-01-15 10:05:00] STEP: Case creation",
            "[2025-01-15 10:10:00] STEP: Containment executed",
        ]
        
        with open(valid_log, 'w') as f:
            for entry in log_content:
                f.write(entry + '\n')
        
        alert_steps = parse_log_file(Path(valid_log))
        
        # Should return dict with step names as keys
        self.assertIsInstance(alert_steps, dict)
        self.assertIn("Alert received", alert_steps)
        self.assertIn("Case creation", alert_steps)
        self.assertIn("Containment executed", alert_steps)
        
        # Each step should have datetime objects
        for step_name, timestamps in alert_steps.items():
            self.assertIsInstance(timestamps, list)
            for ts in timestamps:
                self.assertIsInstance(ts, datetime)
        
        os.remove(valid_log)

    def test_parse_log_file_empty_file(self):
        """Test log file parsing with empty file"""
        empty_log = os.path.join(self.temp_dir, "empty.log")
        with open(empty_log, 'w') as f:
            pass  # Create empty file
        
        alert_steps = parse_log_file(Path(empty_log))
        self.assertEqual(alert_steps, {})
        
        os.remove(empty_log)

    def test_parse_log_file_invalid_format(self):
        """Test log file parsing with invalid format"""
        invalid_log = os.path.join(self.temp_dir, "invalid.log")
        invalid_content = [
            "2025-01-15 10:00:00 - INFO - Alert received",  # Missing brackets
            "[Invalid timestamp] STEP: Alert received",  # Invalid timestamp
            "Random log line without format",
        ]
        
        with open(invalid_log, 'w') as f:
            for entry in invalid_content:
                f.write(entry + '\n')
        
        alert_steps = parse_log_file(Path(invalid_log))
        self.assertEqual(alert_steps, {})  # Should return empty dict
        
        os.remove(invalid_log)

    def test_parse_log_file_unicode_error(self):
        """Test log file parsing with Unicode error"""
        unicode_log = os.path.join(self.temp_dir, "unicode.log")
        
        # Create file with invalid UTF-8
        with open(unicode_log, 'wb') as f:
            f.write(b"[2025-01-15 10:00:00] STEP: Alert received\n")
            f.write(b'\xff\xfe')  # Invalid UTF-8 bytes
        
        with self.assertRaises(UnicodeDecodeError):
            parse_log_file(Path(unicode_log))
        
        os.remove(unicode_log)

    def test_calculate_execution_times_valid_data(self):
        """Test execution times calculation with valid data"""
        alert_steps = {
            'Alert received': [datetime(2025, 1, 15, 10, 0, 0), datetime(2025, 1, 15, 11, 0, 0)],
            'Containment executed': [datetime(2025, 1, 15, 10, 30, 0), datetime(2025, 1, 15, 11, 45, 0)]
        }
        
        execution_times = calculate_execution_times(alert_steps)
        
        # Should calculate time differences in seconds
        self.assertIsInstance(execution_times, list)
        self.assertEqual(len(execution_times), 2)
        
        # First alert: 30 minutes = 1800 seconds
        self.assertAlmostEqual(execution_times[0], 1800.0, places=1)
        # Second alert: 45 minutes = 2700 seconds
        self.assertAlmostEqual(execution_times[1], 2700.0, places=1)

    def test_calculate_execution_times_no_alerts(self):
        """Test execution times calculation with no alerts"""
        alert_steps = {
            'Case creation': [datetime(2025, 1, 15, 10, 5, 0)],
            'Containment executed': [datetime(2025, 1, 15, 10, 30, 0)]
        }
        
        execution_times = calculate_execution_times(alert_steps)
        self.assertEqual(execution_times, [])

    def test_calculate_execution_times_no_containment(self):
        """Test execution times calculation with no containment"""
        alert_steps = {
            'Alert received': [datetime(2025, 1, 15, 10, 0, 0)],
            'Case creation': [datetime(2025, 1, 15, 10, 5, 0)]
        }
        
        execution_times = calculate_execution_times(alert_steps)
        self.assertEqual(execution_times, [])

    def test_calculate_execution_times_mismatched_counts(self):
        """Test execution times with mismatched alert/containment counts"""
        alert_steps = {
            'Alert received': [datetime(2025, 1, 15, 10, 0, 0), datetime(2025, 1, 15, 11, 0, 0)],
            'Containment executed': [datetime(2025, 1, 15, 10, 30, 0)]  # Only one containment
        }
        
        execution_times = calculate_execution_times(alert_steps)
        # Should only calculate for matching pairs
        self.assertEqual(len(execution_times), 1)
        self.assertAlmostEqual(execution_times[0], 1800.0, places=1)  # 30 minutes = 1800 seconds

    def test_calculate_metrics_valid_data(self):
        """Test metrics calculation with valid data"""
        execution_times = [30.0, 45.0, 60.0, 15.0, 90.0]  # in minutes
        
        metrics = calculate_metrics(execution_times)
        
        # Should be a dictionary
        self.assertIsInstance(metrics, dict)
        
        # Should contain expected keys
        expected_keys = [
            "total_executions",
            "mean",
            "median",
            "p50",
            "p90",
            "min",
            "max",
            "std_dev"
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)

    def test_calculate_metrics_data_types(self):
        """Test metrics calculation data types"""
        execution_times = [30.0, 45.0, 60.0]
        
        metrics = calculate_metrics(execution_times)
        
        # Check data types
        self.assertIsInstance(metrics["total_executions"], int)
        self.assertIsInstance(metrics["mean"], (int, float))
        self.assertIsInstance(metrics["median"], (int, float))
        self.assertIsInstance(metrics["p50"], (int, float))
        self.assertIsInstance(metrics["p90"], (int, float))
        self.assertIsInstance(metrics["min"], (int, float))
        self.assertIsInstance(metrics["max"], (int, float))
        self.assertIsInstance(metrics["std_dev"], (int, float))

    def test_calculate_metrics_empty_data(self):
        """Test metrics calculation with empty data"""
        execution_times = []
        
        metrics = calculate_metrics(execution_times)
        
        self.assertEqual(metrics["total_executions"], 0)

    def test_calculate_metrics_single_value(self):
        """Test metrics calculation with single value"""
        execution_times = [30.0]
        
        metrics = calculate_metrics(execution_times)
        
        self.assertEqual(metrics["total_executions"], 1)
        self.assertEqual(metrics["mean"], 30.0)
        self.assertEqual(metrics["median"], 30.0)
        self.assertEqual(metrics["p50"], 30.0)
        self.assertEqual(metrics["min"], 30.0)
        self.assertEqual(metrics["max"], 30.0)
        self.assertEqual(metrics["std_dev"], 0.0)

    def test_save_metrics_structure(self):
        """Test save metrics to CSV file"""
        metrics = {
            "total_executions": 5,
            "mean": 45.0,
            "median": 40.0,
            "p50": 40.0,
            "p90": 80.0,
            "min": 15.0,
            "max": 90.0,
            "std_dev": 25.0
        }
        
        output_file = Path(self.temp_dir) / "test_metrics.csv"
        
        save_metrics(metrics, output_file)
        
        # Check file was created
        self.assertTrue(output_file.exists())
        
        # Check file content
        with open(output_file, 'r') as f:
            content = f.read()
            self.assertIn("total_executions", content)
            self.assertIn("5", content)
        
        os.remove(output_file)

    def test_print_metrics_summary_valid(self):
        """Test print metrics summary with valid data"""
        metrics = {
            "total_executions": 5,
            "mean": 45.0,
            "p50": 40.0,
            "p90": 80.0,
            "std_dev": 25.0
        }
        
        # Should not raise exception
        try:
            print_metrics_summary(metrics)
        except Exception as e:
            self.fail(f"print_metrics_summary raised exception: {e}")

    def test_print_metrics_summary_empty(self):
        """Test print metrics summary with empty data"""
        metrics = {
            "total_executions": 0
        }
        
        # Should not raise exception
        try:
            print_metrics_summary(metrics)
        except Exception as e:
            self.fail(f"print_metrics_summary raised exception: {e}")

    def test_parse_log_file_multiple_same_steps(self):
        """Test log file parsing with multiple occurrences of same step"""
        multiple_log = os.path.join(self.temp_dir, "multiple.log")
        log_content = [
            "[2025-01-15 10:00:00] STEP: Alert received",
            "[2025-01-15 10:05:00] STEP: Alert received",  # Second alert
            "[2025-01-15 10:10:00] STEP: Case creation",
            "[2025-01-15 10:15:00] STEP: Containment executed",
            "[2025-01-15 10:20:00] STEP: Containment executed",  # Second containment
        ]
        
        with open(multiple_log, 'w') as f:
            for entry in log_content:
                f.write(entry + '\n')
        
        alert_steps = parse_log_file(Path(multiple_log))
        
        # Should have multiple timestamps for steps that appear multiple times
        self.assertEqual(len(alert_steps["Alert received"]), 2)
        self.assertEqual(len(alert_steps["Containment executed"]), 2)
        self.assertEqual(len(alert_steps["Case creation"]), 1)
        
        os.remove(multiple_log)


if __name__ == '__main__':
    unittest.main()
