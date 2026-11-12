"""CONTRACT-001..005: API <-> workflow shared contract tests.

Property under test: **no payload the API admits may be dropped by
``normalize_inputs`` on severity or schema grounds alone.** Both sides
consume the same canonical table — these tests pin that parity plus
the rejection matrix required by the backlog.
"""

from __future__ import annotations

import pytest

from soar_lab.domain.severity import (
    DEFAULT_SEVERITY,
    SeverityContractError,
    normalize_severity,
    severity_to_thehive,
)
from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

pytestmark = pytest.mark.contract


def _wf_severity(value):
    """Mirror of the embedded normalize_inputs.py severity logic."""
    import re

    names = {
        "informational": 0, "info": 0, "low": 1,
        "medium": 2, "med": 2, "warning": 2, "warn": 2,
        "high": 3, "critical": 4, "crit": 4,
    }
    if value is None:
        raise ValueError("missing")
    if isinstance(value, bool):
        raise ValueError("bool")
    if isinstance(value, (int, float)):
        v = int(value)
        if float(value) != v or v < 0 or v > 4:
            raise ValueError("range")
        return v
    t = str(value).strip().lower()
    if t in names:
        return names[t]
    if re.fullmatch(r"\d+(?:\.0+)?", t):
        v = int(float(t))
        if v < 0 or v > 4:
            raise ValueError("range")
        return v
    raise ValueError("unknown")


class TestSeverityParity:
    """API-admitted severities are all acceptable to the workflow."""

    @pytest.mark.parametrize("v", [0, 1, 2, 3, 4])
    def test_int_range_accepted_both_sides(self, v):
        assert normalize_severity(v) == _wf_severity(v) == v

    @pytest.mark.parametrize("v", ["informational", "low", "medium", "high", "critical",
                                   "INFO", "Critical", "  high  "])
    def test_names_accepted_both_sides(self, v):
        assert normalize_severity(v) == _wf_severity(v)

    @pytest.mark.parametrize("v", ["0", "1", "2", "3", "4", "2.0"])
    def test_numeric_strings_accepted(self, v):
        assert normalize_severity(v) == _wf_severity(v)

    @pytest.mark.parametrize("v", [-1, 5, 99])
    def test_out_of_range_rejected_both_sides(self, v):
        with pytest.raises(SeverityContractError):
            normalize_severity(v)
        with pytest.raises(ValueError):
            _wf_severity(v)

    @pytest.mark.parametrize("v", ["urgent", "P1", "sev1", "", "3.5.2"])
    def test_unknown_text_rejected_both_sides(self, v):
        with pytest.raises(SeverityContractError):
            normalize_severity(v)
        with pytest.raises(ValueError):
            _wf_severity(v)

    def test_bool_rejected(self):
        with pytest.raises(SeverityContractError):
            normalize_severity(True)
        with pytest.raises(ValueError):
            _wf_severity(True)

    def test_none_default_documented(self):
        """Absent severity normalizes to the documented default."""
        s = AlertIngestSchema(alert_id="a1")
        assert s.to_alert_dict()["severity"] == DEFAULT_SEVERITY
        # And the default is a severity the workflow accepts:
        assert _wf_severity(DEFAULT_SEVERITY) == DEFAULT_SEVERITY

    def test_critical_int_accepted_e2e(self):
        """B3 regression: severity=4 used to be dropped downstream."""
        s = AlertIngestSchema(severity=4)
        canonical = s.to_alert_dict()["severity"]
        assert canonical == 4
        assert _wf_severity(canonical) == 4

    def test_urgent_rejected_at_edge(self):
        """B3 regression: 'urgent' used to pass the schema then die in Shuffle."""
        with pytest.raises(Exception):
            AlertIngestSchema(severity="urgent")

    def test_thehive_mapping(self):
        assert severity_to_thehive(0) == 1
        assert severity_to_thehive(4) == 3


class TestSchemaVersion:
    def test_known_version_accepted(self):
        assert AlertIngestSchema(schema_version="1.0").schema_version == "1.0"

    def test_unknown_version_rejected(self):
        with pytest.raises(Exception):
            AlertIngestSchema(schema_version="9.9")


class TestFieldValidation:
    def test_src_ip_valid(self):
        assert AlertIngestSchema(src_ip="10.0.0.1").src_ip == "10.0.0.1"
        assert AlertIngestSchema(src_ip="fd00::1").src_ip == "fd00::1"

    @pytest.mark.parametrize("bad", ["999.1.1.1", "host/../../x", "10.0.0.1&admin=true", "${jndi:ldap://x}"])
    def test_src_ip_invalid(self, bad):
        with pytest.raises(Exception):
            AlertIngestSchema(src_ip=bad)

    @pytest.mark.parametrize("bad", ["bad host", "host\nforged", "host%0a", "a" * 300 + ".x"])
    def test_hostname_invalid(self, bad):
        with pytest.raises(Exception):
            AlertIngestSchema(hostname=bad)

    def test_extras_bounded(self):
        big = {f"extra_{i}": "x" for i in range(80)}
        with pytest.raises(Exception):
            AlertIngestSchema(**big)

    def test_extra_str_bounded(self):
        with pytest.raises(Exception):
            AlertIngestSchema(vendor_blob="x" * 5000)


class TestSanitizerWired:
    """INPUT-001: the real ingest path sanitizes free-text fields."""

    def test_script_tag_stripped_in_to_alert_dict(self):
        s = AlertIngestSchema(description="run <script>alert(1)</script> now")
        assert "<script>" not in s.to_alert_dict()["description"]

    def test_control_chars_stripped(self):
        s = AlertIngestSchema(title="ok\x00title\x07")
        assert "\x00" not in s.to_alert_dict()["title"]
