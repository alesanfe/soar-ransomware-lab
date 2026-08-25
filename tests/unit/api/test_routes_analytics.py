#!/usr/bin/env python3
"""Unit tests for interfaces/api/routes_analytics.py.

Tests the analytics, KPI, and node-timing endpoints by registering them
on a minimal FastAPI app with mocked dependencies in app.state.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.routes_analytics import register_analytics_routes

__all__ = [
    "TestMetricsEndpoint",
    "TestKpisEndpoint",
    "TestAggregatedKpisEndpoint",
    "TestNodeTimingsEndpoint",
]


@pytest.fixture()
def analytics_app():
    """Create a minimal FastAPI app with analytics routes and mocked deps."""
    app = FastAPI()

    # Mock system metrics
    app.state.system_metrics = Mock()

    # Mock analytics service
    mock_analytics = Mock()
    mock_analytics.get_comprehensive_kpis.return_value = {"mttr": 120.5, "total": 10}

    # Dependency function for analytics service
    def get_analytics_service():
        return mock_analytics

    register_analytics_routes(app, get_analytics_service)
    return app, mock_analytics


@pytest.fixture()
def client(analytics_app):
    """TestClient for the analytics routes app."""
    app, _ = analytics_app
    return TestClient(app)


class TestMetricsEndpoint:
    """Test the /analytics/metrics endpoint."""

    def test_metrics_with_system_metrics(self, client, analytics_app):
        """Test /analytics/metrics returns real metrics when system_metrics is available."""
        app, _ = analytics_app
        app.state.system_metrics.get_hardware_metrics.return_value = {
            "cpu": {"percent": 45.5},
            "memory": {"percent": 60.2},
            "disk": {"percent": 75.8},
        }

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu"] == 45.5
        assert data["memory"] == 60.2
        assert data["disk"] == 75.8

    def test_metrics_without_system_metrics(self, client, analytics_app):
        """Test /analytics/metrics returns mock values when system_metrics is None."""
        app, _ = analytics_app
        app.state.system_metrics = None

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200
        data = resp.json()
        # Mock values from route_helpers
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data

    def test_metrics_exception_returns_500(self, client, analytics_app):
        """Test /analytics/metrics returns 500 when system_metrics raises."""
        app, _ = analytics_app
        app.state.system_metrics.get_hardware_metrics.side_effect = RuntimeError("sensor error")

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 500


class TestKpisEndpoint:
    """Test the /analytics/kpis endpoint."""

    def test_get_kpis_success(self, client, analytics_app):
        """Test /analytics/kpis returns KPI data successfully."""
        app, mock_analytics = analytics_app
        mock_analytics.get_comprehensive_kpis.return_value = {"mttr": 100, "total": 5}

        resp = client.get("/analytics/kpis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mttr"] == 100
        assert data["total"] == 5

    def test_get_kpis_with_log_file_path(self, client, analytics_app):
        """Test /analytics/kpis with log_file_path query parameter."""
        app, mock_analytics = analytics_app
        mock_analytics.get_comprehensive_kpis.return_value = {"mttr": 50}

        resp = client.get("/analytics/kpis?log_file_path=/tmp/notify.log")
        assert resp.status_code == 200
        mock_analytics.get_comprehensive_kpis.assert_called_with("/tmp/notify.log")

    def test_get_kpis_exception_returns_500(self, client, analytics_app):
        """Test /analytics/kpis returns 500 when analytics service raises."""
        app, mock_analytics = analytics_app
        mock_analytics.get_comprehensive_kpis.side_effect = RuntimeError("compute error")

        resp = client.get("/analytics/kpis")
        assert resp.status_code == 500


class TestAggregatedKpisEndpoint:
    """Test the /analytics/kpis/aggregated endpoint."""

    def test_aggregated_kpis_success(self, client):
        """Test /analytics/kpis/aggregated returns data successfully."""
        mock_use_case = Mock()
        mock_use_case.execute.return_value = {
            "period_hours": 24,
            "total_alerts": 10,
            "mttr_statistics": {"mean": 120},
        }

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_aggregated_kpis_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/kpis/aggregated")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_alerts"] == 10

    def test_aggregated_kpis_with_hours_param(self, client):
        """Test /analytics/kpis/aggregated with custom hours parameter."""
        mock_use_case = Mock()
        mock_use_case.execute.return_value = {"period_hours": 48, "total_alerts": 20}

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_aggregated_kpis_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/kpis/aggregated?hours=48")
            assert resp.status_code == 200
            mock_use_case.execute.assert_called_with(hours=48)

    def test_aggregated_kpis_exception_returns_500(self, client):
        """Test /analytics/kpis/aggregated returns 500 when use case raises."""
        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_aggregated_kpis_use_case",
            side_effect=RuntimeError("ES connection failed"),
        ):
            resp = client.get("/analytics/kpis/aggregated")
            assert resp.status_code == 500


class TestNodeTimingsEndpoint:
    """Test the /analytics/node-timings endpoint."""

    def test_node_timings_aggregated(self, client):
        """Test /analytics/node-timings returns aggregated timings."""
        mock_use_case = Mock()
        mock_use_case.get_aggregated.return_value = {"nodes": [{"name": "node1", "avg_time": 5.0}]}

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_node_timings_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/node-timings")
            assert resp.status_code == 200
            data = resp.json()
            assert "nodes" in data

    def test_node_timings_with_execution_id(self, client):
        """Test /analytics/node-timings with execution_id returns specific timings."""
        mock_use_case = Mock()
        mock_use_case.get_execution.return_value = {
            "execution_id": "exec-1",
            "timings": [{"node": "node1", "time": 3.0}],
        }

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_node_timings_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/node-timings?execution_id=exec-1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["execution_id"] == "exec-1"

    def test_node_timings_execution_not_found(self, client):
        """Test /analytics/node-timings returns 404 when execution not found."""
        mock_use_case = Mock()
        mock_use_case.get_execution.return_value = None

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_node_timings_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/node-timings?execution_id=missing")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Execution not found"

    def test_node_timings_exception_returns_500(self, client):
        """Test /analytics/node-timings returns 500 when use case raises."""
        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_node_timings_use_case",
            side_effect=RuntimeError("connection error"),
        ):
            resp = client.get("/analytics/node-timings")
            assert resp.status_code == 500

    def test_node_timings_with_alert_id(self, client):
        """Test /analytics/node-timings with both execution_id and alert_id."""
        mock_use_case = Mock()
        mock_use_case.get_execution.return_value = {"execution_id": "exec-2"}

        with patch(
            "soar_lab.interfaces.api.routes_analytics.create_node_timings_use_case",
            return_value=mock_use_case,
        ):
            resp = client.get("/analytics/node-timings?execution_id=exec-2&alert_id=alert-1")
            assert resp.status_code == 200
            mock_use_case.get_execution.assert_called_with("exec-2", "alert-1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
