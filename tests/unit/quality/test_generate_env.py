#!/usr/bin/env python3
"""Unit tests for scripts/setup/generate_env.py.

BUG-033: ``generate_grafana_datasource`` rendered the template with
``str.format`` — any ``{var}`` in the template other than the four known
placeholders (e.g. ``${VAR:-default}`` shell-style blocks, which the repo
already ships in ``config/templates/``) raised ``KeyError``/``ValueError``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "generate_env", ROOT / "scripts" / "setup" / "generate_env.py"
)
generate_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generate_env)


class TestGrafanaDatasourceTemplate:
    def test_template_with_unknown_braces_does_not_crash(self, tmp_path):
        tpl = tmp_path / "tpl.yml"
        out = tmp_path / "out.yml"
        tpl.write_text(
            "url: ${LOKI_URL:-http://loki:3100}\n"
            "api: {api_url}\n"
            "es: {es_url}\n"
            "user: {elastic_user}\n"
            "pass: <ELASTIC_PASSWORD>\n",
            encoding="utf-8",
        )
        generate_env.generate_grafana_datasource("pw123", tpl, out)
        rendered = out.read_text(encoding="utf-8")
        assert "${LOKI_URL:-http://loki:3100}" in rendered
        assert "pw123" in rendered

    def test_default_placeholders_still_rendered(self, tmp_path):
        tpl = tmp_path / "tpl.yml"
        out = tmp_path / "out.yml"
        tpl.write_text(
            "loki: {loki_url}\nes: {es_url}\nu: {elastic_user}\n"
            "api: {api_url}\np: <ELASTIC_PASSWORD>\n",
            encoding="utf-8",
        )
        generate_env.generate_grafana_datasource("pw", tpl, out)
        rendered = out.read_text(encoding="utf-8")
        assert "{loki_url}" not in rendered and "{es_url}" not in rendered
        assert "pw" in rendered
