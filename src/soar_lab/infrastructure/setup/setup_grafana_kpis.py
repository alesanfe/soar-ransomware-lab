#!/usr/bin/env python3
"""Setup Grafana datasource and dashboard for KPI visualization."""

import json
import os
import requests
from datetime import datetime

# Grafana configuration
GRAFANA_URL = os.getenv('GRAFANA_URL', 'http://localhost:8084')
GRAFANA_USERNAME = os.getenv('GRAFANA_USERNAME', 'admin')
GRAFANA_PASSWORD = os.getenv('GRAFANA_PASSWORD', 'GrafanaLab2024Secure')
API_URL = os.getenv('API_URL', 'http://localhost:8000')


def create_grafana_datasource():
    """Create a datasource for the SOAR API in Grafana."""
    url = f"{GRAFANA_URL}/api/datasources"
    auth = (GRAFANA_USERNAME, GRAFANA_PASSWORD)

    datasource_config = {
        "name": "SOAR API",
        "type": "prometheus",  # Using prometheus type for HTTP JSON API
        "url": API_URL,
        "access": "proxy",
        "isDefault": False,
        "jsonData": {
            "httpMethod": "GET",
            "timeInterval": "1m"
        }
    }

    # Check if datasource already exists
    list_url = f"{GRAFANA_URL}/api/datasources"
    response = requests.get(list_url, auth=auth, verify=False)
    if response.status_code == 200:
        datasources = response.json()
        for ds in datasources:
            if ds.get('name') == 'SOAR API':
                print(f"Datasource 'SOAR API' already exists with ID: {ds['id']}")
                return ds['id']

    # Create datasource
    response = requests.post(url, json=datasource_config, auth=auth, verify=False)
    if response.status_code == 200:
        result = response.json()
        print(f"Created datasource 'SOAR API' with ID: {result['id']}")
        return result['id']
    else:
        print(f"Failed to create datasource: {response.status_code} - {response.text}")
        return None


def create_grafana_dashboard():
    """Create a dashboard for KPI visualization in Grafana."""
    url = f"{GRAFANA_URL}/api/dashboards/db"
    auth = (GRAFANA_USERNAME, GRAFANA_PASSWORD)

    dashboard_config = {
        "dashboard": {
            "title": "SOAR KPI Dashboard",
            "tags": ["soar", "kpi", "ransomware"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "Total Alerts",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "total_alerts",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "MTTR (Mean Time To Respond)",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "mttr_seconds",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0}
                },
                {
                    "id": 3,
                    "title": "MTTR P90",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "p90",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0}
                },
                {
                    "id": 4,
                    "title": "Critical Rate",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "critical_rate",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0}
                },
                {
                    "id": 5,
                    "title": "Service Success Rates",
                    "type": "table",
                    "targets": [
                        {
                            "expr": "services",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4}
                },
                {
                    "id": 6,
                    "title": "KPIs by Alert Type",
                    "type": "table",
                    "targets": [
                        {
                            "expr": "by_alert_type",
                            "refId": "A"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4}
                }
            ],
            "refresh": "1m"
        },
        "overwrite": True
    }

    response = requests.post(url, json=dashboard_config, auth=auth, verify=False)
    if response.status_code == 200:
        result = response.json()
        print(f"Created dashboard 'SOAR KPI Dashboard' with UID: {result['uid']}")
        return result['uid']
    else:
        print(f"Failed to create dashboard: {response.status_code} - {response.text}")
        return None


def main():
    """Main function to setup Grafana KPI dashboard."""
    print("Setting up Grafana KPI dashboard...")
    print(f"Grafana URL: {GRAFANA_URL}")
    print(f"API URL: {API_URL}")

    # Create datasource
    datasource_id = create_grafana_datasource()
    if not datasource_id:
        print("Failed to create datasource. Exiting.")
        return

    # Create dashboard
    dashboard_uid = create_grafana_dashboard()
    if not dashboard_uid:
        print("Failed to create dashboard. Exiting.")
        return

    print(f"\nGrafana KPI dashboard setup complete!")
    print(f"Dashboard URL: {GRAFANA_URL}/d/{dashboard_uid}/soar-kpi-dashboard")


if __name__ == "__main__":
    main()
