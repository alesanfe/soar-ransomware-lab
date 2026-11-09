"""BUG-070 regression: the Shuffle workflow's MISP nodes must target HTTPS.

MISP forces HTTPS internally: ``http://misp:80`` answers ``301 -> https://misp/``
and the Shuffle http app drops the ``Authorization`` header when it follows the
redirect, so ``misp_search``/``misp_create`` receive MISP's HTML error page
instead of JSON. The nodes carried ``http://misp:80`` because
``MISP_URL`` was not exported into the api container env (where
``init_shuffle_webhook`` runs) and ``config.MISP_URL`` defaulted to
``http://misp:80`` — contradicting the code comment "MISP uses HTTPS on
port 443 internally".

Fix: default ``MISP_URL`` to ``https://misp`` and export ``MISP_URL`` into
the api container environment so the workflow generator bakes the HTTPS
URL.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.setup.shuffle_workflow import workflow_actions


def _ctx() -> workflow_actions.WorkflowContext:
    return workflow_actions.WorkflowContext(
        thehive_key="hive",
        cortex_key="ctx",
        misp_key="misp",
        app_id_http="http",
        app_id_shuffle_tools="tools",
        cortex_basic="Y3R4",
        es_basic="ZXM=",
    )


def _param(action: dict, name: str) -> str:
    for p in action.get("parameters", []):
        if p.get("name") == name:
            return p.get("value", "")
    return ""


def _misp_urls() -> list[str]:
    urls: list[str] = []
    for a in workflow_actions.build_actions(_ctx()):
        url = _param(a, "url")
        if url.startswith("http") and "misp" in url:
            urls.append(url)
    return urls


class TestMispNodesUseHttps:
    def test_default_config_uses_https(self, monkeypatch):
        """With no MISP_URL env, the default must be https://misp —
        http://misp:80 301-redirects and drops the Authorization header."""
        monkeypatch.delenv("MISP_URL", raising=False)
        from scripts.setup.shuffle_workflow import config

        reloaded = importlib.reload(config)
        try:
            assert reloaded.MISP_URL == "https://misp", (
                f"MISP_URL default is {reloaded.MISP_URL!r} — must be "
                "https://misp (http://misp:80 301-redirects to https and "
                "the redirect drops the Authorization header)"
            )
        finally:
            monkeypatch.undo()

    def test_misp_action_urls_are_https(self):
        """Every baked MISP URL in the workflow must use https."""
        urls = _misp_urls()
        assert urls, "no MISP http actions found in generated workflow"
        for url in urls:
            assert url.startswith("https://"), (
                f"MISP node URL is not HTTPS: {url} — http://misp:80 "
                "301-redirects and drops the Authorization header"
            )

    def test_api_compose_exports_misp_url(self):
        """docker-compose.api.yml must pass MISP_URL into the api env, or
        the webhook-init script falls back to the in-code default."""
        # Walk up from __file__ to the repo root (marker: infra/docker/)
        # — a fixed-depth `parent.parent.parent` breaks if the test file
        # is imported from a copied tree (e.g. mutmut's `mutants/` dir).
        here = Path(__file__).resolve()
        compose = None
        for parent in here.parents:
            candidate = parent / "infra" / "docker" / "compose" / "docker-compose.api.yml"
            if candidate.exists():
                compose = candidate
                break
        assert compose is not None, f"docker-compose.api.yml not found walking up from {here}"
        text = compose.read_text(encoding="utf-8")
        assert "MISP_URL" in text, (
            "MISP_URL is not in the api container environment — the "
            "workflow generator would use the in-code default"
        )
