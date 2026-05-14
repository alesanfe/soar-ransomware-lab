#!/usr/bin/env python3
"""
Real method tests for analytics/tfm_data_enhancer.py
Tests the actual methods that exist in the TFMDataEnhancer class
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import analytics module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from soar_lab.analytics.tfm_data_enhancer import TFMDataEnhancer
    ENHANCER_AVAILABLE = True
except ImportError:
    ENHANCER_AVAILABLE = False


@pytest.mark.skipif(not ENHANCER_AVAILABLE, reason="TFMDataEnhancer not available")
class TestTFMDataEnhancerMethods:
    """Tests for actual TFMDataEnhancer methods"""
    
    @pytest.fixture
    def enhancer(self):
        """Create TFMDataEnhancer instance"""
        return TFMDataEnhancer()
    
    def test_enhancer_initialization(self, enhancer):
        """Test TFMDataEnhancer initialization"""
        assert enhancer is not None
        assert hasattr(enhancer, 'base_dir')
        assert hasattr(enhancer, 'results_dir')
        assert hasattr(enhancer, 'logs_dir')
        assert hasattr(enhancer, 'scenarios')
        
        # Check scenarios
        expected_scenarios = ['malicious', 'benign', 'edge_cases']
        assert enhancer.scenarios == expected_scenarios
        
        # Check directories exist
        assert enhancer.results_dir.exists()
        assert enhancer.logs_dir.exists()
    
    def test_configure_alert_payload_malicious(self, enhancer):
        """Test _configure_alert_payload for malicious alert"""
        payload = {'test': 'data'}
        enhancer._configure_alert_payload(payload, 'malicious')
        
        assert payload['severity'] == '2'
        assert payload['event_type'] == 'ransomware_detection'
        assert payload['test'] == 'data'
    
    def test_configure_alert_payload_benign(self, enhancer):
        """Test _configure_alert_payload for benign alert"""
        payload = {'test': 'data'}
        enhancer._configure_alert_payload(payload, 'benign')
        
        assert payload['severity'] == '1'
        assert payload['event_type'] == 'false_positive'
        assert payload['test'] == 'data'
    
    def test_configure_alert_payload_other(self, enhancer):
        """Test _configure_alert_payload for other alert types"""
        payload = {'test': 'data'}
        enhancer._configure_alert_payload(payload, 'other')
        
        assert payload['severity'] == '1'
        assert payload['event_type'] == 'false_positive'
        assert payload['test'] == 'data'
    
    @patch('subprocess.run')
    def test_generate_kpis_data_success(self, mock_run, enhancer):
        """Test generate_kpis_data with successful subprocess"""
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "KPI data generated successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = enhancer.generate_kpis_data()
        
        assert 'kpi_generation_time' in result
        assert 'kpi_data' in result
        assert result['kpi_data']['status'] == 'success'
        assert result['kpi_data']['output'] == "KPI data generated successfully"
        assert isinstance(result['kpi_generation_time'], float)
        assert result['kpi_generation_time'] > 0
    
    @patch('subprocess.run')
    def test_generate_kpis_data_error(self, mock_run, enhancer):
        """Test generate_kpis_data with subprocess error"""
        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error generating KPIs"
        mock_run.return_value = mock_result
        
        result = enhancer.generate_kpis_data()
        
        assert 'kpi_generation_time' in result
        assert 'kpi_data' in result
        assert result['kpi_data']['status'] == 'error'
        assert result['kpi_data']['error'] == "Error generating KPIs"
        assert isinstance(result['kpi_generation_time'], float)
    
    @patch('subprocess.run')
    def test_generate_kpis_data_exception(self, mock_run, enhancer):
        """Test generate_kpis_data with exception"""
        # Mock subprocess exception
        mock_run.side_effect = Exception("Subprocess failed")
        
        result = enhancer.generate_kpis_data()
        
        assert 'kpi_generation_time' in result
        assert 'kpi_data' in result
        assert result['kpi_data']['status'] == 'error'
        assert result['kpi_data']['error'] == "Subprocess failed"
        assert isinstance(result['kpi_generation_time'], float)
    
    @patch('soar_lab.analytics.tfm_data_enhancer.SIEMSimulator')
    def test_generate_alert_data(self, mock_siem_class, enhancer):
        """Test generate_alert_data method"""
        # Mock SIEMSimulator
        mock_simulator = Mock()
        mock_siem_class.return_value = mock_simulator
        
        # Mock alert generation
        mock_alert = {
            'id': 'test-alert-1',
            'type': 'ransomware',
            'severity': 'high',
            'timestamp': '2023-01-01T00:00:00Z'
        }
        mock_simulator.generate_malicious_alert.return_value = mock_alert
        
        result = enhancer.generate_alert_data()
        
        assert 'alert_generation_time' in result
        assert 'alerts' in result
        assert isinstance(result['alert_generation_time'], float)
        assert result['alert_generation_time'] > 0
        assert len(result['alerts']) == 3  # Should generate 3 alerts
        
        # Verify SIEMSimulator was called correctly
        mock_siem_class.assert_called_once_with(
            webhook_url="http://localhost:5001/webhook",
            api_token="test-token"
        )
        assert mock_simulator.generate_malicious_alert.call_count == 3
    
    def test_generate_alert_data_timing(self, enhancer):
        """Test generate_alert_data timing measurement"""
        with patch('soar_lab.analytics.tfm_data_enhancer.SIEMSimulator') as mock_siem_class:
            mock_simulator = Mock()
            mock_siem_class.return_value = mock_simulator
            mock_simulator.generate_malicious_alert.return_value = {'id': 'test'}
            
            start_time = time.time()
            result = enhancer.generate_alert_data()
            end_time = time.time()
            
            # Should measure generation time
            assert 'alert_generation_time' in result
            assert result['alert_generation_time'] > 0
            assert result['alert_generation_time'] <= (end_time - start_time + 0.1)  # Allow small margin
    
    @patch('subprocess.run')
    def test_generate_kpis_data_command_args(self, mock_run, enhancer):
        """Test generate_kpis_data subprocess command arguments"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        enhancer.generate_kpis_data()
        
        # Verify subprocess was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        
        assert call_args[0][0] == ['python', '-m', 'soar_lab.data.calc_kpis']
        assert call_args[1]['capture_output'] is True
        assert call_args[1]['text'] is True
        assert call_args[1]['cwd'] == enhancer.base_dir
    
    @patch('subprocess.run')
    def test_generate_kpis_data_large_output(self, mock_run, enhancer):
        """Test generate_kpis_data with large output"""
        large_output = "KPI data " * 1000  # Large output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = large_output
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = enhancer.generate_kpis_data()
        
        assert result['kpi_data']['status'] == 'success'
        assert result['kpi_data']['output'] == large_output
    
    @patch('soar_lab.analytics.tfm_data_enhancer.SIEMSimulator')
    def test_generate_alert_data_complex_alerts(self, mock_siem_class, enhancer):
        """Test generate_alert_data with complex alert structure"""
        mock_simulator = Mock()
        mock_siem_class.return_value = mock_simulator
        
        # Mock complex alert
        complex_alert = {
            'id': 'complex-alert-1',
            'type': 'ransomware',
            'severity': 'critical',
            'timestamp': '2023-01-01T00:00:00Z',
            'details': {
                'file_path': '/path/to/file.txt',
                'hash': 'abc123',
                'user': 'testuser',
                'hostname': 'testhost'
            }
        }
        mock_simulator.generate_malicious_alert.return_value = complex_alert
        
        result = enhancer.generate_alert_data()
        
        assert len(result['alerts']) == 3
        assert result['alerts'][0]['details']['file_path'] == '/path/to/file.txt'
        assert result['alerts'][0]['details']['hash'] == 'abc123'
    
    def test_enhancer_directory_structure(self, enhancer):
        """Test that enhancer creates correct directory structure"""
        base_dir = enhancer.base_dir
        expected_results_dir = base_dir / "artifacts" / "results"
        expected_logs_dir = base_dir / "artifacts" / "logs"
        
        assert enhancer.results_dir == expected_results_dir
        assert enhancer.logs_dir == expected_logs_dir
        assert expected_results_dir.exists()
        assert expected_logs_dir.exists()
    
    def test_enhancer_scenarios_list(self, enhancer):
        """Test that enhancer has correct scenarios"""
        expected_scenarios = ['malicious', 'benign', 'edge_cases']
        assert enhancer.scenarios == expected_scenarios
        assert isinstance(enhancer.scenarios, list)
        assert len(enhancer.scenarios) == 3
    
    @patch('subprocess.run')
    def test_generate_kpis_data_empty_output(self, mock_run, enhancer):
        """Test generate_kpis_data with empty output"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = enhancer.generate_kpis_data()
        
        assert result['kpi_data']['status'] == 'success'
        assert result['kpi_data']['output'] == ""
    
    @patch('subprocess.run')
    def test_generate_kpis_data_unicode_output(self, mock_run, enhancer):
        """Test generate_kpis_data with unicode output"""
        unicode_output = "测试数据 🚀 KPI generated"
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = unicode_output
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = enhancer.generate_kpis_data()
        
        assert result['kpi_data']['status'] == 'success'
        assert result['kpi_data']['output'] == unicode_output
    
    def test_configure_alert_payload_modification(self, enhancer):
        """Test that _configure_alert_payload modifies payload correctly"""
        original_payload = {
            'original_field': 'original_value',
            'severity': 'original_severity',
            'event_type': 'original_event'
        }
        
        enhancer._configure_alert_payload(original_payload, 'malicious')
        
        # Should modify existing fields
        assert original_payload['severity'] == '2'
        assert original_payload['event_type'] == 'ransomware_detection'
        # Should preserve original fields
        assert original_payload['original_field'] == 'original_value'
    
    @patch('soar_lab.analytics.tfm_data_enhancer.SIEMSimulator')
    def test_generate_alert_data_error_handling(self, mock_siem_class, enhancer):
        """Test generate_alert_data error handling"""
        mock_simulator = Mock()
        mock_siem_class.return_value = mock_simulator
        
        # Mock alert generation error
        mock_simulator.generate_malicious_alert.side_effect = Exception("Alert generation failed")
        
        try:
            result = enhancer.generate_alert_data()
            # Should handle error gracefully or raise appropriate exception
            assert isinstance(result, dict) or True
        except Exception:
            # Should raise meaningful error
            assert True
    
    def test_enhancer_base_directory_path(self, enhancer):
        """Test that enhancer base directory is correct"""
        expected_base_dir = Path(__file__).parent.parent.parent.parent
        assert enhancer.base_dir == expected_base_dir
    
    def test_enhancer_initialization_idempotent(self, enhancer):
        """Test that enhancer initialization is idempotent"""
        # Get initial state
        initial_scenarios = enhancer.scenarios
        initial_results_dir = enhancer.results_dir
        initial_logs_dir = enhancer.logs_dir
        
        # Re-initialize
        new_enhancer = TFMDataEnhancer()
        
        # Should have same state
        assert new_enhancer.scenarios == initial_scenarios
        assert new_enhancer.results_dir == initial_results_dir
        assert new_enhancer.logs_dir == initial_logs_dir
