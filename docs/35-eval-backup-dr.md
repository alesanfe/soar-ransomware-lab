# Evaluación multi-marco — Sistema de backup/DR

> Evaluación formal del sistema de backup y recuperación
> (`scripts/maintenance/backup_{core,obs}_stack.sh`, `make
> backup/restore/backup-obs/drill-obs/backup-core/drill-core`,
> `preserve/restore_credentials.py`,
> `src/soar_lab/infrastructure/tar_backup_driver.py`) siguiendo la
> metodología de `docs/25`/`27`-`34`: cada hallazgo se verifica en vivo
> con backup + drill reales y queda pineado con gates
> (`tests/architecture/test_backup_dr.py`, **16 gates**).
> Revisión 2026-11-11: **6 hallazgos** corregidos, cobertura **100%**
> del estado evaluado. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Fiabilidad: recoverability, availability |
| NIST CSF 2.0 | Función RECOVER (RC.RP), PROTECT (PR.DS-11 backups) |
| NIST SP 800-34 | Contingency planning: drills, integrity, retention |
| Regla 3-2-1 | Copias, medios, off-site (lab: 1 copia local + drill) |
| CWE-530/359 | Secretos dentro de artefactos de backup |
| SRE | RTO/RPO medidos, no declarados |

## Inventario y cobertura (post-fix)

