"""Backup service for SOAR Lab API."""

import re
from contextlib import suppress
from datetime import UTC, datetime
from operator import itemgetter
from typing import Any

from soar_lab.common.exceptions import ValidationError
from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import BackupDriver, BackupStorageProvider

logger = get_logger(__name__)


class BackupService:
    """Service class for backup operations with injected dependencies."""

    def __init__(self, driver: BackupDriver, storage: BackupStorageProvider) -> None:
        if not storage:
            raise ValueError("storage (BackupStorageProvider) is required for BackupService")
        self.driver = driver
        self.storage = storage

    def create(self, user: str | None = None) -> dict[str, str]:
        """Create a backup using injected dependencies."""
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"soar_backup_{timestamp}.tar.gz"

            # Use storage provider to get backup directory and ensure it exists
            backup_dir = self.storage.get_backup_directory()
            self.storage.ensure_directory_exists(backup_dir)

            # Create backup using driver with storage-provided paths
            backup_path = self.storage.join_path(backup_dir, backup_filename)
            base_dir = self.storage.get_base_directory()
            self.driver.create(source_dir=base_dir, dest_path=backup_path)

            # Store backup metadata using BackupStorageProvider
            self.storage.store_backup_metadata(
                backup_filename,
                {
                    "created_by": user or "unknown",
                    "created_at": timestamp,
                    "size": self.storage.get_file_size(backup_path),
                },
            )

            # Audit logging
            audit_info = (
                f"backup_name={backup_filename}, user={user or 'unknown'}, timestamp={timestamp}"
            )
            logger.info(f"Backup created successfully: {audit_info}")

            return {"filename": backup_filename, "message": "Backup created successfully"}

        except Exception:
            logger.exception("Error creating backup")
            raise

    def list_backups(self) -> dict[str, Any]:
        """List available backups using injected storage."""
        try:
            # Use storage provider to get backup directory and check if it exists
            backup_dir = self.storage.get_backup_directory()
            if not self.storage.directory_exists(backup_dir):
                return {"backups": []}

            # Use storage provider to list backup files
            backup_files = self.storage.list_files(backup_dir, pattern="*.tar.gz")

            backups = []
            for backup_file in backup_files:
                # Get file metadata from storage provider
                file_info = self.storage.get_file_info(
                    self.storage.join_path(backup_dir, backup_file)
                )
                if file_info:
                    size_mb = round(file_info.get("size", 0) / (1024 * 1024), 2)
                    mtime = file_info.get("modified_time", 0)
                    date_str = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y-%m-%d %H:%M")

                    backups.append(
                        {
                            "name": backup_file,
                            "size": f"{size_mb} MB",
                            "date": date_str,
                            "_mtime": mtime,
                        }
                    )

            # Sort by mtime (newest first) — the display string has only
            # minute resolution and misorders same-minute backups.
            backups.sort(key=itemgetter("_mtime"), reverse=True)
            for b in backups:
                b.pop("_mtime", None)

            return {"backups": backups}

        except Exception:
            logger.exception("Error listing backups")
            raise

    _BACKUP_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*\.tar\.gz$")

    def restore(self, backup_name: str, user: str | None = None) -> dict[str, str]:
        """Restore from backup using injected dependencies."""
        if not isinstance(backup_name, str) or not self._BACKUP_NAME_RE.match(backup_name):
            raise ValidationError(f"Invalid backup name: {backup_name!r}")
        try:
            # Use storage provider to get backup directory and construct path
            backup_dir = self.storage.get_backup_directory()
            backup_path = self.storage.join_path(backup_dir, backup_name)

            # Use storage provider to check if backup exists
            if not self.storage.file_exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_name}")

            # P0.3: verify integrity (tar -tzf + sha256 sidecar) BEFORE
            # extracting — a corrupt archive must not clobber live files.
            if hasattr(self.driver, "verify"):
                self.driver.verify(backup_path)

            # Use driver to extract backup with storage-provided base directory
            base_dir = self.storage.get_base_directory()
            self.driver.extract(archive_path=backup_path, dest_dir=base_dir)

            # Log restore operation using BackupStorageProvider
            self.storage.log_restore_operation(
                backup_name,
                {
                    "restored_by": user or "unknown",
                    "restored_at": datetime.now(UTC).isoformat(),
                },
            )

            # Audit logging
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            audit_info = (
                f"backup_name={backup_name}, user={user or 'unknown'}, timestamp={timestamp}"
            )
            logger.info(f"Backup restored successfully: {audit_info}")

            return {"message": f"Backup {backup_name} restored successfully"}

        except FileNotFoundError:
            logger.exception("Backup file not found")
            raise
        except Exception:
            logger.exception("Error restoring backup")
            raise

    def validate(self, backup_name: str) -> dict[str, Any]:
        """P0.3: dry-run restore validation (``restore --validate``).

        Checks the archive exists, ``tar -tzf`` passes and the SHA-256
        sidecar matches — without touching the live tree.
        """
        if not isinstance(backup_name, str) or not self._BACKUP_NAME_RE.match(backup_name):
            raise ValidationError(f"Invalid backup name: {backup_name!r}")
        backup_dir = self.storage.get_backup_directory()
        backup_path = self.storage.join_path(backup_dir, backup_name)
        if not self.storage.file_exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_name}")
        if not hasattr(self.driver, "verify"):
            return {"valid": None, "detail": "driver does not support verification"}
        try:
            self.driver.verify(backup_path)
        except Exception as exc:
            return {"valid": False, "detail": str(exc)}
        return {"valid": True, "detail": "archive + checksum verified"}

    def apply_retention(self, keep: int = 7) -> dict[str, Any]:
        """P0.3: retention — keep the newest ``keep`` archives, delete the rest.

        Count-based (GFS-lite: schedule cadence comes from the caller —
        daily/weekly/monthly cron jobs pass different ``keep`` values).
        Deletes the ``.sha256`` sidecar alongside each archive.
        """
        if keep < 1:
            raise ValidationError("retention keep must be >= 1")
        backup_dir = self.storage.get_backup_directory()
        if not self.storage.directory_exists(backup_dir):
            return {"deleted": []}
        files = [
            f
            for f in self.storage.list_files(backup_dir, pattern="*.tar.gz")
            if not f.endswith(".sha256")
        ]
        # newest first via mtime
        files.sort(
            key=lambda f: (
                self.storage.get_file_info(self.storage.join_path(backup_dir, f)) or {}
            ).get("modified_time", 0),
            reverse=True,
        )
        stale = files[keep:]
        deleted: list[str] = []
        for name in stale:
            for suffix in ("", ".sha256"):
                path = self.storage.join_path(backup_dir, name + suffix)
                with suppress(FileNotFoundError):
                    self.storage.delete_file(path)
                    deleted.append(name + suffix)
        if deleted:
            logger.info("Backup retention: removed %d file(s): %s", len(deleted), deleted)
        return {"deleted": deleted}
