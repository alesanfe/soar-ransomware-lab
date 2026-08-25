#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Data Consistency Tests
Tests for data consistency between services (TheHive, MISP, ES)
"""

from datetime import UTC, datetime

import pytest

from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient


@pytest.mark.requires_external
class TestDataConsistency:
    """Test data consistency between services."""

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing."""
        return TheHiveClient(base_url="http://thehive:9000", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing."""
        return MISPClient(base_url="http://misp:8083", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            hosts=["http://elasticsearch:9200"], username="elastic", password="test-pass"
        )

    @pytest.fixture
    def test_alert(self):
        """Create test alert data."""
        return {
            "alert_id": "ALERT-TEST-001",
            "hostname": "test-host",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e" * 2,
            "severity": 2,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def test_thehive_misp_case_event_consistency(self, thehive_client, misp_client, test_alert):
        """Test that TheHive cases and MISP events are consistent."""
        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Create event in MISP
        event = misp_client.create_event(
            info=f"Event for {test_alert['alert_id']}",
            attributes=[{"type": "md5", "value": test_alert["hash"]}],
        )

        # Verify consistency
        assert case["description"] == event["info"], "Case description should match event info"

        # Verify hash is present in both
        case_hash = case.get("description", "")
        event_hash = event.get("Attribute", [{}])[0].get("value", "")
        assert (
            test_alert["hash"] in case_hash or test_alert["hash"] == event_hash
        ), "Hash should be consistent between case and event"

    def test_timestamp_synchronization(self, thehive_client, es_client, test_alert):
        """Test that timestamps are synchronized between services."""
        # Index alert in ES
        es_client.index_document(index="alerts", document=test_alert)

        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Retrieve from ES
        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id": test_alert["alert_id"]}}
        )

        # Verify timestamps are close (within 1 minute)
        es_timestamp = datetime.fromisoformat(es_doc["hits"]["hits"][0]["_source"]["timestamp"])
        case_timestamp = datetime.fromisoformat(
            case.get("createdAt", datetime.now(UTC).isoformat())
        )

        time_diff = abs((es_timestamp - case_timestamp).total_seconds())
        assert time_diff < 60, f"Timestamps should be synchronized, diff: {time_diff}s"

    def test_no_orphaned_data(self, thehive_client, es_client):
        """Test that there are no orphaned documents."""
        # Get all cases from TheHive
        cases = thehive_client.search_cases()

        # Get all alerts from ES
        es_alerts = es_client.search(index="alerts", query={"match_all": {}})

        # Verify all ES alerts have corresponding cases
        es_alert_ids = [hit["_source"].get("alert_id") for hit in es_alerts["hits"]["hits"]]
        case_alert_ids = [
            case.get("description", "").split("Alert: ")[-1]
            for case in cases
            if "Alert:" in case.get("description", "")
        ]

        orphaned_alerts = set(es_alert_ids) - set(case_alert_ids)
        assert len(orphaned_alerts) == 0, f"Found orphaned alerts: {orphaned_alerts}"

    def test_referential_integrity(self, thehive_client, misp_client):
        """Test referential integrity between services."""
        # Create case with observable
        case = thehive_client.create_case(
            title="Test Case", description="Test case for referential integrity", severity=2
        )

        thehive_client.create_observable(case_id=case["id"], data_type="ip", data="192.168.1.100")

        # Create MISP event with same IP
        event = misp_client.create_event(
            info="Test Event", attributes=[{"type": "ip-dst", "value": "192.168.1.100"}]
        )

        # Verify observable is linked to case
        case_observables = thehive_client.get_case_observables(case["id"])
        assert any(
            obs["data"] == "192.168.1.100" for obs in case_observables
        ), "Observable should be linked to case"

        # Verify IP is in MISP event
        event_ips = [
            attr["value"] for attr in event.get("Attribute", []) if attr["type"] == "ip-dst"
        ]
        assert "192.168.1.100" in event_ips, "IP should be in MISP event"

    def test_data_consistency_after_update(self, thehive_client, es_client, test_alert):
        """Test that data remains consistent after updates."""
        # Index alert in ES
        es_client.index_document(index="alerts", document=test_alert)

        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Update case
        updated_case = thehive_client.update_case(case_id=case["id"], severity=3)

        # Update ES document
        es_client.update_document(
            index="alerts", doc_id=test_alert["alert_id"], document={"severity": 3}
        )

        # Verify consistency
        assert updated_case["severity"] == 3, "Case should be updated"

        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id": test_alert["alert_id"]}}
        )
        assert (
            es_doc["hits"]["hits"][0]["_source"]["severity"] == 3
        ), "ES document should be updated"

    def test_cross_service_data_validation(self, thehive_client, misp_client, es_client):
        """Test that data is valid across all services."""
        test_data = {
            "alert_id": "ALERT-VALIDATION-001",
            "hostname": "validation-host",
            "src_ip": "10.0.0.1",
            "hash": "a" * 64,
            "severity": 2,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Index in ES
        es_client.index_document(index="alerts", document=test_data)

        # Create case in TheHive
        case = thehive_client.create_case(
            title="Validation Case",
            description=f"Alert: {test_data['alert_id']}",
            severity=test_data["severity"],
        )

        # Create event in MISP
        event = misp_client.create_event(
            info="Validation Event", attributes=[{"type": "md5", "value": test_data["hash"]}]
        )

        # Validate data integrity
        assert case["severity"] == test_data["severity"]
        assert event["Attribute"][0]["value"] == test_data["hash"]

        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id": test_data["alert_id"]}}
        )
        assert es_doc["hits"]["hits"][0]["_source"]["src_ip"] == test_data["src_ip"]

    def test_data_consistency_on_delete(self, thehive_client, es_client, test_alert):
        """Test that data is consistently deleted across services."""
        # Index alert in ES
        es_client.index_document(index="alerts", document=test_alert)

        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Delete case
        thehive_client.delete_case(case["id"])

        # Verify alert is marked as processed in ES
        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id": test_alert["alert_id"]}}
        )
        assert (
            es_doc["hits"]["hits"][0]["_source"].get("status") == "processed"
        ), "Alert should be marked as processed after case deletion"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
