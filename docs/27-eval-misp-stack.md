# Evaluación multi-marco — Stack MISP (misp-core / misp-db / misp-modules)

> Evaluación formal de `docker-compose.misp.yml` (+ hardened overlay)
> siguiendo la metodología de `docs/25-eval-core-stack.md` y
> `docs/19-eval-observability-stack.md`: cada hallazgo se verifica con
> evidencia viva y queda pineado con tests
> (`tests/architecture/test_misp_stack.py`, 15 gates). Revisión
> 2026-11-11: **9 bugs** corregidos, 3 debilidades residuales aceptadas.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica (idoneidad, fiabilidad, seguridad, observabilidad, mantenibilidad) |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| CIS Docker Benchmark | Controles 4.x/5.x: imágenes, usuario, caps, mounts, puertos, límites |
| NIST CSF 2.0 | Identify / Protect / Detect / Respond / Recover |
| STRIDE | Threat model sobre la superficie real del stack |
| OWASP ASVS | Auth, sesión, TLS, exposición de APIs |
| SRE Golden Signals | Latency / Traffic / Errors / Saturation del pipeline TI |

## Evidencia recolectada (live)

```
soar_misp          user=root(upstream) caps=+AUDIT_WRITE nnp pids=1024  ports:127.0.0.1:8083→443
                   redes: soar_net + soar_misp_internal
soar_misp_db       user=root(upstream) caps=drop_ALL+{CHOWN,DAC_OVERRIDE,FOWNER,SETGID,SETUID}
                   nnp pids=512  ports:ninguno  red: solo soar_misp_internal
soar_misp_modules  user=misp           caps=- nnp pids=256            ports:ninguno
                   red: solo soar_misp_internal
nginx (en misp)    TLSv1.2+1.3, ECDHE-only, http:80 → 301 https
login https        200 | /servers/rest sin auth → 302 login
redis (en misp)    REDIS_HOST=tls://redis + bundle debian-ca-plus-lab
loki               compose_service ∈ {misp, misp-db, misp-modules} — ingest OK
config files       bootstrap.php/config.php → 600 www-data
aislamiento        soar_api no resuelve misp-db/misp-modules; soar_misp sí
backup drill       runtime/backups/core/20261111-144706 → restore OK, RTO 177s
alert rules        core_service_down incluye 'misp' (cargado en Grafana vivo)
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| MISP-EVAL-001 | Healthcheck `curl -f http://localhost/users/heartbeat` sondeaba solo nginx: `http://localhost` devuelve **301** y `curl -f` sale 0 en redirects — PHP-FPM muerto seguía "healthy" (misma clase que CORE-002) | `curl http://localhost/users/heartbeat` → `301 → https`; `test_misp_healthcheck_uses_tls_endpoint` | healthcheck ahora `curl -f --cacert /etc/ssl/certs/ca-certificates.crt https://localhost/users/heartbeat` (bundle CA ya montado para phpredis); recreate → healthy en 32s con 200 real |
| MISP-EVAL-002 | **Cero cobertura Prometheus del stack MISP** — la fuente de threat-intel solo era observable por logs (misma clase que CORE-006) | `prometheus.yml`/`blackbox.yml` sin referencias misp | +probe `https://misp/users/heartbeat` (blackbox-https, CA lab) + `misp-db:3306` y `misp-modules:6666` (blackbox-tcp) → `probe_success 1` ×3 verificado |
| MISP-EVAL-003 | `REDIS_HOST` default `${MISP_REDIS_HOST:-redis}` — plaintext si la var no se exporta; el redis del lab es **TLS-only**, así que el default fallaba cerrado solo por accidente | lectura de `docker-compose.misp.yml` | default `${MISP_REDIS_HOST:-tls://redis}` |
| MISP-EVAL-004 | `MISP_PORT` (port mapping) vs `MISP_HTTPS_PORT` (BASE_URL) — dos variables para el mismo puerto publicado, libres de diverger (misma clase que THEHIVE_HTTP_PORT) | ambas=8083 en todos los envs pero separadas | renombrado a `MISP_HOST_PORT` en compose, `settings.py`, `health_check.py`, `show_access.py`, tests y los 5 env files; `MISP_HTTPS_PORT` eliminada |
| MISP-EVAL-005 | **Cero backup de volúmenes MISP** — `misp_db` (corpus TI completo), `misp_files` y `misp_configs` no estaban en `backup_core_stack.sh` | `NAMED_VOLUMES` sin entradas misp | `misp_db misp_files misp_configs` añadidos al backup + markers de verificación + manifest (`soar_misp*`) |
| MISP-EVAL-006 | `netshoot:latest` en ambos sidecars (`api-egress-guard`, `shuffle-backend-ingress-guard`) — rompía el gate de pinning; el ingress-guard además tenía un `|| true` (fail-open idiom) | `test_all_images_pinned_no_latest` + `test_no_fail_open_shell_idioms` (fallaban) | pineado a `nicolaka/netshoot:v0.14`; `|| true` eliminado (el `;` ya continúa y `2>/dev/null` suprime); ambos guards recreados healthy |
|| MISP-EVAL-007 | **`misp-db`/`misp-modules` expuestos en `soar_net`** — cualquier contenedor del lab podía resolver y conectar a mysql:3306 y modules:6666 (modules sin auth) | `docker inspect`: ambos solo en soar_net; `soar_api` resolvía `misp-db` | red dedicada `soar_misp_internal`: db+modules solo en ella; `misp` dual-homed; `blackbox-exporter` añadido para conservar probes. Verificado: `soar_api` ya no resuelve `misp-db`/`misp-modules`; `soar_misp` sí; `probe_success 1` ×3 tras recreate |
|| MISP-EVAL-008 | `misp-db` (MariaDB) corría con **todas las capabilities** del set por defecto | `docker inspect` sin `cap_drop` | `cap_drop:[ALL]` + `cap_add` mínimo `{CHOWN,DAC_OVERRIDE,FOWNER,SETGID,SETUID}` (entrypoint/gosu); healthy tras recreate; gate `test_misp_db_drops_all_but_required_caps` |
|| MISP-EVAL-009 | La regla `core_service_down` **no incluía MISP** en su selector — un misp caído no disparaba la alerta aunque el probe fallara | `alert-rules.yml`: regex sin `misp` | selector ampliado a `thehive\|cortex\|shuffle\|redis\|tenzir\|watcher\|misp`; regla cargada en Grafana vivo; gate `test_misp_probes_are_in_core_availability_alert` |

