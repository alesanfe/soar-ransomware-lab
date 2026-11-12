# ADR-0014 — Endurecimiento del stack de observabilidad (S3 IAM, renderer, excepciones de capacidades)

- **Estado**: Aceptado
- **Fecha**: 2026-11-10
- **Decisores**: owner del repo

## Contexto

El backlog OBS de 203 ítems exigía cerrar las deudas detectadas en la
evaluación ISO/IEC 25010 + NIST 800-92/137 del stack de logging
(`infra/docker/compose/logging/docker-compose.logging.yml`): credenciales
S3 por defecto, `s3-init` fail-open, collector sin healthcheck, alertas con
referencias rotas, `IGNORE_HTTPS_ERRORS` del renderer y ausencia de
validadores en CI.

Varias decisiones tenían alternativas con trade-offs reales; este ADR fija
las elegidas y las excepciones justificadas para que el hardening no se
"desaprenda" en futuros refactors.

## Decisión

### 1. IAM S3 por componente con identidades estáticas + `policyNames`

Loki y Tempo usan credenciales independientes (`LOKI_S3_*`, `TEMPO_S3_*`
en `.env`, rotadas desde el par por defecto `soar-s3/***` ya revocado)
definidas en `infra/docker/config/seaweedfs/iam.config.json`. El scoping
por bucket se aplica con `policyNames` → políticas AWS con `Resource`
ARN (`arn:aws:s3:::loki/*`), no con usuarios dinámicos.

**Alternativa descartada**: crear usuarios en caliente vía `s3.configure`
dentro de `s3-init`. El comando sólo gestiona identidades dinámicas y
devolvía `user loki not found` sobre las estáticas; además introduce un
plano de control dinámico que complica reproducibilidad.

Verificación en vivo: SigV4 loki→loki `200`, loki→tempo `403 AccessDenied`,
par por defecto `403 InvalidAccessKeyId` (test
`test_bucket_scoping_enforced`).

### 2. `s3-init` fail-closed con sonda real

El job inicializador hace `set -euo pipefail`, crea buckets tolerando el
`already exists` idempotente, y ejecuta un ciclo write→read(retry por
consistencia eventual)→delete contra el endpoint filer. `depends_on:
condition: service_completed_successfully` en loki/tempo — si el storage
no está listo, nada arranca en falso.

### 3. Pipeline OTel con protección de memoria

`memory_limiter` (spike 30% / límite 80% de 512m cgroup), `batch`,
`sending_queue` con `retry_on_failure` + backoff en el exportador OTLP a
Tempo. Healthcheck **image-native**: `/otelcol validate --config=…` — la
imagen es distroless (sin shell, `wget` ni `ls`).

### 4. `IGNORE_HTTPS_ERRORS=true` del renderer — aceptado

El Grafana image renderer lanza Chromium headless contra
`https://grafana:3000`. Chromium usa su trust store NSS interno; **no
existe variable de entorno ni flag CLI** para inyectar una CA adicional en
la imagen oficial. Las alternativas son:

- **A**: rebuild de la imagen añadiendo la CA a `/etc/ssl/certs` + base NSS
  (`certutil`) — coste de mantener un fork por cada update de renderer.
- **B**: servir Grafana también en HTTP interno sólo para el callback —
  rompe la política "todo TLS interno" (GRAF-D10).
- **C (elegida)**: `IGNORE_HTTPS_ERRORS=true`. El tráfico renderer→grafana
  sigue cifrado en tránsito; lo que se pierde es autenticación del peer
  dentro de `logging_net` (red bridge aislada, sin salida externa). El
  riesgo es MitM **interno**, acotado por `no-new-privileges`,
  `cap_drop: ALL` y ausencia de publicación de puertos del renderer.

Residual registrado en el risk register (R-06) y RB-13. Si el lab evoluciona
a render externo o a red compartida con tenants, migrar a la opción A.

### 5. Excepciones de capacidades documentadas

`cap_drop: ALL` + `no-new-privileges` en todo el stack salvo:

- `cadvisor`: `privileged: true` + mounts host (`/`, `/var/run`, `/sys`,
  `/var/lib/docker`) — necesita cgroupfs del host para enumerar
  contenedores. Sin alternativa: es el precio de métricas de contenedor.
- `s3-vol2` (SeaweedFS volume): conserva `SETUID`/`SETGID` — el entrypoint
  hace `su-exec` para bajar a UID no-root; con `cap_drop: ALL` falla con
  `su-exec: setgroups: Operation not permitted` (crash-loop verificado).
- `promtail`: `cap_drop: ALL` + `cap_add: [DAC_OVERRIDE]` — docker.sock es
  `srw-rw----` propiedad del uid del daemon (1001 en Docker Desktop); sin
  DAC_OVERRIDE root pierde su bypass y `docker_sd` recibe EACCES (verificado:
  `targets_active=0`, `docker_target_entries` congelado). Con la cap:
  637k+ entries/20MB enviadas a Loki.

El resto (prometheus, loki, tempo, otel, grafana, promtail, renderer,
blackbox, exporter ES, s3-init) corre con privilegios mínimos verificados.

### 6. ISCM por watchdog + canal silencioso

`obs_iscm_watchdog` (`expr: vector(1)`, firing permanente, repite 4h) cierra
el lazo eval→notify→API exigido por NIST 800-137; `obs_alert_channel_silent`
dispara si la API no registra notificaciones en >4.5h — detecta un canal
muerto aunque las reglas evalúen bien.

## Consecuencias

- **Positivas**: credenciales por defecto eliminadas, least-privilege real
  en storage, pipeline OTel acotado en memoria con reintentos, lazo ISCM
  cerrado y medido, excepciones privilegiadas explícitas y justificadas.
- **Negativas**: renderer conserva `IGNORE_HTTPS_ERRORS` (residual R-06);
  cadvisor privileged es irreducible; dos racks SeaweedFS viven en el mismo
  host (R-07) — redundancia de contenedor, no de máquina.
- **Seguimiento**: `scripts/ci/validate_observability_configs.sh` es el
  gate que impide regresiones de config (promtool, loki/tempo/promtail/
  otelcol/blackbox validators + pinning + LF). El test vivo
  `tests/integration/test_observability_live.py` cubre TLS, IAM, targets,
  contact point y watchdog.
