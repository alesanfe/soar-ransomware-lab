# Evaluación Frontend Serving — CIS Docker / OWASP ASVS / NIST 800-190

> **Fecha**: 2026-11-12 · **Resultado**: **2 defectos corregidos** (header deprecado + TLS débil en shuffle-frontend). Score ~9,6/10.

## Defectos corregidos

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| EDGE-EVAL-001 | `X-XSS-Protection "1; mode=block"` activo en edge nginx y shuffle-frontend — header **deprecado** que puede debilitar navegadores modernos (la guía actual recomienda su ausencia; CSP lo supersede) | Eliminado en ambos + gate que lo prohibe en las 4 configs nginx | `test_no_x_xss_protection_header` parametrizado ×4 |
| EDGE-EVAL-002 | shuffle-frontend: `ssl_protocols TLSv1 TLSv1.1 TLSv1.2` — **TLS 1.0/1.1 habilitados** (deprecados RFC 8996) | `TLSv1.2 TLSv1.3` alineado con la política del edge | `test_no_tls_below_1_2` parametrizado ×4 |

## Matriz por dimensión

| Dimensión | Marco | Estado |
|-----------|-------|--------|
| **Hardening nginx** | CIS 5.x / ASVS 14 | `server_tokens off` en las 4 configs · headers por-location (repetidos a propósito — un `add_header` a nivel location suprime la herencia, comentado en conf) · `error_page` custom · `try_files` SPA |
| **Non-root** | CIS 4.1 / NIST 800-190 §4 | web-management + docs-site: `user: 101:101` (uid nginx) sobre puerto no privilegiado `:8080`. Edge: root→worker nginx (necesita :80/:443, compensado por caps mínimas) |
| **Capabilities mínimas** | CIS 5.3 / 800-190 | Frontends: `cap_drop: [ALL]` **sin cap_add** (postura capless, gateada). Edge: `cap_add [NET_BIND_SERVICE, CHOWN, SETUID, SETGID]` — las 4 mínimas documentadas en AGENTS |
| **CSP** | ASVS 14.4.7 | web-management: `default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'`. docs-site más estricta (`frame-ancestors 'none'`). Edge: CSP laxa global porque frontea apps de terceros (TheHive/Shuffle/Grafana la necesitan) — las CSP estrictas viven en la capa interna por app |
| **HSTS** | ASVS 14.4.5 | Edge :443 `max-age=31536000; includeSubDomains` · :80 solo `/nginx-health` + `301 → https` (gate) |
| **TLS** | NIST 800-190 / ASVS 9 | Edge: TLS 1.2/1.3 únicamente, `HIGH:!aNULL:!MD5`. **`proxy_ssl_verify on` + trusted cert + SNI** — los upstreams HTTPS se verifican contra la CA del lab (defensa contra MITM interno). shuffle-frontend ahora ≥1.2 |
| **Healthchecks** | CIS 5.8 / 800-190 | web-management: `/health` a nivel app (WEB-EVAL-005 gateado). docs-site: probe sobre el **baseUrl real** (`/soar-ransomware-lab/` — ejerce el contenido servido, mejor que socket). Edge: `/nginx-health` |
| **Aislamiento** | CIS 5.x / 800-190 §3 | `read_only` + tmpfs mode=1777 + `no-new-privileges` + pids bound + **todos los puertos publicados en loopback** (`127.0.0.1:` gateado — el :80/:443 del edge es loopback desde WEB-EVAL-009) |

## Positivos destacados

- `/api/` y `/api/ws/` proxied correctamente con Upgrade headers (los 4 primeros gates nacieron de un 405 real)
- `escapeHtml` attribute-safe verificado por gate
- Bases de imagen digest-pinned (fix de supply-chain de esta sesión)
- `X-XSS-Protection` ya se había eliminado en web-management (WEB-EVAL-003) — los gates nuevos cierran la clase entera

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Edge CSP laxa (`unsafe-inline`/`unsafe-eval`) | Necesaria para UIs de terceros proxied; las apps propias llevan CSP estricta por capa |
| `script-src 'self' 'unsafe-inline'` en docs-site | Requisito de hidratación de Docusaurus (upstream) |
| Edge corre como root→worker | Requerido para bind :80/:443; mitigado por caps mínimas + loopback |

## Regresión

`test_frontend_stack.py`: 11 → **24 gates** · suite arquitectura completa pendiente de re-ejecución (los cambios tocan solo nginx confs — ningún test de aplicación afectado).
