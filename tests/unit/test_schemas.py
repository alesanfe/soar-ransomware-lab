#!/usr/bin/env python3
"""
Unit tests for JSON schemas
"""

import unittest
import json
import os
from pathlib import Path

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class TestAlertSchema(unittest.TestCase):
    """Test cases for alert schema validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.schema_path = Path('schemas/alert.schema.json')
        self.payloads_dir = Path('tests/payloads')

    def test_schema_file_exists(self):
        """Test that schema file exists"""
        self.assertTrue(self.schema_path.exists())

    def test_schema_is_valid_json(self):
        """Test that schema is valid JSON"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        self.assertIsInstance(schema, dict)

    def test_schema_has_required_fields(self):
        """Test that schema has required structure"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        self.assertIn('$schema', schema)
        self.assertIn('type', schema)
        self.assertIn('properties', schema)
        self.assertIn('required', schema)

    def test_schema_required_properties(self):
        """Test that required properties are defined"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        required = schema.get('required', [])
        expected_required = [
            'alert_id', 'timestamp', 'source', 'event_type',
            'severity', 'hostname', 'ip_address', 'file_hash'
        ]
        
        for prop in expected_required:
            self.assertIn(prop, required, f"Property {prop} should be required")

    def test_schema_property_types(self):
        """Test that property types are correctly defined"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        # Check alert_id type
        self.assertIn('alert_id', properties)
        self.assertEqual(properties['alert_id']['type'], 'string')
        
        # Check timestamp type
        self.assertIn('timestamp', properties)
        self.assertEqual(properties['timestamp']['type'], 'string')
        
        # Check severity type
        self.assertIn('severity', properties)
        self.assertEqual(properties['severity']['type'], 'integer')

    def test_schema_patterns(self):
        """Test that regex patterns are defined"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        # Check alert_id pattern
        if 'alert_id' in properties:
            self.assertIn('pattern', properties['alert_id'])
        
        # Check file_hash pattern
        if 'file_hash' in properties:
            self.assertIn('pattern', properties['file_hash'])

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_payload_case1_validates(self):
        """Test that payload_case1.json validates against schema"""
        payload_path = self.payloads_dir / 'payload_case1.json'
        
        if not payload_path.exists():
            self.skipTest("payload_case1.json not found")
        
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(payload_path, 'r') as f:
            payload = json.load(f)
        
        # Should not raise exception
        jsonschema.validate(payload, schema)

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_payload_case2_validates(self):
        """Test that payload_case2.json validates against schema"""
        payload_path = self.payloads_dir / 'payload_case2.json'
        
        if not payload_path.exists():
            self.skipTest("payload_case2.json not found")
        
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        with open(payload_path, 'r') as f:
            payload = json.load(f)
        
        # Should not raise exception
        jsonschema.validate(payload, schema)

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_invalid_alert_fails_validation(self):
        """Test that invalid alert fails validation"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        # Create invalid alert (missing required field)
        invalid_alert = {
            'alert_id': 'ALERT-001',
            'timestamp': '2025-05-03T10:00:00Z'
            # Missing other required fields
        }
        
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_alert, schema)

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_invalid_severity_fails_validation(self):
        """Test that invalid severity fails validation"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        # Create alert with invalid severity
        invalid_alert = {
            'alert_id': 'ALERT-001',
            'timestamp': '2025-05-03T10:00:00Z',
            'source': 'SIEM',
            'event_type': 'ransomware_detection',
            'severity': 5,  # Assuming max is 3
            'hostname': 'test-host',
            'ip_address': '192.168.1.1',
            'file_hash': 'a' * 64
        }
        
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_alert, schema)

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_invalid_ip_format_fails_validation(self):
        """Test that invalid IP format fails validation"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        # Create alert with invalid IP
        invalid_alert = {
            'alert_id': 'ALERT-001',
            'timestamp': '2025-05-03T10:00:00Z',
            'source': 'SIEM',
            'event_type': 'ransomware_detection',
            'severity': 2,
            'hostname': 'test-host',
            'ip_address': '999.999.999.999',  # Invalid IP
            'file_hash': 'a' * 64
        }
        
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_alert, schema)

    @unittest.skipIf(not JSONSCHEMA_AVAILABLE, "jsonschema not installed")
    def test_invalid_hash_format_fails_validation(self):
        """Test that invalid hash format fails validation"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        # Create alert with invalid hash
        invalid_alert = {
            'alert_id': 'ALERT-001',
            'timestamp': '2025-05-03T10:00:00Z',
            'source': 'SIEM',
            'event_type': 'ransomware_detection',
            'severity': 2,
            'hostname': 'test-host',
            'ip_address': '192.168.1.1',
            'file_hash': 'invalid-hash'  # Not SHA256
        }
        
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(invalid_alert, schema)


class TestSchemaCompleteness(unittest.TestCase):
    """Test cases for schema completeness"""

    def setUp(self):
        """Set up test fixtures"""
        self.schema_path = Path('schemas/alert.schema.json')

    def test_schema_includes_all_alert_fields(self):
        """Test that schema includes all expected alert fields"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        expected_fields = [
            'alert_id', 'timestamp', 'source', 'event_type',
            'severity', 'hostname', 'ip_address', 'file_hash',
            'mitre_attack', 'network_connections', 'impact_assessment'
        ]
        
        for field in expected_fields:
            self.assertIn(field, properties, f"Field {field} should be in schema")

    def test_mitre_attack_structure(self):
        """Test MITRE ATT&CK structure in schema"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        if 'mitre_attack' in properties:
            mitre_props = properties['mitre_attack'].get('properties', {})
            self.assertIn('tactics', mitre_props)
            self.assertIn('techniques', mitre_props)

    def test_network_connections_structure(self):
        """Test network connections structure in schema"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        if 'network_connections' in properties:
            conn_props = properties['network_connections'].get('items', {}).get('properties', {})
            self.assertIn('destination_ip', conn_props)
            self.assertIn('destination_port', conn_props)
            self.assertIn('protocol', conn_props)

    def test_impact_assessment_structure(self):
        """Test impact assessment structure in schema"""
        with open(self.schema_path, 'r') as f:
            schema = json.load(f)
        
        properties = schema.get('properties', {})
        
        if 'impact_assessment' in properties:
            impact_props = properties['impact_assessment'].get('properties', {})
            self.assertIn('affected_hosts', impact_props)
            self.assertIn('files_encrypted', impact_props)
            self.assertIn('data_exfiltrated', impact_props)


if __name__ == '__main__':
    unittest.main()
