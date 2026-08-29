# Testing — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
 - [1.1 Objetivo](#11-objetivo)
 - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
 - [2.1 Qué cubre](#21-qué-cubre)
 - [2.2 Límites](#22-límites)
 - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
 - [3.1 Estrategia general de pruebas](#31-estrategia-general-de-pruebas)
 - [3.2 Suite de pruebas](#32-suite-de-pruebas)
 - [3.3 Pruebas unitarias](#33-pruebas-unitarias)
 - [3.4 Pruebas de integración](#34-pruebas-de-integración)
 - [3.5 Pruebas E2E](#35-pruebas-e2e)
 - [3.6 Pruebas con Docker](#36-pruebas-con-docker)
 - [3.7 Ejecución y evidencias](#37-ejecución-y-evidencias)
 - [Anexo: Estrategia de Testing Consolidada](#anexo-estrategia-de-testing-consolidada)
  - [E.1 a E.13: 2233 tests, pirámide, quality gates, mutation testing](#e1-visión-general)
- [4. Validación](#4-validación)
 - [4.1 Verificación](#41-verificación)
 - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
 - [4.3 Evidencias](#43-evidencias)
- [5. Problemas](#5-problemas)
 - [5.1 Limitaciones](#51-limitaciones)
 - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
 - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones-troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Documentar la estrategia de pruebas, la suite completa y los diferentes niveles de testing del SOAR Ransomware Lab.

### 1.2 Contexto

El proyecto cuenta con 2233 tests coleccionados (1905 seleccionados, 328 deselected) organizados en unit, integration, atomic, e2e, architecture, contracts, security, performance y quality.

---

## 2. Alcance

### 2.1 Qué cubre

- Estrategia general de pruebas
- Pruebas unitarias, de integración y E2E
- Estrategia de testing con Docker
- Ejecución y evidencias

### 2.2 Límites

- No cubre arquitectura (ver 02-architecture.md)
- No cubre operaciones (ver 04-operations.md)

### 2.3 Dependencias

- `pyproject.toml` — configuración de pytest
- `tests/` — suite de pruebas
- `Makefile.win` / `Makefile.linux` — targets de test

---

## 3. Contenido principal

### 3.1 Estrategia general de pruebas

Este directorio contiene la suite completa de tests para el proyecto SOAR Ransomware Lab.

#### Estado actual de la suite

- **Python soportado**: `>=3.11` (declarado en `pyproject.toml`).
- **Comando canónico**: `python -m pytest --collect-only -q`
- **Inventario detallado**: [`tests/baseline/tests_inventory.json`](../tests/baseline/tests_inventory.json)
- **Generación de recuentos**: ejecutar `python -m pytest --collect-only -q` para obtener el recuento actual. Último resultado: `collected 2233 items / 328 deselected / 1905 selected`.

#### Pirámide de calidad

```
 E2E (pocos, lentos)
 Integración (algunos, servicios reales)
 Unitario / Atómico (muchos, rápidos)
```

- **Unit / Atomic**: rápidos, sin dependencias externas, se ejecutan con `make test-unit` / `make test-atomic`.
- **Integración**: validan adaptadores y servicios contra contenedores reales (`make test-integration`).
- **E2E / Smoke**: validan workflows completos del playbook (`make test-e2e`, `make test-smoke`).
- **Rendimiento / Seguridad**: tests específicos con infraestructura dedicada (`make test-performance`, `make test-security`).

#### Flujo canónico de ejecución

```bash
# 1. Preparar credenciales y datos de prueba
make generate-secrets
make generate-iocs

# 2. Limpiar y levantar el stack
make reset
make up

# 3. Verificar salud antes de tests que requieren Docker
make health

# 4. Ejecutar tests por categoría
make test-unit # No requiere Docker
make test-integration # Requiere stack levantado
make test-smoke
make test-e2e
make test-all # Requiere stack completo
```

#### Estructura de Tests

```
tests/
├── atomic/ # Tests atómicos
├── integration/ # Tests de integración
├── unit/ # Tests unitarios
├── performance/ # Tests de rendimiento
├── security/ # Tests de seguridad
├── general/ # Utilidades generales
├── e2e/ # Tests end-to-end
├── fixtures/ # Datos de test compartidos
└── runners/ # Scripts de ejecución de tests
```

> Para recuentos reales, consultar `tests/baseline/tests_inventory.json` o ejecutar `python -m pytest --collect-only -q`.

#### Ejecución de Tests

#### Comandos canónicos con Make

```bash
# Ejecutar tests unitarios (no requieren Docker)
make test-unit

# Ejecutar tests de integración (requiere make up + make health)
make test-integration

# Ejecutar tests E2E
make test-e2e

# Ejecutar smoke tests
make test-smoke

# Ejecutar todos los tests (requiere stack completo)
make test-all

# Ejecutar con cobertura
make test-coverage
```

#### Ejecutar con pytest directo

```bash
# Tests unitarios
pytest tests/unit/ -v

# Tests de integración
pytest tests/integration/ -v

# Tests de rendimiento
pytest tests/performance/ -v

# Tests de seguridad
pytest tests/security/ -v

# Tests atómicos
pytest tests/atomic/ -v

# Tests E2E
pytest tests/e2e/ -v

# Todos los tests con cobertura
pytest tests/ --cov=src/soar_lab --cov-report=html --cov-report=term
```

> **Nota:** `pytest` directo no es el flujo recomendado para tests que requieren Docker o variables de entorno del stack. Los targets `make` configuran `.env.full`, perfiles de Compose y demás prerequisitos. Usar `make test-*` salvo para desarrollo aislado.

#### Ejecutar tests específicos

```bash
pytest tests/atomic/test_alert_validation.py -v
pytest tests/atomic/test_alert_validation.py::TestAlertValidator::test_validate_structure -v
```

#### Ejecutar por marcadores

```bash
# Solo tests unitarios
pytest tests/ -m unit -v

# Solo tests de integración
pytest tests/ -m integration -v

# Solo tests que requieren servicios en vivo
pytest tests/ -m live -v

# Solo tests que pueden ejecutarse offline
pytest tests/ -m offline -v
```

#### Marcadores de pytest

- `unit`: Tests unitarios (sin dependencias externas)
- `integration`: Tests de integración (requieren servicios externos)
- `e2e`: Tests end-to-end (sistema completo)
- `performance`: Tests de rendimiento
- `security`: Tests de seguridad
- `live`: Tests que requieren servicios en vivo
- `offline`: Tests que pueden ejecutarse sin servicios externos
- `smoke`: Tests de smoke (validación rápida)
- `regression`: Tests de regresión

#### Requisitos

#### Para tests unitarios y atómicos

- Python 3.11+
- pytest
- pytest-cov (opcional, para coverage)

#### Para tests de integración

- Todos los requisitos anteriores
- Servicios Docker en ejecución:
 - Elasticsearch
 - MISP
 - TheHive
 - Shuffle

#### Para tests E2E

- Todos los requisitos anteriores
- Configuración completa del entorno (ver `.env.example`)

#### Configuración

Los tests utilizan el archivo `.env.full` para configuración. Asegúrate de:

1. Copiar `.env.example` a `.env.full`
2. Configurar las credenciales de los servicios
3. Asegurarse de que los servicios Docker estén en ejecución

#### Fixtures Compartidos

El archivo `tests/conftest.py` en el directorio raíz de tests contiene fixtures compartidos:

- `sample_alert`: Alerta de ejemplo
- `sample_malicious_alert`: Alerta maliciosa de ejemplo
- `sample_benign_alert`: Alerta benigna de ejemplo
- `sample_ioc_package`: Paquete IOC de ejemplo
- `sample_misp_event`: Evento MISP de ejemplo
- `sample_workflow_data`: Datos de workflow de ejemplo
- `sample_metrics_data`: Datos de métricas de ejemplo
- `mock_elasticsearch_client`: Cliente Elasticsearch mockeado
- `mock_thehive_client`: Cliente TheHive mockeado
- `mock_misp_client`: Cliente MISP mockeado
- `mock_shuffle_client`: Cliente Shuffle mockeado

#### Pirámide de calidad (resumen de tipos)

| Nivel | Tipo | Qué valida | Ejecución canónica |
|---|---|---|---|
| Unitarios | `tests/unit/` | Funciones, modelos, utilidades sin dependencias externas | `pytest tests/unit/ -v` |
| Atómicos | `tests/atomic/` | Componentes individuales con mocks | `pytest tests/atomic/ -v` |
| Integración | `tests/integration/` | Interacción entre adaptadores y clientes | `pytest tests/integration/ -v` |
| Seguridad | `tests/security/` | Validación de secretos, permisos, entradas maliciosas | `pytest tests/security/ -v` |
| Rendimiento | `tests/performance/` | Latencia, carga, benchmarks | `pytest tests/performance/ -v` |
| E2E | `tests/e2e/TC-*` | Flujo completo del playbook con servicios en ejecución | `pytest tests/e2e/ -v` |
| Smoke | marcadores `smoke*` | Salud mínima tras despliegue | `pytest -m smoke -v` |

No se incluyen conteos estáticos. Para conocer el estado actual:

```bash
# Linux/macOS
pytest --collect-only -q | grep -c "::"

# Windows
pytest --collect-only -q | find /c /v ""
```

Para obtener el desglose por categoría, usa los marcadores de `pyproject.toml`:

```bash
pytest --collect-only -q -m unit
pytest --collect-only -q -m integration
pytest --collect-only -q -m e2e
```

#### Scripts de Ejecución

El directorio `runners/` contiene scripts personalizados para ejecución de tests:

- `pytest_runner.py`: Runner personalizado con reportes detallados
- `run_e2e_tests.sh`: Ejecuta un caso E2E dentro del contenedor `soar_api`

#### Coverage

Para asegurar la calidad del código, mantenemos un mínimo de coverage:

- **Coverage general**: 70%
- **Funciones críticas**: 80%
- **Funciones de seguridad**: 90%

#### Mutation Testing

Para verificar la calidad de los tests, utilizamos mutation testing:

- **Score mínimo**: 70%
- **Funciones críticas**: 80%
- **Funciones de seguridad**: 90%

#### Solución de Problemas

#### Tests fallan por credenciales

Verifica que `.env.full` esté configurado correctamente con las credenciales de los servicios.

#### Tests fallan por servicios no disponibles

Asegúrate de que los servicios Docker estén en ejecución:

```bash
docker compose ps
```

#### Tests de integración fallan

Verifica la conectividad a los servicios:

```bash
docker compose logs
```

#### Contribución

Al añadir nuevos tests:

1. Sigue la estructura de directorios existente
2. Usa fixtures compartidos cuando sea posible
3. Añade docstrings claros
4. Usa marcadores apropiados
5. Mantén el coverage mínimo


### 3.2 Suite de pruebas


Suite de pruebas integral para el proyecto SOAR Ransomware Lab, cubriendo pruebas unitarias, de integración, de
rendimiento, de seguridad y de extremo a extremo (E2E).


La suite de pruebas valida todos los componentes del sistema SOAR Ransomware Lab, incluyendo APIs, workflows de
automatización, integraciones de servicios y rendimiento bajo carga.


Este documento cubre:

- Estructura y organización de la suite de pruebas
- Categorías de pruebas (unitarias, atómicas, integración, navegador, rendimiento, seguridad, E2E)
- Ejecución de pruebas (comandos, cobertura, ejecutores de pruebas)
- Configuración de pruebas (pytest.ini, marcadores, fixtures)
- Entornos de pruebas (local, CI/CD, Docker)
- Mejores prácticas y solución de problemas


Este documento no cubre:

- Estrategia detallada de pruebas de Docker (ver [3.6 Pruebas con Docker](#36-pruebas-con-docker))
- Arquitectura detallada del sistema (ver docs/02-architecture.md)
- Planificación del proyecto (ver docs/06-project-management.md)


Este documento depende de:

- Estrategia de pruebas de Docker ([3.6 Pruebas con Docker](#36-pruebas-con-docker))
- Documentación de arquitectura (docs/02-architecture.md)
- Documentación de Docker (docs/02-architecture.md)
- Guía de usuario (docs/01-getting-started.md)


#### 3.2.1 Estructura de pruebas

##### 3.2.1.1 Estructura de directorios

**Estado Actual:**

```
tests/
├── unit/          # 79 archivos de pruebas unitarias (test_*.py)
├── atomic/        # 4 archivos de pruebas atómicas
├── integration/   # 30 archivos de pruebas de integración
├── e2e/           # 48 archivos de pruebas E2E (TC-00..TC-33, TC-KPI-01..06)
├── architecture/  # 1 archivo de tests de arquitectura
├── performance/   # 4 archivos de pruebas de rendimiento
├── security/      # 1 archivo de pruebas de seguridad
├── quality/       # 14 archivos de tests de calidad
├── general/       # 2 archivos de utilidades generales
├── baseline/      # Inventario de tests (tests_inventory.json)
├── contracts/     # Tests de contratos
├── reports/       # Tests de reportes
├── runners/       # Scripts de ejecución de suites
├── runtime/       # Tests de runtime
├── conftest.py    # Configuración global de pytest
└── __init__.py
```

**Conteo total de archivos `test_*.py`:** 184 archivos.

> **Nota:** `tests/e2e/` SÍ existe como directorio con 48 archivos organizados por test case (TC-00..TC-33, TC-KPI-01..06). Los tests marcados `smoke` se encuentran además en `tests/integration/test_smoke.py` y mediante el marcador `smoke` de pytest.

**Nota:** Los tests unitarios cubren `src/soar_lab/` de forma aislada; los E2E validan workflows completos del playbook
Shuffle, TheHive, Cortex, MISP y Elasticsearch; las pruebas de integración verifican adaptadores y servicios del dominio.

##### 3.2.1.2 Categorías de pruebas

**Pruebas Unitarias:** Prueban componentes y funciones individuales de forma aislada.

**Pruebas Atómicas:** Prueban funciones y métodos individuales en el nivel más granular.

**Pruebas de Integración:** Prueban interacciones entre diferentes componentes y servicios.

**Pruebas de Navegador:** Prueban interfaces web con automatización Selenium.

**Pruebas de Rendimiento:** Prueban el rendimiento del sistema bajo diversas condiciones de carga.

**Pruebas de Seguridad:** Prueban aspectos de seguridad y detección de vulnerabilidades.

**Pruebas E2E:** Prueban workflows completos de principio a fin.

##### 3.2.1.3 Recuento de casos recogidos

El recuento exacto depende de la versión actual del código. El inventario detallado se encuentra en `tests/baseline/tests_inventory.json`. Para obtener el recuento reproducible en cualquier entorno:

```bash
python -m pytest --collect-only -q
```

**Conceptos de recuento:**

- `collected`: todos los casos encontrados por `pytest`.
- `deselected`: casos filtrados por los marcadores de `pytest.ini` (por defecto `-m "not requires_docker"`).
- `selected`: casos que finalmente se ejecutarían.
- `skipped`: casos que se omiten en runtime por dependencias no disponibles.

> Para actualizar el inventario o validar el recuento, ejecutar el comando anterior y comparar con `tests/baseline/tests_inventory.json`.

##### 3.2.1.4 Variables de entorno requeridas

La suite usa `tests/conftest.py` para fijar unas variables mínimas y delega las credenciales operativas a `.env.full` (cuando existe) o a los overrides del entorno de ejecución.

**Variables internas (fijadas por `conftest.py`):**

| Variable | Propósito | Ejemplo / Origen |
|----------|-----------|------------------|
| `BASE_DIR` | Raíz del repositorio para `Settings` | `<repositorio>` |
| `SOAR_SKIP_EAGER_INIT` | Evita la creación temprana de la app FastAPI durante la recogida de tests | `1` |

**Variables operativas (esperadas en `.env.full` o `docker exec -e`):**

| Variable | Servicio / Uso | Notas |
|----------|----------------|-------|
| `SHUFFLE_DEFAULT_APIKEY` | Cliente Shuffle API | Obligatorio para tests E2E contra Shuffle |
| `SHUFFLE_DEFAULT_PASSWORD` | Autenticación admin Shuffle | Solo necesario si se regeneran credenciales |
| `THEHIVE_API_KEY` | Cliente TheHive API | Obligatorio para tests E2E |
| `CORTEX_API_KEY` | Cliente Cortex API | Obligatorio para tests E2E |
| `MISP_API_KEY` | Cliente MISP API | Obligatorio para tests E2E |
| `REDIS_PASSWORD` | Conexión Redis / Shuffle | Se escapa en conexiones `redis://` |
| `ELASTIC_PASSWORD` | Elasticsearch + Grafana datasource | También usado por `E2E` para indexar métricas |
| `JWT_SECRET_KEY` | Firma/validación de tokens JWT | `>=32` caracteres; el `conftest.py` usa un secreto de prueba si no existe |

> **Seguridad:** No se deben incluir valores reales en este documento. Las credenciales se cargan desde `.env.full` y se tratan como secretos. Para ejecuciones locales se recomienda usar `cp .env.example .env.full` y ejecutar `make generate-secrets` / `soar-lab generate-secrets`.

##### 3.2.1.5 Flujo real y recomendado de pruebas

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
make test-unit # No requiere Docker (usa mocks)
make test-atomic
make test-integration # Requiere stack completo levantado y saludable
make test-smoke # Requiere stack mínimo post-deploy
make test-e2e # Requiere stack completo y Shuffle configurado
make test-performance
make test-security
make test-all # Requiere stack completo y saludable

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
| `make test-coverage` | Sí (para E2E/integración) | Genera reporte HTML/XML de cobertura en `runtime/coverage/` |

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

#### 3.2.2 Categorías de pruebas

##### 3.2.2.1 Ejecución de pruebas

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

##### 3.2.2.2 Eliminaciones y omisiones

Varios archivos de prueba obsoletos han sido eliminados para mantener una alta relación señal-ruido. Algunas pruebas usan
`pytest.skip` en runtime cuando faltan dependencias externas (Docker, servicios SOAR levantados, API keys, workflow
creado) o cuando se ejecutan dentro de un contenedor sin acceso al código/host. Esto se refleja en el recuento final de
`pytest` como `skipped`, no como `error`.

##### 3.2.2.3 Ejecución individual

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
python3 -m pytest tests/unit/services/test_calc_kpis.py -v

# Ejecutar con cobertura
python3 -m pytest tests/ --cov=src/soar_lab --cov-report=html --cov-report=term --cov-fail-under=80
```

##### 3.2.2.4 Script de ejecución

```bash
# Ejecutar suite de pruebas integral
make test-all

# Ejecutar por categoría
make test-unit
make test-integration
make test-e2e

# Generar reporte de cobertura
make test-coverage
```

##### 3.2.2.5 Configuración de pruebas

**Configuración pytest.ini:**

```ini
[pytest]
asyncio_mode = auto
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    requires_docker: marks tests that require Docker to be running
    requires_external: marks tests that depend on external services (TheHive, Cortex, Shuffle, etc.)
    e2e: marks end-to-end tests that may take longer to run
    unit: marks unit tests that don't require external dependencies
    integration: marks integration tests that require multiple components
    atomic: marks atomic red-team simulation tests
    performance: marks performance and load tests
    security: marks security hardening and vulnerability tests
    kpi: marks KPI-related tests
    smoke: fast post-deployment smoke tests
    smoke_critical: P0 — rollback immediately if these fail
    smoke_high: P1 — investigate immediately, consider rollback
    smoke_medium: P2 — degraded platform, investigate within 24h
    architecture: marks architecture/hexagonal dependency tests
    quality: marks code quality tests (radon, bandit, vulture, coverage, etc.)
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

##### 3.2.2.6 Datos y fixtures

**Ubicación de Datos de Pruebas:**

- Archivos de datos de pruebas: `tests/e2e/fixtures/`
- Configuraciones de muestra: `tests/e2e/fixtures/`
- Respuestas mock: `tests/e2e/fixtures/`

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
 with patch('soar_lab.infrastructure.integrations.thehive.client.TheHiveClient') as mock:
 yield mock
```

##### 3.2.2.7 Tests de autenticación JWT

Los tests del proveedor JWT y del servicio de autenticación se encuentran en:

- `tests/unit/infrastructure/test_jwt_token_provider.py`
- `tests/integration/test_authorization.py`

**Escenarios cubiertos por `test_jwt_token_provider.py`:**

| Escenario | Entrada esperada | Comportamiento validado |
|-----------|------------------|-------------------------|
| Creación exitosa | `username`, secret `>= 32` chars, `expiration_minutes=60`, algoritmo `HS256` | Token JWT no vacío y verificable |
| Secret corto | secret `short` (menos de 32 chars) | `PyJWT` permite crear el token; la validación de longitud se delega a `AuthService` |
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

#### 3.2.3 Casos de prueba

##### 3.2.3.1 Objetivos de cobertura

| Categoría de Pruebas | Objetivo de Cobertura |
|------------------------|---------------------------------|
| Pruebas unitarias | >80% |
| Pruebas atómicas | >70% |
| Pruebas de integración | >60% |
| Pruebas de navegador | >50% |
| Pruebas de seguridad | >60% |
| Pruebas de rendimiento | N/A (benchmarks de rendimiento) |
| Pruebas E2E | >50% |

**Estado Actual de la Suite (v1.4.0):**

- **Python soportado**: `>=3.11` (declarado en `pyproject.toml`; CI y entorno de desarrollo usan 3.11.x).
- **Objetivo mínimo global**: ≥ 80% de cobertura.
- **Inventario de tests**: `tests/baseline/tests_inventory.json` (actualizado mediante `pytest --collect-only`); para el recuento real ejecutar:

 ```bash
 python -m pytest --collect-only -q
 ```

 > El recuento exacto depende de la versión actual del código, parametrizaciones y entorno. Los conteos detallados por directorio se encuentran en `tests/baseline/tests_inventory.json`.

- **Ejecución real (`pytest -q`)**: el número de `passed`/`failed`/`skipped`/`error` depende del entorno. Con los servicios levantados la mayoría de E2E e integración pasan; sin servicios externos se observan `skipped` en tests marcados con `requires_external` o `requires_docker`.

- **Restricciones de plataforma**: algunas pruebas de Docker e integración se omiten si no se detecta el socket de Docker (`/var/run/docker.sock` o equivalente) o si se ejecutan dentro de un contenedor sin acceso al repo/host. En Windows se recomienda ejecutar pruebas E2E e integración con Docker Desktop activo.

- **Smoke tests**: marcador `smoke` de pytest; archivo principal `tests/integration/test_smoke.py`.
- **Reporte de coverage**: `runtime/coverage/htmlcov/` y `runtime/coverage/coverage.xml`.
- **Comando para generar reporte**: `make test-coverage` (Linux/Mac) o `make -f Makefile.win test-coverage` (Windows).

##### 3.2.3.2 Entornos de pruebas

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
docker compose --env-file .env.full -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.opensearch.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml up -d
python -m pytest tests/ -v
```

##### 3.2.3.3 Generación de reportes

```bash
# Generar reporte de cobertura HTML
make test-coverage

# Ver reporte de cobertura
open htmlcov/index.html
```

**Archivos de Resultados:**

- Resultados de pruebas: `reports/test_results/test_results.json`
- Reportes de cobertura: `runtime/coverage/htmlcov/`
- Reportes de rendimiento: `reports/performance/`
- Reportes de seguridad: `reports/security/`

**Formatos de Reporte:**

- JSON: Resultados legibles por máquina
- HTML: Reportes de cobertura legibles por humanos
- JUnit XML: Integración CI/CD
- Consola: Salida en tiempo real

##### 3.2.3.4 Smoke tests y cobertura histórica

**Smoke tests (`pytest -m smoke`)**

- Valoran la salud mínima del despliegue después de `make up`.
- Marcadores: `smoke`, `smoke_critical`, `smoke_high`, `smoke_medium`.
- Ejecución: `make test-smoke` o `pytest -m smoke`.
- Cubren endpoints críticos como `GET /health`, `GET /services/status`, login y el webhook de Shuffle.

**Cobertura histórica en SQLite**

- Los resultados históricos de cobertura se almacenan en `runtime/coverage/history.db` (o similar en SQLite) para comparar
 evolución entre despliegues.
- `make test-coverage` genera tanto el reporte HTML como la métrica consolidada.
- El CLI `soar-lab` y el dashboard de `web-management` pueden consultar los datos de cobertura actuales via API.

#### 3.2.4 Ejecución de pruebas

##### 3.2.4.1 Comandos de ejecución

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

##### 3.2.4.2 Entornos de ejecución

- **Local**: Ejecución en máquina de desarrollo
- **CI/CD**: Ejecución automática en GitHub Actions
- **Docker**: Ejecución dentro de contenedores
- **Remoto vía API / Web Management**: La API SOAR expone `POST /tests/run` que delega en `PytestTestRunner`
 (`src/soar_lab/infrastructure/pytest_test_runner.py`).

##### 3.2.4.3 Ejecución remota vía `PytestTestRunner`

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
 -d '{"username":"admin","password":"<WEB_UI_PASSWORD>"}' | jq -r '.token')

# Lanzar suite E2E
curl -s -X POST http://localhost:8000/tests/run \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"category":"e2e","coverage":false}'
```

> **Nota:** La ejecución remota requiere que el contenedor `soar_api` tenga acceso al socket/código y a las variables
> de entorno de `.env.full`. Para tests E2E e integración, los servicios Docker deben estar levantados.

#### 3.2.5 Reportes y métricas

##### 3.2.5.1 Reportes generados

- **Resultados de pruebas**: `reports/test_results/test_results.json`
- **Reportes de cobertura**: `runtime/coverage/htmlcov/`
- **Reportes de rendimiento**: `reports/performance/`
- **Reportes de seguridad**: `reports/security/`

##### 3.2.5.2 Métricas clave

| Categoría de Pruebas | Objetivo de Cobertura |
|------------------------|---------------------------------|
| Pruebas unitarias | >80% |
| Pruebas atómicas | >70% |
| Pruebas de integración | >60% |
| Pruebas de navegador | >50% |
| Pruebas de seguridad | >60% |
| Pruebas de rendimiento | N/A (benchmarks de rendimiento) |
| Pruebas E2E | >50% |

### 3.3 Pruebas unitarias

Tests unitarios para el proyecto SOAR Ransomware Lab. Estos tests verifican el funcionamiento de componentes
individuales de forma aislada, sin dependencias externas.

#### Propósito

Los tests unitarios validan:

- Funciones y clases individuales
- Lógica de negocio
- Validación de datos
- Generación de datos (IOCs, secretos, KPIs)
- Clientes de servicios (mockeados)
- Utilidades y helpers

#### Requisitos

#### Mínimos

- Python 3.11+
- pytest
- pytest-cov (opcional, para coverage)

#### No requiere servicios externos

Los tests unitarios no requieren servicios Docker en ejecución. Todas las dependencias externas están mockeadas.

#### Ejecución

#### Ejecutar todos los tests unitarios (canónico)

```bash
make test-unit
```

> `make test-unit` ejecuta `pytest tests/unit -v` dentro del contenedor `soar_api` tras sincronizar el código. Para desarrollo aislado en host (sin Docker):
>
> ```bash
> pytest tests/unit/ -v
> ```

#### Ejecutar tests específicos

```bash
# Tests de clientes
pytest tests/unit/clients/test_elasticsearch_client.py -v
pytest tests/unit/clients/test_misp_client.py -v
pytest tests/unit/clients/test_shuffle_client.py -v

# Tests de servicios
pytest tests/unit/services/test_auth_service.py -v
pytest tests/unit/services/test_backup_service.py -v
pytest tests/unit/services/test_health_service.py -v

# Tests de generadores
pytest tests/atomic/test_ioc_generator.py -v
pytest tests/unit/generators/test_generate_secrets.py -v
pytest tests/unit/generators/test_generate_kpi_data.py -v

# Tests de validación
pytest tests/unit/utils/test_validators.py -v
pytest tests/unit/config/test_config_schemas.py -v
```

#### Ejecutar con coverage

```bash
pytest tests/unit/ --cov=src/soar_lab --cov-report=html --cov-report=term
```

#### Ejecutar solo tests que fallen

```bash
pytest tests/unit/ -v --lf
```

#### Ejecutar tests en paralelo

```bash
pytest tests/unit/ -v -n auto
```

#### Categorías de Tests

#### Clientes de Servicios

- `test_elasticsearch_client.py`: Cliente Elasticsearch
- `test_misp_client.py`: Cliente MISP
- `test_shuffle_client.py`: Cliente Shuffle
- `test_thehive_client.py`: Cliente TheHive
- `test_cortex_client.py`: Cliente Cortex
- `test_base_client.py`: Cliente base
- `test_http_client.py`: Cliente HTTP genérico

#### Servicios

- `test_auth_service.py`: Servicio de autenticación
- `test_backup_service.py`: Servicio de backup
- `test_health_service.py`: Servicio de health check
- `test_test_service.py`: Servicio de tests

#### Generadores

- `test_ioc_generator.py`: Generador de IOCs
- `test_generate_iocs.py`: Generación de IOCs
- `test_generate_secrets.py`: Generación de secretos
- `test_generate_kpi_data.py`: Generación de datos KPI
- `test_alert_generator.py`: Generador de alertas

#### Validación y Schemas

- `test_validators.py`: Validadores
- `test_config_schemas.py`: Schemas de configuración
- `test_domain_models.py`: Modelos de dominio
- `test_schema_validation.py`: Validación de schemas (atomic)

#### Utilidades

- `test_path_service.py`: Servicio de rutas
- `test_filesystem_storage.py`: Almacenamiento en filesystem
- `test_file_log_reader.py`: Lector de logs
- `test_log_parser.py`: Parser de logs

#### Resiliencia

- `test_circuit_breaker.py`: Circuit breaker
- `test_retry_policy.py`: Política de reintentos
- `test_timeout_handling.py`: Manejo de timeouts
- `test_payload_sanitization.py`: Sanitización de payloads
- `test_structured_logging.py`: Logging estructurado

#### Analítica y KPIs

- `test_analytics_service.py`: Servicio de analítica
- `test_kpi_analyzer.py`: Analizador de KPIs
- `test_kpi_alerts.py`: Alertas KPI
- `test_kpi_formatter.py`: Formateador de KPIs
- `test_statistical_calculator.py`: Calculadora estadística
- `test_calc_kpis.py`: Cálculo de KPIs

#### API

- `test_api_auth.py`: Autenticación API
- `test_api_models.py`: Modelos API
- `test_api_composition.py`: Composición API
- `test_api_main.py`: App principal API
- `test_api_cli.py`: CLI API
- `test_contracts.py`: Contratos OpenAPI
- `test_routes_analytics.py`: Rutas de analíticas
- `test_routes_soar.py`: Rutas SOAR
- `test_trace_id_middleware.py`: Middleware de trace ID
- `test_validation.py`: Validadores de request/response

#### Otros

- `test_settings.py`: Configuración
- `test_exceptions.py`: Excepciones
- `test_domain_ports.py`: Puertos de dominio
- `test_jwt_token_provider.py`: Proveedor de tokens JWT
- `test_websocket_manager.py`: Gestor de WebSockets

#### Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests unitarios:

- `mock_settings`: Configuración mockeada
- `mock_redis_client`: Cliente Redis mockeado
- `mock_docker_client`: Cliente Docker mockeado

#### Fixtures Globales

Los fixtures en `tests/conftest.py` también están disponibles:

- `sample_alert`: Alerta de ejemplo
- `sample_malicious_alert`: Alerta maliciosa de ejemplo
- `sample_benign_alert`: Alerta benigna de ejemplo
- `mock_elasticsearch_client`: Cliente Elasticsearch mockeado
- `mock_misp_client`: Cliente MISP mockeado
- `mock_shuffle_client`: Cliente Shuffle mockeado

#### Patrones de Tests

#### Test básico

```python
def test_function_name():
 """Test description"""
 # Arrange
 input_data = {...}

 # Act
 result = function_to_test(input_data)

 # Assert
 assert result == expected_value
```

#### Test con fixtures

```python
def test_with_fixture(mock_client):
 """Test with mock fixture"""
 mock_client.return_value = expected_data
 result = function_to_test
 assert result == expected_value
```

#### Test con excepciones

```python
def test_exception():
 """Test that exception is raised"""
 with pytest.raises(ValueError, match="expected message"):
 function_to_test(invalid_input)
```

#### Coverage

Mantenemos un mínimo de coverage para tests unitarios:

- **Coverage general**: 80%
- **Funciones críticas**: 90%
- **Funciones de seguridad**: 95%

#### Tiempo de Ejecución

Los tests unitarios son rápidos debido a que no hay dependencias externas:

- Tiempo estimado: 1-3 minutos
- Pueden ejecutarse en paralelo para mayor velocidad

#### Solución de Problemas

#### Tests fallan por import errors

Verifica que el directorio `src/` esté en el PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### Tests fallan por mocks incorrectos

Verifica que los mocks estén configurados correctamente:

```bash
pytest tests/unit/utils/test_filesystem_storage.py -v -s
```

#### Coverage bajo

Añade tests para las rutas no cubiertas:

```bash
pytest tests/unit/ --cov=src/soar_lab --cov-report=html
# Abre htmlcov/index.html para ver el reporte
```


### 3.4 Pruebas de integración

Tests de integración para el proyecto SOAR Ransomware Lab. Estos tests verifican la interacción entre diferentes
servicios y componentes del sistema.

#### Propósito

Los tests de integración validan:

- Conectividad entre servicios (TheHive, MISP, Elasticsearch, Shuffle)
- Intercambio de datos entre componentes
- Manejo de errores en comunicaciones externas
- Idempotencia de operaciones
- Consistencia de datos entre servicios
- Compatibilidad de versiones

#### Requisitos de Servicios

Para ejecutar estos tests, los siguientes servicios deben estar en ejecución:

#### Servicios Requeridos

- **Elasticsearch**: `localhost:8200` (o puerto configurado en `.env.full`)
- **MISP**: `localhost:8083` (o puerto configurado en `.env.full`)
- **TheHive**: `localhost:8100` (o puerto configurado en `.env.full`)
- **Shuffle**: `localhost:8081` (o puerto configurado en `.env.full`)

#### Verificar Servicios

```bash
# Verificar salud real de servicios (recomendado)
make health

# Verificar estado de servicios Docker
docker compose ps

# Verificar logs de servicios
docker compose logs -f <servicio>
```

> Un contenedor en estado `Up` no implica que el servicio esté listo. Usar `make health` antes de lanzar tests.

#### Configuración

Asegúrate de que `.env.full` esté configurado con las credenciales correctas:

```bash
# Ejemplo de variables requeridas
ELASTIC_HOST=localhost
ELASTIC_PORT=8200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=<ELASTIC_PASSWORD>

MISP_URL=http://localhost:8083
MISP_API_KEY=<MISP_API_KEY>

THEHIVE_URL=http://localhost:8100
THEHIVE_API_KEY=<THEHIVE_API_KEY>

SHUFFLE_URL=http://localhost:8081
SHUFFLE_DEFAULT_APIKEY=<SHUFFLE_DEFAULT_APIKEY>
```

#### Preparación y ejecución canónica

Los tests de integración requieren el stack Docker levantado, `.env.full` correcto y `make health` exitoso.

```bash
# 1. Levantar servicios y verificar salud
make up
make health

# 2. Ejecutar tests de integración (canónico)
make test-integration
```

#### Ejecutar todos los tests de integración (directo)

```bash
pytest tests/integration/ -v
```

> **Nota:** `make test-integration` ejecuta `pytest tests/integration -v -m 'requires_docker or not requires_docker'` dentro del contenedor `soar_api`. Ejecutar `pytest` directo en host puede fallar si faltan variables o dependencias reales.

#### Ejecutar tests específicos

```bash
# Tests de Elasticsearch
pytest tests/integration/test_elasticsearch_integration.py -v

# Tests de MISP
pytest tests/integration/test_misp_integration.py -v

# Tests de Shuffle
pytest tests/integration/test_init_shuffle_webhook.py -v

# Tests de validación de Docker
pytest tests/integration/test_docker_build_validation.py -v
```

#### Ejecutar con coverage

```bash
pytest tests/integration/ --cov=src/soar_lab --cov-report=html
```

#### Categorías de Tests

#### Conectividad de Servicios

- `test_elasticsearch_integration.py`: Integración completa con Elasticsearch
- `test_misp_integration.py`: Integración completa con MISP
- `test_thehive_integration.py`: Integración con TheHive
- `test_shuffle_integration.py`: Integración con Shuffle
- `test_cortex_integration.py`: Integración con Cortex

#### Inicialización y Configuración

- `test_init_shuffle_webhook.py`: Inicialización de webhook Shuffle
- `test_docker_build_validation.py`: Validación de Docker Compose y builds
- `test_docker_runtime_status.py`: Estado de runtime Docker

#### Comunicación y Datos

- `test_data_consistency.py`: Consistencia de datos entre servicios
- `test_idempotency.py`: Idempotencia de operaciones
- `test_external_service_failure.py`: Manejo de fallos de servicios externos

#### Seguridad y Autorización

- `test_authorization.py`: Tests de autorización RBAC
- `test_security.py`: Tests de seguridad
- `test_auth.py`: Tests de autenticación

#### API y Contratos

- `test_api_endpoints.py`: Tests de endpoints API
- `test_api_fastapi.py`: Tests de API FastAPI
- `test_api_integration.py`: Tests de integración API
- `test_contract_compliance.py`: Cumplimiento de contratos de servicio
- `test_openapi_spec_sync.py`: Sincronización de especificación OpenAPI

#### Rendimiento y Condiciones de Carrera

- `test_race_conditions.py`: Condiciones de carrera
- `test_version_compatibility.py`: Compatibilidad de versiones
- `test_docker_partial_failure.py`: Recuperación de fallos parciales

#### Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests de integración:

- `elasticsearch_client`: Cliente Elasticsearch configurado
- `misp_client`: Cliente MISP configurado
- `thehive_client`: Cliente TheHive configurado
- `shuffle_client`: Cliente Shuffle configurado

#### Solución de Problemas

#### Tests fallan por conexión rechazada

Verifica que los servicios estén en ejecución:

```bash
docker compose ps
```

#### Tests fallan por autenticación

Verifica las credenciales en `.env.full`:

```bash
# Verificar variables de entorno
cat .env.full | grep -E "(URL|API_KEY|PASSWORD)"
```

#### Tests fallan por timeout

Aumenta el timeout en el test o verifica el rendimiento del servicio:

```bash
# Verificar uso de recursos
docker stats
```

#### Tests de Elasticsearch fallan

Verifica que Elasticsearch esté saludable:

```bash
curl -u "elastic:<ELASTIC_PASSWORD>" http://localhost:8200/_cluster/health
```

#### Tests de MISP fallan

Verifica que MISP esté accesible:

```bash
curl -H "Authorization: <MISP_API_KEY>" http://localhost:8083/users/me
```

#### Tiempo de Ejecución

Los tests de integración pueden tardar más que los tests unitarios debido a:

- Latencia de red
- Tiempo de respuesta de servicios externos
- Operaciones de I/O

Tiempo estimado: 5-15 minutos (dependiendo de la carga del sistema)


### 3.5 Pruebas E2E

Tests end-to-end (E2E) para el proyecto SOAR Ransomware Lab. Estos tests validan el flujo completo del sistema desde la
recepción de una alerta hasta la respuesta automatizada.

#### Propósito

Los tests E2E validan:

- Flujo completo de ransomware detection
- Integración de todos los servicios
- Coordinación de workflows
- Generación y uso de IOCs
- Actualización de métricas KPI
- Respuesta automatizada a incidentes

#### Requisitos

#### Servicios Requeridos

Todos los servicios deben estar en ejecución:

- **Elasticsearch**: `localhost:8200`
- **MISP**: `localhost:8083`
- **TheHive**: `localhost:8100`
- **Shuffle**: `localhost:8081`
- **Grafana**: `localhost:8084`
- **Promtail/Loki**: Logging stack

#### Configuración Requerida

- `.env.full` configurado con todas las credenciales
- Webhook Shuffle inicializado
- Índices Elasticsearch creados
- Workflows Shuffle configurados

#### Preparación del Entorno

El flujo canónico utiliza los targets de `make`. No se recomienda levantar el stack con `docker compose up -d` directamente porque `make` configura `.env.full`, perfiles, secretos y datos previos.

```bash
# 1. Generar secretos e IOCs de prueba
make generate-secrets
make generate-iocs

# 2. Limpiar entorno previo y levantar stack completo
make reset
make up

# 3. Verificar salud de los servicios
make health

# 4. Inicializar workflow y webhook de Shuffle
make init-webhook
```

#### Verificar configuración

```bash
# Verificar Elasticsearch
curl -u "elastic:$ELASTIC_PASSWORD" http://localhost:8200/_cluster/health

# Verificar MISP
curl -H "Authorization: $MISP_API_KEY" http://localhost:8083/users/me

# Verificar Shuffle (API backend en 5001)
curl -H "Authorization: $SHUFFLE_DEFAULT_APIKEY" http://localhost:5001/api/v1/workflows
```

#### Ejecución

#### Ejecutar todos los tests E2E

```bash
make test-e2e
```

> **Nota:** `make test-e2e` ejecuta `pytest tests/e2e -v --no-cov` dentro del contenedor `soar_api`. Ejecutar `pytest tests/e2e/ -v` directamente en host puede fallar si el entorno no está preparado.

#### Ejecutar tests específicos

```bash
# Tests de casos específicos
pytest tests/e2e/TC-01/ -v
pytest tests/e2e/TC-02/ -v

# Tests de KPI
pytest tests/e2e/TC-KPI-01/ -v
```

#### Ejecutar con timeout extendido

```bash
pytest tests/e2e/ -v --timeout=300
```

#### Ejecutar en modo verbose

```bash
pytest tests/e2e/ -v -s
```

#### Catálogo de escenarios E2E

> **Nota:** La suite E2E evoluciona con el proyecto. Para obtener el listado real y recogible en cualquier entorno,
> ejecutar `python -m pytest tests/e2e --collect-only -q`.

#### Escenarios funcionales representativos

| Caso | Archivo(s) | Objetivo | Servicios implicados | Artefactos generados |
|------|------------|----------|---------------------|----------------------|
| TC-00 | `TC-00/test_both_workflows*.py` | Validar comparación entre workflows de ransomware y benigno | Shuffle, TheHive | `webhook_info.json` |
| TC-01 | `TC-01/test_malicious.py` | Flujo completo de alerta maliciosa: recepción, caso y contención simulada | Shuffle, TheHive, Elasticsearch | Caso en TheHive, métricas en `soar-metrics` |
| TC-02 | `TC-02/test_benign.py` | Flujo de alerta benigna sin contención | Shuffle, TheHive | Caso cerrado/marcado benigno |
| TC-03 | `TC-03/test_edge_cases.py` | Manejo de casos límite (campos faltantes, URLs inválidas, concurrencia) | Shuffle, API | Logs de ejecución |
| TC-04 | `TC-04/test_performance.py` | Métricas de rendimiento bajo carga controlada | API, Elasticsearch | Métricas de latencia |
| TC-05 | `TC-05/test_concurrent_alerts.py` | Procesamiento concurrente de alertas | Shuffle, orborus | Múltiples ejecuciones de workflow |
| TC-06 | `TC-06/test_critical_severity.py` | Priorización por severidad crítica | Shuffle, TheHive | Caso crítico con escalación |
| TC-07 | `TC-07/test_missing_fields.py` | Robustez ante alertas con campos incompletos | API, Shuffle | Errores controlados |
| TC-08 | `TC-08/test_additional_fields.py` | Campos personalizados y extensibilidad de alertas | Shuffle, TheHive | Caso con observables extra |
| TC-09 | `TC-09/test_realistic_ransomware.py` | Fidelidad del simulador frente a ransomware real | API, Shuffle (simulado) | Alertas enriquecidas |
| TC-10 | `TC-10/test_tenzir_integration.py` | Integración con Tenzir (planificada/parcial) | Tenzir | Logs exportados |
| TC-11 | `TC-11/test_network_watcher_integration.py` | Conectividad del Network Watcher con la red de Shuffle | Docker, `soar_net` | Estado de red verificado |
| TC-12 | `TC-12/test_redis_integration.py` | Estado compartido y caché vía Redis | Redis | Claves de prueba |
| TC-13 | `TC-13/test_loki_integration.py` | Logging centralizado Loki/Promtail/Grafana | Logging stack | Logs consultables en Grafana |
| TC-14 | `TC-14/test_complete_soar_integration.py`, `test_traceability.py` | Flujo SOAR completo y trazabilidad de ejecución | Todos | Métricas, casos, logs enlazados |
| TC-15 | `TC-15/test_api_latency.py` | Latencia de endpoints críticos | API | Métricas de latencia |
| TC-16 | `TC-16/test_error_handling.py`, `test_error_rate.py` | Manejo y tasa de errores | API, Shuffle | Reporte de errores |
| TC-17 | `TC-17/test_network_watcher_monitoring.py` | Monitoreo del Network Watcher | Docker, Prometheus | Métricas de red |
| TC-18 | `TC-18/test_resilience.py` | Recuperación ante fallos de workflow | Shuffle, orborus | Reintentos exitosos |
| TC-19 | `TC-19/test_security.py` | Validación de autenticación y seguridad | API, JWT | Tokens validados |
| TC-20 | `TC-20/test_zero_trust.py` | Validación de políticas de acceso | API, Nginx | Políticas aplicadas |
| TC-21 | `TC-21/test_forensic.py` | Recolección de evidencia digital | MISP, TheHive | Evidencias adjuntas |
| TC-22 | `TC-22/test_persistence.py` | Persistencia de datos tras reinicios | SQLite, Elasticsearch | Datos recuperados |
| TC-23 | `TC-23/test_privacy.py` | Anonimización y privacidad de datos | API, Elasticsearch | Datos anonimizados |
| TC-24 | `TC-24/test_malware_specific.py` | Detección de comportamiento ransomware | MISP (simulado) | IoCs de malware |
| TC-25 | `TC-25/test_behavioral_detection.py` | Detección basada en comportamiento | Shuffle, Cortex (parcial) | Análisis de comportamiento |
| TC-26 | `TC-26/test_extreme_load.py` | Carga extrema y estabilidad | Todo el stack | Métricas de saturación |
| TC-27 | `TC-27/test_configuration.py` | Validación de configuración del entorno | CLI, `.env.full` | Configuración verificada |
| TC-28 | `TC-28/test_ui_e2e.py` | Navegación básica de la Web Management | Selenium (opcional) | Capturas/logs |
| TC-29 | `TC-29/test_large_evidence.py` | Manejo de grandes volúmenes de evidencia | TheHive | Evidencias grandes |
| TC-30 | `TC-30/test_offline_mode.py` | Modo offline y mocks de servicios | API, mocks | Tests aislados |
| TC-31 | `TC-31/test_compliance.py` | Cumplimiento de controles de seguridad | API | Reporte de compliance |
| TC-32 | `TC-32/test_golden_thread.py` | Trazabilidad completa del flujo E2E | Todos | Golden thread verificado |
| TC-KPI-01 | `TC-KPI-01/test_mttr_calculation.py` | Cálculo de MTTR | Elasticsearch, `soar-metrics` | Valor MTTR |
| TC-KPI-02 | `TC-KPI-02/test_kpi_dashboard.py` | Disponibilidad del dashboard Grafana | Grafana, Elasticsearch | Dashboard accesible |
| TC-KPI-03 | `TC-KPI-03/test_kpi_alerts.py` | KPIs derivados de alertas | Elasticsearch | Métricas indexadas |
| TC-KPI-04 | `TC-KPI-04/test_mttr_percentiles.py` | Percentiles de respuesta | Elasticsearch, `soar-metrics` | P50/P95 |
| TC-KPI-05 | `TC-KPI-05/test_service_success_rates.py` | Tasa de éxito de servicios | API, Elasticsearch | Ratios por servicio |
| TC-KPI-06 | `TC-KPI-06/test_kpi_data_coherence.py` | Coherencia entre KPIs y datos de origen | Elasticsearch, API | Validación cruzada |

#### Targets Make y comandos canónicos

```bash
# Ejecutar toda la suite E2E
make test-e2e

# Casos individuales (targets make disponibles)
make test-e2e-tc01
make test-e2e-tc02
make test-e2e-tc10
make test-e2e-tc11
make test-e2e-tc12
make test-e2e-tc13
make test-e2e-tc14
make test-e2e-tc16
make test-e2e-tc18
make test-e2e-tc24
make test-e2e-tc26
make test-e2e-tc27
make test-e2e-tc30
make test-e2e-tc32
make test-e2e-kpi-01
make test-e2e-kpi-02
make test-e2e-kpi-03
make test-e2e-kpi-04
make test-e2e-kpi-05

# Alternativa directa con pytest (tras make up + make health)
python -m pytest tests/e2e/TC-01/ -v
python -m pytest tests/e2e/TC-03/ -v --timeout=300
python -m pytest tests/e2e/TC-KPI-01/ -v

# Recolección reproducible (fuente de verdad para conteos)
python -m pytest tests/e2e --collect-only -q
```

#### Estructura de directorios

```
tests/e2e/
├── base/ # Clases base y utilidades compartidas
├── TC-00/ to TC-33/ # Casos de prueba funcionales
├── TC-KPI-01/ to TC-KPI-06/ # Casos de validación de KPIs
├── assertions/ # Helpers de aserciones compartidas
├── conftest.py # Fixtures globales (clientes, alertas, credenciales)
├── fixtures/ # Datos de prueba
├── helpers/ # Utilidades de los tests E2E
└── pytest.ini # Configuración específica de la suite E2E
```

#### Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests E2E:

- `workflow_client`: Cliente Shuffle configurado
- `thehive_client`: Cliente TheHive configurado
- `misp_client`: Cliente MISP configurado
- `elasticsearch_client`: Cliente Elasticsearch configurado

#### Tiempo de Ejecución

Los tests E2E son los más lentos debido a:

- Latencia de red entre servicios
- Tiempo de ejecución de workflows
- Operaciones de I/O en múltiples servicios
- Tiempo de espera para respuestas asíncronas

Tiempo estimado: 15-30 minutos (dependiendo de la carga del sistema)

#### Solución de Problemas

#### Tests fallan por servicios no disponibles

Verifica que todos los servicios estén en ejecución y realmente listos:

```bash
make health
docker compose ps
docker compose logs -f <servicio>
```

> Un contenedor en estado `Up` no garantiza que el servicio esté listo. `make health` verifica endpoints internos.

#### Tests fallan por servicios no listos, recursos insuficientes o Docker Desktop

1. **Servicios no listos:**
 - Ejecutar `make health` antes del test.
 - Consultar logs del servicio específico: `docker compose logs -f <servicio>`.
 - Esperar a que healthchecks finalicen; algunos servicios (TheHive) tardan minutos.

2. **Recursos insuficientes:**
 - Asignar al menos 8 GB de RAM y 4 vCPU a Docker / WSL.
 - Revisar `OOMKilled` con `docker inspect <contenedor> --format='{{.State.OOMKilled}}'`.

3. **Docker Desktop / WSL / Windows:**
 - Activar integración WSL2 y file sharing para el directorio del repo.
 - Ejecutar `make` desde WSL2 o PowerShell (no `cmd`).
 - Si `make` no está disponible: `make -f Makefile.win <target>` o usar WSL.

4. **Credenciales / `.env.full` desactualizadas:**
 - Tras `make reset` el apikey de Shuffle cambia; actualizar `.env.full` o confiar en `ShuffleClient._fetch_real_apikey`.
 - Regenerar secretos: `make generate-secrets`.

#### Tests fallan por webhook no inicializado

Inicializa el webhook Shuffle:

```bash
python scripts/setup/init_shuffle_webhook.py
```

#### Tests fallan por timeout

Aumenta el timeout o verifica el rendimiento del sistema:

```bash
pytest tests/e2e/ -v --timeout=600
```

#### Tests fallan por credenciales incorrectas

Verifica las credenciales en `.env.full`:

```bash
cat .env.full | grep -E "(API_KEY|PASSWORD)"
```

#### Tests fallan por índices Elasticsearch no creados

Crea los índices necesarios:

```bash
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:8200/soar-alerts
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:8200/soar-iocs
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:8200/soar-metrics
```

#### Limpieza después de Tests

Los tests E2E pueden dejar datos en los servicios. Para limpiar:

#### Limpiar Elasticsearch

```bash
curl -u elastic:$ELASTIC_PASSWORD -X DELETE http://localhost:8200/soar-*
```

#### Limpiar TheHive

```bash
# Eliminar casos de prueba vía API o UI
```

#### Limpiar MISP

```bash
# Eliminar eventos de prueba vía API o UI
```

#### Limpiar Shuffle

```bash
# Eliminar ejecuciones de prueba vía API o UI
```

#### Best Practices

#### Ejecutar tests E2E

- Ejecutar en un entorno de pruebas aislado
- No ejecutar en producción
- Limpiar datos después de cada ejecución
- Verificar que no haya tests ejecutándose simultáneamente

#### Desarrollo de tests E2E

- Mantener tests independientes entre sí
- Usar datos de prueba consistentes
- Limpiar recursos en teardown
- Documentar dependencias externas


### 3.6 Pruebas con Docker

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe la estrategia integral de pruebas de Docker para el proyecto SOAR Ransomware Lab, incluyendo
validación de configuración y runtime para garantizar que el entorno Docker completo funcione correctamente.

#### 1.2 Contexto

La estrategia de pruebas incluye tres niveles: validación de configuración (sin requerir Docker daemon), validación de
runtime (con contenedores reales) y validación de navegador/UI (con automatización de navegador). Este enfoque multicapa
proporciona confianza en que el entorno Docker funcionará correctamente en producción.

#### 2. Alcance

#### 2.1 Qué cubre

Este documento cubre:

- Estrategia de pruebas de Docker en tres niveles (configuración, runtime, navegador)
- Validación de servicios SOAR core (Elasticsearch, TheHive, Cortex, Shuffle Dashboard)
- Validación de servicios de threat intelligence (MISP, Redis, MariaDB)
- Validación de redes, volúmenes, health checks, rendimiento y seguridad
- Integración con CI/CD mediante GitHub Actions
- Troubleshooting de problemas comunes
- Mejoras futuras planeadas

#### 2.2 Límites

Este documento no cubre:

- Estrategias de seguridad avanzadas del proyecto (ver docs/02-architecture.md)
- Arquitectura detallada del sistema (ver docs/02-architecture.md)
- Detalle de casos de prueba específicos (ver [3.3 Casos de prueba](#323-casos-de-prueba))
- Guía de usuario para ejecutar pruebas (ver [3.2.4 Ejecución de pruebas](#324-ejecución-de-pruebas))

#### 2.3 Dependencias

Este documento depende de:

- Documentación de arquitectura (docs/02-architecture.md)
- Documentación de Docker (docs/02-architecture.md)
- Guía de pruebas (este documento)
- Especificación de casos de prueba (este documento)

#### 3.6.1 Estrategia de pruebas

##### 3.6.1.1 Niveles de pruebas

**Nivel 1: Validación de Configuración**

- Archivos: `tests/integration/test_docker_build_validation.py`
- Propósito: Validar configuración de `infra/docker/compose/docker-compose*.yml` sin requerir Docker daemon
- Ventajas: Ejecución rápida, puede ejecutarse en cualquier entorno, amigable para CI/CD
- Limitaciones: No valida inicio real de servicios, conectividad de red real, funcionalidad de servicios

**Nivel 2: Validación de Runtime**

- Archivos: `tests/integration/test_docker_runtime_status.py`, `tests/integration/test_docker_partial_failure.py`
- Propósito: Validar funcionalidad del entorno Docker real
- Requisitos: Docker daemon ejecutándose, docker compose disponible, recursos suficientes

**Nivel 3: Validación de Navegador/UI**

- Archivo: `tests/e2e/TC-14/test_complete_soar_integration.py`
- Propósito: Validar interfaces web con automatización de navegador real
- Requisitos: Selenium WebDriver, navegador Chrome/Chromium, servicios Docker ejecutándose

##### 3.6.1.2 Fases de ejecución

Flujo canónico con `make`:

```bash
# 1. Preparar secretos, IOCs y limpiar entorno
make generate-secrets
make generate-iocs
make reset

# 2. Levantar stack y verificar salud
make up
make health

# 3. Ejecutar tests según nivel
make test-unit # Fase de pruebas unitarias (no requiere Docker)
make test-integration # Fase de runtime e integración
make test-e2e # Fase de navegador/UI y flujos completos
make test-all # Ejecuta toda la suite
```

**Selección de perfiles de Docker Compose:**

El proyecto no utiliza el campo `profiles:` de Docker Compose; en su lugar, `Makefile.linux` / `Makefile.win` definen `COMPOSE_FILES` como conjunto de archivos `docker-compose*.yml` y el target `make` selecciona el escenario:

| Escenario | Archivos de compose incluidos | Target make |
|-----------|------------------------------|-------------|
| Stack completo | `docker-compose.yml`, `docker-compose.core.yml`, `docker-compose.misp.yml`, `docker-compose.opensearch.yml`, `docker-compose.logging.yml` | `make up` |
| Tests unitarios | Ninguno | `make test-unit` |
| Tests de integración | Stack completo + contenedor `soar_api` | `make test-integration` |
| Tests E2E | Stack completo + `soar_api` | `make test-e2e` |

> Para escenarios personalizados, sobreescribir `COMPOSE_FILES` o `ENV_FILE`: `make up ENV_FILE=.env.testing`.

#### 3.6.2 Tipos de pruebas

##### 3.6.2.1 Fase 1: pruebas de configuración

```bash
python -m pytest tests/integration/test_docker_build_validation.py -v
```

- Validación rápida de `infra/docker/compose/docker-compose*.yml`
- Puede ejecutarse durante el desarrollo
- Integración en pipeline CI/CD

##### 3.6.2.2 Fase 2: pruebas de runtime

```bash
python -m pytest tests/integration/test_docker_runtime_status.py tests/integration/test_docker_partial_failure.py -v
```

- Validación completa del entorno Docker
- Verificación de inicio de servicios
- Prueba de conectividad de red
- Validación de uso de recursos

##### 3.6.2.3 Fase 3: pruebas de navegador

```bash
python -m pytest tests/e2e/TC-14/test_complete_soar_integration.py -v
```

- Validación de interfaces web
- Prueba de experiencia de usuario
- Validación de rendimiento y seguridad

#### 3.6.3 Herramientas y frameworks

##### 3.6.3.1 Cobertura de servicios

#### Servicios SOAR Core

| Servicio | Puerto | Configuración | Runtime | Navegador |
|---------------------|--------|-------------------------------------|------------------------------------------------|-------------------------------------------|
| **Elasticsearch** | 8200 | Imagen, puertos, volúmenes, entorno | Salud del cluster, accesibilidad de API | No aplicable (solo API) |
| **TheHive** | 8100 | Imagen, puertos, volúmenes, redes | Salud del contenedor (`/api/status`), endpoints de API | Interfaz de login, UI de gestión de casos |
| **Cortex** | 8101 | Imagen, puertos, volúmenes, redes | Container health, analyzer endpoints | Login interface, analyzer management |
| **Shuffle** | 8081 | Imagen, puertos, volúmenes, redes | Container health, workflow engine | Login interface, workflow builder |
| **OpenSearch Dashboards** | 8202 | Imagen, puertos, volúmenes, redes | Dashboard rendering, OpenSearch integration | Login interface, visualization dashboards |
| **Redis** | 6379 | Imagen, puertos, volúmenes, redes | Conectividad, autenticación | No aplicable (solo API) |

#### Threat Intelligence

| Servicio | Configuración | Runtime | Navegador |
|-------------|-----------------------------------|------------------------------|-----------------------------------------|
| **MISP** | Imagen, puertos, volúmenes, redes | Threat intelligence platform | Login interface, threat data management |
| **Redis** | Imagen, puertos, volúmenes, redes | Cache and message broker | No aplicable (data service) |
| **MariaDB** | Imagen, puertos, volúmenes, redes | Database for MISP | No aplicable (data service) |

##### 3.6.3.2 Validación de red

**Redes Esperadas:**

- **soar_net**: Internal service communication

**Pruebas de Red:**

- Network creation and configuration
- Container connectivity within networks
- Inter-network communication rules
- DNS resolution within networks
- Port exposure and routing

##### 3.6.3.3 Validación de volúmenes

**Volúmenes Esperados:**

- **es_data**: Elasticsearch data persistence
- **thehive_files**: TheHive case files
- **cortex_data**: Cortex analyzer data
- **shuffle_app_storage**: Shuffle workflow apps
- **shuffle_file_storage**: Shuffle workflow files
- **misp_data**: MISP database and files
- **misp_logs**: MISP logs
- **misp_uploads**: MISP file uploads
- **misp_gpg**: MISP GPG keys
- **misp_smime**: MISP S/MIME keys
- **misp_ca**: MISP CA certificates
- **redis_data**: Redis persistence
- **mariadb_data**: MariaDB database persistence

**Pruebas de Volúmenes:**

- Volume creation and mounting
- Data persistence across restarts
- File permissions and ownership
- Backup and restore capabilities

#### 3.6.4 Ejecución de pruebas

##### 3.6.4.1 Comandos de ejecución

Los comandos canónicos para ejecutar tests del stack Docker son los targets `make`. `pytest` directo funciona para desarrollo aislado pero no configura el entorno completo.

**Ejecutar todas las pruebas:**

```bash
make test-all
```

**Ejecutar pruebas por nivel:**

```bash
make test-unit # No requiere Docker
make test-integration # Requiere make up + make health
make test-e2e # Requiere stack completo
```

**Ejecutar pruebas de configuración directas:**

```bash
python -m pytest tests/integration/test_docker_build_validation.py -v
```

**Ejecutar pruebas de runtime directas:**

> Ver comando en [Fase 2: pruebas de runtime](#3622-fase-2-pruebas-de-runtime).

**Ejecutar pruebas de navegador directas:**

```bash
python -m pytest tests/e2e/TC-14/test_complete_soar_integration.py -v
```

**Generar reporte de cobertura:**

```bash
make test-coverage
```

> Los reportes se generan en `runtime/coverage/htmlcov/` y `runtime/coverage/coverage.xml`.

**Controles previos en CI:**

```bash
python -m pytest --collect-only -q
make docs-lint
```

##### 3.6.4.2 Integración CI/CD

Las pruebas se integran en GitHub Actions mediante workflows en `.github/workflows/`:

- Ejecución automática en cada PR a main
- Validación de configuración Docker Compose en CI
- Validación de runtime en rama main
- Reportes de cobertura de código

#### 3.6.5 Reportes y métricas

##### 3.6.5.1 Reportes generados

- **Reportes pytest**: Resultados de ejecución de pruebas
- **Cobertura de código**: Porcentaje de código cubierto por pruebas
- **Logs de contenedores**: Registros de ejecución de servicios
- **Capturas de pantalla**: Evidencias de pruebas de navegador
- **Métricas de rendimiento**: Tiempos de respuesta, uso de recursos

##### 3.6.5.2 Métricas clave

| Métrica | Objetivo | Método de Medida |
|--------------------------------------|----------|-------------------------------|
| **Tasa de éxito** | ≥ 95% | Porcentaje de pruebas pasadas |
| **Cobertura de código** | ≥ 80% | pytest-cov |
| **Tiempo de ejecución** | ≤ 5 min | pytest --durations |
| **Tiempo de inicio de contenedores** | ≤ 2 min | docker ps + timestamps |

#### 4. Validación

##### 4.1 Verificación

#### 4.1.1 Validación de health checks

**Métodos de Health Check:**

- Docker native health checks
- HTTP endpoint validation
- TCP port connectivity
- Service-specific health endpoints

**Pruebas de Health Check:**

- Container startup time
- Health check frequency
- Failure detection and recovery
- Health status reporting para servicios core (Elasticsearch, TheHive, Cortex, Shuffle Dashboard, MISP)

#### 4.1.2 Validación de rendimiento

**Métricas Recopiladas:**

- Container startup time
- Memory usage patterns
- CPU utilization
- Network I/O
- Disk I/O
- Response times

**Pruebas de Rendimiento:**

- Resource limit validation
- Performance regression detection
- Scalability testing
- Load testing scenarios

#### 4.1.3 Validación de seguridad

**Headers de Seguridad Probados:**

- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security
- Content-Security-Policy

**Pruebas de Seguridad:**

- Authentication endpoint validation
- Authorization testing
- SSL/TLS certificate validation
- Secure communication testing
- Vulnerability scanning integration

##### 4.2 Criterios de Aceptación

Las pruebas de Docker se consideran exitosas cuando:

- Todas las pruebas de configuración pasan sin errores
- Todos los contenedores inician correctamente y reportan estado healthy
- Todos los servicios son accesibles en sus puertos esperados
- La comunicación entre servicios funciona correctamente
- Los volúmenes se montan correctamente y persisten datos
- Las interfaces web cargan sin errores de consola
- Los headers de seguridad están configurados correctamente
- Las métricas de rendimiento están dentro de los límites aceptables

#### 4.3 Evidencias

Las evidencias de ejecución de pruebas incluyen:

- Reportes de pytest con resultados de pruebas
- Logs de contenedores sin errores críticos
- Capturas de pantalla de interfaces web (para pruebas de navegador)
- Métricas de rendimiento recopiladas
- Reportes de seguridad (headers, vulnerabilidades)

#### 5. Problemas

##### 5.1 Limitaciones

#### 5.1.1 Limitaciones de pruebas de configuración

- No valida el inicio real de servicios
- No prueba la conectividad de red real
- No valida la funcionalidad de servicios

#### 5.1.2 Limitaciones de pruebas de runtime

- Requiere Docker daemon ejecutándose
- Requiere recursos del sistema suficientes
- Puede ser lento en comparación con pruebas de configuración

#### 5.1.3 Limitaciones de pruebas de navegador

- Requiere instalación de navegador y WebDriver
- Puede ser frágil debido a cambios en UI
- Requiere servicios ejecutándose

##### 5.2 Riesgos o incidencias

#### 5.2.1 Docker daemon not running

- Start Docker service
- Check Docker permissions
- Verify Docker installation

#### 5.2.2 Port conflicts

- Check port availability
- Update port mappings
- Stop conflicting services

#### 5.2.3 Resource constraints

- Check system resources
- Adjust memory limits
- Monitor disk space

#### 5.2.4 Network connectivity

- Verify network creation
- Check firewall rules
- Validate DNS resolution

#### 5.2.5 Volume mounting

- Check volume permissions
- Verify mount points
- Validate disk space

##### 5.3 Recomendaciones / troubleshooting

#### 5.3.1 Comandos de debug

**Comandos de Debug:**

```bash
# Check Docker status
docker version
docker info

# Check running containers
docker ps
docker compose ps

# Check container logs
docker logs <container_name>
docker compose logs <service_name>

# Check network status
docker network ls
docker network inspect <network_name>

# Check volume status
docker volume ls
docker volume inspect <volume_name>

# Check resource usage
docker stats
docker system df
```

#### 5.3.2 Integración CI/CD

**Integración CI/CD:**

La estrategia de pruebas se integra con GitHub Actions mediante tres jobs:

- `docker-config`: Ejecuta pruebas de configuración sin Docker
- `docker-runtime`: Ejecuta pruebas de runtime con Docker-in-Docker
- `browser-tests`: Ejecuta pruebas de navegador con Chrome

#### 5.3.3 Mejoras futuras

1. Multi-platform testing (Windows, Linux, cross-platform)
2. Performance benchmarking (baseline metrics, regression detection)
3. Security scanning (container image vulnerability, network security)
4. Monitoring integration (real-time monitoring, alert integration)
5. Automated remediation (self-healing tests, automatic issue detection)

#### 6. Referencias

- **Project Repository**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/
- **pytest Documentation**: https://docs.pytest.org/
- **Playwright Documentation**: https://playwright.dev/
- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **Shuffle Documentation**: https://shuffler.io/docs
- **TheHive Documentation**: https://docs.strangebee.com/thehive/
- **Cortex Documentation**: https://docs.strangebee.com/cortex/


### 3.7 Ejecución y evidencias

#### 1. Resumen

#### 1.1 Objetivo

Este directorio contiene documentación integral para la suite de pruebas del SOAR Ransomware Lab.

#### 1.2 Contexto

El proyecto SOAR Ransomware Lab incluye una suite de pruebas integral que cubre pruebas unitarias, pruebas de
integración, pruebas de navegador, pruebas de rendimiento, pruebas de seguridad y pruebas de extremo a extremo (E2E).

#### 2. Alcance

#### 2.1 Qué cubre

Este documento cubre:

- Visión general de la suite de pruebas del SOAR Ransomware Lab
- Estructura de la suite de pruebas (unit, atomic, integration, browser, performance, security, e2e)
- Stack actual de servicios validados
- Comandos de inicio rápido para ejecutar pruebas
- Objetivos de cobertura por categoría de pruebas

#### 2.2 Límites

Este documento no cubre:

- Detalle de casos de prueba específicos (ver [3.3 Casos de prueba](#323-casos-de-prueba))
- Estrategia detallada de pruebas de Docker (ver [3.6 Pruebas con Docker](#36-pruebas-con-docker))
- Arquitectura detallada del sistema (ver docs/02-architecture.md)

#### 2.3 Dependencias

Este documento depende de:

- Documentación de arquitectura (docs/02-architecture.md)
- README principal del proyecto (/README.md)

#### 3. Contenido principal

#### 3.1 Estrategia de pruebas

#### Archivos de Documentación

Este documento es la fuente canónica de la suite de pruebas. La estrategia de pruebas de Docker se cubre en
[3.6 Pruebas con Docker](#36-pruebas-con-docker).

#### Estructura de la Suite de Pruebas

```
tests/
├── unit/ # Pruebas unitarias para componentes individuales
├── atomic/ # Pruebas atómicas para validación granular de funciones
├── integration/ # Pruebas de integración para interacciones de componentes
├── browser/ # Pruebas de navegador con automatización Selenium (no activas; se usan pruebas E2E)
├── performance/ # Pruebas de rendimiento y estrés
├── security/ # Pruebas de escaneo de seguridad y vulnerabilidades
├── e2e/ # Pruebas de flujo de trabajo de extremo a extremo
├── general/ # Pruebas transversales no asociadas a una categoría
├── conftest.py # Configuración de pytest y fixtures
└── runners/ # Utilidades de ejecución de pruebas
```

#### Stack Actual

La suite de pruebas valida los siguientes servicios:

- **Elasticsearch** (localhost:8200) - Motor de búsqueda y analytics
- **TheHive** (localhost:8100) - Plataforma de respuesta a incidentes
- **Cortex** (localhost:8101) - Motor de análisis de amenazas
- **Shuffle** (localhost:8081) - Orquestación de workflows
- **MISP** (localhost:8083) - Plataforma de inteligencia de amenazas
- **Redis** - Caché y broker de mensajes
- **PostgreSQL** - Base de datos para TheHive
- **MariaDB** - Base de datos para MISP

#### 3.2 Tipos de pruebas

#### Estado Actual de las Pruebas

**Nota Importante:** La estructura actual de pruebas ha sido reconciliada con la implementación. Última actualización: 2026-08-21.

```
# Conteo de archivos test_*.py por categoría
- unit: 79 archivos
- integration: 30 archivos
- e2e: 48 archivos (TC-00..TC-33, TC-KPI-01..06)
- atomic: 4 archivos
- architecture: 1 archivo
- performance: 4 archivos
- security: 1 archivo
- quality: 14 archivos
- general: 2 archivos
- Total: 184 archivos, ~2233 funciones definidas
```

```
# Recolección canónica
python -m pytest --collect-only -q
collected 2233 items / 328 deselected / 1905 selected
```

> Todos los errores previos de recolección (`ModuleNotFoundError`, `NameError`, `SyntaxError`) están resueltos. La fuente de verdad para conteos detallados es `tests/baseline/tests_inventory.json`.

**Objetivo de Cobertura:**

- El objetivo mínimo es **≥ 80% de coverage**
- **Estado actual**: `pytest --collect-only` finaliza con 0 errores de importación/sintaxis; 1905 casos seleccionados (2233 totales con e2e)
- Las pruebas unitarias cubren la mayoría del código Python en `src/soar_lab/`
- El reporte de coverage se genera con `make test-coverage` (ver `runtime/coverage/`)

**Dependencias de Pruebas:**

- **Unit tests**: Usan mocks (unittest.mock) para aislar componentes. No dependen de infraestructura real.
- **Integration tests**: Pueden requerir servicios Docker ejecutándose. Algunos usan infraestructura real.
- **E2E tests**: Requieren el stack completo de Docker Compose ejecutándose.

#### Inicio Rápido

```bash
# Listar casos recolectables antes de ejecutar
python -m pytest --collect-only -q

# Ejecutar todas las pruebas
make test-all

# Ejecutar categorías específicas de pruebas
make test-unit
make test-atomic
make test-integration
make test-smoke
make test-e2e

# Ejecutar con cobertura
make test-coverage

# Ejecutar suite E2E remota desde la API (requiere token JWT)
curl -s -X POST http://localhost:8000/tests/run \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"category":"e2e","coverage":false}'
```

> Los resultados exactos dependen del entorno y del estado de los servicios Docker. Consulta las secciones anteriores de este documento para detalles
> de recolección, reportes y ejecución remota.

#### 3.7.3 Herramientas y frameworks

##### Objetivos de Cobertura

| Categoría de Pruebas | Objetivo de Cobertura |
|------------------------|-----------------------|
| Pruebas unitarias | >80% |
| Pruebas atómicas | >70% |
| Pruebas de integración | >60% |
| Pruebas de navegador | >50% |
| Pruebas de seguridad | >60% |
| Pruebas E2E | >50% |

#### 3.7.4 Ejecución de pruebas

##### Comandos de Ejecución

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

#### Entornos de Ejecución

- **Local**: Ejecución en máquina de desarrollo
- **CI/CD**: Ejecución automática en GitHub Actions
- **Docker**: Ejecución dentro de contenedores
- **Remoto vía API / Web Management**: a través del endpoint `POST /tests/run` delegado a `PytestTestRunner`
 (`src/soar_lab/infrastructure/pytest_test_runner.py`). Ver [sección 3.4.3](#3243-ejecución-remota-vía-pytesttestrunner).

#### 3.7.5 Reportes y métricas

##### Reportes Generados

- **Reportes pytest**: Resultados de ejecución de pruebas
- **Cobertura de código**: Porcentaje de código cubierto por pruebas
- **Logs de ejecución**: Registros de ejecución de pruebas
- **Capturas de pantalla**: Evidencias de pruebas de navegador

#### Métricas Clave

| Categoría de Pruebas | Objetivo de Cobertura |
|------------------------|-----------------------|
| Pruebas unitarias | >80% |
| Pruebas atómicas | >70% |
| Pruebas de integración | >60% |
| Pruebas de navegador | >50% |
| Pruebas de seguridad | >60% |
| Pruebas E2E | >50% |

#### 4. Validación

#### 4.1 Verificación

Todas las pruebas han sido corregidas y ahora están pasando. No se necesitan eliminaciones de pruebas actualmente.

#### 4.2 Criterios de Aceptación

La suite de pruebas se considera exitosa cuando:

- Todas las categorías de pruebas alcanzan sus objetivos de cobertura

- Todos los servicios del stack son validados correctamente
- Las pruebas se ejecutan sin errores en los entornos local y CI/CD
- Los reportes de cobertura muestran los porcentajes esperados

#### 4.3 Evidencias

Las evidencias de ejecución de pruebas incluyen:

- Reportes de pytest con resultados de pruebas
- Reportes de cobertura de código
- Logs de ejecución de pruebas
- Resultados de pruebas de navegador (capturas de pantalla)
- Reportes de seguridad y vulnerabilidades

#### 5. Problemas

#### 5.1 Limitaciones

**Limitaciones de Pruebas de Navegador:**

- Requiere instalación de navegador y WebDriver
- Puede ser frágil debido a cambios en UI
- Requiere servicios ejecutándose

**Limitaciones de Pruebas de Seguridad:**

- Requiere herramientas de escaneo de vulnerabilidades
- Puede ser lento en comparación con otras categorías
- Requiere acceso a servicios externos para algunas validaciones

#### 5.2 Riesgos o incidencias

No hay riesgos o incidencias conocidas actualmente. Todas las pruebas han sido corregidas y están pasando.

#### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**

- Ejecutar pruebas de configuración de Docker antes de pruebas de runtime
- Ejecutar pruebas de navegador solo cuando los servicios estén ejecutándose
- Revisar los reportes de cobertura regularmente para identificar áreas de mejora
- Mantener actualizada la documentación de pruebas eliminadas

**Troubleshooting:**

- Para problemas de ejecución de pruebas, revisar [3.2.4 Ejecución de pruebas](#324-ejecución-de-pruebas)
- Para problemas de pruebas de Docker, revisar [3.6 Pruebas con Docker](#36-pruebas-con-docker)
- Para problemas de configuración del entorno, revisar docs/02-architecture.md

#### 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Arquitectura**: [docs/02-architecture.md](02-architecture.md)
- **README Principal**: [/README.md](../README.md)
- **Documentación de pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing


---

#### 4. Validación

#### 4.1 Verificación

La validación se realiza mediante tests automatizados, health checks y verificación manual del stack.

#### 4.2 Criterios de aceptación

- Todos los servicios críticos responden a health checks
- Los tests unitarios y de integración pasan sin errores
- El composition root cablea correctamente las dependencias

#### 4.3 Evidencias

- Resultados de `pytest` en CI
- `docker ps` mostrando servicios healthy
- Reportes de cobertura en `runtime/coverage/`

---

#### 5. Problemas

#### 5.1 Limitaciones

- Algunos componentes requieren Docker-in-Docker para funcionar completamente
- Elasticsearch single-node: estado `yellow` es normal

#### 5.2 Riesgos o incidencias

- Dependencia de imágenes Docker externas para servicios core
- Fragmentación de configuración entre múltiples archivos Compose

#### 5.3 Recomendaciones / troubleshooting

- Usar `make health` tras `make up` para verificar el stack
- Revisar `make logs` si un servicio no responde
- Consultar [04-operations.md](04-operations.md) para troubleshooting detallado

---

## 4. Validación

### 4.1 Verificación

La suite ha sido depurada de referencias a módulos heredados y errores de sintaxis. `pytest --collect-only` finaliza sin errores de importación (`0 errors`). Los conteos se actualizan de forma reproducible con `tests/baseline/tests_inventory.json`.

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

## 5. Problemas

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
pytest -v -s tests/unit/services/test_calc_kpis.py
```

**Modo de Depuración:**

```bash
pytest --pdb tests/unit/services/test_calc_kpis.py
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

3. **Docker Desktop / WSL en Windows:**
 - Activar integración de WSL2 y file sharing para el directorio del repo.
 - Usar PowerShell o WSL; en `cmd` puede fallar la interpretación de variables `$(...)`.
 - Si `make` no está disponible en Windows, usar `Makefile.win`: `make -f Makefile.win <target>` o ejecutar comandos equivalentes manualmente.

4. **Variables de entorno o `.env.full` ausentes:**
 - Asegurar `cp .env.example .env.full` y regenerar secretos: `make generate-secrets`.
 - Tras `make reset`, `make init-webhook` puede cambiar `SHUFFLE_DEFAULT_APIKEY`; actualizar `.env.full` o confiar en el self-heal de `ShuffleClient`.

5. **Contenedores sin acceso al socket de Docker:**
 - Algunos tests `requires_docker` necesitan acceso al socket (`/var/run/docker.sock`). En Windows/WSL montar el socket correctamente o ejecutar esos tests desde el host.

##### 5.4 Matriz de incongruencias (FASE 49)

Se mantiene la matriz de incongruencias detectadas entre documentación, código, infraestructura y tests en [`docs/06-project-management.md`](06-project-management.md).

Los puntos principales son:

- `.env.full` sigue en el historial de Git (no se purga por decisión del usuario).
- Algunos `docker-compose` y scripts de mantenimiento conservan valores fallback para contraseñas; deben prevalecer las variables de `.env.full`.
- Tests unitarios usan contraseñas dummy (aceptable con mocks), pero tests de integración deben evitar secrets hardcodeados.
- `grafana-datasources.yml` generado en runtime está en `.gitignore`; el template usa placeholders.

#### 6. Gobernanza del backlog y evidencias (FASEs 54–65)

- El plan consolidado de trazabilidad, gobernanza, validación reproducible, arquitectura, seguridad, API, Docker, observabilidad, testing y cierre se encuentra en [`docs/06-project-management.md`](06-project-management.md).
- Plantilla de manifiesto de evidencias y convención de retención definidas en ese documento.
- Registro de decisiones documentales y checklist de privacidad antes de publicar artefactos.

#### 7. Arquitectura hexagonal

- `tests/architecture/test_hexagonal_imports.py` valida que `src/soar_lab/domain` no importe `infrastructure`, `interfaces`, `application`, `scripts`, etc.
- Marcador registrado en `pytest.ini`: `pytest -m architecture`.

#### 8. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Plan de Gobernanza y Validación**: [06-project-management.md](06-project-management.md)
- **README Principal**: [/README.md](../README.md)
- **Documentación del Proyecto**: [../](../)

---

#### Navegación

- [Instalación y guía rápida](01-getting-started.md)
- [Arquitectura hexagonal, Docker, código, seguridad](02-architecture.md)
- [API REST, endpoints e integraciones](03-api-and-integrations.md)
- [Configuración, infraestructura, backups, troubleshooting](04-operations.md)
- [Objetivos, plan, riesgos, auditorías](06-project-management.md)
- [Glosario](glossary.md)
- [Índice](index.md)
## 6. Referencias

- [02-architecture.md](02-architecture.md)
- [04-operations.md](04-operations.md)
- [glossary.md](glossary.md)


---

## Anexo: Estrategia de Testing Consolidada


Referencia TFM: complementa el Capítulo 4 (Desarrollo específico) y el Anexo D (Validación).
Datos extraídos de este documento, `reports/test-review/`, `reports/quality/`,
`reports/holistic/` y `tests/`.

---

### E.1. Visión General

El laboratorio SOAR implementa una estrategia de testing exhaustiva basada en la pirámide
de tests con pytest (pytest, 2024), con cobertura de calidad medida por 3 sistemas independientes:

| Sistema | Score | Dimensiones |
|---------|-------|-------------|
| Quality Score | 92.2/100 | 8 categorías (coverage, complexity, security, linting, typing, docs, architecture, maintainability) |
| Holistic Project Radar | 96.0/100 | 15 dimensiones en 5 capas (core, tests, quality, infra, docs) |
| Test Review | 92.2/100 | 7 dimensiones (pirámide, salud, aislamiento, complejidad, duplicación) |

---

### E.2. Inventario de Tests

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

### E.3. Cobertura de Código

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

### E.4. Marcadores de pytest

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

### E.5. Tests E2E (48 archivos, 281 tests)

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

### E.6. Salud y Aislamiento

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

### E.7. Complejidad y Duplicación

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

### E.8. Mutation Testing

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

### E.9. Requisitos de Cobertura

| Tipo | Umbral | Actual |
|------|--------|--------|
| Coverage general | 80% | 84.6% Sí |
| Funciones críticas | 80% | Sí |
| Funciones de seguridad | 90% | Sí |
| Mutation testing (general) | 70% | 51.8% Parcial |
| Mutation testing (críticas) | 80% | Pendiente |

---

### E.10. Flujo de Ejecución Canónico

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

### E.11. Prerrequisitos por Categoría

| Categoría | Python | Docker | .env.full | Stack Up | Shuffle Init |
|-----------|--------|--------|-----------|----------|--------------|
| Unit/Atomic | 3.11+ | No | placeholders | No | No |
| Integration | 3.11+ | Sí | real creds | Sí | Sí |
| E2E | 3.11+ | Sí | real creds | Sí | Sí |
| Performance | 3.11+ | Sí | real creds | Sí | Sí |
| Security | 3.11+ | No | placeholders | No | No |
| Smoke | 3.11+ | Sí | real creds | Sí | Sí |

---

### E.12. Quality Gates

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

### E.13. Resumen de Validación

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

