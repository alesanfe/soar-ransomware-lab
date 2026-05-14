#!/usr/bin/env python3
"""
Infrastructure Test Functions
Simplified test functions for infrastructure automation
"""

import docker
import requests
import json
import socket
import time


def test_docker_containers(docker_client):
    """Test all required Docker containers are running"""
    required_containers = [
        "soar_grafana", "soar_prometheus", "soar_thehive", 
        "soar_cortex", "soar_elasticsearch", "soar_redis",
        "soar_redis_exporter", "soar_elasticsearch_exporter"
    ]
    
    results = {}
    for container_name in required_containers:
        try:
            container = docker_client.containers.get(container_name)
            status = container.status
            results[container_name] = {
                "running": status == "running",
                "status": status,
                "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
            }
        except docker.errors.NotFound:
            results[container_name] = {
                "running": False,
                "status": "not_found",
                "health": "unknown"
            }
    
    return results


def test_port_accessibility(test_config):
    """Test all required ports are accessible"""
    results = {}
    
    for service_name, config in test_config["services"].items():
        try:
            response = requests.get(
                config["url"] + config["health_endpoint"],
                timeout=config["timeout"]
            )
            results[service_name] = {
                "accessible": True,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except requests.exceptions.RequestException as e:
            results[service_name] = {
                "accessible": False,
                "error": str(e),
                "status_code": None,
                "response_time": None
            }
    
    return results


def test_service_health(test_config):
    """Test health check responses for all services"""
    results = {}
    
    for service_name, config in test_config["services"].items():
        try:
            response = requests.get(
                config["url"] + config["health_endpoint"],
                timeout=config["timeout"]
            )
            
            success = response.status_code == config["expected_status"]
            
            results[service_name] = {
                "healthy": success,
                "status_code": response.status_code,
                "expected_status": config["expected_status"],
                "response_time": response.elapsed.total_seconds()
            }
            
        except requests.exceptions.RequestException as e:
            results[service_name] = {
                "healthy": False,
                "error": str(e)
            }
    
    return results


def test_prometheus_targets():
    """Test Prometheus targets are properly configured and up"""
    try:
        response = requests.get("http://localhost:9090/api/v1/targets", timeout=10)
        
        data = response.json()
        targets = data.get("data", {}).get("activeTargets", [])
        
        up_targets = [t for t in targets if t.get("health") == "up"]
        down_targets = [t for t in targets if t.get("health") == "down"]
        
        results = {
            "total_targets": len(targets),
            "up_targets": len(up_targets),
            "down_targets": len(down_targets),
            "expected_up": 4,
            "target_details": []
        }
        
        for target in targets:
            results["target_details"].append({
                "job": target.get("labels", {}).get("job"),
                "instance": target.get("labels", {}).get("instance"),
                "health": target.get("health"),
                "last_error": target.get("lastError", "")
            })
        
        return results
        
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def test_network_connectivity(docker_client):
    """Test Docker network connectivity between containers"""
    try:
        network = docker_client.networks.get("soar-lab-testing_soar_net")
        containers = network.containers
        
        results = {
            "network_name": network.name,
            "connected_containers": len(containers),
            "container_details": []
        }
        
        for container in containers:
            results["container_details"].append({
                "name": container.name,
                "status": container.status
            })
        
        return results
        
    except docker.errors.NotFound:
        return {"error": "Network not found"}


def test_elasticsearch_indices():
    """Test Elasticsearch has required indices"""
    try:
        response = requests.get("http://localhost:19200/_cat/indices?v", timeout=10)
        
        indices_text = response.text
        required_indices = ["the_hive_17", "cortex"]
        
        results = {
            "total_indices": len([line for line in indices_text.split('\n') if line.strip() and not line.startswith('health')]),
            "required_indices_found": [],
            "missing_indices": []
        }
        
        for index in required_indices:
            if index in indices_text:
                results["required_indices_found"].append(index)
            else:
                results["missing_indices"].append(index)
        
        return results
        
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def test_redis_functionality(docker_client):
    """Test Redis basic functionality"""
    try:
        redis_container = docker_client.containers.get("soar_redis")
        
        # Test PING
        ping_result = redis_container.exec_run("redis-cli -a testredis123 ping")
        ping_success = ping_result.output.decode().strip() == "PONG"
        
        # Test INFO
        info_result = redis_container.exec_run("redis-cli -a testredis123 info server")
        info_success = "redis_version" in info_result.output.decode()
        
        results = {
            "ping_success": ping_success,
            "info_success": info_success,
            "ping_output": ping_result.output.decode().strip(),
            "redis_version": "unknown"
        }
        
        # Extract Redis version
        if info_success:
            info_lines = info_result.output.decode().split('\n')
            for line in info_lines:
                if line.startswith('redis_version:'):
                    results["redis_version"] = line.split(':')[1].strip()
                    break
        
        return results
        
    except docker.errors.NotFound:
        return {"error": "Redis container not found"}
    except Exception as e:
        return {"error": str(e)}


def generate_infrastructure_report(docker_containers, port_accessibility, 
                                 service_health, prometheus_targets, network_connectivity,
                                 elasticsearch_indices, redis_functionality):
    """Generate comprehensive infrastructure report"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "overall_status": "OPERATIONAL",
        "summary": {
            "total_containers": len(docker_containers),
            "running_containers": len([c for c in docker_containers.values() if c["running"]]),
            "accessible_services": len([s for s in port_accessibility.values() if s["accessible"]]),
            "healthy_services": len([s for s in service_health.values() if s["healthy"]]),
            "prometheus_up_targets": prometheus_targets.get("up_targets", 0),
            "elasticsearch_indices": len(elasticsearch_indices.get("required_indices_found", []))
        },
        "details": {
            "containers": docker_containers,
            "ports": port_accessibility,
            "health": service_health,
            "prometheus": prometheus_targets,
            "network": network_connectivity,
            "elasticsearch": elasticsearch_indices,
            "redis": redis_functionality
        }
    }
    
    # Calculate overall status
    if (report["summary"]["running_containers"] == report["summary"]["total_containers"] and
        report["summary"]["accessible_services"] == len(port_accessibility) and
        report["summary"]["healthy_services"] == len(service_health)):
        report["overall_status"] = "FULLY_OPERATIONAL"
    else:
        report["overall_status"] = "PARTIALLY_OPERATIONAL"
    
    return report
