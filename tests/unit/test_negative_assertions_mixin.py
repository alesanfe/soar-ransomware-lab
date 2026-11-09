"""Unit tests for NegativeAssertionsMixin (E2E-ORACLE-003).

Each helper is exercised with mocked service clients — both the pass path
(no forbidden effect) and the fail path (effect present → AssertionError).
Query errors must propagate: an unverifiable absence is not an absence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.e2e.base.negative_mixin import NegativeAssertionsMixin


def _mixin() -> NegativeAssertionsMixin:
    m = NegativeAssertionsMixin()
    m.thehive = MagicMock()
    m.es = MagicMock()
    m.shuffle = MagicMock()
    m.workflow_id = "wf-1"
    m.execution = None
    m.POLL_INTERVAL = 0.01
    m.get_service_url = MagicMock(return_value="http://loki:3100")
    return m


def _case(case_id=1, title="", description="", created_at=0):
    return {"caseId": case_id, "title": title, "description": description, "createdAt": created_at}


def _node(label, status):
    return {"action": {"label": label}, "status": status}


class TestAssertNoCaseCreated:
    def test_passes_when_no_case_matches(self):
        m = _mixin()
        m.thehive.search_cases.return_value = [
            _case(1, description="other-alert"),
            _case(2, title="TC-99"),
        ]
        m.assert_no_case_created("TC-34-REJ")

    def test_fails_when_case_matches(self):
        m = _mixin()
        m.thehive.search_cases.return_value = [
            _case(7, description="alert TC-34-REJ found"),
        ]
        with pytest.raises(AssertionError, match="7"):
            m.assert_no_case_created("TC-34-REJ")

    def test_since_bounds_the_window(self):
        m = _mixin()
        old = _case(7, description="TC-34-REJ", created_at=1_000_000)
        m.thehive.search_cases.return_value = [old]
        # case created before `since` → not a violation
        m.assert_no_case_created("TC-34-REJ", since=datetime.now(UTC))
        # without a bound it IS a violation
        with pytest.raises(AssertionError):
            m.assert_no_case_created("TC-34-REJ")

    def test_query_errors_propagate(self):
        m = _mixin()
        m.thehive.search_cases.side_effect = ConnectionError("thehive down")
        with pytest.raises(ConnectionError):
            m.assert_no_case_created("TC-34-REJ")


class TestAssertNoContainmentAction:
    def test_passes_when_no_containment_node_ran(self):
        m = _mixin()
        m.shuffle.get_execution.return_value = {
            "results": [
                _node("verify_es", "SUCCESS"),
                _node("isolate_host", "SKIPPED"),
            ]
        }
        m.assert_no_containment_action("exec-1")

    def test_fails_when_containment_node_succeeded(self):
        m = _mixin()
        m.shuffle.get_execution.return_value = {"results": [_node("isolate_host", "SUCCESS")]}
        with pytest.raises(AssertionError, match="isolate_host"):
            m.assert_no_containment_action("exec-1")

    def test_failed_containment_node_is_not_an_effect(self):
        m = _mixin()
        m.shuffle.get_execution.return_value = {"results": [_node("block_ip", "FAILURE")]}
        m.assert_no_containment_action("exec-1")

    def test_self_reported_skip_is_not_an_effect(self):
        # Verified live: the "containment" gate node is marked SUCCESS by
        # Shuffle but its result says {"skipped": true} — no effect.
        import json

        m = _mixin()
        node = _node("containment", "SUCCESS")
        node["result"] = json.dumps(
            {
                "success": True,
                "message": {"success": True, "skipped": True, "reason": "containment not required"},
            }
        )
        m.shuffle.get_execution.return_value = {"results": [node]}
        m.assert_no_containment_action("exec-1")

    def test_executed_containment_without_skip_fails(self):
        import json

        m = _mixin()
        node = _node("containment", "SUCCESS")
        node["result"] = json.dumps(
            {
                "success": True,
                "message": {"success": True, "skipped": False, "action": "host isolated"},
            }
        )
        m.shuffle.get_execution.return_value = {"results": [node]}
        with pytest.raises(AssertionError, match="containment"):
            m.assert_no_containment_action("exec-1")


class TestAssertNodeNotExecuted:
    def _ex(self, nodes):
        return SimpleNamespace(
            thehive=MagicMock(),
            es=MagicMock(),
            shuffle=MagicMock(),
            workflow_id="wf",
            execution={"results": nodes},
            POLL_INTERVAL=0.01,
        )

    def test_skipped_node_passes(self):
        m = _mixin()
        m.execution = {"results": [_node("misp_lookup", "SKIPPED")]}
        m.assert_node_not_executed("misp_lookup")

    def test_success_node_fails(self):
        m = _mixin()
        m.execution = {"results": [_node("create_case", "SUCCESS")]}
        with pytest.raises(AssertionError, match="create_case"):
            m.assert_node_not_executed("create_case")

    def test_absent_node_passes(self):
        m = _mixin()
        m.execution = {"results": [_node("other", "SUCCESS")]}
        m.assert_node_not_executed("create_case")


class TestAssertNoDuplicateExecution:
    def _resp(self, n, key="key-1"):
        return {
            "hits": {"hits": [{"_id": f"doc-{i}", "_source": {"alert_id": key}} for i in range(n)]}
        }

    def test_single_doc_passes(self):
        m = _mixin()
        m.es.search.return_value = self._resp(1)
        m.assert_no_duplicate_execution("key-1")

    def test_zero_docs_passes(self):
        m = _mixin()
        m.es.search.return_value = self._resp(0)
        m.assert_no_duplicate_execution("key-1")

    def test_two_docs_fails(self):
        m = _mixin()
        m.es.search.return_value = self._resp(2)
        with pytest.raises(AssertionError, match="key-1"):
            m.assert_no_duplicate_execution("key-1")

    def test_fuzzy_hits_without_exact_key_pass(self):
        # Regression (TC-19 live): the broad match query returns docs whose
        # alert_id merely shares tokens — they must not count as duplicates.
        m = _mixin()
        m.es.search.return_value = {
            "hits": {
                "hits": [
                    {"_id": "d1", "_source": {"alert_id": "key-1-other"}},
                    {"_id": "d2", "_source": {"alert_id": "key-999"}},
                    {"_id": "d3", "_source": {"unrelated": "key-1"}},
                ]
            }
        }
        m.assert_no_duplicate_execution("key-1")


class TestSecretAndPii:
    def test_secret_absent_passes(self):
        m = _mixin()
        m.es.search.return_value = {"hits": {"hits": []}}
        with patch("tests.e2e.base.negative_mixin.requests.get") as g:
            g.return_value = MagicMock(
                status_code=200,
                json=lambda: {"data": {"result": []}},
                raise_for_status=lambda: None,
            )
            m.assert_secret_not_persisted("s3cr3t")

    def test_secret_in_es_fails(self):
        m = _mixin()
        m.es.search.return_value = {
            "hits": {"hits": [{"_id": "d1", "_source": {"payload": "x s3cr3t y"}}]}
        }
        with pytest.raises(AssertionError, match="d1"):
            m.assert_secret_not_persisted("s3cr3t", check_loki=False)

    def test_pii_unmasked_fails(self):
        m = _mixin()
        m.es.search.return_value = {
            "hits": {"hits": [{"_id": "d9", "_source": {"phone": "555-1234"}}]}
        }
        with pytest.raises(AssertionError, match="d9"):
            m.assert_pii_not_present("555-1234", check_loki=False)

    def test_es_hit_not_containing_value_passes(self):
        # The phrase query can return near-misses; the client-side filter
        # must require the literal value inside _source.
        m = _mixin()
        m.es.search.return_value = {
            "hits": {"hits": [{"_id": "d1", "_source": {"payload": "unrelated-value"}}]}
        }
        m.assert_secret_not_persisted("s3cr3t", check_loki=False)

    def test_secret_in_loki_fails(self):
        m = _mixin()
        m.es.search.return_value = {"hits": {"hits": []}}
        with patch("tests.e2e.base.negative_mixin.requests.get") as g:
            g.return_value = MagicMock(
                json=lambda: {"data": {"result": [{"values": [["1", "x"]]}]}},
                raise_for_status=lambda: None,
            )
            with pytest.raises(AssertionError, match="loki"):
                m.assert_secret_not_persisted("s3cr3t")


class TestSideEffectSnapshot:
    def test_no_growth_passes(self):
        m = _mixin()
        m.thehive.search_cases.return_value = [_case(1)]
        m.es.count.return_value = 10
        snap = m.take_side_effect_snapshot()
        m.assert_no_unexpected_side_effects(snap)

    def test_unexpected_growth_fails(self):
        m = _mixin()
        m.thehive.search_cases.side_effect = [
            [_case(1)],  # snapshot
            [_case(1), _case(2)],  # after
        ]
        m.es.count.return_value = 10
        snap = m.take_side_effect_snapshot()
        with pytest.raises(AssertionError, match="thehive_cases"):
            m.assert_no_unexpected_side_effects(snap)

    def test_allowed_growth_passes(self):
        m = _mixin()
        m.thehive.search_cases.side_effect = [
            [_case(1)],
            [_case(1), _case(2)],
        ]
        m.es.count.return_value = 10
        snap = m.take_side_effect_snapshot()
        m.assert_no_unexpected_side_effects(snap, allowed_growth={"thehive_cases": 1})

    def test_unmeasurable_counters_skipped(self):
        m = _mixin()
        m.thehive.search_cases.side_effect = ConnectionError("down")
        m.es.count.return_value = 5
        snap = m.take_side_effect_snapshot()
        assert snap["thehive_cases"] == -1
        m.assert_no_unexpected_side_effects(snap)


class TestRemainsAbsent:
    def test_absent_throughout_passes(self):
        m = _mixin()
        m.assert_remains_absent(lambda: False, duration=0.02)

    def test_appearing_effect_fails(self):
        m = _mixin()
        calls = iter([False, False, True])
        with pytest.raises(AssertionError, match="probe"):
            m.assert_remains_absent(lambda: next(calls), duration=5.0, description="probe")
