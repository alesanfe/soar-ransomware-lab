"""Cleanup Service for managing artifact retention.

This service provides automated cleanup of old artifacts based on
retention policies, preventing artifact accumulation from hiding real
code problems.
"""

import os
from datetime import UTC, datetime, timedelta
from operator import itemgetter
from pathlib import Path
from typing import Any

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import ConfigProvider

__all__ = ["CleanupService"]

logger = get_logger(__name__)


class CleanupService:
    """Service for cleaning up old artifacts based on retention policies."""

    def __init__(self, path_service: object, config_provider: ConfigProvider | None = None) -> None:
        """Initialize the cleanup service.

        Args:
            path_service: PathService instance for path management (required)
            config_provider: Configuration provider for retention settings (optional)
        """
        if not path_service:
            raise ValueError("path_service is required for CleanupService")
        self._path_service = path_service
        self._config_provider = config_provider

    def cleanup_old_artifacts(
        self,
        retention_days: int | None = None,
        *,
        dry_run: bool = False,
        min_keep: int = 1,
    ) -> dict[str, int]:
        """Clean up artifacts older than retention_days.

        Retention resolution is single-sourced: explicit parameter >
        ``config_provider.get("retention_days")`` > ``RETENTION_DAYS``
        environment variable > 30-day fallback. No duplicate literal
        defaults.

        Args:
            retention_days: Number of days to retain (defaults to the
                resolution chain above).
            dry_run: When ``True``, only count what *would* be removed;
                no file is deleted.
            min_keep: Newest files per directory that are never deleted
                regardless of age (active-guard: the latest backup/result
                is always kept).

        Returns:
            Dict with cleanup counts plus ``errors`` (failed deletions,
            never silently dropped) and ``skipped`` (files kept by the
            active-guard).
        """
        if retention_days is None:
            retention_days = self._resolve_retention_days()
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        backups = self._cleanup_directory(
            self._path_service.backup_dir,
            cutoff_date,
            "*.tar.gz",
            dry_run=dry_run,
            min_keep=min_keep,
        )
        results = self._cleanup_directory(
            self._path_service.results_dir,
            cutoff_date,
            "*.json",
            dry_run=dry_run,
            min_keep=min_keep,
        )
        logs = self._cleanup_directory(
            self._path_service.logs_dir,
            cutoff_date,
            "*.log",
            dry_run=dry_run,
            min_keep=min_keep,
        )

        outcome = {
            "backups_cleaned": backups["cleaned"],
            "results_cleaned": results["cleaned"],
            "logs_cleaned": logs["cleaned"],
            "errors": backups["errors"] + results["errors"] + logs["errors"],
            "skipped": backups["skipped"] + results["skipped"] + logs["skipped"],
        }
        logger.info(
            f"Cleanup {'(dry-run) ' if dry_run else ''}completed: "
            f"{outcome['backups_cleaned']} backups, {outcome['results_cleaned']} results, "
            f"{outcome['logs_cleaned']} logs removed, "
            f"{outcome['errors']} errors, {outcome['skipped']} kept by active-guard"
        )
        return outcome

    def _resolve_retention_days(self) -> int:
        """Resolve the effective retention period (single source)."""
        if self._config_provider:
            value = self._config_provider.get("retention_days")
            if value is not None:
                return int(value)
        return int(os.getenv("RETENTION_DAYS", "30"))

    def _cleanup_directory(
        self,
        directory: Path,
        cutoff_date: datetime,
        pattern: str,
        *,
        dry_run: bool,
        min_keep: int,
    ) -> dict[str, int]:
        """Clean up files in *directory* older than *cutoff_date*.

        Args:
            directory: Directory to clean.
            cutoff_date: Cutoff date for file age.
            pattern: File pattern to match.
            dry_run: Count without deleting.
            min_keep: Newest files (by mtime) to always keep.

        Returns:
            Dict with ``cleaned``, ``errors`` and ``skipped`` counts.
        """
        outcome = {"cleaned": 0, "errors": 0, "skipped": 0}
        if not directory.exists():
            return outcome

        candidates: list[tuple[float, Path]] = []
        for file_path in directory.glob(pattern):
            try:
                mtime = file_path.stat().st_mtime
            except OSError as exc:
                outcome["errors"] += 1
                logger.warning(f"Failed to stat {file_path}: {exc}")
                continue
            if datetime.fromtimestamp(mtime, tz=UTC) < cutoff_date:
                candidates.append((mtime, file_path))

        # Active-guard: keep the newest ``min_keep`` expired files so the
        # most recent backup/result is never deleted purely by age.
        candidates.sort(key=itemgetter(0), reverse=True)
        outcome["skipped"] = min(min_keep, len(candidates))
        deletable = candidates[min_keep:] if min_keep else candidates

        for _, file_path in deletable:
            if dry_run:
                outcome["cleaned"] += 1
                logger.debug(f"[dry-run] Would remove old artifact: {file_path}")
                continue
            try:
                file_path.unlink()
                outcome["cleaned"] += 1
                logger.debug(f"Removed old artifact: {file_path}")
            except OSError as exc:
                outcome["errors"] += 1
                logger.warning(f"Failed to remove {file_path}: {exc}")

        return outcome

    def get_artifact_stats(self) -> dict[str, Any]:
        """Get statistics about artifact storage.

        Returns:
            Dict with artifact counts and sizes
        """
        stats = {
            "backups": self._get_directory_stats(self._path_service.backup_dir, "*.tar.gz"),
            "results": self._get_directory_stats(self._path_service.results_dir, "*.json"),
            "logs": self._get_directory_stats(self._path_service.logs_dir, "*.log"),
        }

        total_count = sum(s["count"] for s in stats.values())
        total_size_mb = sum(s["size_mb"] for s in stats.values())

        stats["total"] = {"count": total_count, "size_mb": total_size_mb}

        return stats

    def _get_directory_stats(self, directory: Path, pattern: str) -> dict[str, Any]:
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
                total_size += file_path.stat().st_size
                count += 1
            except Exception:
                continue

        return {"count": count, "size_mb": round(total_size / (1024 * 1024), 2)}
