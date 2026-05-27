#!/usr/bin/env python3
"""
SOAR Ransomware Lab - MISP Client
Dedicated client for MISP threat intelligence platform.
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class MISPClient(BaseHTTPClient):
    """Client for MISP REST API."""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            config_provider: Optional[object] = None,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('misp_url')
            key = api_key or config_provider.get('misp_api_key')
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError("misp_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("misp_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key)
        self._session.headers.update({"Accept": "application/json"})

    def _default_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = api_key
        return headers

    def search_events(self, value: str, type_attribute: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search MISP for events matching an attribute value.

        Args:
            value: IOC value to search (e.g. IP, domain, hash).
            type_attribute: MISP attribute type filter (e.g. "ip-dst", "sha256").

        Returns:
            List of matching MISP events.
        """
        payload: Dict[str, Any] = {"value": value}
        if type_attribute:
            payload["type_attribute"] = type_attribute
        result = self.post("/events/restSearch", data=payload)
        return result.get("response", [])

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """Get a specific event by ID."""
        return self.get(f"/events/{event_id}")

    def create_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new MISP event."""
        logger.info(f"Creating MISP event: {event.get('info', 'unknown')}")
        return self.post("/events", data=event)

    def add_attribute(self, event_id: str, attribute: Dict[str, Any]) -> Dict[str, Any]:
        """Add an attribute to an existing event."""
        logger.info(f"Adding attribute to MISP event {event_id}")
        return self.post(f"/attributes/add/{event_id}", data=attribute)

    def health_check(self) -> bool:
        """Check if MISP is reachable."""
        try:
            self.get("/users/heartbeat")
            return True
        except Exception:
            return False
