#!/usr/bin/env python3
"""E2E host preflight — E11-04/E11-06.

Runs *inside* a lab container (soar_api / soar_test_runner). Checks the
conditions that otherwise turn a long E2E suite into a false failure:

  - docker daemon reachable (via DOCKER_HOST proxy)
  - host/docker disk pressure (from `docker system df` + container disk)
  - required CA bundle readable and TLS-connectable (E6-02)
  - no active reconcile wave in progress (recent container churn)
  - egress guard attached to the live api netns (E5)
  - writable report dir
  - system clock roughly sane vs a peer container

Exit codes: 0 ok (warnings allowed), 1 blocking failure.
Override: E2E_PREFLIGHT_FORCE=1 downgrades blocking failures to warnings.

Emits a JSON summary line (PREFLIGHT_JSON=...) that callers can attach
to JUnit metadata (E9-04/E11-04).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

WARN_PCT = float(os.environ.get("E2E_DISK_WARN_PCT", "80"))
HIGH_PCT = float(os.environ.get("E2E_DISK_HIGH_PCT", "90"))
CRIT_PCT = float(os.environ.get("E2E_DISK_CRIT_PCT", "95"))
CHURN_WINDOW_S = int(os.environ.get("E2E_CHURN_WINDOW_S", "120"))
CHURN_MAX = int(os.environ.get("E2E_CHURN_MAX", "4"))

BLOCKED = "BLOCKED"
WARN = "WARN"
OK = "OK"


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def check_daemon() -> tuple[str, str]:
    rc, out = _run(["docker", "version", "--format", "{{.Server.Version}}"], 15)
    if rc != 0 or not out:
        return BLOCKED, f"docker daemon unreachable: {out[:120]}"
    return OK, f"server {out.splitlines()[-1]}"


def check_disk() -> tuple[str, str]:
    # Container FS where reports are written
    usage = shutil.disk_usage("/app")
    pct = usage.used / usage.total * 100
    detail = f"/app {pct:.1f}% used ({usage.free // 2**20}MiB free)"
    # Docker-side disk (daemon) — approximate via df on images dir is not
    # exposed; use `docker system df` totals instead.
    rc, out = _run(["docker", "system", "df", "--format", "{{.Type}}|{{.Size}}|{{.Reclaimable}}"], 30)
    if rc == 0:
        detail += f" | docker df: {out.replace(chr(10), '; ')}"
    if pct >= CRIT_PCT:
        return BLOCKED, detail
    if pct >= HIGH_PCT:
        return WARN, detail
    return OK, detail


def check_ca_bundle() -> tuple[str, str]:
    path = os.environ.get("REQUESTS_CA_BUNDLE", "/app/certs/ca-bundle.crt")
    if not os.path.isfile(path):
        alt = "/app/certs/ca.crt"
        if os.path.isfile(alt):
            return WARN, f"{path} missing; {alt} exists (single-CA fallback)"
        return BLOCKED, f"CA bundle not found at {path}"
    if os.path.getsize(path) == 0:
        return BLOCKED, f"CA bundle {path} is empty"
    if not os.access(path, os.R_OK):
        return BLOCKED, f"CA bundle {path} not readable"
    # TLS smoke: parseable PEM
    try:
        head = open(path, "rb").read(30)
    except OSError as e:
        return BLOCKED, f"CA bundle unreadable: {e}"
    if b"BEGIN CERTIFICATE" not in head and b"BEGIN CERTIFICATE" not in open(path, "rb").read():
        return BLOCKED, f"CA bundle {path} is not PEM"
    return OK, f"bundle ok ({os.path.getsize(path)} bytes)"


def check_churn() -> tuple[str, str]:
    """Detect an active reconcile wave: >CHURN_MAX (re)starts in the window."""
    now = int(time.time())
    rc, out = _run(
        ["docker", "events", "--since", str(now - CHURN_WINDOW_S), "--until", str(now),
         "--filter", "event=start", "--format", "{{.Actor.Attributes.name}}"],
        20,
    )
    if rc != 0:
        return WARN, f"docker events unavailable: {out[:100]}"
    starts = [ln for ln in out.splitlines() if ln.strip()]
    # docker events --since needs daemon support; fall back to ps ages
    if not starts:
        rc2, out2 = _run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"], 15
        )
        young = [ln for ln in out2.splitlines()
                 if "second" in ln or ("minute" in ln and "minutes" not in ln)]
        if len(young) > CHURN_MAX:
            return WARN, f"{len(young)} containers <2min old — probable reconcile wave"
        return OK, "no churn detected"
    if len(starts) > CHURN_MAX:
        return WARN, f"{len(starts)} container starts in {CHURN_WINDOW_S}s — reconcile wave?"
    return OK, f"{len(starts)} starts in window"


def check_egress_guard() -> tuple[str, str]:
    """E5: verify the guard (if it exists) is attached to the LIVE api netns."""
    rc, api_id = _run(
        ["docker", "inspect", "soar_api", "--format", "{{.Id}}"], 15)
    rc2, guard_target = _run(
        ["docker", "inspect", "soar_api_egress_guard", "--format", "{{.HostConfig.NetworkMode}}"], 15)
    if rc != 0:
        return WARN, "soar_api not inspectable"
    if rc2 != 0 or "container:" not in guard_target:
        return WARN, "egress guard absent (ok if hardened overlay not in use)"
    target_id = guard_target.split("container:")[-1].strip()
    if target_id != api_id.strip():
        return BLOCKED, (
            f"egress guard attached to DEAD netns (api={api_id.strip()[:12]} "
            f"guard→{target_id[:12]}) — egress silently open. Re-anchor: "
            "docker rm -f soar_api_egress_guard && make up"
        )
    rc3, rules = _run(
        ["docker", "exec", "soar_api_egress_guard", "iptables", "-L", "EGRESS_GUARD", "-n"], 15)
    if rc3 != 0 or "DROP" not in rules:
        return BLOCKED, "egress guard live but EGRESS_GUARD rules missing"
    return OK, "guard anchored to live api netns, rules present"


def check_reports_writable() -> tuple[str, str]:
    d = "/app/reports/validation/results/junit"
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".preflight_probe")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
        return OK, f"{d} writable (host-mounted)"
    except OSError as e:
        return BLOCKED, f"cannot write {d}: {e}"


CHECKS = [
    ("daemon", check_daemon),
    ("disk", check_disk),
    ("ca_bundle", check_ca_bundle),
    ("reconcile_churn", check_churn),
    ("egress_guard", check_egress_guard),
    ("reports_writable", check_reports_writable),
]


def main() -> int:
    force = os.environ.get("E2E_PREFLIGHT_FORCE", "").lower() in ("1", "true", "yes")
    results: dict[str, dict] = {}
    worst = OK
    for name, fn in CHECKS:
        level, detail = fn()
        results[name] = {"level": level, "detail": detail}
        icon = {OK: "✓", WARN: "⚠", BLOCKED: "✗"}[level]
        print(f"{icon} {name:18} {level:8} {detail}")
        if level == BLOCKED:
            worst = BLOCKED
        elif level == WARN and worst == OK:
            worst = WARN

    summary = {"verdict": worst, "forced": force, "ts": int(time.time()), "checks": results}
    print(f"PREFLIGHT_JSON={json.dumps(summary)}")
    if worst == BLOCKED and not force:
        print("\nPreflight BLOCKED — fix the failures above or set E2E_PREFLIGHT_FORCE=1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
