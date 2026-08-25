#!/usr/bin/env python3
"""SOAR Ransomware Lab - MISP Client.

Dedicated client for MISP threat intelligence platform.
"""

from typing import Any

import requests

from soar_lab.common.constants import (
    CONTENT_TYPE_JSON,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)
from soar_lab.common.exceptions import IntegrationError
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class MISPClient(BaseHTTPClient):
    """Client for MISP REST API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Any | None = None,
        verify_ssl: bool = True,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get("misp_url")
            key = api_key or config_provider.get("misp_api_key")
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError(
                "misp_url must be provided in config_provider or as base_url parameter"
            )
        if not key:
            raise ValueError(
                "misp_api_key must be provided in config_provider or as api_key parameter"
            )

        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl)
        self._session.headers.update({HEADER_ACCEPT: CONTENT_TYPE_JSON})

    def _default_headers(self, api_key: str | None) -> dict[str, str]:
        headers = {HEADER_ACCEPT: CONTENT_TYPE_JSON, HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
        if api_key:
            headers[HEADER_AUTHORIZATION] = api_key
        return headers

    def get(self, path: str, **kwargs: Any) -> Any:
        """Perform a MISP API GET without replacing its JSON Accept header.

        Args:
            path: API path relative to the MISP base URL.
            **kwargs: Additional keyword arguments forwarded to the
                underlying ``requests.Session.get`` call (e.g. ``params``).

        Returns:
            dict: The parsed JSON response body, or an empty dict if the
            response has no content.

        Raises:
            IntegrationError: If an HTTP error or generic request error occurs.
            requests.ConnectionError: If the connection to MISP fails.
            requests.Timeout: If the request times out.
        """
        try:
            response = self._session.get(self._url(path), timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except requests.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    @staticmethod
    def _normalize_response(response: Any) -> list[dict[str, Any]]:
        """Normalize a MISP API response into a list of event dicts."""
        if isinstance(response, dict):
            response = [response]
        if not isinstance(response, list):
            return []
        return [
            item if "Event" in item else {"Event": item}
            for item in response
            if isinstance(item, dict)
        ]

    def _search_by_value(self, value: str, type_attribute: str | None) -> list[dict[str, Any]]:
        """Search events by IOC value using /events/restSearch."""
        try:
            payload: dict[str, Any] = {"returnFormat": "json", "value": value, "limit": 10}
            if type_attribute:
                payload["type"] = type_attribute
            result = self.post("/events/restSearch", data=payload)
            response = result.get("response", result.get("Event", []))
            events = self._normalize_response(response)
            if events:
                return events
        except Exception as exc:
            logger.debug("search_events /events/restSearch failed for %s: %s", value, exc)
        return []

    def _search_by_attributes(self, value: str, type_attribute: str | None) -> list[dict[str, Any]]:
        """Search events by attribute value using /attributes/restSearch with.

        includeEvent.
        """
        try:
            payload = {"returnFormat": "json", "value": value, "includeEvent": 1, "limit": 10}
            if type_attribute:
                payload["type"] = type_attribute
            result = self.post("/attributes/restSearch", data=payload)
            attributes = result.get("response", {}).get("Attribute", [])
            if not isinstance(attributes, list) or not attributes:
                return []
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
            return [{"Event": event} for event in events.values()] if events else []
        except Exception as exc:
            logger.debug("search_events /attributes/restSearch failed for %s: %s", value, exc)
        return []

    def _search_by_tags(self, tags: Any, **kwargs: Any) -> list[dict[str, Any]]:
        """Search events by tags using /events/restSearch."""
        payload: dict[str, Any] = {"returnFormat": "json"}
        if tags:
            payload["tag"] = tags if isinstance(tags, str) else ",".join(str(t) for t in tags)
        payload.update(kwargs)
        result = self.post("/events/restSearch", data=payload)
        response = result.get("response", result.get("Event", []))
        return self._normalize_response(response)

    def search_events(
        self,
        value: str | None = None,
        type_attribute: str | None = None,
        tags: Any | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search MISP events matching an IOC value or tags.

        Args:
            value: IOC value to search for (IP, hash, domain, ...). If
                ``None``, a tag-based search is performed instead.
            type_attribute: Optional MISP attribute type filter, e.g.
                "ip-dst" or "sha256".
            tags: A tag name or list of tag names to search by. Used only
                when ``value`` is ``None``.
            **kwargs: Additional keyword arguments forwarded to the
                tag-based search payload.

        Returns:
            list: A list of event dicts (each typically wrapped under an
            ``"Event"`` key). Returns an empty list if no matches are found.
        """
        if value:
            return self._search_by_value(value, type_attribute) or self._search_by_attributes(
                value, type_attribute
            )
        return self._search_by_tags(tags, **kwargs)

    def get_event(self, event_id: str) -> dict[str, Any]:
        """Get a specific MISP event with its attributes.

        Args:
            event_id: The numeric ID of the MISP event to retrieve.

        Returns:
            dict: The MISP event dict, or an empty dict if the response is
            not a dict.
        """
        result = self.get(f"/events/view/{event_id}")
        return dict(result.get("Event", result) if isinstance(result, dict) else {})

    def create_event(
        self,
        event: dict[str, Any] | None = None,
        info: str = "",
        distribution: int = 0,
        threat_level_id: int = 2,
        analysis: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new MISP event.

        Args can be supplied as a single dict (`event`) or as individual fields.

        Args:
            event: Optional dict containing the full event payload. When
                provided, individual field arguments are ignored.
            info: Human-readable description of the event.
            distribution: MISP distribution level (0-5).
            threat_level_id: MISP threat level ID (1-4).
            analysis: MISP analysis stage (0-3).
            **kwargs: Additional event fields merged into the payload.

        Returns:
            dict: The created MISP event as returned by the API.
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
        if "attributes" in payload:
            payload["Attribute"] = payload.pop("attributes")
        logger.info("Creating MISP event: %s", payload.get("info", "unknown"))
        result = self.post("/events", data={"Event": payload})
        return dict(result.get("Event", result))

    def update_event(self, event_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing MISP event.

        Args:
            event_id: The numeric ID of the MISP event to update.
            **kwargs: Event fields to update (e.g. ``info``,
                ``threat_level_id``).

        Returns:
            dict: The updated MISP event as returned by the API.
        """
        payload = kwargs.copy()
        payload["id"] = event_id
        result = self.post(f"/events/edit/{event_id}", data=payload)
        return dict(result.get("Event", result))

    def delete_event(self, event_id: str) -> dict[str, Any]:
        """Delete a MISP event.

        Args:
            event_id: The numeric ID of the MISP event to delete.

        Returns:
            dict: The API response confirming deletion.
        """
        return dict(self.post(f"/events/delete/{event_id}"))

    def add_attribute(self, event_id: str, attribute: dict[str, Any]) -> dict[str, Any]:
        """Add an attribute to an existing event.

        Args:
            event_id: The numeric ID of the MISP event to attach the
                attribute to.
            attribute: Dict describing the attribute payload (e.g. ``type``
                and ``value``).

        Returns:
            dict: The API response for the added attribute.
        """
        logger.info("Adding attribute to MISP event %s", event_id)
        return dict(self.post(f"/attributes/add/{event_id}", data=attribute))

    def create_attribute(
        self,
        event_id: str,
        attr_type: str = "",
        value: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create an attribute on a MISP event.

        Args:
            event_id: The numeric ID of the MISP event to attach the
                attribute to.
            attr_type: MISP attribute type, e.g. "ip-dst" or "sha256".
            value: The attribute value (IP, hash, domain, ...).
            **kwargs: Additional attribute fields merged into the payload.

        Returns:
            dict: The created attribute as returned by the API.
        """
        payload = {
            "type": attr_type,
            "value": value,
        }
        payload.update(kwargs)
        result = self.post(f"/attributes/add/{event_id}", data=payload)
        return dict(result.get("Attribute", result))

    def create_sighting(self, attribute_id: str, source: str = "", **kwargs: Any) -> dict[str, Any]:
        """Create a sighting for an attribute.

        Args:
            attribute_id: The numeric ID of the MISP attribute to record a
                sighting against.
            source: Optional free-text source of the sighting.
            **kwargs: Additional sighting fields merged into the payload.

        Returns:
            dict: The created sighting as returned by the API.
        """
        payload = {"id": attribute_id, "source": source}
        payload.update(kwargs)
        result = self.post(f"/sightings/add/{attribute_id}", data=payload)
        return dict(result.get("Sighting", result))

    def create_attribute_proposal(
        self,
        event_id: str,
        attr_type: str = "",
        value: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a proposal (shadow attribute) for a MISP event.

        Args:
            event_id: The numeric ID of the MISP event to propose the
                attribute on.
            attr_type: MISP attribute type, e.g. "ip-dst" or "sha256".
            value: The proposed attribute value.
            **kwargs: Additional proposal fields merged into the payload.

        Returns:
            dict: The created shadow attribute as returned by the API.
        """
        payload = {"type": attr_type, "value": value, "event_id": event_id}
        payload.update(kwargs)
        result = self.post(f"/shadow_attributes/add/{event_id}", data=payload)
        return dict(result.get("Attribute", result))

    def search_attributes(
        self,
        value: str | None = None,
        attr_type: Any | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search MISP attributes by value and/or type.

        Args:
            value: Exact value to match (IP, hash, domain, ...).
            attr_type: MISP attribute type, e.g. "ip-dst", "sha256".
            limit: Max results to return.

        Returns:
            List of attribute dicts.
        """
        payload: dict[str, Any] = {"returnFormat": "json"}
        if value:
            payload["value"] = value
        if attr_type:
            payload["type"] = attr_type
        attributes = (
            self.post("/attributes/restSearch", data=payload)
            .get("response", {})
            .get("Attribute", [])
        )
        return attributes[:limit] if isinstance(attributes, list) else []

    def list_events(self, limit: int = 20) -> list[dict[str, Any]]:
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
        """Return total number of attributes in MISP.

        Returns:
            int: The total attribute count, or 0 if the request fails.
        """
        try:
            attrs = self.search_attributes(limit=1)
            result = self.post("/attributes/restSearch", data={"returnFormat": "count"})
            return int(result.get("count", len(attrs)))
        except Exception:
            return 0

    def get_server_info(self) -> dict[str, Any]:
        """Return MISP server version and settings.

        Returns:
            dict: The MISP server settings and version information.
        """
        return dict(self.get("/servers/serverSettings.json"))

    def health_check(self) -> bool:
        """Check if MISP is reachable.

        Returns:
            bool: True if the MISP heartbeat endpoint responds successfully,
            False otherwise.
        """
        try:
            self.get("/users/heartbeat")
            return True
        except Exception:
            return False
