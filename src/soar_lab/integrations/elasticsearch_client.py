#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Elasticsearch Client
Dedicated client for Elasticsearch (soar-alerts index).
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)

DEFAULT_INDEX = "soar-alerts"


class ElasticsearchClient(BaseHTTPClient):
    """Client for Elasticsearch REST API with optional Basic Auth."""

    def __init__(
            self,
            base_url: str,
            api_key: Optional[str] = None,
            config_provider: Optional[object] = None,
            index: str = DEFAULT_INDEX,
            username: Optional[str] = None,
            password: Optional[str] = None,
    ) -> None:
        import os
        if config_provider:
            url = base_url or config_provider.get('elasticsearch_url')
            key = api_key or config_provider.get('elasticsearch_api_key')
        else:
            url = base_url
            key = api_key

        if not url:
            raise ValueError(
                "elasticsearch_url must be provided in config_provider or as base_url parameter"
            )

        # Resolve Basic Auth credentials: explicit args > env vars
        _username = username or os.environ.get('ELASTIC_USERNAME', 'elastic')
        _password = password or os.environ.get('ELASTIC_PASSWORD', '')

        super().__init__(base_url=url, api_key=key)
        self.index = index

        # Apply Basic Auth if credentials are available
        if _username and _password:
            self._session.auth = (_username, _password)

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
    ) -> Dict[str, Any]:
        """Run a search query against an index.

        Args:
            query: Elasticsearch DSL query (defaults to match_all).
            index: Target index (defaults to self.index).
            size: Max hits to return.
            sort: Optional sort spec, e.g. [{"@timestamp": {"order": "desc"}}].

        Returns:
            Full Elasticsearch search response dict.
        """
        idx = index or self.index
        body: Dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
        if sort:
            body["sort"] = sort
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
            from soar_lab.exceptions import IntegrationError
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
            partial_doc: Dict[str, Any],
            index: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Partially update a document using the _update API.

        Args:
            doc_id: Document ID.
            partial_doc: Dict with the fields to update (will be wrapped in {"doc": ...}).
            index: Target index (defaults to self.index).

        Returns:
            Elasticsearch update response.
        """
        idx = index or self.index
        return self.post(f"/{idx}/_update/{doc_id}", data={"doc": partial_doc})

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
            query={"match": {"alert_id": alert_id}},
            size=1,
            index=idx,
        )
        hits = result.get("hits", {}).get("hits", [])
        if hits:
            return hits[0].get("_source", {})
        return None

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
