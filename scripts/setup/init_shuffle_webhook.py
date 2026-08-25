#!/usr/bin/env python3
"""
Initialize Shuffle with a complete SOAR workflow that orchestrates:
  1. Webhook  — receive alerts from the SIEM simulator
  2. TheHive  — create incident case
  3. Cortex   — analyze ransomware IOCs (hash, IP)
  4. MISP     — look for indicators in threat intelligence
  5. ES/HTTP  — index the alert in Elasticsearch for OpenSearch Dashboards

This file is a **slim orchestrator**: it coordinates the high-level
steps and delegates the details to the ``shuffle_workflow`` package.

Usage:
  python scripts/setup/init_shuffle_webhook.py

Environment variables (only basic credentials that do not rotate):
  SHUFFLE_URL      Shuffle URL (default: https://localhost:8081)
  ES_URL           Elasticsearch URL (default: http://localhost:9201)
  THEHIVE_URL      TheHive URL (default: http://localhost:9000)
  CORTEX_URL       Cortex URL (default: http://localhost:9001)
  MISP_URL         MISP URL (default: https://localhost:8082)
  SHUFFLE_USER     Shuffle user (default: admin)
  SHUFFLE_PASS     Shuffle password
  THEHIVE_ADMIN_USER     TheHive admin user (default: admin)
  THEHIVE_ADMIN_PASSWORD TheHive admin password (default: admin123)
  CORTEX_ADMIN_USER      Cortex admin user (default: admin)
  CORTEX_ADMIN_PASSWORD  Cortex admin password (default: admin123)
  MISP_ADMIN_EMAIL       MISP admin email (default: admin@admin.test)
  MISP_ADMIN_PASSWORD    MISP admin password (default: admin)

The API keys are obtained dynamically from each service at runtime.
"""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

try:
    from . import fix_org_users
except ImportError:
    import fix_org_users

# ── Import the shuffle_workflow package ────────────────────────────────────────
try:
    from .shuffle_workflow import (
        clients,
        cortex_setup,
        credentials,
        es_fixes,
        shuffle_setup,
        test_mode,
        workflow_actions,
        workflow_definition,
    )
    from .shuffle_workflow import config as wf_config
except ImportError:
    # Running as a standalone script (not inside the package)
    from shuffle_workflow import (
        clients,  # type: ignore[no-redef]
        cortex_setup,  # type: ignore[no-redef]
        credentials,  # type: ignore[no-redef]
        es_fixes,  # type: ignore[no-redef]
        shuffle_setup,  # type: ignore[no-redef]
        test_mode,  # type: ignore[no-redef]
        workflow_actions,  # type: ignore[no-redef]
        workflow_definition,  # type: ignore[no-redef]
    )
    from shuffle_workflow import config as wf_config  # type: ignore[no-redef]

# Re-expose ShuffleClient at the module level so that integration tests
# can patch it via ``patch("scripts.setup.init_shuffle_webhook.ShuffleClient")``.
ShuffleClient = clients.get_shuffle_client_class()


