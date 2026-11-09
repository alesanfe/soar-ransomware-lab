# ADR-0008: Sesiones HTTP pooled con lifecycle explícito

**Estado**: Aceptado · **Evidencia**: BUG-122, BUG-127

## Contexto

`AioHTTPClient` y `make_shuffle_forward` creaban una `aiohttp.ClientSession`
por operación: sin pooling (handshake TCP+TLS por request) y sin camino
de cierre — conexiones huérfanas hasta GC.

## Decisión

- `AioHTTPClient` pool por modo `verify_ssl` con `close()` invocado en el
  shutdown hook de la app.
- `make_shuffle_forward` reutiliza una sesión (inyectable vía `session=`)
  y expone `forward.aclose()` que la app cierra en shutdown
  (`state.admission_forward`).
- Timeouts con semántica explícita (BUG-128): `None`→default,
  `<=0`→desactivado (`ClientTimeout(total=None)`), `>0`→ese valor — el
  truthiness de `0` ya no coacciona al default.

## Consecuencias

- Pooling real (keep-alive) y cero sesiones zombie tras shutdown.
- Contrato de lifecycle: todo objeto que crea una sesión la cierra o
  expone quién la cierra.
