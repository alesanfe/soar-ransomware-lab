# 47 — Evaluación: MISP (ISO 27001 A.5/A.8, NIST CTI, STIX/TAXII)

> **Área**: stack MISP (`misp`, `misp-db`, `misp-modules`), integración workflow (enriquecimiento + publicación de IoCs), corpus de threat intelligence.
> **Marcos**: ISO 27001:2022 **A.5.7** (información de amenazas — el control exacto de esta área), A.5.17 (autenticación), A.8.24 (criptografía), A.8.20-21 (seguridad de red); **NIST SP 800-150** (Guide to Cyber Threat Information Sharing); **STIX 2.x / TAXII 2.x** como estándares de intercambio.
> **Resultado**: **~9,4/10**. 11 gates nuevos, 0 defectos activos nuevos — residuales documentados y justificados.

## 1. Matriz de cumplimiento por dimensión

### Integridad de feeds — ISO A.5.7 / NIST CTI §3

- **2 feeds declarados, 0 habilitados** (verificado live en `/feeds/index`) — postura correcta para un lab: no se consume CTI externo no verificado. Al habilitar, la integridad queda delegada al productor del feed (TLS + manifiesto firmado del feed MISP estándar).
- El corpus local (1150 eventos) solo se escribe vía API autenticada — integridad garantizada por auth + TLS.

### Autenticación — ISO A.5.17 / A.9.4

- `Authorization:` API key en todo acceso REST — verificado: sin key → 401 (`"Authentication failed..."`), con `MISP_API_KEY` → `searchall` responde.
- Key inyectada como `ADMIN_KEY: ${MISP_API_KEY}` desde `.env` (gitignored); el export GitOps del workflow scrubbea la key a placeholder (gate TST-EVAL-001 ya existente).
- **MISP-EVAL-013 (cerrado)**: usuario dedicado `soar-automation@soar.local` con rol **Publisher** (role_id 4) — la integración consume `MISP_AUTOMATION_API_KEY` (least privilege); la admin key queda solo para bootstrap/ops del contenedor. Verificado live: search/create/delete 200 con la key Publisher.

### PKI — ISO A.8.24 / CIS 3.10

- Cert servidor **firmado por la CA del lab** (`misp-full.pem` + chain montados sobre el self-signed de la imagen — MISP-001 ya cerrado).
- `debian-ca-plus-lab.crt` montado como `/etc/ssl/certs/ca-certificates.crt` → PHP, phpredis y curl verifican la CA interna (sin ella, clientes internos fallarían TLS).
- `BASE_URL: https://` + puerto publicado a `443` (TLS listener, no el redirect :80).
- Verificado live: heartbeat 200 con `--cacert`; quirk Schannel de Windows documentado.

### Compartición de IoCs — NIST SP 800-150 (producer/consumer)

Bidireccional, verificado:

| Dirección | Nodo workflow | Evidencia |
|-----------|---------------|-----------|
| **In** (enriquecimiento) | `misp_search` → `POST /attributes/restSearch` por hash de alerta (md5/sha1/sha256) | nodo en `workflow_actions.py` + `verify_misp.py` tolerante a truncamiento (non-critical) |
| **Out** (publicación) | `misp_create` → `POST /events` por alerta con `sha256`+`ip-dst` y **`to_ids: true`** (semántica IDS correcta) | **2 eventos "SOAR alert" verificados en live** (`events/index/searchall:SOAR alert`) |
| Canal alternativo | TAXII 2.x server propio (`routes_taxii.py`, STIX export) | discovery 401-con-auth — estándar interoperable |

### Calidad de datos — ISO A.8.10 / NIST CTI §4 (calidad del indicador)

- Tipos de atributo correctos (`sha256`, `ip-dst` — no `text` genérico); `to_ids` distingue indicadores accionables de contexto.
- `threat_level_id`, `analysis`, `distribution` seteados explícitamente en cada evento creado.
- Seed de IoCs vía `setup_analyzers_and_iocs.py` desde `ioc_samples.json`; dedup natural por `restSearch` de valor.
- `verify_misp.py`: verificación no-crítica con fallback a conteo aproximado cuando Shuffle trunca el payload — degradación honesta (WARN, no falso verde).

### Control de acceso — ISO A.8.20 (segmentación)

- **`misp_internal`** red dedicada: `misp-db` + `misp-modules` fuera de `soar_net`, cero puertos publicados — solo la app MISP y el plano de monitoreo los alcanzan.
- Redis sesiones MISP vía `tls://redis` (default scheme TLS — un host plano caía a plaintext y rompía sesiones silenciosamente).
- `cap_add: AUDIT_WRITE` (mínimo requerido por el entrypoint MISP), límites CPU/mem, log rotation.

### Actualización de taxonomías — ISO A.5.7 / NIST CTI

- Taxonomías baked en la imagen `misp-core:v2.5.44` (`/taxonomies/index.json` → 200, set default presente).
- **MISP-EVAL-014 (cerrado)**: `make misp-update-taxonomies` ejecuta `scripts/maintenance/misp_update_taxonomies.py` → `POST /taxonomies|/galaxies|/warninglists/update` con la admin key inyectada desde `.env` del host. Verificado live: galaxies updated, taxonomies/warninglists already current.

## 2. Residuales documentados

### Fixes aplicados en esta ronda (residuales cerrados)

| ID | Residual | Fix | Evidencia |
|----|----------|-----|-----------|
| MISP-EVAL-011 | Passwords db en `docker inspect` | MariaDB `_FILE` + secrets env-sourced (patrón redis) | `inspect` solo muestra `*_FILE`; healthy con healthcheck que lee el secret |
| MISP-EVAL-012 | Healthcheck misp-modules a nivel socket | Probe funcional `POST /query` módulo dns | `soar_misp_modules (healthy)` ejecutando un módulo real |
| MISP-EVAL-013 | Sin RBAC — admin key para todo | Usuario Publisher dedicado + `MISP_AUTOMATION_API_KEY`; compose prefiere la key acotada | `users/view/me` → role Publisher; search/create/delete 200 |
| MISP-EVAL-014 | Sin refresh de taxonomías | `make misp-update-taxonomies` (admin desde `.env`) | taxonomies/galaxies/warninglists → HTTP 200 |

### Residuales que permanecen (restricciones externas, no deuda)

| Restricción | Naturaleza |
|-------------|------------|
| `MYSQL_PASSWORD` env en el servicio `misp` (app) | La imagen MISP no soporta `_FILE` — limitación upstream |
| Feeds deshabilitados | Postura deliberada: el lab no consume CTI externo |
| Taxonomías no auto-refrescadas en CI | El refresh es una operación manual/ops por diseño (pinned lab) — el camino existe ahora vía target |

## 3. Regresión

- `tests/architecture/test_misp_stack.py`: **11/11** (PKI, segmentación, crypto keys, sharing bidireccional, TLS).
- Un falso positivo del gate corregido en desarrollo (comentario "soar_net" en YAML disparaba el check de segmentación — ahora matchea list-entries reales `- soar_net`).
