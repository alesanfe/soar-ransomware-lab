# Anexo G: Estrategia de Testing y Quality Assurance

> **Referencia TFM.** complementa el Capítulo 5 (Desarrollo) y el Anexo E (Validación).
> Datos extraídos de `docs/05-testing.md`, `reports/test-review/`, `reports/quality/`,
> `reports/holistic/` y `tests/`.

---

## I.1. Visión General

El laboratorio SOAR implementa una estrategia de testing exhaustiva basada en la pirámide
de tests con pytest (pytest, 2024), con cobertura de calidad medida por 3 sistemas independientes:

| Sistema | Score | Dimensiones |
|---------|-------|-------------|
| Quality Score | 92.2/100 | 8 categorías (coverage, complexity, security, linting, typing, docs, architecture, maintainability) |
| Holistic Project Radar | 96.0/100 | 15 dimensiones en 5 capas (core, tests, quality, infra, docs) |
| Test Review | 92.2/100 | 7 dimensiones (pirámide, salud, aislamiento, complejidad, duplicación) |

---

## I.2. Inventario de Tests

### I.2.1. Estadísticas Generales

| Métrica | Valor |
|---------|-------|
| Tests coleccionados | 2233 |
| Tests seleccionados | 1905 |
| Tests deseleccionados | 328 |
| Tests ejecutados (última run) | 1905 (2 skipped esperados) |
| Archivos de test | 170 |
| Tiempo de ejecución | ~200s (3m 20s) |
| Warnings | 4 |

### I.2.2. Distribución por Categoría

| Categoría | Archivos | Tests | % del Total |
|-----------|----------|-------|-------------|
| unit | 79 | 1245 | 61.0% |
| integration | 30 | 336 | 16.5% |
| e2e | 49 | 281 | 13.8% |
| atomic | 4 | 101 | 5.0% |
| security | 1 | 27 | 1.3% |
| performance | 4 | 30 | 1.5% |
| general | 2 | 20 | 1.0% |
| architecture | 1 | 1 | 0.05% |
| **Total** | **170** | **2041** | 100% |

### I.2.3. Distribución por Capa (Pirámide)

| Capa | Tests | % Actual | % Ideal | Desviación |
|------|-------|----------|---------|------------|
| Unit + Atomic | 1346 | 65.9% | 70% | -4.1% |
| Integration | 336 | 16.5% | 20% | -3.5% |
| E2E | 281 | 13.8% | 10% | +3.8% |
| Other | 78 | 3.8% | — | — |
| **Pirámide score** | | | | **94.3/100** |

```
           ▲
          / \        E2E (281, 13.8%)
         /   \       ── pocos, lentos, stack completo
        /─────\
       /       \     Integration (336, 16.5%)
      /         \    ── algunos, servicios reales
     /───────────\
    /             \  Unit + Atomic (1346, 65.9%)
   /               \ ── muchos, rápidos, aislados
  /─────────────────\
```

---

## I.3. Cobertura de Código

### I.3.1. Cobertura Global

| Métrica | Valor |
|---------|-------|
| Cobertura de líneas | 84.6% (4730/5592) |
| Cobertura de ramas | 73.2% |
| Archivos analizados | 98 |
| Archivos < 75% threshold | 17 |
| Umbral mínimo (pyproject.toml) | 80% |

### I.3.2. Archivos con Menor Cobertura

| # | Archivo | Línea cov | Branch cov | Líneas |
|---|---------|-----------|------------|--------|
| 1 | `application/ports/output/__init__.py` | 0.0% | — | 0/2 |
| 2 | `interfaces/api/__init__.py` | 12.5% | 50.0% | 7/56 |
| 3 | `infrastructure/subprocess_runner.py` | 30.6% | 0.0% | 19/62 |
| 4 | `interfaces/api/route_helpers.py` | 40.0% | 0.0% | 6/15 |
| 5 | `infrastructure/integrations/shuffle/shuffle_helpers.py` | 44.3% | 35.7% | 66/149 |

### I.3.3. Archivos con Mayor Cobertura (100%)

