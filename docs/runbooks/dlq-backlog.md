# Runbook: Acumulación en la dead-letter queue

## Síntomas

- `soar_admission_dead_total` / `dlq_size` creciendo en `/metrics`.
- Logs: `Admission <id> dead-lettered after N attempt(s): <error>`
  (BUG-136 — ahora visible en logs, no solo en contadores).

## Diagnóstico

```bash
# Listar las entradas DLQ (endpoint autenticado — token de servicio):
curl -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/queue/dlq
```

Cada entrada muestra `attempts`, `last_error` y el payload. Un `error`
repetido (p. ej. `Connection refused` a Shuffle) apunta a causa
infraestructural; errores `4xx` del webhook suelen ser payload
malformado.

## Acción

```bash
# 1. Arreglar la CAUSA primero (Shuffle caído, URL mala, etc.) — un
#    redrive sin causa resuelta devuelve todo a DLQ.
# 2. Redrive individual o masivo:
curl -X POST -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/queue/dlq/redrive
# 3. Purga (solo cuando se decide que esas admissions se descartan):
curl -X DELETE -H "X-Service-Token: $INTERNAL_SERVICE_TOKEN" \
  http://localhost:8000/api/v1/queue/dlq
```

## Verificación

- `dlq_size` vuelve a 0 en `/metrics`.
- Las admissions reencoladas aparecen `forwarded` tras el siguiente
  ciclo del worker.

## Notas

- El redrive reinserta con el mismo `idempotency_key` — un doble envío
  downstream es deduplicado por Shuffle vía `X-Idempotency-Key`.
