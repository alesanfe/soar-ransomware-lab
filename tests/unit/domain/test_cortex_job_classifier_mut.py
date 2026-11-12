#!/usr/bin/env python3
"""Mutation-hardening tests for cortex_job_classifier — exact key sets,
status tables, hint priority and aggregation contract."""

from __future__ import annotations

import pytest

from soar_lab.domain.services.cortex_job_classifier import (
    CATEGORY_EXPECTED_EMPTY,
    CATEGORY_INFRA_FAILURE,
    CATEGORY_SUCCESS,
    CATEGORY_UNKNOWN,
    CATEGORY_VERDICT_ERROR,
    classify_job,
    summarize_jobs,
)


class TestClassifyStatus:
    @pytest.mark.parametrize("s", ["SUCCESS", "FINISHED", "DONE"])
    def test_success_statuses(self, s):
        assert classify_job({"status": s}) == CATEGORY_SUCCESS

    @pytest.mark.parametrize("s", ["WAITING", "INPROGRESS", "RUNNING", "STARTED"])
    def test_inflight_statuses(self, s):
        assert classify_job({"status": s}) == CATEGORY_UNKNOWN

    @pytest.mark.parametrize("s", ["FAILURE", "FAILED", "ERROR"])
    def test_failure_statuses_plain(self, s):
        assert classify_job({"status": s, "statusMessage": "weird"}) == (
            CATEGORY_VERDICT_ERROR
        )

    def test_lowercase_status_normalized(self):
        assert classify_job({"status": "success"}) == CATEGORY_SUCCESS
        assert classify_job({"status": "failure"}) == CATEGORY_VERDICT_ERROR

    def test_missing_and_unexpected_status(self):
        assert classify_job({}) == CATEGORY_UNKNOWN
        assert classify_job({"status": "DELETED"}) == CATEGORY_UNKNOWN


class TestMessageKeys:
    @pytest.mark.parametrize(
        "key", ["statusMessage", "message", "error", "errorMessage"]
    )
    def test_each_top_key_searched(self, key):
        assert classify_job({"status": "FAILURE", key: "docker died"}) == (
            CATEGORY_INFRA_FAILURE
        )

    @pytest.mark.parametrize(
        "key", ["errorMessage", "message", "summary"]
    )
    def test_each_report_key_searched(self, key):
        job = {"status": "FAILURE", "report": {key: "no data"}}
        assert classify_job(job) == CATEGORY_EXPECTED_EMPTY

    def test_falsy_values_skipped(self):
        job = {"status": "FAILURE", "statusMessage": "", "message": "docker"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE

    def test_non_dict_report_ignored(self):
        job = {"status": "FAILURE", "report": "timeout error"}
        # non-dict report text is NOT searched -> falls to verdict error
        assert classify_job(job) == CATEGORY_VERDICT_ERROR

    def test_case_insensitive_hints(self):
        job = {"status": "FAILURE", "statusMessage": "TIMEOUT OCCURRED"}
        assert classify_job(job) == CATEGORY_INFRA_FAILURE
        job["statusMessage"] = "No Data Returned"
        assert classify_job(job) == CATEGORY_EXPECTED_EMPTY

    def test_infra_beats_empty_hint(self):
        job = {
            "status": "FAILURE",
            "statusMessage": "docker error: no data returned",
        }
        assert classify_job(job) == CATEGORY_INFRA_FAILURE


class TestSummarize:
    def test_counts_and_analyzer_buckets(self):
        jobs = [
            {"status": "SUCCESS", "workerName": "w1"},
            {"status": "FAILURE", "statusMessage": "docker", "workerName": "w1"},
            {"status": "FAILURE", "statusMessage": "weird", "analyzerName": "w2"},
            {"status": "WAITING"},
        ]
        out = summarize_jobs(jobs)
        assert out["total"] == 4
        assert out["by_category"] == {
            CATEGORY_SUCCESS: 1,
            CATEGORY_INFRA_FAILURE: 1,
            CATEGORY_VERDICT_ERROR: 1,
            CATEGORY_UNKNOWN: 1,
        }
        assert out["by_analyzer"]["w1"] == {
            CATEGORY_SUCCESS: 1,
            CATEGORY_INFRA_FAILURE: 1,
        }
        assert out["by_analyzer"]["w2"] == {CATEGORY_VERDICT_ERROR: 1}
        assert out["by_analyzer"]["unknown"] == {CATEGORY_UNKNOWN: 1}

    def test_analyzer_fallback_chain(self):
        jobs = [
            {"status": "SUCCESS", "analyzerDefinitionId": "d1"},
            {"status": "SUCCESS", "workerName": "w1"},
            {"status": "SUCCESS", "analyzerName": "a1"},
        ]
        out = summarize_jobs(jobs)
        assert set(out["by_analyzer"]) == {"d1", "w1", "a1"}
        # definition id wins over worker name when both present
        jobs2 = [
            {
                "status": "SUCCESS",
                "analyzerDefinitionId": "d1",
                "workerName": "w1",
            }
        ]
        assert "d1" in summarize_jobs(jobs2)["by_analyzer"]

    def test_flagged_only_bad_categories(self):
        jobs = [
            {
                "status": "FAILURE",
                "statusMessage": "docker dead",
                "id": "j1",
                "workerName": "w",
            },
            {
                "status": "FAILURE",
                "message": "weird",
                "_id": "j2",
                "workerName": "w",
            },
            {"status": "SUCCESS", "_id": "j3", "workerName": "w"},
            {
                "status": "FAILURE",
                "statusMessage": "no data",
                "_id": "j4",
                "workerName": "w",
            },
        ]
        out = summarize_jobs(jobs)
        ids = {f["job_id"] for f in out["flagged"]}
        assert ids == {"j1", "j2"}  # id preferred over _id; _id used as fallback
        entry = next(f for f in out["flagged"] if f["job_id"] == "j1")
        assert entry["analyzer"] == "w"
        assert entry["category"] == CATEGORY_INFRA_FAILURE
        assert entry["status"] == "FAILURE"
        assert entry["message"] == "docker dead"

    def test_message_fallback_and_truncation(self):
        jobs = [
            {
                "status": "FAILURE",
                "statusMessage": "x" * 400,
                "id": "j",
            }
        ]
        entry = summarize_jobs(jobs)["flagged"][0]
        assert len(entry["message"]) == 300
        # statusMessage missing -> falls back to message
        jobs[0].pop("statusMessage")
        jobs[0]["message"] = "m" * 400
        entry = summarize_jobs(jobs)["flagged"][0]
        assert entry["message"] == "m" * 300

    def test_empty_list(self):
        out = summarize_jobs([])
        assert out == {
            "total": 0,
            "by_category": {},
            "by_analyzer": {},
            "flagged": [],
        }
