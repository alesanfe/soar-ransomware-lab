# ADR-0004: Rate limiter con backend intercambiable

**Estado**: Aceptado · **Evidencia**: BUG-111, BUG-123, BUG-134

## Contexto

La ventana deslizante vivía en memoria del proceso: N réplicas ⇒ N×
presupuesto efectivo. Además `X-Forwarded-For` de cualquier peer creaba
buckets (bypass total) y `X-RateLimit-Reset` mentía (`now+60`).

## Decisión

Contrato común `record(key, now, window_s) -> (count, oldest_epoch)`:

- `InMemorySlidingWindowStore` — default, por instancia.
- `RedisSlidingWindowStore` — ZSET `ratelimit:<client>` con
  `ZREMRANGEBYSCORE`+`ZADD`(member único `epoch:uuid`)+`ZCARD`+`ZRANGE`
  +`EXPIRE` en un pipeline: ventana compartida entre réplicas.
- Selección: `RATE_LIMIT_BACKEND=redis` + `RATE_LIMIT_REDIS_URL`/`REDIS_URL`.
- XFF solo se honra desde `RATE_LIMIT_TRUSTED_PROXIES` (CIDRs, default
  vacío = fail-closed), resolución right-to-left; identidad = Bearer-token
  fingerprint (sha256) o IP.
- Fail-open ante error del backend (ver ADR-0007); hits denegados SÍ
  ocupan ventana (anti-probing).

## Consecuencias

- Multi-instancia íntegro con Redis; single-node sin dependencias extra.
- Un fallo de Redis degrada la limitación, no la disponibilidad.
