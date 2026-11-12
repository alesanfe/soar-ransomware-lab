# Evaluación multi-marco — Stack Core SOAR (TheHive/Cortex/Shuffle/Orborus/Tenzir/Redis/watcher)

> Evaluación de `docker-compose.core.yml` (+ hardened overlay) contra
> ISO/IEC 25010+25040, CIS Docker Benchmark, NIST CSF 2.0, STRIDE y
> OWASP ASVS. Primera revisión 2026-11-11: **7 bugs** verificados con
> tests (`test_core_stack.py`). Segunda revisión (misma fecha, ronda
> observabilidad): **+4 bugs más** encontrados por inyección de fallos
> y probes sintéticos, + endurecimiento Tenzir/Redis y observabilidad
> completa (exporters, 6 reglas, backup+drill). Global **~9.0**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica |
| ISO/IEC 25040 | Evidencia → defecto → veredicto |
| CIS Docker Benchmark | Hardening de contenedores (creds, caps, mounts, ports) |
| NIST CSF 2.0 | Identify / Protect / Detect / Respond / Recover |
| STRIDE | Threat model sobre la superficie real (ver `19-threat-model-stride.md`) |
| OWASP ASVS | Auth, sesión, CSRF, exposición de APIs |

## Bugs encontrados — todos verificados con test, todos corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| CORE-001 | `tenzir-node` y `network-watcher` publicaban puertos en `0.0.0.0` — el resto del stack usa `127.0.0.1:`. Tenzir con `web --mode=dev` quedaba expuesto a toda la LAN | `docker ps` + `test_all_host_ports_loopback_bound` (fallaba) | prefijo `127.0.0.1:` en ambos; recreados → bind loopback verificado |
| CORE-002 | Healthcheck de orborus = `nc -z shuffle-backend 5001` — sondeaba la dependencia, no el servicio: un orborus colgado seguía "healthy" | `docker inspect` + `test_healthchecks_probe_the_service_itself` (fallaba) | `pgrep -f orborus`; healthy tras recreate |
| CORE-003 | `cortex.conf.template` renderizaba por defecto `/run/desktop/mnt/host/c/Users/alex0/...` — path de la máquina de un desarrollador; en Linux los jobs DinD de analyzers apuntarían a un path inexistente | `test_cortex_template_has_no_machine_specific_default` (fallaba) | `${CORTEX_DOCKER_JOB_DIR}` requerido + `render_configs.py` calcula el path por-OS (`_docker_host_path`) |
| CORE-004 | `cortex.conf` desactivaba CSRF: `bypassCorsTrustedOrigins:true` + `bypassHeaders` wildcard. Además el template tenía **clave `play` duplicada** (fragilidad HOCON) | `test_cortex_csrf_protection_not_bypassed` (fallaba) | bloque CSRF-bypass eliminado del template (también resuelve el duplicado); re-renderizado; cortex healthy, auth 401 intacta |
| CORE-005 | `THEHIVE_SECRET` y `CORTEX_API_KEY` con default vacío `:-}` — firma de sesión y conector cortex se debilitaban en silencio | `test_session_and_api_secrets_fail_closed` (fallaba) | `${VAR:?required}` — config falla ruidosa y temprano |
| CORE-006 | **Cero cobertura Prometheus de los servicios core** — el corazón del SOAR solo era observable por logs; los 14 probes existían solo para el propio stack de observabilidad | `test_core_services_have_prometheus_coverage` (fallaba) | +2 probes http (`thehive:9000/api/v1/status/public`, `network-watcher:8080/health`), +4 tcp (`cortex`, `shuffle-backend`, `redis`, `tenzir`) → 28 targets, 6/6 core UP |
| CORE-007 | `cortex` y `network-watcher` eran `build:`-only sin `image:` — imágenes sin nombre/tag | `test_all_images_pinned_no_latest` (fallaba) | `image: ${...:-soar-cortex:3.2.0-1}` / `soar-network-watcher:1.0.0` |

## Puntos positivos (evidencia)

