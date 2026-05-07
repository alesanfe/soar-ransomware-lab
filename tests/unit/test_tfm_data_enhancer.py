#!/usr/bin/env python3
"""
Unit tests for TFM Data Enhancer
"""

import unittest
import tempfile
import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.tfm_data_enhancer import TFMDataEnhancer


class TestTFMDataEnhancer(unittest.TestCase):
    """Test TFM Data Enhancer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.enhancer = TFMDataEnhancer()
    
    def test_init(self):
        """Test TFMDataEnhancer initialization"""
        self.assertIsNotNone(self.enhancer.base_dir)
        self.assertIsNotNone(self.enhancer.results_dir)
        self.assertIsNotNone(self.enhancer.logs_dir)
        self.assertTrue(self.enhancer.results_dir.exists())
        self.assertTrue(self.enhancer.logs_dir.exists())
    
    def test_run_test_scenarios_success(self):
        """Test successful test scenario execution"""
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess runs
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Test output",
                stderr=""
            )
            
            result = self.enhancer.run_test_scenarios()
            
            self.assertIsInstance(result, dict)
            self.assertIn('test_execution_time', result)
            self.assertIn('scenarios', result)
            self.assertIn('malicious', result['scenarios'])
            self.assertIn('benign', result['scenarios'])
            self.assertTrue(result['scenarios']['malicious']['success'])
            self.assertTrue(result['scenarios']['benign']['success'])
    
    def test_run_test_scenarios_timeout(self):
        """Test test scenario execution with timeout"""
        with patch('subprocess.run') as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired(['python3', 'test'], 300)
            
            result = self.enhancer.run_test_scenarios()
            
            self.assertIn('scenarios', result)
            self.assertFalse(result['scenarios']['malicious']['success'])
            self.assertEqual(result['scenarios']['malicious']['error'], 'Timeout exceeded')
    
    def test_run_test_scenarios_exception(self):
        """Test test scenario execution with exception"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Test error")
            
            result = self.enhancer.run_test_scenarios()
            
            self.assertIn('scenarios', result)
            self.assertFalse(result['scenarios']['malicious']['success'])
            self.assertEqual(result['scenarios']['malicious']['error'], 'Test error')
    
    def test_generate_kpis_data(self):
        """Test KPI data generation"""
        with patch('scripts.calc_kpis.main') as mock_calc_kpis:
            mock_calc_kpis.return_value = {"test": "data"}
            
            result = self.enhancer.generate_kpis_data()
            
            self.assertIsInstance(result, dict)
            self.assertIn('kpi_generation_time', result)
            self.assertIn('kpi_data', result)
    
    def test_generate_alert_data(self):
        """Test alert data generation"""
        with patch('scripts.send_alert.SIEMSimulator') as mock_siem:
            mock_sim_instance = MagicMock()
            mock_siem.return_value = mock_sim_instance
            mock_sim_instance.generate_malicious_alert.return_value = {"test": "alert"}
            
            result = self.enhancer.generate_alert_data()
            
            self.assertIsInstance(result, dict)
            self.assertIn('alert_generation_time', result)
            self.assertIn('alerts', result)
    
    def test_save_results(self):
        """Test results saving functionality"""
        test_data = {"test": "data", "timestamp": "2025-01-01T00:00:00Z"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            self.enhancer.save_results(test_data, temp_file)
            
            self.assertTrue(temp_file.exists())
            
            with open(temp_file, 'r') as f:
                saved_data = json.load(f)
            
            self.assertEqual(saved_data, test_data)
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def test_get_test_statistics(self):
        """Test test statistics calculation"""
        test_results = {
            'scenarios': {
                'malicious': {'success': True, 'duration': 10.5},
                'benign': {'success': True, 'duration': 8.2},
                'edge_case': {'success': False, 'duration': 5.0}
            }
        }
        
        stats = self.enhancer.get_test_statistics(test_results)
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_scenarios', stats)
        self.assertIn('successful_scenarios', stats)
        self.assertIn('failed_scenarios', stats)
        self.assertIn('success_rate', stats)
        self.assertIn('total_duration', stats)
        self.assertIn('average_duration', stats)
        
        self.assertEqual(stats['total_scenarios'], 3)
        self.assertEqual(stats['successful_scenarios'], 2)
        self.assertEqual(stats['failed_scenarios'], 1)
        self.assertAlmostEqual(stats['success_rate'], 0.6667, places=3)
        self.assertEqual(stats['total_duration'], 23.7)
        self.assertAlmostEqual(stats['average_duration'], 7.9, places=1)


if __name__ == '__main__':
    unittest.main()
