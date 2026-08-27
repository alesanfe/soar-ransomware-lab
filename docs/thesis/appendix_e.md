# Anexo E: Estrategia de Testing y Quality Assurance

Referencia TFM: complementa el Capítulo 4 (Desarrollo específico) y el Anexo D (Validación).
Datos extraídos de `docs/05-testing.md`, `reports/test-review/`, `reports/quality/`,
`reports/holistic/` y `tests/`.

---

## E.1. Visión General

El laboratorio SOAR implementa una estrategia de testing exhaustiva basada en la pirámide
de tests con pytest (pytest, 2024), con cobertura de calidad medida por 3 sistemas independientes:

| Sistema | Score | Dimensiones |
|---------|-------|-------------|
| Quality Score | 92.2/100 | 8 categorías (coverage, complexity, security, linting, typing, docs, architecture, maintainability) |
| Holistic Project Radar | 96.0/100 | 15 dimensiones en 5 capas (core, tests, quality, infra, docs) |
| Test Review | 92.2/100 | 7 dimensiones (pirámide, salud, aislamiento, complejidad, duplicación) |

---

## E.2. Inventario de Tests

### Estadísticas Generales

| Métrica | Valor |
|---------|-------|
| Tests coleccionados | 2233 |
| Tests seleccionados | 1905 |
| Tests deseleccionados | 328 |
| Tests ejecutados (última run) | 1905 (2 skipped esperados) |
| Archivos de test | 169 |
| Tiempo de ejecución | ~200s (3m 20s) |
| Warnings | 4 |

### Distribución por Categoría

| Categoría | Archivos | Tests | % del Total |
|-----------|----------|-------|-------------|
| unit | 79 | 1245 | 61.0% |
| integration | 30 | 336 | 16.5% |
| e2e | 48 | 281 | 13.8% |
| atomic | 4 | 101 | 5.0% |
| security | 1 | 27 | 1.3% |
| performance | 4 | 30 | 1.5% |
| general | 2 | 20 | 1.0% |
| architecture | 1 | 1 | 0.05% |
| **Total** | **169** | **2041** | 100% |

Nota: el desglose por categoría (2041 tests) corresponde a la instantánea del
`holistic_review` en el momento de generación del reporte. El total actual es
2233 tests coleccionados (1905 seleccionados, 328 deseleccionados) — ver estadísticas generales.
La diferencia (192 tests) corresponde a tests añadidos tras la generación del reporte.

### Distribución por Capa (Pirámide)

| Capa | Tests | % Actual | % Ideal | Desviación |
|------|-------|----------|---------|------------|
| Unit + Atomic | 1346 | 65.9% | 70% | -4.1% |
| Integration | 336 | 16.5% | 20% | -3.5% |
| E2E | 281 | 13.8% | 10% | +3.8% |
| Other | 78 | 3.8% | — | — |
| **Pirámide score** | | | | **94.3/100** |

---

## E.3. Cobertura de Código

| Métrica | Valor |
|---------|-------|
| Cobertura de líneas | 84.6% (4730/5592) |
| Cobertura de ramas | 73.2% |
| Archivos analizados | 98 |
| Archivos < 75% threshold | 17 |
| Umbral mínimo (pyproject.toml) | 80% |

Archivos con menor cobertura: `application/ports/output/__init__.py` (0%), `interfaces/api/__init__.py` (12.5%), `infrastructure/subprocess_runner.py` (30.6%), `interfaces/api/route_helpers.py` (40%), `infrastructure/integrations/shuffle/shuffle_helpers.py` (44.3%).

Archivos con 100% cobertura: `sqlite_alert_repository.py` (143 líneas), `routes_soar.py` (190), `models.py` (104), `validation.py` (52), `auth.py` (22).

---

## E.4. Marcadores de pytest

El proyecto usa marcadores auto-aplicados por directorio (configurados en `tests/conftest.py`):

| Marcador | Auto-aplicado a |
|----------|-----------------|
| `unit` | `tests/unit/` |
| `integration` | `tests/integration/` |
| `e2e` | `tests/e2e/` |
| `performance` | `tests/performance/` |
| `security` | `tests/security/` |
| `atomic` | `tests/atomic/` |
| `quality` | `tests/general/`, `tests/quality/` |
| `architecture` | `tests/architecture/` |
| `requires_docker` | E2E (extra) |
| `requires_external` | E2E (extra) |
| `slow` | E2E, performance (extra) |

Los marcadores se aplican automáticamente según el directorio del test
(`pytest_collection_modifyitems` en `conftest.py`), sin necesidad de
anotar cada archivo. Adicionalmente, `test_smoke.py` usa sub-marcadores
`smoke_critical`, `smoke_high`, `smoke_medium`.

---

## E.5. Tests E2E (48 archivos, 281 tests)

Catálogo completo de Test Cases E2E (39 TCs en `tests/e2e/TC-*/`):

