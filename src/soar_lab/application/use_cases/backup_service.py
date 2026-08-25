"""Backup service for SOAR Lab API."""

from datetime import UTC, datetime
from typing import Any

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

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
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
                    date_str = datetime.fromtimestamp(
                        file_info.get("modified_time", 0), tz=UTC
                    ).strftime("%Y-%m-%d %H:%M")

                    backups.append({"name": backup_file, "size": f"{size_mb} MB", "date": date_str})

            # Sort by date (newest first)
            backups.sort(key=lambda x: x["date"], reverse=True)

            return {"backups": backups}

        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            raise

    def restore(self, backup_name: str, user: str | None = None) -> dict[str, str]:
        """Restore from backup using injected dependencies."""
        try:
            # Use storage provider to get backup directory and construct path
            backup_dir = self.storage.get_backup_directory()
            backup_path = self.storage.join_path(backup_dir, backup_name)

            # Use storage provider to check if backup exists
            if not self.storage.file_exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_name}")

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

        except FileNotFoundError as e:
            logger.error(f"Backup file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise
