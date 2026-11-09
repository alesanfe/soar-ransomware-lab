#!/usr/bin/env python3
"""Unit tests for shuffle/shuffle_helpers.py."""

import threading
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import soar_lab.infrastructure.integrations.shuffle.shuffle_helpers as helpers
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.shuffle.shuffle_helpers import (
    api_lookup_execution,
    api_workflow_executions,
    do_login,
    es_lookup_execution,
    fetch_real_apikey,
    keepalive_loop,
    list_lookup_execution,
    load_password,
    match_execution,
    set_org_id_header,
    warm_cache,
)


class TestLoadPassword:
    """Test load_password function."""

    def test_load_password_from_env(self):
        """Test loading password from SHUFFLE_DEFAULT_PASSWORD env var."""
        with patch.dict("os.environ", {"SHUFFLE_DEFAULT_PASSWORD": "test-pass-123"}):
            result = load_password()
        assert result == "test-pass-123"

    def test_load_password_falls_back_to_secret_resolver(self):
        """Without env var, resolve_secret is consulted with the repo .env.full."""
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(helpers, "resolve_secret", return_value="secret-pw") as rs:
                with patch.object(helpers, "repo_root", return_value=Path("/repo")):
                    assert load_password() == "secret-pw"
        rs.assert_called_once()
        assert rs.call_args.args[0] == "SHUFFLE_DEFAULT_PASSWORD"

    def test_load_password_resolver_failure_returns_empty(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(helpers, "resolve_secret", side_effect=RuntimeError("boom")):
                assert load_password() == ""


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
    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers._es_session")
    def test_es_lookup_execution_found(self, mock_es_session, mock_get_es):
        """Test ES lookup when execution is found."""
        mock_get_es.return_value = ("http://es:9200", None, True)
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "hits": {"hits": [{"_source": {"execution_id": "exec1", "status": "COMPLETED"}}]}
        }
        mock_es_session.return_value.post.return_value = mock_resp

        result = es_lookup_execution(Mock(), "exec1", include_results=True)
        assert result is not None
        assert result["execution_id"] == "exec1"

    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.get_es_connection")
    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers._es_session")
    def test_es_lookup_execution_not_found(self, mock_es_session, mock_get_es):
        """Test ES lookup when execution is not found."""
        mock_get_es.return_value = ("http://es:9200", None, True)
        mock_resp = Mock()
        mock_resp.json.return_value = {"hits": {"hits": []}}
        mock_es_session.return_value.post.return_value = mock_resp

        result = es_lookup_execution(Mock(), "nonexistent", include_results=True)
        assert result is None

    @patch("soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers.get_es_connection")
    def test_es_lookup_execution_no_es_connection(self, mock_get_es):
        """Test ES lookup when ES connection fails."""
        mock_get_es.side_effect = Exception("No ES")
        result = es_lookup_execution(Mock(), "exec1", include_results=True)
        assert result is None


