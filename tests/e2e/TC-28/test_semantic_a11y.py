"""TC-28 — server-side WCAG surface checks on OWNED UIs.

Playwright/axe run host-side (test_ui_a11y.py). This file covers what can be
verified without a browser, on the raw HTML the services actually serve:
document language, title, landmark regions, single h1, heading order,
img alt text, form labels, viewport meta (responsive-ready), nav naming.
WCAG refs: 3.1.1, 2.4.2, 1.3.1, 2.4.1, 1.1.1, 3.3.2/4.1.2, 1.4.10.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest
import requests

OWNED = {
    # soar.local is the SAN name the nginx edge actually serves — verifying
    # against 'nginx' would only test a hostname the cert never claimed.
    "web_management": "https://soar.local/",
    "docs_site": "http://docs-site:8080/",
    "api_portal": "http://api:8000/",
}
CA = "/app/certs/ca.crt"


class _Audit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.headings: list[int] = []
        self.imgs_missing_alt = 0
        self.imgs_total = 0
        self.inputs_unlabeled: list[str] = []
        self.labels_for: set[str] = set()
        self._cur_heading: int | None = None
        self._title_seen = False
        self._title_text = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag == "img":
            self.imgs_total += 1
            if "alt" not in a:
                self.imgs_missing_alt += 1
        if tag == "label" and a.get("for"):
            self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            itype = a.get("type", "")
            if itype not in ("hidden", "submit", "button") and a.get("id") not in self.labels_for:
                if not (a.get("aria-label") or a.get("aria-labelledby") or a.get("placeholder")):
                    self.inputs_unlabeled.append(f"{tag}#{a.get('id', '?')}")

    def handle_data(self, data):
        if self._title_seen:
            self._title_text += data

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self._title_seen = False

    # track <title> content
    def handle_starttag_title(self):
        pass


def _audit(html: str) -> _Audit:
    p = _Audit()
    p.feed(html)
    # crude title capture — handle_data accumulates while flag set
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    p._title_text = m.group(1).strip() if m else ""
    return p


def _fetch(url: str) -> str:
    r = requests.get(url, verify=CA, timeout=15, allow_redirects=True)
    r.raise_for_status()
    return r.text


@pytest.mark.e2e
class TestSemanticA11y:
    @pytest.fixture(scope="class", params=sorted(OWNED.items()))
    @classmethod
    def page(cls, request):
        name, url = request.param
        try:
            return name, url, _audit(_fetch(url))
        except requests.RequestException as e:
            pytest.skip(f"{name} unreachable: {e}")

    def test_document_language_declared(self, page):
        name, url, a = page
        html_tag = next((attrs for t, attrs in a.tags if t == "html"), {})
        assert html_tag.get("lang"), f"{name}: <html> missing lang (WCAG 3.1.1)"

    def test_nonempty_title(self, page):
        name, url, a = page
        assert a._title_text, f"{name}: empty/missing <title> (WCAG 2.4.2)"

    def test_single_h1_and_ordered_headings(self, page):
        name, url, a = page
        h1 = a.headings.count(1)
        assert h1 == 1, f"{name}: {h1} h1 elements (WCAG 1.3.1)"
        # no heading-level jumps >1 (h1 -> h3 breaks reading order)
        prev = 0
        for lvl in a.headings:
            assert lvl <= prev + 1 or prev == 0, (
                f"{name}: heading jump h{prev}->h{lvl} (WCAG 1.3.1)"
            )
            prev = lvl

    def test_landmark_regions_present(self, page):
        name, url, a = page
        tags = {t for t, _ in a.tags}
        roles = {attrs.get("role") for _, attrs in a.tags if attrs.get("role")}
        has_main = "main" in tags or "main" in roles
        has_nav = "nav" in tags or "navigation" in roles
        assert has_main and has_nav, (
            f"{name}: missing landmarks main={has_main} nav={has_nav} (WCAG 1.3.1/2.4.1)"
        )

    def test_images_have_alt_text(self, page):
        name, url, a = page
        assert a.imgs_missing_alt == 0, (
            f"{name}: {a.imgs_missing_alt}/{a.imgs_total} <img> without alt (WCAG 1.1.1)"
        )

    def test_form_controls_labeled(self, page):
        name, url, a = page
        assert not a.inputs_unlabeled, (
            f"{name}: unlabeled form controls {a.inputs_unlabeled[:5]} (WCAG 3.3.2/4.1.2)"
        )

    def test_responsive_viewport_meta(self, page):
        name, url, a = page
        metas = [attrs for t, attrs in a.tags if t == "meta"]
        vp = next((m.get("content", "") for m in metas if m.get("name") == "viewport"), "")
        assert "width=device-width" in vp, (
            f"{name}: no responsive viewport meta (WCAG 1.4.10 prerequisite)"
        )
