# Anexo E: Validación Experimental y Métricas de Calidad

> **Referencia TFM:** complementa el Capítulo 4 (Desarrollo Específico) y el Anexo D (Métricas y Visualizaciones).
> Datos extraídos de `reports/e2e/`, `reports/quality/`, `reports/test-review/`,
> `reports/holistic/` y `docs/01-getting-started.md`–`docs/06-project-management.md`.

---

## 1. Resultados Experimentales E2E (n=50)

### 1.1. Cumplimiento de Objetivos TFM

| Objetivo | Umbral | Valor Medido | Cumple |
|----------|--------|--------------|--------|
| MTTR P50 (mediana) | ≤ 120s | 193.19s | No |
| MTTR P90 | ≤ 180s | 621.83s | No |
| Tasa de Éxito | ≥ 95% | 100% | Sí |
| Dataset (n ejecuciones) | ≥ 50 | 50 | Sí |
| Reducción MTTR vs Manual | ≥ 50% | 92.3% | Sí |

**Cumplimiento: 3/5 objetivos.**

### 1.2. MTTR Detallado

| Métrica | Valor |
|---------|-------|
| MTTR Medio | 277.15s |
| MTTR Mediana (P50) | 193.19s |
| MTTR P90 | 621.83s |
| MTTR P95 | 644.46s |
| MTTR Mínimo | 65.38s |
| Desviación Estándar | 187.61s |
| Reducción vs Manual (3600s) | 92.3% |

### 1.3. Decisiones Automatizadas

| Métrica | Valor |
|---------|-------|
| Tasa de contención (score ≥ 80) | 92.0% (46/50) |
| Tasa de observación (score < 80) | 8.0% (4/50) |
| Score promedio | 96.2/100 (min=55, max=100) |
| Verdict malicious | 13 (score medio 97.3) |
| Verdict suspicious | 37 (score medio 95.8) |

### 1.4. Servicios e Integraciones

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

## 2. Calidad del Software

### 2.1. Quality Score Global

**Score: 92.2/100 — Excellent**

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

### 2.2. Complejidad Ciclomática

- Total de bloques: **814**
- Complejidad media: **2.61**
- Complejidad máxima: **15** (grado C, moderado)
- Bloques de alto riesgo (D-F): **0**

| Grado | Count | Significado |
|-------|-------|-------------|
| A | 735 | Riesgo bajo (1-5) |
| B | 61 | Aceptable (6-10) |
| C | 18 | Riesgo moderado (11-20) |
| D | 0 | Riesgo alto (21-30) |
| E | 0 | Riesgo muy alto (31-40) |
| F | 0 | Crítico (41+) |

### 2.3. Cobertura de Tests

- Cobertura de líneas: **84.6%** (4730/5592)
- Cobertura de ramas: **73.2%**
- Archivos por debajo del 75%: **17**

### 2.4. Mantenibilidad

- Archivos analizados: **127**
- Maintainability Index medio: **77.57**
- MI mínimo: **50.02** (`src/soar_lab/data/calc_kpis.py`)
- MI máximo: **100.00**

### 2.5. Seguridad

- Issues bandit: **0** (HIGH=0, MEDIUM=0, LOW=0) (PyCQA, 2024b)
- Vulnerabilidades pip-audit: **0** (pip-audit, 2024)
- Pylint: 9.1/10, 0 errores

### 2.6. Documentación

- Docstrings: **94.6%** (964/1019 funciones documentadas)
- Dead code: **18 items** (todos 60% confianza en tests, 0 en producción)

---

## 3. Holistic Project Radar (HPR)

**Score Global: 96.0/100 — Excellent**

| Capa | Dimensiones | Score Medio | Estado |
|------|-------------|-------------|--------|
| L1 — Core (código producción) | 4 | 94.4 | Excellent |
| L2 — Tests | 3 | 97.2 | Excellent |
| L3 — Quality Gates | 3 | 98.2 | Excellent |
| L4 — Infraestructura | 3 | 100.0 | Excellent |
| L5 — Documentación | 3 | 90.8 | Excellent |

### 3.1. Detalle por Dimensión

