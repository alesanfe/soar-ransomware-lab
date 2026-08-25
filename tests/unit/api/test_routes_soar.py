#!/usr/bin/env python3
"""Unit tests for interfaces/api/routes_soar.py.

Tests the SOAR integration endpoints by registering them on a minimal
FastAPI app with mocked clients in app.state.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.routes_soar import register_soar_routes


@pytest.fixture()
def app_with_soar():
    """Create a minimal FastAPI app with SOAR routes and mocked clients."""
    app = FastAPI()
    app.state.thehive_client = Mock()
    app.state.cortex_client = Mock()
    app.state.misp_client = Mock()
    app.state.shuffle_client = Mock()
    app.state.elasticsearch_client = Mock()
    register_soar_routes(app)
    return app


@pytest.fixture()
def client(app_with_soar):
    """TestClient for the SOAR routes app."""
    return TestClient(app_with_soar)


class TestSoarStatusEndpoint:
    """Test the /soar/status endpoint."""

    def test_soar_status_all_healthy(self, client, app_with_soar):
        """Test /soar/status when all clients are healthy."""
        app_with_soar.state.thehive_client.health_check.return_value = True
        app_with_soar.state.cortex_client.health_check.return_value = True
        app_with_soar.state.misp_client.health_check.return_value = True
        app_with_soar.state.shuffle_client.health_check.return_value = True
        app_with_soar.state.elasticsearch_client.health_check.return_value = True

        resp = client.get("/soar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "thehive" in data
        assert "cortex" in data
        assert "misp" in data
        assert "shuffle" in data
        assert "elasticsearch" in data


class TestTheHiveEndpoints:
    """Test TheHive SOAR endpoints."""

    def test_thehive_cases(self, client, app_with_soar):
        """Test GET /soar/thehive/cases."""
        app_with_soar.state.thehive_client.search_cases.return_value = [
            {"id": "case1", "title": "Test Case"}
        ]
        resp = client.get("/soar/thehive/cases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["cases"][0]["id"] == "case1"

    def test_thehive_case_by_id(self, client, app_with_soar):
        """Test GET /soar/thehive/cases/{case_id}."""
        app_with_soar.state.thehive_client.get_case.return_value = {"id": "123", "title": "Case"}
        resp = client.get("/soar/thehive/cases/123")
        assert resp.status_code == 200
        assert resp.json()["id"] == "123"

    def test_thehive_observables(self, client, app_with_soar):
        """Test GET /soar/thehive/cases/{case_id}/observables."""
        app_with_soar.state.thehive_client.get_case_observables.return_value = []
        resp = client.get("/soar/thehive/cases/123/observables")
        assert resp.status_code == 200

    def test_thehive_tasks(self, client, app_with_soar):
        """Test GET /soar/thehive/cases/{case_id}/tasks."""
        app_with_soar.state.thehive_client.list_case_tasks.return_value = []
        resp = client.get("/soar/thehive/cases/123/tasks")
        assert resp.status_code == 200

    def test_thehive_health(self, client, app_with_soar):
        """Test GET /soar/thehive/health."""
        app_with_soar.state.thehive_client.health_check.return_value = True
        resp = client.get("/soar/thehive/health")
        assert resp.status_code == 200


class TestCortexEndpoints:
    """Test Cortex SOAR endpoints."""

    def test_cortex_analyzers(self, client, app_with_soar):
        """Test GET /soar/cortex/analyzers."""
        app_with_soar.state.cortex_client.list_analyzers.return_value = []
        resp = client.get("/soar/cortex/analyzers")
        assert resp.status_code == 200

    def test_cortex_jobs(self, client, app_with_soar):
        """Test GET /soar/cortex/jobs."""
        app_with_soar.state.cortex_client.list_jobs.return_value = []
        resp = client.get("/soar/cortex/jobs")
        assert resp.status_code == 200

    def test_cortex_job_by_id(self, client, app_with_soar):
        """Test GET /soar/cortex/jobs/{job_id}."""
        app_with_soar.state.cortex_client.get_job.return_value = {"id": "job1"}
        resp = client.get("/soar/cortex/jobs/job1")
        assert resp.status_code == 200

    def test_cortex_job_report(self, client, app_with_soar):
        """Test GET /soar/cortex/jobs/{job_id}/report."""
        app_with_soar.state.cortex_client.get_job_report.return_value = {"report": "data"}
        resp = client.get("/soar/cortex/jobs/job1/report")
        assert resp.status_code == 200

    def test_cortex_health(self, client, app_with_soar):
        """Test GET /soar/cortex/health."""
        app_with_soar.state.cortex_client.health_check.return_value = True
        resp = client.get("/soar/cortex/health")
        assert resp.status_code == 200


class TestMispEndpoints:
    """Test MISP SOAR endpoints."""

    def test_misp_attributes(self, client, app_with_soar):
        """Test GET /soar/misp/attributes."""
        app_with_soar.state.misp_client.search_attributes.return_value = []
        resp = client.get("/soar/misp/attributes")
        assert resp.status_code == 200

    def test_misp_events(self, client, app_with_soar):
        """Test GET /soar/misp/events."""
        app_with_soar.state.misp_client.list_events.return_value = []
        resp = client.get("/soar/misp/events")
        assert resp.status_code == 200

    def test_misp_event_by_id(self, client, app_with_soar):
        """Test GET /soar/misp/events/{event_id}."""
        app_with_soar.state.misp_client.get_event.return_value = {"id": "evt1"}
        resp = client.get("/soar/misp/events/evt1")
        assert resp.status_code == 200

    def test_misp_health(self, client, app_with_soar):
        """Test GET /soar/misp/health."""
        app_with_soar.state.misp_client.health_check.return_value = True
        resp = client.get("/soar/misp/health")
        assert resp.status_code == 200


class TestShuffleEndpoints:
    """Test Shuffle SOAR endpoints."""

    def test_shuffle_workflows(self, client, app_with_soar):
        """Test GET /soar/shuffle/workflows."""
        app_with_soar.state.shuffle_client.list_workflows.return_value = []
        resp = client.get("/soar/shuffle/workflows")
        assert resp.status_code == 200

    def test_shuffle_workflow_by_id(self, client, app_with_soar):
        """Test GET /soar/shuffle/workflows/{workflow_id}."""
        app_with_soar.state.shuffle_client.get_workflow.return_value = {"id": "wf1"}
        resp = client.get("/soar/shuffle/workflows/wf1")
        assert resp.status_code == 200

    def test_shuffle_executions(self, client, app_with_soar):
        """Test GET /soar/shuffle/workflows/{workflow_id}/executions."""
        app_with_soar.state.shuffle_client.get_workflow_executions.return_value = []
        resp = client.get("/soar/shuffle/workflows/wf1/executions")
        assert resp.status_code == 200

    def test_shuffle_execution_by_id(self, client, app_with_soar):
        """Test GET
        /soar/shuffle/workflows/{workflow_id}/executions/{execution_id}."""
        app_with_soar.state.shuffle_client.get_execution.return_value = {"id": "exec1"}
        resp = client.get("/soar/shuffle/workflows/wf1/executions/exec1")
        assert resp.status_code == 200

    def test_shuffle_health(self, client, app_with_soar):
        """Test GET /soar/shuffle/health."""
        app_with_soar.state.shuffle_client.health_check.return_value = True
        resp = client.get("/soar/shuffle/health")
        assert resp.status_code == 200


class TestElasticsearchEndpoints:
    """Test Elasticsearch SOAR endpoints."""

    def test_es_count(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/count."""
        app_with_soar.state.elasticsearch_client.index = "soar-alerts"
        app_with_soar.state.elasticsearch_client.count.return_value = 42
        resp = client.get("/soar/elasticsearch/count")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 42

    def test_es_latest(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/latest."""
        app_with_soar.state.elasticsearch_client.get_latest_documents.return_value = [
            {"id": "1", "type": "alert"}
        ]
        resp = client.get("/soar/elasticsearch/latest")
        assert resp.status_code == 200

    def test_es_health(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/health."""
        app_with_soar.state.elasticsearch_client.cluster_health.return_value = {"status": "green"}
        resp = client.get("/soar/elasticsearch/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reachable"] is True


class TestSoarClientNotAvailable:
    """Test 503 responses when clients are not available."""

    def test_thehive_not_available(self):
        """Test 503 when TheHive client is None."""
        app = FastAPI()
        app.state.thehive_client = None
        app.state.cortex_client = Mock()
        app.state.misp_client = Mock()
        app.state.shuffle_client = Mock()
        app.state.elasticsearch_client = Mock()
        register_soar_routes(app)
        c = TestClient(app)
        resp = c.get("/soar/thehive/cases")
        assert resp.status_code == 503

    def test_cortex_not_available(self):
        """Test 503 when Cortex client is None."""
        app = FastAPI()
        app.state.thehive_client = Mock()
        app.state.cortex_client = None
        app.state.misp_client = Mock()
        app.state.shuffle_client = Mock()
        app.state.elasticsearch_client = Mock()
        register_soar_routes(app)
        c = TestClient(app)
        resp = c.get("/soar/cortex/analyzers")
        assert resp.status_code == 503

    def test_misp_not_available(self):
        """Test 503 when MISP client is None."""
        app = FastAPI()
        app.state.thehive_client = Mock()
        app.state.cortex_client = Mock()
        app.state.misp_client = None
        app.state.shuffle_client = Mock()
        app.state.elasticsearch_client = Mock()
        register_soar_routes(app)
        c = TestClient(app)
        resp = c.get("/soar/misp/attributes")
        assert resp.status_code == 503

    def test_shuffle_not_available(self):
        """Test 503 when Shuffle client is None."""
        app = FastAPI()
        app.state.thehive_client = Mock()
        app.state.cortex_client = Mock()
        app.state.misp_client = Mock()
        app.state.shuffle_client = None
        app.state.elasticsearch_client = Mock()
        register_soar_routes(app)
        c = TestClient(app)
        resp = c.get("/soar/shuffle/workflows")
        assert resp.status_code == 503

    def test_elasticsearch_not_available(self):
        """Test 503 when Elasticsearch client is None."""
        app = FastAPI()
        app.state.thehive_client = Mock()
        app.state.cortex_client = Mock()
        app.state.misp_client = Mock()
        app.state.shuffle_client = Mock()
        app.state.elasticsearch_client = None
        register_soar_routes(app)
        c = TestClient(app)
        resp = c.get("/soar/elasticsearch/count")
        assert resp.status_code == 503


class TestSoarErrorPaths:
    """Test 502 responses when clients raise exceptions."""

    def test_thehive_list_cases_502_on_error(self, client, app_with_soar):
        """Test 502 when TheHive search_cases raises."""
        app_with_soar.state.thehive_client.search_cases.side_effect = RuntimeError("conn refused")
        resp = client.get("/soar/thehive/cases")
        assert resp.status_code == 502
        assert "TheHive error" in resp.json()["detail"]

    def test_thehive_get_case_502_on_error(self, client, app_with_soar):
        """Test 502 when TheHive get_case raises."""
        app_with_soar.state.thehive_client.get_case.side_effect = RuntimeError("not found")
        resp = client.get("/soar/thehive/cases/123")
        assert resp.status_code == 502

    def test_thehive_observables_502_on_error(self, client, app_with_soar):
        """Test 502 when TheHive get_case_observables raises."""
        app_with_soar.state.thehive_client.get_case_observables.side_effect = RuntimeError("err")
        resp = client.get("/soar/thehive/cases/123/observables")
        assert resp.status_code == 502

    def test_thehive_tasks_502_on_error(self, client, app_with_soar):
        """Test 502 when TheHive list_case_tasks raises."""
        app_with_soar.state.thehive_client.list_case_tasks.side_effect = RuntimeError("err")
        resp = client.get("/soar/thehive/cases/123/tasks")
        assert resp.status_code == 502

    def test_cortex_analyzers_502_on_error(self, client, app_with_soar):
        """Test 502 when Cortex list_analyzers raises."""
        app_with_soar.state.cortex_client.list_analyzers.side_effect = RuntimeError("err")
        resp = client.get("/soar/cortex/analyzers")
        assert resp.status_code == 502

    def test_cortex_analyzers_with_data_type_filter(self, client, app_with_soar):
        """Test GET /soar/cortex/analyzers?data_type=ip uses filtered
        method."""
        app_with_soar.state.cortex_client.list_analyzers_by_type.return_value = [
            {"name": "analyzer1"}
        ]
        resp = client.get("/soar/cortex/analyzers?data_type=ip")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        app_with_soar.state.cortex_client.list_analyzers_by_type.assert_called_once_with("ip")
        app_with_soar.state.cortex_client.list_analyzers.assert_not_called()

    def test_cortex_jobs_502_on_error(self, client, app_with_soar):
        """Test 502 when Cortex list_jobs raises."""
        app_with_soar.state.cortex_client.list_jobs.side_effect = RuntimeError("err")
        resp = client.get("/soar/cortex/jobs")
        assert resp.status_code == 502

    def test_cortex_job_502_on_error(self, client, app_with_soar):
        """Test 502 when Cortex get_job raises."""
        app_with_soar.state.cortex_client.get_job.side_effect = RuntimeError("err")
        resp = client.get("/soar/cortex/jobs/job1")
        assert resp.status_code == 502

    def test_cortex_job_report_502_on_error(self, client, app_with_soar):
        """Test 502 when Cortex get_job_report raises."""
        app_with_soar.state.cortex_client.get_job_report.side_effect = RuntimeError("err")
        resp = client.get("/soar/cortex/jobs/job1/report")
        assert resp.status_code == 502

    def test_misp_attributes_502_on_error(self, client, app_with_soar):
        """Test 502 when MISP search_attributes raises."""
        app_with_soar.state.misp_client.search_attributes.side_effect = RuntimeError("err")
        resp = client.get("/soar/misp/attributes")
        assert resp.status_code == 502

    def test_misp_events_502_on_error(self, client, app_with_soar):
        """Test 502 when MISP list_events raises."""
        app_with_soar.state.misp_client.list_events.side_effect = RuntimeError("err")
        resp = client.get("/soar/misp/events")
        assert resp.status_code == 502

    def test_misp_event_502_on_error(self, client, app_with_soar):
        """Test 502 when MISP get_event raises."""
        app_with_soar.state.misp_client.get_event.side_effect = RuntimeError("err")
        resp = client.get("/soar/misp/events/evt1")
        assert resp.status_code == 502

    def test_shuffle_workflows_502_on_error(self, client, app_with_soar):
        """Test 502 when Shuffle list_workflows raises."""
        app_with_soar.state.shuffle_client.list_workflows.side_effect = RuntimeError("err")
        resp = client.get("/soar/shuffle/workflows")
        assert resp.status_code == 502

    def test_shuffle_workflow_502_on_error(self, client, app_with_soar):
        """Test 502 when Shuffle get_workflow raises."""
        app_with_soar.state.shuffle_client.get_workflow.side_effect = RuntimeError("err")
        resp = client.get("/soar/shuffle/workflows/wf1")
        assert resp.status_code == 502

    def test_shuffle_executions_502_on_error(self, client, app_with_soar):
        """Test 502 when Shuffle get_workflow_executions raises."""
        app_with_soar.state.shuffle_client.get_workflow_executions.side_effect = RuntimeError("err")
        resp = client.get("/soar/shuffle/workflows/wf1/executions")
        assert resp.status_code == 502

    def test_shuffle_execution_not_found_returns_404(self, client, app_with_soar):
        """Test 404 when Shuffle get_execution returns None."""
        app_with_soar.state.shuffle_client.get_execution.return_value = None
        resp = client.get("/soar/shuffle/workflows/wf1/executions/missing")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Execution not found"

    def test_shuffle_execution_502_on_error(self, client, app_with_soar):
        """Test 502 when Shuffle get_execution raises (non-HTTPException)."""
        app_with_soar.state.shuffle_client.get_execution.side_effect = RuntimeError("err")
        resp = client.get("/soar/shuffle/workflows/wf1/executions/exec1")
        assert resp.status_code == 502

    def test_es_count_502_on_error(self, client, app_with_soar):
        """Test 502 when Elasticsearch count raises."""
        app_with_soar.state.elasticsearch_client.count.side_effect = RuntimeError("err")
        app_with_soar.state.elasticsearch_client.index = "soar-alerts"
        resp = client.get("/soar/elasticsearch/count")
        assert resp.status_code == 502

    def test_es_latest_502_on_error(self, client, app_with_soar):
        """Test 502 when Elasticsearch get_latest_documents raises."""
        app_with_soar.state.elasticsearch_client.get_latest_documents.side_effect = RuntimeError(
            "err"
        )
        resp = client.get("/soar/elasticsearch/latest")
        assert resp.status_code == 502

    def test_es_health_unreachable_returns_reachable_false(self, client, app_with_soar):
        """Test ES health returns reachable=False when cluster_health
        raises."""
        app_with_soar.state.elasticsearch_client.cluster_health.side_effect = RuntimeError(
            "conn refused"
        )
        resp = client.get("/soar/elasticsearch/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reachable"] is False
        assert "conn refused" in data["error"]


class TestSoarStatusEdgeCases:
    """Test edge cases for the /soar/status endpoint."""

    def test_status_with_unhealthy_client(self, client, app_with_soar):
        """Test /soar/status when one client is unhealthy."""
        app_with_soar.state.thehive_client.health_check.return_value = True
        app_with_soar.state.cortex_client.health_check.return_value = False
        app_with_soar.state.misp_client.health_check.return_value = True
        app_with_soar.state.shuffle_client.health_check.return_value = True
        app_with_soar.state.elasticsearch_client.health_check.return_value = True

        resp = client.get("/soar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cortex"]["reachable"] is False
        assert data["all_reachable"] is False

    def test_status_with_client_exception(self, client, app_with_soar):
        """Test /soar/status when a client health_check raises."""
        app_with_soar.state.thehive_client.health_check.side_effect = RuntimeError("timeout")
        app_with_soar.state.cortex_client.health_check.return_value = True
        app_with_soar.state.misp_client.health_check.return_value = True
        app_with_soar.state.shuffle_client.health_check.return_value = True
        app_with_soar.state.elasticsearch_client.health_check.return_value = True

        resp = client.get("/soar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thehive"]["reachable"] is False
        assert "timeout" in data["thehive"]["error"]
        assert data["all_reachable"] is False

    def test_status_with_none_client(self):
        """Test /soar/status when a client is None (not configured)."""
        app = FastAPI()
        app.state.thehive_client = None
        app.state.cortex_client = Mock()
        app.state.misp_client = Mock()
        app.state.shuffle_client = Mock()
        app.state.elasticsearch_client = Mock()
        for c in (
            app.state.cortex_client,
            app.state.misp_client,
            app.state.shuffle_client,
            app.state.elasticsearch_client,
        ):
            c.health_check.return_value = True
        register_soar_routes(app)
        c = TestClient(app)

        resp = c.get("/soar/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thehive"]["reachable"] is False
        assert "not configured" in data["thehive"]["error"]
        assert data["all_reachable"] is False


class TestElasticsearchQueryParameters:
    """Test query parameter handling for Elasticsearch endpoints."""

    def test_es_count_with_custom_index(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/count?index=custom-index."""
        app_with_soar.state.elasticsearch_client.index = "soar-alerts"
        app_with_soar.state.elasticsearch_client.count.return_value = 10
        resp = client.get("/soar/elasticsearch/count?index=custom-index")
        assert resp.status_code == 200
        data = resp.json()
        assert data["index"] == "custom-index"
        assert data["count"] == 10

    def test_es_count_default_index(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/count uses client.index when no index
        param."""
        app_with_soar.state.elasticsearch_client.index = "soar-alerts"
        app_with_soar.state.elasticsearch_client.count.return_value = 5
        resp = client.get("/soar/elasticsearch/count")
        assert resp.status_code == 200
        data = resp.json()
        assert data["index"] == "soar-alerts"

    def test_es_latest_with_size_and_index(self, client, app_with_soar):
        """Test GET /soar/elasticsearch/latest?size=5&index=custom."""
        app_with_soar.state.elasticsearch_client.get_latest_documents.return_value = []
        resp = client.get("/soar/elasticsearch/latest?size=5&index=custom-idx")
        assert resp.status_code == 200
        app_with_soar.state.elasticsearch_client.get_latest_documents.assert_called_once_with(
            size=5, index="custom-idx"
        )


class TestCortexQueryParameters:
    """Test query parameter handling for Cortex endpoints."""

    def test_cortex_jobs_with_start_and_count(self, client, app_with_soar):
        """Test GET /soar/cortex/jobs?start=10&count=5."""
        app_with_soar.state.cortex_client.list_jobs.return_value = [{"id": "j1"}]
        resp = client.get("/soar/cortex/jobs?start=10&count=5")
        assert resp.status_code == 200
        app_with_soar.state.cortex_client.list_jobs.assert_called_once_with(start=10, count=5)


class TestMispQueryParameters:
    """Test query parameter handling for MISP endpoints."""

    def test_misp_attributes_with_value_and_type(self, client, app_with_soar):
        """Test GET /soar/misp/attributes?value=1.2.3.4&attr_type=ip."""
        app_with_soar.state.misp_client.search_attributes.return_value = [{"id": "a1"}]
        resp = client.get("/soar/misp/attributes?value=1.2.3.4&attr_type=ip&limit=10")
        assert resp.status_code == 200
        app_with_soar.state.misp_client.search_attributes.assert_called_once_with(
            value="1.2.3.4", attr_type="ip", limit=10
        )

    def test_misp_events_with_limit(self, client, app_with_soar):
        """Test GET /soar/misp/events?limit=5."""
        app_with_soar.state.misp_client.list_events.return_value = []
        resp = client.get("/soar/misp/events?limit=5")
        assert resp.status_code == 200
        app_with_soar.state.misp_client.list_events.assert_called_once_with(limit=5)
