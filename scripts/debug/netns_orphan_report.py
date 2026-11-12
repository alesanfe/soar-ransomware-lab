#!/usr/bin/env python3
"""E5-04 — diagnose orphaned netns-attached sidecars.

Read-only report: for every container sharing another's netns
(``network_mode: container:<id>``), verify the target is alive and the
attachment is still meaningful. Flags the post-recreate orphan state where
a guard holds a dead container ID.
"""

from __future__ import annotations

import json
import subprocess
import sys


def docker(*args: str) -> str:
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    rc = subprocess.run(["docker", "info"], capture_output=True).returncode
    if rc != 0:
        print("docker daemon unreachable")
        return 1

    names = docker("ps", "-a", "--format", "{{.Names}}").splitlines()
    containers: dict[str, dict] = {}
    by_id: dict[str, str] = {}
    for n in names:
        n = n.strip()
        if not n:
            continue
        cid = docker("inspect", n, "--format", "{{.Id}}")
        net_mode = docker("inspect", n, "--format", "{{.HostConfig.NetworkMode}}")
        running = docker("inspect", n, "--format", "{{.State.Running}}")
        containers[n] = {"id": cid, "net_mode": net_mode, "running": running}
        by_id[cid] = n

    orphans: list[dict] = []
    attached: list[dict] = []
    for name, c in containers.items():
        mode = c["net_mode"]
        if not mode.startswith("container:"):
            continue
        target_id = mode.removeprefix("container:")
        target_name = by_id.get(target_id)
        entry = {
            "sidecar": name,
            "target_id": target_id[:12],
            "target_name": target_name or "DEAD",
            "sidecar_running": c["running"],
        }
        if target_name is None:
            orphans.append(entry)
        else:
            entry["target_running"] = containers[target_name]["running"]
            attached.append(entry)

    report = {
        "attached_netns_sidecars": attached,
        "orphaned_sidecars": orphans,
        "verdict": "ORPHANS" if orphans else "OK",
    }
    print(json.dumps(report, indent=2))
    if orphans:
        print("\nRECOVERY: for each orphan — docker rm -f <sidecar>, then recreate")
        print("against the live target (e.g. `make up` for compose-managed guards).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
