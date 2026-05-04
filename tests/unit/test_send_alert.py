#!/usr/bin/env python3
"""
Unit tests for send_alert.py
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.send_alert import SIEMSimulator


class TestSIEMSimulator(unittest.TestCase):
    """Test cases for SIEMSimulator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.webhook_url = "http://localhost:5001/webhook"
        self.api_token = "test-token"
        self.simulator = SIEMSimulator(self.webhook_url, self.api_token)

    def test_initialization(self):
        """Test simulator initialization"""
        self.assertEqual(self.simulator.webhook_url, self.webhook_url)
        self.assertEqual(self.simulator.api_token, self.api_token)

    def test_generate_malicious_alert(self):
        """Test generation of malicious alert"""
        alert = self.simulator.generate_alert(malicious=True)
        
        # Check required fields
        self.assertIn('alert_id', alert)
        self.assertIn('timestamp', alert)
        self.assertIn('source', alert)
        self.assertIn('event_type', alert)
        self.assertIn('severity', alert)
        self.assertIn('hostname', alert)
        self.assertIn('ip_address', alert)
        self.assertIn('file_hash', alert)
        
        # Check malicious indicators
        self.assertEqual(alert['event_type'], 'ransomware_detection')
        self.assertGreaterEqual(alert['severity'], 2)
        self.assertIn(alert['ip_address'], self.simulator.MALICIOUS_IPS)

    def test_generate_benign_alert(self):
        """Test generation of benign alert"""
        alert = self.simulator.generate_alert(malicious=False)
        
        # Check required fields
        self.assertIn('alert_id', alert)
        self.assertIn('timestamp', alert)
        
        # Check benign indicators
        self.assertEqual(alert['event_type'], 'ransomware_detection')
        self.assertLessEqual(alert['severity'], 1)
        self.assertIn(alert['ip_address'], self.simulator.BENIGN_IPS)

    def test_validate_alert_structure(self):
        """Test alert structure validation"""
        alert = self.simulator.generate_alert(malicious=True)
        
        # Check alert_id format
        self.assertRegex(alert['alert_id'], r'^ALERT-\d{8}-\d{6}$')
        
        # Check timestamp format
        self.assertRegex(alert['timestamp'], r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')
        
        # Check IP address format
        self.assertRegex(alert['ip_address'], r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        
        # Check hash format (SHA256)
        self.assertEqual(len(alert['file_hash']), 64)
        self.assertRegex(alert['file_hash'], r'^[a-f0-9]{64}$')

    def test_validate_ip_address(self):
        """Test IP address validation"""
        # Valid IPs
        self.assertTrue(self.simulator.validate_ip('192.168.1.1'))
        self.assertTrue(self.simulator.validate_ip('10.0.0.1'))
        self.assertTrue(self.simulator.validate_ip('172.16.0.1'))
        
        # Invalid IPs
        self.assertFalse(self.simulator.validate_ip('256.1.1.1'))
        self.assertFalse(self.simulator.validate_ip('invalid'))
        self.assertFalse(self.simulator.validate_ip(''))

    def test_validate_hash(self):
        """Test hash validation"""
        # Valid SHA256
        valid_hash = 'a' * 64
        self.assertTrue(self.simulator.validate_hash(valid_hash))
        
        # Invalid hashes
        self.assertFalse(self.simulator.validate_hash('short'))
        self.assertFalse(self.simulator.validate_hash('g' * 64))  # Invalid chars
        self.assertFalse(self.simulator.validate_hash(''))

    @patch('scripts.send_alert.requests.post')
    def test_send_alert_success(self, mock_post):
        """Test successful alert sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        alert = self.simulator.generate_alert(malicious=True)
        success = self.simulator.send_alert(alert)
        
        self.assertTrue(success)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], self.webhook_url)
        self.assertEqual(call_args[1]['headers']['Authorization'], f'Bearer {self.api_token}')

    @patch('scripts.send_alert.requests.post')
    def test_send_alert_failure(self, mock_post):
        """Test failed alert sending"""
        mock_post.side_effect = Exception("Network error")
        
        alert = self.simulator.generate_alert(malicious=True)
        success = self.simulator.send_alert(alert)
        
        self.assertFalse(success)

    def test_multiple_alerts_unique(self):
        """Test that multiple alerts have unique IDs"""
        alerts = [self.simulator.generate_alert(malicious=True) for _ in range(10)]
        alert_ids = [alert['alert_id'] for alert in alerts]
        
        # All IDs should be unique
        self.assertEqual(len(alert_ids), len(set(alert_ids)))

    def test_mitre_attack_tactics(self):
        """Test MITRE ATT&CK tactics inclusion"""
        alert = self.simulator.generate_alert(malicious=True)
        
        self.assertIn('mitre_attack', alert)
        self.assertIn('tactics', alert['mitre_attack'])
        self.assertIsInstance(alert['mitre_attack']['tactics'], list)
        self.assertGreater(len(alert['mitre_attack']['tactics']), 0)

    def test_network_connections(self):
        """Test network connections data"""
        alert = self.simulator.generate_alert(malicious=True)
        
        self.assertIn('network_connections', alert)
        self.assertIsInstance(alert['network_connections'], list)
        
        if alert['network_connections']:
            conn = alert['network_connections'][0]
            self.assertIn('destination_ip', conn)
            self.assertIn('destination_port', conn)
            self.assertIn('protocol', conn)

    def test_impact_assessment(self):
        """Test impact assessment data"""
        alert = self.simulator.generate_alert(malicious=True)
        
        self.assertIn('impact_assessment', alert)
        self.assertIn('affected_hosts', alert['impact_assessment'])
        self.assertIn('files_encrypted', alert['impact_assessment'])
        self.assertIn('data_exfiltrated', alert['impact_assessment'])


class TestAlertSchemaValidation(unittest.TestCase):
    """Test cases for JSON schema validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.schema_path = os.path.join(
            os.path.dirname(__file__), 
            '../../schemas/alert.schema.json'
        )
        
    def test_schema_file_exists(self):
        """Test that schema file exists"""
        self.assertTrue(os.path.exists(self.schema_path))
    
    def test_schema_is_valid_json(self):
        """Test that schema is valid JSON"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        self.assertIsInstance(schema, dict)
        self.assertIn('$schema', schema)
        self.assertIn('type', schema)
        self.assertIn('properties', schema)

    @unittest.skipIf(not os.path.exists('../../schemas/alert.schema.json'), "Schema file not found")
    def test_alert_validates_against_schema(self):
        """Test that generated alerts validate against schema"""
        try:
            import jsonschema
            
            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
            
            simulator = SIEMSimulator("http://test", "token")
            alert = simulator.generate_alert(malicious=True)
            
            # Should not raise exception
            jsonschema.validate(alert, schema)
        except ImportError:
            self.skipTest("jsonschema not installed")


if __name__ == '__main__':
    unittest.main()
