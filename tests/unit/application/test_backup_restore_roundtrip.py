"""OP3: real backup→clobber→restore round-trip (not just creation).

Creates a backup of a tmp base dir, destroys a file, restores the
archive and verifies the bytes come back — the check `make restore`
cannot fake. Requires a `tar` binary (bsdtar on Windows, GNU tar on
Linux CI); skipped where absent.
"""

import shutil

import pytest

from soar_lab.application.use_cases.backup_service import BackupService
from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
from soar_lab.infrastructure.tar_backup_driver import TarBackupDriver

pytestmark = pytest.mark.skipif(
    shutil.which("tar") is None, reason="tar binary required for round-trip"
)


class _CP:
    def __init__(self, backup_dir):
        self._backup_dir = backup_dir

    def get(self, key, default=None):
        if key == "BACKUP_DIR":
            return self._backup_dir
        return default


def test_backup_restore_recovers_file_contents(tmp_path):
    base = tmp_path / "base"
    backup_dir = tmp_path / "backups"
    (base / "data").mkdir(parents=True)
    payload = b"SELECT * FROM alerts;"
    (base / "data" / "alerts.db").write_bytes(payload)

    storage = FilesystemStorage(base_dir=str(base), config_provider=_CP(str(backup_dir)))
    service = BackupService(driver=TarBackupDriver(), storage=storage)

    created = service.create(user="test")
    backup_name = created["filename"]
    assert (backup_dir / backup_name).exists()
    assert (backup_dir / f"{backup_name}.sha256").exists()

    # Disaster: the live file is destroyed.
    (base / "data" / "alerts.db").write_bytes(b"CORRUPTED")

    result = service.restore(backup_name, user="test")
    assert "restored" in result["message"]
    assert (base / "data" / "alerts.db").read_bytes() == payload


def test_restore_rejects_tampered_archive(tmp_path):
    base = tmp_path / "base"
    backup_dir = tmp_path / "backups"
    base.mkdir()
    (base / "f.txt").write_text("x")

    storage = FilesystemStorage(base_dir=str(base), config_provider=_CP(str(backup_dir)))
    service = BackupService(driver=TarBackupDriver(), storage=storage)
    backup_name = service.create(user="test")["filename"]

    # Tamper: flip a byte inside the tarball → sha256 sidecar mismatch.
    archive = backup_dir / backup_name
    blob = bytearray(archive.read_bytes())
    blob[len(blob) // 2] ^= 0xFF
    archive.write_bytes(bytes(blob))

    from soar_lab.common.exceptions import BackupError

    with pytest.raises((BackupError, Exception)):
        service.restore(backup_name, user="test")
