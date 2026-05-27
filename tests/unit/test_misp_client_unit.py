#!/usr/bin/env python3
"""
Unit tests for MISP client
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from soar_lab.integrations.misp_client import MISPClient


class TestMISPClient:
    """Test MISP client functionality"""

    def test_init_with_defaults(self):
        """Test MISP client initialization with defaults"""
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        assert client.base_url == "http://localhost:8082"

    def test_init_with_env_vars(self):
        """Test MISP client initialization with settings"""
        client = MISPClient(base_url="http://test-misp:8082", api_key="test-key")
        assert client.base_url == "http://test-misp:8082"

    def test_init_with_params(self):
        """Test MISP client initialization with parameters"""
        client = MISPClient(base_url="http://custom-misp:8082", api_key="custom-key")
        assert client.base_url == "http://custom-misp:8082"

    def test_default_headers(self):
        """Test default headers generation"""
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        headers = client._default_headers("test-key")
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "test-key"

    def test_default_headers_no_api_key(self):
        """Test default headers without API key"""
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        headers = client._default_headers(None)
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    @patch('soar_lab.integrations.misp_client.MISPClient.post')
    def test_search_events(self, mock_post):
        """Test search events"""
        mock_post.return_value = {"response": [{"event": "data"}]}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        result = client.search_events("test-value")
        assert result == [{"event": "data"}]
        mock_post.assert_called_once_with("/events/restSearch", data={"value": "test-value"})

    @patch('soar_lab.integrations.misp_client.MISPClient.post')
    def test_search_events_with_type(self, mock_post):
        """Test search events with type attribute"""
        mock_post.return_value = {"response": [{"event": "data"}]}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        result = client.search_events("test-value", type_attribute="ip-dst")
        assert result == [{"event": "data"}]
        mock_post.assert_called_once_with("/events/restSearch",
                                          data={"value": "test-value", "type_attribute": "ip-dst"})

    @patch('soar_lab.integrations.misp_client.MISPClient.get')
    def test_get_event(self, mock_get):
        """Test get event"""
        mock_get.return_value = {"event": "data"}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        result = client.get_event("123")
        assert result == {"event": "data"}
        mock_get.assert_called_once_with("/events/123")

    @patch('soar_lab.integrations.misp_client.MISPClient.post')
    def test_create_event(self, mock_post):
        """Test create event"""
        mock_post.return_value = {"event": "created"}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        event_data = {"info": "test event"}
        result = client.create_event(event_data)
        assert result == {"event": "created"}
        mock_post.assert_called_once_with("/events", data=event_data)

    @patch('soar_lab.integrations.misp_client.MISPClient.post')
    def test_add_attribute(self, mock_post):
        """Test add attribute"""
        mock_post.return_value = {"attribute": "added"}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        attr_data = {"type": "ip-dst", "value": "1.2.3.4"}
        result = client.add_attribute("123", attr_data)
        assert result == {"attribute": "added"}
        mock_post.assert_called_once_with("/attributes/add/123", data=attr_data)

    @patch('soar_lab.integrations.misp_client.MISPClient.get')
    def test_health_check_success(self, mock_get):
        """Test health check success"""
        mock_get.return_value = {"status": "ok"}
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        result = client.health_check()
        assert result is True
        mock_get.assert_called_once_with("/users/heartbeat")

    @patch('soar_lab.integrations.misp_client.MISPClient.get')
    def test_health_check_failure(self, mock_get):
        """Test health check failure"""
        mock_get.side_effect = Exception("Connection error")
        client = MISPClient(base_url="http://localhost:8082", api_key="test-key")
        result = client.health_check()
        assert result is False
