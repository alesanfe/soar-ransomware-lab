# Evaluación multi-marco — Stack de observabilidad (Grafana/Loki/Prometheus/Promtail/Tempo/OTEL/blackbox/cAdvisor/S3)

> Evaluación formal del stack de observabilidad
> (`infra/docker/compose/logging/docker-compose.logging.yml`,
> `infra/docker/config/{prometheus,prometheus-web,blackbox,otel-collector,tempo,loki-config,seaweedfs}`,
> overlay `docker-compose.hardened.yml`) siguiendo la metodología de
> `docs/25`/`27`-`32`: cada hallazgo se verifica en vivo y queda pineado
> con gates (`tests/architecture/test_observability_stack.py`,
> **26 gates**). Revisión 2026-11-11: **10 hallazgos** corregidos,
> residuales documentados. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica del stack |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| CIS Docker Benchmark | Control a control (usuario, caps, rootfs, recursos, socket) |
| NIST CSF 2.0 | DE (detección), PR.PS (plataforma), PR.DS (datos) |
| STRIDE | DoS, information disclosure, elevation of privilege |
| SRE Golden Signals | El propio stack ES la capa de señales — se evalúa su propia cobertura |
| OWASP ASVS | Secrets handling, TLS interno |

## Evidencia recolectada (en vivo, stack recreado)

