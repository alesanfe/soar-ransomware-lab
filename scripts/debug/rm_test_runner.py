#!/usr/bin/env python3
"""Safe removal of soar_test_runner (E7-04).

- Refuses to remove while a pytest process runs inside (unless --force).
- Idempotent: absent runner is a no-op.
- Reports/artifacts live on bind mounts — removal never deletes results.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

RUNNER = "soar_test_runner"


def docker(*args: str, check: bool = False) -> tuple[int, str]:
    r = subprocess.run(["docker", *args], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="remove even if tests are running")
    args = ap.parse_args()

    rc, _ = docker("inspect", RUNNER)
    if rc != 0:
        print(f"{RUNNER}: absent — nothing to do")
        return 0

    rc, state = docker("inspect", RUNNER, "--format", "{{.State.Status}}")
    running = state == "running"

    if running:
        rc, procs = docker("exec", RUNNER, "sh", "-c",
                           "ls /proc/*/comm 2>/dev/null | xargs -n1 cat 2>/dev/null | grep -c pytest")
        pytest_running = False
        rc2, out2 = docker("exec", RUNNER, "sh", "-c",
                           "for p in /proc/[0-9]*/cmdline; do tr '\\0' ' ' < $p; done 2>/dev/null | grep -c 'pytest'")
        pytest_running = out2.strip() not in ("", "0")
        if pytest_running and not args.force:
            print(f"{RUNNER}: pytest in flight — refuse removal (use --force)")
            return 1

    docker("rm", "-f" if running else "", RUNNER) if running else docker("rm", RUNNER)
    print(f"{RUNNER}: removed (reports persist on bind mounts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
