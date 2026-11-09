# Runbook: Redis caído o no alcanzable

## Síntomas

- `POST /api/v1/alerts` devuelve **503** (admission queue unavailable).
- `GET /health/ready` → `not_ready` con `admission_queue: fail`.
- Logs: `Admission queue unavailable` / `Async Redis connection failed`.
- Si `RATE_LIMIT_BACKEND=redis`: requests pasan igualmente (fail-open)
  con `Rate-limit store failed … allowing request` ≤1/min en logs.

## Diagnóstico

```bash
docker ps --filter name=soar_redis
docker logs soar_redis --tail 50
docker exec soar_redis redis-cli ping        # espera: PONG
```

Si el contenedor está `unhealthy` o reiniciando, mirar `appendonly` /
memoria en `docker inspect soar_redis`.

## Acción

```bash
docker restart soar_redis
# si sigue FATAL: revisar volumen
docker volume ls | grep redis
```

El API se recupera solo: el admission worker reconecta en el siguiente
arranque de app; si el worker arrancó sin Redis, `POST /api/v1/alerts`
sigue 503 hasta reiniciar `soar_api` — el store no hot-recupera.

```bash
docker restart soar_api
```

## Verificación

```bash
docker exec soar_api curl -sf http://localhost:8000/health/ready
# "admission_queue": {"status": "ok"}
```

## Notas

- La caché Redis (síncrona) es best-effort: su ausencia solo degrada
  rendimiento, no funcionalidad — ver `create_redis_client` fail-soft.
