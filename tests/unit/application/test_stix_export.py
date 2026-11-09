"""F6: StixExportUseCase — STIX 2.1 bundle from alert corpus."""

from soar_lab.application.use_cases.stix_export import StixExportUseCase

SHA = "ed01ebfbc9eb5bbea545af4d01bf5f107166184ded876d9e1168d6588e7dc4cb"
ALERTS = [
    {
        "alert_id": "AL-1",
        "data": {"hash": SHA, "source_ip": "185.220.101.4", "domain": "c2.example.com"},
    },
    {"alert_id": "AL-2", "data": {}},  # no IoCs → skipped
    {"alert_id": "AL-3", "hash": SHA},  # same IoC different alert → own indicator
]


def _uc(alerts=ALERTS):
    return StixExportUseCase(alerts_provider=lambda: alerts)


class TestBundle:
    def test_bundle_structure(self):
        b = _uc().build_bundle()
        assert b["type"] == "bundle"
        assert b["id"].startswith("bundle--")
        types = {o["type"] for o in b["objects"]}
        assert {"identity", "indicator", "grouping"} <= types

    def test_indicator_patterns(self):
        b = _uc().build_bundle()
        patterns = {o["pattern"] for o in b["objects"] if o["type"] == "indicator"}
        assert any("SHA-256" in p for p in patterns)
        assert any("ipv4-addr" in p for p in patterns)
        assert any("domain-name" in p for p in patterns)

    def test_alert_without_iocs_no_grouping(self):
        b = _uc().build_bundle()
        groupings = [o for o in b["objects"] if o["type"] == "grouping"]
        names = {g["name"] for g in groupings}
        assert "Lab incident AL-2" not in names

    def test_deterministic_ids(self):
        ids_a = {o["id"] for o in _uc().build_bundle()["objects"]}
        ids_b = {o["id"] for o in _uc().build_bundle()["objects"]}
        assert ids_a == ids_b

    def test_limit(self):
        b = _uc().build_bundle(limit=1)
        assert "Lab incident AL-3" not in {o.get("name") for o in b["objects"]}

    def test_requires_provider(self):
        import pytest

        with pytest.raises(ValueError):
            StixExportUseCase(None)
