#!/usr/bin/env python3
"""
Unit tests for shuffle_client.py
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from soar_lab.exceptions import IntegrationError
from soar_lab.integrations.shuffle_client import ShuffleClient


class TestShuffleClient:
    """Test ShuffleClient"""

    def test_initialization_with_base_url_and_api_key(self):
        """Test initialization with base_url and api_key"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")
            assert client._config_provider is None

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'shuffle_url': 'http://localhost:5001',
            'shuffle_api_key': 'test-key'
        }.get(key, default)

        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url=None, api_key=None, config_provider=mock_config)
            assert client._config_provider == mock_config

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError"""
        with pytest.raises(ValueError, match="shuffle_url must be provided"):
            ShuffleClient(base_url=None, api_key="test-key")

    def test_initialization_without_api_key_raises(self):
        """Test initialization without api_key raises ValueError"""
        with pytest.raises(ValueError, match="shuffle_api_key must be provided"):
            ShuffleClient(base_url="http://localhost:5001", api_key=None)

    def test_send_webhook_payload(self):
        """Test sending webhook payload"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_response = Mock()
            mock_response.content = b'{"result": "ok"}'
            mock_response.json.return_value = {"result": "ok"}
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session

            result = client.send_webhook_payload("http://localhost:5001/api/v1/hooks/test", {"data": "test"})
            assert result == {"result": "ok"}

    def test_send_webhook_payload_http_error(self):
        """Test send_webhook_payload raises IntegrationError on HTTPError"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        with patch('requests.Session') as mock_session_class:
            import requests
            mock_session = Mock()
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_session.post.return_value = mock_response
            mock_session_class.return_value = mock_session

            with pytest.raises(IntegrationError, match="ShuffleClient"):
                client.send_webhook_payload("http://localhost:5001/api/v1/hooks/test", {"data": "test"})

    def test_send_webhook_payload_request_exception(self):
        """Test send_webhook_payload raises IntegrationError on RequestException"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        with patch('requests.Session') as mock_session_class:
            import requests
            mock_session = Mock()
            mock_session.post.side_effect = requests.RequestException("Connection error")
            mock_session_class.return_value = mock_session

            with pytest.raises(IntegrationError, match="ShuffleClient"):
                client.send_webhook_payload("http://localhost:5001/api/v1/hooks/test", {"data": "test"})

    def test_send_webhook_with_token(self):
        """Test send_webhook with token"""
        mock_config = Mock()
        mock_config.get.return_value = ""

        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key", config_provider=mock_config)

        client.post = Mock(return_value={"result": "ok"})

        result = client.send_webhook("webhook-id", {"data": "test"}, token="custom-token")
        assert result == {"result": "ok"}
        client.post.assert_called_once()

    def test_send_webhook_with_config_provider_token(self):
        """Test send_webhook with config_provider token"""
        mock_config = Mock()
        mock_config.get.return_value = "config-token"

        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key", config_provider=mock_config)

        client.post = Mock(return_value={"result": "ok"})

        result = client.send_webhook("webhook-id", {"data": "test"})
        assert result == {"result": "ok"}

    def test_list_apps(self):
        """Test listing apps"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value=[{"name": "app1"}, {"name": "app2"}])

        result = client.list_apps()
        assert result == [{"name": "app1"}, {"name": "app2"}]

    def test_list_apps_returns_empty_on_invalid(self):
        """Test list_apps returns empty list on invalid response"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value={"error": "not a list"})

        result = client.list_apps()
        assert result == []

    def test_download_remote_apps(self):
        """Test downloading remote apps"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response = Mock()
        mock_response.ok = True
        client._session.post = Mock(return_value=mock_response)

        result = client.download_remote_apps("https://github.com/shuffle/python-apps")
        assert result is True

    def test_download_remote_apps_error(self):
        """Test download_remote_apps returns False on error"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client._session.post = Mock(side_effect=Exception("Error"))

        result = client.download_remote_apps("https://github.com/shuffle/python-apps")
        assert result is False

    def test_list_workflows(self):
        """Test listing workflows"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value=[{"id": "1"}, {"id": "2"}])

        result = client.list_workflows()
        assert result == [{"id": "1"}, {"id": "2"}]

    def test_list_workflows_returns_empty_on_invalid(self):
        """Test list_workflows returns empty list on invalid response"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value={"error": "not a list"})

        result = client.list_workflows()
        assert result == []

    def test_get_workflow(self):
        """Test getting a specific workflow"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value={"id": "123", "name": "test"})

        result = client.get_workflow("123")
        assert result == {"id": "123", "name": "test"}

    def _make_es_empty_response(self) -> Mock:
        """Return a mock that simulates an empty ES search response."""
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {"hits": {"hits": []}}
        resp.raise_for_status = Mock()
        return resp

    def test_get_workflow_executions(self):
        """Test getting workflow executions via API fallback when ES is empty"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'[{"execution_id": "1"}]'
        mock_response.json.return_value = [{"execution_id": "1"}]
        mock_response.request = Mock()
        mock_response.request.headers = {"Authorization": "Bearer test"}
        client._session.get = Mock(return_value=mock_response)

        with patch('requests.get', return_value=self._make_es_empty_response()):
            result = client.get_workflow_executions("123")
        assert result == [{"execution_id": "1"}]

    def test_get_workflow_executions_with_retry(self):
        """Test get_workflow_executions API fallback with retry on 401"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.raise_for_status = Mock(side_effect=requests.HTTPError("401"))
        mock_response_401.request = Mock()
        mock_response_401.request.headers = {"Authorization": "Bearer test"}
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.content = b'[{"execution_id": "1"}]'
        mock_response_200.json.return_value = [{"execution_id": "1"}]
        mock_response_200.request = Mock()
        mock_response_200.request.headers = {"Authorization": "Bearer test"}

        with patch('requests.get', return_value=self._make_es_empty_response()):
            client._session.get = Mock(side_effect=[mock_response_401, mock_response_200])
            result = client.get_workflow_executions("123", retries=1, retry_delay=0.1)

        assert result == [{"execution_id": "1"}]

    def test_get_workflow_executions_raises_on_persistent_401(self):
        """Test get_workflow_executions raises IntegrationError on persistent 401"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status = Mock(side_effect=requests.HTTPError("401"))
        mock_response.request = Mock()
        mock_response.request.headers = {"Authorization": "Bearer test"}

        with patch('requests.get', return_value=self._make_es_empty_response()):
            client._session.get = Mock(return_value=mock_response)
            with pytest.raises(IntegrationError, match="ShuffleClient"):
                client.get_workflow_executions("123", retries=0, retry_delay=0.1)

    def test_get_execution(self):
        """Test getting a specific execution"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get_workflow_executions = Mock(return_value=[
            {"execution_id": "1", "status": "completed"},
            {"execution_id": "2", "status": "running"}
        ])

        result = client.get_execution("workflow-123", "1")
        assert result == {"execution_id": "1", "status": "completed"}

    def test_get_execution_not_found(self):
        """Test get_execution returns None when execution not found"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get_workflow_executions = Mock(return_value=[
            {"execution_id": "1", "status": "completed"}
        ])

        result = client.get_execution("workflow-123", "999")
        assert result is None

    def test_login(self):
        """Test login"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response = Mock()
        mock_response.ok = True
        client._session.post = Mock(return_value=mock_response)

        result = client.login("admin", "password")
        assert result is True

    def test_login_error(self):
        """Test login returns False on error"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client._session.post = Mock(side_effect=Exception("Error"))

        result = client.login("admin", "password")
        assert result is False

    def test_delete_workflow(self):
        """Test deleting a workflow"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        mock_response = Mock()
        mock_response.ok = True
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_workflow("123")
        assert result is True

    def test_delete_workflow_error(self):
        """Test delete_workflow returns False on error"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client._session.delete = Mock(side_effect=Exception("Error"))

        result = client.delete_workflow("123")
        assert result is False

    def test_health_check(self):
        """Test health check"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()
        assert result is True

    def test_health_check_error(self):
        """Test health check returns False on error"""
        with patch('soar_lab.integrations.shuffle_client.threading.Thread'):
            client = ShuffleClient(base_url="http://localhost:5001", api_key="test-key")

        client.get = Mock(side_effect=Exception("Error"))

        result = client.health_check()
        assert result is False
