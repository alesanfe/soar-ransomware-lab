#!/usr/bin/env python3
"""SOAR Ransomware Lab - Elasticsearch Client.

Dedicated client for Elasticsearch (soar-alerts index).
"""

from typing import Any

from soar_lab.common.constants import ALERTS_INDEX, ENV_ELASTIC_PASSWORD
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient
from soar_lab.infrastructure.integrations.elasticsearch.es_helpers import (
    build_bulk_body,
    execute_bulk,
    scroll_search_generator,
)

logger = get_logger(__name__)

DEFAULT_INDEX = ALERTS_INDEX
_TEST_PLACEHOLDER = "test-placeholder"


class ElasticsearchClient(BaseHTTPClient):
    """Client for Elasticsearch REST API with optional Basic Auth."""

    def __init__(
        self,
        base_url: str | None = None,
        hosts: Any | None = None,
        api_key: str | None = None,
        config_provider: Any | None = None,
        index: str = DEFAULT_INDEX,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
        timeout: int = 10,
        retries: int = 3,
    ) -> None:
        url, key = self._resolve_url_and_key(base_url, hosts, api_key, config_provider)
        _username, _password = self._resolve_auth(username, password)

        super().__init__(
            base_url=url, api_key=key, timeout=timeout, retries=retries, verify_ssl=verify_ssl
        )
        self.index = index

        # Apply Basic Auth if credentials are available
        if _username and _password:
            self._session.auth = (_username, _password)

    @staticmethod
    def _resolve_url_and_key(
        base_url: str | None,
        hosts: Any | None,
        api_key: str | None,
        config_provider: Any | None,
    ) -> tuple[str, str | None]:
        """Resolve the Elasticsearch URL and API key from params or config."""
        raw_url = base_url or hosts
        if isinstance(raw_url, (list, tuple)):
            raw_url = raw_url[0] if raw_url else None
        if config_provider:
            url = raw_url or config_provider.get("elasticsearch_url")
            key = api_key or config_provider.get("elasticsearch_api_key")
        else:
            url = raw_url
            key = api_key
        if not url:
            raise ValueError(
                "elasticsearch_url must be provided in config_provider, base_url or hosts parameter"
            )
        return url, key

    @staticmethod
    def _resolve_auth(username: str | None, password: str | None) -> tuple[str, str]:
        """Resolve Basic Auth credentials from args or environment."""
        import os

        _username = username or os.environ.get("ELASTIC_USERNAME", "elastic")
        if not password or password == _TEST_PLACEHOLDER:
            _password = os.environ.get(ENV_ELASTIC_PASSWORD, "")
        else:
            _password = password
        return _username, _password

    class _IndicesWrapper:
        """Minimal wrapper exposing indices.* helpers used by tests."""

        def __init__(self, client: "ElasticsearchClient") -> None:
            self._client = client

        def refresh(self, index: str) -> dict[str, Any]:
            """Refresh an index to make recent operations searchable.

            Args:
                index: Name of the Elasticsearch index to refresh.

            Returns:
                dict: The refresh API response.
            """
            return dict(self._client.post(f"/{index}/_refresh"))

        def get_mapping(self, index: str) -> dict[str, Any]:
            """Get the mapping definition for an index.

            Args:
                index: Name of the Elasticsearch index.

            Returns:
                dict: Mapping in the shape ``{index: {mappings: ...}}``.
            """
            mapping = self._client.get(f"/{index}/_mapping")
            # Return in the shape {index: {mappings: ...}}
            return {index: mapping} if mapping else {index: {"mappings": {}}}

        def create(self, index: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
            """Create an index with optional mapping.

            Args:
                index: Name of the Elasticsearch index to create.
                body: Optional body containing ``mappings`` key.

            Returns:
                dict: The create-index API response.
            """
            return self._client.create_index(index_name=index, mapping=(body or {}).get("mappings"))

        def delete(self, index: str) -> bool:
            """Delete an Elasticsearch index.

            Args:
                index: Name of the index to delete.

            Returns:
                bool: ``True`` if the index was deleted.
            """
            return self._client.delete_index(index)

    @property
    def indices(self) -> "ElasticsearchClient._IndicesWrapper":
        """Expose a minimal indices helper used by tests.

        Returns:
            ElasticsearchClient._IndicesWrapper: Wrapper exposing refresh, get_mapping,
            create, and delete helpers bound to this client.
        """
        return self._IndicesWrapper(self)

    def info(self) -> dict[str, Any]:
        """Return Elasticsearch cluster info (GET /).

        Returns:
            dict[str, Any]: Cluster info response from Elasticsearch.
        """
        return dict(self.get("/"))

    def create_index(
        self,
        index_name: str,
        mapping: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an Elasticsearch index with optional mapping and settings.

        Args:
            index_name: Name of the index to create.
            mapping: Optional mappings definition; defaults to a minimal
                mapping with ``alert_id`` and ``hash`` keyword fields.
            settings: Optional index settings dict.

        Returns:
            dict[str, Any]: Elasticsearch create-index response, or
            ``{"acknowledged": True, "index": index_name}`` if the index
            already exists.
        """
        if self.index_exists(index_name):
            return {"acknowledged": True, "index": index_name}
        body: dict[str, Any] = {}
        if settings:
            body["settings"] = settings
        if not mapping:
            mapping = {"properties": {"alert_id": {"type": "keyword"}, "hash": {"type": "keyword"}}}
        body["mappings"] = mapping
        return dict(self.put(f"/{index_name}", data=body))

    def index_exists(self, index_name: str) -> bool:
        """Return True if the index exists.

        Args:
            index_name: Name of the index to check.

        Returns:
            bool: True if the index exists (HTTP 200), False otherwise
            (including when a request error occurs).
        """
        try:
            resp = self._session.head(
                self._url(f"/{index_name}"),
                timeout=self.timeout,
            )
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("Index existence check failed for %s: %s", index_name, exc)
            return False

    def index_document(
        self,
        document: dict[str, Any],
        index: str | None = None,
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Index a document into Elasticsearch.

        Args:
            document: Document body to index.
            index: Target index (defaults to self.index).
            doc_id: Optional document ID; if omitted ES auto-generates one.
            refresh: Whether to refresh the index immediately.

        Returns:
            Elasticsearch index response.
        """
        idx = index or self.index
        path = f"/{idx}/_doc" if doc_id is None else f"/{idx}/_doc/{doc_id}"
        if refresh:
            path += "?refresh=true"
        logger.info("Indexing document into %s", idx)
        return dict(self.post(path, data=document))

    def search(
        self,
        query: dict[str, Any] | None = None,
        index: str | None = None,
        size: int = 10,
        sort: list[dict] | None = None,
        aggs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search query against an index.

        Args:
            query: Elasticsearch DSL query (defaults to match_all).
            index: Target index (defaults to self.index).
            size: Max hits to return.
            sort: Optional sort spec, e.g. [{"@timestamp": {"order": "desc"}}].
            aggs: Optional aggregations DSL.

        Returns:
            Full Elasticsearch search response dict.
        """
        idx = index or self.index
        body: dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
        if sort:
            body["sort"] = sort
        if aggs:
            body["aggs"] = aggs
        return dict(self.post(f"/{idx}/_search", data=body))

    def count(self, index: str | None = None) -> int:
        """Return total document count for an index.

        Args:
            index: Target index (defaults to self.index).

        Returns:
            Document count as int.
        """
        idx = index or self.index
        return int(self.get(f"/{idx}/_count").get("count", 0))

    def get_document(self, doc_id: str, index: str | None = None) -> dict[str, Any]:
        """Retrieve a document by ID.

        Args:
            doc_id: Document ID.
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch get response.
        """
        idx = index or self.index
        return dict(self.get(f"/{idx}/_doc/{doc_id}"))

    def delete_document(self, doc_id: str, index: str | None = None) -> dict[str, Any]:
        """Delete a document by ID.

        Args:
            doc_id: Document ID.
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch delete response.

        Raises:
            IntegrationError: If the delete request fails.
        """
        idx = index or self.index
        try:
            resp = self._session.delete(
                self._url(f"/{idx}/_doc/{doc_id}"),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as exc:
            from soar_lab.common.exceptions import IntegrationError

            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def delete_index(self, index: str | None = None) -> bool:
        """Delete an entire index.

        Args:
            index: Index name (defaults to self.index).

        Returns:
            True if deleted or not found, False on error.
        """
        idx = index or self.index
        try:
            resp = self._session.delete(
                self._url(f"/{idx}"),
                timeout=self.timeout,
            )
            return resp.ok or resp.status_code == 404
        except Exception as exc:
            logger.warning("Failed to delete index %s: %s", idx, exc)
            return False

    def update_document(
        self,
        doc_id: str,
        partial_doc: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        index: str | None = None,
        refresh: bool = False,
        retry_on_conflict: int = 10,
    ) -> dict[str, Any]:
        """Partially update a document using the _update API.

        Args:
            doc_id: Document ID.
            partial_doc: Dict with the fields to update (will be wrapped in {"doc": ...}).
            document: Alias for partial_doc, used by some tests.
            index: Target index (defaults to self.index).
            refresh: Whether to refresh the index immediately.
            retry_on_conflict: Number of retries on version conflict (409).

        Returns:
            Elasticsearch update response.
        """
        idx = index or self.index
        payload = partial_doc if partial_doc is not None else (document or {})
        params = ["retry_on_conflict=10"]
        if retry_on_conflict is not None:
            params = [f"retry_on_conflict={retry_on_conflict}"]
        if refresh:
            params.append("refresh=true")
        path = f"/{idx}/_update/{doc_id}?" + "&".join(params)
        return dict(self.post(path, data={"doc": payload}))

    def get_latest_documents(
        self,
        size: int = 10,
        index: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recently indexed documents.

        Args:
            size: Number of documents to return.
            index: Target index (defaults to self.index).

        Returns:
            List of ``_source`` dicts from the most recent hits.
        """
        # Note: alert_id is a text field, cannot sort. Return most recent by query order.
        result = self.search(
            size=size,
            index=index,
        )
        return [h.get("_source", {}) for h in result.get("hits", {}).get("hits", [])]

    def search_by_alert_id(self, alert_id: str, index: str | None = None) -> dict[str, Any] | None:
        """Search for a document by alert_id.

        Args:
            alert_id: The alert_id to search for.
            index: Target index (defaults to self.index).

        Returns:
            Document source dict if found, None otherwise.
        """
        idx = index or self.index
        # Try alert_id.keyword first (text field with keyword subfield),
        # then fall back to alert_id (native keyword field)
        for field in ("alert_id.keyword", "alert_id"):
            result = self.search(
                query={"term": {field: alert_id}},
                size=1,
                index=idx,
            )
            hits = result.get("hits", {}).get("hits", [])
            if hits:
                return dict(hits[0].get("_source", {}))
        return None

    def bulk_index(
        self,
        documents: list[dict[str, Any]],
        index: str | None = None,
        doc_id_field: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Index multiple documents using the _bulk API.

        Args:
            documents: List of document dicts to index.
            index: Target index (defaults to self.index).
            doc_id_field: If provided, use this field value as the _id for each doc.
            refresh: Whether to refresh the index immediately after bulk indexing.

        Returns:
            Elasticsearch bulk response.
        """
        idx = index or self.index
        body = build_bulk_body(documents, idx, doc_id_field)
        return execute_bulk(self._session, self.base_url, idx, body, refresh, self.timeout)

    def scroll_search(
        self,
        query: dict[str, Any] | None = None,
        index: str | None = None,
        size: int = 100,
        scroll: str = "1m",
    ) -> Any:
        """Simple generator that yields hits from a scroll search.

        Args:
            query: Elasticsearch DSL query (defaults to match_all).
            index: Target index (defaults to self.index).
            size: Number of hits per scroll batch.
            scroll: Scroll context keep-alive.

        Yields:
            Document ``_source`` dicts.
        """
        idx = index or self.index
        yield from scroll_search_generator(self.post, idx, query, size, scroll)

    def cluster_health(self) -> dict[str, Any]:
        """Return Elasticsearch cluster health.

        Returns:
            Cluster health dict with keys like status, number_of_nodes, etc.
        """
        return dict(self.get("/_cluster/health"))

    def health_check(self) -> bool:
        """Return True if Elasticsearch cluster is green or yellow.

        Returns:
            bool: True if cluster status is ``green`` or ``yellow``,
            False if the status is anything else or the health request
            raises an exception.
        """
        try:
            health = self.cluster_health()
            return health.get("status") in ("green", "yellow")
        except Exception as exc:
            logger.warning("Cluster health check failed: %s", exc)
            return False
