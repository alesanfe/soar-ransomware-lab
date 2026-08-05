# Auditoría del Proyecto

Este directorio agrupa los informes de auditoría y aseguramiento de calidad del SOAR Ransomware Lab. La fuente de verdad
para el estado actual sigue siendo el código, los tests y los artefactos del pipeline CI/CD; los informes de `legacy/`
son documentos históricos y pueden contener referencias a rutas o decisiones obsoletas.

## Contenido

- **[README.md](README.md)** - Este índice.
- **[legacy/](legacy/)** - Informes de auditoría históricos archivados.
- **[legacy/legacy_audit_remediation_status.md](legacy/legacy_audit_remediation_status.md)** - Seguimiento de remediación de informes legacy (FASE 51).

## Estado de remediación de informes legacy

> Ver detalles en [`legacy/legacy_audit_remediation_status.md`](legacy/legacy_audit_remediation_status.md).

- Carpetas duplicadas (`backups/` vs `artifacts/backups/`): resuelto.
- Scripts de debug de Shuffle y `src/scripts/debug/`: añadidos a `.gitignore`.
- `.gitignore` y datos runtime: ampliado con `/artifacts/data/` y patrones temporales.
- Certificados SSL/Nginx: validados.
- Grafana provisioning en Windows/Docker Desktop: parcial; workaround documentado.
- Vagrant: no validado en esta sesión.
- Tests E2E y credenciales: corregidos/documentados.

## Índice cronológico de informes representativos

