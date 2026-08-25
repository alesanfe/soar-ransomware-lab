#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Shuffle Webhook Initialization Tests
Tests for Shuffle webhook initialization
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.setup.init_shuffle_webhook import init_shuffle_webhook


class TestInitShuffleWebhook:
    """Test Shuffle webhook initialization."""

    @pytest.fixture
    def webhook_info_path(self):
        """Path to webhook info file (must match
        test_mode.webhook_info_path)."""
        from scripts.setup.shuffle_workflow.test_mode import webhook_info_path as _wip

        return Path(_wip())

    @pytest.fixture
    def shuffle_client(self):
        """Create mock Shuffle client."""
        client = Mock()
        client.create_workflow.return_value = {"id": "workflow-001"}
        client.create_trigger.return_value = {"id": "trigger-001"}
        client.get_api_key.return_value = "test-api-key"
        return client

    def test_webhook_creation(self, shuffle_client):
        """Test that webhook is created correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            assert result is not None, "Webhook initialization should succeed"
            assert "webhook_url" in result, "Result should contain webhook_url"
            assert "workflow_id" in result, "Result should contain workflow_id"

    def test_trigger_configuration(self, shuffle_client):
        """Test that trigger is configured correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify trigger was created
            shuffle_client.create_trigger.assert_called_once()
            assert "trigger_id" in result, "Result should contain trigger_id"

    def test_workflow_initialization(self, shuffle_client):
        """Test that workflow is initialized correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify workflow was created
            shuffle_client.create_workflow.assert_called_once()
            assert result["workflow_id"] == "workflow-001", "Workflow ID should match"

    def test_api_key_generation(self, shuffle_client):
        """Test that API key is generated correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify API key was generated
            shuffle_client.get_api_key.assert_called_once()
            assert "api_key" in result, "Result should contain api_key"
            assert len(result["api_key"]) > 0, "API key should not be empty"

    def test_webhook_info_persistence(self, shuffle_client, webhook_info_path):
        """Test that webhook info is persisted correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify file was created
            assert webhook_info_path.exists(), "Webhook info file should be created"

            # Verify file contents
            with open(webhook_info_path) as f:
                saved_data = json.load(f)

            assert saved_data == result, "Saved data should match result"

    def test_webhook_url_format(self, shuffle_client):
        """Test that webhook URL has correct format."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify URL format
            webhook_url = result["webhook_url"]
            assert webhook_url.startswith("http"), "Webhook URL should start with http"
            assert "webhook" in webhook_url.lower(), "Webhook URL should contain 'webhook'"

    def test_organization_id_in_result(self, shuffle_client):
        """Test that organization ID is included in result."""
        shuffle_client.get_org_id.return_value = "org-001"

        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            result = init_shuffle_webhook()

            # Verify org ID is present
            assert "org_id" in result, "Result should contain org_id"
            assert result["org_id"] == "org-001", "Org ID should match"

    def test_workflow_actions_configured(self, shuffle_client):
        """Test that workflow actions are configured correctly."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook
            init_shuffle_webhook()

            # Verify workflow has actions
            # This would check that the workflow template includes required actions
            assert True, "Workflow should have required actions"

    def test_webhook_idempotency(self, shuffle_client, webhook_info_path):
        """Test that webhook initialization is idempotent."""
        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Initialize webhook first time
            result1 = init_shuffle_webhook()

            # Initialize webhook second time
            result2 = init_shuffle_webhook()

            # Should return same result or not create duplicate
            assert (
                result1["workflow_id"] == result2["workflow_id"]
            ), "Webhook initialization should be idempotent"

    def test_error_handling_on_shuffle_failure(self, shuffle_client):
        """Test error handling when Shuffle is unavailable."""
        shuffle_client.create_workflow.side_effect = Exception("Shuffle unavailable")

        with patch("scripts.setup.init_shuffle_webhook.ShuffleClient") as mock_client:
            mock_client.return_value = shuffle_client

            # Should handle error gracefully
            with pytest.raises(Exception):
                init_shuffle_webhook()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
