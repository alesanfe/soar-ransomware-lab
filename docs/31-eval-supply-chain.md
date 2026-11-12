# Evaluación multi-marco — Cadena de suministro / CI-CD

> Evaluación formal de la cadena de suministro del proyecto
> (`.github/workflows/*`, `.github/dependabot.yml`, `requirements.lock`,
> Dockerfiles, pipeline de release) siguiendo la metodología de
> `docs/25`/`27`-`30`: cada hallazgo se verifica con evidencia y queda
> pineado con gates (`tests/architecture/test_supply_chain.py`,
> **13 gates**). Revisión 2026-11-11: **6 hallazgos** corregidos,
> residuales documentados. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad por característica del pipeline |
| ISO/IEC 25040 | Proceso: evidencia → defecto → veredicto → gate de regresión |
| SLSA (build track) | Provenance, aislamiento del build, reproducibilidad |
| NIST SSDF (SP 800-218) | PO.3/PO.5/PS.1/PS.2/PS.3/PW.4/RV.1 |
| OWASP SCVS | Controles de cadena de suministro software |
| OpenSSF Scorecard | Postura publicada semanalmente (workflow propio) |

## Evidencia recolectada

```
workflows       8 (ci, quality, dast, release, e2e-smoke, deploy-docs,
                 scorecard, vale) — todos YAML-válidos
uses: refs      100% commit-SHA pinned (era ~70% — 17 refs mutables)
permissions     8/8 workflows con bloque explícito least-privilege
secrets         solo GITHUB_TOKEN; sin pull_request_target; sin
                interpolación de github.event en run:
dependabot      pip + npm + github-actions + docker×9 dirs (era 3)
release.yml     SLSA provenance mode=max + sbom:true (buildx) +
                CycloneDX python SBOM + cosign keyless sign +
                self-verify gates de firma y atestación
ci.yml          pip-audit --strict, check_dep_freshness (≥7d, SC5),
                gitleaks + trufflehog + scan_secrets, trivy→SARIF,
                SBOM CycloneDX, mutation gate 80%, compose validation
requirements.lock  43 paquetes (closure completo de runtime deps;
                era 38 parcial — faltaban PyJWT/PyYAML/OTEL/uvloop)
Dockerfile api  runtime deps resueltos con -c requirements.lock
```

## Bugs encontrados — verificados y corregidos

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| SC-EVAL-001 | **17 referencias de acciones mutables** (`@v4`/`@v3`) en deploy-docs, e2e-smoke, quality, vale — un tag movido sustituye código en CI con secretos del repo | `grep uses: @v4` → 17 hits | Todas pineadas al SHA del tag vigente (comentario `# vX` conservado); gate `test_all_action_uses_sha_pinned` |
| SC-EVAL-002 | **3 workflows sin `permissions:`** (ci, e2e-smoke, vale) → GITHUB_TOKEN con permisos por defecto del repo (escritura implícita) | inspección YAML | `contents: read` top-level en los 3; `security-events: write` job-level en `security-scan` (necesario para upload-sarif — antes dependía de defaults del repo) |
| SC-EVAL-003 | **Dependabot docker cubía solo 3 de 9 dirs** con Dockerfile activo (faltaban docs-site, web-management, worker, app-ca, taxii, network_watcher) — imágenes base se quedaban viejas sin PR | diff fd vs dependabot.yml | 6 entradas `docker` añadidas; robtex-patched excluidos (deprecated, documentado) |
| SC-EVAL-004 | **`pip install mutmut` / `cyclonedx-bom` sin versión** en quality/ci/release — CI traía `latest` arbitrario en cada run | grep en workflows | `mutmut==3.8.1`, `cyclonedx-bom==8.0.1`; drift de SHAs normalizado (upload-artifact tenía 3 commits distintos, setup-python mezcla v4/v5 → v5 uniforme) |
| SC-EVAL-005 | **`requirements.lock` stale y parcial** (38 pkgs) — faltaban PyJWT, PyYAML, OTEL×6, uvloop y transitivos → pip-audit los auditaba como ausentes (punto ciego de CVEs) | diff pyproject vs lock | Lock regenerado como closure completo (43 pkgs) resuelto en `python:3.11-slim` limpio; **conectado al Dockerfile con `-c requirements.lock`** → builds reproducibles (SSDF PW.4); gate de frescura lock↔pyproject |
| SC-EVAL-006 | **Cero gates de regresión** de la postura supply-chain — los controles podían degradarse silenciosamente | — | `tests/architecture/test_supply_chain.py` (13 gates) + mounts RO `.github/`+`requirements.lock` en api (base y overlay hardened `!override`) |

## Puntos positivos (evidencia previa al fix)

