"""E2E fixture sanity — the fixtures feed real MISP/Cortex, so an invalid
IOC is silently dropped downstream (MISP discards a malformed sha256 at
event-creation time) and the workflow appears to "lose" IoCs. A 63-char
sha256 in ioc_samples.json caused exactly that in TC-01.
"""

import ipaddress
import json
import re
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent.parent / "e2e" / "fixtures" / "ioc_samples.json"

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _cases(data: dict) -> list[tuple[str, dict]]:
    entries = [("benign_reference", data.get("benign_reference", {}))]
    entries += [(c.get("name", "?"), c) for c in data.get("malicious_test_cases", [])]
    return entries


def test_fixture_hashes_are_valid_sha256():
    for name, case in _cases(_load()):
        h = case.get("hash")
        assert h is None or _SHA256_RE.match(
            h
        ), f"{name}: hash is not a valid 64-hex sha256 ({h!r})"


def test_fixture_ips_are_valid():
    for name, case in _cases(_load()):
        ip = case.get("ip")
        if ip:
            assert ipaddress.ip_address(ip), f"{name}: malformed fixture ip {ip}"


def test_malicious_cases_have_required_fields():
    data = _load()
    assert data.get("malicious_test_cases"), "fixture must define malicious_test_cases"
    for case in data["malicious_test_cases"]:
        for field in ("name", "hash", "ip", "domain"):
            assert case.get(field), f"{case.get('name')}: missing {field}"
