"""Architecture test: domain layer must not import infrastructure or interfaces.

FASE 56 — N013: Añadir pruebas arquitectónicas automáticas que impidan imports
desde domain hacia infrastructure o interfaces.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest


def _get_imports(source: str) -> tuple[set[str], set[str]]:
    """Return (module imports, from X import modules) found at top level."""
    tree = ast.parse(source)
    modules: set[str] = set()
    from_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                from_modules.add(node.module.split(".")[0])
    return modules, from_modules


@pytest.mark.unit
@pytest.mark.architecture
def test_domain_does_not_import_infrastructure_or_interfaces():
    """Domain packages must not depend on infrastructure, interfaces or other outer layers."""
    project_root = Path(__file__).resolve().parents[2]
    domain_dir = project_root / "src" / "soar_lab" / "domain"
    assert domain_dir.exists(), f"Domain directory not found: {domain_dir}"

    forbidden_top_level = {
        "soar_lab",
    }
    forbidden_full_prefixes = {
        "soar_lab.infrastructure",
        "soar_lab.interfaces",
        "soar_lab.application",
        "soar_lab.scripts",
        "soar_lab.api",
        "soar_lab.auth",
        "soar_lab.config",
        "soar_lab.data",
        "soar_lab.db",
        "soar_lab.logging",
        "soar_lab.resilience",
        "soar_lab.security",
        "soar_lab.simulator",
        "soar_lab.validation",
        "soar_lab.analytics",
        "soar_lab.common",
    }

    violations: list[str] = []
    for py_file in domain_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            violations.append(f"{py_file.relative_to(project_root)}: syntax error {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if any(module.startswith(p) for p in forbidden_full_prefixes):
                        violations.append(
                            f"{py_file.relative_to(project_root)}: forbidden import '{module}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if any(module.startswith(p) for p in forbidden_full_prefixes):
                    violations.append(
                        f"{py_file.relative_to(project_root)}: forbidden from-import '{module}'"
                    )

    assert not violations, "Domain layer imports outer layers:\n" + "\n".join(violations)
