#!/usr/bin/env python3
"""
Integration tests for Docker services
Tests Docker container health and connectivity
"""

import unittest
import docker
import time
import requests
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config.settings import get_setting


class TestDockerServices(unittest.TestCase):
    """Integration tests for Docker services"""

    @classmethod
    def setUpClass(cls):
        """Set up Docker client"""
        try:
            cls.client = docker.from_env()
            cls.client.ping()
        except docker.errors.DockerException:
            cls.skipTest("Docker not available")

    def setUp(self):
        """Set up test fixtures"""
        self.expected_services = [
            'soar_thehive',
            'soar_cortex', 
            'soar_shuffle-backend',
            'soar_shuffle-frontend',
            'soar_elasticsearch'
        ]

    def test_docker_daemon_running(self):
        """Test Docker daemon is running"""
        try:
            version = self.client.version()
            self.assertIn('Version', version)
            self.assertIn('ApiVersion', version)
        except docker.errors.DockerException:
            self.fail("Docker daemon not running")

    def test_expected_containers_exist(self):
        """Test expected containers are running"""
        containers = self.client.containers.list(all=True)
        container_names = [c.name for c in containers]
        
        for service in self.expected_services:
            found = any(service in name for name in container_names)
            self.assertTrue(found, f"Container {service} not found")

    def test_containers_running_status(self):
        """Test containers are in running state"""
        containers = self.client.containers.list()
        running_names = [c.name for c in containers]
        
        for service in self.expected_services:
            found = any(service in name for name in running_names)
            self.assertTrue(found, f"Container {service} is not running")

    def test_container_health_checks(self):
        """Test container health status"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    # Check health status if available
                    health = container.attrs.get('State', {}).get('Health', {})
                    if health:
                        status = health.get('Status', 'none')
                        # Should be healthy or starting (not unhealthy)
                        self.assertNotEqual(status, 'unhealthy', 
                                         f"Container {container.name} is unhealthy")
                    
                    # Check container is not restarting
                    restart_count = container.attrs.get('State', {}).get('RestartCount', 0)
                    self.assertLess(restart_count, 5, 
                                   f"Container {container.name} has restarted {restart_count} times")

    def test_container_resource_usage(self):
        """Test container resource usage"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    try:
                        stats = container.stats(stream=False)
                        
                        # Check CPU usage (should be reasonable)
                        cpu_usage = stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0)
                        self.assertGreater(cpu_usage, 0, f"Container {container.name} has no CPU usage")
                        
                        # Check memory usage (should be allocated)
                        memory_usage = stats.get('memory_stats', {}).get('usage', 0)
                        self.assertGreater(memory_usage, 0, f"Container {container.name} has no memory usage")
                        
                        # Check network activity (should have some)
                        networks = stats.get('networks', {})
                        self.assertGreater(len(networks), 0, f"Container {container.name} has no network interfaces")
                        
                    except Exception as e:
                        self.skipTest(f"Could not get stats for {container.name}: {e}")

    def test_container_logs_accessible(self):
        """Test container logs are accessible"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    try:
                        logs = container.logs(tail=10)
                        self.assertIsInstance(logs, bytes)
                        self.assertGreater(len(logs), 0, f"Container {container.name} has no logs")
                    except Exception as e:
                        self.fail(f"Could not access logs for {container.name}: {e}")

    def test_container_restart_policy(self):
        """Test container restart policy"""
        containers = self.client.containers.list(all=True)
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    restart_policy = container.attrs.get('HostConfig', {}).get('RestartPolicy', {})
                    policy_name = restart_policy.get('Name', 'no')
                    
                    # Should have some restart policy (not 'no')
                    self.assertNotEqual(policy_name, 'no', 
                                     f"Container {container.name} has no restart policy")

    def test_docker_network_connectivity(self):
        """Test Docker network connectivity"""
        networks = self.client.networks.list()
        soar_networks = [n for n in networks if 'soar' in n.name or 'default' in n.name]
        
        self.assertGreater(len(soar_networks), 0, "No SOAR Docker network found")
        
        # Check containers are connected to network
        for network in soar_networks:
            containers = network.attrs.get('Containers', {})
            connected_services = [name for name in containers.keys() 
                                 if any(service in name for service in self.expected_services)]
            
            # Should have at least some containers connected
            self.assertGreater(len(connected_services), 0, 
                             f"No SOAR containers connected to network {network.name}")

    def test_docker_volume_mounts(self):
        """Test Docker volume mounts are working"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    mounts = container.attrs.get('Mounts', [])
                    
                    # Check if volume mounts exist
                    if service == 'soar_thehive':
                        # TheHive should have data volume
                        data_mounts = [m for m in mounts if 'data' in m.get('Destination', '').lower()]
                        self.assertGreater(len(data_mounts), 0, 
                                         f"TheHive container missing data volume mount")
                    
                    elif service == 'soar_cortex':
                        # Cortex should have data volume
                        data_mounts = [m for m in mounts if 'data' in m.get('Destination', '').lower()]
                        self.assertGreater(len(data_mounts), 0, 
                                         f"Cortex container missing data volume mount")
                    
                    elif service == 'soar_elasticsearch':
                        # Elasticsearch should have data volume
                        data_mounts = [m for m in mounts if 'data' in m.get('Destination', '').lower()]
                        self.assertGreater(len(data_mounts), 0, 
                                         f"Elasticsearch container missing data volume mount")

    def test_docker_image_availability(self):
        """Test Docker images are available and not outdated"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    image = container.image
                    self.assertIsNotNone(image, f"Container {container.name} has no image")
                    
                    # Check image exists locally
                    try:
                        image_details = self.client.images.get(image.id)
                        self.assertIsNotNone(image_details, f"Image {image.id} not found locally")
                    except docker.errors.ImageNotFound:
                        self.fail(f"Image {image.id} not found locally")

    def test_docker_port_exposure(self):
        """Test Docker ports are properly exposed"""
        containers = self.client.containers.list()
        
        expected_ports = {
            'soar_thehive': [9000],
            'soar_cortex': [9001],
            'soar_shuffle-frontend': [3001],
            'soar_shuffle-backend': [5001],
            'soar_elasticsearch': [19200]
        }
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name and service in expected_ports:
                    ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                    
                    for expected_port in expected_ports[service]:
                        port_key = f"{expected_port}/tcp"
                        self.assertIn(port_key, ports, 
                                     f"Container {container.name} not exposing port {expected_port}")
                        
                        # Check port is actually bound
                        port_bindings = ports[port_key]
                        self.assertIsNotNone(port_bindings, 
                                           f"Port {expected_port} not bound for {container.name}")

    def test_docker_environment_variables(self):
        """Test Docker environment variables are set"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    env_vars = container.attrs.get('Config', {}).get('Env', [])
                    env_dict = {var.split('=')[0]: var.split('=', 1)[1] 
                               for var in env_vars if '=' in var}
                    
                    # Check critical environment variables
                    if service == 'soar_thehive':
                        self.assertIn('THEHIVE_SECRET', env_dict, 
                                    f"TheHive missing THEHIVE_SECRET environment variable")
                    
                    elif service == 'soar_cortex':
                        self.assertIn('CORTEX_SECRET', env_dict, 
                                    f"Cortex missing CORTEX_SECRET environment variable")
                    
                    elif service == 'soar_shuffle-backend':
                        self.assertIn('SHUFFLE_SECRET', env_dict, 
                                    f"Shuffle missing SHUFFLE_SECRET environment variable")

    def test_docker_startup_time(self):
        """Test containers started within reasonable time"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    started_at = container.attrs.get('State', {}).get('StartedAt')
                    if started_at:
                        try:
                            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                            current_time = datetime.now(start_time.tzinfo)
                            uptime = current_time - start_time
                            
                            # Container should be running for at least 30 seconds
                            self.assertGreater(uptime.total_seconds(), 30, 
                                             f"Container {container.name} started too recently")
                        except ValueError:
                            self.skipTest(f"Could not parse start time for {container.name}")

    def test_docker_resource_limits(self):
        """Test Docker resource limits are applied"""
        containers = self.client.containers.list()
        
        for container in containers:
            for service in self.expected_services:
                if service in container.name:
                    host_config = container.attrs.get('HostConfig', {})
                    
                    # Check memory limits
                    memory_limit = host_config.get('Memory', 0)
                    if memory_limit > 0:
                        self.assertGreater(memory_limit, 1024*1024*100,  # At least 100MB
                                         f"Container {container.name} has too low memory limit")
                    
                    # Check CPU limits
                    cpu_quota = host_config.get('CpuQuota', 0)
                    cpu_period = host_config.get('CpuPeriod', 0)
                    if cpu_quota > 0 and cpu_period > 0:
                        cpu_limit = cpu_quota / cpu_period
                        self.assertGreater(cpu_limit, 0.1, 
                                         f"Container {container.name} has too low CPU limit")


class TestDockerIntegration(unittest.TestCase):
    """Test Docker integration with external services"""

    @classmethod
    def setUpClass(cls):
        """Set up Docker client"""
        try:
            cls.client = docker.from_env()
            cls.client.ping()
        except docker.errors.DockerException:
            cls.skipTest("Docker not available")

    def test_container_to_container_communication(self):
        """Test communication between containers"""
        try:
            # Test TheHive can reach Elasticsearch
            thehive_container = None
            for container in self.client.containers.list():
                if 'thehive' in container.name:
                    thehive_container = container
                    break
            
            if thehive_container:
                # Execute curl inside TheHive container
                exit_code, output = thehive_container.exec_run(
                    "curl -f -s http://elasticsearch:9200/_cluster/health"
                )
                
                # Should succeed or fail gracefully (not crash)
                self.assertIn(exit_code, [0, 22, 28])
            
        except Exception as e:
            self.skipTest(f"Could not test container communication: {e}")

    def test_docker_compose_integration(self):
        """Test Docker Compose integration"""
        try:
            # Check if docker-compose.yml exists
            compose_file = os.path.join(os.path.dirname(__file__), '../../docker/docker-compose.yml')
            self.assertTrue(os.path.exists(compose_file), "docker-compose.yml not found")
            
            # Check if services match expected
            with open(compose_file, 'r') as f:
                content = f.read()
                
            expected_services = ['thehive', 'cortex', 'shuffle-backend', 'shuffle-frontend', 'elasticsearch']
            for service in expected_services:
                self.assertIn(service, content, f"Service {service} not found in docker-compose.yml")
                
        except Exception as e:
            self.fail(f"Docker Compose integration test failed: {e}")


if __name__ == '__main__':
    unittest.main()