| Archivo | Líneas | Branch |
|---------|--------|--------|
| `infrastructure/persistence/sqlite_alert_repository.py` | 143 | 100% |
| `interfaces/api/routes_soar.py` | 190 | 100% |
| `interfaces/api/models.py` | 104 | 100% |
| `interfaces/api/validation.py` | 52 | 100% |
| `interfaces/api/auth.py` | 22 | 100% |
| `interfaces/api/contracts.py` | 41 | — |
| `infrastructure/monitoring/system_metrics_driver.py` | 42 | 75% |

---

## I.4. Marcadores de pytest

El proyecto usa marcadores auto-aplicados por directorio (configurados en `tests/conftest.py`) más marcadores extras para E2E:

| Marcador | Descripción | Auto-aplicado a |
|----------|-------------|-----------------|
| `@pytest.mark.unit` | Tests unitarios | `tests/unit/` |
| `@pytest.mark.integration` | Tests de integración | `tests/integration/` |
| `@pytest.mark.e2e` | Tests end-to-end | `tests/e2e/` |
| `@pytest.mark.performance` | Tests de rendimiento | `tests/performance/` |
| `@pytest.mark.security` | Tests de seguridad | `tests/security/` |
| `@pytest.mark.atomic` | Tests atómicos | `tests/atomic/` |
| `@pytest.mark.quality` | Tests de calidad | `tests/general/`, `tests/quality/` |
| `@pytest.mark.architecture` | Tests de arquitectura | `tests/architecture/` |
| `@pytest.mark.requires_docker` | Requiere Docker | E2E (extra) |
| `@pytest.mark.requires_external` | Requiere servicios externos | E2E (extra) |
| `@pytest.mark.slow` | Tests lentos | E2E, performance (extra) |

> Los marcadores se aplican automáticamente según el directorio del test
> (`pytest_collection_modifyitems` en `conftest.py`), sin necesidad de
> anotar cada archivo. Adicionalmente, `test_smoke.py` usa sub-marcadores
> `smoke_critical`, `smoke_high`, `smoke_medium`.

---

## I.5. Tests E2E (49 archivos, 281 tests)

### I.5.1. Catálogo de Test Cases E2E

| TC | Nombre | Archivo | Líneas | Descripción |
|----|--------|---------|--------|-------------|
| TC-00 | Both Workflows | `test_both_workflows.py` | — | Validación ambos escenarios |
| TC-01 | Malicious | `test_malicious.py` | — | Alerta maliciosa básica |
| TC-02 | Benign | `test_benign.py` | — | Alerta benigna (falso positivo) |
| TC-04 | Performance | `test_performance.py` | — | Rendimiento del workflow |
| TC-05 | Concurrent | `test_concurrent_alerts.py` | 172 | Alertas concurrentes |
| TC-06 | Critical | `test_critical_severity.py` | 138 | Severidad crítica |
| TC-09 | Realistic | `test_realistic_ransomware.py` | 224 | Escenario ransomware realista |
| TC-10 | Tenzir | `test_tenzir_integration.py` | — | Integración Tenzir |
| TC-16 | Error Handling | `test_error_handling.py` | — | Manejo de errores |
| TC-20 | Zero Trust | `test_zero_trust.py` | 123 | Zero trust / least privilege |
| TC-21 | Forensic | `test_forensic.py` | — | Análisis forense |
| TC-25 | Behavioral | `test_behavioral_detection.py` | 131 | Detección comportamental |
| TC-26 | Extreme Load | `test_extreme_load.py` | 126 | Carga extrema |
| TC-28 | UI E2E | `test_ui_e2e.py` | — | UI end-to-end |
| TC-30 | Offline | `test_offline_mode.py` | — | Modo offline |
| TC-31 | Compliance | `test_compliance.py` | — | Cumplimiento |
| TC-32 | Golden Thread | `test_golden_thread.py` | 152 | Integridad hilo dorado |
| TC-33 | IOC Analysis | `test_ioc_analysis_time.py` | 143 | Tiempo de análisis IoC |
| TC-KPI-01..05 | KPIs | `test_mttr_*`, `test_node_timings.py` | 132-208 | Métricas KPI (Makefile) |
| TC-KPI-06 | KPIs extra | `test_kpi_data_coherence.py`, `test_service_health.py` | — | Coherencia KPI (no en Makefile) |

