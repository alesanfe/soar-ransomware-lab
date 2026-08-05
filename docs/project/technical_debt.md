# Deuda Técnica y Workarounds - SOAR Ransomware Lab

Índice de TODOs, FIXMEs, XXX, HACKs, NOTEs y workarounds del proyecto.

## Regenerar el listado

```powershell
Get-ChildItem -Path src,apps,infra,tests -Recurse -Include *.py,*.yml,*.yaml,*.js,*.sh,*.md,*.json,*.toml `
  | Select-String -CaseSensitive -Pattern 'TODO|FIXME|XXX|HACK|NOTE'
```

## Comentarios de deuda encontrados

| Tipo | Ubicación | Línea | Descripción | Impacto | Estado |
|------|-----------|-------|-------------|---------|--------|
| TODO | `tests/e2e/TC-03/test_edge_cases.py` | 288 | Fix Cortex API authentication issue | Medio | Pendiente |
| TODO | `tests/e2e/TC-03/test_edge_cases.py` | 293 | Fix MISP API response issue | Medio | Pendiente |
| TODO | `tests/e2e/TC-03/test_edge_cases.py` | 434 | Fix MISP API response issue (teardown) | Medio | Pendiente |

> Los valores de placeholder (`XXX`, `FIXME`, `TODO`) en `src/soar_lab/infrastructure/validate_credentials.py` no son deuda funcional; son entradas del validador. `SECURITY NOTES` en `setup_firewall.sh` es documentación.

## Workarounds de infraestructura Docker

| # | Problema | Ubicación | Workaround | Prioridad |
|---|----------|-----------|------------|-----------|
| 1 | Loki latest no tiene shell/healthcheck | `infra/docker/compose/logging/docker-compose.logging.yml` | Iniciar sin `healthcheck`; depender de reintentos de Promtail/Grafana | Media |
| 2 | Resolución de `configs.file` relativa al primer compose | `infra/docker/compose/logging/docker-compose.logging.yml` | Usar `logging/promtail-config.yml` (sin `./`) | Baja |
| 3 | Bind mount de MariaDB falla en Windows | `infra/docker/compose/docker-compose.misp.yml` | Volumen Docker normal para `misp_db` | Alta (Windows) |
| 4 | Contraseña Wazuh requiere complejidad y escaping | `.env.full` / `docker-compose.wazuh.yml` | Usar `.` y `-` (p. ej. `<WAZUH_API_PASSWORD>`) | Media |
| 5 | Wazuh sin healthcheck fiable inicial | `docker-compose.wazuh.yml` | Nginx depende de `service_started` no `service_healthy` | Media |
| 6 | Elasticsearch disk watermark | `docker-compose.yml` | Umbrales bajos en entorno de lab; monitorizar disco | Media |
| 7 | Grafana 13 no trae datasource ES built-in | `docker-compose.logging.yml` | `GF_INSTALL_PLUGINS=elasticsearch`; Grafana en `logging_net` y `soar_net` | Baja |
| 8 | `soar-metrics` mapping incorrecto (mttr_seconds object) | `src/soar_lab/infrastructure/setup/init_shuffle_webhook.py` | Crear `soar-metrics-v2` y alias `soar-metrics` | Baja |

## Decisiones de diseño con notas técnicas

| Decisión | Motivo | Riesgo / Nota |
|----------|--------|---------------|
| `xpack.security.enabled=${ELASTIC_SECURITY_ENABLED:-true}` en Elasticsearch | Seguridad habilitada por defecto con `ELASTIC_PASSWORD` generado | Verificar que `ELASTIC_PASSWORD` y credenciales de servicios estén en `.env.full`; no usar en producción contraseñas del laboratorio |
| SQLite para almacenamiento de estado leve | Facilita despliegue sin DB externa | Escalabilidad limitada; documentar migración a PostgreSQL si crece |
| Polling periódico en `script.js` | Las WebSockets requieren gestión de conexión y autenticación | Aumenta carga en API; intervalos configurables |
| WebSocket de logs sin autenticación explícita | Simplifica frontend; protegido por red/nginx | Evaluar autenticación por token en hardening |
| `make reset` respalda/restaura `.env.full` | Preservar credenciales entre despliegues | Verificar que `ELASTIC_PASSWORD` coincida con Grafana datasource |

## Targets Make experimentales o deshabilitados

| Target | Archivo | Estado | Notas |
|--------|---------|--------|-------|
| `make vagrant-windows` | `Makefile.win` / `Makefile.linux` | Deshabilitado / incompatible | El `help` indica *"Start Windows victim VM (disabled - incompatible)"*. La VM Windows del `Vagrantfile` está deshabilitada por compatibilidad. |
| `make test-atomic` | `Makefile.linux` | Funcional pero requiere `tests/atomic/` | Ejecuta `pytest tests/atomic -v`; validar que la carpeta y fixtures existan. |
| `make test-security` | `Makefile.linux` | Funcional pero requiere `tests/security/` | Ejecuta `pytest tests/security -v`; validar cobertura real. |
| `make test-performance` | `Makefile.linux` | Funcional pero requiere `tests/performance/` | Ejecuta `pytest tests/performance -v`; no ejecutar en CI sin recursos dedicados. |
| `make test-docker-config` | `Makefile.linux` | Nuevo (FASE 11) | Ejecuta `tests/integration/test_docker_compose_validation.py` sin Docker daemon. |
| `make test-docker-runtime` | `Makefile.linux` | Nuevo (FASE 11) | Ejecuta tests de runtime Docker con daemon. |
| `make test-docker-browser` | `Makefile.linux` | Nuevo (FASE 11) | Ejecuta `test_complete_soar_integration.py` con navegador. |

## Referencias

- [`docs/operations/troubleshooting.md`](../operations/troubleshooting.md)
- [`docs/testing/test_suite.md`](../testing/test_suite.md)
- [`docs/operations/infrastructure_guide.md`](../operations/infrastructure_guide.md)
- [`docs/operations/logging_and_observability.md`](../operations/logging_and_observability.md)
