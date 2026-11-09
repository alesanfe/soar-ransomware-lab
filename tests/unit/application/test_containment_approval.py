"""F4: ContainmentApprovalStore — analyst-in-the-loop parking."""

import time

import pytest

from soar_lab.application.use_cases.containment_approval import (
    MAX_PENDING_APPROVALS,
    STATUS_APPROVED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ContainmentApprovalStore,
)

REQ = {"alert_id": "A1", "case_id": "C1", "hostname": "ws-01", "mode": "simulated"}


class TestStore:
    def test_create_parks_request(self):
        s = ContainmentApprovalStore()
        r = s.create(REQ)
        assert r["status"] == STATUS_PENDING
        assert r["approval_id"].startswith("appr-")
        assert len(s.pending()) == 1

    def test_approve_marks_decided(self):
        s = ContainmentApprovalStore()
        rid = s.create(REQ)["approval_id"]
        r = s.decide(rid, approve=True, decided_by="analyst")
        assert r["status"] == STATUS_APPROVED
        assert r["decided_by"] == "analyst"
        assert s.pending() == []

    def test_reject_marks_decided(self):
        s = ContainmentApprovalStore()
        rid = s.create(REQ)["approval_id"]
        r = s.decide(rid, approve=False)
        assert r["status"] == STATUS_REJECTED

    def test_double_decide_rejected(self):
        s = ContainmentApprovalStore()
        rid = s.create(REQ)["approval_id"]
        s.decide(rid, approve=True)
        assert s.decide(rid, approve=False) is None

    def test_unknown_id(self):
        s = ContainmentApprovalStore()
        assert s.get("nope") is None
        assert s.decide("nope", approve=True) is None

    def test_expiry(self, monkeypatch):
        s = ContainmentApprovalStore(ttl_seconds=10)
        rid = s.create(REQ)["approval_id"]
        real = time.time
        monkeypatch.setattr(time, "time", lambda: real() + 20)
        assert s.get(rid)["status"] == STATUS_EXPIRED
        assert s.decide(rid, approve=True) is None

    def test_backlog_cap(self):
        s = ContainmentApprovalStore()
        for _ in range(MAX_PENDING_APPROVALS):
            s.create(REQ)
        with pytest.raises(RuntimeError):
            s.create(REQ)
