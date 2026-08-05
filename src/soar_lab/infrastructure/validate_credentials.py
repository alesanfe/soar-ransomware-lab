#!/usr/bin/env python3
"""
Credential validation script.
Verifies that all credentials in .env.full match defaults
in docker-compose files and Python scripts.
"""
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def parse_env_file(env_path: Path) -> Dict[str, str]:
    """Parse .env file and return dict of variables."""
    env_vars = {}
    if not env_path.exists():
        print(f"ERROR: File {env_path} not found")
        return env_vars

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


def extract_defaults_from_docker_compose(compose_path: Path) -> Dict[str, str]:
    """Extract default env var values from docker-compose files."""
    defaults = {}
    if not compose_path.exists():
        return defaults

    with open(compose_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: ${VAR_NAME:-default_value}
    pattern = r'\$\{([A-Z_][A-Z0-9_]*):-(.*?)\}'
    matches = re.findall(pattern, content)

    for var_name, default_value in matches:
        defaults[var_name] = default_value

    return defaults


def extract_defaults_from_python(script_path: Path) -> Dict[str, str]:
    """Extract default env var values from Python scripts."""
    defaults = {}
    if not script_path.exists():
        return defaults

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: os.environ.get("VAR_NAME", "default_value")
    pattern = r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]*)["\'],\s*["\'](.*?)["\']\)'
    matches = re.findall(pattern, content)

    for var_name, default_value in matches:
        defaults[var_name] = default_value

    return defaults


def extract_hardcoded_values(file_path: Path, patterns: List[str]) -> Dict[str, str]:
    """Extract hardcoded values from config files."""
    values = {}
    if not file_path.exists():
        return values

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, tuple):
                values[match[0]] = match[1]
            else:
                values[pattern] = match

    return values


PLACEHOLDER_VALUES = frozenset(v.lower() for v in (
    '', 'CHANGE_ME', 'CHANGEME', '***CHANGEME***', 'changeme', 'DEFAULT', 'PASSWORD',
    'SECRET', 'ADMIN', '123456', 'QWERTY', 'PASSWORD123', '12345678', 'TOOR',
    'LETMEIN', 'XXX', 'FIXME', 'TODO', 'EXAMPLE', 'SAMPLE', 'TEST', 'TEST123',
    'NULL', 'NONE', 'N/A', 'NA', 'TBD', 'PLACEHOLDER', 'YOUR_PASSWORD_HERE',
    'INSERT_PASSWORD', 'REPLACE_ME',
))


def _looks_like_placeholder(value: str) -> bool:
    """Return True if the value is a known placeholder or weak secret."""
    return value.lower() in PLACEHOLDER_VALUES


def _sync_config_file(config_path: Path, env_vars: Dict[str, str]) -> List[str]:
    """Synchronize TheHive/Cortex config files with .env.full values.

    Returns a list of human-readable messages describing changes.
    """
    changes = []
    if not config_path.exists():
        return changes

    content = config_path.read_text(encoding='utf-8')
    original = content

    # Map each config file to the specific env vars it should use
    config_name = config_path.name
    if config_name == 'thehive.conf':
        file_mappings = [
            ('THEHIVE_SECRET', r'"play":\s*\{\s*"secret":\s*"([^"]+)"'),
        ]
    elif config_name == 'cortex.conf':
        file_mappings = [
            ('CORTEX_SECRET', r'"play":\s*\{\s*"secret":\s*"([^"]+)"'),
            ('ELASTIC_PASSWORD', r'"search":\s*\{[^}]*"password":\s*"([^"]+)"'),
        ]
    else:
        file_mappings = []

    for env_key, regex in file_mappings:
        if env_key not in env_vars:
            continue
        for match in re.finditer(regex, content):
            old_value = match.group(1)
            new_value = env_vars[env_key]
            if old_value != new_value:
                matched_text = match.group(0)
                new_text = matched_text.replace(f'"{old_value}"', f'"{new_value}"', 1)
                content = content.replace(matched_text, new_text, 1)
                changes.append(f"{config_path.name}: updated {env_key} value")

    if content != original:
        config_path.write_text(content, encoding='utf-8')

    return changes


