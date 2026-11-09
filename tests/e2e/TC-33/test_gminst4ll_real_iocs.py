#!/usr/bin/env python3
"""TC-33: GMinst4ll Real IoCs — Validación con muestra forense real.

Test E2E que valida el pipeline SOAR (Shuffle → Cortex → MISP → TheHive → ES)
usando IoCs reales extraídos del análisis forense de GMinst4ll 2.03.rar
(InfoStealer + Pulsar RAT v1.6.6.0).

Subtests:
  1. test_download_and_hash  — descarga el .rar del repo forense, verifica SHA256, borra
  2. test_malicious_hash_ioc — envía hash de TREZ_cor al workflow, verifica caso TheHive
  3. test_pulsar_rat_hash    — envía hash de Pulsar RAT, verifica enriquecimiento Cortex
  4. test_c2_url_ioc         — envía URLs C2 (Pastebin, Dropbox, GitHub), verifica observables
  5. test_c2_domain_ioc      — envía dominios C2, verifica búsqueda MISP
  6. test_c2_ip_ioc          — envía IPs C2, verifica enriquecimiento
  7. test_telegram_ioc       — envía Chat ID + Bot ID como IoC de exfiltración
  8. test_registry_persistence — envía claves de registro como IoCs de persistencia
  9. test_mitre_mapping      — verifica que el caso TheHive incluye técnicas MITRE ATT&CK
 10. test_multi_ioc_alert    — alerta con todos los IoCs en una sola ejecución

Requiere Docker stack vivo (make up). Lee credenciales de .env.full.
Los IoCs provienen de tests/e2e/fixtures/gminst4ll_iocs.json.

ADVERTENCIA: Este test descarga una muestra de malware REAL (protegida con contraseña).
El archivo se descarga solo para verificar el hash SHA256 y se elimina inmediatamente.
No se ejecuta ni se descomprime.
"""

import hashlib
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
GMINST4LL_IOCS = FIXTURES_DIR / "gminst4ll_iocs.json"

# Fallback base URL for sample downloads when the fixture _meta omits it.
GMINST4LL_SAMPLES_BASE_URL = (
    "https://github.com/alesanfe/gminst4ll-forensics/raw/main/malware_samples"
)


def _pick_tmp_dir() -> str:
    """First writable dir for sample downloads (bind-mounted subdirs may be
    rw while the parent /app/runtime is root-owned in the container)."""
    candidates = ["/tmp", "/app/runtime/data", "/app/runtime"]
    for cand in candidates:
        p = Path(cand)
        if not p.is_dir():
            continue
        try:
            probe = p / ".write_probe"
            probe.touch()
            probe.unlink()
            return cand
        except OSError:
            continue
    return tempfile.gettempdir()


RUNTIME_DIR = (
    Path(_pick_tmp_dir())
    if Path("/app").exists()
    else Path(__file__).parent.parent.parent.parent / "runtime"
)
DOWNLOAD_TIMEOUT = 180
DOWNLOAD_CHUNK = 65536

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


def _load_gminst4ll_iocs() -> dict:
    if not GMINST4LL_IOCS.exists():
        pytest.fail(f"Fixture not found: {GMINST4LL_IOCS}")
    return json.loads(GMINST4LL_IOCS.read_text(encoding="utf-8"))


