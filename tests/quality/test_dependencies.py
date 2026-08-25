"""Test: internal dependency and architecture rules.

Two layers of checks:
1. import-linter (if configured) — checks contracts in pyproject.toml
2. AST-based layer checks — verifies hexagonal architecture rules directly

The AST checks run even when import-linter is not configured.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src" / "soar_lab"


def _run_import_linter() -> tuple[int, str]:
    """Run import-linter via Python API or CLI."""
    try:
        import click.testing
        from importlinter.cli import lint_imports_command

        runner = click.testing.CliRunner()
        result = runner.invoke(lint_imports_command, ["--ci"])
        return result.exit_code, result.output
    except Exception:
        pass
    for cmd in (["lint-imports", "--ci"], [sys.executable, "-m", "lint_imports", "--ci"]):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            return result.returncode, result.stdout + result.stderr
        except FileNotFoundError:
            continue
    return -1, "import-linter CLI not found"


def _get_imports(filepath: Path) -> set[str]:
    """Get all module imports from a Python file using AST."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


@pytest.mark.unit
@pytest.mark.quality
class TestDependencies:
    """Internal dependency checks."""

    def test_no_circular_imports(self):
        """No circular imports should exist between top-level packages.

        Uses AST-based detection (no external dependency on import-
        linter). Falls back to import-linter if installed and
        configured.
        """
        # Try import-linter first if available
        exit_code, output = _run_import_linter()
        if (
            exit_code != -1
            and "no contracts" not in output.lower()
            and "config" not in output.lower()
        ):
            assert exit_code == 0, f"import-linter found violations:\n{output[:2000]}"
            return
        # Fallback: AST-based circular import detection
        packages = ["domain", "application", "infrastructure", "interfaces"]
        graph: dict[str, set[str]] = {p: set() for p in packages}
        for pkg in packages:
            pkg_dir = SRC_DIR / pkg
            if not pkg_dir.exists():
                continue
            for py_file in pkg_dir.rglob("*.py"):
                imports = _get_imports(py_file)
                for imp in imports:
                    for other in packages:
                        if other != pkg and imp.startswith(f"soar_lab.{other}"):
                            graph[pkg].add(other)
        cycles = []
        for a in packages:
            for b in graph[a]:
                if a in graph.get(b, set()):
                    cycles.append(f"{a} <-> {b}")
        assert not cycles, f"Circular imports found: {cycles}"

    def test_domain_does_not_import_infrastructure(self):
        """Domain layer must not import from infrastructure layer."""
        domain_dir = SRC_DIR / "domain"
        assert domain_dir.exists(), "Domain directory must exist"
        violations = []
        for py_file in domain_dir.rglob("*.py"):
            imports = _get_imports(py_file)
            for imp in imports:
                if imp.startswith("soar_lab.infrastructure"):
                    rel = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel}: imports '{imp}'")
        assert (
            not violations
        ), f"Domain layer imports infrastructure ({len(violations)} violations):\n" + "\n".join(
            violations[:20]
        )

    def test_domain_does_not_import_interfaces(self):
        """Domain layer must not import from interfaces layer."""
        domain_dir = SRC_DIR / "domain"
        assert domain_dir.exists(), "Domain directory must exist"
        violations = []
        for py_file in domain_dir.rglob("*.py"):
            imports = _get_imports(py_file)
            for imp in imports:
                if imp.startswith("soar_lab.interfaces"):
                    rel = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel}: imports '{imp}'")
        assert (
            not violations
        ), f"Domain layer imports interfaces ({len(violations)} violations):\n" + "\n".join(
            violations[:20]
        )

    def test_application_does_not_import_interfaces(self):
        """Application layer must not import from interfaces layer."""
        app_dir = SRC_DIR / "application"
        assert app_dir.exists(), "Application directory must exist"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            imports = _get_imports(py_file)
            for imp in imports:
                if imp.startswith("soar_lab.interfaces"):
                    rel = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel}: imports '{imp}'")
        assert (
            not violations
        ), f"Application layer imports interfaces ({len(violations)} violations):\n" + "\n".join(
            violations[:20]
        )

    def test_application_does_not_import_infrastructure(self):
        """Application layer must not import from infrastructure layer.

        This is a key hexagonal architecture rule: the application layer
        should only depend on domain, not on concrete infrastructure.
        """
        app_dir = SRC_DIR / "application"
        assert app_dir.exists(), "Application directory must exist"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            imports = _get_imports(py_file)
            for imp in imports:
                if imp.startswith("soar_lab.infrastructure"):
                    rel = py_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel}: imports '{imp}'")
        assert not violations, (
            f"Application layer imports infrastructure ({len(violations)} violations):\n"
            + "\n".join(violations[:20])
        )

    def test_no_circular_imports_ast(self):
        """Check for obvious circular imports between top-level packages."""
        packages = ["domain", "application", "infrastructure", "interfaces"]
        # Build import graph
        graph: dict[str, set[str]] = {p: set() for p in packages}
        for pkg in packages:
            pkg_dir = SRC_DIR / pkg
            if not pkg_dir.exists():
                continue
            for py_file in pkg_dir.rglob("*.py"):
                imports = _get_imports(py_file)
                for imp in imports:
                    for other in packages:
                        if other != pkg and imp.startswith(f"soar_lab.{other}"):
                            graph[pkg].add(other)
        # Check for cycles (simple: A->B and B->A)
        cycles = []
        for a in packages:
            for b in graph[a]:
                if a in graph.get(b, set()):
                    cycles.append(f"{a} <-> {b}")
        if cycles:
            print(f"\nCircular dependencies detected: {cycles}")
        # Report the dependency graph
        print("\nDependency graph:")
        for pkg in packages:
            deps = graph.get(pkg, set())
            print(f"  {pkg} -> {deps or '(none)'}")
        assert not cycles, f"Circular imports found: {cycles}"
