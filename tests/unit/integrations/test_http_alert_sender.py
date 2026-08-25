#!/usr/bin/env python3
"""Unit tests for http_alert_sender.py."""

from unittest.mock import Mock, patch

from soar_lab.infrastructure.http_alert_sender import AlertSendResult, HTTPAlertSender


class TestAlertSendResult:
    """Test AlertSendResult."""

    def test_bool_true(self):
        """Test AlertSendResult evaluates to True when success is True."""
        result = AlertSendResult(success=True, status_code=200, alert_id="test")

        assert bool(result) == True

    def test_bool_false(self):
        """Test AlertSendResult evaluates to False when success is False."""
        result = AlertSendResult(success=False, status_code=500, alert_id="test")

        assert bool(result) == False

    def test_bool_missing_success(self):
        """Test AlertSendResult evaluates to False when success key is
        missing."""
        result = AlertSendResult(status_code=200, alert_id="test")

        assert bool(result) == False


class TestHTTPAlertSender:
    """Test HTTPAlertSender."""

    def test_initialization(self):
        """Test successful initialization."""
        sender = HTTPAlertSender(
            webhook_url="https://example.com/webhook", api_token="test-token", timeout=30
        )

        assert sender.webhook_url == "https://example.com/webhook"
        assert sender.api_token == "test-token"
        assert sender.timeout == 30
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 0

    def test_initialization_default_timeout(self):
        """Test initialization with default timeout."""
        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")

        assert sender.timeout == 30

    def test_headers_set(self):
        """Test that headers are set correctly."""
        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")

        assert "Authorization" in sender._session.headers
        assert sender._session.headers["Authorization"] == "Bearer test-token"
        assert "Content-Type" in sender._session.headers
        assert sender._session.headers["Content-Type"] == "application/json"

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_success_200(self, mock_session_class):
        """Test successful send with 200 status code."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 200
        assert result["alert_id"] == "alert-1"
        assert "trace_id" in result
        assert "trace_id" in alert  # trace_id injected into alert body
        assert sender.alerts_sent == 1
        assert sender.alerts_failed == 0
        # Verify post was called with the webhook URL and trace_id header
        call_kwargs = mock_session.post.call_args
        assert call_kwargs.args[0] == "https://example.com/webhook"
        assert call_kwargs.kwargs["timeout"] == 30
        assert "X-Request-ID" in call_kwargs.kwargs["headers"]
        assert call_kwargs.kwargs["headers"]["X-Request-ID"] == result["trace_id"]

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_success_202(self, mock_session_class):
        """Test successful send with 202 status code."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.text = "Accepted"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 202
        assert sender.alerts_sent == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_success_204(self, mock_session_class):
        """Test successful send with 204 status code."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["status_code"] == 204
        assert sender.alerts_sent == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_failure_500(self, mock_session_class):
        """Test failed send with 500 status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] == 500
        assert result["alert_id"] == "alert-1"
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_failure_400(self, mock_session_class):
        """Test failed send with 400 status code."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] == 400
        assert sender.alerts_failed == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_request_exception(self, mock_session_class):
        """Test send with request exception."""
        import requests

        mock_session = Mock()
        mock_session.post.side_effect = requests.RequestException("Connection error")
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] is None
        assert result["alert_id"] == "alert-1"
        assert "error" in result
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_generic_exception(self, mock_session_class):
        """Test send with generic exception (not RequestException)"""
        mock_session = Mock()
        mock_session.post.side_effect = ValueError("Unexpected error")
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"alert_id": "alert-1", "type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == False
        assert result["status_code"] is None
        assert result["alert_id"] == "alert-1"
        assert "error" in result
        assert sender.alerts_sent == 0
        assert sender.alerts_failed == 1

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_send_without_alert_id(self, mock_session_class):
        """Test send without alert_id in payload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        alert = {"type": "ransomware"}

        result = sender.send(alert)

        assert result["success"] == True
        assert result["alert_id"] == "unknown"

    def test_get_metrics(self):
        """Test getting metrics."""
        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")
        sender.alerts_sent = 5
        sender.alerts_failed = 2

        metrics = sender.get_metrics()

        assert metrics["alerts_sent"] == 5
        assert metrics["alerts_failed"] == 2
        assert metrics["total_alerts"] == 7

    def test_get_metrics_initial(self):
        """Test getting metrics with no alerts sent."""
        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")

        metrics = sender.get_metrics()

        assert metrics["alerts_sent"] == 0
        assert metrics["alerts_failed"] == 0
        assert metrics["total_alerts"] == 0

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_multiple_sends(self, mock_session_class):
        """Test multiple sends update counters correctly."""
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
            mock_response_success,
        ]
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="test-token")

        sender.send({"alert_id": "alert-1"})
        sender.send({"alert_id": "alert-2"})
        sender.send({"alert_id": "alert-3"})
        sender.send({"alert_id": "alert-4"})

        assert sender.alerts_sent == 3
        assert sender.alerts_failed == 1


class TestHTTPAlertSenderBatch:
    """Test HTTPAlertSender.send_batch with backpressure."""

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_batch_all_success(self, mock_session_class):
        """All alerts in a batch should be sent successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="t")
        alerts = [{"alert_id": f"alert-{i}"} for i in range(5)]
        results = sender.send_batch(alerts, workers=2)

        assert len(results) == 5
        assert all(r["success"] for r in results)
        assert sender.alerts_sent == 5

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_batch_backpressure_rejects(self, mock_session_class):
        """Alerts exceeding queue size should be rejected with 503."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="t")
        # Queue size 2, 10 alerts — 8 should be rejected
        alerts = [{"alert_id": f"alert-{i}"} for i in range(10)]
        results = sender.send_batch(alerts, max_queue_size=2, workers=1)

        rejected = [r for r in results if r.get("status_code") == 503]
        assert len(rejected) > 0, "Some alerts should be rejected by backpressure"
        assert all("queue full" in r.get("error", "") for r in rejected)

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_batch_preserves_order(self, mock_session_class):
        """Results should be returned in the same order as input alerts."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="t")
        alerts = [{"alert_id": f"alert-{i}"} for i in range(8)]
        results = sender.send_batch(alerts, workers=3)

        for i, r in enumerate(results):
            assert r["alert_id"] == f"alert-{i}"

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_batch_empty(self, mock_session_class):
        """Empty batch should return empty list."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="t")
        results = sender.send_batch([])
        assert results == []

    @patch("soar_lab.infrastructure.http_alert_sender.requests.Session")
    def test_batch_mixed_success_failure(self, mock_session_class):
        """Batch with mixed responses should report correctly."""
        ok = Mock()
        ok.status_code = 200
        ok.text = "OK"
        err = Mock()
        err.status_code = 500
        err.text = "Error"
        mock_session = Mock()
        mock_session.post.side_effect = [ok, err, ok]
        mock_session_class.return_value = mock_session

        sender = HTTPAlertSender(webhook_url="https://example.com/webhook", api_token="t")
        alerts = [{"alert_id": "a1"}, {"alert_id": "a2"}, {"alert_id": "a3"}]
        results = sender.send_batch(alerts, workers=1)

        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]
        assert len(successes) == 2
        assert len(failures) == 1
