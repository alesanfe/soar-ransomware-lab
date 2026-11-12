# 43 — Evaluación: documentación como producto

> **Área**: `docs/` (52 md), `apps/docs-site/` (Docusaurus), `docs_quality.py`, `export_openapi.py`, Vale/lychee/markdownlint, `make docs-*`.
> **Marcos**: ISO 25010 (usabilidad, mantenibilidad), docs-as-code (Diátaxis-light), SRE (documentación fresca = contrato operativo).
> **Resultado**: ~9,5/10 (antes ~8,5/10). 3 defectos corregidos, 9 gates nuevos, índice al 100%.

## 1. Resumen

La documentación es extensa (52 docs top-level + ADRs + api/assets) con un gate bloqueante real (`docs_quality.py`: OpenAPI diff, inventario de tests, collect-only, patrones prohibidos, validación Mermaid) y un sitio Docusaurus servido por nginx endurecido. La deuda encontrada: spec OpenAPI publicada **45KB desactualizada** respecto a la app viva, 14 docs huérfanos del índice canónico (5 sin ningún enlace entrante) y una referencia prohibida latente en un doc de backlog.

## 2. Hallazgos corregidos

| ID | Severidad | Defecto | Corrección |
|----|-----------|---------|------------|
| DOC-EVAL-001 | High | **`docs/api/openapi.json` stale** — el gate `docs_quality` fallaba (`docs` ≠ `baseline`): faltaba `/soar/cortex/jobs/summary` y ~45KB de schemas | Regenerado desde `create_app().openapi()` → 67 paths byte-idénticos en los 3 targets (`docs/api`, `docs/assets/references`, `tests/baseline`); gate `test_openapi_snapshots_byte_identical` añadido |
| DOC-EVAL-002 | Medium | **14 docs huérfanos del índice** — `18-eval-tc-iso`…`26-e2e-ops-runbook`, `references`, `rbac-matrix`, `risk-register`, `SCRIPTS-MANIFEST`, `README` no catalogados; 5 sin enlace entrante | Todos indexados con descripción; gate `test_index_catalogs_every_top_level_doc` hace cumplir el invariante |
| DOC-EVAL-003 | Low | **Referencia `localhost`:8080 prohibida en `17-technical-backlog`** — narrativa de bug histórico que disparaba el banned-pattern check | Reformulada sin el literal prohibido |

## 3. Verificación

- Checks sustantivos de `docs_quality.py` replicados en contenedor: openapi sync ✓, inventory JSON válido ✓, **0 referencias prohibidas** ✓.
- Enlaces internos: escaneo propio → **0 rotos** en docs/.
- `soar_docs_site` sirviendo (200s, healthcheck 30s, nginx conf válida).
- Sidebars autogeneradas — cero mantenimiento manual de navegación.
- `pytest --collect-only` dentro del gate es lento (~4min por imports de la app) — verificado que el fallo previo era ambiental del host (sin PyJWT), no del repo.

## 4. Positivos confirmados

- `docs_quality.py` es gate **bloqueante** (sin `-@`): OpenAPI diff, banned patterns (tokens, URLs legacy, puertos viejos), Mermaid directive check, inventario JSON, collect smoke.
- `export_openapi.py` documenta los 3 targets y los mantiene byte-idénticos.
- Vale en CI sobre `docs/` (advisory apropiado para prosa); markdownlint + lychee configurados.
- ADR indexado (`docs/adr/0000-index.md`); `editUrl` del site apunta al repo.

## 5. Residuales aceptados

- `markdownlint`/`lychee`/Sphinx en `docs-lint` son **no-bloqueantes** (`-@`) — decisión razonable: el gate duro (consistencia + patrones + OpenAPI) sí bloquea; linters de formato son advisory. Mejora posible: lychee config para chequeo de anchors.
- Vale `fail_on_error: false` — prose lint advisory por diseño.
- `onBrokenLinks: 'warn'` en Docusaurus — el escaneo propio confirma 0 rotos actualmente; endurecer a `throw` cuando exista CI de docs dedicado.
- `docs-build` (Sphinx HTML) corre bajo demanda, no en CI — los artefactos son efímeros en `reports/`.

## 6. Gates

`tests/architecture/test_docs_product.py` (9): índice completo, snapshots OpenAPI idénticos, checks del quality gate intactos, exporter con 3 targets, workflow Vale, targets make en ambos OS, banned-pattern en eval docs, ADR index, dirs api/assets.
