"""TC-28 — real in-browser axe-core WCAG audit (no host playwright needed).

Drives chromium + puppeteer inside a grafana-image-renderer sidecar on
soar_net (the image already ships both). The api reaches it through the
restricted docker proxy — same pattern as TC-37's netem injector. Owned
surfaces gate on critical/serious violations; vendor pages are audited but
only reported.
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

RENDERER_IMAGE = "grafana/grafana-image-renderer:3.10.4"
GATE_IMPACTS = {"critical", "serious"}

OWNED = {
    "web_management": "https://soar.local/",
    "api_portal": "http://api:8000/",
    "docs_site": "http://docs-site:8080/",
}
VENDOR = {
    "grafana": "http://grafana:3000/login",
    "thehive": "https://thehive:9443/index.html",
}


def _host_tests_path() -> str:
    """Resolve the HOST path mounted at /app/tests via the proxy."""
    r = subprocess.run(
        ["docker", "inspect", "soar_api", "--format", "{{json .Mounts}}"],
        capture_output=True, text=True, timeout=15,
    )
    mounts = json.loads(r.stdout)
    for m in mounts:
        if m.get("Destination") == "/app/tests":
            return m["Source"]
    raise RuntimeError("cannot resolve host tests mount")


def _run_axe(url: str, host_tests: str, timeout: int = 180) -> dict:
    cmd = [
        "docker", "run", "--rm",
        "--network", "soar_net",
        "--entrypoint", "node",
        "-v", f"{host_tests}:/x:ro",
        "-e", "CHROME_BIN=/usr/bin/chromium-browser",
        "-e", "NODE_PATH=/usr/src/app/node_modules",
        RENDERER_IMAGE,
        "/x/e2e/assets/axe_audit.js", url, "/x/e2e/assets/axe.min.js",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    for line in r.stdout.splitlines():
        if line.startswith("AXE_JSON:"):
            return json.loads(line[len("AXE_JSON:"):])
    return {"url": url, "error": f"no AXE_JSON (rc={r.returncode}): {r.stderr[:300]}"}


@pytest.mark.e2e
class TestAxeBrowserAudit:
    @pytest.fixture(scope="class")
    @classmethod
    def audits(cls):
        host_tests = _host_tests_path()
        results = {}
        for name, url in {**OWNED, **VENDOR}.items():
            results[name] = _run_axe(url, host_tests)
        return results

    def test_owned_pages_have_no_gate_violations(self, audits):
        failures = []
        for name in OWNED:
            res = audits.get(name, {})
            if res.get("error"):
                failures.append(f"{name}: audit error {res['error']}")
                continue
            for v in res.get("violations", []):
                if v.get("impact") in GATE_IMPACTS:
                    failures.append(f"{name}: {v['impact']} {v['id']} {v.get('nodes', [])[:3]}")
        assert not failures, "axe gate violations:\n" + "\n".join(failures[:20])

    def test_audit_renders_document(self, audits):
        """Every owned page must actually render (status<400, axe ran)."""
        for name in OWNED:
            res = audits.get(name, {})
            assert not res.get("error"), f"{name}: {res['error']}"
            assert res.get("status") is None or res["status"] < 400
            assert "violations" in res, f"{name}: axe did not run"

    def test_vendor_pages_audited_informational(self, audits):
        """Vendor UIs are audited for the report — their violations don't
        gate (we don't control their markup) but the audit must run."""
        reported = 0
        for name in VENDOR:
            res = audits.get(name, {})
            if res.get("error"):
                continue  # vendor page down is not a WCAG finding
            reported += 1
            n = len(res.get("violations", []))
            print(f"INFO vendor {name}: {n} violations (informational)")
        assert reported >= 1, "no vendor page could be audited at all"
