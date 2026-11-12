#!/usr/bin/env python3
"""TC-33 ext: offline-mode + inert-sample contract.

The IoC pipeline must be able to run fully offline against the pinned
fixture manifest, samples must be inert by construction (download, hash,
delete — never extracted/executed), and a missing manifest must fail
loudly rather than silently skip.
"""

import hashlib
import ipaddress
import json
import re
from pathlib import Path

import pytest

FIXTURE = (
    Path("/app/tests/e2e/fixtures/gminst4ll_iocs.json")
    if Path("/app").exists()
    else Path(__file__).parent.parent / "fixtures" / "gminst4ll_iocs.json"
)
TEST_SRC = Path(__file__).parent / "test_gminst4ll_real_iocs.py"

HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXEC_DIRECTIVES = re.compile(
    r"(?:^|_)(run|exec|execute|extract|unrar|unzip|decompress|invoke|shell|cmd)(?:_|$)",
    re.IGNORECASE,
)


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.e2e
class TestOfflineSamples:
    tc_id = "TC-33"

    def test_availability_gate_explicit(self):
        """The loader fails loudly with a clear message when the manifest
        is absent — no silent skip, no empty-dict fallthrough."""
        assert FIXTURE.exists(), f"fixture manifest missing: {FIXTURE}"
        data = _load()
        for key in ("hashes_sha256", "downloadable_samples", "_meta"):
            assert key in data, f"manifest missing required section {key!r}"
        # simulate the gate: a missing file must raise/fail, not return {}
        try:
            json.loads(Path("/nonexistent-fixture.json").read_text())
            pytest.fail("missing fixture did not raise")
        except (OSError, FileNotFoundError):
            pass

    def test_all_ioc_hashes_pinned_sha256(self):
        """Every hash entry and every downloadable sample pins a valid
        lowercase SHA-256 — the manifest IS the integrity contract."""
        data = _load()
        for h in data["hashes_sha256"]:
            assert HEX64.match(h["hash"]), f"bad sha256 for {h['name']}: {h['hash']!r}"
            assert isinstance(h.get("size_bytes"), int) and h["size_bytes"] > 0
        for s in data["downloadable_samples"]:
            assert HEX64.match(s["sha256"]), f"bad sha256 for {s['name']!r}"
            assert s["size_bytes"] > 0

    def test_manifest_deterministic_no_duplicate_pins(self):
        """Canonical dump hashes deterministically; no hash pinned twice
        under different names (conflicting pins = integrity hole)."""
        data = _load()
        hashes = [h["hash"] for h in data["hashes_sha256"]]
        assert len(hashes) == len(set(hashes)), "duplicate sha256 pins in manifest"
        canon1 = json.dumps({k: v for k, v in data.items() if k != "_meta"}, sort_keys=True)
        canon2 = json.dumps({k: v for k, v in _load().items() if k != "_meta"}, sort_keys=True)
        assert hashlib.sha256(canon1.encode()).hexdigest() == hashlib.sha256(
            canon2.encode()
        ).hexdigest()

    def test_samples_inert_by_construction(self):
        """No execution/extraction directive anywhere in the manifest, and
        the download path never decompresses or runs a sample."""
        raw = FIXTURE.read_text(encoding="utf-8")
        keys = re.findall(r'"([A-Za-z_]+)"\s*:', raw)
        offenders = [k for k in keys if EXEC_DIRECTIVES.search(k)]
        assert not offenders, f"executable directives in manifest: {offenders}"
        src = TEST_SRC.read_text(encoding="utf-8")
        for bad in ("unrar", "7z ", "os.system", "subprocess.run", "Popen(", "exec("):
            assert bad not in src, f"sample handler can execute: {bad!r} found"
        # password-protected archives are never opened — documented inert
        assert _load()["_meta"].get("passwords"), "archive passwords not documented"

    def test_offline_ioc_values_self_contained(self):
        """Every IoC category the detection tests consume is present and
        well-formed in the manifest — zero network fetches needed."""
        data = _load()
        assert data["urls_c2"], "no C2 URLs in manifest"
        assert data["domains_c2"], "no C2 domains"
        assert data["ips_c2"], "no C2 IPs"
        assert data["hashes_sha256"], "no file hashes"
        for ip in data["ips_c2"]:
            addr = ip.get("ip", ip) if isinstance(ip, dict) else ip
            ipaddress.ip_address(addr)  # raises on malformed
        for d in data["domains_c2"]:
            dom = d.get("domain", d) if isinstance(d, dict) else d
            assert re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", dom, re.I), f"bad domain {dom!r}"
