"""SOAR Ransomware Lab - HTTP Alert Sender (Infrastructure)
Sends alert payloads to external SOAR tools via HTTP.
Responsibility: transport only (no payload generation, no validation logic).
"""

import requests
from typing import Any, Dict

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import AlertTransporter

logger = get_logger(__name__)


class AlertSendResult(dict):
    """Dict subclass that evaluates as bool based on 'success' key."""

    def __bool__(self) -> bool:
        return bool(self.get("success", False))


class HTTPAlertSender(AlertTransporter):
    """Sends alert payloads to a webhook endpoint (Shuffle / generic)."""

    def __init__(self, webhook_url: str, api_token: str, timeout: int = 30) -> None:
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.timeout = timeout
        self._session = requests.Session()
        self._session.verify = False
        headers = {"Content-Type": "application/json"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        self._session.headers.update(headers)
        self.alerts_sent = 0
        self.alerts_failed = 0

    def send(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Send a single alert to the webhook URL."""
        alert_id = alert.get("alert_id", "unknown")
        try:
            logger.info(f"Sending alert {alert_id} to {self.webhook_url}")
            response = self._session.post(
                self.webhook_url,
                json=alert,
                timeout=self.timeout,
            )
            success = response.status_code in (200, 202, 204)
            if success:
                self.alerts_sent += 1
                logger.info(f"Alert {alert_id} sent successfully (HTTP {response.status_code})")
            else:
                self.alerts_failed += 1
                logger.error(
                    f"Failed to send alert {alert_id}: "
                    f"HTTP {response.status_code} - {response.text[:200]}"
                )
            return AlertSendResult(
                success=success,
                status_code=response.status_code,
                alert_id=alert_id,
            )
        except requests.RequestException as exc:
            self.alerts_failed += 1
            logger.error(f"Network error sending alert {alert_id}: {exc}")
            return AlertSendResult(success=False, status_code=None, alert_id=alert_id, error=str(exc))
        except Exception as exc:
            self.alerts_failed += 1
            logger.error(f"Unexpected error sending alert {alert_id}: {exc}")
            return AlertSendResult(success=False, status_code=None, alert_id=alert_id, error=str(exc))

    def get_metrics(self) -> Dict[str, int]:
        return {
            "alerts_sent": self.alerts_sent,
            "alerts_failed": self.alerts_failed,
            "total_alerts": self.alerts_sent + self.alerts_failed,
        }