| Dim | Capa | Score | Descripción |
|-----|------|-------|-------------|
| L1a | Core | 100.0 | Arquitectura (0 violaciones import-linter) |
| L1b | Core | 98.6 | Complejidad (814 bloques, max CX=15) |
| L1c | Core | 100 | Tipado (0 errores mypy) |
| L1d | Core | 78.8 | Dead code (18 items, todos en tests) |
| L2a | Tests | 94.3 | Pirámide (2041 tests, 65.9% unit) |
| L2b | Tests | 99.9 | Salud (2 skips esperados, 0 inesperados) |
| L2c | Tests | 97.5 | Aislamiento (1.7% requieren Docker) |
| L3a | Quality | 100 | Linting (0 issues ruff) |
| L3b | Quality | 100 | Seguridad (0 issues bandit) |
| L3c | Quality | 94.6 | Docstrings (964/1019) |
| L4a | Infra | 100.0 | Docker Compose (6/6 válidos, 23 servicios) |
| L4b | Infra | 100 | OpenAPI (38 endpoints, válido) |
| L4c | Infra | 100.0 | Env vars (131/131, 100% coverage) |
| L5a | Docs | 86.9 | Links (260 links, 34 rotos en reports) |
| L5b | Docs | 87.5 | Estructura (7/8 compliant) |
| L5c | Docs | 98.0 | Code refs (402 refs, 8 rotos) |

---

## 4. Revisión de Tests (7 Dimensiones)

**Score Global: 92.2/100 — Excellent**

| Dim | Score | Estado |
|-----|-------|--------|
| D3 Pirámide | 94.3 | Excellent |
| D4 Salud | 99.5 | Excellent |
| D5 Aislamiento | 97.5 | Excellent |
| D6 Complejidad | 83.4 | Good |
| D7 Duplicación | 86.4 | Good |

### 4.1. Distribución de Tests

| Capa | Tests | % Actual | % Ideal |
|------|-------|----------|---------|
| Unit + Atomic | 1346 | 65.9% | 70% |
| Integration | 336 | 16.5% | 20% |
| E2E | 281 | 13.8% | 10% |
| Other | 78 | 3.8% | — |
| **Total** | **2041** | | |

### 4.2. Tests por Categoría

| Categoría | Archivos | Tests |
|-----------|----------|-------|
| unit | 79 | 1245 |
| integration | 30 | 336 |
| e2e | 49 | 281 |
| atomic | 4 | 101 |
| security | 1 | 27 |
| performance | 4 | 30 |
| general | 2 | 20 |
| architecture | 1 | 1 |

### 4.3. Salud de Tests

- Tests saltados: **2** (esperados, 0 inesperados)
- XFail: **0**
- Razones de skip:
  - Tenzir REST API no disponible (404 en /api/v0/status)
  - docker compose no disponible dentro del contenedor

### 4.4. Aislamiento de Tests

- Requieren Docker: **35 tests** (1.7%) en 3 archivos
- Requieren servicios externos: **83 tests** (4.0%) en 9 archivos

### 4.5. Complejidad de Tests

- Tests largos (>50 líneas): **169**
- Tests débiles (<1.5 assertions): **60**
- Test más largo: `test_realistic_ransomware` (224 líneas, TC-09)

### 4.6. Duplicación

- Nombres únicos: **1947**
- Nombres duplicados: **88** (4.3%)
- Duplicados principales: `test_alert`, `test_audit_trail`, `test_case_creation`

---

## 5. Infraestructura y Despliegue

### 5.1. Stack de Servicios (13 componentes)

| Componente | Versión | Función |
|------------|---------|---------|
| Shuffle SOAR | 2.2.1 | Orquestación de workflows (Shuffle Tools, 2024) |
| TheHive | 3.5.2-1 | Gestión de casos (TheHive Project, 2024) |
| Cortex | 3.2.0-1 | Análisis de IoCs (Cortex Project, 2024) |
| MISP | 2.5.44 | Threat intelligence (MISP Project, 2024) |
| Elasticsearch | 7.10.2 | Búsqueda (TheHive/Cortex) (Elastic, 2024) |
| OpenSearch | 2.10.0 | Engine de Shuffle (OpenSearch Project, 2024) |
| Redis | 7-alpine | Cache/cola (Redis Ltd., 2024) |
| PostgreSQL | 14-alpine | DB Grafana |
| MariaDB | 10.11 | DB MISP |
| Nginx | 1.25-alpine | Reverse proxy, TLS (Nginx, 2024) |
| Loki + Promtail | 2.9.10 / 2.9.9 | Agregación de logs (Grafana Labs, 2024b; Grafana Labs, 2024c) |
| Grafana | 10.3.4 | Visualización (Grafana Labs, 2024) |
| Tenzir Node | v6.8.1 | Ingesta de logs (dev) (Tenzir, 2024) |

### 5.2. Docker Compose

- Archivos compose: **6** (todos válidos)
- Servicios totales: **23**
- Pipeline de despliegue: **19 pasos** automáticos (`make up`)

