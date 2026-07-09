#!/usr/bin/env python3
"""
Simulador de alertas SIEM - Reemplazo para VM Windows
Genera alertas de ransomware simuladas y las envía al webhook de Shuffle
"""
import argparse
import json
import random
import requests
import sys
import time
from datetime import datetime

# Webhook URL - usar IP del contenedor shuffle_backend (obtener con: docker exec soar_shuffle_backend hostname -i)
# El nombre DNS 'soar_shuffle_backend' solo funciona dentro de los contenedores Docker
# Para ejecutar desde la VM host, usar la IP: 10.100.0.12
SHUFFLE_WEBHOOK = "http://soar_shuffle_backend:5001/api/v1/hooks/webhook_506f8df3-afc6-598d-9179-4bb8c4c99bd1"


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
    parser.add_argument("--webhook", type=str, default=SHUFFLE_WEBHOOK, help="URL del webhook")
    args = parser.parse_args()

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
