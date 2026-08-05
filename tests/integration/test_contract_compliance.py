#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Contract Compliance Tests
Tests for service contract compliance and API versioning
"""

import json
import pytest
from pathlib import Path
from soar_lab.api.contracts import ServiceContract, APIContract
from soar_lab.api.validation import validate_response_schema
from unittest.mock import Mock, patch


class TestContractCompliance:
    """Test service contract compliance"""

    @pytest.fixture
    def thehive_contract(self):
        """Load TheHive API contract"""
        contract_path = Path(__file__).parent.parent.parent / "contracts" / "thehive.json"
        if contract_path.exists():
            with open(contract_path) as f:
                return ServiceContract.from_dict(json.load(f))
        return ServiceContract(
            service_name="thehive",
            version="1.0.0",
            endpoints={
                "/api/case": {
                    "GET": {"response_schema": {"type": "array"}},
                    "POST": {"request_schema": {"type": "object"}}
                }
            }
        )

    @pytest.fixture
    def cortex_contract(self):
        """Load Cortex API contract"""
        return ServiceContract(
            service_name="cortex",
            version="1.0.0",
            endpoints={
                "/api/analyzer": {
                    "GET": {"response_schema": {"type": "array"}},
                    "POST": {"request_schema": {"type": "object"}}
                }
            }
        )

    @pytest.fixture
    def misp_contract(self):
        """Load MISP API contract"""
        return ServiceContract(
            service_name="misp",
            version="1.0.0",
            endpoints={
                "/events": {
                    "GET": {"response_schema": {"type": "array"}},
                    "POST": {"request_schema": {"type": "object"}}
                }
            }
        )

    def test_thehive_response_schema_validation(self, thehive_contract):
        """Test that TheHive responses match contract schema"""
        valid_response = [
            {
                "id": "123",
                "title": "Test Case",
                "description": "Test description",
                "severity": 2,
                "status": "Open"
            }
        ]

        is_valid, errors = validate_response_schema(
            valid_response,
            thehive_contract.endpoints["/api/case"]["GET"]["response_schema"]
        )
        assert is_valid, f"Valid response should pass: {errors}"

    def test_cortex_response_schema_validation(self, cortex_contract):
        """Test that Cortex responses match contract schema"""
        valid_response = [
            {
                "id": "analyzer-001",
                "name": "VirusTotal",
                "dataTypeList": ["file", "domain"]
            }
        ]

        is_valid, errors = validate_response_schema(
            valid_response,
            cortex_contract.endpoints["/api/analyzer"]["GET"]["response_schema"]
        )
        assert is_valid, f"Valid response should pass: {errors}"

    def test_misp_response_schema_validation(self, misp_contract):
        """Test that MISP responses match contract schema"""
        valid_response = [
            {
                "id": "event-001",
                "info": "Test Event",
                "Attribute": [
                    {"type": "md5", "value": "d41d8cd98f00b204e9800998ecf8427e"}
                ]
            }
        ]

        is_valid, errors = validate_response_schema(
            valid_response,
            misp_contract.endpoints["/events"]["GET"]["response_schema"]
        )
        assert is_valid, f"Valid response should pass: {errors}"

    def test_invalid_response_rejected(self, thehive_contract):
        """Test that invalid responses are rejected"""
        invalid_response = {"invalid": "structure"}

        is_valid, errors = validate_response_schema(
            invalid_response,
            thehive_contract.endpoints["/api/case"]["GET"]["response_schema"]
        )
        assert not is_valid, "Invalid response should be rejected"
        assert errors, "Should return validation errors"

    def test_api_version_compatibility(self, thehive_contract):
        """Test API version compatibility"""
        # Test that current version is supported
        assert thehive_contract.version in thehive_contract.supported_versions

        # Test that deprecated versions are marked
        deprecated_versions = thehive_contract.get_deprecated_versions()
        for version in deprecated_versions:
            assert thehive_contract.is_deprecated(version)

    def test_endpoint_deprecation_warning(self, thehive_contract):
        """Test that deprecated endpoints return warnings"""
        deprecated_endpoint = "/api/legacy/case"
        if thehive_contract.is_endpoint_deprecated(deprecated_endpoint):
            warning = thehive_contract.get_deprecation_warning(deprecated_endpoint)
            assert warning, "Deprecated endpoint should have warning message"

    def test_contract_endpoint_coverage(self, thehive_contract):
        """Test that all endpoints are covered in contract"""
        required_endpoints = [
            "/api/case",
            "/api/case/_search",
            "/api/observable",
            "/api/case/_bulk"
        ]

        for endpoint in required_endpoints:
            assert endpoint in thehive_contract.endpoints, \
                f"Required endpoint {endpoint} not in contract"

    def test_request_schema_validation(self, thehive_contract):
        """Test that requests match contract schema"""
        valid_request = {
            "title": "Test Case",
            "description": "Test description",
            "severity": 2,
            "tags": ["ransomware", "malware"]
        }

        is_valid, errors = validate_response_schema(
            valid_request,
            thehive_contract.endpoints["/api/case"]["POST"]["request_schema"]
        )
        assert is_valid, f"Valid request should pass: {errors}"

    def test_response_headers_validation(self, thehive_contract):
        """Test that response headers match contract"""
        expected_headers = thehive_contract.get_required_headers()

        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-API-Version": "1.0.0"
        }

        for header in expected_headers:
            assert header in mock_response.headers, \
                f"Required header {header} not in response"

    def test_rate_limit_compliance(self, thehive_contract):
        """Test that rate limits comply with contract"""
        rate_limit = thehive_contract.get_rate_limit()

        assert rate_limit["requests_per_minute"] > 0
        assert rate_limit["requests_per_hour"] > 0
        assert rate_limit["requests_per_day"] > 0

    def test_error_response_schema(self, thehive_contract):
        """Test that error responses match contract"""
        error_response = {
            "error": "Validation error",
            "code": 400,
            "message": "Invalid request"
        }

        error_schema = thehive_contract.get_error_schema()
        is_valid, errors = validate_response_schema(error_response, error_schema)
        assert is_valid, f"Error response should match schema: {errors}"

    def test_contract_version_migration(self, thehive_contract):
        """Test contract version migration"""
        old_version = "0.9.0"
        new_version = "1.0.0"

        migration_guide = thehive_contract.get_migration_guide(old_version, new_version)
        assert migration_guide, "Should provide migration guide between versions"

    def test_backward_compatibility(self, thehive_contract):
        """Test backward compatibility with previous versions"""
        previous_version = "0.9.0"

        # Check that previous version fields are still supported
        old_request = {
            "title": "Test Case",
            "description": "Test",
            "severity": "2"  # String severity (old format)
        }

        is_valid, errors = validate_response_schema(
            old_request,
            thehive_contract.endpoints["/api/case"]["POST"]["request_schema"]
        )
        # Should be valid due to backward compatibility
        assert is_valid, f"Old format should be supported: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
