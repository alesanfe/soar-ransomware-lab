#!/usr/bin/env python3
"""
Unit tests for integrations: CortexClient, TheHiveClient, ShuffleClient.
All HTTP calls are mocked via requests_mock / patch so no external services needed.
"""

import pytest
from unittest.mock import MagicMock, patch

from soar_lab.exceptions import IntegrationError
from soar_lab.integrations.cortex_client import CortexClient
from soar_lab.integrations.shuffle_client import ShuffleClient
from soar_lab.integrations.thehive_client import TheHiveClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data=None, status_code=200, content=b"{}"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content if content is not None else b""
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status.return_value = None
    return resp


def _http_error_response(status_code=404):
    import requests
    resp = MagicMock()
    resp.status_code = status_code
    http_err = requests.HTTPError(response=resp)
    resp.raise_for_status.side_effect = http_err
    return resp


# ===========================================================================
# CortexClient
# ===========================================================================

class TestCortexClientInit:
    def test_init_defaults(self):
        client = CortexClient(base_url="http://cortex:9001", api_key="cortexkey")
        assert "9001" in client.base_url or "localhost" in client.base_url

    def test_init_explicit_url_and_key(self):
        client = CortexClient(base_url="http://cortex:9001", api_key="mykey")
        assert client.base_url == "http://cortex:9001"

    def test_init_strips_trailing_slash(self):
        client = CortexClient(base_url="http://cortex:9001/", api_key="k")
        assert not client.base_url.endswith("/")


class TestCortexClientListAnalyzers:
    def test_list_analyzers_success(self, requests_mock):
        analyzers = [{"id": "a1", "name": "Abuse_Finder"}]
        requests_mock.get("http://cortex:9001/api/analyzer", json=analyzers)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        result = client.list_analyzers()
        assert result == analyzers

    def test_list_analyzers_non_list_response(self, requests_mock):
        requests_mock.get("http://cortex:9001/api/analyzer", json={"error": "oops"})
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        result = client.list_analyzers()
        assert result == []

    def test_list_analyzers_http_error(self, requests_mock):
        requests_mock.get("http://cortex:9001/api/analyzer", status_code=500)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        with pytest.raises(IntegrationError):
            client.list_analyzers()


class TestCortexClientRunAnalyzer:
    def test_run_analyzer_success(self, requests_mock):
        job = {"id": "job-1", "status": "Waiting"}
        requests_mock.post("http://cortex:9001/api/analyzer/run", json=job)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        result = client.run_analyzer("Abuse_Finder_3_0", "ip", "1.2.3.4")
        assert result == job

    def test_run_analyzer_sends_correct_payload(self, requests_mock):
        requests_mock.post("http://cortex:9001/api/analyzer/run", json={})
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        client.run_analyzer("Abuse_Finder_3_0", "domain", "evil.com")
        sent = requests_mock.last_request.json()
        assert sent["analyzerId"] == "Abuse_Finder_3_0"
        assert sent["dataType"] == "domain"
        assert sent["data"] == "evil.com"

    def test_run_analyzer_http_error(self, requests_mock):
        requests_mock.post("http://cortex:9001/api/analyzer/run", status_code=400)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        with pytest.raises(IntegrationError):
            client.run_analyzer("X", "ip", "1.2.3.4")


class TestCortexClientGetJob:
    def test_get_job_success(self, requests_mock):
        job = {"id": "job-1", "status": "Success"}
        requests_mock.get("http://cortex:9001/api/job/job-1", json=job)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        assert client.get_job("job-1") == job

    def test_get_job_report_success(self, requests_mock):
        report = {"id": "job-1", "report": {"summary": {}}}
        requests_mock.get("http://cortex:9001/api/job/job-1/report", json=report)
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        assert client.get_job_report("job-1") == report


class TestCortexClientHealthCheck:
    def test_health_check_true(self, requests_mock):
        requests_mock.get("http://cortex:9001/", json={})
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        assert client.health_check() is True

    def test_health_check_false_on_exception(self, requests_mock):
        requests_mock.get("http://cortex:9001/", exc=ConnectionError("refused"))
        client = CortexClient(base_url="http://cortex:9001", api_key="k")
        assert client.health_check() is False


# ===========================================================================
# TheHiveClient
# ===========================================================================

class TestTheHiveClientInit:
    def test_init_defaults(self):
        client = TheHiveClient(base_url="http://hive:9000", api_key="hivekey")
        assert "9000" in client.base_url or "localhost" in client.base_url

    def test_init_explicit(self):
        client = TheHiveClient(base_url="http://hive:9000", api_key="hivekey")
        assert client.base_url == "http://hive:9000"


class TestTheHiveClientCreateAlert:
    def test_create_alert_success(self, requests_mock):
        alert_resp = {"id": "alert-1", "status": "New"}
        requests_mock.post("http://hive:9000/api/alert", json=alert_resp)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        result = client.create_alert({"title": "Ransomware detected", "severity": 2})
        assert result == alert_resp

    def test_create_alert_sends_payload(self, requests_mock):
        requests_mock.post("http://hive:9000/api/alert", json={})
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        client.create_alert({"title": "Test", "severity": 3})
        sent = requests_mock.last_request.json()
        assert sent["title"] == "Test"
        assert sent["severity"] == 3

    def test_create_alert_http_error(self, requests_mock):
        requests_mock.post("http://hive:9000/api/alert", status_code=401)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        with pytest.raises(IntegrationError):
            client.create_alert({"title": "X"})


