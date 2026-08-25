"""SOAR Ransomware Lab - HTTP Alert Sender (Infrastructure).

Sends alert payloads to external SOAR tools via HTTP.
Responsibility: transport only (no payload generation, no validation logic).
"""

import queue
import threading
import uuid
from typing import Any

import requests

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    DEFAULT_WEBHOOK_TIMEOUT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_TRACE_ID,
)
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import AlertTransporter

logger = get_logger(__name__)

TRACE_ID_HEADER = HEADER_TRACE_ID
DEFAULT_BACKPRESSURE_QUEUE_SIZE = 100


class AlertSendResult(dict):
    """Dict subclass that evaluates as bool based on 'success' key."""

    def __bool__(self) -> bool:
        return bool(self.get("success", False))


class HTTPAlertSender(AlertTransporter):
    """Sends alert payloads to a webhook endpoint (Shuffle / generic)."""

    def __init__(
        self, webhook_url: str, api_token: str, timeout: int = DEFAULT_WEBHOOK_TIMEOUT
    ) -> None:
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.timeout = timeout
        self._session = requests.Session()
        self._session.verify = False
        headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
        if api_token:
            headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX} {api_token}"
        self._session.headers.update(headers)
        self.alerts_sent = 0
        self.alerts_failed = 0

    def send(self, alert: dict[str, Any]) -> dict[str, Any]:
        """Send a single alert to the webhook URL.

        A trace ID is generated (or reused from the alert payload) and sent
        both as an ``X-Request-ID`` header and embedded in the alert body
        under the ``trace_id`` key, enabling end-to-end correlation across
        the SOAR pipeline (webhook → API → Shuffle → TheHive → Cortex → ES).
        """
        alert_id = alert.get("alert_id", "unknown")
        # Reuse existing trace_id or generate a new one for this alert
        trace_id = alert.get("trace_id") or uuid.uuid4().hex
        alert["trace_id"] = trace_id
        try:
            logger.info(
                f"Sending alert {alert_id} to {self.webhook_url}",
                extra={"trace_id": trace_id},
            )
            response = self._session.post(
                self.webhook_url,
                json=alert,
                headers={TRACE_ID_HEADER: trace_id},
                timeout=self.timeout,
            )
            success = response.status_code in (200, 202, 204)
            if success:
                self.alerts_sent += 1
                logger.info(
                    f"Alert {alert_id} sent successfully (HTTP {response.status_code})",
                    extra={"trace_id": trace_id},
                )
            else:
                self.alerts_failed += 1
                logger.error(
                    f"Failed to send alert {alert_id}: "
                    f"HTTP {response.status_code} - {response.text[:200]}",
                    extra={"trace_id": trace_id},
                )
            return AlertSendResult(
                success=success,
                status_code=response.status_code,
                alert_id=alert_id,
                trace_id=trace_id,
            )
        except requests.RequestException as exc:
            self.alerts_failed += 1
            logger.error(
                f"Network error sending alert {alert_id}: {exc}",
                extra={"trace_id": trace_id},
            )
            return AlertSendResult(
                success=False,
                status_code=None,
                alert_id=alert_id,
                error=str(exc),
                trace_id=trace_id,
            )
        except Exception as exc:
            self.alerts_failed += 1
            logger.error(
                f"Unexpected error sending alert {alert_id}: {exc}",
                extra={"trace_id": trace_id},
            )
            return AlertSendResult(
                success=False,
                status_code=None,
                alert_id=alert_id,
                error=str(exc),
                trace_id=trace_id,
            )

    def get_metrics(self) -> dict[str, int]:
        return {
            "alerts_sent": self.alerts_sent,
            "alerts_failed": self.alerts_failed,
            "total_alerts": self.alerts_sent + self.alerts_failed,
        }

    def send_batch(
        self,
        alerts: list[dict[str, Any]],
        max_queue_size: int = DEFAULT_BACKPRESSURE_QUEUE_SIZE,
        workers: int = 3,
    ) -> list[dict[str, Any]]:
        """Send a batch of alerts with backpressure via a bounded queue.

        When the queue is full, additional alerts are rejected immediately
        with HTTP 503 semantics (``success=False``, ``error=queue full``)
        rather than overwhelming the downstream webhook.

        Args:
            alerts: List of alert payloads to send.
            max_queue_size: Maximum number of pending alerts in the queue.
            workers: Number of worker threads consuming the queue.

        Returns:
            list[dict]: One ``AlertSendResult`` per input alert, in order.
        """
        bounded: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=max_queue_size)
        results: dict[int, dict[str, Any]] = {}
        results_lock = threading.Lock()

        def _worker() -> None:
            while True:
                item = bounded.get()
                if item is None:
                    bounded.task_done()
                    break
                idx = item["__idx"]
                alert = item["alert"]
                result = self.send(alert)
                with results_lock:
                    results[idx] = result
                bounded.task_done()

        threads = [threading.Thread(target=_worker, daemon=True) for _ in range(workers)]
        for t in threads:
            t.start()

        for idx, alert in enumerate(alerts):
            try:
                bounded.put_nowait({"__idx": idx, "alert": alert})
            except queue.Full:
                with results_lock:
                    results[idx] = AlertSendResult(
                        success=False,
                        status_code=503,
                        alert_id=alert.get("alert_id", "unknown"),
                        error="backpressure queue full",
                    )

        # Signal workers to stop
        for _ in threads:
            bounded.put(None)
        for t in threads:
            t.join(timeout=30)

        return [
            results.get(i, {"success": False, "error": "worker timeout"})
            for i in range(len(alerts))
        ]
