#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Shuffle Client
Dedicated client for Shuffle SOAR orchestration.
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class ShuffleClient(BaseHTTPClient):
    """Client for Shuffle API."""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            config_provider: Optional[object] = None,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('shuffle_url')
            key = api_key or config_provider.get('shuffle_api_key')
            self._config_provider = config_provider
        else:
            url = base_url
            key = api_key
            self._config_provider = None

        # Validate required parameters
        if not url:
            raise ValueError("shuffle_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("shuffle_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key)

    def send_webhook(
            self,
            webhook_id: str,
            payload: Dict[str, Any],
            token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an alert payload to a Shuffle webhook.

        Args:
            webhook_id: Webhook identifier from Shuffle workflow.
            payload: Alert / event data to forward.
            token: Optional bearer token override (uses config from constructor if None).

        Returns:
            Shuffle API response.
        """
        if token is not None:
            effective_token = token
        elif self._config_provider:
            effective_token = self._config_provider.get('siem_webhook_token', "")
        else:
            effective_token = ""
        headers = {}
        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"

        logger.info(f"Sending webhook {webhook_id} to Shuffle")
        path = f"/api/v1/hooks/{webhook_id}"
        return self.post(path, data=payload, headers=headers)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Return list of workflows."""
        result = self.get("/api/v1/workflows")
        return result if isinstance(result, list) else []

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow by ID."""
        return self.get(f"/api/v1/workflows/{workflow_id}")

    def health_check(self) -> bool:
        """Check if Shuffle API is reachable."""
        try:
            self.get("/api/v1/health")
            return True
        except Exception:
            return False
