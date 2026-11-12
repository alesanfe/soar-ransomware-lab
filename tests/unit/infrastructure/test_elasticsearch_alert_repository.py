"""Unit tests for the Elasticsearch-backed alert repository (eval 40)."""

from unittest.mock import MagicMock, patch

import pytest

from soar_lab.infrastructure.persistence.elasticsearch_alert_repository import (
    ElasticsearchAlertRepository,
)


def _repo(tmp_path):
    return ElasticsearchAlertRepository(db_path=str(tmp_path / "t.db"))


def _doc(**kw):
    base = {
        "alert_id": "A-1",
        "alert_type": "ransomware",
        "severity": 3,
        "hostname": "victim-01",
        "status": "processed",
        "timestamp": "2026-01-01T00:00:00Z",
    }
    base.update(kw)
    return base


def test_doc_to_row_matches_sqlite_shape(tmp_path):
    row = _repo(tmp_path)._doc_to_row(_doc(src_ip="10.0.0.1"))
    assert row["alert_id"] == "A-1" and row["status"] == "processed"
    assert row["data"]["src_ip"] == "10.0.0.1"  # full doc preserved
    for k in ("id", "alert_type", "severity", "hostname", "timestamp"):
        assert k in row


def test_get_alerts_maps_es_hits(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search", return_value=[_doc(alert_id="A-1"), _doc(alert_id="A-2")]) as s:
        rows = repo.get_alerts(limit=5)
    assert [r["alert_id"] for r in rows] == ["A-1", "A-2"]
    body = s.call_args[0][0]
    assert body["size"] == 5 and "sort" in body


def test_get_alerts_numeric_severity_term(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search", return_value=[]) as s:
        repo.get_alerts(severity="3")
    assert s.call_args[0][0]["query"] == {"term": {"severity": 3}}


def test_get_alerts_non_numeric_severity_returns_empty(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search") as s:
        assert repo.get_alerts(severity="high") == []
        s.assert_not_called()


def test_get_alerts_falls_back_to_sqlite_on_error(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search", side_effect=ConnectionError("down")):
        assert repo.get_alerts() == []  # empty sqlite, but no exception


def test_get_alert_uses_keyword_term(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search", return_value=[_doc()]) as s:
        assert repo.get_alert("A-1")["alert_id"] == "A-1"
    assert s.call_args[0][0]["query"] == {"term": {"alert_id.keyword": "A-1"}}


def test_get_alert_missing_returns_none(tmp_path):
    repo = _repo(tmp_path)
    with patch.object(repo, "_search", return_value=[]):
        assert repo.get_alert("nope") is None


def test_count_alerts_falls_back_on_error(tmp_path):
    repo = _repo(tmp_path)
    with patch("soar_lab.infrastructure.persistence.elasticsearch_alert_repository.requests.get",
               side_effect=ConnectionError("down")):
        assert repo.count_alerts() == 0


def test_cases_still_served_by_sqlite(tmp_path):
    repo = _repo(tmp_path)
    repo.store_case({"case_id": "C-1", "title": "t", "status": "open", "severity": "high"})
    assert repo.count_cases() == 1  # inherited path untouched
