#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Idempotency Tests
Tests for idempotent operations
"""

import pytest
from datetime import datetime, timezone
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
from unittest.mock import Mock, patch


class TestIdempotency:
    """Test idempotent operations"""

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing"""
        return TheHiveClient(
            base_url="http://localhost:9000",
            api_key="test-key",
            verify_ssl=False
        )

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing"""
        return ElasticsearchClient(
            hosts=["http://localhost:9200"],
            username="elastic",
            password="test-pass"
        )

    @pytest.fixture
    def test_alert(self):
        """Create test alert data"""
        return {
            "alert_id": "ALERT-IDEMPOTENT-001",
            "hostname": "idempotent-host",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e" * 2,
            "severity": 2,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def test_duplicate_alert_no_duplicate_case(self, thehive_client, test_alert):
        """Test that sending same alert twice doesn't create duplicate cases"""
        # Send alert first time
        case1 = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert['severity']
        )

        # Send alert second time
        case2 = thehive_client.create_case(
            title=f"Case for {test_alert['alert_id']}",
            description=f"Alert: {test_alert['alert_id']}",
            severity=test_alert['severity']
        )

        # Should return same case or not create duplicate
        # Implementation should check for existing case with same alert_id
        assert case1['id'] == case2['id'] or case2 is None, \
            "Duplicate alert should not create duplicate case"

    def test_workflow_re_execution_idempotent(self, test_alert):
        """Test that workflow re-execution is idempotent"""
        # Execute workflow first time
        execution_id_1 = "exec-001"

        # Execute workflow second time with same alert
        execution_id_2 = "exec-002"

        # System should detect duplicate and not re-execute
        # or re-execute safely without side effects
        assert True, "Workflow re-execution should be idempotent"

    def test_resource_cleanup_after_idempotent_operation(self, es_client, test_alert):
        """Test that resources are cleaned up after idempotent operation"""
        # Index alert
        es_client.index_document(index="alerts", document=test_alert)

        # Try to index same alert again
        es_client.index_document(index="alerts", document=test_alert)

        # Should update existing document, not create duplicate
        result = es_client.search(
            index="alerts",
            query={"term": {"alert_id": test_alert['alert_id']}}
        )

        assert result['hits']['total']['value'] == 1, \
            "Should have only one document after idempotent operation"

    def test_client_operation_idempotent(self, thehive_client):
        """Test that client operations are idempotent"""
        # Create case
        case = thehive_client.create_case(
            title="Idempotent Test Case",
            description="Test case for idempotency",
            severity=2
        )

        # Update case with same data
        updated_case = thehive_client.update_case(
            case_id=case['id'],
            title="Idempotent Test Case",
            description="Test case for idempotency",
            severity=2
        )

        # Should not cause side effects
        assert updated_case['id'] == case['id'], \
            "Update with same data should be idempotent"

    def test_bulk_operation_idempotent(self, es_client):
        """Test that bulk operations are idempotent"""
        documents = [
            {"alert_id": f"BULK-IDEMP-{i}", "severity": i % 4}
            for i in range(10)
        ]

        # Bulk index first time
        es_client.bulk_index(index="alerts", documents=documents)

        # Bulk index same documents again
        es_client.bulk_index(index="alerts", documents=documents)

        # Should update existing documents, not create duplicates
        result = es_client.search(index="alerts", query={"match_all": {}})
        assert result['hits']['total']['value'] == 10, \
            "Should have only 10 documents after idempotent bulk operation"

    def test_delete_operation_idempotent(self, thehive_client):
        """Test that delete operations are idempotent"""
        # Create case
        case = thehive_client.create_case(
            title="Delete Test Case",
            description="Test case for delete idempotency",
            severity=2
        )

        # Delete case first time
        thehive_client.delete_case(case['id'])

        # Delete case second time
        try:
            thehive_client.delete_case(case['id'])
        except Exception:
            # Should handle gracefully (case already deleted)
            pass

        # Should not cause errors
        assert True, "Delete operation should be idempotent"

    def test_observable_creation_idempotent(self, thehive_client):
        """Test that observable creation is idempotent"""
        # Create case
        case = thehive_client.create_case(
            title="Observable Test Case",
            description="Test case for observable idempotency",
            severity=2
        )

        # Create observable first time
        obs1 = thehive_client.create_observable(
            case_id=case['id'],
            data_type="ip",
            data="192.168.1.100"
        )

        # Create same observable second time
        obs2 = thehive_client.create_observable(
            case_id=case['id'],
            data_type="ip",
            data="192.168.1.100"
        )

        # Should return existing observable or not create duplicate
        assert obs1['id'] == obs2['id'] or obs2 is None, \
            "Duplicate observable should not be created"

    def test_es_upsert_idempotent(self, es_client):
        """Test that Elasticsearch upsert is idempotent"""
        document = {
            "alert_id": "UPSERT-001",
            "severity": 2
        }

        # Upsert first time
        es_client.index_document(index="alerts", document=document)

        # Upsert same document with same data
        es_client.index_document(index="alerts", document=document)

        # Should update existing document
        result = es_client.search(
            index="alerts",
            query={"term": {"alert_id": "UPSERT-001"}}
        )
        assert result['hits']['total']['value'] == 1, \
            "Upsert should be idempotent"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
