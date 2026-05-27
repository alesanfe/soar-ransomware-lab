# Documentación del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Visión general del proyecto](#31-visión-general-del-proyecto)
    - [3.2 Características principales](#32-características-principales)
    - [3.3 Arquitectura](#33-arquitectura)
    - [3.4 Inicio rápido](#34-inicio-rápido)
    - [3.5 Recursos adicionales](#35-recursos-adicionales)
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

Este directorio contiene toda la documentación del proyecto SOAR Ransomware Lab, incluyendo arquitectura, seguridad,
pruebas y guías de usuario.

### 1.2 Contexto

La documentación está organizada en tres categorías principales: documentación core, gestión de proyecto y pruebas. Cada
categoría contiene documentos específicos que cubren diferentes aspectos del proyecto.

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Estructura general de la documentación del proyecto
- Descripción de cada categoría de documentación
- Enlaces rápidos a documentos clave
- Pautas de mantenimiento de documentación

### 2.2 Límites

Este documento es un índice de documentación y no cubre:

- Detalle de arquitectura (ver docs/architecture/overview.md)
- Guías de usuario (ver docs/getting_started/user_guide.md)
- Planificación del proyecto (ver docs/project/plan.md)
- Estrategia de pruebas (ver docs/testing/test_suite.md)

### 2.3 Dependencias

Este documento depende de:

- Todos los documentos en el directorio docs/
- README principal del proyecto (/README.md)

## 3. Contenido principal

### 3.1 Visión general del proyecto

#### Getting Started

- **[getting_started/overview.md](getting_started/overview.md)** - Visión general del laboratorio
- **[getting_started/installation_guide.md](getting_started/installation_guide.md)** - Guía de instalación
- **[getting_started/user_guide.md](getting_started/user_guide.md)** - Guía de usuario y procedimientos operacionales

#### Architecture

- **[architecture/overview.md](architecture/overview.md)** - Arquitectura completa del sistema y diseño
- **[architecture/docker_architecture.md](architecture/docker_architecture.md)** - Arquitectura Docker, archivos compose
  y despliegue
- **[architecture/security.md](architecture/security.md)** - Consideraciones de seguridad y mejores prácticas

#### Operations

- **[operations/configuration_manual.md](operations/configuration_manual.md)** - Manual de configuración completo
- **[operations/playbooks/ransomware_playbook_e2e.md](operations/playbooks/ransomware_playbook_e2e.md)** - Documentación
  de playbook E2E
- **[operations/troubleshooting.md](operations/troubleshooting.md)** - Guía de troubleshooting

#### Integrations

- **[integrations/api_contracts.md](integrations/api_contracts.md)** - Especificaciones y contratos de APIs

#### Project Management

- **[project/scope.md](project/scope.md)** - Alcance y límites del proyecto
- **[project/objectives.md](project/objectives.md)** - Objetivos SMART y entregables
- **[project/plan.md](project/plan.md)** - Cronograma y roadmap del proyecto
- **[project/risks.md](project/risks.md)** - Gestión de riesgos y mitigación

#### Testing

- **[testing/README.md](testing/README.md)** - Índice de documentación de pruebas
- **[testing/test_suite.md](testing/test_suite.md)** - Documentación completa de la suite de pruebas
- **[testing/docker_testing_strategy.md](testing/docker_testing_strategy.md)** - Estrategia de pruebas de Docker

#### Thesis (TFM)

- **[thesis/](thesis/)** - Documentación completa de la Tesis de Máster (múltiples archivos)

### 3.2 Características principales

#### Enlaces Rápidos

- [Inicio Rápido](/README.md) - README principal del proyecto
- [Guía de Usuario](getting_started/user_guide.md) - Procedimientos operacionales
- [Visión General de Arquitectura](architecture/overview.md) - Diseño del sistema
- [Suite de Pruebas](testing/test_suite.md) - Documentación de pruebas

### 3.3 Arquitectura

No aplica. Este documento es un índice de documentación.

### 3.4 Inicio rápido

Para comenzar con el proyecto SOAR Ransomware Lab:

1. Leer la [Visión General](getting_started/overview.md) para entender el propósito del laboratorio
2. Consultar la [Guía de Instalación](getting_started/installation_guide.md) para instrucciones de instalación
3. Consultar la [Guía de Usuario](getting_started/user_guide.md) para procedimientos operacionales
4. Revisar la [Arquitectura](architecture/overview.md) para entender el diseño del sistema
5. Ejecutar la [Suite de Pruebas](testing/test_suite.md) para validar el entorno

### 3.5 Recursos adicionales

- **Documentación Académica (TFM)**: [thesis/](thesis/) - Documentación completa de la Tesis de Máster
- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Issues y Soporte**: GitHub Issues del repositorio

## 4. Validación

### 4.1 Verificación

La documentación se mantiene como parte del pipeline CI/CD del proyecto.

### 4.2 Criterios de Aceptación

La documentación se considera actualizada cuando:

- Todos los enlaces funcionan correctamente
- El contenido está sincronizado con la implementación
- Se sigue el formato y estilo establecido
- Todos los procedimientos y comandos documentados han sido probados

### 4.3 Evidencias

Las evidencias de actualización de documentación incluyen:

- Historial de commits en el repositorio
- Reviews de código en pull requests
- Verificación de enlaces en CI/CD

## 5. Problemas y consideraciones

### 5.1 Limitaciones

No aplica.

### 5.2 Riesgos o incidencias

**Riesgos de Desincronización:**

- La documentación puede desincronizarse de la implementación si no se actualiza regularmente
- Los enlaces pueden romperse si se reorganiza la estructura de archivos

### 5.3 Recomendaciones / troubleshooting

**Mantenimiento de Documentación:**

Para contribuciones:

1. Actualizar secciones relevantes al realizar cambios en el código
2. Mantener la documentación sincronizada con la implementación
3. Seguir el formato y estilo establecido
4. Probar todos los procedimientos y comandos documentados

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html

Para la información más actualizada, siempre referirse al repositorio principal del proyecto.
