# Evaluación API custom SOAR — OWASP ASVS / OWASP API Security Top 10 / ISO 27034

> **Fecha**: 2026-11-12 · **Suite**: `tests/architecture/test_api_app.py` (9 gates de middleware + postura) · **Resultado**: sin defectos nuevos — los controles ASVS ya están gateados.

## Matriz por dimensión

| Dimensión | ASVS / Top10 | Evidencia verificada |
|-----------|--------------|----------------------|
| **AuthN** | ASVS V2 / API2 | `require_api_auth` (Bearer JWT o `X-Service-Token`), fail-closed por defecto (`API_REQUIRE_AUTH`), `DefaultDenyAuthMiddleware` whitelist mínima — live: **401 sin credenciales, antes de parsear body** |
| **AuthZ** | ASVS V4 / API1+API5 | RBAC `Role` + `auth_service.can_access_endpoint` por path+method; tokens de servicio con scopes least-privilege (gate); audit log por denegación |
| **Validación entradas** | ASVS V5 / API8 | Pydantic v2 schemas por ruta, `PayloadSanitizer` (redacción de secretos en alertas/webhooks), `BodyLimitMiddleware` pre-auth (gate de orden), contrato Schemathesis (`test_schemathesis_contract.py`) |
| **Rate limiting** | ASVS V11 / API4 | `PreAuthRateLimitMiddleware` **externo a auth** (previene auth-flood) + `RateLimitMiddleware` con store Redis sliding-window (no in-memory en producción — gate `composition_rejects_workers_with_memory_backends`) + headers `X-RateLimit-*` |
| **Error handling** | ASVS V7 / API7 | `_register_exception_handlers`: HTTPException→ErrorResponse uniforme; Exception→mapa tipado, ≥500 → mensaje genérico (sin fuga de internals); `error_status` por tipo |
| **Trazabilidad** | ASVS V7 / API9 | `TraceIdMiddleware` outermost → `x-request-id` en cada respuesta (live: `01a1cfbb…`) + `trace_id_ctx` propaga a logs; auditoría auth con principal+veredicto |
| **Observabilidad** | ASVS V10 | Métricas Prometheus, OTEL traces, health/readiness endpoints, audit trail auth; warning log si `API_REQUIRE_AUTH` off (fail-visible) |
| **Arquitectura hexagonal** | ISO 27034 | Composition root en `composition.py`; dominio sin FastAPI/frameworks (ports+adapters); rutas delegadas a `routes_*`; `app.state` como única inyección |

## Positivos confirmados (sin fix necesario)

Orden de middlewares gateado: Trace → SecurityHeaders → BodyLimit → PreAuthRateLimit → DefaultDenyAuth · `Server` header deshabilitado (Dockerfile gate) · whitelist pública mínima · secrets nunca en responses (redaction.py) · HSTS/XCTO/XFO en cada response (live).

## Residuales (restricciones, no deuda)

| Restricción | Naturaleza |
|-------------|------------|
| Service tokens por scope fijo (sin rotación auto) | Rotación manual vía `make rotate-secrets` — documentado |
| JWT sin refresh endpoint propio | El SSO (Keycloak) es el IdP de sesión; el API emite tokens de servicio — separación deliberada |
