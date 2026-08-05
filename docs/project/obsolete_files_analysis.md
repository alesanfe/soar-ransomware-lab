# Análisis de archivos obsoletos y artefactos temporales

## Alcance

Este documento registra el análisis realizado en la **FASE 48** del proyecto `documentation_remediation_tasks.md`, relativo a archivos no trackeados, scripts temporales de remediación, artefactos de ejecución y otros elementos que no deben versionarse.

## Estado del repositorio

- `git status` muestra **~600 entradas** entre eliminaciones, modificaciones y archivos no trackeados.
- La mayoría de los archivos no trackeados son **scripts de ayuda de remediación**, **artefactos de pruebas**, **datos de runtime** y **documentación generada**.

## Clasificación de archivos encontrados

### 1. Scripts temporales de remediación (riesgo: bajo, acción: ignorar)

Ubicados en la raíz del repositorio. Generados durante sesiones de remediación de documentación y código. No son parte del producto final.

Ejemplos:

- `_append_*.py`
- `_capture_*.py`
- `_check_*.py`
- `_compile_*.py`
- `_count_*.py`
- `_create_*.py`
- `_deduplicate_*.py`
- `_doc_remediation.py`
- `_extend_*.py`
- `_extract_*.py`
- `_final_validation*.py`
- `_fix_*.py`
- `_generate_*.py`
- `_inspect_*.py.txt`
- `_parse_*.py`
- `_process_*.py`
- `_repair_*.py`
- `_run_*.py`
- `_sanitize_docs_secrets.py` (script de limpieza de secretos en docs; se mantiene explícitamente en Git)
- `_sync_*.py`
- `_test_*.py`
- `_update_*.py`
- `_validate_*.py`
- `_utf8_test.txt`
- `__fix_init_webhook.py`
- `check_null_bytes.py`
- `compile_test.py`
- `debug_import.py`
- `fix_broken_imports.py`
- `scan_doc_inconsistencies.py`
- `tmp_*.py`
- `tmp_*.md`

**Decisión:** Se añaden patrones a `.gitignore` para que no aparezcan en futuros `git status`.

### 2. Artefactos de pruebas y cobertura (riesgo: bajo, acción: ignorar)

- `.pytest_cache/`
- `pytest-cache-files-*/`
- `htmlcov/`
- `.coverage`
- `coverage.xml`
- `pytest_collect*.txt`
- `baseline/`

**Decisión:** Ya están cubiertos en gran parte por `.gitignore`; se refuerzan patrones faltantes.

### 3. Datos de runtime y backups (riesgo: medio, acción: ignorar)

- `artifacts/data/` — contiene datos de Elasticsearch, Wazuh y SQLite (`soar_data.db`). Son generados en ejecución.
- `artifacts/logs/`, `artifacts/results/`, `artifacts/coverage/`, `artifacts/backups/`, `artifacts/temp/` — directorios de salida de operación.

**Decisión:** Se añade `/artifacts/data/` a `.gitignore` (el resto ya estaba parcialmente ignorado). Los directorios se recrean en despliegue o mediante Makefile.

### 4. Archivos de documentación generada / legacy (riesgo: bajo-medio, acción: revisar manualmente)

- `docs/API_DOCUMENTATION.md.legacy`
- `apps/api/docs/legacy/`
- `docs/audit/legacy/`

**Decisión:** Se mantienen por histórico, explícitamente marcados como `legacy` y no se duplican en documentación operativa.

### 5. Archivos de configuración sensibles (riesgo: alto, acción: confirmar que están ignorados)

- `.env.full`
- `.env`
- `.env.testing`
- `.env.local`
- `infra/docker/compose/logging/grafana-datasources.yml`

**Decisión:** Confirmados en `.gitignore`. **Nota histórica:** `.env.full` aparece en commits anteriores del repositorio. El usuario ha decidido no reescribir el historial de Git por el momento; se recomienda rotar esos secretos y considerar un purge posterior si el repositorio se vuelve público.

## Cambios aplicados

- `.gitignore` ampliado con:
  - `/artifacts/data/`
  - Patrones para scripts temporales de remediación.
  - `pytest-cache-files-*/`, `pytest_collect*.txt`, `baseline/`.

## Limitaciones y trabajo pendiente

- Algunos archivos de `.gitignore` son específicos de Elasticsearch/Wazuh y podrían simplificarse con un patrón `/artifacts/data/` general.
- No se eliminan archivos de la copia de trabajo; solo se configura su ignorancia en futuros commits.
- El historial de Git conserva versiones antiguas de `.env.full`; requiere decisión explícita del usuario para purgarlo (`git filter-branch` / `git filter-repo`).

## Referencias

- `.gitignore`
- `docs/project/documentation_remediation_tasks.md` — FASE 48
- `docs/audit/TRACEABILITY_VALIDATION.md`
