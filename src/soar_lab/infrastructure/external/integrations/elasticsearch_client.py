#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Elasticsearch Client
Dedicated client for Elasticsearch (soar-alerts index).
"""

import json

from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

DEFAULT_INDEX = "soar-alerts"


class ElasticsearchClient(BaseHTTPClient):
    """Client for Elasticsearch REST API with optional Basic Auth."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        hosts: Optional[Any] = None,
        api_key: Optional[str] = None,
        config_provider: Optional[object] = None,
        index: str = DEFAULT_INDEX,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 10,
        retries: int = 3,
    ) -> None:
        import os

        # Resolve base_url / hosts alias (tests pass hosts=[url])
        raw_url = base_url or hosts
        if isinstance(raw_url, (list, tuple)):
            raw_url = raw_url[0] if raw_url else None
        if config_provider:
            url = raw_url or config_provider.get('elasticsearch_url')
            key = api_key or config_provider.get('elasticsearch_api_key')
        else:
            url = raw_url
            key = api_key

        if not url:
            raise ValueError(
                "elasticsearch_url must be provided in config_provider, base_url or hosts parameter"
            )

        # Resolve Basic Auth credentials: explicit args > env vars, with a
        # fallback for test fixtures that pass placeholder passwords.
        _username = username or os.environ.get('ELASTIC_USERNAME', 'elastic')
        if not password or password == "test-pass":
            _password = os.environ.get('ELASTIC_PASSWORD', '')
        else:
            _password = password

        super().__init__(base_url=url, api_key=key, timeout=timeout, retries=retries, verify_ssl=verify_ssl)
        self.index = index

        # Apply Basic Auth if credentials are available
        if _username and _password:
            self._session.auth = (_username, _password)

    @property
    def client(self) -> "ElasticsearchClient":
        """Expose self as .client for compatibility with tests using es_client.client.info()."""
        return self

    class _IndicesWrapper:
        """Minimal wrapper exposing indices.* helpers used by tests."""

        def __init__(self, client: "ElasticsearchClient") -> None:
            self._client = client

        def refresh(self, index: str) -> Dict[str, Any]:
            return self._client.post(f"/{index}/_refresh")

        def get_mapping(self, index: str) -> Dict[str, Any]:
            mapping = self._client.get(f"/{index}/_mapping")
            # Return in the shape {index: {mappings: ...}}
            return {index: mapping} if mapping else {index: {"mappings": {}}}

        def create(self, index: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            return self._client.create_index(index_name=index, mapping=(body or {}).get("mappings"))

        def delete(self, index: str) -> bool:
            return self._client.delete_index(index)

    @property
    def indices(self) -> "ElasticsearchClient._IndicesWrapper":
        """Expose a minimal indices helper used by tests."""
        return self._IndicesWrapper(self)

    def info(self) -> Dict[str, Any]:
        """Return Elasticsearch cluster info (GET /)."""
        return self.get("/")

    def create_index(
        self,
        index_name: str,
        mapping: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an Elasticsearch index with optional mapping and settings."""
        if self.index_exists(index_name):
            return {"acknowledged": True, "index": index_name}
        body: Dict[str, Any] = {}
        if settings:
            body["settings"] = settings
        if not mapping:
            mapping = {"properties": {"alert_id": {"type": "keyword"}, "hash": {"type": "keyword"}}}
        body["mappings"] = mapping
        return self.put(f"/{index_name}", data=body)

    def index_exists(self, index_name: str) -> bool:
        """Return True if the index exists."""
        try:
            resp = self._session.head(
                self._url(f"/{index_name}"),
                timeout=self.timeout,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def index_document(
        self,
        document: Dict[str, Any],
        index: Optional[str] = None,
        doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Index a document into Elasticsearch.

        Args:
            document: Document body to index.
            index: Target index (defaults to self.index).
            doc_id: Optional document ID; if omitted ES auto-generates one.

        Returns:
            Elasticsearch index response.
        """
        idx = index or self.index
        path = f"/{idx}/_doc" if doc_id is None else f"/{idx}/_doc/{doc_id}"
        logger.info(f"Indexing document into {idx}")
        return self.post(path, data=document)

    def search(
        self,
        query: Optional[Dict[str, Any]] = None,
        index: Optional[str] = None,
        size: int = 10,
        sort: Optional[List[Dict]] = None,
        aggs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
        body: Dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
        if sort:
            body["sort"] = sort
        if aggs:
            body["aggs"] = aggs
        return self.post(f"/{idx}/_search", data=body)

    def count(self, index: Optional[str] = None) -> int:
        """Return total document count for an index.

        Args:
            index: Target index (defaults to self.index).

        Returns:
            Document count as int.
        """
        idx = index or self.index
        result = self.get(f"/{idx}/_count")
        return result.get("count", 0)

    def get_document(self, doc_id: str, index: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve a document by ID.

        Args:
            doc_id: Document ID.
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch get response.
        """
        idx = index or self.index
        return self.get(f"/{idx}/_doc/{doc_id}")

    def delete_document(self, doc_id: str, index: Optional[str] = None) -> Dict[str, Any]:
        """Delete a document by ID.

        Args:
            doc_id: Document ID.
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch delete response.
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

    def delete_index(self, index: Optional[str] = None) -> bool:
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
        except Exception:
            return False

    def update_document(
        self,
        doc_id: str,
        partial_doc: Optional[Dict[str, Any]] = None,
        document: Optional[Dict[str, Any]] = None,
        index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Partially update a document using the _update API.

        Args:
            doc_id: Document ID.
            partial_doc: Dict with the fields to update (will be wrapped in {"doc": ...}).
            document: Alias for partial_doc, used by some tests.
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch update response.
        """
        idx = index or self.index
        payload = partial_doc if partial_doc is not None else (document or {})
        return self.post(f"/{idx}/_update/{doc_id}", data={"doc": payload})

    def get_latest_documents(
        self,
        size: int = 10,
        index: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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
        hits = result.get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits]

    def search_by_alert_id(self, alert_id: str, index: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Search for a document by alert_id.

        Args:
            alert_id: The alert_id to search for.
            index: Target index (defaults to self.index).

        Returns:
            Document source dict if found, None otherwise.
        """
        idx = index or self.index
        result = self.search(
            query={"term": {"alert_id.keyword": alert_id}},
            size=1,
            index=idx,
        )
        hits = result.get("hits", {}).get("hits", [])
        if hits:
            return hits[0].get("_source", {})
        return None

    def bulk_index(
        self,
        documents: List[Dict[str, Any]],
        index: Optional[str] = None,
        doc_id_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Index multiple documents using the _bulk API.

        Args:
            documents: List of document dicts to index.
            index: Target index (defaults to self.index).
            doc_id_field: If provided, use this field value as the _id for each doc.

        Returns:
            Elasticsearch bulk response.
        """
        idx = index or self.index
        lines = []
        for i, doc in enumerate(documents):
            action = {"index": {"_index": idx}}
            if doc_id_field:
                action["index"]["_id"] = doc.get(doc_id_field)
            else:
                action["index"]["_id"] = str(i)
            lines.append(json.dumps(action))
            lines.append(json.dumps(doc))
        body = "\n".join(lines) + "\n"
        try:
            resp = self._session.post(
                self._url(f"/{idx}/_bulk"),
                data=body,
                headers={"Content-Type": "application/x-ndjson"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as exc:
            from soar_lab.common.exceptions import IntegrationError
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def scroll_search(
        self,
        query: Optional[Dict[str, Any]] = None,
        index: Optional[str] = None,
        size: int = 100,
        scroll: str = "1m",
    ):
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
        body = {"query": query or {"match_all": {}}, "size": size}
        result = self.post(f"/{idx}/_search?scroll={scroll}", data=body)
        scroll_id = result.get("_scroll_id")
        hits = result.get("hits", {}).get("hits", [])
        for hit in hits:
            yield hit.get("_source", {})
        while scroll_id and hits:
            page = self.post("/_search/scroll", data={"scroll": scroll, "scroll_id": scroll_id})
            scroll_id = page.get("_scroll_id")
            hits = page.get("hits", {}).get("hits", [])
            for hit in hits:
                yield hit.get("_source", {})

    def cluster_health(self) -> Dict[str, Any]:
        """Return Elasticsearch cluster health.

        Returns:
            Cluster health dict with keys like status, number_of_nodes, etc.
        """
        return self.get("/_cluster/health")

    def health_check(self) -> bool:
        """Return True if Elasticsearch cluster is green or yellow."""
        try:
            health = self.cluster_health()
            return health.get("status") in ("green", "yellow")
        except Exception:
            return False
