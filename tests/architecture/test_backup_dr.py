#!/usr/bin/env python3
"""Static validators for the backup/DR system (DR-EVAL-*).

Pins the bugs found live during the backup/DR evaluation into permanent
gates:

- DR-EVAL-001: ``soar_es_data`` and ``soar_opensearch_data`` had ZERO
  backup coverage — the SIEM alert corpus and the Shuffle
  environments/executions indexes were unrecoverable.
- DR-EVAL-002: ``runtime/data/api/soar_data.db`` (SqliteAlertRepository)
  lives on a HOST bind mount — invisible to both volume backup scripts
  and excluded from the API codebase archive (``--exclude=runtime``).
- DR-EVAL-003: ``misp_logs`` was in the core MARKERS map but never in
  NAMED_VOLUMES — dead config hiding missing forensic-log coverage.
- DR-EVAL-004: no retention — runtime/backups grew unboundedly
  (814MB observed: core 464 + obs 209 + legacy 141).
- DR-EVAL-005: obs script was weaker than core — no SHA256SUMS, no
  MANIFEST, no archive-vs-restored file-count check; a silently corrupted
  archive could pass the drill.
- DR-EVAL-006: archives were PLAINTEXT tar.gz — grafana.db, MISP configs
  and TheHive volumes carry credential-adjacent data. Archives are now
  AES-256-CBC encrypted (PBKDF2 600k) requiring BACKUP_PASSPHRASE, and
  drills decrypt into a mktemp scratch dir — never back into the set.
- DR-EVAL-007: no periodic pipeline exercise — CI's backup-test only
  imported a class. BACKUP_VOLUMES now overrides the volume list so CI
  runs a real synthetic encrypt→drill cycle on every pipeline.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_DIR = ROOT / "infra/docker/compose"
CORE_SH = ROOT / "scripts/maintenance/backup_core_stack.sh"
OBS_SH = ROOT / "scripts/maintenance/backup_obs_stack.sh"
API_DRIVER = ROOT / "src/soar_lab/infrastructure/tar_backup_driver.py"

# Stateful volumes declared in compose files that are deliberately NOT
# archived, with justification (evaluated 2026-11-11):
EXEMPT = {
    "nginx_logs": "nginx access/error logs — already shipped to Loki "
    "(loki_data is backed up); backing them up twice adds no fidelity",
}

# Volumes resolved live (anonymous): tenzir lib/cache are resolved from
# container mounts by the core script; the cortex DinD anon volume and
# the s3-init one-shot volume carry only regenerable state.


@pytest.fixture(scope="module")
def core_script() -> str:
    return CORE_SH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def obs_script() -> str:
    return OBS_SH.read_text(encoding="utf-8")


class _ComposeLoader(yaml.SafeLoader):
    """Compose-spec tags used by the hardened overlay (`!override`/`!reset`)."""


_ComposeLoader.add_constructor(
    "!override",
    lambda loader, node: loader.construct_sequence(node)
    if isinstance(node, yaml.SequenceNode)
    else loader.construct_mapping(node),
)
_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def _declared_volumes() -> set[str]:
    vols: set[str] = set()
    for f in COMPOSE_DIR.rglob("docker-compose*.yml"):
        data = yaml.load(f.read_text(encoding="utf-8"), Loader=_ComposeLoader) or {}
        vols.update((data.get("volumes") or {}).keys())
    return vols


def test_every_declared_volume_is_covered_or_exempt():
    """The backup scripts must name every stateful volume the composes
    declare — anything else is silently unrecoverable."""
    core = CORE_SH.read_text(encoding="utf-8")
    obs = OBS_SH.read_text(encoding="utf-8")
    uncovered = []
    for vol in sorted(_declared_volumes() - set(EXEMPT)):
        if vol not in core and vol not in obs:
            uncovered.append(vol)
    assert not uncovered, f"volumes with no backup coverage: {uncovered}"


def test_es_and_opensearch_data_covered(core_script):
    """DR-EVAL-001 regression pin."""
    named = re.search(r"NAMED_VOLUMES=\(([^)]*)\)", core_script).group(1)
    assert "es_data" in named
    assert "opensearch_data" in named


def test_api_sqlite_host_dir_covered(core_script):
    """DR-EVAL-002: soar_data.db lives on a host bind — must be an
    explicit HOST_DIRS entry."""
    assert "runtime/data/api" in core_script
    assert "HOST_DIRS" in core_script


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_script_writes_sha256sums(script, request):
    text = request.getfixturevalue(script)
    assert "SHA256SUMS" in text
    assert "sha256sum" in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_drill_verifies_sha256(script, request):
    assert "sha256sum -c" in request.getfixturevalue(script)


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_script_writes_manifest(script, request):
    assert "MANIFEST.txt" in request.getfixturevalue(script)


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_drill_checks_restored_file_counts(script, request):
    """Archive member count must equal restored file count — marker-only
    checks pass on truncated restores."""
    text = request.getfixturevalue(script)
    assert '"$total" -ne "$expected"' in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_script_enforces_retention(script, request):
    """DR-EVAL-004: backup sets must be pruned to BACKUP_KEEP newest."""
    text = request.getfixturevalue(script)
    assert "BACKUP_KEEP" in text
    assert "prune_old" in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_script_fails_closed(script, request):
    assert "set -euo pipefail" in request.getfixturevalue(script)


def test_api_driver_excludes_secret_material():
    """P0.3 posture pin: the codebase archive must never embed secrets."""
    text = API_DRIVER.read_text(encoding="utf-8")
    for pat in (".env", ".env.*", "*.pem", "*.key", "*.crt", "secrets"):
        assert pat in text, f"secret exclusion missing: {pat}"
    assert ".sha256" in text, "archives need an integrity sidecar"
    assert "self.verify" in text or "def verify" in text


# ---------------------------------------------------------------------------
# DR-EVAL-006 — encrypted at rest, fail-closed passphrase
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_archives_encrypted_aes256(script, request):
    text = request.getfixturevalue(script)
    assert "openssl enc -aes-256-cbc" in text
    assert "-pbkdf2" in text
    assert ".tar.gz.enc" in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_passphrase_required_fail_closed(script, request):
    """Without BACKUP_PASSPHRASE the script must exit — never silently
    write a plaintext backup."""
    text = request.getfixturevalue(script)
    assert "require_pass" in text
    assert "BACKUP_PASSPHRASE" in text
    assert "export BACKUP_PASSPHRASE" in text, "openssl -pass env: needs the export"


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_passphrase_loaded_from_env_files(script, request):
    text = request.getfixturevalue(script)
    assert ".env.full" in text and ".env" in text
    assert "grep -E '^BACKUP_PASSPHRASE='" in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_drill_decrypts_to_scratch_tmpdir(script, request):
    """Decrypted payloads must land in a mktemp dir — the backup set
    itself must stay ciphertext at rest."""
    text = request.getfixturevalue(script)
    assert "mktemp -d" in text
    assert "decrypt_one" in text
    assert 'trap ' in text


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_no_plaintext_archive_persisted(script, request):
    """After backup_one runs, only .tar.gz.enc may remain — the plaintext
    tarball must be removed."""
    text = request.getfixturevalue(script)
    assert 'rm -f "$1"' in text


# ---------------------------------------------------------------------------
# DR-EVAL-007 — periodic pipeline exercise (CI synthetic drill)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", ["core_script", "obs_script"])
def test_volume_list_overridable_for_ci(script, request):
    assert "BACKUP_VOLUMES" in request.getfixturevalue(script)


def test_ci_exercises_drill_pipeline():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "dr-drill" in ci
    assert "backup_obs_stack.sh backup" in ci
    assert "backup_obs_stack.sh drill" in ci
    assert "docker volume create" in ci


def test_env_example_documents_backup_passphrase():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "BACKUP_PASSPHRASE" in env_example
