#!/usr/bin/env python3
"""
init_thehive.py - Initialises TheHive 5.x (API v1).

TheHive 5 is self-contained: JanusGraph (BerkeleyJE) storage + Lucene index,
so no Elasticsearch index template or join-field hack is needed.

Bootstrap flow (fresh instance):
  1. Wait for GET /api/v1/status (public).
  2. Authenticate as the built-in admin  admin@thehive.local:secret.
  3. Set the admin password to THEHIVE_ADMIN_PASSWORD.
  4. Renew the admin API key and persist it to .env.full (THEHIVE_API_KEY).
  5. Inject CORTEX_API_KEY into the mounted application.conf and restart
     TheHive so the cortex connector picks it up.

Usage:
  python init_thehive.py           # idempotent
  python init_thehive.py --reset   # re-set password + renew key unconditionally
"""

import base64
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

logger = logging.getLogger(__name__)

THEHIVE_URL = os.environ.get("THEHIVE_URL", "http://thehive:9000")
CORTEX_URL = os.environ.get("CORTEX_URL", "http://cortex:9001")
# TheHive 5 logins are email-format. THEHIVE_ADMIN_USER is the org-admin that
# owns cases/alerts for the lab (built-in admin@thehive.local is a platform
# superadmin without manageCase/* permissions — bootstrap only).
ADMIN_USER = os.environ.get("THEHIVE_ADMIN_USER", "analyst@soar.local")
ADMIN_PASS = os.environ.get("THEHIVE_ADMIN_PASSWORD", "")
ORG_NAME = os.environ.get("THEHIVE_ORG", "soar")
DEFAULT_ADMIN_USER = "admin@thehive.local"
DEFAULT_ADMIN_PASS = "secret"
ENV_FILE = next(
    (
        p
        for p in ["/app/.env.full", ".env.full", "/app/.env.container", ".env.container", ".env"]
        if os.path.exists(p) and os.access(p, os.W_OK)
    ),
    ".env.full",
)


def _auth_header(user: str, password: str) -> dict[str, str]:
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {
        HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
        HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {creds}",
    }


def thehive_request(method: str, path: str, body=None, user: str = "", password: str = ""):
    """Call TheHive 5 ``/api/v1/...``. ``path`` excludes the ``/api/v1`` prefix."""
    url = f"{THEHIVE_URL}/api/v1/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    headers = _auth_header(user, password) if user else {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read()), "http": e.code}
        except Exception:
            return {"error": e.reason, "http": e.code}
    except Exception as e:
        return {"error": str(e)}


def wait_for_thehive(timeout: int = 300) -> bool:
    logger.info("Waiting for TheHive (GET /api/v1/status/public)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"{THEHIVE_URL}/api/v1/status/public", timeout=5
            ) as r:  # nosec B310
                if r.status == 200:
                    logger.info("  ready.")
                    time.sleep(2)  # Grace period for user/index bootstrap
                    return True
        except Exception as exc:
            logger.debug("TheHive not ready: %s", exc)
        time.sleep(3)
    logger.warning(" TIMEOUT")
    return False


def wait_for_admin_auth(user: str, password: str, timeout: int = 120) -> bool:
    logger.info("  Waiting for admin authentication (%s)", user)
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = thehive_request("GET", "user/current", user=user, password=password)
        if "error" not in result and result.get("_id"):
            logger.info("  auth OK.")
            return True
        time.sleep(3)
    logger.warning(" TIMEOUT")
    return False


def admin_identity(user: str, password: str) -> str | None:
    """Resolve the admin user ``_id`` via /user/current."""
    result = thehive_request("GET", "user/current", user=user, password=password)
    if isinstance(result, dict) and result.get("_id"):
        return str(result["_id"])
    return None


def ensure_organisation(auth_user: str, auth_pass: str) -> bool:
    """Ensure the lab organisation exists (requires platform admin)."""
    existing = thehive_request(
        "POST",
        "query",
        {
            "query": [
                {"_name": "listOrganisation"},
                {"_name": "filter", "_eq": {"_field": "name", "_value": ORG_NAME}},
            ]
        },
        user=auth_user,
        password=auth_pass,
    )
    if isinstance(existing, list) and existing:
        logger.info("  Organisation '%s' already exists.", ORG_NAME)
        return True
    result = thehive_request(
        "POST",
        "organisation",
        {"name": ORG_NAME, "description": "SOAR lab organisation"},
        user=auth_user,
        password=auth_pass,
    )
    if "error" not in result or "already" in str(result).lower():
        logger.info("  Organisation '%s' ready.", ORG_NAME)
        return True
    logger.error("  Failed to create organisation: %s", result)
    return False


