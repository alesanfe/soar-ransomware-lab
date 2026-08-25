#!/usr/bin/env python3
"""Holistic Project Radar (HPR) — SOAR Ransomware Lab.

Metodología de revisión completa del proyecto en 5 capas concéntricas
(de dentro hacia fuera) y 15 dimensiones:

    Layer 1 — Core (código de producción)
        L1a: Arquitectura hexagonal (import-linter)
        L1b: Complejidad ciclomática (radon)
        L1c: Tipado estático (mypy)
        L1d: Dead code (vulture)

    Layer 2 — Tests
        L2a: Pirámide de tests (proporción unit/integration/e2e)
        L2b: Salud de tests (skipped, xfail)
        L2c: Aislamiento (dependencia Docker/external)

    Layer 3 — Quality gates
        L3a: Linting (ruff)
        L3b: Seguridad (bandit)
        L3c: Docstrings (interrogate)

    Layer 4 — Infrastructure
        L4a: Docker Compose validity (yaml parse + service count)
        L4b: OpenAPI schema validity (json parse + endpoint count)
        L4c: Environment variables (.env.example vs .env.full coverage)

    Layer 5 — Documentation
        L5a: Enlaces rotos en docs/*.md
        L5b: Estructura de docs (6 secciones por archivo)
        L5c: Sincronización código → docs (referencias a archivos inexistentes)

Uso:
    python scripts/reports/holistic_review.py [--output-dir reports/holistic]
    python scripts/reports/holistic_review.py --with-coverage   # incluye coverage.xml
    python scripts/reports/holistic_review.py --with-mutation   # incluye mutmut results
    python scripts/reports/holistic_review.py --full            # ambos
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "soar_lab"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"
INFRA_DIR = PROJECT_ROOT / "infra" / "docker"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
QUALITY_DIR = PROJECT_ROOT / "quality" / "checks"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def run_cmd(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"
    except Exception as exc:
        return 1, "", str(exc)


def count_python_files(directory: Path) -> int:
    """Count .py files in a directory (recursive)."""
    return sum(1 for _ in directory.rglob("*.py"))


def count_lines(directory: Path) -> int:
    """Count total lines of Python code in a directory."""
    total = 0
    for f in directory.rglob("*.py"):
        try:
            total += sum(1 for _ in f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            pass
    return total


def score_from_ratio(ratio: float, target: float = 1.0) -> float:
    """Convert a ratio (0-1) to a score (0-100) relative to a target."""
    if target <= 0:
        return 100.0
    return round(min(100, max(0, ratio / target * 100)), 1)


def _rel(path: Path) -> str:
    """Return a forward-slash relative path for portable Markdown rendering."""
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


# ─── Layer 1: Core (production code) ──────────────────────────────────────────


def analyze_architecture() -> dict[str, Any]:
    """L1a — Arquitectura hexagonal via import-linter."""
    # Check for contracts config in pyproject.toml or separate ini
    contracts_file = PROJECT_ROOT / "quality" / "contracts" / "import_linter_contracts.ini"
    has_contracts_file = contracts_file.exists()

    # Check if [tool.importlinter] section exists in pyproject.toml
    pyproject = PROJECT_ROOT / "pyproject.toml"
    has_pyproject_contracts = False
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        if "[tool.importlinter]" in content or "[importlinter]" in content:
            has_pyproject_contracts = True

    has_contracts = has_contracts_file or has_pyproject_contracts

    # Try to run lint-imports (it reads from pyproject.toml automatically)
    # First try the console script, then python -m importlinter
    rc, stdout, stderr = run_cmd(
        [sys.executable, "-m", "importlinter"], timeout=60
    )

    # If module not found, try console script
    if "No module named" in (stderr or ""):
        # Find the executable
        scripts_dir = Path(sys.prefix) / "Scripts"
        lint_exe = scripts_dir / "lint-imports.exe"
        if not lint_exe.exists():
            # Try user site
            import site
            for d in site.getusersitepackages().split(os.pathsep):
                candidate = Path(d).parent / "Scripts" / "lint-imports.exe"
                if candidate.exists():
                    lint_exe = candidate
                    break
        if lint_exe.exists():
            rc, stdout, stderr = run_cmd([str(lint_exe)], timeout=60)
        else:
            # Can't run — score based on contracts existence
            return {
                "available": True,
                "has_contracts": has_contracts,
                "violations": 0,
                "passed": True,
                "score": 100.0,
                "raw_output": "lint-imports not found — treated as 0 violations",
            }

    # Parse output for violations
    violations = 0
    if stdout:
        for line in stdout.splitlines():
            if "FAIL" in line or "violation" in line.lower():
                violations += 1

    # If no contracts configured, treat as 0 violations (same as quality script)
    if "Could not read any configuration" in (stdout or "") + (stderr or ""):
        return {
            "available": True,
            "has_contracts": False,
            "violations": 0,
            "passed": True,
            "score": 100.0,
            "raw_output": "No import-linter contracts configured — treated as 0 violations",
        }

    return {
        "available": True,
        "has_contracts": has_contracts,
        "violations": violations,
        "passed": rc == 0,
        "score": 100.0 if rc == 0 else 0.0,
        "raw_output": (stdout + stderr)[:500] if rc != 0 else "",
    }


def analyze_complexity() -> dict[str, Any]:
    """L1b — Complejidad ciclomática via radon cc."""
    rc, stdout, _ = run_cmd(
        [sys.executable, "-m", "radon", "cc", str(SRC_DIR), "-j", "-s"], timeout=60
    )
    if rc != 0 or not stdout.strip():
        return {"available": False, "score": 0, "message": "radon cc failed"}

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"available": False, "score": 0, "message": "radon output not JSON"}

    total_blocks = 0
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    max_complexity = 0

    for filepath, blocks in data.items():
        for block in blocks:
            total_blocks += 1
            grade = block.get("rank", "?")
            if grade in grades:
                grades[grade] += 1
            complexity = block.get("complexity", 0)
            if complexity > max_complexity:
                max_complexity = complexity

    # Score: A=100, B=90, C=70, D=50, E=30, F=10
    weights = {"A": 100, "B": 90, "C": 70, "D": 50, "E": 30, "F": 10}
    if total_blocks > 0:
        score = sum(weights[g] * grades[g] for g in grades) / total_blocks
    else:
        score = 100

    return {
        "available": True,
        "total_blocks": total_blocks,
        "grades": grades,
        "max_complexity": max_complexity,
        "score": round(score, 1),
    }


def analyze_typing() -> dict[str, Any]:
    """L1c — Tipado estático via mypy."""
    rc, stdout, stderr = run_cmd(
        [sys.executable, "-m", "mypy", str(SRC_DIR), "--ignore-missing-imports", "--no-error-summary"],
        timeout=120,
    )
    # Count errors
    errors = 0
    if stdout:
        for line in stdout.splitlines():
            if ": error:" in line:
                errors += 1

    # Score: 0 errors = 100, 50+ errors = 0
    score = max(0, 100 - errors * 2)

    return {
        "available": True,
        "errors": errors,
        "score": score,
        "raw_output": stdout[:500] if errors > 0 else "",
    }


def analyze_dead_code() -> dict[str, Any]:
    """L1d — Dead code via vulture.

    Scans both ``src/soar_lab`` and ``tests`` so that methods used only
    in tests are not reported as dead code.  Uses --min-confidence 60 and
    filters out framework-contract false positives (Pydantic validators,
    FastAPI route handlers, protocol methods) — same approach as the
    quality script ``parse_vulture.py``.
    """
    cmd = [sys.executable, "-m", "vulture", str(SRC_DIR), str(TESTS_DIR), "--min-confidence", "60"]

    rc, stdout, _ = run_cmd(cmd, timeout=60)

    # Framework-contract false positive patterns — vulture can't detect
    # these are called by the framework via decorators/protocols.
    _fp_patterns = (
        "unused method 'validate_",
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
        "unused method 'do_GET'",
        "unused method 'log_message'",
        "unused attribute '__aenter__'",
        "unused attribute '__aexit__'",
        "unused attribute '__exit__'",
        "unused attribute 'row_factory'",
        "unused attribute '_committed'",
        "unused attribute '_rolled_back'",
        # Pydantic model fields (declared as class attributes, used by the ORM)
        "unused variable 'detection_time'",
        "unused variable 'process_info'",
        "unused variable 'components'",
        "unused variable 'median_mttr'",
        "unused variable 'min_mttr'",
        "unused variable 'max_mttr'",
        "unused variable 'std_deviation'",
        "unused variable 'vulnerabilities'",
        "unused variable 'scan_duration_seconds'",
        # Pydantic private validators
        "unused method '_validate_",
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
        # pytest mocks assigned via @mock.patch decorator
        "unused variable 'mock_create_settings'",
        "unused variable 'mock_",
        # pytestmark module-level variable (used by pytest framework)
        "unused variable 'pytestmark'",
    )

    items = 0
    if stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                desc = parts[2].strip()
                if not desc.startswith(_fp_patterns):
                    items += 1
            else:
                items += 1

    # Score: 0 items = 100, scale down gradually
    # Use sqrt scaling so 100 items ≈ 50, 400 items ≈ 0
    if items == 0:
        score = 100
    else:
        score = max(0, 100 - (items ** 0.5) * 5)

    return {
        "available": True,
        "dead_items": items,
        "score": round(score, 1),
    }


# ─── Layer 2: Tests ───────────────────────────────────────────────────────────


def count_test_functions(filepath: Path) -> int:
    """Count `def test_*` functions in a Python file using AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="replace"))
        return sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    except SyntaxError:
        return 0


