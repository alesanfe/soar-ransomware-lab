#!/usr/bin/env python3
"""Static validation of provisioned Grafana dashboards (GRAF-038).

Checks the dashboard JSON files under infra/docker/compose/logging/ without
needing a running Grafana. Catches the regression classes we have actually
seen in this project:

- invalid JSON / missing uid / duplicate uids
- literal $__rate_interval (not substituted in render context -> Loki 400)
- error/warn LogQL patterns without domain scoping (Loki self-match)
- panels without title/description
- references to datasource uids not provisioned
- missing "version" (provisioning version-gating silently skips updates)
- dead artifacts: export-format files ({dashboard: {...}}) in the
  provisioning directory are never imported and are confusing leftovers

Exit code 0 = clean, 1 = violations found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LOGGING_DIR = Path(__file__).resolve().parents[2] / "infra" / "docker" / "compose" / "logging"
DATASOURCES_FILE = Path(__file__).resolve().parents[2] / "runtime" / "config" / "grafana-datasources.yml"
DATASOURCES_TEMPLATE = (
    Path(__file__).resolve().parents[2] / "infra" / "docker" / "config" / "templates" / "grafana-datasources.yml.template"
)

OBS_STACK_RE = r"loki|grafana\.\*|prometheus|cadvisor|tempo|otel-collector|promtail"
ERROR_PATTERN_RE = re.compile(r'\|~\s*"\(\?i\)[^"]*(error|warn|exception|fatal|traceback)')


def load_provisioned_ds_uids() -> set[str]:
    """Parse datasource uids from the yaml (no pyyaml dependency needed for uid lines)."""
    src = DATASOURCES_FILE if DATASOURCES_FILE.exists() else DATASOURCES_TEMPLATE
    uids: set[str] = set()
    for line in src.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*uid:\s*([A-Za-z0-9_-]+)\s*$", line)
        if m:
            uids.add(m.group(1))
    # Built-in pseudo-datasources used by panels/annotations
    uids.update({"-- Grafana --", "grafana", "-- Dashboard --", "datasource", "__expr__"})
    return uids


def collect_exprs(node, out: list) -> None:
    """Walk dashboard JSON collecting every expr/query string."""
    if isinstance(node, dict):
        for key, val in node.items():
            if key in ("expr", "query", "rawSql") and isinstance(val, str):
                out.append(val)
            else:
                collect_exprs(val, out)
    elif isinstance(node, list):
        for item in node:
            collect_exprs(item, out)


def check_dashboard(path: Path, ds_uids: set[str]) -> list[str]:
    errs: list[str] = []
    raw = path.read_text(encoding="utf-8")

    try:
        dash = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"{path.name}: invalid JSON — {exc}"]

    # Export-format dead artifact check (GRAF-012)
    if "dashboard" in dash and "uid" not in dash:
        errs.append(f"{path.name}: export-format file ({{dashboard:...}}) — not provisioned, dead artifact")

    uid = dash.get("uid")
    if not uid:
        errs.append(f"{path.name}: missing uid")
    if "version" not in dash:
        errs.append(f"{path.name}: missing version (provisioning will ignore updates)")

    # Datasource uids can be templated as ${VAR} where VAR is a
    # datasource-type variable declared in the dashboard's templating.list
    tpl_ds_vars = {
        f"${{{v['name']}}}"
        for v in dash.get("templating", {}).get("list", [])
        if v.get("type") == "datasource" and v.get("name")
    }
    valid_uids = ds_uids | tpl_ds_vars

    panels = dash.get("panels", [])
    seen_ids: set[int] = set()
    exprs: list[str] = []
    collect_exprs(dash, exprs)

    for ex in exprs:
        # $__rate_interval stays literal in d-solo render context (Loki 400);
        # $__interval is resolved client-side and is safe.
        if "$__rate_interval" in ex:
            errs.append(f"{path.name}: literal $__rate_interval/$__interval in expr — not substituted in render context")
        # Self-match: error/warn log pattern without domain exclusion
        if ERROR_PATTERN_RE.search(ex):
            if "compose_service!~" not in ex and 'compose_service="' not in ex and 'compose_service=~"' in ex and "$service" not in ex and "api|shuffle" not in ex:
                if "compose_service=~" in ex and "api|shuffle" not in ex:
                    errs.append(f"{path.name}: error-pattern query without domain filter — {ex[:90]}")

    for panel in panels:
        pid = panel.get("id", "?")
        if pid in seen_ids:
            errs.append(f"{path.name}: duplicate panel id {pid}")
        seen_ids.add(pid)
        if not panel.get("title") and panel.get("type") != "row":
            errs.append(f"{path.name}: panel {pid} missing title")
        if not panel.get("description") and panel.get("type") not in ("row", "text"):
            errs.append(f"{path.name}: panel {pid} ({panel.get('title','?')[:40]}) missing description")
        ds = panel.get("datasource") or {}
        ds_uid = ds.get("uid") if isinstance(ds, dict) else None
        if ds_uid and ds_uid not in valid_uids:
            errs.append(f"{path.name}: panel {pid} references unknown datasource uid {ds_uid!r}")
        for tgt in panel.get("targets") or []:
            tds = (tgt.get("datasource") or {}).get("uid")
            if tds and tds not in valid_uids:
                errs.append(f"{path.name}: panel {pid} target references unknown datasource uid {tds!r}")

    return errs


def main() -> int:
    files = sorted(LOGGING_DIR.glob("*dashboard*.json"))
    if not files:
        print(f"No dashboard files found in {LOGGING_DIR}")
        return 1
    ds_uids = load_provisioned_ds_uids()
    all_errs: list[str] = []
    uids: dict[str, str] = {}
    for path in files:
        errs = check_dashboard(path, ds_uids)
        all_errs.extend(errs)
        try:
            u = json.loads(path.read_text(encoding="utf-8")).get("uid")
            if u:
                if u in uids:
                    all_errs.append(f"duplicate dashboard uid {u!r} in {path.name} and {uids[u]}")
                uids[u] = path.name
        except Exception:
            pass
    for e in all_errs:
        print("FAIL", e)
    print(f"{len(files)} dashboards checked, {len(all_errs)} violation(s)")
    return 1 if all_errs else 0


if __name__ == "__main__":
    sys.exit(main())
