"""INT-01: TAXII-lite read-only routes over the STIX 2.1 export.

Mounted under ``/api/v1/taxii2`` so the nginx ``/api/v1/`` passthrough
reaches them unmodified. All endpoints require API auth (TAXII servers
are authenticated services); the TAXII media type is reported on the
objects envelope so clients can negotiate it.

Scope boundary — this is a TAXII-*lite* surface, not a full server:
one static read-only collection, no manifest/status resources, no
object versioning. See ``docs/adr/0011-taxii-lite-scope.md``.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from soar_lab.application.use_cases.stix_export import StixExportUseCase
from soar_lab.application.use_cases.taxii_server import TaxiiLiteServer
from soar_lab.config.logging import get_logger

from .auth import require_api_auth

__all__ = ["register_taxii_routes"]

logger = get_logger(__name__)

_AUTH = Depends(require_api_auth)
_BASE = "/api/v1/taxii2"
_TAXII_MEDIA = "application/taxii+json;version=2.1"


def _server(app_instance: FastAPI) -> TaxiiLiteServer:
    repository = getattr(app_instance.state, "alert_repository", None)
    if repository is None or not hasattr(repository, "get_alerts"):
        raise HTTPException(status_code=503, detail="Alert repository unavailable")
    return TaxiiLiteServer(StixExportUseCase(alerts_provider=repository.get_alerts))


def register_taxii_routes(app_instance: FastAPI) -> None:
    """Register the TAXII-lite surface (INT-01)."""

    @app_instance.get(
        _BASE + "/",
        dependencies=[_AUTH],
        tags=["taxii"],
        summary="TAXII-lite discovery",
    )
    async def taxii_discovery() -> dict[str, Any]:
        return _server(app_instance).discovery()

    @app_instance.get(
        _BASE + "/api/",
        dependencies=[_AUTH],
        tags=["taxii"],
        summary="TAXII-lite API root",
    )
    async def taxii_api_root() -> dict[str, Any]:
        return _server(app_instance).api_root()

    @app_instance.get(
        _BASE + "/api/collections/",
        dependencies=[_AUTH],
        tags=["taxii"],
        summary="List TAXII collections",
    )
    async def taxii_collections() -> dict[str, Any]:
        return _server(app_instance).collections()

    @app_instance.get(
        _BASE + "/api/collections/{collection_id}/",
        dependencies=[_AUTH],
        tags=["taxii"],
        summary="Collection metadata",
    )
    async def taxii_collection(collection_id: str) -> dict[str, Any]:
        meta = _server(app_instance).collection(collection_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return meta

    @app_instance.get(
        _BASE + "/api/collections/{collection_id}/objects/",
        dependencies=[_AUTH],
        tags=["taxii"],
        summary="STIX objects envelope (TAXII media type)",
    )
    async def taxii_objects(
        collection_id: str,
        limit: int = 1000,
        match_type: str | None = None,
    ) -> Any:
        try:
            envelope = _server(app_instance).objects(
                collection_id, limit=limit, match_type=match_type
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error building TAXII objects envelope")
            raise HTTPException(status_code=500, detail="Failed to build objects") from e
        if envelope is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return JSONResponse(envelope, media_type=_TAXII_MEDIA)
