"""Helper functions for Elasticsearch bulk and scroll operations.

Extracted from ``client.py`` to improve maintainability by separating
the bulk-indexing and scroll-search logic from the main client class.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from soar_lab.common.constants import CONTENT_TYPE_NDJSON, HEADER_CONTENT_TYPE

if TYPE_CHECKING:
    from requests import Session


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
    session: Session,
    url: str,
    index: str,
    body: str,
    refresh: bool = False,
    timeout: int = 10,
) -> dict[str, Any]:
    """Send a bulk request to Elasticsearch.

    Args:
        session: requests.Session to use.
        url: Base URL of the Elasticsearch cluster.
        index: Target index name.
        body: NDJSON body from ``build_bulk_body``.
        refresh: Whether to refresh the index immediately.
        timeout: Request timeout in seconds.

    Returns:
        Elasticsearch bulk response dict.

    Raises:
        IntegrationError: If the bulk request fails.
    """
    path = f"/{index}/_bulk"
    if refresh:
        path += "?refresh=true"
    try:
        resp = session.post(
            f"{url}{path}",
            data=body,
            headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_NDJSON},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except Exception as exc:
        from soar_lab.common.exceptions import IntegrationError

        raise IntegrationError("ElasticsearchClient", str(exc)) from exc


def scroll_search_generator(
    post_fn: Any,
    index: str,
    query: dict[str, Any] | None = None,
    size: int = 100,
    scroll: str = "1m",
) -> Any:
    """Generator that yields hits from a scroll search.

    Args:
        post_fn: Callable that performs POST requests (e.g. ``client.post``).
        index: Target index name.
        query: Elasticsearch DSL query (defaults to ``match_all``).
        size: Number of hits per scroll batch.
        scroll: Scroll context keep-alive.

    Yields:
        Document ``_source`` dicts.
    """
    body: dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
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
