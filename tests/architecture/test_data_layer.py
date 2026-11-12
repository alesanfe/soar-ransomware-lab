"""Architecture gates — data layer (eval 40).

Static invariants for the persistence layer documented in
``docs/40-eval-data-layer.md``: ES index schema control and retention for
the ``soar-alerts``/``soar-metrics`` corpus, the ES-backed read repository
that fixed the empty-SQLite divergence, and the production SQLite pragmas.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGURE_ES = ROOT / "scripts" / "setup" / "configure_es.py"
SQLITE_REPO = ROOT / "src" / "soar_lab" / "infrastructure" / "persistence" / "sqlite_alert_repository.py"
ES_REPO = ROOT / "src" / "soar_lab" / "infrastructure" / "persistence" / "elasticsearch_alert_repository.py"
COMPOSITION = ROOT / "src" / "soar_lab" / "interfaces" / "api" / "composition.py"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --- Index schema control --------------------------------------------------

def test_soar_index_template_exists():
    src = _read(CONFIGURE_ES)
    assert "_template/soar_lab_indices" in src
    assert '"soar-alerts*"' in src and '"soar-metrics-*"' in src


def test_template_maps_semantic_types():
    src = _read(CONFIGURE_ES)
    assert '"src_ip": {"type": "ip"}' in src
    assert '"all_ips": {"type": "ip"}' in src
    for field in ("alert_id", "alert_type", "status", "hostname", "mitre_techniques"):
        assert f'"{field}": {{"type": "keyword"}}' in src
    for field in ("@timestamp", "timestamp", "detection_time"):
        assert f'"{field}": {{"type": "date"}}' in src


def test_strings_default_to_text_with_keyword_subfield():
    src = _read(CONFIGURE_ES)
    assert "strings_as_text_keyword" in src
    assert '"keyword", "ignore_above": 256' in src.replace("\n", " ")


# --- Retention --------------------------------------------------------------

def test_ilm_policy_created():
    src = _read(CONFIGURE_ES)
    assert "_ilm/policy/soar-retention" in src
    assert '"min_age": "90d"' in src and '"delete"' in src


def test_template_attaches_lifecycle():
    src = _read(CONFIGURE_ES)
    assert '"index.lifecycle.name": "soar-retention"' in src


def test_existing_indices_get_retention_and_keyword_subfields():
    src = _read(CONFIGURE_ES)
    # The live-update loop must cover both production indices and must add
    # keyword sub-fields to dynamically-mapped text fields (legal update,
    # no reindex) instead of leaving them aggregation-blind.
    assert '("soar-alerts", "soar-metrics-v2")' in src
    assert f"/{{idx}}/_settings" in src and "index.lifecycle.name" in src
    assert f"/{{idx}}/_mapping" in src
    assert 'm.get("type") == "text" and "keyword" not in m.get("fields", {})' in src


# --- ES-backed alert repository ---------------------------------------------

def test_es_repo_subclasses_sqlite_and_overrides_reads():
    src = _read(ES_REPO)
    assert "class ElasticsearchAlertRepository(SqliteAlertRepository)" in src
    for method in ("get_alert", "get_alerts", "count_alerts"):
        assert re.search(rf"def {method}\(", src), method
        # every override falls back to SQLite on transport failure
        assert f"super().{method}" in src


def test_es_repo_uses_lab_ca_and_pinned_index():
    src = _read(ES_REPO)
    assert "ca_verify()" in src
    assert '_ALERTS_INDEX = "soar-alerts"' in src
    assert "DEFAULT_ELASTICSEARCH_URL" in src  # ultimate fallback URL


def test_es_repo_queries_keyword_alert_id():
    # The production mapping exposes alert_id as keyword-capable; a term
    # query on the plain text field would miss exact ids.
    src = _read(ES_REPO)
    assert '"alert_id.keyword"' in src


def test_es_repo_doc_to_row_preserves_contract():
    src = _read(ES_REPO)
    assert '"data": doc' in src  # full ES doc kept under data like sqlite json payload


def test_composition_wires_es_repo():
    src = _read(COMPOSITION)
    assert "ElasticsearchAlertRepository" in src
    assert "self.alert_repository = ElasticsearchAlertRepository(" in src


# --- SQLite baseline (unchanged invariants) ----------------------------------

def test_sqlite_pragmas_production():
    src = _read(SQLITE_REPO)
    assert "journal_mode=WAL" in src
    assert "busy_timeout" in src
    assert "foreign_keys=ON" in src


def test_sqlite_parameterized_writes_and_upsert():
    src = _read(SQLITE_REPO)
    assert "ON CONFLICT" in src
    assert not re.search(r'execute\(\s*f["\']', src)