### 5.3. Requisitos de Hardware

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 8 GB | 16 GB+ |
| CPU | 2 cores | 4 cores+ |
| Disco | 50 GB SSD | 50 GB+ SSD |
| Docker Engine | 20.10+ | 24.0+ |
| Docker Compose | 2.0+ | 2.20+ |
| Python | 3.11+ | 3.12+ |

### 5.4. Variables de Entorno

- Variables totales: **131** (100% documentadas en `.env.example`)
- Generación automática de secretos: `make generate-secrets`
- Secretos nunca commiteados (`.env.full` en `.gitignore`)
- JWT_SECRET_KEY: mínimo 32 caracteres, HS256
- Contraseñas DB: sin `@` ni `!` (escaping)

### 5.5. Seguridad

- TLS: Nginx termina TLS con certificados self-signed
- Redes Docker aisladas: `soar_net` (10.100.0.0/16), `ti_net` (172.22.0.0/16), `logging_net` (172.23.0.0/16)
- Rate limiting webhook: 60 req/min
- Payload máximo: 65536 bytes
- CORS configurado para localhost
- 0 vulnerabilidades (pip-audit)
- 0 issues bandit

### 5.6. Backup

- Manual: `make backup` (POST `/backup/create`)
- Restore: `make restore BACKUP=<name>` (POST `/backup/restore`)
- Almacenamiento: `runtime/backups/` (tar.gz)
- No hay cron automático configurado en el laboratorio

---

## 6. API REST

### 6.1. Endpoints

- Total: **38 endpoints** (OpenAPI 3.1.0, válido)
- WebSocket: `/api/ws/logs` (streaming en tiempo real)
- APIs reales: **7** (TheHive, Cortex, Shuffle, Lab API, MISP, Elasticsearch, OpenSearch)
- APIs simuladas: **1** (SIEM simulado — `src/soar_lab/simulator/simulate_alerts.py`)

### 6.2. Integraciones Clave

| Integración | Timeout | Retries | Concurrente |
|-------------|---------|---------|-------------|
| TheHive API | 30s | 3 (backoff 5s) | — |
| Cortex API | 30s | 1 | 7 analyzers en paralelo |
| Shuffle webhook | — | — | 60 req/min |

---

## 7. Gestión del Proyecto

### 7.1. Objetivos SMART

- **20 objetivos SMART** definidos con métricas cuantificables
- **18 semanas** distribuidas en 4 fases (27 abr - 31 ago 2026)
- **4 hitos** (milestones) de validación

### 7.2. Fases del Proyecto

| Fase | Duración planificada | Duración real | Objetivos |
|------|---------------------|---------------|-----------|
| 1. Infraestructura | 4 semanas | 4 semanas | 1, 8, 17, 18 |
| 2. Desarrollo | 5 semanas | 7 semanas | 2, 5, 6, 19, 20 |
| 3. Validación | 4 semanas | 5 semanas | 3, 9-14 |
| 4. Cierre | 2 semanas | 2 semanas | 4, 15, 16 |

> La estimación inicial fue de 15 semanas, aumentada a 18 tras la
> integración de Cortex con analyzers externos y el stack de monitoreo
> (fase 2) y la ampliación de la suite de tests a 2041 (fase 3).

### 7.3. Consideraciones Éticas

- Uso exclusivo de muestras inertes para simulación
- No exposición de datos reales o sensibles
- Entorno de laboratorio aislado para investigación académica

---

## 8. Resumen Ejecutivo de Validación

| Aspecto | Resultado | Evidencia |
|---------|-----------|-----------|
| Workflow E2E | Sí Funcional | 50/50 workflows completados |
| MTTR | Sí Mejora 92.3% | 3600s -> 277.15s |
| Contención | Sí 92% | 46/50 alertas con score ≥ 80 |
| Automatización | Sí 100% | Sin intervención humana |
| Calidad código | Sí 92.2/100 | Quality score Excellent |
| HPR | Sí 96.0/100 | Holistic radar Excellent |
| Tests | Sí 2041 tests | 1384 passed (última run), coverage 84.6% |
| Seguridad | Sí 0 issues | Bandit + pip-audit limpios |
| Infraestructura | Sí 23 servicios | 6 compose files válidos |
| API | Sí 38 endpoints | OpenAPI 3.1.0 válido |
| Mutation testing | Parcial 51.8% | 13969 mutantes, 5603 killed, 5322 survived |
| Objetivos TFM | Parcial 3/5 | MTTR P50 y P90 no cumplidos |
