"""Path service for centralized filesystem access."""
import os
from pathlib import Path
from typing import Optional


class PathService:
    """Centralized path management for SOAR Lab."""

    def __init__(self, base_dir: Path = None, config_provider: object = None):
        """Initialize path service.

        Args:
            base_dir: Base directory for paths (optional, uses BASE_DIR env var if not provided).
            config_provider: Configuration provider for path overrides (optional).
        """
        # Determine base_dir from parameter, config_provider, or environment
        if base_dir:
            self.base_dir = base_dir
        elif config_provider:
            base_dir_str = config_provider.get('base_dir')
            if base_dir_str:
                self.base_dir = Path(base_dir_str)
            else:
                # Fallback to BASE_DIR environment variable
                base_dir_str = os.getenv('BASE_DIR')
                if not base_dir_str:
                    raise ValueError(
                        "base_dir must be provided via parameter, config_provider, or BASE_DIR environment variable")
                self.base_dir = Path(base_dir_str)
        else:
            # Fallback to BASE_DIR environment variable
            base_dir_str = os.getenv('BASE_DIR')
            if not base_dir_str:
                raise ValueError(
                    "base_dir must be provided via parameter, config_provider, or BASE_DIR environment variable")
            self.base_dir = Path(base_dir_str)

        self._config_provider = config_provider

    @property
    def artifacts_dir(self) -> Path:
        """Get artifacts directory."""
        return Path(self._config_provider.get('artifacts_dir', str(self.base_dir / "artifacts")))

    @property
    def logs_dir(self) -> Path:
        """Get logs directory."""
        return Path(self._config_provider.get('logs_dir', str(self.artifacts_dir / "logs")))

    @property
    def results_dir(self) -> Path:
        """Get results directory."""
        return Path(self._config_provider.get('results_dir', str(self.artifacts_dir / "results")))

    @property
    def coverage_dir(self) -> Path:
        """Get coverage directory."""
        return Path(self._config_provider.get('coverage_dir', str(self.artifacts_dir / "coverage")))

    @property
    def coverage_file(self) -> Path:
        """Get coverage.json file path."""
        default_path = self.coverage_dir / "coverage.json"
        return Path(self._config_provider.get('coverage_path', str(default_path)))

    @property
    def backup_dir(self) -> Path:
        """Get backup directory."""
        return Path(self._config_provider.get('BACKUP_DIR', str(self.artifacts_dir / "backups")))

    @property
    def schemas_dir(self) -> Path:
        """Get schemas directory."""
        return Path(self._config_provider.get('schemas_dir', str(self.base_dir / "schemas")))

    @property
    def scripts_dir(self) -> Path:
        """Get scripts directory."""
        return Path(self._config_provider.get('scripts_dir', str(self.base_dir / "scripts")))

    @property
    def docker_dir(self) -> Path:
        """Get docker directory."""
        return Path(self._config_provider.get('docker_dir', str(self.base_dir / "infra" / "docker")))

    @property
    def notify_log_file(self) -> Path:
        """Get notify.log file path."""
        return self.logs_dir / "notify.log"

    @property
    def kpi_file(self) -> Path:
        """Get kpis.csv file path."""
        return self.results_dir / "kpis.csv"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.coverage_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.schemas_dir.mkdir(parents=True, exist_ok=True)