class TestTheHiveClientCreateCase:
    def test_create_case_success(self, requests_mock):
        case_resp = {"id": "case-1", "title": "SOAR Case"}
        requests_mock.post("http://hive:9000/api/case", json=case_resp)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        result = client.create_case({"title": "SOAR Case", "severity": 2})
        assert result == case_resp

    def test_create_case_http_error(self, requests_mock):
        requests_mock.post("http://hive:9000/api/case", status_code=500)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        with pytest.raises(IntegrationError):
            client.create_case({"title": "X"})


class TestTheHiveClientGetCase:
    def test_get_case_success(self, requests_mock):
        case = {"id": "case-1", "title": "My Case"}
        requests_mock.get("http://hive:9000/api/case/case-1", json=case)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        assert client.get_case("case-1") == case

    def test_get_case_not_found(self, requests_mock):
        requests_mock.get("http://hive:9000/api/case/missing", status_code=404)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        with pytest.raises(IntegrationError):
            client.get_case("missing")


class TestTheHiveClientAddObservable:
    def test_add_observable_success(self, requests_mock):
        obs_resp = {"id": "obs-1"}
        requests_mock.post("http://hive:9000/api/case/case-1/artifact", json=obs_resp)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        result = client.add_observable("case-1", {"dataType": "ip", "data": "1.2.3.4"})
        assert result == obs_resp

    def test_add_observable_http_error(self, requests_mock):
        requests_mock.post("http://hive:9000/api/case/case-1/artifact", status_code=422)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        with pytest.raises(IntegrationError):
            client.add_observable("case-1", {"dataType": "ip", "data": "1.2.3.4"})


class TestTheHiveClientListCases:
    def test_list_cases_success(self, requests_mock):
        cases = [{"id": "case-1"}, {"id": "case-2"}]
        requests_mock.get("http://hive:9000/api/case", json=cases)
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        result = client.list_cases()
        assert result == cases

    def test_list_cases_non_list(self, requests_mock):
        requests_mock.get("http://hive:9000/api/case", json={"error": "bad"})
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        assert client.list_cases() == []


class TestTheHiveClientHealthCheck:
    def test_health_check_true(self, requests_mock):
        requests_mock.get("http://hive:9000/api/health", json={"status": "ok"})
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        assert client.health_check() is True

    def test_health_check_false(self, requests_mock):
        requests_mock.get("http://hive:9000/api/health", exc=ConnectionError("down"))
        client = TheHiveClient(base_url="http://hive:9000", api_key="k")
        assert client.health_check() is False


# ===========================================================================
# ShuffleClient
# ===========================================================================

class TestShuffleClientInit:
    def test_init_defaults(self):
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="shufflekey")
        assert "5001" in client.base_url or "localhost" in client.base_url

    def test_init_explicit(self):
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="shufflekey")
        assert client.base_url == "http://shuffle:5001"


class TestShuffleClientSendWebhook:
    def test_send_webhook_success(self, requests_mock):
        wh_resp = {"id": "exec-1", "status": "EXECUTING"}
        requests_mock.post("http://shuffle:5001/api/v1/hooks/wh-abc", json=wh_resp)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        result = client.send_webhook("wh-abc", {"alert": "ransomware"}, token="test-token")
        assert result == wh_resp

    def test_send_webhook_with_explicit_token(self, requests_mock):
        requests_mock.post("http://shuffle:5001/api/v1/hooks/wh-abc", json={})
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        client.send_webhook("wh-abc", {"x": 1}, token="override-token")
        assert "override-token" in requests_mock.last_request.headers.get("Authorization", "")


    def test_send_webhook_http_error(self, requests_mock):
        requests_mock.post("http://shuffle:5001/api/v1/hooks/wh-abc", status_code=403)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        with pytest.raises(IntegrationError):
            client.send_webhook("wh-abc", {"x": 1})


class TestShuffleClientListWorkflows:
    def test_list_workflows_success(self, requests_mock):
        wfs = [{"id": "wf-1", "name": "SOAR Workflow"}]
        requests_mock.get("http://shuffle:5001/api/v1/workflows", json=wfs)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        assert client.list_workflows() == wfs

    def test_list_workflows_non_list(self, requests_mock):
        requests_mock.get("http://shuffle:5001/api/v1/workflows", json={"error": "x"})
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        assert client.list_workflows() == []

    def test_list_workflows_http_error(self, requests_mock):
        requests_mock.get("http://shuffle:5001/api/v1/workflows", status_code=500)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        with pytest.raises(IntegrationError):
            client.list_workflows()


class TestShuffleClientGetWorkflow:
    def test_get_workflow_success(self, requests_mock):
        wf = {"id": "wf-1", "name": "My Flow"}
        requests_mock.get("http://shuffle:5001/api/v1/workflows/wf-1", json=wf)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        assert client.get_workflow("wf-1") == wf

    def test_get_workflow_not_found(self, requests_mock):
        requests_mock.get("http://shuffle:5001/api/v1/workflows/missing", status_code=404)
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        with pytest.raises(IntegrationError):
            client.get_workflow("missing")


class TestShuffleClientHealthCheck:
    def test_health_check_true(self, requests_mock):
        requests_mock.get("http://shuffle:5001/api/v1/health", json={"status": "ok"})
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        assert client.health_check() is True

    def test_health_check_false(self, requests_mock):
        requests_mock.get("http://shuffle:5001/api/v1/health", exc=ConnectionError("down"))
        client = ShuffleClient(base_url="http://shuffle:5001", api_key="k")
        assert client.health_check() is False
