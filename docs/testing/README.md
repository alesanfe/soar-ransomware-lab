# Documentación de Pruebas

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Estrategia de pruebas](#31-estrategia-de-pruebas)
    - [3.2 Tipos de pruebas](#32-tipos-de-pruebas)
    - [3.3 Herramientas y frameworks](#33-herramientas-y-frameworks)
    - [3.4 Ejecución de pruebas](#34-ejecución-de-pruebas)
    - [3.5 Reportes y métricas](#35-reportes-y-métricas)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Limitaciones](#51-limitaciones)
    - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este directorio contiene documentación integral para la suite de pruebas del SOAR Ransomware Lab.

### 1.2 Contexto

El proyecto SOAR Ransomware Lab incluye una suite de pruebas integral que cubre pruebas unitarias, pruebas de
integración, pruebas de navegador, pruebas de rendimiento, pruebas de seguridad y pruebas de extremo a extremo (E2E).

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Visión general de la suite de pruebas del SOAR Ransomware Lab
- Archivos de documentación de pruebas (docker_testing_strategy.md)
- Estructura de la suite de pruebas (unit, atomic, integration, browser, performance, security, e2e)
- Stack actual de servicios validados
- Comandos de inicio rápido para ejecutar pruebas
- Objetivos de cobertura por categoría de pruebas

### 2.2 Límites

Este documento no cubre:

- Detalle de casos de prueba específicos (ver docs/testing/test_suite.md)
- Estrategia detallada de pruebas de Docker (ver docs/testing/docker_testing_strategy.md)
- Arquitectura detallada del sistema (ver docs/architecture/overview.md)

### 2.3 Dependencias

Este documento depende de:

- Documentación de pruebas (docs/testing/test_suite.md)
- Estrategia de pruebas de Docker (docs/testing/docker_testing_strategy.md)
- Documentación de arquitectura (docs/architecture/overview.md)
- README principal del proyecto (/README.md)

## 3. Contenido principal

### 3.1 Estrategia de pruebas

#### Archivos de Documentación

**[test_suite.md](test_suite.md):** Documentación principal de la suite de pruebas que cubre estructura, categorías,
ejecución, configuración, entornos y mejores prácticas.

**[docker_testing_strategy.md](docker_testing_strategy.md):** Estrategia integral de pruebas de Docker con enfoque
multinivel (configuración, runtime, validación de navegador).

#### Estructura de la Suite de Pruebas

```
tests/
├── unit/                    # Pruebas unitarias para componentes individuales
├── atomic/                  # Pruebas atómicas para validación granular de funciones
├── integration/             # Pruebas de integración para interacciones de componentes
├── browser/                 # Pruebas de navegador con automatización Selenium (no activas; se usan pruebas E2E)
├── performance/             # Pruebas de rendimiento y estrés
├── security/                # Pruebas de escaneo de seguridad y vulnerabilidades
├── e2e/                     # Pruebas de flujo de trabajo de extremo a extremo
├── general/                 # Pruebas transversales no asociadas a una categoría
├── conftest.py              # Configuración de Pytest y fixtures
├── TEST_ELIMINATIONS.md     # Documentación de pruebas eliminadas
└── runners/                 # Utilidades de ejecución de pruebas
```

#### Stack Actual

La suite de pruebas valida los siguientes servicios:

- **Elasticsearch** (localhost:19200) - Motor de búsqueda y analytics
- **TheHive** (localhost:19000) - Plataforma de respuesta a incidentes
- **Cortex** (localhost:19001) - Motor de análisis de amenazas
- **Shuffle** (localhost:8081) - Orquestación de workflows
- **Wazuh Dashboard** (localhost:15601) - Dashboard de visualización
- **Wazuh Manager** (localhost:55100) - Plataforma SIEM/XDR
- **MISP** (localhost:8083) - Plataforma de inteligencia de amenazas
- **Redis** - Caché y broker de mensajes
- **PostgreSQL** - Base de datos para TheHive
- **MariaDB** - Base de datos para MISP

### 3.2 Tipos de pruebas

#### Estado Actual de las Pruebas

**Nota Importante:** La estructura actual de pruebas ha sido reconciliada con la implementación. Última actualización: 2026-07-18.

```
# Conteo de archivos test_*.py por categoría
- unit:           66 archivos, 993 funciones definidas
- integration:    36 archivos, 420 funciones definidas
- e2e:            44 archivos, 285 funciones definidas
- atomic:          4 archivos, 110 funciones definidas
- performance:     4 archivos,  30 funciones definidas
- security:        1 archivo,   26 funciones definidas
- general:         2 archivos,  20 funciones definidas
- Total:         158 archivos, ~1884 funciones definidas
```

```
# Recolección canónica
python -m pytest --collect-only -q
collected 1944 items / 33 deselected / 1911 selected
```

> Todos los errores previos de recolección (`ModuleNotFoundError`, `NameError`, `SyntaxError`) están resueltos. La fuente de verdad para conteos detallados es `baseline/tests_inventory.json`.

**Objetivo de Cobertura:**

- El objetivo mínimo es **≥ 80% de coverage**
- **Estado actual**: `pytest --collect-only` finaliza con 0 errores de importación/sintaxis; 1911 casos seleccionados
- Las pruebas unitarias cubren la mayoría del código Python en `src/soar_lab/`
- El reporte de coverage se genera con `make test-coverage` (ver `artifacts/coverage/`)

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

> Los resultados exactos dependen del entorno y del estado de los servicios Docker. Consulta `test_suite.md` para detalles
> de recolección, reportes y ejecución remota.

### 3.3 Herramientas y frameworks

#### Objetivos de Cobertura

| Categoría de Pruebas   | Objetivo de Cobertura |
|------------------------|-----------------------|
| Pruebas unitarias      | >80%                  |
| Pruebas atómicas       | >70%                  |
| Pruebas de integración | >60%                  |
| Pruebas de navegador   | >50%                  |
| Pruebas de seguridad   | >60%                  |
| Pruebas E2E            | >50%                  |

### 3.4 Ejecución de pruebas

#### Comandos de Ejecución

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
  (`src/soar_lab/infrastructure/pytest_test_runner.py`). Ver [test_suite.md](test_suite.md#343-ejecución-remota-vía-pytesttestrunner).

### 3.5 Reportes y métricas

#### Reportes Generados

- **Reportes pytest**: Resultados de ejecución de pruebas
- **Cobertura de código**: Porcentaje de código cubierto por pruebas
- **Logs de ejecución**: Registros de ejecución de pruebas
- **Capturas de pantalla**: Evidencias de pruebas de navegador

#### Métricas Clave

| Categoría de Pruebas   | Objetivo de Cobertura |
|------------------------|-----------------------|
| Pruebas unitarias      | >80%                  |
| Pruebas atómicas       | >70%                  |
| Pruebas de integración | >60%                  |
| Pruebas de navegador   | >50%                  |
| Pruebas de seguridad   | >60%                  |
| Pruebas E2E            | >50%                  |

## 4. Validación

### 4.1 Verificación

Todas las pruebas han sido corregidas y ahora están pasando. No se necesitan eliminaciones de pruebas actualmente.

### 4.2 Criterios de Aceptación

La suite de pruebas se considera exitosa cuando:

- Todas las categorías de pruebas alcanzan sus objetivos de cobertura

- Todos los servicios del stack son validados correctamente
- Las pruebas se ejecutan sin errores en los entornos local y CI/CD
- Los reportes de cobertura muestran los porcentajes esperados

### 4.3 Evidencias

Las evidencias de ejecución de pruebas incluyen:

- Reportes de pytest con resultados de pruebas
- Reportes de cobertura de código
- Logs de ejecución de pruebas
- Resultados de pruebas de navegador (capturas de pantalla)
- Reportes de seguridad y vulnerabilidades

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de Pruebas de Navegador:**

- Requiere instalación de navegador y WebDriver
- Puede ser frágil debido a cambios en UI
- Requiere servicios ejecutándose

**Limitaciones de Pruebas de Seguridad:**

- Requiere herramientas de escaneo de vulnerabilidades
- Puede ser lento en comparación con otras categorías
- Requiere acceso a servicios externos para algunas validaciones

### 5.2 Riesgos o incidencias

No hay riesgos o incidencias conocidas actualmente. Todas las pruebas han sido corregidas y están pasando.

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**

- Ejecutar pruebas de configuración de Docker antes de pruebas de runtime
- Ejecutar pruebas de navegador solo cuando los servicios estén ejecutándose
- Revisar los reportes de cobertura regularmente para identificar áreas de mejora
- Mantener actualizada la documentación de pruebas eliminadas

**Troubleshooting:**

- Para problemas de ejecución de pruebas, revisar docs/testing/test_suite.md
- Para problemas de pruebas de Docker, revisar docs/testing/docker_testing_strategy.md
- Para problemas de configuración del entorno, revisar docs/architecture/docker_architecture.md

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Pruebas**: [docs/testing/test_suite.md](test_suite.md)
- **Estrategia de Pruebas de Docker**: [docs/testing/docker_testing_strategy.md](docker_testing_strategy.md)
- **Documentación de Arquitectura**: [docs/architecture/overview.md](../architecture/overview.md)
- **README Principal**: [/README.md](../README.md)
- **Auditorías e Informes Históricos**: [docs/audit/legacy/](../audit/legacy/)
- **Documentación de Pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing
