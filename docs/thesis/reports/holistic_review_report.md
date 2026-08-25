# Holistic Project Radar (HPR)

Generated: **2026-08-24 10:14:30 UTC**
Methodology: 5-layer, 15-dimension structured project review

---

## Overall Score

**96.0/100 — Excellent**

```
  Dimension    Layer       Score  Bar
  ──────────── ────────── ──────  ────────────────────────────────────────
  L1a          Core        100.0  ████████████████████████████████████████
  L1c          Core        100.0  ████████████████████████████████████████
  L3a          Quality     100.0  ████████████████████████████████████████
  L3b          Quality     100.0  ████████████████████████████████████████
  L4a          Infra       100.0  ████████████████████████████████████████
  L4b          Infra       100.0  ████████████████████████████████████████
  L4c          Infra       100.0  ████████████████████████████████████████
  L2b          Tests        99.9  ███████████████████████████████████████░
  L1b          Core         98.6  ███████████████████████████████████████░
  L5c          Docs         98.0  ███████████████████████████████████████░
  L2c          Tests        97.5  ███████████████████████████████████████░
  L3c          Quality      94.6  █████████████████████████████████████░░░
  L2a          Tests        94.3  █████████████████████████████████████░░░
  L5b          Docs         87.5  ███████████████████████████████████░░░░░
  L5a          Docs         86.9  ██████████████████████████████████░░░░░░
  L1d          Core         78.8  ███████████████████████████████░░░░░░░░░
```

| Dimension | Layer | Score | Status |
|-----------|-------|-------|--------|
| L1a | Core | 100.0 | Excellent |
| L1b | Core | 98.6 | Excellent |
| L1c | Core | 100 | Excellent |
| L1d | Core | 78.8 | Acceptable |
| L2a | Tests | 94.3 | Excellent |
| L2b | Tests | 99.9 | Excellent |
| L2c | Tests | 97.5 | Excellent |
| L3a | Quality | 100 | Excellent |
| L3b | Quality | 100 | Excellent |
| L3c | Quality | 94.6 | Excellent |
| L4a | Infra | 100.0 | Excellent |
| L4b | Infra | 100 | Excellent |
| L4c | Infra | 100.0 | Excellent |
| L5a | Docs | 86.9 | Good |
| L5b | Docs | 87.5 | Good |
| L5c | Docs | 98.0 | Excellent |
| **Overall** | — | **96.0** | **Excellent** |


---

## Layer 1 — Core (Production Code)

### L1a — Architecture (import-linter)

- Violations: 0
- Has contracts: No
- Score: **100.0**

```
No import-linter contracts configured — treated as 0 violations
```

_No import-linter contracts configured. Score is 100 because there are no violations. Consider adding contracts to enforce hexagonal layering rules._

### L1b — Complexity (radon cc)

- Total blocks: 814

| Grade | Count |
|-------|-------|
| A | 735 |
| B | 61 |
| C | 18 |
| D | 0 |
| E | 0 |
| F | 0 |

- Max complexity: 15
- Score: **98.6**

### L1c — Typing (mypy)

- Errors: 0
- Score: **100**

### L1d — Dead code (vulture)

- Dead items: 18
- Score: **78.8**

_Items are low-confidence (60%) false positives in test files — unused variables, helper functions, and pytest mocks. No high-confidence dead code in production._


---

## Layer 2 — Tests

### L2a — Test Pyramid

- Total tests: 2041
- Unit: 1346 (65.9%)
- Integration: 336 (16.5%)
- E2E: 281 (13.8%)
- Deviation: 5.7%
- Score: **94.3**

### L2b — Test Health

- Total tests: 2093
- Skipped: 2 (expected: 2, unexpected: 0)
- XFail: 0
- Top skip reasons:
  - Tenzir REST API not available (404 on /api/v0/status): 1
  - docker compose not available inside container — test require: 1
- Score: **99.9**

### L2c — Test Isolation

- Requires Docker: 35 (1.7%)
- Requires external: 83 (4.0%)
- Score: **97.5**


---

## Layer 3 — Quality Gates

### L3a — Linting (ruff)

- Issues: 0
- Score: **100**

### L3b — Security (bandit)

- Total issues: 0
- HIGH: 0, MEDIUM: 0, LOW: 0
- Score: **100**

### L3c — Docstrings (interrogate)

- Coverage: 964/1019 (94.6%)
- Score: **94.6**


---

## Layer 4 — Infrastructure

### L4a — Docker Compose

- Compose files: 5
- Valid files: 5
- Total services: 18
- Files: docker-compose.api.yml, docker-compose.core.yml, docker-compose.misp.yml, docker-compose.opensearch.yml, docker-compose.yml
- Score: **100.0**

### L4b — OpenAPI Schema

- Valid: Yes
- Version: 3.1.0
- Title: SOAR Lab Management API
- Endpoints: 38
- Score: **100**