def ensure_org_user(auth_user: str, auth_pass: str) -> str | None:
    """Ensure ADMIN_USER exists as org-admin of ORG_NAME; return its _id."""
    existing = thehive_request(
        "POST",
        "query",
        {
            "query": [
                {"_name": "listUser"},
                {"_name": "filter", "_eq": {"_field": "login", "_value": ADMIN_USER}},
            ]
        },
        user=auth_user,
        password=auth_pass,
    )
    if isinstance(existing, list) and existing:
        uid = str(existing[0].get("_id", ""))
        logger.info("  User '%s' already exists (%s).", ADMIN_USER, uid)
        return uid or None
    result = thehive_request(
        "POST",
        "user",
        {
            "login": ADMIN_USER,
            "name": "SOC Analyst",
            "profile": "org-admin",
            "organisation": ORG_NAME,
        },
        user=auth_user,
        password=auth_pass,
    )
    uid = result.get("_id") if isinstance(result, dict) else None
    if uid:
        logger.info("  Created org-admin user '%s' (%s).", ADMIN_USER, uid)
        return str(uid)
    logger.error("  Failed to create org user: %s", result)
    return None


def set_admin_password(user_id: str, password: str, auth_user: str, auth_pass: str) -> bool:
    """PUT /user/{id}/password/set requires org-admin privileges."""
    result = thehive_request(
        "POST",
        f"user/{user_id}/password/set",
        {"password": password},
        user=auth_user,
        password=auth_pass,
    )
    # TheHive 5 returns 204 (empty body → {}) on success
    if "error" not in result:
        logger.info("  Admin password set.")
        return True
    logger.error("  password/set failed: %s", result)
    return False


