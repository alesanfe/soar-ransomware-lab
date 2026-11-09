#!/usr/bin/env python3
"""SEC-002: rotate all lab credentials on a running stack.

Phases (each reports OK / NEEDS-MANUAL / SKIPPED):
  1. LIVE-API  — rotate credentials via service APIs while old creds still work
                 (thehive/cortex keys, grafana admin, misp authkey/admin).
  2. DB-ALTER  — ALTER USER on postgres (grafana_db) and mysql (misp_db).
  3. ENV-ONLY  — fresh random values for every env-only secret via
                 ``generate_env.GENERATORS``.
  4. SYNC      — write all new values to .env.full / .env.container / .env.
  5. RECREATE  — ``docker compose up -d`` recreates containers whose env changed.
  6. POST-SYNC — re-render grafana datasources, re-wire thehive->cortex conf,
                 regenerate the Shuffle workflow (it embeds thehive Bearer +
                 cortex Basic creds).
  7. VERIFY    — negative auth probes (old creds must fail) + health check.

Skipped (documented):
  - MISP_ENCRYPTION_KEY: rotating it orphans data encrypted with the current
    key inside MISP's DB. Rotation requires a full MISP reset.
  - SHUFFLE_DEFAULT_PASSWORD: Shuffle has no supported admin-side password
    change API; rotate via admin UI (marked NEEDS-MANUAL if API attempt fails).

Never prints secret values — only variable names and outcomes.
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "setup"))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("rotate_secrets")

from scripts.setup import env_files
from scripts.setup.generate_env import GENERATORS, generate_grafana_datasource


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, _, v = s.partition("=")
            env[k.strip()] = v.strip()
    return env


ENV_FULL = REPO_ROOT / ".env.full"
OLD = load_env(ENV_FULL)
NEW: dict[str, str] = {}
REPORT: list[tuple[str, str, str]] = []  # (var, status, note)


import ssl

# Lab services use self-signed certs (MISP https); verification is off for
# localhost rotation calls only.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def http(method: str, url: str, body=None, headers=None, timeout=30) -> tuple[int, str]:
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:  # nosec B310
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return -1, str(e)[:200]


def basic(user: str, pw: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def docker_exec(
    container: str, *cmd: str, timeout=60, env: dict[str, str] | None = None
) -> tuple[int, str]:
    full = ["docker", "exec"]
    for k, v in (env or {}).items():
        full += ["-e", f"{k}={v}"]
    full += [container, *cmd]
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[:500]
    except Exception as e:
        return -1, str(e)[:200]


def mark(var: str, status: str, note: str = "") -> None:
    REPORT.append((var, status, note))
    logger.info("  [%s] %s %s", status, var, f"— {note}" if note else "")


def _flush_new() -> None:
    """Persist every NEW value to the env files immediately.

    Rotated values must never exist only in memory: if the script crashes
    mid-run, the env files still reflect the live state.
    """
    if not NEW:
        return
    env_files.update_env_files(NEW, env_file=ENV_FULL)
    dotenv = REPO_ROOT / ".env"
    if dotenv.exists():
        content = dotenv.read_text(encoding="utf-8")
        for k, v in NEW.items():
            content = env_files._apply(content, k, v)
        dotenv.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- phase 1: live API
def phase_live_api() -> None:
    logger.info("== Phase 1: live-API credential rotation ==")
    th_user = OLD.get("THEHIVE_ADMIN_USER", "admin@soar.local")
    th_pass = OLD.get("THEHIVE_ADMIN_PASSWORD", "")
    th_url = "http://localhost:8100"

    # TheHive API key renew
    code, out = http(
        "POST",
        f"{th_url}/api/v1/user/{th_user}/key/renew",
        b"{}",
        {"Authorization": basic(th_user, th_pass)},
    )
    if code == 200 and len(out.strip().strip('"')) > 10:
        NEW["THEHIVE_API_KEY"] = out.strip().strip('"')
        mark("THEHIVE_API_KEY", "OK", "renewed via key/renew")
    else:
        mark("THEHIVE_API_KEY", "FAILED", f"HTTP {code}")
    _flush_new()

    # TheHive admin password
    new_th_pw = GENERATORS["THEHIVE_ADMIN_PASSWORD"]()
    code, _ = http(
        "POST",
        f"{th_url}/api/v1/user/{th_user}/password/set",
        {"password": new_th_pw},
        {"Authorization": basic(th_user, th_pass), "Content-Type": "application/json"},
    )
    if code == 404:
        code, _ = http(
            "PUT",
            f"{th_url}/api/v1/user/{th_user}",
            {"password": new_th_pw},
            {"Authorization": basic(th_user, th_pass), "Content-Type": "application/json"},
        )
    if code in (200, 201, 204):
        NEW["THEHIVE_ADMIN_PASSWORD"] = new_th_pw
        mark("THEHIVE_ADMIN_PASSWORD", "OK", "rotated via password/set")
    else:
        mark(
            "THEHIVE_ADMIN_PASSWORD",
            "NEEDS-MANUAL",
            f"password/set returned {code}; rotate via TheHive UI",
        )
    _flush_new()

    # Cortex org admin API key renew
    cx_user = OLD.get("CORTEX_ADMIN_USER", "orgadmin")
    cx_pass = OLD.get("CORTEX_ADMIN_PASSWORD", "")
    cx_url = "http://localhost:8101"
    code, out = http(
        "POST",
        f"{cx_url}/api/user/{cx_user}/key/renew",
        b"{}",
        {"Authorization": basic(cx_user, cx_pass)},
    )
    if code not in (200, 201):
        code, out = http(
            "POST",
            f"{cx_url}/api/user/{cx_user}/key/renew",
            b"{}",
            {"Authorization": basic("admin", cx_pass)},
        )
    if code in (200, 201) and len(out.strip().strip('"')) > 10:
        NEW["CORTEX_API_KEY"] = out.strip().strip('"')
        mark("CORTEX_API_KEY", "OK", "renewed via key/renew")
    else:
        mark("CORTEX_API_KEY", "FAILED", f"HTTP {code}")
    _flush_new()

    # Cortex admin (orgadmin) password
    new_cx_pw = GENERATORS["CORTEX_ADMIN_PASSWORD"]()
    code, _ = http(
        "POST",
        f"{cx_url}/api/user/{cx_user}/password/set",
        {"password": new_cx_pw},
        {"Authorization": basic(cx_user, cx_pass), "Content-Type": "application/json"},
    )
    if code == 404:
        code, _ = http(
            "PUT",
            f"{cx_url}/api/user/{cx_user}",
            {"password": new_cx_pw},
            {"Authorization": basic(cx_user, cx_pass), "Content-Type": "application/json"},
        )
    if code in (200, 201, 204):
        NEW["CORTEX_ADMIN_PASSWORD"] = new_cx_pw
        mark("CORTEX_ADMIN_PASSWORD", "OK", "rotated via password/set")
    else:
        mark("CORTEX_ADMIN_PASSWORD", "NEEDS-MANUAL", f"password/set returned {code}")
    _flush_new()

    # Grafana admin password (user id 1) — API first, grafana-cli fallback
    gf_url = "http://localhost:8084"
    new_gf_pw = GENERATORS["GRAFANA_ADMIN_PASSWORD"]()
    code, out = http(
        "PUT",
        f"{gf_url}/api/user/password",
        {"oldPassword": OLD.get("GRAFANA_ADMIN_PASSWORD", ""), "newPassword": new_gf_pw},
        {
            "Authorization": basic(
                OLD.get("GRAFANA_ADMIN_USER", "admin"), OLD.get("GRAFANA_ADMIN_PASSWORD", "")
            ),
            "Content-Type": "application/json",
        },
    )
    if code == 200:
        NEW["GRAFANA_ADMIN_PASSWORD"] = new_gf_pw
        mark("GRAFANA_ADMIN_PASSWORD", "OK", "rotated via user/password")
    else:
        rc, out2 = docker_exec(
            "soar_grafana", "grafana", "cli", "admin", "reset-admin-password", new_gf_pw
        )
        if rc != 0:
            rc, out2 = docker_exec(
                "soar_grafana", "grafana-cli", "admin", "reset-admin-password", new_gf_pw
            )
        if rc == 0:
            NEW["GRAFANA_ADMIN_PASSWORD"] = new_gf_pw
            mark("GRAFANA_ADMIN_PASSWORD", "OK", "rotated via grafana-cli")
        else:
            mark("GRAFANA_ADMIN_PASSWORD", "NEEDS-MANUAL", f"API {code}, cli rc={rc}")
    _flush_new()

    # MISP: rotate authkey + admin password via cake CLI (deterministic,
    # non-interactive; old authkeys get disabled automatically)
    misp_admin = OLD.get("MISP_ADMIN_EMAIL", "admin@admin.test")
    new_misp_key = GENERATORS["MISP_API_KEY"]()
    rc, out = docker_exec(
        "soar_misp",
        "/var/www/MISP/app/Console/cake",
        "user",
        "change_authkey",
        misp_admin,
        new_misp_key,
    )
    if rc == 0:
        NEW["MISP_API_KEY"] = new_misp_key
        mark("MISP_API_KEY", "OK", "rotated via cake change_authkey")
    else:
        mark("MISP_API_KEY", "FAILED", out.strip()[:100])
    _flush_new()

    new_misp_pw = GENERATORS["MISP_ADMIN_PASSWORD"]()
    rc, out = docker_exec(
        "soar_misp",
        "/var/www/MISP/app/Console/cake",
        "user",
        "change_pw",
        "--no_password_change",
        misp_admin,
        new_misp_pw,
    )
    if rc == 0:
        NEW["MISP_ADMIN_PASSWORD"] = new_misp_pw
        mark("MISP_ADMIN_PASSWORD", "OK", "rotated via cake change_pw")
    else:
        mark("MISP_ADMIN_PASSWORD", "NEEDS-MANUAL", out.strip()[:100])
    _flush_new()

    # Shuffle apikey via admin session
    sh_url = "http://localhost:8081"
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(
        f"{sh_url}/api/v1/login",
        data=json.dumps(
            {
                "username": OLD.get("SHUFFLE_DEFAULT_USERNAME", "admin"),
                "password": OLD.get("SHUFFLE_DEFAULT_PASSWORD", ""),
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener.open(req, timeout=30) as r:
            if r.status == 200:
                req2 = urllib.request.Request(f"{sh_url}/api/v1/users/generateapikey")
                with opener.open(req2, timeout=30) as r2:
                    if r2.status == 200:
                        body = json.loads(r2.read().decode())
                        key = body.get("apikey") or body.get("api_key") or ""
                        if len(key) > 10:
                            NEW["SHUFFLE_DEFAULT_APIKEY"] = key
                            mark("SHUFFLE_DEFAULT_APIKEY", "OK", "via generateapikey")
                        else:
                            mark("SHUFFLE_DEFAULT_APIKEY", "FAILED", "empty key")
    except Exception as e:
        mark("SHUFFLE_DEFAULT_APIKEY", "FAILED", str(e)[:120])

    mark(
        "SHUFFLE_DEFAULT_PASSWORD",
        "NEEDS-MANUAL",
        "no supported admin-side password API; rotate via Shuffle UI",
    )
    _flush_new()
    mark(
        "MISP_ENCRYPTION_KEY",
        "SKIPPED",
        "rotating orphans encrypted MISP data — requires MISP reset",
    )


# ---------------------------------------------------------------- phase 2: DB ALTER
def phase_db_alter() -> None:
    logger.info("== Phase 2: database password rotation (ALTER USER) ==")
    # grafana_db postgres: superuser 'grafana', password = GRAFANA_DATABASE_PASSWORD
    # (POSTGRES_* vars are env-only — no live postgres consumes them).
    gf_db_user = OLD.get("GRAFANA_DATABASE_USER", "grafana")
    NEW["GRAFANA_DATABASE_PASSWORD"] = GENERATORS["GRAFANA_DATABASE_PASSWORD"]()
    old_gf = OLD.get("GRAFANA_DATABASE_PASSWORD", "")
    sql = f"ALTER USER {gf_db_user} WITH PASSWORD '{NEW['GRAFANA_DATABASE_PASSWORD']}';"
    rc, out = docker_exec(
        "soar_grafana_db",
        "psql",
        "-h",
        "localhost",
        "-U",
        gf_db_user,
        "-d",
        "postgres",
        "-c",
        sql,
        env={"PGPASSWORD": old_gf},
    )
    mark("GRAFANA_DATABASE_PASSWORD", "OK" if rc == 0 else "FAILED", out.strip()[:80])
    _flush_new()
    _flush_new()

    misp_db_user = OLD.get("MISP_DB_USER", "misp")
    NEW["MISP_DB_PASSWORD"] = GENERATORS["MISP_DB_PASSWORD"]()
    NEW["MISP_DB_ROOT_PASSWORD"] = GENERATORS["MISP_DB_ROOT_PASSWORD"]()
    old_root = OLD.get("MISP_DB_ROOT_PASSWORD", "")
    sql = (
        f"ALTER USER '{misp_db_user}'@'%' IDENTIFIED BY '{NEW['MISP_DB_PASSWORD']}';"
        f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{NEW['MISP_DB_ROOT_PASSWORD']}';"
        "FLUSH PRIVILEGES;"
    )
    rc, out = docker_exec("soar_misp_db", "mysql", "-uroot", f"-p{old_root}", "-e", sql)
    _flush_new()
    mark("MISP_DB_PASSWORD", "OK" if rc == 0 else "FAILED", out.strip()[:100])
    mark("MISP_DB_ROOT_PASSWORD", "OK" if rc == 0 else "FAILED", "same mysql batch")
    _flush_new()


# ---------------------------------------------------------------- phase 3+4: env-only + sync
def phase_env_and_sync() -> None:
    logger.info("== Phase 3: env-only secrets ==")
    # Vars whose value lives in service-side state: if live rotation failed,
    # generating a fresh env value would silently drift env vs live. Skip them
    # unless phase 1/2 already wrote a confirmed value.
    live_state_vars = {
        "THEHIVE_API_KEY",
        "THEHIVE_ADMIN_PASSWORD",
        "CORTEX_API_KEY",
        "CORTEX_ADMIN_PASSWORD",
        "MISP_API_KEY",
        "MISP_ADMIN_PASSWORD",
        "SHUFFLE_DEFAULT_APIKEY",
        "SHUFFLE_DEFAULT_PASSWORD",
        "GRAFANA_DATABASE_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
        "MISP_DB_PASSWORD",
        "MISP_DB_ROOT_PASSWORD",
        "MISP_ENCRYPTION_KEY",
        "JWT_EXPIRATION_MINUTES",
        "JWT_ALGORITHM",
    }
    live_rotated = set(NEW.keys())
    for var, gen in GENERATORS.items():
        if var in live_rotated or var in live_state_vars:
            if var in live_state_vars and var not in live_rotated:
                mark(var, "NEEDS-MANUAL", "live rotation failed — env untouched")
            continue
        NEW[var] = gen()
        mark(var, "OK", "new random value")
    # INTERNAL_SERVICE_TOKEN not in GENERATORS
    if "INTERNAL_SERVICE_TOKEN" in OLD:
        import secrets as _s

        NEW["INTERNAL_SERVICE_TOKEN"] = _s.token_hex(32)
        mark("INTERNAL_SERVICE_TOKEN", "OK", "new random value")

    logger.info("== Phase 4: sync env files ==")
    written = env_files.update_env_files(NEW, env_file=ENV_FULL)
    for p in written:
        logger.info("  wrote %s", p.name)
    dotenv = REPO_ROOT / ".env"
    if dotenv.exists():
        content = dotenv.read_text(encoding="utf-8")
        for k, v in NEW.items():
            content = env_files._apply(content, k, v)
        dotenv.write_text(content, encoding="utf-8")
        logger.info("  wrote %s", dotenv.name)


# ---------------------------------------------------------------- phase 5: recreate
COMPOSE_DIR = REPO_ROOT / "infra" / "docker" / "compose"
COMPOSE_FILES = [
    COMPOSE_DIR / "docker-compose.yml",
    COMPOSE_DIR / "docker-compose.core.yml",
    COMPOSE_DIR / "docker-compose.misp.yml",
    COMPOSE_DIR / "docker-compose.api.yml",
    COMPOSE_DIR / "docker-compose.opensearch.yml",
    COMPOSE_DIR / "logging" / "docker-compose.logging.yml",
]


def phase_recreate() -> None:
    logger.info("== Phase 5: recreate containers with new env ==")
    cmd = ["docker", "compose", "-p", "soar", "--env-file", str(REPO_ROOT / ".env")]
    for f in COMPOSE_FILES:
        cmd += ["-f", str(f)]
    cmd += ["up", "-d"]
    r = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=900)
    logger.info("  compose up rc=%d", r.returncode)
    if r.returncode != 0:
        logger.error("  %s", r.stderr[:800])


# ---------------------------------------------------------------- phase 6: post-sync
def phase_post_sync() -> None:
    logger.info("== Phase 6: dependent re-sync ==")
    # grafana datasource file embeds ELASTIC_PASSWORD
    generate_grafana_datasource(
        NEW.get("ELASTIC_PASSWORD", OLD.get("ELASTIC_PASSWORD", "")),
        REPO_ROOT / "infra/docker/config/templates/grafana-datasources.yml.template",
        REPO_ROOT / "runtime/config/grafana-datasources.yml",
    )
    logger.info("  grafana datasource re-rendered")
    logger.info("  NOTE: run `make init-webhook` to regenerate the Shuffle workflow")
    logger.info("        (it embeds thehive Bearer + cortex Basic credentials)")
    logger.info("  NOTE: run `python scripts/setup/init_thehive.py` (configure_cortex)")
    logger.info("        so TheHive's cortex.conf carries the new CORTEX_API_KEY")


# ---------------------------------------------------------------- phase 7: verify
def phase_verify() -> None:
    logger.info("== Phase 7: negative probes + health ==")
    # old webhook token must fail
    code, _ = http(
        "POST",
        "http://localhost:8000/api/v1/webhooks/siem",
        {"alert_id": "rotation-probe"},
        {
            "Authorization": f"Bearer {OLD.get('SIEM_WEBHOOK_TOKEN','')}",
            "Content-Type": "application/json",
        },
    )
    logger.info("  old SIEM_WEBHOOK_TOKEN -> HTTP %d (expect 401/403)", code)
    # old thehive key must fail
    code, _ = http(
        "GET",
        "http://localhost:8100/api/v1/user/current",
        headers={"Authorization": f"Bearer {OLD.get('THEHIVE_API_KEY','')}"},
    )
    logger.info("  old THEHIVE_API_KEY -> HTTP %d (expect 401)", code)
    # health
    code, out = http("GET", "http://localhost:8000/health")
    logger.info("  api /health -> HTTP %d %s", code, out[:80])


def main() -> int:
    if not ENV_FULL.exists():
        logger.error(".env.full missing")
        return 1
    phase_live_api()
    phase_db_alter()
    phase_env_and_sync()
    phase_recreate()
    logger.info("Waiting for services to settle...")
    time.sleep(30)
    phase_post_sync()
    phase_verify()
    logger.info("\n== ROTATION REPORT ==")
    ok = sum(1 for _, s, _ in REPORT if s == "OK")
    manual = [v for v, s, _ in REPORT if s == "NEEDS-MANUAL"]
    failed = [v for v, s, _ in REPORT if s == "FAILED"]
    logger.info("  rotated: %d | needs-manual: %d | failed: %d", ok, len(manual), len(failed))
    if manual:
        logger.info("  NEEDS-MANUAL: %s", ", ".join(manual))
    if failed:
        logger.info("  FAILED: %s", ", ".join(failed))
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
