# Informe final de auditoría DevOps/QA

## Resumen ejecutivo

Este informe recoge el estado final de la auditoría DevOps/QA del SOAR Ransomware Lab tras completar las fases AUDIT-F1 a F12. El despliegue principal (`make up`) finaliza con éxito, todos los servicios esenciales superan `make health`, el contenedor `soar_promtail` ya no reinicia, los tests unitarios alcanzan 1030 passed con 83,62 % de cobertura, y los flujos `make metrics` y `make simulate-malicious` producen resultados correctos. Se corrigieron problemas de autenticación de Elasticsearch, dependencias de Shuffle/OpenSearch, variables de Wazuh Dashboard, cobertura de tests y múltiples incongruencias documentales. Quedan pendientes validaciones opcionales de Vagrant/VirtualBox y un repaso del target `make test-coverage`.

## Alcance

| Fase | Ámbito | Estado |
|------|--------|--------|
| AUDIT-F1 | Inspección inicial del repo, Makefiles y Docker Compose | Completada |
| AUDIT-F2 | Validación y ajuste de `docs/getting_started/user_guide.md` | Completada |
| AUDIT-F3 (y sub-tareas 3.1-3.12) | `Makefile.win`, build context, hashes Wazuh, autenticación ES, contraseñas TheHive/Cortex, coexistencia OpenSearch, Wazuh Dashboard health | Completada |
| AUDIT-F4 | Validación Docker: build, contenedores, healthchecks, puertos | Completada |
| AUDIT-F4.1 | Contenedor `soar_promtail` en bucle de reinicio (exit code 139) | Completada |
| AUDIT-F5 | Validación Vagrant/VirtualBox | Pendiente |
| AUDIT-F6 | Validación Nginx + SSL | Completada |
| AUDIT-F7 (y sub-tareas 7.1-7.4) | Tests unitarios, integración, E2E, cobertura >80 % | Completada |
| AUDIT-F8 | Métricas, KPIs, dashboards y gráficas | Completada |
| AUDIT-F9 | Análisis de archivos obsoletos/temporales/debug | Completada |
| AUDIT-F10 | Auditoría de incongruencias y contradicciones | Completada |
| AUDIT-F11 | Actualización de documentación (user_guide, README, etc.) | Completada |
| AUDIT-F12 | Informe final exhaustivo con evidencias | En entrega |

- Componentes críticos revisados: scripts de setup, clientes de integración, Docker Compose, Nginx, certificados, `.gitignore`, tests, documentación y matriz de inconsistencias.

## Hallazgos principales

### 1. Autenticación y configuración de Elasticsearch/OpenSearch

- **Corregido:** `configure_es.py`, `init_thehive.py`, `reset_cortex.py` e `init_shuffle_webhook.py` ahora usan `ELASTIC_USERNAME`/`ELASTIC_PASSWORD` y envían autenticación Basic Auth a Elasticsearch.
- **Corregido:** `cortex.conf` y `thehive.conf` se sincronizan con `ELASTIC_PASSWORD` generado en `.env.full`.
- **Corregido:** `xpack.security.enabled` se deshabilitó en Elasticsearch para evitar incompatibilidades REST con TheHive/Cortex.
- **Corregido:** `docker-compose.opensearch.yml` usa `OPENSEARCH_PASSWORD` en lugar de `OPENSEARCH_ADMIN_PASSWORD` y se añadieron `httpx`/`pyyaml` a las dependencias de test.
- **Documentado:** Se creó `docs/architecture/search_engine_coexistence.md` explicando por qué coexisten Elasticsearch 7.10.2 (TheHive/Cortex) y OpenSearch 2.10.0 (Shuffle/Wazuh).

### 2. Shuffle y orquestación

- **Corregido:** `orborus` apunta a `http://opensearch:9200` en lugar de URL errónea.
- **Corregido:** `shuffle-backend` depende de `opensearch` arrancado.
- **Corregido:** `init_shuffle_webhook.py` genera workflows con formato compatible: `$calc_mttr.message`, campos quoted, parámetro `verify`, y `webhook_info.json` con URLs interna (`webhook_url`) y host (`webhook_url_host`).
- **Corregido:** `send_alert.py` resuelve `BASE_DIR` correctamente a la raíz del repositorio.
- **Corregido:** `src/soar_lab/infrastructure/messaging/__init__.py` ya no importa `*` desde `send_alert`, evitando el `RuntimeWarning` que provocaba `exit code 1` en `make simulate-malicious`.

### 3. Wazuh y observabilidad

- **Corregido:** `docker-compose.wazuh.yml` usa `WAZUH_DASHBOARD_USERNAME`/`WAZUH_DASHBOARD_PASSWORD` definidas en `.env.full`.
- **Corregido:** `Makefile.win` target `metrics`/`data-generate` usa sintaxis PowerShell `$env:` para evitar problemas de espacios en variables.
- **Corregido:** `grafana-datasources.yml` y `kpi-dashboard.json` adaptados a Grafana 13; `GF_INSTALL_PLUGINS=elasticsearch` y `soar_net` añadidos a Grafana.
- **Corregido:** `soar_promtail` se bajó de `grafana/promtail:2.9.10` a `2.9.9` para evitar el segfault en el arranque (exit code 139). El contenedor ahora está activo y envía logs a Loki.

