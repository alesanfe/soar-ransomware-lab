# Runbook — DR de la Dead-Letter Queue (IR3)

La DLQ (`soar:dlq` en Redis, o la lista en memoria cuando Redis está
ausente) retiene alertas que agotaron reintentos o fallaron al decodificar.

## Diagnóstico

```bash
# ¿Cuántas entradas hay y de qué tipo?
docker exec soar_api python -c "
from soar_lab.infrastructure.clients import create_redis_client
r = create_redis_client(None); print(r.llen('soar:dlq'))"

# API: listar entradas (token interno requerido)
curl -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/dlq
```

`reason=decode_failed` → la entrada es irrecuperable (payload
malformado); `reason=forward_failed` → reintentable.

## Auto-redrive (R2)

El worker ejecuta `dlq_auto_redrive` periódicamente: reintenta entradas
`forward_failed` con backoff exponencial por antigüedad y un presupuesto
por ciclo. Las que superan `max_attempts` quedan en DLQ — **eso es la
señal de alarma**, no ruido.

## Redrive manual

```bash
curl -X POST -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/dlq/redrive
```

## Purga (destructiva — solo tras exportar si se necesita evidencia)

```bash
curl -X POST -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/dlq/purge
```

## Verificación

El test unitario de round-trip cubre redrive + backoff; el chaos test
cubre Redis caído → 503 tipado en readiness.
