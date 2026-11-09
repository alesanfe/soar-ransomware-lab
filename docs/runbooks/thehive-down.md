# Runbook: TheHive no responde / API key inválida

## Síntomas

- `GET /soar/thehive/cases` → `integration_unavailable` (503) o
  `integration_auth_failed` (502).
- Creación de casos falla tras la ingesta de alertas.
- `IntegrationError [TheHiveClient] 401` → la API key caducó.

## Diagnóstico

```bash
docker ps --filter name=soar_thehive
docker logs soar_thehive --tail 50
docker exec soar_api curl -sf http://thehive:9000/api/status
```

`401` específico → la key de `.env.full` ya no vale (reset reciente).

## Acción

```bash
# 1. Restart del servicio
docker restart soar_thehive

# 2. Regenerar la API key tras un reset (documentado en AGENTS.md):
docker exec soar_api python /app/scripts/setup/init_thehive.py
# → escribe la THEHIVE_API_KEY fresca en .env.full

# 3. Recargar config sin restart completo no existe aún → reiniciar API:
docker restart soar_api
```

## Verificación

```bash
docker exec soar_api python -c "from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient; ..."
# o e2e: pytest tests/integration -k thehive (dentro del contenedor)
```

## Notas

- Cassandra/Elasticsearch internos de TheHive tardan 1-3 min en el primer
  arranque — `starting` ≠ `broken`.
