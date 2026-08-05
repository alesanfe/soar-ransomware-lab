#!/usr/bin/env python3
"""
Unit tests for elasticsearch_client.py
"""

import pytest
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from unittest.mock import Mock, patch


class TestElasticsearchClient:
    """Test ElasticsearchClient"""

    def test_initialization_with_base_url(self):
        """Test initialization with base_url"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        assert client.index == "soar-alerts"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'elasticsearch_url': 'http://localhost:9200',
            'elasticsearch_api_key': 'test-key'
        }.get(key, default)

        client = ElasticsearchClient(base_url=None, config_provider=mock_config)
        assert client.index == "soar-alerts"

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError"""
        with pytest.raises(ValueError, match="elasticsearch_url must be provided"):
            ElasticsearchClient(base_url=None)

    def test_initialization_with_basic_auth(self):
        """Test initialization with basic auth credentials"""
        with patch.dict('os.environ', {'ELASTIC_USERNAME': 'elastic', 'ELASTIC_PASSWORD': 'password'}):
            client = ElasticsearchClient(base_url="http://localhost:9200")
            assert client._session.auth == ('elastic', 'password')

    def test_initialization_with_explicit_auth(self):
        """Test initialization with explicit auth credentials"""
        client = ElasticsearchClient(
            base_url="http://localhost:9200",
            username="admin",
            password="secret"
        )
        assert client._session.auth == ('admin', 'secret')

    def test_initialization_with_custom_index(self):
        """Test initialization with custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200", index="custom-index")
        assert client.index == "custom-index"

    def test_index_document(self):
        """Test indexing a document"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"})
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/soar-alerts/_doc", data={"test": "data"})

    def test_index_document_with_id(self):
        """Test indexing a document with custom ID"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"}, doc_id="123")
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/soar-alerts/_doc/123", data={"test": "data"})

    def test_index_document_with_custom_index(self):
        """Test indexing a document to custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"}, index="custom-index")
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/custom-index/_doc", data={"test": "data"})

    def test_search_default(self):
        """Test search with default parameters"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search()
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with("/soar-alerts/_search", data={"query": {"match_all": {}}, "size": 10})

    def test_search_with_query(self):
        """Test search with custom query"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(query={"match": {"field": "value"}})
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with("/soar-alerts/_search",
                                            data={"query": {"match": {"field": "value"}}, "size": 10})

    def test_search_with_sort(self):
        """Test search with sort parameter"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(sort=[{"@timestamp": {"order": "desc"}}])
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with("/soar-alerts/_search", data={"query": {"match_all": {}}, "size": 10,
                                                                          "sort": [{"@timestamp": {"order": "desc"}}]})

    def test_search_with_custom_index(self):
        """Test search with custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(index="custom-index")
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with("/custom-index/_search", data={"query": {"match_all": {}}, "size": 10})

    def test_count(self):
        """Test counting documents"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"count": 42})

        result = client.count()
        assert result == 42
        client.get.assert_called_once_with("/soar-alerts/_count")

    def test_count_with_custom_index(self):
        """Test counting documents in custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"count": 42})

        result = client.count(index="custom-index")
        assert result == 42
        client.get.assert_called_once_with("/custom-index/_count")

    def test_get_document(self):
        """Test getting a document by ID"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"_source": {"test": "data"}})

        result = client.get_document("123")
        assert result == {"_source": {"test": "data"}}
        client.get.assert_called_once_with("/soar-alerts/_doc/123")

    def test_get_document_with_custom_index(self):
        """Test getting a document from custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"_source": {"test": "data"}})

        result = client.get_document("123", index="custom-index")
        assert result == {"_source": {"test": "data"}}
        client.get.assert_called_once_with("/custom-index/_doc/123")

    def test_delete_document(self):
        """Test deleting a document"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b'{"result": "deleted"}'
        mock_response.json.return_value = {"result": "deleted"}
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_document("123")
        assert result == {"result": "deleted"}

    def test_delete_document_exception(self):
        """Test delete_document raises IntegrationError on exception"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client._session.delete = Mock(side_effect=Exception("Delete error"))

        with pytest.raises(IntegrationError, match="ElasticsearchClient"):
            client.delete_document("123")

    def test_delete_index(self):
        """Test deleting an index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = True
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_index()
        assert result is True

    def test_delete_index_not_found(self):
        """Test deleting an index that doesn't exist returns True"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_index()
        assert result is True

    def test_delete_index_error(self):
        """Test deleting an index on error returns False"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client._session.delete = Mock(side_effect=Exception("Error"))

        result = client.delete_index()
        assert result is False

    def test_update_document(self):
        """Test updating a document"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "updated"})

        result = client.update_document("123", {"field": "new_value"})
        assert result == {"result": "updated"}
        client.post.assert_called_once_with("/soar-alerts/_update/123", data={"doc": {"field": "new_value"}})

    def test_update_document_with_custom_index(self):
        """Test updating a document in custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "updated"})

        result = client.update_document("123", {"field": "new_value"}, index="custom-index")
        assert result == {"result": "updated"}
        client.post.assert_called_once_with("/custom-index/_update/123", data={"doc": {"field": "new_value"}})

    def test_get_latest_documents(self):
        """Test getting latest documents"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={
            "hits": {
                "hits": [
                    {"_source": {"id": 1}},
                    {"_source": {"id": 2}}
                ]
            }
        })

        result = client.get_latest_documents()
        assert result == [{"id": 1}, {"id": 2}]

    def test_get_latest_documents_with_custom_index(self):
        """Test getting latest documents from custom index"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={"hits": {"hits": []}})

        result = client.get_latest_documents(index="custom-index")
        assert result == []
        client.search.assert_called_once_with(size=10, index="custom-index")

    def test_search_by_alert_id_found(self):
        """Test searching by alert_id when found"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={
            "hits": {
                "hits": [
                    {"_source": {"alert_id": "test-123"}}
                ]
            }
        })

        result = client.search_by_alert_id("test-123")
        assert result == {"alert_id": "test-123"}

    def test_search_by_alert_id_not_found(self):
        """Test searching by alert_id when not found"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={"hits": {"hits": []}})

        result = client.search_by_alert_id("test-123")
        assert result is None

    def test_cluster_health(self):
        """Test getting cluster health"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "green", "number_of_nodes": 1})

        result = client.cluster_health()
        assert result == {"status": "green", "number_of_nodes": 1}
        client.get.assert_called_once_with("/_cluster/health")

    def test_health_check_green(self):
        """Test health check returns True for green status"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "green"})

        result = client.health_check()
        assert result is True

    def test_health_check_yellow(self):
        """Test health check returns True for yellow status"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "yellow"})

        result = client.health_check()
        assert result is True

    def test_health_check_red(self):
        """Test health check returns False for red status"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "red"})

        result = client.health_check()
        assert result is False

    def test_health_check_exception(self):
        """Test health check returns False on exception"""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(side_effect=Exception("Connection error"))

        result = client.health_check()
        assert result is False