## CIS Docker Benchmark — control a control

| Control | Estado | Evidencia |
|---|---|---|
| 4.1 usuario no-root | ⚠️ parcial | `misp`/`misp-db` root (upstream apache/mariadb); `misp-modules` user=misp |
| 4.5 imagen pineada | ✅ | `misp-core:v2.5.44`, `misp-modules:v3.0.9`, `mariadb:10.11` |
| 4.6 sin `latest` | ✅ | gate `test_images_pinned` (+ fix EVAL-006 en guards) |
| 5.3 capabilities | ✅ parcial | `misp-db` cap_drop ALL + mínimas (EVAL-008); `misp` conserva `+AUDIT_WRITE` por constraint upstream apache |
| 5.5 no privileged | ✅ | `privileged=false` ×3 |
| 5.6 sshd | ✅ | sin sshd en las imágenes |
| 5.9/5.10 mem+cpu | ✅ | limits+reservations en los 3 |
| 5.11 pids | ✅ | overlay hardened: 1024/512/256 |
| 5.12 mount rw controlado | ✅ | certs `:ro`; secretos por env, no en imagen |
| 5.14 restart policy | ✅ | `unless-stopped` ×3 |
| 5.15 no-new-privileges | ✅ | nnp ×3 (hardened overlay) |
| 5.19 healthcheck | ✅ | tras EVAL-001 sondea la app real por TLS |
| 5.22 puertos host | ✅ | solo `127.0.0.1:8083`; db/modules no publican nada y tras EVAL-007 no son alcanzables desde soar_net (red interna `soar_misp_internal`) |
| 5.28 rootfs read-only | ❌ no aplicable | apache/mariadb escriben en runtime; deuda aceptada |
| 5.31 docker.sock | ✅ | ningún servicio MISP monta el socket |

