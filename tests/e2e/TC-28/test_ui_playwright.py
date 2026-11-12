#!/usr/bin/env python3
"""TC-28: Real browser UI tests via Playwright.

These tests actually render pages in Chromium — unlike test_ui_e2e.py,
which performs HTTP smoke checks only. Playwright + browser binaries are
installed on the host but not inside the api container image, so the whole
module skips honestly when the package is unavailable (the in-container
E2E profile reports SKIPPED, the host profile runs real E4 checks).

Run on the host:
    python -m pytest tests/e2e/TC-28/test_ui_playwright.py -v
"""

import importlib.util
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None

pytestmark = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed in this profile (host-only dependency)",
)

if PLAYWRIGHT_AVAILABLE:
    from playwright.sync_api import sync_playwright

from tests.e2e.base import E2EBaseTest


class TestUIPlaywright(E2EBaseTest):
    """TC-28-UI — navegación real en Chromium sobre las UIs desplegadas."""

    tc_id = "TC-28"

    BROWSER_TIMEOUT_MS = 30_000

    # Browsers always run on the host — never resolve container hostnames
    # (.env files carry in-network URLs like https://thehive:9443 which a
    # host-side browser cannot reach).
    _HOST_PORTS = {
        "shuffle_frontend": "http://localhost:8081",
        "thehive": "https://localhost:18100",
        "cortex": "https://localhost:18101",
        "misp": "http://localhost:8083",
        "grafana": "http://localhost:8084",
    }

    def _ui_url(self, service: str) -> str:
        return os.environ.get(f"E2E_UI_{service.upper()}_URL", self._HOST_PORTS[service])

    # Host-side UI probes: the base preflight resolves in-container
    # hostnames (thehive:9000, loki:3100, …) which are unreachable from a
    # host-side browser. The browser assertions below ARE the health
    # evidence, so the container-network preflight is bypassed here.
    def verify_core_services(self):
        pass

    def verify_workflow_ready(self):
        pass

    def verify_observability_stack(self):
        pass

    def assert_loki_ready(self):
        pass

    def assert_promtail_collecting(self):
        pass

    def assert_grafana_healthy(self):
        pass

    def collect_evidence(self):
        """Skip service-API evidence export — it targets in-container
        hostnames unreachable from the host. The browser assertions are
        the evidence; a screenshot is captured on failure instead."""
        if getattr(self, "_screenshot_path", None):
            self._log(f"screenshot: {self._screenshot_path}")

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)

    def teardown_method(self, method):
        try:
            self._browser.close()
        finally:
            self._pw.stop()
        super().teardown_method(method)

    def _new_page(self):
        context = self._browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.set_default_timeout(self.BROWSER_TIMEOUT_MS)
        return context, page

    # ------------------------------------------------------------------

    def test_shuffle_frontend_renders(self):
        """La UI de Shuffle carga y renderiza contenido real (no 5xx/white page)."""
        url = self._ui_url("shuffle_frontend")
        context, page = self._new_page()
        try:
            # `/` is a logged-out marketing landing (no login fields);
            # the credential form lives on the /login SPA route.
            response = page.goto(f"{url}/login", wait_until="domcontentloaded")
            assert response is not None, "no response from shuffle frontend"
            assert response.status == 200, f"Shuffle /login returned HTTP {response.status}"
            assert "shuffle" in page.title().lower(), f"Page title is not Shuffle: {page.title()!r}"
            # The SPA must mount a real login form — not a blank body.
            # Wait for the field itself (React mounts after first paint;
            # networkidle can fire before hydration completes).
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
                netidle_err = None
            except Exception as e:
                # continuous background traffic; field wait below is the oracle
                netidle_err = e
            if netidle_err is not None:
                self._log(f"networkidle not reached: {netidle_err}")
            password_input = page.locator("input[type='password']").first
            password_input.wait_for(state="visible", timeout=20_000)
            assert (
                page.locator("input").count() >= 2
            ), "Shuffle /login must render user + password inputs"
        finally:
            context.close()

    def test_thehive_login_page_renders(self):
        """TheHive sirve una página de login con campos de credenciales."""
        url = self._ui_url("thehive")
        context, page = self._new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded")
            assert response is not None and response.status == 200
            page.wait_for_load_state("networkidle", timeout=20_000)
            # TheHive 5 login: username + password inputs (AngularJS app).
            inputs = page.locator("input")
            assert inputs.count() >= 2, (
                f"TheHive login page rendered {inputs.count()} inputs, "
                "expected a credential form"
            )
            password_inputs = page.locator("input[type='password']")
            assert password_inputs.count() >= 1, (
                "TheHive login page has no password input — the login " "form did not render"
            )
        finally:
            context.close()

    def test_grafana_kpi_dashboard_renders_panels(self):
        """Login real en Grafana + dashboard provisionado renderiza paneles.

        E4: demuestra que el dashboard `soar-kpi-main` (15 paneles KPI) no
        solo existe vía API sino que se renderiza en un navegador real.
        """
        url = self._ui_url("grafana")
        user = self.env.get("GRAFANA_ADMIN_USER", "admin")
        password = self.env.get("GRAFANA_ADMIN_PASSWORD", "")
        assert password, "GRAFANA_ADMIN_PASSWORD missing — cannot login"

        context, page = self._new_page()
        try:
            page.goto(f"{url}/login", wait_until="domcontentloaded")
            # Grafana login form (name selectors are stable across versions).
            page.locator("input[name='user']").fill(user)
            page.locator("input[name='password']").fill(password)
            page.locator("button[type='submit']").click()
            # Login must succeed — landing page shows the sidemenu/home.
            page.wait_for_url(lambda u: "/login" not in u, timeout=20_000)

            page.goto(f"{url}/d/soar-kpi-main", wait_until="domcontentloaded")
            # Panel titles render as text in the DOM (react-grid layout).
            expected_panels = [
                "Total Alerts Processed",
                "MTTR p50",
            ]
            for title in expected_panels:
                page.locator(f"text={title}").first.wait_for(state="visible", timeout=20_000)
            panels = page.locator("[class*='react-grid-item']")
            assert panels.count() >= 10, (
                f"Dashboard rendered {panels.count()} panels, "
                "expected the 15-panel KPI dashboard"
            )
        finally:
            context.close()

    def test_cortex_ui_renders(self):
        """Cortex sirve su UI (login page) — no un error HTTP ni página vacía."""
        url = self._ui_url("cortex")
        context, page = self._new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded")
            assert response is not None and response.status == 200
            page.wait_for_load_state("networkidle", timeout=20_000)
            body_text = page.locator("body").inner_text(timeout=15_000)
            has_inputs = page.locator("input").count() >= 1
            assert has_inputs or "cortex" in body_text.lower(), (
                "Cortex UI rendered neither inputs nor branding. "
                f"Body starts: {body_text[:200]!r}"
            )
        finally:
            context.close()