class TestDoLogin:
    """do_login posts through the client's pooled session (BL-HTTP-006)."""

    def test_login_success(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.post.return_value = Mock(status_code=200)
        env = {"SHUFFLE_DEFAULT_USERNAME": "admin", "SHUFFLE_DEFAULT_PASSWORD": "pw"}
        with patch.dict("os.environ", env):
            assert do_login(client) is True
        client._session.post.assert_called_once()

    def test_login_non_200_returns_false(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.post.return_value = Mock(status_code=401)
        env = {"SHUFFLE_DEFAULT_USERNAME": "admin", "SHUFFLE_DEFAULT_PASSWORD": "pw"}
        with patch.dict("os.environ", env):
            assert do_login(client) is False

    def test_login_without_credentials_returns_false(self):
        client = Mock()
        with patch.dict("os.environ", {}, clear=True):
            with patch.object(helpers, "load_password", return_value=""):
                assert do_login(client) is False
        client._session.post.assert_not_called()

    def test_login_network_error_returns_false(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.post.side_effect = requests.ConnectionError("down")
        env = {"SHUFFLE_DEFAULT_USERNAME": "admin", "SHUFFLE_DEFAULT_PASSWORD": "pw"}
        with patch.dict("os.environ", env):
            assert do_login(client) is False


class TestSetOrgIdHeader:
    def test_skips_when_header_already_set(self):
        client = Mock()
        client._session.headers = {"Org-Id": "org-1"}
        set_org_id_header(client)
        client._session.get.assert_not_called()

    @patch.object(helpers, "fetch_first_user_source")
    def test_sets_header_from_opensearch(self, mock_fetch):
        mock_fetch.return_value = {"active_org": {"id": "org-42"}}

        client = Mock()
        client._session.headers = {}
        set_org_id_header(client)
        assert client._session.headers["Org-Id"] == "org-42"

    @patch.object(helpers, "fetch_first_user_source")
    def test_es_failure_leaves_header_unset(self, mock_fetch):
        mock_fetch.return_value = None
        client = Mock()
        client._session.headers = {}
        set_org_id_header(client)
        assert "Org-Id" not in client._session.headers


class TestFetchRealApikey:
    @patch.object(helpers, "fetch_first_user_source")
    def test_returns_apikey_from_opensearch(self, mock_fetch):
        mock_fetch.return_value = {"apikey": "key-123"}
        assert fetch_real_apikey() == "key-123"

    @patch.object(helpers, "fetch_first_user_source")
    def test_empty_hits_returns_empty(self, mock_fetch):
        mock_fetch.return_value = {}
        assert fetch_real_apikey() == ""

    @patch.object(helpers, "fetch_first_user_source")
    def test_es_failure_returns_empty(self, mock_fetch):
        mock_fetch.return_value = None
        assert fetch_real_apikey() == ""


class TestWarmCache:
    def test_bearer_ok_skips_heal(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.headers = {"Org-Id": "org"}
        client._session.get.return_value = Mock(status_code=200)
        with patch.object(helpers, "fetch_real_apikey") as fetch:
            warm_cache(client)
        fetch.assert_not_called()

    def test_bearer_stale_heals_apikey(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.headers = {"Org-Id": "org", "Authorization": "Bearer old"}
        # First probe fails, confirm succeeds.
        client._session.get.side_effect = [
            Mock(status_code=401),
            Mock(status_code=200),
        ]
        with patch.object(helpers, "fetch_real_apikey", return_value="new-key"):
            with patch.object(helpers, "do_login", return_value=True):
                warm_cache(client)
        assert client._session.headers["Authorization"] == "Bearer new-key"

    def test_bearer_stale_without_real_key_keeps_header(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client._session.headers = {"Org-Id": "org", "Authorization": "Bearer old"}
        client._session.get.side_effect = [
            Mock(status_code=401),
            Mock(status_code=200),
        ]
        with patch.object(helpers, "fetch_real_apikey", return_value=""):
            with patch.object(helpers, "do_login", return_value=True):
                warm_cache(client)
        assert client._session.headers["Authorization"] == "Bearer old"


class TestKeepaliveLoop:
    def test_loop_pings_until_stop(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        stop = threading.Event()
        calls = []

        def _ping(*a, **kw):
            calls.append(1)
            if len(calls) >= 3:
                stop.set()
            return Mock(status_code=200)

        client._session.get.side_effect = _ping
        keepalive_loop(client, stop, interval=0)
        assert len(calls) == 3

    def test_request_failure_swallowed_and_continues(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        stop = threading.Event()
        calls = []

        def _ping(*a, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise requests.ConnectionError("blip")
            stop.set()
            return Mock(status_code=200)

        client._session.get.side_effect = _ping
        keepalive_loop(client, stop, interval=0)
        assert len(calls) == 2


class TestApiLookupExecutionEdges:
    def test_404_on_first_endpoint_falls_through_to_second(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        resp404 = Mock(status_code=404)
        resp_ok = Mock(status_code=200, content=b"{}")
        resp_ok.json.return_value = {"id": "exec1", "results": {"r": 1}}
        resp_ok.raise_for_status.return_value = None
        client._session.get.side_effect = [resp404, resp_ok]

        result = api_lookup_execution(client, "wf1", "exec1")
        assert result["id"] == "exec1"

    def test_http_error_on_endpoint_continues(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        resp_err = Mock(status_code=500)
        resp_err.raise_for_status.side_effect = requests.HTTPError("500")
        resp_ok = Mock(status_code=200, content=b"{}")
        resp_ok.json.return_value = {"id": "exec1", "results": {}}
        resp_ok.raise_for_status.return_value = None
        client._session.get.side_effect = [resp_err, resp_ok]

        result = api_lookup_execution(client, "wf1", "exec1")
        assert result["id"] == "exec1"

    def test_match_without_results_kept_as_candidate(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        resp = Mock(status_code=200, content=b"{}")
        resp.json.return_value = {"id": "exec1"}  # no "results" key
        resp.raise_for_status.return_value = None
        client._session.get.return_value = resp

        result = api_lookup_execution(client, "wf1", "exec1")
        assert result == {"id": "exec1"}

    def test_generic_exception_on_endpoint_continues(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        client._session.get.side_effect = [RuntimeError("boom"), RuntimeError("boom2")]

        assert api_lookup_execution(client, "wf1", "exec1") is None


class TestListLookupExecutionEdge:
    def test_list_endpoint_exception_returns_none(self):
        client = Mock()
        client.get_workflow_executions.side_effect = RuntimeError("down")
        assert list_lookup_execution(client, "wf1", "exec1") is None


class TestApiWorkflowExecutionsRetry:
    def test_exhausted_retries_raise_integration_error(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        client._session.get.side_effect = requests.ConnectionError("down")

        with patch.object(helpers.time, "sleep"):
            import pytest

            with pytest.raises(IntegrationError):
                api_workflow_executions(client, "wf1", retries=2, retry_delay=0.01)
        assert client._session.get.call_count == 3

    def test_retry_eventually_succeeds(self):
        client = Mock()
        client._url.side_effect = lambda p: f"http://s{p}"
        client.timeout = 10
        resp_ok = Mock(status_code=200, content=b"[]")
        resp_ok.json.return_value = [{"id": "e1"}]
        resp_ok.raise_for_status.return_value = None
        client._session.get.side_effect = [
            requests.ConnectionError("blip"),
            resp_ok,
        ]
        with patch.object(helpers.time, "sleep"):
            out = api_workflow_executions(client, "wf1", retries=1, retry_delay=0.01)
        assert out == [{"id": "e1"}]


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


class TestApiWorkflowExecutions:
    """Regression for BUG-028: f-string without braces sent the literal
    constant NAME 'DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT' as the limit."""

    def test_limit_param_is_numeric(self):
        import re

        from soar_lab.infrastructure.integrations.shuffle.shuffle_helpers import (
            api_workflow_executions,
        )

        mock_client = Mock()
        captured = []
        mock_client._url.side_effect = lambda p: captured.append(p) or f"http://s{p}"
        mock_client.timeout = 10
        resp = Mock()
        resp.content = b"[]"
        resp.json.return_value = []
        resp.raise_for_status = Mock()
        mock_client._session.get.return_value = resp

        api_workflow_executions(mock_client, "wf1", retries=0, retry_delay=0)
        assert captured, "no request was made"
        assert re.search(r"limit=\d+", captured[0]), f"limit param is not numeric: {captured[0]}"
