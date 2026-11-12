# Evaluación multi-marco — Capa de datos (SQLite + ES/OpenSearch)

> Evaluación formal de la capa de persistencia del lab: el repositorio
> SQLite (`soar_data.db`), el corpus Elasticsearch (`soar-alerts`,
> `soar-metrics-v2`) y el backend OpenSearch de Shuffle. Metodología de
> `docs/32`-`39`: hallazgos verificados en vivo y pineados con gates
> (`tests/architecture/test_data_layer.py`, **13 gates** +
> `tests/unit/infrastructure/test_elasticsearch_alert_repository.py`,
> **9 unit tests**). Revisión 2026-11-11: **3 defectos** corregidos.
> Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Integridad/durabilidad/consistencia de datos |
| SRE data practices | Schema control, retención acotada, single source of truth |
| CWE-662 / CWE-772 | Acceso concurrente, recursos sin cota |
| OWASP | Persistencia parametrizada (inyección SQL) |
| 3-2-1 / NIST CSF RC | Cobertura de backup del estado persistente |

## Evidencia de runtime (post-fix)

```
soar-alerts      mapping: 27 campos con subfield keyword (antes 0)
                 settings: index.lifecycle.name = soar-retention
                 agg:     status.keyword -> {processed: 968} (antes fallaba)
soar-metrics-v2  ilm attach OK, 9 campos keyword sub-field
ilm              soar-retention: hot -> delete @90d (los built-ins no aplicaban)
template         soar_lab_indices: soar-alerts* + soar-metrics-*
                 src_ip/all_ips=ip, categoricals=keyword, fechas=date
api              /analytics/attack-coverage -> 100 alerts, 58 c/tecnicas,
                 17 tecnicas unicas (antes: 0 — sqlite vacio)
opensearch       ISM shuffle-rollover: workflowexecution-* rollover
                 40gb/1M docs/90d (correcto desde antes)
sqlite           WAL + busy_timeout=5000 + foreign_keys=ON, 0 filas
                 (write-path historico sin invocadores — residual)
```

## Hallazgos corregidos

| ID | Defecto | Fix verificado |
|----|---------|----------------|
| **DATA-EVAL-001** | **`soar-alerts`/`soar-metrics-v2` sin control de esquema** — creados por dynamic mapping: 33 campos, todo string como `text` plano sin `keyword` (sin agregaciones, sin `term` exacto, sin ordenación); `src_ip`/`all_ips` como `text` (sin queries CIDR); `severity`→`long` por accidente del primer doc — un doc futuro con `severity:"high"` habría sido rechazado por conflicto de mapping | Template `soar_lab_indices` en `configure_es.py` (persiste en `make reset`): categoricals→`keyword`, `src_ip`/`all_ips`→`ip`, fechas→`date`, strings→`text`+subfield `keyword`; `PUT _mapping` añade subfields `keyword` a los índices vivos (update legal, sin reindex) — verificado: `status.keyword` agg devuelve `processed: 968` |
| **DATA-EVAL-002** | **Corpus ES sin retención** — `soar-alerts`/`soar-metrics-v2` crecían sin cota (ninguna de las 7 políticas ILM built-in aplicaba); OpenSearch sí tenía ISM (`shuffle-rollover`) | `PUT _ilm/policy/soar-retention` (hot→delete@90d) + attach vía template para índices futuros y `_settings` para los existentes — verificado `index.lifecycle.name` activo en ambos |
| **DATA-EVAL-003** | **Divergencia de persistencia (funcional)** — `SqliteAlertRepository` cableado en composition y leído por `/analytics/*` + TAXII, pero `store_alert` tenía **cero invocadores**: sqlite siempre vacío → `attack-coverage` devolvía 0 alertas aunque ES tenía 973 | `ElasticsearchAlertRepository` (subclase del sqlite): `get_alert`/`get_alerts`/`count_alerts` leen `soar-alerts` con auth+CA lab, el resto (cases/backups/coverage/stores) hereda de sqlite; fallback a sqlite en error de transporte; shape `{..., data: doc}` preserva el contrato — verificado: coverage devuelve 100 alertas / 17 técnicas |

## Positivos confirmados

- **SQLite**: WAL + `busy_timeout=5000` + `foreign_keys=ON` por conexión,
  SQL 100% parametrizado (sin f-strings en `execute`), UPSERT
  `ON CONFLICT`, lock de proceso, `db_path` explícito obligatorio.
- **OpenSearch**: ISM `shuffle-rollover` cubre `workflowexecution-*` y el
  resto de patrones de Shuffle (rollover 40gb/1M/90d); template propio
  `soar_workflowexecution_kw` (priority 250) corrige el mapping de Shuffle.
- **ES plantillas previas**: `soar_no_replicas`, `soar_environments`,
  `soar_workflowqueue` funcionando; `single_node` ajustado a replicas=0.
- **Backup**: `es_data` + `opensearch_data` en el script core
  (`es_data.tar.gz`/`opensearch_data.tar.gz`, DR-EVAL-001) y
  `runtime/data/api` (sqlite) en `api_data.tar.gz` (DR-EVAL-002) — toda la
  capa de datos cubierta por DR.
- **Cert-expiry**: 12/12 endpoints TLS con `probe_ssl_earliest_cert_expiry`
  (incl. `elasticsearch:9200`, `opensearch:9200`, `tenzir-node:5160` — los
  dos últimos añadidos en esta revisión).

## Residuales aceptados (justificados)

| Residual | Justificación |
|----------|---------------|
| `src_ip` queda `text` en el índice vivo | Cambio de tipo exige reindex; el subfield `keyword` ya da exact-match/agg; el template aplica `ip` real en el próximo índice (p.ej. tras `make reset`) |
| SQLite `alerts`/`cases`/`backups`/`test_coverage` sin DELETE/retention | Write-path sin invocadores vivos (0 filas en producción); las lecturas ES tienen retención ILM |
| `get_cases` sigue en sqlite | Los casos viven en TheHive (API aparte); `cases_provider` es opcional en los use cases |
| Crash-consistency ES/OS | Documentada en DR-EVAL (single-node, backup en caliente de volumen) |

## Regresión

- **13/13** gates `test_data_layer.py`
- **9/9** unit `test_elasticsearch_alert_repository.py` (fallback, shape, term queries, severidad no numérica, delegación cases)
- **229/229** suite `tests/architecture/`

## Áreas evaluadas (tablero)

core · MISP · TAXII · SSO · victim · supply-chain · API · observabilidad ·
frontend · backup/DR · dominio · admission · PKI · perímetro · **datos**

Pendientes: suite de tests como activo, simulador, documentación como
producto, tooling operacional.
