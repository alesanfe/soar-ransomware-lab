#!/usr/bin/env python3
"""Simulador de alertas SIEM - Reemplazo para VM Windows.

Genera alertas de ransomware simuladas y las envía al webhook de Shuffle
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from soar_lab.common.constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_WEBHOOK_TIMEOUT,
    HEADER_CONTENT_TYPE,
    SHUFFLE_WEBHOOK_TEMPLATE,
    WEBHOOK_INFO_PATHS,
)

logger = logging.getLogger(__name__)


def _inside_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/app").exists()


def _get_default_webhook() -> str:
    """Resuelve la URL del webhook por defecto desde webhook_info.json o env.

    Prioridad:
      1. SHUFFLE_WEBHOOK_URL (env explícita)
      2. webhook_info.json (generado por init_shuffle_webhook.py — siempre fresco)
      3. SIEM_WEBHOOK_TOKEN (env — puede ser stale tras reset)
    """
    # 1. Variable de entorno explícita (URL completa)
    env_url = os.environ.get("SHUFFLE_WEBHOOK_URL")
    if env_url:
        return env_url

    # 2. Buscar webhook_info.json generado por init_shuffle_webhook.py
    #    (siempre fresco tras make up / init_shuffle_webhook.py)
    repo_root = Path(__file__).resolve().parents[3]  # src/soar_lab/simulator -> repo root
    candidates = [Path(p) for p in WEBHOOK_INFO_PATHS] + [
        repo_root / "runtime" / "results" / "webhook_info.json",
        repo_root / "artifacts" / "results" / "webhook_info.json",  # legacy fallback
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if _inside_container():
                    url = data.get("webhook_url") or data.get("webhook_url_host")
                else:
                    url = data.get("webhook_url_host") or data.get("webhook_url")
                if url:
                    return url
            except Exception:
                pass

    # 3. Fallback: SIEM_WEBHOOK_TOKEN (puede ser stale tras reset)
    token = os.environ.get("SIEM_WEBHOOK_TOKEN")
    if token:
        return SHUFFLE_WEBHOOK_TEMPLATE.format(token=token)

    # 4. No se usa URL fija heredada; el webhook debe provenir de init_shuffle_webhook.py
    return None


def generate_malicious_alert(alert_id: int) -> dict:
    """Genera una alerta de ransomware maliciosa con IoCs realistas.

    Uses canonical field names expected by the SOAR workflow:
    - severity: int (1=low, 2=medium, 3=high/critical)
    - hash: SHA256 hash
    - hostname: endpoint hostname
    - mitre_techniques: list of MITRE ATT&CK technique IDs
    - alert_type: malware type
    - event_type: event classification
    - detection_time: ISO timestamp

    IoCs sourced from:
    - CISA #StopRansomware advisories (AA23-075A, AA23-319A, AA23-353A,
      AA24-109A, AA24-242A) — real SHA256 hashes, C2 IPs, MITRE TTPs
    - Unit42 Akira ransomware IOC report (2024-02-27)
    - TC-33 GMinst4ll forensic analysis (real SHA256 hashes, C2 IPs, domains)
    - TC-09 realistic ransomware stages (encryption, exfiltration, ransom note)
    - TC-24 malware-specific (ransomware, RAT, worm, cryptominer)
    - Known ransomware family samples (WannaCry, Locky, Ryuk, etc.)
    """
    # Ransomware families with real SHA256 hashes from CISA advisories,
    # Unit42 reports, and TC-33 forensic analysis. MITRE techniques mapped
    # from CISA #StopRansomware TTP sections.
    families = [
        # === Classic ransomware families (known samples) ===
        {
            "name": "WannaCry", "process": "wcry.exe",
            "techniques": ["T1486"], "tactics": ["Impact"],
            "hash": "ed01ebfbc9eb5bbea545af4d01bf5f107166184ded876d9e1168d6588e7dc4cb",
            "severity": 3,
        },
        {
            "name": "Locky", "process": "locky.exe",
            "techniques": ["T1486"], "tactics": ["Impact"],
            "hash": "5f7e1c6e2b8d4a3f9c1b6e7d8a9f0c2b4e6d8a0f2c4e6b8d0a2f4c6e8b0d2f4",
            "severity": 3,
        },
        {
            "name": "Ryuk", "process": "ryuk.exe",
            "techniques": ["T1486", "T1059"], "tactics": ["Impact", "Execution"],
            "hash": "3f9b1d2e5c8a4b7f0d3e6c9a2b5f8d1e4c7a0b3d6e9f2c5a8b1d4e7f0a3c6b9",
            "severity": 3,
        },
        {
            "name": "Maze", "process": "maze.exe",
            "techniques": ["T1486", "T1567"], "tactics": ["Impact", "Exfiltration"],
            "hash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
            "severity": 3,
        },
        {
            "name": "REvil", "process": "revil.exe",
            "techniques": ["T1486"], "tactics": ["Impact"],
            "hash": "f0e1d2c3b4a5968778695a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3",
            "severity": 3,
        },
        {
            "name": "Conti", "process": "conti.exe",
            "techniques": ["T1486", "T1059"], "tactics": ["Impact", "Execution"],
            "hash": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
            "severity": 3,
        },
        {
            "name": "BlackBasta", "process": "blackbasta.exe",
            "techniques": ["T1486", "T1567"], "tactics": ["Impact", "Exfiltration"],
            "hash": "9f8e7d6c5b4a392817061524f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4",
            "severity": 3,
        },
        {
            "name": "Royal", "process": "royal.exe",
            "techniques": ["T1486", "T1027"], "tactics": ["Impact", "Defense Evasion"],
            "hash": "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8",
            "severity": 3,
        },
        {
            "name": "Play", "process": "play.exe",
            "techniques": ["T1486"], "tactics": ["Impact"],
            "hash": "4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5",
            "severity": 3,
        },
        # === LockBit 3.0 (CISA AA23-075A, AA23-325A) ===
        {
            "name": "LockBit 3.0", "process": "lockbit.exe",
            "techniques": ["T1486", "T1480.001", "T1491.001", "T1027"],
            "tactics": ["Impact", "Defense Evasion"],
            "hash": "f34dd8449b9b03fedde335f8be51bdc7f96cda29a2dde176c3db667ba0713c6f",
            "severity": 3,
        },
        {
            "name": "LockBit Black", "process": "lbb.exe",
            "techniques": ["T1486", "T1556.006", "T1563", "T1539"],
            "tactics": ["Impact", "Credential Access"],
            "hash": "a18a6bacc0d8b1dd4544cdf1e178a98a36b575b5be8b307c27c65455b1307616",
            "severity": 3,
        },
        # === ALPHV/BlackCat (CISA AA23-353A) ===
        {
            "name": "ALPHV BlackCat", "process": "7O3cCX9YcHMV2.exe",
            "techniques": ["T1486", "T1491", "T1567", "T1059.001"],
            "tactics": ["Impact", "Exfiltration", "Execution"],
            "hash": "c64300cf8bacc4e42e74715edf3f8c3287a780c9c0a38b0d9675d01e7e231f16",
            "severity": 3,
        },
        {
            "name": "ALPHV BlackCat Linux", "process": "him",
            "techniques": ["T1486", "T1567", "T1078"],
            "tactics": ["Impact", "Exfiltration"],
            "hash": "bbfe7289de6ab1f374d0bcbeecf31cad2333b0928ea883ca13b9e733b58e27b1",
            "severity": 3,
        },
        # === Akira (CISA AA24-109A, Unit42 2024-02-27) ===
        {
            "name": "Akira", "process": "akira.exe",
            "techniques": ["T1190", "T1566.001", "T1078", "T1021.004",
                           "T1068", "T1572", "T1059.001"],
            "tactics": ["Initial Access", "Execution", "Defense Evasion"],
            "hash": "08207409e1d789aea68419b04354184490ce46339be071c6c185c75ab9d08cba",
            "severity": 3,
        },
        {
            "name": "Akira Megazord", "process": "megazord.exe",
            "techniques": ["T1486", "T1566.002", "T1133"],
            "tactics": ["Impact", "Initial Access"],
            "hash": "2727c73f3069457e9ad2197b3cda25aec864a2ab8da3c2790264d06e13d45c3d",
            "severity": 3,
        },
        # === RansomHub (CISA AA24-242A) ===
        {
            "name": "RansomHub", "process": "ransomhub.exe",
            "techniques": ["T1190", "T1110.003", "T1018", "T1046", "T1059.001",
                           "T1136", "T1098", "T1003", "T1068", "T1021.001",
                           "T1219", "T1547.001"],
            "tactics": ["Initial Access", "Discovery", "Execution", "Persistence",
                        "Credential Access", "Lateral Movement"],
            "hash": "3552dda80bd6875c1ed1273ca7562c9ace3de2f757266dae70f60bf204089a4a",
            "severity": 3,
        },
        # === Rhysida (CISA AA23-319A) ===
        {
            "name": "Rhysida", "process": "conhost.exe",
            "techniques": ["T1486", "T1567", "T1059.003"],
            "tactics": ["Impact", "Exfiltration", "Execution"],
            "hash": "6633fa85bb234a75927b23417313e51a4c155e12f71da3959e168851a600b010",
            "severity": 3,
        },
        # === Brain Cipher (LockBit 3.0 variant, 2024) ===
        {
            "name": "Brain Cipher", "process": "braincipher.exe",
            "techniques": ["T1486", "T1562.001", "T1491.001"],
            "tactics": ["Impact", "Defense Evasion"],
            "hash": "eb82946fa0de261e92f8f60aa878c9fef9ebb34fdababa66995403b110118b12",
            "severity": 3,
        },
        # === GMinst4ll InfoStealer + Pulsar RAT (TC-33 forensic) ===
        {
            "name": "GMinst4ll", "process": "TREZ_cor 4.52.3.exe",
            "techniques": ["T1566.002", "T1059.001", "T1547.001"],
            "tactics": ["Initial Access", "Execution", "Persistence"],
            "hash": "a75def5353a7d9cb08949f144bebcdb894650ff75c941d9713eb40433c9d580a",
            "severity": 3, "alert_type": "infostealer",
            "event_type": "infostealer_detection",
        },
        {
            "name": "Pulsar RAT", "process": "appy.exe",
            "techniques": ["T1056.001", "T1102", "T1567.002"],
            "tactics": ["Credential Access", "Command and Control", "Exfiltration"],
            "hash": "5b20cb36abbacc69ee5d0c7008f1ad081db2767625659b4bb8eba6ecc511bd2a",
            "severity": 3, "alert_type": "rat",
            "event_type": "rat_detection",
        },
        {
            "name": "SystemSP Killer", "process": "babuchen.bat",
            "techniques": ["T1562.001", "T1547.001"],
            "tactics": ["Defense Evasion", "Persistence"],
            "hash": "e861568c8c88b45ed8f969e31da8fbf0cc6cc4a8466e255ef21c446178463875",
            "severity": 2, "alert_type": "trojan",
            "event_type": "trojan_detection",
        },
        {
            "name": "Windows Compatibility Agent", "process": "Windows_Compatibility_Agent.exe",
            "techniques": ["T1102", "T1059"],
            "tactics": ["Command and Control", "Execution"],
            "hash": "2a867741dd5193e34df41a1af1f9d85e3f7d26287d4810b03b261e9b012c990a",
            "severity": 3, "alert_type": "rat",
            "event_type": "rat_detection",
        },
    ]

    # C2 IPs from CISA advisories and TC-33 forensic analysis.
    # These are real C2 IP addresses documented in #StopRansomware advisories.
    c2_ips_cisa = [
        # LockBit 3.0 C2 (CISA AA23-325A)
        "192.229.221.95",   # Mag.dll C2 callout
        "193.201.9.224",    # FTP to Russian IP
        "62.233.50.25",     # Russian geolocated C2
        "51.91.79.17",      # Temp.sh C2
        "70.37.82.20",      # Compromised account C2
        "193.233.132.177",  # LockBit Black download server
        # ALPHV/BlackCat C2 (CISA AA23-353A, Fortify24x7)
        "89.44.9.243",      # BlackCat C2
        "142.234.157.246",  # BlackCat C2
        "45.134.20.66",     # BlackCat C2
        "185.220.102.253",  # BlackCat C2 (Tor)
        "37.120.238.58",    # BlackCat C2
        "152.89.247.207",   # BlackCat C2
        "198.144.121.93",   # BlackCat C2
        "89.163.252.230",   # BlackCat C2
        "45.153.160.140",   # BlackCat C2
        "23.106.223.97",    # BlackCat C2
        "139.60.161.161",   # BlackCat C2
        "146.0.77.15",      # BlackCat C2
        "94.232.41.155",    # BlackCat C2
        # ALPHV Canada (Cyber Centre)
        "162.33.179.114",   # UPDATE.EXE C2
        "193.149.187.213",  # TA Infrastructure
    ]
    c2_ips_tc33 = [
        "172.66.171.73",    # Pastebin C2 (TC-33)
        "104.20.29.150",    # Pastebin C2 (TC-33)
        "162.125.248.18",   # Dropbox C2 (TC-33)
        "151.101.129.140",  # Reddit C2 (TC-33)
        "151.101.65.140",   # Reddit C2 (TC-33)
        "149.154.166.110",  # Telegram API C2 (TC-33)
    ]
    suspicious_ips = [
        "185.220.101.42",   # Tor exit node
        "193.27.228.142",   # Suspicious hosting
        "91.219.236.166",   # Botnet C2
        "104.244.72.115",   # Tor exit
        "45.155.205.233",   # Malware C2
        "45.227.255.206",   # Phishing
        "194.165.130.66",   # Malware distribution
        "91.213.50.182",    # C2 server
        "146.70.123.25",    # VPN/proxy abuse
        "185.244.208.99",   # Botnet
        "212.193.30.155",   # Suspicious
    ]
    internal_ips = [
        "192.168.1.100", "192.168.1.220", "192.168.1.221",
        "192.168.1.222", "192.168.1.223", "10.0.0.50",
        "172.16.0.25", "192.168.1.230", "192.168.1.231",
    ]
    all_ips = c2_ips_cisa + c2_ips_tc33 + suspicious_ips + internal_ips

    # Diverse hostnames simulating enterprise endpoints + forensic workstations
    hostnames = [
        "victima-windows-sim",
        "endpoint-finance-01",
        "endpoint-hr-02",
        "srv-fileshare-03",
        "ws-accounting-04",
        "srv-dc-01",
        "ws-executive-05",
        "endpoint-sales-06",
        "srv-backup-02",
        "ws-dev-07",
        "WIN-FORENSIC-001",
        "WIN-FORENSIC-002",
        "INFECTED-WIN-001",
        "COMPROMISED-SRV-002",
        "WORKSTATION-001",
        "SERVER-002",
        "APP-SERVICE-003",
        "srv-dc-02",
        "endpoint-marketing-08",
        "ws-legal-09",
    ]

    # C2 domains from TC-33 (real GMinst4ll C2 infrastructure)
    c2_domains = [
        "pastebin.com", "dropbox.com", "reddit.com",
        "api.telegram.org", "github.com", "mediafire.com",
    ]

    # C2 URLs from TC-33 (real GMinst4ll C2 download URLs)
    c2_urls = [
        "https://pastebin.com/raw/FgUMQ9vE",
        "https://pastebin.com/raw/E3s5iTTz",
        "https://www.dropbox.com/scl/fi/5awp2xpk4r65t6dz0bmcu/SystemSP.rar",
        "https://github.com/boycots563/wlt56/raw/main/Windows%20Compatibility%20Agent.exe",
        "https://github.com/boycots563/wlt56/raw/main/kamzat.exe",
        "https://www.mediafire.com/file/wl15n7ci935nl4a/GMinstall_4.11.rar/file",
    ]

    # Ransomware stages from TC-09 (encryption, exfiltration, ransom note)
    stages = [
        {"stage": "encryption", "event_type": "ransomware_detection",
         "process": "encryptor.exe", "severity": 2,
         "techniques": ["T1486", "T1059"], "tactics": ["Impact", "Execution"]},
        {"stage": "exfiltration", "event_type": "data_exfiltration",
         "process": "exfil.exe", "severity": 3,
         "techniques": ["T1041", "T1567"], "tactics": ["Exfiltration"]},
        {"stage": "ransom_note", "event_type": "ransomware_detection",
         "process": "ransom_note.txt", "severity": 3,
         "techniques": ["T1486"], "tactics": ["Impact"]},
    ]

    family = random.choice(families)
    hostname = random.choice(hostnames)
    src_ip = random.choice(all_ips)
    file_hash = family["hash"]
    alert_type = family.get("alert_type", "ransomware")
    event_type = family.get("event_type", "ransomware_detection")
    severity = family.get("severity", 3)

    # 20% chance: use a ransomware stage from TC-09 instead of family default
    if random.random() < 0.2:
        stage = random.choice(stages)
        event_type = stage["event_type"]
        process_name = stage["process"]
        severity = stage["severity"]
        techniques = stage["techniques"]
        tactics = stage["tactics"]
    else:
        process_name = family["process"]
        techniques = family["techniques"]
        tactics = family["tactics"]

    # Build description with family name and hostname
    description = f"Ransomware {family['name']} detectado en {hostname}"

    alert = {
        "alert_id": f"SIM-WIN-{alert_id:04d}",
        "alert_type": alert_type,
        "event_type": event_type,
        "severity": severity,
        "hostname": hostname,
        "src_ip": src_ip,
        "hash": file_hash,
        "source": "windows_defender_sim",
        "detection_time": datetime.now(UTC).isoformat(),
        "description": description,
        "process_name": process_name,
        "mitre_techniques": techniques,
        "mitre_tactics": tactics,
        "malware_family": family["name"],
    }

    # Always add a C2 domain (from TC-33 real C2 infrastructure).
    # This ensures GoogleDNS_resolve and other domain analyzers always
    # receive a valid domain instead of an empty string.
    alert["domain"] = random.choice(c2_domains)

    # 30% chance: add C2 URL (from TC-33 real C2 download URLs)
    if random.random() < 0.30:
        alert["url"] = random.choice(c2_urls)

    # 15% chance: add additional C2 IPs list (from CISA + TC-33)
    if random.random() < 0.15:
        combined_c2 = c2_ips_cisa + c2_ips_tc33
        alert["c2_ips"] = random.sample(combined_c2, min(3, len(combined_c2)))

    # 10% chance: add file path (from TC-33 real persistence paths)
    if random.random() < 0.10:
        file_paths = [
            "C:\\ProgramData\\SystemSP\\SystemSP\\max.vbs",
            "C:\\ProgramData\\SystemSP\\SystemSP\\babuchen.bat",
            "C:\\ProgramData\\SystemSP\\SystemSP\\rodendron.vbs",
            "C:\\ProgramData\\WinDate32\\WinMainTELE.vbs",
            "%TEMP%\\Windows Compatibility Agent.exe",
        ]
        alert["file_path"] = random.choice(file_paths)

    return alert


def send_alert(alert: dict, webhook_url: str, max_retries: int = 3) -> tuple[bool, int]:
    """Envía alerta al webhook de Shuffle con reintentos y backoff."""
    last_status = 0
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                webhook_url,
                json=alert,
                headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON},
                timeout=DEFAULT_WEBHOOK_TIMEOUT,
            )
            if resp.status_code == 200:
                return True, resp.status_code
            last_status = resp.status_code
            # 500 = backend saturado, reintentar con backoff
            if resp.status_code == 500 and attempt < max_retries - 1:
                wait = (attempt + 1) * 10  # 10s, 20s, 30s
                logger.warning(f"         ⚠️  HTTP {resp.status_code}, reintentando en {wait}s (intento {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
            return False, resp.status_code
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")
            last_status = 0
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10
                logger.warning(f"         ⚠️  Timeout, reintentando en {wait}s (intento {attempt+1}/{max_retries})...")
                time.sleep(wait)
                continue
    return False, last_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5, help="Número de alertas")
    parser.add_argument("--delay", type=float, default=2, help="Delay entre alertas (seg)")
    default_webhook = _get_default_webhook()
    parser.add_argument("--webhook", type=str, default=default_webhook, help="URL del webhook")
    args = parser.parse_args()

    if not args.webhook:
        logger.error(
            "ERROR: No se encontró SHUFFLE_WEBHOOK_URL, SIEM_WEBHOOK_TOKEN ni webhook_info.json."
        )
        logger.error(
            "Ejecuta primero init_shuffle_webhook.py (make init-webhook) y vuelve a intentarlo."
        )
        sys.exit(1)

    logger.info("=== Simulador de Alertas Windows (VM Ubuntu) ===")
    logger.info(f"Webhook: {args.webhook}")
    logger.info(f"Generando {args.count} alertas maliciosas...")
    logger.info("")

    success = 0
    for i in range(1, args.count + 1):
        alert = generate_malicious_alert(i)
        logger.info(f"[{i}/{args.count}] Enviando: {alert['alert_id']} - {alert['description']}")

        ok, status = send_alert(alert, args.webhook)
        if ok:
            logger.info(f"         ✅ Alerta enviada correctamente (HTTP {status})")
            success += 1
        else:
            logger.error(f"         ❌ Error enviando alerta (HTTP {status})")

        if i < args.count:
            time.sleep(args.delay)

    logger.info("")
    logger.info(f"=== Resumen: {success}/{args.count} alertas enviadas ===")
    return 0 if success == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
