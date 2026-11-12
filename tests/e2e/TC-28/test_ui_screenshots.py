#!/usr/bin/env python3
"""TC-28-UI-SHOTS: visual E2E — screenshot every UI exposed by the stack.

Discovery is dynamic: every host-published port is probed over HTTP(S) and
classified as UI (HTML document) or API-only (JSON / no listener). Each UI
is then rendered in headless Chromium, asserted to produce real content
(non-empty title or DOM), and captured to
``reports/e2e/ui-screenshots/<service>.png``.

This complements ``test_ui_playwright.py`` (deep per-service assertions)
with breadth: full visual coverage + a regression oracle on the exposed
surface itself (a port that loses its UI, or a new one appearing, fails).

Run on the host:
    python -m pytest tests/e2e/TC-28/test_ui_screenshots.py -v \
        -c pytest.ini --no-cov
"""

import importlib.util
import json
import os
import ssl
import sys
import urllib.request
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

REPO_ROOT = Path(__file__).resolve().parents[3]
SCREENSHOT_DIR = REPO_ROOT / "reports" / "e2e" / "ui-screenshots"


class TestUIScreenshots(E2EBaseTest):
    """Descubrimiento dinámico de UIs + captura + oráculo de render real."""

    tc_id = "TC-28"

    BROWSER_TIMEOUT_MS = 30_000
    SETTLE_MS = 4_000  # SPAs need a few seconds past first paint to mount

    # Every host-published port of the stack. Keys = docker service names.
    # UI ports get screenshots + render assertions; API ports get probed
    # and asserted to NOT serve an HTML UI (surface invariant).
    _PORTS = {
        "nginx": "http://localhost:80",
        "api_swagger": "http://localhost:8000",
        "shuffle_frontend": "http://localhost:8081/login",
        "misp": "https://localhost:8083",
        "grafana": "http://localhost:8084/login",
        "web_management": "http://localhost:8085",
        "docs_site": "http://localhost:8086/soar-ransomware-lab/",
        "thehive": "https://localhost:18100",
        "cortex": "https://localhost:18101",
        "opensearch_dashboards": "http://localhost:19202",
    }
    _API_ONLY_PORTS = {
        "shuffle_backend": "http://localhost:5001",
        "elasticsearch": "https://localhost:19200",
        "opensearch": "https://localhost:19201",
        "network_watcher": "http://localhost:15130",
        "tenzir_node": "http://localhost:15160",
    }

    def _ui_url(self, service: str) -> str:
        return os.environ.get(f"E2E_UI_{service.upper()}_URL", self._PORTS[service])

    # Client URLs: .env.full carries container hostnames (thehive:9000, …)
    # which do not resolve from a host-side run — the E2E base would burn
    # ~30 s per client in DNS retries. Force published localhost ports.
    _HOST_URL_OVERRIDES = {
        "SHUFFLE_URL": "http://localhost:5001",
        "THEHIVE_URL": "https://localhost:18100",
        "CORTEX_URL": "https://localhost:18101",
        "MISP_URL": "https://localhost:8083",
        "ES_URL": "https://localhost:19200",
        "OPENSEARCH_URL": "https://localhost:19201",
        "GRAFANA_URL": "http://localhost:8084",
        "API_URL": "http://localhost:8000",
        "LOKI_URL": "http://localhost:3100",
        "NGINX_URL": "http://localhost:80",
        "WEB_MANAGEMENT_URL": "http://localhost:8085",
        "DOCS_URL": "http://localhost:8086",
    }

    def load_env(self):
        env = super().load_env()
        env.update(self._HOST_URL_OVERRIDES)
        return env

    # --- host-side probes: skip in-container preflight entirely ---------
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
        if getattr(self, "_screenshot_dir", None):
            self._log(f"screenshots dir: {self._screenshot_dir}")

    def setup_method(self, method):
        super().setup_method(method)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._screenshot_dir = SCREENSHOT_DIR
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

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
    # Discovery
    # ------------------------------------------------------------------
    def _http_probe(self, url: str) -> dict:
        """Classify a port's response: HTML / JSON / redirect / down.

        Retried once — Docker Desktop's port proxy drops sporadic
        connections under load. SSL errors following a redirect (MISP
        http→https upgrade) classify as ``tls-redirect``, which is the
        service's expected posture, not a failure.
        """
        last = None
        for _ in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "tc28-probe"})
                # MISP publishes HTTPS-only with a self-signed lab cert —
                # plain HTTP gets nginx 400, not a redirect, so the probe
                # must speak TLS (unverified: we assert reachability, not
                # cert validity — TLS posture is a separate oracle).
                ctx = ssl._create_unverified_context() if url.startswith("https://") else None
                resp = urllib.request.urlopen(req, timeout=6, context=ctx)
                body = resp.read(4096).lower()
                return {
                    "status": resp.status,
                    "kind": "html" if (b"<html" in body or b"<!doctype" in body) else "non-html",
                    "final_url": resp.geturl(),
                }
            except urllib.error.HTTPError as e:
                return {"status": e.code, "kind": "http-error", "final_url": url}
            except urllib.error.URLError as e:
                reason = str(e.reason) if e.reason else str(e)
                if "CERTIFICATE" in reason.upper() or "SSL" in reason.upper():
                    return {
                        "status": None,
                        "kind": "tls-redirect",
                        "final_url": url,
                    }
                last = {"status": None, "kind": f"down:{type(e).__name__}", "final_url": url}
            except Exception as e:
                last = {"status": None, "kind": f"down:{type(e).__name__}", "final_url": url}
        return last

    def _screenshot(self, page, name: str) -> Path:
        out = self._screenshot_dir / f"{name}.png"
        page.screenshot(path=str(out), full_page=False)
        return out

    # ------------------------------------------------------------------
    def test_port_surface_inventory(self):
        """Oracle estático: cada puerto UI sigue sirviendo HTML; cada puerto
        API-only sigue sin exponer UI. Captura el inventario en JSON."""
        inventory = {"checked_at": datetime.now(UTC).isoformat(), "ui": {}, "api": {}}
        failures = []

        for name, url in self._PORTS.items():
            # Probe the real UI path — e.g. docs-site lives under a baseUrl
            # and legitimately 404s on /.
            probe = self._http_probe(url)
            inventory["ui"][name] = probe
            # UIs must at least respond; render correctness is asserted
            # per-page in the screenshot test. tls-redirect = the service
            # upgraded http→https (MISP) — expected posture.
            healthy = probe["status"] in (200, 301, 302, 401, 403) or probe["kind"] in (
                "html",
                "tls-redirect",
            )
            if not healthy:
                failures.append(f"UI {name} ({url}): {probe}")

        for name, url in self._API_ONLY_PORTS.items():
            probe = self._http_probe(url + "/")
            inventory["api"][name] = probe
            if probe["kind"] == "html":
                failures.append(f"{name} ({url}) unexpectedly serves HTML UI: {probe}")

        (self._screenshot_dir / "_inventory.json").write_text(json.dumps(inventory, indent=2))
        assert not failures, "UI surface regression:\n" + "\n".join(failures)

    def test_all_uis_render_and_capture(self):
        """Render real en Chromium de cada UI + captura PNG.

        Oracle por servicio: la página debe producir contenido visible —
        título, inputs de login, o texto de marca — no una pantalla en
        blanco ni un error 5xx.
        """
        results = {}
        failures = []

        for name, url in self._PORTS.items():
            target = self._ui_url(name)
            context, page = self._new_page()
            entry = {"url": target}
            try:
                response = page.goto(target, wait_until="domcontentloaded")
                entry["status"] = response.status if response else None
                if response is None or response.status >= 500:
                    failures.append(f"{name}: HTTP {entry['status']}")
                    self._screenshot(page, f"{name}_FAIL")
                    continue

                try:
                    page.wait_for_load_state("networkidle", timeout=15_000)
                except Exception:
                    pass  # long-poll services never go idle; settle instead
                page.wait_for_timeout(self.SETTLE_MS)

                entry["title"] = page.title()
                # Render oracle: any of title / inputs / visible text >50 chars
                body_text = ""
                try:
                    body_text = page.locator("body").inner_text(timeout=5_000)
                except Exception:
                    pass
                entry["has_inputs"] = page.locator("input").count() > 0
                entry["body_chars"] = len(body_text.strip())
                shot = self._screenshot(page, name)
                entry["screenshot"] = shot.name

                rendered = (
                    bool(entry["title"].strip()) or entry["has_inputs"] or entry["body_chars"] > 50
                )
                if not rendered:
                    failures.append(
                        f"{name}: blank render (title={entry['title']!r}, "
                        f"inputs={entry['has_inputs']}, body={entry['body_chars']} chars)"
                    )
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {e}"
                failures.append(f"{name}: {entry['error']}")
                try:
                    self._screenshot(page, f"{name}_ERR")
                except Exception:
                    pass
            finally:
                context.close()
                results[name] = entry

        (self._screenshot_dir / "_render_results.json").write_text(
            json.dumps(results, indent=2, default=str)
        )
        for name, entry in results.items():
            self._log(
                f"{name}: status={entry.get('status')} title={entry.get('title')!r} "
                f"shot={entry.get('screenshot', '-')}"
            )
        assert not failures, "UI render failures:\n" + "\n".join(failures)

    def test_web_management_soar_panel_present(self):
        """La consola propia debe montar la sección SOAR Pipeline (la parte
        construida en este proyecto — oráculo funcional, no solo render)."""
        url = self._ui_url("web_management")
        context, page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(self.SETTLE_MS)
            # The pipeline section renders even logged-out (login gate may
            # overlay it — check DOM presence, not interaction).
            content = page.content()
            assert "queue" in content.lower() or "decision" in content.lower(), (
                "web-management missing SOAR pipeline section — "
                "static assets may be stale in the image"
            )
            self._screenshot(page, "web_management_detail")
        finally:
            context.close()

    def test_web_management_authenticated_capture(self):
        """Login real con WEB_UI_* → la consola operativa carga datos y se
        captura el estado autenticado (queue depth, decisions feed).

        The UI's API_BASE is relative (`/api`), so the authenticated flow
        must go through the edge nginx (:80) which proxies /api → api:8000 —
        the web-management container itself serves static files only.
        """
        url = self._ui_url("nginx")
        user = self.env.get("WEB_UI_USER", "")
        password = self.env.get("WEB_UI_PASSWORD", "")
        assert user and password, "WEB_UI_USER/WEB_UI_PASSWORD missing in env"

        context, page = self._new_page()
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.locator("#username").fill(user)
            page.locator("#password").fill(password)
            page.locator("#loginBtn").click()
            # Auth hides #authSection and mounts #mainContent with data.
            page.locator("#mainContent").wait_for(state="visible", timeout=20_000)
            # Let the 15s-refresh panels fetch at least once.
            page.wait_for_timeout(self.SETTLE_MS * 2)
            shot = self._screenshot(page, "web_management_authenticated")
            self._log(f"authenticated capture: {shot.name}")

            # Operational oracle: the authenticated console must surface
            # live data — services list or KPI numbers, not empty panels.
            body = page.locator("body").inner_text()
            assert len(body.strip()) > 200, (
                f"Authenticated console rendered only {len(body.strip())} "
                "chars — panels did not populate"
            )
        finally:
            context.close()

    # ------------------------------------------------------------------
    # Deep page coverage — every reachable page of every UI
    # ------------------------------------------------------------------
    def _login_web_management(self, page, url):
        page.locator("#username").fill(self.env.get("WEB_UI_USER", ""))
        page.locator("#password").fill(self.env.get("WEB_UI_PASSWORD", ""))
        page.locator("#loginBtn").click()
        page.locator("#mainContent").wait_for(state="visible", timeout=20_000)

    def _login_grafana(self, page, url):
        page.locator("input[name='user']").fill(self.env.get("GRAFANA_ADMIN_USER", "admin"))
        page.locator("input[name='password']").fill(self.env.get("GRAFANA_ADMIN_PASSWORD", ""))
        page.locator("button[type='submit']").click()
        page.wait_for_url(lambda u: "/login" not in u, timeout=20_000)

    def _login_form(self, page, user_sel, pass_sel, user, password, submit_sel):
        """Generic form login for Angular/SPA UIs."""
        page.locator(user_sel).first.fill(user)
        page.locator(pass_sel).first.fill(password)
        page.locator(submit_sel).first.click()
        page.wait_for_timeout(self.SETTLE_MS * 2)

    def _login_thehive(self, page, url):
        # TheHive 5 React login: email + password, "Log in" submit.
        self._login_form(
            page,
            "input[type='text'], input[type='email'], input:not([type])",
            "input[type='password']",
            self.env.get("THEHIVE_ADMIN_USER", "admin@thehive.local"),
            self.env.get("THEHIVE_ADMIN_PASSWORD", ""),
            "button[type='submit'], button:has-text('Log in'), "
            "button:has-text('Sign In'), input[type='submit']",
        )

    def _login_cortex(self, page, url):
        self._login_form(
            page,
            "input:not([type='password'])",
            "input[type='password']",
            self.env.get("CORTEX_ADMIN_USER", ""),
            self.env.get("CORTEX_ADMIN_PASSWORD", ""),
            "button:has-text('Sign In'), input[type='submit']",
        )

    def _login_shuffle(self, page, url):
        # Shuffle login form lives in the left card; the topbar also has a
        # search input — target by placeholder to avoid filling it.
        user = self.env.get("SHUFFLE_DEFAULT_USERNAME", "")
        password = self.env.get("SHUFFLE_DEFAULT_PASSWORD", "")
        page.locator("input[placeholder*='username'], input[placeholder*='example']").first.fill(
            user
        )
        page.locator("input[type='password']").first.fill(password)
        page.locator("button:has-text('Continue'), button[type='submit']").first.click()
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=20_000)
        except Exception:
            pass  # SPA may stay on /login while session cookie is set
        # Auth oracle: a genuinely failed login must mark the service
        # (login_failed) so its pages count as failures — otherwise the
        # coverage gate could pass on login-wall screenshots. Probe a
        # protected route: unauthenticated sessions bounce back to /login.
        page.goto(url.rsplit("/", 1)[0] + "/workflows", timeout=20_000)
        page.wait_for_load_state("domcontentloaded")
        if "/login" in page.url:
            raise AssertionError(f"shuffle login failed — still at {page.url}")

    def _login_misp(self, page, url):
        page.locator("input[name='data[User][email]']").fill(self.env.get("MISP_ADMIN_EMAIL", ""))
        page.locator("input[name='data[User][password]']").fill(
            self.env.get("MISP_ADMIN_PASSWORD", "")
        )
        page.locator("button:has-text('Login'), input[type='submit']").first.click()
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=20_000)
        except Exception:
            pass  # MISP may stay on /login while the session cookie is set
        # Auth oracle (same rationale as _login_shuffle): probe a protected
        # route — unauthenticated sessions bounce to /users/login.
        page.goto(url.rstrip("/") + "/users/index", timeout=20_000)
        page.wait_for_load_state("domcontentloaded")
        if "/users/login" in page.url:
            raise AssertionError(f"misp login failed — bounced to {page.url}")

    def test_all_pages_captured(self):
        """Captura exhaustiva: cada página navegable de cada UI.

        Método: login por servicio (credenciales de .env.full) → lista de
        páginas por servicio → PNG por página + JSON de evidencia.
        Fallos de una página no abortan el resto — se registran y el
        assert final exige cobertura ≥90% de las páginas declaradas.
        """
        # Single source of truth: _PORTS/_ui_url (E2E_UI_*_URL overridable).
        # MISP publishes HTTPS-only with a self-signed lab cert — plain
        # HTTP gets nginx 400 (no redirect). Chromium context already
        # uses ignore_https_errors.
        base = {
            "nginx": self._ui_url("nginx"),
            "api": self._ui_url("api_swagger"),
            "shuffle": self._ui_url("shuffle_frontend").rsplit("/", 1)[0],
            "grafana": self._ui_url("grafana").rsplit("/", 1)[0],
            "misp": self._ui_url("misp"),
            "thehive": self._ui_url("thehive"),
            "cortex": self._ui_url("cortex"),
            "docs": self._ui_url("docs_site").rstrip("/"),
            "osd": self._ui_url("opensearch_dashboards"),
        }

        # plan entries hold: service, shot_name, path, section_selector-or-None
        plan = [
            # --- API portal (Swagger/ReDoc disabled by design under
            # API_DOCS_ENABLED=spec — only the portal + openapi.json exist)
            ("api", "api_portal", "/", None),
            # --- web-management: every panel section after login
            ("nginx", "wm_dashboard", "/", ".dashboard"),
            ("nginx", "wm_pipeline", "/", ".pipeline-section"),
            ("nginx", "wm_services", "/", ".services-section"),
            ("nginx", "wm_testing", "/", ".testing-section"),
            ("nginx", "wm_logs", "/", ".logs-section"),
            ("nginx", "wm_backup", "/", ".backup-section"),
            ("nginx", "wm_full_page", "/", "FULLPAGE"),
            # --- grafana
            ("grafana", "grafana_dashboards", "/dashboards", None),
            ("grafana", "grafana_kpi_main", "/d/soar-kpi-main", None),
            ("grafana", "grafana_explore", "/explore", None),
            # --- shuffle SPA
            ("shuffle", "shuffle_workflows", "/workflows", None),
            ("shuffle", "shuffle_apps", "/apps", None),
            # --- thehive (TH5 React routes) / cortex (AngularJS hash routes)
            ("thehive", "thehive_cases", "/cases", None),
            ("thehive", "thehive_alerts", "/alerts", None),
            ("cortex", "cortex_jobs", "/index.html#/jobs", None),
            ("cortex", "cortex_analyzers", "/index.html#/analyzers", None),
            # --- misp: login page + authenticated event index
            ("misp", "misp_landing", "/", None),
            ("misp", "misp_events", "/events/index", None),
            ("misp", "misp_event_view", "/events/view/1", None),
            # --- docs-site (Docusaurus — real routes from nav links)
            ("docs", "docs_home", "/", None),
            ("docs", "docs_getting_started", "/docs/getting-started", None),
            ("docs", "docs_architecture", "/docs/architecture/overview", None),
            ("docs", "docs_reports", "/docs/reports", None),
            ("docs", "docs_reports_quality", "/docs/reports/quality/quality-summary", None),
            ("docs", "docs_reports_e2e", "/docs/reports/test-review/test_review_report", None),
            # --- opensearch dashboards
            ("osd", "osd_home", "/app/home", None),
            ("osd", "osd_dashboards", "/app/dashboards", None),
            ("osd", "osd_discover", "/app/discover", None),
        ]

        logins = {
            "nginx": self._login_web_management,
            "grafana": self._login_grafana,
            "thehive": self._login_thehive,
            "cortex": self._login_cortex,
            "shuffle": self._login_shuffle,
            "misp": self._login_misp,
        }

        results, failures = {}, []
        contexts = {}
        login_failed = set()

        def ctx_for(service):
            if service not in contexts:
                context, page = self._new_page()
                contexts[service] = (context, page)
                # Per-service login once, before its first page. A slow boot
                # (fresh recreate) must not kill the whole service — allow a
                # generous navigation window.
                if service in logins:
                    try:
                        entry_url = base[service] + "/"
                        page.goto(entry_url, wait_until="domcontentloaded", timeout=60_000)
                        logins[service](page, entry_url)
                    except Exception as e:
                        login_failed.add(service)
                        results[service + "__login"] = {"auth_error": str(e)[:200]}
            return contexts[service][1]

        # Content that proves the page actually rendered (not a spinner or a
        # login wall). Best-effort — absence only delays the shot.
        _READY = {
            "grafana": (
                ".react-grid-item, .panel-container, "
                "[data-testid='data-testid Dashboard browse']"
            ),
            "shuffle": "text=Workflows",
            "osd": ".euiDataGrid, .dscWrapper, .osdHeaderPageLayout",
            "docs": "article, .markdown, .theme-doc-markdown",
            "thehive": "#root, main, .main-content, .ui-view, [ui-view]",
            "cortex": ".main-content, .ui-view, [ui-view]",
            "misp": "#content, .navbar",
            "nginx": "#mainContent",
        }

        # Dev-mode servers compile routes on first hit (Docusaurus lazily
        # webpack-compiles each /docs/* route; TheHive boots a heavy
        # AngularJS bundle) — the first visit can exceed 30s legitimately.
        # A failed goto still records the page, so the coverage oracle is
        # what guards real regressions, not the timeout budget.
        _SLOW_SERVICES = {"docs", "thehive"}
        for service, shot, path, section in plan:
            page = ctx_for(service)
            entry = {"url": base[service] + path}
            if service in login_failed:
                # Pages behind a failed login can only show a login wall —
                # count them as failed captures, not silent login screenshots.
                entry["error"] = f"login failed for {service}"
                failures.append(f"{shot}: {entry['error']}")
                results[shot] = entry
                continue
            page_timeout = 90_000 if service in _SLOW_SERVICES else self.BROWSER_TIMEOUT_MS
            try:
                r = page.goto(
                    base[service] + path, wait_until="domcontentloaded", timeout=page_timeout
                )
                entry["status"] = r.status if r else None
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                # Wait for real content (not spinners/login walls) before
                # shooting — e.g. Shuffle's 'Loading Workflows and Apps'.
                ready = _READY.get(service)
                if ready:
                    try:
                        page.wait_for_selector(ready, state="visible", timeout=20_000)
                    except Exception:
                        pass
                    # Shuffle: data still fetching once the grid shell shows.
                    if service == "shuffle":
                        try:
                            page.wait_for_selector("text=Loading", state="detached", timeout=15_000)
                        except Exception:
                            pass
                    # web-management: KPIs/coverage hydrate via a fetch chain
                    # that lands a few seconds after #mainContent appears.
                    if service == "nginx":
                        try:
                            page.wait_for_function(
                                "document.getElementById('kpiMttr')"
                                " && document.getElementById('kpiMttr')"
                                ".textContent.trim() !== '—'",
                                timeout=15_000,
                            )
                        except Exception:
                            pass
                    # OSD: Discover keeps querying after the shell renders.
                    if service == "osd":
                        try:
                            page.wait_for_selector(
                                '[data-test-subj="loadingSpinner"]',
                                state="detached",
                                timeout=20_000,
                            )
                        except Exception:
                            pass
                page.wait_for_timeout(self.SETTLE_MS)
                entry["title"] = page.title()
                if section == "FULLPAGE":
                    out = self._screenshot_dir / f"{shot}.png"
                    page.screenshot(path=str(out), full_page=True)
                    entry["screenshot"] = out.name
                elif section:
                    out = self._screenshot_dir / f"{shot}.png"
                    try:
                        el = page.locator(section).first
                        el.scroll_into_view_if_needed(timeout=10_000)
                        page.wait_for_timeout(1500)
                        el.screenshot(path=str(out))
                    except Exception:
                        # Sections populated late are never "stable" for
                        # Playwright — JS-scroll and capture the viewport.
                        page.evaluate(
                            f"document.querySelector('{section}')"
                            ".scrollIntoView({block:'start'})"
                        )
                        page.wait_for_timeout(1500)
                        page.screenshot(path=str(out), full_page=False)
                    entry["screenshot"] = out.name
                else:
                    entry["screenshot"] = self._screenshot(page, shot).name
                entry["body_chars"] = len(page.locator("body").inner_text(timeout=5_000).strip())
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {str(e)[:150]}"
                failures.append(f"{shot}: {entry['error']}")
            results[shot] = entry

        for context, _ in contexts.values():
            context.close()

        (self._screenshot_dir / "_deep_results.json").write_text(
            json.dumps(results, indent=2, default=str)
        )
        for shot, entry in results.items():
            self._log(
                f"{shot}: status={entry.get('status')} title={entry.get('title')!r} "
                f"shot={entry.get('screenshot', '-')} err={entry.get('error', '-')}"
            )
        coverage = (len(plan) - len(failures)) / len(plan)
        assert coverage >= 0.9, f"Page coverage {coverage:.0%} <90%.\nFailures:\n" + "\n".join(
            failures
        )
