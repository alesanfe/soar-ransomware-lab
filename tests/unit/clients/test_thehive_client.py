#!/usr/bin/env python3
"""Unit tests for soar_lab.integrations.thehive_client."""

from unittest.mock import Mock

import pytest

from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


class TestTheHiveClient:
    """Test TheHiveClient integration adapter."""

    def test_initialization_with_base_url_and_api_key(self):
        """Test successful initialization with base_url and api_key."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")

        # When running inside Docker, localhost URLs are converted to container names
        import os

        if os.path.exists("/.dockerenv"):
            assert client.base_url == "http://thehive:9000"
        else:
            assert client.base_url == "http://localhost:9000"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider."""
        mock_config_provider = Mock()
        mock_config_provider.get.side_effect = lambda key, default=None: {
            "thehive_url": "http://localhost:9000",
            "thehive_api_key": "test-key",
        }.get(key, default)

        client = TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

        # When running inside Docker, localhost URLs are converted to container names
        import os

        if os.path.exists("/.dockerenv"):
            assert client.base_url == "http://thehive:9000"
        else:
            assert client.base_url == "http://localhost:9000"

    def test_initialization_requires_url(self):
        """Test that base_url is required when not in config_provider."""
        with pytest.raises(ValueError, match="thehive_url must be provided"):
            TheHiveClient(base_url=None, api_key="test-key")

    def test_initialization_requires_api_key(self):
        """Test that api_key is required when not in config_provider."""
        with pytest.raises(ValueError, match="thehive_api_key must be provided"):
            TheHiveClient(base_url="http://localhost:9000", api_key=None)

    def test_initialization_config_provider_missing_url(self):
        """Test that config_provider must provide thehive_url."""
        mock_config_provider = Mock()
        mock_config_provider.get.return_value = None

        with pytest.raises(ValueError, match="thehive_url must be provided"):
            TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

    def test_initialization_config_provider_missing_api_key(self):
        """Test that config_provider must provide thehive_api_key."""
        mock_config_provider = Mock()
        mock_config_provider.get.side_effect = lambda key, default=None: {
            "thehive_url": "http://localhost:9000",
            "thehive_api_key": None,
        }.get(key, default)

        with pytest.raises(ValueError, match="thehive_api_key must be provided"):
            TheHiveClient(base_url=None, api_key=None, config_provider=mock_config_provider)

    def test_create_alert(self):
        """Test creating an alert."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "alert-123"})

        alert = {"title": "Test Alert", "type": "external"}
        result = client.create_alert(alert)

        client.post.assert_called_once_with("/api/alert", data=alert)
        assert result == {"id": "alert-123"}

    def test_create_case(self):
        """Test creating a case."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "case-123"})

        case = {"title": "Test Case", "severity": 2}
        result = client.create_case(case)

        client.post.assert_called_once_with("/api/case", data=case)
        assert result == {"id": "case-123"}

    def test_get_case(self):
        """Test retrieving a case by ID."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value={"id": "case-123", "title": "Test Case"})

        result = client.get_case("case-123")

        client.get.assert_called_once_with("/api/case/case-123")
        assert result == {"id": "case-123", "title": "Test Case"}

    def test_add_observable(self):
        """Test adding an observable to a case."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "obs-123"})

        observable = {"dataType": "ip", "data": "192.168.1.1"}
        result = client.add_observable("case-123", observable)

        # The client now uses /api/case/{case_id}/artifact with defaults
        expected_payload = {
            "dataType": "ip",
            "data": "192.168.1.1",
            "tlp": 2,
            "ioc": True,
            "sighted": False,
            "tags": [],
            "message": "",
        }
        client.post.assert_called_once_with("/api/case/case-123/artifact", data=expected_payload)
        assert result == {"id": "obs-123"}

    def test_list_cases(self):
        """Test listing all cases."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value=[{"id": "case-1"}, {"id": "case-2"}])

        result = client.list_cases()

        client.get.assert_called_once_with("/api/case", params={"range": "0-1000"})
        assert result == [{"id": "case-1"}, {"id": "case-2"}]

    def test_list_cases_empty(self):
        """Test listing cases when response is not a list."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value={"error": "not found"})

        result = client.list_cases()

        assert result == []

    def test_search_cases(self):
        """Test searching cases with query (uses POST /api/case/_search)"""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "case-1"}])

        result = client.search_cases(query={"status": "Open"}, range_="0-50")

        # search_cases with query uses POST /api/case/_search
        expected_data = {"query": {"status": "Open"}, "range": "0-50"}
        client.post.assert_called_once_with("/api/case/_search", data=expected_data)
        assert result == [{"id": "case-1"}]

    def test_search_cases_default_params(self):
        """Test searching cases with default parameters (delegates to
        list_cases)"""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value=[{"id": "case-1"}])

        result = client.search_cases()

        # search_cases now delegates to list_cases which uses GET with params
        client.get.assert_called_once_with("/api/case", params={"range": "0-1000"})
        assert result == [{"id": "case-1"}]

    def test_get_case_observables(self):
        """Test getting case observables (uses POST /api/case/{id}/artifact/_search)"""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "obs-1"}, {"id": "obs-2"}])

        result = client.get_case_observables("case-123")

        client.post.assert_called_once_with(
            "/api/case/case-123/artifact/_search", data={"query": {}, "range": "all"}
        )
        assert result == [{"id": "obs-1"}, {"id": "obs-2"}]

    def test_close_case(self):
        """Test closing a case."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "case-123", "status": "Resolved"})

        result = client.close_case("case-123", resolution="TruePositive", summary="Test summary")

        client.post.assert_called_once_with(
            "/api/case/case-123",
            data={
                "status": "Resolved",
                "resolutionStatus": "TruePositive",
                "summary": "Test summary",
            },
        )
        assert result == {"id": "case-123", "status": "Resolved"}

    def test_close_case_default_params(self):
        """Test closing a case with default parameters."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"id": "case-123", "status": "Resolved"})

        result = client.close_case("case-123")

        client.post.assert_called_once_with(
            "/api/case/case-123",
            data={
                "status": "Resolved",
                "resolutionStatus": "TruePositive",
                "summary": "",
            },
        )
        assert result == {"id": "case-123", "status": "Resolved"}

    def test_list_case_tasks(self):
        """Test listing case tasks."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value=[{"id": "task-1"}, {"id": "task-2"}])

        result = client.list_case_tasks("case-123")

        client.post.assert_called_once_with(
            "/api/case/case-123/task/_search", data={"query": {}, "range": "all"}
        )
        assert result == [{"id": "task-1"}, {"id": "task-2"}]

    def test_list_case_tasks_empty(self):
        """Test listing case tasks when response is not a list."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.post = Mock(return_value={"error": "not found"})

        result = client.list_case_tasks("case-123")

        assert result == []

    def test_health_check_success(self):
        """Test health check when service is reachable."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()

        assert result is True

    def test_health_check_failure(self):
        """Test health check when service is not reachable."""
        client = TheHiveClient(base_url="http://localhost:9000", api_key="test-key")
        client.get = Mock(side_effect=Exception("Connection error"))

        result = client.health_check()

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
