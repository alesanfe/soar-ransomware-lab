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
            verify_ssl: bool = True,
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

        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl)
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

    def search_attributes(
            self,
            value: Optional[str] = None,
            attr_type: Optional[str] = None,
            limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search MISP attributes by value and/or type.

        Args:
            value: Exact value to match (IP, hash, domain, ...).
            attr_type: MISP attribute type, e.g. "ip-dst", "sha256".
            limit: Max results to return.

        Returns:
            List of attribute dicts.
        """
        payload: Dict[str, Any] = {"returnFormat": "json", "limit": limit}
        if value:
            payload["value"] = value
        if attr_type:
            payload["type"] = attr_type
        result = self.post("/attributes/restSearch", data=payload)
        return result.get("response", {}).get("Attribute", [])

    def list_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent MISP events.

        Args:
            limit: Max number of events.

        Returns:
            List of event dicts.
        """
        result = self.post("/events/restSearch",
                           data={"returnFormat": "json", "limit": limit})
        return result.get("response", [])

    def get_attribute_count(self) -> int:
        """Return total number of attributes in MISP."""
        try:
            attrs = self.search_attributes(limit=1)
            result = self.post("/attributes/restSearch",
                               data={"returnFormat": "count"})
            return result.get("count", len(attrs))
        except Exception:
            return 0

    def health_check(self) -> bool:
        """Check if MISP is reachable."""
        try:
            self.get("/users/heartbeat")
            return True
        except Exception:
            return False
