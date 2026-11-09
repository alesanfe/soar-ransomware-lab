"""Unit tests for cortex_job_classifier (CTX-001)."""

from soar_lab.domain.services.cortex_job_classifier import (
    CATEGORY_EXPECTED_EMPTY,
    CATEGORY_INFRA_FAILURE,
    CATEGORY_SUCCESS,
    CATEGORY_VERDICT_ERROR,
    classify_job,
    summarize_jobs,
)


def test_success_status():
    assert classify_job({"status": "Success"}) == CATEGORY_SUCCESS


def test_infra_timeout():
    job = {"status": "Failure", "statusMessage": "Timeout waiting for container"}
    assert classify_job(job) == CATEGORY_INFRA_FAILURE


def test_infra_docker():
    job = {"status": "Failed", "message": "Docker image pull access denied"}
    assert classify_job(job) == CATEGORY_INFRA_FAILURE


def test_expected_no_data():
    job = {"status": "Failure", "statusMessage": "No data returned for observable"}
    assert classify_job(job) == CATEGORY_EXPECTED_EMPTY


def test_expected_not_found_in_report():
    job = {
        "status": "Failure",
        "report": {"errorMessage": "NXDOMAIN: name does not exist"},
    }
    assert classify_job(job) == CATEGORY_EXPECTED_EMPTY


def test_verdict_error_default_failure():
    job = {"status": "Failure", "statusMessage": "analyzer exited with code 1"}
    assert classify_job(job) == CATEGORY_VERDICT_ERROR


def test_inprogress_unknown():
    assert classify_job({"status": "InProgress"}) == "unknown"


def test_summarize_jobs_aggregates():
    jobs = [
        {"status": "Success", "workerName": "A"},
        {"status": "Failure", "statusMessage": "timeout", "workerName": "B"},
        {"status": "Failure", "statusMessage": "no data", "workerName": "B"},
        {"status": "Failure", "statusMessage": "crash", "workerName": "C"},
    ]
    s = summarize_jobs(jobs)
    assert s["total"] == 4
    assert s["by_category"][CATEGORY_SUCCESS] == 1
    assert s["by_category"][CATEGORY_INFRA_FAILURE] == 1
    assert s["by_category"][CATEGORY_EXPECTED_EMPTY] == 1
    assert s["by_category"][CATEGORY_VERDICT_ERROR] == 1
    assert s["by_analyzer"]["B"][CATEGORY_INFRA_FAILURE] == 1
    # two non-benign failures flagged (infra + analyzer_error)
    assert len(s["flagged"]) == 2
    assert {f["category"] for f in s["flagged"]} == {
        CATEGORY_INFRA_FAILURE,
        CATEGORY_VERDICT_ERROR,
    }
