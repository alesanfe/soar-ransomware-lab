# 24 — Registro del backlog de observabilidad (203 ítems)

## 1. Resumen

### 1.1 Objetivo

Registrar el estado de los 203 ítems del backlog OBS del stack de
observabilidad (Grafana/Loki/Tempo/Prometheus/OTel/Promtail/SeaweedFS/
blackbox/cadvisor/renderer) tras el sprint ejecutado el 2026-11-10.

### 1.2 Contexto

El backlog cubría: regression tests de alertas, healthchecks, init
fail-closed, rotación de secretos, IAM scoping, redacción, buffering/retry
OTel, alerting de auto-monitorización, probes blackbox, TLS del renderer,
hardening, validadores, gates CI, backups/recovery, tests de fallo, SLOs,
HA, WORM/integridad, notificación externa, documentación, gestión de
riesgo y gates de score.

Convención de estados: **DONE** (implementado + verificado en vivo),
**DONE-STATIC** (implementado, gate CI/test), **ADR** (decisión aceptada y
documentada), **RISK** (limitación estructural en risk-register),
**PENDING** (no ejecutado), **N/A-LAB** (fuera del alcance del lab —
horizonte producción, documentado).

## 2. Estado por bloque

### 2.1 Sprint ejecutado (DONE / DONE-STATIC)

| Bloque | Ítems (referencias OBS) | Estado | Evidencia |
|--------|------------------------|--------|-----------|
| Regression tests de referencias de alertas (parse refIds, self-ref, forward-ref, ciclos directos/indirectos, duplicados, mutaciones) | OBS-001..005 | **DONE-STATIC** | `tests/architecture/test_observability_stack.py` 18/18; cazó bug real (`cortex_success_rate_low` D→D) |
| Healthcheck OTel (distroless) | OBS-006 | **DONE** | `/otelcol validate`, container `healthy` |
| `s3-init` fail-closed + creación + sonda write/read/delete + `depends_on` completion | OBS-007..010 | **DONE** | logs `soar_s3_init`, probes verdes |
| Alertas de auto-monitorización: absent/down, target loss, NoSuchBucket, restart loop, watchdog, spans dropped, cert expiry, canal silencioso | OBS-011/021/022/023/025/046/085/127 | **DONE** | 9 reglas `obs_*`, 22/22 evalúan sin error |
| Rotación de credenciales S3 + bloqueo de defaults + vars requeridas | OBS-012/013/148 | **DONE** | 403 verificado SigV4 |
| IAM scoping por bucket | OBS-015 | **DONE** | `policyNames`+ARN, 403 cross-bucket |
| Redacción de secretos en Promtail (auth, bearer, cookies, api keys, webhooks) | OBS-070 | **DONE-STATIC** | template + `promtail -check-syntax` |
| OTel memory_limiter/batch/sending_queue/retry | OBS-076..080 | **DONE** | collector healthy, config validada |
| Blackbox probes HTTP/TLS + cert-expiry metrics | OBS-023/046/048/053 | **DONE** | 14 probes up |
| Hardening `no-new-privileges`/`cap_drop` selectivo + excepciones | OBS-036/037 | **DONE** | ADR-0014 §5 |
| Validadores de montes (paths, existencia, tipo, RO) | OBS-087 | **DONE-STATIC** | architecture test mounts |
| Validación de configs en CI (compose/promtool/loki/tempo/promtail/otelcol/blackbox/pinning/LF/gitleaks) | OBS-088/089/097/098/109/147 | **DONE-STATIC** | `validate_observability_configs.sh` 10/10 + job `observability-configs` |
| Live checks: targets, reglas, contact point webhook, ingestion `grafana_alert` | OBS-005/087/130 | **DONE** | `test_observability_live.py` 14/14 |
| Severity + runbook en todas las reglas | OBS-049 | **DONE** | RB-16..23 escritos y anclados |

### 2.2 Decisiones documentadas (ADR/RISK)

| Ítem | Estado | Referencia |
|------|--------|-----------|
| Renderer `IGNORE_HTTPS_ERRORS` (Chromium NSS) | **ADR/RISK** | ADR-0014 §4, R-06, RB-13 |
| cadvisor `privileged` | **RISK** | ADR-0014 §5, R-08 |
| s3-vol2 caps su-exec | **ADR** | ADR-0014 §5 |
| S3 mismo host (2 racks lógicos) | **RISK** | R-07, RB-14 |
| Single-instance filer/gateway/Tempo/Loki | **RISK** | ADR-0012 análogo, doc 19 §5.1 |

### 2.3 Sprint 2 ejecutado (2026-11-10 tarde)

