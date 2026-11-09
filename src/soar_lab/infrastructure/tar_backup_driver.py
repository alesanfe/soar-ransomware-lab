"""TarBackupDriver - encapsulates tar command knowledge.

This adapter isolates the application layer from OS-specific backup commands.
The service layer only knows about BackupDriver.create/extract, not about tar flags.
"""

import hashlib
import os
from pathlib import Path

from soar_lab.common.constants import DEFAULT_BACKUP_TIMEOUT
from soar_lab.common.exceptions import BackupError
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.subprocess_runner import SubprocessRunner

logger = get_logger(__name__)


def _archive_created(path: str) -> bool:
    """Check whether a tar archive was created and is non-empty."""
    return Path(path).exists() and Path(path).stat().st_size > 0


def _read_only_mounts(dest_dir: str) -> list[str]:
    """Return dest-relative paths that are bind-mounted read-only under dest_dir.

    Restore must skip them: extracting into a read-only bind mount makes tar
    fail with "Cannot open: Read-only file system" per member.
    """
    dest = os.path.realpath(dest_dir)
    mounts: list[str] = []
    try:
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 4:
                    continue
                mp, opts = parts[1], parts[3].split(",")
                if "ro" in opts and (mp == dest or mp.startswith(dest + "/")):
                    mounts.append(os.path.relpath(mp, dest))
    except OSError:
        return []
    return mounts


# P0.3: secret material must NEVER enter a backup. The ``.env*`` glob
# covers .env.full / .env.testing / .env.container — previously only the
# bare ``.env`` was excluded, so real credentials leaked into archives.
# (.env.example is collateral; it documents no secrets and can be
# regenerated — secrecy beats convenience here.)
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
    "--exclude=.env.*",
    "--exclude=*.pem",
    "--exclude=*.key",
    "--exclude=*.crt",
    "--exclude=*.pfx",
    "--exclude=*.p12",
    "--exclude=*.srl",
    "--exclude=*.csr",
    "--exclude=secrets",
    "--exclude=infra/docker/config/nginx/ssl",
    "--exclude=.mypy_cache",
    "--exclude=.tox",
    "--exclude=dist",
    "--exclude=build",
    "--exclude=.eggs",
    "--exclude=*.egg-info",
]


def _sha256_of(path: str) -> str:

    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TarBackupDriver:
    """Adapter that encapsulates tar backup operations."""

    def __init__(self, timeout: int = DEFAULT_BACKUP_TIMEOUT) -> None:
        self._runner = SubprocessRunner(default_timeout=timeout)

    def create(self, source_dir: str, dest_path: str) -> None:
        """Create a tar.gz backup archive."""
        result = self._runner.run(
            ["tar", "-czf", dest_path, "--force-local", "--warning=no-file-changed"]
            + _EXCLUDES
            + ["."],
            cwd=source_dir,
            raise_on_error=False,
        )
        # tar may exit 1 when files change while being read (e.g. live logs);
        # accept the archive if it was created successfully.
        if result.returncode != 0 and not _archive_created(dest_path):
            raise BackupError(f"tar create failed: {result.stderr}")
        # P0.3: sidecar SHA-256 so restores can detect corruption/tampering.
        if _archive_created(dest_path):
            checksum = _sha256_of(dest_path)
            with open(dest_path + ".sha256", "w", encoding="utf-8") as fh:
                fh.write(f"{checksum}  {os.path.basename(dest_path)}\n")
            # P0.3: self-verify the archive we just wrote (tar -tzf).
            self.verify(dest_path)
            logger.info(f"Backup created: {dest_path} sha256={checksum[:16]}…")
        else:
            logger.info(f"Backup created: {dest_path}")

    def verify(self, archive_path: str) -> None:
        """P0.3: integrity check — ``tar -tzf`` plus SHA-256 vs sidecar.

        Raises ``BackupError`` on a corrupt archive or checksum mismatch.
        """
        result = self._runner.run(
            ["tar", "-tzf", archive_path, "--force-local"],
            raise_on_error=False,
        )
        if result.returncode != 0:
            raise BackupError(f"backup archive failed verification (tar -tzf): {result.stderr}")
        sidecar = archive_path + ".sha256"
        if Path(sidecar).exists():
            expected = Path(sidecar).read_text(encoding="utf-8").split()[0]
            actual = _sha256_of(archive_path)
            if expected != actual:
                raise BackupError(
                    f"backup checksum mismatch: expected {expected[:16]}…, got {actual[:16]}…"
                )

    def extract(self, archive_path: str, dest_dir: str) -> None:
        """Extract a tar.gz backup archive.

        P0.3: verifies integrity BEFORE overwriting live files — a corrupt
        or tampered archive must not partially clobber the working tree.
        """
        self.verify(archive_path)
        ro_mounts = _read_only_mounts(dest_dir)
        if ro_mounts:
            logger.info(f"Skipping read-only mounts during restore: {ro_mounts}")
        excludes = [f"--exclude=./{rel}" for rel in ro_mounts]
        result = self._runner.run(
            [
                "tar",
                "-xzf",
                archive_path,
                "--force-local",
                "--no-same-permissions",
                "--no-same-owner",
                "--warning=no-file-changed",
                "--overwrite",
            ]
            + excludes,
            cwd=dest_dir,
            raise_on_error=False,
        )
        if result.returncode != 0:
            raise BackupError(f"tar extract failed: {result.stderr}")
        logger.info(f"Backup extracted: {archive_path}")
