#!/usr/bin/env python3
"""Fase-1 hardening regressions.

Covers:
- BL-ES-001: scroll_search_generator releases the server-side scroll
  context (DELETE /_search/scroll) on exhaustion, errors and early close.
- BL-FS-002: FilesystemStorage.write is atomic (temp+fsync+os.replace);
  a crash mid-write cannot leave a truncated file.
- BL-FS-004: get_file_info/delete_file honest contracts.
- BL-TEST-002/003: TestRunResult typing + timeout kills the whole
  process tree, not only the direct child.
- BL-CLEAN-001..005: single-sourced retention, dry-run, active-guard
  (min_keep) and explicit error counts in CleanupService.
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from soar_lab.infrastructure.cleanup_service import CleanupService
from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
from soar_lab.infrastructure.integrations.elasticsearch.es_helpers import (
    scroll_search_generator,
)
from soar_lab.infrastructure.pytest_test_runner import TestRunResult
from soar_lab.infrastructure.subprocess_runner import SubprocessRunner


class TestScrollCleanup:
    """BL-ES-001 — scroll context must be released, not left to expire."""

    @staticmethod
    def _pages(*pages):
        post_fn = Mock()
        post_fn.side_effect = list(pages)
        return post_fn

    def test_scroll_cleared_after_exhaustion(self):
        post_fn = self._pages(
            {"_scroll_id": "s1", "hits": {"hits": [{"_source": {"id": 1}}]}},
            {"_scroll_id": "s2", "hits": {"hits": []}},
        )
        delete_fn = Mock()

        results = list(scroll_search_generator(post_fn, "idx", delete_fn=delete_fn))

        assert results == [{"id": 1}]
        delete_fn.assert_called_once_with("/_search/scroll", json={"scroll_id": "s2"})

    def test_scroll_cleared_on_early_close(self):
        """Partial consumption (caller breaks early) must also free the context."""
        post_fn = self._pages(
            {"_scroll_id": "s1", "hits": {"hits": [{"_source": {"id": 1}}]}},
        )
        delete_fn = Mock()

        gen = scroll_search_generator(post_fn, "idx", delete_fn=delete_fn)
        assert next(gen) == {"id": 1}
        gen.close()  # caller abandons the generator mid-scroll

        delete_fn.assert_called_once_with("/_search/scroll", json={"scroll_id": "s1"})

    def test_scroll_cleared_on_iteration_error(self):
        """An exception raised while consuming still frees the context."""
        post_fn = self._pages(
            {"_scroll_id": "s1", "hits": {"hits": [{"_source": {"id": 1}}]}},
        )
        delete_fn = Mock()
        gen = scroll_search_generator(post_fn, "idx", delete_fn=delete_fn)
        next(gen)
        with pytest.raises(RuntimeError, match="boom"):
            gen.throw(RuntimeError("boom"))
        delete_fn.assert_called_once_with("/_search/scroll", json={"scroll_id": "s1"})

    def test_clear_failure_does_not_break_iteration(self):
        """A failed clear_scroll is logged, never raised into the caller."""
        post_fn = self._pages(
            {"_scroll_id": "s1", "hits": {"hits": []}},
        )
        delete_fn = Mock(side_effect=RuntimeError("es down"))

        assert list(scroll_search_generator(post_fn, "idx", delete_fn=delete_fn)) == []
        delete_fn.assert_called_once()

    def test_no_delete_fn_still_works(self):
        post_fn = self._pages(
            {"_scroll_id": "s1", "hits": {"hits": [{"_source": {"id": 1}}]}},
            {"_scroll_id": "s2", "hits": {"hits": []}},
        )
        assert list(scroll_search_generator(post_fn, "idx")) == [{"id": 1}]


class TestAtomicWrite:
    """BL-FS-002 — write() must never leave a truncated target."""

    def test_write_is_complete(self, tmp_path):
        storage = FilesystemStorage(base_dir=str(tmp_path))
        storage.write("a/b.bin", b"\x01\x02" * 5000)
        assert (tmp_path / "a" / "b.bin").read_bytes() == b"\x01\x02" * 5000

    def test_failed_write_preserves_old_content_and_no_tmp(self, tmp_path):
        storage = FilesystemStorage(base_dir=str(tmp_path))
        storage.write("f.bin", b"original")
        target = tmp_path / "f.bin"

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(os, "replace", Mock(side_effect=OSError("crash")))
            with pytest.raises(OSError, match="crash"):
                storage.write("f.bin", b"corrupted")

        assert target.read_bytes() == b"original"
        assert list(tmp_path.glob("*.tmp")) == []


class TestUnsafeKeyHardening:
    """BUG-121 — NUL/control chars must raise UnsafeStorageKey, not raw errors."""

    @pytest.mark.parametrize("key", ["\x00", "a\x00b", "\x1fdir", "log/\x07x"])
    def test_control_char_keys_rejected_cleanly(self, tmp_path, key):
        from soar_lab.infrastructure.filesystem_storage import (
            FilesystemStorage,
            UnsafeStorageKey,
        )

        storage = FilesystemStorage(base_dir=str(tmp_path))
        with pytest.raises(UnsafeStorageKey):
            storage.write(key, b"x")

    @pytest.mark.parametrize("key", ["./", "a/../", "x/y/../../"])
    def test_keys_resolving_to_base_rejected(self, tmp_path, key):
        """A key naming the base directory itself is invalid — write/delete
        on a directory path would fail with raw OS errors."""
        from soar_lab.infrastructure.filesystem_storage import (
            FilesystemStorage,
            UnsafeStorageKey,
        )

        storage = FilesystemStorage(base_dir=str(tmp_path))
        with pytest.raises(UnsafeStorageKey):
            storage.write(key, b"x")


class TestRepoRootDotenv:
    """BUG-124 — dotenv fallback must hit the repo root, never CWD/src."""

    def test_repo_root_resolves_to_project_root(self):
        from soar_lab.common.runtime import repo_root

        # pyproject.toml exists only at the real repository root
        assert (repo_root() / "pyproject.toml").exists()
        assert (repo_root() / "src" / "soar_lab").is_dir()

    def test_es_credentials_ignore_cwd_decoy(self, tmp_path, monkeypatch):
        """A .env.full in the CWD must NOT be consulted (BUG-109 class)."""
        from soar_lab.infrastructure.integrations.shuffle.shuffle_es_helpers import (
            read_env_credentials,
        )

        decoy = tmp_path / ".env.full"
        decoy.write_text(
            "SHUFFLE_OPENSEARCH_URL=http://decoy:9999\n" "SHUFFLE_OPENSEARCH_USERNAME=decoy-user\n"
        )
        monkeypatch.chdir(tmp_path)
        for var in (
            "SHUFFLE_OPENSEARCH_URL",
            "SHUFFLE_OPENSEARCH_USERNAME",
            "SHUFFLE_OPENSEARCH_PASSWORD",
            "OPENSEARCH_USERNAME",
            "OPENSEARCH_PASSWORD",
        ):
            monkeypatch.delenv(var, raising=False)

        url, user, _ = read_env_credentials()
        assert url != "http://decoy:9999", "CWD decoy was consulted"
        assert user != "decoy-user", "CWD decoy was consulted"


class TestAioHTTPSessionPooling:
    """BL-HTTP-002 — sessions pooled per SSL mode + explicit close()."""

    @pytest.mark.asyncio
    async def test_sessions_reused_per_verify_mode(self):
        from soar_lab.infrastructure.http_client import AioHTTPClient

        client = AioHTTPClient()
        s1 = await client._session(verify_ssl=True)
        s2 = await client._session(verify_ssl=True)
        s3 = await client._session(verify_ssl=False)

        assert s1 is s2, "same verify mode must reuse the pooled session"
        assert s3 is not s1
        await client.close()

    @pytest.mark.asyncio
    async def test_close_closes_all_and_resets(self):
        from unittest.mock import Mock

        from soar_lab.infrastructure.http_client import AioHTTPClient

        client = AioHTTPClient()
        s1 = await client._session(verify_ssl=True)
        s1.close = Mock()
        await client.close()

        s1.close.assert_called_once()
        assert client._sessions == {}

        s2 = await client._session(verify_ssl=True)
        assert s2 is not s1, "post-close must create a fresh session"
        await client.close()


class TestStartupValidation:
    """BL-ARCH-002 — composition warns about unconfigured integrations."""

    def test_missing_integrations_logged(self, caplog):
        import logging

        from soar_lab.interfaces.api.composition import CompositionRoot

        root = CompositionRoot.__new__(CompositionRoot)
        provider = Mock()
        provider.get = Mock(return_value=None)
        root.config_provider = provider

        with caplog.at_level(logging.WARNING):
            root._warn_unconfigured_integrations()

        assert "thehive" in caplog.text
        assert "elasticsearch" in caplog.text

    def test_fully_configured_no_warning(self, caplog):
        import logging

        from soar_lab.interfaces.api.composition import CompositionRoot

        root = CompositionRoot.__new__(CompositionRoot)
        provider = Mock()
        provider.get = Mock(return_value="http://x")
        root.config_provider = provider

        with caplog.at_level(logging.WARNING):
            root._warn_unconfigured_integrations()

        assert "without config" not in caplog.text


class TestFileInfoContract:
    """BL-FS-004 — None means absent; it is part of the declared contract."""

    def test_get_file_info_missing_returns_none(self, tmp_path):
        storage = FilesystemStorage(base_dir=str(tmp_path))
        assert storage.get_file_info(str(tmp_path / "nope")) is None

    def test_get_file_info_present(self, tmp_path):
        storage = FilesystemStorage(base_dir=str(tmp_path))
        f = tmp_path / "x.txt"
        f.write_text("data")
        info = storage.get_file_info(str(f))
        assert info is not None and info["size"] == 4


class TestRunResultContract:
    """BL-TEST-002 — typed result, honest success semantics."""

    def test_missing_returncode_is_failure_not_zero(self):
        r = TestRunResult(returncode=-1, stdout="", stderr="", duration=0.0)
        assert not r.success

    def test_to_dict_shape(self):
        r = TestRunResult(returncode=0, stdout="o", stderr="e", duration=1.5)
        d = r.to_dict()
        assert d == {
            "returncode": 0,
            "stdout": "o",
            "stderr": "e",
            "duration": 1.5,
        }
        assert r.success


class TestTreeKill:
    """BL-TEST-003 — a timed-out process must not leave orphan children."""

    @pytest.mark.timeout(60)
    def test_timeout_kills_process_tree(self, tmp_path):
        """Grandchild process must not survive the parent's timeout."""
        marker = tmp_path / "grandchild_survived"
        cmd = [
            sys.executable,
            "-c",
            (
                "import subprocess, sys, time\n"
                "subprocess.Popen([sys.executable, '-c', "
                f'\'import time,pathlib; time.sleep(2); pathlib.Path(r"{marker}")'
                '.write_text("x")\'])\n'
                "time.sleep(60)\n"
            ),
        ]
        runner = SubprocessRunner()
        result = runner.run(cmd, timeout=1)

        assert not result.success
        # If the grandchild survived the tree-kill it writes the marker
        # ~2s after spawn; wait beyond that to prove it never arrived.
        time.sleep(4)
        assert not marker.exists(), "grandchild orphan survived the timeout"


