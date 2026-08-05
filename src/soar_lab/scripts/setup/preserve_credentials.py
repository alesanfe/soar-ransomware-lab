#!/usr/bin/env python3
"""
Preserva credenciales de servicios SOAR antes de un make reset.

Este script extrae las credenciales actuales de TheHive, Cortex, Grafana y otros servicios
y las guarda en un archivo JSON para ser restauradas después de un fresh deploy.

Uso:
    python preserve_credentials.py
"""
import json
import os
import requests
import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv('.env.full', override=False)
except ImportError:
    pass

# Configuración
# Guardar directamente en el host para que sobreviva al reset
CREDENTIALS_FILE_HOST = Path('src/soar_lab/infrastructure/artifacts/credentials_backup.json')
CREDENTIALS_FILE = Path('/app/src/soar_lab/infrastructure/artifacts/credentials_backup.json')

# URLs de servicios
THEHIVE_URL = os.environ.get('THEHIVE_URL', 'http://thehive:9000')
CORTEX_URL = os.environ.get('CORTEX_URL', 'http://cortex:9001')
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://grafana:3000')
SHUFFLE_URL = os.environ.get('SHUFFLE_BACKEND_URL', 'http://shuffle-backend:5001')

# Credenciales actuales
THEHIVE_API_KEY = os.environ.get('THEHIVE_API_KEY', '')
CORTEX_API_KEY = os.environ.get('CORTEX_API_KEY', '')
SHUFFLE_API_KEY = os.environ.get('SHUFFLE_DEFAULT_APIKEY', '')
GRAFANA_USER = os.environ.get('GRAFANA_ADMIN_USER', 'admin')
GRAFANA_PASS = os.environ.get('GRAFANA_ADMIN_PASSWORD', '')


def preserve_thehive_credentials():
    """Preserva la API key actual de TheHive."""
    if not THEHIVE_API_KEY:
        print("[WARN] THEHIVE_API_KEY no encontrada en entorno")
        return None

    # Verificar que la key es válida
    try:
        r = requests.get(f'{THEHIVE_URL}/api/user/admin',
                         headers={'Authorization': f'Bearer {THEHIVE_API_KEY}'},
                         timeout=10)
        if r.ok:
            print("[OK] TheHive API key válida")
            return THEHIVE_API_KEY
        else:
            print(f"[WARN] TheHive API key inválida: HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"[WARN] Error verificando TheHive API key: {e}")
        return None


def preserve_cortex_credentials():
    """Preserva la API key actual de Cortex."""
    if not CORTEX_API_KEY:
        print("[WARN] CORTEX_API_KEY no encontrada en entorno")
        return None

    # Verificar que la key es válida
    try:
        r = requests.get(f'{CORTEX_URL}/api/user/admin',
                         headers={'Authorization': f'Bearer {CORTEX_API_KEY}'},
                         timeout=10)
        if r.ok:
            print("[OK] Cortex API key válida")
            return CORTEX_API_KEY
        else:
            print(f"[WARN] Cortex API key inválida: HTTP {r.status_code}")
            return None
    except Exception as e:
        print(f"[WARN] Error verificando Cortex API key: {e}")
        return None


def preserve_shuffle_credentials():
    """Preserva la API key actual de Shuffle."""
    if not SHUFFLE_API_KEY:
        print("[WARN] SHUFFLE_DEFAULT_APIKEY no encontrada en entorno")
        return None

    # Shuffle API key se genera en cada fresh deploy, no tiene sentido preservarla
    # Solo la guardamos si existe
    print("[INFO] Shuffle API key: configurada")
    return SHUFFLE_API_KEY


def preserve_grafana_credentials():
    """Preserva las credenciales de Grafana."""
    # Grafana usa credenciales estáticas, no API key rotativa
    # Solo guardamos las credenciales actuales
    print(f"[INFO] Grafana credenciales: {GRAFANA_USER} / <redacted>")
    return {
        'user': GRAFANA_USER,
        'password': GRAFANA_PASS
    }


def main():
    """Función principal."""
    print("=" * 60)
    print("PRESERVANDO CREDENCIALES DE SERVICIOS SOAR")
    print("=" * 60)

    credentials = {
        'thehive_api_key': preserve_thehive_credentials(),
        'cortex_api_key': preserve_cortex_credentials(),
        'shuffle_api_key': preserve_shuffle_credentials(),
        'grafana': preserve_grafana_credentials(),
        'timestamp': None  # Se añadirá al guardar
    }

    # Guardar en archivo
    from datetime import datetime
    credentials['timestamp'] = datetime.now().isoformat()

    # Crear directorio si no existe
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f, indent=2)

    print(f"[OK] Credenciales guardadas en: {CREDENTIALS_FILE}")
    print(f"[INFO] Copia manual al host requerida: docker cp soar_api:{CREDENTIALS_FILE} {CREDENTIALS_FILE_HOST}")

    print("=" * 60)
    print("PRESERVACIÓN COMPLETADA")
    print("=" * 60)


if __name__ == '__main__':
    main()
