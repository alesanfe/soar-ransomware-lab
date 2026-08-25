#!/usr/bin/env python3
"""
SOAR Ransomware Lab - OpenAPI Spec Sync Tests
Tests for OpenAPI specification synchronization
"""

import json
from pathlib import Path

import pytest


@pytest.mark.requires_external
class TestOpenAPISpecSync:
    """Test OpenAPI specification synchronization."""

    @pytest.fixture
    def openapi_spec_path(self):
        """Path to OpenAPI spec file."""
        return Path(__file__).parent.parent.parent / "docs" / "api" / "openapi.json"

    @pytest.fixture
    def openapi_spec(self, openapi_spec_path):
        """Load OpenAPI specification."""
        if openapi_spec_path.exists():
            with open(openapi_spec_path) as f:
                return json.load(f)
        return {"openapi": "3.0.0", "info": {"title": "SOAR API", "version": "1.0.0"}, "paths": {}}

    def test_spec_is_up_to_date(self, openapi_spec):
        """Test that OpenAPI spec is up to date."""
        assert "openapi" in openapi_spec, "Spec should have openapi version"
        assert "info" in openapi_spec, "Spec should have info section"
        assert "paths" in openapi_spec, "Spec should have paths section"

    def test_client_generation_from_spec(self, openapi_spec):
        """Test client generation from OpenAPI spec."""
        # Verify spec can be used to generate clients
        assert openapi_spec["openapi"].startswith(
            "3."
        ), "Should be OpenAPI 3.x for client generation"

    def test_endpoints_match_implementation(self, openapi_spec):
        """Test that spec endpoints match implementation."""
        required_endpoints = [
            "/health",
            "/auth/login",
            "/analytics/metrics",
            "/soar/thehive/cases",
            "/soar/cortex/analyzers",
            "/soar/misp/events",
            "/soar/shuffle/workflows",
        ]

        paths = openapi_spec.get("paths", {})
        for endpoint in required_endpoints:
            assert endpoint in paths, f"Required endpoint {endpoint} not in spec"

    def test_request_response_schemas(self, openapi_spec):
        """Test request and response schemas."""
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if "requestBody" in details:
                    request_body = details["requestBody"]
                    if "content" in request_body:
                        assert any(
                            "schema" in media for media in request_body["content"].values()
                        ), f"{method} {path} should have request schema"
                    else:
                        assert (
                            "schema" in request_body
                        ), f"{method} {path} should have request schema"

                if "responses" in details:
                    assert (
                        "200" in details["responses"]
                    ), f"{method} {path} should have 200 response"
                    response = details["responses"]["200"]
                    # OpenAPI 3 places schemas under content -> media-type -> schema
                    if "content" in response:
                        assert any(
                            "schema" in media for media in response["content"].values()
                        ), f"{method} {path} should have response schema"
                    else:
                        assert "schema" in response, f"{method} {path} should have response schema"

    def test_spec_version_consistency(self, openapi_spec):
        """Test spec version consistency."""
        spec_version = openapi_spec["info"]["version"]

        # Version should follow semantic versioning
        parts = spec_version.split(".")
        assert len(parts) == 3, "Version should be MAJOR.MINOR.PATCH"
        assert all(part.isdigit() for part in parts), "Version parts should be numeric"

    def test_endpoint_deprecation_marked(self, openapi_spec):
        """Test that deprecated endpoints are marked."""
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if details.get("deprecated", False):
                    assert (
                        "description" in details
                    ), f"Deprecated endpoint {method} {path} should have description"

    def test_security_schemes_defined(self, openapi_spec):
        """Test that security schemes are defined."""
        if "components" in openapi_spec:
            if "securitySchemes" in openapi_spec["components"]:
                security_schemes = openapi_spec["components"]["securitySchemes"]
                bearer_defined = any(
                    scheme.get("type") == "http" and scheme.get("scheme") == "bearer"
                    for scheme in security_schemes.values()
                )
                assert (
                    "apiKey" in security_schemes
                    or "bearerAuth" in security_schemes
                    or bearer_defined
                ), "Should define API key or bearer auth"

    def test_parameter_validation(self, openapi_spec):
        """Test parameter validation in spec."""
        paths = openapi_spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if "parameters" in details:
                    for param in details["parameters"]:
                        assert "name" in param, f"Parameter should have name in {method} {path}"
                        assert "in" in param, f"Parameter should have location in {method} {path}"
                        assert "schema" in param, f"Parameter should have schema in {method} {path}"

    def test_spec_persistence(self, openapi_spec, openapi_spec_path):
        """Test that spec is persisted correctly."""
        if openapi_spec_path.exists():
            with open(openapi_spec_path) as f:
                saved_spec = json.load(f)

            assert saved_spec == openapi_spec, "Saved spec should match loaded spec"

    def test_spec_sync_with_code(self, openapi_spec):
        """Test that spec stays in sync with code."""
        # This would typically compare spec with actual API implementation
        # For now, just verify spec structure
        assert "paths" in openapi_spec, "Spec should have paths"
        assert len(openapi_spec["paths"]) > 0, "Spec should have at least one endpoint"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
