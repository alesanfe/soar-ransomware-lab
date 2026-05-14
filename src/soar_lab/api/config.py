"""Configuration module for SOAR Lab API."""
import logging
import os
import docker
import redis
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_TITLE: str = "SOAR Lab Management API"
    API_DESCRIPTION: str = "REST API for SOAR Ransomware Lab Management"
    API_VERSION: str = "1.0.0"
    
    # Authentication
    WEB_UI_USER: Optional[str] = os.getenv("WEB_UI_USER")
    WEB_UI_PASSWORD: Optional[str] = os.getenv("WEB_UI_PASSWORD")
    API_AUTH_SECRET: Optional[str] = os.getenv("API_AUTH_SECRET")
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY", os.getenv("API_AUTH_SECRET", "change-this-in-production"))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    
    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:3000").split(",")
    
    # Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # Backup
    BACKUP_DIR: str = "backups"
    BACKUP_TIMEOUT_SECONDS: int = 300
    
    # Test execution
    TEST_TIMEOUT_SECONDS: int = 300
    TEST_COVERAGE_PATH: str = "src/soar_lab"
    
    # Service configuration
    SERVICES: Dict[str, Dict[str, str]] = {
        "thehive": {"url": "http://localhost:9000/api/health", "container": "soar_thehive"},
        "cortex": {"url": "http://localhost:9001/", "container": "soar_cortex"},
        "shuffle": {"url": "http://localhost:5001/api/v1/health", "container": "soar_shuffle_backend"},
        "kibana": {"url": "http://localhost:15601/api/status", "container": "soar_wazuh_dashboard"},
        "wazuh-manager": {"url": "http://localhost:55100/", "container": "soar_wazuh_manager"},
        "misp": {"url": "http://localhost:8082/users/heartbeat", "container": "soar_misp"},
        "docs-site": {"url": "http://localhost:3000/docs/", "container": "soar_docs_site"},
        "api": {"url": "http://localhost:8000/health", "container": "soar_api"}
    }


settings = Settings()


def get_redis_client() -> Optional[redis.Redis]:
    """Initialize and return Redis client."""
    try:
        if not settings.REDIS_URL:
            logger.warning("REDIS_URL environment variable not set, Redis caching disabled")
            return None
        
        client = redis.from_url(settings.REDIS_URL)
        client.ping()
        logger.info("Connected to Redis")
        return client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return None


def get_docker_client() -> Optional[docker.DockerClient]:
    """Initialize and return Docker client."""
    try:
        client = docker.from_env()
        logger.info("Connected to Docker")
        return client
    except Exception as e:
        logger.error(f"Docker connection failed: {e}")
        return None


# Initialize clients
redis_client = get_redis_client()
docker_client = get_docker_client()
