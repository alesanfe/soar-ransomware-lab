# 48 — Evaluación: TAXII (ISO 27001 A.5/A.8, NIST CTI, STIX/TAXII)

> **Área**: dos superficies TAXII — `soar_taxii` (medallion TAXII 2.1 en ti_net) y TAXII-lite (FastAPI sobre el export STIX 2.1, `/api/v1/taxii2/`, alcance ADR-0011).
> **Marcos**: ISO 27001:2022 **A.5.7** (información de amenazas), A.5.17 (autenticación), A.8.20-24 (red/criptografía); **NIST SP 800-150**; **STIX 2.1 / TAXII 2.1** como estándares de intercambio.
> **Resultado**: **~9,4/10**. 14 gates nuevos, 0 defectos activos nuevos — residuales documentados y justificados.

## 1. Matriz de cumplimiento por dimensión

### Integridad de feeds — ISO A.5.7 / NIST CTI §3

- **TAXII-lite**: bundle generado on-demand desde `alert_repository` vivo — la feed refleja el corpus real al momento de la consulta; IDs `uuid5` deterministas → re-exportar el mismo corpus produce bundle diff-estable (verificable/diffable entre consumidores).
- **Medallion**: memory backend sembrado desde `data.json` commiteado — fixture estático del lab.
- `more` flag **honesto**: solo true cuando el probe `limit+1` devuelve más objetos — nunca una paginación fingida.

### Autenticación — ISO A.5.17

| Superficie | Mecanismo | Verificado |
|------------|-----------|------------|
| Medallion | HTTP Basic `taxii_reader`/`taxii_writer`, creds env-inyectadas | `401` sin auth · `406` con Accept inválido (content-negotiation TAXII 2.1 correcta) · `200` discovery con creds + `Accept: application/taxii+json;version=2.1` |
| TAXII-lite | `require_api_auth` (Service-Token, scope `internal`) en las 5 rutas | `401` sin token · discovery/collections/objects `200` con token |

### PKI — ISO A.8.24

- **TAXII-lite**: hereda el plano TLS del nginx/API (`/api/v1/` passthrough).
- **Medallion**: **TLS-only** — el runner propio de medallion es HTTP-only, así que la app Flask se sirve con **gunicorn + cert firmado por la CA del lab** (`tls_app.py`, certs montados RO). Verificado live: `https://taxii:5000/taxii2/` → 406 sin `Accept` TAXII, 200 + media type con él (desde `soar_api` verificando la CA). Sigue en `ti_net` (`internal:true`, sin puertos publicados).

### Compartición de IoCs — NIST SP 800-150

Outbound-only en ambas superficies (el lab **produce** CTI):
- Medallion: feed TAXII 2.1 completo (discovery/api_roots/collections/objects) consumible por MISP TAXII-pull o clientes estándar.
- Lite: colección `lab-alerts` read-only (`can_write:false`) exponiendo indicators+groupings del corpus — **verificado live**: objects envelope `200` con media type `application/taxii+json;version=2.1`, `more:true` cuando limita.
- Colección con `id` `uuid5` estable → los consumidores pueden referenciarla persistentemente.

### Calidad de datos — STIX 2.1 / NIST CTI §4

- `spec_version: "2.1"`, `pattern_type: "stix"`, patrones sintácticamente válidos verificados live: `[file:hashes.'SHA-256' = '...']`, `[ipv4-addr:value = '...']`, `[domain-name:value = '...']`.
- Provenance completa: `identity` (class `system`) como `created_by_ref`, `grouping` por alerta con `object_refs`, `valid_from`/`created`/`modified`.
- Dedup por `seen_ids` (uuid5 de `alert_id:pattern`); extracción busca campos IoC en raíz y `data` anidado.
- **TLP:CLEAR** `marking-definition` (id canónico de spec) emitida en cada bundle; indicators y groupings llevan `object_marking_refs` + `confidence: 80` — verificado live en objects.

### Control de acceso — ISO A.8.20

- Medallion = **el contenedor más endurecido del stack**: `cap_drop:[ALL]`, `read_only` rootfs + tmpfs `/tmp` 8m, `no-new-privileges`, usuario `taxii` non-root, `pids:64`, credenciales por env con plantilla placeholder (nunca literals commiteadas — gate).
- ti_net = plano threat-intel dedicado; servicios no-TI no alcanzan el feed.
- Writer account existe (`taxii_writer`) pero el lab solo usa reader — principio de menor privilegio disponible si se expone escritura.

### Actualización de taxonomías — ISO A.5.7

- STIX usa open-vocab strings (sin taxonomía versionada que refrescar).
- `data.json` seed del medallion: estático por diseño (fixture); refresh = rebuild/reseed manual — residual aceptado.
- TAXII-lite no tiene taxonomía: deriva en vivo del corpus de alertas.

## 2. Fixes aplicados en esta ronda (residuales cerrados)

| ID | Residual | Fix | Evidencia |
|----|----------|-----|-----------|
| TAXII-EVAL-005 | Medallion HTTP plano | gunicorn + cert CA-lab (`tls_app.py`); TLS-only | `https://taxii:5000` → 406/200 live verificados |
| TAXII-EVAL-006 | Sin manifest (recurso requerido por spec en colecciones read) | `GET .../manifest/` con entradas `{id, date_added, version, media_type}` | live: 200, `application/taxii+json;version=2.1`, 17 entries |
| TAXII-EVAL-007 | Sin TLP/`confidence` | `marking-definition` TLP:CLEAR + `object_marking_refs` + `confidence:80` | live: marking-def presente, indicator marcado |

### Residuales que permanecen (decisiones de spec/diseño, no deuda)

| Restricción | Naturaleza |
|-------------|------------|
| Sin `status` ni write path | La spec TAXII 2.1 solo los exige en colecciones **writable** — `can_write:false` los hace no aplicables |
| Sin version history de objetos | Los objetos son deterministas (uuid5) y no mutan — una sola versión válida por id |
| Seed `data.json` estático | Fixture deliberado; refresh = rebuild/reseed |
| Paginación `limit` simple | Bounded export + flag `more` honesto (probe +1), suficiente para el tamaño del corpus |

## 3. Regresión

- `tests/architecture/test_taxii_stack.py`: **14/14** (hardening medallion, auth en las 5 rutas, semántica TAXII honesta, calidad STIX).