### I.5.2. Tests Más Largos (>50 líneas)

| Test | Archivo | Líneas |
|------|---------|--------|
| `test_realistic_ransomware` | TC-09 | 224 |
| `test_mttr_percentiles` | TC-KPI-02 | 208 |
| `test_concurrent_alerts` | TC-05 | 172 |
| `test_golden_thread_integrity` | TC-32 | 152 |
| `test_ioc_analysis_time` | TC-33 | 143 |
| `test_critical_severity` | TC-06 | 138 |
| `test_node_timings` | TC-KPI-05 | 132 |
| `test_polymorphic_behavior` | TC-25 | 131 |
| `test_duplicate_prevention` | TC-26 | 126 |
| `test_least_privilege` | TC-20 | 123 |

Total de tests largos: **169** (8.3% del total)

---

## I.6. Salud de Tests

| Métrica | Valor |
|---------|-------|
| Tests saltados (skipped) | 2 |
| XFail | 0 |
| Skips esperados | 2 |
| Skips inesperados | 0 |
| **Health score** | **99.9/100** |

### I.6.1. Razones de Skip

| Razón | Count |
|-------|-------|
| Tenzir REST API not available (404 on /api/v0/status) | 1 |
| docker compose not available inside container | 1 |

> Ambos skips son esperados: Tenzir está en modo dev y docker compose no está
> disponible dentro de contenedores (requiere ejecución en host).

---

## I.7. Aislamiento de Tests

| Métrica | Valor |
|---------|-------|
| Tests que requieren Docker | 35 (1.7%) en 3 archivos |
| Tests que requieren servicios externos | 83 (4.0%) en 9 archivos |
| Tests offline (sin dependencias) | ~1923 (94.3%) |
| **Isolation score** | **97.5/100** |

### I.7.1. Archivos que Requieren Docker

- `tests/integration/test_docker_partial_failure.py`
- `tests/integration/test_docker_runtime_status.py`
- `tests/integration/test_smoke.py`

### I.7.2. Archivos que Requieren Servicios Externos

- `tests/integration/test_api_init.py`
- `tests/integration/test_app_e2e.py`
- `tests/integration/test_data_consistency.py`
- `tests/integration/test_elasticsearch_integration.py`
- `tests/integration/test_idempotency.py`
- `tests/integration/test_openapi_spec_sync.py`
- `tests/integration/test_race_conditions.py`
- `tests/performance/test_database_performance.py`
- `tests/performance/test_workflow_performance.py`

---

## I.8. Complejidad y Duplicación

### I.8.1. Complejidad de Tests

| Métrica | Valor |
|---------|-------|
| Tests largos (>50 líneas) | 169 |
| Tests débiles (<1.5 assertions) | 60 |
| **Complexity score** | **83.4/100** |

### I.8.2. Tests con Baja Densidad de Assertions

| Archivo | Tests | Assertions | Avg/test |
|---------|-------|------------|----------|
| `tests/unit/integrations/test_send_alert.py` | 5 | 2 | 0.4 |
| `tests/unit/common/test_timeout_handling.py` | 10 | 5 | 0.5 |
| `tests/atomic/test_alert_validation.py` | 21 | 14 | 0.7 |
| `tests/integration/test_cortex_integration.py` | 3 | 2 | 0.7 |
| `tests/integration/test_external_service_failure.py` | 15 | 10 | 0.7 |

### I.8.3. Duplicación de Nombres

| Métrica | Valor |
|---------|-------|
| Nombres únicos | 1947 |
| Nombres duplicados | 88 (4.3%) |
| **Duplication score** | **86.4/100** |

> Los nombres duplicados son principalmente tests que verifican la misma funcionalidad
> desde diferentes niveles (unit + integration), lo cual es esperado en una pirámide de tests.

---

## I.9. Requisitos de Cobertura

