#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Centralized Configuration
Single source of truth for all configuration across the project.
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, Optional

from soar_lab.config.logging import get_logger

# Load environment variables
# Load .env first, then .env.full with override=True to ensure E2E test URLs take precedence
load_dotenv()
env_file = Path(__file__).parent.parent.parent.parent / '.env.full'
if env_file.exists():
    load_dotenv(env_file, override=True)

logger = get_logger(__name__)


class Settings:
    """Central configuration class for SOAR Lab"""

    def __init__(self):
        self._config = self._load_config()
        self._backup_dir_override = None  # For testing purposes

    # ------------------------------------------------------------------
    # API-level attributes (consumed by src/soar_lab/api/)
    # Dynamic properties to allow test mocking via os.environ
    # ------------------------------------------------------------------
    @property
    def API_HOST(self) -> str:
        return self._config.get('api_host', '127.0.0.1')

    @property
    def API_PORT(self) -> int:
        return self._config.get('api_port', 8000)

    API_TITLE: str = "SOAR Lab Management API"
    API_DESCRIPTION: str = "REST API for SOAR Ransomware Lab Management"
    API_VERSION: str = "1.0.0"

    @property
    def WEB_UI_USER(self) -> Optional[str]:
        return self._config.get('web_ui_user')

    @property
    def WEB_UI_PASSWORD(self) -> Optional[str]:
        return self._config.get('web_ui_password')

    @property
    def API_AUTH_SECRET(self) -> Optional[str]:
        return self._config.get('api_auth_secret')

    @property
    def JWT_SECRET_KEY(self) -> Optional[str]:
        jwt_secret = self._config.get('jwt_secret_key')
        api_secret = self._config.get('api_auth_secret')
        return jwt_secret or api_secret or "change-this-in-production-use-32-chars"

    JWT_ALGORITHM: str = "HS256"

    @property
    def JWT_EXPIRATION_MINUTES(self) -> int:
        return self._config.get('jwt_expiration_minutes', 60)

    @property
    def CORS_ORIGINS(self) -> list:
        origins = self._config.get('cors_origins', 'http://localhost:8086,http://localhost:8081')
        return origins.split(",") if isinstance(origins, str) else origins

    @property
    def REDIS_URL(self) -> Optional[str]:
        return self._config.get('redis_url')

    @property
    def BACKUP_DIR(self) -> str:
        if self._backup_dir_override is not None:
            return self._backup_dir_override
        return self._config.get('backup_dir')

    @BACKUP_DIR.setter
    def BACKUP_DIR(self, value: str):
        # Allow setting BACKUP_DIR for testing purposes
        self._backup_dir_override = value

    BACKUP_TIMEOUT_SECONDS: int = 600
    TEST_TIMEOUT_SECONDS: int = 300
    TEST_COVERAGE_PATH: str = "src/soar_lab"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        base_dir_str = os.getenv('BASE_DIR')
        if not base_dir_str:
            raise ValueError("BASE_DIR environment variable must be set")
        base_dir = Path(base_dir_str)

        config = {
            # === Base Directory (for PathService) ===
            'base_dir': str(base_dir),

            # === API Configuration ===
            'api_host': os.getenv('API_HOST', '127.0.0.1'),
            'api_port': int(os.getenv('API_PORT', '8000')),
            'web_ui_user': os.getenv('WEB_UI_USER'),
            'web_ui_password': os.getenv('WEB_UI_PASSWORD'),
            'api_auth_secret': os.getenv('API_AUTH_SECRET'),
            'jwt_secret_key': os.getenv('JWT_SECRET_KEY'),
            'jwt_expiration_minutes': int(os.getenv('JWT_EXPIRATION_MINUTES', '60')),
            'cors_origins': os.getenv('CORS_ORIGINS', 'http://localhost:8086,http://localhost:8081'),
            'redis_url': os.getenv('REDIS_URL'),

            # === Project Configuration ===
            'project_name': os.getenv('COMPOSE_PROJECT_NAME', 'soar'),

            # === Network Configuration ===
            'thehive_port': int(os.getenv('THEHIVE_HTTP_PORT', '9000')),
            'cortex_port': int(os.getenv('CORTEX_HTTP_PORT', '9001')),
            'shuffle_ui_port': int(os.getenv('SHUFFLE_UI_PORT', '8081')),
            'shuffle_api_port': int(os.getenv('SHUFFLE_API_PORT', '5001')),
            'elasticsearch_port': int(os.getenv('ELASTICSEARCH_PORT', '9201')),
            'kibana_port': int(os.getenv('KIBANA_PORT', '15601')),
            'wazuh_api_port': int(os.getenv('WAZUH_API_PORT', '55100')),
            'misp_port': int(os.getenv('MISP_PORT', '8083')),
            'http_port': int(os.getenv('HTTP_PORT', '80')),

            # === Service URLs (single source of truth) ===
            'thehive_url': os.getenv('THEHIVE_URL', 'http://thehive:9000'),
            'cortex_url': os.getenv('CORTEX_URL', 'http://cortex:9001'),
            'shuffle_url': os.getenv('SHUFFLE_URL', 'http://soar_shuffle_backend:5001'),
            'kibana_url': os.getenv('KIBANA_URL', 'http://localhost:15601'),
            'wazuh_url': os.getenv('WAZUH_URL', 'https://wazuh-manager:55000'),
            'misp_url': os.getenv('MISP_URL', 'https://soar_misp:443'),
            'elasticsearch_url': os.getenv('ES_URL', os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')),
            'shuffle_webhook_url': os.getenv('SHUFFLE_WEBHOOK_URL', 'http://localhost:5001/api/v1/hooks'),

            # === Security Configuration ===
            'elastic_security_enabled': os.getenv('ELASTIC_SECURITY_ENABLED', 'true').lower() == 'true',
            'elastic_password': os.getenv('ELASTIC_PASSWORD', ''),

            # === Authentication ===
            'thehive_secret': os.getenv('THEHIVE_SECRET', ''),
            'thehive_api_key': os.getenv('THEHIVE_API_KEY', ''),
            'cortex_secret': os.getenv('CORTEX_SECRET', ''),
            'cortex_api_key': os.getenv('CORTEX_API_KEY', ''),
            'shuffle_username': os.getenv('SHUFFLE_DEFAULT_USERNAME', 'admin'),
            'shuffle_password': os.getenv('SHUFFLE_DEFAULT_PASSWORD', ''),
            'shuffle_api_key': os.getenv('SHUFFLE_DEFAULT_APIKEY', ''),
            'misp_api_key': os.getenv('MISP_API_KEY', ''),
            'wazuh_user': os.getenv('WAZUH_API_USERNAME', 'wazuh-wui'),
            'wazuh_password': os.getenv('WAZUH_API_PASSWORD', ''),

            # === Security Tokens ===
            'siem_webhook_token': os.getenv('SIEM_WEBHOOK_TOKEN', ''),
            'edr_sim_token': os.getenv('EDR_SIM_TOKEN', ''),
            'firewall_sim_token': os.getenv('FIREWALL_SIM_TOKEN', ''),

            # === Decision Thresholds ===
            'decision_score_threshold': int(os.getenv('DECISION_SCORE_THRESHOLD', '80')),

            # === Database Configuration ===
            'postgres_user': os.getenv('POSTGRES_USER', 'thehive'),
            'postgres_password': os.getenv('POSTGRES_PASSWORD', ''),
            'postgres_db': os.getenv('POSTGRES_DB', 'thehive'),
            'redis_password': os.getenv('REDIS_PASSWORD', ''),

            # === Logging Configuration ===
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'log_format': os.getenv('LOG_FORMAT', 'json'),
            'log_dir': os.getenv('LOG_DIR', str(base_dir / 'artifacts' / 'logs' / 'soar')),

            # === Performance Configuration ===
            'max_concurrent_analyzers': int(os.getenv('MAX_CONCURRENT_ANALYZERS', '3')),
            'analyzer_timeout': int(os.getenv('ANALYZER_TIMEOUT', '30')),
            'analyzer_retries': int(os.getenv('ANALYZER_RETRIES', '1')),

            # === Rate Limiting ===
            'webhook_rate_limit': int(os.getenv('WEBHOOK_RATE_LIMIT', '60')),
            'webhook_payload_max_size': int(os.getenv('WEBHOOK_PAYLOAD_MAX_SIZE', '65536')),

            # === Health Check Configuration ===
            'health_check_interval': os.getenv('HEALTH_CHECK_INTERVAL', '30s'),
            'health_check_timeout': os.getenv('HEALTH_CHECK_TIMEOUT', '10s'),
            'health_check_retries': int(os.getenv('HEALTH_CHECK_RETRIES', '3')),

            # === Backup Configuration ===
            'backup_dir': os.getenv('BACKUP_DIR', str(base_dir / 'artifacts' / 'backups')),
            'retention_days': int(os.getenv('RETENTION_DAYS', '7')),
            'compress_backups': os.getenv('COMPRESS', 'true').lower() == 'true',

            # === Service Health Check URLs and Containers ===
            'thehive_health_url': os.getenv("THEHIVE_HEALTH_URL", "http://soar_thehive:9000/api/health"),
            'thehive_container': os.getenv("THEHIVE_CONTAINER", "soar_thehive"),
            'cortex_health_url': os.getenv("CORTEX_HEALTH_URL", "http://soar_cortex:9001/"),
            'cortex_container': os.getenv("CORTEX_CONTAINER", "soar_cortex"),
            'shuffle_ui_health_url': os.getenv("SHUFFLE_UI_HEALTH_URL", "http://soar_shuffle_frontend:80/"),
            'shuffle_frontend_container': os.getenv("SHUFFLE_FRONTEND_CONTAINER", "soar_shuffle_frontend"),
            'shuffle_health_url': os.getenv("SHUFFLE_HEALTH_URL", "http://soar_shuffle_backend:5001/api/v1/health"),
            'shuffle_container': os.getenv("SHUFFLE_CONTAINER", "soar_shuffle_backend"),
            'kibana_health_url': os.getenv("KIBANA_HEALTH_URL", "http://soar_kibana:5601/api/status"),
            'kibana_container': os.getenv("KIBANA_CONTAINER", "soar_kibana"),
            'docs_health_url': os.getenv("DOCS_HEALTH_URL", "http://soar_docs_site:8086/"),
            'docs_container': os.getenv("DOCS_CONTAINER", "soar_docs_site"),
            'api_health_url': os.getenv("API_HEALTH_URL", "http://soar_api:8000/health"),
            'api_container': os.getenv("API_CONTAINER", "soar_api"),
            'elasticsearch_health_url': os.getenv("ELASTICSEARCH_HEALTH_URL",
                                                  "http://soar_elasticsearch:9200/_cluster/health"),
            'elasticsearch_container': os.getenv("ELASTICSEARCH_CONTAINER", "soar_elasticsearch"),
            'nginx_health_url': os.getenv("NGINX_HEALTH_URL", "http://soar_nginx:80/"),
            'nginx_container': os.getenv("NGINX_CONTAINER", "soar_nginx"),
            'redis_health_url': os.getenv("REDIS_HEALTH_URL", "http://soar_redis:6379/"),
            'redis_container': os.getenv("REDIS_CONTAINER", "soar_redis"),
            'loki_health_url': os.getenv("LOKI_HEALTH_URL", "http://soar_loki:3100/ready"),
            'loki_container': os.getenv("LOKI_CONTAINER", "soar_loki"),
            'grafana_health_url': os.getenv("GRAFANA_HEALTH_URL", "http://soar_grafana:3000/api/health"),
            'grafana_container': os.getenv("GRAFANA_CONTAINER", "soar_grafana"),
            'promtail_health_url': os.getenv("PROMTAIL_HEALTH_URL", "http://soar_promtail:9080/"),
            'promtail_container': os.getenv("PROMTAIL_CONTAINER", "soar_promtail"),
            'misp_health_url': os.getenv("MISP_HEALTH_URL", "http://soar_misp:8083/"),
            'misp_container': os.getenv("MISP_CONTAINER", "soar_misp"),
            'wazuh_dashboard_health_url': os.getenv("WAZUH_DASHBOARD_HEALTH_URL", "http://soar_wazuh_dashboard:443/"),
            'wazuh_dashboard_container': os.getenv("WAZUH_DASHBOARD_CONTAINER", "soar_wazuh_dashboard"),
        }

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value from unified _config dict.
        
        All environment variables are loaded once at initialization time
        via _load_config(). This eliminates multiple sources of truth.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self._config[key] = value

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration"""
        return self._config.copy()

    def validate(self) -> bool:
        """Validate configuration"""
        required_keys = [
            'elastic_password',
            'thehive_secret',
            'thehive_api_key',
            'cortex_secret',
            'cortex_api_key',
            'siem_webhook_token',
        ]

        missing_keys = []
        for key in required_keys:
            if not self.get(key):
                missing_keys.append(key)

        if missing_keys:
            logger.warning(f"Missing required configuration: {', '.join(missing_keys)}")
            return False

        return True

    def get_service_urls(self) -> Dict[str, Dict[str, str]]:
        """Get service URLs and container names for health checks"""
        return {
            "thehive": {
                "url": self._config.get('thehive_health_url'),
                "container": self._config.get('thehive_container'),
            },
            "cortex": {
                "url": self._config.get('cortex_health_url'),
                "container": self._config.get('cortex_container'),
            },
            "shuffle-frontend": {
                "url": self._config.get('shuffle_ui_health_url'),
                "container": self._config.get('shuffle_frontend_container'),
            },
            "shuffle-backend": {
                "url": self._config.get('shuffle_health_url'),
                "container": self._config.get('shuffle_container'),
            },
            "kibana": {
                "url": self._config.get('kibana_health_url'),
                "container": self._config.get('kibana_container'),
            },
            "docs-site": {
                "url": self._config.get('docs_health_url'),
                "container": self._config.get('docs_container'),
            },
            "api": {
                "url": self._config.get('api_health_url'),
                "container": self._config.get('api_container'),
            },
            "elasticsearch": {
                "url": self._config.get('elasticsearch_health_url'),
                "container": self._config.get('elasticsearch_container'),
            },
            "nginx": {
                "url": self._config.get('nginx_health_url'),
                "container": self._config.get('nginx_container'),
            },
            "redis": {
                "url": self._config.get('redis_health_url'),
                "container": self._config.get('redis_container'),
            },
            "loki": {
                "url": self._config.get('loki_health_url'),
                "container": self._config.get('loki_container'),
            },
            "grafana": {
                "url": self._config.get('grafana_health_url'),
                "container": self._config.get('grafana_container'),
            },
            "promtail": {
                "url": self._config.get('promtail_health_url'),
                "container": self._config.get('promtail_container'),
            },
            "misp": {
                "url": self._config.get('misp_health_url'),
                "container": self._config.get('misp_container'),
            },
            "wazuh-dashboard": {
                "url": self._config.get('wazuh_dashboard_health_url'),
                "container": self._config.get('wazuh_dashboard_container'),
            },
        }

    def get_webhook_url(self) -> str:
        """Get Shuffle webhook URL"""
        return self._config.get('shuffle_webhook_url', 'http://localhost:5001/api/v1/hooks')

    def __str__(self) -> str:
        """String representation of configuration"""
        return f"Settings(project={self.get('project_name')})"


# Factory function to create Settings instances
def create_settings() -> Settings:
    """Factory function to create a Settings instance."""
    return Settings()