### L4c — Environment Variables

- Example vars: 131
- Full vars: 131
- Coverage: 100.0%
- Score: **100.0**


---

## Layer 5 — Documentation

### L5a — Doc Links

- MD files: 33
- Total links: 260
- Broken links: 34
- Broken links by file:
  - `docs/thesis/reports/e2e_report.md`: `./charts/threshold_compliance.png`, `./charts/service_health.png`, `./charts/GE1_component_timings.png` (+17 more)
- Score: **86.9**

### L5b — Doc Structure (6 sections)

- Total files: 8
- Compliant: 7
- Non-compliant: 1 files
  - `docs/glossary.md`: missing ['Resumen', 'Alcance', 'Validación', 'Problemas', 'Referencias']
- Score: **87.5**

### L5c — Code References in Docs

- Total references: 402
- Broken references: 8
- Broken references by file:
  - `docs/thesis/CHANGELOG_THESIS_UPDATE.md`: `src/soar_lab/scripts/setup/generate_env.py`, `infra/docker/compose/logging/grafana-datasources.yml`
  - `docs/thesis/data_visualizations.md`: `infra/docker/compose/logging/promtail-config.yml`
  - `docs/thesis/specific_development.md`: `infra/docker/compose/docker-compose.wazuh.yml`
  - `docs/thesis/reports/holistic_review_report.md`: `src/soar_lab/scripts/setup/generate_env.py`, `infra/docker/compose/logging/grafana-datasources.yml`, `infra/docker/compose/logging/promtail-config.yml` (+1 more)
- Score: **98.0**


---

## Layer Scores

| Layer | Dimensions | Avg Score | Status |
|-------|------------|-----------|--------|
| L1 (Core) | 4 | 94.4 | Excellent |
| L2 (Tests) | 3 | 97.2 | Excellent |
| L3 (Quality) | 3 | 98.2 | Excellent |
| L4 (Infra) | 3 | 100.0 | Excellent |
| L5 (Docs) | 3 | 90.8 | Excellent |


---

## Recommendations

- ⚠️ **L1d** (Core): 78.8/100 — needs attention
- ℹ️ Run with `--with-coverage` to include structural coverage analysis.
- ℹ️ Run `make mutation` in Docker to include mutation testing analysis.


---

## Methodology — HPR (Holistic Project Radar)

The HPR methodology evaluates the project across 5 concentric layers,
from the innermost (production code) to the outermost (documentation).
Each layer contains 3 dimensions, for a total of 15 dimensions.

```
         ┌─────────────────────────────────────┐
         │  Layer 5 — Documentation             │
         │  ┌───────────────────────────────┐   │
         │  │  Layer 4 — Infrastructure      │   │
         │  │  ┌───────────────────────────┐ │   │
         │  │  │  Layer 3 — Quality Gates   │ │   │
         │  │  │  ┌───────────────────────┐ │ │   │
         │  │  │  │  Layer 2 — Tests       │ │ │   │
         │  │  │  │  ┌───────────────────┐ │ │ │   │
         │  │  │  │  │  Layer 1 — Core    │ │ │ │   │
         │  │  │  │  │  (production code) │ │ │ │   │
         │  │  │  │  └───────────────────┘ │ │ │   │
         │  │  │  └───────────────────────┘ │ │   │
         │  │  └───────────────────────────┘ │   │
         │  └───────────────────────────────┘   │
         └─────────────────────────────────────┘
```

| Layer | Dim | What it measures | Tool |
|-------|-----|------------------|------|
| L1 Core | L1a | Architecture (hexagonal) | import-linter |
| L1 Core | L1b | Complexity | radon cc |
| L1 Core | L1c | Typing | mypy |
| L1 Core | L1d | Dead code | vulture |
| L2 Tests | L2a | Pyramid (unit/int/e2e) | AST analysis |
| L2 Tests | L2b | Health (skip/xfail) | AST + regex |
| L2 Tests | L2c | Isolation (Docker deps) | pytest markers |
| L3 Quality | L3a | Linting | ruff |
| L3 Quality | L3b | Security | bandit |
| L3 Quality | L3c | Docstrings | interrogate |
| L4 Infra | L4a | Docker Compose | yaml parse |
| L4 Infra | L4b | OpenAPI schema | json parse |
| L4 Infra | L4c | Env vars coverage | .env comparison |
| L5 Docs | L5a | Links | path resolution |
| L5 Docs | L5b | Structure (6 sections) | regex |
| L5 Docs | L5c | Code refs | path resolution |
| Opt | Cov | Structural coverage | coverage.py |
| Opt | Mut | Logic coverage | mutmut |

### Scoring

Each dimension produces a 0-100 score. Layer scores are the arithmetic
mean of their dimensions. The overall score is the mean of all available
dimensions (including optional ones if present).
