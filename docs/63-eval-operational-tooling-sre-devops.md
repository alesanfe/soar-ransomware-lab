# 63 — Evaluación: tooling operacional (SRE / DevOps Capability Model)

**Fecha**: 2026-08-06 · **Alcance**: Makefiles, `scripts/` (build_local_env, verify_image_digests, doctor), Dockerfiles, `requirements.lock`, compose image refs
**Marcos**: SRE (toil reduction, automation), DevOps Capability Model (deployment automation, env parity, reproducible builds, trunk-based CI), 12-factor dev/prod parity
**Veredicto**: **~9.6/10** — 0 defectos activos; 5 gates nuevos sellan invariantes de reproducibilidad que antes eran solo convención

---

## 1. Resumen

Segunda evaluación del tooling (la primera fue `docs/44-eval-operational-tooling.md`, que cerró `.PHONY`, paridad de targets y manifiesto). Esta iteración audita **reproducibilidad de builds, paridad de entornos y caminos de enforcement** — los ejes SRE/DevOps que la eval anterior no cubría.

**Hallazgo principal**: las invariantes de reproducibilidad ya se cumplían en la práctica (lock usado, tags pineados, `.env.container` generado), pero **nada las hacía cumplir** — una dep runtime añadida a `pyproject.toml` sin regenerar el lock hubiera instalado *floating* silenciosamente. Los 5 gates nuevos convierten convención en contrato.

## 2. Verificación de la matriz pedida

| Dimensión | Estado | Evidencia |
|-----------|--------|-----------|
| **Mantenibilidad** | ✅ | 350 targets con paridad win↔linux gateada · 0 refs muertas · `.PHONY` 100% · manifiesto AST auto-generado con freshness en CI |
| **Automatización (toil SRE)** | ✅ | `make up` ejecuta 19 pasos automatizados (env gen, digests, redes, volúmenes) · runbooks usan `docker exec` solo para *diagnóstico* (no toil repetitivo) · guard/watcher self-healing |
| **Paridad entornos** | ✅ | `.env.container` **regenerado en cada `make up`** por `build_local_env.py` (derivado, nunca mantenido a mano) · perfiles `up` hardened / `up-lab` explícitos |
| **Reproducibilidad** | ✅ | **Runtime deps 100% pineados** en `requirements.lock` (verificado: 14/14 runtime, solo flotan extras dev/test/quality) · api Dockerfile instala con `-c requirements.lock` · docs-site `npm ci` · taxii/watcher pins exactos · todas las imágenes `${VAR:-name:version}` — sin `:latest`, sin bare names |
| **DX operativa** | ✅ | `make help` curado por secciones · `doctor.py` diagnósticos accionables · `preflight` gatea el arranque · mensajes con siguiente paso (`run 'make verify-digests' to enforce`) |

## 3. Datos de la verificación

- **Lock parity**: `project.dependencies` → 14 runtime deps, **todos** en `requirements.lock`. Flotan solo extras (`pytest`, `ruff`, `hypothesis`, `matplotlib`…): herramientas de build/test, no superficie runtime.
- **Image refs**: ~30 `image:` en compose — cada default resuelve a `name:version` explícito o `${COMPOSE_PROJECT_NAME}-*` local-build (fuente = pin). Cero flotantes.
- **Env parity**: `build_local_env.py` invocado como paso 3/19 en la secuencia `up` de **ambos** Makefiles.
- **Enforcement opt-in**: verificación de digests warn-only en `up` con `make verify-digests` blocking disponible — diseño deliberado (lab), documentado en el propio mensaje.

## 4. Gates añadidos (5 nuevos → 13 total)

| Gate | Invariante |
|------|-----------|
| `test_runtime_deps_all_pinned_in_lock` | Toda dep en `project.dependencies` aparece `==` en el lock — una dep añadida sin regenerar el lock rompe CI |
| `test_api_dockerfile_constrains_installs_with_lock` | La imagen de producción instala bajo `-c requirements.lock` y lo embarca |
| `test_compose_image_defaults_pinned` | Cero defaults sin tag en `image:` — ni `:latest` ni bare names |
| `test_env_container_regenerated_in_up_sequence` | `.env.container` se genera en cada `up` — paridad derivada, no manual |
| `test_verify_digests_enforcement_path_exists` | El camino blocking `verify-digests` persiste en ambos Makefiles |

## 5. Residuales (justificados, no deuda)

- **Extras dev/test/quality flotan en el build de imagen** (instalan sin pin bajo `-c`): herramientas de test embebidas para ejecución in-container, no superficie runtime. Mitigado por: runtime 100% pineado + pip-audit sobre el lock. Subir el lock a full-closure requeriría regenerarlo con `pip-compile` — mejora posible, no defecto.
- **Digest verify warn-default en `up`**: enforcement opt-in documentado (lab donde la imagen tarda en publicar digests); CI tiene SLSA/provenance (eval 51).
- **`docker exec` en runbooks**: pasos de *diagnóstico*, no automatización de toil — el formato runbook exige comandos literales ejecutables.

## 6. Verificación

```
$ pytest tests/architecture/test_operational_tooling.py → 13/13 PASSED
$ runtime↔lock: 14/14 pinned | images: 30/30 tagged-default | env gen: 2/2 makefiles
```

## 7. Referencias

- Google SRE Book, cap. 5 — Eliminating Toil
- DORA / DevOps Capability Model — deployment automation, loosely-coupled architectures, version control of everything
- 12-Factor App, §X — Dev/prod parity
- `docs/44-eval-operational-tooling.md` — primera evaluación (paridad/PHONY/manifiesto)
- `tests/architecture/test_operational_tooling.py` — 13 gates
