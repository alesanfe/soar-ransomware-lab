#!/usr/bin/env python3
"""Generate a runnable .env.full and grafana-datasources.yml from templates.

Reads `.env.example` and replaces known secret/password values with random ones.
The generated `.env.full` is meant for local lab use only and must NOT be committed.
Also renders `infra/docker/compose/logging/grafana-datasources.yml` from its
template, substituting the generated Elasticsearch password so the Grafana
Elasticsearch datasource stays in sync.
"""

from __future__ import annotations

import logging
import os
import secrets
import string
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_TEMPLATE = REPO_ROOT / ".env.example"
ENV_OUTPUT = REPO_ROOT / ".env.full"
DATASOURCE_TEMPLATE = (
    REPO_ROOT / "infra" / "docker" / "compose" / "logging" / "grafana-datasources.yml.template"
)
DATASOURCE_OUTPUT = (
    REPO_ROOT / "infra" / "docker" / "compose" / "logging" / "grafana-datasources.yml"
)


def _random_alnum(length: int) -> str:
    """Random alphanumeric string."""
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def _random_hex(length: int) -> str:
    """Random lowercase hex string of the requested length."""
    return secrets.token_hex(length // 2)[:length]


def _random_urlsafe(length: int) -> str:
    """URL-safe token of the requested length."""
    return secrets.token_urlsafe(length)[:length]


def _make_password(length: int = 32, special: str = "") -> str:
    """Random password with at least one upper, lower, digit and optional
    special char."""
    if special:
        alphabet = string.ascii_letters + string.digits + special
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice(special),
        ]
    else:
        alphabet = string.ascii_letters + string.digits
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
        ]
    for _ in range(length - len(password)):
        password.append(secrets.choice(alphabet))
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def generate_elastic_password() -> str:
    # Generate a random password. The same value must be set as ELASTIC_PASSWORD
    # in .env.full and used by all services that connect to Elasticsearch
    # (TheHive, Cortex, Grafana datasource, Makefile metrics targets).
    return _make_password(28)


def generate_opensearch_password() -> str:
    return _make_password(32)


def generate_thehive_secret() -> str:
    return _random_hex(32)


def generate_api_key(length: int = 64) -> str:
    return _random_alnum(length)


def generate_cortex_secret() -> str:
    return _random_hex(32)


def generate_shuffle_password() -> str:
    return _make_password(32)


def generate_postgres_password() -> str:
    return _make_password(32)


def generate_redis_password() -> str:
    return _make_password(32)


def generate_misp_password() -> str:
    return _make_password(32)


def generate_misp_api_key() -> str:
    return _random_alnum(40)


def is_valid_misp_api_key(value: str) -> bool:
    return len(value) == 40 and value.isalnum()


def generate_misp_hex_key(length: int = 32) -> str:
    return _random_hex(length)


def generate_grafana_password() -> str:
    return _make_password(32)


def generate_web_ui_password() -> str:
    return _make_password(32)


def generate_api_auth_secret() -> str:
    return _random_hex(32)


def generate_jwt_secret() -> str:
    return _random_alnum(64)


def generate_webhook_token(length: int = 48) -> str:
    return _random_urlsafe(length)


GENERATORS: dict[str, callable] = {
    "ELASTIC_PASSWORD": generate_elastic_password,
    "OPENSEARCH_PASSWORD": generate_opensearch_password,
    "THEHIVE_ADMIN_PASSWORD": lambda: _make_password(32, special="."),
    "THEHIVE_SECRET": generate_thehive_secret,
    "THEHIVE_API_KEY": lambda: generate_api_key(64),
    "CORTEX_ADMIN_PASSWORD": lambda: _make_password(32, special="."),
    "CORTEX_SECRET": generate_cortex_secret,
    "CORTEX_API_KEY": lambda: generate_api_key(64),
    "SHUFFLE_DEFAULT_PASSWORD": generate_shuffle_password,
    "SHUFFLE_DEFAULT_APIKEY": lambda: generate_api_key(64),
    "POSTGRES_PASSWORD": generate_postgres_password,
    "REDIS_PASSWORD": generate_redis_password,
    "MISP_DB_ROOT_PASSWORD": generate_misp_password,
    "MISP_DB_PASSWORD": generate_misp_password,
    "MISP_ADMIN_PASSWORD": generate_misp_password,
    "MISP_API_KEY": generate_misp_api_key,
    "MISP_ENCRYPTION_KEY": lambda: generate_misp_hex_key(32),
    "MISP_SALT": lambda: generate_misp_hex_key(32),
    "GRAFANA_ADMIN_PASSWORD": generate_grafana_password,
    "GRAFANA_DATABASE_PASSWORD": generate_grafana_password,
    "WEB_UI_PASSWORD": generate_web_ui_password,
    "API_AUTH_SECRET": generate_api_auth_secret,
    "JWT_SECRET_KEY": generate_jwt_secret,
    "JWT_EXPIRATION_MINUTES": lambda: "60",
    "JWT_ALGORITHM": lambda: "HS256",
    "SIEM_WEBHOOK_TOKEN": lambda: generate_webhook_token(48),
    "EDR_SIM_TOKEN": lambda: generate_webhook_token(48),
    "FIREWALL_SIM_TOKEN": lambda: generate_webhook_token(48),
}