def init_shuffle_webhook():
    # ── 0. Fast path for integration tests (patched ShuffleClient) ─────────────
    # Use the module-level ShuffleClient (which tests patch via
    # ``patch("scripts.setup.init_shuffle_webhook.ShuffleClient")``) rather
    # than ``clients.get_shuffle_client_class()`` so the test seam works.
    _test_result = test_mode.maybe_run_test_mode(ShuffleClient)
    if _test_result is not None:
        return _test_result

    logger.info("[init_shuffle_webhook] Connecting to %s ...", wf_config.SHUFFLE_URL)

    # ── 1. Wait for Shuffle to be ready ────────────────────────────────────────
    session = clients.create_shuffle_session()
    clients.wait_for_shuffle_ready(session)

    # ── 2. Fix ES indices (users mapping + workflow execution mapping) ────────
    es_fixes.fix_es_users_mapping()
    es_fixes.fix_workflow_execution_mapping()

    # ── 2b. Sync apikey so DB matches .env.full (prevents Orborus auth failures)
    es_fixes.sync_apikey()

    # ── 3. Validate API key ────────────────────────────────────────────────────
    _shuffle_apikey = clients.validate_api_key(session)

    # ── 3b. If validate_api_key generated a new key, sync it back to .env.full
    #       and Elasticsearch so Orborus and the keepalive loop use the same key.
    if _shuffle_apikey and _shuffle_apikey != os.environ.get("SHUFFLE_DEFAULT_APIKEY", ""):
        es_fixes.update_env_file("SHUFFLE_DEFAULT_APIKEY", _shuffle_apikey)
        os.environ["SHUFFLE_DEFAULT_APIKEY"] = _shuffle_apikey
        es_fixes.sync_apikey()
        logger.info("  SHUFFLE_DEFAULT_APIKEY updated in .env.full and ES")

    # ── 4. Resolve API keys from TheHive, Cortex, MISP ─────────────────────────
    logger.info("  Getting API keys from the services...")
    thehive_key, cortex_key, misp_key = credentials.resolve_all_keys()

    # ── 5. Search for previous workflows with the same name ────────────────────
    logger.info("  Searching for workflow '%s'...", wf_config.WF_NAME)
    wfs_r = session.get(f"{wf_config.SHUFFLE_URL}/api/v1/workflows", timeout=60)
    wfs = wfs_r.json() if isinstance(wfs_r.json(), list) else []
    old_workflows = [w for w in wfs if w.get("name") == wf_config.WF_NAME]
    old_workflow_ids = [w["id"] for w in old_workflows]

    # ── 6. Resolve SHUFFLE_DEFAULT_APIKEY (required for app downloads) ─────────
    _shuffle_apikey = os.environ.get("SHUFFLE_DEFAULT_APIKEY", "")
    if not _shuffle_apikey and os.path.exists(wf_config.ENV_FILE):
        import re as _re2

        with open(wf_config.ENV_FILE) as _f:
            _m = _re2.search(r"^SHUFFLE_DEFAULT_APIKEY=(.+)$", _f.read(), _re2.MULTILINE)
        if _m:
            _shuffle_apikey = _m.group(1).strip()
    if not _shuffle_apikey:
        logger.error("Missing SHUFFLE_DEFAULT_APIKEY")
        sys.exit(1)

    # ── 7. Install official apps and get their IDs ─────────────────────────────
    logger.info("  Installing official apps required by the workflow...")
    app_ids = clients.get_app_ids(session, wf_config.SHUFFLE_URL)
    app_id_http = app_ids.get("http", "")
    app_id_shuffle_tools = app_ids.get("Shuffle Tools", app_ids.get("http", ""))

    # ── 8. Discover and select Cortex analyzers ────────────────────────────────
    cortex_basic = workflow_actions._cortex_basic_auth()
    es_basic = workflow_actions._es_basic_auth()

    analyzer_info = cortex_setup.discover_and_select_analyzers(cortex_basic, app_id_http)

    # ── 9. Build the WorkflowContext ───────────────────────────────────────────
    _loki_start_ns = int((time.time() - 7200) * 1e9)
    _loki_end_ns = int((time.time() + 7200) * 1e9)

    ctx = workflow_actions.WorkflowContext(
        thehive_key=thehive_key,
        cortex_key=cortex_key,
        misp_key=misp_key,
        app_id_http=app_id_http,
        app_id_shuffle_tools=app_id_shuffle_tools,
        cortex_basic=cortex_basic,
        es_basic=es_basic,
        loki_start_ns=_loki_start_ns,
        loki_end_ns=_loki_end_ns,
        **analyzer_info,
    )

    # ── 10. Build the workflow definition ──────────────────────────────────────
    wf_def = workflow_definition.build_workflow_definition(ctx)

    # ── 11. Ensure 'Shuffle' environment exists ────────────────────────────────
    org_id = shuffle_setup.ensure_shuffle_environment(session)

    # ── 12. Fix org users in ES ────────────────────────────────────────────────
    fix_org_users.fix_organization_users(
        wf_config.SHUFFLE_DATA_URL, wf_config.SHUFFLE_DATA_USER, wf_config.SHUFFLE_DATA_PASS
    )
    es_fixes.fix_es_users_mapping()

    # ── 13. Create the workflow ────────────────────────────────────────────────
    wf = shuffle_setup.create_workflow(session, wf_def)
    wf_id = wf["id"]

    # Get the real trigger UUID
    wf_detail = session.get(f"{wf_config.SHUFFLE_URL}/api/v1/workflows/{wf_id}", timeout=60).json()
    triggers = wf_detail.get("triggers", [])
    trigger_id = triggers[0]["id"] if triggers else workflow_actions.TRIGGER_NODE
    if not org_id:
        org_id = wf_detail.get("org_id", "")
    logger.info("  Trigger ID : %s", trigger_id)
    logger.info("  Org ID     : %s", org_id)

    # ── 14. Fix branches and startnode ─────────────────────────────────────────
    org_id, _ = shuffle_setup.fix_branches_and_startnode(session, wf_id, trigger_id)

    # ── 15. Delete old workflows ───────────────────────────────────────────────
    shuffle_setup.delete_old_workflows(session, old_workflow_ids, wf_id)

    # ── 16. Register hook in Elasticsearch ─────────────────────────────────────
    shuffle_setup.register_hook_in_es(trigger_id, wf_id, org_id)

    # ── 17. Create soar-alerts and soar-metrics indices ────────────────────────
    shuffle_setup.ensure_es_indices()

    # ── 18. Compute webhook URLs ───────────────────────────────────────────────
    webhook_url_internal = f"{wf_config.SHUFFLE_URL}/api/v1/hooks/webhook_{trigger_id}"
    _external_base = (
        wf_config.SHUFFLE_URL
        .replace("shuffle-backend", "localhost")
        .replace("soar_shuffle_backend", "localhost")
        .replace("shuffle-frontend", "localhost")
        .replace("soar_shuffle_frontend", "localhost")
    )
    webhook_url = f"{_external_base}/api/v1/hooks/webhook_{trigger_id}"
    logger.info("  Webhook URL: %s", webhook_url)

    # ── 19. Save webhook info for E2E tests ────────────────────────────────────
    shuffle_setup.save_webhook_info(trigger_id, wf_id, org_id, webhook_url_internal, webhook_url)

    # ── 20. Print summary ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  ACTIVE WEBHOOK : {webhook_url}")
    print(f"  Workflow       : {wf_config.WF_NAME}")
    print("  Actions        :")
    print(f"    TheHive  -> create case at   {wf_config.THEHIVE_URL}")
    print(f"    Cortex   -> analyze hash+IP  {wf_config.CORTEX_URL}")
    print(f"    MISP     -> search IOC       {wf_config.MISP_URL}")
    print(f"    ES       -> index alerts     {wf_config.ES_URL}/soar-alerts")
    print()
    print("  Use with:")
    print(f'    make simulate SIMULATE_WEBHOOK="{webhook_url}"')
    print("=" * 60)

    # ── 21. Import Grafana KPI dashboard ───────────────────────────────────────
    shuffle_setup.import_grafana_dashboard()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        credentials.validate_required_passwords()
        init_shuffle_webhook()
    except (RuntimeError, ConnectionError) as exc:
        logger.error("[FATAL] %s", exc)
        sys.exit(1)
