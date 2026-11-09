# OWASP ASVS 4.0 — Mapeo de controles (nivel L2, aplicable al lab)

Estado por dominio ASVS con evidencia concreta del repo. Convención:
**✅ implementado** · **◐ parcial** · **N/A** (no aplica al contexto) ·
**❌ gap** (entra en backlog).

## V1 — Architecture, Design and Threat Modeling

| Control | Estado | Evidencia |
| --- | --- | --- |
| Arquitectura documentada | ✅ | `docs/02-architecture.md`, hexagonal + diagramas |
| Trust boundaries identificados | ✅ | zonas de seguridad (docs/02), `docs/rbac-matrix.md` |
| Análisis de amenazas | ◐ | evaluación OWASP API Top 10 en `docs/07-framework-evaluation.md`; falta STRIDE formal por componente |
| Inventario de componentes | ✅ | `docs/ui-inventory.json` + `check_ui_inventory.py` (gate CI) |

## V2 — Authentication

| Control | Estado | Evidencia |
| --- | --- | --- |
| Credenciales no en código | ✅ | `.env.full` gitignored, `scan_secrets.py` en CI, `generate_env.py` |
| Passwords hasheadas | ✅ | Argon2/bcrypt en `AuthService` |
| Anti-brute-force | ✅ | `RateLimitMiddleware` (`/auth` 10/min) + lockout en login |
| Auth factor uniforme | ✅ | JWT HS256 con exp/iat (`JwtTokenProvider`); tests anti-falsificación |
| SSO/federación | ◐ | AUTH-*: Keycloak + oauth2-proxy edge (en progreso, ver docs/17) |

## V3 — Session Management

| Control | Estado | Evidencia |
| --- | --- | --- |
| Tokens con expiración | ✅ | JWT `exp` configurable (`JWT_EXPIRATION_MINUTES`) |
| Logout efectivo | ✅ | token blacklist/stateless con TTL corto; WS tickets single-use (`/auth/ws-ticket`) |
| Sesiones concurrentes | ◐ | límite de streams WS (4429); sesiones HTTP stateless por diseño |

## V4 — Access Control

| Control | Estado | Evidencia |
| --- | --- | --- |
| RBAC por rol | ✅ | `docs/rbac-matrix.md` + `AuthService` permisos por rol |
| Default-deny | ✅ | `API_REQUIRE_AUTH=true` por defecto; endpoints sin auth explícitos |
| Service-to-service auth | ✅ | `X-Service-Token` (`INTERNAL_SERVICE_TOKEN`) en endpoints internos |
| CORS restringido | ✅ | `CORS_ORIGINS` configurable, no wildcard en prod (nosemgrep justificado) |

## V5 — Validation, Sanitization and Encoding

| Control | Estado | Evidencia |
| --- | --- | --- |
| Validación de entrada | ✅ | Pydantic v2 en todos los contratos API (`interfaces/api/contracts.py`) |
| Sanitización de payloads | ✅ | `PayloadSanitizer` (`security/`) en ingestas |
| Output encoding | ✅ | UI propia: `escapeHtml` en todo render dinámico (js/util.js) |
| Query parametrizada | ✅ | clientes usan params, no concat de SQL; ES/OS via cliente oficial |

## V6 — Stored Cryptography

| Control | Estado | Evidencia |
| --- | --- | --- |
| Datos sensibles cifrados | ◐ | secretos en `.env.full` (gitignored); volúmenes sin cifrado (lab, aceptado) |
| Algoritmos aprobados | ✅ | RSA-4096 CA, RSA-2048 leaf, TLS1.2/1.3 (nginx), JWT HS256 |

## V7 — Error Handling and Logging

| Control | Estado | Evidencia |
| --- | --- | --- |
| Logging estructurado | ✅ | `StructuredLogger` + Promtail → Loki |
| No fugas de secretos en logs | ✅ | `scan_secrets.py` + revisión; secrets no en respuestas |
| Errores genéricos al cliente | ✅ | handlers FastAPI no exponen stack traces |
| Auditoría/alertas | ✅ | Grafana unified alerting (4 reglas provisionadas) |

## V8 — Data Protection

| Control | Estado | Evidencia |
| --- | --- | --- |
| Clasificación de datos | ◐ | `reports/` y `runtime/` gitignored; IOCs de lab sintéticos |
| TLS interno | ✅ | PKI interna (MISP-001): CA propia + SANs, verify=ca.crt en clientes |
| TLS externo | ✅ | nginx edge 443 TLS1.2/1.3, HSTS-ready |

## V9 — Communications

| Control | Estado | Evidencia |
| --- | --- | --- |
| TLS verificado en clientes | ✅ | `verify_ssl` acepta CA bundle (`base_client.py`), e2e usa CA real |
| Certs con SAN correctos | ✅ | `gen_certs.sh` (SAN hostname+localhost+127.0.0.1), `make certs` |
| WS seguro | ✅ | ticket single-use + códigos 44xx de cierre tipados |

## V10 — Malicious Code

| Control | Estado | Evidencia |
| --- | --- | --- |
| Secrets scanning | ✅ | `scan_secrets.py --mode all` en CI |
| Integrity de builds | ✅ | get-pip verificado por SHA-256 (Cortex Dockerfile), imágenes pineadas por tag |
| Dependabot | ✅ | `.github/dependabot.yml` + `npm audit` triaged (R-05) |

## V11 — Business Logic

| Control | Estado | Evidencia |
| --- | --- | --- |
| Flujos de negocio validados | ✅ | pipeline alerta→decisión con estados verificables (e2e) |
| Idempotencia | ✅ | `tests/integration/test_idempotency.py`, admission queue |

## V12 — Files and Resources

| Control | Estado | Evidencia |
| --- | --- | --- |
| Uploads controlados | ◐ | MISP attachment path con límites PHP (50M); API no acepta uploads |
| Path traversal | ✅ | no file-serving desde paths de usuario; docs nginx `try_files` acotado |

## V13 — API and Web Service

| Control | Estado | Evidencia |
| --- | --- | --- |
| OWASP API Top 10 | ✅ | mapeo completo en `docs/07-framework-evaluation.md` §3.5 |
| Rate limiting | ✅ | `RateLimitMiddleware` con presupuestos por cliente |
| OpenAPI spec viva | ✅ | portal sirve `/openapi.json` real |
| DAST | ✅ | `.github/workflows/dast.yml` — ZAP baseline + api-scan (semanal) |

## V14 — Configuration

| Control | Estado | Evidencia |
| --- | --- | --- |
| Superficie de red mínima | ✅ | 12 puertos en `127.0.0.1`, solo edge+ingestas públicos (test de regresión) |
| Contenedores endurecidos | ✅ | `docker-socket-proxy`, `no-new-privileges`, `cap_drop`, `read_only` (perfil hardened) |
| CIS Docker | ◐ | mapeo en `docs/07` §3.7; excepciones documentadas y testeadas |
| Seguridad en headers | ✅ | CSP/HSTS/XFO/XCTO por servicio + tests de regresión |

## Resumen de gaps

| Gap | Severidad | Acción |
| --- | --- | --- |
| STRIDE formal por componente | baja | documentar en docs/02 (futuro) |
| SSO federado | media | AUTH-* en curso (Keycloak + oauth2-proxy) |
| Cifrado de volúmenes | baja | lab — riesgo aceptado (R-xx) |
| Sesiones concurrentes HTTP | baja | stateless por diseño; revisar si se adopta SSO |
