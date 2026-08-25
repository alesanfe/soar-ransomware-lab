#!/usr/bin/env python3
"""
SOAR Ransomware Lab - MISP Integration Tests
Complete integration tests for MISP
"""

from unittest.mock import Mock, patch

import pytest

from soar_lab.infrastructure.integrations.misp.client import MISPClient


class TestMISPIntegration:
    """Test MISP integration."""

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing."""
        return MISPClient(base_url="http://localhost:8083", api_key="test-key", verify_ssl=False)

    def test_connection_and_authentication(self, misp_client):
        """Test MISP connection and authentication."""
        # Test connection
        with patch.object(misp_client.session, "get") as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: {"version": "2.4.0"})

            info = misp_client.get_server_info()
            assert info is not None, "Should connect to MISP"
            assert "version" in info, "Should return server info"

    def test_event_creation(self, misp_client):
        """Test event creation."""
        event_data = {"info": "Test Event", "distribution": 1, "threat_level_id": 1, "analysis": 1}

        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"Event": {"id": "event-001", "info": "Test Event"}}
            )

            event = misp_client.create_event(**event_data)
            assert event["id"] == "event-001", "Event should be created"
            assert event["info"] == "Test Event", "Event info should match"

    def test_ioc_search(self, misp_client):
        """Test IOC search."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "response": [
                        {
                            "Event": {
                                "id": "event-001",
                                "info": "Test Event",
                                "Attribute": [
                                    {"type": "md5", "value": "d41d8cd98f00b204e9800998ecf8427e"}
                                ],
                            }
                        }
                    ]
                },
            )

            results = misp_client.search_events(value="d41d8cd98f00b204e9800998ecf8427e")
            assert len(results) > 0, "Should find IOC"
            assert results[0]["Event"]["id"] == "event-001", "Should return event"

    def test_attribute_enrichment(self, misp_client):
        """Test attribute enrichment."""
        with patch.object(misp_client.session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                content=b'{"Event": {}}',
                json=lambda: {
                    "Event": {
                        "id": "event-001",
                        "Attribute": [
                            {
                                "type": "md5",
                                "value": "d41d8cd98f00b204e9800998ecf8427e",
                                "category": "Payload delivery",
                                "to_ids": True,
                            }
                        ],
                    }
                },
            )

            event = misp_client.get_event("event-001")
            attributes = event.get("Attribute", [])

            assert len(attributes) > 0, "Event should have attributes"
            assert attributes[0]["to_ids"] == True, "Attribute should be enriched"

    def test_event_update(self, misp_client):
        """Test event update."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"Event": {"id": "event-001", "info": "Updated Event"}},
            )

            updated = misp_client.update_event(event_id="event-001", info="Updated Event")
            assert updated["info"] == "Updated Event", "Event should be updated"

    def test_attribute_creation(self, misp_client):
        """Test attribute creation."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"Attribute": {"id": "attr-001", "value": "192.168.1.100"}},
            )

            attribute = misp_client.create_attribute(
                event_id="event-001", type="ip-dst", value="192.168.1.100"
            )
            assert attribute["value"] == "192.168.1.100", "Attribute should be created"

    def test_event_search_by_tags(self, misp_client):
        """Test event search by tags."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "response": [
                        {
                            "Event": {
                                "id": "event-001",
                                "info": "Ransomware Event",
                                "Tag": [{"name": "ransomware"}, {"name": "malware"}],
                            }
                        }
                    ]
                },
            )

            results = misp_client.search_events(tags="ransomware")
            assert len(results) > 0, "Should find events with tag"
            assert results[0]["Event"]["Tag"][0]["name"] == "ransomware", "Tag should match"

    def test_sighting_creation(self, misp_client):
        """Test sighting creation."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"Sighting": {"id": "sighting-001"}}
            )

            sighting = misp_client.create_sighting(attribute_id="attr-001", source="TheHive")
            assert sighting["id"] == "sighting-001", "Sighting should be created"

    def test_event_deletion(self, misp_client):
        """Test event deletion."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"message": "Event deleted"}
            )

            result = misp_client.delete_event("event-001")
            assert result["message"] == "Event deleted", "Event should be deleted"

    def test_proposal_creation(self, misp_client):
        """Test attribute proposal creation."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"Attribute": {"id": "proposal-001"}}
            )

            proposal = misp_client.create_attribute_proposal(
                event_id="event-001", type="domain", value="malicious-domain.com"
            )
            assert proposal["id"] == "proposal-001", "Proposal should be created"

    def test_event_distribution_levels(self, misp_client):
        """Test event distribution levels."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"Event": {"id": "event-001", "distribution": 1}}
            )

            event = misp_client.create_event(
                info="Test Event",
                distribution=1,  # Your organisation only
            )
            assert event["distribution"] == 1, "Distribution level should be set"

    def test_event_threat_levels(self, misp_client):
        """Test event threat levels."""
        with patch.object(misp_client.session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, json=lambda: {"Event": {"id": "event-001", "threat_level_id": 4}}
            )

            event = misp_client.create_event(info="Critical Event", threat_level_id=4)  # Critical
            assert event["threat_level_id"] == 4, "Threat level should be set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
