#!/usr/bin/env python3
"""
Unit tests for wazuh_client.py
"""

import pytest
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.external.integrations.wazuh_client import WazuhClient
from unittest.mock import Mock, patch


class TestWazuhClient:
    """Test WazuhClient"""

    def test_initialization_with_credentials(self):
        """Test initialization with username and password"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        assert client._username == "wazuh-wui"
        assert client._password == "password"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'wazuh_url': 'http://localhost:55000',
            'wazuh_user': 'wazuh-wui',
            'wazuh_password': 'password'
        }.get(key, default)

        client = WazuhClient(base_url=None, username=None, password=None, config_provider=mock_config)
        assert client._username == "wazuh-wui"
        assert client._password == "password"

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError"""
        with pytest.raises(ValueError, match="wazuh_url must be provided"):
            WazuhClient(base_url=None, username="wazuh-wui", password="password")

    def test_initialization_without_credentials_raises(self):
        """Test initialization without credentials raises ValueError"""
        with pytest.raises(ValueError, match="wazuh username and password must be provided"):
            WazuhClient(base_url="http://localhost:55000", username=None, password=None)

    def test_basic_auth_header(self):
        """Test basic auth header generation"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        header = client._basic_auth_header()
        assert header
        assert isinstance(header, str)

    def test_get_token_cached(self):
        """Test get_token returns cached token if valid"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._token = "cached-token"
        client._token_ts = 0  # Old timestamp, but token exists

        with patch('time.time', return_value=100):
            client._token_ts = 95  # 5 seconds ago (within TTL)
            token = client._get_token()
            assert token == "cached-token"

    def test_get_token_refreshes(self):
        """Test get_token refreshes token when expired"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._token = "old-token"
        client._token_ts = 0

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"token": "new-token"}}
        client._session.get = Mock(return_value=mock_response)

        with patch('time.time', return_value=1000):
            client._token_ts = 0  # Expired
            token = client._get_token()
            assert token == "new-token"
            assert client._token == "new-token"

    def test_get_token_auth_failure(self):
        """Test get_token raises IntegrationError on auth failure"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        client._session.get = Mock(return_value=mock_response)

        with pytest.raises(IntegrationError, match="Authentication failed"):
            client._get_token()

    def test_get_token_empty_token(self):
        """Test get_token raises IntegrationError on empty token"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")

        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": {"token": ""}}
        client._session.get = Mock(return_value=mock_response)

        with pytest.raises(IntegrationError, match="Empty JWT token"):
            client._get_token()

    def test_request_with_401_retry(self):
        """Test _request retries on 401"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")

        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.content = b'{"data": "ok"}'
        mock_response_200.json.return_value = {"data": "ok"}
        client._session.request = Mock(side_effect=[mock_response_401, mock_response_200])

        result = client._request("GET", "/test")
        assert result == {"data": "ok"}

    def test_request_http_error(self):
        """Test _request raises IntegrationError on HTTPError"""
        import requests
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        client._session.request = Mock(return_value=mock_response)

        with pytest.raises(IntegrationError, match="WazuhClient"):
            client._request("GET", "/test")

    def test_request_request_exception(self):
        """Test _request raises IntegrationError on RequestException"""
        import requests
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")

        client._get_token = Mock()  # Mock _get_token to avoid it failing
        client._session.request = Mock(side_effect=requests.RequestException("Connection error"))

        with pytest.raises(IntegrationError, match="WazuhClient"):
            client._request("GET", "/test")

    def test_list_agents(self):
        """Test listing agents"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"id": "001"}, {"id": "002"}]}})

        result = client.list_agents()
        assert result == [{"id": "001"}, {"id": "002"}]

    def test_list_agents_with_status(self):
        """Test listing agents with status filter"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"id": "001"}]}})

        result = client.list_agents(status="active")
        assert result == [{"id": "001"}]

    def test_list_agents_with_select(self):
        """Test listing agents with select fields"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"id": "001"}]}})

        result = client.list_agents(select="name,id")
        assert result == [{"id": "001"}]

    def test_get_agent(self):
        """Test getting a specific agent"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"id": "001", "name": "agent1"}]}})

        result = client.get_agent("001")
        assert result == {"id": "001", "name": "agent1"}

    def test_get_agent_not_found(self):
        """Test get_agent returns empty dict when not found"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": []}})

        result = client.get_agent("999")
        assert result == {}

    def test_get_manager_info(self):
        """Test getting manager info"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"version": "4.5.0"}]}})

        result = client.get_manager_info()
        assert result == {"version": "4.5.0"}

    def test_get_manager_info_empty(self):
        """Test get_manager_info returns empty dict when no items"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": []}})

        result = client.get_manager_info()
        assert result == {}

    def test_get_manager_status(self):
        """Test getting manager status"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"status": "active"}})

        result = client.get_manager_status()
        assert result == {"data": {"status": "active"}}

    def test_list_agent_vulnerabilities(self):
        """Test listing agent vulnerabilities"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": {"affected_items": [{"cve": "CVE-2021-1234"}]}})

        result = client.list_agent_vulnerabilities("001")
        assert result == [{"cve": "CVE-2021-1234"}]

    def test_run_active_response(self):
        """Test running active response"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": "ok"})

        result = client.run_active_response("isolate-host", "001", ["arg1", "arg2"])
        assert result == {"data": "ok"}

    def test_run_active_response_without_arguments(self):
        """Test running active response without arguments"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._request = Mock(return_value={"data": "ok"})

        result = client.run_active_response("isolate-host", "001")
        assert result == {"data": "ok"}

    def test_health_check(self):
        """Test health check returns True when successful"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._get_token = Mock()
        client.get_manager_info = Mock(return_value={"version": "4.5.0"})

        result = client.health_check()
        assert result is True

    def test_health_check_no_version(self):
        """Test health check returns False when no version"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._get_token = Mock()
        client.get_manager_info = Mock(return_value={})

        result = client.health_check()
        assert result is False

    def test_health_check_exception(self):
        """Test health check returns False on exception"""
        client = WazuhClient(base_url="http://localhost:55000", username="wazuh-wui", password="password")
        client._get_token = Mock(side_effect=Exception("Error"))

        result = client.health_check()
        assert result is False
