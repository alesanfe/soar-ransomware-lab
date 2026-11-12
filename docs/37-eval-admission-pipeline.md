# Evaluación multi-marco — Pipeline de admisión/mensajería

> Evaluación formal del pipeline de admisión de alertas:
> `src/soar_lab/infrastructure/messaging/` — `admission_worker.py`,
> `redis_streams_queue.py`, `redis_admission_store.py`,
> `worker_lease.py`, `shuffle_forward.py`, `send_alert.py` — más el
> wiring de `interfaces/api/lifecycle.py`. Metodología de `docs/32`-`36`:
> hallazgos verificados en vivo y pineados con gates
> (`tests/architecture/test_messaging_pipeline.py`, **19 gates**).
> Revisión 2026-11-11: **2 hallazgos de concurrencia** corregidos.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Fiabilidad/corrección del transporte de alertas |
| SRE / reliability patterns | At-least-once, dedup, backoff, DLQ, leader election |
| NIST SP 800-53 SC-7 / Zero Trust | Egress allowlist en el forward |
| STRIDE | Amenazas del pipeline (spoofing, repudio, DoS) |
| CWE-367 (TOCTOU), CWE-662 | Sincronización del lease |

## Evidencia de runtime (post-fix)

```
lease    holder=worker-<hostname>, pttl ~162s (renovación real),
         fence=159 ESTABLE entre ciclos (antes: None/expirado + fence
         creciendo cada ciclo — 157→158→…)
worker   admission worker started (stream=soar:admissions)
e2e      XADD sintética → entries-read 3, pending=0, lag=0, dlq=0
metrics  soar_admission_processed_total=1, forwarded_total=1
```

## Hallazgos corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| MSG-EVAL-001 | **TOCTOU en el leader lease** — `held()` hacía GET+SET: dos workers leyendo `None` concurrentemente ambos SETeaban y ambos lideraban un ciclo (el docstring prometía `SET holder NX PX` atómico). `release()` tenía la misma carrera: un lease expirado podía borrar la clave del nuevo holder | Lectura del código + análisis de ventana | Lua CAS para acquire/renew (`_HELD_SCRIPT`: renew=1 / acquire=2 / denied=0) y compare-and-delete en release — misma convención que `unbind_key` del store; test `test_concurrent_acquire_single_winner` (8 candidatos → 1 líder) + gates de atomicidad |
| MSG-EVAL-002 | **TTL del lease < cadencia de renovación** — `ttl_ms=30_000` por defecto pero `_leader()` solo se invoca cada `recover_interval_s=60s`: el lease expiraba entre ciclos, así que cada "renovación" era una adquisición nueva → huecos de liderazgo de 30s por ciclo (doble-liderazgo posible en multi-réplica) y el fence INCR crecía sin sentido (observado: 157→158→…, lease=None) | `GET soar:worker:lease` → None, `fence` incrementándose | `ttl_ms=180_000` (3× cadencia) en `lifecycle.py`; verificado en vivo: pttl renovado ~162s, **fence estable en 159** entre ciclos; gate `test_lease_ttl_exceeds_renewal_cadence` |

## Puntos positivos (verificados)

- **At-least-once honesto**: XREADGROUP + PEL + XAUTOCLAIM post-restart; re-enqueue antes de ack (crash-safe); `delivery_id = admission_id:attempt` para correlacionar reintentos transporte↔efecto.
- **Dedup fail-safe**: record terminal → ack sin re-forward; **store ilegible → defer** (WORKER-003), nunca re-POST de una forward posiblemente commitada.
- **Backpressure real**: stream acotado `MAXLEN ~100k`, batch+semaphore de concurrencia, `depth()` via lag+pending (no XLEN inflado).
- **DLQ con ciclo de vida**: size/list/redrive/purge + auto-redrive con backoff exponencial por `redrive_count` y skip de poison `decode_failed`.
- **Máquina de estados auditada**: `check_transition` + `transition_violation` loud (ADMISSION-004), `state_version` monótono.
- **Forward endurecido**: egress allowlist (http/https, sin credenciales en URL, host allowlist opcional), errores estructurados por clase (`error_code`/`retryable` — la capability URL nunca llega a logs/métricas), sobre CONTRACT-003 firmado HMAC-SHA256.
- **Idempotencia atómica**: `try_bind_key` SET NX, `unbind_key` Lua CAS.
- **Métricas pull-model en `/metrics`**: contadores processed/forwarded/retried/dead/dedup/orphans, gauge inflight, errores bucketizados por código.
- **Degradación honesta**: sin Redis → 503 explícito en ingest, `held()=True` en despliegue standalone, `xautoclaim` failure → lista vacía con warning.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| `recover()` inicial sin guardia de lease al arrancar | Las entradas reclamadas se reparten vía XAUTOCLAIM atómico por entrada; solo >30s idle; idempotente |
| Consumidores stale en el consumer group (3 observados con 1 réplica) | PEL propio de cada uno se reclama por XAUTOCLAIM; `XINFO` los lista pero no hay fuga funcional — limpieza cosmética |
| `stats.processed_total` cuenta forwards, no entradas | Semántica "intentos de entrega" — consistente con `forward_seconds_total` |
| `send_alert.py` sin validación de esquema de alerta | Herramienta de inyección manual (`make simulate`) — el contrato se valida en ingest |
| `update` store no es CAS (GET+HSET por campos) | Las escrituras de una admission convergen en su consumidor; `state_version` ordena lecturas |

## STRIDE del pipeline

| Amenaza | Control | Estado |
|---|---|---|
| Spoofing (alerta inyectada) | HMAC en el sobre + validación en workflow | ✅ |
| Tampering (registro) | máquina de estados + `state_version` + violation loud | ✅ |
| Repudio | records con TTL 7d + delivery_id + audit chain | ✅ |
| Info disclosure | errores estructurados, `redact_*`, sin secrets en estado | ✅ |
| DoS | MAXLEN acotado, rate-limit en ingest, batch+semaphore, backoff jitter | ✅ |
| Elevación (SSRF via forward) | egress allowlist + sin credenciales en URL | ✅ |

## Regresión

- **19/19 gates** `test_messaging_pipeline.py`.
- **243/243** `tests/unit/infrastructure/` + gates (incluye 3 tests nuevos del lease).
- Verificado en vivo: lease atómico/renovado, pipeline e2e, métricas.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Fiabilidad (entrega/recuperación) | 8.5 → **9.5** — lease atómico + TTL coherente |
| Corrección de concurrencia | 7.5 → **9.5** — TOCTOU eliminado, tests de carrera |
| Seguridad (egress/firma) | 9.0 → **9.5** |
| Observabilidad | 9.0 → **9.5** — métricas reales pull-model |
| Mantenibilidad | 8.5 → **9.5** — 19 gates nuevos |
| **Global** | ~8.6 → **~9.5** |