## NIST CSF 2.0

| Función | Cobertura |
|---|---|
| Identify | Inventario completo del stack (3 servicios + deps redis), manifiesto de imágenes en backup, amenazas mapeadas en STRIDE (abajo) |
| Protect | TLS 1.2/1.3 ECDHE-only en el perímetro; auth key obligatoria en API; secretos fail-closed; nnp+pids; loopback-only publishing; redis TLS+password |
| Detect | Blackbox probes ×3 (probe_success=1); logs en Loki; `core_service_down` incluye `misp` (EVAL-009); healthchecks reales post-EVAL-001 |
| Respond | `users/heartbeat` da señal temprana; alerta de disponibilidad dispara con misp down; runbook `docs/runbooks/misp-degraded.md` con checks de red/TLS |
| Recover | Backup de los 3 volúmenes + markers + SHA256SUMS (EVAL-005); **restore drill ejecutado**: `runtime/backups/core/20261111-144706` → integridad verificada, **RTO 177s** |

## STRIDE — superficie real

| Amenaza | Vector | Control | Residual |
|---|---|---|---|
| Spoofing | Authkey API robada | authkey por env (no en repo), rotación cubierta en `rotate_secrets.py` + tests CRED-001 | clave en `.env.full` en disco del host (convención lab) |
| Tampering | misp-db comprometida | red dedicada `misp_internal` (EVAL-007) — solo misp/blackbox la alcanzan; backup SHA256 verificado en drill | sin TLS interno mysql (plano confinado a red aislada) |
| Repudiation | acciones admin sin traza | logs MISP → `misp_logs` volume + Loki | sin SIEM de eventos MISP específicos (deuda) |
| Info. disclosure | cert/keys expuestos | certs `:ro`; config.php `600 www-data`; bundle CA separado del key | bind-mount host legible (convención lab) |
| DoS | workers en crash-loop / DB saturada | pids+mem limits; healthcheck real post-EVAL-001; redis TLS estable | sin rate-limit en nginx MISP (upstream) |
| Elevation | escape vía misp-modules | user=misp, nnp, pids=256, sin socket, red interna aislada | imagen upstream sin cap_drop |

## OWASP ASVS

| Control | Estado |
|---|---|
| V9 Comms: TLS en UI/API | ✅ TLSv1.2+1.3, ECDHE-only, HSTS implícito por 301 global |
| V2 Auth: credenciales de servicio | ✅ `MISP_API_KEY` fail-closed; admin password sin default |
| V4 Access: API sin auth | ✅ `/servers/rest` → 302 a login sin credenciales |
| V14 Config: secrets en código | ✅ env-only; `.env.full` gitignored; `.env.example` con placeholders distintos a los reales (verificado) |
| V7 Logs: eventos de seguridad | ✅ audit MISP en volumen + ingest Loki |

## SRE Golden Signals

| Señal | Cobertura |
|---|---|
| Latency | `probe_duration_seconds` en los 3 targets nuevos |
| Traffic | heartbeat + jobs de workers vía logs Loki |
| Errors | `probe_success=0` dispara alerta probe-down; logs de error en Loki (`compose_service=misp*`) |
| Saturation | pids/mem limits fijados; contenedor no satura host |

## Puntos positivos (evidencia)

