# Image signing and provenance verification (SUP-02 / SC2)

Every project-built image published to GHCR on a `v*.*.*` tag is:

1. Built with `docker/build-push-action` emitting **SLSA provenance
   (mode=max)** and an inline **SBOM attestation** (BuildKit attestations,
   stored as OCI referrers alongside the image).
2. **Keyless-signed with cosign** (Sigstore/Fulcio short-lived cert bound
   to the GitHub Actions OIDC identity — no long-lived key material).
3. **Self-verified in the pipeline** — the release job fails if
   `cosign verify` does not confirm the signature just produced.

Published images (matrix in `.github/workflows/release.yml`):

| Image | Dockerfile |
| --- | --- |
| `ghcr.io/<owner>/soar-api` | `apps/api/Dockerfile` |
| `ghcr.io/<owner>/soar-docs-site` | `apps/docs-site/Dockerfile` |
| `ghcr.io/<owner>/soar-web-management` | `apps/web-management/Dockerfile` |
| `ghcr.io/<owner>/shuffle-worker-patched` | `infra/docker/images/worker/Dockerfile` |
| `ghcr.io/<owner>/shuffle-orborus-patched` | `infra/docker/images/orborus/Dockerfile` |

## Verifying a release image (consumers)

```bash
# 1. Resolve the digest (never verify a mutable tag)
DIGEST=$(docker buildx imagetools inspect \
  ghcr.io/<owner>/soar-api:1.4.0 --format '{{.Manifest.Digest}}')

# 2. Verify the cosign signature — proves the image was built by the
#    release workflow of this repository on GitHub-hosted runners
cosign verify "ghcr.io/<owner>/soar-api@${DIGEST}" \
  --certificate-identity-regexp \
    "https://github.com/<owner>/<repo>/.github/workflows/release.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

# 3. Inspect SLSA provenance (source repo, workflow, materials)
cosign verify-attestation --type slsaprovenance \
  --certificate-identity-regexp \
    "https://github.com/<owner>/<repo>/.github/workflows/release.yml@.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  "ghcr.io/<owner>/soar-api@${DIGEST}" | jq '.payload' -r | base64 -d | jq

# 4. Inspect the CycloneDX SBOM for Python dependencies (uploaded as
#    release artifact `sbom-<tag>` for soar-api)
cosign verify-attestation --type spdxjson ... # buildkit SBOM attestation
```

## Scope and honest limits

- Signing covers **project-built images only**. Third-party bases
  (TheHive, Cortex, MISP, Grafana, Shuffle upstream, Orborus base) are
  pinned by tag/digest in compose files but are upstream-signed or
  unsigned — not covered by our cosign signature.
- A signature proves *who built it and from which workflow*, not that
  the image is free of vulnerabilities — pair with `pip-audit` over
  `requirements.lock` and the Trivy/Grype scan results in CI.
- Keyless signing relies on Sigstore transparency (Rekor). Air-gapped
  verification requires exporting the Rekor bundle (`cosign sign --bundle`).
- Until the first `v*.*.*` tag is pushed, this pipeline is **verified by
  review and self-check design, not by execution evidence** — see the
  SUP-02 row in `docs/17-technical-backlog-9of10.md` for the residual.
