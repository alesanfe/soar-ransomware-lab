"""Exact-contract tests for cortex_job_classifier — constants, precedence
order, hint matching, aggregation shape and truncation boundaries.
"""

from __future__ import annotations

import pytest

from soar_lab.domain.services import cortex_job_classifier as cj
from soar_lab.domain.services.cortex_job_classifier import (
    CATEGORY_EXPECTED_EMPTY,
    CATEGORY_INFRA_FAILURE,
    CATEGORY_SUCCESS,
    CATEGORY_UNKNOWN,
    CATEGORY_VERDICT_ERROR,
    classify_job,
    summarize_jobs,
)


class TestConstants:
    def test_category_values(self):
        assert CATEGORY_SUCCESS == "success"
        assert CATEGORY_EXPECTED_EMPTY == "expected_no_data"
        assert CATEGORY_VERDICT_ERROR == "analyzer_error"
        assert CATEGORY_INFRA_FAILURE == "infrastructure_failure"
        assert CATEGORY_UNKNOWN == "unknown"


class TestClassifyJob:
    def test_all_success_statuses(self):
        for status in ("SUCCESS", "FINISHED", "DONE", "success", "Finished"):
            assert classify_job({"status": status}) == CATEGORY_SUCCESS

    def test_all_inflight_statuses(self):
        for status in ("WAITING", "INPROGRESS", "RUNNING", "STARTED"):
            assert classify_job({"status": status}) == CATEGORY_UNKNOWN

    def test_all_failure_statuses_default_verdict(self):
        for status in ("FAILURE", "FAILED", "ERROR"):
            job = {"status": status, "statusMessage": "analyzer exit 1"}
            assert classify_job(job) == CATEGORY_VERDICT_ERROR

    def test_unknown_status_is_unknown(self):
        assert classify_job({"status": "DELETED"}) == CATEGORY_UNKNOWN
        assert classify_job({}) == CATEGORY_UNKNOWN

    def test_infra_beats_empty_hint(self):
        # message contains BOTH an infra hint and an empty hint — infra wins
        job = {"status": "FAILURE", "statusMessage": "timeout: no data returned"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE

    def test_empty_beats_failure_status(self):
        job = {"status": "FAILED", "statusMessage": "no results for observable"}
        assert classify_job(job) == CATEGORY_EXPECTED_EMPTY

    def test_infra_beats_failure_status(self):
        job = {"status": "ERROR", "statusMessage": "connection refused"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE

    def test_hints_checked_case_insensitively(self):
        job = {"status": "FAILURE", "statusMessage": "DOCKER DAEMON UNREACHABLE"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE

    def test_each_message_field_searched(self):
        for key in ("statusMessage", "message", "error", "errorMessage"):
            job = {"status": "FAILURE", key: "socket closed"}
            assert classify_job(job) == CATEGORY_INFRA_FAILURE, key

    def test_report_fields_searched(self):
        for key in ("errorMessage", "message", "summary"):
            job = {"status": "FAILURE", "report": {key: "connection refused"}}
            assert classify_job(job) == CATEGORY_INFRA_FAILURE, key

    def test_non_dict_report_ignored(self):
        job = {"status": "FAILURE", "report": "not-a-dict", "statusMessage": "x"}
        assert classify_job(job) == CATEGORY_VERDICT_ERROR

    def test_falsy_message_fields_ignored(self):
        job = {"status": "FAILURE", "statusMessage": "", "message": None, "error": 0}
        assert classify_job(job) == CATEGORY_VERDICT_ERROR

    @pytest.mark.parametrize(
        "hint",
        ["connection refused", "timed out", "no such host", "econnrefused", "oom"],
    )
    def test_representative_infra_hints(self, hint):
        job = {"status": "FAILURE", "statusMessage": f"failed: {hint}"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE

    @pytest.mark.parametrize(
        "hint", ["no data", "not found", "nxdomain", "empty", "does not exist"]
    )
    def test_representative_empty_hints(self, hint):
        job = {"status": "FAILURE", "statusMessage": f"result: {hint}"}
        assert classify_job(job) == CATEGORY_EXPECTED_EMPTY


class TestSummarizeJobs:
    def test_return_shape(self):
        s = summarize_jobs([])
        assert s == {"total": 0, "by_category": {}, "by_analyzer": {}, "flagged": []}

    def test_analyzer_resolution_order(self):
        jobs = [
            {
                "status": "SUCCESS",
                "analyzerDefinitionId": "def",
                "workerName": "worker",
                "analyzerName": "name",
            },
            {"status": "SUCCESS", "workerName": "worker", "analyzerName": "name"},
            {"status": "SUCCESS", "analyzerName": "name"},
            {"status": "SUCCESS"},
        ]
        s = summarize_jobs(jobs)
        assert set(s["by_analyzer"]) == {"def", "worker", "name", "unknown"}
        assert s["by_analyzer"]["def"][CATEGORY_SUCCESS] == 1
        assert s["by_analyzer"]["worker"][CATEGORY_SUCCESS] == 1
        assert s["by_analyzer"]["name"][CATEGORY_SUCCESS] == 1
        assert s["by_analyzer"]["unknown"][CATEGORY_SUCCESS] == 1

    def test_flagged_entry_shape(self):
        job = {
            "status": "FAILURE",
            "statusMessage": "timeout while pulling image",
            "id": "job-1",
            "analyzerDefinitionId": "ana-1",
        }
        s = summarize_jobs([job])
        assert s["flagged"] == [
            {
                "job_id": "job-1",
                "analyzer": "ana-1",
                "category": CATEGORY_INFRA_FAILURE,
                "status": "FAILURE",
                "message": "timeout while pulling image",
            }
        ]

    def test_flagged_id_fallback(self):
        job = {"status": "ERROR", "statusMessage": "boom", "_id": "mongo-9"}
        s = summarize_jobs([job])
        assert s["flagged"][0]["job_id"] == "mongo-9"

    def test_flagged_message_prefers_status_message(self):
        job = {
            "status": "FAILURE",
            "statusMessage": "primary",
            "message": "secondary",
        }
        s = summarize_jobs([job])
        assert s["flagged"][0]["message"] == "primary"

    def test_flagged_message_falls_back_to_message(self):
        job = {"status": "FAILURE", "message": "secondary"}
        s = summarize_jobs([job])
        assert s["flagged"][0]["message"] == "secondary"

    def test_flagged_message_empty_default(self):
        s = summarize_jobs([{"status": "FAILURE"}])
        assert s["flagged"][0]["message"] == ""

    def test_flagged_message_truncated_at_300(self):
        job = {"status": "FAILURE", "statusMessage": "x" * 400}
        s = summarize_jobs([job])
        assert len(s["flagged"][0]["message"]) == 300

    def test_benign_categories_not_flagged(self):
        jobs = [
            {"status": "SUCCESS"},
            {"status": "WAITING"},
            {"status": "FAILURE", "statusMessage": "no data"},
        ]
        s = summarize_jobs(jobs)
        assert s["flagged"] == []

    def test_by_category_counts_multiple(self):
        jobs = [{"status": "SUCCESS"}] * 3 + [{"status": "WAITING"}] * 2
        s = summarize_jobs(jobs)
        assert s["by_category"] == {CATEGORY_SUCCESS: 3, CATEGORY_UNKNOWN: 2}
        assert s["total"] == 5
