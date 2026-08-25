"""TarBackupDriver - encapsulates tar command knowledge.

This adapter isolates the application layer from OS-specific backup commands.
The service layer only knows about BackupDriver.create/extract, not about tar flags.
"""

import os

from soar_lab.common.constants import DEFAULT_BACKUP_TIMEOUT
from soar_lab.common.exceptions import BackupError
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.subprocess_runner import SubprocessRunner

logger = get_logger(__name__)


def _archive_created(path: str) -> bool:
    """Check whether a tar archive was created and is non-empty."""
    return os.path.exists(path) and os.path.getsize(path) > 0


_EXCLUDES = [
    "--exclude=__pycache__",
    "--exclude=*.pyc",
    "--exclude=.git",
    "--exclude=node_modules",
    "--exclude=htmlcov",
    "--exclude=.pytest_cache",
    "--exclude=coverage.xml",
    "--exclude=.coverage",
    "--exclude=artifacts",
    "--exclude=runtime",
    "--exclude=reports",
    "--exclude=*.tar.gz",
    "--exclude=venv",
    "--exclude=env",
    "--exclude=.env",
    "--exclude=__pycache__",
    "--exclude=.mypy_cache",
    "--exclude=.tox",
    "--exclude=dist",
    "--exclude=build",
    "--exclude=.eggs",
    "--exclude=*.egg-info",
]


class TarBackupDriver:
    """Adapter that encapsulates tar backup operations."""

    def __init__(self, timeout: int = DEFAULT_BACKUP_TIMEOUT) -> None:
        self._runner = SubprocessRunner(default_timeout=timeout)

    def create(self, source_dir: str, dest_path: str) -> None:
        """Create a tar.gz backup archive."""
        result = self._runner.run(
            ["tar", "-czf", dest_path, "--warning=no-file-changed"] + _EXCLUDES + ["."],
            cwd=source_dir,
            raise_on_error=False,
        )
        # tar may exit 1 when files change while being read (e.g. live logs);
        # accept the archive if it was created successfully.
        if result.returncode != 0 and not _archive_created(dest_path):
            raise BackupError(f"tar create failed: {result.stderr}")
        logger.info(f"Backup created: {dest_path}")

    def extract(self, archive_path: str, dest_dir: str) -> None:
        """Extract a tar.gz backup archive."""
        result = self._runner.run(
            [
                "tar",
                "-xzf",
                archive_path,
                "--no-same-permissions",
                "--no-same-owner",
                "--warning=no-file-changed",
                "--skip-old-files",
            ],
            cwd=dest_dir,
            raise_on_error=False,
        )
        if result.returncode != 0:
            raise BackupError(f"tar extract failed: {result.stderr}")
        logger.info(f"Backup extracted: {archive_path}")
