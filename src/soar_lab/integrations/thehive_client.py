#!/usr/bin/env python3
"""
SOAR Ransomware Lab - TheHive Client
Dedicated client for TheHive incident management platform.
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class TheHiveClient(BaseHTTPClient):
    """Client for TheHive API."""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            config_provider: Optional[object] = None,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('thehive_url')
            key = api_key or config_provider.get('thehive_api_key')
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError("thehive_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("thehive_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key)

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert in TheHive.

        Args:
            alert: Alert payload dict.

        Returns:
            TheHive API response.
        """
        logger.info(f"Creating alert in TheHive: {alert.get('title', 'unknown')}")
        return self.post("/api/alert", data=alert)

    def create_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Create a case in TheHive.

        Args:
            case: Case payload dict.

        Returns:
            TheHive API response.
        """
        logger.info(f"Creating case in TheHive: {case.get('title', 'unknown')}")
        return self.post("/api/case", data=case)

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Retrieve a case by ID."""
        return self.get(f"/api/case/{case_id}")

    def add_observable(self, case_id: str, observable: Dict[str, Any]) -> Dict[str, Any]:
        """Add an observable (artifact) to a case."""
        logger.info(f"Adding observable to case {case_id}")
        return self.post(f"/api/case/{case_id}/artifact", data=observable)

    def list_cases(self) -> List[Dict[str, Any]]:
        """Return all open cases."""
        result = self.get("/api/case")
        return result if isinstance(result, list) else []

    def health_check(self) -> bool:
        """Check if TheHive is reachable."""
        try:
            self.get("/api/health")
            return True
        except Exception:
            return False
