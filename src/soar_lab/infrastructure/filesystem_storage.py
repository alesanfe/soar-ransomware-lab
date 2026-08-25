"""FilesystemStorage - production implementation of StorageProvider.

This adapter provides a filesystem-backed implementation of StorageProvider
for production use. Tests should use InMemoryStorage instead.
"""

import os
from datetime import UTC
from pathlib import Path
from typing import Any

__all__ = ["FilesystemStorage"]


class FilesystemStorage:
    """Filesystem implementation of StorageProvider for production."""

    def __init__(self, base_dir: str | None = None, config_provider: object | None = None) -> None:
        if base_dir:
            self._base = Path(base_dir)
        elif config_provider:
            self._base = Path(config_provider.get("base_dir", "."))
        else:
            # Require explicit config or base_dir - no fallback to global settings
            raise ValueError("base_dir or config_provider must be supplied")
        self._base.mkdir(parents=True, exist_ok=True)
        self._config_provider = config_provider

    def write(self, key: str, data: bytes) -> None:
        """Write data to a file."""
        (self._base / key).parent.mkdir(parents=True, exist_ok=True)
        (self._base / key).write_bytes(data)

    def read(self, key: str) -> bytes:
        """Read data from a file."""
        return (self._base / key).read_bytes()

    def read_file(self, key: str) -> str:
        """Read file content as string."""
        try:
            return (self._base / key).read_text(encoding="utf-8")
        except Exception:
            return None

    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        return (self._base / key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all files with a prefix."""
        return [f.name for f in self._base.glob(f"{prefix}*")]

    def delete(self, key: str) -> None:
        """Delete a file."""
        (self._base / key).unlink(missing_ok=True)

    # StorageProviderInterface methods for backup service
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists."""
        Path(path).mkdir(parents=True, exist_ok=True)

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        return os.path.getsize(path)

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return Path(path).exists() and Path(path).is_dir()

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return Path(path).exists() and Path(path).is_file()

    def list_files(self, directory: str, pattern: str = "*") -> list[str]:
        """List files in directory with pattern."""
        return [f.name for f in Path(directory).glob(pattern) if f.is_file()]

    def get_file_info(self, path: str) -> dict[str, Any]:
        """Get file information."""
        if not Path(path).exists():
            return None
        stat = Path(path).stat()
        return {"size": stat.st_size, "modified_time": stat.st_mtime, "created_time": stat.st_ctime}

    def delete_file(self, path: str) -> bool:
        """Delete a file."""
        try:
            Path(path).unlink(missing_ok=True)
            return True
        except Exception:
            return False

    def store_backup_metadata(self, filename: str, metadata: dict[str, Any]) -> None:
        """Store backup metadata to a JSON file."""
        metadata_file = self._base / f"{filename}.metadata.json"
        import json

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def log_restore_operation(self, backup_name: str, metadata: dict[str, Any]) -> None:
        """Log restore operation to a log file."""
        log_file = self._base / "restore_operations.log"
        import json
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "backup_name": backup_name,
            "metadata": metadata,
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_backup_directory(self) -> str:
        """Get backup directory from config_provider."""
        if not self._config_provider:
            raise ValueError("config_provider is required for get_backup_directory")
        return self._config_provider.get("BACKUP_DIR", str(self._base / "backups"))

    def get_base_directory(self) -> str:
        """Get base directory from settings."""
        return str(self._base)

    def join_path(self, *parts: str) -> str:
        """Join path parts in an OS-agnostic way."""
        return str(Path(*parts))
