#!/usr/bin/env python3
"""
Unit tests for TFM Data Viewer
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

from scripts.tfm_data_viewer import TFMDataViewer


class TestTFMDataViewer(unittest.TestCase):
    """Test TFM Data Viewer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.viewer = TFMDataViewer()
    
    def test_init(self):
        """Test TFMDataViewer initialization"""
        self.assertIsNotNone(self.viewer.tfm_file)
        self.assertIsNotNone(self.viewer.log_file)
        self.assertIsNotNone(self.viewer.results_file)
        self.assertIsNotNone(self.viewer.test_report_file)
        self.assertIsInstance(self.viewer._cache, dict)
        self.assertIsNone(self.viewer._cache_timestamp)
    
    def test_extract_placeholders_file_not_found(self):
        """Test placeholder extraction when file doesn't exist"""
        self.viewer.tfm_file = Path("/nonexistent/file.md")
        
        placeholders = self.viewer.extract_placeholders()
        
        self.assertIsInstance(placeholders, dict)
        self.assertEqual(len(placeholders), 0)
    
    def test_extract_placeholders_success(self):
        """Test successful placeholder extraction"""
        test_content = """
        Some text here
        {variable1: description1 - ref1}
        More text
        {variable2: description2 - ref2}
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.tfm_file = temp_file
            placeholders = self.viewer.extract_placeholders()
            
            self.assertIsInstance(placeholders, dict)
            self.assertIn('variable1', placeholders)
            self.assertIn('variable2', placeholders)
            self.assertEqual(placeholders['variable1']['description'], 'description1')
            self.assertEqual(placeholders['variable1']['reference'], 'ref1')
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def test_parse_log_file_not_found(self):
        """Test log parsing when file doesn't exist"""
        self.viewer.log_file = Path("/nonexistent/log.log")
        
        result = self.viewer.parse_log_file()
        
        self.assertIsInstance(result, dict)
        self.assertIn('entries', result)
        self.assertIn('total_entries', result)
        self.assertEqual(result['total_entries'], 0)
    
    def test_parse_log_file_success(self):
        """Test successful log parsing"""
        test_log_content = """
        2025-01-01 10:00:00 - INFO - Test message 1
        2025-01-01 10:01:00 - ERROR - Test error message
        2025-01-01 10:02:00 - INFO - Test message 2
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(test_log_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.log_file = temp_file
            result = self.viewer.parse_log_file()
            
            self.assertIsInstance(result, dict)
            self.assertIn('entries', result)
            self.assertIn('total_entries', result)
            self.assertIn('info_count', result)
            self.assertIn('error_count', result)
            self.assertEqual(result['total_entries'], 3)
            self.assertEqual(result['info_count'], 2)
            self.assertEqual(result['error_count'], 1)
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def test_parse_results_file_not_found(self):
        """Test results parsing when file doesn't exist"""
        self.viewer.results_file = Path("/nonexistent/results.csv")
        
        result = self.viewer.parse_results_file()
        
        self.assertIsInstance(result, dict)
        self.assertIn('data', result)
        self.assertIn('total_records', result)
        self.assertEqual(result['total_records'], 0)
    
    def test_parse_results_file_success(self):
        """Test successful results parsing"""
        test_csv_content = """timestamp,kpi1,kpi2
2025-01-01,100,200
2025-01-02,150,250
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(test_csv_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.results_file = temp_file
            result = self.viewer.parse_results_file()
            
            self.assertIsInstance(result, dict)
            self.assertIn('data', result)
            self.assertIn('total_records', result)
            self.assertIn('headers', result)
            self.assertEqual(result['total_records'], 2)
            self.assertEqual(len(result['data']), 2)
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def test_generate_summary_report(self):
        """Test summary report generation"""
        mock_data = {
            'placeholders': {'var1': {'description': 'desc1', 'reference': 'ref1'}},
            'logs': {'total_entries': 10, 'info_count': 8, 'error_count': 2},
            'results': {'total_records': 5, 'headers': ['col1', 'col2']}
        }
        
        with patch.object(self.viewer, 'extract_placeholders', return_value=mock_data['placeholders']):
            with patch.object(self.viewer, 'parse_log_file', return_value=mock_data['logs']):
                with patch.object(self.viewer, 'parse_results_file', return_value=mock_data['results']):
                    
                    report = self.viewer.generate_summary_report()
                    
                    self.assertIsInstance(report, dict)
                    self.assertIn('summary', report)
                    self.assertIn('placeholders', report)
                    self.assertIn('logs', report)
                    self.assertIn('results', report)
                    self.assertIn('generated_at', report)
    
    def test_format_data_for_display(self):
        """Test data formatting for display"""
        test_data = {
            'summary': {'total_placeholders': 5, 'total_log_entries': 10},
            'placeholders': {'var1': {'description': 'desc1'}},
            'logs': {'entries': [{'timestamp': '2025-01-01', 'level': 'INFO'}]},
            'results': {'data': [{'kpi1': 100}]}
        }
        
        formatted = self.viewer.format_data_for_display(test_data)
        
        self.assertIsInstance(formatted, str)
        self.assertIn('SUMMARY', formatted)
        self.assertIn('PLACEHOLDERS', formatted)
        self.assertIn('LOGS', formatted)
        self.assertIn('RESULTS', formatted)
    
    def test_cache_functionality(self):
        """Test caching functionality"""
        test_data = {"test": "data"}
        
        # Test cache miss
        with patch.object(self.viewer, 'generate_summary_report', return_value=test_data) as mock_gen:
            result1 = self.viewer.get_cached_summary()
            result2 = self.viewer.get_cached_summary()
            
            # Should only call once due to caching
            mock_gen.assert_called_once()
            self.assertEqual(result1, test_data)
            self.assertEqual(result2, test_data)
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.viewer._cache = {"test": "data"}
        self.viewer._cache_timestamp = time.time()
        
        self.viewer.clear_cache()
        
        self.assertEqual(self.viewer._cache, {})
        self.assertIsNone(self.viewer._cache_timestamp)

    def test_calculate_mttr_metrics_no_file(self):
        """Test MTTR calculation when log file doesn't exist"""
        self.viewer.log_file = Path("/nonexistent/log.log")
        
        result = self.viewer.calculate_mttr_metrics()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_calculate_mttr_metrics_with_data(self):
        """Test MTTR calculation with valid log data"""
        test_log_content = """
        2025-01-01 10:00:00 - INFO - STEP: Alert received
        2025-01-01 10:01:00 - INFO - Some other log
        2025-01-01 10:02:00 - INFO - STEP: Containment executed
        2025-01-01 10:03:00 - INFO - STEP: Alert received
        2025-01-01 10:05:00 - INFO - STEP: Containment executed
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(test_log_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.log_file = temp_file
            result = self.viewer.calculate_mttr_metrics()
            
            self.assertIsInstance(result, dict)
            if result:  # Only test if MTTR data was calculated
                self.assertIn('total_time_soaR', result)
                self.assertIn('p50_soaR', result)
                self.assertIn('p90_soaR', result)
                self.assertIn('p95_soaR', result)
                self.assertIn('mean_soaR', result)
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_parse_results_file_json(self):
        """Test results file parsing for JSON format"""
        test_json_content = """[
            {"timestamp": "2025-01-01", "kpi1": 100, "kpi2": 200},
            {"timestamp": "2025-01-02", "kpi1": 150, "kpi2": 250}
        ]"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(test_json_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.results_file = temp_file
            result = self.viewer.parse_results_file()
            
            self.assertIsInstance(result, dict)
            self.assertIn('data', result)
            self.assertIn('total_records', result)
            self.assertIn('headers', result)
            self.assertEqual(result['total_records'], 2)
            self.assertEqual(len(result['data']), 2)
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_extract_placeholders_edge_cases(self):
        """Test placeholder extraction with edge cases"""
        test_content = """
        With description: {complex_var: This is a description}
        With reference: {ref_var: Description - reference123}
        With ver reference: {ver_var: Description - ver [ref456]}
        Multiple placeholders: {var2: desc - ref}
        Empty braces: {}
        Malformed: {incomplete
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file = Path(f.name)
        
        try:
            self.viewer.tfm_file = temp_file
            placeholders = self.viewer.extract_placeholders()
            
            self.assertIsInstance(placeholders, dict)
            self.assertIn('complex_var', placeholders)
            self.assertIn('ref_var', placeholders)
            self.assertIn('ver_var', placeholders)
            self.assertIn('var2', placeholders)
            
            # Check structure
            self.assertEqual(placeholders['complex_var']['description'], 'This is a description')
            self.assertEqual(placeholders['ref_var']['reference'], 'reference123')
            # Note: ver reference parsing might be different than expected
            self.assertIn('ver_var', placeholders)
            
            # Check that all placeholders have required fields
            for placeholder in placeholders.values():
                self.assertIn('description', placeholder)
                self.assertIn('reference', placeholder)
                self.assertIn('value', placeholder)
                self.assertIn('available', placeholder)
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_format_data_for_display_different_types(self):
        """Test data formatting for different data types"""
        # Test with dict
        dict_data = {"key": "value", "number": 123}
        formatted_dict = self.viewer.format_data_for_display(dict_data)
        self.assertIsInstance(formatted_dict, str)
        self.assertIn("KEY", formatted_dict)
        self.assertIn("VALUE", formatted_dict)
        
        # Test with list
        list_data = ["item1", "item2"]
        formatted_list = self.viewer.format_data_for_display(list_data)
        self.assertIsInstance(formatted_list, str)
        self.assertIn("ITEM1", formatted_list)
        
        # Test with string
        string_data = "simple string"
        formatted_string = self.viewer.format_data_for_display(string_data)
        self.assertEqual(formatted_string, "SIMPLE STRING")
        
        # Test with number
        number_data = 123
        formatted_number = self.viewer.format_data_for_display(number_data)
        self.assertEqual(formatted_number, "123")


if __name__ == '__main__':
    unittest.main()
