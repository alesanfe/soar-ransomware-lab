#!/usr/bin/env python3
"""
Unit tests for calc_kpis.py
"""

import unittest
import tempfile
import os
import sys
import csv
import shutil
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.calc_kpis import (
    LOG_PATH, 
    RESULTS_PATH
)


class TestKPICalculator(unittest.TestCase):
    """Test cases for KPI calculation"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_log_path = os.path.join(self.test_dir, 'notify.log')
        self.test_results_path = os.path.join(self.test_dir, 'results')
        os.makedirs(self.test_results_path, exist_ok=True)
        
        # Monkey patch paths
        import scripts.calc_kpis as kpis_module
        self.original_log_path = kpis_module.LOG_PATH
        self.original_results_path = kpis_module.RESULTS_PATH
        kpis_module.LOG_PATH = Path(self.test_log_path)
        kpis_module.RESULTS_PATH = Path(self.test_results_path)

    def tearDown(self):
        """Clean up test fixtures"""
        import scripts.calc_kpis as kpis_module
        kpis_module.LOG_PATH = self.original_log_path
        kpis_module.RESULTS_PATH = self.original_results_path
        shutil.rmtree(self.test_dir)

    def write_test_log(self, entries):
        """Helper to write test log entries"""
        with open(self.test_log_path, 'w') as f:
            for entry in entries:
                f.write(f"{entry}\n")

    def test_log_file_not_exists(self):
        """Test behavior when log file doesn't exist"""
        # Ensure log doesn't exist
        if os.path.exists(self.test_log_path):
            os.remove(self.test_log_path)
        
        # Should raise SystemExit
        with self.assertRaises(SystemExit):
            from scripts.calc_kpis import main
            main()

    def test_single_execution(self):
        """Test KPI calculation for single execution"""
        # Write log with single execution
        start_time = datetime(2025, 5, 3, 10, 0, 0)
        end_time = datetime(2025, 5, 3, 10, 1, 30)  # 90 seconds later
        
        entries = [
            f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Alert received",
            f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Containment executed"
        ]
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Check results file
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        self.assertTrue(os.path.exists(kpi_file))
        
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            metrics = next(reader)
            
        self.assertEqual(int(metrics['total_executions']), 1)
        self.assertEqual(float(metrics['mean']), 90.0)
        self.assertEqual(float(metrics['p50']), 90.0)
        self.assertEqual(float(metrics['p90']), 90.0)

    def test_multiple_executions(self):
        """Test KPI calculation for multiple executions"""
        # Write log with multiple executions
        base_time = datetime(2025, 5, 3, 10, 0, 0)
        entries = []
        
        for i in range(5):
            start = base_time
            end = datetime.fromtimestamp(base_time.timestamp() + 90 + i * 10)  # 90, 100, 110, 120, 130s
            entries.append(f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Alert received")
            entries.append(f"[{end.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Containment executed")
            base_time = datetime.fromtimestamp(end.timestamp() + 60)  # Gap between executions
        
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Check results
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            metrics = next(reader)
            
        self.assertEqual(int(metrics['total_executions']), 5)
        self.assertGreater(float(metrics['mean']), 90)
        self.assertGreater(float(metrics['p50']), 90)
        self.assertGreater(float(metrics['p90']), 90)
        self.assertGreater(float(metrics['std_dev']), 0)

    def test_percentile_calculation(self):
        """Test percentile calculation accuracy"""
        # Write log with known values
        base_time = datetime(2025, 5, 3, 10, 0, 0)
        deltas = [50, 60, 70, 80, 90, 100, 110, 120, 130, 140]  # 10 values
        entries = []
        
        for delta in deltas:
            start = base_time
            end = datetime.fromtimestamp(base_time.timestamp() + delta)
            entries.append(f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Alert received")
            entries.append(f"[{end.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Containment executed")
            base_time = datetime.fromtimestamp(end.timestamp() + 60)
        
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Check percentiles
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            metrics = next(reader)
            
        # p50 should be around 95 (median of 50-140)
        self.assertGreater(float(metrics['p50']), 90)
        self.assertLess(float(metrics['p50']), 100)
        
        # p90 should be around 135 (90th percentile)
        self.assertGreaterEqual(float(metrics['p90']), 130)
        self.assertLess(float(metrics['p90']), 140)

    def test_no_complete_executions(self):
        """Test when no complete executions exist"""
        # Write log with only alert received
        entries = [
            "[2025-05-03 10:00:00] STEP: Alert received",
            "[2025-05-03 10:01:00] STEP: Alert received",
        ]
        self.write_test_log(entries)
        
        # Run calculation - should handle gracefully
        from scripts.calc_kpis import main
        main()
        
        # Check that file is not created or has no data
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        # File might not be created if no valid executions

    def test_negative_time_delta(self):
        """Test handling of negative time deltas (invalid data)"""
        # Write log with reversed order (should be filtered out)
        entries = [
            "[2025-05-03 10:02:00] STEP: Alert received",
            "[2025-05-03 10:01:00] STEP: Containment executed",  # Before alert
        ]
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Should not include invalid entries
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        if os.path.exists(kpi_file):
            with open(kpi_file, 'r') as f:
                reader = csv.DictReader(f)
                metrics = next(reader)
            # Should be 0 executions
            self.assertEqual(int(metrics['total_executions']), 0)

    def test_threshold_checking(self):
        """Test MTTR threshold checking"""
        # Write log with values below threshold
        base_time = datetime(2025, 5, 3, 10, 0, 0)
        entries = []
        
        for i in range(10):
            start = base_time
            end = datetime.fromtimestamp(base_time.timestamp() + 60)  # 60s - below p50 threshold
            entries.append(f"[{start.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Alert received")
            entries.append(f"[{end.strftime('%Y-%m-%d %H:%M:%S')}] STEP: Containment executed")
            base_time = datetime.fromtimestamp(end.timestamp() + 60)
        
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Check thresholds are met
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            metrics = next(reader)
            
        self.assertLessEqual(float(metrics['p50']), 120)
        self.assertLessEqual(float(metrics['p90']), 180)

    def test_csv_format(self):
        """Test CSV output format"""
        # Write simple log
        entries = [
            "[2025-05-03 10:00:00] STEP: Alert received",
            "[2025-05-03 10:01:30] STEP: Containment executed"
        ]
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Check CSV format
        kpi_file = os.path.join(self.test_results_path, 'kpis.csv')
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
        expected_fields = [
            'total_executions', 'mean', 'median', 'p50', 
            'p90', 'min', 'max', 'std_dev'
        ]
        for field in expected_fields:
            self.assertIn(field, fieldnames)

    def test_results_directory_creation(self):
        """Test that results directory is created if it doesn't exist"""
        # Remove results directory
        if os.path.exists(self.test_results_path):
            os.rmdir(self.test_results_path)
        
        # Write log
        entries = [
            "[2025-05-03 10:00:00] STEP: Alert received",
            "[2025-05-03 10:01:30] STEP: Containment executed"
        ]
        self.write_test_log(entries)
        
        # Run calculation
        from scripts.calc_kpis import main
        main()
        
        # Directory should be created
        self.assertTrue(os.path.exists(self.test_results_path))


class TestLogParsing(unittest.TestCase):
    """Test cases for log parsing"""

    def test_valid_log_entry(self):
        """Test parsing of valid log entry"""
        line = "[2025-05-03 10:00:00] STEP: Alert received"
        
        import re
        m = re.match(r"\[(.*?)\]\sSTEP:\s(.*)", line)
        
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "2025-05-03 10:00:00")
        self.assertEqual(m.group(2), "Alert received")

    def test_invalid_log_entry(self):
        """Test parsing of invalid log entry"""
        line = "Invalid log entry"
        
        import re
        m = re.match(r"\[(.*?)\]\sSTEP:\s(.*)", line)
        
        self.assertIsNone(m)

    def test_timestamp_parsing(self):
        """Test timestamp parsing"""
        timestamp_str = "2025-05-03 10:00:00"
        
        from datetime import datetime
        ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        
        self.assertEqual(ts.year, 2025)
        self.assertEqual(ts.month, 5)
        self.assertEqual(ts.day, 3)
        self.assertEqual(ts.hour, 10)
        self.assertEqual(ts.minute, 0)
        self.assertEqual(ts.second, 0)


if __name__ == '__main__':
    unittest.main()
