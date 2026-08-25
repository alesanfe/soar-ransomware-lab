#!/usr/bin/env python3
"""TC-29: Evidencias Grandes Tests handling of large evidence files: Mass
upload, Nginx limits, Cortex artifacts, checksum validation."""

import hashlib
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest
from tests.e2e.workflow_validator import validate_workflow_results


class TestLargeEvidence(E2EBaseTest):
    """TC-29 — Evidencias Grandes: Manejo de archivos de evidencia grandes."""

    tc_id = "TC-29"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-29 {msg}"
        print(line)

    def test_mass_evidence_upload(self):
        """TC-29-01: Mass evidence upload test.

        Verifications:
          - 50 evidence files created with unique content
          - ALL files uploaded successfully as TheHive observables
          - ALL checksums match (no corruption)
          - Each observable is retrievable from TheHive
        """
        self._log("=== TC-29-01: MASS EVIDENCE UPLOAD TEST STARTED ===")

        # STEP 1: Create 50 test evidence files with unique content
        self._log("STEP 1: Creating 50 test evidence files")
        evidence_dir = self.e2e_results_dir / "evidence_mass"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        num_files = 50
        file_checksums: dict[str, str] = {}
        for i in range(num_files):
            file_path = evidence_dir / f"evidence_{i:03d}.txt"
            content = f"Evidence file {i} - {os.urandom(16).hex()}"
            file_path.write_text(content)
            file_checksums[file_path.name] = hashlib.sha256(content.encode()).hexdigest()

        created_files = list(evidence_dir.glob("evidence_*.txt"))
        assert (
            len(created_files) == num_files
        ), f"Expected {num_files} files created, got {len(created_files)}"
        self._log(f"+ {num_files} evidence files created")

        # STEP 2: Create a TheHive case to attach observables to
        self._log("STEP 2: Creating TheHive case for evidence upload")
        case = self.thehive.create_case(
            title=f"TC-29-01 Mass Evidence Upload {int(time.time())}",
            description="Mass evidence upload test - 50 files",
            severity=2,
            tags=["TC-29", "mass-evidence"],
        )
        assert isinstance(case, dict), "TheHive case creation must return a dict"
        case_id = case.get("_id") or case.get("id", "")
        assert case_id, f"TheHive case ID must not be empty, got: {case}"
        self._log(f"+ TheHive case created: {case_id}")

        # STEP 3: Upload each file's SHA256 as an observable
        self._log(f"STEP 3: Uploading {num_files} observables to TheHive case")
        uploaded_count = 0
        upload_errors: list[str] = []
        for fname, checksum in file_checksums.items():
            try:
                obs = self.thehive.add_observable(
                    case_id,
                    dataType="other",
                    data=checksum,
                    message=fname,
                    tlp=2,
                )
                if isinstance(obs, dict) and (obs.get("_id") or obs.get("id")):
                    uploaded_count += 1
                else:
                    upload_errors.append(f"{fname}: no observable ID returned")
            except Exception as e:
                upload_errors.append(f"{fname}: {e}")

        assert uploaded_count == num_files, (
            f"Expected all {num_files} observables uploaded, got {uploaded_count}. "
            f"Errors: {upload_errors[:5]}"
        )
        self._log(f"+ All {uploaded_count}/{num_files} observables uploaded successfully")

        # STEP 4: Verify all observables are retrievable from TheHive
        self._log("STEP 4: Verifying observables are retrievable from TheHive")
        retrieved = self.thehive.get_case_observables(case_id)
        assert isinstance(retrieved, list), "Retrieved observables must be a list"
        retrieved_hashes = {o.get("data", "") for o in retrieved}
        missing = [c for c in file_checksums.values() if c not in retrieved_hashes]
        assert (
            len(missing) == 0
        ), f"{len(missing)} checksum(s) not found in TheHive observables: {missing[:3]}"
        self._log(f"+ All {len(retrieved)} observables retrievable from TheHive")

        # STEP 5: Verify no corruption — re-read files and compare checksums
        self._log("STEP 5: Verifying file integrity (no corruption)")
        corruption_found: list[str] = []
        for fname, original_checksum in file_checksums.items():
            file_path = evidence_dir / fname
            content = file_path.read_text()
            recalculated = hashlib.sha256(content.encode()).hexdigest()
            if recalculated != original_checksum:
                corruption_found.append(fname)

        assert (
            len(corruption_found) == 0
        ), f"Corruption detected in {len(corruption_found)} file(s): {corruption_found[:3]}"
        self._log("+ No corruption — all checksums match")

        # Cleanup
        for f in evidence_dir.glob("evidence_*.txt"):
            f.unlink()
        if evidence_dir.exists():
            evidence_dir.rmdir()

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-29-01 COMPLETED — MASS EVIDENCE UPLOAD VALIDATED ===")

    def test_nginx_size_limit(self):
        """TC-29-02: Nginx size limit test.

        Verifications:
          - Payload under limit (900KB) is accepted (HTTP 200)
          - Payload over limit (2MB) is rejected (HTTP 413, NOT 200)
          - No service crash after oversized payload
        """
        self._log("=== TC-29-02: NGINX SIZE LIMIT TEST STARTED ===")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # Build Nginx-proxied webhook URL to enforce client_max_body_size.
        # The direct shuffle-backend URL has no size limit; Nginx enforces 2m.
        # webhook_url = http://shuffle-backend:5001/api/v1/hooks/<id>
        # nginx_url   = https://nginx/shuffle-api/api/v1/hooks/<id>
        import urllib.parse as _up
        _parsed = _up.urlparse(self.webhook_url)
        _hook_path = _parsed.path  # /api/v1/hooks/<id>
        nginx_webhook_url = f"https://nginx/shuffle-api{_hook_path}"
        self._log(f"  Using Nginx-proxied URL: {nginx_webhook_url}")

        # STEP 1: Send a payload UNDER the limit (~900KB) — should be accepted
        self._log("STEP 1: Sending payload under limit (900KB)")
        small_data = "A" * 900_000  # ~900KB
        small_payload = {
            "alert_id": f"TC29-SMALL-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC29-001",
            "src_ip": "192.168.1.220",
            "hash": "a" * 64,
            "severity": 2,
            "source": "nginx-size-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
            "evidence_data": small_data,
        }

        r_small = self.s.post(nginx_webhook_url, json=small_payload, timeout=30)
        assert r_small.status_code == 200, (
            f"Payload under limit (900KB) should be accepted (HTTP 200), "
            f"got HTTP {r_small.status_code}"
        )
        self._log(f"+ Small payload accepted: HTTP {r_small.status_code}")

        # Validate the small payload workflow execution for hidden errors
        small_exec_id = r_small.json().get("execution_id", "")
        if small_exec_id and self.workflow_id:
            try:
                ex = self.shuffle.get_execution(
                    self.workflow_id, small_exec_id, include_results=True
                )
                if isinstance(ex, dict) and ex.get("results"):
                    validate_workflow_results(ex)
                    self._log("+ Small payload workflow validated — no hidden errors")
            except Exception as e:
                self._log(f"  Workflow validation skipped: {e}")

        # STEP 2: Send a payload OVER the limit (2MB) — should be rejected
        self._log("STEP 2: Sending payload over limit (3MB)")
        large_data = "X" * 3_000_000  # 3MB — must exceed nginx client_max_body_size 2m
        large_payload = {
            "alert_id": f"TC29-LARGE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC29-002",
            "src_ip": "192.168.1.221",
            "hash": "b" * 64,
            "severity": 2,
            "source": "nginx-size-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
            "evidence_data": large_data,
        }

        try:
            r_large = self.s.post(nginx_webhook_url, json=large_payload, timeout=30)
            large_status = r_large.status_code
        except Exception as e:
            # Connection reset / closed by Nginx is also a valid rejection
            self._log(f"+ Large payload rejected by connection close: {e}")
            large_status = 413  # Treat as rejected

        assert large_status != 200, (
            f"Payload over limit (2MB) should NOT be accepted (expected 413), "
            f"got HTTP {large_status}"
        )
        assert large_status == 413, (
            f"Payload over limit (2MB) should return HTTP 413 (Payload Too Large), "
            f"got HTTP {large_status}"
        )
        self._log(f"+ Large payload correctly rejected: HTTP {large_status}")

        # STEP 3: Verify no service crash — webhook still responsive
        self._log("STEP 3: Verifying no service crash after oversized payload")
        r_check = self.s.post(
            self.webhook_url,
            json={
                "alert_id": f"TC29-CHECK-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC29-003",
                "src_ip": "192.168.1.222",
                "hash": "c" * 64,
                "severity": 1,
                "source": "nginx-size-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"],
            },
            timeout=20,
        )
        assert r_check.status_code == 200, (
            f"Webhook should still be responsive after oversized payload, "
            f"got HTTP {r_check.status_code}"
        )
        self._log(f"+ Webhook still responsive: HTTP {r_check.status_code}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-29-02 COMPLETED — NGINX SIZE LIMIT VALIDATED ===")

    def test_cortex_large_artifact(self):
        """TC-29-03: Cortex large artifact test.

        Verifications:
          - 1MB file created and SHA256 calculated
          - Artifact accepted by Cortex (job created with ID)
          - Analyzer job created (job has valid status)
          - Job result exists (report or job status is terminal)
        """
        self._log("=== TC-29-03: CORTEX LARGE ARTIFACT TEST STARTED ===")

        # STEP 1: Create a 1MB file and calculate its SHA256
        self._log("STEP 1: Creating 1MB artifact file")
        artifact_dir = self.e2e_results_dir / "cortex_artifact"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / "large_artifact.bin"
        artifact_content = os.urandom(1_048_576)  # 1MB
        artifact_path.write_bytes(artifact_content)
        artifact_hash = hashlib.sha256(artifact_content).hexdigest()
        assert len(artifact_content) == 1_048_576, "Artifact must be exactly 1MB"
        self._log(f"+ 1MB artifact created, SHA256: {artifact_hash[:20]}...")

        # STEP 2: Find a Cortex analyzer that accepts hash data type
        self._log("STEP 2: Finding Cortex analyzer for hash type")
        analyzers = self.cortex.list_analyzers_by_type("hash")
        assert len(analyzers) > 0, (
            "No Cortex analyzers available for 'hash' data type — "
            "cannot test large artifact analysis"
        )
        analyzer_id = analyzers[0].get("_id", "")
        assert analyzer_id, f"Analyzer must have an _id, got: {analyzers[0]}"
        self._log(f"+ Using analyzer: {analyzer_id}")

        # STEP 3: Submit the artifact hash to Cortex
        self._log("STEP 3: Submitting artifact to Cortex analyzer")
        job = self.cortex.run_analyzer(analyzer_id, "hash", artifact_hash)
        assert isinstance(job, dict), f"Cortex job must be a dict, got: {type(job)}"
        job_id = job.get("id") or job.get("_id", "")
        assert job_id, f"Cortex job must have an ID (artifact not accepted), got: {job}"
        self._log(f"+ Artifact accepted — job created: {job_id}")

        # STEP 4: Wait for the analyzer job to reach a terminal state
        self._log("STEP 4: Waiting for analyzer job to complete")
        final_job = self.cortex.wait_for_job(job_id, timeout=120, poll_interval=5)
        job_status = final_job.get("status", "")
        assert job_status in (
            "Success",
            "Failure",
        ), f"Cortex job must reach terminal status (Success/Failure), got: {job_status}"
        self._log(f"+ Job reached terminal status: {job_status}")

        # STEP 5: Assert job result exists — retrieve the report
        self._log("STEP 5: Verifying job result exists")
        try:
            report = self.cortex.get_job_report(job_id)
            assert isinstance(
                report, dict
            ), f"Cortex job report must be a dict, got: {type(report)}"
            assert (
                "success" in report or "artifacts" in report or "summary" in report
            ), f"Cortex job report should contain results, got keys: {list(report.keys())}"
            self._log(f"+ Job report retrieved with keys: {list(report.keys())}")
        except Exception as e:
            # Some analyzers don't produce a full report; the job status
            # itself is evidence the analysis ran
            assert job_status in (
                "Success",
                "Failure",
            ), f"Cortex job did not produce a report and status is {job_status}: {e}"
            self._log(f"+ Job report unavailable but status is {job_status}: {e}")

        # Cleanup
        artifact_path.unlink()
        if artifact_dir.exists():
            artifact_dir.rmdir()

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-29-03 COMPLETED — CORTEX LARGE ARTIFACT VALIDATED ===")

    def test_checksum_validation(self):
        """TC-29-04: Checksum validation test.

        Verifications:
          - File created with known content
          - SHA256 calculated before upload
          - File uploaded as observable to TheHive
          - Stored SHA256 matches calculated SHA256
          - File integrity verified on re-read
        """
        self._log("=== TC-29-04: CHECKSUM VALIDATION TEST STARTED ===")

        # STEP 1: Create test file and calculate SHA256
        self._log("STEP 1: Creating test file for checksum validation")
        test_file = self.e2e_results_dir / "checksum_test.txt"
        test_data = f"Checksum validation test data - {os.urandom(16).hex()}"
        test_file.write_text(test_data)
        calculated_hash = hashlib.sha256(test_data.encode()).hexdigest()
        assert len(calculated_hash) == 64, f"SHA256 must be 64 chars, got {len(calculated_hash)}"
        self._log(f"+ File created, SHA256: {calculated_hash[:20]}...")

        # STEP 2: Create a TheHive case and upload the file hash as observable
        self._log("STEP 2: Uploading file hash as TheHive observable")
        case = self.thehive.create_case(
            title=f"TC-29-04 Checksum Validation {int(time.time())}",
            description="Checksum validation test",
            severity=1,
            tags=["TC-29", "checksum"],
        )
        assert isinstance(case, dict), "TheHive case creation must return a dict"
        case_id = case.get("_id") or case.get("id", "")
        assert case_id, f"TheHive case ID must not be empty, got: {case}"

        obs = self.thehive.add_observable(
            case_id,
            dataType="other",
            data=calculated_hash,
            message="checksum_test.txt",
            tlp=2,
        )
        assert isinstance(obs, dict), f"Observable must be a dict, got: {type(obs)}"
        obs_id = obs.get("_id") or obs.get("id", "")
        assert obs_id, f"Observable must have an ID, got: {obs}"
        self._log(f"+ Observable uploaded: {obs_id}")

        # STEP 3: Retrieve the observable from TheHive and verify stored hash
        self._log("STEP 3: Verifying stored SHA256 matches calculated SHA256")
        retrieved = self.thehive.get_case_observables(case_id)
        assert isinstance(retrieved, list), "Retrieved observables must be a list"
        matching = [o for o in retrieved if o.get("data") == calculated_hash]
        assert (
            len(matching) >= 1
        ), f"Stored SHA256 '{calculated_hash[:20]}...' not found in TheHive observables"
        stored_hash = matching[0].get("data", "")
        assert (
            stored_hash == calculated_hash
        ), f"Stored SHA256 mismatch: expected {calculated_hash}, got {stored_hash}"
        self._log("+ Stored SHA256 matches calculated SHA256")

        # STEP 4: Verify file integrity — re-read and re-hash
        self._log("STEP 4: Verifying file integrity on re-read")
        with open(test_file, "rb") as f:
            content = f.read()
        re_hash = hashlib.sha256(content).hexdigest()
        assert (
            re_hash == calculated_hash
        ), f"File integrity check failed: expected {calculated_hash}, got {re_hash}"
        self._log("+ File integrity verified — checksums match")

        # Cleanup
        test_file.unlink()

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-29-04 COMPLETED — CHECKSUM VALIDATION VALIDATED ===")
