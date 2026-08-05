#!/usr/bin/env python3
"""
Unit tests for misp_client.py
"""

import pytest
from soar_lab.infrastructure.external.integrations.misp_client import MISPClient
from unittest.mock import Mock, patch


class TestMISPClient:
    """Test MISPClient"""

    def test_initialization_with_base_url_and_api_key(self):
        """Test initialization with base_url and api_key"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        assert "Accept" in client._session.headers
        assert client._session.headers["Accept"] == "application/json"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'misp_url': 'http://localhost:8083',
            'misp_api_key': 'test-key'
        }.get(key, default)

        client = MISPClient(base_url=None, api_key=None, config_provider=mock_config)
        assert "Accept" in client._session.headers

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError"""
        with pytest.raises(ValueError, match="misp_url must be provided"):
            MISPClient(base_url=None, api_key="test-key")

    def test_initialization_without_api_key_raises(self):
        """Test initialization without api_key raises ValueError"""
        with pytest.raises(ValueError, match="misp_api_key must be provided"):
            MISPClient(base_url="http://localhost:8083", api_key=None)

    def test_default_headers_with_api_key(self):
        """Test _default_headers with api_key"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        headers = client._default_headers("custom-key")
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "custom-key"

    def test_default_headers_without_api_key(self):
        """Test _default_headers without api_key"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        headers = client._default_headers(None)
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_search_events(self):
        """Test searching events"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        result = client.search_events("8.8.8.8")
        assert result == [{"id": "1"}]

    def test_search_events_with_type_attribute(self):
        """Test searching events with type_attribute filter"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        result = client.search_events("8.8.8.8", type_attribute="ip-dst")
        assert result == [{"id": "1"}]

    @pytest.mark.skip(reason="Requires proper HTTP layer mocking - revisit")
    def test_get_event(self):
        """Test getting a specific event"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key", verify_ssl=False)
        # Mock the parent class get method
        with patch.object(type(client), 'get', return_value={"id": "1", "info": "test event"}):
            result = client.get_event("1")
            assert result == {"id": "1", "info": "test event"}

    def test_create_event(self):
        """Test creating a new event"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"id": "1", "info": "new event"})

        result = client.create_event({"info": "new event"})
        assert result == {"id": "1", "info": "new event"}

    def test_add_attribute(self):
        """Test adding an attribute to an event"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"id": "1", "value": "8.8.8.8"})

        result = client.add_attribute("1", {"type": "ip-dst", "value": "8.8.8.8"})
        assert result == {"id": "1", "value": "8.8.8.8"}

    def test_search_attributes(self):
        """Test searching attributes"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": [{"id": "1"}]}})

        result = client.search_attributes(value="8.8.8.8")
        assert result == [{"id": "1"}]

    def test_search_attributes_with_type(self):
        """Test searching attributes with type filter"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": [{"id": "1"}]}})

        result = client.search_attributes(value="8.8.8.8", attr_type="ip-dst")
        assert result == [{"id": "1"}]

    def test_search_attributes_with_limit(self):
        """Test searching attributes with custom limit"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": []}})

        result = client.search_attributes(limit=100)
        assert result == []

    def test_list_events(self):
        """Test listing events"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}, {"id": "2"}]})

        result = client.list_events()
        assert result == [{"id": "1"}, {"id": "2"}]

    def test_list_events_with_limit(self):
        """Test listing events with custom limit"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        result = client.list_events(limit=50)
        assert result == [{"id": "1"}]

    def test_get_attribute_count(self):
        """Test getting attribute count"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"count": 42})

        result = client.get_attribute_count()
        assert result == 42

    def test_get_attribute_count_fallback(self):
        """Test get_attribute_count falls back to len of attributes"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(side_effect=[{"response": {"Attribute": [{"id": "1"}]}}, {}])

        result = client.get_attribute_count()
        assert result == 1

    def test_get_attribute_count_exception(self):
        """Test get_attribute_count returns 0 on exception"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(side_effect=Exception("Error"))

        result = client.get_attribute_count()
        assert result == 0

    def test_health_check(self):
        """Test health check returns True when successful"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()
        assert result is True

    def test_health_check_exception(self):
        """Test health check returns False on exception"""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(side_effect=Exception("Error"))

        result = client.health_check()
        assert result is False
