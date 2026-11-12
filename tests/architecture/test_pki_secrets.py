"""Architecture gates — PKI and secret management (eval 38).

Static invariants for the lab CA / gen_certs.sh / secret tooling so the
properties documented in ``docs/38-eval-pki-secrets.md`` cannot silently
regress: proper CA extensions, issuer-scoped --verify, CSPRNG secrets,
cert-expiry monitoring coverage and Makefile target parity.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN_CERTS = ROOT / "scripts" / "setup" / "gen_certs.sh"
SECRET_GEN = ROOT / "src" / "soar_lab" / "security" / "secret_generator.py"
ROTATE = ROOT / "scripts" / "setup" / "rotate_secrets.py"
INVENTORY = ROOT / "scripts" / "audit" / "inventory_secrets.py"
BLACKBOX = ROOT / "infra" / "docker" / "config" / "blackbox.yml"
PROMETHEUS = ROOT / "infra" / "docker" / "config" / "prometheus.yml"
MAKE_WIN = ROOT / "Makefile.win"
MAKE_LINUX = ROOT / "Makefile.linux"
COMPOSE = ROOT / "infra" / "docker" / "compose"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --- CA / cert generation --------------------------------------------------

def test_ca_is_idempotent_reuse():
    src = _read(GEN_CERTS)
    assert "CA already exists" in src and "reusing" in src.lower()


def test_server_certs_have_san_and_eku():
    src = _read(GEN_CERTS)
    assert "subjectAltName" in src and "extendedKeyUsage = serverAuth" in src
    assert "keyUsage = digitalSignature" in src


def test_client_certs_use_clientauth_eku():
    src = _read(GEN_CERTS)
    assert "extendedKeyUsage = clientAuth" in src


def test_verify_filters_foreign_bundles():
    # --verify must only check certs issued BY the lab CA — public-CA
    # bundles in the same dir made it fail unconditionally (PKI-EVAL-002).
    src = _read(GEN_CERTS)
    body = src.split("verify_certificates()", 1)[1].split("\n}\n", 1)[0]
    assert "issuer" in body and "ca_subject" in body and "not issued by lab CA" in body


def test_generated_keys_are_600():
    src = _read(GEN_CERTS)
    assert src.count("chmod 600") >= 2


def test_env_example_has_no_real_secrets():
    # The committed example must hold placeholders, not real values —
    # the primary leak vector for env files (PKI-EVAL-003). Project
    # convention: placeholder secrets embed the variable name
    # (``ElasticLab2024SecurePass`` for ``ELASTIC_PASSWORD``); a real
    # generated secret never contains the var name, so a ≥24-char
    # literal unrelated to its key is flagged as a possible leak.
    placeholder_words = ("example", "changeme", "replace", "your-", "generate", "placeholder")
    config_suffixes = ("_URL", "_HOST", "_ENDPOINT", "_DIR", "_FILE", "_IMAGE", "_PORT")
    src = _read(ROOT / ".env.example")
    for line in src.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        k = key.strip().upper()
        if not val or val.startswith("${"):
            continue
        if any(w in val.lower() for w in placeholder_words):
            continue
        if k.endswith(config_suffixes) or "://" in val:
            continue  # URLs / paths / image refs are not secrets
        if len(val) < 24:
            continue  # short literals like "admin" are fine
        # ≥24 chars: must be self-describing (embed a key-name token) or
        # it looks like a committed real secret.
        tokens = [t for t in re.split(r"[_\-]", k) if len(t) >= 4]
        if not any(t.lower() in val.lower() for t in tokens):
            raise AssertionError(f"{key.strip()} looks like a real secret in .env.example")


def test_mounted_private_keys_are_read_only():
    # Any *.key bind-mounted into a container must be :ro — a writable
    # mount lets a compromised service rewrite PKI material on the host.
    for f in COMPOSE.rglob("*.yml"):
        for line in _read(f).splitlines():
            if ".key:" in line or ".key:" in line.replace(" ", ""):
                target = line.split(":")[-1].strip()
                assert "ro" in target.split(",") or line.rstrip().endswith(":ro"), (
                    f"writable key mount in {f.name}: {line.strip()}"
                )


def test_ca_key_never_mounted_into_containers():
    # The CA private key must stay on the host — only ca.crt is mountable.
    for f in COMPOSE.rglob("*.yml"):
        src = _read(f)
        for line in src.splitlines():
            if "ca.key" in line and not line.strip().startswith("#"):
                raise AssertionError(f"ca.key mounted in {f.name}")


# --- secret generation / rotation -----------------------------------------

def test_secret_generator_uses_csprng():
    src = _read(SECRET_GEN)
    assert "import secrets" in src
    assert "random.random" not in src and "random.choice" not in src


def test_rotation_script_exists_and_never_prints_secrets():
    src = _read(ROTATE)
    assert "rotate" in src and "NEEDS-MANUAL" in src
    assert "Never prints secret values" in src


def test_secret_inventory_exists():
    src = _read(INVENTORY)
    assert "REAL" in src and "SYNTHETIC" in src and "PLACEHOLDER" in src


# --- cert-expiry monitoring -------------------------------------------------

def test_tls_probe_module_exists():
    src = _read(BLACKBOX)
    assert "tcp_tls" in src and "tls: true" in src and "min_version: TLS12" in src


def test_all_tls_services_probed_for_expiry():
    src = _read(PROMETHEUS)
    tls_job = src.split("job_name: blackbox-tls", 1)[1].split("- job_name", 1)[0]
    for target in ("opensearch:9200", "elasticsearch:9200", "redis:6379",
                   "shuffle-backend:5443", "tenzir-node:5160"):
        assert target in tls_job, target


def test_tls_endpoints_not_plain_tcp_probed():
    # A TLS listener must be probed with a handshake, not a bare connect —
    # a broken TLS stack would pass plain TCP.
    src = _read(PROMETHEUS)
    tcp_job = src.split("job_name: blackbox-tcp", 1)[1].split("- job_name", 1)[0]
    for target in ("redis:6379", "shuffle-backend:5443", "opensearch:9200",
                   "elasticsearch:9200", "tenzir-node:5160"):
        assert target not in tcp_job, target


# --- Makefile parity --------------------------------------------------------

def _targets(src: str) -> set[str]:
    return set(re.findall(r"^([a-zA-Z][\w-]*):", src, re.M))


def test_pki_targets_exist_both_makefiles():
    for mk in (MAKE_WIN, MAKE_LINUX):
        names = _targets(_read(mk))
        for t in ("verify-certs", "rotate-secrets", "secrets-inventory"):
            assert t in names, f"{mk.name} missing {t}"


def test_makefile_win_certs_covers_internal_ca():
    src = _read(MAKE_WIN)
    certs = src.split("\ncerts:", 1)[1].split("\n# ", 1)[0]
    assert "config/certs" in certs and "misp" in certs and "misp-full.pem" in certs


# --- PKI-EVAL-2 (eval 58): rotation audit + env-file hygiene ----------------

def test_rotation_writes_persistent_audit_record():
    # ISO 27001 A.8.15 / OWASP secrets-management: rotations must leave a
    # tamper-evident trail (names only, never values) — stdout alone is lost.
    src = _read(ROTATE)
    assert "secrets-rotation.audit.jsonl" in src and "write_audit_record" in src
    assert '"vars"' in src and "json.dumps" in src


def test_env_files_chmod_600_after_write():
    # Env files hold real secrets; POSIX hosts must not leave them at the
    # default umask (group/world-readable). Best-effort chmod is the fix.
    src = _read(ROOT / "scripts" / "setup" / "env_files.py")
    assert "os.chmod" in src and "0o600" in src


def _tracked_files() -> list[str] | None:
    """Tracked paths via ``git ls-files``; falls back to parsing the
    ``.git/index`` (DIRC v2/v3) so the gate also runs where git is not
    installed. Returns ``None`` when neither source exists (container
    without the .git mount)."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        return out.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    import struct

    index = ROOT / ".git" / "index"
    if not index.exists():
        return None
    data = index.read_bytes()
    assert data[:4] == b"DIRC", "unsupported git index"
    _version, count = struct.unpack(">II", data[4:12])
    pos, paths = 12, []
    for _ in range(count):
        entry_start = pos
        flags = struct.unpack(">H", data[pos + 60 : pos + 62])[0]
        namelen = flags & 0xFFF
        pos += 62
        end = data.index(b"\x00", pos) if namelen == 0xFFF else pos + namelen
        paths.append(data[pos:end].decode())
        pos = entry_start + ((end - entry_start + 8) // 8) * 8
    return paths


def test_no_new_env_files_tracked():
    # Accepted lab debt (eval 58): .env.full/.env.testing were committed and
    # pushed to GitHub before the .gitignore rule — secrets protect a local
    # lab only, rotation is the documented remediation. This gate pins the
    # blast radius: NO NEW secret-bearing file may become tracked.
    tracked = _tracked_files()
    if tracked is None:
        import pytest

        pytest.skip("no git / .git index available (enforced in CI)")
    env_files = {
        f for f in _tracked_files()
        if re.fullmatch(r"\.env[\w.-]*", f) or f.endswith((".env", ".env.local"))
    }
    assert env_files <= {".env.example", ".env.full", ".env.testing"}, (
        f"new secret-bearing file(s) tracked: "
        f"{sorted(env_files - {'.env.example', '.env.full', '.env.testing'})}"
    )
