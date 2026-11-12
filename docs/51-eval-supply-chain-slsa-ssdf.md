# Evaluación Supply Chain / CI-CD — SLSA, NIST SSDF, ISO 27034, NIST SP 800-218

> **Fecha**: 2026-11-12 · **Suite**: `tests/architecture/test_supply_chain.py` (15 gates) · **Resultado**: gap de pinning cerrado; pipeline ya era fuerte.

## 1. Defecto corregido

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| SC-EVAL-001 | **`FROM` base de los 4 Dockerfiles con tag mutable** (`python:3.11-slim`, `nginx:1.27-alpine`, `node:22-alpine`) — builds no reproducibles + ventana de supply-chain | `FROM img@sha256:<digest>` en los 4 Dockerfiles (stage aliases intactos) | gate `test_all_froms_digest_pinned` |

## 2. Matriz por dimensión

| Dimensión | Marco | Estado |
|-----------|-------|--------|
| **SBOM** | SSDF PW.4 / SLSA | CycloneDX en `ci.yml` (artifact por SHA) **y** en `release.yml` (por tag) + `sbom: true` buildkit attestation en imagen |
| **Firma artefactos** | SLSA / sigstore | `cosign sign` **keyless** por digest + `cosign verify` con `--certificate-identity-regexp` + `--certificate-oidc-issuer` (self-check gate) |
| **Provenance** | SLSA L3 | `provenance: mode=max` + `verify-attestation --type slsaprovenance` con identidad OIDC atada al workflow |
| **Dependencia segura** | SSDF RV.1 | `pip-audit --strict` gate, 4 lock files (`requirements*.lock`), `requirements-docker.lock` + `verify_image_digests.py` (preflight + `make verify-digests`), Trivy→SARIF, Dependabot |
| **Reproducibilidad** | ISO 27034 | Imágenes compose digest-locked, **bases FROM ahora digest-pinned**, actions 100% SHA-pinned (0 `@v*`/`@main` en workflows) |
| **Secretos** | SSDF PS | `scan_secrets.py` en CI + exports GitOps scrubbed + entrypoints con placeholders (misp/keycloak/taxii/redis) — cero literals |
| **Gates seguridad** | SSDF RV | CI: pip-audit, secret scan, trivy SARIF→code-scanning, bandit/semgrep/checkov en lint suite, ZAP DAST (`dast.yml`), scorecard semanal |

## 3. Verificación

- 15/15 gates (incluye `test_no_unpinned_pip_installs_in_workflows` + `test_release_pipeline_provenance_signing` preexistentes — confirmados)
- cosign 2.5.3 pinned (v3 rompe `verify-attestation` — decisión documentada en workflow)
- Release: `attestations: write` permission + GHCR publish por digest

## 4. Residuales

| Restricción | Naturaleza |
|-------------|------------|
| SBOM generado no se *verifica* (diff vs release anterior) | Mejora incremental posible; el artifact existe y es publicado |
| Builds heredados (docs-site con npm) | `npm ci` + lockfile commiteado — hermetismo razonable |
