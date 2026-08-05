#!/usr/bin/env python3
"""
SOAR Ransomware Lab - MISP Client
Dedicated client for MISP threat intelligence platform.
"""

import requests

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger

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

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Perform a MISP API GET without replacing its JSON Accept header."""
        try:
            response = self._session.get(self._url(path), timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except requests.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def search_events(
        self,
        value: Optional[str] = None,
        type_attribute: Optional[str] = None,
        tags: Optional[Any] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search MISP events matching an IOC value or tags."""
        if value:
            # Primary: /events/restSearch with the IOC value returns matching
            # events (with attributes) in a single request.
            try:
                payload: Dict[str, Any] = {
                    "returnFormat": "json",
                    "value": value,
                    "limit": 10,
                }
                if type_attribute:
                    payload["type"] = type_attribute
                result = self.post("/events/restSearch", data=payload)
                response = result.get("response", result.get("Event", []))
                if isinstance(response, dict):
                    response = [response]
                if isinstance(response, list) and response:
                    return [item if "Event" in item else {"Event": item}
                            for item in response if isinstance(item, dict)]
            except Exception as exc:
                logger.debug("search_events /events/restSearch failed for %s: %s", value, exc)

            # Secondary: /attributes/restSearch with includeEvent to find the
            # events that contain this value, then fetch each full event once.
            try:
                payload = {
                    "returnFormat": "json",
                    "value": value,
                    "includeEvent": 1,
                    "limit": 10,
                }
                if type_attribute:
                    payload["type"] = type_attribute
                result = self.post("/attributes/restSearch", data=payload)
                attributes = result.get("response", {}).get("Attribute", [])
                if isinstance(attributes, list) and attributes:
                    events = {}
                    for attribute in attributes:
                        if not isinstance(attribute, dict):
                            continue
                        event_id = attribute.get("event_id")
                        if not event_id or event_id in events:
                            continue
                        event = self.get_event(str(event_id))
                        if isinstance(event, dict) and event.get("id") == event_id:
                            events[event_id] = event
                    if events:
                        return [{"Event": event} for event in events.values()]
            except Exception as exc:
                logger.debug("search_events /attributes/restSearch failed for %s: %s", value, exc)

            return []

        payload: Dict[str, Any] = {"returnFormat": "json"}
        if tags:
            payload["tag"] = tags if isinstance(tags, str) else ",".join(str(t) for t in tags)
        payload.update(kwargs)
        result = self.post("/events/restSearch", data=payload)
        response = result.get("response", result.get("Event", []))
        if isinstance(response, dict):
            response = [response]
        if not isinstance(response, list):
            return []
        return [item if "Event" in item else {"Event": item}
                for item in response if isinstance(item, dict)]

    def get_event(self, event_id: str) -> Dict[str, Any]:
        """Get a specific MISP event with its attributes."""
        result = self.get(f"/events/view/{event_id}")
        return result.get("Event", result) if isinstance(result, dict) else {}

    def create_event(
        self,
        event: Optional[Dict[str, Any]] = None,
        info: str = "",
        distribution: int = 0,
        threat_level_id: int = 2,
        analysis: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new MISP event.

        Args can be supplied as a single dict (`event`) or as individual fields.
        """
        if event is not None:
            payload = dict(event)
        else:
            payload = {
                "info": info,
                "distribution": distribution,
                "threat_level_id": threat_level_id,
                "analysis": analysis,
            }
        payload.update(kwargs)
        logger.info(f"Creating MISP event: {payload.get('info', 'unknown')}")
        result = self.post("/events", data=payload)
        return result.get("Event", result)

    def update_event(self, event_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing MISP event."""
        payload = dict(kwargs)
        payload["id"] = event_id
        result = self.post(f"/events/edit/{event_id}", data=payload)
        return result.get("Event", result)

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete a MISP event."""
        return self.post(f"/events/delete/{event_id}")

    def add_attribute(self, event_id: str, attribute: Dict[str, Any]) -> Dict[str, Any]:
        """Add an attribute to an existing event."""
        logger.info(f"Adding attribute to MISP event {event_id}")
        return self.post(f"/attributes/add/{event_id}", data=attribute)

    def create_attribute(
        self,
        event_id: str,
        type: str = "",  # noqa: A002
        value: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Create an attribute on a MISP event."""
        payload = {
            "type": type,
            "value": value,
        }
        payload.update(kwargs)
        result = self.post(f"/attributes/add/{event_id}", data=payload)
        return result.get("Attribute", result)

    def create_sighting(self, attribute_id: str, source: str = "", **kwargs) -> Dict[str, Any]:
        """Create a sighting for an attribute."""
        payload = {"id": attribute_id, "source": source}
        payload.update(kwargs)
        result = self.post(f"/sightings/add/{attribute_id}", data=payload)
        return result.get("Sighting", result)

    def create_attribute_proposal(
        self,
        event_id: str,
        type: str = "",  # noqa: A002
        value: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a proposal (shadow attribute) for a MISP event."""
        payload = {"type": type, "value": value, "event_id": event_id}
        payload.update(kwargs)
        result = self.post(f"/shadow_attributes/add/{event_id}", data=payload)
        return result.get("Attribute", result)

    def search_attributes(
        self,
        value: Optional[str] = None,
        attr_type: Optional[Any] = None,
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
        payload: Dict[str, Any] = {"returnFormat": "json"}
        if value:
            payload["value"] = value
        if attr_type:
            payload["type"] = attr_type
        result = self.post("/attributes/restSearch", data=payload)
        attributes = result.get("response", {}).get("Attribute", [])
        return attributes[:limit] if isinstance(attributes, list) else []

    def list_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent MISP events.

        Args:
            limit: Max number of events.

        Returns:
            List of event dicts.
        """
        result = self.get("/events/index", params={"limit": limit})
        if isinstance(result, list):
            return result
        response = result.get("response", result)
        return response if isinstance(response, list) else []

    def get_attribute_count(self) -> int:
        """Return total number of attributes in MISP."""
        try:
            attrs = self.search_attributes(limit=1)
            result = self.post("/attributes/restSearch",
                               data={"returnFormat": "count"})
            return result.get("count", len(attrs))
        except Exception:
            return 0

    def get_server_info(self) -> Dict[str, Any]:
        """Return MISP server version and settings."""
        return self.get("/servers/serverSettings.json")

    def health_check(self) -> bool:
        """Check if MISP is reachable."""
        try:
            self.get("/users/heartbeat")
            return True
        except Exception:
            return False
