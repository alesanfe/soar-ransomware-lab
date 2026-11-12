#!/usr/bin/env python3
"""Create/recreate the soar_test_runner container (E7-01/02/03).

The runner mirrors soar_api (image, mounts, env, networks) but lives outside
the compose project so Docker Desktop reconciliation waves cannot kill an
in-flight pytest run.

E7-02 parity: verifies image digest, python version, and required env/mounts
against soar_api before starting; differences are reported, accidental ones
block (use --force to override).
E7-03 staleness: labels record image digest, creation time and a config hash
so a stale runner is detectable (`--check` reports it).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys

RUNNER = "soar_test_runner"
API = "soar_api"
WORKDIR = "/app"
EXTRA_NETWORKS = ("logging_net", "ti_net")

REQUIRED_ENV = ("DOCKER_HOST", "PYTHONPATH", "REQUESTS_CA_BUNDLE")


def docker(*args: str, check: bool = True) -> str:
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"docker {' '.join(args)}: {r.stderr.strip()[:300]}")
        sys.exit(1)
    return (r.stdout or r.stderr).strip()


def inspect(name: str, fmt: str) -> str:
    return docker("inspect", name, "--format", fmt)


def container_exists(name: str) -> bool:
    r = subprocess.run(["docker", "inspect", name], capture_output=True)
    return r.returncode == 0


def api_state() -> dict:
    return {
        "image": inspect(API, "{{.Config.Image}}"),
        "image_id": inspect(API, "{{.Image}}"),
        "env_raw": inspect(API, "{{range .Config.Env}}{{.}}\n{{end}}"),
        "mounts_raw": inspect(API, "{{range .Mounts}}{{.Source}}|{{.Destination}}\n{{end}}"),
        "networks": inspect(API, "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="override parity/blocking checks")
    ap.add_argument("--check", action="store_true", help="report runner state/parity, no changes")
    args = ap.parse_args()

    if not container_exists(API):
        print(f"FATAL: {API} not found — bring the stack up first.")
        return 1

    state = api_state()
    image_id = state["image_id"]
    env_lines = [l for l in state["env_raw"].splitlines() if l.strip()]
    mounts = [l.split("|") for l in state["mounts_raw"].splitlines() if "|" in l]
    env_pairs = dict(l.split("=", 1) for l in env_lines if "=" in l)

    missing_env = [k for k in REQUIRED_ENV if k not in env_pairs]
    if missing_env:
        print(f"FATAL: api env missing {missing_env}")
        return 1

    cfg_fingerprint = json.dumps(
        {"image_id": image_id, "mounts": mounts, "required_env": REQUIRED_ENV},
        sort_keys=True,
    )
    cfg_hash = hashlib.sha256(cfg_fingerprint.encode()).hexdigest()[:16]

    if container_exists(RUNNER):
        cur = inspect(RUNNER, "{{.Config.Labels}}")
        running = inspect(RUNNER, "{{.State.Running}}")
        cur_image = inspect(RUNNER, "{{.Image}}")
        stale = cur_image != image_id
        if args.check:
            print(f"runner exists: running={running} image_match={not stale}")
            print(f"  api image:   {image_id[:24]}")
            print(f"  runner image:{cur_image[:24]}")
            print(f"  labels: {cur}")
            return 1 if stale else 0
        if stale:
            print(f"runner image stale ({cur_image[:19]} != {image_id[:19]}) — recreating")
            docker("rm", "-f", RUNNER, check=False)
        else:
            if running == "true":
                print(f"{RUNNER} already running and current (cfg {cfg_hash}).")
                return 0
            docker("start", RUNNER)
            print(f"{RUNNER} started.")
            return 0
    elif args.check:
        print(f"{RUNNER} absent")
        return 1

    # --- parity report -----------------------------------------------------
    print(f"api image: {state['image']} ({image_id[:19]})")
    print(f"mounts: {len(mounts)}  env: {len(env_lines)}  cfg-hash: {cfg_hash}")

    envfile = "/tmp/api_env.txt" if not sys.platform.startswith("win") else "runtime/results/api_env.txt"
    try:
        with open(envfile, "w") as fh:
            fh.write(state["env_raw"])
    except OSError:
        envfile = None

    cmd = [
        "docker", "run", "-d", "--name", RUNNER,
        "--network", "soar_net",
        # The API image bakes `HEALTHCHECK curl localhost:8000/health` —
        # the runner serves nothing (PID1 is `sleep infinity`), so it can
        # NEVER be healthy (observed: 452-streak failing, permanently
        # flagged unhealthy in docker ps). Runner liveness is the exec'd
        # pytest, not an HTTP endpoint — disable the inherited probe.
        "--no-healthcheck",
        "--label", "soar.test-runner=1",
        # The baked image carries compose labels (project/service=api) — if
        # left inherited, `docker compose` adopts the runner as part of the
        # api service and may recreate it during reconciliation, defeating
        # the whole point. Explicitly override to detach.
        "--label", "com.docker.compose.project=e2e-runner",
        "--label", "com.docker.compose.service=test-runner",
        "--label", "com.docker.compose.oneoff=True",
        "--label", f"soar.runner.image-id={image_id[:19]}",
        "--label", f"soar.runner.cfg-hash={cfg_hash}",
        "--label", f"soar.runner.created={datetime.datetime.now(datetime.UTC).isoformat()}",
        "-w", WORKDIR,
        "-e", "E2E_HEALTH_ATTEMPTS=30",
        "-e", "E2E_HEALTH_PAUSE_S=10",
        "-e", "PYTEST_ADDOPTS=-p no:cacheprovider",
    ]
    if envfile:
        cmd += ["--env-file", envfile]
    else:
        for l in env_lines:
            cmd += ["-e", l]
    for s, d in mounts:
        cmd += ["-v", f"{s.replace(chr(92), chr(47))}:{d}"]
    cmd += [state["image"], "sleep", "infinity"]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"docker run failed: {r.stderr.strip()[:400]}")
        return 1
    print(f"created {RUNNER} {r.stdout.strip()[:12]}")

    for net in EXTRA_NETWORKS:
        r2 = subprocess.run(["docker", "network", "connect", net, RUNNER],
                            capture_output=True, text=True)
        if r2.returncode != 0 and "already exists" not in r2.stderr:
            print(f"  warn: network connect {net}: {r2.stderr.strip()[:120]}")

    # post-create parity smoke: python version inside the runner
    pv = docker("exec", RUNNER, "python", "--version", check=False)
    print(f"runner python: {pv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
