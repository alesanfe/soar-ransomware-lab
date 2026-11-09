#!/usr/bin/env python3
"""Property-based API contract fuzzing against the live OpenAPI spec.

Schemathesis + Hypothesis generate inputs for every GET operation and
assert the API conforms to its published OpenAPI schema. Only GET
operations are fuzzed: POST/DELETE have real side effects downstream
(alert ingestion -> Shuffle executions, TheHive cases, containment
actions) and are covered by dedicated integration/E2E suites.

Two tiers:
- strict — core ops (`/api/v1/*`, `/analytics/*`, `/health*`): no 5xx.
- proxy — `/soar/*` ops forward to Shuffle/Cortex/MISP/ES; a typed 502
  for a downstream failure is designed behaviour (RES-02), so
  `not_a_server_error` is skipped there while every other check stays.

Requires the live stack (``api:8000`` reachable) — run inside the container:

    docker exec soar_api python -m pytest \\
        tests/integration/test_schemathesis_fuzz.py -m requires_docker
"""

import os
from pathlib import Path

import pytest
import requests

schemathesis = pytest.importorskip(
    "schemathesis",
    reason="schemathesis not installed — pip install -e .[test]",
)
from dotenv import load_dotenv
from hypothesis import HealthCheck, settings
from schemathesis.checks import not_a_server_error
from schemathesis.generation import GenerationMode
from schemathesis.specs.openapi.checks import ignored_auth

pytestmark = [pytest.mark.requires_docker, pytest.mark.integration]

_API_BASE = os.getenv("API_URL", "http://api:8000")
_TIMEOUT = 15
_MAX_EXAMPLES = int(os.getenv("SCHEMATHESIS_MAX_EXAMPLES", "10"))

# Match tests/conftest.py: .env.full (if mounted) wins over process env.
for _env in (Path("/app/.env.full"), Path(".env.full")):
    if _env.is_file():
        load_dotenv(_env, override=True)
        break

_SERVICE_HEADERS = {}
_svc_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")
if _svc_token:
    _SERVICE_HEADERS["X-Service-Token"] = _svc_token


def _load_schema():
    exc = None
    for _ in range(3):
        try:
            resp = requests.get(f"{_API_BASE}/openapi.json", timeout=_TIMEOUT)
            resp.raise_for_status()
            return schemathesis.openapi.from_dict(resp.json())
        except requests.RequestException as err:
            exc = err
    pytest.skip(f"live API unreachable at {_API_BASE}: {exc}", allow_module_level=True)


def _configure(schema):
    """Common generation knobs for both tiers."""
    # Positive-mode only: parameter values are still fuzzed to schema-valid
    # extremes, but generated *invalid* requests (missing auth, wrong types)
    # race the global rate-limiter — a 429 fired before the expected 401/422
    # is legitimate middleware ordering, not a contract violation.
    schema.config.generation.update(modes=[GenerationMode.POSITIVE])
    # Throttle client-side so the fuzz stays under the API's 300 req/min
    # sliding window — a 429 here would be our own load, not a defect.
    schema.config.update(rate_limit="4/s")
    return schema


_base = _load_schema()
# /soar/cortex/jobs/summary aggregates the full Cortex job history (~15k
# jobs) per request in-process; fuzzing it serially saturates the single
# uvicorn worker. It is covered by dedicated integration tests instead.
_base = _base.exclude(path="/soar/cortex/jobs/summary")

strict_schema = _configure(_base.include(method="GET").exclude(path_regex="^/soar/"))
proxy_schema = _configure(_base.include(method="GET", path_regex="^/soar/"))

_SETTINGS = {
    "max_examples": _MAX_EXAMPLES,
    "deadline": None,
    "derandomize": True,
    "suppress_health_check": [HealthCheck.function_scoped_fixture],
}


@strict_schema.parametrize()
@settings(**_SETTINGS)
def test_openapi_contract_strict(case):
    """Core ops: spec-conformant responses, never a 5xx.

    ``ignored_auth`` is excluded because the valid X-Service-Token header
    is attached to every generated request — the check would flag
    legitimate service-token auth as "ignored".
    """
    case.call_and_validate(
        base_url=_API_BASE,
        headers=_SERVICE_HEADERS,
        excluded_checks=[ignored_auth],
        timeout=60,
    )


@proxy_schema.parametrize()
@settings(**_SETTINGS)
def test_openapi_contract_proxy(case):
    """Downstream-proxy ops: typed 502s are designed (RES-02)."""
    case.call_and_validate(
        base_url=_API_BASE,
        headers=_SERVICE_HEADERS,
        excluded_checks=[ignored_auth, not_a_server_error],
        timeout=60,
    )
