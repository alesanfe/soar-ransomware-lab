# Anexo D: Validación Experimental y Métricas de Calidad

Referencia TFM: complementa el Capítulo 4 (Desarrollo Específico) y el Anexo C (Métricas y Visualizaciones).
Datos extraídos de `reports/e2e/`, `reports/quality/`, `reports/test-review/`,
`reports/holistic/` y `docs/01-getting-started.md`–`docs/06-project-management.md`.

---

## D.1. Resultados Experimentales E2E (n=50)

### Cumplimiento de Objetivos TFM

| Objetivo | Umbral | Valor Medido | Cumple |
|----------|--------|--------------|--------|
| MTTR P50 (mediana) | ≤ 120s | 193.19s | No |
| MTTR P90 | ≤ 180s | 621.83s | No |
| Tasa de Éxito | ≥ 95% | 100% | Sí |
| Dataset (n ejecuciones) | ≥ 50 | 50 | Sí |
| Reducción MTTR vs Manual | ≥ 50% | 92.3% | Sí |

Cumplimiento: 3/5 objetivos.

### MTTR Detallado

| Métrica | Valor |
|---------|-------|
| MTTR Medio | 277.15s |
| MTTR Mediana (P50) | 193.19s |
| MTTR P90 | 621.83s |
| MTTR P95 | 644.46s |
| MTTR Mínimo | 65.38s |
| Desviación Estándar | 187.61s |
| Reducción vs Manual (3600s) | 92.3% |

### Decisiones Automatizadas

| Métrica | Valor |
|---------|-------|
| Tasa de contención (score ≥ 80) | 92.0% (46/50) |
| Tasa de observación (score < 80) | 8.0% (4/50) |
| Score promedio | 96.2/100 (min=55, max=100) |
| Verdict malicious | 13 (score medio 97.3) |
| Verdict suspicious | 37 (score medio 95.8) |

### Servicios e Integraciones

| Métrica | Valor |
|---------|-------|
| Servicios healthy | 10/10 (100%) |
| Workflows completados | 50/50 (100%) |
| Casos TheHive creados | 50/50 (100%) |
| Jobs Cortex | 255/257 (99.2%) |
| Analyzers Cortex disponibles | 34 |
| Técnicas MITRE detectadas | 32 (MITRE, 2025) |
| Nodos en workflow | 46 definidos (49 ejecutados) |
| Tasa de automatización | 100% |

---

## D.2. Métricas de Calidad Consolidadas

| Radar | Score Global | Estado | Fuente |
|-------|-------------|--------|--------|
| Quality Score | 92.2/100 | Excellent | `reports/quality/` |
| Holistic Project Radar (HPR) | 96.0/100 | Excellent | `reports/holistic/` |
| Test Review (7 dims) | 92.2/100 | Excellent | `reports/test-review/` |

### Quality Score por Categoría

| Categoría | Score | Peso | Estado |
|-----------|-------|------|--------|
| Maintainability | 77.6 | 20% | Acceptable |
| Coverage | 84.6 | 20% | Good |
| Complexity | 100 | 15% | Excellent |
| Linting (ruff) | 100 | 15% | Excellent (Astral, 2024) |
| Typing (mypy) | 100 | 10% | Excellent (Python Software Foundation, 2024) |
| Security (bandit) | 100 | 10% | Excellent (PyCQA, 2024b) |
| Documentation | 94.6 | 5% | Excellent |
| Architecture | 100 | 5% | Excellent |

### HPR por Capa

| Capa | Dimensiones | Score Medio | Estado |
|------|-------------|-------------|--------|
| L1 — Core (código producción) | 4 | 94.4 | Excellent |
| L2 — Tests | 3 | 97.2 | Excellent |
| L3 — Quality Gates | 3 | 98.2 | Excellent |
| L4 — Infraestructura | 3 | 100.0 | Excellent |
| L5 — Documentación | 3 | 90.8 | Excellent |

### Métricas Clave de Código

| Métrica | Valor | Herramienta |
|---------|-------|-------------|
| Coverage de líneas | 84.6% (4730/5592) | pytest/cov |
| Complejidad media | 2.61 (max 15, 0 bloques alto riesgo) | radon |
| Maintainability Index | 77.57 (min 50.02, max 100) | radon |
| Issues bandit | 0 (HIGH=0, MEDIUM=0, LOW=0) | bandit |
| Vulnerabilidades | 0 | pip-audit |
| Pylint | 9.1/10, 0 errores | pylint |
| Docstrings | 94.6% (964/1019 funciones) | — |
| Dead code | 18 items (todos en tests) | vulture |

