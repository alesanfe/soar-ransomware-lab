# Backup y restauración del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Arquitectura del backup](#2-arquitectura-del-backup)
- [3. Crear un backup](#3-crear-un-backup)
- [4. Listar backups](#4-listar-backups)
- [5. Restaurar un backup](#5-restaurar-un-backup)
- [6. Metadatos y exclusión de archivos](#6-metadatos-y-exclusión-de-archivos)
- [7. Backups de volúmenes Docker](#7-backups-de-volúmenes-docker)
- [8. Pruebas](#8-pruebas)
- [9. Referencias](#9-referencias)

---

## 1. Resumen

La funcionalidad de backup crea un archivo comprimido `.tar.gz` del directorio base del proyecto, excluyendo artefactos generados, contenedores y dependencias. Se expone como endpoint REST y se implementa con el adaptador `TarBackupDriver`.

---

## 2. Arquitectura del backup

| Componente | Archivo | Responsabilidad |
|------------|---------|-----------------|
| Endpoint REST | `src/soar_lab/interfaces/api/main.py` | Recibe peticiones en `/backup/create`, `/backup/list` y `/backup/restore` |
| Servicio de aplicación | `src/soar_lab/application/use_cases/backup_service.py` | Orquesta creación, listado y restauración |
| Adaptador de infraestructura | `src/soar_lab/infrastructure/tar_backup_driver.py` | Ejecuta `tar`, encapsula los flags y valida exclusiones |
| Almacenamiento | `src/soar_lab/infrastructure/filesystem_storage.py` | Persiste metadatos (`backup_metadata.json`), resuelve rutas (`get_backup_directory`) y gestiona listado de backups |

---

## 3. Crear un backup

### API

```bash
curl -k -X POST https://soar.local/api/backup/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_name": "manual-backup"}'
```

Respuesta:

```json
{
  "backup_name": "soar_backup_20260101_120000.tar.gz",
  "status": "success",
  "message": "Backup created successfully"
}
```

### CLI (desde el contenedor o entorno Python)

```bash
python -m src.soar_lab.interfaces.api.cli api
# o directamente con la API en http://localhost:8000
```

El backup se guarda en el directorio devuelto por `storage.get_backup_directory()` (por defecto `artifacts/backups/` dentro del proyecto).

---

## 4. Listar backups

```bash
curl -k -X GET https://soar.local/api/backup/list \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```json
{
  "backups": [
    {
      "name": "soar_backup_20260101_120000.tar.gz",
      "size": "12.34 MB",
      "date": "2026-01-01 12:00"
    }
  ]
}
```

---

## 5. Restaurar un backup

```bash
curl -k -X POST https://soar.local/api/backup/restore \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_name": "soar_backup_20260101_120000.tar.gz"}'
```

Respuesta:

```json
{
  "backup_name": "soar_backup_20260101_120000.tar.gz",
  "status": "success",
  "message": "Backup soar_backup_20260101_120000.tar.gz restored successfully"
}
```

> **Atención:** La restauración extrae el contenido sobre el directorio base del proyecto (`tar -xzf ... --skip-old-files`). No sobrescribe archivos más recientes por defecto, pero sí debe ejecutarse con precaución para evitar dejar el stack en un estado incoherente.

---

## 6. Metadatos y exclusión de archivos

### Metadatos

Cada backup registra:

- `created_by`: usuario que solicitó el backup
- `created_at`: timestamp ISO
- `size`: tamaño en bytes

Los metadatos se almacenan en `backup_metadata.json` junto al archivo `.tar.gz`.

### Exclusiones

`TarBackupDriver` excluye automáticamente:

```text
__pycache__, *.pyc, .git, node_modules, htmlcov, .pytest_cache,
coverage.xml, .coverage, artifacts, *.tar.gz, venv, env, .env,
.mypy_cache, .tox, dist, build, .eggs, *.egg-info
```

Esto evita que el backup contenga contenedores, cachés, secretos locales o archivos de cobertura.

---

## 7. Backups de volúmenes Docker

El backup a nivel de aplicación no incluye volúmenes Docker. Para proteger datos persistentes (Elasticsearch, MISP DB, Grafana, TheHive, Cortex, etc.), realiza un backup de volúmenes adicional:

```bash
# Listar volúmenes del proyecto
docker volume ls | grep soar

# Backup de un volumen específico (ejemplo: datos de Elasticsearch)
docker run --rm -v soar_es_data:/data -v $(pwd)/backups:/backup alpine \
  tar -czf /backup/soar_es_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Restaurar el volumen
docker run --rm -v soar_es_data:/data -v $(pwd)/backups:/backup alpine \
  tar -xzf /backup/soar_es_data_20260101_120000.tar.gz -C /data
```

> En Windows con Docker Desktop, los volúmenes que usan bind mounts (por ejemplo `misp_db` en versiones antiguas) pueden dar `Permission denied`. La solución es usar volúmenes Docker normales (ver [logging stack notes](../architecture/docker_architecture.md)).

---

## 8. Pruebas

El suite de tests incluye pruebas de integración del driver y del servicio:

```bash
python -m pytest tests/integration/test_tar_backup_driver.py -v
python -m pytest tests/unit/infrastructure/test_tar_backup_driver.py -v
```

---

## 9. Referencias

- [src/soar_lab/application/use_cases/backup_service.py](../../src/soar_lab/application/use_cases/backup_service.py)
- [src/soar_lab/infrastructure/tar_backup_driver.py](../../src/soar_lab/infrastructure/tar_backup_driver.py)
- [src/soar_lab/interfaces/api/main.py](../../src/soar_lab/interfaces/api/main.py)
