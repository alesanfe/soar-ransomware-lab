"""Centralized E2E timeouts (E2E-TIME-002).

One table, one accessor: ``self.timeout("workflow")``.  Every value can be
overridden via ``E2E_TIMEOUT_<KIND>`` env vars, and every poll loop should
derive its deadline from here instead of embedding magic numbers.

Initial values follow the table in docs/18 §8 (E2E-TIME-002).
"""

from __future__ import annotations

import os

# Seconds per operation class.  Justification is carried in the comment —
# a timeout without a reason is a magic number with a name.
TIMEOUTS: dict[str, int] = {
    "api_local": 5,  # loopback/localhost HTTP round-trip
    "http_default": 30,  # generic in-cluster HTTP call
    "healthcheck": 60,  # service readiness after (re)start
    "case_creation": 120,  # TheHive case visible after workflow step
    "workflow": 300,  # normal Shuffle workflow end-to-end
    "workflow_slow": 600,  # workflow with Cortex analyzer fan-out
    "cortex_analyzer": 120,  # single analyzer job
    "misp_query": 60,  # MISP attribute/event search
    "misp_restart": 600,  # MISP is the slowest service to recycle
    "es_index": 30,  # document visible after refresh
    "loki_ingest": 90,  # promtail ship + Loki index latency
    "cleanup": 120,  # transactional cleanup budget
    "queue_drain": 240,  # Shuffle queue drain under load
}

ENV_PREFIX = "E2E_TIMEOUT_"


def timeout_for(kind: str, env: dict[str, str] | None = None) -> int:
    """Return the configured timeout for ``kind`` (seconds).

    Resolution order: explicit env override → TIMEOUTS table → KeyError
    (an unknown kind is a programming error, not a config issue).
    """
    source = env if env is not None else os.environ
    override = source.get(f"{ENV_PREFIX}{kind.upper()}")
    if override is not None:
        return int(override)
    if kind not in TIMEOUTS:
        raise KeyError(f"Unknown timeout kind '{kind}'. Registered: {sorted(TIMEOUTS)}")
    return TIMEOUTS[kind]