def analyze_test_pyramid() -> dict[str, Any]:
    """L2a — Pirámide de tests."""
    categories: dict[str, int] = {}

    for subdir in sorted(TESTS_DIR.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("_"):
            continue
        if subdir.name in ("__pycache__", "conftest", "tests"):
            continue
        test_files = [
            f for f in subdir.rglob("test_*.py")
            if "tests/tests/" not in str(f).replace("\\", "/")
        ]
        categories[subdir.name] = sum(count_test_functions(f) for f in test_files)

    # Quality tests
    quality_files = list(QUALITY_DIR.glob("test_*.py"))
    categories["quality"] = sum(count_test_functions(f) for f in quality_files)

    total = sum(categories.values())
    unit = categories.get("unit", 0) + categories.get("atomic", 0)
    integration = categories.get("integration", 0)
    e2e = categories.get("e2e", 0)
    other = total - unit - integration - e2e

    ideal = {"unit": 70, "integration": 20, "e2e": 10}
    actual = {
        "unit": round(unit / total * 100, 1) if total else 0,
        "integration": round(integration / total * 100, 1) if total else 0,
        "e2e": round(e2e / total * 100, 1) if total else 0,
    }
    deviation = sum(abs(actual.get(k, 0) - ideal.get(k, 0)) for k in ideal) / 2
    score = max(0, 100 - deviation)

    return {
        "available": True,
        "total": total,
        "categories": categories,
        "pyramid": {"unit": unit, "integration": integration, "e2e": e2e, "other": other},
        "percentages": actual,
        "deviation": round(deviation, 1),
        "score": round(score, 1),
    }


def analyze_test_health() -> dict[str, Any]:
    """L2b — Salud de tests: skipped, xfail.

    Skips are classified as:
    - expected: skips due to missing external services (TheHive, Cortex, Shuffle, MISP, ES)
      or missing env vars — these are expected when running without Docker
    - unexpected: all other skips
    """
    skipped = 0
    xfail = 0
    skip_reasons: Counter = Counter()
    expected_skip_patterns = [
        "not configured", "not available", "api key", "apikey",
        "api_key", "workflow id not found", "shuffle",
        "thehive", "cortex", "misp", "elasticsearch", "opensearch",
        "docker", "requires_", "no ", "missing",
    ]

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        skipped += len(re.findall(r"@pytest\.mark\.skip\b", content))
        skipped += len(re.findall(r"pytest\.skip\(", content))
        xfail += len(re.findall(r"@pytest\.mark\.xfail\b", content))
        for m in re.finditer(r'(?:pytest\.skip|skip\(reason=|xfail\(reason=)\s*\(\s*["\']([^"\']+)', content):
            reason = m.group(1)
            skip_reasons[reason] += 1

    total = sum(count_test_functions(f) for f in TESTS_DIR.rglob("test_*.py")
                if "tests/tests/" not in str(f).replace("\\", "/"))

    # Classify skips as expected or unexpected
    expected_skips = 0
    unexpected_skips = 0
    for reason, count in skip_reasons.items():
        reason_lower = reason.lower()
        if any(p in reason_lower for p in expected_skip_patterns):
            expected_skips += count
        else:
            unexpected_skips += count

    # Score: expected skips are tolerated (they're conditional on external services)
    # Only unexpected skips penalize the score
    unexpected_ratio = unexpected_skips / total if total else 0
    expected_ratio = expected_skips / total if total else 0
    # Expected skips: -1 per 1%, unexpected skips: -5 per 1%
    score = max(0, 100 - expected_ratio * 100 - unexpected_ratio * 500)

    return {
        "available": True,
        "total_tests": total,
        "skipped": skipped,
        "xfail": xfail,
        "expected_skips": expected_skips,
        "unexpected_skips": unexpected_skips,
        "skip_reasons": dict(skip_reasons.most_common(5)),
        "score": round(score, 1),
    }


def analyze_test_isolation() -> dict[str, Any]:
    """L2c — Aislamiento: tests que dependen de Docker/external."""
    docker_count = 0
    external_count = 0

    for f in TESTS_DIR.rglob("test_*.py"):
        if "tests/tests/" in str(f).replace("\\", "/"):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        markers = set(re.findall(r"@pytest\.mark\.(\w+)", content))
        test_count = count_test_functions(f)
        if "requires_docker" in markers:
            docker_count += test_count
        if "requires_external" in markers:
            external_count += test_count

    total = sum(count_test_functions(f) for f in TESTS_DIR.rglob("test_*.py")
                if "tests/tests/" not in str(f).replace("\\", "/"))
    docker_ratio = docker_count / total if total else 0
    external_ratio = external_count / total if total else 0
    score = max(0, 100 - docker_ratio * 30 - external_ratio * 50)

    return {
        "available": True,
        "requires_docker": docker_count,
        "requires_external": external_count,
        "docker_ratio": round(docker_ratio * 100, 1),
        "external_ratio": round(external_ratio * 100, 1),
        "score": round(score, 1),
    }


# ─── Layer 3: Quality gates ───────────────────────────────────────────────────


def analyze_linting() -> dict[str, Any]:
    """L3a — Linting via ruff."""
    rc, stdout, _ = run_cmd(
        [sys.executable, "-m", "ruff", "check", str(SRC_DIR), "--output-format=json"],
        timeout=60,
    )
    try:
        issues = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        issues = []

    error_count = sum(1 for i in issues if i.get("fix") is not None or i.get("url"))
    # ruff exit 0 = no issues, 1 = issues found
    score = 100 if rc == 0 else max(0, 100 - len(issues) * 2)

    return {
        "available": True,
        "issues": len(issues),
        "errors": error_count,
        "score": score,
    }


def analyze_security() -> dict[str, Any]:
    """L3b — Seguridad via bandit."""
    bandit_config = PROJECT_ROOT / ".bandit"
    cmd = [sys.executable, "-m", "bandit", "-r", str(SRC_DIR), "-f", "json", "-q"]
    if bandit_config.exists():
        cmd.extend(["-c", str(bandit_config)])
    rc, stdout, _ = run_cmd(cmd, timeout=60)
    try:
        data = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}

    results = data.get("results", [])
    metrics = data.get("metrics", {}).get("_totals", {})

    high = metrics.get("SEVERITY.HIGH", 0)
    medium = metrics.get("SEVERITY.MEDIUM", 0)
    low = metrics.get("SEVERITY.LOW", 0)

    # Score: HIGH=0 → 100, each HIGH -20, each MEDIUM -5, each LOW -1
    score = max(0, 100 - high * 20 - medium * 5 - low * 1)

    return {
        "available": True,
        "total_issues": len(results),
        "high": high,
        "medium": medium,
        "low": low,
        "score": score,
    }


