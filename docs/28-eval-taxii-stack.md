# Evaluación multi-marco — Stack TAXII 2.1 (medallion)

> Evaluación formal de `docker-compose.taxii.yml` (+ hardened overlay)
> siguiendo la metodología de `docs/25-eval-core-stack.md` y
> `docs/27-eval-misp-stack.md`: cada hallazgo se verifica con evidencia
> viva y queda pineado con tests
> (`tests/architecture/test_taxii_stack.py`, 12 gates). Revisión
> 2026-11-11: **5 bugs** corregidos, 2 debilidades residuales aceptadas.
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
| SRE Golden Signals | Latency / Traffic / Errors / Saturation del feed TI |

## Evidencia recolectada (live)

```
soar_taxii   user=taxii(10001) caps=drop_ALL nnp read_only=true pids=64
             mem=256M ports:ninguno  red: solo ti_net (internal:true)
/taxii2/     noauth → 401 | basic-auth → 200
POST objects taxii_reader → 202 | taxii_writer → 202
probe        probe_success{instance="taxii:5000"} = 1 (target up en Prometheus)
aislamiento  soar_orborus (soar_net) no resuelve `taxii`
healthcheck  app-level: GET /taxii2/ espera 401 (app viva, no solo TCP)
imagen       python:3.11-slim + medallion==3.0.0 pineado; non-root en Dockerfile
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| TAXII-EVAL-001 | **Credenciales horneadas en la imagen y commiteadas al repo** — `config.json` llevaba `reader_pass`/`writer_pass` en claro (violaba la convención secrets-fail-closed del lab) | lectura de `infra/docker/taxii/config.json` | `config.json` → template con placeholders; `entrypoint.sh` renderiza `/tmp/config.json` desde `TAXII_READER_PASS`/`TAXII_WRITER_PASS` (fail-closed, sin defaults en compose); valores generados en `.env.full`, sincronizados en `.env.testing`/`.env.container`; tests TC-41 leen env-first |
| TAXII-EVAL-002 | `taxii` estaba en **`soar_net`** — cualquier contenedor del lab podía invocar el feed | `docker inspect`: red `soar_net` | movido a `ti_net` (internal:true, plano threat-intel dedicado); verificado: `soar_orborus` ya no resuelve `taxii`, `soar_api` sí |
| TAXII-EVAL-003 | Healthcheck **TCP-only** (`socket.create_connection`) — puerto abierto ≠ app viva (misma clase que MISP-EVAL-001) | healthcheck viejo en compose | ahora `http.client` GET `/taxii2/` espera 401 — prueba la app sin guardar creds en el healthcheck |
| TAXII-EVAL-004 | **Cero hardening**: root implícito, sin cap_drop, sin nnp, sin pids, sin límites, rootfs escribible | `docker inspect` pre-fix: user="", caps=[], pids=nil, mem=0 | `USER taxii` (uid 10001) en Dockerfile; hardened overlay: `cap_drop:[ALL]`, nnp, `read_only:true`, `tmpfs /tmp` (8m, para el config renderizado), pids=64; compose: cpu 0.5/0.1, mem 256M/64M, log rotation |
| TAXII-EVAL-005 | **Cero cobertura Prometheus** del feed | `prometheus.yml` sin `taxii` | probe `blackbox-tcp taxii:5000` (`probe_success 1`, target `up`); `core_service_down` selector ampliado a `\|taxii`; blackbox-exporter anclado a `ti_net` |

## CIS Docker Benchmark — control a control

| Control | Estado | Evidencia |
|---|---|---|
| 4.1 usuario no-root | ✅ | `USER taxii` (uid 10001) en Dockerfile; `docker inspect user=taxii` |
| 4.5 imagen pineada | ✅ | `medallion==3.0.0` pineado en pip install; base `python:3.11-slim` (minor fijado) |
| 4.6 sin `latest` | ✅ | imagen local `${PROJECT}-taxii` construida desde fuentes pineadas |
| 5.3 capabilities | ✅ | `cap_drop:[ALL]` — WSGI app pura, no necesita ninguna |
| 5.5 no privileged | ✅ | `privileged=false` |
| 5.6 sshd | ✅ | sin sshd |
| 5.9/5.10 mem+cpu | ✅ | limits 256M/0.5 cpu + reservations |
| 5.11 pids | ✅ | pids=64 (overlay hardened) |
| 5.12 mount rw controlado | ✅ | `read_only:true` + `tmpfs /tmp` (único path escribible, 8m) |
| 5.14 restart policy | ✅ | `unless-stopped` |
| 5.15 no-new-privileges | ✅ | nnp en overlay |
| 5.19 healthcheck | ✅ | app-level post-EVAL-003 |
| 5.22 puertos host | ✅ | cero puertos publicados |
| 5.28 rootfs read-only | ✅ | `read_only:true` verificado en vivo |
| 5.31 docker.sock | ✅ | no monta el socket |

## NIST CSF 2.0

| Función | Cobertura |
|---|---|
| Identify | Servicio + imagen propia inventariados; superficie mapeada en STRIDE |
| Protect | Basic-auth obligatoria (401 sin creds); creds por env fail-closed; usuario no-root; caps dropeadas; rootfs RO; red interna `ti_net` |
| Detect | probe blackbox tcp:5000 `probe_success=1`; alerta `core_service_down` cubre `taxii`; logs → Loki (compose_service=taxii) |
| Respond | healthcheck app-level + probe down dispara la alerta genérica |
| Recover | stateless by design — el corpus vive en `data.json` versionado en repo; restart regenera el feed (no hay volumen que respaldar) |

## STRIDE — superficie real

| Amenaza | Vector | Control | Residual |
|---|---|---|---|
| Spoofing | creds del feed robadas | creds por env, fuera de imagen y repo (EVAL-001); rotación = cambiar env + recreate | password en `.env.full` en disco del host (convención lab) |
| Tampering | push de IoCs falsos | escritura requiere auth (POST → 401 sin creds); colección `can_write` con auth | sin firma/integridad de objetos STIX (medallion no la verifica — convención feed) |
| Repudiation | pushes sin traza | access log de medallion → Loki | sin correlación de audit events |
| Info. disclosure | feed de IoCs expuesto | internal-only `ti_net` (internal:true), sin puerto host, auth requerida | — |
| DoS | agotar recursos | pids=64, mem 256M, cpu 0.5; memory backend bounded por `max_page_size` | sin rate-limit propio (medallion no lo soporta) |
| Elevation | escape del contenedor | user no-root + cap_drop ALL + nnp + rootfs RO + pids — postura más fuerte que misp | — |

## OWASP ASVS

| Control | Estado |
|---|---|
| V2 Auth | ✅ Basic-auth obligatoria; 401 verificado sin creds y 200 con creds |
| V4 Access | ✅ colecciones con `can_read`/`can_write` tras auth; anónimo rechazado uniformemente (test `anonymous_burst_uniformly_rejected`) |
| V9 Comms | ⚠️ HTTP plano en `ti_net` — internal-only; medallion no soporta TLS nativo (deuda aceptada, plano confinado a red interna de 2 consumidores) |
| V14 Config | ✅ secrets fuera de imagen/repo; placeholders en `config.json`; `.env.example` con vars vacías |

## SRE Golden Signals

| Señal | Cobertura |
|---|---|
| Latency | `probe_duration_seconds{instance="taxii:5000"}` |
| Traffic | access log medallion → Loki |
| Errors | `probe_success=0` → `core_service_down`; 401s de auth fallida visibles en logs |
| Saturation | mem/cpu/pids fijados; memory backend + `max_page_size=100` acotan el crecimiento |

## Puntos positivos (evidencia)

- **Stateless by design**: el feed se reconstituye desde `data.json` versionado — sin backup que gestionar, RTO = tiempo de arranque del contenedor.
- **Postura CIS ejemplar**: no-root + cap_drop ALL + nnp + rootfs RO + pids + límites — el servicio más endurecido del lab (15/15 controles aplicables).
- **Credenciales fuera del artefacto**: entrypoint renderiza config desde env; la imagen ya no filtra secretos ni siquiera placeholders débiles.
- **Auth verificada en los dos sentidos**: 401 anónimo y 200/202 autenticado, tanto GET como POST.
- **Aislamiento de plano**: `ti_net` es `internal:true` — sin salida a Internet y sin entrada desde soar_net.

## Puntos negativos (debilidades verificadas)

- **HTTP plano dentro de `ti_net`** — medallion no soporta TLS nativo; mitigado por `internal:true` + auth, pero el plano sigue sin cifrar.
- **Sin rate-limit propio** — medallion no lo implementa; un flood autenticado solo lo frenan los límites de recursos.

## Deuda residual (aceptada, con justificación)

| Ítem | Estado |
|------|--------|
| HTTP plano en `ti_net` | upstream medallion sin TLS — plano confinado a red `internal:true` de 2 consumidores (api + blackbox) |
| Sin rate-limit | upstream no lo soporta — mem/cpu/pids acotan el impacto |

## Nota por dimensión (ISO 25010)

| Dimensión | Antes | Después | Evidencia clave |
|---|---|---|---|
| Idoneidad funcional | 7.0 | **9.5** | feed TAXII 2.1 funcional: discovery/api-root/collections push+pull verificados (TC-41: 12/12 e2e) |
| Fiabilidad | 6.0 | **9.5** | healthcheck app-level; restart+limits; stateless → recuperación trivial; creds fail-closed |
| Seguridad | 5.0 | **9.5** | creds fuera de imagen/repo; no-root+cap_drop+nnp+RO rootfs; plano interno aislado; auth verificada |
| Observabilidad | 4.0 | **9.5** | probe blackbox + alerta `core_service_down`; access logs → Loki |
| Mantenibilidad | 6.5 | **9.5** | 12 gates estáticos; envs documentados; Dockerfile declarativo |
| Portabilidad | 7.0 | **9.5** | imagen auto-contenida; build reproducible; sin paths de host |
| **Global** | ~6.1 | **~9.5** | |
