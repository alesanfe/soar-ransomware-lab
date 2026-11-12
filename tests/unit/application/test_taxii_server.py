"""INT-01: TaxiiLiteServer — TAXII-shaped surface over the STIX bundle."""

import uuid

import pytest

from soar_lab.application.use_cases.stix_export import STIX_NS, StixExportUseCase
from soar_lab.application.use_cases.taxii_server import (
    ALERTS_COLLECTION_ID,
    TaxiiLiteServer,
)

SHA = "ed01ebfbc9eb5bbea545af4d01bf5f107166184ded876d9e1168d6588e7dc4cb"
ALERTS = [
    {"alert_id": "AL-1", "data": {"hash": SHA, "source_ip": "185.220.101.4"}},
    {"alert_id": "AL-2", "data": {}},
]


def _server(alerts=ALERTS):
    return TaxiiLiteServer(StixExportUseCase(alerts_provider=lambda: alerts))


class TestDiscovery:
    def test_discovery_shape(self):
        d = _server().discovery()
        assert d["default"].endswith("/api/")
        assert d["api_roots"] == [d["default"]]
        assert "lite" in d["title"].lower()

    def test_api_root_versions(self):
        root = _server().api_root()
        assert root["versions"] == ["taxii-2.1"]
        assert root["max_content_length"] > 0


class TestCollections:
    def test_collection_id_is_deterministic_uuid5(self):
        assert ALERTS_COLLECTION_ID == str(uuid.uuid5(STIX_NS, "taxii-collection:lab-alerts"))
        uuid.UUID(ALERTS_COLLECTION_ID)  # parses as a UUID

    def test_collections_list_single_readonly(self):
        cols = _server().collections()["collections"]
        assert len(cols) == 1
        c = cols[0]
        assert c["id"] == ALERTS_COLLECTION_ID
        assert c["can_read"] is True
        assert c["can_write"] is False
        assert "application/taxii+json;version=2.1" in c["media_types"]

    def test_collection_meta_known_id(self):
        meta = _server().collection(ALERTS_COLLECTION_ID)
        assert meta is not None and meta["id"] == ALERTS_COLLECTION_ID

    def test_collection_meta_unknown_id(self):
        assert _server().collection("nope") is None


class TestObjects:
    def test_objects_envelope_contains_stix(self):
        env = _server().objects(ALERTS_COLLECTION_ID)
        assert env is not None
        types = {o["type"] for o in env["objects"]}
        assert {"identity", "indicator", "grouping"} <= types
        assert env["more"] is False

    def test_objects_unknown_collection(self):
        assert _server().objects("unknown") is None

    def test_objects_match_type_filter(self):
        env = _server().objects(ALERTS_COLLECTION_ID, match_type="indicator")
        assert {o["type"] for o in env["objects"]} == {"indicator"}

    def test_objects_limit_sets_more_flag(self):
        # ``limit`` bounds ALERTS exported, not objects — 3 alerts produce
        # 1 identity + 1 marking-definition + 3 indicators + 3 groupings
        # = 8 objects, and the remaining 2 alerts make the envelope
        # report ``more``.
        alerts = [{"alert_id": f"AL-{i}", "data": {"hash": SHA}} for i in range(5)]
        env = _server(alerts).objects(ALERTS_COLLECTION_ID, limit=3)
        assert env is not None
        assert env["more"] is True
        assert len(env["objects"]) == 8

    def test_objects_no_truncation_more_false(self):
        env = _server(ALERTS).objects(ALERTS_COLLECTION_ID, limit=100)
        assert env is not None and env["more"] is False


class TestGuards:
    def test_none_stix_rejected(self):
        with pytest.raises(ValueError):
            TaxiiLiteServer(None)  # type: ignore[arg-type]
