"""P0.1/P0.2/P0.3: watcher Zero-Trust, socket-inject gating, backup security."""

from __future__ import annotations

import importlib
import io
import sys
import tarfile
from unittest.mock import Mock, patch

import pytest


def _watcher(monkeypatch=None, **env):
    """Import network_watcher fresh with the given env (module reads env at import)."""
    if monkeypatch:
        for k, v in env.items():
            monkeypatch.setenv(k, v)
    sys.modules.pop("soar_lab.infrastructure.network_watcher.network_watcher", None)
    return importlib.import_module("soar_lab.infrastructure.network_watcher.network_watcher")


class TestZeroTrustVerification:
    """P0.1: name-only trust is spoofable — labels/ownership must gate."""

    def test_labelled_container_always_allowed(self):
        nw = _watcher()
        ok, why = nw.verify_managed_container("anything", labels={"com.shuffle.managed": "true"})
        assert ok and "label" in why

    def test_name_match_without_label_hybrid_allows(self):
        nw = _watcher()
        ok, _ = nw.verify_managed_container("worker-abc", labels={})
        assert ok  # hybrid default: name pattern is the lab fallback

    def test_label_mode_rejects_name_spoof(self, monkeypatch):
        nw = _watcher(monkeypatch, WATCHER_TRUST_MODE="label")
        ok, why = nw.verify_managed_container("worker-evil", labels={})
        assert not ok and "label" in why

    def test_spoofed_name_with_wrong_label_rejected(self):
        nw = _watcher()
        ok, _ = nw.verify_managed_container("nginx", labels={"com.shuffle.managed": "false"})
        assert not ok

    def test_image_allowlist_enforced_in_hybrid(self, monkeypatch):
        nw = _watcher(monkeypatch, WATCHER_MANAGED_IMAGES="shuffle-orborus,ghcr.io/shuffle")
        ok, _ = nw.verify_managed_container("worker-x", labels={}, image="malicious/pwn:latest")
        assert not ok
        ok2, _ = nw.verify_managed_container(
            "worker-y", labels={}, image="shuffle-orborus-worker:1"
        )
        assert ok2

    def test_name_mode_still_works_but_is_flagged(self, monkeypatch):
        nw = _watcher(monkeypatch, WATCHER_TRUST_MODE="name")
        ok, why = nw.verify_managed_container("worker-z", labels={})
        assert ok and "INSECURE" in why

    def test_attach_rejects_unverified_container(self, monkeypatch):
        nw = _watcher(monkeypatch, WATCHER_TRUST_MODE="label")
        client = Mock()
        net = Mock()
        client.networks.get.return_value = net
        container = Mock()
        container.name = "worker-spoofed"
        container.attrs = {"Config": {"Labels": {}, "Image": "x"}}
        client.containers.get.return_value = container

        nw.attach(client, "cid", "worker-spoofed", "net")
        net.connect.assert_not_called()
        assert nw._REJECTED["count"] == 1


class TestSocketInjectGating:
    """P0.2: daemon-socket injection is OFF by default now."""

    def test_socket_inject_disabled_by_default(self):
        nw = _watcher()
        assert nw.SOCKET_INJECT_ENABLED is False

    def test_socket_inject_can_be_enabled_explicitly(self, monkeypatch):
        nw = _watcher(monkeypatch, WATCHER_DOCKER_SOCKET_INJECT="true")
        assert nw.SOCKET_INJECT_ENABLED is True


class TestWatchReconnect:
    """P0.1: the event loop is supervised with backoff+jitter."""

    def test_reconnects_after_stream_error(self, monkeypatch):
        nw = _watcher()
        calls = {"n": 0}

        def dispatch(cli):
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("daemon gone")
            raise KeyboardInterrupt  # stop the loop deterministically

        with (
            patch.object(nw.docker, "from_env", return_value=Mock()),
            patch("time.sleep") as sleep,
            pytest.raises(KeyboardInterrupt),
        ):
            nw._watch_forever(dispatch)
        assert calls["n"] == 3
        assert sleep.call_count == 2
        # backoff values grow with attempts (full jitter: 0..cap)
        first_max, second_max = 1.0, 2.0
        assert 0 <= sleep.call_args_list[0].args[0] <= first_max
        assert 0 <= sleep.call_args_list[1].args[0] <= second_max


class TestBackupSecurity:
    """P0.3: exclusions, checksums, verification, retention."""

    def test_secret_files_excluded(self):
        from soar_lab.infrastructure.tar_backup_driver import _EXCLUDES

        for pat in (".env", ".env.*", "*.pem", "*.key", "*.crt", "*.pfx", "secrets"):
            assert f"--exclude={pat}" in _EXCLUDES

    def test_create_writes_checksum_and_verifies(self, tmp_path):
        from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

        src = tmp_path / "src"
        src.mkdir()
        (src / "data.txt").write_text("payload")
        dest = tmp_path / "b.tar.gz"
        driver = TarBackupDriver()
        driver.create(str(src), str(dest))
        assert dest.exists() and (tmp_path / "b.tar.gz.sha256").exists()

    def test_verify_detects_corruption(self, tmp_path):
        from soar_lab.common.exceptions import BackupError
        from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

        bad = tmp_path / "bad.tar.gz"
        bad.write_bytes(b"not a real archive")
        with pytest.raises(BackupError):
            TarBackupDriver().verify(str(bad))

    def test_verify_detects_checksum_mismatch(self, tmp_path):
        from soar_lab.common.exceptions import BackupError
        from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

        # build a real archive then tamper the sidecar
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            data = b"x"
            info = tarfile.TarInfo("f")
            info.size = 1
            tf.addfile(info, io.BytesIO(data))
        arc = tmp_path / "a.tar.gz"
        arc.write_bytes(buf.getvalue())
        (tmp_path / "a.tar.gz.sha256").write_text("deadbeef  a.tar.gz\n")
        with pytest.raises(BackupError, match="checksum"):
            TarBackupDriver().verify(str(arc))

    def test_restore_validate_dry_run(self):
        from soar_lab.application.use_cases.backup_service import BackupService

        driver, storage = Mock(), Mock()
        storage.get_backup_directory.return_value = "/b"
        storage.join_path.side_effect = lambda *p: "/".join(p)
        storage.file_exists.return_value = True
        svc = BackupService(driver, storage)
        out = svc.validate("ok.tar.gz")
        assert out["valid"] is True
        driver.verify.assert_called_once()

    def test_retention_keeps_newest(self):
        from soar_lab.application.use_cases.backup_service import BackupService

        storage = Mock()
        storage.get_backup_directory.return_value = "/b"
        storage.join_path.side_effect = lambda *p: "/".join(p)
        storage.directory_exists.return_value = True
        storage.list_files.return_value = ["b1.tar.gz", "b2.tar.gz", "b3.tar.gz"]
        storage.get_file_info.side_effect = lambda p: {
            "/b/b1.tar.gz": {"modified_time": 1},
            "/b/b2.tar.gz": {"modified_time": 2},
            "/b/b3.tar.gz": {"modified_time": 3},
        }[p]
        svc = BackupService(Mock(), storage)
        out = svc.apply_retention(keep=2)
        assert "/b/b1.tar.gz" in [storage.join_path("/b", f) for f in ["b1.tar.gz"]]
        assert "b1.tar.gz" in out["deleted"] and "b3.tar.gz" not in out["deleted"]
