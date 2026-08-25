"""Configuration object for the Shuffle workflow setup.

This is the **only** module that reads environment variables related to
the setup process.  The rest of the system receives a ready-made
``SetupConfig`` instance and never touches ``os.environ`` directly.

No hardcoded fallback passwords — the caller is expected to validate
credentials via :mod:`credentials` before using them.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Load environment variables from .env file (only if not already set).
# Tried lazily so that ``import config`` works even if python-dotenv
# is not installed (e.g. in minimal test environments).
try:
    from dotenv import load_dotenv

    if not load_dotenv(".env.full", override=False):
        load_dotenv(override=False)
except ImportError:  # pragma: no cover
    pass


# ── URLs with defaults ─────────────────────────────────────────────────────────
# SHUFFLE_URL: always use the backend (port 5001) for API/setup operations.
# The SHUFFLE_URL env may point to the frontend (port 80); ignore it for setup.
SHUFFLE_URL = os.environ.get(
    "SHUFFLE_BACKEND_URL", os.environ.get("SHUFFLE_API_URL", "http://shuffle-backend:5001")
)
ES_URL = os.environ.get("ELASTICSEARCH_URL", os.environ.get("ES_URL", "http://elasticsearch:9200"))
SHUFFLE_DATA_URL = os.environ.get("SHUFFLE_OPENSEARCH_URL", "http://opensearch:9200")
SHUFFLE_DATA_USER = os.environ.get("SHUFFLE_OPENSEARCH_USERNAME", "")
SHUFFLE_DATA_PASS = os.environ.get("SHUFFLE_OPENSEARCH_PASSWORD", "")
THEHIVE_URL = os.environ.get("THEHIVE_URL", "http://thehive:9000")
CORTEX_URL = os.environ.get("CORTEX_URL", "http://cortex:9001")
MISP_URL = os.environ.get("MISP_URL", "http://misp:80")
LOKI_URL = os.environ.get("LOKI_URL", "http://loki:3100")
API_URL = os.environ.get("API_URL", "http://api:8000")
TENZIR_URL = os.environ.get("TENZIR_URL", "http://tenzir-node:5160")

# ── Basic credentials (non-rotating) ───────────────────────────────────────────
# All credentials MUST be provided via environment variables (e.g. .env.full).
SHUFFLE_USER = os.environ.get("SHUFFLE_USER", os.environ.get("SHUFFLE_DEFAULT_USERNAME", "admin"))
SHUFFLE_PASS = os.environ.get("SHUFFLE_PASS", os.environ.get("SHUFFLE_DEFAULT_PASSWORD", ""))
ES_USER = os.environ.get("ELASTIC_USERNAME", "elastic")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "")

THEHIVE_ADMIN_USER = os.environ.get("THEHIVE_ADMIN_USER", "admin")
THEHIVE_ADMIN_PASS = os.environ.get("THEHIVE_ADMIN_PASSWORD", "")
CORTEX_ADMIN_USER = os.environ.get("CORTEX_ADMIN_USER", "admin")
CORTEX_ADMIN_PASS = os.environ.get("CORTEX_ADMIN_PASSWORD", "")
MISP_ADMIN_EMAIL = os.environ.get("MISP_ADMIN_EMAIL", "admin@soar.local")
MISP_ADMIN_PASS = os.environ.get("MISP_ADMIN_PASSWORD", "")

# ── Internal Docker URLs (using container names in the Docker network) ─────────
# Reuse the already-resolved URLs which default to the internal Docker hostnames.
# MISP uses HTTPS on port 443 internally.
THEHIVE_INT = THEHIVE_URL
CORTEX_INT = CORTEX_URL
MISP_INT = MISP_URL
ES_INT = ES_URL

# ── Workflow metadata ──────────────────────────────────────────────────────────
WF_NAME = "SOAR-Ransomware-Response"

# ── Env-file priority list ─────────────────────────────────────────────────────
# Prefer .env.full (inside container at /app/.env.full) over .env
ENV_FILE = next((p for p in ["/app/.env.full", ".env.full", ".env"] if os.path.exists(p)), ".env")


def check_required_passwords() -> None:
    """Raise ``RuntimeError`` if any mandatory password is missing."""
    missing = []
    if not SHUFFLE_PASS:
        missing.append("SHUFFLE_PASS (or SHUFFLE_DEFAULT_PASSWORD)")
    if not THEHIVE_ADMIN_PASS:
        missing.append("THEHIVE_ADMIN_PASSWORD")
    if not CORTEX_ADMIN_PASS:
        missing.append("CORTEX_ADMIN_PASSWORD")
    if not MISP_ADMIN_PASS:
        missing.append("MISP_ADMIN_PASSWORD")
    if not ES_PASS:
        missing.append("ELASTIC_PASSWORD")
    if missing:
        msg = "Missing required credentials: " + ", ".join(missing)
        logger.error("%s", msg)
        logger.error("Set them in .env.full (or as environment variables) and retry.")
        raise RuntimeError(msg)
