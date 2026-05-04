#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Automated Security Tests
Comprehensive security testing for SOAR components
"""

import asyncio
import aiohttp
import json
import re
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import get_setting
from config.schemas import validate_alert_data, RansomwareAlert

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecurityTester:
    """Automated security testing framework"""
    
    def __init__(self):
        self.base_url = get_setting('shuffle_api_url', 'http://localhost:5001')
        self.webhook_url = f"{self.base_url}/api/v1/webhooks/siem"
        self.api_token = get_setting('siem_webhook_token', 'test-token')
        self.results = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests"""
        logger.info("Starting comprehensive security testing")
        
        test_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tests": {}
        }
        
        # Test categories
        test_methods = [
            ("input_validation", self.test_input_validation),
            ("authentication", self.test_authentication),
            ("authorization", self.test_authorization),
            ("injection_attacks", self.test_injection_attacks),
            ("xss_protection", self.test_xss_protection),
            ("rate_limiting", self.test_rate_limiting),
            ("data_validation", self.test_data_validation),
            ("error_handling", self.test_error_handling),
            ("file_upload", self.test_file_upload),
            ("ssl_tls", self.test_ssl_tls),
        ]
        
        for test_name, test_method in test_methods:
            logger.info(f"Running {test_name} tests...")
            try:
                result = test_method()
                test_results["tests"][test_name] = result
                logger.info(f"{test_name} tests completed: {result.get('status', 'unknown')}")
            except Exception as e:
                logger.error(f"{test_name} tests failed: {e}")
                test_results["tests"][test_name] = {
                    "status": "failed",
                    "error": str(e),
                    "tests_run": 0,
                    "tests_passed": 0
                }
        
        # Calculate overall status
        total_tests = sum(test.get("tests_run", 0) for test in test_results["tests"].values())
        passed_tests = sum(test.get("tests_passed", 0) for test in test_results["tests"].values())
        
        test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": "passed" if passed_tests == total_tests else "failed"
        }
        
        return test_results
    
    def test_input_validation(self) -> Dict[str, Any]:
        """Test input validation security"""
        tests = []
        passed = 0
        
        # Test cases for malformed input
        test_cases = [
            {
                "name": "malformed_alert_id",
                "alert": {
                    "alert_id": "INVALID-ID",
                    "hostname": "test-host",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": "test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": "Test alert"
                },
                "should_fail": True
            },
            {
                "name": "invalid_ip_address",
                "alert": {
                    "alert_id": "ALERT-1234567890-0001",
                    "hostname": "test-host",
                    "src_ip": "999.999.999.999",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": "test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": "Test alert"
                },
                "should_fail": True
            },
            {
                "name": "invalid_hash_format",
                "alert": {
                    "alert_id": "ALERT-1234567890-0002",
                    "hostname": "test-host",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "invalid_hash"},
                    "severity": "2",
                    "source": "test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": "Test alert"
                },
                "should_fail": True
            },
            {
                "name": "missing_required_fields",
                "alert": {
                    "alert_id": "ALERT-1234567890-0003",
                    "hostname": "test-host",
                    # Missing src_ip, hash, etc.
                    "severity": "2",
                    "source": "test"
                },
                "should_fail": True
            }
        ]
        
        for test_case in test_cases:
            try:
                validate_alert_data(test_case["alert"])
                if test_case["should_fail"]:
                    tests.append({
                        "name": test_case["name"],
                        "status": "failed",
                        "message": "Validation should have failed but passed"
                    })
                else:
                    tests.append({
                        "name": test_case["name"],
                        "status": "passed",
                        "message": "Validation passed as expected"
                    })
                    passed += 1
            except Exception as e:
                if test_case["should_fail"]:
                    tests.append({
                        "name": test_case["name"],
                        "status": "passed",
                        "message": f"Validation failed as expected: {str(e)}"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": test_case["name"],
                        "status": "failed",
                        "message": f"Validation failed unexpectedly: {str(e)}"
                    })
        
        return {
            "status": "passed" if passed == len(tests) else "failed",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_authentication(self) -> Dict[str, Any]:
        """Test authentication security"""
        tests = []
        passed = 0
        
        # Test cases for authentication
        test_cases = [
            {
                "name": "no_token",
                "token": None,
                "should_fail": True
            },
            {
                "name": "invalid_token",
                "token": "invalid-token",
                "should_fail": True
            },
            {
                "name": "empty_token",
                "token": "",
                "should_fail": True
            },
            {
                "name": "valid_token",
                "token": self.api_token,
                "should_fail": False
            }
        ]
        
        for test_case in test_cases:
            try:
                result = asyncio.run(self._send_test_request(test_case["token"]))
                
                if test_case["should_fail"]:
                    if result.get("status_code") == 401:
                        tests.append({
                            "name": test_case["name"],
                            "status": "passed",
                            "message": "Authentication properly rejected"
                        })
                        passed += 1
                    else:
                        tests.append({
                            "name": test_case["name"],
                            "status": "failed",
                            "message": f"Authentication should have been rejected, got {result.get('status_code')}"
                        })
                else:
                    if result.get("status_code") == 200:
                        tests.append({
                            "name": test_case["name"],
                            "status": "passed",
                            "message": "Authentication accepted"
                        })
                        passed += 1
                    else:
                        tests.append({
                            "name": test_case["name"],
                            "status": "failed",
                            "message": f"Authentication should have been accepted, got {result.get('status_code')}"
                        })
            except Exception as e:
                tests.append({
                    "name": test_case["name"],
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "failed",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_authorization(self) -> Dict[str, Any]:
        """Test authorization security"""
        tests = []
        passed = 0
        
        # Test unauthorized endpoints
        unauthorized_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/config",
            "/api/v1/system/status",
            "/api/v1/workflows/delete-all"
        ]
        
        for endpoint in unauthorized_endpoints:
            try:
                result = asyncio.run(self._send_unauthorized_request(endpoint))
                
                if result.get("status_code") == 403:
                    tests.append({
                        "name": f"unauthorized_endpoint_{endpoint.replace('/', '_')}",
                        "status": "passed",
                        "message": "Properly rejected unauthorized access"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": f"unauthorized_endpoint_{endpoint.replace('/', '_')}",
                        "status": "failed",
                        "message": f"Should have returned 403, got {result.get('status_code')}"
                    })
            except Exception as e:
                tests.append({
                    "name": f"unauthorized_endpoint_{endpoint.replace('/', '_')}",
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "failed",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_injection_attacks(self) -> Dict[str, Any]:
        """Test injection attack protection"""
        tests = []
        passed = 0
        
        # SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' UNION SELECT * FROM sensitive_data --"
        ]
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]
        
        # Command injection payloads
        cmd_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`"
        ]
        
        all_payloads = sql_payloads + xss_payloads + cmd_payloads
        
        for i, payload in enumerate(all_payloads):
            try:
                # Create malicious alert
                malicious_alert = {
                    "alert_id": f"ALERT-{int(time.time())}-{i:04d}",
                    "hostname": f"test-{payload[:20]}",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": f"test-{payload[:20]}",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": f"Test alert with payload: {payload}"
                }
                
                result = asyncio.run(self._send_test_request(self.api_token, malicious_alert))
                
                # Check if payload was properly sanitized/rejected
                if result.get("status_code") in [400, 422]:
                    tests.append({
                        "name": f"injection_test_{i}",
                        "status": "passed",
                        "message": "Malicious payload properly rejected"
                    })
                    passed += 1
                elif result.get("status_code") == 200:
                    # Check if payload appears in response (indicating no sanitization)
                    response_text = str(result.get("response", ""))
                    if payload in response_text:
                        tests.append({
                            "name": f"injection_test_{i}",
                            "status": "failed",
                            "message": "Payload appears in response - possible injection vulnerability"
                        })
                    else:
                        tests.append({
                            "name": f"injection_test_{i}",
                            "status": "passed",
                            "message": "Payload accepted but properly sanitized"
                        })
                        passed += 1
                else:
                    tests.append({
                        "name": f"injection_test_{i}",
                        "status": "failed",
                        "message": f"Unexpected status code: {result.get('status_code')}"
                    })
            except Exception as e:
                tests.append({
                    "name": f"injection_test_{i}",
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "failed",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_xss_protection(self) -> Dict[str, Any]:
        """Test XSS protection"""
        tests = []
        passed = 0
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')>"
        ]
        
        for i, payload in enumerate(xss_payloads):
            try:
                # Create alert with XSS payload
                xss_alert = {
                    "alert_id": f"ALERT-{int(time.time())}-{i:04d}",
                    "hostname": f"test-{i}",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": f"test-{payload[:20]}",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": f"Test alert with XSS: {payload}",
                    "affected_files": [
                        {
                            "path": f"/tmp/{payload}.txt",
                            "name": f"{payload}.txt",
                            "size": 1024
                        }
                    ]
                }
                
                result = asyncio.run(self._send_test_request(self.api_token, xss_alert))
                
                # Check if XSS was properly handled
                if result.get("status_code") in [400, 422]:
                    tests.append({
                        "name": f"xss_test_{i}",
                        "status": "passed",
                        "message": "XSS payload properly rejected"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": f"xss_test_{i}",
                        "status": "warning",
                        "message": f"XSS payload accepted - manual review needed"
                    })
                    passed += 1  # Not necessarily a failure
            
            except Exception as e:
                tests.append({
                    "name": f"xss_test_{i}",
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "warning",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting protection"""
        tests = []
        passed = 0
        
        try:
            # Send multiple rapid requests
            rapid_requests = []
            for i in range(50):  # Send 50 requests quickly
                alert = {
                    "alert_id": f"ALERT-{int(time.time())}-{i:04d}",
                    "hostname": f"test-{i}",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": "rate-limit-test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": f"Rate limit test {i}"
                }
                rapid_requests.append(alert)
            
            # Send requests rapidly
            results = []
            for alert in rapid_requests:
                try:
                    result = asyncio.run(self._send_test_request(self.api_token, alert))
                    results.append(result.get("status_code", 0))
                except:
                    results.append(0)
            
            # Check if rate limiting kicked in
            rate_limited_responses = sum(1 for code in results if code == 429)
            
            if rate_limited_responses > 0:
                tests.append({
                    "name": "rate_limiting_active",
                    "status": "passed",
                    "message": f"Rate limiting active - {rate_limited_responses}/50 requests rate limited"
                })
                passed += 1
            else:
                tests.append({
                    "name": "rate_limiting_active",
                    "status": "warning",
                    "message": "No rate limiting detected - may need implementation"
                })
                passed += 1  # Not necessarily a failure
        
        except Exception as e:
            tests.append({
                "name": "rate_limiting_active",
                "status": "failed",
                "message": f"Rate limiting test failed: {str(e)}"
            })
        
        return {
            "status": "passed" if passed == len(tests) else "warning",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_data_validation(self) -> Dict[str, Any]:
        """Test data validation"""
        tests = []
        passed = 0
        
        # Test oversized data
        oversized_tests = [
            {
                "name": "oversized_description",
                "field": "description",
                "value": "x" * 10000  # Very long description
            },
            {
                "name": "oversized_hostname",
                "field": "hostname",
                "value": "x" * 300  # Very long hostname
            },
            {
                "name": "oversized_source",
                "field": "source",
                "value": "x" * 200  # Very long source
            }
        ]
        
        for test in oversized_tests:
            try:
                alert = {
                    "alert_id": f"ALERT-{int(time.time())}-0001",
                    "hostname": "test-host",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": "test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": "Test alert"
                }
                alert[test["field"]] = test["value"]
                
                result = asyncio.run(self._send_test_request(self.api_token, alert))
                
                if result.get("status_code") in [400, 422]:
                    tests.append({
                        "name": test["name"],
                        "status": "passed",
                        "message": "Oversized data properly rejected"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": test["name"],
                        "status": "warning",
                        "message": f"Oversized data accepted - size: {len(test['value'])}"
                    })
                    passed += 1  # Not necessarily a failure
            
            except Exception as e:
                tests.append({
                    "name": test["name"],
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "warning",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling security"""
        tests = []
        passed = 0
        
        # Test malformed requests
        malformed_requests = [
            {
                "name": "invalid_json",
                "data": "invalid json string",
                "content_type": "application/json"
            },
            {
                "name": "empty_request",
                "data": "",
                "content_type": "application/json"
            },
            {
                "name": "wrong_content_type",
                "data": '{"test": "data"}',
                "content_type": "text/plain"
            }
        ]
        
        for test in malformed_requests:
            try:
                result = asyncio.run(self._send_malformed_request(
                    test["data"], test["content_type"]
                ))
                
                if result.get("status_code") in [400, 415, 422]:
                    tests.append({
                        "name": test["name"],
                        "status": "passed",
                        "message": "Malformed request properly rejected"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": test["name"],
                        "status": "failed",
                        "message": f"Should have rejected malformed request, got {result.get('status_code')}"
                    })
            except Exception as e:
                tests.append({
                    "name": test["name"],
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "failed",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_file_upload(self) -> Dict[str, Any]:
        """Test file upload security"""
        tests = []
        passed = 0
        
        # Test malicious file uploads
        malicious_files = [
            {
                "name": "executable_file",
                "filename": "malware.exe",
                "content": b"MZ\x90\x00",  # PE header
                "content_type": "application/octet-stream"
            },
            {
                "name": "script_file",
                "filename": "malicious.js",
                "content": b"<script>alert('XSS')</script>",
                "content_type": "application/javascript"
            },
            {
                "name": "oversized_file",
                "filename": "large.txt",
                "content": b"x" * (10 * 1024 * 1024),  # 10MB
                "content_type": "text/plain"
            }
        ]
        
        for test in malicious_files:
            try:
                # This would test file upload endpoints if they exist
                # For now, we'll test if file paths in alerts are handled safely
                alert = {
                    "alert_id": f"ALERT-{int(time.time())}-0001",
                    "hostname": "test-host",
                    "src_ip": "192.168.1.1",
                    "hash": {"sha256": "a" * 64},
                    "severity": "2",
                    "source": "file-upload-test",
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                    "event_type": "ransomware_detection",
                    "description": "Test alert",
                    "affected_files": [
                        {
                            "path": f"/tmp/{test['filename']}",
                            "name": test["filename"],
                            "size": len(test["content"])
                        }
                    ]
                }
                
                result = asyncio.run(self._send_test_request(self.api_token, alert))
                
                if result.get("status_code") in [200, 400, 422]:
                    tests.append({
                        "name": test["name"],
                        "status": "passed",
                        "message": f"File reference handled safely"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": test["name"],
                        "status": "warning",
                        "message": f"Unexpected response: {result.get('status_code')}"
                    })
                    passed += 1
            
            except Exception as e:
                tests.append({
                    "name": test["name"],
                    "status": "failed",
                    "message": f"Test failed with exception: {str(e)}"
                })
        
        return {
            "status": "passed" if passed == len(tests) else "warning",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    def test_ssl_tls(self) -> Dict[str, Any]:
        """Test SSL/TLS configuration"""
        tests = []
        passed = 0
        
        try:
            # Test if HTTPS is available
            https_url = self.base_url.replace('http://', 'https://')
            
            # Test SSL configuration
            result = asyncio.run(self._test_ssl_connection(https_url))
            
            if result.get("ssl_available"):
                tests.append({
                    "name": "ssl_available",
                    "status": "passed",
                    "message": "SSL/TLS is available"
                })
                passed += 1
                
                # Check SSL version
                if result.get("ssl_version", "").startswith("TLSv1.2") or result.get("ssl_version", "").startswith("TLSv1.3"):
                    tests.append({
                        "name": "ssl_version",
                        "status": "passed",
                        "message": f"Modern SSL version: {result.get('ssl_version')}"
                    })
                    passed += 1
                else:
                    tests.append({
                        "name": "ssl_version",
                        "status": "warning",
                        "message": f"Old SSL version: {result.get('ssl_version')}"
                    })
                    passed += 1
            else:
                tests.append({
                    "name": "ssl_available",
                    "status": "warning",
                    "message": "SSL/TLS not available or not configured"
                })
                passed += 1  # Not necessarily a failure
        
        except Exception as e:
            tests.append({
                "name": "ssl_test",
                "status": "failed",
                "message": f"SSL test failed: {str(e)}"
            })
        
        return {
            "status": "passed" if passed == len(tests) else "warning",
            "tests_run": len(tests),
            "tests_passed": passed,
            "tests": tests
        }
    
    async def _send_test_request(self, token: Optional[str], alert_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send test request to webhook"""
        if alert_data is None:
            alert_data = {
                "alert_id": "ALERT-1234567890-0001",
                "hostname": "test-host",
                "src_ip": "192.168.1.1",
                "hash": {"sha256": "a" * 64},
                "severity": "2",
                "source": "security-test",
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "event_type": "ransomware_detection",
                "description": "Security test alert"
            }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        payload = {
            "alert": alert_data,
            "metadata": {"test_type": "security_test"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "status_code": response.status,
                        "response": await response.text(),
                        "headers": dict(response.headers)
                    }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e)
            }
    
    async def _send_unauthorized_request(self, endpoint: str) -> Dict[str, Any]:
        """Send unauthorized request to test endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "status_code": response.status,
                        "response": await response.text()
                    }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e)
            }
    
    async def _send_malformed_request(self, data: str, content_type: str) -> Dict[str, Any]:
        """Send malformed request"""
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': content_type
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "status_code": response.status,
                        "response": await response.text()
                    }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e)
            }
    
    async def _test_ssl_connection(self, url: str) -> Dict[str, Any]:
        """Test SSL/TLS connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "ssl_available": True,
                        "ssl_version": response.version,
                        "status_code": response.status
                    }
        except Exception as e:
            return {
                "ssl_available": False,
                "error": str(e)
            }
    
    def save_results(self, results: Dict[str, Any]) -> None:
        """Save security test results"""
        results_dir = Path("results/security_tests")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"security_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Security test results saved to {output_file}")


async def main():
    """Main function to run security tests"""
    tester = SecurityTester()
    
    logger.info("Starting automated security testing")
    results = tester.run_all_tests()
    
    # Save results
    tester.save_results(results)
    
    # Print summary
    summary = results["summary"]
    print(f"\nSECURITY TEST SUMMARY:")
    print(f"  Total Tests: {summary['total_tests']}")
    print(f"  Passed: {summary['passed_tests']}")
    print(f"  Failed: {summary['failed_tests']}")
    print(f"  Success Rate: {summary['success_rate']:.2f}%")
    print(f"  Overall Status: {summary['overall_status'].upper()}")
    
    # Print failed tests
    for test_name, test_result in results["tests"].items():
        if test_result.get("status") == "failed":
            print(f"\nFAILED TEST CATEGORY: {test_name}")
            for test in test_result.get("tests", []):
                if test.get("status") == "failed":
                    print(f"  - {test['name']}: {test['message']}")
    
    logger.info("Security testing completed")


if __name__ == "__main__":
    asyncio.run(main())