| Fecha       | Informe | Alcance | Estado / Sucesor |
|-------------|---------|-------|------------------|
| 2024-07-04  | [AUDIT_REPORT_FINAL_2024-07-04.md](legacy/AUDIT_REPORT_FINAL_2024-07-04.md) | Informe final de auditoría (versión 2024) | Histórico; ver `legacy/AUDIT_REPORT.md` y CI/CD actual |
| 2026-07-04  | [AUDIT_INITIAL_STATE_2026-07-04.md](legacy/AUDIT_INITIAL_STATE_2026-07-04.md) | Estado inicial del repositorio y estructura detectada | Histórico |
| 2026-07-04  | [AUDIT_DUPLICATE_FOLDERS_2026-07-04.md](legacy/AUDIT_DUPLICATE_FOLDERS_2026-07-04.md) | Carpetas duplicadas y propuesta de limpieza | Parcialmente resuelto en refactorización de `docs/` e `infra/` |
| 2026-07-04  | [AUDIT_OBSOLETE_PY_FILES_2026-07-04.md](legacy/AUDIT_OBSOLETE_PY_FILES_2026-07-04.md) | Archivos Python obsoletos y propuesta de borrado | Parcialmente resuelto; `infrastructure/scripts/` aún contiene scripts legacy |
| 2026-07-04  | [AUDIT_PHASE1_CLASSIFICATION_2026-07-04.md](legacy/AUDIT_PHASE1_CLASSIFICATION_2026-07-04.md) | Clasificación de archivos y directorios | Histórico |
| 2026-07-04  | [AUDIT_PHASE2_REORGANIZATION_2026-07-04.md](legacy/AUDIT_PHASE2_REORGANIZATION_2026-07-04.md) | Reorganización de archivos del proyecto | Histórico |
| 2026-07-04  | [AUDIT_PHASE3_DETECTION_2026-07-04.md](legacy/AUDIT_PHASE3_DETECTION_2026-07-04.md) | Detección de problemas (rutas, dependencias) | Histórico |
| 2026-07-04  | [AUDIT_PHASE5_MAKE_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE5_MAKE_VALIDATION_2026-07-04.md) | Validación de Makefiles | Histórico |
| 2026-07-04  | [AUDIT_PHASE6_DOCKER_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE6_DOCKER_VALIDATION_2026-07-04.md) | Validación de Compose y Docker | Histórico |
| 2026-07-04  | [AUDIT_PHASE7_VAGRANT_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE7_VAGRANT_VALIDATION_2026-07-04.md) | Validación de provisiones Vagrant | Histórico |
| 2026-07-04  | [AUDIT_PHASE8_NGINX_SSL_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE8_NGINX_SSL_VALIDATION_2026-07-04.md) | Validación de Nginx y certificados | Histórico |
| 2026-07-04  | [AUDIT_PHASE9_TESTING_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE9_TESTING_VALIDATION_2026-07-04.md) | Validación de tests | Histórico |
| 2026-07-04  | [AUDIT_PHASE10_METRICS_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE10_METRICS_VALIDATION_2026-07-04.md) | Validación de métricas | Histórico |
| 2026-07-04  | [AUDIT_PHASE11_DOCUMENTATION_VALIDATION_2026-07-04.md](legacy/AUDIT_PHASE11_DOCUMENTATION_VALIDATION_2026-07-04.md) | Validación de documentación | Histórico |
| 2026-07-04  | [AUDIT_PHASE13_GITIGNORE_PROPOSAL_2026-07-04.md](legacy/AUDIT_PHASE13_GITIGNORE_PROPOSAL_2026-07-04.md) | Propuesta de `.gitignore` | Histórico |
| 2026-07-04  | [AUDIT_REPORT_2026-07-04.md](legacy/AUDIT_REPORT_2026-07-04.md) | Informe general de auditoría | Histórico |
| 2026-07-04  | [AUDIT_REPORT_2026-07-05.md](legacy/AUDIT_REPORT_2026-07-05.md) | Informe general de auditoría (día siguiente) | Histórico |
| 2026-07-05  | [AUDIT_REPORT_2026-07-05_COMPLETE.md](legacy/AUDIT_REPORT_2026-07-05_COMPLETE.md) | Informe completo de auditoría | Histórico |
| 2026-07-05  | [AUDIT_REPORT_2026-07-05_FINAL.md](legacy/AUDIT_REPORT_2026-07-05_FINAL.md) | Informe final de auditoría | Histórico |
| 2026-07-04  | [AUDIT_SRC_ORGANIZATION_2026-07-04.md](legacy/AUDIT_SRC_ORGANIZATION_2026-07-04.md) | Organización del código fuente y módulos | Parcialmente resuelto; ver `docs/architecture/code_structure.md` |
| 2026-07-04  | [CODE_ANALYSIS_REPORT_2026-07-04.md](legacy/CODE_ANALYSIS_REPORT_2026-07-04.md) | Análisis de código y dependencias | Histórico |
| 2026-07-04  | [GRAFANA_CHARTS_COMPARISON_2026-07-04.md](legacy/GRAFANA_CHARTS_COMPARISON_2026-07-04.md) | Comparación de dashboards Grafana | Resuelto en refactorización de KPIs; ver `infra/docker/compose/logging/kpi-dashboard.json` |
| 2026-07-04  | [TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md](legacy/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md) | Auditoría técnica general v4 | Histórico |
| 2026-07-08  | [AUDIT_REPORT_DEVOPS_QA_2026-07-08.md](legacy/AUDIT_REPORT_DEVOPS_QA_2026-07-08.md) | Auditoría DevOps/QA | Histórico |
| 2026-07-09  | [AUDIT_REPORT_DEVOPS_QA_2026-07-09.md](legacy/AUDIT_REPORT_DEVOPS_QA_2026-07-09.md) | Auditoría DevOps/QA | Histórico |
| 2026-07-09  | [AUDIT_REPORT_DEVOPS_QA_COMPLETE_2026-07-09.md](legacy/AUDIT_REPORT_DEVOPS_QA_COMPLETE_2026-07-09.md) | Auditoría DevOps/QA completa | Histórico |
| 2026-07-09  | [AUDIT_REPORT_DEVOPS_QA_COMPLETE_FINAL_2026-07-09.md](legacy/AUDIT_REPORT_DEVOPS_QA_COMPLETE_FINAL_2026-07-09.md) | Auditoría DevOps/QA completa final | Histórico |
| 2026-07-09  | [AUDIT_REPORT_DEVOPS_QA_FINAL_2026-07-09.md](legacy/AUDIT_REPORT_DEVOPS_QA_FINAL_2026-07-09.md) | Auditoría DevOps/QA final | Histórico |
| 2026-07-14  | [AUDIT_REPORT_DEVOPS_QA_2026-07-14.md](legacy/AUDIT_REPORT_DEVOPS_QA_2026-07-14.md) | Auditoría DevOps/QA | Histórico |
| 2026-07-14  | [AUDIT_REPORT_DEVOPS_QA_2026-07-14_FINAL.md](legacy/AUDIT_REPORT_DEVOPS_QA_2026-07-14_FINAL.md) | Auditoría DevOps/QA final | Histórico |
| 2026-07-15  | [AUDIT_REPORT_DEVOPS_QA_2026-07-15.md](legacy/AUDIT_REPORT_DEVOPS_QA_2026-07-15.md) | Auditoría DevOps/QA más reciente del periodo | Histórico |
| 2026-07-14  | [AUDIT_REPORT_DOCUMENTATION_2026-07-14.md](legacy/AUDIT_REPORT_DOCUMENTATION_2026-07-14.md) | Auditoría integral de documentación | Parcialmente resuelto; sucesor: presente plan de remediación de documentación |
| 2026-07-??  | [AUDIT_REPORT.md](legacy/AUDIT_REPORT.md) | Informe consolidado de auditoría DevOps/QA | Histórico; consultar CI/CD para estado actual |
| 2026-07-??  | [README.md](legacy/README.md) | Índice interno de la carpeta `legacy` | Histórico |

