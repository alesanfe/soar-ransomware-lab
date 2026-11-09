# ADR-0003: Idempotencia atómica SET NX + fingerprint de contenido

**Estado**: Aceptado · **Evidencia**: IDEMP-001/002/003

## Contexto

Sin `Idempotency-Key` explícita, el fallback era un `alert_id` aleatorio —
dos alertas idénticas reenviadas jamás dedupeaban, y un retry de Shuffle
podía disparar el workflow dos veces.

## Decisión

- `AlertAdmissionUseCase.admit()` calcula `fingerprint =
  SHA-256(contenido canónico JSON menos ids volátiles)` cuando no hay key
  explícita — idénticas colapsan, distintas jamás.
- La clave se reclama atómicamente con `SET key val NX` (`try_bind_key`);
  el registro de admission guarda estado `pending|queued|forwarded|dead`.
- `X-Idempotency-Key` se propaga al webhook de Shuffle con la key
  efectiva, estampada también en el body para trazabilidad.
- Concurrencia: dos admits simultáneos de la misma alerta → uno gana NX,
  el otro recibe la admission existente (no duplica).

## Consecuencias

- Dedupe correcto bajo retries y bajo fan-in concurrente.
- Un cambio semántico mínimo en cualquier campo altera el fingerprint —
  intencional: solo **idénticas** dedupean.