| Tipo | Umbral | Actual |
|------|--------|--------|
| Coverage general | 80% | 84.6% Sí |
| Funciones críticas | 80% | Sí |
| Funciones de seguridad | 90% | Sí |
| Mutation testing (general) | 70% | 51.8% Parcial |
| Mutation testing (críticas) | 80% | Pendiente |

> Mutation testing con mutmut (mutmut, 2024) ejecutado en Docker (`make mutation`).
> Resultados: 13 969 mutantes generados, 5603 killed (40.1%), 5322 survived (38.1%),
> 125 timeout (0.9%), 2919 sin cobertura (20.9%). Mutation Score sobre mutantes con
> cobertura: **51.8%** (5603 + 125 killed/timeout sobre 11 050 mutantes probados).
> El score es inferior al umbral del 70%, lo que indica que existe margen de mejora
> en la calidad de los tests para detectar mutaciones de código.

### I.9.1. Resultados Detallados de Mutation Testing

**Resumen ejecutivo.**

| Métrica | Valor |
|---------|-------|
| **Mutation Score** | **51.8%** |
| **Estado** | Parcial High risk |
| Total mutantes generados | 13 969 |
| Mutantes con cobertura (probados) | 11 050 |
| 🎉 Killed | 5603 (40.1% del total, 50.7% de probados) |
| 🙁 Survived | 5322 (38.1% del total, 48.2% de probados) |
| ⏰ Timeout | 125 (0.9% del total, 1.1% de probados) |
| 🫥 Sin cobertura (no tests) | 2919 (20.9% del total) |
| Suspicious | 0 |
| Skipped | 0 |
| Throughput | 2.43 mutations/second |
| Duración aproximada | ~96 min (13 969 / 2.43) |

**Distribución de mutantes sobrevivientes por módulo (top 10).**

| Módulo | Mutantes sobrevivientes |
|--------|------------------------|
| `infrastructure.integrations` | 1132 |
| `interfaces.api` | 614 |
| `config.settings` | 567 |
| `application.use_cases` | 531 |
| `data.calc_kpis` | 387 |
| `infrastructure.network_watcher` | 297 |
| `infrastructure.monitoring` | 275 |
| `infrastructure.messaging` | 162 |
| `infrastructure.validate_credentials` | 129 |
| `domain.services` | 126 |

**Distribución de mutantes sin cobertura por módulo (top 5).**

| Módulo | Mutantes sin cobertura |
|--------|----------------------|
| `simulator.simulate_alerts` | 1321 |
| `infrastructure.integrations` | 848 |
| `infrastructure.subprocess_runner` | 182 |
| `interfaces.api` | 148 |
| `application.use_cases` | 147 |

**Interpretación.**

El mutation score del 51.8% se clasifica como "High risk" según la escala de mutmut,
lo que significa que los tests detectan aproximadamente la mitad de las mutaciones
introducidas. Los módulos con mayor concentración de mutantes sobrevivientes son
`infrastructure.integrations` (1132) e `interfaces.api` (614), lo que sugiere que
estas capas de adaptadores y endpoints API requieren tests más específicos que
verifiquen tanto el camino feliz como las ramificaciones lógicas
(operadores booleanos, comparaciones, constantes).

El módulo `simulator.simulate_alerts` aporta 1321 mutantes sin cobertura, lo que
refleja que el simulador de alertas no tiene tests unitarios directos (se prueba
indirectamente vía tests E2E). Excluir este módulo de la mutación reduciría el
total a 12 648 mutantes y elevaría el score a (5603 + 125) / (12 648 - 2919 + 1321)
≈ 57.3%.

**Configuración utilizada.**

```toml
[tool.mutmut]
source_paths = ["src/soar_lab/"]
pytest_add_cli_args = ["-q", "--tb=no", "--timeout=30", "--no-cov", ...]
pytest_add_cli_args_test_selection = ["tests/unit/"]
do_not_mutate = ["src/soar_lab/__init__.py", "*/scripts/*", "*/tests/*"]
```

**Comando de reproducción.**