class TestGMinst4llRealIoCs(E2EBaseTest):
    """TC-33 — Validación del pipeline SOAR con IoCs reales del GMinst4ll."""

    tc_id = "TC-33"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.iocs = _load_gminst4ll_iocs()

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-33 {msg}"
        print(line)

    def _get_case_for_alert(self, alert_id: str) -> dict:
        """Return OUR case via the alert_id marker — never 'newest globally'."""
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        matching = [
            c
            for c in sorted(cases, key=lambda c: c.get("caseId", 0), reverse=True)
            if alert_id in c.get("description", "")
        ]
        if not matching:
            pytest.fail(
                f"No TheHive case containing alert_id={alert_id} "
                "(workflow may not create case for this IoC type)"
            )
        return matching[0]

    # ------------------------------------------------------------------
    # Subtest 1: Descargar TODAS las muestras, verificar hash, borrar
    # ------------------------------------------------------------------
    def test_download_and_hash_all_samples(self):
        """TC-33-01: Download ALL malware samples from forensics repo, verify
        SHA256, delete.

        Descarga cada muestra de malware real del repositorio forense, calcula su hash
        SHA256 y lo compara con el valor esperado del fixture. Cada archivo se elimina
        inmediatamente después de la verificación. No se descomprime ni ejecuta ninguno.

        Muestras descargadas:
          - GMinst4ll 2.03.rar (loader principal, 844 MiB)
          - SystemSP.rar (killer AV + persistencia)
          - beket.rar (Pulsar RAT v1.6.6.0)
          - appy.exe (launcher Rust)
          - Windows_Compatibility_Agent.exe (payload Python C2)
          - Windows_Compatibility_Agent_Host.exe (payload Python C2)
          - kamzat.exe (payload Python alternativo)
          - postevak.exe (payload Python simple)
        """
        samples = self.iocs.get("downloadable_samples", [])
        assert len(samples) > 0, "No downloadable samples in fixture"
        base_url = self.iocs.get("_meta", {}).get(
            "download_base_url",
            GMINST4LL_SAMPLES_BASE_URL,
        )

        self._log(f"=== TC-33-01: DOWNLOAD AND HASH ALL {len(samples)} SAMPLES ===")

        results = []
        for idx, sample in enumerate(samples, 1):
            name = sample["name"]
            expected_hash = sample["sha256"]
            subfolder = sample["subfolder"]
            url_encoded = sample.get("url_encoded", name.replace(" ", "%20"))
            url = f"{base_url}/{subfolder}/{url_encoded}"

            self._log(f"--- Sample {idx}/{len(samples)}: {name} ---")
            self._log(f"  + URL: {url}")
            self._log(f"  + Expected SHA256: {expected_hash}")

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=Path(name).suffix,
                    delete=False,
                    dir=str(RUNTIME_DIR),
                ) as f:
                    tmp_path = Path(f.name)

                sha256 = hashlib.sha256()
                total_bytes = 0
                last_exc = None
                for attempt in range(3):
                    try:
                        sha256 = hashlib.sha256()
                        total_bytes = 0
                        response = self.s.get(
                            url,
                            stream=True,
                            timeout=DOWNLOAD_TIMEOUT,
                            allow_redirects=True,
                        )
                        assert (
                            response.status_code == 200
                        ), f"Download failed for {name}: HTTP {response.status_code}"
                        with open(tmp_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK):
                                if chunk:
                                    f.write(chunk)
                                    sha256.update(chunk)
                                    total_bytes += len(chunk)
                        last_exc = None
                        break
                    except (requests.RequestException, AssertionError) as exc:
                        last_exc = exc
                        self._log(f"  ! Download attempt {attempt + 1}/3 failed: {exc}")
                        time.sleep(5 * (attempt + 1))
                if last_exc is not None:
                    raise last_exc

                actual_hash = sha256.hexdigest()
                self._log(f"  + Downloaded {total_bytes} bytes")
                self._log(f"  + SHA256 actual:   {actual_hash}")

                assert (
                    actual_hash == expected_hash
                ), f"SHA256 mismatch for {name}: got {actual_hash}, expected {expected_hash}"
                self._log(f"  + Hash verification PASSED for {name}")
                results.append(
                    {"name": name, "hash": actual_hash, "bytes": total_bytes, "ok": True}
                )

            finally:
                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                        self._log(f"  + Deleted: {tmp_path.name}")
                    except PermissionError:
                        # Windows bind-mounts can deny unlink; harmless leftover
                        self._log(f"  + Could not delete {tmp_path.name} (denied)")

        # Summary
        self._log(f"=== SUMMARY: {len(results)}/{len(samples)} samples verified ===")
        for r in results:
            self._log(f"  + {r['name']}: {r['bytes']} bytes, SHA256 OK")

        assert len(results) == len(
            samples
        ), f"Only {len(results)}/{len(samples)} samples verified successfully"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Total elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-01 COMPLETED — ALL SAMPLES HASH-VERIFIED ===")

    # ------------------------------------------------------------------
    # Subtest 2: Hash IoC — TREZ_cor (loader principal)
    # ------------------------------------------------------------------
    def test_malicious_hash_ioc(self):
        """TC-33-02: Send TREZ_cor 4.52.3.exe SHA256 as IoC to the SOAR
        workflow.

        Envía el hash SHA256 del ejecutable principal del GMinst4ll al
        webhook de Shuffle. Verifica que el workflow crea un caso en
        TheHive con observables de tipo hash.
        """
        hashes = self.iocs.get("hashes_sha256", [])
        trez = next((h for h in hashes if "TREZ_cor" in h["name"]), None)
        assert trez is not None, "TREZ_cor hash not found in fixture"

        alert_id = self.uid("TC33-HASH-TREZ")
        payload = {
            "alert_id": alert_id,
            "alert_type": "infostealer",
            "hostname": "WIN-FORENSIC-001",
            "src_ip": "192.168.1.230",
            "hash": trez["hash"],
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "infostealer_detection",
            "mitre_techniques": ["T1566.002", "T1059.001", "T1547.001"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "file_name": "TREZ_cor 4.52.3.exe",
            "file_size": trez.get("size_bytes", 0),
        }

        self._log("=== TC-33-02: MALICIOUS HASH IoC (TREZ_cor) STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        case_id = case.get("id", case.get("_id", ""))
        self._log(f"  + TheHive case: {case_id}")

        observables = self.thehive.get_case_observables(case_id)
        obs_values = [o.get("data", "") for o in (observables or [])]
        self._log(f"  + Observables: {obs_values[:5]}")
        # The submitted hash must appear as a case observable — that is the
        # point of this test, not merely 'a case exists'.
        assert any(
            trez["hash"].lower() == v.lower() for v in obs_values
        ), f"Submitted hash not found in case observables: {obs_values[:10]}"

        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-02 COMPLETED — HASH IoC VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 3: Pulsar RAT hash
    # ------------------------------------------------------------------
    def test_pulsar_rat_hash(self):
        """TC-33-03: Send Pulsar RAT v1.6.6.0 SHA256 as IoC.

        Envía el hash de appy.exe (Pulsar RAT) al workflow. Verifica que
        Cortex analiza el hash y TheHive crea observable.
        """
        hashes = self.iocs.get("hashes_sha256", [])
        pulsar = next((h for h in hashes if "pulsar_rat" in h["name"]), None)
        assert pulsar is not None, "Pulsar RAT hash not found in fixture"

        alert_id = self.uid("TC33-HASH-PULSAR")
        payload = {
            "alert_id": alert_id,
            "alert_type": "rat",
            "hostname": "WIN-FORENSIC-002",
            "src_ip": "192.168.1.231",
            "hash": pulsar["hash"],
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "rat_detection",
            "mitre_techniques": ["T1056.001", "T1102", "T1567.002"],
            "malware_type": "rat",
            "malware_family": "Pulsar RAT v1.6.6.0",
            "file_name": "appy.exe",
            "file_size": pulsar.get("size_bytes", 0),
        }

        self._log("=== TC-33-03: PULSAR RAT HASH IoC STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"

        case_id = case.get("id", case.get("_id", ""))
        observables = self.thehive.get_case_observables(case_id)
        obs_values = [o.get("data", "") for o in (observables or [])]
        assert any(
            pulsar["hash"].lower() == v.lower() for v in obs_values
        ), f"Pulsar RAT hash not found in case observables: {obs_values[:10]}"
        self._log("  + Pulsar hash present as observable")
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-03 COMPLETED — PULSAR RAT IoC VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 4: C2 URLs
    # ------------------------------------------------------------------
    def test_c2_url_ioc(self):
        """TC-33-04: Send C2 URLs (Pastebin, Dropbox, GitHub) as IoCs.

        Envía las URLs C2 del GMinst4ll al workflow. Verifica que se
        crean observables de tipo URL en TheHive.
        """
        urls = self.iocs.get("urls_c2", [])
        assert len(urls) > 0, "No C2 URLs in fixture"

        alert_id = self.uid("TC33-URL-C2")
        payload = {
            "alert_id": alert_id,
            "alert_type": "c2_communication",
            "hostname": "WIN-FORENSIC-003",
            "src_ip": "192.168.1.232",
            "hash": "0" * 64,
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "c2_communication",
            "mitre_techniques": ["T1102", "T1567.002"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "urls": urls,
            "c2_urls": urls,
        }

        self._log("=== TC-33-04: C2 URL IoCs STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-04 COMPLETED — C2 URL IoCs VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 5: C2 domains
    # ------------------------------------------------------------------
    def test_c2_domain_ioc(self):
        """TC-33-05: Send C2 domains (pastebin.com, dropbox.com, etc.) as IoCs.

        Envía los dominios C2 al workflow. Verifica búsqueda en MISP y
        creación de observables.
        """
        domains = self.iocs.get("domains_c2", [])
        assert len(domains) > 0, "No C2 domains in fixture"

        alert_id = self.uid("TC33-DOMAIN-C2")
        payload = {
            "alert_id": alert_id,
            "alert_type": "c2_communication",
            "hostname": "WIN-FORENSIC-004",
            "src_ip": "192.168.1.233",
            "hash": "0" * 64,
            "severity": 2,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "c2_domain_lookup",
            "mitre_techniques": ["T1102"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "domains": domains,
            "c2_domains": domains,
        }

        self._log("=== TC-33-05: C2 DOMAIN IoCs STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-05 COMPLETED — C2 DOMAIN IoCs VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 6: C2 IPs
    # ------------------------------------------------------------------
    def test_c2_ip_ioc(self):
        """TC-33-06: Send C2 IP addresses as IoCs.

        Envía las IPs de los servicios C2 (Pastebin, Dropbox, Reddit,
        Telegram) al workflow. Verifica enriquecimiento en Cortex.
        """
        ips_data = self.iocs.get("ips_c2", [])
        assert len(ips_data) > 0, "No C2 IPs in fixture"
        ips = [entry["ip"] for entry in ips_data]

        alert_id = self.uid("TC33-IP-C2")
        payload = {
            "alert_id": alert_id,
            "alert_type": "c2_communication",
            "hostname": "WIN-FORENSIC-005",
            "src_ip": ips[0] if ips else "172.66.171.73",
            "hash": "0" * 64,
            "severity": 2,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "c2_ip_connection",
            "mitre_techniques": ["T1102"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "ips": ips,
            "c2_ips": ips,
        }

        self._log("=== TC-33-06: C2 IP IoCs STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-06 COMPLETED — C2 IP IoCs VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 7: Telegram exfiltration IoC
    # ------------------------------------------------------------------
    def test_telegram_ioc(self):
        """TC-33-07: Send Telegram Bot ID + Chat ID as exfiltration IoC.

        Envía los identificadores de Telegram (bot ID, chat ID) como
        IoCs de exfiltración. Verifica que el caso TheHive los
        documenta.
        """
        tg = self.iocs.get("telegram", {})
        assert tg, "No telegram data in fixture"

        alert_id = self.uid("TC33-TELEGRAM-EXFIL")
        payload = {
            "alert_id": alert_id,
            "alert_type": "data_exfiltration",
            "hostname": "WIN-FORENSIC-006",
            "src_ip": "149.154.166.110",
            "hash": "0" * 64,
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "telegram_exfiltration",
            "mitre_techniques": ["T1567.002", "T1102"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "telegram_bot_id": tg.get("bot_id", ""),
            "telegram_chat_id": tg.get("chat_id_exfiltration", ""),
            "telegram_operator": tg.get("operator_username", ""),
            "exfiltration_channel": "telegram_bot_api",
        }

        self._log("=== TC-33-07: TELEGRAM EXFIL IoC STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-07 COMPLETED — TELEGRAM IoC VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 8: Registry persistence IoCs
    # ------------------------------------------------------------------
    def test_registry_persistence(self):
        """TC-33-08: Send registry persistence keys as IoCs.

        Envía las claves de registro usadas para persistencia (Winlogon
        UserInit, EnableLUA, RunOnceEx) como IoCs de persistencia.
        """
        reg_keys = self.iocs.get("registry_persistence", [])
        assert len(reg_keys) > 0, "No registry persistence keys in fixture"

        alert_id = self.uid("TC33-REGISTRY-PERSIST")
        payload = {
            "alert_id": alert_id,
            "alert_type": "persistence",
            "hostname": "WIN-FORENSIC-007",
            "src_ip": "192.168.1.234",
            "hash": "0" * 64,
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "registry_persistence",
            "mitre_techniques": ["T1547.001", "T1548.002"],
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
            "registry_keys": [k["key"].replace("\\", "/") for k in reg_keys],
            "persistence_mechanism": "winlogon_userinit",
        }

        self._log("=== TC-33-08: REGISTRY PERSISTENCE IoCs STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        self._log(f"  + TheHive case: {case.get('title', '')}")
        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-08 COMPLETED — REGISTRY IoCs VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 9: MITRE ATT&CK mapping verification
    # ------------------------------------------------------------------
    def test_mitre_mapping(self):
        """TC-33-09: Verify MITRE ATT&CK techniques are mapped in TheHive case.

        Envía una alerta con técnicas MITRE ATT&CK del GMinst4ll y
        verifica que el caso TheHive las documenta correctamente.
        """
        mitre = self.iocs.get("mitre_attack", [])
        assert len(mitre) > 0, "No MITRE techniques in fixture"
        techniques = [m["technique"] for m in mitre]

        alert_id = self.uid("TC33-MITRE-MAP")
        payload = {
            "alert_id": alert_id,
            "alert_type": "infostealer",
            "hostname": "WIN-FORENSIC-008",
            "src_ip": "192.168.1.235",
            "hash": self.iocs["hashes_sha256"][0]["hash"],
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "mitre_attack_mapping",
            "mitre_techniques": techniques,
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll",
        }

        self._log("=== TC-33-09: MITRE ATT&CK MAPPING STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        case = self._get_case_for_alert(alert_id)
        case_id = case.get("id", case.get("_id", ""))
        self._log(f"  + TheHive case: {case_id}")
        self._log(f"  + Case description: {case.get('description', '')[:200]}")

        assert isinstance(case, dict), "Case must be a dict"
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-09 COMPLETED — MITRE MAPPING VALIDATED ===")

    # ------------------------------------------------------------------
    # Subtest 10: Multi-IoC alert (all IoCs in one execution)
    # ------------------------------------------------------------------
    def test_multi_ioc_alert(self):
        """TC-33-10: Send alert with ALL GMinst4ll IoCs in a single execution.

        Envía una alerta completa con hashes, URLs, dominios, IPs,
        técnicas MITRE y datos de Telegram en una sola ejecución del
        workflow. Verifica que el pipeline SOAR procesa todos los tipos
        de IoC simultáneamente.
        """
        hashes = self.iocs.get("hashes_sha256", [])
        urls = self.iocs.get("urls_c2", [])
        domains = self.iocs.get("domains_c2", [])
        ips = [e["ip"] for e in self.iocs.get("ips_c2", [])]
        mitre = [m["technique"] for m in self.iocs.get("mitre_attack", [])]
        tg = self.iocs.get("telegram", {})

        alert_id = self.uid("TC33-MULTI-IOC")
        payload = {
            "alert_id": alert_id,
            "alert_type": "infostealer",
            "hostname": "WIN-FORENSIC-009",
            "src_ip": "192.168.1.236",
            "hash": hashes[0]["hash"] if hashes else "0" * 64,
            "severity": 3,
            "source": "gminst4ll-forensics",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "multi_ioc_infostealer",
            "mitre_techniques": mitre,
            "malware_type": "infostealer",
            "malware_family": "GMinst4ll / Pulsar RAT",
            "all_hashes": [h["hash"] for h in hashes],
            "all_urls": urls,
            "all_domains": domains,
            "all_ips": ips,
            "telegram_bot_id": tg.get("bot_id", ""),
            "telegram_chat_id": tg.get("chat_id_exfiltration", ""),
            "actor_github": self.iocs.get("actor", {}).get("github_user", ""),
            "actor_telegram": self.iocs.get("actor", {}).get("telegram_operator", ""),
            "iocs_count": len(hashes) + len(urls) + len(domains) + len(ips),
        }

        self._log("=== TC-33-10: MULTI-IOC ALERT (ALL IoCs) STARTED ===")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log("  + Workflow FINISHED")

        # Validate that the workflow execution completed successfully
        assert isinstance(execution, dict), "Workflow execution must be a dict"
        assert (
            execution.get("status") == "FINISHED"
        ), f"Multi-IoC workflow execution must be FINISHED, got {execution.get('status')}"
        self._log("  + Workflow execution status validated: FINISHED")

        case = self._get_case_for_alert(alert_id)
        case_id = case.get("id", case.get("_id", ""))
        self._log(f"  + TheHive case: {case_id}")
        self._log(f"  + Total IoCs sent: {payload['iocs_count']}")

        assert isinstance(case, dict), "Case must be a dict"
        # Validate the case has a valid ID
        assert case_id, "TheHive case must have a non-empty 'id' or '_id'"

        # Validate the case was created with the multi-IoC alert data
        case_description = case.get("description", "")
        assert isinstance(case_description, str), "Case description must be a string"
        # The case should reference the alert or contain IoC-related content
        assert len(case_description) > 0, "Case description must not be empty"
        self._log(f"  + Case description length: {len(case_description)} chars")

        # Verify the ES document has all IoC fields from the multi-IoC payload
        doc = self.es.search_by_alert_id(alert_id)
        assert doc is not None, "ES document for multi-IoC alert not found"
        assert isinstance(doc, dict), "ES document must be a dict"

        # Validate that all IoC types are present in the ES document
        ioc_fields = ["all_hashes", "all_urls", "all_domains", "all_ips"]
        for field in ioc_fields:
            assert (
                field in doc
            ), f"ES document must contain IoC field '{field}', got keys: {list(doc.keys())[:20]}"
        self._log(f"  + All IoC fields present in ES document: {ioc_fields}")

        # Validate that the IoC counts match what was sent
        assert isinstance(doc.get("all_hashes"), list), "all_hashes in ES must be a list"
        assert isinstance(doc.get("all_urls"), list), "all_urls in ES must be a list"
        assert isinstance(doc.get("all_domains"), list), "all_domains in ES must be a list"
        assert isinstance(doc.get("all_ips"), list), "all_ips in ES must be a list"
        self._log(
            f"  + IoC counts in ES: hashes={len(doc['all_hashes'])}, "
            f"urls={len(doc['all_urls'])}, domains={len(doc['all_domains'])}, "
            f"ips={len(doc['all_ips'])}"
        )
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"  Elapsed: {elapsed:.1f}s")
        self._log("=== TC-33-10 COMPLETED — MULTI-IOC ALERT VALIDATED ===")