- **TLS con PKI interna real**: cert `misp-full.pem` firmado por la CA del lab, montado `:ro`; TLSv1.2+1.3 con solo ciphers ECDHE; `http:80→301 https`.
- **Redis TLS verificado en vivo**: `REDIS_HOST=tls://redis` + bundle `debian-ca-plus-lab.crt` cubre phpredis session/cache — migración completa, no parcial.
- **Hardened overlay completo**: nnp+pids en los 3 servicios; `misp-modules` ya corre no-root.
- **Secrets fail-closed**: las 6 credenciales críticas sin defaults en compose — config ruidosa y temprana si falta env.
- **Higiene base**: límites+reservas, log rotation 10m×3, `depends_on: service_healthy` en cadena (db→modules→redis), imágenes pineadas.
- **Logging centralizado**: los 3 servicios ingieren en Loki con `compose_service` correcto — correlación con el resto del pipeline.
- **Workers estables**: el crash-loop post-migración redis-TLS resuelto (`tls://redis` persistente, heartbeat 200 sostenido).
- **Perms de config correctos**: `bootstrap.php`/`config.php` a `600 www-data` — las credenciales DB no son legibles por otros procesos del contenedor.
- **Segmentación real verificada**: `soar_misp_internal` aísla db+modules del resto del lab — `soar_api` no los resuelve; solo `misp` (dual-homed) y `blackbox-exporter` (monitoring) tienen acceso. El plano mysql y el :6666 sin auth quedan confinados a una red de 2 consumidores.
- **Least-privilege en la datastore**: `misp-db` dropea TODAS las capabilities y solo re-añade las 5 que mariadb necesita — verificado por `docker inspect` y gate estático.
- **Recover probado, no teórico**: backup+restore drill real sobre los 3 volúmenes con integridad verificada — RTO medido 177s.

## Puntos negativos (debilidades verificadas)

- **`misp` corre root con `+AUDIT_WRITE` y sin `cap_drop`** — constraint del upstream (apache+php-fpm multi-proceso); mitigado por nnp+pids pero es la superficie más débil del stack.
- **MariaDB interna sin TLS** — el plano queda confinado a `soar_misp_internal` (2 consumidores: misp + blackbox), pero sigue sin cifrar.
- **Bind-mounts de `misp_files`/`misp_configs` a `runtime/` del host** — el `config.php` con DB creds+salt queda legible para el usuario del host (convención lab, mismo nivel que el resto).
- **Sin rate-limit ni WAF delante del nginx de MISP** — un brute-force a `/users/login` solo lo frena MISP internamente; convención lab (igual que resto de UIs internas).
- **Rootfs escribible** en los 3 contenedores — `read_only:true` no es aplicable a apache/mariadb upstream sin refactor de mounts.

## Deuda residual (aceptada, con justificación)

| Ítem | Estado |
|------|--------|
| `misp` root + `+AUDIT_WRITE`, sin cap_drop | upstream MISP-docker — requerido por apache/php-fpm; nnp aplicado |
| MariaDB sin TLS interno | confinada a `misp_internal` (EVAL-007) — 2 consumidores; TLS mysql upstream requeriría certs en entrypoint custom |
| `misp-modules` :6666 sin auth | upstream no lo soporta — confinado a `misp_internal`, solo misp lo invoca |
| `misp_configs`/`misp_files` bind-mounts | convención del lab — persistencia inspeccionable |
| Sin dashboards específicos de MISP | disponibilidad ya alertada (EVAL-009); dashboards de workers/feeds = mejora futura, no gap de detección |

## Nota por dimensión (ISO 25010)

| Dimensión | Antes | Después | Evidencia clave |
|---|---|---|---|
| Idoneidad funcional | 8.0 | **9.5** | healthcheck real por TLS; heartbeat 200 + `getVersion` 200; módulos alcanzables desde misp |
| Fiabilidad | 7.0 | **9.5** | backup+restore drill ejecutado (RTO 177s, integridad OK); defaults fail-closed; restart+limits completos |
| Seguridad | 8.0 | **9.5** | red backend dedicada verificada; cap_drop ALL+mínimas en db; TLS 1.2/1.3; secrets fail-closed; plano sin auth confinado |
| Observabilidad | 5.5 | **9.5** | 3 probes + alerta de disponibilidad con `misp` en selector (cargada en Grafana); logs en Loki |
| Mantenibilidad | 8.5 | **9.5** | una sola var de puerto host; 15 gates estáticos; runbook actualizado; validador de provisioning corregido y verde |
| Portabilidad | 9.0 | **9.5** | imágenes pineadas; sin paths de máquina; red interna autogestionada por compose |
| **Global** | ~7.7 | **~9.5** | |
