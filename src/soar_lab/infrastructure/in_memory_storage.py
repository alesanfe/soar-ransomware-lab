"""In-memory StorageProvider for unit tests.

This adapter provides a volatile implementation of StorageProvider
that requires no filesystem, no permissions, and no disk I/O.
Perfect for fast, isolated unit tests in environments without artifacts/.
"""

import time
from typing import List, Dict, Any


class InMemoryStorage:
    """In-memory implementation of StorageProvider for testing.

    100% volatile: no disk, no artifacts/, no permission issues.
    """

    def __init__(self):
        self._store: Dict[str, bytes] = {}
        self._file_info: Dict[str, Dict[str, Any]] = {}
        self._directories: set = set()

    def write(self, key: str, data: bytes) -> None:
        """Write data to a key in memory."""
        self._store[key] = data
        self._file_info[key] = {
            'size': len(data),
            'modified_time': time.time(),
            'created_time': time.time()
        }

    def read(self, key: str) -> bytes:
        """Read data from a key in memory."""
        if key not in self._store:
            raise FileNotFoundError(f"Key not found: {key}")
        return self._store[key]

    def exists(self, key: str) -> bool:
        """Check if a key exists in memory."""
        return key in self._store

    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with a prefix in memory."""
        return [k for k in self._store if k.startswith(prefix)]

    def delete(self, key: str) -> None:
        """Delete a key from memory."""
        self._store.pop(key, None)
        self._file_info.pop(key, None)

    def clear(self) -> None:
        """Clear all keys (useful for test isolation)."""
        self._store.clear()
        self._file_info.clear()
        self._directories.clear()

    # StorageProviderInterface methods for backup service
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists in memory."""
        self._directories.add(path)

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        if path in self._file_info:
            return self._file_info[path]['size']
        return 0

    def directory_exists(self, path: str) -> bool:
        """Check if directory exists in memory."""
        return path in self._directories

    def file_exists(self, path: str) -> bool:
        """Check if file exists in memory."""
        return path in self._store

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory with pattern."""
        if pattern == "*":
            return [f for f in self._store.keys() if f.startswith(directory)]
        return [f for f in self._store.keys() if f.startswith(directory) and pattern.replace("*", "") in f]

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        return self._file_info.get(path, None)

    def delete_file(self, path: str) -> bool:
        """Delete a file from memory."""
        try:
            self.delete(path)
            return True
        except Exception:
            return False

    def store_backup_metadata(self, filename: str, metadata: Dict[str, Any]) -> None:
        """Store backup metadata (placeholder)."""
        pass  # Could implement metadata storage if needed

    def log_restore_operation(self, backup_name: str, metadata: Dict[str, Any]) -> None:
        """Log restore operation (placeholder)."""
        pass  # Could implement restore logging if needed

    def get_backup_directory(self) -> str:
        """Get backup directory (in-memory)."""
        return "/tmp/backups"

    def get_base_directory(self) -> str:
        """Get base directory (in-memory)."""
        return "/tmp/base"

    def join_path(self, *parts: str) -> str:
        """Join path parts in an OS-agnostic way (in-memory)."""
        # Use forward slash for in-memory paths (OS-agnostic)
        return "/".join(parts)
