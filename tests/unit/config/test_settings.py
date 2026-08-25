#!/usr/bin/env python3
"""Unit tests for settings.py Tests configuration settings."""

import os
from pathlib import Path

import pytest

from soar_lab.config.settings import Settings


class TestSettings:
    """Test Settings configuration class."""

    @pytest.fixture
    def settings(self):
        """Create a Settings instance with BASE_DIR set."""
        # Clear environment variables to test default values
        for var in [
            "API_HOST", "REDIS_URL", "MISP_URL",
            "THEHIVE_HTTP_PORT", "CORTEX_HTTP_PORT",
            "SHUFFLE_UI_PORT", "SHUFFLE_API_PORT",
        ]:
            if var in os.environ:
                del os.environ[var]
        os.environ["BASE_DIR"] = str(Path(__file__).parent.parent.parent)
        return Settings()

    def test_initialization(self, settings):
        """Test successful initialization."""
        assert settings._config is not None
        assert settings._backup_dir_override is None

    def test_api_host_default(self, settings):
        """Test default API_HOST."""
        assert settings.API_HOST == "127.0.0.1"

    def test_api_port_default(self, settings):
        """Test default API_PORT."""
        assert settings.API_PORT == 8000

    def test_api_title(self, settings):
        """Test API_TITLE."""
        assert settings.API_TITLE == "SOAR Lab Management API"

    def test_api_description(self, settings):
        """Test API_DESCRIPTION."""
        assert settings.API_DESCRIPTION == "REST API for SOAR Ransomware Lab Management"

    def test_api_version(self, settings):
        """Test API_VERSION."""
        assert settings.API_VERSION == "1.0.0"

    def test_web_ui_user_none(self, settings):
        """Test WEB_UI_USER property exists."""
        assert hasattr(settings, "WEB_UI_USER")
        assert isinstance(settings.WEB_UI_USER, (str, type(None)))

    def test_web_ui_password_none(self, settings):
        """Test WEB_UI_PASSWORD property exists."""
        assert hasattr(settings, "WEB_UI_PASSWORD")
        assert isinstance(settings.WEB_UI_PASSWORD, (str, type(None)))

    def test_api_auth_secret_none(self, settings):
        """Test API_AUTH_SECRET property exists."""
        assert hasattr(settings, "API_AUTH_SECRET")
        assert isinstance(settings.API_AUTH_SECRET, (str, type(None)))

    def test_jwt_secret_key_default(self, settings):
        """Test JWT_SECRET_KEY property exists."""
        assert hasattr(settings, "JWT_SECRET_KEY")
        assert isinstance(settings.JWT_SECRET_KEY, str)

    def test_jwt_algorithm(self, settings):
        """Test JWT_ALGORITHM."""
        assert settings.JWT_ALGORITHM == "HS256"

    def test_jwt_expiration_minutes_default(self, settings):
        """Test default JWT_EXPIRATION_MINUTES."""
        assert settings.JWT_EXPIRATION_MINUTES == 60

    def test_cors_origins_default(self, settings):
        """Test CORS_ORIGINS property exists and is list."""
        assert hasattr(settings, "CORS_ORIGINS")
        assert isinstance(settings.CORS_ORIGINS, list)

    def test_redis_url_none(self, settings):
        """Test REDIS_URL when not set."""
        assert settings.REDIS_URL is None

    def test_backup_dir_default(self, settings):
        """Test default BACKUP_DIR."""
        assert settings.BACKUP_DIR is not None

    def test_backup_dir_override(self, settings):
        """Test BACKUP_DIR override for testing."""
        settings.BACKUP_DIR = "/custom/backup/path"
        assert settings.BACKUP_DIR == "/custom/backup/path"

    def test_backup_timeout_seconds(self, settings):
        """Test BACKUP_TIMEOUT_SECONDS."""
        assert settings.BACKUP_TIMEOUT_SECONDS == 600

    def test_test_timeout_seconds(self, settings):
        """Test TEST_TIMEOUT_SECONDS."""
        assert settings.TEST_TIMEOUT_SECONDS == 300

    def test_test_coverage_path(self, settings):
        """Test TEST_COVERAGE_PATH."""
        assert settings.TEST_COVERAGE_PATH == "src/soar_lab"

    def test_base_dir_required(self):
        """Test that BASE_DIR is required."""
        # Clear BASE_DIR if set
        if "BASE_DIR" in os.environ:
            del os.environ["BASE_DIR"]

        with pytest.raises(ValueError, match="BASE_DIR environment variable must be set"):
            Settings()

    def test_load_config_from_env(self):
        """Test loading config from environment variables."""
        os.environ["BASE_DIR"] = str(Path(__file__).parent.parent.parent)
        os.environ["API_HOST"] = "192.168.1.1"
        os.environ["API_PORT"] = "9000"

        settings = Settings()

        assert settings.API_HOST == "192.168.1.1"
        assert settings.API_PORT == 9000

        # Clean up
        del os.environ["API_HOST"]
        del os.environ["API_PORT"]

    def test_project_name_default(self, settings):
        """Test project name exists."""
        assert "project_name" in settings._config
        assert isinstance(settings._config.get("project_name"), str)

    def test_thehive_port_default(self, settings):
        """Test default THEHIVE_HTTP_PORT."""
        assert settings._config.get("thehive_port") == 9000

    def test_cortex_port_default(self, settings):
        """Test default CORTEX_HTTP_PORT."""
        assert settings._config.get("cortex_port") == 9001

    def test_shuffle_ui_port_default(self, settings):
        """Test default SHUFFLE_UI_PORT."""
        assert settings._config.get("shuffle_ui_port") == 8081

    def test_shuffle_api_port_default(self, settings):
        """Test default SHUFFLE_API_PORT."""
        assert settings._config.get("shuffle_api_port") == 5001

    def test_elasticsearch_port_default(self, settings):
        """Test elasticsearch port exists."""
        assert "elasticsearch_port" in settings._config
        assert isinstance(settings._config.get("elasticsearch_port"), int)

    def test_misp_port_default(self, settings):
        """Test default MISP_PORT."""
        assert settings._config.get("misp_port") == 8083

    def test_http_port_default(self, settings):
        """Test default HTTP_PORT."""
        assert settings._config.get("http_port") == 80

    def test_thehive_url_default(self, settings):
        """Test default THEHIVE_URL."""
        assert settings._config.get("thehive_url") == "http://thehive:9000"

    def test_cortex_url_default(self, settings):
        """Test default CORTEX_URL."""
        assert settings._config.get("cortex_url") == "http://cortex:9001"

    def test_shuffle_url_default(self, settings):
        """Test default SHUFFLE_URL."""
        assert settings._config.get("shuffle_url") == "http://shuffle-backend:5001"

    def test_misp_url_default(self, settings):
        """Test default MISP_URL."""
        assert settings._config.get("misp_url") == "http://misp:80"

    def test_elasticsearch_url_default(self, settings):
        """Test default ELASTICSEARCH_URL."""
        assert settings._config.get("elasticsearch_url") == "http://elasticsearch:9200"

    def test_shuffle_webhook_url_default(self, settings):
        """Test default SHUFFLE_WEBHOOK_URL."""
        assert settings._config.get("shuffle_webhook_url") == "http://localhost:5001/api/v1/hooks"

    def test_elastic_security_enabled_default(self, settings):
        """Test ELASTIC_SECURITY_ENABLED exists."""
        assert "elastic_security_enabled" in settings._config
        assert isinstance(settings._config.get("elastic_security_enabled"), bool)

    def test_elastic_password_default(self, settings):
        """Test ELASTIC_PASSWORD exists."""
        assert "elastic_password" in settings._config
        assert isinstance(settings._config.get("elastic_password"), str)

    def test_thehive_secret_default(self, settings):
        """Test THEHIVE_SECRET exists."""
        assert "thehive_secret" in settings._config
        assert isinstance(settings._config.get("thehive_secret"), str)

    def test_thehive_api_key_default(self, settings):
        """Test THEHIVE_API_KEY exists."""
        assert "thehive_api_key" in settings._config
        assert isinstance(settings._config.get("thehive_api_key"), str)

    def test_cortex_secret_default(self, settings):
        """Test CORTEX_SECRET exists."""
        assert "cortex_secret" in settings._config
        assert isinstance(settings._config.get("cortex_secret"), str)

    def test_cortex_api_key_default(self, settings):
        """Test CORTEX_API_KEY exists."""
        assert "cortex_api_key" in settings._config
        assert isinstance(settings._config.get("cortex_api_key"), str)

    def test_shuffle_username_default(self, settings):
        """Test SHUFFLE_DEFAULT_USERNAME exists."""
        assert "shuffle_username" in settings._config
        assert isinstance(settings._config.get("shuffle_username"), str)

    def test_shuffle_password_default(self, settings):
        """Test SHUFFLE_DEFAULT_PASSWORD exists."""
        assert "shuffle_password" in settings._config
        assert isinstance(settings._config.get("shuffle_password"), str)

    def test_shuffle_api_key_default(self, settings):
        """Test SHUFFLE_DEFAULT_APIKEY exists."""
        assert "shuffle_api_key" in settings._config
        assert isinstance(settings._config.get("shuffle_api_key"), str)

    def test_misp_api_key_default(self, settings):
        """Test MISP_API_KEY exists."""
        assert "misp_api_key" in settings._config
        assert isinstance(settings._config.get("misp_api_key"), str)

    def test_siem_webhook_token_default(self, settings):
        """Test SIEM_WEBHOOK_TOKEN exists."""
        assert "siem_webhook_token" in settings._config
        assert isinstance(settings._config.get("siem_webhook_token"), str)

    def test_edr_sim_token_default(self, settings):
        """Test EDR_SIM_TOKEN exists."""
        assert "edr_sim_token" in settings._config
        assert isinstance(settings._config.get("edr_sim_token"), str)

    def test_firewall_sim_token_default(self, settings):
        """Test FIREWALL_SIM_TOKEN exists."""
        assert "firewall_sim_token" in settings._config
        assert isinstance(settings._config.get("firewall_sim_token"), str)

    def test_decision_score_threshold_default(self, settings):
        """Test DECISION_SCORE_THRESHOLD exists."""
        assert "decision_score_threshold" in settings._config
        assert isinstance(settings._config.get("decision_score_threshold"), int)

    def test_postgres_user_default(self, settings):
        """Test POSTGRES_USER exists."""
        assert "postgres_user" in settings._config
        assert isinstance(settings._config.get("postgres_user"), str)

    def test_postgres_password_default(self, settings):
        """Test POSTGRES_PASSWORD exists."""
        assert "postgres_password" in settings._config
        assert isinstance(settings._config.get("postgres_password"), str)

    def test_postgres_db_default(self, settings):
        """Test POSTGRES_DB exists."""
        assert "postgres_db" in settings._config
        assert isinstance(settings._config.get("postgres_db"), str)

    def test_redis_password_default(self, settings):
        """Test REDIS_PASSWORD exists."""
        assert "redis_password" in settings._config
        assert isinstance(settings._config.get("redis_password"), str)

    def test_log_level_default(self, settings):
        """Test default LOG_LEVEL."""
        assert settings._config.get("log_level") == "INFO"

    def test_log_format_default(self, settings):
        """Test default LOG_FORMAT."""
        assert settings._config.get("log_format") == "json"

    def test_max_concurrent_analyzers_default(self, settings):
        """Test default MAX_CONCURRENT_ANALYZERS."""
        assert settings._config.get("max_concurrent_analyzers") == 3

    def test_analyzer_timeout_default(self, settings):
        """Test default ANALYZER_TIMEOUT."""
        assert settings._config.get("analyzer_timeout") == 30

    def test_analyzer_retries_default(self, settings):
        """Test default ANALYZER_RETRIES."""
        assert settings._config.get("analyzer_retries") == 1

    def test_webhook_rate_limit_default(self, settings):
        """Test default WEBHOOK_RATE_LIMIT."""
        assert settings._config.get("webhook_rate_limit") == 60

    def test_webhook_payload_max_size_default(self, settings):
        """Test default WEBHOOK_PAYLOAD_MAX_SIZE."""
        assert settings._config.get("webhook_payload_max_size") == 65536

    def test_health_check_interval_default(self, settings):
        """Test default HEALTH_CHECK_INTERVAL."""
        assert settings._config.get("health_check_interval") == "30s"

    def test_health_check_timeout_default(self, settings):
        """Test default HEALTH_CHECK_TIMEOUT."""
        assert settings._config.get("health_check_timeout") == "10s"

    def test_health_check_retries_default(self, settings):
        """Test default HEALTH_CHECK_RETRIES."""
        assert settings._config.get("health_check_retries") == 3

    def test_retention_days_default(self, settings):
        """Test default RETENTION_DAYS."""
        assert settings._config.get("retention_days") == 7

    def test_compress_backups_default(self, settings):
        """Test default COMPRESS."""
        assert settings._config.get("compress_backups") == True

    def test_get_method(self, settings):
        """Test get method."""
        value = settings.get("api_host")
        assert value == "127.0.0.1"

    def test_get_method_with_default(self, settings):
        """Test get method with default value."""
        value = settings.get("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_set_method(self, settings):
        """Test set method."""
        settings.set("custom_key", "custom_value")
        assert settings.get("custom_key") == "custom_value"

    def test_get_all_method(self, settings):
        """Test get_all method."""
        all_config = settings.get_all()
        assert isinstance(all_config, dict)
        assert "api_host" in all_config
        assert "base_dir" in all_config

    def test_validate_missing_keys(self, settings):
        """Test validate with missing required keys."""
        # Set required keys to empty
        settings.set("elastic_password", "")
        settings.set("thehive_secret", "")
        settings.set("thehive_api_key", "")
        settings.set("cortex_secret", "")
        settings.set("cortex_api_key", "")
        settings.set("siem_webhook_token", "")

        result = settings.validate()
        assert result is False

    def test_validate_success(self, settings):
        """Test validate with all required keys."""
        settings.set("elastic_password", "test_password")
        settings.set("thehive_secret", "test_secret")
        settings.set("thehive_api_key", "test_key")
        settings.set("cortex_secret", "test_secret")
        settings.set("cortex_api_key", "test_key")
        settings.set("siem_webhook_token", "test_token")

        result = settings.validate()
        assert result is True

    def test_get_service_urls(self, settings):
        """Test get_service_urls method."""
        service_urls = settings.get_service_urls()
        assert isinstance(service_urls, dict)
        assert "thehive" in service_urls
        assert "cortex" in service_urls
        assert "shuffle-backend" in service_urls
        assert "elasticsearch" in service_urls

        # Check structure of one service
        thehive = service_urls["thehive"]
        assert "url" in thehive
        assert "container" in thehive

    def test_get_webhook_url(self, settings):
        """Test get_webhook_url method."""
        webhook_url = settings.get_webhook_url()
        assert isinstance(webhook_url, str)
        assert "api/v1/hooks" in webhook_url

    def test_str_method(self, settings):
        """Test __str__ method."""
        str_repr = str(settings)
        assert "Settings" in str_repr
        assert "project=" in str_repr
