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
├── browser/                 # Pruebas de navegador con automatización Selenium
├── performance/             # Pruebas de rendimiento y estrés
├── security/                # Pruebas de escaneo de seguridad y vulnerabilidades
├── e2e/                     # Pruebas de flujo de trabajo de extremo a extremo
├── conftest.py              # Configuración de Pytest y fixtures
├── TEST_ELIMINATIONS.md     # Documentación de pruebas eliminadas
└── runners/                 # Utilidades de ejecución de pruebas
```

#### Stack Actual

La suite de pruebas valida los siguientes servicios:

- **Elasticsearch** (localhost:9201) - Motor de búsqueda y analytics
- **TheHive** (localhost:9000) - Plataforma de respuesta a incidentes
- **Cortex** (localhost:9001) - Motor de análisis de amenazas
- **Shuffle** (localhost:8081) - Orquestación de workflows
- **Kibana** (localhost:15601) - Dashboard de visualización
- **Wazuh Manager** (localhost:55100) - Plataforma SIEM/XDR
- **MISP** (localhost:8082) - Plataforma de inteligencia de amenazas
- **Redis** - Caché y broker de mensajes
- **MariaDB** - Base de datos para TheHive, Cortex, MISP

### 3.2 Tipos de pruebas

#### Estado Actual de las Pruebas

**Nota Importante:** La estructura actual de pruebas difiere significativamente de la documentación anterior:

- **tests/unit/**: 37 archivos de prueba
- **tests/atomic/**: 4 archivos de prueba
- **tests/integration/**: 23 archivos de prueba
- **tests/e2e/**: 3 archivos de prueba
- **tests/performance/**: 2 archivos de prueba
- **tests/security/**: 2 archivos de prueba
- **tests/fixtures/**: 9 archivos de fixtures
- **tests/runners/**: 2 archivos de ejecutores

**Objetivo de Cobertura:**

- El objetivo mínimo es **≥ 80% de coverage**
- **Estado actual**: No se ha verificado recientemente si se cumple este objetivo
- Las pruebas unitarias cubren la mayoría del código Python en `src/soar_lab/`
- **Limitación**: No hay un reporte de coverage actual disponible en `artifacts/coverage/`

**Dependencias de Pruebas:**

- **Unit tests**: Usan mocks (unittest.mock) para aislar componentes. No dependen de infraestructura real.
- **Integration tests**: Pueden requerir servicios Docker ejecutándose. Algunos usan infraestructura real.
- **E2E tests**: Requieren el stack completo de Docker Compose ejecutándose.

#### Inicio Rápido

```bash
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
```

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
- **Documentación de Pytest**: https://docs.pytest.org/
- **Documentación de Playwright**: https://playwright.dev/
- **Documentación de Docker**: https://docs.docker.com/
- **Guía de Pruebas de Shuffle**: https://shuffler.io/docs/testing
