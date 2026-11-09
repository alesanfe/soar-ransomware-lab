# ADR-0013 — Uvicorn multi-worker opt-in con stores compartidos en Redis

- **Estado**: Aceptado
- **Fecha**: 2026-11-08
- **Decisores**: owner del repo

## Contexto

La API corría con un único worker uvicorn (`--workers 1` implícito).
Para carga real del laboratorio sobra (soak medido: admisión P95=90 ms,
0% fallos), pero el scorecard marcaba "single-worker" como debilidad de
API REST: sin ruta de escala horizontal, cualquier CPU-bound saturaba el
proceso único.

El bloqueo no era uvicorn sino el **estado en proceso**:

1. `RateLimitMiddleware` con ventana deslizante en memoria — N workers
   implicaban N presupuestos independientes.
2. `WsTicketStore` en memoria — un ticket emitido por el worker A era
   rechazado por el B (single-use roto entre procesos).
3. `ConnectionManager` WebSocket — los broadcasts solo alcanzan sockets
   del mismo proceso (intrínseco a websockets, no migrable).

## Decisión

`UVICORN_WORKERS` (default 1) parametriza los workers en el CMD del
Dockerfile. Para `>1` se requiere activar los backends compartidos:

- `RATE_LIMIT_BACKEND=redis` — `RedisSlidingWindowStore` (ya existía,
  BL-RATE-005) comparte el presupuesto entre procesos.
- `WS_TICKET_BACKEND=redis` — nuevo `RedisWsTicketStore` con consume
  atómico `GETDEL` y TTL nativo Redis; fallback a memoria con warning si
  Redis no responde. Errores en `consume()` deniegan (fail-closed).

El fanout de broadcast WebSocket (`/ws/logs`) permanece por worker:
un cliente solo ve eventos emitidos en su worker. En el lab el WS es
telemetría de diagnóstico — la degradación es aceptable y está
documentada; con balanceo sticky (cookie/affinity) desaparece.

## Consecuencias

- `UVICORN_WORKERS=1` (default): comportamiento idéntico al anterior,
  sin dependencia de Redis para auth/tickets.
- `UVICORN_WORKERS>1` + ambos backends Redis: requests HTTP escalan
  horizontalmente con rate-limit y tickets correctos; el broadcast WS
  queda particionado por worker.
- El healthcheck de compose no cambia (uvicorn expone el puerto una vez
  levantado el master).

## Alternativas consideradas

- **Replica del contenedor + LB**: misma necesidad de stores
  compartidos + un nginx delante — más superficie para el mismo efecto.
- **Redis pub/sub para fanout WS**: eliminaría la limitación pero
  añade un canal más; diferido — la telemetría por worker es suficiente
  en este laboratorio.

## Verificación en vivo (2026-11-09)

Recreación con `UVICORN_WORKERS=2 RATE_LIMIT_BACKEND=redis
WS_TICKET_BACKEND=redis`: 3 procesos uvicorn (master+2), ticket WS
emitido → `ws:ticket:*` keys en Redis (store compartido, GETDEL
atómico), ventana rate-limit en `ratelimit:*` ZSETs (presupuesto único
entre workers). Revertido a `UVICORN_WORKERS=1` (default documentado)
tras la prueba — comportamiento idéntico al anterior.
