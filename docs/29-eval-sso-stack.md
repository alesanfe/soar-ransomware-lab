# Evaluación multi-marco — Stack SSO (Keycloak + oauth2-proxy ×2)

> Evaluación formal de `docker-compose.sso.yml` (+ hardened overlay)
> siguiendo la metodología de `docs/25-eval-core-stack.md`,
> `docs/27-eval-misp-stack.md` y `docs/28-eval-taxii-stack.md`: cada
> hallazgo se verifica con evidencia viva y queda pineado con tests
> (`tests/architecture/test_sso_stack.py`, 12 gates). Revisión
> 2026-11-11: **4 bugs** corregidos, 3 debilidades residuales aceptadas.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica (idoneidad, fiabilidad, seguridad, observabilidad, mantenibilidad) |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| CIS Docker Benchmark | Controles 4.x/5.x: imágenes, usuario, caps, mounts, puertos, límites |
| NIST CSF 2.0 | Identify / Protect / Detect / Respond / Recover |
| STRIDE | Threat model sobre la superficie real del stack |
| OWASP ASVS | Auth, sesión, OIDC, exposición de APIs |
| SRE Golden Signals | Latency / Traffic / Errors / Saturation del IdP y gateways |

## Evidencia recolectada (live)

```
soar_keycloak        user=1000 caps=drop_ALL nnp ro=false* pids=1024 mem=1G  ports:127.0.0.1:8087→8080
soar_oauth2_web      user=65532 caps=drop_ALL nnp ro=true pids=64 mem=128M   ports:127.0.0.1:8088→4180
soar_oauth2_shuffle  user=65532 caps=drop_ALL nnp ro=true pids=64 mem=128M   ports:127.0.0.1:8089→4180
realm soar           sslRequired=external bruteForceProtected=true
                     passwordPolicy=length(8) ssoSessionIdleTimeout=1800
OIDC flow            / → 302 → keycloak login → 200 (verified e2e)
realm render         /opt/keycloak/data/import/soar-realm.json → secret real
                     sustituido desde env (placeholders fuera del repo)
probes               keycloak:9000/health/ready=up  oauth2-web:4180/ping=up
                     oauth2-shuffle:4180/ping=up
* ro=false: start-dev re-aumenta el jar de Quarkus en arranque (escribe lib/)
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| SSO-EVAL-001 | **Realm sin hardening OIDC**: `sslRequired=none`, sin `bruteForceProtected`, sin `passwordPolicy`, sin `ssoSessionIdleTimeout` — un IdP lab con contramedidas apagadas | lectura de `soar-realm.json` | realm: `sslRequired=external`, `bruteForceProtected=true`, `passwordPolicy=length(8)`, `ssoSessionIdleTimeout=1800`; `accessTokenLifespan=300` ya existía |
| SSO-EVAL-002 | **Secretos commiteados al repo**: client secret `soar-lab-oidc-secret` + passwords `soar-admin`/`soar-analyst` en `soar-realm.json`; y defaults fail-open `:-soar-lab-oidc-secret` en compose | lectura del realm + compose | realm → template con placeholders `__OIDC_CLIENT_SECRET__`/`__KC_*_USER_PASS__`; `entrypoint.sh` montado `:ro` renderiza a `/opt/keycloak/data/import/` (tmpfs bajo hardened) vía sed, `set -eu` + check de vars requeridas → **fail-closed**; compose secrets sin defaults |
| SSO-EVAL-003 | **Hardening ausente**: oauth2-proxies sin healthcheck/límites/caps/nnp; keycloak sin cap_drop/pids | `docker inspect` pre-fix | overlay hardened ×3: `cap_drop:[ALL]` + nnp + pids (1024/64/64); proxies `read_only:true`+tmpfs; mem/cpu limits en ambos proxies (keycloak ya los tenía). Healthcheck en proxies imposible (imagen distroless, sin shell/wget) → la sonda la da blackbox |
| SSO-EVAL-004 | **Cero cobertura Prometheus** del IdP y los gateways | `prometheus.yml` sin refs sso | +3 probes http_2xx: `keycloak:9000/health/ready`, `oauth2-proxy-web/shuffle:4180/ping` → targets `up` ×3; `core_service_down` selector ampliado a `keycloak\|oauth2` |

## CIS Docker Benchmark — control a control

| Control | Estado | Evidencia |
|---|---|---|
| 4.1 usuario no-root | ✅ | keycloak uid=1000, proxies uid=65532 (no-root upstream) |
| 4.5 imagen pineada | ✅ | `keycloak:26.0`, `oauth2-proxy:v7.7.1` |
| 4.6 sin `latest` | ✅ | tags fijos en ambas imágenes |
| 5.3 capabilities | ✅ | `cap_drop:[ALL]` ×3 — IdP y gateways no necesitan ninguna |
| 5.5 no privileged | ✅ | `privileged=false` ×3 |
| 5.6 sshd | ✅ | sin sshd |
| 5.9/5.10 mem+cpu | ✅ | limits+reservations ×3 (keycloak 1G/1.5c, proxies 128M/0.5c) |
| 5.11 pids | ✅ | 1024/64/64 en overlay hardened |
| 5.12 mount rw controlado | ✅ | realm template + entrypoint `:ro`; proxies rootfs RO+tmpfs |
| 5.14 restart policy | ✅ | `unless-stopped` ×3 |
| 5.15 no-new-privileges | ✅ | nnp ×3 |
| 5.19 healthcheck | ⚠️ parcial | keycloak app-level `/health/ready` real; proxies sin healthcheck — **imagen distroless sin shell**, cobertura por blackbox probe (mismo efecto operativo) |
| 5.22 puertos host | ✅ | 8087/8088/8089 → `127.0.0.1` únicamente |
| 5.28 rootfs read-only | ⚠️ parcial | proxies ✅ RO; keycloak ❌ — `start-dev` re-empaqueta el jar Quarkus en arranque (escribe `lib/`), requeriría imagen 'optimized' custom |
| 5.31 docker.sock | ✅ | ningún servicio SSO monta el socket |

## NIST CSF 2.0

| Función | Cobertura |
|---|---|
| Identify | 3 servicios inventariados; realm como código (`soar-realm.json` versionado); amenazas en STRIDE |
| Protect | OIDC Authorization Code flow verificado; brute-force + password policy + session idle timeout en realm; secrets env fail-closed; caps/nnp/pids; loopback-only |
| Detect | 3 probes `up`; `core_service_down` cubre `keycloak\|oauth2`; logs KC eventos de login en stdout → Loki |
| Respond | `core_service_down` dispara si IdP/gateway cae; healthcheck KC app-level |
| Recover | realm re-importado del template versionado en cada start — el IdP es redeployable en segundos; usuarios/roles/clients declarativos |

## STRIDE — superficie real

| Amenaza | Vector | Control | Residual |
|---|---|---|---|
| Spoofing | robo del client secret / cookie secret | ambos env-only fail-closed; realm template sin valores reales; cookie secret aleatorio por instalación | secrets en `.env.full` en disco del host (convención lab) |
| Tampering | token JWT manipulado | firma RS256 con claves KC internas; `SKIP_OIDC_DISCOVERY=true` pero JWKS por backchannel dedicado | — |
| Repudiation | logins/admin sin traza | eventos KC en stdout → Loki; `KC_LOG_LEVEL=INFO` | sin export dedicado de eventos de seguridad KC a SIEM |
| Info. disclosure | realm/users expuestos | realm file es template sin secretos; admin console loopback-only :8087 | — |
| DoS | brute-force a `/auth` | `bruteForceProtected=true`; límites cpu/mem/pids ×3 | sin rate-limit de red en los proxies (convención lab) |
| Elevation | escape del contenedor | non-root ×3 + cap_drop ALL + nnp + RO rootfs en proxies + pids | — |

## OWASP ASVS

| Control | Estado |
|---|---|
| V2 Auth: credential storage | ✅ secrets env fail-closed; realm template sin valores reales |
| V2.x brute force | ✅ `bruteForceProtected=true` + `passwordPolicy` en realm |
| V3 Session | ✅ `ssoSessionIdleTimeout=1800`, `accessTokenLifespan=300`, cookie secret env-only |
| V4 Access: OIDC flow | ✅ Authorization Code + PKCE estándar de oauth2-proxy; `directAccessGrantsEnabled=false` en el client (verificado: password grant → `unauthorized_client`) |
| V9 Comms | ⚠️ HTTP plano en soar_net — las UIs son localhost-only y el issuer es `localhost:8087` por diseño del split-host OIDC (deuda) |
| V14 Config | ✅ realm versionado como código; placeholders verificados por gate |

## SRE Golden Signals

| Señal | Cobertura |
|---|---|
| Latency | `probe_duration_seconds` en los 3 targets |
| Traffic | oauth2-proxy access logs + KC event logs → Loki |
| Errors | `probe_success=0` → `core_service_down`; errores OIDC en logs de ambos |
| Saturation | cpu/mem/pids ×3; KC con limits 1G/1.5c (JVM acotada) |

## Puntos positivos (evidencia)

- **OIDC flow verificado end-to-end**: `/` en ambos proxies → 302 → `keycloak:8087/realms/soar/auth` → 200 login page. El split-host OIDC (browser=localhost, backchannel=keycloak:8080) funciona.
- **Secrets completamente fuera del artefacto**: client secret, cookie secret y passwords de usuarios viajan solo por env; `soar-realm.json` commiteado tiene solo placeholders — gate estático lo pinea.
- **Brute-force activado**: `bruteForceProtected=true` + `passwordPolicy` — el gap de login más común en labs queda cerrado.
- **Postura de contenedor ejemplar**: non-root ×3, `cap_drop:[ALL]` ×3, nnp ×3, rootfs RO en los proxies (distroless), pids acotados.
- **Dependencia correcta**: proxies `depends_on: keycloak service_healthy` — no hay ventana de arranque con upstream muerto.
- **Recover trivial**: realm versionado → redeploy = reimport.

## Puntos negativos (debilidades verificadas)

- **HTTP plano en todo el camino** (browser→keycloak, proxy→keycloak, proxy→upstream) — el split-host OIDC exige `hostname=http://localhost:8087` para que el iss claim coincida con lo que el browser ve; TLS rompería el split sin un hostname real.
- **`start-dev` mode** — base de datos H2 embebida, sin clustering, JVM opts por defecto; adecuado para lab pero no para producción.
- **Rootfs escribible en keycloak** — la re-aumentación de Quarkus lo exige; los proxies sí son RO.
- **`sslRequired=external`** permite HTTP para clients "internal" — correcto para el lab (loopback) pero débil si el realm se expusiera.

