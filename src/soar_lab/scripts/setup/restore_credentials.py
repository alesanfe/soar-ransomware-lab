#!/usr/bin/env python3
"""
Restaura credenciales de servicios SOAR después de un make up.

Este script lee el archivo JSON generado por preserve_credentials.py y
restaura las credenciales en los servicios correspondientes.

Uso:
    python restore_credentials.py
"""
import base64
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
# Buscar en el host para que sobreviva al reset
CREDENTIALS_FILE_HOST = Path('src/soar_lab/infrastructure/artifacts/credentials_backup.json')
CREDENTIALS_FILE = Path('/app/src/soar_lab/infrastructure/artifacts/credentials_backup.json')

# URLs de servicios
THEHIVE_URL = os.environ.get('THEHIVE_URL', 'http://thehive:9000')
CORTEX_URL = os.environ.get('CORTEX_URL', 'http://cortex:9001')
GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://grafana:3000')

# Credenciales para reconfiguración
THEHIVE_ADMIN_USER = os.environ.get('THEHIVE_ADMIN_USER', 'admin')
THEHIVE_ADMIN_PASS = os.environ.get('THEHIVE_ADMIN_PASSWORD', '')
CORTEX_ADMIN_USER = os.environ.get('CORTEX_ADMIN_USER', 'admin')
CORTEX_ADMIN_PASS = os.environ.get('CORTEX_ADMIN_PASSWORD', '')

if not THEHIVE_ADMIN_PASS:
    print('[ERROR] Falta THEHIVE_ADMIN_PASSWORD', file=sys.stderr)
    sys.exit(1)
if not CORTEX_ADMIN_PASS:
    print('[ERROR] Falta CORTEX_ADMIN_PASSWORD', file=sys.stderr)
    sys.exit(1)


def load_credentials():
    """Carga las credenciales preservadas."""
    # Intentar cargar del contenedor primero
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)

    # Intentar cargar del host
    if CREDENTIALS_FILE_HOST.exists():
        with open(CREDENTIALS_FILE_HOST) as f:
            return json.load(f)

    print("[ERROR] No se encontró archivo de credenciales preservadas")
    print(f"  Buscando en: {CREDENTIALS_FILE}")
    print(f"  Buscando en: {CREDENTIALS_FILE_HOST}")
    return None


def restore_thehive_credentials(api_key):
    """Restaura la API key de TheHive actualizando .env.full."""
    if not api_key:
        print("[SKIP] TheHive API key no preservada")
        return False

    # Verificar si la key preservada es válida
    try:
        r = requests.get(f'{THEHIVE_URL}/api/user/admin',
                         headers={'Authorization': f'Bearer {api_key}'},
                         timeout=10)
        if r.ok:
            print("[OK] TheHive API key preservada aún válida")
        else:
            print(f"[WARN] TheHive API key preservada inválida, generando nueva...")
            # Generar nueva key
            auth = base64.b64encode(f'{THEHIVE_ADMIN_USER}:{THEHIVE_ADMIN_PASS}'.encode()).decode()
            r = requests.post(f'{THEHIVE_URL}/api/user/{THEHIVE_ADMIN_USER}/key/renew',
                              data='{}',
                              headers={'Authorization': f'Basic {auth}',
                                       'Content-Type': 'application/json'},
                              timeout=10)
            if r.ok:
                api_key = r.text.strip().strip('"')
                print("[OK] Nueva TheHive API key generada")
            else:
                print(f"[ERROR] No se pudo generar nueva TheHive API key: HTTP {r.status_code}")
                return False
    except Exception as e:
        print(f"[WARN] Error verificando TheHive API key: {e}")
        return False

    # Actualizar .env.full
    try:
        env_file = Path('.env.full')
        if not env_file.exists():
            env_file = Path('/app/.env.full')

        if env_file.exists():
            content = env_file.read_text()
            import re
            if re.search(r'^THEHIVE_API_KEY=', content, re.MULTILINE):
                content = re.sub(r'^THEHIVE_API_KEY=.*$', f'THEHIVE_API_KEY={api_key}', content, flags=re.MULTILINE)
            else:
                content += f'\nTHEHIVE_API_KEY={api_key}'
            env_file.write_text(content)
            print(f"[OK] THEHIVE_API_KEY actualizada en .env.full")
            return True
        else:
            print(f"[WARN] No se encontró .env.full para actualizar")
            return False
    except Exception as e:
        print(f"[ERROR] Error actualizando .env.full: {e}")
        return False


