"""Shared OpenSearch query builders.

Small helpers for query shapes that must stay consistent across callers —
placed in ``common`` so application and infrastructure layers can both use
them without violating the hexagonal import contracts.
"""

from __future__ import annotations

from typing import Any


def id_terms_filter(field: str, values: list[str]) -> dict[str, Any]:
    """Exact-ID filter tolerant to either ``keyword`` or ``text``+``.keyword``
    mappings.

    Shuffle's ``workflowexecution`` indices sometimes map identifier fields
    dynamically as ``text`` (with a ``.keyword`` sub-field) depending on how
    the first index was created; ``terms`` on a text field never matches.
    Querying both variants keeps exact-ID lookups working either way.
    """
    return {
        "bool": {
            "should": [
                {"terms": {field: values}},
                {"terms": {f"{field}.keyword": values}},
            ],
            "minimum_should_match": 1,
        }
    }
