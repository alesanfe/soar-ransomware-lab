# FASE 2: Propuesta de Reorganización Conservadora

**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Análisis de Dependencias de Rutas

### Revisión de Makefile.win

El Makefile.win usa extensivamente la ruta `artifacts/`:

```makefile
export ARTIFACTS_DIR := $(CURDIR)/artifacts
```

**Dependencias identificadas**:

- Creación de directorios: `artifacts/data/elasticsearch`, `artifacts/data/thehive/files`, etc.
- Backups: `artifacts/backups/`
- Logs: `artifacts/logs/`
- Results: `artifacts/results/`
- Coverage: `artifacts/coverage/`
- Scripts de setup usan `artifacts/` como ruta base

### Revisión de Docker Compose

Los archivos docker-compose.yml también usan `artifacts/` para volúmenes y montajes.

---

## Propuesta de Reorganización Conservadora

### Principio: NO MOVER `artifacts/`

**Motivo**:

- `artifacts/` está fuertemente integrado en Makefile.win
- `artifacts/` está fuertemente integrado en docker-compose.yml
- Mover `artifacts/` a `runtime/` rompería múltiples scripts y configuraciones
- El objetivo es una reorganización CONSERVADORA que respete la estructura existente

### Propuesta: Mantener Estructura, Ajustar .gitignore

**Estructura final propuesta**:

```
soar-ransomware-lab/
├── apps/              (NO CAMBIAR)
├── src/               (NO CAMBIAR)
├── tests/             (NO CAMBIAR)
├── infra/             (NO CAMBIAR)
├── docs/              (NO CAMBIAR)
├── schemas/           (NO CAMBIAR)
├── simulator/         (NO CAMBIAR)
├── artifacts/         (NO CAMBIAR - mantener estructura existente)
│   ├── data/          (PROPONER IGNORAR EN .gitignore)
│   ├── logs/          (YA IGNORADO EN .gitignore)
│   ├── results/       (YA IGNORADO EN .gitignore)
│   ├── coverage/      (YA IGNORADO EN .gitignore)
│   ├── temp/          (YA IGNORADO EN .gitignore)
│   └── backups/       (YA IGNORADO EN .gitignore)
└── archivos raíz      (NO CAMBIAR)
```

---

## Acciones Específicas Propuestas

### 1. NO MOVER - Mantener estructura existente

**Carpetas principales**:

- `apps/` - NO TOCAR
- `src/` - NO TOCAR
- `tests/` - NO TOCAR
- `infra/` - NO TOCAR
- `docs/` - NO TOCAR
- `schemas/` - NO TOCAR
- `simulator/` - NO TOCAR
- `artifacts/` - NO TOCAR (estructura existente)

**Archivos raíz**:

- `README.md` - NO TOCAR
- `LICENSE` - NO TOCAR
- `Makefile` - NO TOCAR
- `Makefile.win` - NO TOCAR
- `pyproject.toml` - NO TOCAR
- `pytest.ini` - NO TOCAR
- `requirements-test.txt` - NO TOCAR
- `docker-compose*.yml` - NO TOCAR
- `Vagrantfile` - NO TOCAR
- `.gitignore` - NO TOCAR (solo actualizar al final)

### 2. BORRAR_SEGURO - Directorio duplicado

**Acción**: Eliminar `infra/infra/`

**Motivo**: Directorio duplicado de `infra/docker/nginx/`

**Comando**:

```bash
powershell -Command "if (Test-Path infra\infra) { Remove-Item -Recurse -Force infra\infra }"
```

**Riesgo**: Bajo - es un duplicado

### 3. PROPONER_IGNORAR_AL_FINAL - Datos runtime

**Acción**: Agregar `artifacts/data/` a .gitignore (al final)

**Motivo**: 4255 items de datos runtime (Elasticsearch, Wazuh, MISP, Grafana)

**Patrón a agregar**:

```gitignore
# Runtime data
artifacts/data/
```

**Riesgo**: Bajo - datos regenerables por servicios

### 4. REVISAR_MANUALMENTE - Archivos específicos

**Archivos a revisar manualmente**:

- `src/soar_lab/infrastructure/artifacts/` (credentials_backup.json, webhook_info.json)
- `infra/docker/nginx/ssl/` (certificados SSL)
- `infra/docker/compose/logging/*.json` (dashboards Grafana)
- `docs/testing/*.md` (informes de auditoría)
- `.env.full` (variables de entorno con secretos)

**Criterio de revisión**:

- Si son generados automáticamente → PROPONER_IGNORAR_AL_FINAL
- Si son configuración base → CONSERVAR_EN_GIT
- Si son informes → PROPONER_IGNORAR_AL_FINAL

---

## Resumen de Cambios Propuestos

### Cambios Estructurales

- **NINGÚN cambio estructural** en carpetas principales
- **MANTENER** `artifacts/` en su ubicación actual
- **ELIMINAR** solo `infra/infra/` (directorio duplicado)

### Cambios en .gitignore (propuesto al final)

- Agregar `artifacts/data/` (datos runtime)
- Agregar `src/soar_lab/infrastructure/artifacts/` (si se confirma que son generados)
- Agregar `infra/vagrant/.vagrant/` (estado Vagrant)
- Agregar `docs/testing/*.md` (informes de auditoría generados)
- Revisar certificados SSL y dashboards Grafana

---

## Justificación de la Propuesta Conservadora

### 1. Respeto a la Estructura Existente

- El proyecto tiene una estructura bien organizada
- `artifacts/` está integrado en Makefile, Docker Compose y scripts
- Mover `artifacts/` rompería múltiples dependencias

### 2. Minimización de Riesgos

- No mover carpetas principales reduce riesgo de rotura
- No cambiar rutas en Makefile o Docker Compose
- Solo ajustar .gitignore para ignorar datos runtime

### 3. Enfoque en Limpieza de Datos Runtime

- El problema principal son los 4255 items en `artifacts/data/`
- La solución es ignorar estos datos en .gitignore
- No requiere cambios estructurales

### 4. Alineación con Objetivos del Usuario

- El usuario solicitó reorganización CONSERVADORA
- El usuario solicitó respetar la estructura existente
- El usuario solicitó NO rediseñar el proyecto

---

## Conclusión de FASE 2

**Propuesta final**:

1. **NO mover** `artifacts/` a `runtime/`
2. **MANTENER** estructura existente de carpetas principales
3. **ELIMINAR** solo `infra/infra/` (directorio duplicado)
4. **PROPONER** ajustes a .gitignore al final (no ahora)
5. **REVISAR** manualmente archivos específicos (certificados, dashboards, informes)

Esta propuesta es conservadora, minimiza riesgos, y se alinea con los objetivos del usuario de respetar la estructura
existente.
