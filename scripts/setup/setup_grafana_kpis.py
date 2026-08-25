#!/usr/bin/env python3
"""Setup Grafana datasource and dashboard for KPI visualization."""

import json
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Load environment variables from .env.full
for _env_path in [".env.full", "/app/.env.full"]:
    _p = Path(_env_path)
    if _p.exists():
        with open(_p) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
        break

# Grafana configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:8084")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", os.getenv("GRAFANA_PASSWORD", ""))
API_URL = os.getenv("API_URL", "http://localhost:8000")


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
        "jsonData": {"httpMethod": "GET", "timeInterval": "1m"},
    }

    # Check if datasource already exists
    list_url = f"{GRAFANA_URL}/api/datasources"
    try:
        response = requests.get(list_url, auth=auth, verify=False, timeout=10)  # nosec B501
    except Exception as e:
        logger.error(f"Could not list Grafana datasources: {e}")
        return None
    if response.status_code == 200:
        datasources = response.json()
        for ds in datasources:
            if ds.get("name") == "SOAR API":
                logger.info(f"Datasource 'SOAR API' already exists with ID: {ds['id']}")
                return ds["id"]

    # Create datasource
    try:
        response = requests.post(url, json=datasource_config, auth=auth, verify=False, timeout=10)  # nosec B501
    except Exception as e:
        logger.error(f"Could not create Grafana datasource: {e}")
        return None
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Created datasource 'SOAR API' with ID: {result['id']}")
        return result["id"]
    else:
        logger.error(f"Failed to create datasource: {response.status_code} - {response.text}")
        return None


def create_grafana_dashboard():
    """Create a dashboard for KPI visualization in Grafana.

    Loads the dashboard definition from the provisioning JSON file
    (infra/docker/compose/logging/kpi-dashboard.json) which contains
    15 panels aligned with the TFM figures. Falls back to a minimal
    6-panel dashboard if the file is not found.
    """
    url = f"{GRAFANA_URL}/api/dashboards/db"
    auth = (GRAFANA_USERNAME, GRAFANA_PASSWORD)

    # Try to load the full 15-panel dashboard from the provisioning JSON
    dashboard_json = None
    for candidate in [
        Path("/app/infra/docker/compose/logging/kpi-dashboard.json"),
        Path(__file__).parent.parent.parent / "infra" / "docker" / "compose" / "logging" / "kpi-dashboard.json",
    ]:
        if candidate.exists():
            try:
                dashboard_json = json.loads(candidate.read_text(encoding="utf-8"))
                logger.info(f"Loaded dashboard JSON from {candidate} ({len(dashboard_json.get('panels', []))} panels)")
                break
            except Exception as e:
                logger.warning(f"Could not parse {candidate}: {e}")

    if dashboard_json:
        dashboard_config = {
            "dashboard": dashboard_json,
            "overwrite": True,
        }
    else:
        logger.warning("Falling back to minimal 6-panel dashboard")
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
                        "targets": [{"expr": "total_alerts", "refId": "A"}],
                        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    },
                    {
                        "id": 2,
                        "title": "MTTR (Mean Time To Respond)",
                        "type": "stat",
                        "targets": [{"expr": "mttr_seconds", "refId": "A"}],
                        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                    },
                    {
                        "id": 3,
                        "title": "MTTR P90",
                        "type": "stat",
                        "targets": [{"expr": "p90", "refId": "A"}],
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                    },
                    {
                        "id": 4,
                        "title": "Critical Rate",
                        "type": "stat",
                        "targets": [{"expr": "critical_rate", "refId": "A"}],
                        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                    },
                    {
                        "id": 5,
                        "title": "Service Success Rates",
                        "type": "table",
                        "targets": [{"expr": "services", "refId": "A"}],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                    },
                    {
                        "id": 6,
                        "title": "KPIs by Alert Type",
                        "type": "table",
                        "targets": [{"expr": "by_alert_type", "refId": "A"}],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                    },
                ],
                "refresh": "1m",
            },
            "overwrite": True,
        }

    # Check if dashboard already exists (provisioned via file)
    try:
        check_url = f"{GRAFANA_URL}/api/dashboards/uid/soar-kpi-main"
        check_resp = requests.get(check_url, auth=auth, verify=False, timeout=10)  # nosec B501
        if check_resp.status_code == 200:
            existing = check_resp.json()
            uid = existing.get("dashboard", {}).get("uid", "")
            logger.info(f"Dashboard already exists (provisioned) with UID: {uid}")
            return uid
    except Exception:
        pass

    try:
        response = requests.post(url, json=dashboard_config, auth=auth, verify=False, timeout=10)  # nosec B501
    except Exception as e:
        logger.error(f"Could not create Grafana dashboard: {e}")
        return None
    if response.status_code == 200:
        result = response.json()
        logger.info(f"Created dashboard 'SOAR KPI Dashboard' with UID: {result['uid']}")
        return result["uid"]
    else:
        logger.error(f"Failed to create dashboard: {response.status_code} - {response.text}")
        return None


def main():
    """Main function to setup Grafana KPI dashboard."""
    logger.info("Setting up Grafana KPI dashboard...")
    logger.info(f"Grafana URL: {GRAFANA_URL}")
    logger.info(f"API URL: {API_URL}")

    # Create datasource
    for attempt in range(3):
        datasource_id = create_grafana_datasource()
        if datasource_id:
            break
        logger.warning(f"Datasource setup failed (attempt {attempt + 1}/3), retrying in 5s...")
        import time

        time.sleep(5)

    if not datasource_id:
        logger.error("Failed to create datasource. Continuing without dashboard.")
        return

    # Create dashboard
    dashboard_uid = create_grafana_dashboard()
    if not dashboard_uid:
        logger.error("Failed to create dashboard. Continuing.")
        return

    print("\nGrafana KPI dashboard setup complete!")
    print(f"Dashboard URL: {GRAFANA_URL}/d/{dashboard_uid}/soar-kpi-dashboard")


if __name__ == "__main__":
    main()
