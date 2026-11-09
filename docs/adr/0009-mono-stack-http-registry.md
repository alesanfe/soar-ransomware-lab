# ADR-0009: Stack HTTP único (requests) y registro declarativo de adaptadores

**Estado**: Aceptado · **Evidencia**: D2/D5/A2 de la auditoría — suite unit
2268 verde tras la migración.

## Contexto

El proyecto mantenía dos stacks HTTP: `aiohttp` (health checks async,
`AioHTTPClient`, `shuffle_forward`) y `requests` (clientes de
integración con circuit breaker, `BaseHTTPClient`). Dos implementaciones
de timeout/retry/TLS implicaban comportamiento divergente y deuda real.

Además, añadir una integración exigía editar el composition root en
varios puntos (import, constructor, atributo, mapa de health).

## Decisión

1. **Mono-stack `requests`**. `AioHTTPClient` pasa a ser una fachada
   async sobre `requests.Session` pooled vía `asyncio.to_thread` — la
   API pública async se conserva, pero hay una sola pila de transporte.
   `aiohttp` solo queda como dependencia de los harness de carga en
   `tests/performance/` (extra `test`), no del código de producción.
2. **`AdapterRegistry` declarativo** (`infrastructure/adapter_registry.py`):
   cada integración es un `AdapterSpec` (nombre, url_key, api_key_key,
   factory). `CompositionRoot` itera el registro y expone
   `<name>_client`; `_warn_unconfigured_integrations` se deriva de la
   misma spec — una fila por adaptador, cero edits dispersos.
3. **Cero lazy imports** en `src/` — todos los imports son top-level;
   el arranque perezoso queda cubierto por `SOAR_SKIP_EAGER_INIT`.

## Consecuencias

- Un solo lugar para timeouts/retries/TLS de salida (`base_client` +
   `http_client`).
- `shuffle_forward` usa la fachada común — un solo comportamiento de
   keep-alive y pooling.
- Añadir una integración = una fila `AdapterSpec` + el cliente.

## Alternativas descartadas

- Async nativo end-to-end (`httpx`/`aiohttp` real): refactor de todos
  los clientes sync + el workflow admission — riesgo alto sin beneficio
  medible a escala de laboratorio.
