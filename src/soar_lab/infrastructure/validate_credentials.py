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


def validate_credentials():
    """Validate that credentials are synchronized."""
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
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'execute_workflow.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'setup' / 'init_thehive.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'setup' / 'init_shuffle_webhook.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'setup' / 'init_shuffle_webhook_wazuh.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'setup' / 'reset_cortex.py',
        repo_root / 'src' / 'soar_lab' / 'integrations' / 'cortex_client.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'setup' / 'setup_analyzers_and_iocs.py',
        repo_root / 'src' / 'soar_lab' / 'infrastructure' / 'diagnose_cortex_es.py',
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

    # Validate docker-compose files
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
                    errors.append(
                        f"{compose_file.name}: {var} - .env.full='{env_vars[var]}' vs default='{defaults[var]}'")

    # Validate Python scripts
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
                    errors.append(f"{script.name}: {var} - .env.full='{env_vars[var]}' vs default='{defaults[var]}'")

    # Validate config files (hardcoded)
    print("\n--- Validating config files ---")
    thehive_conf = repo_root / 'infra' / 'docker' / 'thehive.application.conf' / 'thehive.conf'
    cortex_conf = repo_root / 'infra' / 'docker' / 'cortex.application.conf' / 'cortex.conf'

    if thehive_conf.exists():
        with open(thehive_conf, 'r') as f:
            content = f.read()
            # Extract play.secret
            play_secret_match = re.search(r'"play":\s*\{\s*"secret":\s*"([^"]+)"', content)
            if play_secret_match:
                play_secret = play_secret_match.group(1)
                if 'THEHIVE_SECRET' in env_vars and env_vars['THEHIVE_SECRET'] != play_secret:
                    errors.append(
                        f"thehive.conf: play.secret - .env.full='{env_vars['THEHIVE_SECRET']}' vs hardcoded='{play_secret}'")

        # Extract search.password
        search_pass_match = re.search(r'"search":\s*\{[^}]*"password":\s*"([^"]+)"', content)
        if search_pass_match:
            search_pass = search_pass_match.group(1)
            if 'ELASTIC_PASSWORD' in env_vars and env_vars['ELASTIC_PASSWORD'] != search_pass:
                errors.append(
                    f"thehive.conf: search.password - .env.full='{env_vars['ELASTIC_PASSWORD']}' vs hardcoded='{search_pass}'")

    if cortex_conf.exists():
        with open(cortex_conf, 'r') as f:
            content = f.read()
            # Extract play.secret
            play_secret_match = re.search(r'"play":\s*\{\s*"secret":\s*"([^"]+)"', content)
            if play_secret_match:
                play_secret = play_secret_match.group(1)
                if 'CORTEX_SECRET' in env_vars and env_vars['CORTEX_SECRET'] != play_secret:
                    errors.append(
                        f"cortex.conf: play.secret - .env.full='{env_vars['CORTEX_SECRET']}' vs hardcoded='{play_secret}'")

        # Extract search.password
        search_pass_match = re.search(r'"search":\s*\{[^}]*"password":\s*"([^"]+)"', content)
        if search_pass_match:
            search_pass = search_pass_match.group(1)
            if 'ELASTIC_PASSWORD' in env_vars and env_vars['ELASTIC_PASSWORD'] != search_pass:
                errors.append(
                    f"cortex.conf: search.password - .env.full='{env_vars['ELASTIC_PASSWORD']}' vs hardcoded='{search_pass}'")

    # Report results
    print("\n=== Results ===")

    if warnings:
        print(f"\n[WARNING] Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"\n[ERROR] Errors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
        print("\n[FAIL] Validation failed: Credentials are not synchronized")
        return False
    else:
        print("\n[OK] Validation successful: All credentials are synchronized")
        return True


if __name__ == '__main__':
    success = validate_credentials()
    sys.exit(0 if success else 1)
