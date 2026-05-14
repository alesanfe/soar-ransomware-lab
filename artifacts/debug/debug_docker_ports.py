#!/usr/bin/env python3
"""
Debug script to check Docker Compose port configurations
"""

import yaml
from pathlib import Path

def main():
    compose_path = Path("infra/docker/docker-compose.yml")
    with open(compose_path, 'r', encoding='utf-8') as f:
        compose_content = yaml.safe_load(f)
    
    services = compose_content.get("services", {})
    
    print("=== Docker Compose Port Configuration ===")
    
    # Check Elasticsearch specifically
    if "elasticsearch" in services:
        es = services["elasticsearch"]
        print(f"\nElasticsearch service:")
        print(f"  Ports: {es.get('ports', [])}")
        
        for port_mapping in es.get("ports", []):
            print(f"    Port mapping: {port_mapping}")
            if isinstance(port_mapping, str):
                if ":" in port_mapping:
                    parts = port_mapping.split(":")
                    print(f"      Host port: {parts[0]}")
                    print(f"      Container port: {parts[1]}")
                else:
                    print(f"      Single port: {port_mapping}")
    
    # Check all services
    print(f"\n=== All Services Port Mappings ===")
    for service_name, service_config in services.items():
        if "ports" in service_config:
            ports = service_config["ports"]
            print(f"\n{service_name}:")
            for port_mapping in ports:
                print(f"  {port_mapping}")

if __name__ == "__main__":
    main()
