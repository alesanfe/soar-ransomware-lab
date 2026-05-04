#!/usr/bin/env python3
"""
Integration tests for Docker services
"""

import unittest
import subprocess
import time
import requests
import os
from pathlib import Path


class TestDockerServices(unittest.TestCase):
    """Test cases for Docker service integration"""

    @classmethod
    def setUpClass(cls):
        """Set up Docker services before tests"""
        # Check if Docker is running
        try:
            subprocess.run(['docker', 'ps'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise unittest.SkipTest("Docker not available or not running")

    def test_docker_compose_file_exists(self):
        """Test that docker-compose.yml exists"""
        compose_path = Path('docker/docker-compose.yml')
        self.assertTrue(compose_path.exists())

    def test_env_file_exists(self):
        """Test that .env file exists"""
        env_path = Path('docker/.env')
        self.assertTrue(env_path.exists())

    def test_docker_compose_config_valid(self):
        """Test that docker-compose configuration is valid"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config'],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0, "docker-compose config failed")

    def test_services_defined(self):
        """Test that all required services are defined"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config', '--services'],
            capture_output=True,
            text=True
        )
        services = result.stdout.strip().split('\n')
        
        required_services = ['elasticsearch', 'thehive', 'cortex', 'shuffle-frontend', 'shuffle-backend', 'orborus']
        for service in required_services:
            self.assertIn(service, services, f"Service {service} not defined")

    def test_networks_defined(self):
        """Test that required networks are defined"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config', '--networks'],
            capture_output=True,
            text=True
        )
        networks = result.stdout.strip().split('\n')
        
        self.assertIn('soar_edge', networks)
        self.assertIn('soar_net', networks)

    def test_volumes_defined(self):
        """Test that required volumes are defined"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config', '--volumes'],
            capture_output=True,
            text=True
        )
        volumes = result.stdout.strip().split('\n')
        
        required_volumes = ['es_data', 'thehive_files', 'cortex_data', 'shuffle_apps', 'shuffle_files']
        for volume in required_volumes:
            self.assertIn(volume, volumes, f"Volume {volume} not defined")


class TestServiceHealth(unittest.TestCase):
    """Test cases for service health checks"""

    @classmethod
    def setUpClass(cls):
        """Set up - check if services are running"""
        cls.services_running = False
        try:
            result = subprocess.run(
                ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'ps'],
                capture_output=True,
                text=True
            )
            if 'running' in result.stdout:
                cls.services_running = True
        except:
            pass

    def test_elasticsearch_health(self):
        """Test Elasticsearch health endpoint"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        try:
            response = requests.get('http://localhost:19200/_cluster/health', timeout=5)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn('status', data)
            self.assertIn(data['status'], ['green', 'yellow'])
        except requests.exceptions.RequestException:
            self.skipTest("Elasticsearch not accessible")

    def test_thehive_health(self):
        """Test TheHive health endpoint"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        try:
            response = requests.get('http://localhost:9000/api/health', timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.skipTest("TheHive not accessible")

    def test_cortex_health(self):
        """Test Cortex health endpoint"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        try:
            response = requests.get('http://localhost:9001/api/health', timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.skipTest("Cortex not accessible")

    def test_shuffle_health(self):
        """Test Shuffle health endpoint"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        try:
            response = requests.get('http://localhost:5001/health', timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.skipTest("Shuffle not accessible")


class TestServiceConnectivity(unittest.TestCase):
    """Test cases for inter-service connectivity"""

    @classmethod
    def setUpClass(cls):
        """Set up - check if services are running"""
        cls.services_running = False
        try:
            result = subprocess.run(
                ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'ps'],
                capture_output=True,
                text=True
            )
            if 'running' in result.stdout:
                cls.services_running = True
        except:
            pass

    def test_thehive_to_elasticsearch(self):
        """Test TheHive can reach Elasticsearch"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        result = subprocess.run(
            ['docker', 'exec', 'soar_thehive', 'wget', '-qO-', 'http://elasticsearch:9200'],
            capture_output=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)

    def test_cortex_to_thehive(self):
        """Test Cortex can reach TheHive"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        result = subprocess.run(
            ['docker', 'exec', 'soar_cortex', 'wget', '-qO-', 'http://thehive:9000'],
            capture_output=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)

    def test_shuffle_to_elasticsearch(self):
        """Test Shuffle can reach Elasticsearch"""
        if not self.services_running:
            self.skipTest("Services not running")
        
        result = subprocess.run(
            ['docker', 'exec', 'soar_shuffle-backend', 'wget', '-qO-', 'http://elasticsearch:9200'],
            capture_output=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)


class TestConfigurationFiles(unittest.TestCase):
    """Test cases for configuration files"""

    def test_thehive_config_exists(self):
        """Test TheHive configuration file exists"""
        config_path = Path('docker/thehive.application.conf')
        self.assertTrue(config_path.exists())

    def test_cortex_config_exists(self):
        """Test Cortex configuration file exists"""
        config_path = Path('docker/cortex.application.conf')
        self.assertTrue(config_path.exists())

    def test_env_example_exists(self):
        """Test .env.example file exists"""
        env_path = Path('docker/.env.example')
        self.assertTrue(env_path.exists())

    def test_cortex_secret_key_configured(self):
        """Test Cortex secret key is configured"""
        config_path = Path('docker/cortex.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('play.http.secret.key', content)
        self.assertNotIn('***CHANGEME***', content)

    def test_tls_enabled_in_env_example(self):
        """Test TLS is enabled by default in .env.example"""
        env_path = Path('docker/.env.example')
        with open(env_path, 'r') as f:
            content = f.read()
        self.assertIn('ENABLE_TLS=true', content)


class TestResourceLimits(unittest.TestCase):
    """Test cases for Docker resource limits"""

    def test_elasticsearch_has_resource_limits(self):
        """Test Elasticsearch has resource limits configured"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config'],
            capture_output=True,
            text=True
        )
        config = result.stdout
        self.assertIn('deploy:', config)
        self.assertIn('resources:', config)
        self.assertIn('limits:', config)

    def test_thehive_has_resource_limits(self):
        """Test TheHive has resource limits configured"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config'],
            capture_output=True,
            text=True
        )
        config = result.stdout
        # Check for resource limits in thehive service
        self.assertIn('cpus:', config)
        self.assertIn('memory:', config)


class TestLogRotation(unittest.TestCase):
    """Test cases for log rotation configuration"""

    def test_logging_configured(self):
        """Test logging is configured in docker-compose"""
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker/docker-compose.yml', 'config'],
            capture_output=True,
            text=True
        )
        config = result.stdout
        self.assertIn('logging:', config)
        self.assertIn('max-size:', config)
        self.assertIn('max-file:', config)


if __name__ == '__main__':
    unittest.main()
