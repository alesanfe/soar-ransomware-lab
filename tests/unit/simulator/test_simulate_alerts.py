"""Unit tests for the SIEM alert simulator (eval 42).

The simulator feeds the whole pipeline — every generated alert must satisfy
the same structural contract the admission validator enforces (required
fields, valid severity, IP, hash length).  ``random.choice`` is patched to a
round-robin selector so all 21 families are exercised deterministically.
"""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from soar_lab.simulator import simulate_alerts as sim
from soar_lab.validation.validators import AlertValidator

pytestmark = pytest.mark.unit


def _all_family_alerts() -> list[dict]:
    """One alert per family — round-robin choice, optional branches skipped.

    ``families`` is rebuilt inside ``generate_malicious_alert`` on every call,
    so the selector cycles on a single global counter rather than per-list
    state: the first ``choice`` of each call picks the next family.
    """
    counter = {"n": -1}

    def pick(seq):
        if seq and isinstance(seq[0], dict) and "name" in seq[0]:
            counter["n"] += 1  # family selection — advance once per alert
        return seq[counter["n"] % len(seq)]

    alerts = []
    with patch.object(random, "choice", side_effect=pick), \
         patch.object(random, "random", return_value=0.99), \
         patch.object(random, "sample", side_effect=lambda s, k: list(s)[:k]):
        for i in range(25):  # >21 families — wraps around to confirm cycling
            alerts.append(sim.generate_malicious_alert(i))
    return alerts


def test_every_family_produces_structurally_valid_alert():
    alerts = _all_family_alerts()
    families = {a["malware_family"] for a in alerts}
    assert len(families) >= 21, f"round-robin missed families: {families}"
    for alert in alerts:
        assert AlertValidator.validate_structure(alert), (
            f"{alert['malware_family']} produces an invalid alert: {alert}"
        )


def test_alert_fields_match_pipeline_contract():
    alert = _all_family_alerts()[0]
    for field in (
        "alert_id", "alert_type", "event_type", "severity", "hostname",
        "src_ip", "hash", "source", "detection_time", "description",
        "mitre_techniques", "mitre_tactics", "malware_family", "domain",
    ):
        assert field in alert, f"missing contract field {field}"
    assert alert["domain"], "domain must always be set (GoogleDNS analyzer contract)"


def test_send_alert_retries_on_transient_5xx():
    calls = []

    class Resp:
        def __init__(self, code):
            self.status_code = code

    def fake_post(*a, **kw):
        calls.append(1)
        return Resp(503 if len(calls) < 3 else 200)

    with patch.object(sim.requests, "post", side_effect=fake_post), \
         patch.object(sim.time, "sleep"):
        ok, status = sim.send_alert({}, "http://x", max_retries=3)
    assert ok and status == 200 and len(calls) == 3


def test_send_alert_does_not_retry_client_errors():
    class Resp:
        status_code = 422

    with patch.object(sim.requests, "post", return_value=Resp()) as post:
        ok, status = sim.send_alert({}, "http://x", max_retries=3)
    assert not ok and status == 422 and post.call_count == 1


def test_webhook_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "http://env-webhook/x")
    assert sim._get_default_webhook() == "http://env-webhook/x"


class TestSimulateAlertsCoverage:
    """Fill remaining branches: container detection, webhook resolution,
    optional alert fields, send_alert exception path, and main()."""

    def test_inside_container_true(self):
        assert sim._inside_container() is True  # tests run inside Docker

    def test_inside_container_false(self):
        with patch.object(sim.Path, "exists", return_value=False):
            assert sim._inside_container() is False

    def test_webhook_info_json_container(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        info = tmp_path / "webhook_info.json"
        info.write_text('{"webhook_url": "http://internal/hook", '
                        '"webhook_url_host": "http://host/hook"}')
        monkeypatch.setattr(sim, "WEBHOOK_INFO_PATHS", [str(info)])
        monkeypatch.setattr(sim, "_inside_container", lambda: True)
        assert sim._get_default_webhook() == "http://internal/hook"

    def test_webhook_info_json_host_prefers_host_url(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        info = tmp_path / "webhook_info.json"
        info.write_text('{"webhook_url": "http://internal/hook", '
                        '"webhook_url_host": "http://host/hook"}')
        monkeypatch.setattr(sim, "WEBHOOK_INFO_PATHS", [str(info)])
        monkeypatch.setattr(sim, "_inside_container", lambda: False)
        assert sim._get_default_webhook() == "http://host/hook"

    def test_webhook_info_unreadable_falls_through(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("SIEM_WEBHOOK_TOKEN", raising=False)
        info = tmp_path / "webhook_info.json"
        info.write_text("not-json")
        monkeypatch.setattr(sim, "WEBHOOK_INFO_PATHS", [str(info)])
        monkeypatch.setattr(sim.Path, "exists",
                            lambda self=None: str(self) == str(info))
        assert sim._get_default_webhook() is None

    def test_webhook_token_fallback(self, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        monkeypatch.setattr(sim, "WEBHOOK_INFO_PATHS", [])
        monkeypatch.setattr(sim.Path, "exists", lambda self: False)
        monkeypatch.setenv("SIEM_WEBHOOK_TOKEN", "tok123")
        assert "tok123" in sim._get_default_webhook()

    def test_webhook_none_when_nothing_available(self, monkeypatch):
        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        monkeypatch.delenv("SIEM_WEBHOOK_TOKEN", raising=False)
        monkeypatch.setattr(sim, "WEBHOOK_INFO_PATHS", [])
        monkeypatch.setattr(sim.Path, "exists", lambda self: False)
        assert sim._get_default_webhook() is None

    def test_optional_branches_all_taken(self):
        with patch.object(random, "random", return_value=0.0), \
             patch.object(random, "sample", side_effect=lambda s, k: list(s)[:k]):
            alert = sim.generate_malicious_alert(1)
        assert "url" in alert
        assert "c2_ips" in alert
        assert "file_path" in alert

    def test_send_alert_exception_retries_then_fails(self):
        with patch.object(sim.requests, "post",
                          side_effect=ConnectionError("down")), \
             patch.object(sim.time, "sleep"):
            ok, status = sim.send_alert({}, "http://x", max_retries=2)
        assert not ok and status == 0

    def test_main_no_webhook_exits(self, monkeypatch, caplog):
        monkeypatch.setattr(sim, "_get_default_webhook", lambda: None)
        monkeypatch.setattr("sys.argv", ["sim", "--count", "1"])
        with pytest.raises(SystemExit) as exc:
            sim.main()
        assert exc.value.code == 1

    def test_main_success_and_partial_failure(self, monkeypatch):
        monkeypatch.setattr(sim, "_get_default_webhook",
                            lambda: "http://hook")
        monkeypatch.setattr("sys.argv",
                            ["sim", "--count", "2", "--delay", "0"])
        results = iter([(True, 200), (False, 500)])
        monkeypatch.setattr(sim, "send_alert",
                            lambda a, u: next(results))
        monkeypatch.setattr(sim.time, "sleep", lambda s: None)
        assert sim.main() == 1  # 1/2 sent → nonzero