### Métricas Clave de Tests

| Métrica | Valor |
|---------|-------|
| Tests coleccionados | 2233 (1905 seleccionados) |
| Distribución | 65.9% unit, 16.5% integration, 13.8% e2e, 3.8% other |
| Tests saltados | 2 (esperados: Tenzir 404, docker compose en contenedor) |
| Requieren Docker | 35 tests (1.7%) |
| Requieren servicios externos | 83 tests (4.0%) |
| Tests largos (>50 líneas) | 169 |
| Nombres duplicados | 88 (4.3%) |
| Mutation testing | 51.8% (13969 mutantes, 5603 killed, 5322 survived) |

---

## D.3. Infraestructura y API

| Aspecto | Valor |
|---------|-------|
| Servicios totales | 23 (6 compose files, todos válidos) |
| Endpoints API | 38 (OpenAPI 3.1.0 válido) |
| WebSocket | `/api/ws/logs` (streaming tiempo real) |
| APIs reales | 7 (TheHive, Cortex, Shuffle, Lab API, MISP, ES, OpenSearch) |
| APIs simuladas | 1 (SIEM simulado) |
| Variables de entorno | 131 (100% documentadas en `.env.example`) |
| TLS | Nginx self-signed |
| Redes Docker | 3 aisladas (soar_net, ti_net, logging_net) |
| Rate limiting webhook | 60 req/min |
| Backup | `make backup` / `make restore` (tar.gz en `runtime/backups/`) |

Integraciones clave: TheHive API (timeout 120s, 3 retries backoff 0.5), Cortex API (timeout 120s, 3 retries, 7 analyzers en paralelo), Shuffle webhook (60 req/min).

Stack de servicios: Shuffle 2.2.1, TheHive 3.5.2-1, Cortex 3.2.0-1, MISP 2.5.44, Elasticsearch 7.10.2, OpenSearch 2.10.0, Redis 7, PostgreSQL 14, MariaDB 10.11, Nginx 1.25, Loki 2.9.10, Promtail 2.9.9, Grafana 10.3.4, Tenzir v6.8.1.

Requisitos hardware: 8 GB RAM (16 GB+ recomendado), 2 cores (4+), 50 GB SSD, Docker 20.10+, Python 3.11+.

---

## D.4. Gestión del Proyecto

- **20 objetivos SMART** en 4 fases (18 semanas, 27 abr - 31 ago 2026)
- Fase 1 Investigación (3 sem), Fase 2 Diseño (3 sem), Fase 3 Desarrollo (6 sem), Fase 4 Validación (6 sem)
- Estimación inicial 12 sem → 15 sem → 18 sem real (ampliación tests + experimento n=50)
- Consideraciones éticas: muestras inertes, no exposición de datos reales, entorno aislado

Detalle del cronograma y objetivos en `objectives_and_methodology.md` y Anexo F (F.8, F.9).

---

## D.5. Resumen Ejecutivo de Validación

| Aspecto | Resultado | Evidencia |
|---------|-----------|-----------|
| Workflow E2E | Sí Funcional | 50/50 workflows completados |
| MTTR | Sí Mejora 92.3% | 3600s -> 277.15s |
| Contención | Sí 92% | 46/50 alertas con score ≥ 80 |
| Automatización | Sí 100% | Sin intervención humana |
| Calidad código | Sí 92.2/100 | Quality score Excellent |
| HPR | Sí 96.0/100 | Holistic radar Excellent |
| Tests | Sí 2233 tests (1905 seleccionados) | 2 skipped (esperados), coverage 84.6% |
| Seguridad | Sí 0 issues | Bandit + pip-audit limpios |
| Infraestructura | Sí 23 servicios | 6 compose files válidos |
| API | Sí 38 endpoints | OpenAPI 3.1.0 válido |
| Mutation testing | Parcial 51.8% | 13969 mutantes, 5603 killed, 5322 survived |
| Objetivos TFM | Parcial 3/5 | MTTR P50 y P90 no cumplidos |
