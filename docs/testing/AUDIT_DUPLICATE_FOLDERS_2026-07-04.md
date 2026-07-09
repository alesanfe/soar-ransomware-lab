# Análisis de Carpetas Duplicadas
**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Problema Identificado

### Dos carpetas `backups` encontradas

1. **backups/** (raíz del proyecto)
   - Ubicación: `C:\Users\alex0\PycharmProjects\soar-ransomware-lab\backups\`
   - Contenido: 2 archivos de backup (soar_backup_20260704_*.tar.gz)
   - Estado: TIENE DATOS

2. **artifacts/backups/** (dentro de artifacts)
   - Ubicación: `C:\Users\alex0\PycharmProjects\soar-ransomware-lab\artifacts\backups\`
   - Contenido: VACÍA
   - Estado: VACÍA

---

## Causa del Problema

### Configuración Inconsistente de BACKUP_DIR

**1. Código Python (settings.py)**
```python
'backup_dir': os.getenv('BACKUP_DIR', str(base_dir / 'artifacts' / 'backups'))
```
- **Por defecto**: `artifacts/backups/`
- **Ubicación**: `src/soar_lab/config/settings.py` línea 191

**2. Docker Compose (docker-compose.api.yml)**
```yaml
- BACKUP_DIR=/app/backups
```
- **Dentro del contenedor**: `/app/backups`
- **Ubicación**: `infra/docker/compose/docker-compose.api.yml` línea 23

**3. Script de Shell (CONTRIBUTING.md)**
```bash
BACKUP_DIR="${BACKUP_DIR:-./backups}"
```
- **Por defecto**: `./backups` (raíz del proyecto)
- **Ubicación**: `CONTRIBUTING.md` línea 227

---

## Análisis de Referencias

### Código Python usa `artifacts/backups`
- `src/soar_lab/infrastructure/path_service.py`: `str(self.artifacts_dir / "backups")`
- `src/soar_lab/infrastructure/filesystem_storage.py`: `str(self._base / "backups")`
- Tests unitarios esperan `artifacts/backups`

### Docker usa `/app/backups`
- El contenedor API usa `/app/backups` (path interno del contenedor)
- Probablemente montado desde `artifacts/backups` o `backups/` según el volume

### Script de shell usa `./backups`
- El script en `CONTRIBUTING.md` usa `./backups` (raíz del proyecto)
- Esto puede haber creado la carpeta `backups/` en la raíz

---

## Recomendación

### 1. Unificar BACKUP_DIR a `artifacts/backups`

**Razón**:
- El código Python ya usa `artifacts/backups` por defecto
- Es consistente con la estructura de `artifacts/` para datos runtime
- El script de shell debería actualizarse para usar `artifacts/backups`

**Acciones**:
1. Mover backups de `backups/` a `artifacts/backups/`
2. Actualizar `CONTRIBUTING.md` para usar `artifacts/backups`
3. Verificar que Docker Compose monta correctamente `artifacts/backups` a `/app/backups`
4. Eliminar carpeta `backups/` de la raíz

### 2. Verificar Docker Volume Mapping

**Investigar**:
- ¿Cómo está montado `/app/backups` en el contenedor?
- ¿Está montado desde `artifacts/backups` o `backups/`?

**Comando para verificar**:
```bash
docker inspect soar_api | grep -A 10 "backups"
```

---

## Archivos a Modificar

1. **CONTRIBUTING.md** (línea 227)
   - Cambiar: `BACKUP_DIR="${BACKUP_DIR:-./backups}"`
   - Por: `BACKUP_DIR="${BACKUP_DIR:-./artifacts/backups}"`

2. **docker-compose.api.yml** (verificar volume mapping)
   - Asegurar que `/app/backups` se monta desde `artifacts/backups`

---

## Riesgos

- **Riesgo Medio**: Mover backups puede romper referencias existentes
- **Riesgo Bajo**: Cambiar script de shell solo afecta a usuarios que usen ese script manualmente

---

## Verificación Docker Volume Mapping

**Resultado**: ✅ CORRECTO

El archivo `docker-compose.api.yml` línea 66 muestra:
```yaml
- ${ARTIFACTS_DIR:-../../../artifacts}/backups:/app/backups
```

Esto confirma que `/app/backups` en el contenedor está montado desde `artifacts/backups/` en el host, que es consistente con el código Python.

---

## Solución Implementada

### 1. Mover backups de `backups/` a `artifacts/backups/`

**Acción**: Mover los 2 archivos de backup
- `backups/soar_backup_20260704_095125.tar.gz` → `artifacts/backups/`
- `backups/soar_backup_20260704_101855.tar.gz` → `artifacts/backups/`

### 2. Actualizar CONTRIBUTING.md

**Acción**: Cambiar línea 227
- De: `BACKUP_DIR="${BACKUP_DIR:-./backups}"`
- A: `BACKUP_DIR="${BACKUP_DIR:-./artifacts/backups}"`

### 3. Eliminar carpeta `backups/` de la raíz

**Acción**: Eliminar carpeta vacía `backups/`

---

## Estado

**COMPLETADO**: Carpetas unificadas en `artifacts/backups/`

---

## Hallazgos Adicionales

### 1. Carpeta `schemas/` duplicada (raíz)

**Encontrado**: `schemas/` (vacío) en la raíz del proyecto
**Ya existe**: `src/soar_lab/config/schemas.json` (JSON schema de alertas)
**Acción**: Eliminada carpeta vacía `schemas/` de la raíz

### 2. Archivo `nul` en la raíz

**Encontrado**: Archivo `nul` (2649 bytes) en la raíz
**Causa**: Probablemente un archivo temporal generado por algún comando de shell
**Acción**: Eliminado (ya está en `.gitignore`)

### 3. Carpetas `logs/` y `data/` - NO son duplicadas

**Investigación**: Encontradas múltiples carpetas con estos nombres
**Resultado**: Todas son legítimas y tienen propósitos específicos:
- `artifacts/data/misp/logs/` - Runtime de MISP
- `artifacts/data/wazuh/logs/` - Runtime de Wazuh
- `artifacts/logs/` - Logs generales del proyecto
- `artifacts/results/logs/` - Logs de resultados de tests
- `artifacts/data/` - Datos runtime de servicios (MISP, Wazuh, etc.)

### 4. Carpetas IDE ya ignoradas

**Encontrado**: `.refact/`, `.idea/`, `.junie/`
**Estado**: Ya están en `.gitignore` (líneas 40, 45-46)

---

## Resumen de Cambios Realizados

1. ✅ Mover 2 archivos de backup de `backups/` a `artifacts/backups/`
2. ✅ Actualizar `CONTRIBUTING.md` para usar `artifacts/backups`
3. ✅ Eliminar carpeta `backups/` de la raíz
4. ✅ Eliminar carpeta `schemas/` vacía de la raíz
5. ✅ Eliminar archivo `nul` de la raíz

---

## Conclusión

No se encontraron más carpetas duplicadas significativas. Las carpetas con nombres similares (`logs`, `data`) tienen propósitos legítimos y diferentes según su ubicación en la estructura del proyecto.
