"""File Utilities - Infrastructure file operations.

This module provides pure file system utilities isolated from the application layer.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional


def calculate_file_checksum(file_path: str, algorithm: str = 'sha256') -> str:
    """
    Calculate checksum of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm ('sha256', 'md5', 'sha1')
        
    Returns:
        Hexadecimal checksum string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    hash_func = getattr(hashlib, algorithm)()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure directory exists, creating if necessary.
    
    Args:
        directory_path: Path to directory
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    return os.path.getsize(file_path)


def file_exists(file_path: str) -> bool:
    """
    Check if file exists.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists() and Path(file_path).is_file()


def directory_exists(directory_path: str) -> bool:
    """
    Check if directory exists.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        True if directory exists, False otherwise
    """
    return Path(directory_path).exists() and Path(directory_path).is_dir()


def list_files(directory: str, pattern: str = "*") -> list:
    """
    List files in directory matching pattern.
    
    Args:
        directory: Directory path
        pattern: Glob pattern (default: "*")
        
    Returns:
        List of file names
    """
    return [f.name for f in Path(directory).glob(pattern) if f.is_file()]


def get_file_info(file_path: str) -> dict:
    """
    Get file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict with file information
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    stat = Path(file_path).stat()
    return {
        'size': stat.st_size,
        'modified_time': stat.st_mtime,
        'created_time': stat.st_ctime,
        'is_file': Path(file_path).is_file(),
        'is_dir': Path(file_path).is_dir()
    }


def delete_file(file_path: str) -> bool:
    """
    Delete a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(file_path).unlink(missing_ok=True)
        return True
    except Exception:
        return False


def read_file_content(file_path: str, encoding: str = 'utf-8') -> str:
    """
    Read file content as string.
    
    Args:
        file_path: Path to the file
        encoding: File encoding
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file cannot be decoded
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_file_content(file_path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    Write content to file.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding
    """
    ensure_directory_exists(str(Path(file_path).parent))

    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)


def copy_file(source: str, destination: str) -> None:
    """
    Copy file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
    """
    import shutil
    ensure_directory_exists(str(Path(destination).parent))
    shutil.copy2(source, destination)


def move_file(source: str, destination: str) -> None:
    """
    Move file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
    """
    import shutil
    ensure_directory_exists(str(Path(destination).parent))
    shutil.move(source, destination)
