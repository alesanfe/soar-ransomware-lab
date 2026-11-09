"""Regression tests for the 9.5 master-backlog Fase-0 hardening batch.

Covers BL-FS-001/003 (storage traversal + None contract), BL-TEST-001
(returncode honesty), BL-SEC-010 (dotenv credential lookup), BL-SEC-001
(alert-sender TLS default), BL-RATE-003 (trusted-proxy XFF) and
BL-CONC-001/002 (batch deadline + cooperative cancellation).
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from soar_lab.infrastructure.filesystem_storage import FilesystemStorage, UnsafeStorageKey


@pytest.fixture
def storage(tmp_path: Path) -> FilesystemStorage:
    return FilesystemStorage(str(tmp_path / "store"))


class TestFilesystemTraversal:
    """BL-FS-001: key-based ops can never resolve outside the base."""

    @pytest.mark.parametrize(
        "key",
        [
            "../../etc/evil",
            "..",
            ".",
            "",
            "a/../../../x",
            "/etc/passwd",
            "C:/Windows/evil.txt" if Path("C:/").exists() else "/root/evil",
        ],
    )
    def test_write_rejects_unsafe_keys(self, storage: FilesystemStorage, key: str) -> None:
        with pytest.raises(UnsafeStorageKey):
            storage.write(key, b"payload")

    def test_write_inside_base_ok(self, storage: FilesystemStorage, tmp_path: Path) -> None:
        storage.write("sub/dir/file.txt", b"data")
        assert (tmp_path / "store" / "sub" / "dir" / "file.txt").read_bytes() == b"data"

    def test_read_delete_exist_guarded(self, storage: FilesystemStorage) -> None:
        for op in (storage.read, storage.delete, storage.exists):
            with pytest.raises(UnsafeStorageKey):
                op("../../outside.txt")

    def test_symlink_escape_rejected(self, storage: FilesystemStorage, tmp_path: Path) -> None:
        outside = tmp_path / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        link = tmp_path / "store" / "link.txt"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlinks unavailable on this platform")
        # Reading through a symlink that escapes the base must be refused.
        with pytest.raises(UnsafeStorageKey):
            storage.read("link.txt")

    def test_list_keys_prefix_guarded(self, storage: FilesystemStorage) -> None:
        with pytest.raises(UnsafeStorageKey):
            storage.list_keys("../")

    def test_metadata_filename_guarded(self, storage: FilesystemStorage) -> None:
        with pytest.raises(UnsafeStorageKey):
            storage.store_backup_metadata("../../meta", {"a": 1})

    def test_read_file_none_only_when_absent(self, storage: FilesystemStorage) -> None:
        assert storage.read_file("missing.txt") is None
        storage.write("present.txt", b"hello")
        assert storage.read_file("present.txt") == "hello"


class TestSubprocessReturncode:
    """BL-TEST-001: ``returncode=None`` must never coerce to success."""

    def test_pytest_runner_none_returncode_is_failure(self, monkeypatch) -> None:
        from soar_lab.infrastructure.pytest_test_runner import PytestTestRunner

        runner = PytestTestRunner(Path("/repo"), MagicMock())

        class FakeProc:
            returncode = None

            async def communicate(self):
                return b"out", b"err"

        async def fake_create(*args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
        result = asyncio.run(runner._run_async(["pytest"]))
        assert result.returncode == -1
        assert result.success is False

    def test_subprocess_runner_reports_negative_for_none(self, monkeypatch) -> None:
        from soar_lab.infrastructure.subprocess_runner import SubprocessRunner

        runner = SubprocessRunner()

        class FakeProc:
            returncode = None

            async def communicate(self):
                return b"", b""

        async def fake_create(*args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
        result = asyncio.run(runner.run_async(["cmd", "arg"], timeout=5))
        assert result.returncode == -1
        assert result.success is False


class TestDotenvCredentialLookup:
    """BL-SEC-010: strict KEY=value parsing — no substring matches."""

    def _lookup(self, tmp_path: Path, content: str) -> str:
        from soar_lab.common.runtime import dotenv_lookup

        env_file = tmp_path / ".env.full"
        env_file.write_text(content, encoding="utf-8")
        return dotenv_lookup(env_file, "SHUFFLE_DEFAULT_PASSWORD")

    def test_commented_line_not_matched(self, tmp_path: Path) -> None:
        assert self._lookup(tmp_path, "# SHUFFLE_DEFAULT_PASSWORD=leaked\nFOO=1\n") == ""

    def test_similar_name_not_matched(self, tmp_path: Path) -> None:
        assert self._lookup(tmp_path, "MY_SHUFFLE_DEFAULT_PASSWORD=wrong\n") == ""

    def test_exact_key_with_value_containing_equals(self, tmp_path: Path) -> None:
        assert (
            self._lookup(tmp_path, "SHUFFLE_DEFAULT_PASSWORD=pw=with=equals\n") == "pw=with=equals"
        )

    def test_quoted_value_unquoted(self, tmp_path: Path) -> None:
        assert self._lookup(tmp_path, 'SHUFFLE_DEFAULT_PASSWORD="s3cret"\n') == "s3cret"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from soar_lab.common.runtime import dotenv_lookup

        assert dotenv_lookup(tmp_path / "nope.env", "KEY") == ""

    def test_env_var_takes_precedence_over_file(self, monkeypatch, tmp_path: Path) -> None:
        from soar_lab.infrastructure.integrations.shuffle import shuffle_helpers

        monkeypatch.setenv("SHUFFLE_DEFAULT_PASSWORD", "from-env")
        monkeypatch.setattr(
            shuffle_helpers,
            "resolve_secret",
            lambda *a, **k: pytest.fail("file must not be read"),
        )
        assert shuffle_helpers.load_password() == "from-env"


class TestAlertSenderTLS:
    """BL-SEC-001: TLS verification is on by default; opt-out is explicit."""

    def test_verify_tls_default_true(self) -> None:
        from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender

        sender = HTTPAlertSender("https://hook.local", "tok")
        assert sender._session.verify is True

    def test_verify_tls_explicit_disable_warns(self, caplog) -> None:
        import logging

        from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender

        with caplog.at_level(logging.WARNING):
            sender = HTTPAlertSender("https://hook.local", "tok", verify_tls=False)
        assert sender._session.verify is False
        # record.message only exists after format() — getMessage() is robust
        # regardless of which handler ran first (order-dependent flakiness).
        assert any("TLS verification DISABLED" in r.getMessage() for r in caplog.records)


class TestTrustedProxyRateLimit:
    """BL-RATE-003: XFF only honoured from configured trusted proxies."""

    def _request(self, xff: str | None, peer: str):
        from starlette.requests import Request

        headers = []
        if xff:
            headers.append((b"x-forwarded-for", xff.encode()))
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": headers,
            "client": (peer, 1234),
        }
        return Request(scope)

    def _limiter(self, proxies):
        from soar_lab.interfaces.api.middleware.rate_limit import RateLimitMiddleware

        return RateLimitMiddleware(app=MagicMock(), trusted_proxies=proxies)

    def test_spoofed_xff_ignored_without_trusted_peer(self) -> None:
        limiter = self._limiter(proxies=[])
        req = self._request("9.9.9.9", peer="203.0.113.5")
        assert limiter._client_key(req) == "ip:203.0.113.5"

    def test_xff_honoured_from_trusted_peer(self) -> None:
        limiter = self._limiter(proxies=["10.0.0.0/8"])
        req = self._request("9.9.9.9, 10.1.2.3", peer="10.0.0.1")
        assert limiter._client_key(req) == "ip:9.9.9.9"

    def test_rightmost_untrusted_ip_wins(self) -> None:
        limiter = self._limiter(proxies=["10.0.0.0/8", "172.16.0.0/12"])
        req = self._request("8.8.8.8, 172.16.5.5, 10.0.0.9", peer="10.0.0.1")
        assert limiter._client_key(req) == "ip:8.8.8.8"

    def test_bearer_token_keyed_by_fingerprint(self) -> None:
        limiter = self._limiter(proxies=[])
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [(b"authorization", b"Bearer secret-token")],
            "client": ("1.2.3.4", 55),
        }
        from starlette.requests import Request

        key = limiter._client_key(Request(scope))
        assert key.startswith("tok:")
        assert "secret-token" not in key


class TestBatchDeadline:
    """BL-CONC-001/002: deadline exceeded → distinct 504 result, no zombies."""

    def _sender(self, send_fn):
        from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender

        sender = HTTPAlertSender("http://hook", "t")
        sender.send = send_fn
        return sender

    def test_slow_batch_marks_504_and_cancels(self) -> None:
        started = []
        gate = threading.Event()

        def slow_send(alert):
            started.append(alert)
            gate.wait(0.4)  # each send takes 400ms — outlives the deadline
            return {"success": True}

        sender = self._sender(slow_send)
        alerts = [{"alert_id": f"A{i}"} for i in range(10)]
        results = sender.send_batch(alerts, max_queue_size=4, workers=2, batch_timeout=0.25)
        assert len(results) == 10
        timed_out = [r for r in results if r.get("status_code") == 504]
        assert timed_out, "expected deadline-exceeded results"
        # Workers must not keep consuming new sends after the deadline —
        # bounded: at most workers*ceil items could have started.
        assert len(started) < len(alerts)

    def test_normal_batch_completes(self) -> None:
        sender = self._sender(lambda a: {"success": True, "id": a["alert_id"]})
        results = sender.send_batch([{"alert_id": "x"}], max_queue_size=4, workers=1)
        assert results[0]["success"] is True

    def test_queue_full_returns_503(self) -> None:
        release = threading.Event()

        def blocking_send(alert):
            release.wait(1.0)
            return {"success": True}

        sender = self._sender(blocking_send)
        try:
            results = sender.send_batch(
                [{"alert_id": f"A{i}"} for i in range(8)],
                max_queue_size=1,
                workers=1,
                batch_timeout=10,
            )
            assert any(r.get("status_code") == 503 for r in results)
        finally:
            release.set()

    def test_zero_or_negative_timeout_rejected(self) -> None:
        sender = self._sender(lambda a: {"success": True})
        with pytest.raises(ValueError):
            sender.send_batch([{"a": 1}], batch_timeout=0)


class TestSingleCompositionRoot:
    """EPIC-1: package import must not perform wiring side effects."""

    def test_skip_flag_yields_no_app_and_no_io(self, monkeypatch) -> None:
        import importlib
        import sys

        monkeypatch.setenv("SOAR_SKIP_EAGER_INIT", "1")
        sys.modules.pop("soar_lab.interfaces.api", None)
        import soar_lab.interfaces.api as api_pkg

        importlib.reload(api_pkg)
        assert api_pkg.app is None

    def test_create_app_reexport_is_composition_factory(self) -> None:
        """`uvicorn ...:app --factory` and `soar-lab api` share one wiring."""
        import soar_lab.interfaces.api as api_pkg
        import soar_lab.interfaces.api.composition as comp

        assert api_pkg.create_app is comp.create_app

    def test_src_does_not_import_scripts_test_service(self) -> None:
        import inspect

        import soar_lab.interfaces.api.composition as comp

        src = inspect.getsource(comp)
        assert "from scripts.test_service" not in src
        assert "from scripts import" not in src
