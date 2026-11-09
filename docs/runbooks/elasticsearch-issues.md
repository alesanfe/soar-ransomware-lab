# Runbook: Elasticsearch — estado amarillo, scroll leaks, bulk errors

## Síntomas

- `GET _cluster/health` → `yellow` (es **normal** en single-node: no hay
  réplicas a asignar — no es un fallo).
- `too_many_scrolls` / `SearchContextMissingException` crecientes.
- `execute_bulk` → `IntegrationError … bulk partial failure`.

## Diagnóstico

```bash
docker exec soar_api curl -s http://elasticsearch:9200/_cluster/health?pretty
# Contextos scroll abiertos (deberían tender a 0):
docker exec soar_api curl -s http://elasticsearch:9200/_nodes/stats/indices/search | grep -i scroll
```

## Acción

- **Amarillo single-node**: nada — es el estado esperado. Si se quiere
  verde, bajar `number_of_replicas` a 0 en el índice.
- **Scroll contexts acumulados**: el generador libera en `finally` desde
  BUG-117; si aún quedan abiertos (worker matado a medio scroll):
  ```bash
  docker exec soar_api curl -X DELETE http://elasticsearch:9200/_search/scroll/_all
  ```
- **Bulk partial failure (BUG-137)**: el error ya llega como excepción con
  los `_id`+`error.type` — revisar el mensaje para ver si es
  `mapper_parsing_exception` (doc mal formado) o `version_conflict`
  (ídem concurrente — benigno si es el mismo doc).

## Verificación

```bash
docker exec soar_api curl -s http://elasticsearch:9200/_cat/indices?v
docker exec soar_api curl -s "http://elasticsearch:9200/soar-alerts/_count"
```
