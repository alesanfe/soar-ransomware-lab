"""Clean stale Shuffle executions from OpenSearch and abort them via API.

When Shuffle workflows are interrupted (e.g. test failures, container
restarts, Orborus crashes), executions remain stuck in ``EXECUTING``
state inside OpenSearch.  The Orborus worker orchestrator keeps polling
these stale records and spins up new worker containers for them,
eventually saturating Docker Desktop's worker pool (max 10 concurrent)
and throttling new legitimate executions.

This script performs a three-step cleanup:

1.  **OpenSearch purge** — delete every document from the
    ``workflowexecution-000001`` and ``workflowqueue-shuffle`` indices.
2.  **API abort** — call ``DELETE /api/v1/executions/<id>`` for every
    execution still marked ``EXECUTING`` across all workflows.
3.  **Worker removal** — ``docker rm -f`` every ``worker-*`` and
    ``Shuffle-Tools_*`` container so Orborus starts from a clean slate.

The script is safe to run at any time (idempotent) and is designed to
be invoked before ``make test-e2e`` to guarantee a clean Shuffle state.

Usage (inside the ``soar_api`` container)::

    python /app/scripts/maintenance/clean_shuffle_executions.py

Exit codes:
    0 — cleanup completed (regardless of how many records were purged)
    1 — unrecoverable error (OpenSearch unreachable, etc.)
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any

import requests
import urllib3

from soar_lab.common.constants import (
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

logger = logging.getLogger(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Configuration (read from .env.full via dotenv, fall back to os.environ)
# ---------------------------------------------------------------------------


def _load_env() -> None:
    """Load .env.full if dotenv is available (it is inside the container)."""
    try:
        from dotenv import load_dotenv

        for candidate in ("/app/.env.full", ".env.full"):
            if os.path.isfile(candidate):
                load_dotenv(candidate, override=True)
                break
    except ImportError:
        pass


_load_env()

_ES_USER = os.environ.get("SHUFFLE_OPENSEARCH_USER", "admin")
_ES_PASS = os.environ.get("SHUFFLE_OPENSEARCH_PASSWORD", "")
_ES_URL = os.environ.get("SHUFFLE_OPENSEARCH_URL", "http://opensearch:9200")
_API_KEY = os.environ.get(
    "SHUFFLE_DEFAULT_APIKEY",
    "DLLOPNJqbL2zlJX0icyGb1EJ1uBJpvefJOdW6G3hlDhuHW5gd4FqVV6atmmlu3Fi",
)
_SHUFFLE_URL = os.environ.get("SHUFFLE_BACKEND_URL", "http://shuffle-backend:5001")

_EXECUTION_INDICES = (
    "workflowexecution-000001",
    "workflowqueue-shuffle",
)


# ---------------------------------------------------------------------------
# Step 1 — OpenSearch purge
# ---------------------------------------------------------------------------


def _purge_opensearch() -> dict[str, int]:
    """Delete stale (EXECUTING/ABORTED/FAILED) executions from OpenSearch.

    FINISHED executions are preserved so that reports can use them for
    statistics.  The ``workflowqueue-shuffle`` index is purged entirely
    because it only contains pending queue items.

    Returns a mapping of ``index_name -> deleted_count``.
    """
    deleted: dict[str, int] = {}
    auth = (_ES_USER, _ES_PASS)
    headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}

    # Only delete non-FINISHED executions from workflowexecution-000001
    stale_query = {
        "query": {
            "bool": {
                "should": [
                    {"term": {"status": "EXECUTING"}},
                    {"term": {"status": "ABORTED"}},
                    {"term": {"status": "FAILED"}},
                ],
                "must_not": [{"term": {"status": "FINISHED"}}],
            }
        }
    }

    for index in _EXECUTION_INDICES:
        try:
            # workflowqueue-shuffle: purge all (only pending items)
            # workflowexecution-000001: only purge stale (not FINISHED)
            query = {"query": {"match_all": {}}} if index == "workflowqueue-shuffle" else stale_query
            r = requests.post(
                f"{_ES_URL}/{index}/_delete_by_query",
                headers=headers,
                json=query,
                auth=auth,
                timeout=30,
                verify=False,
            )
            if r.status_code == 404:
                # Index doesn't exist yet — nothing to delete.
                deleted[index] = 0
            elif r.status_code == 200:
                deleted[index] = r.json().get("deleted", 0)
            else:
                logger.warning(f"  WARN: {index}: HTTP {r.status_code} — {r.text[:200]}")
                deleted[index] = 0
        except Exception as exc:
            logger.warning(f"  WARN: {index}: {exc}")
            deleted[index] = 0

    return deleted


# ---------------------------------------------------------------------------
# Step 2 — API abort
# ---------------------------------------------------------------------------


def _abort_executions() -> int:
    """Abort every ``EXECUTING`` execution across all workflows via the Shuffle
    REST API.

    Returns the number of executions aborted.
    """
    headers = {HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {_API_KEY}"}
    aborted = 0

    try:
        r = requests.get(
            f"{_SHUFFLE_URL}/api/v1/workflows",
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        wfs = r.json()
        if isinstance(wfs, dict) and "data" in wfs:
            wfs = wfs["data"]
    except Exception as exc:
        logger.warning(f"  WARN: cannot list workflows: {exc}")
        return 0

    for wf in wfs:
        wf_id = wf.get("id")
        if not wf_id:
            continue
        try:
            r = requests.get(
                f"{_SHUFFLE_URL}/api/v1/workflows/{wf_id}/executions",
                headers=headers,
                timeout=15,
            )
            execs = r.json()
            if isinstance(execs, dict) and "data" in execs:
                execs = execs["data"]
            for e in execs:
                if e.get("status") in ("EXECUTING", "ABORTED"):
                    eid = e.get("execution_id")
                    if not eid:
                        continue
                    try:
                        requests.delete(
                            f"{_SHUFFLE_URL}/api/v1/executions/{eid}",
                            headers=headers,
                            timeout=10,
                        )
                        aborted += 1
                    except Exception:
                        pass
        except Exception:
            pass

    return aborted


# ---------------------------------------------------------------------------
# Step 3 — Worker container removal
# ---------------------------------------------------------------------------


def _remove_workers() -> int:
    """Force-remove every ``worker-*`` and ``Shuffle-Tools_*`` Docker
    container.

    Returns the number of containers removed.
    """
    removed = 0
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        names = result.stdout.splitlines()
    except Exception as exc:
        logger.warning(f"  WARN: cannot list containers: {exc}")
        return 0

    for name in names:
        name = name.strip()
        if name.startswith("worker-") or name.startswith("Shuffle-Tools_"):
            try:
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    capture_output=True,
                    timeout=15,
                )
                removed += 1
            except Exception:
                pass

    return removed


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def clean(*, restart_orborus: bool = False, verbose: bool = True) -> dict[str, Any]:
    """Run the full three-step cleanup.

    Parameters
    ----------
    restart_orborus
        If ``True``, stop the Orborus container before cleanup and restart
        it afterwards.  This prevents Orborus from re-creating workers
        while we are deleting executions.  Defaults to ``False`` because
        restarting the backend causes webhook timeouts for ~60s.
    verbose
        Print progress messages to stdout.

    Returns
    -------
    dict
        Summary with keys ``purged``, ``aborted``, ``workers_removed``.
    """
    summary: dict[str, Any] = {}

    # --- Stop Orborus to avoid race conditions ---------------------------
    if restart_orborus:
        if verbose:
            logger.info("Stopping Orborus to prevent worker re-creation...")
        try:
            subprocess.run(
                ["docker", "stop", "soar_orborus"],
                capture_output=True,
                timeout=30,
            )
        except Exception as exc:
            logger.warning(f"  WARN: cannot stop orborus: {exc}")

    # --- Step 1: OpenSearch purge ----------------------------------------
    if verbose:
        logger.info("Step 1: Purging stale executions from OpenSearch...")
    summary["purged"] = _purge_opensearch()
    if verbose:
        for idx, count in summary["purged"].items():
            logger.info(f"  {idx}: deleted {count} documents")

    # --- Step 2: API abort -----------------------------------------------
    if verbose:
        logger.info("Step 2: Aborting EXECUTING executions via Shuffle API...")
    summary["aborted"] = _abort_executions()
    if verbose:
        logger.info(f"  Aborted {summary['aborted']} executions")

    # --- Step 3: Worker removal ------------------------------------------
    if verbose:
        logger.info("Step 3: Removing orphaned worker containers...")
    summary["workers_removed"] = _remove_workers()
    if verbose:
        logger.info(f"  Removed {summary['workers_removed']} worker containers")

    # --- Restart Orborus -------------------------------------------------
    if restart_orborus:
        if verbose:
            logger.info("Restarting Orborus and Shuffle backend...")
        try:
            subprocess.run(
                ["docker", "restart", "soar_shuffle_backend"],
                capture_output=True,
                timeout=60,
            )
            time.sleep(10)
            subprocess.run(
                ["docker", "start", "soar_orborus"],
                capture_output=True,
                timeout=30,
            )
            time.sleep(10)
        except Exception as exc:
            logger.warning(f"  WARN: cannot restart orborus/backend: {exc}")

    if verbose:
        print("Cleanup complete.")
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    try:
        clean()
    except Exception as exc:
        logger.error(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