| TC | Nombre | Tests | Descripción |
|----|--------|-------|-------------|
| TC-00 | Both Workflows | 4 | Validación parametrizada de ambos escenarios (malicioso/benigno) |
| TC-01 | Malicious | 11 | Alerta maliciosa básica — pipeline SOAR completo |
| TC-02 | Benign | 5 | Alerta benigna (falso positivo) — pipeline SOAR completo |
| TC-03 | Edge Cases | 10 | Resiliencia: payloads edge-case no deben causar crash |
| TC-04 | Performance | 15 | Latencia, throughput y uso de recursos bajo carga |
| TC-05 | Concurrent | 6 | Alertas concurrentes (múltiples simultáneas) |
| TC-06 | Critical | 6 | Severidad crítica — comportamiento del workflow |
| TC-07 | Missing Fields | 5 | Campos ausentes (hash/IP) — manejo de errores |
| TC-08 | Additional Fields | 4 | Campos adicionales — comportamiento del workflow |
| TC-09 | Realistic | 7 | Escenario ransomware realista (224 líneas, el más largo) |
| TC-10 | Tenzir | 11 | Integración Tenzir (ingestión de eventos) |
| TC-11 | Network Watcher | 11 | Integración Network Watcher (conexiones de red) |
| TC-12 | Redis | 10 | Integración Redis (caché de IoCs) |
| TC-13 | Loki | 15 | Integración Loki (ingestión de logs) |
| TC-14 | Complete SOAR + Traceability | 10 | Integración completa SOAR + trazabilidad end-to-end |
| TC-15 | API Latency | 9 | Latencia de API por servicio individual |
| TC-16 | Error Handling | 7 | Clasificación de errores, éxito parcial y modo degradado |
| TC-17 | Network Watcher Monitoring | 9 | Monitorización de conexiones de red |
| TC-18 | Resilience | 5 | Resiliencia y modo degradado (Cortex/MISP no disponibles) |
| TC-19 | Security | 13 | Validación de input y autenticación (payloads malformados) |
| TC-20 | Zero Trust | 4 | Zero trust y segmentación de red (least privilege) |
| TC-21 | Forensic | 7 | Integridad forense (cadena de custodia, audit trail) |
| TC-22 | Persistence | 9 | Persistencia y restauración (reboot, backup) |
| TC-23 | Privacy | 7 | Privacidad y secretos (PII masking, secret redaction) |
| TC-24 | Malware Específico | 4 | Respuesta diferenciada para malware específico |
| TC-25 | Behavioral | 4 | Detección conductual (behavioral detection) |
| TC-26 | Extreme Load | 4 | Carga extrema: alert storm, estrés del sistema |
| TC-27 | Configuration | 4 | Gestión de configuración |
| TC-28 | UI E2E | 12 | UI end-to-end: login, navegación, alert management |
| TC-29 | Compliance + Large Evidence | 5 | Cumplimiento (MITRE/D3FEND) + evidencia grande |
| TC-30 | Offline | 3 | Modo offline / air-gapped |
| TC-31 | Compliance + Containment | 11 | Cumplimiento (MITRE/D3FEND) + contención de endpoint |
| TC-32 | Golden Thread + IOC Analysis | 5 | Hilo dorado (integridad cross-system) + tiempo de análisis IOC |
| TC-33 | Real IoCs (gminst4ll) | 10 | Validación con muestra forense real |
| TC-KPI-01 | MTTR Calculation | 1 | Verificación del cálculo de MTTR |
| TC-KPI-02 | KPI Dashboard | 2 | Dashboard Grafana + percentiles MTTR |
| TC-KPI-03 | KPI Alerts | 1 | Alertas basadas en KPIs |
| TC-KPI-04 | MTTR Percentiles + Success Rates | 3 | Percentiles MTTR (SLA) + tasas de éxito por servicio |
| TC-KPI-05 | Node Timings + Success Rates | 3 | Timing por nodo + tasas de éxito por servicio |
| TC-KPI-06 | KPI Data Coherence + Service Health | 9 | Coherencia Shuffle/TheHive/Cortex + salud de servicios |

Los 48 archivos incluyen `__init__.py`, `conftest.py`, `workflow_validator.py`,
`base/` (8 mixins), `assertions/` (4 módulos) y `helpers/` (4 módulos)
además de los 39 directorios TC-*/TC-KPI-*.

Total de tests largos (>50 líneas): **169** (8.3% del total).

---

## E.6. Salud y Aislamiento

| Métrica | Valor |
|---------|-------|
| Tests saltados | 2 (esperados: Tenzir 404, docker compose en contenedor) |
| XFail | 0 |
| Health score | 99.5/100 |
| Tests que requieren Docker | 35 (1.7%) en 3 archivos |
| Tests que requieren servicios externos | 83 (4.0%) en 9 archivos |
| Tests offline | ~1923 (94.3%) |
| Isolation score | 97.5/100 |

---

## E.7. Complejidad y Duplicación

| Métrica | Valor | Score |
|---------|-------|-------|
| Tests largos (>50 líneas) | 169 | — |
| Tests débiles (<1.5 assertions) | 60 | — |
| Complexity score | — | 83.4/100 |
| Nombres únicos | 1947 | — |
| Nombres duplicados | 88 (4.3%) | — |
| Duplication score | — | 86.4/100 |

