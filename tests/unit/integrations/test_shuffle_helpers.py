#!/usr/bin/env python3
"""Unit tests for shuffle/shuffle_helpers.py."""

from unittest.mock import Mock, patch

from soar_lab.infrastructure.integrations.shuffle.shuffle_helpers import (
    api_lookup_execution,
    es_lookup_execution,
    list_lookup_execution,
    load_password,
    match_execution,
)


class TestLoadPassword:
    """Test load_password function."""

    def test_load_password_from_env(self):
        """Test loading password from SHUFFLE_DEFAULT_PASSWORD env var."""
        with patch.dict("os.environ", {"SHUFFLE_DEFAULT_PASSWORD": "test-pass-123"}):
            result = load_password()
        assert result == "test-pass-123"


class TestMatchExecution:
    """Test match_execution function."""

    def test_match_execution_by_id(self):
        """Test matching execution by 'id' field."""
        data = {"id": "exec1", "status": "COMPLETED"}
        result = match_execution(data, "exec1")
        assert result is not None
        assert result["id"] == "exec1"
        assert result["status"] == "COMPLETED"

    def test_match_execution_by_execution_id(self):
        """Test matching execution by 'execution_id' field."""
        data = {"execution_id": "exec2", "status": "RUNNING"}
        result = match_execution(data, "exec2")
        assert result is not None
        assert result["execution_id"] == "exec2"

    def test_match_execution_not_found(self):
        """Test when execution ID does not match."""
        data = {"id": "other"}
        result = match_execution(data, "exec1")
        assert result is None

    def test_match_execution_nested_data(self):
        """Test matching when execution is nested under 'data' key."""
        data = {"data": {"id": "exec1", "results": {"key": "val"}}}
        result = match_execution(data, "exec1")
        assert result is not None
        assert result["id"] == "exec1"
        assert result["results"]["key"] == "val"

    def test_match_execution_non_dict(self):
        """Test that non-dict input returns None."""
        result = match_execution("not a dict", "exec1")  # type: ignore[arg-type]
        assert result is None

    def test_match_execution_empty_dict(self):
        """Test with empty dict."""
        result = match_execution({}, "exec1")
        assert result is None


class TestEsLookupExecution:
    """Test es_lookup_execution function."""

    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.get_es_connection")
    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.requests")
    def test_es_lookup_execution_found(self, mock_requests, mock_get_es):
        """Test ES lookup when execution is found."""
        mock_get_es.return_value = ("http://es:9200", None, True)
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "hits": {"hits": [{"_source": {"execution_id": "exec1", "status": "COMPLETED"}}]}
        }
        mock_requests.get.return_value = mock_resp

        result = es_lookup_execution(Mock(), "exec1", include_results=True)
        assert result is not None
        assert result["execution_id"] == "exec1"

    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.get_es_connection")
    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.requests")
    def test_es_lookup_execution_not_found(self, mock_requests, mock_get_es):
        """Test ES lookup when execution is not found."""
        mock_get_es.return_value = ("http://es:9200", None, True)
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_requests.get.return_value = mock_resp

        result = es_lookup_execution(Mock(), "nonexistent", include_results=True)
        assert result is None

    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.get_es_connection")
    def test_es_lookup_execution_no_es_connection(self, mock_get_es):
        """Test ES lookup when ES connection fails."""
        mock_get_es.side_effect = Exception("No ES")
        result = es_lookup_execution(Mock(), "exec1", include_results=True)
        assert result is None


class TestApiLookupExecution:
    """Test api_lookup_execution function."""

    def test_api_lookup_execution_found(self):
        """Test API lookup when execution is found via direct endpoint."""
        mock_client = Mock()
        mock_client._url.side_effect = lambda p: f"http://shuffle:3001{p}"
        mock_client.timeout = 10
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"id": "exec1", "status": "COMPLETED"}'
        mock_resp.json.return_value = {"id": "exec1", "status": "COMPLETED"}
        mock_resp.raise_for_status.return_value = None
        mock_client._session.get.return_value = mock_resp

        result = api_lookup_execution(mock_client, "wf1", "exec1")
        assert result is not None
        assert result["id"] == "exec1"

    def test_api_lookup_execution_not_found(self):
        """Test API lookup when execution returns 404."""
        mock_client = Mock()
        mock_client._url.side_effect = lambda p: f"http://shuffle:3001{p}"
        mock_client.timeout = 10
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_client._session.get.return_value = mock_resp

        result = api_lookup_execution(mock_client, "wf1", "nonexistent")
        assert result is None


class TestListLookupExecution:
    """Test list_lookup_execution function."""

    def test_list_lookup_execution_found(self):
        """Test list lookup when execution is found in workflow executions."""
        mock_client = Mock()
        mock_client.get_workflow_executions.return_value = [{"id": "exec1", "status": "COMPLETED"}]

        result = list_lookup_execution(mock_client, "wf1", "exec1")
        assert result is not None
        assert result["id"] == "exec1"

    def test_list_lookup_execution_not_found(self):
        """Test list lookup when execution is not in list."""
        mock_client = Mock()
        mock_client.get_workflow_executions.return_value = [{"id": "other"}]

        result = list_lookup_execution(mock_client, "wf1", "exec1")
        assert result is None
