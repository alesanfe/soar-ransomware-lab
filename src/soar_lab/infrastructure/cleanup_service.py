"""Cleanup Service for managing artifact retention.

This service provides automated cleanup of old artifacts based on retention policies,
preventing artifact accumulation from hiding real code problems.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class CleanupService:
    """Service for cleaning up old artifacts based on retention policies."""

    def __init__(self, path_service: object, config_provider: object = None):
        """Initialize the cleanup service.

        Args:
            path_service: PathService instance for path management (required)
            config_provider: Configuration provider for retention settings (optional)
        """
        if not path_service:
            raise ValueError("path_service is required for CleanupService")
        self._path_service = path_service
        self._config_provider = config_provider

    def cleanup_old_artifacts(self, retention_days: int = None) -> Dict[str, int]:
        """Clean up artifacts older than retention_days.

        Args:
            retention_days: Number of days to retain (defaults to config_provider RETENTION_DAYS or 30)

        Returns:
            Dict with cleanup counts: backups_cleaned, results_cleaned, logs_cleaned
        """
        if retention_days is None and self._config_provider:
            retention_days = self._config_provider.get('retention_days', 30)
        elif retention_days is None:
            retention_days = 30
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        backups_cleaned = self._cleanup_directory(self._path_service.backup_dir, cutoff_date, '*.tar.gz')
        results_cleaned = self._cleanup_directory(self._path_service.results_dir, cutoff_date, '*.json')
        logs_cleaned = self._cleanup_directory(self._path_service.logs_dir, cutoff_date, '*.log')

        logger.info(
            f"Cleanup completed: {backups_cleaned} backups, "
            f"{results_cleaned} results, {logs_cleaned} logs removed"
        )

        return {
            "backups_cleaned": backups_cleaned,
            "results_cleaned": results_cleaned,
            "logs_cleaned": logs_cleaned
        }

    def _cleanup_directory(self, directory: Path, cutoff_date: datetime, pattern: str) -> int:
        """Clean up files in directory older than cutoff_date.

        Args:
            directory: Directory to clean
            cutoff_date: Cutoff date for file age
            pattern: File pattern to match

        Returns:
            Number of files cleaned
        """
        if not directory.exists():
            return 0

        cleaned_count = 0

        for file_path in directory.glob(pattern):
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                if file_mtime < cutoff_date:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"Removed old artifact: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove {file_path}: {e}")

        return cleaned_count

    def get_artifact_stats(self) -> Dict[str, Any]:
        """Get statistics about artifact storage.

        Returns:
            Dict with artifact counts and sizes
        """
        stats = {
            "backups": self._get_directory_stats(self._path_service.backup_dir, '*.tar.gz'),
            "results": self._get_directory_stats(self._path_service.results_dir, '*.json'),
            "logs": self._get_directory_stats(self._path_service.logs_dir, '*.log')
        }

        total_count = sum(s['count'] for s in stats.values())
        total_size_mb = sum(s['size_mb'] for s in stats.values())

        stats['total'] = {
            "count": total_count,
            "size_mb": total_size_mb
        }

        return stats

    def _get_directory_stats(self, directory: Path, pattern: str) -> Dict[str, Any]:
        """Get statistics for files in directory.

        Args:
            directory: Directory to analyze
            pattern: File pattern to match

        Returns:
            Dict with count and size_mb
        """
        if not directory.exists():
            return {"count": 0, "size_mb": 0.0}

        count = 0
        total_size = 0

        for file_path in directory.glob(pattern):
            try:
                count += 1
                total_size += file_path.stat().st_size
            except Exception:
                continue

        return {
            "count": count,
            "size_mb": round(total_size / (1024 * 1024), 2)
        }
