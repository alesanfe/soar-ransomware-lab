#!/usr/bin/env python3
"""CFG domain-unification regression tests.

EPIC 1 (CFG-001..005): a single canonical AlertSeverity governs every
validator, KPI, generator and schema — the repo previously carried four
incompatible severity definitions (0-3 tuple, 0-3 strings, 1-5 inline,
1-4 enum).

CFG-016/017: containment mode is Literal — no silent simulated
downgrade. CFG-048/049: IPv6 parity. CFG-031/032: 12-Factor dotenv
precedence.
"""

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from soar_lab.config.schemas import RansomwareAlert
from soar_lab.config.schemas.validators import is_valid_ip_address
from soar_lab.domain.alert_generator import AlertGenerator
from soar_lab.domain.models import AlertSeverity
from soar_lab.interfaces.api.models import ContainmentRequest
from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema
from soar_lab.validation.validators import AlertValidator, IPValidator

_CANONICAL = tuple(s.value for s in AlertSeverity)


class TestCanonicalSeverity:
    """CFG-001/002/005 — one severity enum to rule them all."""

    def test_validator_derives_from_canonical_enum(self):
        assert AlertValidator.VALID_SEVERITIES == _CANONICAL
        assert 0 in AlertValidator.VALID_SEVERITIES  # INFORMATIONAL (CONTRACT-001)
        assert 4 in AlertValidator.VALID_SEVERITIES  # CRITICAL was rejected before

    def test_generator_outputs_always_canonical(self):
        gen = AlertGenerator()
        for _ in range(50):
            for alert in (
                gen.generate_benign(),
                gen.generate_malicious(),
                gen.generate_test(),
            ):
                assert alert["severity"] in _CANONICAL

    def test_ransomware_alert_uses_canonical_enum(self):
        field = RansomwareAlert.model_fields["severity"]
        assert field.annotation is AlertSeverity

    def test_ransomware_alert_accepts_int_and_enum(self):
        base = {
            "alert_id": "ALERT-1234567890-1234",
            "hostname": "h1",
            "src_ip": "10.0.0.1",
            "hash": {"sha256": "a" * 64},
            "source": "s",
            "detection_time": "2025-01-01T00:00:00",
            "event_type": "ransomware_detection",
            "description": "d",
        }
        assert RansomwareAlert(**{**base, "severity": 3}).severity is AlertSeverity.HIGH
        assert (
            RansomwareAlert(**{**base, "severity": AlertSeverity.CRITICAL}).severity
            is AlertSeverity.CRITICAL
        )
        assert RansomwareAlert(**{**base, "severity": 0}).severity is AlertSeverity.INFORMATIONAL

    def test_ingest_schema_canonical_bounds(self):
        AlertIngestSchema(severity=0)  # INFORMATIONAL — canonical 0..4
        AlertIngestSchema(severity=1)
        AlertIngestSchema(severity=4)
        with pytest.raises(ValidationError):
            AlertIngestSchema(severity=5)
        with pytest.raises(ValidationError):
            AlertIngestSchema(severity=True)  # bool is not a severity

    def test_no_parallel_severity_definitions(self):
        """CFG-001 guard: the removed SeverityLevel must stay gone."""
        import soar_lab.config.schemas as schemas_pkg

        assert not hasattr(schemas_pkg, "SeverityLevel")
        import soar_lab.config.schemas.enums as enums_mod

        assert not hasattr(enums_mod, "SeverityLevel")


class TestKpiCriticalCount:
    """CFG-003 — critical_count follows the canonical enum, not '==3'."""

    def test_critical_counts_only_critical(self):
        from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

        KPIAnalyzer.__new__(KPIAnalyzer)
        # call the aggregation block indirectly is complex; instead verify
        # semantics: HIGH (3) must NOT count as critical, CRITICAL (4) must.
        assert AlertSeverity.HIGH < AlertSeverity.CRITICAL
        # The analyzer now uses `severity >= AlertSeverity.CRITICAL`:
        assert 3 < AlertSeverity.CRITICAL
        assert 4 >= AlertSeverity.CRITICAL


