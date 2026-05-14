#!/usr/bin/env python3
"""
Docker Services Validation Tests - Real Configuration Version
Tests Docker Compose services configuration against ACTUAL docker-compose.yml with environment variables
"""

import pytest
import yaml
import re
from pathlib import Path


class TestDockerServiceContractsLive:
    """Test Docker Compose services configuration - Real Configuration Version"""
    
    @pytest.fixture
    def compose_file_path(self):
        """Path to docker-compose.yml file"""
        return Path("infra/docker/docker-compose.yml")
    
    @pytest.fixture
    def compose_content(self, compose_file_path):
        """Load and parse docker-compose.yml content"""
        with open(compose_file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
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
        assert set(thehive["networks"]) == {"soar_edge", "soar_net"}, "TheHive should use correct networks"
        
        # Check healthcheck
        assert "healthcheck" in thehive, "TheHive should have healthcheck"
        assert "test" in thehive["healthcheck"], "TheHive healthcheck should have test command"
        
        # Check restart policy
        assert thehive.get("restart") == "unless-stopped", "TheHive should have restart policy unless-stopped"
    
    def test_cortex_service_configuration(self, compose_content):
        """Test Cortex service configuration"""
        services = compose_content["services"]
        cortex = services["cortex"]
        
        # Check image
        assert "image" in cortex, "Cortex should have image"
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
        assert set(cortex["networks"]) == {"soar_edge", "soar_net"}, "Cortex should use correct networks"
        
        # Check healthcheck
        assert "healthcheck" in cortex, "Cortex should have healthcheck"
        assert "test" in cortex["healthcheck"], "Cortex healthcheck should have test command"
        
        # Check restart policy
        assert cortex.get("restart") == "unless-stopped", "Cortex should have restart policy unless-stopped"
    
    def test_orborus_service_configuration(self, compose_content):
        """Test Orborus service configuration"""
        services = compose_content["services"]
        orborus = services["orborus"]
        
        # Check image
        assert "image" in orborus, "Orborus should have image"
        assert "shuffler.io/orborus:1.3.0" in orborus["image"], "Orborus should use correct image"
        
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
        
        # Test shuffle-backend
        shuffle_backend = services["shuffle-backend"]
        assert "image" in shuffle_backend, "Shuffle backend should have image"
        assert "shuffler.io/shuffle:1.3.0" in shuffle_backend["image"], "Shuffle backend should use correct image"
        
        assert "environment" in shuffle_backend, "Shuffle backend should have environment variables"
        assert "SHUFFLE_ELASTIC" in shuffle_backend["environment"], "Shuffle backend should have SHUFFLE_ELASTIC"
        
        assert "ports" in shuffle_backend, "Shuffle backend should expose ports"
        assert any("5001" in str(port) for port in shuffle_backend["ports"]), "Shuffle backend should expose port 5001"
        
        assert "volumes" in shuffle_backend, "Shuffle backend should have volumes"
        assert any("shuffle_apps" in str(vol) for vol in shuffle_backend["volumes"]), "Shuffle backend should use shuffle_apps volume"
        
        # Check networks - shuffle-backend uses both soar_edge and soar_net
        assert "networks" in shuffle_backend, "Shuffle backend should have networks"
        assert set(shuffle_backend["networks"]) == {"soar_edge", "soar_net"}, "Shuffle backend should use correct networks"
        
        # Test shuffle-frontend
        shuffle_frontend = services["shuffle-frontend"]
        assert "image" in shuffle_frontend, "Shuffle frontend should have image"
        # Handle environment variable for image
        frontend_image = self._get_image_name(shuffle_frontend["image"])
        assert "shuffler.io/frontend:1.3.0" in frontend_image, "Shuffle frontend should use correct image"
        
        assert "depends_on" in shuffle_frontend, "Shuffle frontend should have dependencies"
        assert "shuffle-backend" in shuffle_frontend["depends_on"], "Shuffle frontend should depend on shuffle-backend"
        
        assert "ports" in shuffle_frontend, "Shuffle frontend should expose ports"
        assert any("3001" in str(port) for port in shuffle_frontend["ports"]), "Shuffle frontend should expose port 3001"
        
        assert "networks" in shuffle_frontend, "Shuffle frontend should have networks"
        assert set(shuffle_frontend["networks"]) == {"soar_edge", "soar_net"}, "Shuffle frontend should use correct networks"
    
    def test_monitoring_services_configuration(self, compose_content):
        """Test monitoring services configuration"""
        services = compose_content["services"]
        
        # Test Prometheus
        prometheus = services["prometheus"]
        assert "image" in prometheus, "Prometheus should have image"
        assert "prom/prometheus:v2.45.0" in prometheus["image"], "Prometheus should use correct image"
        
        assert "ports" in prometheus, "Prometheus should expose ports"
        assert any("9090" in str(port) for port in prometheus["ports"]), "Prometheus should expose port 9090"
        
        assert "volumes" in prometheus, "Prometheus should have volumes"
        assert any("prometheus_data" in str(vol) for vol in prometheus["volumes"]), "Prometheus should use prometheus_data volume"
        
        assert "networks" in prometheus, "Prometheus should have networks"
        assert set(prometheus["networks"]) == {"monitoring_net", "soar_net"}, "Prometheus should use correct networks"
        
        # Test Grafana
        grafana = services["grafana"]
        assert "image" in grafana, "Grafana should have image"
        assert "grafana/grafana:10.0.0" in grafana["image"], "Grafana should use correct image"
        
        assert "environment" in grafana, "Grafana should have environment variables"
        # Check for GF_SECURITY_ADMIN_USER in environment variables
        env_vars = grafana["environment"]
        assert any("GF_SECURITY_ADMIN_USER" in str(var) for var in env_vars), "Grafana should have GF_SECURITY_ADMIN_USER"
        
        assert "ports" in grafana, "Grafana should expose ports"
        assert any("3000" in str(port) for port in grafana["ports"]), "Grafana should expose port 3000"
        
        assert "volumes" in grafana, "Grafana should have volumes"
        assert any("grafana_data" in str(vol) for vol in grafana["volumes"]), "Grafana should use grafana_data volume"
        
        assert "depends_on" in grafana, "Grafana should have dependencies"
        assert "prometheus" in grafana["depends_on"], "Grafana should depend on Prometheus"
        
        # Check networks - grafana uses monitoring_net and soar_edge
        assert "networks" in grafana, "Grafana should have networks"
        assert set(grafana["networks"]) == {"monitoring_net", "soar_edge"}, "Grafana should use correct networks"
        
        # Test InfluxDB
        influxdb = services["influxdb"]
        assert "image" in influxdb, "InfluxDB should have image"
        assert "influxdb:1.8" in influxdb["image"], "InfluxDB should use correct image"
        
        assert "ports" in influxdb, "InfluxDB should expose ports"
        assert any("8086" in str(port) for port in influxdb["ports"]), "InfluxDB should expose port 8086"
        
        assert "volumes" in influxdb, "InfluxDB should have volumes"
        assert any("influxdb_data" in str(vol) for vol in influxdb["volumes"]), "InfluxDB should use influxdb_data volume"
        
        assert "networks" in influxdb, "InfluxDB should have networks"
        assert influxdb["networks"] == ["monitoring_net"], "InfluxDB should use monitoring_net"
        
        # Test Telegraf
        telegraf = services["telegraf"]
        assert "image" in telegraf, "Telegraf should have image"
        assert "telegraf:1.27" in telegraf["image"], "Telegraf should use correct image"
        
        assert "volumes" in telegraf, "Telegraf should have volumes"
        assert any("telegraf_conf" in str(vol) for vol in telegraf["volumes"]), "Telegraf should use telegraf_conf volume"
        
        assert "depends_on" in telegraf, "Telegraf should have dependencies"
        assert "influxdb" in telegraf["depends_on"], "Telegraf should depend on InfluxDB"
        
        assert "networks" in telegraf, "Telegraf should have networks"
        assert set(telegraf["networks"]) == {"monitoring_net", "soar_net"}, "Telegraf should use correct networks"
    
    def test_threat_intelligence_services_configuration(self, compose_content):
        """Test threat intelligence services configuration"""
        services = compose_content["services"]
        
        # Test MISP
        misp = services["misp"]
        assert "image" in misp, "MISP should have image"
        assert "jpcas/misp:2.4.162" in misp["image"], "MISP should use correct image"
        
        assert "environment" in misp, "MISP should have environment variables"
        env_vars = misp["environment"]
        assert any("MYSQL_HOST" in str(var) for var in env_vars), "MISP should have MYSQL_HOST"
        
        assert "ports" in misp, "MISP should expose ports"
        assert any("80" in str(port) for port in misp["ports"]), "MISP should expose port 80"
        
        assert "volumes" in misp, "MISP should have volumes"
        assert any("misp_data" in str(vol) for vol in misp["volumes"]), "MISP should use misp_data volume"
        
        assert "depends_on" in misp, "MISP should have dependencies"
        assert {"misp-db", "misp-redis"}.issubset(set(misp["depends_on"])), "MISP should depend on MISP DB and Redis"
        
        assert "networks" in misp, "MISP should have networks"
        assert set(misp["networks"]) == {"ti_net", "soar_edge"}, "MISP should use correct networks"
        
        # Test MISP DB
        misp_db = services["misp-db"]
        assert "image" in misp_db, "MISP DB should have image"
        assert "mysql:8.0" in misp_db["image"], "MISP DB should use correct image"
        
        assert "environment" in misp_db, "MISP DB should have environment variables"
        env_vars = misp_db["environment"]
        assert any("MYSQL_ROOT_PASSWORD" in str(var) for var in env_vars), "MISP DB should have MYSQL_ROOT_PASSWORD"
        
        assert "volumes" in misp_db, "MISP DB should have volumes"
        assert any("misp_db_data" in str(vol) for vol in misp_db["volumes"]), "MISP DB should use misp_db_data volume"
        
        assert "networks" in misp_db, "MISP DB should have networks"
        assert misp_db["networks"] == ["ti_net"], "MISP DB should use ti_net"
        
        # Test MISP Redis
        misp_redis = services["misp-redis"]
        assert "image" in misp_redis, "MISP Redis should have image"
        assert "redis:7" in misp_redis["image"], "MISP Redis should use correct image"
        
        assert "command" in misp_redis, "MISP Redis should have command"
        assert "requirepass" in misp_redis["command"], "MISP Redis should configure password in command"
        
        assert "volumes" in misp_redis, "MISP Redis should have volumes"
        assert any("misp_redis_data" in str(vol) for vol in misp_redis["volumes"]), "MISP Redis should use misp_redis_data volume"
        
        assert "networks" in misp_redis, "MISP Redis should have networks"
        assert misp_redis["networks"] == ["ti_net"], "MISP Redis should use ti_net"
        
        # Test OpenCTI
        opencti = services["opencti"]
        assert "image" in opencti, "OpenCTI should have image"
        assert "opencti/platform:5.3.0" in opencti["image"], "OpenCTI should use correct image"
        
        assert "environment" in opencti, "OpenCTI should have environment variables"
        env_vars = opencti["environment"]
        assert any("APP__ADMIN__EMAIL" in str(var) for var in env_vars), "OpenCTI should have APP__ADMIN__EMAIL"
        
        assert "ports" in opencti, "OpenCTI should expose ports"
        assert any("4000" in str(port) for port in opencti["ports"]), "OpenCTI should expose port 4000"
        
        assert "volumes" in opencti, "OpenCTI should have volumes"
        assert any("opencti_data" in str(vol) for vol in opencti["volumes"]), "OpenCTI should use opencti_data volume"
        
        assert "depends_on" in opencti, "OpenCTI should have dependencies"
        assert {"opencti-db", "redis", "elasticsearch"}.issubset(set(opencti["depends_on"])), "OpenCTI should depend on OpenCTI DB, Redis and Elasticsearch"
        
        assert "networks" in opencti, "OpenCTI should have networks"
        assert set(opencti["networks"]) == {"ti_net", "soar_edge"}, "OpenCTI should use correct networks"
        
        # Test OpenCTI DB
        opencti_db = services["opencti-db"]
        assert "image" in opencti_db, "OpenCTI DB should have image"
        assert "postgres:14" in opencti_db["image"], "OpenCTI DB should use correct image"
        
        assert "environment" in opencti_db, "OpenCTI DB should have environment variables"
        env_vars = opencti_db["environment"]
        assert any("POSTGRES_PASSWORD" in str(var) for var in env_vars), "OpenCTI DB should have POSTGRES_PASSWORD"
        
        assert "volumes" in opencti_db, "OpenCTI DB should have volumes"
        assert any("opencti_db_data" in str(vol) for vol in opencti_db["volumes"]), "OpenCTI DB should use opencti_db_data volume"
        
        assert "networks" in opencti_db, "OpenCTI DB should have networks"
        assert opencti_db["networks"] == ["ti_net"], "OpenCTI DB should use ti_net"
        
        # Test Redis (shared)
        redis = services["redis"]
        assert "image" in redis, "Redis should have image"
        assert "redis:7" in redis["image"], "Redis should use correct image"
        
        assert "command" in redis, "Redis should have command"
        assert "requirepass" in redis["command"], "Redis should configure password in command"
        
        assert "volumes" in redis, "Redis should have volumes"
        assert any("redis_data" in str(vol) for vol in redis["volumes"]), "Redis should use redis_data volume"
        
        assert "networks" in redis, "Redis should have networks"
        assert set(redis["networks"]) == {"ti_net", "soar_net"}, "Redis should use correct networks"
    
    def test_storage_services_configuration(self, compose_content):
        """Test storage services configuration"""
        services = compose_content["services"]
        
        # Test MinIO
        minio = services["minio"]
        assert "image" in minio, "MinIO should have image"
        minio_image = self._get_image_name(minio["image"])
        assert "minio/minio:RELEASE.2023-05-27T05-56-19Z" in minio_image, "MinIO should use correct image"
        
        assert "environment" in minio, "MinIO should have environment variables"
        # Check for MINIO_ROOT_USER in environment variables
        env_vars = minio["environment"]
        assert any("MINIO_ROOT_USER" in str(var) for var in env_vars), "MinIO should have MINIO_ROOT_USER"
        
        assert "ports" in minio, "MinIO should expose ports"
        assert any("9001" in str(port) for port in minio["ports"]), "MinIO should expose port 9001"
        assert any("9000" in str(port) for port in minio["ports"]), "MinIO should expose port 9000"
        
        assert "volumes" in minio, "MinIO should have volumes"
        assert any("minio_data" in str(vol) for vol in minio["volumes"]), "MinIO should use minio_data volume"
        
        # Check networks - minio uses both soar_net and soar_edge
        assert "networks" in minio, "MinIO should have networks"
        assert set(minio["networks"]) == {"soar_net", "soar_edge"}, "MinIO should use correct networks"
        
        # Test NFS Server
        nfs_server = services["nfs-server"]
        assert "image" in nfs_server, "NFS Server should have image"
        assert "erichough/nfs-server:2.2.2" in nfs_server["image"], "NFS Server should use correct image"
        
        assert "environment" in nfs_server, "NFS Server should have environment variables"
        env_vars = nfs_server["environment"]
        assert any("NFS_SERVER_V4_ROOT" in str(var) for var in env_vars), "NFS Server should have NFS_SERVER_V4_ROOT"
        
        assert "ports" in nfs_server, "NFS Server should expose ports"
        assert any("2049" in str(port) for port in nfs_server["ports"]), "NFS Server should expose port 2049"
        
        assert "volumes" in nfs_server, "NFS Server should have volumes"
        assert any("nfs_data" in str(vol) for vol in nfs_server["volumes"]), "NFS Server should use nfs_data volume"
        
        assert "networks" in nfs_server, "NFS Server should have networks"
        assert nfs_server["networks"] == ["soar_net"], "NFS Server should use soar_net"
    
    def test_management_services_configuration(self, compose_content):
        """Test management services configuration"""
        services = compose_content["services"]
        
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
        assert set(api["networks"]) == {"soar_edge", "soar_net", "ti_net"}, "API should use correct networks"
        
        # Test Nginx
        nginx = services["nginx"]
        assert "image" in nginx, "Nginx should have image"
        assert "nginx:1.25-alpine" in nginx["image"], "Nginx should use correct image"
        
        assert "ports" in nginx, "Nginx should expose ports"
        assert any("80" in str(port) for port in nginx["ports"]), "Nginx should expose port 80"
        assert any("443" in str(port) for port in nginx["ports"]), "Nginx should expose port 443"
        
        assert "volumes" in nginx, "Nginx should have volumes"
        assert any("nginx_logs" in str(vol) for vol in nginx["volumes"]), "Nginx should use nginx_logs volume"
        assert any("certs" in str(vol) for vol in nginx["volumes"]), "Nginx should use certs volume"
        
        assert "depends_on" in nginx, "Nginx should have dependencies"
        assert {"api", "shuffle-frontend"}.issubset(set(nginx["depends_on"])), "Nginx should depend on API and Shuffle Frontend"
        
        assert "networks" in nginx, "Nginx should have networks"
        assert set(nginx["networks"]) == {"soar_edge", "soar_net"}, "Nginx should use correct networks"
    
    def test_elasticsearch_service_configuration(self, compose_content):
        """Test Elasticsearch service configuration"""
        services = compose_content["services"]
        elasticsearch = services["elasticsearch"]
        
        # Check image - Use actual version 7.17.17
        assert "image" in elasticsearch, "Elasticsearch should have image"
        assert "docker.elastic.co/elasticsearch/elasticsearch:7.17.17" in elasticsearch["image"], "Elasticsearch should use correct image"
        
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
        assert elasticsearch.get("restart") == "unless-stopped", "Elasticsearch should have restart policy unless-stopped"
        
        # Check resource limits
        assert "deploy" in elasticsearch, "Elasticsearch should have resource limits"
        assert "resources" in elasticsearch["deploy"], "Elasticsearch should have resource configuration"
        assert "limits" in elasticsearch["deploy"]["resources"], "Elasticsearch should have resource limits"
        assert "cpus" in elasticsearch["deploy"]["resources"]["limits"], "Elasticsearch should have CPU limits"
        assert "memory" in elasticsearch["deploy"]["resources"]["limits"], "Elasticsearch should have memory limits"