```bash
make mutation    # Ejecuta mutmut en Docker (60-180 min)
# Reporte generado: reports/mutmut/mutation_report.md
```

---

## I.10. Flujo de Ejecución Canónico

```bash
# 1. Generar secretos y configuración
make generate-secrets
make generate-iocs

# 2. Levantar stack
make reset          # down + clean + up
make health         # verificar 10/10 servicios

# 3. Tests sin Docker (rápidos)
make test-unit      # 1245 tests, ~30s
make test-atomic    # 101 tests, ~10s

# 4. Tests con stack (lentos)
make test-integration   # 336 tests, ~120s
make test-smoke         # smoke tests
make test-e2e           # 281 tests, ~300s

# 5. Tests especializados
make test-performance   # 30 tests
make test-security      # 27 tests

# 6. Todo en uno
make test-all           # 2233 tests coleccionados (1905 seleccionados)

# 7. Coverage
make test-coverage      # genera HTML + XML + JSON (pytest-cov (pytest-cov, 2024))

# 8. Quality
make quality            # radon (PyCQA, 2024a) + bandit + vulture (jendrikse, 2024) + ...
make test-review        # informe 7 dimensiones
make holistic-review    # radar 15 dimensiones
```

---

## I.11. Prerrequisitos por Categoría

| Categoría | Python | Docker | .env.full | Stack Up | Shuffle Init |
|-----------|--------|--------|-----------|----------|--------------|
| Unit/Atomic | 3.11+ | No | placeholders | No | No |
| Integration | 3.11+ | Sí | real creds | Sí | Sí |
| E2E | 3.11+ | Sí | real creds | Sí | Sí |
| Performance | 3.11+ | Sí | real creds | Sí | Sí |
| Security | 3.11+ | Sí | real creds | Sí | No |
| Smoke | 3.11+ | Sí | real creds | Sí | Sí |

---

## I.12. Quality Gates

### I.12.1. Linting

| Tool | Issues | Score |
|------|--------|-------|
| ruff | 0 | 100/100 |
| mypy | 0 errors | 100/100 |
| pylint | 528 issues (0 errors) | 9.1/10 |

### I.12.2. Seguridad

| Tool | Issues | Score |
|------|--------|-------|
| bandit | 0 (HIGH=0, MED=0, LOW=0) | 100/100 |
| pip-audit | 0 vulnerabilities | 100/100 |

### I.12.3. Complejidad

| Métrica | Valor |
|---------|-------|
| Total bloques | 814 |
| Complejidad media | 2.61 |
| Complejidad máxima | 15 (grado C) |
| Bloques alto riesgo (D-F) | 0 |
| **Complexity score** | **98.6/100** |

| Grado | Count | Significado |
|-------|-------|-------------|
| A | 735 | Riesgo bajo (1-5) |
| B | 61 | Aceptable (6-10) |
| C | 18 | Moderado (11-20) |
| D | 0 | Alto riesgo (21-30) |
| E | 0 | Muy alto (31-40) |
| F | 0 | Crítico (41+) |

### I.12.4. Documentación

| Métrica | Valor |
|---------|-------|
| Docstrings coverage | 94.6% (964/1019) |
| Dead code items | 18 (todos en tests, 0 en producción) |
| **Documentation score** | **94.6/100** |

---

## I.13. Resumen de Validación

| Aspecto | Score | Estado |
|---------|-------|--------|
| Quality Score global | 92.2/100 | Excellent |
| Holistic Project Radar | 96.0/100 | Excellent |
| Test Review | 92.2/100 | Excellent |
| Coverage de líneas | 84.6% | Sí (>80%) |
| Pirámide de tests | 94.3/100 | Excellent |
| Salud de tests | 99.9/100 | Excellent |
| Aislamiento | 97.5/100 | Excellent |
| Seguridad (bandit) | 0 issues | Sí Clean |
| Linting (ruff) | 0 issues | Sí Clean |
| Tipado (mypy) | 0 errors | Sí Clean |
| Complejidad | 98.6/100 | Excellent |
| Docstrings | 94.6% | Excellent |
| Mutation testing | 51.8% | Parcial High risk |
