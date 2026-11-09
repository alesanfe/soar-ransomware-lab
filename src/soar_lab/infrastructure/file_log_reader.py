"""File Log Reader - Infrastructure implementation of LogReader port.

This adapter encapsulates filesystem access for log file reading,
allowing the application layer to remain infrastructure-agnostic.
"""

from pathlib import Path

from soar_lab.config.logging import get_logger

__all__ = ["FileLogReader"]

logger = get_logger(__name__)


class FileLogReader:
    """Infrastructure implementation of LogReader port for file-based logs."""

    def __init__(self, path_service: object) -> None:
        """Initialize the file log reader.

        Args:
            path_service: PathService instance for log file paths (required).
        """
        if not path_service:
            raise ValueError("path_service is required for FileLogReader")
        self._path_service = path_service

    def read_log_file(self, log_path: str, max_bytes: int = 512 * 1024) -> str:
        """Read log file content, bounded to the last ``max_bytes``.

        Unbounded reads turn ``/ws/logs`` into a memory-exhaustion vector —
        a multi-GB log would be loaded whole per request.

        Args:
            log_path: Path to the log file
            max_bytes: Maximum bytes to return (tail of the file). The first
                partial line after the cut point is discarded.

        Returns:
            Log file content as string (tailed when oversized)
        """
        try:

            path = Path(log_path)
            if not path.exists():
                logger.warning(f"Log file not found: {log_path}")
                return ""
            size = path.stat().st_size
            if size <= max_bytes:
                return path.read_text(encoding="utf-8")
            with path.open("rb") as fh:
                fh.seek(-max_bytes, 2)
                tail = fh.read().decode("utf-8", errors="replace")
            first_newline = tail.find("\n")
            return tail[first_newline + 1 :] if first_newline != -1 else tail
        except Exception:
            logger.exception(f"Error reading log file {log_path}")
            return ""

    def get_default_log_path(self) -> str:
        """Get default log file path.

        Returns:
            Default log file path as string
        """
        return str(self._path_service.notify_log_file)