def restore_cortex_credentials(api_key):
    """Restaura la API key de Cortex actualizando .env.full."""
    if not api_key:
        print("[SKIP] Cortex API key no preservada")
        return False

    # Cortex API key se regenera automáticamente en make up
    # Solo verificamos que existe
    print(f"[INFO] Cortex API key preservada: {api_key[:8]}...")
    print(f"[INFO] Cortex API key se regenera automáticamente en make up")

    # Actualizar .env.full con la key preservada
    try:
        env_file = Path('.env.full')
        if not env_file.exists():
            env_file = Path('/app/.env.full')

        if env_file.exists():
            content = env_file.read_text()
            import re
            if re.search(r'^CORTEX_API_KEY=', content, re.MULTILINE):
                content = re.sub(r'^CORTEX_API_KEY=.*$', f'CORTEX_API_KEY={api_key}', content, flags=re.MULTILINE)
            else:
                content += f'\nCORTEX_API_KEY={api_key}'
            env_file.write_text(content)
            print(f"[OK] CORTEX_API_KEY actualizada en .env.full")
            return True
        else:
            print(f"[WARN] No se encontró .env.full para actualizar")
            return False
    except Exception as e:
        print(f"[ERROR] Error actualizando .env.full: {e}")
        return False


def restore_shuffle_credentials(api_key):
    """Restaura la API key de Shuffle."""
    if not api_key:
        print("[SKIP] Shuffle API key no preservada")
        return False

    # Shuffle API key se genera en cada fresh deploy
    # No tiene sentido restaurarla, solo informamos
    print(f"[INFO] Shuffle API key preservada: {api_key[:8]}...")
    print(f"[INFO] Shuffle API key se genera automáticamente en fresh deploy")
    return True


def restore_grafana_credentials(grafana_creds):
    """Restaura las credenciales de Grafana."""
    if not grafana_creds:
        print("[SKIP] Grafana credenciales no preservadas")
        return False

    user = grafana_creds.get('user', 'admin')
    password = grafana_creds.get('password', os.environ.get('GRAFANA_ADMIN_PASSWORD', ''))

    print(f"[INFO] Grafana credenciales preservadas: {user} / {password[:4]}...")
    print(f"[INFO] Grafana usa credenciales estáticas, no requiere restauración")
    return True


def main():
    """Función principal."""
    print("=" * 60)
    print("RESTAURANDO CREDENCIALES DE SERVICIOS SOAR")
    print("=" * 60)

    credentials = load_credentials()
    if not credentials:
        print("[ERROR] No se pudieron cargar credenciales preservadas")
        sys.exit(1)

    print(f"[INFO] Credenciales preservadas el: {credentials.get('timestamp', 'desconocido')}")
    print()

    # Restaurar cada servicio
    results = {
        'thehive': restore_thehive_credentials(credentials.get('thehive_api_key')),
        'cortex': restore_cortex_credentials(credentials.get('cortex_api_key')),
        'shuffle': restore_shuffle_credentials(credentials.get('shuffle_api_key')),
        'grafana': restore_grafana_credentials(credentials.get('grafana'))
    }

    print()
    print("=" * 60)
    print("RESULTADO DE RESTAURACIÓN")
    print("=" * 60)
    for service, success in results.items():
        status = "✅ OK" if success else "❌ FAIL"
        print(f"  {service}: {status}")

    print("=" * 60)
    print("RESTAURACIÓN COMPLETADA")
    print("=" * 60)


if __name__ == '__main__':
    main()
