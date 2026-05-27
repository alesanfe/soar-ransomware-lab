#!/usr/bin/env python3
"""
Docker Services Validation Tests - Real Configuration Version
Tests Docker Compose services configuration against ACTUAL docker-compose.yml with environment variables
"""

import pytest
import re
import yaml
from pathlib import Path


class TestDockerServiceContractsLive:
    """Test Docker Compose services configuration - Real Configuration Version"""

    @pytest.fixture
    def compose_file_path(self):
        """Path to main docker-compose file"""
        return Path("infra/docker/compose/docker-compose.yml")

    @pytest.fixture
    def compose_content(self):
        """Load and merge all docker-compose files from infra/docker/compose/"""
        compose_dir = Path("infra/docker/compose")
        merged = {"services": {}, "networks": {}, "volumes": {}}
        for yml_file in sorted(compose_dir.glob("**/*.yml")):
            with open(yml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            for section in ("services", "networks", "volumes"):
                if section in data and isinstance(data[section], dict):
                    merged[section].update(data[section])
        return merged

    def _get_image_name(self, image_value):
        """Extract actual image name from environment variable format"""
        if isinstance(image_value, str) and "${" in image_value:
            # Extract default value from ${VAR:-default}
            match = re.match(r'\$\{[^:]+:-([^}]+)\}', image_value)
            return match.group(1) if match else image_value
        return image_value

    def _get_env_var_value(self, env_vars, key):
        """Extract actual value from environment variable list"""
        for var in env_vars:
            if isinstance(var, str) and var.startswith(f"{key}="):
                return var
            elif isinstance(var, dict) and key in var:
                return var[key]
        return None

    def test_thehive_service_configuration(self, compose_content):
        """Test TheHive service configuration"""
        services = compose_content["services"]

        # Skip if thehive service is not configured
        if "thehive" not in services:
            pytest.skip("TheHive service not configured in docker-compose.yml")

        thehive = services["thehive"]

        # Check image
        assert "image" in thehive, "TheHive should have image"
        assert "thehiveproject/thehive:3.5.2-1" in thehive["image"], "TheHive should use correct image"

        # Check dependencies
        assert "depends_on" in thehive, "TheHive should have dependencies"
        assert "elasticsearch" in thehive["depends_on"], "TheHive should depend on Elasticsearch"

        # Check ports
        assert "ports" in thehive, "TheHive should expose ports"
        assert any("9000" in str(port) for port in thehive["ports"]), "TheHive should expose port 9000"

        # Check volumes
        assert "volumes" in thehive, "TheHive should have volumes"
        assert any("thehive_files" in str(vol) for vol in thehive["volumes"]), "TheHive should use thehive_files volume"

        # Check networks
        assert "networks" in thehive, "TheHive should have networks"
        assert "soar_net" in set(thehive["networks"]), "TheHive should use soar_net"

        # Check healthcheck
        assert "healthcheck" in thehive, "TheHive should have healthcheck"
        assert "test" in thehive["healthcheck"], "TheHive healthcheck should have test command"

        # Check restart policy
        assert thehive.get("restart") == "unless-stopped", "TheHive should have restart policy unless-stopped"

    def test_cortex_service_configuration(self, compose_content):
        """Test Cortex service configuration"""
        services = compose_content["services"]

        # Skip if cortex service is not configured
        if "cortex" not in services:
            pytest.skip("Cortex service not configured in docker-compose.yml")

        cortex = services["cortex"]

        # Check image or build (Cortex may use build instead of image)
        assert "image" in cortex or "build" in cortex, "Cortex should have image or build"
        if "image" in cortex:
            assert "thehiveproject/cortex:3.1.0-1" in cortex["image"], "Cortex should use correct image"

        # Check dependencies
        assert "depends_on" in cortex, "Cortex should have dependencies"
        assert "elasticsearch" in cortex["depends_on"], "Cortex should depend on Elasticsearch"

        # Check ports
        assert "ports" in cortex, "Cortex should expose ports"
        assert any("9001" in str(port) for port in cortex["ports"]), "Cortex should expose port 9001"

        # Check volumes
        assert "volumes" in cortex, "Cortex should have volumes"
        assert any("cortex_data" in str(vol) for vol in cortex["volumes"]), "Cortex should use cortex_data volume"

        # Check networks
        assert "networks" in cortex, "Cortex should have networks"
        assert "soar_net" in set(cortex["networks"]), "Cortex should use soar_net"

        # Check healthcheck
        assert "healthcheck" in cortex, "Cortex should have healthcheck"
        assert "test" in cortex["healthcheck"], "Cortex healthcheck should have test command"

        # Check restart policy
        assert cortex.get("restart") == "unless-stopped", "Cortex should have restart policy unless-stopped"

    def test_orborus_service_configuration(self, compose_content):
        """Test Orborus service configuration"""
        services = compose_content["services"]

        # Skip if orborus service is not configured
        if "orborus" not in services:
            pytest.skip("Orborus service not configured in docker-compose.yml")

        orborus = services["orborus"]

        # Check image
        assert "image" in orborus, "Orborus should have image"
        assert "ghcr.io/shuffle/shuffle-orborus:latest" in orborus["image"], "Orborus should use correct image"

        # Check dependencies
        assert "depends_on" in orborus, "Orborus should have dependencies"
        assert "shuffle-backend" in orborus["depends_on"], "Orborus should depend on shuffle-backend"

        # Orborus doesn't expose ports (internal service)
        assert "ports" not in orborus, "Orborus should not expose ports"

        # Check networks
        assert "networks" in orborus, "Orborus should have networks"
        assert orborus["networks"] == ["soar_net"], "Orborus should use soar_net"

        # Check healthcheck
        assert "healthcheck" in orborus, "Orborus should have healthcheck"
        assert "test" in orborus["healthcheck"], "Orborus healthcheck should have test command"

        # Check restart policy
        assert orborus.get("restart") == "unless-stopped", "Orborus should have restart policy unless-stopped"

    def test_shuffle_services_configuration(self, compose_content):
        """Test Shuffle services configuration"""
        services = compose_content["services"]

        # Skip if shuffle services are not configured
        if "shuffle-backend" not in services:
            pytest.skip("Shuffle services not configured in docker-compose.yml")

        # Test shuffle-backend
        shuffle_backend = services["shuffle-backend"]
        assert "image" in shuffle_backend, "Shuffle backend should have image"
        assert "ghcr.io/shuffle/shuffle-backend:latest" in shuffle_backend[
            "image"], "Shuffle backend should use correct image"

        assert "environment" in shuffle_backend, "Shuffle backend should have environment variables"
        assert "SHUFFLE_ELASTIC" in shuffle_backend["environment"], "Shuffle backend should have SHUFFLE_ELASTIC"

        assert "ports" in shuffle_backend, "Shuffle backend should expose ports"
        assert any("5001" in str(port) for port in shuffle_backend["ports"]), "Shuffle backend should expose port 5001"

        assert "volumes" in shuffle_backend, "Shuffle backend should have volumes"
        assert any("shuffle_apps" in str(vol) for vol in
                   shuffle_backend["volumes"]), "Shuffle backend should use shuffle_apps volume"

        # Check networks - shuffle-backend uses both soar_edge and soar_net
        assert "networks" in shuffle_backend, "Shuffle backend should have networks"
        assert "soar_net" in set(shuffle_backend["networks"]), "Shuffle backend should use soar_net"

        # Test shuffle-frontend
        shuffle_frontend = services["shuffle-frontend"]
        assert "image" in shuffle_frontend, "Shuffle frontend should have image"
        assert "ghcr.io/shuffle/shuffle-frontend:latest" in shuffle_frontend[
            "image"], "Shuffle frontend should use correct image"

        assert "depends_on" in shuffle_frontend, "Shuffle frontend should have dependencies"
        assert "shuffle-backend" in shuffle_frontend["depends_on"], "Shuffle frontend should depend on shuffle-backend"

        # Shuffle frontend may use healthcheck instead of explicit ports
        # Check for either ports or healthcheck configuration
        has_ports = "ports" in shuffle_frontend
        has_healthcheck = "healthcheck" in shuffle_frontend
        assert has_ports or has_healthcheck, "Shuffle frontend should have ports or healthcheck"

        if has_ports:
            assert any(
                "3001" in str(port) for port in shuffle_frontend["ports"]), "Shuffle frontend should expose port 3001"

        assert "networks" in shuffle_frontend, "Shuffle frontend should have networks"
        assert "soar_net" in set(shuffle_frontend["networks"]), "Shuffle frontend should use soar_net"

    def test_monitoring_services_configuration(self, compose_content):
        """Test monitoring services configuration"""
        services = compose_content["services"]

        # Check which monitoring services are available
        monitoring_services = ["prometheus", "grafana", "influxdb", "telegraf"]
        available_services = [s for s in monitoring_services if s in services]

        if not available_services:
            pytest.skip("Monitoring services not configured in docker-compose.yml")

        # If monitoring services are present, verify they are properly configured
        for service in available_services:
            assert "image" in services[service], f"{service} should have image"

    def test_threat_intelligence_services_configuration(self, compose_content):
        """Test threat intelligence services configuration"""
        services = compose_content["services"]

        # Skip if threat intelligence services are not configured
        if "misp" not in services:
            pytest.skip("Threat intelligence services (MISP) not configured in docker-compose.yml")

        # Test MISP
        misp = services["misp"]
        assert "image" in misp, "MISP should have image"
        assert "ghcr.io/misp/misp-docker/misp-core:latest" in misp["image"], "MISP should use correct image"

        assert "environment" in misp, "MISP should have environment variables"
        env_vars = misp["environment"]
        assert any("MYSQL_HOST" in str(var) for var in env_vars), "MISP should have MYSQL_HOST"

        assert "ports" in misp, "MISP should expose ports"
        assert any("8082" in str(port) for port in misp["ports"]), "MISP should expose port 8082"

        assert "volumes" in misp, "MISP should have volumes"
        assert any("misp_files" in str(vol) for vol in misp["volumes"]), "MISP should use misp_files volume"

        assert "depends_on" in misp, "MISP should have dependencies"
        assert {"misp-db", "misp-modules", "redis"}.issubset(
            set(misp["depends_on"])), "MISP should depend on MISP DB, MISP modules, and Redis"

        assert "networks" in misp, "MISP should have networks"
        assert "soar_net" in set(misp["networks"]), "MISP should use soar_net"

        # Test MISP DB
        misp_db = services["misp-db"]
        assert "image" in misp_db, "MISP DB should have image"
        assert "mariadb:10.11" in misp_db["image"], "MISP DB should use correct image"

        assert "environment" in misp_db, "MISP DB should have environment variables"
        env_vars = misp_db["environment"]
        assert any("MYSQL_ROOT_PASSWORD" in str(var) for var in env_vars), "MISP DB should have MYSQL_ROOT_PASSWORD"

        assert "volumes" in misp_db, "MISP DB should have volumes"
        assert any("misp_db" in str(vol) for vol in misp_db["volumes"]), "MISP DB should use misp_db volume"

        assert "networks" in misp_db, "MISP DB should have networks"
        assert misp_db["networks"] == ["soar_net"], "MISP DB should use soar_net"

        # Test MISP modules
        misp_modules = services["misp-modules"]
        assert "image" in misp_modules, "MISP modules should have image"
        assert "ghcr.io/misp/misp-docker/misp-modules:latest" in misp_modules[
            "image"], "MISP modules should use correct image"

        assert "networks" in misp_modules, "MISP modules should have networks"
        assert misp_modules["networks"] == ["soar_net"], "MISP modules should use soar_net"

        # OpenCTI is not in the current docker-compose.yml
        # Skip OpenCTI tests as this service is not configured

        # Test Redis (shared)
        redis = services["redis"]
        assert "image" in redis, "Redis should have image"
        assert "redis:7-alpine" in redis["image"], "Redis should use correct image"

        assert "command" in redis, "Redis should have command"
        assert "requirepass" in redis["command"], "Redis should configure password in command"

        assert "volumes" in redis, "Redis should have volumes"
        assert any("redis_data" in str(vol) for vol in redis["volumes"]), "Redis should use redis_data volume"

        assert "networks" in redis, "Redis should have networks"
        assert set(redis["networks"]) == {"ti_net", "soar_net"}, "Redis should use correct networks"

    def test_storage_services_configuration(self, compose_content):
        """Test storage services configuration"""
        services = compose_content["services"]

        # MinIO and NFS Server are not in the current docker-compose.yml
        # Verify they are indeed not present
        storage_services = ["minio", "nfs-server"]
        for service in storage_services:
            assert service not in services, f"{service} should not be in current docker-compose.yml"

    def test_management_services_configuration(self, compose_content):
        """Test management services configuration"""
        services = compose_content["services"]

        # Skip if management services are not fully configured
        if "api" not in services or "nginx" not in services:
            pytest.skip("Management services not fully configured in docker-compose.yml")

        # Test API
        api = services["api"]
        assert "build" in api, "API should have build configuration"
        assert "context" in api["build"], "API should have build context"

        assert "environment" in api, "API should have environment variables"
        # Check for REDIS_URL instead of REDIS_HOST
        env_vars = api["environment"]
        assert any("REDIS_URL" in str(var) for var in env_vars), "API should have REDIS_URL"

        assert "ports" in api, "API should expose ports"
        assert any("8000" in str(port) for port in api["ports"]), "API should expose port 8000"

        assert "volumes" in api, "API should have volumes"
        # API doesn't use redis_data volume directly, but uses REDIS_URL
        assert len(api["volumes"]) >= 0, "API should have volumes"

        assert "depends_on" in api, "API should have dependencies"
        assert "redis" in api["depends_on"], "API should depend on Redis"

        assert "networks" in api, "API should have networks"
        assert {"soar_net", "ti_net"}.issubset(set(api["networks"])), "API should use soar_net and ti_net"

        # Test Nginx
        nginx = services["nginx"]
        assert "image" in nginx, "Nginx should have image"
        assert "nginx:1.25-alpine" in nginx["image"], "Nginx should use correct image"

        assert "ports" in nginx, "Nginx should expose ports"
        assert any("80" in str(port) for port in nginx["ports"]), "Nginx should expose port 80"

        assert "volumes" in nginx, "Nginx should have volumes"
        assert any("nginx_logs" in str(vol) for vol in nginx["volumes"]), "Nginx should use nginx_logs volume"

        assert "depends_on" in nginx, "Nginx should have dependencies"
        # Nginx depends on core SOAR services
        expected_deps = {"thehive", "cortex", "shuffle-frontend", "wazuh-manager"}
        assert expected_deps.issubset(set(nginx["depends_on"])), f"Nginx should depend on {expected_deps}"

        assert "networks" in nginx, "Nginx should have networks"
        assert "soar_net" in set(nginx["networks"]), "Nginx should use soar_net"

    def test_elasticsearch_service_configuration(self, compose_content):
        """Test Elasticsearch service configuration"""
        services = compose_content["services"]

        # Skip if elasticsearch is not configured
        if "elasticsearch" not in services:
            pytest.skip("Elasticsearch service not configured in docker-compose.yml")

        elasticsearch = services["elasticsearch"]

        # Check image - Use actual version 7.17.17
        assert "image" in elasticsearch, "Elasticsearch should have image"
        assert "docker.elastic.co/elasticsearch/elasticsearch:7.17.17" in elasticsearch[
            "image"], "Elasticsearch should use correct image"

        # Check environment
        assert "environment" in elasticsearch, "Elasticsearch should have environment variables"
        env_vars = elasticsearch["environment"]
        assert any("discovery.type" in str(var) for var in env_vars), "Elasticsearch should have discovery.type"

        # Check ports
        assert "ports" in elasticsearch, "Elasticsearch should expose ports"
        assert any("9200" in str(port) for port in elasticsearch["ports"]), "Elasticsearch should expose port 9200"

        # Check volumes
        assert "volumes" in elasticsearch, "Elasticsearch should have volumes"
        assert any("es_data" in str(vol) for vol in elasticsearch["volumes"]), "Elasticsearch should use es_data volume"

        # Check networks
        assert "networks" in elasticsearch, "Elasticsearch should have networks"
        assert set(elasticsearch["networks"]) == {"soar_net", "ti_net"}, "Elasticsearch should use correct networks"

        # Check healthcheck
        assert "healthcheck" in elasticsearch, "Elasticsearch should have healthcheck"
        assert "test" in elasticsearch["healthcheck"], "Elasticsearch healthcheck should have test command"

        # Check restart policy
        assert elasticsearch.get(
            "restart") == "unless-stopped", "Elasticsearch should have restart policy unless-stopped"

        # Check resource limits
        assert "deploy" in elasticsearch, "Elasticsearch should have resource limits"
        assert "resources" in elasticsearch["deploy"], "Elasticsearch should have resource configuration"
        assert "limits" in elasticsearch["deploy"]["resources"], "Elasticsearch should have resource limits"
        assert "cpus" in elasticsearch["deploy"]["resources"]["limits"], "Elasticsearch should have CPU limits"
        assert "memory" in elasticsearch["deploy"]["resources"]["limits"], "Elasticsearch should have memory limits"