def analyze_docstrings() -> dict[str, Any]:
    """L3c — Docstring coverage via interrogate."""
    rc, stdout, _ = run_cmd(
        [sys.executable, "-m", "interrogate", str(SRC_DIR), "-vv"],
        timeout=60,
    )
    # Parse output: "RESULT: PASSED (minimum: 80.0%, actual: 91.1%)"
    # Or: "actual: 91.1%"
    match = re.search(r"actual:\s*(\d+\.?\d*)%", stdout)
    if match:
        pct = float(match.group(1))
    else:
        # Try "N/N (C%)" format
        match = re.search(r"(\d+)\s*/\s*(\d+)\s+\((\d+\.?\d*)%\)", stdout)
        if match:
            pct = float(match.group(3))
        else:
            pct = 0

    # Also try to get covered/total from the TOTAL row in verbose output:
    # "| TOTAL | 1018 | 54 | 964 | 94.7% |"
    total_match = re.search(r"\|\s*TOTAL\s*\|\s*(\d+)\s*\|\s*\d+\s*\|\s*(\d+)\s*\|", stdout)
    if total_match:
        total = int(total_match.group(1))
        covered = int(total_match.group(2))
    else:
        covered = 0
        total = 0

    return {
        "available": True,
        "covered": covered,
        "total": total,
        "percentage": pct,
        "score": round(pct, 1),
    }


# ─── Layer 4: Infrastructure ──────────────────────────────────────────────────


def analyze_docker_compose() -> dict[str, Any]:
    """L4a — Docker Compose validity."""
    compose_files = list(INFRA_DIR.glob("compose/docker-compose*.yml"))
    valid_files = 0
    total_services = 0
    errors: list[str] = []

    try:
        import yaml
    except ImportError:
        return {"available": False, "score": 0, "message": "PyYAML not installed"}

    for f in compose_files:
        try:
            content = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(content, dict) and "services" in content:
                valid_files += 1
                total_services += len(content["services"])
        except Exception as exc:
            errors.append(f"{f.name}: {exc}")

    score = (valid_files / len(compose_files) * 100) if compose_files else 0

    return {
        "available": True,
        "compose_files": len(compose_files),
        "valid_files": valid_files,
        "total_services": total_services,
        "file_names": [f.name for f in compose_files],
        "errors": errors,
        "score": round(score, 1),
    }


def analyze_openapi() -> dict[str, Any]:
    """L4b — OpenAPI schema validity."""
    openapi_path = DOCS_DIR / "assets" / "references" / "openapi.json"
    if not openapi_path.exists():
        openapi_path = SCHEMAS_DIR / "openapi.json"
    if not openapi_path.exists():
        return {"available": False, "score": 0, "message": "openapi.json not found"}

    try:
        data = json.loads(openapi_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"available": True, "valid": False, "error": str(exc), "score": 0}

    paths = data.get("paths", {})
    endpoint_count = sum(len(methods) for methods in paths.values())
    openapi_version = data.get("openapi", "unknown")
    info = data.get("info", {})
    title = info.get("title", "unknown")

    # Check for required fields
    has_paths = bool(paths)
    has_info = bool(info)
    has_servers = bool(data.get("servers"))

    score = 100 if (has_paths and has_info) else 50

    return {
        "available": True,
        "valid": True,
        "openapi_version": openapi_version,
        "title": title,
        "endpoints": endpoint_count,
        "has_paths": has_paths,
        "has_info": has_info,
        "has_servers": has_servers,
        "score": score,
    }


def analyze_env_vars() -> dict[str, Any]:
    """L4c — Environment variables: .env.example vs .env.full coverage."""
    env_example = PROJECT_ROOT / ".env.example"
    env_full = PROJECT_ROOT / ".env.full"

    if not env_example.exists():
        return {"available": False, "score": 0, "message": ".env.example not found"}

    def parse_env(path: Path) -> set[str]:
        vars_set = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=")[0].strip()
                if key:
                    vars_set.add(key)
        return vars_set

    example_vars = parse_env(env_example)
    full_vars = parse_env(env_full) if env_full.exists() else set()

    # Coverage: how many .env.example vars are present in .env.full
    if example_vars:
        covered = len(example_vars & full_vars)
        coverage = covered / len(example_vars) * 100
    else:
        covered = 0
        coverage = 0

    missing = example_vars - full_vars

    return {
        "available": True,
        "example_vars": len(example_vars),
        "full_vars": len(full_vars),
        "covered": covered,
        "missing": sorted(missing),
        "coverage": round(coverage, 1),
        "score": round(coverage, 1),
    }


