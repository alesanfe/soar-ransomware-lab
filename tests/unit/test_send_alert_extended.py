#!/usr/bin/env python3
"""
Extended unit tests for SIEM Simulator
"""

import unittest
from unittest.mock import patch, MagicMock
import requests
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.send_alert import SIEMSimulator


class TestSIEMSimulatorExtended(unittest.TestCase):
    """Extended tests for SIEM Simulator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.siem = SIEMSimulator(
            webhook_url="http://localhost:5001/webhook",
            api_token="test-token"
        )
    
    def test_validate_alert_missing_fields(self):
        """Test alert validation with missing fields"""
        # Missing alert_id
        alert = {
            'hostname': 'test-host',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'src_ip': '192.168.1.100',
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        result = self.siem.validate_alert(alert)
        self.assertFalse(result)
    
    def test_validate_alert_empty_fields(self):
        """Test alert validation with empty fields"""
        alert = {
            'alert_id': '',
            'hostname': 'test-host',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'src_ip': '192.168.1.100',
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        result = self.siem.validate_alert(alert)
        self.assertFalse(result)
    
    def test_validate_alert_invalid_ip(self):
        """Test alert validation with invalid IP"""
        alert = {
            'alert_id': 'ALERT-001',
            'hostname': 'test-host',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e',
            'src_ip': 'invalid.ip.address',
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        result = self.siem.validate_alert(alert)
        self.assertFalse(result)
    
    def test_validate_alert_invalid_hash(self):
        """Test alert validation with invalid hash"""
        alert = {
            'alert_id': 'ALERT-001',
            'hostname': 'test-host',
            'hash': 'invalid_hash',
            'src_ip': '192.168.1.100',
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        result = self.siem.validate_alert(alert)
        self.assertFalse(result)
    
    def test_validate_ip_valid_addresses(self):
        """Test IP validation with valid addresses"""
        valid_ips = [
            '192.168.1.1',
            '10.0.0.1',
            '172.16.0.1',
            '0.0.0.0',
            '255.255.255.255'
        ]
        
        for ip in valid_ips:
            result = self.siem.validate_ip(ip)
            self.assertTrue(result, f"IP {ip} should be valid")
    
    def test_validate_ip_invalid_addresses(self):
        """Test IP validation with invalid addresses"""
        invalid_ips = [
            '256.1.1.1',
            '192.168.1',
            '192.168.1.1.1',
            'abc.def.ghi.jkl',
            '192.168.-1.1',
            '192.168.1.256'
        ]
        
        for ip in invalid_ips:
            result = self.siem.validate_ip(ip)
            self.assertFalse(result, f"IP {ip} should be invalid")
    
    def test_validate_hash_none(self):
        """Test hash validation with None"""
        result = self.siem.validate_hash(None)
        self.assertFalse(result)
    
    def test_validate_hash_invalid_format(self):
        """Test hash validation with invalid format"""
        invalid_hashes = [
            'short',
            'toolonghash123456789012345678901234567890123456789012345678901234567890',
            'invalid_characters_here',
            '1234567890123456789012345678901234567890'  # Only digits
        ]
        
        for hash_val in invalid_hashes:
            result = self.siem.validate_hash(hash_val)
            self.assertFalse(result, f"Hash {hash_val} should be invalid")
    
    def test_validate_hash_valid(self):
        """Test hash validation with valid hashes"""
        valid_hashes = [
            'd41d8cd98f00b204e9800998ecf8427e',  # MD5
            'da39a3ee5e6b4b0d3255bfef95601890afd80709',  # SHA1
            'd41d8cd98f00b204e9800998ecf8427e' * 2,  # SHA256
        ]
        
        for hash_val in valid_hashes:
            result = self.siem.validate_hash(hash_val)
            self.assertTrue(result, f"Hash {hash_val} should be valid")
    
    def test_validate_alert_structure_missing_required_fields(self):
        """Test alert structure validation with missing required fields"""
        incomplete_alert = {
            'alert_id': 'ALERT-001'
            # Missing hostname, src_ip, hash, severity, event_type
        }
        
        result = self.siem.validate_alert_structure(incomplete_alert)
        self.assertFalse(result)
    
    def test_validate_alert_structure_invalid_severity(self):
        """Test alert structure validation with invalid severity"""
        alert = {
            'alert_id': 'ALERT-001',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e' * 2,
            'severity': 5,  # Invalid severity (should be 0-3)
            'event_type': 'test'
        }
        
        result = self.siem.validate_alert_structure(alert)
        self.assertFalse(result)
    
    def test_validate_alert_structure_invalid_ip(self):
        """Test alert structure validation with invalid IP"""
        alert = {
            'alert_id': 'ALERT-001',
            'hostname': 'test-host',
            'src_ip': 'invalid.ip',
            'hash': 'd41d8cd98f00b204e9800998ecf8427e' * 2,
            'severity': 1,
            'event_type': 'test'
        }
        
        result = self.siem.validate_alert_structure(alert)
        self.assertFalse(result)
    
    def test_validate_alert_structure_invalid_hash(self):
        """Test alert structure validation with invalid hash"""
        alert = {
            'alert_id': 'ALERT-001',
            'hostname': 'test-host',
            'src_ip': '192.168.1.100',
            'hash': 'invalid_hash',
            'severity': 1,
            'event_type': 'test'
        }
        
        result = self.siem.validate_alert_structure(alert)
        self.assertFalse(result)
    
    def test_mitre_attack_tactics_property(self):
        """Test MITRE ATT&CK tactics property"""
        tactics = self.siem.mitre_attack_tactics
        
        self.assertIsInstance(tactics, dict)
        self.assertIn('TA0001', tactics)
        self.assertIn('TA0011', tactics)
        self.assertEqual(len(tactics), 11)  # Should have 11 tactics
        
        # Check specific tactics
        self.assertEqual(tactics['TA0001'], 'Initial Access')
        self.assertEqual(tactics['TA0011'], 'Command and Control')
    
    @patch('requests.post')
    def test_send_alert_network_error(self, mock_post):
        """Test sending alert with network error"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")
        
        alert = self.siem.generate_alert('malicious')
        result = self.siem.send_alert(alert)
        
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_send_alert_timeout_error(self, mock_post):
        """Test sending alert with timeout error"""
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        alert = self.siem.generate_alert('malicious')
        result = self.siem.send_alert(alert)
        
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_send_alert_unexpected_error(self, mock_post):
        """Test sending alert with unexpected error"""
        mock_post.side_effect = Exception("Unexpected error")
        
        alert = self.siem.generate_alert('malicious')
        result = self.siem.send_alert(alert)
        
        self.assertFalse(result)
    
    @patch('time.sleep')
    @patch('requests.post')
    def test_run_simulation_success(self, mock_post, mock_sleep):
        """Test successful simulation run"""
        mock_post.return_value = MagicMock(status_code=200, text='OK')
        
        with patch('builtins.print') as mock_print:
            self.siem.run_simulation(num_alerts=2, delay=0, alert_type='malicious')
            
            # Should have sent 2 alerts
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_not_called()  # No delay for last alert
    
    @patch('time.sleep')
    @patch('requests.post')
    def test_run_simulation_with_delay(self, mock_post, mock_sleep):
        """Test simulation run with delay"""
        mock_post.return_value = MagicMock(status_code=200, text='OK')
        
        with patch('builtins.print'):
            self.siem.run_simulation(num_alerts=2, delay=1, alert_type='malicious')
            
            # Should have slept once (between alerts, not after last)
            mock_sleep.assert_called_once_with(1)
    
    @patch('requests.post')
    def test_run_simulation_with_failures(self, mock_post):
        """Test simulation run with some failures"""
        # First alert succeeds, second fails
        mock_post.side_effect = [
            MagicMock(status_code=200, text='OK'),
            MagicMock(status_code=500, text='Error')
        ]
        
        with patch('builtins.print'):
            self.siem.run_simulation(num_alerts=2, delay=0, alert_type='malicious')
            
            # Should have attempted to send 2 alerts
            self.assertEqual(mock_post.call_count, 2)


if __name__ == '__main__':
    unittest.main()