- **Secure-by-default**: `make up` siempre compone `docker-compose.hardened.yml`; el perfil relajado exige opt-out explícito (`LAB=1`).
- **Zero-trust real**: `docker-socket-proxy` con whitelist de verbos (BUILD/VOLUMES/SECRETS off), `network-watcher` sin socket crudo (`volumes: !reset []` → proxy), sidecar `api-egress-guard` con iptables DROP por defecto (TC-20).
- **Postura viva verificada**: redis `user=redis` + `cap_drop ALL` + `nnp`; thehive `user=thehive`; orborus perdió `seccomp:unconfined` (override `!override` correcto — patrón BUG-053 documentado); todos nnp+pids.
- **Auth surface sana**: thehive/cortex/shuffle responden 401 sin credenciales; swagger backend no expone UI pública.
- **Bootstrap idempotente**: `init_thehive.py` renueva keys solo si la actual no valida.
- **Higiene base completa**: 8/8 healthchecks, 8/8 límites+reservas, log rotation 10m×3, restart unless-stopped, imágenes pineadas (tras fix CORE-007).
- **Secretos fuera del repo**: `runtime/config/` gitignored; templates con placeholders; `render_configs.py` como pipeline único.
- **Trabajo de ingeniería real en orborus/worker**: warm apps, replicas, poll-time tuning documentado (PERF-004).

## Deuda residual (aceptada, con justificación)

| Ítem | Estado |
|------|--------|
| ~~`docker.sock` RW en cortex / shuffle-backend / orborus~~ | **CERRADO (SOAR-012)**: los 3 consumidores hablan con el daemon vía `DOCKER_HOST=tcp://docker-socket-proxy:2375` con whitelist de endpoints (CONTAINERS+IMAGES+NETWORKS+EXEC+EVENTS+INFO+PING). Socket RW eliminado de los 3; el mount anónimo `VOLUME /var/lib/docker` de cortex neutralizado con tmpfs. Verificado: `DockerJobRunnerSrv — Docker is available` (cortex) y `"New Worker created"` por proxy (orborus) |
| Esos 3 servicios corren root + sin cap_drop | residual del upstream — las imágenes son root-by-design; el daemon ya no está expuesto (ver fila anterior) |
| `TENZIR_WEB_MODE:-dev` por defecto (no existe `.env.hardened`) | override documentado disponible (SOAR-016) |
| ~~`SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=true`~~ | **CERRADO**: `SKIPSSL_VERIFY=false` + `SHUFFLE_OPENSEARCH_CERTIFICATE_FILE=/certs/ca.crt` (backend), CA horneada en la imagen worker (`SSL_CERT_FILE`, build context `infra/docker`), credenciales `admin:<OPENSEARCH_PASSWORD>` en URL para orborus (sin envs de auth en el binario) |
| `SHUFFLE_SWAGGER_ENABLED:-true` | superficie extra opcional; endpoint 404 en live |
| ~~Tráfico interno HTTP plano a datastores~~ | **CERRADO**: Elasticsearch 7.10.2 con `xpack.security` + TLS HTTP (api/Cortex JKS/TheHive JKS/exporter/Grafana basicAuth+CA — verificado 0 hits plaintext), OpenSearch 2.10 con security plugin + TLS transport/HTTP + `internal_users.yml` propio (backend `CERTIFICATE_FILE`, orborus URL con creds+CA en pool sistema, dashboards `opensearch.ssl.*`, api `SHUFFLE_OPENSEARCH_*`), Redis `rediss://` con TLS (api + exporter `REDIS_EXPORTER_TLS_CA_CERT_FILE`, `redis_up 1`). Residual: thehive↔cortex y backend↔frontend HTTP plano por convención lab (misma limitación que stack obs) |
| ~~`SHUFFLE_APP_FORCE_UPDATE=true` + analyzer/responder URLs externas~~ | **CERRADO**: `${SHUFFLE_APP_FORCE_UPDATE:-false}` — sin re-pull en cada boot |
| ~~Lucene index deprecated en TheHive~~ | **CERRADO**: `db.janusgraph.index.search.backend=elasticsearch` (key anidada correcta — la top-level `index.search` se ignoraba); índice `thehive_global1` reindexado automáticamente (9.4K→67K+ docs), Query API devuelve casos reales. JKS truststore `changeit` (el p12 RC2-40 no lo soporta la JRE); `ssl.enabled/truststore.location/storepassword` verificados contra `janusgraph-es` jar |
| ~~17 volúmenes anónimos dangling~~ | **CERRADO**: prune + fix del `VOLUME /var/lib/docker` de cortex |
| Todo single-instance | topología de laboratorio |
| ~~Contenedor huérfano `tenzir-node`~~ | **CERRADO DE RAÍZ** (ver sección siguiente) |
| `nginx-es.conf` proxy chunked-encoding | eliminado — config muerta sin consumidor (cortex/thehive conectan directo por TLS) |

