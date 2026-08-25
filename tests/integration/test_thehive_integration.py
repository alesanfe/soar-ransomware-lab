#!/usr/bin/env python3
"""Integration tests for TheHive client.

Tests TheHive client functionality using mocks when service is not
available.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient

THEHIVE_URL = os.getenv("THEHIVE_URL", "http://localhost:9000")
THEHIVE_API_KEY = os.getenv("THEHIVE_API_KEY", "")


@pytest.fixture(scope="module")
def thehive_client():
    return TheHiveClient(base_url=THEHIVE_URL, api_key=THEHIVE_API_KEY)


@pytest.mark.integration
class TestTheHiveHealth:
    def test_health_check_returns_bool(self, thehive_client):
        with patch.object(thehive_client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            result = thehive_client.health_check()
            assert isinstance(result, bool)


@pytest.mark.integration
class TestTheHiveAlerts:
    def test_create_alert_returns_dict(self, thehive_client):
        with patch.object(thehive_client._session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "test-alert-id"}
            mock_post.return_value = mock_response
            alert = {
                "title": "Integration test alert",
                "description": "Created by automated integration test",
                "type": "external",
                "source": "soar-lab-test",
                "sourceRef": "IT-001",
                "severity": 2,
                "tlp": 2,
                "tags": ["integration-test"],
            }
            response = thehive_client.create_alert(alert)
            assert isinstance(response, dict)

    def test_list_cases_returns_list(self, thehive_client):
        with patch.object(thehive_client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response
            cases = thehive_client.list_cases()
            assert isinstance(cases, list)


@pytest.mark.integration
class TestTheHiveErrorHandling:
    def test_unreachable_host_raises_integration_error(self):
        client = TheHiveClient(base_url="http://localhost:19999", api_key="bad")
        with pytest.raises(IntegrationError):
            client.get_case("nonexistent")
