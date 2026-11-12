#!/usr/bin/env python3
"""Unit tests for elasticsearch_client.py."""

from unittest.mock import Mock, patch

import pytest

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)


class TestElasticsearchClient:
    """Test ElasticsearchClient."""

    def test_initialization_with_base_url(self):
        """Test initialization with base_url."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        assert client.index == "soar-alerts"

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "elasticsearch_url": "http://localhost:9200",
            "elasticsearch_api_key": "test-key",
        }.get(key, default)

        client = ElasticsearchClient(base_url=None, config_provider=mock_config)
        assert client.index == "soar-alerts"

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError."""
        with pytest.raises(ValueError, match="elasticsearch_url must be provided"):
            ElasticsearchClient(base_url=None)

    def test_initialization_with_basic_auth(self):
        """Test initialization with basic auth credentials."""
        with patch.dict(
            "os.environ", {"ELASTIC_USERNAME": "elastic", "ELASTIC_PASSWORD": "password"}
        ):
            client = ElasticsearchClient(base_url="http://localhost:9200")
            assert client._session.auth == ("elastic", "password")

    def test_initialization_with_explicit_auth(self):
        """Test initialization with explicit auth credentials."""
        client = ElasticsearchClient(
            base_url="http://localhost:9200", username="admin", password="secret"
        )
        assert client._session.auth == ("admin", "secret")

    def test_initialization_with_custom_index(self):
        """Test initialization with custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200", index="custom-index")
        assert client.index == "custom-index"

    def test_index_document(self):
        """Test indexing a document."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"})
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/soar-alerts/_doc", data={"test": "data"})

    def test_index_document_with_id(self):
        """Test indexing a document with custom ID."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"}, doc_id="123")
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/soar-alerts/_doc/123", data={"test": "data"})

    def test_index_document_with_custom_index(self):
        """Test indexing a document to custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "created"})

        result = client.index_document({"test": "data"}, index="custom-index")
        assert result == {"result": "created"}
        client.post.assert_called_once_with("/custom-index/_doc", data={"test": "data"})

    def test_search_default(self):
        """Test search with default parameters."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search()
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with(
            "/soar-alerts/_search", data={"query": {"match_all": {}}, "size": 10}
        )

    def test_search_with_query(self):
        """Test search with custom query."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(query={"match": {"field": "value"}})
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with(
            "/soar-alerts/_search", data={"query": {"match": {"field": "value"}}, "size": 10}
        )

    def test_search_with_sort(self):
        """Test search with sort parameter."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(sort=[{"@timestamp": {"order": "desc"}}])
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with(
            "/soar-alerts/_search",
            data={
                "query": {"match_all": {}},
                "size": 10,
                "sort": [{"@timestamp": {"order": "desc"}}],
            },
        )

    def test_search_with_custom_index(self):
        """Test search with custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"hits": {"hits": []}})

        result = client.search(index="custom-index")
        assert result == {"hits": {"hits": []}}
        client.post.assert_called_once_with(
            "/custom-index/_search", data={"query": {"match_all": {}}, "size": 10}
        )

    def test_count(self):
        """Test counting documents."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"count": 42})

        result = client.count()
        assert result == 42
        client.get.assert_called_once_with("/soar-alerts/_count")

    def test_count_with_custom_index(self):
        """Test counting documents in custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"count": 42})

        result = client.count(index="custom-index")
        assert result == 42
        client.get.assert_called_once_with("/custom-index/_count")

    def test_get_document(self):
        """Test getting a document by ID."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"_source": {"test": "data"}})

        result = client.get_document("123")
        assert result == {"_source": {"test": "data"}}
        client.get.assert_called_once_with("/soar-alerts/_doc/123")

    def test_get_document_with_custom_index(self):
        """Test getting a document from custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"_source": {"test": "data"}})

        result = client.get_document("123", index="custom-index")
        assert result == {"_source": {"test": "data"}}
        client.get.assert_called_once_with("/custom-index/_doc/123")

    def test_delete_document(self):
        """Test deleting a document."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = True
        mock_response.content = b'{"result": "deleted"}'
        mock_response.json.return_value = {"result": "deleted"}
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_document("123")
        assert result == {"result": "deleted"}

    def test_delete_document_exception(self):
        """delete_document routes through the breakered pipeline: transport
        failures surface as TYPED IntegrationError (BL-ES-003)."""
        import requests as _req

        client = ElasticsearchClient(base_url="http://localhost:9200")
        client._session.delete = Mock(side_effect=_req.ConnectionError("Delete error"))

        with pytest.raises(IntegrationError, match="ElasticsearchClient"):
            client.delete_document("123")

    def test_delete_index(self):
        """Test deleting an index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = True
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_index()
        assert result is True

    def test_delete_index_not_found(self):
        """Test deleting an index that doesn't exist returns True."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        client._session.delete = Mock(return_value=mock_response)

        result = client.delete_index()
        assert result is True

    def test_delete_index_error(self):
        """Test deleting an index on error returns False."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client._session.delete = Mock(side_effect=Exception("Error"))

        result = client.delete_index()
        assert result is False

    def test_update_document(self):
        """Test updating a document."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "updated"})

        result = client.update_document("123", {"field": "new_value"})
        assert result == {"result": "updated"}
        client.post.assert_called_once_with(
            "/soar-alerts/_update/123?retry_on_conflict=10", data={"doc": {"field": "new_value"}}
        )

    def test_update_document_with_custom_index(self):
        """Test updating a document in custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.post = Mock(return_value={"result": "updated"})

        result = client.update_document("123", {"field": "new_value"}, index="custom-index")
        assert result == {"result": "updated"}
        client.post.assert_called_once_with(
            "/custom-index/_update/123?retry_on_conflict=10", data={"doc": {"field": "new_value"}}
        )

    def test_get_latest_documents(self):
        """Test getting latest documents."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(
            return_value={"hits": {"hits": [{"_source": {"id": 1}}, {"_source": {"id": 2}}]}}
        )

        result = client.get_latest_documents()
        assert result == [{"id": 1}, {"id": 2}]

    def test_get_latest_documents_with_custom_index(self):
        """Test getting latest documents from custom index."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={"hits": {"hits": []}})

        result = client.get_latest_documents(index="custom-index")
        assert result == []
        client.search.assert_called_once_with(
            size=10,
            index="custom-index",
            sort=[{"@timestamp": {"order": "desc", "unmapped_type": "date"}}],
        )

    def test_search_by_alert_id_found(self):
        """Test searching by alert_id when found."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(
            return_value={"hits": {"hits": [{"_source": {"alert_id": "test-123"}}]}}
        )

        result = client.search_by_alert_id("test-123")
        assert result == {"alert_id": "test-123"}

    def test_search_by_alert_id_not_found(self):
        """Test searching by alert_id when not found."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.search = Mock(return_value={"hits": {"hits": []}})

        result = client.search_by_alert_id("test-123")
        assert result is None

    def test_cluster_health(self):
        """Test getting cluster health."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "green", "number_of_nodes": 1})

        result = client.cluster_health()
        assert result == {"status": "green", "number_of_nodes": 1}
        client.get.assert_called_once_with("/_cluster/health")

    def test_health_check_green(self):
        """Test health check returns True for green status."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "green"})

        result = client.health_check()
        assert result is True

    def test_health_check_yellow(self):
        """Test health check returns True for yellow status."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "yellow"})

        result = client.health_check()
        assert result is True

    def test_health_check_red(self):
        """Test health check returns False for red status."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(return_value={"status": "red"})

        result = client.health_check()
        assert result is False

    def test_health_check_exception(self):
        """Test health check returns False on exception."""
        client = ElasticsearchClient(base_url="http://localhost:9200")
        client.get = Mock(side_effect=Exception("Connection error"))

        result = client.health_check()
        assert result is False


