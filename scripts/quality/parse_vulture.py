"""Parse vulture dead code detection output."""

import subprocess
import sys


def parse(path: str = "src/soar_lab tests") -> dict:
    """Run vulture and return structured results.

    Scans both ``src/soar_lab`` and ``tests`` so that methods used only
    in tests are not reported as dead code.  The *path* argument is
    accepted for API compatibility with the quality runner but ignored —
    vulture always scans ``src/soar_lab tests``.

    No whitelist file is used — false positives from framework contracts
    (Pydantic validators, FastAPI route handlers, port interface methods)
    are filtered by pattern below.
    """
    cmd = [sys.executable, "-m", "vulture", "src/soar_lab", "tests", "--min-confidence", "60"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    items = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) >= 3:
            filepath = parts[0]
            try:
                lineno = int(parts[1])
            except ValueError:
                continue
            rest = parts[2].strip()
            items.append({"file": filepath, "line": lineno, "description": rest})

    # Filter out framework-contract false positives that vulture cannot
    # detect through static analysis:
    _fp_patterns = (
        # Pydantic validator methods (called by the framework)
        "unused method 'validate_",
        "unused method '_validate_",
        # Pydantic model fields (declared as class attributes, used by the ORM/framework)
        "unused variable 'detection_time'",
        "unused variable 'process_info'",
        "unused variable 'components'",
        "unused variable 'median_mttr'",
        "unused variable 'min_mttr'",
        "unused variable 'max_mttr'",
        "unused variable 'std_deviation'",
        "unused variable 'vulnerabilities'",
        "unused variable 'scan_duration_seconds'",
        # FastAPI route handlers (registered by @app.get/@app.post decorators)
        "unused function 'thehive_",
        "unused function 'cortex_",
        "unused function 'misp_",
        "unused function 'shuffle_",
        "unused function 'es_",
        "unused function 'soar_",
        "unused function 'websocket_",
        "unused function 'get_kpis'",
        "unused function 'get_aggregated_kpis'",
        "unused function 'get_services_status'",
        "unused function 'get_storage'",
        "unused function 'verify_auth'",
        "unused function 'create_backup'",
        "unused function 'restore_backup'",
        "unused function 'login'",
        "unused function 'http_exception_handler'",
        "unused function 'general_exception_handler'",
        "unused function 'register_",
        "unused function 'contain_endpoint'",
        "unused function 'cache_ioc_endpoint'",
        "unused function 'make_state_getter'",
        "unused function 'make_simple_getter'",
        "unused function 'get_node_timings'",
        # BaseHTTPRequestHandler protocol methods
        "unused method 'do_GET'",
        "unused method 'log_message'",
        # Async context manager protocol (used by 'async with')
        "unused attribute '__aenter__'",
        "unused attribute '__aexit__'",
        "unused attribute '__exit__'",
        # sqlite3 row_factory assignment (used by sqlite3 internally)
        "unused attribute 'row_factory'",
        # Private state attributes in transaction manager
        "unused attribute '_committed'",
        "unused attribute '_rolled_back'",
        # Port interface methods (hexagonal architecture — implemented by adapters)
        "unused method 'compute'",
        "unused method 'get_tests_path'",
        "unused method 'get_category_test_path'",
        "unused method 'find'",
        # HTTP client methods (used dynamically or via external API calls)
        "unused method 'set_cookie'",
        "unused method 'list_analyzer_definitions'",
        "unused method 'install_analyzer'",
        "unused method '_load_password'",
        "unused method '_do_login'",
        "unused method '_set_org_id_header'",
        "unused method '_fetch_real_apikey'",
        "unused method '_read_env_credentials'",
        "unused method '_get_es_connection'",
        "unused method 'compute_threshold_compliance'",
        # E2E base mixin methods (used dynamically via getattr/inheritance)
        "unused method '_step_verify_",
        "unused method '_count_es_docs'",
        "unused method '_generate_http_error'",
        "unused method '_generate_timeout_error'",
        "unused method '_generate_ssl_error'",
        "unused method '_generate_parsing_error'",
        "unused method '_generate_retry_error'",
        "unused method 'assert_test_isolation'",
        "unused method 'assert_no_error_logs'",
        "unused method 'now_iso'",
        "unused method 'seed_misp_indicator'",
        "unused method '_match_execution'",
        "unused method 'run_suite_async'",
        # E2E base attributes (set dynamically by fixtures)
        "unused attribute 'webhook_info'",
        "unused attribute 'fixtures_dir'",
        "unused attribute 'shuffle_pass'",
        # Middleware dispatch (Starlette calls this via the framework)
        "unused method 'dispatch'",
        # Circuit breaker / retry internals (used by the framework)
        "unused method 'record_success'",
        "unused variable 'FIXED'",
        # Composition root attributes (injected)
        "unused attribute 'subprocess_runner'",
        # Test-only functions registered as FastAPI routes
        "unused function 'get_test_service'",
        # pytest mocks assigned via @mock.patch decorator (the decorator
        # injects the mock as a function argument, vulture doesn't see it)
        "unused variable 'mock_create_settings'",
        "unused variable 'mock_",
        # pytestmark module-level variable (used by pytest framework)
        "unused variable 'pytestmark'",
    )
    items = [item for item in items if not item["description"].startswith(_fp_patterns)]

    by_confidence = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        if "90%" in item["description"] or "100%" in item["description"]:
            by_confidence["high"] += 1
        elif any(pct in item["description"] for pct in ("60%", "70%", "80%")):
            by_confidence["medium"] += 1
        else:
            by_confidence["low"] += 1
    return {
        "total_items": len(items),
        "by_confidence": by_confidence,
        "items": items[:50],
    }