## NIST CSF 2.0

| Función | Estado | Nota |
|---|---|---|
| Identify | 9.0 | Inventario completo, tests de arquitectura, exceptions documentadas (SOAR-012..016, security-exceptions.json) |
| Protect | 8.5 | nnp+pids+caps+proxy+egress-guard; residuals documentados (sock RW, HTTP plano) |
| Detect | 7.5 → tras fix | logs a Loki + 6 probes nuevas; **aún sin exporters de métricas de aplicación** (JVM thehive/cortex, Go shuffle) |
| Respond | 8.5 | healthchecks veraces, restart policies, runbooks obs; orborus cleanup automático |
| Recover | 8.0 | `make backup`, volúmenes nombrados; thehive data en named volumes; drill probado en obs stack |

## STRIDE residual (sobre el threat model existente)

- **Spoofing**: mitigado por API keys + basic auth internos; residual HTTP plano interno.
- **Tampering**: sock RW ×3 = superficie de escape host si un servicio se compromete (residual SOAR-012 aceptado).
- **Repudiation/InfoDisclosure**: logs centralizados en Loki; secretos renderizados fuera del repo.
- **DoS**: límites cpu/mem/pids en 100% de servicios; orborus concurrency/timeouts configurados.
- **EoP**: no-new-privileges universal + cap_drop donde aplica; root residual justificado.

## Nota por ámbito

| Dimensión | Antes | Después | Justificación |
|---|---|---|---|
| Idoneidad funcional | 9.5 | 9.5 | Cadena alerta→workflow→case funciona E2E; conectores cableados |
| Fiabilidad | 8.0 | **8.5** | Healthchecks ahora veraces (CORE-002); single-instance limita |
| Seguridad | 7.5 | **8.5** | Ports LAN + CSRF bypass + secrets fail-open corregidos; residuals documentados (sock, HTTP, dev-mode) |
| Observabilidad | 5.0 | **8.0** | Era solo-logs; ahora probes UP + targets 28/28; falta exporters de app |
| Mantenibilidad | 8.5 | **9.0** | Render pipeline corregida (CORE-003), 13 gates nuevos, templates limpios |
| Portabilidad | 6.5 | **8.5** | Path Windows hardcodeado eliminado; queda supuesto Docker-Desktop en otros puntos |
| Rendimiento | 8.5 | 8.5 | Warm apps/polling tuneado; sin cambios |
| **Global** | ~7.6 | **~8.6** | |

## Verificación final

```text
tests/architecture/test_core_stack.py      13/13 PASS (7 fallaban antes)
tests/architecture/ (suite completa)       50/50 PASS
validate_observability_configs.sh          10/10 PASS
docker ps                                  core services healthy, binds 127.0.0.1
prometheus targets                         31 targets, todos UP
grafana alert rules                        29 provisionadas, 6 core evaluando sin error
cortex                                     healthy post-conf, 401 unauth intacto
tenzir                                     https :5160, 401 sin token, 200 con token
backup_core_stack.sh drill                 8/8 volúmenes restaurados, RTO≈49s
```

## Segunda revisión (2026-11-11, ronda observabilidad/rel)

Cuatro defectos más encontrados por inyección de fallos y probes sintéticos —
cada uno verificado en vivo antes de corregirse:

| ID | Defecto | Verificación live | Fix |
|----|---------|-------------------|-----|
| CORE-008 | `blackbox-exporter` solo en `logging_net` — los 6 probes core nuevos leían **0** pese a servicios sanos (silencio de monitorización total sobre el corazón del SOAR) | `probe_success` = 0 en los 6 targets core mientras `curl` directo devolvía 200 | `+ soar_net` en blackbox networks; probes 6/6 UP |
| CORE-009 | `network-watcher` respondía **HTTP/1.0** (default `BaseHTTPRequestHandler`) — el módulo `http_2xx` exige 1.1: probe fallaba con status 200 | `probe_http_version 1` + `probe_success 0` contra `/health` | `protocol_version = "HTTP/1.1"` en `_handler.py`; rebuild → `probe_success 1` |
| CORE-010 | `JAVA_TOOL_OPTIONS=-javaagent:kanela...` se filtraba al `java -version` del launcher sbt — el actor system de Kanela (threads non-daemon) impedía que la JVM de chequeo terminara → **boot hang >10min** | `docker top`: `java -version` vivo 10min; `BindException` al probarlo a mano | `JAVA_OPTS` en su lugar (solo la JVM de app carga agentes); thehive healthy ~2min |
| CORE-011 | Redis sin `maxmemory` → `redis_memory_max_bytes=0` → `used/max=+Inf` → alerta de memoria en pending **permanente** (falso positivo) | métrica live + `CONFIG GET maxmemory` = 0 | `--maxmemory 768mb --maxmemory-policy noeviction` (fail-closed, debajo del límite 1G del contenedor) |

