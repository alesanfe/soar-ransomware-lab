#!/usr/bin/env python3
"""GRAF-D3: frictionless dashboard provisioning reload.

Grafana's file provisioner is version-gated: a dashboard JSON whose
``version`` field is <= the one stored in grafana.db is silently ignored.
Forgetting the bump is the classic cause of "I edited the file and
nothing changed".

This script makes the safe operation the only operation:

1. Stamps ``version = <unix epoch>`` into every provisioned dashboard
   JSON (monotonic → the gate can never skip the update).
2. Validates each file afterwards (validate_dashboards).
3. Recreates the grafana container so provisioning re-imports.

Usage:
    python scripts/maintenance/grafana_dashboards_deploy.py [--no-restart]

``--no-restart`` bumps versions only (useful inside CI before compose up).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGGING_DIR = REPO_ROOT / "infra" / "docker" / "compose" / "logging"
VALIDATOR = REPO_ROOT / "scripts" / "quality" / "validate_dashboards.py"
# Full file set + hardened overlay — must match Makefile.win/Makefile.linux
# COMPOSE_FILES or the recreated container silently loses hardening.
COMPOSE_FILES = [
    "-f", "infra/docker/compose/docker-compose.yml",
    "-f", "infra/docker/compose/docker-compose.core.yml",
    "-f", "infra/docker/compose/docker-compose.misp.yml",
    "-f", "infra/docker/compose/docker-compose.opensearch.yml",
    "-f", "infra/docker/compose/docker-compose.api.yml",
    "-f", "infra/docker/compose/logging/docker-compose.logging.yml",
    "-f", "infra/docker/compose/docker-compose.hardened.yml",
]
ENV_FILE = REPO_ROOT / ".env"


def bump_versions() -> list[str]:
    version = int(time.time())
    touched = []
    for path in sorted(LOGGING_DIR.glob("*-dashboard.json")):
        dash = json.loads(path.read_text(encoding="utf-8"))
        if dash.get("version") == version:
            continue
        dash["version"] = version
        path.write_text(
            json.dumps(dash, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        touched.append(f"{path.name} -> v{version}")
    return touched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    touched = bump_versions()
    for t in touched:
        print("bumped:", t)
    if not touched:
        print("all dashboards already at current epoch version")

    rc = subprocess.call([sys.executable, str(VALIDATOR)])
    if rc:
        print("validator failed — aborting before restart", file=sys.stderr)
        return rc

    if args.no_restart:
        return 0

    env_args = ["--env-file", str(ENV_FILE)] if ENV_FILE.exists() else []
    cmd = (
        ["docker", "compose", "-p", "soar", *COMPOSE_FILES, *env_args,
         "up", "-d", "--force-recreate", "grafana"]
    )
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


if __name__ == "__main__":
    sys.exit(main())
