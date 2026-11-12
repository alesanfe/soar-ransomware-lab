#!/usr/bin/env python3
"""TC-38: workflow timeout & orphan-execution garbage collection.

Shuffle leaves interrupted executions stuck in EXECUTING forever
(worker/orborus crash, timeout). ``StaleExecutionGC`` is the production
sweeper — these tests inject fabricated zombie docs into the real
``workflowexecution`` index and assert the GC aborts exactly the stale
ones, idempotently.
"""

import time

import pytest
import requests

from tests.e2e.base import E2EBaseTest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.resilience,
]

try:
    from soar_lab.infrastructure.monitoring.stale_execution_gc import StaleExecutionGC
except ImportError:  # src layout differs outside container
    StaleExecutionGC = None


class TestWorkflowTimeouts(E2EBaseTest):
    tc_id = "TC-38"

    INDEX = "workflowexecution"

    def _os(self) -> str:
        return self.env.get(
            "SHUFFLE_OPENSEARCH_URL",
            self.env.get("OPENSEARCH_URL", "https://opensearch:9200"),
        ).rstrip("/")

    def _put_exec(self, doc_id: str, status: str, started_at: float) -> None:
        r = requests.put(
            f"{self._os()}/{self.INDEX}/_doc/{doc_id}?refresh=true",
            auth=self.s.auth,
            verify=self.s.verify,
            json={
                "execution_id": doc_id,
                "status": status,
                "started_at": int(started_at),
                "workflow": {"id": "gc-test-wf"},
                "source": "tc38",
            },
            timeout=15,
        )
        assert r.status_code in (200, 201), r.text[:200]

    def _get_status(self, doc_id: str) -> str:
        r = requests.get(
            f"{self._os()}/{self.INDEX}/_doc/{doc_id}",
            auth=self.s.auth,
            verify=self.s.verify,
            timeout=15,
        )
        assert r.status_code == 200
        return r.json()["_source"].get("status", "")

    def _del(self, doc_id: str) -> None:
        requests.delete(
            f"{self._os()}/{self.INDEX}/_doc/{doc_id}",
            auth=self.s.auth,
            verify=self.s.verify,
            timeout=10,
        )

    # ── TC-38-01 ──────────────────────────────────────────────────────────

    def test_gc_aborts_only_stale_executing(self):
        """Fabricate a 2h-old EXECUTING zombie + a fresh one + a FINISHED doc.
        GC must abort ONLY the stale EXECUTING doc."""
        stale_id = f"tc38-stale-{int(time.time())}"
        fresh_id = f"tc38-fresh-{int(time.time())}"
        done_id = f"tc38-done-{int(time.time())}"
        old_ts = time.time() - 7200  # 2h ago — past the 30min stale window
        try:
            self._put_exec(stale_id, "EXECUTING", old_ts)
            self._put_exec(fresh_id, "EXECUTING", time.time())
            self._put_exec(done_id, "FINISHED", old_ts)

            gc = StaleExecutionGC(
                os_url=self._os(),
                backend_url=self.env.get("SHUFFLE_URL", "https://shuffle-backend:5443"),
                api_key=self.env.get("SHUFFLE_DEFAULT_APIKEY", ""),
                stale_minutes=30,
            )
            gc.collect_once()

            assert self._get_status(stale_id) == "ABORTED", (
                f"zombie not aborted: {self._get_status(stale_id)}"
            )
            assert self._get_status(fresh_id) == "EXECUTING", (
                "fresh execution wrongly aborted"
            )
            assert self._get_status(done_id) == "FINISHED", (
                "finished doc wrongly touched"
            )
        finally:
            for i in (stale_id, fresh_id, done_id):
                self._del(i)

    # ── TC-38-02 ──────────────────────────────────────────────────────────

    def test_gc_idempotent_double_pass(self):
        """Second GC pass must not raise nor re-mutate the aborted doc."""
        doc_id = f"tc38-idem-{int(time.time())}"
        try:
            self._put_exec(doc_id, "EXECUTING", time.time() - 7200)
            gc = StaleExecutionGC(
                os_url=self._os(),
                backend_url=self.env.get("SHUFFLE_URL", "https://shuffle-backend:5443"),
                api_key=self.env.get("SHUFFLE_DEFAULT_APIKEY", ""),
                stale_minutes=30,
            )
            gc.collect_once()
            gc.collect_once()  # idempotent — no error, stays ABORTED
            assert self._get_status(doc_id) == "ABORTED"
        finally:
            self._del(doc_id)

    # ── TC-38-03 ──────────────────────────────────────────────────────────

    def test_no_zombie_executing_older_than_stale_window(self):
        """Production check: no EXECUTING doc older than the stale window
        may exist right now (GC is wired into the API lifecycle)."""
        r = requests.post(
            f"{self._os()}/{self.INDEX}/_search",
            auth=self.s.auth,
            verify=self.s.verify,
            json={
                "size": 20,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "bool": {
                                    "should": [
                                        {"term": {"status": "EXECUTING"}},
                                        {"term": {"status.keyword": "EXECUTING"}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            },
                            {
                                "range": {
                                    "started_at": {
                                        "lt": int(time.time()) - 40 * 60
                                    }
                                }
                            },
                        ],
                    }
                },
                "_source": ["execution_id", "started_at"],
            },
            timeout=15,
        )
        assert r.status_code == 200
        hits = r.json()["hits"]["hits"]
        zombies = [
            h["_id"]
            for h in hits
            if not h["_id"].startswith("tc38-")  # ignore our own fixtures
        ]
        assert not zombies, (
            f"stale EXECUTING zombies alive despite GC: {zombies[:5]}"
        )

    # ── TC-38-04..07: TMO-001 state machine + metrics ─────────────────────

    def _gc(self) -> "StaleExecutionGC":
        return StaleExecutionGC(
            os_url=self._os(),
            backend_url=self.env.get("SHUFFLE_URL", "https://shuffle-backend:5443"),
            api_key=self.env.get("SHUFFLE_DEFAULT_APIKEY", ""),
            stale_minutes=30,
        )

    def _get_source(self, doc_id: str) -> dict:
        r = requests.get(f"{self._os()}/{self.INDEX}/_doc/{doc_id}", auth=self.s.auth, verify=self.s.verify, timeout=15)
        assert r.status_code == 200
        return r.json()["_source"]

    def test_timeout_state_machine_audit_trail(self):
        """A stale doc must end ABORTED *through* the state machine —
        timed_out_at and cancel_requested_at prove it passed TIMED_OUT and
        a cancel was issued, not a blind flag flip."""
        doc_id = f"tc38-trail-{int(time.time())}"
        try:
            self._put_exec(doc_id, "EXECUTING", time.time() - 7200)
            self._gc().collect_once()
            src = self._get_source(doc_id)
            assert src["status"] == "ABORTED"
            assert src.get("timed_out_at"), "no TIMED_OUT transition recorded"
            assert src.get("cancel_requested_at"), "no cancel issued"
            assert src["timed_out_at"] <= src["cancel_requested_at"]
        finally:
            self._del(doc_id)

    def test_late_result_is_reconciled_not_clobbered(self):
        """A doc that flips to FINISHED between the stale scan and the
        transition must NOT be touched — conditional update reconciles."""
        doc_id = f"tc38-late-{int(time.time())}"
        try:
            self._put_exec(doc_id, "EXECUTING", time.time() - 7200)
            gc = self._gc()
            # The result lands before the GC pass mutates anything:
            requests.post(
                f"{self._os()}/{self.INDEX}/_update/{doc_id}?refresh=true",
                auth=self.s.auth,
                verify=self.s.verify,
                json={"doc": {"status": "FINISHED"}},
                timeout=15,
            )
            gc.collect_once()
            assert self._get_status(doc_id) == "FINISHED", (
                "GC clobbered a late-arriving FINISHED result"
            )
        finally:
            self._del(doc_id)

    def test_cancelling_forced_abort_after_max_confirms(self):
        """A CANCELLING doc whose backend never confirms must still
        terminate: after MAX_CONFIRM_ATTEMPTS it is ABORTED(forced=true).

        To make the backend genuinely report "still executing" we borrow a
        real in-flight execution id (ambient locust load keeps them coming);
        if none is in flight we still assert the termination guarantee.
        """
        doc_id = f"tc38-forced-{int(time.time())}"
        real = requests.post(
            f"{self._os()}/{self.INDEX}/_search",
            auth=self.s.auth,
            verify=self.s.verify,
            json={
                "size": 1,
                "sort": [{"started_at": "desc"}],
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"status": "EXECUTING"}},
                            {"term": {"status.keyword": "EXECUTING"}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "_source": ["execution_id", "workflow_id", "workflow"],
            },
            timeout=15,
        ).json()["hits"]["hits"]
        eid = wf = None
        if real:
            src = real[0]["_source"]
            eid = src.get("execution_id")
            wf = src.get("workflow_id") or (src.get("workflow") or {}).get("id")
        try:
            self._put_exec(doc_id, "CANCELLING", time.time() - 7200)
            requests.post(
                f"{self._os()}/{self.INDEX}/_update/{doc_id}?refresh=true",
                auth=self.s.auth,
                verify=self.s.verify,
                json={"doc": {"confirm_attempts": 5,
                              "execution_id": eid or "tc38-nonexistent",
                              "workflow_id": wf}},
                timeout=15,
            )
            self._gc().collect_once()
            src = self._get_source(doc_id)
            assert src["status"] == "ABORTED", src["status"]
            if eid:
                assert src.get("forced") is True, (
                    f"backend still reports executing — expected forced abort, "
                    f"got forced={src.get('forced')}"
                )
            else:
                assert src.get("aborted_at"), "no termination evidence recorded"
        finally:
            self._del(doc_id)

    def test_timeout_metrics_exposed_on_prometheus_endpoint(self):
        """GET /metrics must expose the GC gauges/counters."""
        api_url = self.env.get("API_URL", "http://api:8000").rstrip("/")
        r = requests.get(f"{api_url}/metrics", timeout=15)
        assert r.status_code == 200
        body = r.text
        assert "soar_workflow_stuck_total" in body
        assert "soar_workflow_oldest_executing_seconds" in body
        # Gauge must be a finite non-negative float
        for line in body.splitlines():
            if line.startswith("soar_workflow_oldest_executing_seconds"):
                assert float(line.split()[-1]) >= 0

    def test_node_durations_bounded_observed(self):
        """Per-node timeout evidence (TC-38-08): every recorded node timing
        in soar-metrics must stay under the workflow-level bound — no node
        may run unbounded inside a bounded workflow."""
        r = requests.post(
            f"{self.env.get('ES_URL', 'https://elasticsearch:9200')}/soar-metrics*/_search",
            auth=(
                self.env.get("ELASTIC_USERNAME", "elastic"),
                self.env.get("ELASTIC_PASSWORD", ""),
            ),
            verify=self.s.verify,
            json={
                "size": 50,
                "sort": [{"timestamp": "desc"}],
                "query": {"match_all": {}},
                "_source": ["node_timings", "execution_id"],
            },
            timeout=15,
        )
        assert r.status_code == 200
        hits = [
            h for h in r.json()["hits"]["hits"]
            if h["_source"].get("node_timings")
        ]
        if not hits:
            pytest.skip("no node_timings samples yet — cannot assert bound")
        max_node_s = 0.0
        for h in hits:
            for node, info in (h["_source"].get("node_timings") or {}).items():
                secs = float((info or {}).get("duration_s", 0) or 0)
                max_node_s = max(max_node_s, secs)
        # A node exceeding the workflow bound would prove per-node
        # timeout is unenforced — the whole point of TMO-001.
        assert max_node_s < 1800, f"node ran {max_node_s}s — unbounded"
