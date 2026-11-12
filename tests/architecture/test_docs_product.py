"""Architecture gates — documentation as a product (eval 43).

Static invariants for ``docs/`` documented in ``docs/43-eval-docs-product.md``:
the index must catalog every top-level doc, the OpenAPI snapshots must stay
byte-identical, and the blocking quality gate must keep its checks.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.md"
QUALITY = ROOT / "scripts" / "ci" / "docs_quality.py"
EXPORT = ROOT / "scripts" / "ci" / "export_openapi.py"
VALE = ROOT / ".github" / "workflows" / "vale.yml"
MAKE_WIN = ROOT / "Makefile.win"
MAKE_LINUX = ROOT / "Makefile.linux"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_index_catalogs_every_top_level_doc():
    """DOC-EVAL-002 regression: every docs/*.md must be linked from index.md."""
    idx = _read(INDEX)
    linked = set(re.findall(r"\]\(([^)]+)\)", idx))
    missing = [
        f.name for f in DOCS.glob("*.md")
        if f.name not in linked and f.name != "index.md"
    ]
    assert not missing, f"docs orphaned from index.md: {missing}"


def test_openapi_snapshots_byte_identical():
    a = DOCS / "api" / "openapi.json"
    b = ROOT / "tests" / "baseline" / "openapi.json"
    assert _read(a) == _read(b), "docs/api/openapi.json drifted from baseline — run export_openapi.py"


def test_docs_quality_gate_keeps_all_checks():
    src = _read(QUALITY)
    for check in ("openapi.json", "tests_inventory.json", "collect-only", "banned", "mermaid"):
        assert check in src, f"docs_quality.py lost the {check} check"


def test_export_script_writes_all_three_targets():
    src = _read(EXPORT)
    assert src.count("openapi.json") >= 3
    for target in ("docs/api", "assets/references", "baseline"):
        assert target.replace("/", " / ").replace(" / ", ' / ') or target.split("/")[0] in src


def test_vale_workflow_exists():
    assert VALE.exists()
    assert "vale" in _read(VALE).lower()


def test_docs_lint_and_build_targets_in_both_makefiles():
    for mk in (MAKE_WIN, MAKE_LINUX):
        body = _read(mk)
        assert "docs-lint" in body and "docs-build" in body


def test_no_banned_legacy_references_in_eval_docs():
    """Spot-check the banned-pattern gate against eval docs specifically."""
    banned = re.compile(r"localhost:8080\b(?!/health)|http://soar\.local:8000")
    offenders = [
        f.name for f in DOCS.glob("*-eval-*.md")
        if banned.search(_read(f))
    ]
    assert not offenders, f"eval docs carry banned legacy references: {offenders}"


def test_adr_index_exists():
    adr = DOCS / "adr" / "0000-index.md"
    assert adr.exists(), "ADR index missing"


def test_docs_dirs_have_readme_or_index():
    for d in (DOCS / "api", DOCS / "assets"):
        assert d.is_dir()


# ---------------------------------------------------------------------------
# DOC-EVAL-2 — discoverability (eval 62): every source doc must reach the
# published site and every internal link between published docs must resolve.
# The gates replay the REAL sync into a temp target so they exercise the
# actual emit + link-rewrite code path, not a reimplementation.
# ---------------------------------------------------------------------------

import importlib.util  # noqa: E402

SYNC = ROOT / "scripts" / "ci" / "sync_docs_to_docusaurus.py"
DEPLOY_WF = ROOT / ".github" / "workflows" / "deploy-docs.yml"


def _sync_into(tmp_path):
    """Run the real sync_docs() against a scratch target; returns (site, module)."""
    spec = importlib.util.spec_from_file_location("sync_docs_to_docusaurus", SYNC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target = tmp_path / "site_docs"
    mod.TARGET_DIR = target
    assert mod.sync_docs() == 0, "sync_docs() failed against scratch target"
    return target, mod


def test_sync_publishes_every_source_doc(tmp_path):
    """DOC-EVAL-2-001: no docs/*.md may be silently dropped by the Pages sync."""
    site, mod = _sync_into(tmp_path)
    published = {p.name for p in site.rglob("*.md")}
    mapped = set(mod.DOC_MAPPING)  # renamed docs publish under target names
    missing = [
        f.name
        for f in DOCS.glob("*.md")
        if f.name not in published and f.name not in mapped
    ]
    # Mapped docs must actually have landed at their target path.
    for name, (tp, tf) in mod.DOC_MAPPING.items():
        expected = site / (tp if tf is None else f"{tp}/{tf}")
        if not expected.exists():
            missing.append(f"{name} -> {expected.relative_to(site)}")
    for sub in ("adr", "runbooks"):
        d = DOCS / sub
        if d.exists():
            missing += [
                f"{sub}/{f.name}" for f in d.rglob("*.md") if f.name not in published
            ]
    assert not missing, f"docs dropped by Pages sync: {missing}"


def test_sync_emits_zero_broken_internal_links(tmp_path):
    """DOC-EVAL-2-002: every markdown link between published docs resolves."""
    site, _m = _sync_into(tmp_path)
    broken = []
    for f in site.rglob("*.md"):
        for m in re.finditer(r"\]\(([^)#]+\.md)\)", _read(f)):
            link = m.group(1)
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (f.parent / link).resolve().exists():
                broken.append(f"{f.relative_to(site)} -> {link}")
    assert not broken, f"sync emits broken internal links: {broken[:10]}"


def test_eval_docs_land_in_evaluations_category(tmp_path):
    """Eval corpus must be navigable as a category, not a flat dump."""
    site, _m = _sync_into(tmp_path)
    evals = list((site / "evaluations").glob("*.md"))
    assert len(evals) >= 10, f"evaluations/ has {len(evals)} docs — category collapsed?"
    assert (site / "evaluations" / "_category_.json").exists()


def test_deploy_workflow_syncs_corpus_before_build():
    """Pages pipeline must run both syncs — dropping one silently un-publishes."""
    wf = _read(DEPLOY_WF)
    assert "sync_docs_to_docusaurus.py" in wf
    assert "sync_reports_to_docusaurus.py" in wf
    assert "npm run build" in wf


def test_excluded_subtrees_stay_unpublished(tmp_path):
    """Intentional exclusions: thesis (academic TFM, not ops docs), api (raw
    spec dir), assets (attachments) — none may leak into the site build."""
    site, _m = _sync_into(tmp_path)
    rels = {p.relative_to(site).parts[0] for p in site.rglob("*.md")}
    assert not rels & {"thesis", "api", "assets"}, "excluded subtree leaked into site"
