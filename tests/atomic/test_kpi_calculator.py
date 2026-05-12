#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for KPI Calculator
Tests individual KPI calculation functions in isolation
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
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
            shutil.rmtree(self.test_dir)

    def test_validate_log_file_exists_valid(self):
        """Test log file validation when file exists and is valid"""
        # Create a valid log file
        with open(self.test_log_path, 'w') as f:
            f.write("[2025-05-08 10:00:00] STEP: Alert received\n")
            f.write("[2025-05-08 10:01:30] STEP: Containment executed\n")
        
        # Mocks LOG_PATH to point to our test file
        from soar_lab.data import calc_kpis
        original_log_path = calc_kpis.LOG_PATH
        calc_kpis.LOG_PATH = Path(self.test_log_path)
        
        try:
            result = validate_log_file(self.test_log_path)
            self.assertTrue(result)
        finally:
            calc_kpis.LOG_PATH = original_log_path

    def test_validate_log_file_not_exists(self):
        """Test log file validation when file doesn't exist"""
        non_existent_path = "/non/existent/path.log"
        
        # Mocks LOG_PATH to point to non-existent file
        from soar_lab.data import calc_kpis
        original_log_path = calc_kpis.LOG_PATH
        calc_kpis.LOG_PATH = Path(non_existent_path)
        
        with self.assertRaises(FileNotFoundError):
            validate_log_file(non_existent_path)
        
        calc_kpis.LOG_PATH = original_log_path

    def test_parse_log_file_valid(self):
        """Test parsing a valid log file"""
        # Create test log
        entries = [
            "[2025-05-08 10:00:00] STEP: Alert received",
            "[2025-05-08 10:01:30] STEP: Containment executed",
            "[2025-05-08 10:02:45] STEP: Investigation started"
        ]
        with open(self.test_log_path, 'w') as f:
            for entry in entries:
                f.write(f"{entry}\n")
        
        parsed = parse_log_file(self.test_log_path)
        self.assertEqual(len(parsed), 3)
        self.assertIn('Alert received', parsed)
        self.assertIn('Containment executed', parsed)
        self.assertIn('Investigation started', parsed)
        self.assertEqual(len(parsed['Alert received']), 1)
        self.assertEqual(len(parsed['Containment executed']), 1)
        self.assertEqual(len(parsed['Investigation started']), 1)

    def test_parse_log_file_empty(self):
        """Test parsing an empty log file"""
        # Create empty file
        with open(self.test_log_path, 'w') as f:
            pass
        
        parsed = parse_log_file(self.test_log_path)
        self.assertEqual(len(parsed), 0)

    def test_parse_log_file_mixed_format(self):
        """Test parsing log file with mixed valid and invalid entries"""
        # Create test log with mixed entries
        with open(self.test_log_path, 'w') as f:
            f.write("[2025-05-08 10:00:00] STEP: Alert received\n")
            f.write("Invalid entry without proper format\n")
            f.write("[2025-05-08 10:01:30] STEP: Containment executed\n")
        
        parsed = parse_log_file(self.test_log_path)
        self.assertEqual(len(parsed), 2)  # Only valid entries should be parsed

    def test_calculate_execution_times_single(self):
        """Test execution time calculation with single execution"""
        # Create test log with single execution
        start_time = datetime(2025, 5, 8, 10, 0, 0)
        end_time = datetime(2025, 5, 8, 10, 1, 30)
        
        with open(self.test_log_path, 'w') as f:
            f.write(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Alert received\n")
            f.write(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Containment executed\n")
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 1)
        self.assertAlmostEqual(times[0], 90.0, places=1)

    def test_calculate_execution_times_multiple(self):
        """Test execution time calculation with multiple executions"""
        # Create test log with multiple executions
        with open(self.test_log_path, 'w') as f:
            f.write("[2025-05-08 10:00:00] STEP: Alert received\n")
            f.write("[2025-05-08 10:01:30] STEP: Containment executed\n")
            f.write("[2025-05-08 11:00:00] STEP: Alert received\n")
            f.write("[2025-05-08 11:02:00] STEP: Containment executed\n")
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 2)
        self.assertAlmostEqual(times[0], 90.0, places=1)
        self.assertAlmostEqual(times[1], 120.0, places=1)

    def test_calculate_execution_times_incomplete(self):
        """Test execution time calculation with incomplete pairs"""
        # Create test log with incomplete execution pairs
        with open(self.test_log_path, 'w') as f:
            f.write("[2025-05-08 10:00:00] STEP: Alert received\n")
            f.write("[2025-05-08 10:01:30] STEP: Containment executed\n")
            f.write("[2025-05-08 11:00:00] STEP: Alert received\n")  # Missing end
        
        parsed = parse_log_file(self.test_log_path)
        times = calculate_execution_times(parsed)
        self.assertEqual(len(times), 1)  # Only complete pairs should be calculated

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
        """Test metrics calculation with empty data"""
        metrics = calculate_metrics([])
        
        self.assertEqual(metrics['total_executions'], 0)
        self.assertEqual(metrics['mean'], 0.0)
        self.assertEqual(metrics['min'], 0.0)
        self.assertEqual(metrics['max'], 0.0)
        self.assertEqual(metrics['median'], 0.0)

    def test_calculate_metrics_single(self):
        """Test metrics calculation with single data point"""
        times = [75.0]
        metrics = calculate_metrics(times)
        
        self.assertEqual(metrics['total_executions'], 1)
        self.assertAlmostEqual(metrics['mean'], 75.0, places=1)
        self.assertEqual(metrics['min'], 75.0)
        self.assertEqual(metrics['max'], 75.0)
        self.assertEqual(metrics['median'], 75.0)

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

    def test_save_metrics_custom_path(self):
        """Test saving metrics to custom path"""
        metrics = {'total_executions': 3, 'mean': 85.0}
        custom_path = Path(self.test_results_path) / 'custom_kpis.csv'
        
        save_metrics(metrics, custom_path)
        self.assertTrue(custom_path.exists())

    def test_print_metrics_summary(self):
        """Test printing metrics summary"""
        metrics = {
            'total_executions': 10,
            'mean': 95.5,
            'median': 90.0,
            'p50': 90.0,
            'p90': 120.0,
            'min': 30.0,
            'max': 180.0,
            'std_dev': 25.0
        }
        
        # This test just ensures function doesn't crash
        try:
            print_metrics_summary(metrics)
            function_executed = True
        except Exception:
            function_executed = False
        
        self.assertTrue(function_executed)

    def test_print_metrics_summary_empty(self):
        """Test printing metrics summary with empty metrics"""
        empty_metrics = {
            'total_executions': 0,
            'mean': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0
        }
        
        # This test just ensures function handles empty data gracefully
        try:
            print_metrics_summary(empty_metrics)
            function_executed = True
        except Exception:
            function_executed = False
        
        self.assertTrue(function_executed)


if __name__ == '__main__':
    unittest.main()
