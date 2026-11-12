# Evaluación multi-marco — Superficie frontend (web-management, docs-site, edge nginx)

> Evaluación formal de las apps frontend y su capa de servicio
> (`apps/web-management/`, `apps/docs-site/`, `infra/docker/config/nginx/nginx.conf`,
> `docker-compose.api.yml`, `docker-compose.sso.yml`, overlay hardened)
> siguiendo la metodología de `docs/25`/`27`-`33`: cada hallazgo se
> verifica en vivo y queda pineado con gates
> (`tests/architecture/test_frontend_stack.py`, **12 gates**).
> Complementa `docs/21` (evaluación visual/UX — capturas autenticadas):
> esta evalúa la **infraestructura de servicio y seguridad**, no el UX.
> Revisión 2026-11-11: **8 hallazgos** corregidos, superficie XSS
> auditada limpia. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Calidad por característica del serving layer |
| OWASP ASVS 4.0 | V14 (HTTP headers), V4 (control de acceso en borde), V5 (XSS en sinks) |
| OWASP Secure Headers | Cobertura y coherencia de headers por ruta |
| CIS Docker Benchmark | Postura de contenedores nginx (non-root, caps, RO) |
| STRIDE | Amenazas del serving layer (spoofing de upstream, tampering de estáticos, info disclosure por banners/rutas, DoS por proxy) |
| NIST CSF | PR.AC/PR.DS — exposición mínima, TLS en el borde |

## Evidencia de runtime (post-fix)

