"""TarBackupDriver - encapsulates tar command knowledge.

This adapter isolates the application layer from OS-specific backup commands.
The service layer only knows about BackupDriver.create/extract, not about tar flags.
"""

from soar_lab.config.logging import get_logger
from soar_lab.exceptions import BackupError
from soar_lab.infrastructure.subprocess_runner import SubprocessRunner

logger = get_logger(__name__)

_EXCLUDES = [
    '--exclude=__pycache__',
    '--exclude=*.pyc',
    '--exclude=.git',
    '--exclude=node_modules',
    '--exclude=htmlcov',
    '--exclude=.pytest_cache',
    '--exclude=coverage.xml',
    '--exclude=.coverage',
    '--exclude=artifacts',
    '--exclude=*.tar.gz',
    '--exclude=venv',
    '--exclude=env',
    '--exclude=.env',
    '--exclude=__pycache__',
    '--exclude=.mypy_cache',
    '--exclude=.tox',
    '--exclude=dist',
    '--exclude=build',
    '--exclude=.eggs',
    '--exclude=*.egg-info',
]


class TarBackupDriver:
    """Adapter that encapsulates tar backup operations."""

    def __init__(self, timeout: int = 600):
        self._runner = SubprocessRunner(default_timeout=timeout)

    def create(self, source_dir: str, dest_path: str) -> None:
        """Create a tar.gz backup archive."""
        result = self._runner.run(
            ['tar', '-czf', dest_path] + _EXCLUDES + ['.'],
            cwd=source_dir,
            raise_on_error=True
        )
        if result.returncode != 0:
            raise BackupError(f"tar create failed: {result.stderr}")
        logger.info(f"Backup created: {dest_path}")

    def extract(self, archive_path: str, dest_dir: str) -> None:
        """Extract a tar.gz backup archive."""
        result = self._runner.run(
            ['tar', '-xzf', archive_path,
             '--no-same-permissions',
             '--no-same-owner',
             '--warning=no-file-changed',
             '--skip-old-files'],
            cwd=dest_dir,
            raise_on_error=True
        )
        if result.returncode != 0:
            raise BackupError(f"tar extract failed: {result.stderr}")
        logger.info(f"Backup extracted: {archive_path}")
