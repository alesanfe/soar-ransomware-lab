#!/usr/bin/env python3
"""SOAR Ransomware Lab - Centralized Configuration.

Single source of truth for all configuration across the project.
"""

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from soar_lab.common.constants import (
    DEFAULT_API_VERSION,
    DEFAULT_BACKUP_TIMEOUT,
    DEFAULT_ELASTICSEARCH_URL,
    DEFAULT_SHUFFLE_BACKEND_URL,
    DEFAULT_TEST_TIMEOUT,
    JWT_ALGORITHM_DEFAULT,
)
from soar_lab.common.exceptions import ConfigurationError
from soar_lab.config.logging import get_logger
from soar_lab.config.schema import validate_config_dict

__all__ = ["Settings", "create_settings"]

# Load environment variables — CFG-031/032 (12-Factor):
# precedence is: real environment > .env.full > .env > code defaults.
#
# Legacy deviation: .env.full used to be loaded with override=True so
# regenerated keys (init_thehive.py writes fresh THEHIVE_API_KEY into
# .env.full) won over stale shell vars. That inverts 12-Factor — a real
# env var must always win. The lab workflow that needs file-wins can
# opt in explicitly with SOAR_DOTENV_OVERRIDE=1. Test suites keep their
# own override=True in tests/conftest.py, unaffected by this.
load_dotenv()
env_file = Path(__file__).parent.parent.parent.parent / ".env.full"
if env_file.exists():
    _dotenv_strong = os.environ.get("SOAR_DOTENV_OVERRIDE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    load_dotenv(env_file, override=_dotenv_strong)

logger = get_logger(__name__)

# CFG-BOOT-001 — keys whose absence makes the deployment non-functional.
# Resolved through the config provider (``cp.get``) so the same list
# applies to Settings and dict-style providers alike.
REQUIRED_CONFIG_KEYS: tuple[str, ...] = (
    "elastic_password",
    "thehive_secret",
    "thehive_api_key",
    "cortex_secret",
    "cortex_api_key",
    "siem_webhook_token",
)
# JWT signs auth tokens — either key satisfies the requirement.
JWT_CONFIG_KEYS: tuple[str, ...] = ("jwt_secret_key", "api_auth_secret")


def missing_required_keys(cp: Any) -> list[str]:
    """Return the required config keys absent from provider ``cp``.

    ``cp`` is any object with ``.get(key)`` — Settings, dict provider
    or the composition-root config provider. An empty list means the
    deployment has every mandatory credential configured.
    """
    missing = [key for key in REQUIRED_CONFIG_KEYS if not cp.get(key)]
    if not any(cp.get(key) for key in JWT_CONFIG_KEYS):
        missing.append("jwt_secret_key (or api_auth_secret)")
    return missing


class Settings:
    """Central configuration class for SOAR Lab."""

    def __init__(self) -> None:
        """Initialize the Settings by loading configuration from environment."""
        self._config = self._load_config()
        # C2: schema-validate the merged dict at boot — range/type
        # errors surface here with field names, not mid-request.
        try:
            validate_config_dict(self._config)
        except Exception as exc:
            raise ConfigurationError(f"Invalid configuration: {exc}") from exc
        self._backup_dir_override = None  # For testing purposes

    # ------------------------------------------------------------------
    # API-level attributes (consumed by src/soar_lab/api/)
    # Dynamic properties to allow test mocking via os.environ
    # ------------------------------------------------------------------
    @property
    def API_HOST(self) -> str:
        """API host address."""
        return self._config.get("api_host", "127.0.0.1")

    @property
    def API_PORT(self) -> int:
        """API port number."""
        return self._config.get("api_port", 8000)

    API_TITLE: str = "SOAR Lab Management API"
    API_DESCRIPTION: str = "REST API for SOAR Ransomware Lab Management"
    API_VERSION: str = DEFAULT_API_VERSION

    @property
    def WEB_UI_USER(self) -> str | None:
        """Web UI username, if configured."""
        return self._config.get("web_ui_user")

    @property
    def WEB_UI_PASSWORD(self) -> str | None:
        """Web UI password, if configured."""
        return self._config.get("web_ui_password")

    @property
    def API_AUTH_SECRET(self) -> str | None:
        """API authentication secret, if configured."""
        return self._config.get("api_auth_secret")

    @property
    def JWT_SECRET_KEY(self) -> str | None:
        """JWT signing secret key."""
        jwt_secret = self._config.get("jwt_secret_key")
        api_secret = self._config.get("api_auth_secret")
        # Fail closed: a public hardcoded fallback would let anyone forge tokens.
        return jwt_secret or api_secret

    @property
    def JWT_ALGORITHM(self) -> str:
        """JWT signing algorithm."""
        return self._config.get("jwt_algorithm", JWT_ALGORITHM_DEFAULT)

    @property
    def JWT_EXPIRATION_MINUTES(self) -> int:
        """JWT token expiration time in minutes."""
        return self._config.get("jwt_expiration_minutes", 60)

    @property
    def CORS_ORIGINS(self) -> list:
        """List of allowed CORS origins."""
        origins = self._config.get("cors_origins", "http://localhost:8086,http://localhost:8081")
        return origins.split(",") if isinstance(origins, str) else origins

    @property
    def REDIS_URL(self) -> str | None:
        """Redis connection URL, if configured."""
        return self._config.get("redis_url")

    @property
    def BACKUP_DIR(self) -> str:
        """Backup directory path."""
        if self._backup_dir_override is not None:
            return self._backup_dir_override
        return self._config.get("backup_dir")

    @BACKUP_DIR.setter
    def BACKUP_DIR(self, value: str) -> None:
        """Set the backup directory override (for testing purposes)."""
        # Allow setting BACKUP_DIR for testing purposes
        self._backup_dir_override = value

    BACKUP_TIMEOUT_SECONDS: int = DEFAULT_BACKUP_TIMEOUT
    TEST_TIMEOUT_SECONDS: int = DEFAULT_TEST_TIMEOUT
    TEST_COVERAGE_PATH: str = "src/soar_lab"

    # ------------------------------------------------------------------
    # Config sections — each returns a fragment merged by _load_config.
    # Keep env-var names and defaults byte-identical when editing.
    # ------------------------------------------------------------------

    @staticmethod
    def _api_config() -> dict[str, Any]:
        """API host/auth/JWT/CORS and the Redis cache URL."""
        return {
            "api_host": os.getenv("API_HOST", "127.0.0.1"),
            "api_port": int(os.getenv("API_PORT", "8000")),
            "web_ui_user": os.getenv("WEB_UI_USER"),
            "web_ui_password": os.getenv("WEB_UI_PASSWORD"),
            "api_auth_secret": os.getenv("API_AUTH_SECRET"),
            "jwt_secret_key": os.getenv("JWT_SECRET_KEY"),
            "jwt_algorithm": os.getenv("JWT_ALGORITHM", JWT_ALGORITHM_DEFAULT),
            "jwt_expiration_minutes": int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
            "cors_origins": os.getenv(
                "CORS_ORIGINS", "http://localhost:8086,http://localhost:8081"
            ),
            "redis_url": os.getenv("REDIS_URL"),
            # Deployment profile — "production" turns on fail-fast config
            # validation at boot (CFG-BOOT-001).
            "environment": os.getenv("SOAR_ENV", "development"),
        }

    @staticmethod
    def _service_config() -> dict[str, Any]:
        """Compose project name, published ports and service base URLs."""
        return {
            "project_name": os.getenv("COMPOSE_PROJECT_NAME", "soar"),
            "thehive_port": int(os.getenv("THEHIVE_HTTP_PORT", "9000")),
            "cortex_port": int(os.getenv("CORTEX_HTTP_PORT", "9001")),
            "shuffle_ui_port": int(os.getenv("SHUFFLE_UI_PORT", "8081")),
            "shuffle_api_port": int(os.getenv("SHUFFLE_API_PORT", "5001")),
            "elasticsearch_port": int(os.getenv("ELASTICSEARCH_PORT", "9201")),
            "misp_port": int(os.getenv("MISP_PORT", "8083")),
            "http_port": int(os.getenv("HTTP_PORT", "80")),
            "thehive_url": os.getenv("THEHIVE_URL", "http://thehive:9000"),
            "cortex_url": os.getenv("CORTEX_URL", "http://cortex:9001"),
            "shuffle_url": os.getenv("SHUFFLE_URL", DEFAULT_SHUFFLE_BACKEND_URL),
            # MISP in this stack serves HTTPS with a self-signed cert — the
            # http:80 default was BUG-070. Keep the source default aligned
            # with what base_client rewrites.
            "misp_url": os.getenv("MISP_URL", "https://misp:443"),
            "elasticsearch_url": os.getenv(
                "ES_URL", os.getenv("ELASTICSEARCH_URL", DEFAULT_ELASTICSEARCH_URL)
            ),
            "shuffle_webhook_url": os.getenv(
                "SHUFFLE_WEBHOOK_URL", "http://localhost:5001/api/v1/hooks"
            ),
        }

    @staticmethod
    def _security_config() -> dict[str, Any]:
        """Credentials, service tokens, thresholds and datastore logins."""
        return {
            "elastic_security_enabled": os.getenv("ELASTIC_SECURITY_ENABLED", "true").lower()
            == "true",
            "elastic_password": os.getenv("ELASTIC_PASSWORD", ""),
            "thehive_secret": os.getenv("THEHIVE_SECRET", ""),
            "thehive_api_key": os.getenv("THEHIVE_API_KEY", ""),
            "cortex_secret": os.getenv("CORTEX_SECRET", ""),
            "cortex_api_key": os.getenv("CORTEX_API_KEY", ""),
            "shuffle_username": os.getenv("SHUFFLE_DEFAULT_USERNAME", "admin"),
            "shuffle_password": os.getenv("SHUFFLE_DEFAULT_PASSWORD", ""),
            "shuffle_api_key": os.getenv("SHUFFLE_DEFAULT_APIKEY", ""),
            "misp_api_key": os.getenv("MISP_API_KEY", ""),
            "siem_webhook_token": os.getenv("SIEM_WEBHOOK_TOKEN", ""),
            "edr_sim_token": os.getenv("EDR_SIM_TOKEN", ""),
            "firewall_sim_token": os.getenv("FIREWALL_SIM_TOKEN", ""),
            "decision_score_threshold": int(os.getenv("DECISION_SCORE_THRESHOLD", "80")),
            "postgres_user": os.getenv("POSTGRES_USER", "thehive"),
            "postgres_password": os.getenv("POSTGRES_PASSWORD", ""),
            "postgres_db": os.getenv("POSTGRES_DB", "thehive"),
            "redis_password": os.getenv("REDIS_PASSWORD", ""),
        }

    @staticmethod
    def _logging_config(base_dir: Path) -> dict[str, Any]:
        """Log level/format/destination (``log_dir`` derives from base dir)."""
        return {
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_format": os.getenv("LOG_FORMAT", "json"),
            "log_dir": os.getenv("LOG_DIR", str(base_dir / "runtime" / "logs" / "soar")),
        }

    @staticmethod
    def _performance_config() -> dict[str, Any]:
        """Analyzer concurrency, rate limits and health-check timing."""
        return {
            "max_concurrent_analyzers": int(os.getenv("MAX_CONCURRENT_ANALYZERS", "3")),
            "analyzer_timeout": int(os.getenv("ANALYZER_TIMEOUT", "30")),
            "analyzer_retries": int(os.getenv("ANALYZER_RETRIES", "1")),
            "webhook_rate_limit": int(os.getenv("WEBHOOK_RATE_LIMIT", "60")),
            "webhook_payload_max_size": int(os.getenv("WEBHOOK_PAYLOAD_MAX_SIZE", "65536")),
            "health_check_interval": os.getenv("HEALTH_CHECK_INTERVAL", "30s"),
            "health_check_timeout": os.getenv("HEALTH_CHECK_TIMEOUT", "10s"),
            "health_check_retries": int(os.getenv("HEALTH_CHECK_RETRIES", "3")),
        }

    @staticmethod
    def _backup_config(base_dir: Path) -> dict[str, Any]:
        """Backup location, retention and compression."""
        return {
            "backup_dir": os.getenv("BACKUP_DIR", str(base_dir / "runtime" / "backups")),
            "retention_days": int(os.getenv("RETENTION_DAYS", "7")),
            "compress_backups": os.getenv("COMPRESS", "true").lower() == "true",
        }

    @staticmethod
    def _health_endpoints_config() -> dict[str, Any]:
        """Per-service health URL + container name pairs."""
        return {
            "thehive_health_url": os.getenv(
                "THEHIVE_HEALTH_URL", "http://thehive:9000/api/v1/status/public"
            ),
            "thehive_container": os.getenv("THEHIVE_CONTAINER", "soar_thehive"),
            "cortex_health_url": os.getenv("CORTEX_HEALTH_URL", "http://cortex:9001/"),
            "cortex_container": os.getenv("CORTEX_CONTAINER", "soar_cortex"),
            "shuffle_ui_health_url": os.getenv(
                "SHUFFLE_UI_HEALTH_URL", "http://shuffle-frontend:80/"
            ),
            "shuffle_frontend_container": os.getenv(
                "SHUFFLE_FRONTEND_CONTAINER", "soar_shuffle_frontend"
            ),
            "shuffle_health_url": os.getenv(
                "SHUFFLE_HEALTH_URL", "http://shuffle-backend:5001/api/v1/health"
            ),
            "shuffle_container": os.getenv("SHUFFLE_CONTAINER", "soar_shuffle_backend"),
            "docs_health_url": os.getenv("DOCS_HEALTH_URL", "http://docs-site:8080/"),
            "docs_container": os.getenv("DOCS_CONTAINER", "soar_docs_site"),
            "api_health_url": os.getenv("API_HEALTH_URL", "http://api:8000/health"),
            "api_container": os.getenv("API_CONTAINER", "soar_api"),
            "elasticsearch_health_url": os.getenv(
                "ELASTICSEARCH_HEALTH_URL", "http://elasticsearch:9200/_cluster/health"
            ),
            "elasticsearch_container": os.getenv("ELASTICSEARCH_CONTAINER", "soar_elasticsearch"),
            "nginx_health_url": os.getenv("NGINX_HEALTH_URL", "http://nginx:80/"),
            "nginx_container": os.getenv("NGINX_CONTAINER", "soar_nginx"),
            "redis_health_url": os.getenv("REDIS_HEALTH_URL", "tcp://redis:6379"),
            "redis_container": os.getenv("REDIS_CONTAINER", "soar_redis"),
            "loki_health_url": os.getenv("LOKI_HEALTH_URL", "https://loki:3100/ready"),
            "loki_container": os.getenv("LOKI_CONTAINER", "soar_loki"),
            "grafana_health_url": os.getenv(
                "GRAFANA_HEALTH_URL", "https://grafana:3000/api/health"
            ),
            "grafana_container": os.getenv("GRAFANA_CONTAINER", "soar_grafana"),
            "promtail_health_url": os.getenv("PROMTAIL_HEALTH_URL", "http://promtail:9080/"),
            "promtail_container": os.getenv("PROMTAIL_CONTAINER", "soar_promtail"),
            "misp_health_url": os.getenv("MISP_HEALTH_URL", "https://misp:443/users/heartbeat"),
            "misp_container": os.getenv("MISP_CONTAINER", "soar_misp"),
            # GRAF-D10: services serving lab-CA certs need the CA pinned here —
            # requests accepts a bundle path in verify=.
            "health_check_ssl_config": {
                "loki": "/app/certs/ca.crt",
                "grafana": "/app/certs/ca.crt",
                "misp": "/app/certs/ca.crt",
            },
        }

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        CFG-034: ``BASE_DIR`` is optional — it resolves to the repo root
        derived from this file's location (``src/soar_lab/config`` → up 3).
        In Docker that yields ``/app``, matching the baked layout. The env
        var remains an explicit override; a totally absent BASE_DIR no
        longer kills ``import soar_lab.interfaces.api``.
        """
        base_dir_str = os.getenv("BASE_DIR")
        base_dir = Path(base_dir_str) if base_dir_str else Path(__file__).resolve().parents[3]

        config: dict[str, Any] = {"base_dir": str(base_dir)}
        for section in (
            self._api_config,
            self._service_config,
            self._security_config,
            self._performance_config,
            self._health_endpoints_config,
        ):
            config.update(section())
        config.update(self._logging_config(base_dir))
        config.update(self._backup_config(base_dir))
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value from unified _config dict.

        All environment variables are loaded once at initialization time
        via _load_config(). This eliminates multiple sources of truth.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value

    # BL-SEC-011 / BL-CFG: keys whose values are credentials. ``get_all``
    # redacts them by default so a config dump (debug endpoint, support
    # bundle, log line) can never serialize secrets in plaintext.
    _SENSITIVE_KEY_RE = re.compile(
        r"(password|passwd|secret|token|api_?key|apikey|private_?key|credential)",
        re.IGNORECASE,
    )
    _REDACTED = "***REDACTED***"

    def get_all(self, redact: bool = True) -> dict[str, Any]:
        """Get all configuration.

        Args:
            redact: when True (default) values under secret-looking keys
                are replaced with ``***REDACTED***``. Pass ``redact=False``
                only for internal consumers that truly need plaintext —
                never for anything that may reach logs or a response body.
        """
        if not redact:
            return self._config.copy()
        return {
            k: (self._REDACTED if self._SENSITIVE_KEY_RE.search(k) and v else v)
            for k, v in self._config.items()
        }

    def get_redacted(self) -> dict[str, Any]:
        """Explicit alias for ``get_all(redact=True)`` for config dumps."""
        return self.get_all(redact=True)

    def validate(self, strict: bool = False) -> bool:
        """Validate configuration.

        With ``strict=False`` (default) missing keys only log a warning.
        With ``strict=True`` a ``ConfigurationError`` is raised instead —
        used at boot when ``SOAR_CONFIG_STRICT``/``SOAR_ENV=production``
        demands fail-fast startup.
        """
        missing_keys = missing_required_keys(self)

        if missing_keys:
            message = f"Missing required configuration: {', '.join(missing_keys)}"
            if strict:
                raise ConfigurationError(message)
            logger.warning(message)
            return False

        return True

    def get_service_urls(self) -> dict[str, dict[str, str]]:
        """Get service URLs and container names for health checks."""
        return {
            "thehive": {
                "url": self._config.get("thehive_health_url"),
                "container": self._config.get("thehive_container"),
            },
            "cortex": {
                "url": self._config.get("cortex_health_url"),
                "container": self._config.get("cortex_container"),
            },
            "shuffle-frontend": {
                "url": self._config.get("shuffle_ui_health_url"),
                "container": self._config.get("shuffle_frontend_container"),
            },
            "shuffle-backend": {
                "url": self._config.get("shuffle_health_url"),
                "container": self._config.get("shuffle_container"),
            },
            "docs-site": {
                "url": self._config.get("docs_health_url"),
                "container": self._config.get("docs_container"),
            },
            "api": {
                "url": self._config.get("api_health_url"),
                "container": self._config.get("api_container"),
            },
            "elasticsearch": {
                "url": self._config.get("elasticsearch_health_url"),
                "container": self._config.get("elasticsearch_container"),
            },
            "nginx": {
                "url": self._config.get("nginx_health_url"),
                "container": self._config.get("nginx_container"),
            },
            "redis": {
                "url": self._config.get("redis_health_url"),
                "container": self._config.get("redis_container"),
            },
            "loki": {
                "url": self._config.get("loki_health_url"),
                "container": self._config.get("loki_container"),
            },
            "grafana": {
                "url": self._config.get("grafana_health_url"),
                "container": self._config.get("grafana_container"),
            },
            "promtail": {
                "url": self._config.get("promtail_health_url"),
                "container": self._config.get("promtail_container"),
            },
            "misp": {
                "url": self._config.get("misp_health_url"),
                "container": self._config.get("misp_container"),
            },
        }

    def get_webhook_url(self) -> str:
        """Get Shuffle webhook URL."""
        return self._config.get("shuffle_webhook_url", "http://localhost:5001/api/v1/hooks")

    def __str__(self) -> str:
        """String representation of configuration."""
        return f"Settings(project={self.get('project_name')})"


# Factory function to create Settings instances
def create_settings() -> Settings:
    """Factory function to create a Settings instance."""
    return Settings()