Los nombres duplicados son principalmente tests que verifican la misma funcionalidad
desde diferentes niveles (unit + integration), lo cual es esperado en una pirámide de tests.

---

## E.8. Mutation Testing

| Métrica | Valor |
|---------|-------|
| Mutation Score | 51.8% (Parcial High risk) |
| Total mutantes generados | 13 969 |
| Mutantes con cobertura (probados) | 11 050 |
| Killed | 5603 (50.7% de probados) |
| Survived | 5322 (48.2% de probados) |
| Timeout | 125 (1.1% de probados) |
| Sin cobertura | 2919 (20.9% del total) |
| Throughput | 2.43 mutations/second |
| Duración | ~96 min |

Mutation testing con mutmut (mutmut, 2024) ejecutado en Docker (`make mutation`). El score del 51.8% es inferior al umbral del 70%, indicando margen de mejora en la calidad de los tests. Los módulos con mayor concentración de mutantes sobrevivientes son `infrastructure.integrations` (1132) e `interfaces.api` (614). El módulo `simulator.simulate_alerts` aporta 1321 mutantes sin cobertura (se prueba indirectamente vía E2E).

Configuración en `pyproject.toml`:
```toml
[tool.mutmut]
source_paths = ["src/soar_lab/"]
pytest_add_cli_args = ["-q", "--tb=no", "--timeout=30", "--no-cov", ...]
pytest_add_cli_args_test_selection = ["tests/unit/"]
do_not_mutate = ["src/soar_lab/__init__.py", "*/scripts/*", "*/tests/*"]
```

Reproducción: `make mutation` (60-180 min, reporte en `reports/mutmut/mutation_report.md`).

---

## E.9. Requisitos de Cobertura

| Tipo | Umbral | Actual |
|------|--------|--------|
| Coverage general | 80% | 84.6% Sí |
| Funciones críticas | 80% | Sí |
| Funciones de seguridad | 90% | Sí |
| Mutation testing (general) | 70% | 51.8% Parcial |
| Mutation testing (críticas) | 80% | Pendiente |

---

## E.10. Flujo de Ejecución Canónico

```bash
# 1. Generar secretos y configuración
make generate-secrets && make generate-iocs

# 2. Levantar stack
make reset && make health

# 3. Tests sin Docker (rápidos): make test-unit, make test-atomic
# 4. Tests con stack (lentos): make test-integration, make test-smoke, make test-e2e
# 5. Tests especializados: make test-performance, make test-security
# 6. Todo en uno: make test-all (2233 coleccionados, 1905 seleccionados)
# 7. Coverage: make test-coverage (HTML + XML + JSON)
# 8. Quality: make quality, make test-review, make holistic-review
```

---

## E.11. Prerrequisitos por Categoría

| Categoría | Python | Docker | .env.full | Stack Up | Shuffle Init |
|-----------|--------|--------|-----------|----------|--------------|
| Unit/Atomic | 3.11+ | No | placeholders | No | No |
| Integration | 3.11+ | Sí | real creds | Sí | Sí |
| E2E | 3.11+ | Sí | real creds | Sí | Sí |
| Performance | 3.11+ | Sí | real creds | Sí | Sí |
| Security | 3.11+ | No | placeholders | No | No |
| Smoke | 3.11+ | Sí | real creds | Sí | Sí |

---

## E.12. Quality Gates

| Tool | Issues | Score |
|------|--------|-------|
| ruff | 0 | 100/100 |
| mypy | 0 errors | 100/100 |
| pylint | 528 issues (0 errors) | 9.1/10 |
| bandit | 0 (HIGH=0, MED=0, LOW=0) | 100/100 |
| pip-audit | 0 vulnerabilities | 100/100 |

Complejidad ciclomática: 814 bloques, media 2.61, max 15 (grado C), 0 bloques alto riesgo. Complexity score: 98.6/100.

Documentación: docstrings 94.6% (964/1019 funciones), dead code 18 items (todos en tests). Documentation score: 94.6/100.

---

## E.13. Resumen de Validación

| Aspecto | Score | Estado |
|---------|-------|--------|
| Quality Score global | 92.2/100 | Excellent |
| Holistic Project Radar | 96.0/100 | Excellent |
| Test Review | 92.2/100 | Excellent |
| Coverage de líneas | 84.6% | Sí (>80%) |
| Pirámide de tests | 94.3/100 | Excellent |
| Salud de tests | 99.5/100 | Excellent |
| Aislamiento | 97.5/100 | Excellent |
| Seguridad (bandit) | 0 issues | Sí Clean |
| Linting (ruff) | 0 issues | Sí Clean |
| Tipado (mypy) | 0 errors | Sí Clean |
| Complejidad | 98.6/100 | Excellent |
| Docstrings | 94.6% | Excellent |
| Mutation testing | 51.8% | Parcial High risk |
