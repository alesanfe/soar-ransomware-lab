#!/usr/bin/env python3
"""Unit tests for misp_client.py."""

from unittest.mock import Mock

import pytest

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.misp.client import MISPClient


class TestMISPClient:
    """Test MISPClient."""

    def test_initialization_with_base_url_and_api_key(self):
        """Test initialization with base_url and api_key."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        assert "Accept" in client._session.headers
        assert client._session.headers["Accept"] == "application/json"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "misp_url": "http://localhost:8083",
            "misp_api_key": "test-key",
        }.get(key, default)

        client = MISPClient(base_url=None, api_key=None, config_provider=mock_config)
        assert "Accept" in client._session.headers

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError."""
        with pytest.raises(ValueError, match="misp_url must be provided"):
            MISPClient(base_url=None, api_key="test-key")

    def test_initialization_without_api_key_raises(self):
        """Test initialization without api_key raises ValueError."""
        with pytest.raises(ValueError, match="misp_api_key must be provided"):
            MISPClient(base_url="http://localhost:8083", api_key=None)

    def test_default_headers_with_api_key(self):
        """Test _default_headers with api_key."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        headers = client._default_headers("custom-key")
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "custom-key"

    def test_default_headers_without_api_key(self):
        """Test _default_headers without api_key."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        headers = client._default_headers(None)
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_search_events(self):
        """Test searching events."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        result = client.search_events("8.8.8.8")
        assert result == [{"Event": {"id": "1"}}]

    def test_search_events_with_type_attribute(self):
        """Test searching events with type_attribute filter."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        result = client.search_events("8.8.8.8", type_attribute="ip-dst")
        assert result == [{"Event": {"id": "1"}}]

    def test_get_event(self):
        """Test getting a specific event."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key", verify_ssl=False)
        # Mock the instance's get method (inherited from BaseHTTPClient)
        client.get = Mock(return_value={"Event": {"id": "1", "info": "test event"}})

        result = client.get_event("1")
        assert result == {"id": "1", "info": "test event"}
        client.get.assert_called_once_with("/events/view/1")

    def test_create_event(self):
        """Test creating a new event."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"id": "1", "info": "new event"})

        result = client.create_event({"info": "new event"})
        assert result == {"id": "1", "info": "new event"}

    def test_add_attribute(self):
        """Test adding an attribute to an event."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"id": "1", "value": "8.8.8.8"})

        result = client.add_attribute("1", {"type": "ip-dst", "value": "8.8.8.8"})
        assert result == {"id": "1", "value": "8.8.8.8"}

    def test_search_attributes(self):
        """Test searching attributes."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": [{"id": "1"}]}})

        result = client.search_attributes(value="8.8.8.8")
        assert result == [{"id": "1"}]

    def test_search_attributes_with_type(self):
        """Test searching attributes with type filter."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": [{"id": "1"}]}})

        result = client.search_attributes(value="8.8.8.8", attr_type="ip-dst")
        assert result == [{"id": "1"}]

    def test_search_attributes_with_limit(self):
        """Test searching attributes with custom limit."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"response": {"Attribute": []}})

        result = client.search_attributes(limit=100)
        assert result == []

    def test_list_events(self):
        """Test listing events."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(return_value=[{"id": "1"}, {"id": "2"}])

        result = client.list_events()
        assert result == [{"id": "1"}, {"id": "2"}]

    def test_list_events_with_limit(self):
        """Test listing events with custom limit."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(return_value=[{"id": "1"}])

        result = client.list_events(limit=50)
        assert result == [{"id": "1"}]

    def test_get_attribute_count(self):
        """Test getting attribute count."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(return_value={"count": 42})

        result = client.get_attribute_count()
        assert result == 42

    def test_get_attribute_count_fallback(self):
        """Test get_attribute_count falls back to len of attributes."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(side_effect=[{"response": {"Attribute": [{"id": "1"}]}}, {}])

        result = client.get_attribute_count()
        assert result == 1

    def test_get_attribute_count_exception(self):
        """Test get_attribute_count returns 0 on exception."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.post = Mock(side_effect=Exception("Error"))

        result = client.get_attribute_count()
        assert result == 0

    def test_health_check(self):
        """Test health check returns True when successful."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()
        assert result is True

    def test_health_check_exception(self):
        """Test health check returns False on exception."""
        client = MISPClient(base_url="http://localhost:8083", api_key="test-key")
        client.get = Mock(side_effect=Exception("Error"))

        result = client.health_check()
        assert result is False


