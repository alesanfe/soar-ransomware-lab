#!/usr/bin/env python3
"""Unit tests for soar_lab.domain.alert_generator."""

import re

import pytest

from soar_lab.domain.alert_generator import AlertGenerator


@pytest.mark.unit
class TestAlertGenerator:
    @pytest.fixture
    def generator(self):
        return AlertGenerator()

    def test_generate_malicious_returns_dict(self, generator):
        alert = generator.generate_malicious()
        assert isinstance(alert, dict)

    def test_generate_benign_returns_dict(self, generator):
        alert = generator.generate_benign()
        assert isinstance(alert, dict)

    def test_alert_has_required_fields(self, generator):
        required = ["alert_id", "hostname", "src_ip", "hash", "severity", "timestamp", "event_type"]
        alert = generator.generate_malicious()
        for field in required:
            assert field in alert, f"Missing field: {field}"

    def test_alert_id_format(self, generator):
        alert = generator.generate()
        assert re.match(r"ALERT-\d{10}-\d{4}", alert["alert_id"])

    def test_malicious_severity_high_or_critical(self, generator):
        for _ in range(20):
            alert = generator.generate_malicious()
            assert alert["severity"] in (2, 3)

    def test_benign_severity_low_or_medium(self, generator):
        for _ in range(20):
            alert = generator.generate_benign()
            assert alert["severity"] in (0, 1)

    def test_malicious_uses_known_bad_ip(self, generator):
        ips_seen = set()
        for _ in range(30):
            alert = generator.generate_malicious()
            ips_seen.add(alert["src_ip"])
        assert ips_seen <= set(AlertGenerator.MALICIOUS_IPS)

    def test_generate_test_uses_custom_id(self, generator):
        alert = generator.generate_test("MY-TEST-001")
        assert alert["alert_id"] == "MY-TEST-001"
        assert alert["event_type"] == "test_alert"

    def test_generate_test_auto_id_when_none(self, generator):
        alert = generator.generate_test()
        assert alert["alert_id"] is not None


class TestAlertGeneratorMutationHardening:
    def test_counter_increments_by_one(self):
        # seq_offset=0 pins the per-instance phase so the emitted sequence
        # is deterministic; production generators get a random phase to
        # avoid same-second collisions across instances.
        g = AlertGenerator(seq_offset=0)
        assert g._counter == 0
        id1 = g._id()
        id2 = g._id()
        assert id1.endswith("-0001")
        assert id2.endswith("-0002")

    def test_malicious_payload_exact(self, monkeypatch):
        import soar_lab.domain.alert_generator as m

        monkeypatch.setattr(m.random, "choice", lambda seq: seq[0])
        g = AlertGenerator()
        a = g.generate_malicious()
        assert set(a) == {
            "alert_id",
            "hostname",
            "src_ip",
            "hash",
            "severity",
            "timestamp",
            "event_type",
            "alert_type",
        }
        assert a["alert_type"] == "ransomware"
        assert a["event_type"] == "ransomware_detection"
        assert a["severity"] == 2  # seq[0] of [2,3]
        assert a["src_ip"] == AlertGenerator.MALICIOUS_IPS[0]
        assert a["hostname"] == "HOST-0001"
        import hashlib

        assert a["hash"] == hashlib.sha256((a["alert_id"] + a["src_ip"]).encode()).hexdigest()
        from datetime import datetime

        ts = datetime.fromisoformat(a["timestamp"])
        assert ts.tzinfo is not None

    def test_malicious_severity_candidates(self, monkeypatch):
        import soar_lab.domain.alert_generator as m

        captured = []
        monkeypatch.setattr(m.random, "choice", lambda seq: captured.append(seq) or seq[0])
        AlertGenerator().generate_malicious()
        assert [2, 3] in captured  # severity candidates, not [3,3]

    def test_benign_payload_exact(self):
        g = AlertGenerator()
        a = g.generate_benign()
        assert a["alert_type"] == "benign"
        assert a["event_type"] == "benign_activity"
        assert a["severity"] == 1
        assert a["src_ip"] in AlertGenerator.BENIGN_IPS

    def test_test_alert_payload_exact(self):
        g = AlertGenerator()
        a = g.generate_test()
        assert a["alert_type"] == "test"
        assert a["event_type"] == "test_alert"
        assert a["severity"] == 1

    def test_test_alert_id_override(self):
        a = AlertGenerator().generate_test(alert_id="CUSTOM-1")
        assert a["alert_id"] == "CUSTOM-1"

    def test_generate_alias_is_malicious(self):
        a = AlertGenerator().generate()
        assert a["alert_type"] == "ransomware"

    def test_seq_offset_randrange_bound_exact(self, monkeypatch):
        import soar_lab.domain.alert_generator as ag

        seen = []
        monkeypatch.setattr(ag.random, "randrange", lambda n: seen.append(n) or 5)
        AlertGenerator()
        assert seen == [10_000]

    def test_seq_offset_normalized_mod_10000(self, monkeypatch):
        import soar_lab.domain.alert_generator as ag

        monkeypatch.setattr(ag.random, "randrange", lambda n: 10_000)
        g = AlertGenerator()
        assert g._seq_offset == 0  # 10_000 % 10_000; `% 10001` mutant yields 10_000