class TestRateLimitResetHeader:
    """X-RateLimit-Reset must be the real window expiry, not now+60."""

    def test_reset_reflects_oldest_hit(self):
        import asyncio
        import time as _time

        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
            RateLimitMiddleware,
        )

        store = InMemorySlidingWindowStore()
        mw = RateLimitMiddleware(app=Mock(), per_minute=5, store=store)
        key = "ip:1.2.3.4"

        # Seed a hit ~30s ago inside the window (store uses epoch clock)
        store._hits[key].append(_time.time() - 30)

        _, _, _, reset_epoch = asyncio.run(mw._allow(key, 5))
        # Window resets when the 30s-old hit expires → ~now+30, not now+60
        assert reset_epoch <= _time.time() + 31
        assert reset_epoch > _time.time()


class TestCleanupServiceFase1:
    """BL-CLEAN-001..005 — retention source, dry-run, active-guard, errors."""

    @staticmethod
    def _svc(tmp_path, config_provider=None):
        ps = Mock()
        ps.backup_dir = tmp_path / "backups"
        ps.results_dir = tmp_path / "results"
        ps.logs_dir = tmp_path / "logs"
        for d in (ps.backup_dir, ps.results_dir, ps.logs_dir):
            d.mkdir(parents=True, exist_ok=True)
        return CleanupService(path_service=ps, config_provider=config_provider), ps

    @staticmethod
    def _aged(path: Path, days: int):
        path.write_text("x")
        old = (datetime.now(UTC) - timedelta(days=days)).timestamp()
        os.utime(path, (old, old))  # Path.touch(n) sets MODE, not mtime

    def test_dry_run_counts_without_deleting(self, tmp_path):
        svc, ps = self._svc(tmp_path)
        old = ps.backup_dir / "old.tar.gz"
        self._aged(old, 100)

        result = svc.cleanup_old_artifacts(retention_days=30, dry_run=True, min_keep=0)

        assert result["backups_cleaned"] == 1
        assert old.exists(), "dry-run deleted a file"

    def test_min_keep_preserves_newest_expired(self, tmp_path):
        svc, ps = self._svc(tmp_path)
        newest = ps.backup_dir / "newest.tar.gz"
        older = ps.backup_dir / "older.tar.gz"
        self._aged(newest, 60)
        self._aged(older, 90)

        result = svc.cleanup_old_artifacts(retention_days=30)  # min_keep=1 default

        assert result["backups_cleaned"] == 1
        assert result["skipped"] == 1
        assert newest.exists(), "active-guard failed: newest backup deleted"
        assert not older.exists()

    def test_env_retention_fallback(self, tmp_path, monkeypatch):
        """Without provider/param, RETENTION_DAYS env var is the source."""
        monkeypatch.setenv("RETENTION_DAYS", "10")
        svc, ps = self._svc(tmp_path)
        f = ps.logs_dir / "mid.log"
        self._aged(f, 20)

        result = svc.cleanup_old_artifacts(min_keep=0)

        assert result["logs_cleaned"] == 1  # 20 days old > 10-day retention
        assert not f.exists()

    def test_errors_explicitly_reported(self, tmp_path):
        from unittest.mock import patch

        svc, ps = self._svc(tmp_path)
        f = ps.results_dir / "old.json"
        self._aged(f, 100)

        with patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            result = svc.cleanup_old_artifacts(retention_days=30, min_keep=0)

        assert result["errors"] == 1
        assert result["results_cleaned"] == 0