### Resolución de deuda + endurecimiento adicional

- **CORE-SEC-003 (SOAR-016)**: Tenzir `--mode=dev` → `--mode=server`:
  TLS con CA del lab (`gen_certs.sh tenzir-node`, CA idempotente) +
  `X-Tenzir-Token` obligatorio. Verificado: `401` sin token, `200` con
  token; token minteado por `scripts/setup/init_tenzir_token.sh`
  (`make init-tenzir-token`) y cabecera renderizada en el workflow
  desplegado (comprobado en OpenSearch). `upstream` se descartó:
  solo permite bind a localhost. **Bug latente encontrado y corregido**:
  `MSYS_NO_PATHCONV=1` hacía que `gen_certs.sh` entregara paths `/c/...`
  literales a `openssl.exe` → generación silenciosamente rota en Git Bash.
- **Defaults fail-safe**: `SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY:-false`,
  `SHUFFLE_SWAGGER_ENABLED:-false` (era `true`; swagger no servía rutas
  de todos modos — ahora es opt-in explícito).
- **CORE-OBS-005**: `redis-exporter` (pinned, non-root estático,
  `cap_drop ALL`, `read_only`, creds por env) → `up{job="redis"}=1` con
  ~30 series. Sin healthcheck de contenedor: imagen distroless sin
  shell — señal de salud = scrape (exención documentada en test).
- **CORE-OBS-002**: JMX en thehive y cortex (jmx_prometheus_javaagent
  1.0.1 SHA-verificado + kanela 2.0.0 para kamon) → 101 series cada
  uno, `up=1` en Prometheus.
- **CORE-OBS-008**: grupo `core-availability` en Grafana — 6 reglas
  (down P0, scrape P1, redis mem/evictions, JVM heap, tenzir stalled)
  evaluando sin `lastError`.
- **CORE-REL-003/004**: `backup_core_stack.sh` — 8 volúmenes
  (6 named + 2 anónimos de tenzir resueltos en vivo), tar+gzip+sha256,
  drill a volúmenes `*_drill` con conteo de ficheros vs archivo →
  **8/8 restaurados en 49s** (RTO evidencia). Targets
  `make backup-core` / `make drill-core` (win+linux).
- **Bug API**: `/openapi.json` devolvía 500 — `_Req` era un alias
  local de `fastapi.Request` dentro de una función; el ForwardRef
  no resolvía al generar el schema. Import top-level → 200.
- **Feasibility negativa documentada**: shuffle-backend/orborus/tenzir
  no exponen `/metrics` nativo (probado 404/000) — cobertura vía
  cAdvisor + blackbox + redis-exporter; no se fuerza instrumentación.

### Nuevo scoring por ámbito

| Dimensión | R1 | R2 | Justificación R2 |
|---|---|---|---|
| Idoneidad funcional | 9.5 | **9.5** | Workflow recreado con token tenzir; cadena intacta |
| Fiabilidad | 8.5 | **9.0** | Backup core verificado con drill (RTO 49s); failure-injection redis ejercitada y recuperada; boot-hang JVM eliminado |
| Seguridad | 8.5 | **9.0** | Tenzir con TLS+token; defaults fail-safe; OpenAPI bug cerrado; residuals documentados (sock RW ×3, HTTP plano interno) |
| Observabilidad | 8.0 | **9.0** | 31 targets UP, JMX+redis exporters, 6 reglas core evaluando, gap de red blackbox cerrado |
| Mantenibilidad | 9.0 | **9.0** | +runbooks core (3), scripts init/backup, gates 50/50 |
| Portabilidad | 8.5 | **9.0** | `gen_certs.sh` y `backup_core_stack.sh` MSYS-safe (`cygpath`); sin paths Windows |
| Rendimiento | 8.5 | **8.5** | maxmemory acotado; sin cambios estructurales |
| **Global** | ~8.6 | **~9.0** | |

### Deuda residual actualizada

