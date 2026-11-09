#!/usr/bin/env python3
"""Fail-closed validation of the effective Docker Compose configuration (DK-P0-004, DK-P0-056).

Renders a profile with ``docker compose config --format json`` (or accepts a
pre-rendered file) and checks CIS/NIST-SP-800-190 invariants per service.
A critical deviation exits non-zero so CI and ``make up`` stop before an
insecure topology starts — the failure names service, field, observed value
and expected value.

Profiles:
    lab        base compose files (relaxed; sockets/EOL allowed by design)
    hardened   base + docker-compose.hardened.yml (the secure default)

Exceptions live in ``infra/docker/compose/security-exceptions.json``::
    {"service": {"check-id": {"reason": "...", "expires": "YYYY-MM-DD"}}}
An expired exception stops being an exception — it becomes a violation.

Usage:
    python scripts/setup/validate_compose_security.py --profile hardened
    python scripts/setup/validate_compose_security.py --rendered config.json
    python scripts/setup/validate_compose_security.py --runtime            # docker inspect on the running stack
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE_DIR = ROOT / "infra" / "docker" / "compose"
EXCEPTIONS_FILE = COMPOSE_DIR / "security-exceptions.json"

BASE_FILES = [
    "docker-compose.yml",
    "docker-compose.core.yml",
    "docker-compose.misp.yml",
    "docker-compose.api.yml",
    "docker-compose.opensearch.yml",
    "logging/docker-compose.logging.yml",
]
HARDENED_OVERLAY = "docker-compose.hardened.yml"

COMPOSE_MIN_VERSION = (2, 24)  # !reset / !override require >= 2.24 (BUG-053)

SEVERITY = {"CRITICAL": 2, "WARNING": 1, "INFO": 0}


class Check:
    def __init__(self, check_id, severity, desc, services=None):
        self.id = check_id
        self.severity = severity
        self.desc = desc
        self.services = services  # None = every service


def _secopt(svc, name):
    for opt in svc.get("security_opt") or []:
        if str(opt).startswith(name):
            return True
    return False


def _cap_drop_all(svc):
    drops = svc.get("cap_drop") or []
    return "ALL" in [str(c).upper() for c in drops]


def _mounts_socket(svc):
    for m in svc.get("volumes") or []:
        src = str(m.get("source", "")) if isinstance(m, dict) else str(m)
        if "docker.sock" in src:
            return m.get("read_only", False) if isinstance(m, dict) else (":ro" in str(m))
    return None


def _env_value(svc, key):
    env = svc.get("environment") or {}
    if isinstance(env, dict):
        return env.get(key)
    for item in env:
        if str(item).startswith(key + "="):
            return str(item).split("=", 1)[1]
    return None


# ---------------------------------------------------------------- checks ---

CHECKS = [
    Check("no-privileged", "CRITICAL", "privileged:true forbidden"),
    Check("no-unconfined-seccomp", "CRITICAL", "seccomp:unconfined forbidden"),
    Check("no-direct-docker-socket", "CRITICAL", "no /var/run/docker.sock mount"),
    Check("non-root-user", "CRITICAL", "container must not run as UID 0"),
    Check("cap-drop-all", "WARNING", "cap_drop should include ALL"),
    Check("no-new-privileges", "WARNING", "security_opt no-new-privileges:true"),
    Check("pids-limit", "WARNING", "pids_limit must be set"),
    Check("healthcheck", "WARNING", "healthcheck defined"),
    Check("restart-policy", "INFO", "restart policy defined"),
    Check("log-rotation", "WARNING", "json-file max-size rotation configured"),
    Check("auth-enabled", "CRITICAL", "API_REQUIRE_AUTH must not be false", services={"api"}),
]

PROFILE_RULES = {
    # check-id -> set of services the check applies to in this profile
    "lab": {
        "no-direct-docker-socket": set(),
        "non-root-user": set(),
        "cap-drop-all": set(),
        "no-new-privileges": set(),
        "pids-limit": set(),
        "no-unconfined-seccomp": set(),
    },
    "hardened": {
        # sockets: apply to EVERY service — the residual raw-socket consumers
        # (cortex / shuffle-backend / orborus worker spawning, promtail ro
        # log discovery, the proxy itself) are recorded in
        # security-exceptions.json with reason + expiry, never silently
        # out of scope.
        "no-direct-docker-socket": "*",
        "non-root-user": {"api", "redis"},
        "cap-drop-all": {"api", "network-watcher", "docs-site", "nginx", "web-management"},
        "no-new-privileges": {"api", "network-watcher", "thehive", "cortex", "docker-socket-proxy"},
        "pids-limit": {"api", "redis", "docs-site", "nginx", "web-management"},
        "no-unconfined-seccomp": {"orborus"},
        "auth-enabled": {"api"},
    },
}


def load_exceptions():
    if not EXCEPTIONS_FILE.exists():
        return {}
    return json.loads(EXCEPTIONS_FILE.read_text(encoding="utf-8"))


def is_excepted(exc, svc, check_id):
    entry = (exc.get(svc) or {}).get(check_id) or (exc.get("*") or {}).get(check_id)
    if not entry:
        return False, None
    exp = entry.get("expires")
    if exp:
        try:
            if dt.date.fromisoformat(exp) < dt.datetime.now(dt.UTC).date():
                return False, f"exception EXPIRED {exp}"
        except ValueError:
            return False, f"exception has invalid expires={exp!r}"
    return True, entry.get("reason", "no reason given")


def evaluate_service(name, svc, profile, exc):
    findings = []
    rules = PROFILE_RULES[profile]
    for chk in CHECKS:
        scope = rules.get(chk.id)
        if scope is not None and scope != "*" and name not in scope:
            continue

        ok, observed = True, None
        if chk.id == "no-privileged":
            ok = not svc.get("privileged")
            observed = svc.get("privileged")
        elif chk.id == "no-unconfined-seccomp":
            bad = _secopt(svc, "seccomp:unconfined") or _secopt(svc, "seccomp=unconfined")
            ok, observed = not bad, svc.get("security_opt")
        elif chk.id == "no-direct-docker-socket":
            ro = _mounts_socket(svc)
            ok, observed = ro is None, ro
        elif chk.id == "non-root-user":
            user = str(svc.get("user") or "0")
            ok = user not in ("0", "root", "")
            observed = user
        elif chk.id == "cap-drop-all":
            ok, observed = _cap_drop_all(svc), svc.get("cap_drop")
        elif chk.id == "no-new-privileges":
            ok = _secopt(svc, "no-new-privileges:true")
            observed = svc.get("security_opt")
        elif chk.id == "pids-limit":
            lim = svc.get("pids_limit") or (
                ((svc.get("deploy") or {}).get("resources") or {}).get("limits") or {}
            ).get("pids")
            ok, observed = bool(lim), lim
        elif chk.id == "healthcheck":
            hc = svc.get("healthcheck") or {}
            ok = bool(hc.get("test"))
            observed = hc.get("test")
        elif chk.id == "restart-policy":
            ok, observed = bool(svc.get("restart")), svc.get("restart")
        elif chk.id == "auth-enabled":
            v = str(_env_value(svc, "API_REQUIRE_AUTH") or "true").lower()
            ok, observed = v != "false", v
        elif chk.id == "log-rotation":
            log = (svc.get("logging") or {}).get("options") or {}
            ok = "max-size" in log or (svc.get("logging") or {}).get("driver") not in (
                None,
                "json-file",
            )
            observed = svc.get("logging")

        if not ok:
            excepted, note = is_excepted(exc, name, chk.id)
            findings.append(
                {
                    "service": name,
                    "check": chk.id,
                    "severity": chk.severity,
                    "observed": observed,
                    "expected": chk.desc,
                    "excepted": excepted,
                    "note": note,
                }
            )
    return findings


def render_config(profile, env_file):
    files = list(BASE_FILES)
    if profile == "hardened":
        files.append(HARDENED_OVERLAY)
    cmd = ["docker", "compose", "-p", "soar"]
    cmd += [arg for f in files for arg in ("-f", str(COMPOSE_DIR / f))]
    if env_file and Path(env_file).exists():
        cmd += ["--env-file", env_file]
    cmd += ["config", "--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc.returncode != 0:
        sys.exit(f"FATAL: docker compose config failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def check_compose_version():
    proc = subprocess.run(
        ["docker", "compose", "version", "--short"], capture_output=True, text=True, timeout=15
    )
    ver = proc.stdout.strip().lstrip("v")
    try:
        parts = tuple(int(p) for p in ver.split(".")[:2])
    except ValueError:
        return False, ver
    return parts >= COMPOSE_MIN_VERSION, ver


def runtime_findings(exc):
    proc = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=soar_"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    ids = proc.stdout.split()
    if not ids:
        return [
            {
                "service": "*",
                "check": "runtime",
                "severity": "INFO",
                "observed": "no containers",
                "expected": "running stack",
                "excepted": False,
                "note": None,
            }
        ]
    proc = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, timeout=60)
    findings = []
    for cont in json.loads(proc.stdout):
        name = cont["Name"].lstrip("/").replace("soar_", "")
        cfg, hc = cont.get("Config") or {}, cont.get("HostConfig") or {}
        pseudo = {
            "privileged": hc.get("Privileged"),
            "security_opt": hc.get("SecurityOpt"),
            "cap_drop": hc.get("CapDrop"),
            "user": cfg.get("User"),
            "pids_limit": hc.get("PidsLimit"),
            "restart": (hc.get("RestartPolicy") or {}).get("Name"),
            "healthcheck": cfg.get("Healthcheck"),
            "logging": {
                "driver": (hc.get("LogConfig") or {}).get("Type"),
                "options": (hc.get("LogConfig") or {}).get("Config"),
            },
            "volumes": [
                {"source": m.get("Source"), "read_only": not m.get("RW", True)}
                for m in cont.get("Mounts") or []
            ],
        }
        findings += evaluate_service(name, pseudo, "hardened", exc)
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", choices=["lab", "hardened"], default="hardened")
    ap.add_argument("--rendered", help="pre-rendered compose config JSON")
    ap.add_argument("--env-file", default=str(ROOT / ".env"))
    ap.add_argument("--runtime", action="store_true", help="inspect running containers")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    ok_ver, ver = check_compose_version()
    if not ok_ver:
        sys.exit(
            f"FATAL: docker compose {ver} < {'.'.join(map(str, COMPOSE_MIN_VERSION))} "
            f"(!reset/!override unsupported — BUG-053)"
        )

    exc = load_exceptions()
    if args.runtime:
        findings = runtime_findings(exc)
    else:
        config = (
            json.loads(Path(args.rendered).read_text())
            if args.rendered
            else render_config(args.profile, args.env_file)
        )
        findings = []
        for name, svc in (config.get("services") or {}).items():
            findings += evaluate_service(name, svc, args.profile, exc)

    if args.as_json:
        print(json.dumps(findings, indent=2, default=str))
        return 0

    violations = [f for f in findings if not f["excepted"]]
    for f in findings:
        tag = "EXCEPTED" if f["excepted"] else f["severity"]
        print(
            f"[{tag:8}] {f['service']:25} {f['check']:22} "
            f"observed={str(f['observed'])[:60]} expected={f['expected']}"
            + (f"  ({f['note']})" if f["note"] else "")
        )

    n_crit = sum(1 for f in violations if f["severity"] == "CRITICAL")
    n_warn = sum(1 for f in violations if f["severity"] == "WARNING")
    n_exc = len(findings) - len(violations)
    print(
        f"\nSummary: {n_crit} critical, {n_warn} warning, {n_exc} excepted "
        f"(profile={args.profile}, compose={ver})"
    )
    return 1 if n_crit else 0


if __name__ == "__main__":
    sys.exit(main())
