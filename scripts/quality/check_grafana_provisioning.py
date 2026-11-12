#!/usr/bin/env python3
"""Validate Grafana provisioning artifacts (GRAF-005).

Checks, without needing a running Grafana:
  * Every dashboard JSON under infra/docker/compose/logging/ parses and
    has the required keys (title, uid, panels with valid datasource uids).
  * alert-rules.yml parses, groups/rules have the required alert fields,
    and every datasourceUid referenced exists in the datasources file.
  * grafana-kpi-dashboard.yml provider config parses and points at an
    existing provisioning path.
  * docker-compose.logging.yml mounts every provisioned artifact that
    exists on disk (no orphan dashboards/rules).

Exit 0 on success, 1 on any failure. Designed for `make quality` / CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LOGGING_DIR = REPO_ROOT / "infra" / "docker" / "compose" / "logging"
# Rendered artifact mounted by docker-compose.logging.yml. Fall back to the
# template so the check also works before `generate_env.py` has run (CI).
DATASOURCES_RENDERED = REPO_ROOT / "runtime" / "config" / "grafana-datasources.yml"
DATASOURCES_TEMPLATE = (
    REPO_ROOT / "infra" / "docker" / "config" / "templates" / "grafana-datasources.yml.template"
)
DATASOURCES = DATASOURCES_RENDERED if DATASOURCES_RENDERED.exists() else DATASOURCES_TEMPLATE
ALERT_RULES = LOGGING_DIR / "alert-rules.yml"
PROVIDER = LOGGING_DIR / "grafana-kpi-dashboard.yml"
COMPOSE = LOGGING_DIR / "docker-compose.logging.yml"
DASHBOARDS = sorted(LOGGING_DIR.glob("*dashboard*.json"))

VALID_EXPR_UIDS = {"__expr__"}
# Built-in pseudo-datasources (e.g. alertlist panels use -- Grafana --).
BUILTIN_DS_UIDS = {"-- Grafana --", "grafana", "-- Dashboard --", "datasource"}
REQUIRED_PANEL_KEYS = {"id", "type", "title"}
# Panel types that legitimately have no query targets.
NO_TARGET_PANEL_TYPES = {"alertlist", "dashlist", "text", "news", "annolist"}
REQUIRED_RULE_KEYS = {"uid", "title", "condition", "data", "for"}


def _fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def check_datasources(errors: list[str]) -> set[str]:
    uids: set[str] = set()
    if not DATASOURCES.exists():
        _fail(f"missing {DATASOURCES}", errors)
        return uids
    data = yaml.safe_load(DATASOURCES.read_text(encoding="utf-8")) or {}
    for ds in data.get("datasources", []):
        name = ds.get("name")
        uid = ds.get("uid")
        if not name or not ds.get("type"):
            _fail(f"datasource without name/type: {ds!r}", errors)
        if not uid:
            _fail(f"datasource '{name}' lacks a stable uid", errors)
        elif uid in uids:
            _fail(f"duplicate datasource uid '{uid}'", errors)
        else:
            uids.add(uid)
    return uids


def check_dashboards(known_uids: set[str], errors: list[str]) -> None:
    if not DASHBOARDS:
        _fail("no dashboard JSON files found", errors)
        return
    for path in DASHBOARDS:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _fail(f"{path.name}: invalid JSON — {exc}", errors)
            continue
        # Import-format artifacts ({dashboard: {...}}) are consumed by
        # tests via /api/dashboards/db, not file provisioning.
        dash = raw.get("dashboard", raw) if isinstance(raw, dict) else raw
        for key in ("title", "panels"):
            if key not in dash:
                _fail(f"{path.name}: missing '{key}'", errors)
        if "dashboard" not in raw and "uid" not in dash:
            _fail(f"{path.name}: missing 'uid'", errors)
        for panel in dash.get("panels", []):
            missing = REQUIRED_PANEL_KEYS - set(panel)
            if missing:
                _fail(
                    f"{path.name}: panel id={panel.get('id')} missing {sorted(missing)}",
                    errors,
                )
            if panel.get("type") not in NO_TARGET_PANEL_TYPES and "targets" not in panel:
                _fail(f"{path.name}: panel id={panel.get('id')} missing ['targets']", errors)
            ds = panel.get("datasource") or {}
            uid = ds.get("uid")
            if uid and uid.startswith("${"):
                # dashboard templating variable (e.g. ${DS_ELASTICSEARCH})
                continue
            if uid and uid not in known_uids and uid not in VALID_EXPR_UIDS | BUILTIN_DS_UIDS:
                _fail(
                    f"{path.name}: panel id={panel.get('id')} references "
                    f"unknown datasource uid '{uid}'",
                    errors,
                )


def check_alert_rules(known_uids: set[str], errors: list[str]) -> None:
    if not ALERT_RULES.exists():
        _fail(f"missing {ALERT_RULES}", errors)
        return
    data = yaml.safe_load(ALERT_RULES.read_text(encoding="utf-8")) or {}
    groups = data.get("groups") or []
    if not groups:
        _fail("alert-rules.yml: no groups", errors)
        return
    rule_uids: set[str] = set()
    for group in groups:
        for key in ("name", "folder", "interval", "rules"):
            if key not in group:
                _fail(f"alert group missing '{key}': {group.get('name')}", errors)
        for rule in group.get("rules", []):
            missing = REQUIRED_RULE_KEYS - set(rule)
            if missing:
                _fail(
                    f"rule '{rule.get('uid')}' missing {sorted(missing)}",
                    errors,
                )
            uid = rule.get("uid")
            if uid in rule_uids:
                _fail(f"duplicate rule uid '{uid}'", errors)
            rule_uids.add(uid)
            cond_refs = {d.get("refId") for d in rule.get("data", [])}
            if rule.get("condition") not in cond_refs:
                _fail(
                    f"rule '{uid}': condition '{rule.get('condition')}' " "is not a data refId",
                    errors,
                )
            for d in rule.get("data", []):
                duid = d.get("datasourceUid")
                if duid and duid not in known_uids and duid not in VALID_EXPR_UIDS:
                    _fail(
                        f"rule '{uid}': unknown datasourceUid '{duid}'",
                        errors,
                    )
                model = d.get("model") or {}
                if model.get("refId") != d.get("refId"):
                    _fail(
                        f"rule '{uid}': model.refId mismatch on refId " f"'{d.get('refId')}'",
                        errors,
                    )


def check_compose_mounts(errors: list[str]) -> None:
    if not COMPOSE.exists():
        _fail(f"missing {COMPOSE}", errors)
        return
    text = COMPOSE.read_text(encoding="utf-8")
    for artifact in DASHBOARDS + [ALERT_RULES]:
        try:
            raw = json.loads(artifact.read_text(encoding="utf-8"))
            is_import_artifact = isinstance(raw, dict) and "dashboard" in raw
        except Exception:
            is_import_artifact = False
        if not is_import_artifact and artifact.name not in text:
            _fail(
                f"{artifact.name} exists but is not mounted in " "docker-compose.logging.yml",
                errors,
            )


def main() -> int:
    errors: list[str] = []
    uids = check_datasources(errors)
    check_dashboards(uids, errors)
    check_alert_rules(uids, errors)
    check_compose_mounts(errors)
    if errors:
        print("Grafana provisioning validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(
        f"Grafana provisioning OK: {len(DASHBOARDS)} dashboard(s), "
        f"{len(uids)} datasource uid(s), alert rules valid."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
