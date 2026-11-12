# Evaluación multi-marco — Stack Victim (victim-sim)

> Evaluación formal de `docker-compose.victim.yml` siguiendo la
> metodología de `docs/25`/`27`/`28`/`29`: cada hallazgo se verifica con
> evidencia viva y queda pineado con tests
> (`tests/architecture/test_victim_stack.py`, 12 gates). Revisión
> 2026-11-11: **5 bugs** corregidos, 0 debilidades residuales.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| CIS Docker Benchmark | Controles 4.x/5.x |
| NIST CSF 2.0 | Identify / Protect / Detect / Respond / Recover |
| STRIDE | Threat model sobre la superficie real |
| OWASP ASVS | (parcial — no es un servicio con API; aplica como workload) |
| SRE Golden Signals | Latency / Traffic / Errors / Saturation del workload |

## Evidencia recolectada (live)

```
victim_sim   user=nobody(65534) caps=drop_ALL nnp ro=true pids=32
             mem=256M cpu=0.5 restart=unless-stopped logrotate=10m×3
             ports:ninguno  red: solo soar_net
healthcheck  PID1=sleep verificado → healthy en 30s
atomic run   T1003 ejecutado como nobody → rc=0, /tmp/lsass_dump_sim.dmp
allowlist    label soar.victim=true + name victim_sim → containable
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| VICTIM-EVAL-001 | `victim-sim` corría como **root** (sin `user:`) — las técnicas atómicas no necesitan privilegios y un workload de "víctima" con root es el peor patrón posible si se escapa el contenedor | `docker inspect user=""` | `user: "65534:65534"` (nobody); verificado: técnica T1003 ejecuta rc=0 como nobody |
| VICTIM-EVAL-002 | **`restart: no`** — la política por defecto dejaba el victim muerto tras un `docker restart` o reboot del daemon sin que nadie lo notara | `inspect restart=no` | `restart: unless-stopped` |
| VICTIM-EVAL-003 | **Sin pids limit** — una técnica fork-bomb podía agotar la tabla de procesos del daemon | `inspect pids=nil` | `pids: 32` (sleep + sh + python3 esporádico) |
| VICTIM-EVAL-004 | Healthcheck `python -c exit(0)` — probaba que python existe, no que el payload (sleep supervisor) esté vivo | lectura del compose | `http.client`-style check: lee `/proc/1/comm` y exige `sleep` |
| VICTIM-EVAL-005 | **Sin log rotation** — el stream de telemetría atómica a stdout es unbounded → llena el disco en sesiones largas | `inspect LogConfig={}` | `json-file` 10m×3 igual que el resto del lab |

## CIS Docker Benchmark — control a control

| Control | Estado | Evidencia |
|---|---|---|
| 4.1 usuario no-root | ✅ | `user=65534:65534` (nobody) |
| 4.5 imagen pineada | ✅ | `python:3.11-slim` (minor fijado; `${VICTIM_IMAGE}` permite override explícito) |
| 4.6 sin `latest` | ✅ | gate `test_image_pinned_not_latest` |
| 5.3 capabilities | ✅ | `cap_drop:[ALL]` |
| 5.5 no privileged | ✅ | `privileged=false` |
| 5.9/5.10 mem+cpu | ✅ | 256M/0.5c |
| 5.11 pids | ✅ | 32 |
| 5.12 mount rw controlado | ✅ | rootfs RO + `/tmp` tmpfs 1777 |
| 5.14 restart policy | ✅ | `unless-stopped` |
| 5.15 no-new-privileges | ✅ | nnp |
| 5.19 healthcheck | ✅ | app-level (supervisor vivo) |
| 5.22 puertos host | ✅ | cero publicados |
| 5.28 rootfs read-only | ✅ | `read_only:true` |
| 5.31 docker.sock | ✅ | no lo monta (la contención la hace el api, no el victim) |

**15/15 controles aplicables ✅** — junto con taxii, el workload más endurecido del lab.

## NIST CSF 2.0

| Función | Cobertura |
|---|---|
| Identify | workload de prueba declarado; allowlist `soar.victim` documentada |
| Protect | nobody + cap_drop ALL + nnp + RO + pids + límites — blast radius mínimo si una técnica "escapa" |
| Detect | stdout etiquetado `[atomic:<tid>]` → Promtail → Loki; healthcheck real |
| Respond | containable vía API (victim label + name prefix verificados por gate) |
| Recover | stateless puro — recreate devuelve un victim limpio |

## STRIDE — superficie real

| Amenaza | Vector | Control | Residual |
|---|---|---|---|
| Tampering | técnica modifica el FS | rootfs RO + tmpfs /tmp | — |
| DoS | fork-bomb / fuga memoria | pids=32, mem=256M, cpu=0.5 | — |
| Elevation | escape del contenedor | nobody + cap_drop ALL + nnp + RO — postura máxima | — |
| Info. disclosure | técnicas leen secretos | ningún secreto montado (solo tmpfs); sin env vars | — |

## OWASP ASVS

Parcialmente aplicable: no es un servicio con API/HTTP. Como workload:
- V14 Config: secrets en env → N/A (ninguno montado) ✅
- V12 Files: uploads → N/A; RO rootfs cubre integridad del FS ✅

## SRE Golden Signals

| Señal | Cobertura |
|---|---|
| Latency | n/a — no sirve requests; la latencia relevante es la de `docker exec` de run_atomic (medida por el propio runner) |
| Traffic | `[atomic:<tid>]` lines en stdout → Loki |
| Errors | rc≠0 de técnicas lo reporta `run_atomic.py`; unhealthy si el supervisor muere |
| Saturation | mem/cpu/pids fijados |

## Puntos positivos (evidencia)

- **Blast radius mínimo**: nobody + cap_drop ALL + nnp + RO rootfs + pids — un workload que ejecuta técnicas de ataque simuladas es exactamente donde más importa el confinamiento.
- **Allowlist de contención verificada**: `soar.victim=true` + prefijo `victim_` — el gate pinea ambos (sin ellos, POST /contain → 400).
- **Ejecución real verificada**: T1003 como nobody → rc=0, artefacto creado en tmpfs.
- **Stateless puro**: recreate = victim limpio; sin estado que respaldar ni migrar.
- **Telemetría real**: las técnicas emiten tags `[atomic:<tid>]` que entran en el pipeline de detección — ejercita el path Loki→detección, no solo alertas sintéticas.

## Puntos negativos

- **Ninguno residual** — tras EVAL-001..005 todos los gaps verificados están cerrados. (El sleep-infinity como PID 1 es el diseño: el payload es "estar dormido y disponible para exec".)

## Nota por dimensión (ISO 25010)

| Dimensión | Antes | Después | Evidencia clave |
|---|---|---|---|
| Idoneidad funcional | 7.0 | **9.5** | victim presente + containable + técnicas ejecutan (T1003 rc=0) |
| Fiabilidad | 5.0 | **9.5** | restart policy + healthcheck real + stateless |
| Seguridad | 6.0 | **9.5** | nobody+cap_drop+nnp+RO+pids — blast radius mínimo |
| Observabilidad | 5.5 | **9.5** | telemetría etiquetada → Loki; healthcheck real |
| Mantenibilidad | 6.5 | **9.5** | 12 gates; compose auto-contenido y comentado |
| Portabilidad | 7.0 | **9.5** | imagen pública pineada; sin paths de host |
| **Global** | ~6.2 | **~9.5** | |
