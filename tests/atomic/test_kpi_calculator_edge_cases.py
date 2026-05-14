#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for KPI Calculator (Corrected)
Tests individual KPI calculation functions in isolation
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from soar_lab.data.calc_kpis import (
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
        self.test_dir = tempfile.mkdtemp()
        self.test_log_path = os.path.join(self.test_dir, 'test_kpi.log')
        self.test_results_path = os.path.join(self.test_dir, 'results')
        os.makedirs(self.test_results_path, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.test_dir):
            import shutil
            try:
                shutil.rmtree(self.test_dir)
            except PermissionError:
                pass  # Handle Windows file locking issues

    def create_test_log(self, entries):
        """Create a test log file with specified entries"""
        with open(self.test_log_path, 'w') as f:
            for entry in entries:
                f.write(f"{entry}\n")

    def test_validate_log_file_not_exists(self):
        """Test validation with non-existent file"""
        with self.assertRaises(FileNotFoundError):
            validate_log_file("/non/existent/file.log")

    def test_validate_log_file_exists_valid(self):
        """Test validation with existing valid file"""
        self.create_test_log([
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed"
        ])
        result = validate_log_file(self.test_log_path)
        self.assertEqual(result, Path(self.test_log_path))

    def test_validate_log_file_empty(self):
        """Test validation with empty file"""
        self.create_test_log([])
        result = validate_log_file(self.test_log_path)
        self.assertEqual(result, Path(self.test_log_path))

    def test_validate_log_file_invalid_format(self):
        """Test validation with invalid format"""
        self.create_test_log([
            "Invalid log entry without timestamp",
            "Another invalid entry"
        ])
        result = validate_log_file(self.test_log_path)
        self.assertEqual(result, Path(self.test_log_path))

    def test_parse_log_file_valid(self):
        """Test parsing a valid log file"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed",
            "[2025-05-08 10:02:45] STEP: Investigation started"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        self.assertEqual(len(parsed), 3)
        
        # Check structure of parsed data
        for step_name in parsed:
            self.assertIsInstance(parsed[step_name], list)
            for entry in parsed[step_name]:
                self.assertIsInstance(entry, datetime)

    def test_parse_log_file_empty(self):
        """Test parsing an empty log file"""
        self.create_test_log([])
        
        parsed = parse_log_file(self.test_log_path)
        self.assertEqual(len(parsed), 0)

    def test_parse_log_file_invalid_entries(self):
        """Test parsing log file with some invalid entries"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "Invalid entry without proper format",
            "[2025-05-08 10:01:30] STEP: Containment executed"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        # Should only parse valid entries
        self.assertEqual(len(parsed), 2)

    def test_calculate_execution_times_single(self):
        """Test execution time calculation with single execution"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 1)
        self.assertAlmostEqual(times[0], 90.0, places=1)

    def test_calculate_execution_times_multiple(self):
        """Test execution time calculation with multiple executions"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed",
            "[2025-05-08 10:05:00] STEP: Alert received",
            "[2025-05-08 10:06:00] STEP: Containment executed",
            "[2025-05-08 10:10:00] STEP: Alert received",
            "[2025-05-08 10:12:30] STEP: Containment executed"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 3)
        self.assertAlmostEqual(times[0], 90.0, places=1)
        self.assertAlmostEqual(times[1], 60.0, places=1)
        self.assertAlmostEqual(times[2], 150.0, places=1)

    def test_calculate_execution_times_incomplete(self):
        """Test execution time calculation with incomplete pairs"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed",
            "[2025-05-08 10:05:00] STEP: Alert received",
            # Missing containment step
            "[2025-05-08 10:10:00] STEP: Alert received",
            "[2025-05-08 10:11:00] STEP: Containment executed"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        # Should only calculate complete pairs
        self.assertEqual(len(times), 2)

    def test_calculate_metrics_single(self):
        """Test metrics calculation with single execution time"""
        times = [120.0]
        metrics = calculate_metrics(times)
        
        self.assertEqual(metrics['total_executions'], 1)
        self.assertAlmostEqual(metrics['mean'], 120.0, places=1)
        self.assertEqual(metrics['min'], 120.0)
        self.assertEqual(metrics['max'], 120.0)
        self.assertEqual(metrics['median'], 120.0)

    def test_calculate_metrics_basic(self):
        """Test basic metrics calculation"""
        times = [90.0, 120.0, 150.0]
        metrics = calculate_metrics(times)
        
        self.assertEqual(metrics['total_executions'], 3)
        self.assertAlmostEqual(metrics['mean'], 120.0, places=1)
        self.assertEqual(metrics['min'], 90.0)
        self.assertEqual(metrics['max'], 150.0)
        self.assertEqual(metrics['median'], 120.0)

    def test_calculate_metrics_empty(self):
        """Test metrics calculation with empty list"""
        times = []
        metrics = calculate_metrics(times)
        
        self.assertEqual(metrics['total_executions'], 0)
        self.assertEqual(metrics['mean'], 0.0)
        self.assertEqual(metrics['min'], 0.0)
        self.assertEqual(metrics['max'], 0.0)
        self.assertEqual(metrics['median'], 0.0)

    def test_calculate_metrics_large_dataset(self):
        """Test metrics calculation with large dataset"""
        times = list(range(1, 101))  # 1 to 100 seconds
        metrics = calculate_metrics(times)
        
        self.assertEqual(metrics['total_executions'], 100)
        self.assertAlmostEqual(metrics['mean'], 50.5, places=1)
        self.assertEqual(metrics['min'], 1.0)
        self.assertEqual(metrics['max'], 100.0)
        self.assertEqual(metrics['median'], 50.5)

    def test_save_metrics(self):
        """Test saving metrics to CSV"""
        metrics = {
            'total_executions': 5,
            'mean': 100.5,
            'median': 95.0,
            'min': 45.0,
            'max': 180.0
        }
        
        csv_path = Path(self.test_results_path) / 'kpis.csv'
        save_metrics(metrics, csv_path)
        self.assertTrue(csv_path.exists())
        
        # Verify CSV content
        with open(csv_path, 'r') as f:
            content = f.read()
            self.assertIn('total_executions', content)
            self.assertIn('mean', content)
            self.assertIn('100.5', content)

    def test_save_metrics_file_creation(self):
        """Test saving metrics creates file in correct location"""
        metrics = {'total_executions': 1, 'mean': 60.0}
        
        csv_path = Path(self.test_results_path) / 'test_metrics.csv'
        save_metrics(metrics, csv_path)
        
        self.assertTrue(csv_path.exists())
        self.assertGreater(csv_path.stat().st_size, 0)

    def test_print_metrics_summary(self):
        """Test printing metrics summary"""
        metrics = {
            'total_executions': 5,
            'mean': 100.5,
            'median': 95.0,
            'p50': 95.0,
            'p90': 150.0,
            'min': 45.0,
            'max': 180.0,
            'std_dev': 25.0
        }
        
        # Capture stdout
        captured_output = StringIO()
        import sys
        original_stdout = sys.stdout
        sys.stdout = captured_output
        
        try:
            print_metrics_summary(metrics)
            output = captured_output.getvalue()
            
            # Check output contains expected information
            self.assertIn('Total ejecuciones', output)
            self.assertIn('100.5', output)
            self.assertIn('95.0', output)
            self.assertIn('150.0', output)
            
        finally:
            sys.stdout = original_stdout

    def test_print_metrics_summary_empty(self):
        """Test printing metrics summary with empty metrics"""
        metrics = {'total_executions': 0}
        
        # Capture log output instead of stdout
        with self.assertLogs('soar_lab.data.calc_kpis', level='WARNING') as log:
            print_metrics_summary(metrics)
        
        # Should have warning message about no metrics
        self.assertIn('No metrics to display', log.output[0])

    def test_edge_cases_invalid_timestamps(self):
        """Test parsing with invalid timestamps"""
        entries = [
            "[2025-13-08 10:00:00] STEP: Alert received",  # Invalid month
            "[2025-05-08 25:00:00] STEP: Containment executed",  # Invalid hour
            "[2025-05-08 10:00:00] STEP: Alert received",  # Valid
            "[2025-05-08 10:01:30] STEP: Containment executed"   # Valid
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        # Should only parse valid entries
        self.assertEqual(len(parsed), 2)

    def test_edge_cases_mixed_step_names(self):
        """Test parsing with different step names"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] ACTION: Containment executed",
            "[2025-05-08 10:02:45] PROCESS: Investigation started"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        # Only "STEP:" entries are parsed by current implementation
        self.assertEqual(len(parsed), 1)

    def test_edge_cases_very_long_execution_time(self):
        """Test calculation with very long execution time"""
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 18:00:00] STEP: Containment executed"  # 8 hours
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 1)
        self.assertAlmostEqual(times[0], 28800.0, places=1)  # 8 hours in seconds

    def test_edge_cases_fractional_seconds(self):
        """Test parsing timestamps with fractional seconds"""
        entries = [
            "[2025-05-08 10:00:00.123] STEP: Alert received",
            "[2025-05-08 10:01:30.456] STEP: Containment executed"
        ]
        self.create_test_log(entries)
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        # Fractional seconds are not supported, so no times should be parsed
        self.assertEqual(len(times), 0)


if __name__ == '__main__':
    unittest.main()
