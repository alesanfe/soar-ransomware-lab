# Runbook: Redis memory pressure / evictions

Alertas cubiertas: `core_redis_memory_high` (>80% de maxmemory 10m),
`core_redis_evictions` (cualquier evicción 5m).

## Contexto

Redis es la cola de admisión SOAR (`alert stream` + worker leases).
`maxmemory=768mb` con política `noeviction`: al llenarse, los productores
reciben OOM (fail-closed, visible) en lugar de pérdida silenciosa.

## Diagnóstico

```bash
docker exec soar_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
    info memory | grep -E 'used_memory_human|maxmemory|evicted'
# Series vivas:
docker exec soar_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
    xlen soar:alerts
# Exportador:
docker run --rm --network soar_net curlimages/curl:8.10.1 -s \
    http://redis-exporter:9121/metrics | grep redis_memory_
```

## Acción

- **Crecimiento legítimo** (rafaga de alertas): esperar a que el worker
  drene; si persiste, subir `REDIS_MAXMEMORY` en `.env` y recrear redis.
- **Fuga**: identificar keys grandes con `redis-cli --bigkeys` y streams
  sin consumidor (`xinfo groups`).
- **Evictions activas**: la política no debería evictar (noeviction);
  si `evicted_keys` sube, alguien cambió la política — revisar
  entrypoint en `docker-compose.hardened.yml`.
