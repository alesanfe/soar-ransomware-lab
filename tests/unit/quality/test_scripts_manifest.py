"""MNT-01: scripts manifest freshness + compile-all smoke."""

import importlib.util
import py_compile
import sys
import tempfile
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "Makefile.win").is_file())
SCRIPTS = ROOT / "scripts"
MANIFEST = ROOT / "docs" / "SCRIPTS-MANIFEST.md"
GEN = ROOT / "scripts" / "ci" / "generate_scripts_manifest.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_manifest_is_fresh():
    mod = _load("generate_scripts_manifest", GEN)
    expected = mod.render(mod.collect()) + "\n"
    assert MANIFEST.exists(), "docs/SCRIPTS-MANIFEST.md missing — run the generator"
    actual = MANIFEST.read_text(encoding="utf-8")
    assert actual == expected, (
        "docs/SCRIPTS-MANIFEST.md is stale — regenerate with "
        "`python scripts/ci/generate_scripts_manifest.py`"
    )


def test_all_scripts_compile():
    """py_compile every script — catches syntax/import-level breakage
    without executing anything (scripts may be destructive)."""
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for path in sorted(SCRIPTS.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            cfile = Path(tmp) / f"{len(failures)}_{path.stem}.pyc"
            try:
                py_compile.compile(str(path), cfile=str(cfile), doraise=True)
            except py_compile.PyCompileError as exc:
                failures.append(f"{path.relative_to(ROOT)}: {exc.msg}")
    assert not failures, "scripts that fail to compile:\n" + "\n".join(failures)
