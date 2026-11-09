# 19. Threat Model (STRIDE) — SOAR Lab API

> Análisis STRIDE sobre la superficie **real** del API. Cada amenaza cita
> el control que la mitiga (verificado en código/tests) o el residual
> aceptado/documentado.

## 1. Resumen

| | |
| --- | --- |
| **Objetivo** | Catalogar amenazas de la API de gestión SOAR y sus controles |
| **Alcance** | API REST, WebSocket `/ws/logs`, admission queue, integraciones downstream, filesystem storage, config |
| **Método** | STRIDE por elemento de superficie |

## 2. Alcance

Elementos de superficie:

- **Auth**: `POST /auth/login` (JWT), `X-Service-Token`, WS tickets.
- **Mutaciones**: `POST /api/v1/alerts`, `/api/v1/contain`, `/backup/*`,
  `/tests/run`, DLQ ops.
- **Lecturas**: `/api/v1/alerts`, `/analytics/*`, `/api/v1/audit`,
  `/health/ready`, `/metrics`.
- **Storage**: `FilesystemStorage` (claves de usuario → fs).
- **Downstream**: Shuffle webhook, TheHive/Cortex/MISP/ES.

## 3. STRIDE por elemento

### 3.1 Autenticación y endpoints

| Amenaza | Vectores | Controles verificados | Residual |
| --- | --- | --- | --- |
| **S**poofing — acceso sin credencial | rutas nuevas sin `Depends` | `DefaultDenyAuthMiddleware` cubre todo lo no-whitelisted (ADR-0002) | — |
| **S**poofing — token de servicio filtrado | `X-Service-Token` en logs | SecretRedactorFilter redacta tokens/JWT en logs (LOG-001); `get_all()` redacta (BUG-130) | token en `.env.full` (fuera de repo, `.gitignore`) |
| **T**ampering — JWT forjado | firma HS256 | `jwt_secret` sin fallback público; fail-closed si falta (settings) | rotación manual |
| **R**epudiation | acciones sin traza | `_audit_access` por request: user+endpoint+method+result → `/api/v1/audit` (AUTH-004) | audit en memoria, no persistido |
| **I**nfo disclosure | errores con internals | mapeo `SOARError`→status sin `str(exc)` en 5xx (BUG-133) | — |
| **D**oS — brute force login | flood `/auth/*` | rate limit por IP, `RATE_LIMIT_AUTH_PER_MINUTE=10` | — |
| **E**levation — viewer muta | RBAC por rutas | `can_access_endpoint` + claim `role` (AUTH-003); unknown role→readonly | rutas nuevas no clasificadas → tier default (tests de matriz) |

### 3.2 Rate limiting / abuso

| Amenaza | Vectores | Controles | Residual |
| --- | --- | --- | --- |
| **D**oS por spoof de identidad | `X-Forwarded-For` forjado rotando buckets | XFF solo desde `RATE_LIMIT_TRUSTED_PROXIES` (default vacío = fail-closed), right-to-left (BUG-111) | — |
| **D**oS distribuido multi-réplica | límites por instancia | `RATE_LIMIT_BACKEND=redis` ventana compartida (BUG-134) | fail-open ante Redis caído (ADR-0007) |
| **D**oS por payload gigante | body enorme | `WEBHOOK_PAYLOAD_MAX_SIZE`, límites Pydantic `max_length` | — |

### 3.3 Ingesta / idempotencia

| Amenaza | Vectores | Controles | Residual |
| --- | --- | --- | --- |
| **T**ampering — replay de alerta | mismo payload reenviado | fingerprint SHA-256 + `SET NX` atómico; `X-Idempotency-Key`→Shuffle (IDEMP-002/003) | — |
| **D**oS — cola infinita | poison messages | max_attempts→DLQ, `maxlen` aprox en streams, poison→DLQ directo | — |
| **R**epudiation downstream | reenvío sin correlación | `idempotency_key` en body+header → Shuffle correlaciona replay | — |

### 3.4 Storage / filesystem

| Amenaza | Vectores | Controles | Residual |
| --- | --- | --- | --- |
| **T**ampering — path traversal | `key="../../x"` | `_resolve_key` rechaza absolutas, `..`, NUL, symlinks que escapan, base-dir alias (BUG-107/121, PBT) | — |
| **I**nfo disclosure | lectura fuera del base | mismo guard | — |
| **D**oS — escritura no atómica | crash mid-write | temp+fsync+`os.replace` (BUG-118) | — |

### 3.5 WebSocket `/ws/logs`

| Amenaza | Vectores | Controles | Residual |
| --- | --- | --- | --- |
| **S**poofing — WS sin auth | ticket de un solo uso | `?ticket=` consumido una vez (WEB-AUTH-001); scope `logs:read` | — |
| **D**oS — conexiones zombie | send falla sin limpieza | `disconnect()` en `finally` (BUG-126) | — |

### 3.6 Config / secretos

| Amenaza | Vectores | Controles | Residual |
| --- | --- | --- | --- |
| **I**nfo disclosure — config dump | `Settings.get_all()` serializaba keys | `get_all(redact=True)` default (BUG-130) | `_config` sigue en memoria en claro |
| **I**nfo disclosure — repo | secretos committeados | `scan_secrets.py` en CI (BUG-131); `.env.full` en `.gitignore` | histórico git pre-hardening |
| **T**ampering — TLS off silencioso | `verify=False` hardcodeado | cero `False` en código; env-driven con warning (ADR-0005) | — |

## 4. Riesgos residuales aceptados

1. Audit trail en memoria (no persistente entre restarts) — suficiente
   para lab; P11/BL-0003 propone persistir.
2. Rate-limit fail-open cuando Redis cae (decisión ADR-0007, log
   monitoreado).
3. `.env.full` como store de secretos (P19 propone Docker Secrets/Vault).
4. Roles default `admin` para JWTs legacy sin claim — retrocompatibilidad
   deliberada (tests pineados).

## 5. Matriz probabilidad × impacto

| Riesgo | P | I | Mitigación |
| --- | --- | --- | --- |
| Fuga de credencial via logs | Baja | Alto | RedactorFilter + get_all redact |
| Bypass rate-limit | Baja | Medio | trusted-proxies fail-closed + Redis backend |
| Falsa dedupe (colisión fingerprint) | Muy baja | Medio | SHA-256 sobre contenido canónico completo |
| Escalada rol por claim forjado | Baja | Alto | firma JWT + role whitelist en modelo |
| DoS cola por poison | Media | Medio | max_attempts→DLQ + alerta en logs |
| Secret en repo | Baja | Alto | scan CI + gitignore + nosecret docs |

## 6. Validación

Cada control enlaza su test: `tests/unit/test_fase0/1/2_hardening.py`,
`test_require_api_auth`, `test_rbac_matrix`, `test_authorization`,
`test_ws_ticket`. El threat model se re-verifica cuando cambia la
superficie (nueva ruta, nuevo middleware, nuevo rol).