def _load_existing_env(path: Path) -> dict[str, str]:
    """Load non-placeholder key=value pairs from an existing .env file."""
    existing: dict[str, str] = {}
    if not path.exists():
        return existing
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and not (value.startswith("<") and value.endswith(">")):
            existing[key] = value
    return existing


def generate_env_file(template_path: Path, output_path: Path) -> dict[str, str]:
    """Generate .env.full from .env.example, returning the secret values used.

    Existing real values in output_path are preserved so re-running the
    script does not rotate credentials already deployed. Placeholders
    and new keys are filled with generated values.
    """
    if not template_path.exists():
        raise FileNotFoundError(f"Environment template not found: {template_path}")

    text = template_path.read_text(encoding="utf-8")
    existing = _load_existing_env(output_path)
    generated: dict[str, str] = {}
    output_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output_lines.append(line)
            continue

        key, _value = stripped.split("=", 1)
        key = key.strip()
        generator = GENERATORS.get(key)
        if key in existing and (key != "MISP_API_KEY" or is_valid_misp_api_key(existing[key])):
            value = existing[key]
        elif generator:
            value = generator()
        else:
            output_lines.append(line)
            continue

        if value is not None:
            # Keep the real value used (existing or newly generated) in the returned secrets map
            generated[key] = value
        output_lines.append(f"{key}={value}")

    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return generated


def generate_grafana_datasource(
    elastic_password: str,
    template_path: Path,
    output_path: Path,
) -> None:
    """Render Grafana datasource file with the current Elasticsearch
    password."""
    default_template = """apiVersion: 1

datasources:
  - name: Loki
    type: loki
    access: proxy
    url: {loki_url}
    jsonData:
      maxLines: 1000
    isDefault: true
    editable: true

  - name: Elasticsearch
    type: elasticsearch
    access: proxy
    url: {es_url}
    jsonData:
      esVersion: "8.0.0"
      timeField: "@timestamp"
      index: "soar-metrics"
      maxConcurrentShardRequests: 5
      includeFrozen: false
    basicAuth: true
    basicAuthUser: {elastic_user}
    secureJsonData:
      basicAuthPassword: <ELASTIC_PASSWORD>
    editable: true

  - name: SOAR API
    type: json
    access: proxy
    url: {api_url}
    jsonData:
      httpMethod: "GET"
    editable: true
"""
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = default_template

    rendered = template.replace("<ELASTIC_PASSWORD>", elastic_password)
    rendered = rendered.format(
        loki_url=os.environ.get("LOKI_URL", "http://loki:3100"),
        es_url=os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200"),
        elastic_user=os.environ.get("ELASTIC_USERNAME", "elastic"),
        api_url=os.environ.get("API_URL", "http://api:8000"),
    )
    output_path.write_text(rendered, encoding="utf-8")


def main() -> int:
    logger.info("Generating environment file from %s", ENV_TEMPLATE)
    generated = generate_env_file(ENV_TEMPLATE, ENV_OUTPUT)
    logger.info("Wrote %s", ENV_OUTPUT)

    elastic_password = generated.get("ELASTIC_PASSWORD", "")
    if not elastic_password:
        logger.error("ERROR: ELASTIC_PASSWORD was not generated")
        return 1

    logger.info("Rendering Grafana datasource to %s", DATASOURCE_OUTPUT)
    generate_grafana_datasource(elastic_password, DATASOURCE_TEMPLATE, DATASOURCE_OUTPUT)
    logger.info("Wrote %s", DATASOURCE_OUTPUT)

    print("\nNext steps:")
    print("  1. Review .env.full and adjust non-secret variables if needed.")
    print("  2. Never commit .env.full or infra/docker/compose/logging/grafana-datasources.yml.")
    print("  3. Run 'make up' to start the stack.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