class TestMISPClientCoverage:
    """Tests targeting previously uncovered MISPClient methods/paths."""

    def _client(self) -> MISPClient:
        return MISPClient(base_url="http://localhost:8083", api_key="test-key")

    def test_get_pins_accept_json_and_forwards_headers(self):
        """MISPClient.get pins Accept to JSON while delegating to the base."""
        from unittest.mock import patch

        from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient

        client = self._client()
        with patch.object(BaseHTTPClient, "get", return_value={}) as base_get:
            client.get("/events/view/1", headers={"X-Extra": "1"}, params={"a": 1})
        base_get.assert_called_once_with(
            "/events/view/1",
            headers={"X-Extra": "1", "Accept": "application/json"},
            params={"a": 1},
        )

    def test_normalize_response_wraps_dict(self):
        assert MISPClient._normalize_response({"id": 1}) == [{"Event": {"id": 1}}]

    def test_normalize_response_rejects_non_list(self):
        assert MISPClient._normalize_response("nope") == []

    def test_normalize_response_wraps_bare_items(self):
        assert MISPClient._normalize_response([{"id": 1}, "junk", {"Event": {"id": 2}}]) == [
            {"Event": {"id": 1}},
            {"Event": {"id": 2}},
        ]

    def test_search_by_attributes_fetches_events(self):
        client = self._client()
        client.post = Mock(
            return_value={"response": {"Attribute": [{"event_id": 7}, {"event_id": 7}, "junk"]}}
        )
        client.get_event = Mock(return_value={"id": 7, "info": "ev"})

        result = client._search_by_attributes("8.8.8.8", "ip-dst", 5)

        assert result == [{"Event": {"id": 7, "info": "ev"}}]
        client.get_event.assert_called_once_with("7")

    def test_search_by_attributes_empty_returns_empty(self):
        client = self._client()
        client.post = Mock(return_value={"response": {}})

        assert client._search_by_attributes("8.8.8.8", None, 5) == []

    def test_search_by_attributes_mismatched_event_skipped(self):
        client = self._client()
        client.post = Mock(return_value={"response": {"Attribute": [{"event_id": 7}]}})
        client.get_event = Mock(return_value={"id": 8})  # id mismatch

        assert client._search_by_attributes("8.8.8.8", None, 5) == []

    def test_search_by_tags_with_string_and_list(self):
        client = self._client()
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        assert client._search_by_tags("tlp:red") == [{"Event": {"id": "1"}}]
        payload_str = client.post.call_args.kwargs["data"]
        assert payload_str["tag"] == "tlp:red"

        client.post = Mock(return_value={"response": [{"id": "1"}]})
        client._search_by_tags(["a", "b"], extra="x")
        payload_list = client.post.call_args.kwargs["data"]
        assert payload_list["tag"] == "a,b"
        assert payload_list["extra"] == "x"

        client.post = Mock(return_value={"response": [{"id": "1"}]})
        client._search_by_tags(None)
        assert "tag" not in client.post.call_args.kwargs["data"]

    def test_search_events_without_value_uses_tags(self):
        """value=None delegates to the tag-based search."""
        client = self._client()
        client.post = Mock(return_value={"response": [{"id": "1"}]})

        assert client.search_events(tags="tlp:red") == [{"Event": {"id": "1"}}]
        assert client.post.call_args.kwargs["data"]["tag"] == "tlp:red"

    def test_search_events_value_endpoint_failure_falls_back(self):
        """When /events/restSearch raises, the attribute search is used."""
        client = self._client()
        client.post = Mock(
            side_effect=[
                IntegrationError("MISPClient", "boom"),
                {"response": {"Attribute": [{"event_id": 7}]}},
            ]
        )
        client.get_event = Mock(return_value={"id": 7})

        result = client.search_events("8.8.8.8")
        assert result == [{"Event": {"id": 7}}]

    def test_search_events_both_endpoints_fail_raises_first_error(self):
        client = self._client()
        client.post = Mock(
            side_effect=[
                IntegrationError("MISPClient", "first"),
                IntegrationError("MISPClient", "second"),
            ]
        )

        with pytest.raises(IntegrationError, match="first"):
            client.search_events("8.8.8.8")

    def test_search_events_empty_then_failure_raises_second_error(self):
        """Empty first search (no error) + failing attribute search → the
        attribute error propagates since there is no earlier failure."""
        client = self._client()
        client.post = Mock(
            side_effect=[
                {"response": []},
                IntegrationError("MISPClient", "attr-fail"),
            ]
        )

        with pytest.raises(IntegrationError, match="attr-fail"):
            client.search_events("8.8.8.8")

    def test_create_event_from_fields_and_attribute_rename(self):
        client = self._client()
        client.post = Mock(return_value={"Event": {"id": 9}})

        result = client.create_event(info="ev", attributes=[{"type": "ip-dst"}])
        assert result == {"id": 9}
        sent = client.post.call_args.kwargs["data"]["Event"]
        assert sent["info"] == "ev"
        assert sent["Attribute"] == [{"type": "ip-dst"}]
        assert "attributes" not in sent

    def test_update_event(self):
        client = self._client()
        client.post = Mock(return_value={"Event": {"id": "3", "info": "upd"}})

        assert client.update_event("3", info="upd") == {"id": "3", "info": "upd"}
        client.post.assert_called_once_with("/events/edit/3", data={"info": "upd", "id": "3"})

    def test_delete_event(self):
        client = self._client()
        client.post = Mock(return_value={"success": True})

        assert client.delete_event("3") == {"success": True}
        client.post.assert_called_once_with("/events/delete/3")

    def test_create_attribute(self):
        client = self._client()
        client.post = Mock(return_value={"Attribute": {"id": 5}})

        assert client.create_attribute("7", "ip-dst", "1.2.3.4", comment="c") == {"id": 5}
        sent = client.post.call_args.kwargs["data"]
        assert sent == {"type": "ip-dst", "value": "1.2.3.4", "comment": "c"}

    def test_create_sighting(self):
        client = self._client()
        client.post = Mock(return_value={"Sighting": {"id": 6}})

        assert client.create_sighting("5", source="lab") == {"id": 6}
        sent = client.post.call_args.kwargs["data"]
        assert sent == {"id": "5", "source": "lab"}

    def test_create_attribute_proposal(self):
        client = self._client()
        client.post = Mock(return_value={"Attribute": {"id": 8}})

        assert client.create_attribute_proposal("7", "domain", "evil.example") == {"id": 8}
        sent = client.post.call_args.kwargs["data"]
        assert sent == {"type": "domain", "value": "evil.example", "event_id": "7"}

    def test_list_events_dict_response_and_non_list(self):
        client = self._client()
        client.get = Mock(return_value={"response": [{"id": "1"}]})
        assert client.list_events() == [{"id": "1"}]

        client.get = Mock(return_value={"other": "shape"})
        assert client.list_events() == []

    def test_get_server_info(self):
        client = self._client()
        client.get = Mock(return_value={"version": "2.4"})

        assert client.get_server_info() == {"version": "2.4"}
        client.get.assert_called_once_with("/servers/serverSettings.json")