- **SLSA L3 build**: `provenance: mode=max` + `sbom: true` en buildx; atestaciones publicadas a GHCR junto a cada imagen.
- **Firma keyless cosign** con OIDC (`id-token: write`) + **self-verify gates** que abortan el release si la firma o la atestación no verifican — fail-closed real.
- **Triple escaneo de secretos**: gitleaks + trufflehog (`--only-verified`) + `scan_secrets.py` propio en cada push/PR.
- **pip-audit --strict** sobre el lock de producción + **minimum release age** propio (`check_dep_freshness --min-age-days 7`, equivalente a `minimumReleaseAge` de pnpm que pip no tiene).
- **Trivy FS → SARIF** a code scanning con `exit-code: 1` en CRITICAL/HIGH; **ZAP DAST** baseline + api-scan semanal con `-l FAIL`.
- **OpenSSF Scorecard** semanal con `publish_results` → api.scorecard.dev + SARIF a code scanning, `persist-credentials: false` en checkout.
- **Cero `pull_request_target`** y cero interpolación de `github.event.*` en `run:` — sin vectores clásicos de "pwn request".
- `verify_image_digests.py` genera `requirements-docker.lock` con digests runtime; orborus/worker Dockerfiles pinean base por `@sha256:`.
- `validate_compose_security.py --profile hardened` como gate CI; permisos de workflow ya acotados en los 5 workflows con escritura.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| Imágenes base en Dockerfiles pineadas por **tag** (`python:3.11-slim`), no por digest | Convención documentada: Dependabot propone bumps; los digests runtime quedan congelados en `requirements-docker.lock`. Digest-pin en 9 Dockerfiles rompería el flujo dependabot habitual |
| `pip>=26.2 setuptools>=84.1 wheel` con min-version (no `==`) en Dockerfile | Instala el toolchain más reciente a propósito — la imagen base trae pip/setuptools con CVEs publicadas; el gate de freshness cubre deps de aplicación |
| Dockerfiles `robtex-*-patched` fuera de Dependabot | Deprecated (reemplazados por DShield/Mnemonic) — se conservan por compatibilidad histórica, no se construyen |
| Branch/tag protection de `main`/`v*.*.*` no verificable desde el repo | Vive en settings de GitHub, no en código; mitigado por `release.yml` que solo dispara en tags semver y firma cada artefacto |
| Scorecard publica pero no bloquea por umbral | `fail_on_publish_error` activo; el umbral ≥8.5 (SUP-02) se monitoriza — un gate duro rompería CI por señales externas |
| `npm ci` en docs-site sin integrity adicional | `npm ci` ya exige `package-lock.json` con hashes — resolución estricta por diseño |

## SLSA (build track)

| Requisito | Estado | Evidencia |
|---|---|---|
| Provenance | ✅ L3 | `mode=max` buildx attestation a GHCR + self-verify gate |
| Build as code | ✅ | Todo build en workflow versionado |
| Ephemeral builder | ✅ | GitHub-hosted runners efímeros |
| Isolated params | ✅ | Sin inputs libres; `workflow_dispatch` solo en jobs inofensivos |
| Reproducible | 🟡 parcial | Runtime deps pineados por lock; base images por tag + digest-lock externo |

## NIST SSDF

| Práctica | Estado | Evidencia |
|---|---|---|
| PO.3 toolchain config | ✅ | Actions SHA-pinned, YAML gate, actionlint en lint suite |
| PO.5 artefactos confiables | ✅ | cosign sign + verify + provenance + SBOM por imagen |
| PS.1 código protegido | ✅ | Secrets nunca commiteados (3 escáneres), GITHUB_TOKEN mínimo |
| PS.2 verificación | ✅ | pip-audit, trivy, ZAP, scorecard, freshness gate |
| PS.3 herramientas actualizadas | ✅ | Dependabot 4 ecosistemas/9 dirs + SHAs revisables |
| PW.4 builds reproducibles | ✅ | `-c requirements.lock` en imagen + lock auditado |
| RV.1 vulns identificadas | ✅ | pip-audit --strict gate + SARIF code scanning |

## OWASP SCVS

| Área | Estado |
|---|---|
| Gestión de paquetes | ✅ lock auditado + ranges acotados en pyproject |
| SBOM | ✅ CycloneDX en CI y release + attestación buildx |
| Firmas/atestaciones | ✅ cosign keyless + self-verify |
| Análisis de dependencias | ✅ pip-audit + freshness gate + dependabot |
| Integridad del pipeline | ✅ SHA pinning, least-priv tokens, sin PR-target |

## Deuda pendiente

| Ítem | Estado |
|---|---|
| Digest-pin de base images en Dockerfiles | **Aceptado** — convención tag+digest-lock documentada arriba |
| Umbral duro de Scorecard en CI | **Aceptado** — monitorizado, no bloqueante por flakiness externa |
| Renovación automática de `requirements.lock` | Dependabot pip cubre `/` — los bump PRs lo refrescan vía CI |

## Regresión

- **13/13 gates** `tests/architecture/test_supply_chain.py` verdes.
- **114/114** `tests/architecture/` totales verdes tras los cambios.
- YAML de los 8 workflows + dependabot parseados (`test_workflow_yaml_parses`).
- Verificado en vivo: `.github/` + `requirements.lock` montados RO en
  `soar_api` (base `api.yml` y overlay hardened con `volumes: !override`).

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Idoneidad funcional | 8.5 → **9.6** — CI cubre lint/test/contracts/security/sbom/mutation/backup/docs |
| Seguridad | 7.0 → **9.5** — SHA pinning completo, least-priv, OIDC keyless, triple secret scan |
| Fiabilidad | 7.5 → **9.5** — builds reproducibles por lock, self-verify gates, compose validado |
| Mantenibilidad | 8.0 → **9.5** — dependabot cobertura completa, gates de drift, manifest freshness |
| Portabilidad | 9.0 → **9.5** — artefactos firmados + SBOM + provenance consumibles externamente |
| Observabilidad del pipeline | 8.0 → **9.5** — SARIF/code-scanning, scorecard publicado, artefactos con retención |
| **Global** | ~8.1 → **~9.5** |
