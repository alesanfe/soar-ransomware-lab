#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Elasticsearch Integration Tests
Complete integration tests for Elasticsearch
"""

from datetime import UTC, datetime

import pytest

from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)


@pytest.mark.requires_external
class TestElasticsearchIntegration:
    """Test Elasticsearch integration."""

    @pytest.fixture
    def es_client(self):
        """Create Elasticsearch client for testing."""
        return ElasticsearchClient(
            hosts=["http://localhost:9200"], username="elastic", password="test-pass"
        )

    def test_connection_and_authentication(self, es_client):
        """Test ES connection and authentication."""
        # Test connection
        info = es_client.info()
        assert info is not None, "Should connect to Elasticsearch"
        assert "cluster_name" in info, "Should return cluster info"

    def test_index_creation(self, es_client):
        """Test index creation."""
        index_name = "test-alerts"

        # Create index
        es_client.create_index(
            index_name=index_name,
            mapping={
                "properties": {
                    "alert_id": {"type": "keyword"},
                    "hostname": {"type": "keyword"},
                    "severity": {"type": "integer"},
                    "timestamp": {"type": "date"},
                }
            },
        )

        # Verify index exists
        assert es_client.index_exists(index_name), "Index should be created"

        # Cleanup
        es_client.delete_index(index_name)

    def test_document_indexing(self, es_client):
        """Test document indexing."""
        index_name = "test-docs"
        es_client.create_index(index_name=index_name)

        document = {
            "alert_id": "TEST-001",
            "hostname": "test-host",
            "severity": 2,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Index document
        result = es_client.index_document(index=index_name, document=document)

        assert result["result"] == "created", "Document should be created"

        # Cleanup
        es_client.delete_index(index_name)

    def test_document_retrieval(self, es_client):
        """Test document retrieval."""
        index_name = "test-retrieval"
        es_client.create_index(index_name=index_name)

        document = {"alert_id": "TEST-RETRIEVE-001", "hostname": "retrieval-host", "severity": 3}

        # Index document
        es_client.index_document(index=index_name, document=document)

        # Refresh index
        es_client.indices.refresh(index=index_name)

        # Retrieve document
        result = es_client.search(
            index=index_name, query={"term": {"alert_id": "TEST-RETRIEVE-001"}}
        )

        assert result["hits"]["total"]["value"] > 0, "Document should be retrieved"
        assert result["hits"]["hits"][0]["_source"]["hostname"] == "retrieval-host"

        # Cleanup
        es_client.delete_index(index_name)

    def test_query_execution(self, es_client):
        """Test query execution."""
        index_name = "test-query"
        es_client.create_index(index_name=index_name)

        # Index multiple documents
        for i in range(5):
            es_client.index_document(
                index=index_name, document={"alert_id": f"QUERY-{i}", "severity": i % 4}
            )

        es_client.indices.refresh(index=index_name)

        # Execute query
        result = es_client.search(index=index_name, query={"range": {"severity": {"gte": 2}}})

        assert result["hits"]["total"]["value"] > 0, "Query should return results"

        # Cleanup
        es_client.delete_index(index_name)

    def test_aggregation_query(self, es_client):
        """Test aggregation queries."""
        index_name = "test-agg"
        es_client.create_index(index_name=index_name)

        # Index documents
        for i in range(10):
            es_client.index_document(
                index=index_name,
                document={
                    "alert_id": f"AGG-{i}",
                    "severity": i % 4,
                    "type": "ransomware" if i % 2 == 0 else "malware",
                },
            )

        es_client.indices.refresh(index=index_name)

        # Execute aggregation
        result = es_client.search(
            index=index_name,
            query={"match_all": {}},
            aggs={"severity_distribution": {"terms": {"field": "severity"}}},
        )

        assert "aggregations" in result, "Aggregation should be present"
        assert (
            "severity_distribution" in result["aggregations"]
        ), "Severity distribution should be present"

        # Cleanup
        es_client.delete_index(index_name)

    def test_document_update(self, es_client):
        """Test document update."""
        index_name = "test-update"
        es_client.create_index(index_name=index_name)

        document = {"alert_id": "TEST-UPDATE-001", "severity": 1}

        # Index document
        result = es_client.index_document(index=index_name, document=document)
        doc_id = result["_id"]

        es_client.indices.refresh(index=index_name)

        # Update document
        es_client.update_document(index=index_name, doc_id=doc_id, document={"severity": 3})

        es_client.indices.refresh(index=index_name)

        # Verify update
        result = es_client.search(index=index_name, query={"match_all": {}})
        assert result["hits"]["hits"][0]["_source"]["severity"] == 3, "Document should be updated"

        # Cleanup
        es_client.delete_index(index_name)

    def test_document_deletion(self, es_client):
        """Test document deletion."""
        index_name = "test-delete"
        es_client.create_index(index_name=index_name)

        document = {"alert_id": "TEST-DELETE-001", "severity": 2}

        # Index document
        result = es_client.index_document(index=index_name, document=document)
        doc_id = result["_id"]

        es_client.indices.refresh(index=index_name)

        # Delete document
        es_client.delete_document(index=index_name, doc_id=doc_id)

        es_client.indices.refresh(index=index_name)

        # Verify deletion
        result = es_client.search(index=index_name, query={"match_all": {}})
        assert result["hits"]["total"]["value"] == 0, "Document should be deleted"

        # Cleanup
        es_client.delete_index(index_name)

    def test_bulk_indexing(self, es_client):
        """Test bulk indexing."""
        index_name = "test-bulk"
        es_client.create_index(index_name=index_name)

        documents = [{"alert_id": f"BULK-{i}", "severity": i % 4} for i in range(100)]

        # Bulk index
        es_client.bulk_index(index=index_name, documents=documents)

        es_client.indices.refresh(index=index_name)

        # Verify all documents indexed
        result = es_client.search(index=index_name, query={"match_all": {}})
        assert result["hits"]["total"]["value"] == 100, "All documents should be indexed"

        # Cleanup
        es_client.delete_index(index_name)

    def test_document_mapping_validation(self, es_client):
        """Test document mapping validation."""
        index_name = "test-mapping"

        mapping = {
            "properties": {
                "alert_id": {"type": "keyword"},
                "hostname": {"type": "keyword"},
                "severity": {"type": "integer"},
                "timestamp": {"type": "date"},
                "hash": {"type": "keyword"},
            }
        }

        es_client.create_index(index_name=index_name, mapping=mapping)

        # Verify mapping
        actual_mapping = es_client.indices.get_mapping(index=index_name)
        assert index_name in actual_mapping, "Mapping should be retrieved"

        # Cleanup
        es_client.delete_index(index_name)

    def test_scroll_search(self, es_client):
        """Test scroll search for large result sets."""
        index_name = "test-scroll"
        es_client.create_index(index_name=index_name)

        # Index many documents
        documents = [{"alert_id": f"SCROLL-{i}", "severity": i % 4} for i in range(1000)]

        es_client.bulk_index(index=index_name, documents=documents)
        es_client.indices.refresh(index=index_name)

        # Scroll search
        all_results = []
        for hit in es_client.scroll_search(index=index_name, query={"match_all": {}}):
            all_results.append(hit)

        assert len(all_results) == 1000, "All documents should be retrieved via scroll"

        # Cleanup
        es_client.delete_index(index_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
