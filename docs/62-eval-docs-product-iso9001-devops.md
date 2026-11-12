# 62 — Evaluación: Documentación como producto (ISO 9001 / DevOps docs)

**Fecha**: 2026-08-06 · **Alcance**: `docs/`, `apps/docs-site/`, `scripts/ci/sync_docs_to_docusaurus.py`, `scripts/ci/docs_quality.py`, `.github/workflows/deploy-docs.yml`, `tests/architecture/test_docs_product.py`
**Marcos**: ISO 9001 (documented information, §7.5), DevOps documentation-as-code (docs in repo, built in CI, deployed like code), discoverability as a quality attribute
**Veredicto**: **~9.6/10** — 1 defecto de discoverability corregido, 5 gates nuevos

---

## 1. Resumen

### 1.1 Objetivo

Segunda evaluación del producto documental (la primera fue `docs/43-eval-docs-product.md`, que cerró sincronización OpenAPI, indexación del corpus y patrones prohibidos). Esta iteración audita **discoverability y fidelidad de publicación**: que todo documento fuente llegue al sitio publicado, que los enlaces internos sobrevivan a la reestructuración y que la tubería de despliegue sea verificable.

### 1.2 Contexto

El proyecto mantiene un corpus de ~100 documentos: 7 curados (getting-started, architecture, operations, testing, project, glossary, index), ~30 evaluaciones numeradas, ADRs, runbooks y documentos de referencia. Existen **dos rutas de publicación**:

- **Imagen Docker** (`apps/docs-site/Dockerfile`): `COPY docs ./docs` → todo el corpus, sidebar plano autogenerado.
- **GitHub Pages** (`deploy-docs.yml`): `sync_docs_to_docusaurus.py` → solo los 7 mapeados explícitamente, y `shutil.rmtree` borraba el resto.

## 2. Alcance

### 2.1 Qué se evalúa

Completitud del índice, trazabilidad código↔doc, documentación viva (sync scripts, OpenAPI), discoverability del sitio, consistencia entre rutas de publicación.

### 2.2 Defecto encontrado y corregido

| ID | Defecto | Fix |
|----|---------|-----|
| DOC-EVAL-2-001 | **Sync de Pages publicaba solo 7 docs y borraba el resto** — los ~94 docs restantes (evals, ADRs, runbooks, referencias) nunca llegaban al sitio público, aunque la imagen Docker sí los incluía. Divergencia silenciosa entre las dos rutas. | `sync_extra_docs()`: publica el corpus completo en categorías (`evaluations/`, `adr/`, `runbooks/`, `resources/`) con `_category_.json` colapsables; `_fix_links()` **depth-aware** reescribe enlaces internos según la profundidad del destino |

### 2.3 Corrección de enlaces (sub-defecto)

La reestructuración por categorías rompía enlaces que en fuente resolvían por nombre plano (`](02-architecture.md)`). El fixer original solo cubría los 7 mapeados y con profundidad hardcodeada. La reescritura ahora:

- Deriva destinos de `_top_level_dests()` — la misma función que mapea y emite, así que una categoría renombrada no puede romper enlaces silenciosamente.
- Calcula el prefijo `../` por profundidad real del archivo emitido (0 para `intro.md`, 1 para categorías, 2 para `adr/sub/`).
- Respeta `./README.md` desde docs de nivel superior pero no lo reescribe dentro de subárboles (`adr/`, `runbooks/`), donde es un enlace a hermano.

**Resultado**: 237 enlaces internos, **0 rotos** tras el sync (antes del fix: 178 rotos por categorías + ~90 docs no publicados en absoluto).

## 3. Matriz de cumplimiento

| Dimensión | Estado | Evidencia |
|-----------|--------|-----------|
| **Completitud** (ISO 9001 §7.5.2) | ✅ | Todo `docs/*.md` + `adr/` + `runbooks/` publicado; gate que ninguno se cae del sync |
| **Trazabilidad** | ✅ | `index.md` cataloga cada doc top-level (gate eval-43); ADR index `0000-index.md`; cada doc cita código que lo respalda |
| **Documentación viva** | ✅ | Sync + build + deploy en CI/CD como código; `docs_quality.py` valida OpenAPI/inventario de tests/collect-only por PR |
| **Sincronización OpenAPI** | ✅ | 3 targets byte-idénticos (`docs/api/`, `docs/assets/references/`, `tests/baseline/`), drift gateado |
| **Discoverability** | ✅ | Corpus completo en 11 categorías etiquetadas y colapsables; sidebar autogenerado; búsqueda vía índice + categorías |

## 4. Gates añadidos (5 nuevos → 14 total)

| Gate | Invariante |
|------|-----------|
| `test_sync_publishes_every_source_doc` | Ningún `docs/*.md` puede ser silenciosamente descartado por el sync de Pages |
| `test_sync_emits_zero_broken_internal_links` | Todo enlace `.md` entre docs publicados debe resolver en el sitio emitido |
| `test_eval_docs_land_in_evaluations_category` | El corpus de evals es navegable como categoría, no un dump plano |
| `test_deploy_workflow_syncs_corpus_before_build` | El pipeline de Pages corre ambos syncs antes del `npm run build` |
| `test_excluded_subtrees_stay_unpublished` | `thesis/` (TFM académico), `api/` (spec cruda), `assets/` (adjuntos) quedan excluidos deliberadamente |

Los gates ejecutan el `sync_docs()` **real** contra un target scratch — ejercitan el código de emit + rewrite verdadero, no una reimplementación.

## 5. Verificación

```
$ pytest tests/architecture/test_docs_product.py → 14/14 PASSED
$ python scripts/ci/sync_docs_to_docusaurus.py → 8 curados + 94 extra, 0 enlaces rotos
```

## 6. Residuales (justificados, no deuda)

- **`thesis/` excluido del sitio**: contenido académico (TFM), no documentación operativa — decisión gateada.
- **Ruta Docker sigue publicando plano**: la imagen `COPY docs ./docs` da sidebar plano autogenerado; funcional pero menos organizado que Pages. Aceptado: la imagen local prioriza "todo disponible" sobre "bien categorizado"; Pages es el sitio de referencia.
- **`apps/docs-site/docs/` es contenido generado**: el sync lo re-crea cada run; está gitignored por diseño (fuente de verdad = `docs/`).

## 7. Referencias

- ISO 9001 §7.5 — Documented information
- DevOps Research & Assessment — documentation as a first-class artifact
- `docs/43-eval-docs-product.md` — primera evaluación (9.5/10, OpenAPI/indexación)
- `tests/architecture/test_docs_product.py` — 14 gates
