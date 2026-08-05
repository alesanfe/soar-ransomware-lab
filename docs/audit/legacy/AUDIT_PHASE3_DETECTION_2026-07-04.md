# FASE 3: Detección de Archivos Candidatos a Borrado

**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Dry-Run de Detección

### Cachés de Python

**Directorios __pycache__ encontrados**: 31

```
src/soar_lab/__pycache__/
src/soar_lab/api/__pycache__/
src/soar_lab/config/__pycache__/
src/soar_lab/data/__pycache__/
src/soar_lab/domain/__pycache__/
src/soar_lab/domain/ports/__pycache__/
src/soar_lab/infrastructure/__pycache__/
src/soar_lab/infrastructure/persistence/__pycache__/
src/soar_lab/infrastructure/setup/__pycache__/
src/soar_lab/integrations/__pycache__/
src/soar_lab/services/__pycache__/
src/soar_lab/validation/__pycache__/
tests/__pycache__/
tests/atomic/__pycache__/
tests/e2e/TC-00/__pycache__/
tests/e2e/TC-01/__pycache__/
tests/e2e/TC-02/__pycache__/
tests/e2e/TC-03/__pycache__/
tests/e2e/TC-05/__pycache__/
tests/e2e/TC-06/__pycache__/
tests/e2e/TC-07/__pycache__/
tests/e2e/TC-08/__pycache__/
tests/e2e/TC-09/__pycache__/
tests/e2e/TC-KPI-01/__pycache__/
tests/e2e/TC-KPI-02/__pycache__/
tests/e2e/TC-KPI-03/__pycache__/
tests/e2e/__pycache__/
tests/integration/__pycache__/
tests/performance/__pycache__/
tests/security/__pycache__/
tests/unit/__pycache__/
```

**Archivos .pyc encontrados**: 221 (comprobación exhaustiva)

**Clasificación**: BORRAR_SEGURO
**Motivo**: Cachés de Python generados automáticamente, regenerables
**Riesgo**: Ninguno

### Cachés de Testing

**Directorios .pytest_cache**: 0 encontrados
**Directorios .mypy_cache**: 0 encontrados
**Directorios .ruff_cache**: 0 encontrados

**Clasificación**: No encontrados (ya limpios o ya ignorados)

### Archivos Temporales

**Archivos .tmp**: 0 encontrados
**Archivos .bak**: 0 encontrados
**Archivos .swp**: 0 encontrados
**Archivos .swo**: 0 encontrados

**Clasificación**: No encontrados (ya limpios o ya ignorados)

### Datos Runtime

**Directorio artifacts/data/**: 4255 items

- Elasticsearch: 1347 items
- Wazuh: 949 items
- MISP: 1452 items
- Grafana: 506 items
- Kibana: 1 item

**Clasificación**: PROPONER_IGNORAR_AL_FINAL
**Motivo**: Datos runtime de servicios, regenerables
**Riesgo**: Bajo (datos regenerables por servicios)

### Directorio Duplicado

**Directorio infra/infra/**: 2 items

- docker/nginx/ssl/

**Clasificación**: BORRAR_SEGURO
**Motivo**: Directorio duplicado de infra/docker/nginx/
**Riesgo**: Bajo (es un duplicado)

---

## Resumen de Detección

### BORRAR_SEGURO (Inmediato)

- 31 directorios __pycache__
- 221 archivos .pyc (comprobación exhaustiva)
- 1 directorio infra/infra/ (duplicado)

### PROPONER_IGNORAR_AL_FINAL

- artifacts/data/ (4255 items de datos runtime)

### NO ENCONTRADOS (Ya limpios o ignorados)

- .pytest_cache
- .mypy_cache
- .ruff_cache
- .tmp
- .bak
- .swp
- .swo

---

## Comandos de Limpieza Propuestos (FASE 4)

### Cachés de Python

```bash
# Windows PowerShell
powershell -Command "Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force"
powershell -Command "Get-ChildItem -Path . -Recurse -Filter '*.pyc' | Remove-Item -Force"
```

### Directorio Duplicado

```bash
# Windows PowerShell
powershell -Command "if (Test-Path infra\infra) { Remove-Item -Recurse -Force infra\infra }"
```

### Datos Runtime (NO BORRAR - Propuesto para .gitignore)

```bash
# NO EJECUTAR - Solo proponer ignorar en .gitignore
# artifacts/data/ debe ignorarse, no borrarse
```

---

## Conclusión de FASE 3

**Archivos candidatos a borrado seguro**:

- 31 directorios __pycache__
- 221 archivos .pyc (comprobación exhaustiva)
- 1 directorio infra/infra/ (duplicado)

**Archivos a ignorar en .gitignore (no borrar)**:

- artifacts/data/ (4255 items de datos runtime)

**Estado**: Listo para FASE 4 (Limpieza segura)
