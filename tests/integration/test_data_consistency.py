#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Data Consistency Tests
Tests for data consistency between services (TheHive, MISP, ES)
"""

import os
import uuid
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
        return TheHiveClient(
            base_url=os.environ.get("THEHIVE_URL", "http://localhost:9000"),
            api_key=os.environ.get("THEHIVE_API_KEY", "test-key"),
            verify_ssl=False,
        )

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing."""
        return MISPClient(
            base_url=os.environ.get("MISP_URL", "http://localhost:8083"),
            api_key=os.environ.get("MISP_API_KEY", "test-key"),
            verify_ssl=False,
        )

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            base_url=os.environ.get("ES_URL", "http://localhost:9200"),
            username=os.environ.get("ELASTIC_USERNAME", "elastic"),
            password=os.environ.get("ELASTIC_PASSWORD", "test-pass"),
        )

    @pytest.fixture
    def test_alert(self):
        """Create test alert data with a unique id so reruns stay hermetic
        against the shared ``alerts`` index."""
        return {
            "alert_id": f"ALERT-TEST-{uuid.uuid4().hex[:10].upper()}",
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
            attributes=[{"type": "sha256", "value": test_alert["hash"]}],
        )

        # Verify both reference the same alert_id
        assert test_alert["alert_id"] in case["description"], "Case must reference the alert"
        assert test_alert["alert_id"] in event["info"], "Event must reference the alert"

        # Verify hash is present in the MISP event (create response does not
        # embed attributes — fetch the event to check them)
        fetched = misp_client.get_event(event["id"])
        event_hash = fetched.get("Attribute", [{}])[0].get("value", "")
        assert test_alert["hash"] == event_hash, "Hash should be stored in the MISP event"

    def test_timestamp_synchronization(self, thehive_client, es_client, test_alert):
        """Test that timestamps are synchronized between services."""
        # Index alert in ES
        es_client.index_document(
            index="alerts",
            document=test_alert,
            doc_id=test_alert["alert_id"],
            refresh=True,
        )

        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Retrieve from ES
        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id.keyword": test_alert["alert_id"]}}
        )

        # Verify timestamps are close (within 1 minute)
        es_timestamp = datetime.fromisoformat(es_doc["hits"]["hits"][0]["_source"]["timestamp"])
        # TheHive createdAt is epoch milliseconds
        created_at = case.get("createdAt")
        case_timestamp = (
            datetime.fromtimestamp(created_at / 1000, UTC)
            if isinstance(created_at, (int, float))
            else datetime.fromisoformat(str(created_at))
        )

        time_diff = abs((es_timestamp - case_timestamp).total_seconds())
        assert time_diff < 60, f"Timestamps should be synchronized, diff: {time_diff}s"

    def test_no_orphaned_data(self, thehive_client, es_client):
        """Test that a correlated alert has a matching case (hermetic check
        on data created by this test — the shared ``alerts`` index holds
        pipeline data without per-case linkage)."""
        alert_id = f"ALERT-ORPHAN-{uuid.uuid4().hex[:10].upper()}"
        es_client.index_document(
            index="alerts",
            document={"alert_id": alert_id, "severity": 2},
            doc_id=alert_id,
            refresh=True,
        )
        thehive_client.create_case(
            title="Orphan Check Case",
            description=f"Alert: {alert_id}",
            severity=2,
        )

        cases = [c for c in thehive_client.search_cases() if alert_id in c.get("description", "")]
        es_alerts = es_client.search(index="alerts", query={"term": {"alert_id.keyword": alert_id}})

        assert es_alerts["hits"]["total"]["value"] >= 1, "ES alert must exist"
        assert len(cases) >= 1, "Correlated TheHive case must exist"

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
        es_client.index_document(
            index="alerts",
            document=test_alert,
            doc_id=test_alert["alert_id"],
            refresh=True,
        )

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
            index="alerts",
            doc_id=test_alert["alert_id"],
            document={"severity": 3},
            refresh=True,
        )

        # Verify consistency
        assert updated_case["severity"] == 3, "Case should be updated"

        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id.keyword": test_alert["alert_id"]}}
        )
        assert (
            es_doc["hits"]["hits"][0]["_source"]["severity"] == 3
        ), "ES document should be updated"

    def test_cross_service_data_validation(self, thehive_client, misp_client, es_client):
        """Test that data is valid across all services."""
        test_data = {
            "alert_id": f"ALERT-VALIDATION-{uuid.uuid4().hex[:10].upper()}",
            "hostname": "validation-host",
            "src_ip": "10.0.0.1",
            "hash": "a" * 64,
            "severity": 2,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Index in ES
        es_client.index_document(
            index="alerts",
            document=test_data,
            doc_id=test_data["alert_id"],
            refresh=True,
        )

        # Create case in TheHive
        case = thehive_client.create_case(
            title="Validation Case",
            description=f"Alert: {test_data['alert_id']}",
            severity=test_data["severity"],
        )

        # Create event in MISP
        event = misp_client.create_event(
            info="Validation Event", attributes=[{"type": "sha256", "value": test_data["hash"]}]
        )

        # Validate data integrity
        assert case["severity"] == test_data["severity"]
        fetched = misp_client.get_event(event["id"])
        assert fetched["Attribute"][0]["value"] == test_data["hash"]

        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id.keyword": test_data["alert_id"]}}
        )
        assert es_doc["hits"]["hits"][0]["_source"]["src_ip"] == test_data["src_ip"]

    def test_data_consistency_on_delete(self, thehive_client, es_client, test_alert):
        """Test delete semantics: deleting a TheHive case does NOT cascade to
        the indexed ES alert — each service owns its data independently."""
        # Index alert in ES
        es_client.index_document(
            index="alerts",
            document=test_alert,
            doc_id=test_alert["alert_id"],
            refresh=True,
        )

        # Create case in TheHive
        case = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert["severity"],
        )

        # Delete case
        thehive_client.delete_case(case["id"])

        # Verify case is gone (soft-deleted → filtered from list_cases)
        remaining = [c for c in thehive_client.list_cases() if c.get("id") == case["id"]]
        assert len(remaining) == 0, "Deleted case must not be listed"

        # ES alert is untouched — no cross-service cascade exists
        es_doc = es_client.search(
            index="alerts", query={"term": {"alert_id.keyword": test_alert["alert_id"]}}
        )
        assert (
            es_doc["hits"]["total"]["value"] == 1
        ), "ES alert must remain after TheHive case deletion"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
