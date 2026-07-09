#!/usr/bin/env python3
"""
Unit tests for http_alert_sender.py
"""

import pytest
from unittest.mock import Mock, patch

from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender, AlertSendResult


class TestAlertSendResult:
    """Test AlertSendResult"""

    def test_bool_true(self):
        """Test AlertSendResult evaluates to True when success is True"""
        result = AlertSendResult(success=True, status_code=200, alert_id="test")

        assert bool(result) == True

    def test_bool_false(self):
        """Test AlertSendResult evaluates to False when success is False"""
        result = AlertSendResult(success=False, status_code=500, alert_id="test")

        assert bool(result) == False

    def test_bool_missing_success(self):
        """Test AlertSendResult evaluates to False when success key is missing"""
        result = AlertSendResult(status_code=200, alert_id="test")

        assert bool(result) == False


class TestHTTPAlertSender:
    """Test HTTPAlertSender"""

    def test_initialization(self):
        """Test successful initialization"""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token",
            timeout=30
        )

        assert sender.webhook_url == "https://example.com/webhook"
        assert sender.api_token == "test-token"
        assert sender.timeout == 30
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 0

    def test_initialization_default_timeout(self):
        """Test initialization with default timeout"""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )

        assert sender.timeout == 30

    def test_headers_set(self):
        """Test that headers are set correctly"""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )

        assert "Authorization" in sender._session.headers
        assert sender._session.headers["Authorization"] == "Bearer test-token"
        assert "Content-Type" in sender._session.headers
        assert sender._session.headers["Content-Type"] == "application/json"

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_success_200(self, mock_session_class):
        """Test successful send with 200 status code"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 200
        assert result["alert_id"] == "alert-1"
        assert sender.alerts_sent == 1
        assert sender.alerts_failed == 0
        mock_session.post.assert_called_once_with(
            "https://example.com/webhook",
            json=alert,
            timeout=30
        )

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_success_202(self, mock_session_class):
        """Test successful send with 202 status code"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = "Accepted"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 202
        assert sender.alerts_sent == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_success_204(self, mock_session_class):
        """Test successful send with 204 status code"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 204
        assert sender.alerts_sent == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_failure_500(self, mock_session_class):
        """Test failed send with 500 status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] == 500
        assert result["alert_id"] == "alert-1"
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_failure_400(self, mock_session_class):
        """Test failed send with 400 status code"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] == 400
        assert sender.alerts_failed == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_request_exception(self, mock_session_class):
        """Test send with request exception"""
        import requests
        mock_session = Mock()
        mock_session.post.side_effect = requests.RequestException("Connection error")
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] is None
        assert result["alert_id"] == "alert-1"
        assert "error" in result
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_generic_exception(self, mock_session_class):
        """Test send with generic exception (not RequestException)"""
        mock_session = Mock()
        mock_session.post.side_effect = ValueError("Unexpected error")
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] is None
        assert result["alert_id"] == "alert-1"
        assert "error" in result
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_send_without_alert_id(self, mock_session_class):
        """Test send without alert_id in payload"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        alert = {"type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["alert_id"] == "unknown"

    def test_get_metrics(self):
        """Test getting metrics"""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )
        sender.alerts_sent = 5
        sender.alerts_failed = 2

        metrics = sender.get_metrics()

        assert metrics["alerts_sent"] == 5
        assert metrics["alerts_failed"] == 2
        assert metrics["total_alerts"] == 7

    def test_get_metrics_initial(self):
        """Test getting metrics with no alerts sent"""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )

        metrics = sender.get_metrics()

        assert metrics["alerts_sent"] == 0
        assert metrics["alerts_failed"] == 0
        assert metrics["total_alerts"] == 0

    @patch('soar_lab.infrastructure.http_alert_sender.requests.Session')
    def test_multiple_sends(self, mock_session_class):
        """Test multiple sends update counters correctly"""
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.text = "OK"

        mock_response_failure = Mock()
        mock_response_failure.status_code = 500
        mock_response_failure.text = "Error"

        mock_session = Mock()
        mock_session.post.side_effect = [
            mock_response_success,
            mock_response_success,
            mock_response_failure,
            mock_response_success
        ]
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook",
            api_token="test-token"
        )

        sender.send({"alert_id": "alert-1"})
        sender.send({"alert_id": "alert-2"})
        sender.send({"alert_id": "alert-3"})
        sender.send({"alert_id": "alert-4"})

        assert sender.alerts_sent == 3
        assert sender.alerts_failed == 1
