#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Infrastructure Client Factories
Centralised initialisation of Docker and Redis clients.
Injectable for testing (call set_redis / set_docker to override).
"""

import os
from typing import Optional, Protocol

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class DockerConnectionStrategy(Protocol):
    """Protocol for Docker connection strategies."""

    def connect(self, socket_path: str) -> Optional[object]:
        """Attempt to connect to Docker and return client or None."""
        ...


class GatewayIPStrategy:
    """Connect via gateway IP (configurable)."""

    def __init__(self, gateway_ip: str):
        self.gateway_ip = gateway_ip

    def connect(self, socket_path: str) -> Optional[object]:
        try:
            import docker

            client = docker.DockerClient(base_url=f"tcp://{self.gateway_ip}:2375", version='auto')
            client.ping()
            logger.info(f"Connected to Docker via gateway IP {self.gateway_ip}:2375")
            return client
        except Exception as exc:
            logger.debug(f"Gateway IP connection failed: {exc}")
            return None


class UnixSocketStrategy:
    """Connect via unix socket with explicit version."""

    def connect(self, socket_path: str) -> Optional[object]:
        try:
            import docker

            client = docker.DockerClient(base_url=f"unix://{socket_path}", version='auto')
            client.ping()
            logger.info("Connected to Docker via unix socket with version='auto'")
            return client
        except Exception as exc:
            logger.debug(f"Unix socket with version='auto' failed: {exc}")
            return None


class DefaultFromEnvStrategy:
    """Connect using default from_env."""

    def connect(self, socket_path: str) -> Optional[object]:
        try:
            import docker

            # Use docker.from_env without modifying os.environ
            # If DOCKER_HOST is set in environment, docker.from_env will use it
            client = docker.from_env(version='auto')
            client.ping()
            logger.info("Connected to Docker via default from_env with version='auto'")
            return client
        except Exception as exc:
            logger.debug(f"Default from_env with version='auto' failed: {exc}")
            return None


def create_redis_client(config_provider=None) -> Optional[object]:
    """Create and return a Redis client from ConfigProvider."""
    try:
        import redis

        if not config_provider:
            raise ValueError("config_provider must be supplied to create_redis_client")

        redis_url = config_provider.get('REDIS_URL')

        if not redis_url:
            logger.warning("REDIS_URL not set — Redis caching disabled")
            return None

        client = redis.from_url(redis_url)
        client.ping()
        logger.info("Connected to Redis")
        return client
    except Exception as exc:
        logger.warning(f"Redis connection failed: {exc}")
        return None


def create_docker_client(config_provider=None) -> Optional[object]:
    """Create and return a Docker client using strategy pattern."""
    try:
        if not config_provider:
            raise ValueError("config_provider must be supplied to create_docker_client")

        socket_path = config_provider.get('docker_socket_path', "/var/run/docker.sock")
        gateway_ip = config_provider.get('docker_gateway_ip')

        # Try connection strategies in order
        strategies = [
            UnixSocketStrategy(),
        ]

        # Only add GatewayIPStrategy if gateway_ip is configured
        if gateway_ip:
            strategies.append(GatewayIPStrategy(gateway_ip=gateway_ip))

        strategies.extend([
            DefaultFromEnvStrategy(),
        ])

        for strategy in strategies:
            client = strategy.connect(socket_path)
            if client is not None:
                return client

        logger.error("All Docker connection methods failed")
        return None

    except Exception as exc:
        logger.error(f"Docker connection failed: {exc}")
        return None
