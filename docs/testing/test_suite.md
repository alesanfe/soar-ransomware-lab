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
        - [3.1.3 Recuento de casos recogidos](#313-recuento-de-casos-recogidos)
        - [3.1.4 Variables de entorno requeridas](#314-variables-de-entorno-requeridas)
    - [3.2 Categorías de pruebas](#32-categorías-de-pruebas)
        - [3.2.1 Ejecución de pruebas](#321-ejecución-de-pruebas)
        - [3.2.2 Eliminaciones de pruebas](#322-eliminaciones-de-pruebas)
        - [3.2.3 Ejecución individual](#323-ejecución-individual)
        - [3.2.4 Script de ejecución](#324-script-de-ejecución)
        - [3.2.5 Configuración de pruebas](#325-configuración-de-pruebas)
        - [3.2.6 Datos y fixtures](#326-datos-y-fixtures)
        - [3.2.7 Tests de autenticación JWT](#327-tests-de-autenticación-jwt)
    - [3.3 Casos de prueba](#33-casos-de-prueba)
        - [3.3.1 Objetivos de cobertura](#331-objetivos-de-cobertura)
        - [3.3.2 Entornos de pruebas](#332-entornos-de-pruebas)
        - [3.3.3 Generación de reportes](#333-generación-de-reportes)
    - [3.4 Ejecución de pruebas](#34-ejecución-de-pruebas)
        - [3.4.1 Comandos de ejecución](#341-comandos-de-ejecución)
        - [3.4.2 Entornos de ejecución](#342-entornos-de-ejecución)


        - [3.4.3 Ejecución remota vía `PytestTestRunner`](#343-ejecución-remota-vía-pytesttestrunner)
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

**Estado Actual:**

```
tests/
├── unit/                    # 66 archivos de pruebas unitarias (test_*.py)
├── atomic/                  # 4 archivos de pruebas atómicas
├── integration/             # 36 archivos de pruebas de integración
├── e2e/                     # 44 archivos de pruebas E2E
├── performance/             # 4 archivos de pruebas de rendimiento
├── security/                # 1 archivo de pruebas de seguridad
├── general/                 # 2 archivos de utilidades generales
├── fixtures/                # Datos de prueba compartidos
├── runners/                 # Scripts de ejecución de suites
├── conftest.py              # Configuración global de Pytest
└── __init__.py
```

**Conteo total de archivos `test_*.py`:** 158 archivos.

> **Nota:** No existe `tests/smoke/` como directorio; los tests marcados `smoke` se encuentran en `tests/integration/test_smoke.py` y mediante el marcador `smoke` de pytest.

**Nota:** Los tests unitarios cubren `src/soar_lab/` de forma aislada; los E2E validan workflows completos del playbook
Shuffle, TheHive, Cortex, MISP y Wazuh; las pruebas de integración verifican adaptadores y servicios del dominio.

#### 3.1.2 Categorías de pruebas

**Pruebas Unitarias:** Prueban componentes y funciones individuales de forma aislada.

**Pruebas Atómicas:** Prueban funciones y métodos individuales en el nivel más granular.

**Pruebas de Integración:** Prueban interacciones entre diferentes componentes y servicios.

**Pruebas de Navegador:** Prueban interfaces web con automatización Selenium.

**Pruebas de Rendimiento:** Prueban el rendimiento del sistema bajo diversas condiciones de carga.

**Pruebas de Seguridad:** Prueban aspectos de seguridad y detección de vulnerabilidades.

**Pruebas E2E:** Prueban workflows completos de principio a fin.

#### 3.1.3 Recuento de casos recogidos

El recuento exacto depende de la versión actual del código. El inventario detallado se encuentra en `baseline/tests_inventory.json`. Para obtener el recuento reproducible en cualquier entorno:

```bash
python -m pytest --collect-only -q
```

**Conceptos de recuento:**

- `collected`: todos los casos encontrados por `pytest`.
- `deselected`: casos filtrados por los marcadores de `pytest.ini` (por defecto `-m "not requires_docker"`).
- `selected`: casos que finalmente se ejecutarían.
- `skipped`: casos que se omiten en runtime por dependencias no disponibles.

> Para actualizar el inventario o validar el recuento, ejecutar el comando anterior y comparar con `baseline/tests_inventory.json`.

#### 3.1.4 Variables de entorno requeridas

La suite usa `tests/conftest.py` para fijar unas variables mínimas y delega las credenciales operativas a `.env.full` (cuando existe) o a los overrides del entorno de ejecución.

**Variables internas (fijadas por `conftest.py`):**

| Variable | Propósito | Ejemplo / Origen |
|----------|-----------|------------------|
| `BASE_DIR` | Raíz del repositorio para `Settings()` | `<repositorio>` |
| `SOAR_SKIP_EAGER_INIT` | Evita la creación temprana de la app FastAPI durante la recogida de tests | `1` |

**Variables operativas (esperadas en `.env.full` o `docker exec -e`):**

| Variable | Servicio / Uso | Notas |
|----------|----------------|-------|
| `SHUFFLE_DEFAULT_APIKEY` | Cliente Shuffle API | Obligatorio para tests E2E contra Shuffle |
| `SHUFFLE_DEFAULT_PASSWORD` | Autenticación admin Shuffle | Solo necesario si se regeneran credenciales |
| `THEHIVE_API_KEY` | Cliente TheHive API | Obligatorio para tests E2E |
| `CORTEX_API_KEY` | Cliente Cortex API | Obligatorio para tests E2E |
| `MISP_API_KEY` | Cliente MISP API | Obligatorio para tests E2E |
| `WAZUH_API_USER` | API de Wazuh Manager | Valor por defecto en `.env.example` |
| `WAZUH_API_PASSWORD` | API de Wazuh Manager | Requiere mayúsculas, minúsculas, números y un carácter especial permitido |
| `REDIS_PASSWORD` | Conexión Redis / Shuffle | Se escapa en conexiones `redis://` |
| `ELASTIC_PASSWORD` | Elasticsearch + Grafana datasource | También usado por `E2E` para indexar métricas |
| `JWT_SECRET_KEY` | Firma/validación de tokens JWT | `>=32` caracteres; el `conftest.py` usa un secreto de prueba si no existe |

> **Seguridad:** No se deben incluir valores reales en este documento. Las credenciales se cargan desde `.env.full` y se tratan como secretos. Para ejecuciones locales se recomienda usar `cp .env.example .env.full` y ejecutar `make generate-secrets` / `soar-lab generate-secrets`.

#### 3.1.5 Flujo real y recomendado de pruebas

El flujo canónico en un entorno local utiliza los targets `make` definidos en `Makefile.linux` / `Makefile.win`. No se recomienda ejecutar `pytest` directamente sin el entorno y perfiles Docker correctos.

```bash
# 1. Generar secretos e IOCs previos a los tests
make generate-secrets
make generate-iocs

# 2. Limpiar entorno previo (volúmenes, contenedores, redes y artefactos)
make reset

# 3. Levantar el stack completo
make up

# 4. Verificar salud de los servicios antes de lanzar tests de integración/E2E
make health

# 5. Ejecutar tests según la categoría
make test-unit          # No requiere Docker (usa mocks)
make test-atomic
make test-integration   # Requiere stack completo levantado y saludable
make test-smoke         # Requiere stack mínimo post-deploy
make test-e2e           # Requiere stack completo y Shuffle configurado
make test-performance
make test-security
make test-all           # Requiere stack completo y saludable

# 6. Generar cobertura y reportes
make test-coverage
```

**Targets Make disponibles:**

| Target | Requiere Docker | Descripción |
|--------|-----------------|-------------|
| `make test` (sin alias) | No* | Equivalente a `pytest` base; evitar en flujo operativo |
| `make test-unit` | No | Ejecuta `tests/unit/`; no requiere servicios |
| `make test-atomic` | No | Ejecuta `tests/atomic/` |
| `make test-integration` | Sí | Ejecuta `tests/integration/`; requiere `make up` y `make health` |
| `make test-smoke` | Sí | Ejecuta tests marcados `smoke`; validación rápida post-deploy |
| `make test-e2e` | Sí | Ejecuta `tests/e2e/`; requiere todos los servicios y el workflow Shuffle |
| `make test-performance` | Sí | Ejecuta `tests/performance/` |
| `make test-security` | No/Sí* | Ejecuta `tests/security/`; algunos casos escanean dependencias |
| `make test-all` | Sí | Ejecuta todas las categorías; requiere stack completo |
| `make test-coverage` | Sí (para E2E/integración) | Genera reporte HTML/XML de cobertura en `artifacts/coverage/` |

> *`make test-security` puede ejecutar análisis estático sin Docker; los tests de seguridad del repositorio requieren el entorno de Python.

**Prerrequisitos por categoría:**

- **Unit / Atomic**: Python 3.11+, dependencias de desarrollo (`make deps-test`), `.env.full` con placeholders o secretos.
- **Integración / E2E / Smoke / Performance**: Stack Docker levantado (`make up`), `make health` exitoso, `.env.full` con credenciales reales, workflow Shuffle inicializado (`make init-webhook`), índices `soar-metrics` disponibles.

**Control previo en CI:**

```bash
# Asegurar que pytest puede recolectar todos los tests sin errores de importación
python -m pytest --collect-only -q

# Control de calidad de documentación
make docs-lint
```

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

#### 3.2.2 Eliminaciones y omisiones

Varios archivos de prueba obsoletos han sido eliminados para mantener una alta relación señal-ruido. Algunas pruebas usan
`pytest.skip` en runtime cuando faltan dependencias externas (Docker, servicios SOAR levantados, API keys, workflow
creado) o cuando se ejecutan dentro de un contenedor sin acceso al código/host. Esto se refleja en el recuento final de
`pytest` como `skipped`, no como `error`.

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
python3 -m pytest tests/ --cov=src/soar_lab --cov-report=html --cov-report=term --cov-fail-under=80
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

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "requires_docker: marks tests that require Docker to be running",
    "requires_external: marks tests that depend on external services (TheHive, Cortex, Shuffle, etc.)",
    "e2e: marks end-to-end tests that may take longer to run",
    "unit: marks unit tests that don't require external dependencies",
    "integration: marks integration tests that require multiple components",
    "atomic: marks atomic red-team simulation tests",
    "performance: marks performance and load tests",
    "security: marks security hardening and vulnerability tests",
    "kpi: marks KPI-related tests",
    "smoke: fast post-deployment smoke tests",
    "smoke_critical: P0 — rollback immediately if these fail",
    "smoke_high: P1 — investigate immediately, consider rollback",
    "smoke_medium: P2 — degraded platform, investigate within 24h",
]
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
pytest -m requires_docker

# Ejecutar pruebas que requieren servicios externos levantados
pytest -m requires_external
```

> **Conceptos de recuento**: `collected` son todos los casos encontrados; `deselected` los filtrados por `-m`; `selected` los que finalmente se ejecutarán. `skipped` aparece cuando una prueba llama a `pytest.skip` en runtime (por ejemplo, falta de servicio externo o ejecución dentro del contenedor). `xfail` indica un caso marcado como fallo esperado; en este repositorio no se usa `xfail` de forma masiva, pero puede existir en pruebas experimentales.

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

#### 3.2.7 Tests de autenticación JWT

Los tests del proveedor JWT y del servicio de autenticación se encuentran en:

- `tests/unit/infrastructure/test_jwt_token_provider.py`
- `tests/integration/test_authorization.py`

**Escenarios cubiertos por `test_jwt_token_provider.py`:**

| Escenario | Entrada esperada | Comportamiento validado |
|-----------|------------------|-------------------------|
| Creación exitosa | `username`, secret `>= 32` chars, `expiration_minutes=60`, algoritmo `HS256` | Token JWT no vacío y verificable |
| Secret corto | secret `short` (menos de 32 chars) | `python-jose` permite crear el token; la validación de longitud se delega a `AuthService` |
| Verificación exitosa | Token creado con el mismo secret | Payload con `user`, `method=jwt` y `exp` |
| Token inválido | Cadena aleatoria | `AuthError` con mensaje de credenciales inválidas |
| Secret incorrecto | Token firmado con `secret1`, verificado con `secret2` | `AuthError` |
| Expiración personalizada | `expiration_minutes=120` | Token verificable y payload correcto |
| Algoritmo inválido | `INVALID_ALGORITHM` | `AuthError` "Failed to create authentication token" |
| Payload sin `sub` | Token sin claim `sub` | `AuthError` "Invalid token payload" |
| Token expirado | `exp` en el pasado | `AuthError` "Invalid authentication credentials" |

**Algoritmo y expiración canónicos:**

- Algoritmo: `HS256` (`src/soar_lab/config/settings.py` → `JWT_ALGORITHM`).
- Expiración por defecto: `60` minutos (`JWT_EXPIRATION_MINUTES`).
- Secret canónico: `JWT_SECRET_KEY`; fallback legacy `API_AUTH_SECRET`.
- Longitud mínima de secret: `32` caracteres (validada en `src/soar_lab/application/use_cases/auth_service.py`).

**Ejecución:**

```bash
python -m pytest tests/unit/infrastructure/test_jwt_token_provider.py -v
python -m pytest tests/integration/test_authorization.py -v
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

**Estado Actual del Suite (v1.4.0):**

- **Python soportado**: `>=3.11` (declarado en `pyproject.toml`; CI y entorno de desarrollo usan 3.11.x).
- **Objetivo mínimo global**: ≥ 80% de cobertura.
- **Inventario de tests**: `baseline/tests_inventory.json` (actualizado mediante `pytest --collect-only`); para el recuento real ejecutar:

  ```bash
  python -m pytest --collect-only -q
  ```

  > El recuento exacto depende de la versión actual del código, parametrizaciones y entorno. Los conteos detallados por directorio se encuentran en `baseline/tests_inventory.json`.

- **Ejecución real (`pytest -q`)**: el número de `passed`/`failed`/`skipped`/`error` depende del entorno. Con los servicios levantados la mayoría de E2E e integración pasan; sin servicios externos se observan `skipped` en tests marcados con `requires_external` o `requires_docker`.

- **Restricciones de plataforma**: algunas pruebas de Docker e integración se omiten si no se detecta el socket de Docker (`/var/run/docker.sock` o equivalente) o si se ejecutan dentro de un contenedor sin acceso al repo/host. En Windows se recomienda ejecutar pruebas E2E e integración con Docker Desktop activo.

- **Smoke tests**: marcador `smoke` de pytest; archivo principal `tests/integration/test_smoke.py`.
- **Reporte de coverage**: `artifacts/coverage/htmlcov/` y `artifacts/coverage/coverage.xml`.
- **Comando para generar reporte**: `make test-coverage` (Linux/Mac) o `make -f Makefile.win test-coverage` (Windows).

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
docker compose --env-file .env.full -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml up -d
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

#### 3.3.4 Smoke tests y cobertura histórica

**Smoke tests (`pytest -m smoke`)**

- Valoran la salud mínima del despliegue después de `make up`.
- Marcadores: `smoke`, `smoke_critical`, `smoke_high`, `smoke_medium`.
- Ejecución: `make test-smoke` o `pytest -m smoke`.
- Cubren endpoints críticos como `GET /health`, `GET /services/status`, login y el webhook de Shuffle.

**Cobertura histórica en SQLite**

- Los resultados históricos de cobertura se almacenan en `artifacts/coverage/history.db` (o similar en SQLite) para comparar
  evolución entre despliegues.
- `make test-coverage` genera tanto el reporte HTML como la métrica consolidada.
- El CLI `soar-lab` y el dashboard de `web-management` pueden consultar los datos de cobertura actuales via API.

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
- **Remoto vía API / Web Management**: La API SOAR expone `POST /tests/run` que delega en `PytestTestRunner`
  (`src/soar_lab/infrastructure/pytest_test_runner.py`).

#### 3.4.3 Ejecución remota vía `PytestTestRunner`

`PytestTestRunner` es el adaptador de infraestructura que encapsula la ejecución de `pytest`:

- Ubicación: `src/soar_lab/infrastructure/pytest_test_runner.py`
- Métodos: `run_suite(category, coverage)` (síncrono) y `run_suite_async(category, coverage)` (para FastAPI).
- Categorías soportadas: `unit`, `integration`, `e2e`, `atomic`, `performance`, `security`, `smoke`, `all`.
- Timeout por defecto: 300 s. Ajustable en la inyección del `CompositionRoot`.
- Cobertura: si `coverage=True`, añade `--cov=src/soar_lab --cov-report=json`.
- Resultados: se devuelven como JSON con `status`, `output`, `error`, `duration` y `returncode`.

Ejemplo de uso desde el panel Web Management o cURL:

```bash
# Obtener token JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<WEB_UI_PASSWORD>"}' | jq -r '.access_token')

# Lanzar suite E2E
curl -s -X POST http://localhost:8000/tests/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"e2e","coverage":false}'
```

> **Nota:** La ejecución remota requiere que el contenedor `soar_api` tenga acceso al socket/código y a las variables
> de entorno de `.env.full`. Para tests E2E e integración, los servicios Docker deben estar levantados.

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

La suite ha sido depurada de referencias a módulos heredados y errores de sintaxis. `pytest --collect-only` finaliza sin errores de importación (`0 errors`). Los conteos se actualizan de forma reproducible con `baseline/tests_inventory.json`.

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
docker compose down -v
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
- Python 3.11
- Múltiples versiones de Docker

**Matriz de Pruebas:**

```yaml
strategy:
  matrix:
    python-version: [3.11]
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

#### 5.3.7 Tests fallan por servicios no listos, recursos insuficientes o Docker Desktop

**Síntoma:**
Tests de integración/E2E fallan con `ConnectionRefusedError`, `skipped`, timeouts o `docker.errors.DockerException`.

**Causas probables y soluciones:**

1. **Servicios no listos:**
   - Ejecutar `make health` antes de tests. No basta con `docker compose ps` (contenedor en ejecución != servicio listo).
   - Verificar logs: `docker compose logs <servicio>`.
   - Aumentar `HEALTHCHECK` esperas si los servicios arrancan lentamente.

2. **Recursos insuficientes:**
   - Asignar al menos 8 GB de RAM y 4 vCPU a Docker Desktop / WSL.
   - Wazuh y Elasticsearch requieren varios GB. Si hay `OOMKilled`, aumentar memoria o limitar `OPENSEARCH_JAVA_OPTS` / `ES_JAVA_OPTS`.

3. **Docker Desktop / WSL en Windows:**
   - Activar integración de WSL2 y file sharing para el directorio del repo.
   - Usar PowerShell o WSL; en `cmd` puede fallar la interpretación de variables `$(...)`.
   - Si `make` no está disponible en Windows, usar `Makefile.win`: `make -f Makefile.win <target>` o ejecutar comandos equivalentes manualmente.

4. **Variables de entorno o `.env.full` ausentes:**
   - Asegurar `cp .env.example .env.full` y regenerar secretos: `make generate-secrets`.
   - Tras `make reset`, `make init-webhook` puede cambiar `SHUFFLE_DEFAULT_APIKEY`; actualizar `.env.full` o confiar en el self-heal de `ShuffleClient`.

5. **Contenedores sin acceso al socket de Docker:**
   - Algunos tests `requires_docker` necesitan acceso al socket (`/var/run/docker.sock`). En Windows/WSL montar el socket correctamente o ejecutar esos tests desde el host.

## 5.4 Matriz de incongruencias (FASE 49)

Se mantiene la matriz de incongruencias detectadas entre documentación, código, infraestructura y tests en [`docs/project/inconsistency_matrix.md`](../project/inconsistency_matrix.md).

Los puntos principales son:

- `.env.full` sigue en el historial de Git (no se purga por decisión del usuario).
- Algunos `docker-compose` y scripts de mantenimiento conservan valores fallback para contraseñas; deben prevalecer las variables de `.env.full`.
- Tests unitarios usan contraseñas dummy (aceptable con mocks), pero tests de integración deben evitar secrets hardcodeados.
- `grafana-datasources.yml` generado en runtime está en `.gitignore`; el template usa placeholders.

## 6. Gobernanza del backlog y evidencias (FASEs 54–65)

- El plan consolidado de trazabilidad, gobernanza, validación reproducible, arquitectura, seguridad, API, Docker, observabilidad, testing y cierre se encuentra en [`docs/project/governance_and_validation_plan.md`](../project/governance_and_validation_plan.md).
- Plantilla de manifiesto de evidencias y convención de retención definidas en ese documento.
- Registro de decisiones documentales y checklist de privacidad antes de publicar artefactos.

## 7. Arquitectura hexagonal

- `tests/architecture/test_hexagonal_imports.py` valida que `src/soar_lab/domain` no importe `infrastructure`, `interfaces`, `application`, `scripts`, etc.
- Marcador registrado en `pytest.ini`: `pytest -m architecture`.

## 8. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Plan de Gobernanza y Validación**: [../project/governance_and_validation_plan.md](../project/governance_and_validation_plan.md)
- **README Principal**: [/README.md](../README.md)
- **Documentación del Proyecto**: [../](../)
