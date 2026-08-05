# Matriz de requisitos — Estado final de auditoría

## Propósito

Documento generado en la **FASE 50** del proyecto `documentation_remediation_tasks.md` para registrar el estado de los requisitos principales del SOAR Ransomware Lab tras la auditoría DevOps/QA.

## Leyenda

- **PASS**: Cumple con el requisito sin observaciones.
- **FIXED**: Cumple después de correcciones realizadas.
- **PARTIAL**: Cumple parcialmente; existen limitaciones documentadas.
- **BLOCKED**: Requiere acción del usuario o condiciones externas.
- **FAIL**: No cumple; debe abordarse.

## Matriz

| ID | Requisito | Categoría | Estado | Evidencia / Notas |
|----|-----------|-----------|--------|---------------------|
| R1 | El repositorio no contiene `.env.full` o `.env` en el *working tree* actual. | Seguridad | PASS | `.gitignore` los excluye; `git status` no los muestra como no trackeados. |
| R2 | No existen contraseñas hardcodeadas como fallback en scripts de setup o integraciones críticas. | Seguridad | FIXED | Eliminados fallbacks en `init_thehive.py`, `reset_cortex.py`, `restore_credentials.py`, `setup_analyzers_and_iocs.py`, `init_shuffle_webhook.py`, `cortex_client.py`, `create_simple_workflow.py`, `create_workflow_api.py`, `check_execution.py` y tests E2E. |
| R3 | Los scripts críticos hacen *fail-fast* si faltan variables de entorno requeridas. | Seguridad/Confiabilidad | FIXED | Añadidas comprobaciones en scripts de setup y clientes de Cortex/Shuffle. |
| R4 | `.env.full` no aparece en el historial de Git. | Seguridad | BLOCKED | El historial contiene versiones de `.env.full`. El usuario decidió no reescribirlo; se recomienda rotar secretos y purgar si se publica. |
| R5 | Nginx redirige HTTP a HTTPS y sirve proxy inverso en 443. | Infraestructura | PASS | `nginx.conf` contiene `return 301 https://$host$request_uri` y bloque `listen 443 ssl`. |
| R6 | La configuración de Nginx es sintácticamente válida. | Infraestructura | PASS | `nginx -t` ejecutado vía `docker run` con el config del repo: `syntax is ok`. |
| R7 | Los certificados TLS son autofirmados, válidos y cubren `soar.local`. | Infraestructura | PASS | Certificado `soar.local.crt` CN=`soar.local`, válido hasta 2027-05-18. |
| R8 | Los servicios usan redes Docker correctas (`soar_net`, `logging_net`, etc.). | Infraestructura | PASS | `docker-compose.api.yml`, `docker-compose.yml` y `docker-compose.logging.yml` definen y asignan las redes. |
| R9 | Los puertos documentados coinciden con los mapeos de Docker Compose. | Infraestructura/Docs | PASS | Revisados en `docker-compose.*.yml` y `docs/operations/ports_and_urls.md` / `user_guide.md`. |
| R10 | `make reset` preserva `.env.full` y datos persistentes. | Operación | FIXED | `restore_credentials.py` y backup/restore del Makefile preservan `.env.full`; volúmenes Docker persisten salvo `docker compose down -v`. |
| R11 | Los tests E2E pasan con credenciales gestionadas por variables de entorno. | Testing | FIXED | `test_app_e2e.py`, `test_ui_e2e.py` y `test_kpi_dashboard.py` leen credenciales de `.env.full` / entorno. |
| R12 | El stack de logging (Promtail → Loki → Grafana) es funcional. | Observabilidad | PASS | Grafana en `logging_net` + `soar_net`; `grafana-datasources.yml.template` usa placeholder para ES; plugin ES instalado. |
| R13 | Los artefactos temporales y de runtime no se versionan. | Limpieza | FIXED | `.gitignore` ampliado con `artifacts/data/`, `tmp_*.py`, `_*.py`, `pytest-cache-files-*`, etc. |
| R14 | Existe una matriz de incongruencias documentada. | Gobernanza | PASS | `docs/project/inconsistency_matrix.md` y sección en `docs/testing/test_suite.md`. |
| R15 | Existe un análisis de archivos obsoletos. | Gobernanza | PASS | `docs/project/obsolete_files_analysis.md` creado. |
| R16 | `grafana-datasources.yml` generado no se versiona y usa placeholders. | Seguridad | PASS | El archivo generado está en `.gitignore`; el template usa `<ELASTIC_PASSWORD>`. |
| R17 | Las contraseñas de base de datos no contienen `@` ni `!`. | Seguridad/Operación | PASS | `.env.example` y `generate_env.py` evitan esos caracteres; Wazuh usa `WazuhApi.Lab2024-Secure`. |
| R18 | `docker compose config` se puede generar sin secretos reales en logs. | Infraestructura | PARTIAL | Compose utiliza variables; validación completa requiere `.env.full`. |
| R19 | Documentación refleja el estado operativo final. | Documentación | FIXED | `user_guide.md`, `test_suite.md`, `infrastructure_guide.md` actualizados con estado actual. |
| R20 | Existe un informe final de auditoría. | Gobernanza | PASS | `docs/project/final_audit_report.md`. |

## Resumen de estados

- **PASS / FIXED**: 18
- **PARTIAL**: 1
- **BLOCKED**: 1

## Limitaciones principales

- **R4**: Historial de Git con `.env.full`. Mitigación: no publicar el repo sin purgar; rotar secretos.
- **R18**: Validación de `docker compose config` depende de disponibilidad de `.env.full` y de Docker.

## Referencias

- `.gitignore`
- `docs/project/inconsistency_matrix.md`
- `docs/project/obsolete_files_analysis.md`
- `docs/project/final_audit_report.md`
- `docs/operations/infrastructure_guide.md`
- `docs/operations/certificate_lifecycle.md`
- `docs/testing/test_suite.md`
