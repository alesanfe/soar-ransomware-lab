#!/usr/bin/env python3
"""TC-28-A11Y: WCAG 2.1 A/AA accessibility audit of every UI surface.

Injects vendored ``axe-core`` (``tests/e2e/assets/axe.min.js``) into each
page already navigated by the TC-28 suite and runs the WCAG 2.0/2.1 A+AA
rule set. Results land in ``reports/a11y/``.

Two-tier oracle:

* **Owned UIs** (web-management console, API portal, docs-site) — the
  code lives in this repo, so violations are fixable and gate the run:
  any ``critical`` or ``serious`` violation fails the test.
* **Vendor UIs** (Shuffle, Grafana, TheHive, Cortex, MISP, OSD) — scanned
  and reported for visibility, but their violations are informational:
  third-party frontends cannot be patched from this repo.

Run on the host (same profile as the screenshot suite):
    python -m pytest tests/e2e/TC-28/test_ui_a11y.py -v -c pytest.ini --no-cov
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None

pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed in this profile (host-only dependency)",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
AXE_PATH = REPO_ROOT / "tests" / "e2e" / "assets" / "axe.min.js"
A11Y_DIR = REPO_ROOT / "reports" / "a11y"

# Reuse the sibling test class (logins, page factory, port map) — TC-28's
# directory name is not a valid Python identifier so import by path.
_sib_spec = importlib.util.spec_from_file_location(
    "tc28_screenshots",
    Path(__file__).parent / "test_ui_screenshots.py",
)
_sib = importlib.util.module_from_spec(_sib_spec)
sys.modules.setdefault("tc28_screenshots", _sib)
_sib_spec.loader.exec_module(_sib)
TestUIScreenshots = _sib.TestUIScreenshots

_WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
_GATE_IMPACTS = {"critical", "serious"}


class TestUIAccessibility(TestUIScreenshots):
    """axe-core WCAG audit — owned UIs gate, vendor UIs informational."""

    def _new_page(self):
        # bypass_csp: axe injects as an inline script, which our own strict
        # CSPs (script-src 'self', api portal's default-src 'none') rightly
        # block. The CSP posture is asserted by the hardening regression
        # tests — this context exists only to run the audit tool.
        context = self._browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
            bypass_csp=True,
        )
        page = context.new_page()
        page.set_default_timeout(self.BROWSER_TIMEOUT_MS)
        return context, page

    # (service key, report name, path) — owned surfaces gate the run.
    _OWNED_PAGES = [
        ("nginx", "web_management", "/"),
        ("api_swagger", "api_portal", "/"),
        ("docs_site", "docs_home", "/"),
        ("docs_site", "docs_getting_started", "/docs/getting-started"),
        ("docs_site", "docs_architecture", "/docs/architecture/overview"),
    ]
    _VENDOR_PAGES = [
        ("shuffle_frontend", "shuffle_workflows", "/workflows"),
        ("grafana", "grafana_dashboards", "/dashboards"),
        ("thehive", "thehive_cases", "/index.html#/case/list"),
        ("cortex", "cortex_jobs", "/index.html#/jobs"),
        ("misp", "misp_events", "/events/index"),
        ("opensearch_dashboards", "osd_home", "/app/home"),
    ]
    _LOGINS = {}  # filled in test body — bound methods

    def _run_axe(self, page) -> dict:
        """Inject axe and return the raw results dict."""
        page.add_script_tag(path=str(AXE_PATH))
        return page.evaluate(
            "() => axe.run(document, {runOnly: {type: 'tag', values: "
            + json.dumps(_WCAG_TAGS)
            + "}, resultTypes: ['violations', 'incomplete']})"
        )

    def _scan(self, service, name, path, page, results):
        base = self._ui_url(service)
        entry = {"service": service, "url": base + path}
        try:
            r = page.goto(base + path, wait_until="domcontentloaded", timeout=60_000)
            entry["status"] = r.status if r else None
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass  # collect-then-report: long-poll pages never go idle
            page.wait_for_timeout(self.SETTLE_MS)
            axe = self._run_axe(page)
            violations = [
                {
                    "id": v["id"],
                    "impact": v.get("impact"),
                    "help": v.get("help"),
                    "nodes": [n.get("target") for n in v.get("nodes", [])][:10],
                }
                for v in axe.get("violations", [])
            ]
            entry["violations"] = violations
            entry["gate_failures"] = [v for v in violations if v.get("impact") in _GATE_IMPACTS]
        except Exception as e:  # collect-then-report: audit every page
            entry["error"] = f"{type(e).__name__}: {str(e)[:150]}"
        results[name] = entry
        return entry

    def test_wcag_aa_audit(self):
        A11Y_DIR.mkdir(parents=True, exist_ok=True)
        results = {"checked_at": datetime.now(UTC).isoformat(), "pages": {}}
        gate_failures = []

        logins = {
            "nginx": self._login_web_management,
            "grafana": self._login_grafana,
            "thehive": self._login_thehive,
            "cortex": self._login_cortex,
            "shuffle_frontend": self._login_shuffle,
            "misp": self._login_misp,
        }

        contexts = {}

        def ctx_for(service):
            if service not in contexts:
                context, page = self._new_page()
                contexts[service] = (context, page)
                if service in logins:
                    try:
                        entry_url = self._ui_url(service).rsplit("/", 1)[0] + "/"
                        page.goto(entry_url, wait_until="domcontentloaded", timeout=60_000)
                        logins[service](page, entry_url)
                    except Exception as e:  # collect-then-report
                        results["pages"][service + "__login"] = {"auth_error": str(e)[:200]}
            return contexts[service][1]

        try:
            for service, name, path in self._OWNED_PAGES:
                entry = self._scan(service, name, path, ctx_for(service), results["pages"])
                if entry.get("error"):
                    # An owned page that could not be scanned is a gate
                    # failure — otherwise a broken scan would pass silently.
                    gate_failures.append(f"{name}: scan error — {entry['error']}")
                for v in entry.get("gate_failures", []):
                    gate_failures.append(f"{name}: [{v['impact']}] {v['id']} — {v['help']}")

            for service, name, path in self._VENDOR_PAGES:
                self._scan(service, name, path, ctx_for(service), results["pages"])
        finally:
            for context, _ in contexts.values():
                context.close()

        # Vendor summary: informational, never gates.
        results["summary"] = {
            name: {
                "violations": len(e.get("violations", [])),
                "gate_failures": len(e.get("gate_failures", [])),
                "owned": any(n == name for _, n, _ in self._OWNED_PAGES),
            }
            for name, e in results["pages"].items()
        }
        (A11Y_DIR / "summary.json").write_text(json.dumps(results, indent=2, default=str))
        for name, entry in results["pages"].items():
            self._log(
                f"{name}: violations={len(entry.get('violations', []))} "
                f"gate={len(entry.get('gate_failures', []))} err={entry.get('error', '-')}"
            )
        assert (
            not gate_failures
        ), "WCAG A/AA critical/serious violations on owned UIs:\n" + "\n".join(gate_failures)
