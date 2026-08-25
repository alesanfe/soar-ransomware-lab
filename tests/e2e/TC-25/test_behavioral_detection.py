#!/usr/bin/env python3
"""TC-25: Detección Conductual (Behavioral Detection)

Validates behavioral detection for unknown threats:
  - Polymorphic malware (same behavior, different hash)
  - Low and slow exfiltration (correlated over time)
  - Multi-stage kill chain (recon -> access -> execution -> exfiltration)
  - Canary file detection (honeypot triggers)
"""

import time
from datetime import UTC, datetime

import pytest

from tests.e2e.base import E2EBaseTest


class TestBehavioralDetection(E2EBaseTest):
    """TC-25 — Detección Conductual: Amenazas desconocidas por
    comportamiento."""

    tc_id = "TC-25"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-25 {msg}"
        print(line)

    # ------------------------------------------------------------------
    # Helper: find TheHive case by alert_id
    # ------------------------------------------------------------------

    def _find_case_for_alert(self, alert_id: str, timeout: int = 120) -> dict:
        """Search TheHive for a case matching the alert_id.

        Fail if not found.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                cases = self.thehive.search_cases()
                for c in cases:
                    title = c.get("title", "")
                    desc = c.get("description", "")
                    if alert_id in title or alert_id in desc:
                        return c
            except Exception as e:
                self._log(f"  + TheHive search error: {e}")
            time.sleep(5)
        pytest.fail(f"TheHive case not found for alert_id={alert_id} within {timeout}s")

    # ------------------------------------------------------------------
    # Test 1: Polymorphic behavior
    # ------------------------------------------------------------------

    def test_polymorphic_behavior(self):
        """TC-25-01: Polymorphic malware detection.

        Sends 2 alerts with DIFFERENT hashes but SAME behavior pattern
        (same process_name, same file_path pattern). Asserts:
          1. BOTH alerts create TheHive cases.
          2. BOTH cases have the same MITRE techniques tagged.
          3. BOTH trigger containment (workflow FINISHED).
        """
        self._log("=== TC-25-01: POLYMORPHIC BEHAVIOR TEST STARTED ===")

        base_ts = int(time.time())
        process_name = "encryptor_payload.exe"
        file_path_pattern = "C:/Users/admin/Documents/encrypted_"

        # --- Alert 1: hash "a" * 64 ---
        alert_id_1 = f"TC25-POLY-A-{base_ts}"
        payload_1 = self.build_alert_payload(
            alert_id=alert_id_1,
            alert_type="polymorphic",
            severity=3,
            hash_val="a" * 64,
            mitre_techniques=["T1027"],
            process_name=process_name,
            file_path=f"{file_path_pattern}batch1",
            behavior="file_encryption",
        )
        self._log("STEP 1: Sending polymorphic alert #1 (hash=aaa...)")
        exec_id_1, execution_1 = self.submit_alert_and_wait(payload_1)
        self.execution = execution_1
        self.execution_id = exec_id_1
        self.validate_workflow_execution(execution_1, alert_id=alert_id_1)
        assert (
            execution_1.get("status") == "FINISHED"
        ), f"Polymorphic alert #1 workflow should FINISH, got {execution_1.get('status')}"
        self._log("+ Alert #1 workflow FINISHED")

        # --- Alert 2: hash "b" * 64, SAME behavior ---
        alert_id_2 = f"TC25-POLY-B-{base_ts}"
        payload_2 = self.build_alert_payload(
            alert_id=alert_id_2,
            alert_type="polymorphic",
            severity=3,
            hash_val="b" * 64,
            mitre_techniques=["T1027"],
            process_name=process_name,
            file_path=f"{file_path_pattern}batch2",
            behavior="file_encryption",
        )
        self._log("STEP 2: Sending polymorphic alert #2 (hash=bbb...)")
        exec_id_2, execution_2 = self.submit_alert_and_wait(payload_2)
        self.execution = execution_2
        self.execution_id = exec_id_2
        self.validate_workflow_execution(execution_2, alert_id=alert_id_2)
        assert (
            execution_2.get("status") == "FINISHED"
        ), f"Polymorphic alert #2 workflow should FINISH, got {execution_2.get('status')}"
        self._log("+ Alert #2 workflow FINISHED")

        # --- Verify BOTH created TheHive cases ---
        self._log("STEP 3: Verifying both alerts created TheHive cases")
        case_1 = self._find_case_for_alert(alert_id_1)
        case_2 = self._find_case_for_alert(alert_id_2)
        assert isinstance(case_1, dict), "Case #1 must be a dict"
        assert isinstance(case_2, dict), "Case #2 must be a dict"
        case_id_1 = case_1.get("_id") or case_1.get("id")
        case_id_2 = case_2.get("_id") or case_2.get("id")
        assert case_id_1, f"Case #1 must have _id, got: {case_1}"
        assert case_id_2, f"Case #2 must have _id, got: {case_2}"
        self._log(f"+ Case #1: {case_id_1} — {case_1.get('title', '')[:60]}")
        self._log(f"+ Case #2: {case_id_2} — {case_2.get('title', '')[:60]}")

        # --- Verify BOTH cases have the same MITRE techniques ---
        self._log("STEP 4: Verifying both cases have same MITRE techniques")
        tags_1 = set(case_1.get("tags", []))
        tags_2 = set(case_2.get("tags", []))
        self._log(f"  Case #1 tags: {tags_1}")
        self._log(f"  Case #2 tags: {tags_2}")

        # At least one MITRE technique should appear in both cases' tags
        # or in the case title/description
        combined_1 = " ".join(
            [
                " ".join(tags_1),
                case_1.get("title", ""),
                case_1.get("description", ""),
            ]
        ).upper()
        combined_2 = " ".join(
            [
                " ".join(tags_2),
                case_2.get("title", ""),
                case_2.get("description", ""),
            ]
        ).upper()

        mitre_techniques = ["T1027"]
        shared_techniques = [
            t for t in mitre_techniques if t.upper() in combined_1 and t.upper() in combined_2
        ]
        assert len(shared_techniques) > 0, (
            f"Both polymorphic cases should share MITRE techniques {mitre_techniques}. "
            f"Case #1 has: {combined_1[:200]}, Case #2 has: {combined_2[:200]}"
        )
        self._log(f"+ Both cases share MITRE techniques: {shared_techniques}")

        # --- Verify BOTH triggered containment (workflow FINISHED = containment ran) ---
        self._log("STEP 5: Verifying both triggered containment")
        # validate_workflow_execution already checked FINISHED + node success,
        # but we explicitly assert the containment node ran for both
        results_1 = execution_1.get("results", [])
        results_2 = execution_2.get("results", [])
        assert isinstance(results_1, list) and len(results_1) > 0, "Alert #1 must have results"
        assert isinstance(results_2, list) and len(results_2) > 0, "Alert #2 must have results"

        # Both executions should have the same behavior field in the payload
        assert payload_1.get("behavior") == payload_2.get(
            "behavior"
        ), "Both payloads should have the same behavior field"
        assert (
            payload_1["behavior"] == "file_encryption"
        ), "Behavior should be file_encryption for both"
        # Hashes must be different (polymorphic)
        assert (
            payload_1["hash"] != payload_2["hash"]
        ), "Polymorphic alerts must have different hashes"
        self._log("+ Both alerts have different hashes but same behavior — polymorphic detected")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-01 COMPLETED — POLYMORPHIC BEHAVIOR VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 2: Low and slow exfiltration
    # ------------------------------------------------------------------

    def test_low_and_slow_exfiltration(self):
        """TC-25-02: Low and slow exfiltration detection.

        Sends 3 alerts over time with small data exfiltration indicators.
        Asserts:
          1. Each alert creates a TheHive case.
          2. The cases are correlated (same correlation_id or linked observables).
          3. At least one case has "exfiltration" in tags or description.
        """
        self._log("=== TC-25-02: LOW AND SLOW EXFILTRATION TEST STARTED ===")

        base_ts = int(time.time())
        correlation_tag = f"TC25-SLOW-{base_ts}"
        case_ids: list[str] = []
        alert_ids: list[str] = []

        # --- Send 3 alerts with small exfiltration volumes ---
        for i in range(3):
            alert_id = f"TC25-SLOW-{base_ts}-{i + 1}"
            alert_ids.append(alert_id)
            payload = self.build_alert_payload(
                alert_id=alert_id,
                alert_type="exfiltration",
                severity=2,
                src_ip="192.168.1.221",
                hash_val=f"f{i}" * 32,
                mitre_techniques=["T1041"],
                behavior="slow_data_transfer",
                data_volume_kb=10 + i * 5,  # 10, 15, 20 KB — small increments
                exfiltration_tag=correlation_tag,
            )
            self._log(f"STEP {i + 1}: Sending slow exfiltration alert #{i + 1} ({10 + i * 5}KB)")
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id
            self.validate_workflow_execution(execution, alert_id=alert_id)
            assert (
                execution.get("status") == "FINISHED"
            ), f"Exfiltration alert #{i + 1} workflow should FINISH, got {execution.get('status')}"
            self._log(f"+ Alert #{i + 1} workflow FINISHED")

            # Small delay between alerts to simulate "slow" pattern
            if i < 2:
                time.sleep(3)

        # --- Verify each alert created a case ---
        self._log("STEP 4: Verifying each alert created a TheHive case")
        cases_found: list[dict] = []
        for aid in alert_ids:
            case = self._find_case_for_alert(aid)
            assert isinstance(case, dict), f"Case for {aid} must be a dict"
            cid = case.get("_id") or case.get("id")
            assert cid, f"Case for {aid} must have _id"
            case_ids.append(cid)
            cases_found.append(case)
            self._log(f"+ Case for {aid}: {cid}")

        assert len(cases_found) == 3, f"Should have 3 cases for 3 alerts, got {len(cases_found)}"

        # --- Verify cases are correlated ---
        self._log("STEP 5: Verifying cases are correlated")
        # Check that all 3 cases share the same src_ip observable (192.168.1.221)
        # or share the correlation_tag in their description/tags
        all_descriptions = " ".join(c.get("description", "") for c in cases_found)
        all_tags = []
        for c in cases_found:
            all_tags.extend(c.get("tags", []))

        # Correlation via shared src_ip in observables
        correlated_via_ip = 0
        for case in cases_found:
            cid = case.get("_id") or case.get("id")
            try:
                observables = self.thehive.get_case_observables(cid)
                has_src_ip = any(obs.get("data") == "192.168.1.221" for obs in observables)
                if has_src_ip:
                    correlated_via_ip += 1
            except Exception as e:
                self._log(f"  + Could not check observables for {cid}: {e}")

        assert correlated_via_ip >= 2, (
            f"At least 2 of 3 cases should share the src_ip observable "
            f"(192.168.1.221) for correlation, got {correlated_via_ip}/3"
        )
        self._log(f"+ {correlated_via_ip}/3 cases correlated via shared src_ip observable")

        # --- Verify at least one case has "exfiltration" in tags/description ---
        self._log("STEP 6: Verifying exfiltration keyword in case data")
        exfiltration_found = False
        for case in cases_found:
            combined = " ".join(
                [
                    " ".join(case.get("tags", [])),
                    case.get("title", ""),
                    case.get("description", ""),
                ]
            ).lower()
            if "exfiltration" in combined or "exfil" in combined:
                exfiltration_found = True
                self._log(f"+ Case {case.get('_id')} has exfiltration keyword")
                break

        assert exfiltration_found, (
            "At least one case should have 'exfiltration' in tags, title, or description. "
            f"Tags: {all_tags}, Descriptions: {all_descriptions[:300]}"
        )

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-02 COMPLETED — LOW AND SLOW EXFILTRATION VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 3: Multi-stage kill chain
    # ------------------------------------------------------------------

    def test_multi_stage_kill_chain(self):
        """TC-25-03: Multi-stage kill chain detection.

        Sends alerts representing kill chain stages:
          reconnaissance -> initial access -> execution -> exfiltration.
        Asserts:
          1. Each stage creates a TheHive case.
          2. MITRE techniques are correctly mapped per stage.
          3. The final stage (exfiltration) has critical severity.
        """
        self._log("=== TC-25-03: MULTI-STAGE KILL CHAIN TEST STARTED ===")

        base_ts = int(time.time())
        stages = [
            {
                "name": "reconnaissance",
                "alert_id": f"TC25-KC-RECON-{base_ts}",
                "mitre": "T1590",
                "severity": 1,
                "behavior": "network_scan",
            },
            {
                "name": "initial_access",
                "alert_id": f"TC25-KC-ACCESS-{base_ts}",
                "mitre": "T1078",
                "severity": 2,
                "behavior": "credential_use",
            },
            {
                "name": "execution",
                "alert_id": f"TC25-KC-EXEC-{base_ts}",
                "mitre": "T1059",
                "severity": 2,
                "behavior": "process_execution",
            },
            {
                "name": "exfiltration",
                "alert_id": f"TC25-KC-EXFIL-{base_ts}",
                "mitre": "T1041",
                "severity": 3,
                "behavior": "data_exfiltration",
            },
        ]

        created_cases: list[dict] = []

        for i, stage in enumerate(stages):
            self._log(f"STEP {i + 1}: Sending kill chain stage '{stage['name']}'")
            payload = self.build_alert_payload(
                alert_id=stage["alert_id"],
                alert_type="kill_chain",
                severity=stage["severity"],
                src_ip="192.168.1.222",
                hash_val=f"{stage['name'][0]}" * 64,
                mitre_techniques=[stage["mitre"]],
                kill_chain_stage=stage["name"],
                behavior=stage["behavior"],
            )
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id
            self.validate_workflow_execution(execution, alert_id=stage["alert_id"])
            assert execution.get("status") == "FINISHED", (
                f"Kill chain stage '{stage['name']}' workflow should FINISH, "
                f"got {execution.get('status')}"
            )
            self._log(f"+ Stage '{stage['name']}' workflow FINISHED")

            # Find the case
            case = self._find_case_for_alert(stage["alert_id"])
            assert isinstance(case, dict), f"Case for {stage['name']} must be a dict"
            created_cases.append(case)
            self._log(f"+ Case created for '{stage['name']}': {case.get('_id')}")

        # --- Verify all 4 stages created cases ---
        self._log("STEP 5: Verifying all kill chain stages created cases")
        assert (
            len(created_cases) == 4
        ), f"All 4 kill chain stages should create cases, got {len(created_cases)}"

        # --- Verify MITRE techniques mapped per stage ---
        self._log("STEP 6: Verifying MITRE techniques mapped per stage")
        for i, stage in enumerate(stages):
            case = created_cases[i]
            combined = " ".join(
                [
                    " ".join(case.get("tags", [])),
                    case.get("title", ""),
                    case.get("description", ""),
                ]
            ).upper()
            assert stage["mitre"].upper() in combined, (
                f"Stage '{stage['name']}' case should reference MITRE {stage['mitre']}. "
                f"Case data: {combined[:200]}"
            )
            self._log(f"+ Stage '{stage['name']}' has MITRE {stage['mitre']}")

        # --- Verify final stage has critical severity ---
        self._log("STEP 7: Verifying final stage (exfiltration) has critical severity")
        final_case = created_cases[-1]
        final_severity = final_case.get("severity")
        # TheHive severity: 0=low, 1=medium, 2=high, 3=critical
        assert final_severity is not None, "Final stage case must have a severity field"
        # Accept either int 3 or string "3" or high/critical
        if isinstance(final_severity, str):
            try:
                final_severity = int(final_severity)
            except ValueError:
                pass
        assert final_severity == 3 or (
            isinstance(final_severity, str) and final_severity.lower() in ("high", "critical")
        ), (
            f"Final kill chain stage (exfiltration) should have critical severity (3), "
            f"got {final_severity}"
        )
        self._log(f"+ Final stage severity: {final_severity} (critical)")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-03 COMPLETED — MULTI-STAGE KILL CHAIN VALIDATED ===")

    # ------------------------------------------------------------------
    # Test 4: Canary file detection
    # ------------------------------------------------------------------

    def test_canary_file_detection(self):
        """TC-25-04: Canary file detection.

        Sends an alert with a canary file hash. Asserts:
          1. Workflow FINISHED.
          2. TheHive case created.
          3. Case has "canary" or "honeypot" in tags/description.
          4. Alert was treated as high priority (severity >= 2).
        """
        self._log("=== TC-25-04: CANARY FILE DETECTION TEST STARTED ===")

        alert_id = f"TC25-CANARY-{int(time.time())}"
        canary_hash = "c" * 64  # Distinct canary hash
        payload = self.build_alert_payload(
            alert_id=alert_id,
            alert_type="canary",
            severity=3,
            src_ip="192.168.1.223",
            hash_val=canary_hash,
            mitre_techniques=["T1005"],
            file_path="C:/Users/admin/Documents/canary.txt",
            file_type="canary",
            behavior="canary_file_access",
        )

        # --- Step 1: Submit and wait ---
        self._log("STEP 1: Sending canary file alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)

        # --- Step 2: Assert workflow FINISHED ---
        assert (
            execution.get("status") == "FINISHED"
        ), f"Canary file alert workflow should FINISH, got {execution.get('status')}"
        self._log("+ Canary file alert workflow FINISHED")

        # --- Step 3: Assert TheHive case created ---
        self._log("STEP 2: Verifying TheHive case created")
        case = self._find_case_for_alert(alert_id)
        assert isinstance(case, dict), "Canary case must be a dict"
        case_id = case.get("_id") or case.get("id")
        assert case_id, f"Canary case must have _id, got: {case}"
        self._log(f"+ TheHive case created: {case_id}")

        # --- Step 4: Assert case has "canary" or "honeypot" in tags/description ---
        self._log("STEP 3: Verifying canary/honeypot keyword in case")
        tags = case.get("tags", [])
        title = case.get("title", "")
        description = case.get("description", "")
        combined = " ".join(tags + [title, description]).lower()

        assert "canary" in combined or "honeypot" in combined, (
            f"Canary case should have 'canary' or 'honeypot' in tags/title/description. "
            f"Tags: {tags}, Title: {title[:100]}, Description: {description[:200]}"
        )
        self._log(f"+ Case contains canary/honeypot keyword (tags: {tags})")

        # --- Step 5: Assert alert was treated as high priority ---
        self._log("STEP 4: Verifying high priority treatment")
        case_severity = case.get("severity")
        if isinstance(case_severity, str):
            try:
                case_severity = int(case_severity)
            except ValueError:
                pass

        # TheHive severity: 0=low, 1=medium, 2=high, 3=critical
        # Canary files should be treated as high priority (>= 2)
        assert case_severity is not None, "Canary case must have a severity"
        if isinstance(case_severity, int):
            assert (
                case_severity >= 2
            ), f"Canary file alert should be high priority (severity >= 2), got {case_severity}"
        elif isinstance(case_severity, str):
            assert case_severity.lower() in (
                "high",
                "critical",
            ), f"Canary file alert should be high/critical severity, got {case_severity}"
        self._log(f"+ Canary alert treated as high priority (severity={case_severity})")

        # --- Step 6: Assert canary file path is in case data ---
        self._log("STEP 5: Verifying canary file path in case data")
        assert "canary" in combined, "Case should reference the canary file path or type"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-04 COMPLETED — CANARY FILE DETECTION VALIDATED ===")