def validate_credentials():
    """Validate that credentials are synchronized and not placeholders."""
    repo_root = Path(__file__).parent.parent.parent.parent
    env_full = repo_root / '.env.full'

    print("=== Credential Validation ===\n")

    # Parse .env.full
    env_vars = parse_env_file(env_full)
    if not env_vars:
        print("ERROR: Could not read .env.full")
        return False

    print(f"[OK] Read {len(env_vars)} variables from .env.full")

    # Files to validate
    docker_compose_files = [
        repo_root / 'infra' / 'docker' / 'compose' / 'docker-compose.core.yml',
        repo_root / 'infra' / 'docker' / 'compose' / 'docker-compose.misp.yml',
        repo_root / 'infra' / 'docker' / 'compose' / 'docker-compose.wazuh.yml',
        repo_root / 'infra' / 'docker' / 'compose' / 'docker-compose.api.yml',
        repo_root / 'infra' / 'docker' / 'compose' / 'logging' / 'docker-compose.logging.yml',
    ]

    python_scripts = [
        repo_root / 'src' / 'soar_lab' / 'scripts' / 'setup' / 'init_thehive.py',
        repo_root / 'src' / 'soar_lab' / 'scripts' / 'setup' / 'init_shuffle_webhook.py',
        repo_root / 'src' / 'soar_lab' / 'scripts' / 'setup' / 'fix_org_users.py',
        repo_root / 'src' / 'soar_lab' / 'scripts' / 'setup' / 'reset_cortex.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'external' / 'integrations' / 'cortex_client.py',
        repo_root / 'src' / 'soar_lab' / 'scripts' / 'setup' / 'setup_analyzers_and_iocs.py',
    ]

    config_files = [
        repo_root / 'infra' / 'docker' / 'thehive.application.conf' / 'thehive.conf',
        repo_root / 'infra' / 'docker' / 'cortex.application.conf' / 'cortex.conf',
    ]

    # Critical variables to validate
    critical_vars = [
        'ELASTIC_PASSWORD',
        'THEHIVE_SECRET',
        'THEHIVE_API_KEY',
        'CORTEX_SECRET',
        'CORTEX_API_KEY',
        'SHUFFLE_DEFAULT_PASSWORD',
        'SHUFFLE_DEFAULT_APIKEY',
        'SHUFFLE_PIPELINE_AUTH',
        'POSTGRES_PASSWORD',
        'REDIS_PASSWORD',
        'MISP_DB_ROOT_PASSWORD',
        'MISP_DB_PASSWORD',
        'MISP_ADMIN_PASSWORD',
        'MISP_ENCRYPTION_KEY',
        'MISP_SALT',
        'WAZUH_API_PASSWORD',
        'WAZUH_CLUSTER_KEY',
        'KIBANA_ENCRYPTION_KEY',
        'GRAFANA_ADMIN_PASSWORD',
        'GRAFANA_DB_PASSWORD',
        'WEB_UI_PASSWORD',
        'API_AUTH_SECRET',
        'SIEM_WEBHOOK_TOKEN',
        'EDR_SIM_TOKEN',
        'FIREWALL_SIM_TOKEN',
    ]

    errors = []
    warnings = []
    info = []

    # Validate .env.full values are not placeholders
    for var in critical_vars:
        if var in env_vars and _looks_like_placeholder(env_vars[var]):
            errors.append(f".env.full: {var} contains a placeholder or weak value")

    # Validate docker-compose files: env overrides default, so only warn on differences
    print("\n--- Validating docker-compose files ---")
    for compose_file in docker_compose_files:
        if not compose_file.exists():
            warnings.append(f"File not found: {compose_file}")
            continue

        defaults = extract_defaults_from_docker_compose(compose_file)
        print(f"  {compose_file.name}: {len(defaults)} defaults found")

        for var in critical_vars:
            if var in env_vars and var in defaults:
                if env_vars[var] != defaults[var]:
                    info.append(
                        f"{compose_file.name}: {var} - .env.full overrides default '{defaults[var]}'")

    # Validate Python scripts: env overrides default, so only warn on differences
    print("\n--- Validating Python scripts ---")
    for script in python_scripts:
        if not script.exists():
            warnings.append(f"File not found: {script}")
            continue

        defaults = extract_defaults_from_python(script)
        print(f"  {script.name}: {len(defaults)} defaults found")

        for var in critical_vars:
            if var in env_vars and var in defaults:
                if env_vars[var] != defaults[var]:
                    info.append(f"{script.name}: {var} - .env.full overrides default '{defaults[var]}'")

    # Validate and sync config files (hardcoded)
    print("\n--- Validating config files ---")
    for config_file in config_files:
        if not config_file.exists():
            warnings.append(f"File not found: {config_file}")
            continue
        changes = _sync_config_file(config_file, env_vars)
        for change in changes:
            info.append(change)

    # Report results
    print("\n=== Results ===")

    if info:
        print(f"\n[INFO] Informational ({len(info)}):")
        for msg in info:
            print(f"  - {msg}")

    if warnings:
        print(f"\n[WARNING] Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"\n[ERROR] Errors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        print("\n[FAIL] Validation failed: Credentials contain placeholders or are not synchronized")
        return False
    else:
        print("\n[OK] Validation successful: Credentials are valid and synchronized")
        return True


if __name__ == '__main__':
    success = validate_credentials()
    sys.exit(0 if success else 1)