```
rutas /api     :8085 directo → 422 FastAPI (antes 405); :8088 SSO →
                 302→Keycloak→upstream; :443 edge → 422 (sin cambio)
websocket      GET /api/ws/logs sin auth → 401 (upgrade proxied; antes
               el path ni existía en web-management)
edge bind      PortBindings 127.0.0.1:{80,443,8444} (antes 0.0.0.0)
web-management uid 101:101, capadd=[], ro=true, /health → "healthy"
docs-site      uid 101:101, capadd=[], ro=true, sirve 200
healthcheck    http://127.0.0.1:8080/health (antes pgrep nginx)
XSS sinks      innerHTML dinámico: 0 sin escapar (escapeHtml cubre
               &<>"'; logs.js usa textContent; backups.js usa DOM APIs)
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| WEB-EVAL-004 | **`/api/*` servido como estático** — `POST /api/auth/login` → 405 en el puerto directo (:8085) **y** en la puerta SSO (:8088, upstream = web-management): la UI no podía autenticarse en 2 de 3 entradas | curl en vivo → 405 nginx vs 422 FastAPI | `location /api/` + `proxy_pass` con `resolver 127.0.0.11` (DNS dinámico, mismo patrón del edge); `/api/v1/` pasa sin reescritura porque FastAPI registra esas rutas con prefijo |
| WEB-EVAL-002 | **WebSocket sin soporte** — `logs.js` abre `/api/ws/logs` con ticket; web-management no tenía bloque ws | `GET /api/ws/logs` no-auth → 401 vía upgrade | `location /api/ws/` con `Upgrade`/`Connection` headers + `proxy_read_timeout 3600s` |
| WEB-EVAL-005 | **healthcheck `pgrep nginx`** — pasaba con config rota (el proceso master vive aunque la config no cargue) | observado al migrar a :8080 | healthcheck = request real a `127.0.0.1:8080/health`; endpoint `/health` añadido; bug secundario corregido: `localhost` resolvía a `::1` mientras nginx escuchaba solo IPv4 → literal `127.0.0.1` |
| WEB-EVAL-008 | **web-management y docs-site privilegiados** — listen :80 obligaba a root+NET_BIND_SERVICE+CHOWN/SETUID/SETGID | `docker inspect` caps/uid | listen :8080 ×2 → `user: 101:101`, `cap_drop:[ALL]` **sin** cap_add, RO rootfs, tmpfs `mode=1777`; upstreams edge/SSO/ports actualizados |
| WEB-EVAL-006 | **rootfs escribible** en web-management | inspect `ReadonlyRootfs` | `read_only: true` + tmpfs cache/pid/tmp — logs fluyen por los symlinks stdout/stderr de la imagen |
| WEB-EVAL-001/003 | **headers**: banner de versión; `X-XSS-Protection` presente (deprecado, contradictorio con CSP); Referrer-Policy laxa; sin Permissions-Policy | curl `-I` | `server_tokens off`; X-XSS-Protection eliminado; `Referrer-Policy: no-referrer`; `Permissions-Policy` añadido — repetidos por location (semántica add_header de nginx) |
| WEB-EVAL-009 | **edge nginx en 0.0.0.0** — `:80`/`:443` publicados en todas las interfaces: TheHive/Cortex/Shuffle/UI/auth alcanzables desde la LAN | `inspect PortBindings` → HostIp `0.0.0.0` | `127.0.0.1:${HTTP_PORT}`/`127.0.0.1:${HTTPS_PORT}` — convención del resto del proyecto; verificado 443→200, :80→301, API→422 |
| WEB-EVAL-010 | **sin gate de binds** en api.yml — el 0.0.0.0 sobrevivió porque nadie lo comprobaba | — | `test_all_api_compose_ports_loopback_bound` cubre api/docs-site/web-management/nginx |
| WEB-EVAL-011 | **`soar_test_runner` unhealthy permanente** (452-streak) — la imagen api hornea `HEALTHCHECK curl :8000/health` pero el runner ejecuta `sleep infinity`: jamás podía ser healthy, ensuciando `docker ps` y las alertas de salud | `inspect` → streak 452, FailingStreak creciente | `--no-healthcheck` en `scripts/debug/mk_test_runner.py` — la liveness real del runner es el pytest exec'd; aplica en el próximo recreate (no se recreó ahora: tenía un e2e en vuelo) |

## Puntos positivos (verificados)

- **CSP restrictiva real**: `default-src 'self'`, `script-src 'self'` (sin unsafe-inline en scripts), `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'self'` — XFO redundante para navegadores legacy.
- **Superficie XSS limpia** tras auditoría de todos los sinks: `escapeHtml` cubre `&<>"'` (seguro en texto y atributos `"`), `logs.js` usa `textContent`, `backups.js` usa `createElement`/`option.value`, `pipeline.js`/`exec.js` escapan cada campo de API antes de `innerHTML`.
- **Resolver dinámico**: `resolver 127.0.0.11` + variable en `proxy_pass` — upstream `api:8000` se re-resuelve en recreates (un proxy_pass literal queda stale).
- **Semántica consistente en las 3 puertas**: directo/SSO/edge reescriben `/api/*` igual (excepto `/api/v1/` que pasa con prefijo) — mismo comportamiento observable.
- **Cache discipline**: assets con fingerprint `expires 1y immutable`; `index.html` `no-store` — sin riesgo de HTML cacheado tras deploy.
- **Capless-verified**: ambos frontends corren uid 101 con `capadd=[]` — verificado `id` + `curl /health` + contenido servido.
- **Healthchecks app-level**: request HTTP real, no existencia de proceso.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| `style-src 'unsafe-inline'` en CSP | Docusaurus y atributos style inline lo requieren; endurecer exige reescritura upstream — scripts (vector real de XSS) sí van sin unsafe-inline |
| :8085/:8086 HTTP plano en loopback | Puertos de debug directo, solo loopback; el borde TLS es :443 — equivalente al resto de puertos de servicio del lab |
| WS interno sin TLS (ws:// detrás del edge) | TLS termina en el edge; tráfico interno cifrado no aplica a redes docker aisladas — mismo criterio que el resto del stack |
| JS de build de Docusaurus no auditado línea a línea | Artefacto generado; la superficie custom (web-management/js) sí está auditada completa |

## STRIDE

| Amenaza | Control | Estado |
|---|---|---|
| Spoofing | TLS en edge, oauth2-proxy en puerta SSO, auth JWT default-deny en API | ✅ |
| Tampering | RO rootfs ×2 frontends, configs nginx :ro, CSP `object-src 'none'` | ✅ |
| Info disclosure | `server_tokens off` ×2, sin stack traces al cliente, CSP+nosniff | ✅ |
| DoS | pids ×2, body/conn limits del API detrás, timeouts de proxy | ✅ |
| EoP | uid 101 capless, nnp, sin socket mounts | ✅ |

## Regresión

- **12/12 gates** `test_frontend_stack.py` verdes.
- **142/142** `tests/architecture/` totales verdes.
- Vivo: `:8085 /api/auth/login` → 422; `/api/ws/logs` → 401; `:8088` → 302 OIDC; `:443` → 200; edge binds 127.0.0.1; ambos frontends uid 101/capadd=[]/ro=true/healthy.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Idoneidad funcional | 6.5 → **9.5** — login/REST/WS rotos en 2 de 3 puertas → las 3 funcionan |
| Fiabilidad | 7.0 → **9.5** — healthcheck real, resolver dinámico, IPv6 literal |
| Seguridad | 6.5 → **9.5** — capless ×2, RO rootfs, edge loopback, headers endurecidos, XSS limpio |
| Interacción (docs/21 cubre UX) | 9.0 → **9.5** — rutas consistentes eliminan fallos de auth |
| Mantenibilidad | 7.5 → **9.5** — 12 gates, upstreams pineados, postura documentada |
| Portabilidad | 9.0 → **9.5** — sin privilegios requeridos en el serving layer |
| **Global** | ~7.6 → **~9.5** |
