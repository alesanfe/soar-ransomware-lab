#!/usr/bin/env python3
"""
Simulador de alertas SIEM - Reemplazo para VM Windows
Genera alertas de ransomware simuladas y las envía al webhook de Shuffle
"""
import argparse
import json
import os
import random
import requests
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

def _inside_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/app").exists()


def _get_default_webhook() -> str:
    """Resuelve la URL del webhook por defecto desde env, .env.full o webhook_info.json."""
    # 1. Variables de entorno explícitas
    env_url = os.environ.get("SHUFFLE_WEBHOOK_URL")
    if env_url:
        return env_url

    token = os.environ.get("SIEM_WEBHOOK_TOKEN")
    if token:
        return f"http://soar_shuffle_backend:5001/api/v1/hooks/{token}"

    # 2. Buscar webhook_info.json generado por init_shuffle_webhook.py
    repo_root = Path(__file__).resolve().parents[3]  # src/soar_lab/simulator -> repo root
    candidates = [
        Path("/app/webhook_info.json"),
        repo_root / "artifacts" / "results" / "webhook_info.json",
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

    # 3. No se usa URL fija heredada; el webhook debe provenir de init_shuffle_webhook.py
    return None


def generate_malicious_alert(alert_id):
    """Genera una alerta de ransomware maliciosa"""
    ransomware_families = ["WannaCry", "Locky", "Ryuk", "Maze", "REvil"]
    ips = ["185.220.101.42", "198.51.100.15", "203.0.113.88"]

    return {
        "alert_id": f"SIM-WIN-{alert_id:04d}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "severity": "critical",
        "classification": "malicious",
        "src_ip": random.choice(ips),
        "dst_ip": "192.168.56.10",
        "description": f"Ransomware {random.choice(ransomware_families)} detectado",
        "file_hash": "d41d8cd98f00b204e9800998ecf8427e",
        "process_name": "encryptor.exe",
        "host": "victima-windows-sim",
        "source": "windows_defender_sim",
        "MITRE": "T1486"
    }


def send_alert(alert, webhook_url):
    """Envía alerta al webhook de Shuffle"""
    try:
        resp = requests.post(
            webhook_url,
            json=alert,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        return resp.status_code == 200, resp.status_code
    except Exception as e:
        print(f"Error enviando alerta: {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5, help="Número de alertas")
    parser.add_argument("--delay", type=float, default=2, help="Delay entre alertas (seg)")
    default_webhook = _get_default_webhook()
    parser.add_argument("--webhook", type=str, default=default_webhook, help="URL del webhook")
    args = parser.parse_args()

    if not args.webhook:
        print("ERROR: No se encontró SHUFFLE_WEBHOOK_URL, SIEM_WEBHOOK_TOKEN ni webhook_info.json.")
        print("Ejecuta primero init_shuffle_webhook.py (make init-webhook) y vuelve a intentarlo.")
        sys.exit(1)

    print(f"=== Simulador de Alertas Windows (VM Ubuntu) ===")
    print(f"Webhook: {args.webhook}")
    print(f"Generando {args.count} alertas maliciosas...")
    print()

    success = 0
    for i in range(1, args.count + 1):
        alert = generate_malicious_alert(i)
        print(f"[{i}/{args.count}] Enviando: {alert['alert_id']} - {alert['description']}")

        ok, status = send_alert(alert, args.webhook)
        if ok:
            print(f"         ✅ Alerta enviada correctamente (HTTP {status})")
            success += 1
        else:
            print(f"         ❌ Error enviando alerta (HTTP {status})")

        if i < args.count:
            time.sleep(args.delay)

    print()
    print(f"=== Resumen: {success}/{args.count} alertas enviadas ===")
    return 0 if success == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
