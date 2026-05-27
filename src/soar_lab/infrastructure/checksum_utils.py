"""Checksum utilities for file integrity verification.

This module provides infrastructure-level utilities for calculating file checksums,
separating I/O operations from domain logic.
"""

import hashlib
from pathlib import Path


def calculate_file_checksum(file_path: str | Path) -> str:
    """Calculate SHA-256 checksum of a file.

    Args:
        file_path: Path to the file to calculate checksum for

    Returns:
        SHA-256 hex digest string

    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    file_path = Path(file_path)
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
