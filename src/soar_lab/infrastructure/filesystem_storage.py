"""FilesystemStorage - production implementation of StorageProvider.

This adapter provides a filesystem-backed implementation of StorageProvider
for production use. Tests should use InMemoryStorage instead.
"""

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import ConfigProvider

__all__ = ["FilesystemStorage", "UnsafeStorageKey"]

logger = get_logger(__name__)


class UnsafeStorageKey(ValueError):
    """Raised when a storage key would resolve outside the storage base."""


class FilesystemStorage:
    """Filesystem implementation of StorageProvider for production.

    Key-based operations (``write``/``read``/``exists``/``delete``/
    ``list_keys``) confine the resolved path to ``self._base``: absolute
    keys, ``..`` segments and escaping symlinks raise
    :class:`UnsafeStorageKey`. The ``*_file``/``*_directory`` helpers take
    explicit paths and are intentionally unscoped (backup service contract).
    """

    def __init__(
        self, base_dir: str | None = None, config_provider: ConfigProvider | None = None
    ) -> None:
        if base_dir:
            self._base = Path(base_dir)
        elif config_provider:
            self._base = Path(config_provider.get("base_dir", "."))
        else:
            # Require explicit config or base_dir - no fallback to global settings
            raise ValueError("base_dir or config_provider must be supplied")
        self._base.mkdir(parents=True, exist_ok=True)
        self._base = self._base.resolve()
        self._config_provider = config_provider

    def _resolve_key(self, key: str) -> Path:
        """Resolve ``key`` under ``self._base`` or raise :class:`UnsafeStorageKey`."""
        if not key or key.strip() in {"", ".", ".."}:
            raise UnsafeStorageKey(f"invalid storage key: {key!r}")
        # NUL is invalid on every platform; control chars and Windows
        # device names make Path.resolve()/stat() raise raw errors that
        # would escape this guard's contract.
        if "\x00" in key or any(ord(c) < 0x20 for c in key):
            raise UnsafeStorageKey(f"storage key contains control character: {key!r}")
        candidate = Path(key)
        if candidate.is_absolute():
            raise UnsafeStorageKey(f"absolute storage key rejected: {key!r}")
        try:
            resolved = (self._base / candidate).resolve()
        except (OSError, ValueError) as exc:
            raise UnsafeStorageKey(f"unresolvable storage key: {key!r}") from exc
        try:
            resolved.relative_to(self._base)
        except ValueError as exc:
            raise UnsafeStorageKey(f"storage key escapes base: {key!r}") from exc
        # A key must name a file *inside* the base — one that resolves to
        # the base directory itself ("./", "a/../") is invalid too: write
        # or delete on a directory path would fail with raw OS errors.
        if resolved == self._base:
            raise UnsafeStorageKey(f"storage key resolves to base directory: {key!r}")
        return resolved

    def write(self, key: str, data: bytes) -> None:
        """Write data to a file atomically.

        Data is written to a sibling temp file, fsynced and then
        ``os.replace``d over the target, so a crash mid-write can never
        leave a truncated/corrupt file at ``key`` — readers see either the
        old content or the new content, never a partial write.
        """
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f"{target.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                Path(tmp_name).unlink()
            raise

    def read(self, key: str) -> bytes:
        """Read data from a file."""
        return self._resolve_key(key).read_bytes()

    def read_file(self, key: str) -> str | None:
        """Read file content as string.

        Returns ``None`` only when the file does not exist; I/O and decoding
        failures propagate so callers can distinguish absence from error.
        """
        try:
            return self._resolve_key(key).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        return self._resolve_key(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        """List all files with a prefix."""
        resolved_prefix = str(self._resolve_key(prefix)) if prefix else str(self._base)
        return [
            f.name
            for f in Path(resolved_prefix).parent.glob(f"{Path(resolved_prefix).name}*")
            if self._base in f.resolve().parents or f.resolve() == self._base
        ]

    def delete(self, key: str) -> None:
        """Delete a file."""
        self._resolve_key(key).unlink(missing_ok=True)

    # StorageProviderInterface methods for backup service
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists."""
        Path(path).mkdir(parents=True, exist_ok=True)

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        return Path(path).stat().st_size

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists."""
        return Path(path).exists() and Path(path).is_dir()

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return Path(path).exists() and Path(path).is_file()

    def list_files(self, directory: str, pattern: str = "*") -> list[str]:
        """List files in directory with pattern."""
        return [f.name for f in Path(directory).glob(pattern) if f.is_file()]

    def get_file_info(self, path: str) -> dict[str, Any] | None:
        """Get file information, or ``None`` when the path does not exist."""
        if not Path(path).exists():
            return None
        stat = Path(path).stat()
        return {"size": stat.st_size, "modified_time": stat.st_mtime, "created_time": stat.st_ctime}

    def delete_file(self, path: str) -> bool:
        """Delete a file.

        Returns ``True`` on success or when the file is already absent;
        ``False`` when deletion failed (the failure is logged — it is
        never silently swallowed).
        """
        try:
            Path(path).unlink(missing_ok=True)
            return True
        except Exception as exc:
            logger.warning(f"Failed to delete file {path}: {exc}")
            return False

    def store_backup_metadata(self, filename: str, metadata: dict[str, Any]) -> None:
        """Store backup metadata to a JSON file."""
        metadata_file = self._resolve_key(f"{filename}.metadata.json")

        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def log_restore_operation(self, backup_name: str, metadata: dict[str, Any]) -> None:
        """Log restore operation to a log file."""
        log_file = self._base / "restore_operations.log"

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "backup_name": backup_name,
            "metadata": metadata,
        }
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

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