## Informes canónicos actuales

> No existe un informe de auditoría canónico vivo fuera de `legacy/`. El estado del proyecto debe verificarse con:
>
> - `docs/testing/test_suite.md`
> - `docs/operations/troubleshooting.md`
> - `.github/workflows/ci.yml`
> - `docs/architecture/version_matrix.md`
> - `docs/project/documentation_remediation_tasks.md`

### Criterios de aceptación y verificación actuales (DevOps/QA)

| Criterio | Método de verificación | Estado |
|----------|----------------------|--------|
| Sin contraseñas ni tokens reales en documentación | Revisión manual + búsquedas de patrones (`docs/`) y `src/soar_lab/scripts/ci/docs_quality.py` | ✅ Toda credencial sensible usa placeholder o variable `.env.full` |
| URLs/puertos/healthchecks coherente con `infra/docker/compose/` | Contrastar `docs/operations/ports_and_urls.md`, `docs/operations/infrastructure_guide.md` y compose files | ✅ Revisado: Shuffle API `15001`, Wazuh Dashboard `https://localhost:15601`, Nginx 80/443, etc. |
| Cuentas de tests y recolección actualizadas | `python -m pytest --collect-only -q` | ✅ `1911/1944 tests collected (33 deselected)`; 158 archivos `test_*.py` |
| OpenAPI sincronizado | Diferencia entre `docs/api/openapi.json` y `baseline/openapi.json` | ✅ Coinciden |
| Inventario de tests parseable | `baseline/tests_inventory.json` | ✅ JSON válido |
| Stack listo para `make up` / `make reset` | Verificación de volúmenes, credenciales y scripts `preserve_credentials.py` / `restore_credentials.py` | ✅ `.env.full` se preserva; credenciales internas se regeneran y se documenta actualización manual de `SHUFFLE_DEFAULT_APIKEY` |
| Criterios de cierre documentales | `docs_quality.py` sin errores | ✅ Pasa |

### Resumen de acciones de remediación recientes

- FASE 27/28/29/30: corrección de URLs Wazuh (`https`), puertos Shuffle API, mensaje Vagrant y healthcheck de Shuffle.
- FASE 31: actualización de conteos de tests a 158 archivos y 1911/1944 recogidos.
- FASE 32: sustitución de credenciales literales (`<ELASTIC_PASSWORD>`, `${GRAFANA_ADMIN_PASSWORD}`) por placeholders en `docs/operations/troubleshooting.md`; corrección de variables (`GRAFANA_PASSWORD` → `GRAFANA_ADMIN_PASSWORD`) y Wazuh Dashboard (`WAZUH_API_PASSWORD` → `WAZUH_INDEXER_PASSWORD`).
- FASE 33: nota actualizada sobre seguridad de Elasticsearch (`xpack.security.enabled=true`) y estado de la documentación.

> **Nota:** los informes `legacy/` se mantienen como archivo histórico; no deben usarse como fuente de verdad.

## Notas

- Los informes archivados en `legacy/` se conservan únicamente con fines históricos.
- Para validar el estado actual del proyecto, siempre consultar el pipeline CI/CD y los documentos operativos actualizados.
- Los informes de auditoría previos se movieron a `docs/audit/legacy/` para eliminar duplicados en la raíz y `docs/testing/`.