```
servicios       14 (grafana-db, grafana, renderer, s3, s3-vol2, s3-init,
                loki, promtail, otel-collector, tempo, prometheus,
                cadvisor, es-exporter, blackbox) — todos healthy
privilegios     0 privileged (cadvisor era privileged:true — eliminado)
uids            grafana 472, loki/tempo/otel 10001, prometheus+es-exp
                nobody, blackbox 65534, promtail 65534, cadvisor root
                (necesario para cgroups — nnp+cap_drop+RO), s3 su-exec
pids            13/13 long-running con límite (era 7/13)
read_only       10/13 (era 2/13) — incl. grafana/loki/tempo/prometheus
socket          0 mounts de docker.sock (promtail → docker-socket-proxy)
cap_add         0 (promtail ya no necesita DAC_OVERRIDE)
secrets         todos :? fail-closed (era: 4 vars fail-open)
TLS             prometheus web TLS + CA pinning en scrapes https;
                loki/tempo TLS internos; grafana :8084 loopback HTTPS
targets         39/39 Prometheus targets up tras todos los cambios
logs→loki       verificado: entradas de soar_api llegan vía promtail→proxy
blackbox        probe https_2xx→loki: probe_http_status_code=200
cadvisor        49 series container_cpu_* sin privileged (antes: idem
                con privileged:true)
make up         set por defecto parsea (37 svcs) — antes FALLABA con
                'oauth2-proxy-web has neither image nor build context'
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| OBS-EVAL-001 | **6/13 servicios sin `pids`** (prometheus, otel, cadvisor, blackbox, es-exporter, s3-vol2) — superficie de fork-bomb sin cota | `docker inspect` → `PidsLimit <nil>` | pids en overlay (512/128/256/128/64/512, calibrados al perfil Go de cada uno); gate `test_every_service_has_pids_limit` |
| OBS-EVAL-002 | **cadvisor `privileged: true`** — concede TODAS las caps + todos los devices del host rw para recolectar métricas RO | recreado sin privileged → healthy, 49 series métricas | privileged eliminado + nnp añadido + RO; los mounts `/:/rootfs`, `/sys`, `/var/lib/docker` ya eran explícitos :ro; gate `test_no_privileged_services` |
| OBS-EVAL-003 | **4 secretos fail-open**: `ELASTIC_PASSWORD:-` (exporter scrapea ES sin auth → métricas vacías silenciosas), `OIDC_CLIENT_SECRET:-soar-lab-oidc-secret` (mismo patrón corregido en SSO-EVAL-002), `GRAFANA_ADMIN_PASSWORD` e `INTERNAL_SERVICE_TOKEN` pasaban vacío si faltan | grep compose | `${VAR:?}` ×4 — fallo en tiempo de config, no en runtime; gate ampliado |
| OBS-EVAL-004 | **blackbox uid=0, promtail uid=0** — imágenes default-root sin necesidad | `docker exec id` | `user: "65534:65534"` en ambos + RO rootfs; gate `test_needs_no_root_run_as_non_root` |
| OBS-EVAL-005 | **race en s3-init**: el healthcheck de s3 solo prueba master `/cluster/status` — el filer (path que ejercitan las probes) puede ir por detrás; un `compose up` sobre stack caliente re-ejecutó el one-shot y murió en read-probe (bloqueando a loki/tempo vía `service_completed_successfully`) | `s3-init` exit 1 observado en vivo | write-probe con 15×2s retry (ejercita el path real del filer) + read-probe ampliado 5→15; verificado: segunda corrida exit 0 |
| OBS-EVAL-006 | **`make up` por defecto roto**: el overlay hardened referenciaba `keycloak`/`oauth2-proxy-*`/`taxii` sin imagen — servicios de overlays opcionales ausentes del set por defecto → `docker compose config` fallaba | `config --services` → error confirmado | Claves movidas a `docker-compose.sso.yml`/`taxii.yml` (convención victim-sim: auto-endurecidos); set por defecto parsea 37 svcs, set completo también; gate `test_hardened_refs_resolve_in_default_set` |
| OBS-EVAL-007 | **promtail con socket crudo + `DAC_OVERRIDE`** — excepción documentada que decía "podría moverse al proxy cuando se verifique" | verificado: discovery + tailing funcionan vía proxy (logs llegan a Loki) | `docker_sd.host: tcp://docker-socket-proxy:2375`; socket mount + DAC_OVERRIDE + excepción eliminados; **proxy movido al set por defecto** (un `depends_on` desde logging no puede resolver un servicio del overlay opcional); gate `test_no_raw_docker_socket_mounts` + inventario socket actualizado |
| OBS-EVAL-008 | **8/13 sin `read_only`** en servicios stateless o con estado en volumen | recreate + health | RO en grafana/loki/tempo/prometheus/cadvisor + otel/blackbox/es-exporter (+ tmpfs /tmp donde aplica); 39/39 targets up; gate `test_stateless_and_volume_backed_services_readonly` |
| OBS-EVAL-009 | **docker-socket-proxy sin healthcheck** — punto único de fallo para promtail (docker_sd), network-watcher, cortex DinD y orborus: un haproxy colgado rompía todo el consumo del socket sin señal | proxy healthy verificado tras recreate | `/_ping` (verbo PING whitelisted) como healthcheck 30s/5s/×3; gate `test_proxy_has_app_level_healthcheck` |
| OBS-EVAL-010 | **job `system-logs` muerto** en promtail — `__path__: /var/log/**` resolvía DENTRO del contenedor (sin mount de host): solo tailaba residuos de build (apt/dpkg) y, como uid 65534, generaba `permission denied` en bucle | `docker exec ls /var/log` → residuos jul-2024; logs post-fix limpios | job eliminado del template + config runtime re-renderizada; gate `test_promtail_has_no_dead_file_targets` |

## Puntos positivos (evidencia previa al fix)

