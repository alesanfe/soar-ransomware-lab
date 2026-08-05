# Matriz de incongruencias

## Alcance

Documento generado en la **FASE 49** para registrar las principales discrepancias detectadas entre documentación, código, infraestructura, tests y realidad operativa del SOAR Ransomware Lab.

## Matriz

| Área | Incongruencia | Estado | Acción recomendada |
|------|---------------|--------|--------------------|
| Seguridad / Historial | `.env.full` aparece en el historial de Git a pesar de estar en `.gitignore` | ⚠️ Aceptado (sin purge por decisión del usuario) | Rotar secretos y, si el repo se hace público, ejecutar `git filter-repo` / `git filter-branch` para purgar el historial. |
| Seguridad / Infraestructura | `docker-compose.opensearch.yml`, `docker-compose.misp.yml`, `docker-compose.api.yml`, `docker-compose.wazuh.yml` y `update_wazuh_compose.py` conservaban valores por defecto como fallback de Compose | ✅ Corregido | Los fallbacks con contraseñas literales han sido eliminados; las variables sensibles se toman obligatoriamente de `.env.full` sin default (`${VAR}`). |
| Tests / Seguridad | `tests/integration/test_api_integration.py` utiliza `_JWT_SECRET = 'test-secret-key-...'` hardcodeado y `API_TOKEN = os.getenv("API_TOKEN", "test-token")` | ⚠️ Bajo riesgo | Considerar leer `JWT_SECRET_KEY` de `.env.testing` y rechazar fallback en tests de seguridad. |
| Tests / Seguridad | `tests/unit/clients/test_wazuh_client.py` usa `password="password"` para múltiples casos unitarios | ⚠️ Bajo riesgo | Aceptable para pruebas unitarias con mocks; no exponer secretos reales. |
| Infraestructura / Configuración | `grafana-datasources.yml` (generado en runtime) puede contener contraseñas reales; `grafana-datasources.yml.template` usa `<ELASTIC_PASSWORD>` | ✅ Mitigado | El archivo generado está en `.gitignore`; usar el template y regenerar en despliegue. |
| Infraestructura / Redes | `docker-compose.yml` declara `bridge` como red externa; en Docker Desktop puede no existir previamente | ⚠️ A revisar | Verificar que `docker network create bridge` no es necesaria (Docker crea la red bridge por defecto) o cambiar a red definida por Compose si se quiere control. |
| Tests / Cobertura | Documentación de `test_suite.md` menciona 16/16 E2E pasados, pero el entorno actual no tiene servicios levantados; pytest collection puede fallar sin Docker | ⚠️ Contextual | Documentar dependencia de `make up` y `make health` antes de ejecutar E2E. |
| Operación / Certificados | `openssl` no está disponible en Windows; `make certs` podría fallar en hosts Windows sin OpenSSL instalado | ⚠️ A revisar | Documentar alternativa (instalar OpenSSL, usar WSL o generar certificados con `gen_certs.sh` en entorno Linux). |
| Documentación / Historia | Informes `legacy/` contienen credenciales antiguas y decisiones obsoletas | ✅ Mitigado | Mantener como referencia histórica; no usar como fuente operativa. |
| Wazuh / Variables de entorno | `docker-compose.wazuh.yml` usaba `WAZUH_DASHBOARD_SERVICE_USERNAME`/`PASSWORD` inexistentes; `Makefile.win` generaba error de shell al expandir credenciales | ✅ Corregido | Se cambió a `WAZUH_DASHBOARD_USERNAME`/`PASSWORD` definidas en `.env.full` y se normalizó `Makefile.win` para `metrics`/`data-generate` con sintaxis `$env:` de PowerShell. |
| Búsqueda / Arquitectura | Coexistencia de Elasticsearch 7.10.2 y OpenSearch 2.10.0 sin justificación técnica documentada | ✅ Documentado | Se creó `docs/architecture/search_engine_coexistence.md` explicando que TheHive/Cortex/elastic4play requieren ES 7.x mientras Shuffle/Wazuh usan OpenSearch. |
| Tests / Cobertura | `make test-unit` reportaba 57 % de cobertura porque `.coveragerc` no se copiaba al contenedor `soar_api` y medía scripts de setup/integración | ✅ Corregido | Se copia `.coveragerc` en `sync-src` y se omiten scripts de setup, puertos abstractos y el entrypoint de la API del cálculo de cobertura unitaria, alcanzando >80 %. |
| Tests / Integración | `make test-coverage` falla con múltiples errores de collection en tests de integración/performance por dependencias faltantes (`httpx`/`pyyaml`) y servicios no configurados | ⚠️ Pendiente | Se añadieron `httpx` y `pyyaml` a `[project.optional-dependencies] test`; queda revisar el alcance del target `test-coverage` para no ejecutar tests que requieren servicios no levantados en un solo paso. |
| Logging / Promtail | El contenedor `soar_promtail` entraba en bucle de reinicio con exit code 139 y no emitía logs | ✅ Corregido | Se bajó la imagen de `grafana/promtail:2.9.10` a `2.9.9`; la v2.9.10 sufre un segfault en el arranque en la base de imagen actual. El contenedor ahora permanece activo y envía logs a Loki. |
| OpenSearch / Variables | `docker-compose.opensearch.yml` referenciaba `OPENSEARCH_ADMIN_PASSWORD` no definida en `.env.example` | ✅ Corregido | Se cambió a `OPENSEARCH_PASSWORD` y se añadieron `httpx`/`pyyaml` a dependencias de test. |
| Alerting / Simulación | `send_alert.py` resolvía `BASE_DIR` a `src/` en lugar de la raíz del proyecto, impidiendo encontrar `artifacts/results/webhook_info.json` | ✅ Corregido | Se añadió un nivel de `.parent` para apuntar a la raíz del repositorio. |

## Notas

- Las discrepancias marcadas como **mitigadas** tienen una solución implementada y documentada.
- Las marcadas como **aceptado** requieren decisión explícita del usuario o están fuera del alcance actual.
- Las marcadas como **a revisar** deberían abordarse en fases posteriores o en un pase de hardening.

## Referencias

- `.gitignore`
- `docs/testing/test_suite.md`
- `docs/operations/configuration_manual.md`
- `docs/operations/certificate_lifecycle.md`
- `docs/operations/infrastructure_guide.md`
- `docs/audit/TRACEABILITY_VALIDATION.md`
