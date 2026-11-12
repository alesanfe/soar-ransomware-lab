# Evaluación Perímetro — NIST SP 800-207 (Zero Trust) · CIS Controls 12/13

> **Fecha**: 2026-11-12 · Re-evaluación bajo Zero Trust + CIS (complementa `docs/39`, ISO 25010/STRIDE). **Resultado**: 1 defecto corregido + inventario de flujos creado. Score ~9.5/10.

## Defecto corregido

| ID | Defecto | Fix | Evidencia live |
|----|---------|-----|----------------|
| NET-EVAL-2-001 | **`misp-db` con egress NAT innecesario** — MariaDB vivía solo en `misp_internal` (red con gateway): podía salir a internet pese a no necesitarlo jamás (solo habla con `misp` y el probe blackbox) | Nueva red **`misp_db_net` con `internal: true`** — sin gateway NAT, egress físicamente imposible. misp-db migra a ella; misp-modules conserva `misp_internal` (egress legítimo de enrichment); blackbox se adhiere para mantener el probe :3306 | `docker exec misp-db → /dev/tcp/8.8.8.8/53` → **"Network is unreachable"** · `misp→misp-db` resuelve · `probe_success 1` |

## Inventario de flujos (CIS 12.2 — era el gap principal)

`infra/docker/compose/flow-inventory.yml` — fuente de verdad machine-readable:

- **`published:`** — 21 puertos publicados (todos loopback-only) con propósito; gate verifica que todo `${*_PORT}` en compose figure documentado
- **`flows:`** — 25 flujos internos autorizados `src→dst:port proto tls` con propósito (api→redis TLS, api→shuffle 5443, orborus→5001 plaintext-loopback, misp→db…)
- **`egress_policy:`** — política por plano declarada explícitamente
- Gate obliga: puerto publicado nuevo sin documentar → suite roja

## Matriz por dimensión

| Dimensión | Control | Estado |
|-----------|---------|--------|
| **Egress filtering** | CIS 12.4/13.4 | api: `EGRESS_GUARD` iptables ACCEPT privados → DROP (self-heal netns, eval 39) · misp-db: `internal:true` ahora **egress cero físico** · allowlist app-level en shuffle_forward |
| **Segmentación** | 800-207 §4, CIS 12.2 | 5 planos: `soar_net` / `ti_net` / `misp_internal` / **`misp_db_net` (internal)** / `logging_net` · db/módulos fuera del plano público · sidecars `network_mode: service:` comparten netns deliberadamente |
| **Política deny-all** | 800-207 §7 | Egress api DROP final · ingress shuffle-backend DROP excepto :5001 loopback · publicación loopback-only (gate) · `${VAR:?}` fail-closed |
| **Inventario flujos** | CIS 12.2/13.1 | `flow-inventory.yml` + `network-watcher` `/api/connections` live (GET-only) |
| **Inspección TLS** | CIS 13 | **Ausente deliberadamente** — cert pinning + mTLS romperían bajo MITM; detección por metadatos (watcher + tenzir + blackbox probes). Decisión registrada en el inventario (gate) |

## Positivos adicionales

- `api-egress-guard`/`ingress-guard`: NET_ADMIN solo en sidecar mínimo (netshoot RO+nnp+pids), nunca en la app
- `netns-guardian` repara sidecars stale (restart no re-resuelve `service:x`)
- Attach zero-trust del watcher: label+imagen verificados **antes** de `net.connect`

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Egress NAT libre en `soar_net` | Cortex analyzers (DShield/pDNS), MISP feeds, Orborus pull necesitan internet — universal guard rompería el lab |
| Plano único para ~30 servicios | Docker Compose no ofrece micro-segmentación declarativa; mitigado por autenticación mutua + TLS en cada flujo |
| Ventana ~45s egress abierto tras recreate api | Acotada por watch-loop (eval 39) |
| Sin IDS/IPS inline | Lab: detección vía Zeek-like tenzir + watcher, no inline |

## Regresión

`test_network_perimeter.py`: 12 → **17 gates** · verificación live del aislamiento incluida arriba.
