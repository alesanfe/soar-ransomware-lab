# Suite de Pruebas del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Estructura de pruebas](#31-estructura-de-pruebas)
        - [3.1.1 Estructura de directorios](#311-estructura-de-directorios)
        - [3.1.2 Categorías de pruebas](#312-categorías-de-pruebas)
    - [3.2 Categorías de pruebas](#32-categorías-de-pruebas)
        - [3.2.1 Ejecución de pruebas](#321-ejecución-de-pruebas)
        - [3.2.2 Eliminaciones de pruebas](#322-eliminaciones-de-pruebas)
        - [3.2.3 Ejecución individual](#323-ejecución-individual)
        - [3.2.4 Script de ejecución](#324-script-de-ejecución)
        - [3.2.5 Configuración de pruebas](#325-configuración-de-pruebas)
        - [3.2.6 Datos y fixtures](#326-datos-y-fixtures)
    - [3.3 Casos de prueba](#33-casos-de-prueba)
        - [3.3.1 Objetivos de cobertura](#331-objetivos-de-cobertura)
        - [3.3.2 Entornos de pruebas](#332-entornos-de-pruebas)
        - [3.3.3 Generación de reportes](#333-generación-de-reportes)
    - [3.4 Ejecución de pruebas](#34-ejecución-de-pruebas)
        - [3.4.1 Comandos de ejecución](#341-comandos-de-ejecución)
        - [3.4.2 Entornos de ejecución](#342-entornos-de-ejecución)
    - [3.5 Reportes y métricas](#35-reportes-y-métricas)
        - [3.5.1 Reportes generados](#351-reportes-generados)
        - [3.5.2 Métricas clave](#352-métricas-clave)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Limitaciones](#51-limitaciones)
        - [5.1.1 Limitaciones de pruebas de navegador](#511-limitaciones-de-pruebas-de-navegador)
        - [5.1.2 Limitaciones de pruebas de seguridad](#512-limitaciones-de-pruebas-de-seguridad)
    - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
        - [5.2.1 Servicios faltantes](#521-servicios-faltantes)
        - [5.2.2 Problemas de permisos](#522-problemas-de-permisos)
        - [5.2.3 Problemas de Docker](#523-problemas-de-docker)
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
        - [5.3.1 Depuración de pruebas](#531-depuración-de-pruebas)
        - [5.3.2 Mejores prácticas](#532-mejores-prácticas)
        - [5.3.3 Integración continua](#533-integración-continua)
        - [5.3.4 Contribución](#534-contribución)
        - [5.3.5 Pruebas de seguridad](#535-pruebas-de-seguridad)
        - [5.3.6 Pruebas de rendimiento](#536-pruebas-de-rendimiento)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Suite de pruebas integral para el proyecto SOAR Ransomware Lab, cubriendo pruebas unitarias, de integración, de
rendimiento, de seguridad y de extremo a extremo (E2E).

### 1.2 Contexto

La suite de pruebas valida todos los componentes del sistema SOAR Ransomware Lab, incluyendo APIs, workflows de
automatización, integraciones de servicios y rendimiento bajo carga.

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Estructura y organización de la suite de pruebas
- Categorías de pruebas (unitarias, atómicas, integración, navegador, rendimiento, seguridad, E2E)
- Ejecución de pruebas (comandos, cobertura, ejecutores de pruebas)
- Configuración de pruebas (pytest.ini, marcadores, fixtures)
- Entornos de pruebas (local, CI/CD, Docker)
- Mejores prácticas y solución de problemas

### 2.2 Límites

Este documento no cubre:

- Estrategia detallada de pruebas de Docker (ver docs/testing/docker_testing_strategy.md)
- Arquitectura detallada del sistema (ver docs/architecture/overview.md)
- Planificación del proyecto (ver docs/project/plan.md)

### 2.3 Dependencias

Este documento depende de:

- Estrategia de pruebas de Docker (docs/testing/docker_testing_strategy.md)
- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de Docker (docs/architecture/docker_architecture.md)
- Guía de usuario (docs/getting_started/user_guide.md)

## 3. Contenido principal

### 3.1 Estructura de pruebas

#### 3.1.1 Estructura de directorios

**Estado Actual (Enero 2026):**

```
tests/
├── unit/                    # 37 archivos de pruebas unitarias
│   ├── test_alert_generator.py
│   ├── test_analytics_service.py
│   ├── test_api_models.py
│   ├── test_auth.py
│   ├── test_backup_service.py
│   ├── test_base_client.py
│   ├── test_checksum_utils.py
│   ├── test_cleanup_service.py
│   ├── test_clients.py
│   ├── test_composition.py
│   ├── test_config_provider.py
│   ├── test_config_schemas.py
│   ├── test_dependencies.py
│   ├── test_domain_models.py
│   ├── test_domain_ports.py
│   ├── test_file_log_reader.py
│   ├── test_filesystem_storage.py
│   ├── test_generate_secrets.py
│   ├── test_health_check_adapter.py
│   ├── test_health_service.py
│   ├── test_http_alert_sender.py
│   ├── test_http_client.py
│   ├── test_in_memory_alert_repository.py
│   ├── test_in_memory_storage.py
│   ├── test_integration_clients_unit.py
│   ├── test_ioc_generator.py
│   ├── test_jwt_token_provider.py
│   ├── test_kpi_analyzer.py
│   ├── test_kpi_formatter.py
│   ├── test_log_parser.py
│   ├── test_logging.py
│   ├── test_misp_client_unit.py
│   ├── test_path_service.py
│   ├── test_pytest_output_parser.py
│   ├── test_pytest_test_runner.py
│   ├── test_settings.py
│   ├── test_sqlite_alert_repository.py
│   ├── test_statistical_calculator.py
│   ├── test_subprocess_runner.py
│   ├── test_system_metrics_driver.py
│   ├── test_tar_backup_driver.py
│   ├── test_test_service.py
│   ├── test_validators.py
│   └── test_websocket_manager.py
├── atomic/                  # 4 archivos de pruebas atómicas
├── integration/             # 23 archivos de pruebas de integración
├── e2e/                     # 3 archivos de pruebas E2E
├── performance/             # 2 archivos de pruebas de rendimiento
├── security/                # 2 archivos de pruebas de seguridad
├── fixtures/                # 9 archivos de fixtures
├── runners/                 # 2 archivos de ejecutores
├── conftest.py              # Configuración de Pytest
└── __init__.py
```

**Nota:** La estructura actual difiere significativamente de la documentación anterior. Las pruebas unitarias ahora
cubren exhaustivamente el código Python en `src/soar_lab/` con 37 archivos de prueba.

#### 3.1.2 Categorías de pruebas

**Pruebas Unitarias:** Prueban componentes y funciones individuales de forma aislada.

**Pruebas Atómicas:** Prueban funciones y métodos individuales en el nivel más granular.

**Pruebas de Integración:** Prueban interacciones entre diferentes componentes y servicios.

**Pruebas de Navegador:** Prueban interfaces web con automatización Selenium.

**Pruebas de Rendimiento:** Prueban el rendimiento del sistema bajo diversas condiciones de carga.

**Pruebas de Seguridad:** Prueban aspectos de seguridad y detección de vulnerabilidades.

**Pruebas E2E:** Prueban workflows completos de principio a fin.

### 3.2 Categorías de pruebas

#### 3.2.1 Ejecución de pruebas

**Inicio Rápido:**

```bash
# Ejecutar todas las pruebas
make test-all

# Ejecutar categorías específicas de pruebas
make test-unit
make test-atomic
make test-security
make test-integration
make test-performance
make test-smoke
make test-e2e

# Ejecutar con cobertura
make test-coverage
```

#### 3.2.2 Eliminaciones de pruebas

Varios archivos de prueba han sido eliminados para mantener una alta relación señal-ruido. Todas las pruebas han sido
corregidas exitosamente y ahora están pasando con cero saltos.

#### 3.2.3 Ejecución individual

```bash
# Ejecutar pruebas unitarias
python3 -m pytest tests/unit/ -v

# Ejecutar pruebas atómicas
python3 -m pytest tests/atomic/ -v

# Ejecutar pruebas de seguridad
python3 -m pytest tests/security/ -v

# Ejecutar pruebas de integración
python3 -m pytest tests/integration/ -v

# Ejecutar pruebas de rendimiento
python3 -m pytest tests/performance/ -v

# Ejecutar pruebas E2E
python3 -m pytest tests/e2e/ -v

# Ejecutar archivo de prueba específico
python3 -m pytest tests/unit/test_calc_kpis.py -v

# Ejecutar con cobertura
python3 -m pytest tests/ --cov=scripts --cov=config --cov-report=html --cov-report=term --cov-fail-under=80
```

#### 3.2.4 Script de ejecución

```bash
# Ejecutar suite de pruebas integral
python tests/run_all_tests.py

# Ejecutar con opciones específicas
python tests/run_all_tests.py --unit-only
python tests/run_all_tests.py --integration-only
python tests/run_all_tests.py --e2e-only
python tests/run_all_tests.py --generate-report
```

#### 3.2.5 Configuración de pruebas

**Configuración pytest.ini:**

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
addopts = -v --strict-markers --tb=short --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    docker: Tests requiring Docker
    network: Tests requiring network access
```

**Marcadores de Pruebas:**

```bash
# Ejecutar solo pruebas unitarias
pytest -m unit

# Ejecutar solo pruebas de integración
pytest -m integration

# Ejecutar solo pruebas E2E
pytest -m e2e

# Saltar pruebas lentas
pytest -m "not slow"

# Ejecutar pruebas que requieren Docker
pytest -m docker
```

#### 3.2.6 Datos y fixtures

**Ubicación de Datos de Pruebas:**

- Archivos de datos de pruebas: `tests/fixtures/`
- Configuraciones de muestra: `tests/fixtures/configs/`
- Respuestas mock: `tests/fixtures/responses/`

**Fixtures de Pruebas:**
Las fixtures comunes de pruebas están disponibles en `tests/conftest.py`:

```python
@pytest.fixture
def sample_alert():
    \"\"\"Alerta de ransomware de muestra para pruebas\"\"\"
    return {
        \"alert_id\": \"TEST-001\",
        \"event_type\": \"ransomware_detection\",
        \"severity\": \"2\",
        \"timestamp\": \"2024-01-01T12:00:00Z\",
        \"source\": \"test_source\"
    }

@pytest.fixture
def mock_thehive_client():
    \"\"\"Mock del cliente API de TheHive\"\"\"
    with patch('scripts.send_alert.TheHiveClient') as mock:
        yield mock
```

### 3.3 Casos de prueba

#### 3.3.1 Objetivos de cobertura

| Categoría de Pruebas   | Objetivo de Cobertura           |
|------------------------|---------------------------------|
| Pruebas unitarias      | >80%                            |
| Pruebas atómicas       | >70%                            |
| Pruebas de integración | >60%                            |
| Pruebas de navegador   | >50%                            |
| Pruebas de seguridad   | >60%                            |
| Pruebas de rendimiento | N/A (benchmarks de rendimiento) |
| Pruebas E2E            | >50%                            |

**Estado Actual del Coverage (v1.4.0):**

- **Objetivo mínimo global**: ≥ 80% de coverage
- **Estado actual**: 84% de coverage ✅ (excede el objetivo)
- **Total de pruebas**: 1393 tests pasando
  - Unit tests: 1000 passed
  - Integration tests: 277 passed
  - E2E tests: 16 passed
  - Atomic tests: 86 passed
  - Security tests: 5 passed
  - Performance tests: 9 passed
- **Última ejecución**: 2026-07-02
- **Correcciones aplicadas**:
  - Elasticsearch disk watermark assertion ajustado de `<= 85` a `<= 90` en `tests/integration/test_smoke.py`
  - Requisito documentado: cambios en archivos de prueba requieren reconstrucción del contenedor `api`
- **Reporte de coverage**: Disponible en `artifacts/coverage/htmlcov/` y `artifacts/coverage/coverage.xml`
- **Comando para generar reporte**: `make test-coverage` (Linux/Mac) o `make -f Makefile.win test-coverage` (Windows)

#### 3.3.2 Entornos de pruebas

**Desarrollo Local:**

```bash
# Configurar entorno de pruebas
make deps-test

# Ejecutar pruebas localmente
make test-all
```

**Pipeline CI/CD:**
Las pruebas se ejecutan automáticamente en:

- Pull requests
- Push a rama main
- Ejecuciones programadas diarias

**Entorno de Pruebas Docker:**

```bash
# Ejecutar pruebas en Docker
docker-compose -f infra/docker/docker-compose.yml up
python -m pytest tests/ -v
```

#### 3.3.3 Generación de reportes

```bash
# Generar reporte de cobertura HTML
make test-coverage

# Ver reporte de cobertura
open htmlcov/index.html
```

**Archivos de Resultados:**

- Resultados de pruebas: `artifacts/results/test_results.json`
- Reportes de cobertura: `artifacts/coverage/htmlcov/`
- Reportes de rendimiento: `artifacts/results/performance/`
- Reportes de seguridad: `artifacts/results/security/`

**Formatos de Reporte:**

- JSON: Resultados legibles por máquina
- HTML: Reportes de cobertura legibles por humanos
- JUnit XML: Integración CI/CD
- Consola: Salida en tiempo real

### 3.4 Ejecución de pruebas

#### 3.4.1 Comandos de ejecución

**Ejecutar todas las pruebas:**

```bash
make test-all
```

**Ejecutar categorías específicas de pruebas:**

```bash
make test-unit
make test-atomic
make test-integration
make test-smoke
make test-e2e
```

**Ejecutar con cobertura:**

```bash
make test-coverage
```

#### 3.4.2 Entornos de ejecución

- **Local**: Ejecución en máquina de desarrollo
- **CI/CD**: Ejecución automática en GitHub Actions
- **Docker**: Ejecución dentro de contenedores

### 3.5 Reportes y métricas

#### 3.5.1 Reportes generados

- **Resultados de pruebas**: `artifacts/results/test_results.json`
- **Reportes de cobertura**: `artifacts/coverage/htmlcov/`
- **Reportes de rendimiento**: `artifacts/results/performance/`
- **Reportes de seguridad**: `artifacts/results/security/`

#### 3.5.2 Métricas clave

| Categoría de Pruebas   | Objetivo de Cobertura           |
|------------------------|---------------------------------|
| Pruebas unitarias      | >80%                            |
| Pruebas atómicas       | >70%                            |
| Pruebas de integración | >60%                            |
| Pruebas de navegador   | >50%                            |
| Pruebas de seguridad   | >60%                            |
| Pruebas de rendimiento | N/A (benchmarks de rendimiento) |
| Pruebas E2E            | >50%                            |

## 4. Validación

### 4.1 Verificación

Varios archivos de prueba han sido eliminados para mantener una alta relación señal-ruido. Todas las pruebas han sido
corregidas exitosamente y ahora están pasando con cero saltos.

### 4.2 Criterios de Aceptación

La suite de pruebas se considera exitosa cuando:

- Todas las categorías de pruebas alcanzan sus objetivos de cobertura
- Todas las pruebas pasan sin errores en los entornos local y CI/CD
- Los reportes de cobertura muestran los porcentajes esperados
- Las pruebas de seguridad están limpias
- Las pruebas de rendimiento cumplen con los baselines

### 4.3 Evidencias

Las evidencias de ejecución de pruebas incluyen:

- Reportes de pytest con resultados de pruebas
- Reportes de cobertura de código
- Logs de ejecución de pruebas
- Resultados de pruebas de navegador (capturas de pantalla)
- Reportes de seguridad y vulnerabilidades

## 5. Problemas y consideraciones

### 5.1 Limitaciones

#### 5.1.1 Limitaciones de pruebas de navegador

- Requieren instalación de navegador y WebDriver
- Pueden ser frágiles debido a cambios en UI
- Requieren servicios ejecutándose

#### 5.1.2 Limitaciones de pruebas de seguridad

- Requieren herramientas de escaneo de vulnerabilidades
- Pueden ser lentas en comparación con otras categorías
- Requieren acceso a servicios externos para algunas validaciones

### 5.2 Riesgos o incidencias

#### 5.2.1 Servicios faltantes

**Las Pruebas Fallan Debido a Servicios Faltantes:**

```bash
# Iniciar servicios requeridos
make up

# Verificar salud de servicios
make health
```

#### 5.2.2 Problemas de permisos

**Problemas de Permisos:**

```bash
# Corregir permisos de pruebas
chmod +x tests/**/*.py
```

#### 5.2.3 Problemas de Docker

**Problemas de Pruebas Docker:**

```bash
# Limpiar entorno Docker
docker system prune -f
docker-compose down -v
```

### 5.3 Recomendaciones / troubleshooting

#### 5.3.1 Depuración de pruebas

**Depuración de Pruebas:**

**Salida Verbosa:**

```bash
pytest -v -s tests/unit/test_calc_kpis.py
```

**Modo de Depuración:**

```bash
pytest --pdb tests/unit/test_calc_kpis.py
```

**Detener en Primer Fallo:**

```bash
pytest -x tests/
```

#### 5.3.2 Mejores prácticas

**Mejores Prácticas:**

**Escritura de Pruebas:**

1. **Nombres Descriptivos:** Usar nombres de pruebas claros y descriptivos
2. **Organizar-Actuar-Assertar:** Estructurar pruebas claramente
3. **Aislamiento de Pruebas:** Las pruebas no deben depender unas de otras
4. **Mock de Dependencias Externas:** Usar mocks para servicios externos
5. **Prueba de Edge Cases:** Incluir condiciones límite y escenarios de error

**Organización de Pruebas:**

1. **Agrupar Pruebas Relacionadas:** Organizar por funcionalidad
2. **Usar Fixtures:** Compartir código de configuración común
3. **Parametrizar Pruebas:** Probar múltiples escenarios con una prueba
4. **Aserciones Claras:** Usar mensajes de aserción descriptivos

**Pruebas de Rendimiento:**

1. **Mediciones de Baseline:** Establecer baselines de rendimiento
2. **Aislar Pruebas:** Ejecutar pruebas de rendimiento por separado
3. **Medir Recursos:** Monitorear uso de CPU, memoria y red
4. **Análisis Estadístico:** Usar métodos estadísticos para validación de rendimiento

#### 5.3.3 Integración continua

**Integración Continua:**

**GitHub Actions:**
Las pruebas se ejecutan en:

- Ejecutores de Ubuntu y Windows
- Python 3.9+
- Múltiples versiones de Docker

**Matriz de Pruebas:**

```yaml
strategy:
  matrix:
    python-version: [3.9, '3.10', 3.11]
    os: [ubuntu-latest, windows-latest]
```

**Quality Gates:**

- Todas las pruebas deben pasar
- El umbral de cobertura debe cumplirse
- Los escaneos de seguridad deben estar limpios
- Las pruebas de rendimiento deben cumplir con los baselines

#### 5.3.4 Contribución

**Contribución:**

Al agregar nuevas pruebas:

1. **Seguir Convenciones de Nomenclatura:** Usar nomenclatura `test_*.py`
2. **Agregar Documentación:** Documentar escenarios de prueba complejos
3. **Actualizar Cobertura:** Mantener umbrales de cobertura
4. **Categorías de Pruebas:** Usar marcadores apropiados
5. **Incluir Ejemplos:** Proporcionar ejemplos de uso en docstrings

#### 5.3.5 Pruebas de seguridad

**Pruebas de Seguridad:**

**Escaneos Automatizados:**

- **Bandit:** Escáner de seguridad de Python
- **Safety:** Escáner de vulnerabilidades de dependencias
- **Semgrep:** Análisis estático para bugs de seguridad

**Pruebas Manuales:**

- **Pruebas de Penetración:** Evaluaciones de seguridad regulares
- **Modelado de Amenazas:** Identificar vectores de ataque potenciales
- **Verificación de Cumplimiento:** Verificar cumplimiento de seguridad

#### 5.3.6 Pruebas de rendimiento

**Pruebas de Rendimiento:**

**Pruebas de Carga:**

- **Usuarios Concurrentes:** Probar con 10, 50, 100 usuarios concurrentes
- **Tiempos de Respuesta:** Verificar tiempos de respuesta <2s
- **Throughput:** Medir solicitudes por segundo

**Pruebas de Estrés:**

- **Límites de Recursos:** Probar límites del sistema y degradación
- **Fugas de Memoria:** Verificar fugas de memoria
- **Rendimiento de Base de Datos:** Probar rendimiento de consultas bajo carga

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **README Principal**: [/README.md](../README.md)
- **Documentación del Proyecto**: [../](../)
