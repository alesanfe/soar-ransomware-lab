#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Version Compatibility Tests
Tests for version compatibility and migration
"""

from unittest.mock import Mock, patch

import pytest

from soar_lab.infrastructure.integrations.cortex.client import CortexClient
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


class TestVersionCompatibility:
    """Test version compatibility and migration."""

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing."""
        return TheHiveClient(base_url="http://localhost:9000", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def cortex_client(self):
        """Create Cortex client for testing."""
        return CortexClient(base_url="http://localhost:9001", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing."""
        return MISPClient(base_url="http://localhost:8083", api_key="test-key", verify_ssl=False)

    def test_thehive_backward_compatibility(self, thehive_client):
        """Test backward compatibility with previous TheHive versions."""
        with patch.object(thehive_client.session, "get") as mock_get:
            # Simulate old version response
            mock_get.return_value = Mock(
                status_code=200, json=lambda: {"version": "4.0.0", "build": "2020-01-01"}
            )

            version_info = thehive_client.get_version()
            assert version_info["version"] == "4.0.0", "Should work with old version"

    def test_cortex_backward_compatibility(self, cortex_client):
        """Test backward compatibility with previous Cortex versions."""
        with patch.object(cortex_client.session, "get") as mock_get:
            # Simulate old version response
            mock_get.return_value = Mock(
                status_code=200, json=lambda: {"version": "3.0.0", "build": "2020-01-01"}
            )

            version_info = cortex_client.get_version()
            assert version_info["version"] == "3.0.0", "Should work with old version"

    def test_misp_backward_compatibility(self, misp_client):
        """Test backward compatibility with previous MISP versions."""
        with patch.object(misp_client.session, "get") as mock_get:
            # Simulate old version response
            mock_get.return_value = Mock(status_code=200, json=lambda: {"version": "2.4.0"})

            version_info = misp_client.get_server_info()
            assert version_info["version"] == "2.4.0", "Should work with old version"

    def test_data_migration(self, thehive_client):
        """Test data migration between versions."""
        # Simulate old data format
        old_case = {
            "title": "Old Case",
            "description": "Old description",
            "severity": "2",  # String (old format)
            "status": "Open",
        }

        # Migrate to new format
        migrated_case = thehive_client.migrate_case_format(old_case)

        assert migrated_case["severity"] == 2, "Severity should be migrated to integer"
        assert isinstance(migrated_case["severity"], int), "Severity should be integer"

    def test_api_version_negotiation(self, thehive_client):
        """Test API version negotiation."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200, json=lambda: {"version": "5.0.0", "api_versions": ["v1", "v2"]}
            )

            version_info = thehive_client.get_version()
            assert "v1" in version_info["api_versions"], "Should support v1 API"
            assert "v2" in version_info["api_versions"], "Should support v2 API"

    def test_rollback_capability(self, thehive_client):
        """Test rollback capability after upgrade."""
        # Simulate upgrade
        upgraded_data = {"version": "5.0.0", "new_field": "value"}

        # Simulate rollback
        rolled_back_data = thehive_client.rollback_data_format(upgraded_data)

        assert "new_field" not in rolled_back_data, "New field should be removed on rollback"
        assert rolled_back_data["version"] == "4.0.0", "Version should be rolled back"

    def test_schema_evolution(self, thehive_client):
        """Test schema evolution compatibility."""
        # Old schema
        old_schema = {"title": "string", "description": "string", "severity": "string"}

        # New schema
        new_schema = {
            "title": "string",
            "description": "string",
            "severity": "integer",
            "tags": "array",
        }

        # Check compatibility
        is_compatible = thehive_client.check_schema_compatibility(old_schema, new_schema)
        assert is_compatible, "Schema evolution should be compatible"

    def test_deprecated_field_handling(self, thehive_client):
        """Test handling of deprecated fields."""
        case_with_deprecated = {
            "title": "Test Case",
            "description": "Test",
            "severity": 2,
            "old_field": "deprecated_value",  # Deprecated field
        }

        # Should handle deprecated field gracefully
        processed_case = thehive_client.process_deprecated_fields(case_with_deprecated)

        assert "old_field" not in processed_case, "Deprecated field should be removed"
        assert processed_case["severity"] == 2, "Valid fields should be preserved"

    def test_version_specific_features(self, thehive_client):
        """Test version-specific feature detection."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"version": "5.0.0", "features": ["advanced_search", "automation"]},
            )

            version_info = thehive_client.get_version()
            assert "advanced_search" in version_info["features"], "Should detect features"

    def test_minimum_version_requirement(self, thehive_client):
        """Test minimum version requirement."""
        current_version = "5.0.0"
        minimum_version = "4.0.0"

        is_compatible = thehive_client.check_version_compatibility(current_version, minimum_version)
        assert is_compatible, "Current version should meet minimum requirement"

    def test_incompatible_version_detection(self, thehive_client):
        """Test detection of incompatible versions."""
        current_version = "3.0.0"
        minimum_version = "4.0.0"

        is_compatible = thehive_client.check_version_compatibility(current_version, minimum_version)
        assert not is_compatible, "Should detect incompatible version"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
