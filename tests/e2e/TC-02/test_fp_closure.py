"""TC-02 — formal false-positive closure + FP→TP reclassification.

TheHive 5 case statuses: New, InProgress, TruePositive, FalsePositive,
Indeterminate, Duplicated, Other. Closing a case as FP without a recorded
reason is an audit gap — these subtests prove reason persistence and the
reclassification path a real analyst takes when a verdict flips.
"""

from __future__ import annotations

import pytest

from tests.e2e.base import E2EBaseTest


@pytest.mark.e2e
class TestFalsePositiveClosure(E2EBaseTest):
    tc_id = "TC-02"

    def _mk_case(self, title: str) -> str:
        case = self.thehive.create_case(
            title=title,
            description="TC-02 FP-closure subtest case",
            severity=2,
            tags=["tc02", "fp-closure"],
        )
        cid = case.get("id") or case.get("_id") or case.get("caseId")
        assert cid, f"no case id in {case}"
        return str(cid)

    def test_case_closed_false_positive_with_reason(self):
        cid = self._mk_case(f"TC-02 FP close {self.uid('fp')}")
        reason = "Benign admin activity — approved tooling hash match"
        self.thehive.close_case(cid, resolution="FalsePositive", summary=reason)
        case = self.thehive.get_case(cid)
        assert case.get("status") == "FalsePositive", f"status={case.get('status')}"
        # the reason must be persisted, not silently dropped
        assert reason.split("—")[0].strip() in str(case.get("summary", "")), (
            "closure reason not persisted in case summary"
        )

    def test_fp_reclassification_to_true_positive(self):
        """Analyst flips verdict: FP -> reopened -> TP. Final state must be TP."""
        cid = self._mk_case(f"TC-02 reclass {self.uid('rc')}")
        self.thehive.close_case(cid, resolution="FalsePositive", summary="initial FP verdict")
        assert self.thehive.get_case(cid).get("status") == "FalsePositive"

        # reopen + reclassify
        self.thehive.update_case(cid, status="InProgress")
        assert self.thehive.get_case(cid).get("status") == "InProgress"
        self.thehive.close_case(cid, resolution="TruePositive", summary="reclassified: real C2")
        case = self.thehive.get_case(cid)
        assert case.get("status") == "TruePositive", (
            f"reclassification failed — status={case.get('status')}"
        )

    def test_invalid_resolution_status_rejected(self):
        """'Resolved'/'Closed' are not TH5 statuses — server must reject, not accept."""
        cid = self._mk_case(f"TC-02 badstatus {self.uid('bs')}")
        rejected = False
        try:
            self.thehive.close_case(cid, resolution="Resolved", summary="bogus status")
        except Exception:
            rejected = True
        if not rejected:
            case = self.thehive.get_case(cid)
            assert case.get("status") != "Resolved", (
                "TheHive accepted invalid status 'Resolved' — audit contract broken"
            )
