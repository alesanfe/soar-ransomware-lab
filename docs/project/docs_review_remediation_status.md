# Seguimiento de la revisión de `docs/` - FASE 52

## Alcance

Documento de seguimiento de la **FASE 52** del plan de remediación (`docs/project/documentation_remediation_tasks.md`), correspondiente a las tareas extraídas de la revisión archivo a archivo de la documentación del proyecto.

## Acciones realizadas

| Tema | Archivos / Componentes | Acción | Estado |
|------|------------------------|--------|--------|
| Contraseñas literales en ejemplos de API | `docs/integrations/api_contracts.md` | Reemplazado `X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1` por `<WEB_UI_PASSWORD>` en ejemplos de login JWT. | ✅ |
| Fallbacks de contraseñas en Compose | `infra/docker/compose/docker-compose.api.yml`, `docker-compose.misp.yml`, `docker-compose.opensearch.yml`, `docker-compose.wazuh.yml`, `src/soar_lab/scripts/maintenance/update_wazuh_compose.py` | Eliminados los valores por defecto literales (`Y0f#...`, `X9e#...`, `OpenSearchLab2024SecurePass`, `kibanaserver`, etc.); las variables sensibles se leen ahora exclusivamente de `.env.full`. | ✅ |
| Healthcheck de MISP DB | `infra/docker/compose/docker-compose.misp.yml` | Cambiado a `CMD-SHELL` y se referencia `$$MYSQL_ROOT_PASSWORD` del contenedor para evitar exponer el fallback en el manifesto. | ✅ |
| `api-docs.html` y documentación HTML legacy | `apps/api/docs/legacy/` | No se modifica evidencia histórica; la fuente actual es `docs/integrations/api_contracts.md` y `docs/api/openapi.json`. | ✅ Documentado |
| `API_AUTH_SECRET` legacy | `src/soar_lab/config/settings.py`, `src/soar_lab/application/use_cases/auth_service.py` | El secreto se lee de `API_AUTH_SECRET` / `JWT_SECRET_KEY`; el fallback por defecto es inherente a la configuración. | ✅ Documentado |
| `network-watcher` y resolución DNS | `docs/operations/network_watcher.md`, `docs/operations/infrastructure_guide.md` | El watcher inyecta `/etc/hosts` y reescribe `resolv.conf`; procedimiento de recuperación manual y logs documentados. | ✅ |
| `misp_db` como volumen Docker | `infra/docker/compose/docker-compose.misp.yml`, `docs/operations/infrastructure_guide.md` | Configurado como volumen nombrado (no bind mount) para evitar `Permission denied` en Windows; nota sobre `docker compose down -v` en `infrastructure_guide.md`. | ✅ |

## Verificación

- `python src/soar_lab/scripts/ci/docs_quality.py` (o su equivalente CI) debe seguir pasando.
- `docker compose -f infra/docker/compose/docker-compose.api.yml config` no imprime secretos reales al no definir `.env.full` (devuelve variables sin resolver).
- Los ejemplos de `api_contracts.md` usan placeholders y no credenciales reales.

## Riesgos remanentes

- Si `.env.full` no existe, los servicios sensibles fallarán en lugar de usar una contraseña por defecto. Esto es el comportamiento esperado; el usuario debe ejecutar `make generate-secrets` antes de `make up`.
- `apps/api/docs/legacy/` contiene ejemplos con credenciales antiguas; se mantiene como evidencia histórica y no se usa como fuente operativa.

## Referencias

- `docs/integrations/api_contracts.md`
- `docs/operations/network_watcher.md`
- `docs/operations/infrastructure_guide.md`
- `docs/project/inconsistency_matrix.md`
- `docs/project/final_audit_report.md`
