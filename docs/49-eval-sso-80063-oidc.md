# Evaluación SSO (Keycloak + oauth2-proxy) — ISO 27001 A.5/A.8, NIST SP 800-63, OIDC/OAuth2 BCP

> **Fecha**: 2026-11-12 · **Suite**: `tests/architecture/test_sso_stack.py` (18 gates) · **Resultado**: defectos estructurales corregidos, TLS end-to-end verificado en vivo.

## 1. Defectos encontrados y corregidos

| ID | Severidad | Defecto | Fix | Evidencia |
|----|-----------|---------|-----|-----------|
| SSO-EVAL-004 | **Alta** | **Todo el plano SSO en HTTP plano** — IdP, backchannel token/JWKS y proxies sin TLS; cookies `secure:false` | CA-lab en los 3 servicios: KC `--https-certificate-*` (8443), proxies `TLS_CERT/KEY_FILE` + `COOKIE_SECURE:true` + `SameSite:lax` | `https://localhost:8072/` → 302 → `https://localhost:8071/.../auth` verificado; log proxy `secure(https):true` |
| SSO-EVAL-005 | **Alta** | **Puertos 8087-8089 inalcanzables** — caían en el rango excluido de Hyper-V (8081-8180): el overlay entero no funcionaba desde el host | `KEYCLOAK_PORT=8071`, `OAUTH2_WEB/SHUFFLE_PORT=8072/8073` (ventana libre 8069-8080) | host: `https://localhost:8071/...discovery` → 200 |
| — | Media | `start-dev` fuerza listener HTTP `:8080` ignorando `--http-enabled`; `--http-host` ata **todos** los listeners | Migrado a `kc.sh start --db dev-file` (modo producción, auto-build): honra `--http-enabled=false` | log: `Listening on: https://0.0.0.0:8443` únicamente; http refused desde soar_net |
| — | Media | Healthcheck HTTP sobre mgmt **HTTPS**:9000 — nunca pasaba a `healthy` (proxies colgaban de `service_healthy`) | Probe Java single-file `HttpsURLConnection` real | `soar_keycloak (healthy)` por primera vez |
| — | Media | Sin MFA | `CONFIGURE_TOTP` required action en los 2 usuarios (AAL2 NIST 800-63B) | gate `test_mfa_required_action_on_all_users` |
| — | Media | Refresh tokens no rotaban | `revokeRefreshToken:true` + `refreshTokenMaxReuse:0` (rotación por uso, OAuth2 BCP) | realm reimportado (OVERWRITE) |
| — | Baja | `implicitFlowEnabled` implícito | `false` explícito | gate |
| — | Baja | Prometheus scrapeaba SSO en HTTP (3 targets rotos tras TLS) | Movidos al job `blackbox-https` (módulo `https_2xx`, CA lab) | `prometheus.yml` + gate actualizado |

## 2. Matriz por dimensión pedida

| Dimensión | Marco | Estado |
|-----------|-------|--------|
| **MFA** | NIST 800-63B AAL2 | `CONFIGURE_TOTP` obligatorio en primer login — enroll forzado, verificado en realm importado |
| **Token lifecycle** | NIST 800-63C / OAuth2 BCP | access 300s, session max 8h, idle 30min, **refresh rotativo** (revoke-on-use), `implicit`/`password`/`client_credentials` off en el cliente |
| **Refresh/revoke** | RFC 7009 | `revocation_endpoint` anunciado en discovery; rotación activada |
| **Roles** | ISO A.8.2 | 6 realm roles (platform-admin…auditor) vía mapper `roles` en id+access+userinfo; asignaciones least-privilege |
| **Sesiones** | ISO A.5.17 | idle 1800s / max 28800s; cookies `Secure+HttpOnly+SameSite:lax`, expiry 168h; brute-force protection on |
| **Cabeceras** | OWASP/800-63 | Live verificadas: **HSTS 1año**, `X-Content-Type-Options`, `X-Frame-Options` |
| **Federación** | NIST 800-63C | No habilitada (lab sin IdP externo) — decisión documentada, no deuda |
| **Logout** | OIDC RP-initiated | `end_session_endpoint` anunciado; oauth2-proxy `/oauth2/sign_out` limpia cookie local — RP-initiated backchannel al IdP es limitación upstream del proxy (documentada) |
| **Secreto lifecycle** | ISO A.5.17 | Realm es plantilla con placeholders (`__OIDC_CLIENT_SECRET__`) renderizados por entrypoint — fail-closed |

## 3. Verificación viva

```
proxy https://localhost:8072/ → 302 → https://localhost:8071/.../auth (authorization_code, redirect https)
keycloak discovery https → 200 · issuer https://localhost:8071 · endpoints https
http://keycloak:8080 → ConnectionRefused (listener eliminado)
auth page → 200 · HSTS/XCTO/XFO presentes
soar_keycloak (healthy) — probe HTTPS real
```

## 4. Residuales (restricciones externas)

| Restricción | Naturaleza |
|-------------|------------|
| RP-initiated logout no propaga al IdP | oauth2-proxy no implementa backchannel logout (upstream); la sesión IdP expira por idle (30min) |
| Sin federación/LDAP | Lab sin directorio externo — decisión de diseño |
| Session store en cookie cifrada | Redis session store disponible en oauth2-proxy si se requiere revocación instantánea — no activado (cookie AES cifrada con `OAUTH2_PROXY_COOKIE_SECRET`) |
| `kc.sh start` auto-build en boot | Coste ~15s extra de arranque; imagen `optimized` sería el siguiente paso si se requiere |
