#!/usr/bin/env python3
"""
Infrastructure Test Automation Script
Runs comprehensive tests and generates reports
"""

import pytest
import json
import time
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from infrastructure_test_functions import (
    test_docker_containers, test_port_accessibility, test_service_health,
    test_prometheus_targets, test_network_connectivity, test_elasticsearch_indices,
    test_redis_functionality, generate_infrastructure_report
)


def run_infrastructure_tests():
    """Run all infrastructure tests and generate report"""
    print("Starting SOAR Infrastructure Automation Tests")
    print("=" * 60)
    
    # Import required modules
    import docker
    import requests
    
    # Initialize test configuration
    test_config = {
        "services": {
            "grafana": {
                "url": "http://localhost:3000",
                "health_endpoint": "/api/health",
                "expected_status": 200,
                "timeout": 5
            },
            "prometheus": {
                "url": "http://localhost:9090",
                "health_endpoint": "/-/healthy",
                "expected_status": 200,
                "timeout": 5
            },
            "thehive": {
                "url": "http://localhost:9000",
                "health_endpoint": "/api/health",
                "expected_status": 200,
                "timeout": 10
            },
            "cortex": {
                "url": "http://localhost:9001",
                "health_endpoint": "/",
                "expected_status": 200,
                "timeout": 5
            },
            "elasticsearch": {
                "url": "http://localhost:19200",
                "health_endpoint": "/_cluster/health",
                "expected_status": 200,
                "timeout": 5
            },
            "redis_exporter": {
                "url": "http://localhost:9121",
                "health_endpoint": "/metrics",
                "expected_status": 200,
                "timeout": 5
            },
            "elasticsearch_exporter": {
                "url": "http://localhost:9114",
                "health_endpoint": "/metrics",
                "expected_status": 200,
                "timeout": 5
            }
        }
    }
    
    # Initialize Docker client
    docker_client = docker.from_env()
    
    # Run tests manually to collect results
    results = {}
    
    try:
        print("Testing Docker Containers...")
        results['docker_containers'] = test_docker_containers(docker_client)
        print(f"[OK] {len([c for c in results['docker_containers'].values() if c['running']])} containers running")
        
        print("Testing Port Accessibility...")
        results['port_accessibility'] = test_port_accessibility(test_config)
        print(f"[OK] {len([s for s in results['port_accessibility'].values() if s['accessible']])} services accessible")
        
        print("Testing Service Health...")
        results['service_health'] = test_service_health(test_config)
        print(f"[OK] {len([s for s in results['service_health'].values() if s['healthy']])} services healthy")
        
        print("Testing Prometheus Targets...")
        results['prometheus_targets'] = test_prometheus_targets()
        print(f"[OK] {results['prometheus_targets']['up_targets']}/{results['prometheus_targets']['total_targets']} targets up")
        
        print("Testing Network Connectivity...")
        results['network_connectivity'] = test_network_connectivity(docker_client)
        print(f"[OK] {results['network_connectivity']['connected_containers']} containers in network")
        
        print("Testing Elasticsearch Indices...")
        results['elasticsearch_indices'] = test_elasticsearch_indices()
        print(f"[OK] {len(results['elasticsearch_indices']['required_indices_found'])} required indices found")
        
        print("Testing Redis Functionality...")
        results['redis_functionality'] = test_redis_functionality(docker_client)
        print(f"[OK] Redis v{results['redis_functionality']['redis_version']} functional")
        
        # Generate comprehensive report
        print("Generating Infrastructure Report...")
        report = generate_infrastructure_report(
            results['docker_containers'],
            results['port_accessibility'],
            results['service_health'],
            results['prometheus_targets'],
            results['network_connectivity'],
            results['elasticsearch_indices'],
            results['redis_functionality']
        )
        
        # Save report to file
        report_file = f"artifacts/infrastructure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "=" * 60)
        print("INFRASTRUCTURE TEST RESULTS")
        print("=" * 60)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Containers: {report['summary']['running_containers']}/{report['summary']['total_containers']} running")
        print(f"Services: {report['summary']['accessible_services']}/{len(results['port_accessibility'])} accessible")
        print(f"Health: {report['summary']['healthy_services']}/{len(results['service_health'])} healthy")
        print(f"Prometheus: {report['summary']['prometheus_up_targets']} targets up")
        print(f"Elasticsearch: {report['summary']['elasticsearch_indices']} indices")
        print(f"Report saved: {report_file}")
        
        return report
        
    except Exception as e:
        print(f"[FAILED] Test failed: {e}")
        return {"status": "failed", "error": str(e)}


def print_service_status():
    """Print current service status"""
    print("Current Service Status:")
    print("-" * 40)
    
    services = [
        ("Grafana", "http://localhost:3000/api/health"),
        ("Prometheus", "http://localhost:9090/-/healthy"),
        ("TheHive", "http://localhost:9000/api/health"),
        ("Cortex", "http://localhost:9001/"),
        ("Elasticsearch", "http://localhost:19200/_cluster/health"),
        ("Redis Exporter", "http://localhost:9121/metrics"),
        ("Elasticsearch Exporter", "http://localhost:9114/metrics")
    ]
    
    for name, url in services:
        try:
            import requests
            response = requests.get(url, timeout=5)
            status = "[UP]" if response.status_code == 200 else f"[{response.status_code}]"
        except:
            status = "[DOWN]"
        print(f"{name:20} {status}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print_service_status()
    else:
        run_infrastructure_tests()