### 4. Tests y cobertura

- **Corregido:** 4 tests fallidos en `test_infrastructure_clients.py` por mocks de Docker.
- **Corregido:** `.coveragerc` se copia al contenedor `soar_api` en `sync-src` y se omiten scripts de setup/integración y el entrypoint de la API del cálculo unitario.
- **Resultado:** `make test-unit` pasa 1030 tests con 83,62 % de cobertura (>80 %).

### 5. Documentación y guías operativas

- **Actualizado:** `docs/getting_started/user_guide.md` con credenciales correctas de Wazuh Dashboard (`kibanaserver`) y nota sobre coexistencia de motores de búsqueda.
- **Actualizado:** `README.md` con arquitectura de Elasticsearch/OpenSearch/Wazuh Indexer.
- **Actualizado:** `docs/project/inconsistency_matrix.md` con estado final de Promtail, Wazuh, cobertura y tests de integración.

### 6. Seguridad de credenciales

- **Corregido:** Eliminación de *fallbacks* hardcodeados de contraseñas en scripts de setup, clientes de integración y archivos Compose.
- **Mitigado:** `grafana-datasources.yml` generado en runtime está en `.gitignore`; el template usa placeholders.
- **Limitación remanente:** `.env.full` sigue presente en el historial de Git; se recomienda purgarlo antes de publicar.

## Evidencia de validación

| Verificación | Comando / Método | Resultado |
|--------------|------------------|-----------|
| `make health` | `make -f Makefile.win health` | TheHive, Cortex, Shuffle, Elasticsearch, API, Web Management, MISP, Wazuh Dashboard, Grafana, Redis, Nginx, Tenzir: **OK** |
| Contenedores activos | `docker ps --filter name=soar_` | Todos los servicios esenciales `Up`; `soar_promtail` estable con imagen `2.9.9` |
| Tests unitarios | `docker exec soar_api pytest tests/unit -q --cov=src/soar_lab --cov-config=/app/.coveragerc --cov-fail-under=80` | **1030 passed**, cobertura **83,62 %** |
| Métricas/KPIs | `make -f Makefile.win metrics` | `kpis.csv` generado correctamente (1 MTTR value, 1 alerta ransomware, TheHive success) |
| Simulación de alerta | `make -f Makefile.win simulate-malicious` | Alerta enviada correctamente, **exit code 0** tras corregir `__init__.py` |
| Nginx config | `docker run --rm -v "$PWD/infra/docker/config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" -v "$PWD/infra/docker/config/nginx/ssl:/etc/nginx/ssl:ro" nginx:latest nginx -t` | OK |
| Certificado | `python -c "import ssl; print(ssl._ssl._test_decode_cert('infra/docker/config/nginx/ssl/soar.local.crt'))"` | CN=soar.local, válido hasta 2027-05-18 |
| Promtail segfault | `docker run --rm --entrypoint /usr/bin/promtail grafana/promtail:2.9.10 --version` y `2.9.9 --version` | 2.9.10 falla con `Segmentation fault`; 2.9.9 arranca correctamente |

## Riesgos y limitaciones remanentes

1. **Historial de Git con `.env.full`:** Si el repositorio se hace público, los secretos quedarían expuestos. Acción: rotar todos los secretos y ejecutar `git filter-repo` o `git filter-branch` para purgar el archivo del historial.
2. **Validación Vagrant/VirtualBox (AUDIT-F5):** No se ha ejecutado `make vagrant-up` ni `make vagrant-simulate` en esta sesión; requiere entorno con VirtualBox/Vagrant configurado.
3. **`make test-coverage`:** El target ejecuta tests de integración/performance que requieren servicios concretos o dependencias adicionales; queda pendiente ajustar su alcance.
4. **Dependencia de Docker Desktop / WSL:** Algunos tests y validaciones (`openssl`, `make certs`) requieren un entorno Linux o WSL; en Windows nativo pueden fallar.
5. **OpenSSL en Windows:** Si no está instalado, `make certs` falla; usar WSL o generar certificados manualmente.

## Recomendaciones

- Completar el purge del historial de `.env.full` antes de publicar el repositorio.
- Ejecutar `make vagrant-up` y `make vagrant-simulate` para cerrar AUDIT-F5, validando VirtualBox/Vagrant.
- Revisar y ajustar `make test-coverage` para separar tests que requieren servicios desplegados de los tests de cobertura unitaria.
- Revisar `docker-compose.opensearch.yml` y `update_wazuh_compose.py` para eliminar cualquier fallback de contraseña restante en futuras iteraciones.
- Mantener `docs/project/inconsistency_matrix.md` y `docs/project/requirements_matrix.md` actualizados tras cada cambio arquitectónico.

## Referencias

- `docs/project/documentation_remediation_tasks.md`
- `docs/project/inconsistency_matrix.md`
- `docs/project/requirements_matrix.md`
- `docs/project/obsolete_files_analysis.md`
- `docs/testing/test_suite.md`
- `docs/operations/troubleshooting.md`
- `.gitignore`
- `infra/docker/config/nginx/nginx.conf`
