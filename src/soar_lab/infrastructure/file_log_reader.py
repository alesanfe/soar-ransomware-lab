"""File Log Reader - Infrastructure implementation of LogReader port.

This adapter encapsulates filesystem access for log file reading,
allowing the application layer to remain infrastructure-agnostic.
"""

from typing import Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class FileLogReader:
    """Infrastructure implementation of LogReader port for file-based logs."""

    def __init__(self, path_service: object):
        """
        Initialize the file log reader.

        Args:
            path_service: PathService instance for log file paths (required).
        """
        if not path_service:
            raise ValueError("path_service is required for FileLogReader")
        self._path_service = path_service

    def read_log_file(self, log_path: str) -> str:
        """
        Read log file content.

        Args:
            log_path: Path to the log file

        Returns:
            Log file content as string
        """
        try:
            from pathlib import Path
            path = Path(log_path)
            if not path.exists():
                logger.warning(f"Log file not found: {log_path}")
                return ""
            return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")
            return ""

    def get_default_log_path(self) -> str:
        """
        Get default log file path.

        Returns:
            Default log file path as string
        """
        return str(self._path_service.notify_log_file)