def renew_api_key(user_id: str, auth_user: str, auth_pass: str) -> str | None:
    """POST /user/{id}/key/renew — returns the raw key as text/plain."""
    url = f"{THEHIVE_URL}/api/v1/user/{user_id}/key/renew"
    for attempt in range(1, 6):
        req = urllib.request.Request(
            url, data=b"{}", method="POST", headers=_auth_header(auth_user, auth_pass)
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                key = resp.read().decode().strip().strip('"')
                if len(key) > 10:
                    logger.info("  API key generated.")
                    return key
                logger.warning("  key/renew attempt %d/5: unexpected body %r", attempt, key[:40])
        except Exception as e:
            logger.warning("  key/renew attempt %d/5 failed: %s", attempt, str(e)[:120])
        time.sleep(5)
    logger.error("  Failed to generate API key.")
    return None


def update_env_file(api_key: str) -> None:
    if not api_key or not os.path.exists(ENV_FILE):
        return
    logger.info("Updating %s...", ENV_FILE)
    try:
        try:
            from scripts.setup import env_files
        except ImportError:
            import env_files  # type: ignore[no-redef]

        written = env_files.update_env_files(
            {"THEHIVE_API_KEY": api_key, "THEHIVE_ADMIN_USER": ADMIN_USER},
            env_file=ENV_FILE,
        )
        logger.info("  Done." if written else f"  Warning: {ENV_FILE} not found.")
    except OSError as e:
        logger.warning("  Warning: Could not update %s: %s", ENV_FILE, e)


def configure_cortex() -> None:
    """Report the Cortex connector status.

    The connector key is injected via the ``CORTEX_API_KEY`` container env
    (resolved by ``${?CORTEX_API_KEY}`` in application.conf), so a key
    rotation only requires ``docker compose up -d thehive`` — no rewrite,
    no restart from here.
    """
    try:
        status = thehive_request("GET", "status", user=ADMIN_USER, password=ADMIN_PASS)
        cortex = (status or {}).get("connectors", {}).get("cortex", {})
        servers = cortex.get("servers", [])
        names = [s.get("name") for s in servers]
        logger.info(
            "  [cortex] connector status=%s servers=%s",
            cortex.get("status", "unknown"),
            names or "-",
        )
    except Exception as e:
        logger.warning("  [cortex] Could not verify TheHive status: %s", e)


def main() -> None:
    global ADMIN_PASS
    force_reset = "--reset" in sys.argv

    if not ADMIN_PASS and os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            content = f.read()
            m = re.search(r"^THEHIVE_ADMIN_PASSWORD=(.+)$", content, re.MULTILINE)
            if m:
                ADMIN_PASS = m.group(1).strip().strip('"')

    print("=" * 60)
    print("TheHive 5 Init Script" if not force_reset else "TheHive 5 Reset Script")
    print("=" * 60)

    if not wait_for_thehive():
        logger.error("ERROR: TheHive is not running. Start containers first.")
        sys.exit(1)

    # 1) Try configured credentials; fall back to bootstrap admin/secret.
    auth_user, auth_pass = ADMIN_USER, ADMIN_PASS
    if ADMIN_PASS and wait_for_admin_auth(ADMIN_USER, ADMIN_PASS, timeout=10):
        logger.info("Configured org-user credentials are valid.")
    elif ADMIN_PASS and wait_for_admin_auth(DEFAULT_ADMIN_USER, ADMIN_PASS, timeout=10):
        logger.info("Built-in admin uses the configured password already.")
        auth_user, auth_pass = DEFAULT_ADMIN_USER, ADMIN_PASS
    elif wait_for_admin_auth(DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS, timeout=30):
        logger.info("Using TheHive bootstrap credentials (admin@thehive.local/secret).")
        auth_user, auth_pass = DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS
    else:
        logger.error("ERROR: cannot authenticate to TheHive with any admin credential.")
        sys.exit(1)

    if auth_user == ADMIN_USER:
        # Org user already authenticates → org/user bootstrap already done.
        org_user_id = admin_identity(ADMIN_USER, ADMIN_PASS)
        if not org_user_id:
            logger.error("ERROR: could not resolve org user id.")
            sys.exit(1)
    else:
        # Fresh bootstrap: set platform-admin password away from 'secret'.
        bootstrap_id = admin_identity(auth_user, auth_pass)
        if not bootstrap_id:
            logger.error("ERROR: could not resolve admin user id.")
            sys.exit(1)
        if ADMIN_PASS:
            if set_admin_password(bootstrap_id, ADMIN_PASS, auth_user, auth_pass):
                auth_pass = ADMIN_PASS

        # Organisation + org-admin case user (platform admin lacks manageCase/*)
        if not ensure_organisation(auth_user, auth_pass):
            sys.exit(1)
        org_user_id = ensure_org_user(auth_user, auth_pass)
        if not org_user_id:
            sys.exit(1)
        if ADMIN_PASS:
            set_admin_password(org_user_id, ADMIN_PASS, auth_user, auth_pass)

    # 4) API key for the org user — this is what THEHIVE_API_KEY must hold
    #    (the platform-admin key cannot create cases). Renewing rotates the
    #    key, so only do it when no valid key is configured.
    existing_key = os.environ.get("THEHIVE_API_KEY", "")
    if existing_key and not force_reset:
        # Bearer probe — thehive_request only does Basic; do it directly.
        req = urllib.request.Request(
            f"{THEHIVE_URL}/api/v1/user/current",
            headers={
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
                HEADER_AUTHORIZATION: f"Bearer {existing_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:  # nosec B310
                key_valid = r.status == 200
        except urllib.error.HTTPError as e:
            key_valid = False
            logger.debug("  existing key probe HTTP %s", e.code)
        except Exception:
            key_valid = False
        if key_valid:
            logger.info("  Existing THEHIVE_API_KEY is valid — skipping renewal.")
            api_key = existing_key
        else:
            logger.info("  Existing THEHIVE_API_KEY invalid/missing — renewing.")
            api_key = None
    else:
        api_key = None
    if not api_key:
        api_key = renew_api_key(org_user_id, auth_user, auth_pass)
        if not api_key:
            logger.error("ERROR: TheHive API key generation failed.")
            sys.exit(1)
        # Persist where the host can sync it back to .env.full — no env
        # file is writable from inside this container.
        for out in (
            "/app/runtime/results/thehive_api_key.txt",
            "runtime/results/thehive_api_key.txt",
        ):
            try:
                with open(out, "w") as fh:
                    fh.write(api_key)
                logger.info("  Key written to %s", out)
                break
            except OSError:
                continue
    update_env_file(api_key)

    # 5) Cortex connector key
    ADMIN_PASS = ADMIN_PASS or auth_pass
    configure_cortex()

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  URL:        {THEHIVE_URL}")
    print(f"  Org:        {ORG_NAME}")
    print(f"  Case user:  {ADMIN_USER} / <redacted>")
    print("  Bearer key: configured" if api_key else "")
    print("=" * 60)


if __name__ == "__main__":
    main()
