"""TAXII-lite read-only server surface (INT-01).

Exposes the lab's STIX 2.1 bundle through a minimal TAXII 2.1-shaped
API so real TAXII clients (and MISP's TAXII pull) can discover and
fetch the lab's indicators:

- ``GET <root>/``                    — server discovery
- ``GET <root>/api/``               — API root information
- ``GET <root>/api/collections/``   — collection list
- ``GET <root>/api/collections/{id}/``         — collection metadata
- ``GET <root>/api/collections/{id}/objects/`` — STIX objects envelope
- ``GET <root>/api/collections/{id}/manifest/``— object manifest

This is deliberately **not** a full TAXII 2.x server: there is a
single read-only collection backed by :class:`StixExportUseCase`, no
``status`` resource and no write path (both only apply to writable
collections per the spec), no object-level version history, and
pagination is a plain ``limit`` bound rather than envelope paging.
The honest boundary is documented in ``docs/adr/0011-taxii-lite-scope.md``.
"""

from __future__ import annotations

import uuid
from typing import Any

from .stix_export import STIX_NS, StixExportUseCase

__all__ = ["TaxiiLiteServer", "ALERTS_COLLECTION_ID"]

ALERTS_COLLECTION_ID = str(uuid.uuid5(STIX_NS, "taxii-collection:lab-alerts"))

_TAXII_VERSION = "taxii-2.1"
_MEDIA_TYPE = "application/taxii+json;version=2.1"
_STIX_MEDIA_TYPE = "application/stix+json;version=2.1"


class TaxiiLiteServer:
    """Minimal read-only TAXII 2.1-shaped surface over the STIX bundle."""

    def __init__(self, stix: StixExportUseCase, base_url: str = "/api/v1/taxii2") -> None:
        if stix is None:
            raise ValueError("stix use case is required for TaxiiLiteServer")
        self._stix = stix
        self._base = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Discovery / API root
    # ------------------------------------------------------------------

    def discovery(self) -> dict[str, Any]:
        """TAXII 2.1 ``GET /taxii2/`` discovery response."""
        return {
            "title": "SOAR Lab TAXII-lite",
            "description": (
                "Read-only TAXII-lite surface exposing the lab's STIX 2.1 "
                "IoC bundle. Not a full TAXII 2.x server — single static "
                "collection, no manifest/status resources."
            ),
            "default": f"{self._base}/api/",
            "api_roots": [f"{self._base}/api/"],
        }

    def api_root(self) -> dict[str, Any]:
        """TAXII 2.1 API root resource."""
        return {
            "title": "SOAR Lab IoCs",
            "description": "Lab alert IoCs (SHA-256, IPv4, domain) as STIX indicators.",
            "versions": [_TAXII_VERSION],
            "max_content_length": 10_485_760,
        }

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def collections(self) -> dict[str, Any]:
        return {"collections": [self._collection_meta()]}

    def collection(self, collection_id: str) -> dict[str, Any] | None:
        if collection_id != ALERTS_COLLECTION_ID:
            return None
        return self._collection_meta()

    def objects(
        self,
        collection_id: str,
        *,
        limit: int = 1000,
        match_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Return the STIX objects envelope for the collection.

        ``None`` when the collection does not exist. The envelope uses
        the TAXII ``more`` flag honestly: it is only true when the
        bounded bundle was truncated.
        """
        if collection_id != ALERTS_COLLECTION_ID:
            return None
        bounded = max(1, min(limit, 10_000))
        bundle = self._stix.build_bundle(limit=bounded)
        objects = list(bundle.get("objects") or [])
        # Exact truncation probe: if ``bounded + 1`` alerts yield more
        # objects than ``bounded`` did, the corpus was truncated.
        probe = self._stix.build_bundle(limit=bounded + 1)
        more = len(probe.get("objects") or []) > len(objects)
        if match_type:
            objects = [o for o in objects if o.get("type") == match_type]
        return {
            "more": more,
            "objects": objects,
        }

    def manifest(
        self,
        collection_id: str,
        *,
        limit: int = 1000,
    ) -> dict[str, Any] | None:
        """TAXII 2.1 manifest resource — one entry per object.

        Each entry carries ``id``, ``date_added`` (mapped from the STIX
        ``created`` timestamp), ``version`` and ``media_type``, matching
        the manifest record shape the spec defines.
        """
        if collection_id != ALERTS_COLLECTION_ID:
            return None
        bounded = max(1, min(limit, 10_000))
        bundle = self._stix.build_bundle(limit=bounded)
        objects = list(bundle.get("objects") or [])
        entries = [
            {
                "id": o.get("id"),
                "date_added": o.get("created") or o.get("modified"),
                "version": o.get("modified") or o.get("created"),
                "media_type": _STIX_MEDIA_TYPE,
            }
            for o in objects
            if isinstance(o, dict) and o.get("id")
        ]
        return {"more": False, "objects": entries}

    # ------------------------------------------------------------------

    def _collection_meta(self) -> dict[str, Any]:
        return {
            "id": ALERTS_COLLECTION_ID,
            "title": "lab-alerts",
            "description": "Indicators and groupings derived from lab alerts.",
            "can_read": True,
            "can_write": False,
            "media_types": [_MEDIA_TYPE],
        }
