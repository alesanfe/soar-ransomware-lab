# Visión General del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Propósito del laboratorio](#31-propósito-del-laboratorio)
    - [3.2 Componentes principales](#32-componentes-principales)
        - [3.2.1 Plataformas SOAR](#321-plataformas-soar)
        - [3.2.2 Servicios de soporte](#322-servicios-de-soporte)
        - [3.2.3 Infraestructura](#323-infraestructura)
    - [3.3 Casos de uso](#33-casos-de-uso)
        - [3.3.1 Respuesta a incidentes](#331-respuesta-a-incidentes)
        - [3.3.2 Análisis de amenazas](#332-análisis-de-amenazas)
        - [3.3.3 Validación y aprendizaje](#333-validación-y-aprendizaje)
    - [3.4 Requisitos](#34-requisitos)
        - [3.4.1 Requisitos de hardware](#341-requisitos-de-hardware)
        - [3.4.2 Requisitos de software](#342-requisitos-de-software)
    - [3.5 Arquitectura de alto nivel](#35-arquitectura-de-alto-nivel)
        - [3.5.1 Modelo de despliegue](#351-modelo-de-despliegue)
        - [3.5.2 Redes y comunicación](#352-redes-y-comunicación)
        - [3.5.3 Persistencia y almacenamiento](#353-persistencia-y-almacenamiento)
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

Este documento proporciona una visión general del SOAR Ransomware Lab, un laboratorio mínimo viable (MSV) diseñado para
la respuesta automatizada ante incidentes de ransomware.

### 1.2 Contexto

El laboratorio SOAR Ransomware Lab integra múltiples herramientas de seguridad orquestación (SOAR), gestión de casos (
TheHive), análisis de amenazas (Cortex), e inteligencia de amenazas (MISP) para automatizar la respuesta ante incidentes
de ransomware en un entorno controlado y seguro.

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Propósito y objetivos del laboratorio
- Componentes principales y su función
- Casos de uso típicos
- Requisitos de hardware y software
- Arquitectura de alto nivel del sistema

### 2.2 Límites

Este documento es una visión general y no cubre:

- Detalle de configuración (ver [installation_guide.md](installation_guide.md))
- Guía de usuario detallada (ver [user_guide.md](user_guide.md))
- Arquitectura técnica detallada (ver [architecture/overview.md](../architecture/overview.md))

### 2.3 Dependencias

Este documento depende de:

- [installation_guide.md](installation_guide.md) - Guía de instalación
- [user_guide.md](user_guide.md) - Guía de usuario
- [architecture/overview.md](../architecture/overview.md) - Arquitectura detallada

## 3. Contenido principal

### 3.1 Propósito del laboratorio

El SOAR Ransomware Lab tiene como propósito principal:

- **Automatización**: Orquestar respuestas automatizadas ante incidentes de ransomware
- **Validación**: Validar la integración de herramientas SOAR en un entorno controlado
- **Aprendizaje**: Proporcionar un entorno educativo para aprender sobre SOAR y respuesta a incidentes
- **Investigación**: Permitir experimentación con workflows de seguridad y análisis de amenazas

### 3.2 Componentes principales

El laboratorio integra los siguientes componentes principales:

#### 3.2.1 Plataformas de orquestación y gestión de casos

- **Shuffle SOAR**: plataforma de orquestación de workflows de seguridad (v2.2.1).
- **TheHive**: plataforma de gestión de casos e incidentes (v3.5.2).
- **Cortex**: motor de análisis de observables e IOCs (v3.1.4).

#### 3.2.2 Inteligencia de amenazas y SIEM

- **MISP**: plataforma de inteligencia de amenazas.
- **Wazuh**: plataforma SIEM/XDR compuesta por `wazuh.manager`, `wazuh.indexer` y `wazuh.dashboard` (v4.14.0). Estado real: manager, indexer y dashboard operativos en Docker; alertas reales de endpoints requieren agentes adicionales.
- **Elasticsearch**: motor de búsqueda y métricas usado por TheHive, Cortex, Shuffle y Grafana.

#### 3.2.3 Aplicaciones propias

- **Lab API** (`apps/api`): API FastAPI con autenticación JWT, alertas, métricas, backups, tests y WebSocket de logs.
- **Web Management** (`apps/web-management`): SPA HTML/JS consumidora de la API; acceso por Nginx (`/`) y directo (`8085`).
- **Docs Site** (`apps/docs-site`): portal Docusaurus con la documentación del proyecto (`8086`).

#### 3.2.4 Infraestructura y soporte

- **Redis**: cache/cola con autenticación por contraseña.
- **MariaDB**: base de datos de MISP (`misp_db`).
- **PostgreSQL**: base de datos de Grafana (`grafana-db`).
- **Nginx**: proxy inverso y terminación TLS; punto de entrada canónico `https://soar.local`.
- **Loki + Promtail + Grafana**: stack de observabilidad centralizado (logs y KPIs).
- **Network Watcher**: servicio de diagnóstico y recuperación de conectividad para Shuffle workers.
- **Orborus**: ejecutor de contenedores de analizadores de Shuffle/Cortex.
- **Tenzir Node**: nodo de ingestión de logs/alertas (modo desarrollo).

> **Estado funcional:** Las capacidades de respuesta activa (aislamiento de red, bloqueo de cuentas, contención de endpoints) están **simuladas** salvo que se desplieguen agentes reales en endpoints gestionados.

### 3.3 Casos de uso

El laboratorio soporta los siguientes casos de uso:

#### 3.3.1 Respuesta a incidentes

- **Respuesta a ransomware** (simulada/parcial): detección y contención automatizada de incidentes de ransomware. Los workflows generan casos, notificaciones e IOCs, pero el aislamiento real de endpoints requiere agentes EDR desplegados.
- **Gestión de casos** (implementada): creación, enriquecimiento y seguimiento de casos en TheHive a partir de alertas del SOAR.

#### 3.3.2 Análisis de amenazas

- **Análisis de IoCs** (implementada): ejecución de analizadores de Cortex sobre IPs, dominios, hashes y URLs.
- **Enriquecimiento de alertas** (implementada): consulta de MISP y otras fuentes de inteligencia desde Shuffle para enriquecer observables.

#### 3.3.3 Validación y aprendizaje

- **Validación de integraciones** (implementada): pruebas unitarias, de integración, E2E, atómicas y de rendimiento ejecutadas con pytest y validadas vía Makefile.
- **Aprendizaje** (implementada): entorno educativo para experimentar con arquitectura hexagonal, pipelines SOAR e integraciones de seguridad.

### 3.4 Requisitos

#### 3.4.1 Requisitos de hardware

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

#### 3.4.2 Requisitos de software

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: para clonar el repositorio

### 3.5 Arquitectura de alto nivel

El laboratorio sigue una arquitectura basada en contenedores Docker con las siguientes características:

#### 3.5.1 Modelo de despliegue

- **Single-host**: Todos los servicios ejecutan en un único host
- **Contenedores Docker**: Cada servicio se ejecuta en un contenedor aislado
- **Docker Compose**: Orquestación de servicios mediante `docker compose`

#### 3.5.2 Redes y comunicación

- **Redes Docker**: Múltiples redes aisladas para comunicación entre servicios
- **Health checks**: Verificación de salud de servicios
- **Reverse proxy**: Nginx para acceso centralizado a servicios web

#### 3.5.3 Persistencia y almacenamiento

- **Persistencia de datos**: bind mounts bajo `artifacts/data/` para mayoría de servicios; volúmenes Docker normales para `misp_db` y Wazuh indexer/dashboard.
- **Elasticsearch**: motor de búsqueda y métricas usado por TheHive, Cortex, Shuffle y Grafana.
- **PostgreSQL**: base de datos de Grafana (`grafana-db`).
- **MariaDB**: base de datos de MISP (`misp_db`).
- **Redis**: cache/cola con autenticación por contraseña.

## 4. Validación

### 4.1 Verificación

El laboratorio se considera funcional cuando:

- Todos los servicios se inician correctamente
- Los health checks reportan estado healthy
- Los servicios son accesibles en sus puertos esperados
- El playbook E2E se ejecuta sin errores

### 4.2 Criterios de aceptación

El laboratorio se considera aceptado cuando:

- El playbook E2E se ejecuta en ≤ 180s (p90)
- Todos los servicios son accesibles y funcionales
- Las métricas de rendimiento cumplen los umbrales establecidos
- La documentación está completa y actualizada

### 4.3 Evidencias

Las evidencias de funcionamiento incluyen:

- Logs de contenedores sin errores críticos
- Ejecuciones de workflows exitosas en Shuffle
- Casos creados en TheHive
- Análisis ejecutados en Cortex
- Métricas de rendimiento recopiladas

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones del entorno:**

- **Single-host**: el stack completo se ejecuta en un único nodo Docker; no soporta alta disponibilidad ni clustering.
- **Recursos limitados**: requiere al menos 16 GB de RAM y 4 cores para el stack completo; con 8 GB se pueden omitir perfiles opcionales.
- **Respuesta activa simulada**: el aislamiento de red, bloqueo de cuentas y contención de endpoints se simulan mediante workflows; no se ejecutan acciones reales sobre endpoints sin agentes EDR desplegados.
- **Entorno de laboratorio**: no es apto para producción sin hardening adicional (TLS revalidado, secretos rotados, firewalls, RBAC, etc.).

### 5.2 Riesgos o incidencias

**Riesgos de Seguridad:**

- Uso de contraseñas predeterminadas que deben cambiarse
- Exposición de servicios en puertos conocidos
- Necesidad de hardening adicional para producción

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**

- Cambiar todas las contraseñas predeterminadas
- Usar en entornos aislados o de prueba
- No desplegar en producción sin hardening adicional
- Mantener actualizaciones de seguridad de imágenes Docker

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
