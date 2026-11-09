#!/usr/bin/env python3
"""Unit tests for elasticsearch/es_helpers.py."""

from unittest.mock import Mock

import pytest

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.elasticsearch.es_helpers import (
    build_bulk_body,
    execute_bulk,
    scroll_search_generator,
)


class TestBuildBulkBody:
    """Test build_bulk_body function."""

    def test_build_bulk_body_with_enumerated_ids(self):
        """Test bulk body construction with auto-enumerated IDs."""
        docs = [{"name": "doc1"}, {"name": "doc2"}]
        body = build_bulk_body(docs, "soar-alerts")
        lines = body.strip().split("\n")
        assert len(lines) == 4  # 2 action + 2 doc lines
        assert '"_index": "soar-alerts"' in lines[0]
        assert '"_id": "0"' in lines[0]
        assert '"_id": "1"' in lines[2]
        assert '"name": "doc1"' in lines[1]
        assert '"name": "doc2"' in lines[3]

    def test_build_bulk_body_with_doc_id_field(self):
        """Test bulk body construction using a field value as _id."""
        docs = [{"id": "abc", "name": "doc1"}, {"id": "def", "name": "doc2"}]
        body = build_bulk_body(docs, "soar-alerts", doc_id_field="id")
        lines = body.strip().split("\n")
        assert '"_id": "abc"' in lines[0]
        assert '"_id": "def"' in lines[2]

    def test_build_bulk_body_empty(self):
        """Test bulk body with empty document list."""
        body = build_bulk_body([], "soar-alerts")
        assert body == "\n"

    def test_build_bulk_body_missing_id_field(self):
        """Test that missing doc_id_field defaults to empty string."""
        docs = [{"name": "doc1"}]
        body = build_bulk_body(docs, "soar-alerts", doc_id_field="missing")
        lines = body.strip().split("\n")
        assert '"_id": ""' in lines[0]


class TestExecuteBulk:
    """Test execute_bulk function."""

    def test_execute_bulk_success(self):
        """Test successful bulk request (BL-HTTP-007: post_fn contract)."""
        post_fn = Mock(return_value={"errors": False})

        result = execute_bulk(post_fn, "soar-alerts", '{"data":"test"}')
        assert result == {"errors": False}
        post_fn.assert_called_once()
        call_args = post_fn.call_args[0]
        assert call_args[0] == "/soar-alerts/_bulk"

    def test_execute_bulk_with_refresh(self):
        """Test bulk request with refresh=true."""
        post_fn = Mock(return_value={"errors": False})

        result = execute_bulk(post_fn, "soar-alerts", "{}", refresh=True)
        assert result == {"errors": False}
        assert "?refresh=true" in post_fn.call_args[0][0]

    def test_execute_bulk_empty_response(self):
        """Test bulk request with empty response body."""
        post_fn = Mock(return_value=None)

        result = execute_bulk(post_fn, "soar-alerts", "{}")
        assert result == {}

    def test_execute_bulk_error_propagates_typed_error(self):
        """Transport errors from post_fn keep the typed hierarchy (BL-ERR-004)."""
        from soar_lab.common.exceptions import IntegrationUnavailableError

        post_fn = Mock(side_effect=IntegrationUnavailableError("c", "HTTP 500"))

        with pytest.raises(IntegrationUnavailableError):
            execute_bulk(post_fn, "soar-alerts", "{}")

    def test_execute_bulk_connection_error_raises(self):
        """Test that connection errors raise IntegrationError."""
        post_fn = Mock(side_effect=IntegrationError("c", "Connection refused"))

        with pytest.raises(IntegrationError):
            execute_bulk(post_fn, "soar-alerts", "{}")


class TestScrollSearchGenerator:
    """Test scroll_search_generator function."""

    def test_scroll_search_single_batch(self):
        """Test scroll search with a single batch of results."""
        post_fn = Mock()
        post_fn.side_effect = [
            {
                "_scroll_id": "abc123",
                "hits": {"hits": [{"_source": {"id": 1}}, {"_source": {"id": 2}}]},
            },
            {
                "_scroll_id": "abc123",
                "hits": {"hits": []},
            },
        ]

        results = list(scroll_search_generator(post_fn, "soar-alerts", size=10))
        assert results == [{"id": 1}, {"id": 2}]
        assert post_fn.call_count == 2

    def test_scroll_search_multiple_batches(self):
        """Test scroll search with multiple batches."""
        post_fn = Mock()
        post_fn.side_effect = [
            {
                "_scroll_id": "s1",
                "hits": {"hits": [{"_source": {"id": 1}}]},
            },
            {
                "_scroll_id": "s2",
                "hits": {"hits": [{"_source": {"id": 2}}]},
            },
            {
                "_scroll_id": "s3",
                "hits": {"hits": []},
            },
        ]

        results = list(scroll_search_generator(post_fn, "soar-alerts"))
        assert results == [{"id": 1}, {"id": 2}]

    def test_scroll_search_no_results(self):
        """Test scroll search with no results."""
        post_fn = Mock()
        post_fn.return_value = {
            "_scroll_id": "abc",
            "hits": {"hits": []},
        }

        results = list(scroll_search_generator(post_fn, "soar-alerts"))
        assert results == []

    def test_scroll_search_custom_query(self):
        """Test scroll search with custom query."""
        post_fn = Mock()
        post_fn.return_value = {
            "_scroll_id": "abc",
            "hits": {"hits": []},
        }

        list(scroll_search_generator(post_fn, "soar-alerts", query={"term": {"severity": 3}}))
        call_kwargs = post_fn.call_args.kwargs
        assert call_kwargs["data"]["query"] == {"term": {"severity": 3}}

    def test_scroll_search_default_query_is_match_all(self):
        """Test that default query is match_all."""
        post_fn = Mock()
        post_fn.return_value = {
            "_scroll_id": "abc",
            "hits": {"hits": []},
        }

        list(scroll_search_generator(post_fn, "soar-alerts"))
        call_kwargs = post_fn.call_args.kwargs
        assert call_kwargs["data"]["query"] == {"match_all": {}}
