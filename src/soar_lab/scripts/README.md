# Scripts del SOAR Ransomware Lab

Esta carpeta contiene scripts de inicialización, depuración y mantenimiento.

- `setup/` — Generación de certificados (`gen_certs.sh`), secretos (`generate_secrets.py`), inicialización de Shuffle (`init_shuffle_webhook.py`) y TheHive (`init_thehive.py`), seed de Wazuh, setup de Grafana KPIs.
- `debug/` — Utilidades de diagnóstico (health checks, validación de credenciales, verificación de workflows).
- `maintenance/` — Limpieza de volúmenes, backups, reset de credenciales y scripts de recuperación.

Ver la guía de operaciones en `docs/operations/infrastructure_guide.md` y `docs/operations/configuration_manual.md`.