| Bloque | Ítems | Estado |
|--------|-------|--------|
| Backup/restore drill del stack obs + RTO/RPO documentado | OBS-140s | **DONE** — `scripts/maintenance/backup_obs_stack.sh` (`backup`/`drill`), targets `make backup-obs`/`drill-obs` en ambos Makefiles. Verificado: 7/7 volúmenes (grafana×2, loki, tempo, prometheus, s3×2) → tar.gz verificado (gzip -t + miembros>0); drill restaura a volúmenes `*_drill` con markers de contenido — **RTO medido 94s**, RPO = cadencia de backup (manual, lab) |
| Failure-injection: matar tempo → `obs_probe_down` dispara → recovery → resuelve | OBS-150s | **DONE** — drill real ejecutado: `docker stop soar_tempo` → pending(+60s) → **firing(+4m, `for:3m`)** → `docker start` → **inactive**. Canal notificación verificado (`soar_grafana_alert_notifications_total` incrementa). Cazó 3 bugs reales (ver abajo) |
| Retention enforcement | OBS-160s | **DONE** — tempo `retention.go:97 deleting block` a las 23:18 (sweep 48h real); loki `applying retention with compaction` + `cleaning up unwanted indexes` cada ~1min (720h). Purga real de bloques >48h demostrada |
| SLI/SLO + burn-rate | OBS-170s | **DONE** — regla `obs_admission_slo_burn_rate`: 2 ventanas (5m+1h), umbral 14.4× presupuesto 1% (SLO 99%), `noDataState: OK` (lab idle). SLI: `dead/(processed+dead)` sobre métricas de admisión existentes |
| Alert→Loki `grafana_alert=1` ingestion check automatizado | OBS-130 | **DONE** — `test_grafana_alert_lines_reach_loki` (label `compose_service="api"`, no `container_name`) |
| disk-full simulado / test de capacidad | OBS-150s | **DONE (parcial)** — capacidad verificada: `scripts/maintenance/obs_capacity_report.sh` (`make capacity-obs`) reporta los 7 volúmenes obs + headroom real del FS de datos vía `df` sobre mount de named volume (probe `soar_loki:/loki` → `soar_api:/` fallback). Estado actual: **FS 4% usado**, mayor volumen prometheus_data 254.8MB. El drill completo disk-fill sigue siendo procedimiento **manual** (es destructivo sobre el FS compartido): crear volumen scratch `s3_fill_test`, `docker run --rm -v s3_fill_test:/f alpine dd if=/dev/zero of=/f/fill bs=1M`, confirmar ENOSPC en seaweedfs → `obs_s3_objectstore_errors` dispara, `docker volume rm s3_fill_test` |

### 2.3b Bugs reales cazados por el failure-injection

| Bug | Causa | Fix |
|-----|-------|-----|
| **Promtail no enviaba nada a Loki desde el hardening** | `cap_drop: ALL` eliminó `CAP_DAC_OVERRIDE` → EACCES en docker.sock (`srw-rw----` uid 1001) → `targets_active=0`, ingest parado | `cap_add: [DAC_OVERRIDE]` + comentario; alerta `soar_loki_ingest_stalled` lo detectó correctamente (alerta funcionando, no falso positivo) |
| **`obs_alert_channel_silent` perma-firing** | `increase(metric[270m])` devuelve una serie por `{status}` — `resolved`/`other` siempre 0 → `lt 1` siempre cierto | `sum(increase(...))` — agregado antes del umbral |
| **`obs_s3_objectstore_errors` self-match (clase RB-06)** | la query de eval queda logueada por loki (`caller=metrics|engine|roundtrip.go`, `msg="executing query"`) y contiene la regex → se auto-matchea | `!~` excluye los callers de query-echo (verificado: expr devuelve vacío) |

**Estado post-sprint**: 23 reglas provisionadas, solo `obs_iscm_watchdog` firing (por diseño). `High error log rate` resolvió tras la tormenta de restarts. Suites: 19/19 architecture, 15/15 live, 10/10 config gate.

### 2.4 Fuera del alcance del lab (N/A-LAB — horizonte producción)

| Ítem | Disposición |
|------|-------------|
| HA multi-host (Loki/Tempo/Grafana replicados) | No aplica a lab single-host; R-07 |
| Object storage externo gestionado (S3 real/MinIO remoto) | R-07 — externalizar solo si pasa a multi-host |
| WORM/immutability de bloques Tempo | Fuera de SeaweedFS lab; requiere object-lock |
| mTLS completo receivers OTel / ES xpack | Third-party TLS interno; residual documentado RB-13 |
| Notificación externa (SMTP/PagerDuty/OpsGenie) | Lab usa webhook interno `soar-api-webhook`; externo = config de contact point, no código |
| mTLS Grafana↔API | Canal interno cifrado + service token; mTLS = producción |

## 3. Gates de madurez (estado)

| Gate | Estado |
|------|--------|
| Sin fallos silenciosos conocidos | ✅ watchdog + alert-channel-silent + s3-init fail-closed + ingest-stalled (cazó la regresión promtail) |
| Todas las reglas evaluando sin error | ✅ 23/23 health ok |
| Todos los targets activos | ✅ 22/22 up |
| E2E automatizado del stack | ✅ 15/15 live tests |
| Alerting independiente del servicio monitorizado | ✅ contact point → api (fuera del loop Grafana); lazo cerrado verificado con kill→fire→restore→resolve |
| Secrets no-default verificados | ✅ 403 default |
| TLS con verificación CA en consumidores | ✅ scrape/push/datasource/health (renderer = excepción ADR) |
| Restore test exitoso | ✅ drill 7/7 volúmenes, RTO 94s (`backup_obs_stack.sh drill`) |
| Evidencia de retention efectiva | ✅ tempo `deleting block` (48h sweep real) + loki compactor retention cycles |

## 4. Referencias

- `docs/19-eval-observability-stack.md` §Séptima revisión — evidencia.
- `docs/adr/0014-observability-stack-hardening.md` — decisiones.
- `docs/risk-register.md` R-06..R-08 — residuales aceptados.
- `docs/20-observability-runbooks.md` RB-16..23 — runbooks obs_*.
- `scripts/ci/validate_observability_configs.sh` — gate CI.
- `tests/architecture/test_observability_stack.py`,
  `tests/integration/test_observability_live.py` — tests.