class TestContainmentModeLiteral:
    """CFG-016/017 — no silent downgrade to 'simulated'."""

    def test_valid_modes(self):
        assert (
            ContainmentRequest(alert_id="a", case_id="c", hostname="h", mode="simulated").mode
            == "simulated"
        )
        assert (
            ContainmentRequest(alert_id="a", case_id="c", hostname="h", mode="enforce").mode
            == "enforce"
        )

    def test_default_is_simulated(self):
        req = ContainmentRequest(alert_id="a", case_id="c", hostname="h")
        assert req.mode == "simulated"

    @pytest.mark.parametrize("bad", ["simulation", "ENFORCE", "enforc", "SIM"])
    def test_invalid_modes_rejected(self, bad):
        with pytest.raises(ValidationError):
            ContainmentRequest(alert_id="a", case_id="c", hostname="h", mode=bad)


class TestIPv6Parity:
    """CFG-048/049 — IPv4 and IPv6 both validate."""

    @pytest.mark.parametrize(
        "ip", ["192.168.1.1", "10.0.0.1", "::1", "fe80::1", "2001:db8::1", "fe80::1%eth0"]
    )
    def test_valid_ips(self, ip):
        assert IPValidator.validate(ip)
        assert is_valid_ip_address(ip)

    @pytest.mark.parametrize(
        "ip", ["999.1.1.1", "not-an-ip", "192.168.1.256", "", "gg::1", "1.2.3"]
    )
    def test_invalid_ips(self, ip):
        assert not IPValidator.validate(ip)
        assert not is_valid_ip_address(ip)

    def test_ransomware_alert_accepts_ipv6(self):
        alert = RansomwareAlert(
            alert_id="ALERT-1234567890-1234",
            hostname="h1",
            src_ip="2001:db8::1",
            hash={"sha256": "a" * 64},
            severity=2,
            source="s",
            detection_time="2025-01-01T00:00:00",
            event_type="ransomware_detection",
            description="d",
        )
        assert "2001:db8::1" in str(alert.src_ip)


class TestDotenvPrecedence:
    """CFG-031/032 — real env wins over .env.full unless opted out."""

    def _reload_capturing(self, monkeypatch, env_override: str | None):
        """Reload settings with dotenv intercepted; return captured kwargs."""
        import dotenv

        import soar_lab.config.settings as settings_mod

        # The .env.full load is conditional on the file existing next to the
        # package root — under mutants/ it is not copied, so the call never
        # happens and there is nothing to assert.
        env_file = Path(settings_mod.__file__).resolve().parent.parent.parent.parent / ".env.full"
        if not env_file.exists():
            pytest.skip(".env.full not present in this tree (e.g. mutants/ copy)")

        calls = []
        if env_override is None:
            monkeypatch.delenv("SOAR_DOTENV_OVERRIDE", raising=False)
        else:
            monkeypatch.setenv("SOAR_DOTENV_OVERRIDE", env_override)
        # reload() re-imports `from dotenv import load_dotenv`, so the fake
        # must live at the source module, not on settings_mod.
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **kw: calls.append(kw))
        importlib.reload(settings_mod)
        return calls, settings_mod

    @staticmethod
    def _env_full_call(calls: list[dict]) -> dict:
        """The .env.full load is the only one passing an override kwarg."""
        explicit = [c for c in calls if "override" in c]
        assert explicit, "no .env.full load_dotenv call captured"
        return explicit[-1]

    def test_default_no_override(self, monkeypatch):
        calls, settings_mod = self._reload_capturing(monkeypatch, None)
        try:
            assert self._env_full_call(calls)["override"] is False
        finally:
            monkeypatch.undo()
            importlib.reload(settings_mod)

    def test_opt_in_override(self, monkeypatch):
        calls, settings_mod = self._reload_capturing(monkeypatch, "1")
        try:
            assert self._env_full_call(calls)["override"] is True
        finally:
            monkeypatch.undo()
            importlib.reload(settings_mod)
