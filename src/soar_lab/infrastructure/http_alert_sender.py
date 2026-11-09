"""SOAR Ransomware Lab - HTTP Alert Sender (Infrastructure).

Sends alert payloads to external SOAR tools via HTTP.
Responsibility: transport only (no payload generation, no validation logic).
"""

import queue
import threading
import time
from typing import Any, TypedDict

import requests

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    DEFAULT_WEBHOOK_TIMEOUT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_TRACE_ID,
)
from soar_lab.common.trace_context import new_trace_id
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import AlertTransporter

logger = get_logger(__name__)

TRACE_ID_HEADER = HEADER_TRACE_ID
DEFAULT_BACKPRESSURE_QUEUE_SIZE = 100


class AlertSendResult(TypedDict, total=False):
    """Result of a single alert send — a plain serializable dict.

    Callers must check the ``success`` field explicitly; truthiness of the
    dict itself carries no meaning.
    """

    success: bool
    status_code: int | None
    alert_id: str
    error: str
    trace_id: str


class HTTPAlertSender(AlertTransporter):
    """Sends alert payloads to a webhook endpoint (Shuffle / generic)."""

    def __init__(
        self,
        webhook_url: str,
        api_token: str,
        timeout: int = DEFAULT_WEBHOOK_TIMEOUT,
        verify_tls: bool = True,
    ) -> None:
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.timeout = timeout
        self._session = requests.Session()
        self._session.verify = verify_tls
        if not verify_tls:
            logger.warning(
                "TLS verification DISABLED for alert sender — insecure, "
                "intended only for local development profiles"
            )
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
        trace_id = alert.get("trace_id") or new_trace_id()
        alert["trace_id"] = trace_id
        try:
            # GRAF-D8: the Shuffle webhook returns intermittent 500s
            # (upstream bug). Alerts are idempotent (dedup by alert_id
            # downstream), so a short bounded retry on transient failures
            # is safe and removes the lost-alert gap without masking real
            # 4xx rejections.
            response = None
            attempts = 3
            for attempt in range(attempts):
                try:
                    response = self._session.post(
                        self.webhook_url,
                        json=alert,
                        headers={TRACE_ID_HEADER: trace_id},
                        timeout=self.timeout,
                    )
                except requests.RequestException:
                    response = None
                if response is not None and response.status_code < 500 and response.status_code != 429:
                    break
                if attempt < attempts - 1:
                    logger.warning(
                        f"Transient failure sending alert {alert_id} "
                        f"(attempt {attempt + 1}/{attempts}), retrying",
                        extra={"trace_id": trace_id},
                    )
                    time.sleep(1.5 * (attempt + 1))
            if response is None:
                self.alerts_failed += 1
                return AlertSendResult(
                    success=False,
                    status_code=None,
                    alert_id=alert_id,
                    error="network error after retries",
                    trace_id=trace_id,
                )
            logger.info(
                f"Sending alert {alert_id} to {self.webhook_url}",
                extra={"trace_id": trace_id},
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
            logger.exception(
                f"Network error sending alert {alert_id}",
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
            logger.exception(
                f"Unexpected error sending alert {alert_id}",
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
        batch_timeout: float = 120.0,
    ) -> list[dict[str, Any]]:
        """Send a batch of alerts with backpressure via a bounded queue.

        When the queue is full, additional alerts are rejected immediately
        with HTTP 503 semantics (``success=False``, ``error=queue full``)
        rather than overwhelming the downstream webhook.

        The batch runs against an absolute deadline (``batch_timeout``).
        Workers check a cooperative-cancellation event between items; once
        the deadline is exceeded no further sends are started, and pending
        alerts are reported with a distinct ``batch deadline exceeded``
        result (HTTP 504 semantics) — never a silent success or a worker
        that keeps sending in the background after the caller has already
        been told it failed.

        Args:
            alerts: List of alert payloads to send.
            max_queue_size: Maximum number of pending alerts in the queue.
            workers: Number of worker threads consuming the queue.
            batch_timeout: Absolute budget in seconds for the whole batch.

        Returns:
            list[dict]: One ``AlertSendResult`` per input alert, in order.
        """
        if max_queue_size < 1 or workers < 1 or batch_timeout <= 0:
            raise ValueError("max_queue_size, workers and batch_timeout must be positive")
        bounded: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=max_queue_size)
        results: dict[int, dict[str, Any]] = {}
        results_lock = threading.Lock()
        cancelled = threading.Event()
        deadline = time.monotonic() + batch_timeout

        threads = [
            threading.Thread(
                target=self._batch_worker,
                args=(bounded, results, results_lock, cancelled),
                daemon=True,
            )
            for _ in range(workers)
        ]
        for t in threads:
            t.start()

        self._produce_batch(alerts, bounded, results, results_lock, cancelled, deadline)
        self._join_batch(threads, bounded, cancelled, deadline)

        return [results.get(i, self._batch_deadline_result()) for i in range(len(alerts))]

    @staticmethod
    def _batch_deadline_result() -> dict[str, Any]:
        return {"success": False, "status_code": 504, "error": "batch deadline exceeded"}

    def _batch_worker(
        self,
        bounded: queue.Queue[dict[str, Any] | None],
        results: dict[int, dict[str, Any]],
        results_lock: threading.Lock,
        cancelled: threading.Event,
    ) -> None:
        while True:
            item = bounded.get()
            if item is None or cancelled.is_set():
                bounded.task_done()
                if item is not None:
                    with results_lock:
                        results[item["__idx"]] = self._batch_deadline_result()
                if item is None:
                    break
                continue
            idx = item["__idx"]
            result = self.send(item["alert"])
            with results_lock:
                results[idx] = result
            bounded.task_done()

    def _produce_batch(
        self,
        alerts: list[dict[str, Any]],
        bounded: queue.Queue[dict[str, Any] | None],
        results: dict[int, dict[str, Any]],
        results_lock: threading.Lock,
        cancelled: threading.Event,
        deadline: float,
    ) -> None:
        for idx, alert in enumerate(alerts):
            if cancelled.is_set() or time.monotonic() >= deadline:
                with results_lock:
                    results[idx] = self._batch_deadline_result()
                continue
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

    def _join_batch(
        self,
        threads: list[threading.Thread],
        bounded: queue.Queue[dict[str, Any] | None],
        cancelled: threading.Event,
        deadline: float,
    ) -> None:
        # Signal workers to stop after queued items drain.
        for _ in threads:
            try:
                bounded.put_nowait(None)
            except queue.Full:
                # Queue is full; workers will see sentinels once drained.
                bounded.put(None)

        # Join within the remaining budget, then cancel cooperatively.
        for t in threads:
            remaining = deadline - time.monotonic()
            t.join(timeout=max(0.0, remaining))
        if any(t.is_alive() for t in threads):
            cancelled.set()
            for t in threads:
                t.join(timeout=self.timeout + 1 if isinstance(self.timeout, int) else 5)
