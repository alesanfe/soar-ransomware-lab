# Evaluación Admission Pipeline — NIST Reliability / CNCF Resiliency Patterns

> **Fecha**: 2026-11-12 · **Resultado**: **2 defectos corregidos** (bound de backoff auto-violado + fencing dead-store). Score ~9,6/10.

## Defectos corregidos

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| PIPE-EVAL-001 | **`retry_cap_s=32s` violaba su propio invariante documentado** — el comentario decía "30s > max delay 32s" (falso) y "keep retry_cap_s < stale_ms". El clamp `stale_ms/2000` lo hacía seguro en runtime pero el default contradecía el contrato | Default → `16.0` + `ValueError` fail-loud si `retry_cap_s*1000 >= stale_ms` | Gate: default 16 < 30 + guard presente |
| PIPE-EVAL-002 | **`fence_token` capturado pero nunca consultado** — dead store: un líder pausado que pierde y readquiere el lease ejecuta singleton duties sobre liderazgo stale | Detección de rotación: token distinto del previo → skip del ciclo con warning | Gate: `token != self._fence_token` → `return False` |

## Matriz por dimensión

| Dimensión | Patrón CNCF/NIST | Estado verificado |
|-----------|------------------|-------------------|
| **Idempotencia** | Idempotent receiver | Bind atómico vía Lua + dedup terminal check + **fail-safe defer** (store ilegible → pendiente, nunca re-forward) + `delivery_id` por intento + `idempotency_key` en envelope firmado |
| **DLQ** | Dead Letter Queue | `dead_letter` con `reason` estructurada · lifecycle real (list/redrive/purge) · auto-redrive acotado (max 3, min_age 60s, **skips decode_failed poison**) · `log.error` operator-visible |
| **Retry** | Exponential backoff + jitter | Full-jitter AWS (`uniform(0, min(cap, base·2^n))`) · `max_attempts=5` · retryable classification por error_code · attempts tracking |
| **Backpressure** | Load shedding | `depth ≥ 50_000` → **503 + Retry-After** · stream bounded (XADD MAXLEN) · semaphore concurrency=4 · batch=10 |
| **Ordering** | FIFO stream | XREADGROUP `" >"` (entry-id ordered) · state machine `check_transition` + `state_version` por admisión (orden a nivel registro; alertas independientes no requieren orden global — documentado) |
| **Observabilidad** | Metrics + alerting | WorkerStats completo → `/metrics` · alertas: `soar_dlq_not_empty`, consumer lag >50, `admission_dead_rate`, **SLO burn-rate 99%** |
| **Recuperación** | Recovery / leader election | `recover()` **periódico** (no solo boot) XAUTOCLAIM · duties singleton **lease-guarded** + fencing rotation · reconciler repara orphans `enqueue_failed` · release en shutdown |

## Positivos destacados

- `return_exceptions=True` en gather — fallo de una entrada nunca cancela el batch (WORKER-001)
- Backoff ANTES de forward con entry pending — bound cap<stale ahora **enforced**, no solo documentado
- Envelope firmado (`sign_envelope`) + egress allowlist en forward (gates previos)
- Suite de unit tests del usuario (`test_messaging_contracts.py`) con oráculos de args XREADGROUP/XAUTOCLAIM, envelope contract, DLQ semantics — mutación-ready

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| At-least-once, no exactly-once | Imposible en transporte distribuido; mitigado por dedup terminal + delivery_id — el workflow downstream también debe tolerar re-entrega (documentado) |
| Orden estricto global | No requerido: alertas independientes; orden por-admisión preservado vía state machine |
| Fencing no transaccional | La rotación se detecta al siguiente ciclo — la ventana residual es inherente a fencing por polling (mitigada por lease TTL < ciclo de duties) |

## Verificación live (Redis TLS real)

Drill `scripts/debug/drill_admission_recovery.py` ejecutado en `soar_api` contra el Redis productivo (stream scratch `soar:drill:*`, sin tocar `soar:admissions`):

- **Crash recovery**: consumidor lee sin ack → `pending:1` → `claim_stale` (XAUTOCLAIM) recupera → ack → `pending:0` ✅
- **DLQ lifecycle**: `dead_letter` → `dlq_list` (reason+payload) → `dlq_redrive` → re-entregado y acked → `dlq_size:0` ✅
- **Métricas live**: `/metrics` expone `soar_queue_depth`, `soar_queue_pending`, `soar_queue_consumer_lag`, `soar_queue_dlq_size`, `soar_queue_available`, `soar_admission_{processed,forwarded,retried,dead}_total` ✅

## Regresión

`test_messaging_pipeline.py`: **21 gates** · `test_messaging_contracts.py`: **111/111** unit (2 expectativas del cap antiguo actualizadas: `32.0 → 16.0` + invariante `cap·1000 < stale_ms` ahora también en el test de defaults) · architecture suite completa: **351/351** en `soar_api`.