class TestElasticsearchClientCoverage:
    """Tests targeting previously uncovered ElasticsearchClient paths."""

    def _client(self) -> ElasticsearchClient:
        return ElasticsearchClient(base_url="http://localhost:9200")

    def test_hosts_list_uses_first_entry(self):
        client = ElasticsearchClient(hosts=["http://es-a:9200", "http://es-b:9200"])
        assert client.base_url.startswith("http")

    def test_hosts_empty_list_falls_back_to_config(self):
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            "elasticsearch_url": "http://localhost:9200",
        }.get(key, default)
        client = ElasticsearchClient(hosts=[], config_provider=mock_config)
        assert client.base_url

    def test_info(self):
        client = self._client()
        client.get = Mock(return_value={"cluster_name": "soar"})
        assert client.info() == {"cluster_name": "soar"}
        client.get.assert_called_once_with("/")

    def test_indices_property_and_refresh(self):
        client = self._client()
        client.post = Mock(return_value={"_shards": {"successful": 1}})
        assert client.indices.refresh("idx") == {"_shards": {"successful": 1}}
        client.post.assert_called_once_with("/idx/_refresh")

    def test_indices_get_mapping(self):
        client = self._client()
        client.get = Mock(return_value={"mappings": {"properties": {}}})
        assert client.indices.get_mapping("idx") == {
            "idx": {"mappings": {"properties": {}}}
        }

        client.get = Mock(return_value={})
        assert client.indices.get_mapping("idx") == {"idx": {"mappings": {}}}

    def test_indices_create_and_delete_delegate(self):
        client = self._client()
        client.create_index = Mock(return_value={"acknowledged": True})
        client.delete_index = Mock(return_value=True)

        assert client.indices.create("idx", body={"mappings": {"m": 1}}) == {
            "acknowledged": True
        }
        client.create_index.assert_called_once_with(index_name="idx", mapping={"m": 1})
        assert client.indices.delete("idx") is True
        client.delete_index.assert_called_once_with("idx")

    def test_create_index_builds_body_and_puts(self):
        client = self._client()
        client.index_exists = Mock(return_value=False)
        client.put = Mock(return_value={"acknowledged": True, "index": "idx"})

        result = client.create_index("idx", settings={"number_of_shards": 1})
        assert result == {"acknowledged": True, "index": "idx"}
        body = client.put.call_args.kwargs["data"]
        assert body["settings"] == {"number_of_shards": 1}
        assert "alert_id" in body["mappings"]["properties"]

    def test_create_index_explicit_mapping_no_settings(self):
        """Custom mapping skips the default; no settings skips that key."""
        client = self._client()
        client.index_exists = Mock(return_value=False)
        client.put = Mock(return_value={"acknowledged": True})

        client.create_index("idx", mapping={"properties": {"x": {"type": "keyword"}}})
        body = client.put.call_args.kwargs["data"]
        assert "settings" not in body
        assert body["mappings"] == {"properties": {"x": {"type": "keyword"}}}

    def test_create_index_existing_short_circuits(self):
        client = self._client()
        client.index_exists = Mock(return_value=True)
        client.put = Mock()

        result = client.create_index("idx")
        assert result == {"acknowledged": True, "index": "idx"}
        client.put.assert_not_called()

    def test_index_exists_true_false_and_error(self):
        client = self._client()
        ok = Mock(status_code=200)
        client._session.head = Mock(return_value=ok)
        assert client.index_exists("idx") is True

        missing = Mock(status_code=404)
        client._session.head = Mock(return_value=missing)
        assert client.index_exists("idx") is False

        client._session.head = Mock(side_effect=Exception("boom"))
        assert client.index_exists("idx") is False

    def test_index_document_refresh_appends_param(self):
        client = self._client()
        client.post = Mock(return_value={"result": "created"})

        client.index_document({"a": 1}, refresh=True)
        client.post.assert_called_once_with(
            "/soar-alerts/_doc?refresh=true", data={"a": 1}
        )

    def test_search_with_aggs(self):
        client = self._client()
        client.post = Mock(return_value={"hits": {"hits": []}, "aggregations": {}})

        client.search(aggs={"by_tag": {"terms": {"field": "tag"}}})
        body = client.post.call_args.kwargs["data"]
        assert body["aggs"] == {"by_tag": {"terms": {"field": "tag"}}}

    def test_update_document_retry_none_omits_param_and_refresh(self):
        client = self._client()
        client.post = Mock(return_value={"result": "updated"})

        client.update_document("1", {"a": 1}, retry_on_conflict=None, refresh=True)
        client.post.assert_called_once_with(
            "/soar-alerts/_update/1?refresh=true", data={"doc": {"a": 1}}
        )

        client.update_document("1", {"a": 1}, retry_on_conflict=3)
        client.post.assert_called_with(
            "/soar-alerts/_update/1?retry_on_conflict=3", data={"doc": {"a": 1}}
        )

    def test_bulk_index_delegates_through_post_raw(self):
        client = self._client()
        client.post_raw = Mock(return_value={"errors": False, "items": []})

        result = client.bulk_index(
            [{"id": "d1", "v": 1}], index="idx", doc_id_field="id", refresh=True
        )
        assert result == {"errors": False, "items": []}
        path, body, content_type = client.post_raw.call_args.args
        assert path == "/idx/_bulk?refresh=true"
        assert '"_id": "d1"' in body
        assert content_type == "application/x-ndjson"

    def test_scroll_search_yields_and_clears_scroll(self):
        client = self._client()
        page1 = {
            "_scroll_id": "s1",
            "hits": {"hits": [{"_source": {"n": 1}}]},
        }
        page2 = {"_scroll_id": "s2", "hits": {"hits": []}}
        client.post = Mock(side_effect=[page1, page2])
        client.delete = Mock(return_value={})

        assert list(client.scroll_search(size=1)) == [{"n": 1}]
        assert client.post.call_count == 2
        client.delete.assert_called_once()

    def test_auth_not_applied_without_password(self):
        """No credentials anywhere → session.auth stays unset (50->exit)."""
        with patch.dict("os.environ", {}, clear=True):
            client = ElasticsearchClient(base_url="http://localhost:9200")
        assert client._session.auth is None
