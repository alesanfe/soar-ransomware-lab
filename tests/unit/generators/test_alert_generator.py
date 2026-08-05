#!/usr/bin/env python3
"""
Unit tests for soar_lab.domain.alert_generator
"""

import pytest
import re

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