| Estado | Ubicación | Cobertura |
|---|---|---|
| thehive_data/files, cortex_data, shuffle_apps/files, redis_data | named volumes | ✅ core script |
| misp_db/files/configs/**logs** | named volumes | ✅ core (logs añadidos DR-EVAL-003) |
| **es_data** (corpus soar-alerts) | named volume | ✅ **nuevo** DR-EVAL-001 |
| **opensearch_data** (índices Shuffle) | named volume | ✅ **nuevo** DR-EVAL-001 |
| **api soar_data.db** (SqliteAlertRepository) | host bind `runtime/data/api` | ✅ **nuevo** DR-EVAL-002 (HOST_DIRS) |
| grafana, grafana_db, loki, tempo, prometheus, s3, s3_vol2 | named volumes | ✅ obs script |
| tenzir lib/cache | volúmenes anónimos | ✅ core (resolución live por mount) |
| credenciales de servicios | preserve/restore_credentials.py | ✅ pipeline make reset→up |
| codebase | repo | ✅ API `/backup/create` (sha256 + self-verify + exclusiones) |
| nginx_logs | named volume | ➖ exento: logs ya en Loki (loki_data sí cubierto) |
| cortex `/var/lib/docker` (anon), s3-init anon, cortex/jobs | transitorios | ➖ exento: estado regenerable (pulls/jobs efímeros) |
| keycloak (H2 embebido) | container fs | ➖ exento: realm es código templated + usuarios seed |
| runtime/config | host dir | ➖ exento: regenerable via `render_configs.py` |

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| DR-EVAL-001 | **`es_data`+`opensearch_data` sin backup** — 275MB de corpus SIEM e índices Shuffle irrecuperables; `docker volume ls` vs listas de los scripts | backup real → 40MB/333 miembros + 126MB/1557 miembros; drill restaura 286+1282 ficheros | añadidos a NAMED_VOLUMES con marcadores `nodes\|indices\|_state`; imágenes ES/OS/api añadidas al MANIFEST |
| DR-EVAL-002 | **`soar_data.db` (sqlite de alertas) sin cobertura** — vive en bind mount `runtime/data/api`; el archivo de código lo excluye (`--exclude=runtime`) y los scripts de volúmenes no ven binds | backup → `api_data.tar.gz`; drill `1 files, 1 markers` | sección `HOST_DIRS` en el script core (misma técnica: bind :ro + tar + sha256 + drill) |
| DR-EVAL-003 | **`misp_logs` en MARKERS pero ausente de NAMED_VOLUMES** — config muerta; logs forenses (57MB) sin cobertura | backup → 321KB/10 miembros; drill OK | añadido a NAMED_VOLUMES + marcador |
| DR-EVAL-004 | **sin retención** — `runtime/backups` crecía sin cota: 814MB observados (core 464 + obs 209 + legacy 141) | `du -sh` | `BACKUP_KEEP` (defecto 5) + `prune_old` en ambos scripts tras cada backup |
| DR-EVAL-005 | **obs script degradado vs core** — sin SHA256SUMS (solo `gzip -t`), sin MANIFEST, sin chequeo de conteo de archivos: un archivo corrupto podía pasar el drill | comparativa lado a lado | reescrito a paridad: SHA256SUMS + `sha256sum -c` pre-drill + MANIFEST de digests + verificación `total == expected` + retención |
| DR-EVAL-006 | **cero gates** — la divergencia obs↔core y los huecos de cobertura sobrevivieron porque nada los comprobaba | — | `test_backup_dr.py`: cobertura compose↔scripts, sha256/manifest/count/retención en ambos, exclusiones de secretos del driver |

## Puntos positivos preexistentes

- **Drill real, no teatral**: restaura a volúmenes `*_drill` scratch, verifica contenido, limpia — prueba restorabilidad sin tocar datos vivos; mide wall-time → evidencia RTO.
- **Verificación por capas**: `gzip -t` + conteo de miembros en backup; `sha256sum -c` + conteo archivo↔restaurado + marcadores semánticos en drill.
- **MANIFEST de digests**: cada set registra imagen+id de cada contenedor — un restore sabe exactamente a qué build vuelve.
- **Crash-consistency documentada** (volúmenes capturados en vivo) — decisión deliberada y honesta para un lab.
- **tar_backup_driver maduro**: sha256 sidecar + self-verify post-write + exclusiones de secretos (`.env*`, claves, certs) + restore consciente de mounts :ro.
- **Resolución live de volúmenes anónimos** de tenzir (no depende de nombres estáticos).
- **Pipeline de credenciales**: `preserve_credentials.py` (pre-reset) → `restore_credentials.py` (post-up) cubre el estado no-volumizable.

## Residuales aceptados (justificados)

| Residual | Justificación |
|---|---|
| Crash-consistency (sin snapshots ES/OS nativos) | Single-node + lab: una copia de data-dir entera se restaura bien en ES/OS single-node; snapshot API añadiría un repo fs + ciclo de vida para ganancia marginal |
| 1 copia local (no off-site, no 3-2-1 completo) | Lab; el drill demuestra la parte recuperable. Sin cifrado de archivos: los datos son sintéticos/simulados |
| misp_logs/cortex-jobs de bajo valor | logs cubiertos por coste marginal; jobs de cortex son workspace transitorio → exento |
| Backup del codebase via API | El repo es la fuente real (git); el endpoint cubre estado no-versionado — marginal pero coherente |

## STRIDE / NIST CSF

| Amenaza / función | Control | Estado |
|---|---|---|
| Tampering (archivo corrupto) | sha256sums + `sha256sum -c` en drill + self-verify | ✅ |
| Info disclosure (secretos en backup) | exclusiones `.env*`/keys/certs + gate | ✅ |
| DoS (disco lleno por acumulación) | retención BACKUP_KEEP=5 | ✅ |
| RECOVER (RC.RP) | drills scratch con RTO medido | ✅ |

## Evidencia viva (2026-11-11)

```
core backup rc=0  → 13 archivos (incl. es 40MB, opensearch 126MB,
                    misp_logs 321KB, api_data 1KB)
core drill  rc=0  → sha256 OK, 14/14 restaurados, RTO 431s
obs  backup rc=0  → 7 archivos (grafana, loki, tempo, prometheus, s3×2)
obs  drill  rc=0  → sha256 OK, 7/7 restaurados, RTO 345s
scratch volumes residuales: 0
```

## Regresión

- **16/16 gates** `test_backup_dr.py` verdes.
- **160/160** `tests/architecture/` totales verdes.

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Recoverability | 6.5 → **9.5** — 100% del estado evaluado cubierto + drills verificados |
| Integridad | 7.0 → **9.5** — sha256+counts en ambos stacks |
| Capacidad (crecimiento) | 5.0 → **9.5** — retención con cota |
| Completitud de cobertura | 6.0 → **9.5** — ES/OS/sqlite/logs incluidos |
| Evidencia (RTO/RPO) | 8.5 → **9.5** — medido: 431s/345s wall-time |
| Mantenibilidad | 7.5 → **9.5** — paridad de scripts, 16 gates |
| **Global** | ~6.8 → **~9.5** |