- **TLS interno extremo a extremo**: Prometheus web con `web.yml` TLS + scrapes https con `ca_file` pineada; Loki/Tempo TLS internos; Grafana sirve HTTPS en :8084 loopback con cert de la CA lab.
- **S3 con identidades por componente** (OBS-015): loki/tempo tienen credenciales scoped por bucket, IAM template sin secretos commiteados, entrypoint fail-closed.
- **s3-init fail-closed por diseño**: `service_completed_successfully` bloquea a loki/tempo si el bootstrap falla — fail-fast en boot, no NoSuchBucket tardío.
- **Réplica de datos**: `replicaPlacement 010` s3↔s3-vol2 (rack separado, misma host — limitación documentada).
- **OTEL pipeline endurecido**: `memory_limiter` primero, `batch`, `retry_on_failure`, `sending_queue` — gates OBS-076..079 previos.
- **cAdvisor ya calibrado** (OBS-021): `--docker_only`, housekeeping 60s, métricas recortadas — resuelve timeouts reales observados.
- **Retenciones acotadas**: prometheus 7d/2GB, logs 10m×3 en todos.
- **Alertas con severity + runbook** pineados por gate; mutation-test de auto-referencia en expresiones (OBS-001/002).
- **Pipeline de secretos**: redacción en promtail antes de Loki (creds MISP/webhook tokens).
- **Backups**: `make backup-obs`/`drill-obs`/`capacity-obs` existen para grafana/loki/tempo/prometheus/s3.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| `logging_net` no es `internal: true` | `GF_INSTALL_PLUGINS` descarga el plugin de comunidad en el primer arranque — volumen fresco sin egress → grafana sin datasource JSON. Mitigado: solo grafana publica puerto (loopback), resto del stack no tiene egress in necesario |
| cadvisor corre root (uid=0) | Lectura de `/sys/fs/cgroup` y OOM via `/dev/kmsg` lo exige; mitigado con nnp + cap_drop implícito del perfil + RO rootfs + mounts :ro |
| s3/s3-vol2 entrypoint su-exec root→seaweed | Constraint upstream documentada (nnp exceptuado, igual que MISP upstream) |
| positions de promtail efímeros | Decisión deliberada documentada: restart re-escanea logs actuales (entradas viejas rechazadas por Loki "too far behind" unos minutos tras recreate) |
| remote-write receiver sin auth extra | Listener TLS-only en red interna; escritores conocidos (tempo); un writer malicioso necesitaría ya estar en logging_net |
| s3-init sin healthcheck/log-rotation | One-shot por diseño — warning aceptado del validador (no crítico) |

## STRIDE

| Amenaza | Control | Estado |
|---|---|---|
| Spoofing | TLS en scrape/push/query paths + CA pineada | ✅ |
| Tampering | Secrets `:?` fail-closed, IAM templated, mounts :ro | ✅ |
| Info disclosure | Sin socket crudo, sin caps extras, RO rootfs | ✅ |
| DoS | pids ×13, mem/cpu limits, retenciones, memory_limiter OTEL | ✅ |
| EoP | users no-root donde aplica, 0 privileged, nnp | ✅ |

## Regresión

- **26/26 gates** `test_observability_stack.py` verdes.
- **144/144** `tests/architecture/` totales verdes (incluye gates sso/taxii
  re-anclados al modelo self-hardened + inventario de sockets).
- `validate_compose_security.py --profile hardened`: **0 critical, 3
  warning** (warnings preexistentes documentados).
- Vivo: 39/39 targets up; logs api→loki vía proxy verificados; cadvisor
  49 series sin privileged; s3-init re-run exit 0.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Idoneidad funcional | 9.0 → **9.5** — pipeline métricas+logs+traces+probes+alertas+dashboards completo |
| Fiabilidad | 7.5 → **9.5** — s3-init race cerrada, retenciones, failover buckets verificados |
| Seguridad | 7.0 → **9.5** — 0 privileged, 0 socket mounts, 0 caps extra, secrets fail-closed |
| Observabilidad (auto-cobertura) | 8.5 → **9.5** — 39/39 targets, probes https/tcp, alertas con runbook |
| Mantenibilidad | 8.0 → **9.5** — 26 gates, excepciones con expiry, validador 0-critical |
| Portabilidad | 8.5 → **9.5** — overlays opcionales self-hardened, default set parseable |
| **Global** | ~8.1 → **~9.5** |
