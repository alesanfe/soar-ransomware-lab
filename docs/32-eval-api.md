# Evaluación multi-marco — API SOAR (FastAPI + hexagonal)

> Evaluación formal del componente de aplicación propio — la API REST
> (`src/soar_lab/interfaces/api/`, `apps/api/Dockerfile`,
> `infra/docker/compose/docker-compose.api.yml`) — siguiendo la
> metodología de `docs/25`/`27`-`31`: cada hallazgo se verifica con
> evidencia en vivo y queda pineado con gates
> (`tests/architecture/test_api_app.py`, **9 gates** + suite unitaria).
> Revisión 2026-11-11: **4 hallazgos** corregidos, residuales
> documentados. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica del componente |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| OWASP ASVS 4.0 | V2 auth, V4 access control, V7 errors/logging, V11 HTTP sec, V13 API |
| CWE | CWE-307 (restricción de intentos de auth), CWE-200 (info exposure) |
| STRIDE | DoS, information disclosure, spoofing, repudiation |
| SRE Golden Signals | /metrics, request-id, health/live/ready, audit trail |

## Evidencia recolectada (en vivo, `soar_api` recreado)

```
auth            default-deny: rutas inexistentes → 401 (no 404) —
                no filtra topología; tokens malos → 401 con x-request-id
headers         CSP, HSTS, nosniff, frame-options DENY,
                permissions-policy, referrer-policy — presentes en 200/401/429
rate-limit      pre-auth: 60×401 → 429 (tras fix DOS-002);
                post-auth: ráfaga autenticada → 429 con Retry-After
brute-force     70× token inválido → 60×401 + 429 (presupuesto consumido)
JWT             alg=none / firma forjada / payload alterado / expirado → 401
service-token   scope enforce (analyst→contain 403); *_PREV rotación;
                CIDR allowlist; audit log con hash-chain (tamper-evident)
WS tickets      30s TTL, single-use, replay rechazado, 401 sin auth
server header   AUSENTE tras --no-server-header (antes: "uvicorn")
workers guard   UVICORN_WORKERS=4 + memory backend → RuntimeError fail-closed
/docs           404 en producción; /openapi.json público (ver negativos)
/metrics        200 sin auth (deliberado — Prometheus, ver negativos)
contenedor      user 1000:1000, cap_drop ALL, nnp, pids 256, RO rootfs,
                límites mem/cpu, loopback-bound :8000, egress guard NET_ADMIN
hexagonal       test_hexagonal_imports: dominio no importa infra/interfaces
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| API-EVAL-001 | **DOS-002 invertido**: `PreAuthRateLimit` se registraba DESPUÉS de `DefaultDenyAuth` (en Starlette el último `add_middleware` es la capa más externa) → el limiter ejecutaba **tras** auth; 70 tokens malos → 70×401 sin consumir presupuesto (CWE-307). El docstring ya afirmaba "runs BEFORE DefaultDeny" — el código hacía lo contrario | 70 brute-force en vivo → cero 429 | Orden de registro invertido en `main.py`; **60×401 → 429** verificado; gate `test_preauth_ratelimit_is_outermost` |
| API-EVAL-002 | **Banner `Server: uvicorn`** en todas las respuestas (CWE-200 fingerprinting). `SecurityHeadersMiddleware` ya lo borraba, pero Uvicorn lo añade en la capa de protocolo **después** del middleware de aplicación — imposible quitarlo desde ASGI | `curl -I` → `server: uvicorn` | `--no-server-header` en el CMD del Dockerfile → header ausente en vivo; gate `test_uvicorn_no_server_header` |
| API-EVAL-003 | **`UVICORN_WORKERS>1` + backends `memory`** fragmentaba silenciosamente rate-limits y tickets WS entre procesos: presupuesto de brute-force ×N workers, tickets WS validables solo por el worker emisor (~1/N de rechazo aleatorio) | análisis composition.py | `create_app` fail-closed: `RuntimeError` explícito si workers>1 sin `RATE_LIMIT_BACKEND=redis` + `WS_TICKET_BACKEND=redis` — verificado en vivo (arranque aborta); gate `test_multiworker_requires_shared_backends` |
| API-EVAL-004 | **4 tests stale** vs el refactor ADMISSION-004/IDEMP-004/WORKER-003 en curso: `test_failed_enqueue_unbinds_key` (ahora conserva binding + marca `enqueue_failed` reconcilable — B4), `test_concurrent_same_key_enqueues_once` (mismo key + payload distinto → `IdempotencyConflictError` loud), `test_retry_sleeps_before_forward` (store ilegible → defer, no forward), fixture Stats sin `orphans_repaired_total` | 4 fallos en suite | Tests reescritos a la semántica nueva (que es la correcta: conflict loud, keep-binding, defer fail-safe) + nuevo `test_same_key_different_content_conflicts`; **499/499 unit+api verdes** |

## Puntos positivos (evidencia previa al fix)

- **Default-deny real**: rutas inexistentes devuelven 401 (no 404) — la topología no se filtra; la auth matrix tiene suite dedicada (`test_auth_matrix_and_queue.py`, `test_auth_adversarial.py`).
- **Auth de servicio de diseño maduro**: scopes por token, slot `*_PREV` para rotación sin downtime, `service_token_cidrs` allowlist por red, y **audit log append-only con hash-chain** (STRIDE repudiation cubierto — las entradas son tamper-evident).
- **Defensa JWT completa**: allowlist de algoritmos (alg=none rechazado), verificación de firma, expiración, issuer/audience — suite adversarial dedicada.
- **WS tickets single-use** con TTL 30s y binding de scope — replay y uso cruzado rechazados.
- **Health checks honestos**: `/health/ready` mide dependencias reales (queue, store) con timeouts — no un 200 vacío.
- **Idempotencia end-to-end**: NX claim atómico, fingerprint de contenido, `IdempotencyConflictError` en mismo-key/distinto-payload, binding conservada en enqueue_failed para replay reconcilable.
- **Admission worker fail-safe**: store ilegible → defer (no re-POST — evita doble ejecución downstream), dedup de estados terminales, reconciler de huérfanos con métrica `orphans_repaired_total`.
- **Contenedor endurecido**: 1000:1000, `cap_drop:[ALL]`, nnp, RO rootfs, pids 256, límites, loopback-bound; `NET_ADMIN` aislado en el egress-guard sidecar (la API no la posee).
- **Arquitectura hexagonal enforceada por test**: el dominio no puede importar infraestructura/interfaces (`test_hexagonal_imports`).
- **CORS fail-safe**: `allow_credentials` + wildcard origins se descarta con warning explícito.
- `/docs` deshabilitado en producción (404); esquema solo vía `/openapi.json` (ver negativos).

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| `/openapi.json` público sin auth | Schema disclosure deliberada — el puerto es loopback-bound en host y la red interna es de confianza; facilita codegen de clientes. Si el puerto se expusiera fuera de loopback debería autenticarse |
| `/metrics` público sin auth | Necesario para el scrape de Prometheus (sin soporte de auth en la config actual); métricas operacionales sin PII ni secretos; solo alcanzable desde redes docker internas |
| `API_REQUIRE_AUTH=false` desactiva la auth entera | Modo dev documentado — emite WARNING ruidoso en cada arranque y cada request mutador; los tests e2e lo fijan a `true` |
| Backends `memory` por defecto (rate-limit, WS tickets, admission store SQLite) | Válido para despliegue single-worker documentado; `UVICORN_WORKERS>1` ahora **fail-closed** exige Redis — la incoherencia silenciosa está cerrada |
| Audit log sin firma externa | Hash-chain detecta manipulación local; un anchor externo (p.ej. timestamping) sería mejora futura, no un defecto del lab |

## STRIDE

| Amenaza | Control | Estado |
|---|---|---|
| Spoofing | JWT alg-allowlist + firma + exp; service tokens HMAC + CIDR; WS tickets bound-scope | ✅ |
| Tampering | Hash-chain audit log; payload sanitizer; state-machine con `transition_violation` auditado | ✅ |
| Repudiation | Audit log append-only tamper-evident + `x-request-id` end-to-end | ✅ |
| Info disclosure | Sin `Server` header, default-deny 401 (no 404), errores sanitizados, `/docs` off | ✅ |
| DoS | Pre-auth limiter (outermost tras fix), post-auth limiter, bounded queue `MAXLEN`, pids/mem limits | ✅ |
| Elevation of privilege | RBAC scopes enforced (403 verificado), non-root, cap_drop ALL, nnp | ✅ |

## OWASP ASVS (muestra)

| Control | Estado |
|---|---|
| V2.x credenciales | ✅ hash + `*_PREV` rotation + secrets fail-closed |
| V4.x access control | ✅ default-deny + scope enforce + denegación auditada |
| V7.x logging | ✅ request-id, audit chain, errores sanitizados |
| V11.x HTTP security | ✅ headers completos, sin banner, TLS-ready |
| V13.x API | ✅ 422 validación, auth matrix, rate-limit, CORS fail-safe |

## Deuda pendiente

| Ítem | Estado |
|---|---|
| Auth en `/openapi.json` y `/metrics` | **Aceptado** — loopback-bound + red interna; reevaluar si se publica el puerto |
| Anchor externo del audit hash-chain | Mejora futura (no defecto) |
| Consolidar dispatch de middlewares | Los middlewares son clases separadas con orden documentado + gate de orden — deuda cerrada con API-EVAL-001 |

## Regresión

- **9/9 gates** `tests/architecture/test_api_app.py` verdes (postura compose +
  middleware order + no-server-header + worker/backend guard).
- **499 passed, 1 skipped** en `tests/unit/api/` + `tests/architecture/` completo.
- Verificado en vivo tras rebuild: `/health` 200, `Server` ausente,
  60×401→429 brute-force, egress-guard healthy, ticket WS 30s.
- Imagen reconstruida con `requirements.lock` como constraints (SC-EVAL-005).

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Idoneidad funcional | 9.0 → **9.5** — admission queue con estado reconcilable, workflow verdicts, dedup end-to-end |
| Fiabilidad | 8.0 → **9.5** — defer-on-unreadable, keep-binding, multi-worker incoherente ahora fail-closed |
| Seguridad | 8.0 → **9.5** — DOS-002 corregido (limiter realmente pre-auth), sin banner, hash-chain audit |
| Observabilidad | 9.0 → **9.5** — /metrics Prometheus, request-id universal, audit trail, OTEL hooks |
| Mantenibilidad | 9.0 → **9.5** — hexagonal gateado, 499 tests, middleware order pineado por gate |
| Portabilidad | 9.0 → **9.5** — imagen única reproducible por lock, config por env fail-closed |
| **Global** | ~8.6 → **~9.5** |