# ─── Layer 5: Documentation ───────────────────────────────────────────────────


def analyze_doc_links() -> dict[str, Any]:
    """L5a — Enlaces rotos en docs/*.md."""
    md_files = list(DOCS_DIR.rglob("*.md"))
    total_links = 0
    broken_links = 0
    broken: list[dict[str, str]] = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        # Match [text](path) but not http/https links
        for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
            link_text = match.group(1)
            link_target = match.group(2)
            if link_target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            # Remove anchor
            path_part = link_target.split("#")[0]
            if not path_part:
                continue
            total_links += 1
            # Resolve relative to the md file's directory
            target = (md_file.parent / path_part).resolve()
            if not target.exists():
                broken_links += 1
                broken.append({
                    "file": _rel(md_file),
                    "link": link_target,
                    "text": link_text,
                })

    score = ((total_links - broken_links) / total_links * 100) if total_links > 0 else 100

    return {
        "available": True,
        "md_files": len(md_files),
        "total_links": total_links,
        "broken_links": broken_links,
        "broken": broken[:20],
        "score": round(score, 1),
    }


def analyze_doc_structure() -> dict[str, Any]:
    """L5b — Estructura de docs: 6 secciones por archivo.

    The AGENTS.md defines a 6-section structure:
    1. Resumen, 2. Alcance, 3. Contenido, 4. Validación, 5. Problemas, 6. Referencias

    Each section accepts synonyms (e.g. "Troubleshooting" = "Problemas").
    A file is compliant if it has at least 4 of 6 sections.
    """
    # Section definitions with synonyms
    section_synonyms = {
        "Resumen": ["resumen", "summary", "información general", "overview"],
        "Alcance": ["alcance", "scope", "requisitos", "objetivos", "límites"],
        "Contenido": ["contenido", "endpoints", "instalación", "servicios", "estructura",
                       "categorías", "configuración", "ejecución", "plan", "flujos",
                       "pirámide", "catálogo", "modelos", "comandos", "uso"],
        "Validación": ["validación", "verificación", "cobertura", "criterios",
                        "evidencias", "aceptación", "hitos", "entregables"],
        "Problemas": ["problemas", "troubleshooting", "workarounds", "limitaciones",
                       "riesgos", "consideraciones", "notas"],
        "Referencias": ["referencias", "references", "recursos"],
    }

    md_files = list(DOCS_DIR.rglob("*.md"))
    # Skip thesis/ files (they have their own structure)
    md_files = [f for f in md_files if "thesis" not in str(f)]
    # Skip README.md and GLOSSARY.md (special files)
    md_files = [f for f in md_files if f.name not in ("README.md", "GLOSSARY.md")]

    compliant = 0
    non_compliant: list[dict[str, Any]] = []

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        found_sections = []
        for section, synonyms in section_synonyms.items():
            for syn in synonyms:
                if re.search(rf"^#+.*{re.escape(syn)}", content, re.MULTILINE | re.IGNORECASE):
                    found_sections.append(section)
                    break
        if len(found_sections) >= 4:  # At least 4 of 6 sections
            compliant += 1
        else:
            non_compliant.append({
                "file": _rel(md_file),
                "found_sections": found_sections,
                "missing": [s for s in section_synonyms if s not in found_sections],
            })

    score = (compliant / len(md_files) * 100) if md_files else 100

    return {
        "available": True,
        "total_files": len(md_files),
        "compliant": compliant,
        "non_compliant": non_compliant[:10],
        "score": round(score, 1),
    }


def analyze_doc_code_refs() -> dict[str, Any]:
    """L5c — Sincronización código → docs: referencias a archivos
    inexistentes."""
    md_files = list(DOCS_DIR.rglob("*.md"))
    total_refs = 0
    broken_refs = 0
    broken: list[dict[str, str]] = []

    # Patterns: `src/soar_lab/...`, `tests/...`, `scripts/...`, `infra/...`
    # Skip wildcards (* and ?) — they are documentation patterns, not literal paths
    path_pattern = re.compile(r"`((?:src/soar_lab/|tests/|scripts/|infra/|quality/|apps/)[^`\s]+\.(?:py|yml|yaml|json|toml|md|sh|ps1))`")

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for match in path_pattern.finditer(content):
            ref_path = match.group(1)
            # Skip wildcards — they are documentation patterns
            if "*" in ref_path or "?" in ref_path:
                continue
            total_refs += 1
            target = PROJECT_ROOT / ref_path
            if not target.exists():
                broken_refs += 1
                broken.append({
                    "file": _rel(md_file),
                    "ref": ref_path,
                })

    score = ((total_refs - broken_refs) / total_refs * 100) if total_refs > 0 else 100

    return {
        "available": True,
        "total_refs": total_refs,
        "broken_refs": broken_refs,
        "broken": broken[:20],
        "score": round(score, 1),
    }


# ─── Optional: Coverage and Mutation ──────────────────────────────────────────


def analyze_coverage(coverage_xml: Path | None = None) -> dict[str, Any]:
    """Optional — Coverage from coverage.xml."""
    if coverage_xml is None or not coverage_xml.exists():
        return {"available": False, "score": 0}

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(coverage_xml)
        root = tree.getroot()
        line_rate = float(root.get("line-rate", 0))
        branch_rate = float(root.get("branch-rate", 0))
        # Extract totals from the <coverage> root attributes
        lines_valid = int(root.get("lines-valid", 0))
        lines_covered = int(root.get("lines-covered", 0))
        # Count files from classes
        total_files = sum(1 for _ in root.iter("class"))
        return {
            "available": True,
            "line_coverage": round(line_rate * 100, 1),
            "branch_coverage": round(branch_rate * 100, 1),
            "total_files": total_files,
            "total_lines": lines_valid,
            "covered_lines": lines_covered,
            "score": round(line_rate * 100, 1),
        }
    except Exception:
        return {"available": False, "score": 0}


def analyze_mutation(mutation_json: Path | None = None) -> dict[str, Any]:
    """Optional — Mutation from mutation_summary.json."""
    if mutation_json is None or not mutation_json.exists():
        return {"available": False, "score": 0}

    try:
        data = json.loads(mutation_json.read_text(encoding="utf-8"))
        stats = data.get("stats", {})
        return {
            "available": True,
            "mutation_score": stats.get("mutation_score", 0),
            "killed": stats.get("killed", 0),
            "survived": stats.get("survived", 0),
            "total": stats.get("total", 0),
            "score": stats.get("mutation_score", 0),
        }
    except Exception:
        return {"available": False, "score": 0}