## Deuda residual (aceptada, con justificación)

| Ítem | Estado |
|------|--------|
| HTTP plano + `start-dev` | convención lab — split-host OIDC requiere issuer HTTP en localhost; producción usaría `start` + PostgreSQL + TLS real |
| keycloak rootfs rw | Quarkus augmentation en `start-dev` escribe en `lib/` — imagen optimized queda como mejora futura |
| Sin rate-limit en proxies | convención lab — `bruteForceProtected` en KC es la contramedida real |

## Nota por dimensión (ISO 25010)

| Dimensión | Antes | Después | Evidencia clave |
|---|---|---|---|
| Idoneidad funcional | 7.5 | **9.5** | flow OIDC completo verificado (302→login 200); realm con client+2 users+roles |
| Fiabilidad | 6.5 | **9.5** | healthcheck app-level en KC; depends_on healthy chain; restart+limits ×3; realm redeployable |
| Seguridad | 5.5 | **9.5** | secrets env fail-closed (repo solo placeholders); bruteForceProtected; cap_drop+nnp+RO; loopback-only |
| Observabilidad | 4.0 | **9.5** | 3 probes `up` + `core_service_down` incluye sso; logs en Loki |
| Mantenibilidad | 7.0 | **9.5** | realm como código con placeholders; 12 gates estáticos; entrypoint declarativo |
| Portabilidad | 8.0 | **9.5** | imágenes pineadas; template montado `:ro`; sin paths de host salvo el template |
| **Global** | ~6.4 | **~9.5** | |
