# ADR-0002: Autenticación default-deny + RBAC por rutas

**Estado**: Aceptado · **Evidencia**: AUTH-001/003/004, BUG-126

## Contexto

Las rutas dependían de `Depends(require_api_auth)` por endpoint — una ruta
nueva que olvidara el `Depends` quedaba pública por omisión. Los roles
existían en el modelo pero `can_access_endpoint` nunca se llamaba.

## Decisión

`DefaultDenyAuthMiddleware` protege **toda** ruta HTTP fuera de la
whitelist pública (`/`, `/health*`, `/metrics`, `/docs`, `/redoc`,
`/openapi.json`, `/auth/*`, `/static*`, `/favicon*`). El JWT lleva claim
`role`; `require_api_auth` además aplica `can_access_endpoint` sobre la
superficie real (admin→`/backup`,`/tests/run`,`/api/v1/audit`;
operator→`/api/v1/contain`,`/api/v1/queue/*`; analyst→`POST
/api/v1/alerts`,`/api/v1/cache/ioc`; viewer→solo lectura). Cada decisión
allow/deny/401 se audita vía `_audit_access` expuesta en
`GET /api/v1/audit` (admin-only). Token principal cacheado en
`request.state` para no auditar dos veces por request.

## Consecuencias

- Una ruta futura sin `Depends` sigue protegida — el riesgo residual es
  que un endpoint quede clasificado en un tier equivocado del mapa RBAC
  (mitigado por tests de matriz rol×ruta).
- JWTs emitidos antes del claim `role` se tratan como `admin`
  (retrocompatibilidad documentada).
