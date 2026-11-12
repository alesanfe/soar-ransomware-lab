#!/usr/bin/env python3
"""Unit tests for send_alert — webhook URL resolution and CLI flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import soar_lab.infrastructure.messaging.send_alert as sa
from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
    # Real webhook_info paths exist inside the container — isolate tests.
    monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", ["/nonexistent/x.json"])


def _write(tmp: Path, rel: str, data: dict) -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


class TestDefaultWebhookUrl:
    def test_env_var_wins(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "http://env/hook")
        assert sa._default_webhook_url(tmp_path) == "http://env/hook"

    def test_runtime_results_container_prefers_internal(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "runtime/results/webhook_info.json",
            {"webhook_url": "http://internal/h", "webhook_url_host": "http://host/h"},
        )
        monkeypatch.setattr(Path, "exists", lambda self: True)
        # /.dockerenv exists -> container branch -> webhook_url first
        assert sa._default_webhook_url(tmp_path) == "http://internal/h"

    def test_runtime_results_host_prefers_host(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "runtime/results/webhook_info.json",
            {"webhook_url": "http://internal/h", "webhook_url_host": "http://host/h"},
        )
        real_exists = Path.exists

        def fake(self):
            if str(self) == "/.dockerenv":
                return False
            return real_exists(self)

        monkeypatch.setattr(Path, "exists", fake)
        assert sa._default_webhook_url(tmp_path) == "http://host/h"

    def test_artifacts_fallback_exact_path(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "artifacts/results/webhook_info.json",
            {"webhook_url": "http://legacy/h"},
        )
        monkeypatch.setattr(Path, "exists", lambda self: True)
        assert sa._default_webhook_url(tmp_path) == "http://legacy/h"

    def test_missing_files_return_default(self, tmp_path):
        assert sa._default_webhook_url(tmp_path) == SHUFFLE_WEBHOOK_DEFAULT

    def test_bad_json_suppressed(self, tmp_path, monkeypatch):
        p = tmp_path / "runtime" / "results"
        p.mkdir(parents=True)
        (p / "webhook_info.json").write_text("{broken", encoding="utf-8")
        monkeypatch.setattr(Path, "exists", lambda self: True)
        assert sa._default_webhook_url(tmp_path) == SHUFFLE_WEBHOOK_DEFAULT

    def test_webhook_url_empty_falls_to_host(self, tmp_path, monkeypatch):
        _write(
            tmp_path,
            "runtime/results/webhook_info.json",
            {"webhook_url": "", "webhook_url_host": "http://host/h"},
        )
        monkeypatch.setattr(Path, "exists", lambda self: True)
        # container branch: "" is falsy -> webhook_url_host
        assert sa._default_webhook_url(tmp_path) == "http://host/h"

    def test_webhook_info_paths_entry(self, tmp_path, monkeypatch):
        ext = _write(tmp_path, "ext.json", {"webhook_url": "http://ext/h"})
        monkeypatch.setattr(sa, "WEBHOOK_INFO_PATHS", [str(ext)])
        monkeypatch.setattr(Path, "exists", lambda self: True)
        assert sa._default_webhook_url(tmp_path) == "http://ext/h"


class TestMain:
    def _run(self, argv, sender=None, capsys=None):
        if sender is None:
            sender = MagicMock()
            sender.send.return_value = {"success": True}
        sender.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}
        with (
            patch.object(sys, "argv", argv),
            patch.object(sa, "AlertGenerator") as ag,
            patch.object(sa, "HTTPAlertSender", return_value=sender) as hs,
            patch.object(sa, "get_logger"),
            patch.object(sa, "_verify_tls", return_value=False),
            patch.object(sa, "_default_webhook_url", return_value="http://w/h"),
            patch.object(sa.time, "sleep") as slp,
        ):
            sa.main()
        return ag, hs, slp, sender

    def test_single_benign_sends_once(self):
        ag, hs, slp, sender = self._run(
            ["x", "--type", "benign", "--single", "--webhook-url", "http://u"]
        )
        ag.return_value.generate_benign.assert_called_once()
        ag.return_value.generate_malicious.assert_not_called()
        assert sender.send.call_count == 1
        slp.assert_not_called()

    def test_malicious_default_type(self):
        ag, *_ = self._run(["x", "--single", "--webhook-url", "http://u"])
        ag.return_value.generate_malicious.assert_called_once()

    def test_num_alerts_and_delay(self):
        _, _, slp, sender = self._run(
            ["x", "--num-alerts", "3", "--delay", "0", "--webhook-url", "http://u"]
        )
        assert sender.send.call_count == 3
        slp.assert_not_called()  # delay=0 -> no sleep

    def test_failure_exits_1(self, capsys):
        sender = MagicMock()
        sender.send.return_value = {"success": False, "error": "conn refused"}
        sender.get_metrics.return_value = {"alerts_sent": 0, "alerts_failed": 1}
        with pytest.raises(SystemExit) as se:
            self._run(["x", "--single", "--webhook-url", "http://u"], sender=sender)
        assert se.value.code == 1

    def test_help_text_exact(self, capsys):
        with (
            patch.object(sys, "argv", ["x", "--help"]),
            pytest.raises(SystemExit),
        ):
            sa.main()
        out = capsys.readouterr().out
        assert "Send SOAR alert payloads to webhook" in out
        assert "Alert type (malicious or benign)" in out
        assert "Send a single alert" in out
        assert "Number of alerts to send" in out
        assert "Delay between alerts" in out
        assert "Webhook URL" in out
        assert "API token" in out

    def test_webhook_url_default_resolution(self):
        ag, hs, slp, sender = self._run(["x", "--single"])
        # no --webhook-url arg -> resolved default used for sender
        assert hs.call_args.kwargs["webhook_url"] == "http://w/h"

    def test_delay_positive_sleeps_between(self):
        _, _, slp, sender = self._run(
            ["x", "--num-alerts", "2", "--delay", "1", "--webhook-url", "http://u"]
        )
        slp.assert_called_once_with(1)  # between, not after last