| Ítem | Estado |
|------|--------|
| `docker.sock` RW en cortex/shuffle-backend/orborus | residual aceptado SOAR-012 (DinD necesario) |
| ~~HTTP plano interno (thehive↔cortex, shuffle→OS, redis)~~ | **CERRADO**: thehive↔cortex HTTPS :9443, backend↔frontend HTTPS :5443 (sidecar TLS + ingress-guard), shuffle→OS y redis con TLS+auth. Residual: listener Go del backend en `127.0.0.1:5001` (binario upstream sin TLS) bloqueado externamente por iptables del `shuffle-backend-ingress-guard` |
| ~~Contenedor huérfano `tenzir-node`~~ | **CERRADO DE RAÍZ**: `tenzir/tenzir:main` sin pinnar, dev-mode sin auth en 0.0.0.0:5160 (verificado 200 sin credenciales). El `rm` no bastaba: **Orborus lo auto-aprovisionaba** (~30s tras cada borrado) porque `SHUFFLE_PIPELINE_URL` activa el pipeline-management (incluso vacío cae al default `http://tenzir-node:5160`). Fix: `SHUFFLE_SKIP_PIPELINES=true` (default, opt-out documentado) + `SHUFFLE_PIPELINE_URL` vacío; contenedor y `tenzir-network` eliminados; verificado >2min sin recreación. El workflow usa acciones HTTP contra el alias `tenzir-node` del nodo gestionado (TLS+token) — sin dependencia del pipeline de orborus |
| `soar_taxii` (compose warning de orphan) | **CONSERVADO**: servicio del propio proyecto (`docker-compose.taxii.yml`), imagen `soar-taxii`, sin puertos publicados, healthy — el warning solo indica que no está en el set de ficheros actual |
| ~~`soar_api` drift: corría sin overlay hardened~~ | **CORREGIDO**: el contenedor se había recreado con un set parcial de ficheros → uid=root + `/var/run/docker.sock:rw` + sin `DOCKER_HOST`. Recreado con el set completo (`make up`): uid=1000, sin socket, DOCKER_HOST→proxy restringido, `api-egress-guard` activo. Verificado: `/health` 200, `/openapi.json` 200 |
| ~~Proxy duplicado `soarransomwarelab_docker_proxy`~~ | **ELIMINADO**: residuo de una invocación con `-p` por defecto (nombre de directorio). Queda `soar_docker_proxy` (project=soar) |
| ~~`SHUFFLE_APP_FORCE_UPDATE=true`~~ | **CERRADO**: `${SHUFFLE_APP_FORCE_UPDATE:-false}` — sin re-pull de GitHub en cada boot (egress + no determinismo). Catálogo intacto: 32 apps en OpenSearch `workflowapp`, workflow verificado |
| Lucene index en TheHive (deprecated desde 5.1) | warning oficial en logs; migración a ES = cambio estructural mayor — deuda registrada |
| ~~Recreate pendiente de shuffle-backend para defaults SKIPSSL/SWAGGER~~ | **APLICADO**: `SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=false` y `SHUFFLE_SWAGGER_ENABLED=false` verificados en el env del contenedor |
| ~~401 periódicos `No 'Authorization' header` en OpenSearch~~ | **CERRADO**: el loop del GC lanzaba `backfill_node_timings.py` cada 300s; el script leía `OPENSEARCH_USERNAME/PASSWORD` (inexistentes en el contenedor — solo `SHUFFLE_OPENSEARCH_*`) → POST `/workflowexecution/_search` sin auth. Diagnóstico vía `http.tracer` + `XFFResolver` (URI + IP origen). Fix: jerarquía `SHUFFLE_OPENSEARCH_*`→`OPENSEARCH_*` en script y en `routes_analytics` (`NodeTimingExtractor`). Verificado: 2 ventanas ×300s, 0 warnings |
| ~~`status.keyword` sin matches tras rollover~~ | **CERRADO**: el mapping rollover es `status: keyword` plano — `term status.keyword` y aggs sobre `.keyword` devolvían vacío silencioso (GC nunca encontraba stale, backfill 0 FINISHED). Fix: OR-bool `status`/`status.keyword` en `stale_execution_gc`, `backfill_node_timings`, TC-38; aggs con fallback `status`→`status.keyword` en `generate_e2e_report` y TC-KPI-06 (patrón ya usado en `clean_shuffle_executions._status_filter`). Backfill verificado: 20 FINISHED escaneados y parcheados |
| `thehive-app` (kamon embedded reporter :9095) | **retirado** — kanela-agent.jar no empaqueta kamon-prometheus; cobertura app vía JMX |
