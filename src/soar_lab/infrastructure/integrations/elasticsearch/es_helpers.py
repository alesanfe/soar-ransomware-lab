"""Helper functions for Elasticsearch bulk and scroll operations.

Extracted from ``client.py`` to improve maintainability by separating
the bulk-indexing and scroll-search logic from the main client class.
"""

from __future__ import annotations

import json
from typing import Any

from soar_lab.common.constants import CONTENT_TYPE_NDJSON
from soar_lab.common.exceptions import IntegrationError
from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


def build_bulk_body(
    documents: list[dict[str, Any]],
    index: str,
    doc_id_field: str | None = None,
) -> str:
    """Build the NDJSON body for an Elasticsearch ``_bulk`` request.

    Args:
        documents: List of document dicts to index.
        index: Target index name.
        doc_id_field: If provided, use this field value as the ``_id``
            for each document. Otherwise use the enumerate index.

    Returns:
        NDJSON string suitable for the ``_bulk`` endpoint.
    """
    lines: list[str] = []
    for i, doc in enumerate(documents):
        action: dict[str, Any] = {"index": {"_index": index}}
        if doc_id_field:
            action["index"]["_id"] = str(doc.get(doc_id_field, ""))
        else:
            action["index"]["_id"] = str(i)
        lines.extend((json.dumps(action), json.dumps(doc)))
    return "\n".join(lines) + "\n"


def execute_bulk(
    post_fn: Any,
    index: str,
    body: str,
    refresh: bool = False,
) -> dict[str, Any]:
    """Send a bulk request to Elasticsearch.

    Args:
        post_fn: Callable ``(path, body, content_type) -> dict`` performing
            the POST — in practice ``ElasticsearchClient.post_raw`` so the
            request goes through the circuit breaker, typed error
            translation and trace propagation (BL-HTTP-007).
        index: Target index name.
        body: NDJSON body from ``build_bulk_body``.
        refresh: Whether to refresh the index immediately.

    Returns:
        Elasticsearch bulk response dict.

    Raises:
        IntegrationError: If the bulk request fails (transport errors keep
            the typed hierarchy from ``_translate_error``).
    """
    path = f"/{index}/_bulk"
    if refresh:
        path += "?refresh=true"
    result = post_fn(path, body, CONTENT_TYPE_NDJSON)
    result = result or {}
    # ES returns HTTP 200 even when individual documents fail —
    # ``errors: true`` with per-item status/reason. Treating that as
    # success hides partial data loss, so surface it as an error
    # with the failed ids (truncated, no doc bodies).
    if result.get("errors"):
        failed = [
            item.get("index", {})
            for item in result.get("items", [])
            if item.get("index", {}).get("error")
        ]
        detail = "; ".join(
            f"{f.get('_id', '?')}: {f.get('error', {}).get('type', 'unknown')}" for f in failed[:10]
        )

        raise IntegrationError(
            "ElasticsearchClient",
            f"bulk partial failure ({len(failed)} doc(s)): {detail}",
        )
    return result


def scroll_search_generator(
    post_fn: Any,
    index: str,
    query: dict[str, Any] | None = None,
    size: int = 100,
    scroll: str = "1m",
    delete_fn: Any = None,
) -> Any:
    """Generator that yields hits from a scroll search.

    The server-side scroll context is released in a ``finally`` block via
    ``DELETE /_search/scroll`` — on exhaustion, on iteration errors and on
    early termination (``GeneratorExit`` from ``gen.close()`` or GC), so
    partially-consumed scrolls cannot leak contexts in Elasticsearch.

    Args:
        post_fn: Callable that performs POST requests (e.g. ``client.post``).
        index: Target index name.
        query: Elasticsearch DSL query (defaults to ``match_all``).
        size: Number of hits per scroll batch.
        scroll: Scroll context keep-alive.
        delete_fn: Optional callable performing DELETE requests
            (e.g. ``client.delete``). When provided, used to clear the
            scroll context. When ``None``, cleanup is skipped (the
            keep-alive still bounds server-side lifetime).

    Yields:
        Document ``_source`` dicts.
    """
    body: dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
    scroll_id: Any = None
    try:
        result = post_fn(f"/{index}/_search?scroll={scroll}", data=body)
        scroll_id = result.get("_scroll_id")
        hits = result.get("hits", {}).get("hits", [])
        for hit in hits:
            yield hit.get("_source", {})
        while scroll_id and hits:
            page = post_fn("/_search/scroll", data={"scroll": scroll, "scroll_id": scroll_id})
            scroll_id = page.get("_scroll_id")
            hits = page.get("hits", {}).get("hits", [])
            for hit in hits:
                yield hit.get("_source", {})
    finally:
        if scroll_id and delete_fn is not None:
            try:
                delete_fn("/_search/scroll", json={"scroll_id": scroll_id})
            except Exception as exc:  # best-effort cleanup; keep-alive bounds lifetime
                logger.warning(f"Failed to clear scroll context: {exc}")
