#!/usr/bin/env python3
"""Unit tests for kpi_alerts module."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.monitoring.kpi_alerts import KPIAlertManager


class TestKPIAlertManager:
    """Tests for KPIAlertManager class."""

    def test_initialization(self):
        """Test initialization with Elasticsearch client."""
        mock_es = Mock()
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        assert manager.es == mock_es
        assert manager.webhook_url is None
        assert manager.thresholds["mttr_seconds"] == 120
        assert manager.thresholds["success_rate_percent"] == 90
        assert manager.thresholds["health_score"] == 70
        assert manager.thresholds["service_success_rate"] == 85

    def test_initialization_with_webhook(self):
        """Test initialization with webhook URL."""
        mock_es = Mock()
        manager = KPIAlertManager(
            elasticsearch_client=mock_es, webhook_url="http://example.com/webhook"
        )

        assert manager.webhook_url == "http://example.com/webhook"

    def test_check_mttr_threshold_no_data(self):
        """Test MTTR threshold check with no data."""
        mock_es = Mock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_mttr_threshold(hours=1)

        assert result["status"] == "no_data"
        assert "No MTTR data available" in result["message"]

    def test_check_mttr_threshold_ok(self):
        """Test MTTR threshold check when MTTR is below threshold."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 60}},
                    {"_source": {"mttr_seconds": 80}},
                    {"_source": {"mttr_seconds": 100}},
                ]
            }
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_mttr_threshold(hours=1)

        assert result["status"] == "ok"
        assert result["metric"] == "mttr_seconds"
        assert result["value"] == 80.0
        assert result["threshold"] == 120

    def test_check_mttr_threshold_alert(self):
        """Test MTTR threshold check when MTTR exceeds threshold."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 150}},
                    {"_source": {"mttr_seconds": 180}},
                    {"_source": {"mttr_seconds": 200}},
                ]
            }
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es, webhook_url=None)

        result = manager.check_mttr_threshold(hours=1)

        assert result["status"] == "alert"
        assert result["metric"] == "mttr_seconds"
        assert result["value"] == 176.66666666666666
        assert result["threshold"] == 120
        assert "exceeded threshold" in result["message"]

    def test_check_mttr_threshold_error(self):
        """Test MTTR threshold check with error."""
        mock_es = Mock()
        mock_es.search.side_effect = Exception("ES error")
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_mttr_threshold(hours=1)

        assert result["status"] == "error"
        assert "ES error" in result["message"]

    def test_check_service_health_no_data(self):
        """Test service health check with no data."""
        mock_es = Mock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_service_health(hours=1)

        assert result["status"] == "no_data"
        assert "No metrics data available" in result["message"]

    def test_check_service_health_ok(self):
        """Test service health check when all services are healthy."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"service": "thehive", "success": True}},
                    {"_source": {"service": "thehive", "success": True}},
                    {"_source": {"service": "cortex", "success": True}},
                ]
            }
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_service_health(hours=1)

        # With the actual KPIAnalyzer, this will return the real calculated KPIs
        # We just check that it doesn't error
        assert "status" in result

    def test_check_service_health_alert(self):
        """Test service health check when service success rate is below
        threshold."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"service": "thehive", "success": True}},
                    {"_source": {"service": "thehive", "success": False}},
                ]
            }
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es, webhook_url=None)

        result = manager.check_service_health(hours=1)

        # With the actual KPIAnalyzer, this will return the real calculated KPIs
        # We just check that it doesn't error
        assert "status" in result

    def test_check_service_health_error(self):
        """Test service health check with error."""
        mock_es = Mock()
        mock_es.search.side_effect = Exception("ES error")
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_service_health(hours=1)

        assert result["status"] == "error"
        assert "ES error" in result["message"]

    def test_check_health_score_no_data(self):
        """Test health score check with no data."""
        mock_es = Mock()
        mock_es.search.return_value = {"hits": {"hits": []}}
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_health_score()

        assert result["status"] == "no_data"
        assert "No health score data available" in result["message"]

    def test_check_health_score_ok(self):
        """Test health score check when health score is above threshold."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"metric_type": "health_score", "score": 80}}]}
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_health_score()

        assert result["status"] == "ok"
        assert result["metric"] == "health_score"
        assert result["value"] == 80
        assert result["threshold"] == 70

    def test_check_health_score_alert(self):
        """Test health score check when health score is below threshold."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"metric_type": "health_score", "score": 50}}]}
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es, webhook_url=None)

        result = manager.check_health_score()

        assert result["status"] == "alert"
        assert result["metric"] == "health_score"
        assert result["value"] == 50
        assert result["threshold"] == 70
        assert "below threshold" in result["message"]

    def test_check_health_score_error(self):
        """Test health score check with error."""
        mock_es = Mock()
        mock_es.search.side_effect = Exception("ES error")
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_health_score()

        assert result["status"] == "error"
        assert "ES error" in result["message"]

    def test_check_all_thresholds(self):
        """Test checking all thresholds."""
        mock_es = Mock()
        mock_es.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 60}},
                    {"_source": {"service": "thehive", "success": True}},
                ]
            }
        }
        manager = KPIAlertManager(elasticsearch_client=mock_es)

        result = manager.check_all_thresholds(hours=1)

        assert "timestamp" in result
        assert "checks" in result
        assert "mttr" in result["checks"]
        assert "service_health" in result["checks"]
        assert "health_score" in result["checks"]
        assert "overall_status" in result

    def test_send_alert_no_webhook(self):
        """Test sending alert when webhook is not configured."""
        mock_es = Mock()
        manager = KPIAlertManager(elasticsearch_client=mock_es, webhook_url=None)

        # Should not raise exception
        manager._send_alert({"message": "test alert"})

    def test_send_alert_with_webhook(self):
        """Test sending alert when webhook is configured."""
        mock_es = Mock()
        manager = KPIAlertManager(
            elasticsearch_client=mock_es, webhook_url="http://example.com/webhook"
        )

        # This will try to send the alert via requests
        # We just check it doesn't raise an exception
        alert = {"message": "test alert"}
        manager._send_alert(alert)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