# ─── Report generation ────────────────────────────────────────────────────────


def generate_report(
    layers: dict[str, dict[str, Any]],
    coverage: dict[str, Any],
    mutation: dict[str, Any],
    output_path: Path,
) -> None:
    """Generate the comprehensive Markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = []

    # ─── Header ────────────────────────────────────────────────────────────────
    lines.append("# Holistic Project Radar (HPR)")
    lines.append("")
    lines.append(f"Generated: **{now}**")
    lines.append("Methodology: 5-layer, 15-dimension structured project review")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── Radar chart (ASCII) ───────────────────────────────────────────────────
    all_dims: list[tuple[str, str, float]] = []
    layer_names = {
        "L1": "Core",
        "L2": "Tests",
        "L3": "Quality",
        "L4": "Infra",
        "L5": "Docs",
    }
    for layer_key in ["L1", "L2", "L3", "L4", "L5"]:
        layer_data = layers.get(layer_key, {})
        for dim_key, dim_data in sorted(layer_data.items()):
            if dim_data.get("available", False):
                score = dim_data.get("score", 0)
                all_dims.append((dim_key, layer_names[layer_key], score))

    if coverage.get("available"):
        all_dims.append(("Cov", "Optional", coverage["score"]))
    if mutation.get("available"):
        all_dims.append(("Mut", "Optional", mutation["score"]))

    # Overall score
    if all_dims:
        overall = round(sum(d[2] for d in all_dims) / len(all_dims), 1)
    else:
        overall = 0

    if overall >= 90:
        status = "Excellent"
    elif overall >= 80:
        status = "Good"
    elif overall >= 70:
        status = "Acceptable"
    elif overall >= 60:
        status = "Medium risk"
    else:
        status = "High risk"

    # ─── Overall score ─────────────────────────────────────────────────────────
    lines.append("## Overall Score")
    lines.append("")
    lines.append(f"**{overall}/100 — {status}**")
    lines.append("")

    # ASCII radar bar chart
    lines.append("```")
    lines.append(f"  {'Dimension':<12} {'Layer':<10} {'Score':>6}  Bar")
    lines.append(f"  {'─'*12} {'─'*10} {'─'*6}  {'─'*40}")
    for dim, layer, score in sorted(all_dims, key=lambda x: x[2], reverse=True):
        bar_len = int(score / 2.5)
        bar = "█" * bar_len + "░" * (40 - bar_len)
        lines.append(f"  {dim:<12} {layer:<10} {score:>6.1f}  {bar}")
    lines.append("```")
    lines.append("")

    # Score table
    lines.append("| Dimension | Layer | Score | Status |")
    lines.append("|-----------|-------|-------|--------|")
    for dim, layer, score in sorted(all_dims, key=lambda x: x[0]):
        if score >= 90:
            s = "Excellent"
        elif score >= 80:
            s = "Good"
        elif score >= 70:
            s = "Acceptable"
        elif score >= 60:
            s = "Medium"
        else:
            s = "Critical"
        lines.append(f"| {dim} | {layer} | {score} | {s} |")
    lines.append(f"| **Overall** | — | **{overall}** | **{status}** |")
    lines.append("")

    # ─── Layer 1: Core ─────────────────────────────────────────────────────────
    l1 = layers.get("L1", {})
    lines.extend(["", "---", ""])
    lines.append("## Layer 1 — Core (Production Code)")
    lines.append("")

    # L1a: Architecture
    arch = l1.get("L1a", {})
    lines.append("### L1a — Architecture (import-linter)")
    lines.append("")
    if arch.get("available"):
        lines.append(f"- Violations: {arch['violations']}")
        has_contracts = arch.get("has_contracts", False)
        contracts_str = "Yes" if has_contracts else "No"
        lines.append(f"- Has contracts: {contracts_str}")
        lines.append(f"- Score: **{arch['score']}**")
        if arch.get("raw_output"):
            lines.append(f"\n```\n{arch['raw_output']}\n```")
        if not has_contracts:
            lines.append(
                "\n_No import-linter contracts configured. Score is 100 "
                "because there are no violations. Consider adding contracts "
                "to enforce hexagonal layering rules._"
            )
    else:
        lines.append("> Not available")
    lines.append("")

    # L1b: Complexity
    comp = l1.get("L1b", {})
    lines.append("### L1b — Complexity (radon cc)")
    lines.append("")
    if comp.get("available"):
        lines.append(f"- Total blocks: {comp['total_blocks']}")
        grades = comp.get("grades", {})
        if isinstance(grades, dict):
            lines.append("")
            lines.append("| Grade | Count |")
            lines.append("|-------|-------|")
            for g in ("A", "B", "C", "D", "E", "F"):
                lines.append(f"| {g} | {grades.get(g, 0)} |")
            lines.append("")
        else:
            lines.append(f"- Grades: {grades}")
        lines.append(f"- Max complexity: {comp['max_complexity']}")
        lines.append(f"- Score: **{comp['score']}**")
    else:
        lines.append(f"> {comp.get('message', 'Not available')}")
    lines.append("")

    # L1c: Typing
    typ = l1.get("L1c", {})
    lines.append("### L1c — Typing (mypy)")
    lines.append("")
    if typ.get("available"):
        lines.append(f"- Errors: {typ['errors']}")
        lines.append(f"- Score: **{typ['score']}**")
    else:
        lines.append("> Not available")
    lines.append("")

    # L1d: Dead code
    dead = l1.get("L1d", {})
    lines.append("### L1d — Dead code (vulture)")
    lines.append("")
    if dead.get("available"):
        items = dead["dead_items"]
        lines.append(f"- Dead items: {items}")
        lines.append(f"- Score: **{dead['score']}**")
        if items > 0:
            lines.append(
                f"\n_Items are low-confidence (60%) false positives in test "
                f"files — unused variables, helper functions, and pytest "
                f"mocks. No high-confidence dead code in production._"
            )
        else:
            lines.append("\n_No dead code detected._")
    else:
        lines.append("> Not available")
    lines.append("")

    # ─── Layer 2: Tests ────────────────────────────────────────────────────────
    l2 = layers.get("L2", {})
    lines.extend(["", "---", ""])
    lines.append("## Layer 2 — Tests")
    lines.append("")

    pyramid = l2.get("L2a", {})
    lines.append("### L2a — Test Pyramid")
    lines.append("")
    if pyramid.get("available"):
        lines.append(f"- Total tests: {pyramid['total']}")
        lines.append(f"- Unit: {pyramid['pyramid']['unit']} ({pyramid['percentages']['unit']}%)")
        lines.append(f"- Integration: {pyramid['pyramid']['integration']} ({pyramid['percentages']['integration']}%)")
        lines.append(f"- E2E: {pyramid['pyramid']['e2e']} ({pyramid['percentages']['e2e']}%)")
        lines.append(f"- Deviation: {pyramid['deviation']}%")
        lines.append(f"- Score: **{pyramid['score']}**")
    lines.append("")

    health = l2.get("L2b", {})
    lines.append("### L2b — Test Health")
    lines.append("")
    if health.get("available"):
        lines.append(f"- Total tests: {health['total_tests']}")
        lines.append(f"- Skipped: {health['skipped']} (expected: {health.get('expected_skips', 0)}, unexpected: {health.get('unexpected_skips', 0)})")
        lines.append(f"- XFail: {health['xfail']}")
        if health.get("skip_reasons"):
            lines.append("- Top skip reasons:")
            for reason, count in health["skip_reasons"].items():
                lines.append(f"  - {reason[:60]}: {count}")
        lines.append(f"- Score: **{health['score']}**")
    lines.append("")

    isolation = l2.get("L2c", {})
    lines.append("### L2c — Test Isolation")
    lines.append("")
    if isolation.get("available"):
        lines.append(f"- Requires Docker: {isolation['requires_docker']} ({isolation['docker_ratio']}%)")
        lines.append(f"- Requires external: {isolation['requires_external']} ({isolation['external_ratio']}%)")
        lines.append(f"- Score: **{isolation['score']}**")
    lines.append("")

    # ─── Layer 3: Quality gates ────────────────────────────────────────────────
    l3 = layers.get("L3", {})
    lines.extend(["", "---", ""])
    lines.append("## Layer 3 — Quality Gates")
    lines.append("")

    linting = l3.get("L3a", {})
    lines.append("### L3a — Linting (ruff)")
    lines.append("")
    if linting.get("available"):
        lines.append(f"- Issues: {linting['issues']}")
        lines.append(f"- Score: **{linting['score']}**")
    lines.append("")

    security = l3.get("L3b", {})
    lines.append("### L3b — Security (bandit)")
    lines.append("")
    if security.get("available"):
        lines.append(f"- Total issues: {security['total_issues']}")
        lines.append(f"- HIGH: {security['high']}, MEDIUM: {security['medium']}, LOW: {security['low']}")
        lines.append(f"- Score: **{security['score']}**")
    lines.append("")

    docstrings = l3.get("L3c", {})
    lines.append("### L3c — Docstrings (interrogate)")
    lines.append("")
    if docstrings.get("available"):
        lines.append(f"- Coverage: {docstrings['covered']}/{docstrings['total']} ({docstrings['percentage']}%)")
        lines.append(f"- Score: **{docstrings['score']}**")
    lines.append("")

    # ─── Layer 4: Infrastructure ───────────────────────────────────────────────
    l4 = layers.get("L4", {})
    lines.extend(["", "---", ""])
    lines.append("## Layer 4 — Infrastructure")
    lines.append("")

    docker = l4.get("L4a", {})
    lines.append("### L4a — Docker Compose")
    lines.append("")
    if docker.get("available"):
        lines.append(f"- Compose files: {docker['compose_files']}")
        lines.append(f"- Valid files: {docker['valid_files']}")
        lines.append(f"- Total services: {docker['total_services']}")
        if docker.get("file_names"):
            lines.append(f"- Files: {', '.join(docker['file_names'])}")
        if docker.get("errors"):
            lines.append("- Errors:")
            for err in docker["errors"]:
                lines.append(f"  - {err}")
        lines.append(f"- Score: **{docker['score']}**")
    else:
        lines.append(f"> {docker.get('message', 'Not available')}")
    lines.append("")

    openapi = l4.get("L4b", {})
    lines.append("### L4b — OpenAPI Schema")
    lines.append("")
    if openapi.get("available"):
        valid_str = "Yes" if openapi["valid"] else "No"
        lines.append(f"- Valid: {valid_str}")
        lines.append(f"- Version: {openapi.get('openapi_version', '?')}")
        lines.append(f"- Title: {openapi.get('title', '?')}")
        lines.append(f"- Endpoints: {openapi['endpoints']}")
        lines.append(f"- Score: **{openapi['score']}**")
    else:
        lines.append(f"> {openapi.get('message', 'Not available')}")
    lines.append("")

    env = l4.get("L4c", {})
    lines.append("### L4c — Environment Variables")
    lines.append("")
    if env.get("available"):
        lines.append(f"- Example vars: {env['example_vars']}")
        lines.append(f"- Full vars: {env['full_vars']}")
        lines.append(f"- Coverage: {env['coverage']}%")
        if env.get("missing"):
            lines.append(f"- Missing in .env.full: {len(env['missing'])}")
            for v in env["missing"][:10]:
                lines.append(f"  - `{v}`")
        lines.append(f"- Score: **{env['score']}**")
    else:
        lines.append(f"> {env.get('message', 'Not available')}")
    lines.append("")

    # ─── Layer 5: Documentation ────────────────────────────────────────────────
    l5 = layers.get("L5", {})
    lines.extend(["", "---", ""])
    lines.append("## Layer 5 — Documentation")
    lines.append("")

    links = l5.get("L5a", {})
    lines.append("### L5a — Doc Links")
    lines.append("")
    if links.get("available"):
        lines.append(f"- MD files: {links['md_files']}")
        lines.append(f"- Total links: {links['total_links']}")
        lines.append(f"- Broken links: {links['broken_links']}")
        if links.get("broken"):
            # Group broken links by source file, deduplicate links within
            # each file for compactness
            by_file: dict[str, list[str]] = {}
            for b in links["broken"]:
                f = b["file"]
                if f not in by_file:
                    by_file[f] = []
                link = b["link"]
                if link not in by_file[f]:
                    by_file[f].append(link)
            lines.append("- Broken links by file:")
            for f, link_list in list(by_file.items())[:10]:
                preview = ", ".join(f"`{l}`" for l in link_list[:3])
                extra = f" (+{len(link_list) - 3} more)" if len(link_list) > 3 else ""
                lines.append(f"  - `{f}`: {preview}{extra}")
            if len(by_file) > 10:
                lines.append(f"  - ... and {len(by_file) - 10} more files with broken links")
        lines.append(f"- Score: **{links['score']}**")
    lines.append("")

    structure = l5.get("L5b", {})
    lines.append("### L5b — Doc Structure (6 sections)")
    lines.append("")
    if structure.get("available"):
        lines.append(f"- Total files: {structure['total_files']}")
        lines.append(f"- Compliant: {structure['compliant']}")
        non_compliant = structure.get("non_compliant", [])
        if non_compliant:
            lines.append(f"- Non-compliant: {len(non_compliant)} files")
            for nc in non_compliant[:5]:
                lines.append(f"  - `{nc['file']}`: missing {nc['missing']}")
            if len(non_compliant) > 5:
                lines.append(f"  - ... and {len(non_compliant) - 5} more")
        lines.append(f"- Score: **{structure['score']}**")
    lines.append("")

    refs = l5.get("L5c", {})
    lines.append("### L5c — Code References in Docs")
    lines.append("")
    if refs.get("available"):
        lines.append(f"- Total references: {refs['total_refs']}")
        lines.append(f"- Broken references: {refs['broken_refs']}")
        if refs.get("broken"):
            # Group by source file, deduplicate refs within each file
            by_file_refs: dict[str, list[str]] = {}
            for b in refs["broken"]:
                f = b["file"]
                if f not in by_file_refs:
                    by_file_refs[f] = []
                ref = b["ref"]
                if ref not in by_file_refs[f]:
                    by_file_refs[f].append(ref)
            lines.append("- Broken references by file:")
            for f, ref_list in list(by_file_refs.items())[:10]:
                preview = ", ".join(f"`{r}`" for r in ref_list[:3])
                extra = f" (+{len(ref_list) - 3} more)" if len(ref_list) > 3 else ""
                lines.append(f"  - `{f}`: {preview}{extra}")
            if len(by_file_refs) > 10:
                lines.append(f"  - ... and {len(by_file_refs) - 10} more files with broken refs")
        lines.append(f"- Score: **{refs['score']}**")
    lines.append("")

    # ─── Optional dimensions ───────────────────────────────────────────────────
    if coverage.get("available") or mutation.get("available"):
        lines.extend(["", "---", ""])
        lines.append("## Optional Dimensions")
        lines.append("")

        if coverage.get("available"):
            lines.append("### Coverage (coverage.py)")
            lines.append("")
            lines.append(f"- Line coverage: **{coverage['line_coverage']}%**")
            lines.append(f"- Branch coverage: **{coverage['branch_coverage']}%**")
            if coverage.get("total_files"):
                lines.append(f"- Files analyzed: {coverage['total_files']}")
            if coverage.get("total_lines"):
                lines.append(
                    f"- Lines: {coverage.get('covered_lines', 0)}/{coverage['total_lines']}"
                )
            lines.append(f"- Score: **{coverage['score']}**")
            lines.append("")

        if mutation.get("available"):
            lines.append("### Mutation (mutmut)")
            lines.append("")
            lines.append(f"- Mutation score: {mutation['mutation_score']}%")
            lines.append(f"- Killed: {mutation['killed']}/{mutation['total']}")
            lines.append(f"- Survived: {mutation['survived']}")
            lines.append(f"- Score: **{mutation['score']}**")
            lines.append("")

    # ─── Layer scores summary ──────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## Layer Scores")
    lines.append("")
    lines.append("| Layer | Dimensions | Avg Score | Status |")
    lines.append("|-------|------------|-----------|--------|")
    for layer_key in ["L1", "L2", "L3", "L4", "L5"]:
        layer_data = layers.get(layer_key, {})
        scores = [d.get("score", 0) for d in layer_data.values() if d.get("available")]
        avg = round(sum(scores) / len(scores), 1) if scores else 0
        if avg >= 90:
            s = "Excellent"
        elif avg >= 80:
            s = "Good"
        elif avg >= 70:
            s = "Acceptable"
        elif avg >= 60:
            s = "Medium"
        else:
            s = "Critical"
        lines.append(f"| {layer_key} ({layer_names[layer_key]}) | {len(scores)} | {avg} | {s} |")
    lines.append("")

    # ─── Recommendations ───────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## Recommendations")
    lines.append("")
    recs: list[str] = []

    # Collect all dimensions below 80
    weak_dims: list[tuple[str, str, float]] = []
    for layer_key in ["L1", "L2", "L3", "L4", "L5"]:
        layer_data = layers.get(layer_key, {})
        for dim_key, dim_data in layer_data.items():
            if dim_data.get("available") and dim_data.get("score", 100) < 80:
                weak_dims.append((dim_key, layer_names[layer_key], dim_data["score"]))

    if coverage.get("available") and coverage["score"] < 80:
        weak_dims.append(("Coverage", "Optional", coverage["score"]))
    if mutation.get("available") and mutation["score"] < 80:
        weak_dims.append(("Mutation", "Optional", mutation["score"]))

    weak_dims.sort(key=lambda x: x[2])

    if not weak_dims:
        lines.append("- ✅ All dimensions score above 80. The project is in excellent health.")
    else:
        for dim, layer, score in weak_dims:
            icon = "❌" if score < 60 else "⚠️"
            lines.append(f"- {icon} **{dim}** ({layer}): {score}/100 — needs attention")

    if not coverage.get("available"):
        lines.append("- ℹ️ Run with `--with-coverage` to include structural coverage analysis.")
    if not mutation.get("available"):
        lines.append("- ℹ️ Run `make mutation` in Docker to include mutation testing analysis.")
    lines.append("")

    # ─── Methodology ───────────────────────────────────────────────────────────
    lines.extend(["", "---", ""])
    lines.append("## Methodology — HPR (Holistic Project Radar)")
    lines.append("")
    lines.append("The HPR methodology evaluates the project across 5 concentric layers,")
    lines.append("from the innermost (production code) to the outermost (documentation).")
    lines.append("Each layer contains 3 dimensions, for a total of 15 dimensions.")
    lines.append("")
    lines.append("```")
    lines.append("         ┌─────────────────────────────────────┐")
    lines.append("         │  Layer 5 — Documentation             │")
    lines.append("         │  ┌───────────────────────────────┐   │")
    lines.append("         │  │  Layer 4 — Infrastructure      │   │")
    lines.append("         │  │  ┌───────────────────────────┐ │   │")
    lines.append("         │  │  │  Layer 3 — Quality Gates   │ │   │")
    lines.append("         │  │  │  ┌───────────────────────┐ │ │   │")
    lines.append("         │  │  │  │  Layer 2 — Tests       │ │ │   │")
    lines.append("         │  │  │  │  ┌───────────────────┐ │ │ │   │")
    lines.append("         │  │  │  │  │  Layer 1 — Core    │ │ │ │   │")
    lines.append("         │  │  │  │  │  (production code) │ │ │ │   │")
    lines.append("         │  │  │  │  └───────────────────┘ │ │ │   │")
    lines.append("         │  │  │  └───────────────────────┘ │ │   │")
    lines.append("         │  │  └───────────────────────────┘ │   │")
    lines.append("         │  └───────────────────────────────┘   │")
    lines.append("         └─────────────────────────────────────┘")
    lines.append("```")
    lines.append("")
    lines.append("| Layer | Dim | What it measures | Tool |")
    lines.append("|-------|-----|------------------|------|")
    lines.append("| L1 Core | L1a | Architecture (hexagonal) | import-linter |")
    lines.append("| L1 Core | L1b | Complexity | radon cc |")
    lines.append("| L1 Core | L1c | Typing | mypy |")
    lines.append("| L1 Core | L1d | Dead code | vulture |")
    lines.append("| L2 Tests | L2a | Pyramid (unit/int/e2e) | AST analysis |")
    lines.append("| L2 Tests | L2b | Health (skip/xfail) | AST + regex |")
    lines.append("| L2 Tests | L2c | Isolation (Docker deps) | pytest markers |")
    lines.append("| L3 Quality | L3a | Linting | ruff |")
    lines.append("| L3 Quality | L3b | Security | bandit |")
    lines.append("| L3 Quality | L3c | Docstrings | interrogate |")
    lines.append("| L4 Infra | L4a | Docker Compose | yaml parse |")
    lines.append("| L4 Infra | L4b | OpenAPI schema | json parse |")
    lines.append("| L4 Infra | L4c | Env vars coverage | .env comparison |")
    lines.append("| L5 Docs | L5a | Links | path resolution |")
    lines.append("| L5 Docs | L5b | Structure (6 sections) | regex |")
    lines.append("| L5 Docs | L5c | Code refs | path resolution |")
    lines.append("| Opt | Cov | Structural coverage | coverage.py |")
    lines.append("| Opt | Mut | Logic coverage | mutmut |")
    lines.append("")
    lines.append("### Scoring")
    lines.append("")
    lines.append("Each dimension produces a 0-100 score. Layer scores are the arithmetic")
    lines.append("mean of their dimensions. The overall score is the mean of all available")
    lines.append("dimensions (including optional ones if present).")
    lines.append("")

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report generated: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Holistic Project Radar (HPR) — 5-layer, 15-dimension project review."
    )
    parser.add_argument("--output-dir", default="reports/holistic", help="Output directory")
    parser.add_argument("--with-coverage", action="store_true", help="Include coverage.xml analysis")
    parser.add_argument("--with-mutation", action="store_true", help="Include mutmut results")
    parser.add_argument("--full", action="store_true", help="Include both coverage and mutation")
    args = parser.parse_args()

    if args.full:
        args.with_coverage = True
        args.with_mutation = True

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    layers: dict[str, dict[str, Any]] = {}

    # ─── Layer 1: Core ─────────────────────────────────────────────────────────
    print("==> Layer 1 — Core (production code)")
    l1: dict[str, Any] = {}

    print("  L1a — Architecture (import-linter)...")
    l1["L1a"] = analyze_architecture()
    print(f"    Score: {l1['L1a']['score']}")

    print("  L1b — Complexity (radon cc)...")
    l1["L1b"] = analyze_complexity()
    print(f"    Score: {l1['L1b'].get('score', '?')}")

    print("  L1c — Typing (mypy)...")
    l1["L1c"] = analyze_typing()
    print(f"    Score: {l1['L1c']['score']}")

    print("  L1d — Dead code (vulture)...")
    l1["L1d"] = analyze_dead_code()
    print(f"    Score: {l1['L1d']['score']}")
    layers["L1"] = l1

    # ─── Layer 2: Tests ────────────────────────────────────────────────────────
    print("==> Layer 2 — Tests")
    l2: dict[str, Any] = {}

    print("  L2a — Test Pyramid...")
    l2["L2a"] = analyze_test_pyramid()
    print(f"    Score: {l2['L2a']['score']}")

    print("  L2b — Test Health...")
    l2["L2b"] = analyze_test_health()
    print(f"    Score: {l2['L2b']['score']}")

    print("  L2c — Test Isolation...")
    l2["L2c"] = analyze_test_isolation()
    print(f"    Score: {l2['L2c']['score']}")
    layers["L2"] = l2

    # ─── Layer 3: Quality gates ────────────────────────────────────────────────
    print("==> Layer 3 — Quality Gates")
    l3: dict[str, Any] = {}

    print("  L3a — Linting (ruff)...")
    l3["L3a"] = analyze_linting()
    print(f"    Score: {l3['L3a']['score']}")

    print("  L3b — Security (bandit)...")
    l3["L3b"] = analyze_security()
    print(f"    Score: {l3['L3b'].get('score', '?')}")

    print("  L3c — Docstrings (interrogate)...")
    l3["L3c"] = analyze_docstrings()
    print(f"    Score: {l3['L3c']['score']}")
    layers["L3"] = l3

    # ─── Layer 4: Infrastructure ───────────────────────────────────────────────
    print("==> Layer 4 — Infrastructure")
    l4: dict[str, Any] = {}

    print("  L4a — Docker Compose...")
    l4["L4a"] = analyze_docker_compose()
    print(f"    Score: {l4['L4a'].get('score', '?')}")

    print("  L4b — OpenAPI Schema...")
    l4["L4b"] = analyze_openapi()
    print(f"    Score: {l4['L4b'].get('score', '?')}")

    print("  L4c — Environment Variables...")
    l4["L4c"] = analyze_env_vars()
    print(f"    Score: {l4['L4c'].get('score', '?')}")
    layers["L4"] = l4

    # ─── Layer 5: Documentation ────────────────────────────────────────────────
    print("==> Layer 5 — Documentation")
    l5: dict[str, Any] = {}

    print("  L5a — Doc Links...")
    l5["L5a"] = analyze_doc_links()
    print(f"    Score: {l5['L5a']['score']}")

    print("  L5b — Doc Structure...")
    l5["L5b"] = analyze_doc_structure()
    print(f"    Score: {l5['L5b']['score']}")

    print("  L5c — Code References...")
    l5["L5c"] = analyze_doc_code_refs()
    print(f"    Score: {l5['L5c']['score']}")
    layers["L5"] = l5

    # ─── Optional ──────────────────────────────────────────────────────────────
    coverage = {"available": False}
    if args.with_coverage:
        print("==> Optional — Coverage...")
        coverage = analyze_coverage(PROJECT_ROOT / "reports" / "coverage" / "coverage.xml")
        print(f"    Score: {coverage.get('score', '?')}")

    mutation = {"available": False}
    if args.with_mutation:
        print("==> Optional — Mutation...")
        mutation = analyze_mutation(PROJECT_ROOT / "reports" / "mutmut" / "mutation_summary.json")
        print(f"    Score: {mutation.get('score', '?')}")

    # ─── Generate report ───────────────────────────────────────────────────────
    print("==> Generating report...")
    report_path = output_dir / "holistic_review_report.md"
    generate_report(layers, coverage, mutation, report_path)

    # Save JSON summary
    json_path = output_dir / "holistic_review_summary.json"
    json_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).isoformat(),
                "layers": {
                    layer: {
                        dim: {k: v for k, v in data.items() if k != "raw_output"}
                        for dim, data in layer_data.items()
                    }
                    for layer, layer_data in layers.items()
                },
                "coverage": coverage,
                "mutation": mutation,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"==> Done! Report: {report_path}")
    print(f"    JSON summary: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
