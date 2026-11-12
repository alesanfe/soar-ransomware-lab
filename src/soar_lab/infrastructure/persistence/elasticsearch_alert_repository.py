"""Elasticsearch-backed read repository for SOAR alerts.

The admission pipeline writes alert documents to the ``soar-alerts``
Elasticsearch index (via the Shuffle workflow), while the SQLite
``alerts`` table has no write callers — it stays empty.  Analytics and
TAXII routes therefore read an empty store and reported zero coverage /
404s although the real corpus lived in ES.

This adapter fixes the divergence on the read path: it inherits the
SQLite repository (cases, backups, test-coverage and all write methods
are delegated unchanged) but serves ``get_alert``/``get_alerts``/
``count_alerts`` from ``soar-alerts``.  Every ES call falls back to the
SQLite implementation on transport errors, so analytics keep working on
local data if the search node is down.
"""

import logging
import os
from typing import Any

import requests

from soar_lab.common.constants import DEFAULT_ELASTICSEARCH_URL
from soar_lab.infrastructure.persistence.sqlite_alert_repository import (
    DEFAULT_ALERT_QUERY_LIMIT,
    SqliteAlertRepository,
)
from soar_lab.security.tls_config import ca_verify

logger = logging.getLogger(__name__)

_ALERTS_INDEX = "soar-alerts"
_TIMEOUT = 10


class ElasticsearchAlertRepository(SqliteAlertRepository):
    """Alert reads served from the ``soar-alerts`` ES index.

    Args:
        db_path/config_provider/path_service: forwarded to
            :class:`SqliteAlertRepository` (still required: cases,
            backups and coverage tables live in SQLite).
    """

    def __init__(self, config_provider=None, *args, **kwargs) -> None:
        super().__init__(config_provider=config_provider, *args, **kwargs)
        get = config_provider.get if config_provider else os.getenv
        self._es_url = str(
            get("ES_URL", None)
            or get("ELASTICSEARCH_URL", None)
            or os.getenv("ES_URL", os.getenv("ELASTICSEARCH_URL", ""))
            or DEFAULT_ELASTICSEARCH_URL
        ).rstrip("/")
        self._es_auth = (
            "elastic",
            str(get("ELASTIC_PASSWORD", None) or os.getenv("ELASTIC_PASSWORD", "")),
        )
        self._es_verify = ca_verify()

    # -- internal helpers ------------------------------------------------

    def _doc_to_row(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Map an ES source document to the SQLite row shape routes expect."""
        return {
            "id": doc.get("alert_id"),
            "alert_id": doc.get("alert_id"),
            "alert_type": doc.get("alert_type"),
            "severity": doc.get("severity"),
            "hostname": doc.get("hostname"),
            "timestamp": doc.get("timestamp") or doc.get("@timestamp"),
            "data": doc,
            "status": doc.get("status"),
        }

    def _search(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        r = requests.post(
            f"{self._es_url}/{_ALERTS_INDEX}/_search",
            auth=self._es_auth,
            verify=self._es_verify,
            json=body,
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return [h.get("_source", {}) for h in r.json().get("hits", {}).get("hits", [])]

    # -- alert reads ------------------------------------------------------

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        try:
            docs = self._search(
                {
                    "size": 1,
                    "query": {"term": {"alert_id.keyword": alert_id}},
                }
            )
            return self._doc_to_row(docs[0]) if docs else None
        except Exception as exc:
            logger.warning("ES get_alert failed, falling back to SQLite: %s", exc)
            return super().get_alert(alert_id)

    def get_alerts(
        self, limit: int = DEFAULT_ALERT_QUERY_LIMIT, severity: str = None
    ) -> list[dict[str, Any]]:
        limit = max(0, limit)
        query: dict[str, Any] = {"match_all": {}}
        if severity is not None:
            # soar-alerts stores severity as long; non-numeric filters
            # cannot match and return empty rather than raising.
            try:
                query = {"term": {"severity": int(float(severity))}}
            except (TypeError, ValueError):
                return []
        try:
            docs = self._search(
                {
                    "size": limit,
                    "query": query,
                    "sort": [{"@timestamp": {"order": "desc", "unmapped_type": "date"}}],
                }
            )
            return [self._doc_to_row(d) for d in docs]
        except Exception as exc:
            logger.warning("ES get_alerts failed, falling back to SQLite: %s", exc)
            return super().get_alerts(limit=limit, severity=severity)

    def count_alerts(self) -> int:
        try:
            r = requests.get(
                f"{self._es_url}/{_ALERTS_INDEX}/_count",
                auth=self._es_auth,
                verify=self._es_verify,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            return int(r.json().get("count", 0))
        except Exception as exc:
            logger.warning("ES count_alerts failed, falling back to SQLite: %s", exc)
            return super().count_alerts()
