#!/usr/bin/env python3
"""
Unit tests for soar_lab.validation.validators
"""

import pytest

from soar_lab.exceptions import ValidationError
from soar_lab.validation.validators import (
    IPValidator,
    HashValidator,
    AlertValidator,
    PathValidator,
)


@pytest.mark.unit
class TestIPValidator:
    def test_valid_ipv4(self):
        assert IPValidator.validate("192.168.1.1") is True

    def test_valid_ipv4_zeros(self):
        assert IPValidator.validate("0.0.0.0") is True

    def test_valid_ipv4_broadcast(self):
        assert IPValidator.validate("255.255.255.255") is True

    def test_invalid_octet_too_large(self):
        assert IPValidator.validate("999.0.0.1") is False

    def test_invalid_too_few_octets(self):
        assert IPValidator.validate("192.168.1") is False

    def test_invalid_empty(self):
        assert IPValidator.validate("") is False

    def test_invalid_none(self):
        assert IPValidator.validate(None) is False

    def test_invalid_letters(self):
        assert IPValidator.validate("abc.def.ghi.jkl") is False

    def test_assert_valid_raises(self):
        with pytest.raises(ValidationError):
            IPValidator.assert_valid("not-an-ip")


@pytest.mark.unit
class TestHashValidator:
    def test_valid_md5(self):
        assert HashValidator.validate("d41d8cd98f00b204e9800998ecf8427e") is True

    def test_valid_sha256_64_chars(self):
        hash64 = "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"
        assert HashValidator.validate(hash64) is True

    def test_invalid_only_digits(self):
        assert HashValidator.validate("1" * 32) is False

    def test_invalid_wrong_length(self):
        assert HashValidator.validate("abc123") is False

    def test_invalid_none(self):
        assert HashValidator.validate(None) is False

    def test_assert_valid_raises(self):
        with pytest.raises(ValidationError):
            HashValidator.assert_valid("not-a-hash")


@pytest.mark.unit
class TestAlertValidator:
    def _valid_alert(self):
        return {
            "alert_id": "ALERT-20240101-123456",
            "hostname": "WIN-001",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e",
            "timestamp": "2024-01-01T00:00:00Z",
            "severity": 2,
            "event_type": "ransomware_detection",
        }

    def test_valid_alert(self):
        assert AlertValidator.validate(self._valid_alert()) is True

    def test_missing_required_field(self):
        alert = self._valid_alert()
        del alert["hostname"]
        assert AlertValidator.validate(alert) is False

    def test_invalid_ip(self):
        alert = self._valid_alert()
        alert["src_ip"] = "not.an.ip"
        assert AlertValidator.validate(alert) is False

    def test_invalid_hash(self):
        alert = self._valid_alert()
        alert["hash"] = "badhash"
        assert AlertValidator.validate(alert) is False

    def test_valid_structure(self):
        assert AlertValidator.validate_structure(self._valid_alert()) is True

    def test_structure_invalid_severity(self):
        alert = self._valid_alert()
        alert["severity"] = 99
        assert AlertValidator.validate_structure(alert) is False

    def test_empty_dict(self):
        assert AlertValidator.validate({}) is False

    def test_none(self):
        assert AlertValidator.validate(None) is False


@pytest.mark.unit
class TestPathValidator:
    def test_valid_path(self, tmp_path):
        p = tmp_path / "backup.tar.gz"
        assert PathValidator.validate(p) is True

    def test_path_traversal(self):
        assert PathValidator.validate("../../etc/passwd") is False

    def test_none_path(self):
        assert PathValidator.validate(None) is False

    def test_assert_valid_raises_on_traversal(self):
        with pytest.raises(ValidationError):
            PathValidator.assert_valid("../../etc/passwd")
