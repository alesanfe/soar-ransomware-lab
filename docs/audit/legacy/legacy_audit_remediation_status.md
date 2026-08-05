# Estado de remediación de informes de auditoría legacy

## Alcance

Este documento recoge el seguimiento de la **FASE 51** del plan de remediación (`docs/project/documentation_remediation_tasks.md`), correspondiente a las tareas extraídas de los informes de auditoría históricos ubicados en `docs/audit/legacy/`.

> **Nota:** Los informes de `legacy/` se mantienen como archivo histórico. No deben usarse como fuente de verdad operativa; su contenido ha sido revisado y, cuando procede, integrado en la documentación y configuración actuales.

## Decisiones generales

| Tema | Estado | Decisión / Acción |
|------|--------|-------------------|
| Carpetas duplicadas `backups/` vs `artifacts/backups/` | ✅ Resuelto | `CONTRIBUTING.md` ya apunta a `./artifacts/backups`; `docker-compose.api.yml` monta `${ARTIFACTS_DIR}/backups:/app/backups`; la carpeta `backups/` en raíz no existe actualmente. |
| Scripts de debug de Shuffle | ✅ Resuelto | Añadidos a `.gitignore` los scripts no trackeados de `src/soar_lab/infrastructure/external/integrations/shuffle/` y `src/scripts/debug/`, usables solo para troubleshooting manual. |
| `.gitignore` y datos runtime | ✅ Resuelto | Añadido `/artifacts/data/` y otros patrones temporales; el directorio `artifacts/data/` contiene datos regenerables (Elasticsearch, Wazuh, SQLite). |
| Certificados SSL | ✅ Resuelto | `nginx -t` superado; certificado `soar.local.crt` válido hasta 2027-05-18, CN=`soar.local`; certificados de desarrollo se mantienen en `infra/docker/config/nginx/ssl/`. |
| Grafana provisioning en Windows/Docker Desktop | ⚠️ Parcial | Dashboard JSON válido e importable manualmente; el provisioning automático por bind mount queda documentado como workaround en `user_guide.md` y `troubleshooting.md`. |
| Vagrant/VirtualBox | ⚠️ No validado | Entorno alternativo no desplegado en sesión actual; documentado como alternativa. |
| Tests E2E | ✅ Resuelto | Última ejecución documentada 16/16 passed con credenciales de `.env.full`; conteos actualizados en `test_suite.md` y `user_guide.md`. |
| Credenciales y secretos | ✅ Resuelto | Eliminados fallbacks hardcodeados en scripts de setup e integraciones; `.env.full` es fuente de verdad. Historial de Git contiene `.env.full`; no se purga por decisión del usuario (rotar secretos si se publica). |

## Mapeo de informes legacy

| Informe | Alcance | Estado |
|---------|---------|--------|
| `AUDIT_INITIAL_STATE_2026-07-04.md` | Estado inicial y estructura detectada | Revisado; estructura actual reflejada en `docs/architecture/` y `docs/testing/`. |
| `AUDIT_DUPLICATE_FOLDERS_2026-07-04.md` | Carpetas `backups/` duplicadas | Resuelto (ver tabla). |
| `AUDIT_OBSOLETE_PY_FILES_2026-07-04.md` | Scripts de debug en `src/soar_lab/integrations/shuffle/` | Scripts correspondientes en `src/soar_lab/infrastructure/external/integrations/shuffle/` y `src/scripts/debug/` añadidos a `.gitignore`; no se eliminan para conservar utilidades de troubleshooting manual. |
| `AUDIT_PHASE1_CLASSIFICATION_2026-07-04.md` | Clasificación de archivos | Histórico; clasificación actual en `docs/architecture/code_structure.md` y `docs/project/`. |
| `AUDIT_PHASE2_REORGANIZATION_2026-07-04.md` | Reorganización de archivos | Histórico; reestructuración ya aplicada. |
| `AUDIT_PHASE3_DETECTION_2026-07-04.md` | Detección de problemas de rutas/dependencias | Revisado; dependencias corregidas en FASES 27-30. |
| `AUDIT_PHASE5_MAKE_VALIDATION_2026-07-04.md` | Validación de Makefiles | Revisado; `Makefile.win` y `Makefile.linux` documentados. |
| `AUDIT_PHASE6_DOCKER_VALIDATION_2026-07-04.md` | Validación de Docker Compose | Revisado; config validada, `nginx -t` OK. |
| `AUDIT_PHASE7_VAGRANT_VALIDATION_2026-07-04.md` | Validación de Vagrant | No ejecutado; documentado como alternativa. |
| `AUDIT_PHASE8_NGINX_SSL_VALIDATION_2026-07-04.md` | Validación de Nginx + SSL | Resuelto; config y certificados validados. |
| `AUDIT_PHASE9_TESTING_VALIDATION_2026-07-04.md` | Validación de tests | Resuelto; conteos y cobertura actualizados. |
| `AUDIT_PHASE10_METRICS_VALIDATION_2026-07-04.md` | Validación de métricas | Resuelto; dashboard y alias `soar-metrics`/`soar-metrics-v2` operativos. |
| `AUDIT_PHASE11_DOCUMENTATION_VALIDATION_2026-07-04.md` | Validación de documentación | Resuelto; documentos operativos actualizados, legacy archivado. |
| `AUDIT_PHASE13_GITIGNORE_PROPOSAL_2026-07-04.md` | Propuesta de `.gitignore` | Integrada en FASE 48; patrones añadidos. |
| `AUDIT_REPORT_*.md` (varios) | Informes generales | Histórico; estado actual en `docs/project/final_audit_report.md`. |
| `AUDIT_REPORT_DOCUMENTATION_2026-07-14.md` | Auditoría integral de documentación | Parcialmente resuelto; remanente cubierto por el presente plan de remediación. |
| `AUDIT_SRC_ORGANIZATION_2026-07-04.md` | Organización del código | Revisado; estructura actual en `docs/architecture/code_structure.md`. |
| `CODE_ANALYSIS_REPORT_2026-07-04.md` | Análisis de código y dependencias | Revisado; dependencias gestionadas por `pyproject.toml`. |
| `GRAFANA_CHARTS_COMPARISON_2026-07-04.md` | Comparación de dashboards Grafana | Resuelto; `kpi-dashboard.json` reescrito a formato Grafana 13. |
| `TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md` | Auditoría técnica general v4 | Histórico; sucesores en `docs/project/`. |

## Referencias

- `docs/audit/README.md`
- `docs/project/final_audit_report.md`
- `docs/project/obsolete_files_analysis.md`
- `docs/project/inconsistency_matrix.md`
- `.gitignore`
