# Manual de Configuración del Laboratorio SOAR para Respuesta ante Ransomware

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Requisitos previos](#31-requisitos-previos)
        - [3.1.1 Componentes del laboratorio](#311-componentes-del-laboratorio)
        - [3.1.2 Fases de configuración](#312-fases-de-configuración)
    - [3.2 Proceso de configuración](#32-proceso-de-configuración)
        - [3.2.1 Paso 1: requisitos previos](#321-paso-1-requisitos-previos)
            - [3.2.1.1 Configuración de resolución de nombres (`soar.local`)](#3211-configuración-de-resolución-de-nombres-soarlocal)
        - [3.2.2 Paso 2: despliegue del stack core](#322-paso-2-despliegue-del-stack-core)
        - [3.2.3 Paso 3: configuración de Elasticsearch](#323-paso-3-configuración-de-elasticsearch)
        - [3.2.4 Paso 4: configuración de TheHive](#324-paso-4-configuración-de-thehive)
        - [3.2.5 Paso 5: configuración de Cortex](#325-paso-5-configuración-de-cortex)
        - [3.2.6 Paso 6: configuración de Shuffle](#326-paso-6-configuración-de-shuffle)
        - [3.2.7 Paso 7: registro de apps en Shuffle](#327-paso-7-registro-de-apps-en-shuffle)
        - [3.2.8 Paso 8: creación de workflows](#328-paso-8-creación-de-workflows)
        - [3.2.9 Paso 9: configuración de Wazuh](#329-paso-9-configuración-de-wazuh)
        - [3.2.10 Paso 10: configuración de MISP](#3210-paso-10-configuración-de-misp)
        - [3.2.11 Paso 11: pruebas end-to-end](#3211-paso-11-pruebas-end-to-end)
    - [3.3 Verificación de configuración](#33-verificación-de-configuración)
        - [3.3.1 Resumen de URLs de acceso](#331-resumen-de-urls-de-acceso)
        - [3.3.2 Scripts de automatización](#332-scripts-de-automatización)
        - [3.3.3 Arquitectura de integraciones](#333-arquitectura-de-integraciones)
        - [3.3.4 Validación de tests](#334-validación-de-tests)
        - [3.3.5 Checklist de verificación post-`make up'`](#335-checklist-de-verificación-post-make-up)
        - [3.3.6 Directorio de trabajo y contexto Docker](#336-directorio-de-trabajo-y-contexto-docker)
        - [3.3.7 Herramientas de calidad y CI](#337-herramientas-de-calidad-y-ci)
    - [3.4 Troubleshooting](#34-troubleshooting)
        - [3.4.1 Workers no se conectan a soar_net](#341-workers-no-se-conectan-a-soar_net)
        - [3.4.2 App TheHive no funciona](#342-app-thehive-no-funciona)
        - [3.4.3 Workflow se queda en "Step is still running"](#343-workflow-se-queda-en-step-is-still-running)
    - [3.5 Mantenimiento](#35-mantenimiento)
        - [3.5.1 Backups](#351-backups)
        - [3.5.2 Actualizaciones](#352-actualizaciones)
        - [3.5.3 Monitoreo](#353-monitoreo)
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

Este manual explica paso a paso cómo configurar el laboratorio SOAR completo para respuesta automatizada ante incidentes
de ransomware.

### 1.2 Contexto

El laboratorio SOAR integra múltiples herramientas (Shuffle, TheHive, Cortex, MISP, Wazuh, Elasticsearch) para orquestar
respuestas automatizadas a incidentes de seguridad. Este manual guía el proceso completo de configuración desde los
requisitos previos hasta las pruebas end-to-end.

## 2. Alcance

### 2.1 Qué cubre

Este manual cubre:

- Requisitos previos de hardware y software
- Despliegue del stack core con Docker Compose
- Configuración de Elasticsearch, TheHive, Cortex, Shuffle, Wazuh y MISP
- Registro de apps en Shuffle
- Creación de workflows
- Pruebas end-to-end
- Troubleshooting de problemas comunes
- Referencias y proyectos de investigación

### 2.2 Límites

Este manual no cubre:

- Estrategias de seguridad avanzadas (ver docs/architecture/security.md)
- Arquitectura detallada del sistema (ver docs/architecture/overview.md)
- Planificación del proyecto (ver docs/project/plan.md)
- Gestión de riesgos (ver docs/project/risks.md)
- Detalle del playbook E2E (ver docs/operations/playbooks/ransomware_playbook_e2e.md)

### 2.3 Dependencias

Este manual depende de:

- Documentación de arquitectura (`docs/architecture/overview.md`)
- Estructura del código y mapeo puertos/adaptadores (`docs/architecture/code_structure.md`)
- Composition Root (`docs/architecture/composition_root.md`)
- Documentación de Docker (`docs/architecture/docker_architecture.md`)
- Guía de usuario (`docs/getting_started/user_guide.md`)
- Especificación de APIs (`docs/integrations/api_contracts.md`)
- Tabla canónica de puertos y URLs (`docs/operations/ports_and_urls.md`)
- Manual de la CLI (`docs/operations/cli_manual.md`)
- Manual del Network Watcher (`docs/operations/network_watcher.md`)
- Guía de infraestructura (`docs/operations/infrastructure_guide.md`)
- Suite de pruebas (`docs/testing/test_suite.md`)
- Tests unitarios (`docs/testing/unit_tests.md`)
- Tests E2E (`docs/testing/e2e_tests.md`)

## 3. Contenido principal

### 3.1 Requisitos previos

#### 3.1.1 Componentes del laboratorio

- **Shuffle**: Plataforma de automatización SOAR.
- **TheHive**: Gestión de casos e incidentes.
- **Cortex**: Motor de análisis de observables.
- **MISP**: Plataforma de threat intelligence.
- **Wazuh**: SIEM/XDR (manager, indexer, dashboard).
- **Elasticsearch**: Motor de búsqueda y almacenamiento compartido.
- **Redis**: Cache/cola para Shuffle y API.
- **MariaDB**: Base de datos de MISP.
- **PostgreSQL**: Base de datos de Grafana (`grafana-db`).
- **Nginx**: Reverse proxy y terminación TLS (`https://soar.local`).
- **Loki + Promtail + Grafana**: Stack de observabilidad centralizado.
- **Network Watcher**: Reconexión dinámica de workers de Shuffle.
- **Orborus**: Ejecutor de contenedores de analizadores Cortex/Shuffle.

#### 3.1.2 Fases de configuración

1. **Requisitos Previos**: Verificación de hardware y software
2. **Despliegue del Stack Core**: Inicialización de contenedores
3. **Configuración de Servicios**: Elasticsearch, TheHive, Cortex, Shuffle
4. **Registro de Apps**: Integración de servicios con Shuffle
5. **Creación de Workflows**: Definición de flujos de automatización
6. **Configuración de Wazuh y MISP**: Integración SIEM y threat intelligence
7. **Pruebas End-to-End**: Validación de integraciones

### 3.2 Proceso de configuración

Esta sección describe los pasos detallados para configurar el laboratorio SOAR completo.

#### 3.2.1 Paso 1: requisitos previos

**Hardware:**

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

**Software:**

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: para clonar el repositorio

**Verificar Instalación:**

```bash
docker --version
docker compose --version
python --version
```

#### 3.2.1.1 Configuración de resolución de nombres (`soar.local`)

Nginx expone la entrada principal en `https://soar.local`. Antes de iniciar el stack, añade la línea
`127.0.0.1 soar.local` al archivo `hosts` del sistema operativo:

- **Windows**: `C:\Windows\System32\drivers\etc\hosts`
- **Linux / macOS**: `/etc/hosts`

En Windows se requieren privilegios de administrador para editar el archivo; elijo un editor con
permisos elevados. Si no se configura el `hosts`, accede directamente a los servicios por `http://localhost:<puerto>`.

#### 3.2.2 Paso 2: despliegue del stack core

**1. Clonar el Repositorio:**

```bash
git clone <repo-url>
cd soar-ransomware-lab
```

**2. Configurar Variables de Entorno:**

El archivo canónico es `.env.full`. Se genera automáticamente a partir de `.env.example` (plantilla saneada con marcadores de relleno) y reemplaza todos los secretos por valores aleatorios. Puedes generarlo de tres formas equivalentes:

```bash
# Opción A: a través del Makefile (recomendado)
make generate-secrets

# Opción B: script Python directo
python src/soar_lab/scripts/setup/generate_env.py

# Opción C: CLI nativa del proyecto (tras `pip install -e .`)
soar-lab generate-secrets --env > .env.full
```

Todas producen una plantilla `.env` lista para copiar a `.env.full` como archivo canónico de despliegue. `make generate-secrets` es la opción más habitual porque no requiere tener el entorno Python instalado en el host.

Tras generarlo, revisa `.env.full` y ajusta los valores no secretos (puertos, hosts, perfiles) antes del despliegue. Los secretos generados nunca deben versionarse: `.env.full` y `.env` están en `.gitignore`.

> **Nota sobre secretos válidos:**
> - Las contraseñas de las bases de datos (MariaDB/PostgreSQL) **no deben contener `@` ni `!`** para evitar problemas de escaping en URLs de conexión.
> - Wazuh requiere una contraseña de alta complejidad: mayúsculas, minúsculas, números y un carácter especial permitido como `.` o `-` (p. ej. `<WAZUH_API_PASSWORD>`). No usar `@` ni `!`.

#### Catálogo de variables de entorno

A continuación se listan las variables del archivo `.env.full` (catálogo derivado de `.env.example`), indicando propósito, obligatoriedad, ejemplo/valor por defecto y consumidor. Todos los valores canónicos residen en `.env.full`; `.env.example` es solo una plantilla.

##### Proyecto y puertos

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `COMPOSE_PROJECT_NAME` | Nombre del proyecto Docker Compose | Sí (default: `soar`) | `soar` | Docker Compose |
| `THEHIVE_HTTP_PORT` | Puerto HTTP de TheHive | Sí (default: 19000) | `19000` | Docker Compose / TheHive |
| `CORTEX_HTTP_PORT` | Puerto HTTP de Cortex | Sí (default: 19001) | `19001` | Docker Compose / Cortex |
| `SHUFFLE_UI_PORT` | Puerto del frontend de Shuffle | Sí (default: 8081) | `8081` | Docker Compose / Shuffle |
| `SHUFFLE_API_PORT` | Puerto del backend de Shuffle | Sí (default: 15001) | `15001` | Docker Compose / Shuffle |
| `ELASTICSEARCH_PORT` | Puerto de Elasticsearch | Sí (default: 19200) | `19200` | Docker Compose / Elasticsearch |
| `OPENSEARCH_PORT` | Puerto de OpenSearch (migración) | Sí (default: 19201) | `19201` | Docker Compose / OpenSearch |
| `OPENSEARCH_DASHBOARDS_PORT` | Puerto de OpenSearch Dashboards | Sí (default: 15601) | `15601` | Docker Compose / OpenSearch |
| `REDIS_PORT` | Puerto de Redis | Sí (default: 6379) | `6379` | Docker Compose / Redis |
| `WAZUH_API_PORT` | Puerto de la API de Wazuh Manager | Sí (default: 55100) | `55100` | Docker Compose / Wazuh |
| `WAZUH_EVENTS_PORT` | Puerto de eventos Wazuh | Sí (default: 15141) | `15141` | Docker Compose / Wazuh |
| `WAZUH_ENROLLMENT_PORT` | Puerto de enrollment Wazuh | Sí (default: 1515) | `1515` | Docker Compose / Wazuh |
| `WAZUH_SYSLOG_PORT` | Puerto syslog de Wazuh | Sí (default: 514) | `514` | Docker Compose / Wazuh |
| `WAZUH_INDEXER_PORT` | Puerto interno del Wazuh Indexer | Sí (default: 9200) | `9200` | Docker Compose / Wazuh |
| `WAZUH_DASHBOARD_PORT` | Puerto del Wazuh Dashboard | Sí (default: 15601) | `15601` | Docker Compose / Wazuh |
| `HTTP_PORT` | Puerto HTTP de Nginx | Sí (default: 80) | `80` | Docker Compose / Nginx |
| `WEB_UI_PORT` | Puerto del Web Management | Sí (default: 8085) | `8085` | Docker Compose / Web Management |
| `API_PORT` | Puerto de la Lab API | Sí (default: 8000) | `8000` | Docker Compose / Lab API |
| `DOCS_PORT` | Puerto del docs-site de Docusaurus | Sí (default: 8086) | `8086` | Docker Compose / Docs site |
| `MISP_PORT` | Puerto de MISP | Sí (default: 8083) | `8083` | Docker Compose / MISP |
| `GRAFANA_PORT` | Puerto de Grafana | Sí (default: 8084) | `8084` | Docker Compose / Grafana |

##### Elasticsearch y OpenSearch

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `ELASTIC_USERNAME` | Usuario de Elasticsearch | Sí (default: `elastic`) | `elastic` | Elasticsearch |
| `ELASTIC_PASSWORD` | Contraseña de Elasticsearch | Sí (generado) | `<ELASTIC_PASSWORD>` | Elasticsearch |
| `ELASTIC_SECURITY_ENABLED` | Habilitar seguridad de Elasticsearch | Sí (default: `true`) | `true` | Elasticsearch |
| `ES_JAVA_OPTS` | Opciones de memoria de la JVM de Elasticsearch | Sí (default: `-Xms2g -Xmx2g`) | `-Xms2g -Xmx2g` | Elasticsearch |
| `OPENSEARCH_USERNAME` | Usuario de OpenSearch | Sí (default: `admin`) | `admin` | OpenSearch |
| `OPENSEARCH_PASSWORD` | Contraseña de OpenSearch | Sí (generado) | `<OPENSEARCH_PASSWORD>` | OpenSearch |
| `OPENSEARCH_SECURITY_ENABLED` | Habilitar seguridad de OpenSearch | Sí (default: `false`) | `false` | OpenSearch |

##### TheHive y Cortex

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `THEHIVE_SECRET` | Secret de TheHive | Sí (generado) | `<THEHIVE_SECRET>` | TheHive |
| `THEHIVE_API_KEY` | API key de TheHive | Sí (generado) | `<THEHIVE_API_KEY>` | TheHive / Lab API |
| `CORTEX_SECRET` | Secret de Cortex | Sí (generado) | `<CORTEX_SECRET>` | Cortex |
| `CORTEX_API_KEY` | API key de Cortex | Sí (generado) | `<CORTEX_API_KEY>` | Cortex / Lab API |

##### Shuffle

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `SHUFFLE_DEFAULT_USERNAME` | Usuario administrador de Shuffle | Sí (default: `admin`) | `admin` | Shuffle |
| `SHUFFLE_DEFAULT_PASSWORD` | Contraseña admin de Shuffle | Sí (generado) | `<SHUFFLE_DEFAULT_PASSWORD>` | Shuffle |
| `SHUFFLE_DEFAULT_APIKEY` | API key por defecto de Shuffle | Sí (generado; rota en cada despliegue) | `<SHUFFLE_DEFAULT_APIKEY>` | Shuffle / Lab API |
| `SHUFFLE_ORG_ID` | Identificador de organización de Shuffle | Sí (default: `soar-lab-org-default`) | `soar-lab-org-default` | Shuffle |
| `SHUFFLE_ENV_NAME` | Nombre del entorno de Shuffle | Sí (default: `Shuffle`) | `Shuffle` | Shuffle |
| `DOCKER_API_VERSION` | Versión de la API de Docker para Orborus | Sí (default: `1.45`) | `1.45` | Shuffle / Orborus |

##### Bases de datos y caché

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `POSTGRES_USER` | Usuario de PostgreSQL (TheHive DB) | Sí (default: `thehive`) | `thehive` | PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | Sí (generado) | `<POSTGRES_PASSWORD>` | PostgreSQL |
| `POSTGRES_DB` | Base de datos de PostgreSQL | Sí (default: `thehive`) | `thehive` | PostgreSQL |
| `REDIS_PASSWORD` | Contraseña de Redis | Sí (generado) | `<REDIS_PASSWORD>` | Redis |

##### MISP

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `MISP_HOSTNAME` | Hostname de MISP | Sí (default: `localhost`) | `localhost` | MISP |
| `MISP_DB_ROOT_PASSWORD` | Contraseña root de MariaDB de MISP | Sí (generado) | `<MISP_DB_ROOT_PASSWORD>` | MISP DB |
| `MISP_DB_NAME` | Nombre de la BD de MISP | Sí (default: `misp`) | `misp` | MISP DB |
| `MISP_DB_USER` | Usuario de la BD de MISP | Sí (default: `misp`) | `misp` | MISP DB |
| `MISP_DB_PASSWORD` | Contraseña de la BD de MISP | Sí (generado) | `<MISP_DB_PASSWORD>` | MISP DB |
| `MISP_ADMIN_EMAIL` | Email del admin de MISP | Sí (default: `admin@soar.local`) | `admin@soar.local` | MISP |
| `MISP_ADMIN_PASSWORD` | Contraseña del admin de MISP | Sí (generado) | `<MISP_ADMIN_PASSWORD>` | MISP |
| `MISP_ADMIN_ORG` | Organización admin de MISP | Sí (default: `SOAR Lab`) | `SOAR Lab` | MISP |
| `MISP_EMAIL` | Email de contacto de MISP | Sí (default: `noreply@soar.local`) | `noreply@soar.local` | MISP |
| `MISP_CONTACT` | Email de contacto del administrador | Sí (default: `admin@soar.local`) | `admin@soar.local` | MISP |
| `MISP_ENCRYPTION_KEY` | Clave de cifrado de MISP | Sí (generado) | `<MISP_ENCRYPTION_KEY>` | MISP |
| `MISP_SALT` | Salt de MISP | Sí (generado) | `<MISP_SALT>` | MISP |
| `MISP_API_KEY` | API key de MISP | Sí (generado) | `<MISP_API_KEY>` | MISP / Lab API |

##### Wazuh

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `WAZUH_API_USERNAME` | Usuario de la API de Wazuh | Sí (default: `wazuh-wui`) | `wazuh-wui` | Wazuh |
| `WAZUH_API_PASSWORD` | Contraseña de la API de Wazuh | Sí (generado) | `<WAZUH_API_PASSWORD>` | Wazuh |
| `WAZUH_CLUSTER_KEY` | Clave del cluster de Wazuh | Sí (generado) | `<WAZUH_CLUSTER_KEY>` | Wazuh Manager |
| `WAZUH_INDEXER_USERNAME` | Usuario del Wazuh Indexer | Sí (default: `admin`) | `admin` | Wazuh Indexer |
| `WAZUH_INDEXER_PASSWORD` | Contraseña del Wazuh Indexer | Sí (generado) | `<WAZUH_INDEXER_PASSWORD>` | Wazuh Indexer |
| `WAZUH_DASHBOARD_USERNAME` | Usuario del Wazuh Dashboard | Sí (default: `kibanaserver`) | `kibanaserver` | Wazuh Dashboard |
| `WAZUH_DASHBOARD_PASSWORD` | Contraseña del Wazuh Dashboard | Sí (generado) | `<WAZUH_DASHBOARD_PASSWORD>` | Wazuh Dashboard |

##### Grafana

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `GRAFANA_ADMIN_USER` | Usuario administrador de Grafana | Sí (default: `admin`) | `admin` | Grafana |
| `GRAFANA_ADMIN_PASSWORD` | Contraseña admin de Grafana | Sí (generado) | `<GRAFANA_ADMIN_PASSWORD>` | Grafana |
| `GRAFANA_DATABASE_HOST` | Host de la BD de Grafana | Sí (default: `grafana-db`) | `grafana-db` | Grafana |
| `GRAFANA_DATABASE_NAME` | Nombre de la BD de Grafana | Sí (default: `grafana`) | `grafana` | Grafana |
| `GRAFANA_DATABASE_USER` | Usuario de la BD de Grafana | Sí (default: `grafana`) | `grafana` | Grafana |
| `GRAFANA_DATABASE_PASSWORD` | Contraseña de la BD de Grafana | Sí (generado) | `<GRAFANA_DATABASE_PASSWORD>` | Grafana |

##### Web Management y Lab API

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `WEB_UI_USER` | Usuario del Web Management | Sí (default: `admin`) | `admin` | Web Management |
| `WEB_UI_PASSWORD` | Contraseña del Web Management | Sí (generado) | `<WEB_UI_PASSWORD>` | Web Management |
| `API_LOG_LEVEL` | Nivel de log de la Lab API | Sí (default: `INFO`) | `INFO` | Lab API |
| `API_AUTH_SECRET` | Secreto legacy de firma de tokens | Sí (generado; **legacy**) | `<API_AUTH_SECRET>` | Lab API (fallback) |
| `JWT_SECRET_KEY` | Secreto preferente de firma de tokens JWT | Sí (generado) | `<JWT_SECRET_KEY>` | Lab API |
| `JWT_EXPIRATION_MINUTES` | Tiempo de expiración del token JWT | Sí (default: 60) | `60` | Lab API |
| `JWT_ALGORITHM` | Algoritmo de firma JWT | Sí (default: `HS256`) | `HS256` | Lab API |
| `CORS_ORIGINS` | Orígenes permitidos para CORS | Sí (default: lista de localhost) | `http://localhost:8085,...` | Lab API |

> **Resolución de nombres duplicados:** La Lab API prioriza `JWT_SECRET_KEY`; `API_AUTH_SECRET` actúa como fallback legacy. No se usan `JWT_SECRET` ni `AUTH_SECRET_KEY`; si aparecen en documentación antigua, deben sustituirse por `JWT_SECRET_KEY` y `API_AUTH_SECRET` respectivamente.

##### Tokens de simulación y notificaciones

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `SIEM_WEBHOOK_TOKEN` | Token para el webhook de simulación SIEM | Sí (generado) | `<SIEM_WEBHOOK_TOKEN>` | Simulación / Shuffle |
| `EDR_SIM_TOKEN` | Token de simulación EDR | Sí (generado) | `<EDR_SIM_TOKEN>` | Simulación / Lab API |
| `FIREWALL_SIM_TOKEN` | Token de simulación de firewall | Sí (generado) | `<FIREWALL_SIM_TOKEN>` | Simulación / Lab API |
| `SMTP_HOST` | Servidor SMTP para notificaciones | No (default: `localhost`) | `localhost` | Lab API (notificaciones) |
| `SMTP_PORT` | Puerto SMTP | No (default: 25) | `25` | Lab API (notificaciones) |
| `SMTP_USER` | Usuario SMTP | No (default: vacío) | *(vacío)* | Lab API (notificaciones) |
| `SMTP_PASSWORD` | Contraseña SMTP | No (default: vacío) | *(vacío)* | Lab API (notificaciones) |

##### Playbook, analyzers y rate limiting

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `DECISION_SCORE_THRESHOLD` | Umbral de puntuación para decisiones del playbook | Sí (default: 80) | `80` | Lab API / Playbook |
| `WEBHOOK_RATE_LIMIT` | Límite de peticiones por minuto al webhook | Sí (default: 60) | `60` | Lab API / Shuffle |
| `WEBHOOK_PAYLOAD_MAX_SIZE` | Tamaño máximo del payload del webhook | Sí (default: 65536) | `65536` | Lab API / Shuffle |
| `MAX_CONCURRENT_ANALYZERS` | Analizadores concurrentes de Cortex | Sí (default: 3) | `3` | Cortex / Lab API |
| `ANALYZER_TIMEOUT` | Timeout de analizadores Cortex | Sí (default: 30) | `30` | Cortex |
| `ANALYZER_RETRIES` | Reintentos de analizadores Cortex | Sí (default: 1) | `1` | Cortex |

##### Logging, backups y opciones de desarrollo

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `LOG_LEVEL` | Nivel de log global | Sí (default: `INFO`) | `INFO` | Logging |
| `LOG_FORMAT` | Formato de log (`json` o `text`) | Sí (default: `json`) | `json` | Logging |
| `LOG_DIR` | Directorio de logs; vacío = consola | No (default: vacío) | *(vacío)* | Logging |
| `BACKUP_ENABLED` | Habilitar backups automáticos | Sí (default: `true`) | `true` | Backup |
| `BACKUP_SCHEDULE` | Cron de backups | Sí (default: `0 2 * * *`) | `0 2 * * *` | Backup |
| `BACKUP_RETENTION_DAYS` | Días de retención de backups | Sí (default: 30) | `30` | Backup |
| `BACKUP_ENCRYPTION` | Cifrar backups | Sí (default: `true`) | `true` | Backup |
| `BACKUP_COMPRESSION` | Comprimir backups | Sí (default: `true`) | `true` | Backup |
| `DEBUG_MODE` | Modo debug de la Lab API | No (default: `false`) | `false` | Lab API |
| `VERBOSE_LOGGING` | Logging verbose | No (default: `false`) | `false` | Logging |
| `HOT_RELOAD` | Recarga en caliente de la Lab API | No (default: `false`) | `false` | Lab API |

##### Límites de recursos de Docker

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `ELASTICSEARCH_CPU_LIMIT` | Límite CPU de Elasticsearch | Sí (default: 2.0) | `2.0` | Docker Compose |
| `ELASTICSEARCH_CPU_RESERVATION` | Reserva CPU de Elasticsearch | Sí (default: 1.0) | `1.0` | Docker Compose |
| `ELASTICSEARCH_MEMORY_LIMIT` | Límite memoria de Elasticsearch | Sí (default: 4G) | `4G` | Docker Compose |
| `ELASTICSEARCH_MEMORY_RESERVATION` | Reserva memoria de Elasticsearch | Sí (default: 2G) | `2G` | Docker Compose |
| `THEHIVE_CPU_LIMIT` | Límite CPU de TheHive | Sí (default: 2.0) | `2.0` | Docker Compose |
| `THEHIVE_CPU_RESERVATION` | Reserva CPU de TheHive | Sí (default: 1.0) | `1.0` | Docker Compose |
| `THEHIVE_MEMORY_LIMIT` | Límite memoria de TheHive | Sí (default: 4G) | `4G` | Docker Compose |
| `THEHIVE_MEMORY_RESERVATION` | Reserva memoria de TheHive | Sí (default: 2G) | `2G` | Docker Compose |
| `CORTEX_CPU_LIMIT` | Límite CPU de Cortex | Sí (default: 2.0) | `2.0` | Docker Compose |
| `CORTEX_CPU_RESERVATION` | Reserva CPU de Cortex | Sí (default: 1.0) | `1.0` | Docker Compose |
| `CORTEX_MEMORY_LIMIT` | Límite memoria de Cortex | Sí (default: 4G) | `4G` | Docker Compose |
| `CORTEX_MEMORY_RESERVATION` | Reserva memoria de Cortex | Sí (default: 2G) | `2G` | Docker Compose |
| `SHUFFLE_CPU_LIMIT` | Límite CPU de Shuffle | Sí (default: 2.0) | `2.0` | Docker Compose |
| `SHUFFLE_CPU_RESERVATION` | Reserva CPU de Shuffle | Sí (default: 1.0) | `1.0` | Docker Compose |
| `SHUFFLE_MEMORY_LIMIT` | Límite memoria de Shuffle | Sí (default: 4G) | `4G` | Docker Compose |
| `SHUFFLE_MEMORY_RESERVATION` | Reserva memoria de Shuffle | Sí (default: 2G) | `2G` | Docker Compose |
| `WAZUH_MANAGER_CPU_LIMIT` | Límite CPU de Wazuh Manager | Sí (default: 2.0) | `2.0` | Docker Compose |
| `WAZUH_MANAGER_CPU_RESERVATION` | Reserva CPU de Wazuh Manager | Sí (default: 1.0) | `1.0` | Docker Compose |
| `WAZUH_MANAGER_MEMORY_LIMIT` | Límite memoria de Wazuh Manager | Sí (default: 2G) | `2G` | Docker Compose |
| `WAZUH_MANAGER_MEMORY_RESERVATION` | Reserva memoria de Wazuh Manager | Sí (default: 1G) | `1G` | Docker Compose |
| `WAZUH_DASHBOARD_CPU_LIMIT` | Límite CPU de Wazuh Dashboard | Sí (default: 1.0) | `1.0` | Docker Compose |
| `WAZUH_DASHBOARD_CPU_RESERVATION` | Reserva CPU de Wazuh Dashboard | Sí (default: 0.5) | `0.5` | Docker Compose |
| `WAZUH_DASHBOARD_MEMORY_LIMIT` | Límite memoria de Wazuh Dashboard | Sí (default: 1G) | `1G` | Docker Compose |
| `WAZUH_DASHBOARD_MEMORY_RESERVATION` | Reserva memoria de Wazuh Dashboard | Sí (default: 512M) | `512M` | Docker Compose |

##### Imágenes y URLs externas

| Variable | Propósito | Obligatoriedad | Ejemplo / Valor por defecto | Consumidor |
|----------|-----------|----------------|-----------------------------|------------|
| `SHUFFLE_FRONTEND_IMAGE` | Imagen del frontend de Shuffle | Sí (default: `shuffler.io/frontend:1.3.0`) | `shuffler.io/frontend:1.3.0` | Docker Compose / Shuffle |
| `SHUFFLE_BACKEND_IMAGE` | Imagen del backend de Shuffle | Sí (default: `shuffler.io/shuffle:1.3.0`) | `shuffler.io/shuffle:1.3.0` | Docker Compose / Shuffle |
| `ORBORUS_IMAGE` | Imagen de Orborus | Sí (default: `shuffler.io/orborus:1.3.0`) | `shuffler.io/orborus:1.3.0` | Docker Compose / Orborus |
| `OUTER_HOSTNAME` | Hostname externo para URLs | Sí (default: `localhost`) | `localhost` | Lab API / Shuffle |
| `SHUFFLE_APP_DOWNLOAD_LOCATION` | URL de descarga de apps de Shuffle | Sí (default: URL GitHub) | `https://github.com/shuffle/python-apps` | Shuffle |

> **Nota:** `SOAR_LOCAL_HOST` no aparece en `.env.example`; el host canónico por defecto es `soar.local` y se configura en `infra/docker/config/nginx/nginx.conf`. Si se desea cambiar, edita dicho archivo y el `hosts` del sistema.

> Recuerda: `.env.full` y `.env` están en `.gitignore` y no deben publicarse. Para regenerar secretos, ejecuta `make generate-secrets`, `python src/soar_lab/scripts/setup/generate_env.py` o `soar-lab generate-secrets --env` según tu preferencia, revisa `.env.full` y vuelve a desplegar.

**3. Desplegar el Stack Completo:**

```bash
make up
```

Este comando despliega: Elasticsearch, Redis, TheHive, Cortex, Shuffle (frontend + backend + orborus), Network-watcher,
Tenzir Node, MISP, Wazuh, API FastAPI, docs-site, web-management, Nginx y el stack de observabilidad (Grafana, Loki,
Promtail, PostgreSQL).

> El orden y la disponibilidad de cada perfil dependen de `COMPOSE_FILE` y los perfiles definidos en `.env.full`.
> El stack mínimo se puede iniciar con `make up` (Makefile / Makefile.win).

**4. Verificar Estado de Servicios:**

```bash
docker ps
```

#### 3.2.3 Paso 3: configuración de Elasticsearch

**1. Verificar Elasticsearch esté Healthy:**

```bash
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:19200/_cluster/health
```

**2. Crear Índices Iniciales:**
Elasticsearch crea automáticamente los índices cuando Shuffle inicia, pero puedes verificar:

```bash
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:19200/_cat/indices?v
```

#### 3.2.4 Paso 4: configuración de TheHive

**1. Acceder a TheHive:**
URL: https://soar.local/thehive/ o http://localhost:19000/

**2. Credenciales de Admin:**

El usuario administrador se crea automáticamente durante el despliegue con `init_thehive.py`:

- Usuario: `admin`
- Contraseña: generada por `init_thehive.py` (consultar los logs del contenedor `soar_api` o `.env.full` si el script la guarda)
- API key: `THEHIVE_API_KEY` en `.env.full`

**3. Crear Organización:**

1. Ir a **Admin** > **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

**4. Generar API Key:**

1. Ir a tu perfil (click en tu nombre)
2. Click en **API Keys**
3. Click en **Create a new API Key**
4. Copiar la API Key (¡solo se muestra una vez!)

**IMPORTANTE**: Guardar esta API Key, se necesitará para configurar Shuffle.

**5. Configurar Webhook en TheHive:**

1. Editar `application.conf` de TheHive:

```bash
docker exec -it soar_thehive bash
vi /etc/thehive/application.conf
```

2. Agregar configuración de webhook:

```python
webhook {
  url = "http://soar_shuffle_backend:5001/api/v1/hooks/<workflow_id>"
}
```

3. Configurar notificaciones en TheHive: Ir a **Admin** > **Webhooks**, crear nuevo webhook apuntando a Shuffle,
   seleccionar eventos (Case created, Alert created, Case updated).

4. Reiniciar TheHive:

```bash
docker restart soar_thehive
```

#### 3.2.5 Paso 5: configuración de Cortex

**Sitio Oficial**: [Cortex Project](https://thehive-project.org/cortex)
**Documentación**: [Cortex Documentation](https://docs.strangebee.com/cortex/)
**GitHub**: [TheHive-Project/Cortex](https://github.com/TheHive-Project/Cortex)

**1. Acceder a Cortex:**
Similar a TheHive, el primer paso es acceder a la interfaz web de Cortex para realizar la configuración inicial.
URL: https://soar.local/cortex/ o http://localhost:19001/

[CAPTURA: Screenshot de la página de login de Cortex.](https://soar.local/cortex/ #screenshot-11-cortex-login)

**2. Credenciales de Admin:**

El usuario administrador se crea automáticamente durante el despliegue con `reset_cortex.py`:

- Usuario: `admin`
- Contraseña: generada por `reset_cortex.py` (consultar los logs del contenedor `soar_api` o `.env.full` si el script la guarda)
- API key: `CORTEX_API_KEY` en `.env.full`

**3. Crear Organización:**

1. Ir a **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

**4. Configurar Analyzers:**

1. Ir a **Organization** > **Analyzers**
2. Verificar que analyzers como `VirusTotal_3`, `MISP_Search`, `IPInfo` estén habilitados

**5. Generar API Key:**

1. Ir a tu perfil
2. Click en **API Keys**
3. Click en **Create a new API Key**
4. Copiar la API Key

**6. Configurar Analyzers Adicionales:**
Analyzers recomendados:

- Shodan (para IPs y puertos abiertos)

- Hybrid Analysis (para análisis de malware)

- AlienVault OTX (para threat intelligence)

- Have I Been Pwned (para credenciales comprometidas)
    - Requiere API Key de HIBP
    - Verifica si emails/contraseñas han sido comprometidos
    - Referencia: [Have I Been Pwned](https://haveibeenpwned.com/)

**Configuración de Analyzers:**

1. Ir a **Organization** > **Analyzers**
2. Buscar el analyzer deseado
3. Click en **Enable**
4. Configurar la API Key requerida
5. Click en **Test** para verificar conexión

**Referencia**: [Cortex Analyzers Documentation](https://docs.strangebee.com/cortex/analyzer-tutorial/)

#### 3.2.6 Paso 6: configuración de Shuffle

**Sitio Oficial**: [Shuffle SOAR](https://shuffler.io/)
**Documentación**: [Shuffle Documentation](https://shuffler.io/docs)
**GitHub**: [Shuffle/Shuffle](https://github.com/Shuffle/Shuffle)
**Apps**: [Shuffle/openapi-apps](https://github.com/Shuffle/openapi-apps)

Shuffle es la plataforma de automatización de orquestación SOAR del laboratorio. Permite crear workflows que conectan
diferentes servicios y automatizan la respuesta a incidentes. Esta sección configura Shuffle y sus componentes
principales.

**1. Acceder a Shuffle:**
El primer paso es acceder a la interfaz web de Shuffle para realizar la configuración inicial del usuario y
organización.
URL: http://localhost:8081/

[CAPTURA: Screenshot de la página de login de Shuffle.](http://localhost:8081/ #screenshot-16-shuffle-login)

**2. Crear Usuario Admin:**
Si es el primer acceso a Shuffle, debes crear un usuario administrador. Las credenciales predeterminadas se pueden
modificar en el archivo `.env.full` antes del despliegue.

Si es el primer acceso:

- Usuario: `admin`
- Contraseña: `<SHUFFLE_DEFAULT_PASSWORD>` (configurado en .env.full)

[CAPTURA: Screenshot de la página de login de Shuffle con credenciales ingresadas.](http://localhost:8081/
#screenshot-17-shuffle-login-creds)

**3. Crear Organización:**
Las organizaciones en Shuffle permiten agrupar workflows, apps y configuraciones. Crear una organización específica para
el laboratorio SOAR facilita la gestión de los workflows de ransomware.

1. Ir a **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

[CAPTURA: Screenshot del formulario de creación de organización en Shuffle.](http://localhost:8081/organizations
#screenshot-18-shuffle-org)

**4. Verificar Networking de Workers:**
El network-watcher es un servicio que conecta automáticamente los workers de Shuffle a la red Docker `soar_net`.
Esto es crucial para que los workers puedan comunicarse con otros servicios del laboratorio. Verificar que esté
funcionando correctamente:

```bash
docker network inspect soar_net
```

[CAPTURA: Screenshot de la salida de
`docker network inspect soar_net` mostrando los contenedores conectados.](#screenshot-19-network-inspect)

**5. Generar API Key:**
La API Key de Shuffle es necesaria para autenticar requests a la API de Shuffle, especialmente para ejecutar workflows
vía webhook. Esta clave debe guardarse de forma segura.

1. Ir a tu perfil
2. Click en **API Keys**
3. Click en **Create new API Key**
4. Nombre: `SOAR Lab Key`
5. Copiar la API Key

[CAPTURA: Screenshot de la sección de API Keys en Shuffle.](http://localhost:8081/profile
#screenshot-20-shuffle-apikey)

#### 3.2.7 Paso 7: registro de apps en Shuffle

Shuffle utiliza apps para conectarse con diferentes servicios. Esta sección configura las apps de TheHive, Cortex, MISP
y Elasticsearch para que Shuffle pueda interactuar con estos servicios.

**1. Registrar App TheHive:**
TheHive es una de las apps principales que Shuffle utilizará para crear casos y alertas. Debe descargarse y configurarse
con las credenciales generadas anteriormente.

1. Ir a **Apps** en Shuffle
2. Buscar **TheHive** en el buscador
3. Click en **TheHive** app
4. Click en **Download/Install**

[CAPTURA: Screenshot de la página de TheHive app en Shuffle mostrando el botón Download/Install.](http://localhost:8081/apps/TheHive
#screenshot-21-shuffle-thehive-app)

**2. Configurar Autenticación TheHive:**
Una vez descargada la app, debes configurar la autenticación con la API Key y URL de TheHive generadas anteriormente.

1. Después de descargar, click en **Authentication**
2. Configurar:
    - **apikey**: [Pegar la API Key de TheHive generada anteriormente]
    - **url**: `http://thehive:9000`
3. Click en **Save**
4. Click en **Test** para verificar conexión

[CAPTURA: Screenshot del formulario de autenticación de TheHive en Shuffle mostrando los campos configurados.](http://localhost:8081/apps/TheHive
#screenshot-22-shuffle-thehive-auth)

[CAPTURA: Screenshot del resultado del test de conexión mostrando "Success".](#screenshot-23-shuffle-thehive-test)

**3. Registrar App Cortex:**
Similar a TheHive, Cortex debe registrarse para que Shuffle pueda ejecutar analyzers y obtener resultados de análisis.

1. Ir a **Apps**
2. Buscar **Cortex**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **apikey**: [Pegar la API Key de Cortex generada anteriormente]
    - **url**: `http://cortex:9001`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de Cortex en Shuffle.](http://localhost:8081/apps/Cortex
#screenshot-24-shuffle-cortex-auth)

**4. Registrar App MISP:**
MISP es la plataforma de threat intelligence del laboratorio. Registrar esta app permite a Shuffle consultar IoCs y
crear eventos en MISP.

1. Ir a **Apps**
2. Buscar **MISP**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **apikey**: [API Key de MISP]
    - **url**: `http://misp`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de MISP en Shuffle.](http://localhost:8081/apps/MISP
#screenshot-25-shuffle-misp-auth)

**Integración Adicional MISP - Shuffle:**

**¿Por qué integrar MISP con Shuffle?**

- MISP es una plataforma de threat intelligence para compartir IoCs
- Shuffle puede consultar MISP para enriquecer alertas con información de amenazas
- Permite crear eventos en MISP desde workflows de Shuffle

**Configuración de Synchronization en MISP:**

1. Acceder a MISP: http://localhost:8083
2. Ir a **Event Actions** > **Automation**
3. Crear nuevo automation rule para enviar eventos a Shuffle:
    - **Trigger**: Cuando se crea un evento
    - **Action**: POST a webhook de Shuffle
    - **Format**: JSON con datos del evento

**Acciones MISP disponibles en Shuffle:**

- **search_attributes**: Buscar IoCs en MISP (IPs, dominios, hashes, emails)
- **create_event**: Crear evento en MISP desde Shuffle
- **add_attribute**: Añadir atributo a un evento existente
- **get_event**: Obtener detalles de un evento

**Caso de uso:**

1. Wazuh detecta una IP sospechosa
2. Shuffle recibe la alerta vía webhook
3. Shuffle consulta MISP con la IP
4. MISP devuelve información de amenazas asociadas
5. Shuffle decide si crear caso en TheHive basándose en la reputación

**Referencia**: [MISP Documentation](https://www.misp-project.org/documentation/)

**5. Registrar App Elasticsearch:**
Elasticsearch se utiliza para indexar datos de incidentes y ejecuciones. Registrar esta app permite a Shuffle almacenar
y consultar datos en Elasticsearch.

1. Ir a **Apps**
2. Buscar **Elasticsearch**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **username**: `elastic`
    - **password**: [Contraseña de Elasticsearch de .env.full]
    - **url**: `http://elasticsearch:9200`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de Elasticsearch en Shuffle.](http://localhost:8081/apps/Elasticsearch
#screenshot-26-shuffle-es-auth)

#### 3.2.8 Paso 8: creación de workflows

Los workflows en Shuffle definen la lógica de automatización para responder a incidentes. Esta sección crea un workflow
de respuesta a ransomware que integra TheHive, Cortex y Elasticsearch.

**1. Crear Workflow de Respuesta a Ransomware:**
El primer paso es crear un nuevo workflow en Shuffle que orquestará la respuesta automatizada a incidentes de
ransomware.

1. Ir a **Workflows** en Shuffle
2. Click en **New Workflow**
3. Nombre: `Ransomware Response`
4. Descripción: `Workflow automatizado para respuesta a incidentes de ransomware`

[CAPTURA: Screenshot del formulario de creación de workflow en Shuffle.](http://localhost:8081/workflows
#screenshot-27-shuffle-workflow-create)

**2. Configurar Trigger Webhook:**
El trigger webhook permite que el workflow se inicie cuando se reciba una solicitud HTTP externa, como una alerta de
Wazuh o cualquier otro sistema.

1. En el panel izquierdo, buscar **Triggers**
2. Arrastrar **Webhook** al canvas
3. Click en el trigger webhook
4. Nombre: `Ransomware Alert`
5. Guardar

[CAPTURA: Screenshot del canvas de workflow mostrando el trigger webhook.](http://localhost:8081/workflows/{workflow_id}
#screenshot-28-shuffle-webhook-trigger)

**3. Agregar Acción: Crear Caso en TheHive:**
Esta acción crea un caso en TheHive cuando el workflow se ejecuta, permitiendo documentar y gestionar el incidente de
ransomware.

1. En el panel izquierdo, buscar **TheHive** app
2. Arrastrar acción **create_case** al canvas
3. Conectar el webhook a la acción
4. Configurar la acción:
    - **title**: `$exec.alert_id` - Ransomware Detection
    - **description**: `$exec.description`
    - **severity**: `$exec.severity`
    - **tags**: `ransomware,automated`
    - **tlp**: 2 (Amber)
    - **pap**: 2 (Amber)

[CAPTURA: Screenshot de la configuración de la acción create_case de TheHive.](http://localhost:8081/workflows/{workflow_id}
#screenshot-29-shuffle-thehive-action)

**4. Agregar Acción: Analizar IoCs con Cortex:**
Esta acción utiliza Cortex para analizar observables (como hashes) con analyzers como VirusTotal, proporcionando
información adicional sobre el malware.

1. Buscar **Cortex** app
2. Arrastrar acción **run_analyzer** al canvas
3. Conectar la acción anterior a esta
4. Configurar:
    - **analyzer**: `VirusTotal_3`
    - **data**: `$exec.hash`
    - **datatype**: `hash`

[CAPTURA: Screenshot de la configuración de la acción run_analyzer de Cortex.](http://localhost:8081/workflows/{workflow_id}
#screenshot-30-shuffle-cortex-action)

**5. Agregar Acción: Indexar en Elasticsearch:**
Esta acción indexa los datos del incidente en Elasticsearch para su posterior análisis y consulta.

1. Buscar **Elasticsearch** app
2. Arrastrar acción **create_index** al canvas
3. Conectar la acción anterior a esta
4. Configurar:
    - **index**: `ransomware-alerts`
    - **document**: JSON con todos los datos del incidente

[CAPTURA: Screenshot de la configuración de la acción create_index de Elasticsearch.](http://localhost:8081/workflows/{workflow_id}
#screenshot-31-shuffle-es-action)

**6. Guardar y Activar Workflow:**
Una vez configuradas todas las acciones, es necesario guardar el workflow y activarlo para que el webhook esté
disponible para recibir solicitudes.

1. Click en **Save** (icono de disquete)
2. Click en **Start** para activar el webhook

[CAPTURA: Screenshot del workflow completo mostrando todas las acciones conectadas.](http://localhost:8081/workflows/{workflow_id}
#screenshot-32-shuffle-workflow-complete)

**7. Obtener URL del Webhook:**
La Webhook URL es necesaria para que sistemas externos (como Wazuh) puedan enviar alertas al workflow.

1. Click en el trigger webhook
2. Copiar la **Webhook URL**

[CAPTURA: Screenshot mostrando la Webhook URL del trigger.](http://localhost:8081/workflows/{workflow_id}
#screenshot-33-shuffle-webhook-url)

#### 3.2.9 Paso 9: configuración de Wazuh

**Sitio Oficial**: [Wazuh](https://wazuh.com/)
**Documentación**: [Wazuh Documentation](https://documentation.wazuh.com/)
**GitHub**: [wazuh/wazuh](https://github.com/wazuh/wazuh)

Wazuh es el SIEM/XDR del laboratorio, compuesto por `wazuh.manager`, `wazuh.indexer` y `wazuh.dashboard`. Antes de
iniciar el stack Wazuh, deben generarse los certificados TLS del indexer y validarse los archivos generados.

**1. Generar certificados del Wazuh Indexer:**

El generador usa la imagen `wazuh/wazuh-certs-generator:0.0.2` y produce certificados autofirmados en
`infra/docker/wazuh/config/wazuh_indexer_ssl_certs/`:

```bash
docker compose -f infra/docker/wazuh/generate-indexer-certs.yml run --rm generator
```

Certificados generados (ubicación canónica):

- CA: `root-ca.pem`
- Wazuh Indexer: `wazuh.indexer.pem` / `wazuh.indexer-key.pem`
- Wazuh Manager (Filebeat): `wazuh.manager.pem` / `wazuh.manager-key.pem`
- Wazuh Dashboard: `wazuh.dashboard.pem` / `wazuh.dashboard-key.pem`
- Administrador: `admin.pem` / `admin-key.pem`

Si se recrea el entorno, regenerar certificados antes de `make up` para evitar rechazos SSL entre indexer y dashboard.
No es necesario confiar en la CA del sistema para las comunicaciones internas Docker, pero sí para acceder con el
navegador a `https://localhost:<WAZUH_DASHBOARD_PORT>` sin advertencias.

**2. Iniciar el stack Wazuh:**

El stack Wazuh se arranca junto al resto del laboratorio con `make up`. Para levantar solo Wazuh:

```bash
docker compose \
  --env-file .env.full \
  -f infra/docker/compose/docker-compose.yml \
  -f infra/docker/compose/docker-compose.wazuh.yml \
  up -d
```

**3. Acceder a Wazuh Dashboard:**

- URL directa: `https://localhost:<WAZUH_DASHBOARD_PORT>` (por defecto `15601`)
- Credenciales: `admin` / `<WAZUH_INDEXER_PASSWORD>` (según `.env.full`)
- Acceso por Nginx: **no soportado**; la interfaz usa rutas absolutas que no se sirven correctamente bajo subdirectorio.
- El navegador mostrará advertencia de certificado autofirmado; acepta el riesgo o importa
  `infra/docker/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem` en el almacén de confianza.

**4. Verificar API de Wazuh Manager:**

Puerto host: `<WAZUH_API_PORT>` → contenedor `55000`.

```bash
curl -k -u <WAZUH_API_USERNAME>:<WAZUH_API_PASSWORD> https://localhost:<WAZUH_API_PORT>/security/users/me
```

**5. Validar certificados y credenciales:**

Comprueba que los archivos del paso 1 existen y que los servicios pueden conectarse. La secuencia recomendada es:

1. Certificados en el host:
   ```bash
   ls infra/docker/wazuh/config/wazuh_indexer_ssl_certs/
   ```
2. Health del indexer (usando el usuario administrador del indexer):
   ```bash
   curl -k -u <WAZUH_INDEXER_USERNAME>:<WAZUH_INDEXER_PASSWORD> https://localhost:<WAZUH_INDEXER_PORT>/_cluster/health
   ```
3. Estado de los procesos del manager:
   ```bash
   docker exec soar_wazuh_manager /var/ossec/bin/wazuh-control status
   ```
4. API del manager:
   ```bash
   curl -k -u <WAZUH_API_USERNAME>:<WAZUH_API_PASSWORD> https://localhost:<WAZUH_API_PORT>/
   ```
5. Dashboard (acceso web o `curl`):
   ```bash
   curl -k -L -u admin:<WAZUH_INDEXER_PASSWORD> https://localhost:<WAZUH_DASHBOARD_PORT>/
   ```

Si alguna conexión SSL falla con `SSL_ERROR_SYSCALL` o similar, los certificados no coinciden: regenera con el paso 1,
elimina los volúmenes de Wazuh (`docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.wazuh.yml down -v`) y vuelve a desplegar.

**6. Configurar Webhook hacia Shuffle:**

Wazuh puede enviar alertas a Shuffle vía webhook para orquestar respuestas. Obtener primero la URL del webhook del
workflow:

```bash
make init-webhook
# o directamente
docker exec soar_api python src/soar_lab/scripts/setup/init_shuffle_webhook.py
```

La salida incluye la `Webhook URL` interna, por ejemplo:

```text
http://soar_shuffle_backend:5001/api/v1/hooks/webhook_<TRIGGER_ID>
```

Acceder al contenedor del manager:

```bash
docker exec -it soar_wazuh_manager bash
```

Editar `/var/ossec/etc/ossec.conf` y añadir la integración custom (sustituir `<TRIGGER_ID>` por el valor de `webhook_info.json`):

```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://soar_shuffle_backend:5001/api/v1/hooks/webhook_<TRIGGER_ID></hook_url>
  <api_format>json</api_format>
</integration>
```

Configurar reglas en `/var/ossec/rules/local_rules.xml` para disparar el webhook, por ejemplo cuando el nivel de alerta sea >= 10:

```xml
<rule id="100001" level="10">
  <field name="rule.groups">ransomware</field>
  <description>Ransomware detection - Trigger Shuffle webhook</description>
</rule>
```

**Referencia**: [Wazuh Integration Documentation](https://documentation.wazuh.com/current/user-manual/reference/integrations/webhook.html)

**7. Reiniciar Wazuh:**

```bash
/var/ossec/bin/ossec-control restart
```

[CAPTURA: Screenshot de terminal mostrando Wazuh reiniciándose.](#screenshot-35-wazuh-restart)

> **Nota:** la integración Wazuh → Shuffle es **híbrida**: Wazuh genera alertas reales pero el procesamiento y la
> respuesta en Shuffle dependen de que los workers tengan conectividad de red (`soar_net`) y que el Network Watcher esté
> activo.

#### 3.2.10 Paso 10: configuración de MISP

**Sitio Oficial**: [MISP Project](https://www.misp-project.org/)
**Documentación**: [MISP Documentation](https://www.misp-project.org/documentation/)
**GitHub**: [MISP/MISP](https://github.com/MISP/MISP)

MISP es la plataforma de threat intelligence del laboratorio. Permite compartir y consultar IoCs para enriquecer la
respuesta a incidentes. Esta sección configura MISP para su integración con Shuffle.

**1. Acceder a MISP:**
El primer paso es acceder a la interfaz web de MISP para realizar la configuración inicial.
URL: http://localhost:8083/

[CAPTURA: Screenshot de la página de login de MISP.](http://localhost:8083/ #screenshot-36-misp-login)

**2. Credenciales de Admin:**
El usuario administrador se configura durante el despliegue desde `.env.full`:

- Usuario: `admin@soar.local`
- Contraseña: `<MISP_ADMIN_PASSWORD>`
- Cambiar contraseña al primer login

[CAPTURA: Screenshot del formulario de cambio de contraseña de MISP.](http://localhost:8083/users/edit
#screenshot-37-misp-password)

**3. Generar Auth Key:**
La Auth Key es necesaria para que Shuffle pueda autenticarse con MISP y realizar acciones como consultar IoCs y crear
eventos. Esta clave debe guardarse de forma segura.

1. Ir a **Event Actions** > **Automation**
2. Click en **New Auth Key**
3. Copiar el Auth Key

[CAPTURA: Screenshot de la sección de Auth Keys en MISP.](http://localhost:8083/auth_keys/index
#screenshot-38-misp-authkey)

#### 3.2.11 Paso 11: pruebas end-to-end

Esta sección verifica que toda la integración del laboratorio SOAR esté funcionando correctamente. Se realizan pruebas
para asegurar que los workflows se ejecuten y que los servicios se comuniquen adecuadamente.

**1. Enviar Alerta de Prueba:**
El script Python envía una alerta de prueba al webhook de Shuffle para iniciar el workflow de respuesta a ransomware.

Usar el script Python:

```bash
python src/soar_lab/infrastructure/external/integrations/shuffle/test_workflow.py
```

[CAPTURA: Screenshot de la salida del script mostrando el webhook enviado y el worker creado en soar_net.](#screenshot-39-test-workflow)

**2. Verificar Ejecución en Shuffle:**
Después de enviar la alerta de prueba, es importante verificar que el workflow se haya ejecutado correctamente en
Shuffle.

1. Ir a **Workflows** en Shuffle
2. Click en el workflow `Ransomware Response`
3. Click en **Executions**
4. Ver la ejecución más reciente

[CAPTURA: Screenshot de la ejecución del workflow mostrando el estado y resultados.](http://localhost:8081/workflows/{workflow_id}/executions
#screenshot-40-shuffle-execution)

**3. Verificar Caso en TheHive:**
Es importante verificar que el workflow haya creado correctamente el caso en TheHive con los datos de la alerta.

1. Ir a TheHive en http://localhost:19000
2. Verificar que se creó el caso

[CAPTURA: Screenshot del caso creado en TheHive.](https://soar.local/thehive/case/{case_id} #screenshot-41-thehive-case)

**4. Verificar Análisis en Cortex:**
Verifica que el workflow haya ejecutado el analyzer en Cortex y que los resultados estén disponibles.

1. Ir a Cortex en http://localhost:19001
2. Verificar el análisis del hash

[CAPTURA: Screenshot del análisis en Cortex.](https://soar.local/cortex/job/{job_id} #screenshot-42-cortex-analysis)

**5. Verificar Datos en Elasticsearch:**
Finalmente, verifica que los datos del incidente se hayan indexado correctamente en Elasticsearch para su posterior
análisis.

```bash
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:19200/ransomware-alerts/_search
```

[CAPTURA: Screenshot de la respuesta de Elasticsearch mostrando los datos indexados.](#screenshot-43-es-search)

### 3.3 Verificación de configuración

#### 3.3.1 Resumen de URLs de acceso

Esta tabla resume todas las URLs de acceso a los servicios del laboratorio SOAR, incluyendo rutas de navegación
específicas y credenciales.

**Web Management UI**: `http://localhost:8085` (acceso directo) o `https://soar.local` a través de Nginx.

| Servicio | URL directa | Vía Nginx `https://soar.local` | Credenciales | Notas |
|----------|-------------|-------------------------------|--------------|-------|
| **Web Management** | `http://localhost:8085/` | `/` | `WEB_UI_USER` / `WEB_UI_PASSWORD` | SPA principal del panel de operación |
| **SOAR API** | `http://localhost:8000/` | `/api/` | JWT Bearer (`/auth/login`) | `/docs` y `/openapi.json` |
| **Shuffle UI** | `http://localhost:8081/` | No soportado | `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD` | SPA con rutas absolutas; acceso directo obligatorio |
| **Shuffle API** | `http://localhost:15001/` | `/shuffle-api/` | `SHUFFLE_DEFAULT_APIKEY` | Base URL interna: `http://soar_shuffle_backend:5001` |
| **TheHive** | `http://localhost:19000/` | `/thehive/` | admin / contraseña generada por `init_thehive.py` (ver logs) | API key: `THEHIVE_API_KEY` |
| **Cortex** | `http://localhost:19001/` | `/cortex/` | admin / contraseña generada por `reset_cortex.py` (ver logs) | API key: `CORTEX_API_KEY` |
| **MISP** | `http://localhost:8083/` | No soportado | `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD` | Acceso directo obligatorio |
| **Wazuh Dashboard** | `https://localhost:15601/` | No soportado | `admin` / `WAZUH_INDEXER_PASSWORD` | Usa `5601` interno con TLS; certificados del indexer en `infra/docker/wazuh/config/wazuh_indexer_ssl_certs/` |
| **Wazuh API** | `https://localhost:55100/` | No expuesto | `WAZUH_API_USERNAME` / `WAZUH_API_PASSWORD` | Interno `https://wazuh.manager:55000` |
| **Grafana** | `http://localhost:8084/` | No soportado | admin / `GRAFANA_ADMIN_PASSWORD` | Datasource Elasticsearch en `soar-metrics` |
| **Docs Site** | `http://localhost:8086/` | No soportado | - | Docusaurus / docs-site |
| **Elasticsearch** | `http://localhost:19200/` | No expuesto | `elastic` / `ELASTIC_PASSWORD` | Interno `http://elasticsearch:9200` |
| **Nginx Health** | - | `/nginx-health` | - | Healthcheck del proxy |

> Los valores `admin`, `elastic` y los nombres de servicio se toman de `.env.example`. Todos los secretos se generan ejecutando
> `make generate-secrets` (`src/soar_lab/scripts/setup/generate_env.py`). Revisar `.env.full` para las credenciales vigentes.

#### 3.3.x Archivos de entorno y sincronía de credenciales

| Archivo | Propósito | ¿Se versiona? | Notas |
|---------|-----------|---------------|-------|
| `.env.example` | Plantilla con marcadores y valores por defecto saneados | Sí | No contiene secretos reales; se usa como base para `make generate-secrets`. |
| `.env.full` | Archivo efectivo de configuración del stack | No (`.gitignore`) | Generado con `make generate-secrets`. Todos los `docker compose` y `make` targets lo cargan con `--env-file .env.full`. |
| `.env` / `docker/.env` | **No se usan** en el proyecto | Depende | Si existen, pueden ser leídos por `docker compose` al ejecutarse sin `--env-file`. Los ejemplos manuales incluyen siempre `--env-file .env.full` para evitar confusiones. |

**Sincronía de la API key de Shuffle:**

- `init_shuffle_webhook.py` crea el usuario admin y la API key de Shuffle y la indexa en Elasticsearch (`users_<org>`).
- Tras `make reset` se genera una nueva API key, por lo que `SHUFFLE_DEFAULT_APIKEY` de `.env.full` puede quedar desactualizada.
- El `ShuffleClient` implementa `_fetch_real_apikey()` para leer la clave actual desde Elasticsearch en runtime (self-heal).
- Para evitar inconsistencias, se recomienda actualizar `SHUFFLE_DEFAULT_APIKEY` en `.env.full` tras cada `make reset` (o verificar que los tests usan el self-heal).
- El archivo `artifacts/webhook_info.json` generado por `init_shuffle_webhook.py` contiene:
  - `webhook_url`: URL interna Docker (`http://shuffle-backend:5001/api/v1/hooks/...`) para uso desde contenedores.
  - `webhook_url_host`: URL accesible desde el host (`http://localhost:15001/api/v1/hooks/...`) para pruebas manuales externas.

#### 3.3.2 Scripts de automatización

Los scripts de inicialización y workflow están en:

- `src/soar_lab/scripts/setup/` — inicialización de secretos, certificados, servicios y webhooks.
- `src/soar_lab/infrastructure/external/integrations/shuffle/` — gestión de workflows y ejecuciones de Shuffle.

Scripts principales:

- `src/soar_lab/scripts/setup/generate_secrets.py` — Genera contraseñas y tokens.
- `src/soar_lab/scripts/setup/init_shuffle_webhook.py` — Crea/actualiza el workflow de ransomware y el webhook.
- `src/soar_lab/scripts/setup/init_thehive.py` — Inicializa índices y usuario admin de TheHive.
- `src/soar_lab/scripts/setup/reset_cortex.py` — Reinicia índice y admin de Cortex.
- `src/soar_lab/scripts/setup/preserve_credentials.py` / `restore_credentials.py` — Guardan/restauran credenciales tras `make reset`.
- `src/soar_lab/infrastructure/external/integrations/shuffle/activate_workflow.py` — Activa workflow y guarda info.
- `src/soar_lab/infrastructure/external/integrations/shuffle/test_workflow.py` — Prueba workflow y verifica networking.
- `src/soar_lab/infrastructure/external/integrations/shuffle/check_execution.py` — Verifica resultado de ejecución.
- `src/soar_lab/infrastructure/external/integrations/shuffle/fix_workflow_thehive.py` — Arregla workflow para usar app TheHive.

> Muchos scripts de inicialización se ejecutan automáticamente durante `make up`; solo es necesario ejecutarlos manualmente
> para recuperación o diagnóstico.

#### 3.3.3 Arquitectura de integraciones

**Flujo de Trabajo Típico:**

```
Wazuh (SIEM) → Shuffle (SOAR) → TheHive (Case Management)
                            ↓
                          Cortex (Analysis)
                            ↓
                          MISP (Threat Intelligence)
                            ↓
                          Elasticsearch (Logging)
```

**Ejemplo de Workflow de Respuesta a Ransomware:**

```
[Trigger] Wazuh Webhook
    ↓
[Action] Consultar MISP para verificar reputación de IP/hash
    ↓
[Condition] Si es malicioso:
    ↓
[Action] Analizar con VirusTotal (Cortex)
    ↓
[Action] Crear caso en TheHive
    ↓
[Action] Indexar en Elasticsearch
    ↓
[Action] Notificar analistas por email
```

**Integraciones Configuradas:**

1. **Wazuh → Shuffle**: Webhook para alertas de seguridad en tiempo real
2. **Shuffle → MISP**: Consulta de IoCs para enriquecimiento de amenazas
3. **Shuffle → Cortex**: Análisis de malware y observables
4. **Shuffle → TheHive**: Creación de casos y alertas
5. **TheHive → Shuffle**: Notificaciones de eventos vía webhook
6. **Shuffle → Elasticsearch**: Indexación de incidentes para análisis

**Estado Actual de Integraciones:**

| Integración | Componentes | Modo | Estado | Notas |
|---|---|---|---|---|
| Wazuh → Shuffle | Wazuh Manager, Shuffle Webhook | Wazuh genera alertas reales; Shuffle procesa y responde | **Híbrida** | Requiere reglas Wazuh, Network Watcher y `soar_net` |
| Shuffle → TheHive | Shuffle workflow, TheHive API | Creación/actualización de casos | **Implementada** | `THEHIVE_API_KEY` en `.env.full`; app descargada en Shuffle |
| Shuffle → Cortex | Shuffle workflow, Cortex API | Ejecución de analyzers | **Implementada** | `CORTEX_API_KEY`; analyzers con API key externa son opcionales |
| Shuffle → MISP | Shuffle workflow, MISP API | Enriquecimiento y registro de IoCs | **Implementada** | `MISP_API_KEY`; sincronización bidireccional puede requerir ajuste manual |
| Shuffle → Elasticsearch | Shuffle workflow, ES API | Indexado de métricas e incidentes | **Implementada** | Índice `soar-metrics` (`soar-metrics-v2` alias) |
| TheHive → Shuffle | TheHive webhook a Shuffle | Notificación de eventos de caso | **Implementada** | Configurar webhook en `application.conf` / UI |
| Lab API → Elasticsearch / TheHive / Cortex / MISP / Wazuh | API endpoints, clientes Python | Consulta de estado y KPIs | **Implementada** | Clientes en `src/soar_lab/infrastructure/external/integrations/` |
| Contención de endpoints | Shuffle workflow, scripts `notify.sh` | Simulada | **Simulada** | No hay agente EDR real; se registran notificaciones y métricas |
| MFA / SSO | — | No operativo | **Planificado** | Autenticación actual: JWT HS256 |
| WAF / mTLS / segmentación real | Nginx | No operativo | **Planificado / No verificado** | Nginx es proxy inverso con certificado autofirmado |
| Alta disponibilidad | Docker Compose | No operativo | **Planificado** | Despliegue single-host |



#### 3.3.4 Validación de tests

**Requisitos:**

- Python `>=3.11` (`pyproject.toml` declara `requires-python = ">=3.11"`).
- pytest con los extras de test (`pip install -e ".[test]"` o `make deps-test`).

**Recolectar casos sin ejecutarlos:**

```bash
python -m pytest --collect-only -q
```

Salida típica (2026-07-18, Windows, Python 3.11.9, pytest 9.0.3):

```text
collected 1944 items / 33 deselected / 1911 selected
```

**Conteos separados:**

- `collected`: total de ítems de prueba encontrados (incluye parametrizaciones).
- `deselected`: ítems filtrados por `-m` (por ejemplo, marcador `slow`).
- `selected`: ítems que finalmente ejecutará pytest.
- `skipped`: pruebas que llaman a `pytest.skip` en runtime por falta de requisitos (Docker, servicios externos, variables no configuradas, ejecución dentro del contenedor).
- `xfail`: fallos esperados; no se usan masivamente en el repo actual pero pueden aparecer en pruebas experimentales.

**Comandos útiles:**

```bash
# Saltar tests lentos
python -m pytest -m "not slow"

# Solo tests que requieren Docker
python -m pytest -m requires_docker

# Solo tests que requieren servicios externos
python -m pytest -m requires_external

# Ejecutar suite completa con cobertura
make test-coverage
```

**Notas sobre plataforma:**

- En Windows ejecutar E2E e integración con Docker Desktop activo y el repo disponible (sin WSL bind mounts problemáticos).
- Algunos tests de Docker se saltan si no se detecta `/var/run/docker.sock` o si se ejecutan dentro del contenedor `soar_api` sin acceso al repo.
- Los conteos exactos dependen del entorno y del estado de `baseline/tests_inventory.json`.

#### 3.3.5 Checklist de verificación post-`make up`

Tras ejecutar `make up` (o el equivalente `docker compose -f ... up -d`), desde la raíz del repositorio:

1. **Estado de los contenedores**
   ```bash
   docker compose ps
   ```
   Todos los servicios deben mostrar `healthy` o `up` (sin `unhealthy`).

2. **Healthcheck de Nginx**
   ```bash
   curl -k -I https://soar.local/nginx-health
   ```
   Debe devolver `HTTP/2 200` o `200 OK`.

3. **Healthcheck de la Lab API**
   ```bash
   curl -sf http://localhost:8000/health | python -m json.tool
   ```

4. **Grafana**
   ```bash
   curl -sf http://localhost:8084/api/health
   ```

5. **Network Watcher**
   ```bash
   curl -sf http://localhost:15130/health
   ```

6. **Logs de inicialización**
   ```bash
   docker logs -f --tail 100 soar_api
   ```
   Buscar mensajes de "Application startup complete" y ausencia de errores de conexión a Elasticsearch o Redis.

7. **Credenciales generadas**
   Verificar que `.env.full` no contiene placeholders `CHANGEME`/`CHANGE_ME` tras `make generate-secrets`:
   ```bash
   grep -iE "CHANGEME|CHANGE_ME|123456|admin/admin" .env.full || echo "OK"
   ```

8. **Acceso a Shuffle UI**
   - URL: `http://localhost:8081`
   - Usuario: `${SHUFFLE_DEFAULT_USERNAME:-admin}`
   - Contraseña: `${SHUFFLE_DEFAULT_PASSWORD}` (valor de `.env.full`)

9. **Prueba end-to-end mínima**
   ```bash
   python -m pytest tests/e2e/TC-01 -v
   ```
   (requiere Docker y los servicios levantados).

#### 3.3.6 Directorio de trabajo y contexto Docker

- **Raíz del repositorio**: `make up`, `make generate-secrets`, `make test-all` y `docker compose ...` deben ejecutarse desde la raíz del repositorio, donde se encuentran `.env.full`, `Makefile`, `pyproject.toml` y `infra/docker/compose/`.
- **Rutas relativas**: los `Dockerfile` y `docker-compose*.yml` usan rutas relativas a la raíz (por ejemplo `../../../artifacts`, `../config`, `logging/promtail-config.yml`). Si se ejecutan desde otro directorio, los volúmenes, bind mounts y `configs` fallarán.
- **Resolución de `configs.file`**: Docker Compose resuelve `configs.file` relativo al **primer** archivo compose (`infra/docker/compose/`). Por eso Promtail se configura como `logging/promtail-config.yml` y no como `./logging/promtail-config.yml`.
- **Configuración efectiva**: para depurar variables y volúmenes sin levantar contenedores, usar:
  ```bash
  docker compose --env-file .env.full -f infra/docker/compose/docker-compose.yml \
    -f infra/docker/compose/docker-compose.core.yml config | less
  ```

#### 3.3.7 Herramientas de calidad y CI

El entorno de desarrollo usa **Python 3.11+**. Las herramientas y sus versiones se declaran en `pyproject.toml` y se ejecutan en `.github/workflows/ci.yml`:

- **Black** (`>=23.0.0`, `line-length = 100`)
- **isort** (`>=5.12.0`, perfil `black`)
- **flake8** (`>=6.0.0`, dos pasos en CI)
- **mypy** (`>=1.0.0`, `python_version = "3.11"`)
- **pytest** (`>=7.0.0`, con `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-timeout`)
- **pre-commit** (`>=3.0.0`)

Para ejecutar localmente:

```bash
# Instalar entorno de desarrollo
pip install -e ".[dev]"

# Formatear y ordenar imports
black src/soar_lab
isort src/soar_lab

# Lint
flake8 src/soar_lab --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src/soar_lab --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

# Type check
mypy src/soar_lab --ignore-missing-imports

# Tests unitarios con cobertura
pytest tests/unit/ -v --cov=src.soar_lab --cov-report=xml
```

> `make lint` y `make test-all` ejecutan estos pasos agrupados según la plataforma (Linux/macOS/WSL vs Windows).

### 3.4 Troubleshooting

#### 3.4.1 Workers no se conectan a soar_net

Si los workers de Shuffle no se conectan a la red Docker correcta, las ejecuciones de workflows fallarán. Verificar que
el network-watcher esté funcionando correctamente:

```bash
docker logs soar_network_watcher
```

#### 3.4.2 App TheHive no funciona

Si la app de TheHive no funciona en Shuffle, puede ser un problema de autenticación o configuración. Verificar que la
app esté descargada y autenticada correctamente. Revisar la API Key y URL de TheHive.

#### 3.4.3 Workflow se queda en "Step is still running"

Este error indica que un worker no está ejecutando el paso del workflow. Puede ser un problema de networking o de
autenticación de apps. Verificar que el worker esté en la red correcta y que las apps estén autenticadas correctamente.

### 3.5 Mantenimiento

#### 3.5.1 Backups

El módulo de backups del laboratorio está implementado por tres componentes principales:

- `src/soar_lab/application/use_cases/backup_service.py`: orquesta la creación, listado y restauración de backups.
- `src/soar_lab/infrastructure/filesystem_storage.py`: provee acceso al sistema de archivos, localiza el
  directorio de backups y guarda metadatos.
- `src/soar_lab/infrastructure/tar_backup_driver.py`: encapsula los comandos `tar` para comprimir y extraer.

##### Crear un backup

```bash
make backup
```

Equivalente directo por API:

```bash
curl -sf -X POST http://localhost:8000/backup/create \
  -H "Content-Type: application/json" \
  -d '{"backup_name":"manual-backup.tar.gz"}'
```

El servicio `BackupService.create()` genera un archivo `soar_backup_YYYYMMDD_HHMMSS.tar.gz` (el parámetro
`backup_name` se valida, pero el nombre final lleva timestamp). `FilesystemStorage` obtiene la ruta desde la
variable `BACKUP_DIR` (por defecto `artifacts/backups` dentro de `BASE_DIR`) y `TarBackupDriver` empaqueta el
contenido de `BASE_DIR` excluyendo:

```text
__pycache__  *.pyc  .git  node_modules  htmlcov  .pytest_cache  coverage.xml
.coverage  artifacts  *.tar.gz  venv  env  .env  .mypy_cache  .tox  dist  build
.eggs  *.egg-info
```

Además, se escribe un archivo `<backup>.metadata.json` con el usuario, timestamp y tamaño.

##### Listar backups

```bash
curl -sf http://localhost:8000/backup/list | python3 -m json.tool
```

`BackupService.list_backups()` usa `FilesystemStorage` para leer `BACKUP_DIR` y devuelve nombre, tamaño en MB y
fecha de modificación.

##### Restaurar un backup

```bash
make restore BACKUP=soar_backup_YYYYMMDD_HHMMSS.tar.gz
```

Equivalente directo por API:

```bash
curl -sf -X POST http://localhost:8000/backup/restore \
  -H "Content-Type: application/json" \
  -d '{"backup_name":"soar_backup_YYYYMMDD_HHMMSS.tar.gz"}'
```

`BackupService.restore()` localiza el archivo en `BACKUP_DIR`, `TarBackupDriver.extract()` lo descomprime en
`BASE_DIR` con `--skip-old-files` para no sobrescriber versiones más recientes, y `FilesystemStorage` registra
la operación en `restore_operations.log`.

##### Consideraciones de persistencia

- `BACKUP_DIR` se configura en `.env.full`; el valor por defecto es `artifacts/backups` relativo a `BASE_DIR`.
- El directorio `artifacts/backups` debe persistir fuera del contenedor (bind mount de `artifacts` en Compose) o
  sincronizarse con el host para que los backups sobrevivan a `docker compose down -v`.
- El backup de archivos **no** incluye los volúmenes Docker de datos de Elasticsearch, MISP, Wazuh, TheHive,
  Cortex o Grafana. Para esos datos usar snapshots de volumen o los mecanismos nativos de cada servicio.
- `BACKUP_RETENTION_DAYS` define la política de retención; limpiar archivos antiguos periódicamente o programar un
  job externo que use `find artifacts/backups -name 'soar_backup_*.tar.gz' -mtime +$BACKUP_RETENTION_DAYS -delete`.
- `.env.full` no se elimina durante `make reset`, pero mantener una copia adicional fuera del repositorio como
  salvaguarda.

#### 3.5.2 Actualizaciones

Mantener las imágenes Docker actualizadas:

```bash
docker compose pull
docker compose up -d
```

#### 3.5.3 Monitoreo

Verificar el estado de servicios regularmente:

```bash
docker ps
docker logs soar_thehive
docker logs soar_cortex
docker logs soar_shuffle
```

## 4. Validación

### 4.1 Verificación

La configuración del laboratorio SOAR se considera exitosa cuando:

- Todos los servicios están ejecutándose y reportan estado healthy
- Las apps de Shuffle están descargadas, autenticadas y funcionando correctamente
- El workflow de respuesta a ransomware se ejecuta sin errores
- Las pruebas end-to-end pasan exitosamente
- Los servicios se comunican correctamente entre sí
- Los webhooks están configurados y funcionando

### 4.2 Criterios de Aceptación

La configuración del laboratorio SOAR se considera exitosa cuando se cumplen los criterios de verificación descritos en
la sección 4.1.

### 4.3 Evidencias

Las evidencias de configuración exitosa incluyen:

- Logs de contenedores sin errores críticos
- Ejecuciones de workflows exitosas en Shuffle
- Casos creados en TheHive
- Análisis ejecutados en Cortex
- Datos indexados en Elasticsearch
- Webhooks configurados y funcionando

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de Integración:**

- Algunos analyzers de Cortex requieren API keys externas (VirusTotal, Shodan, etc.)
- La integración Wazuh-Shuffle requiere configuración manual de reglas
- MISP requiere configuración adicional para sincronización bidireccional

### 5.2 Riesgos o incidencias

**Riesgos de Seguridad:**

- Las API keys deben guardarse de forma segura
- Las contraseñas predeterminadas deben cambiarse inmediatamente
- Los webhooks deben estar protegidos con autenticación

### 5.3 Recomendaciones / troubleshooting

**Troubleshooting:**

**Workers no se conectan a soar_net:**
Si los workers de Shuffle no se conectan a la red Docker correcta, las ejecuciones de workflows fallarán. Verificar que
el network-watcher esté funcionando correctamente:

```bash
docker logs soar_network_watcher
```

**App TheHive no funciona:**
Si la app de TheHive no funciona en Shuffle, puede ser un problema de autenticación o configuración. Verificar que la
app esté descargada y autenticada correctamente. Revisar la API Key y URL de TheHive.

**Workflow se queda en "Step is still running":**
Este error indica que un worker no está ejecutando el paso del workflow. Puede ser un problema de networking o de
autenticación de apps. Verificar que el worker esté en la red correcta y que las apps estén autenticadas correctamente.

**Próximos Pasos:**

Una vez configurado el laboratorio SOAR, hay varias mejoras y extensiones que puedes implementar para enriquecer las
capacidades del sistema.

1. **Crear workflows adicionales** para otros tipos de incidentes
2. **Configurar más analyzers** en Cortex
3. **Integrar Wazuh** completamente con Shuffle
4. **Crear dashboards** en Wazuh Dashboard para visualización
5. **Configurar alertas** automáticas desde Wazuh a Shuffle

**Soporte:**

Si encuentras problemas o tienes preguntas durante la configuración u operación del laboratorio SOAR, hay varios
recursos disponibles para obtener ayuda.

Para problemas o preguntas:

- Revisar logs: `docker logs <container_name>`
- Documentación oficial: https://shuffler.io/docs
- TheHive docs: https://docs.strangebee.com/thehive/
- Cortex docs: https://docs.strangebee.com/cortex/

## 6. Referencias

**Referencias y Proyectos de Investigación:**

**Proyectos con Integración Webhook para Shuffle:**

**TheHive + Shuffle + MISP:**

- **Descripción**: Integración real-time entre TheHive, Shuffle y MISP para automatización de IoCs
- **Referencia
  **: [Real-time executions and IoC's with Shuffle, TheHive and MISP - Medium](https://medium.com/shuffle-automation/indicators-and-webhooks-with-thehive-cortex-and-misp-open-source-soar-part-4-f70cde942e59)
- **Webhook Config**: TheHive envía alertas a Shuffle vía webhook, Shuffle procesa y consulta MISP
- **Caso de uso**: Detección de IoCs desde texto, análisis con MISP, creación de casos en TheHive

**Wazuh + Shuffle + TheHive:**

- **Descripción**: SOC automation project integrando Wazuh SIEM con Shuffle y TheHive
- **Referencia
  **: [Wazuh, TheHive, and Shuffle — SOC Automation Project - Medium](https://medium.com/@jblemard/wazuh-thehive-and-shuffle-soc-automation-project-08ff58e0a4c9)
- **Webhook Config**: Wazuh envía alertas a Shuffle, Shuffle crea casos en TheHive, analiza con VirusTotal
- **Caso de uso**: Respuesta automatizada a alertas de Wazuh, análisis de malware, notificación a analistas

**Shuffle + VirusTotal + TheHive:**

- **Descripción**: Integración de Shuffle con VirusTotal y TheHive para análisis de malware
- **Referencia
  **: [Integrating Shuffle with Virustotal and TheHive - Medium](https://medium.com/shuffle-automation/integrating-shuffle-with-virustotal-and-thehive-open-source-soar-part-3-8e2e0d3396a9)
- **Webhook Config**: Shuffle analiza archivos con VirusTotal, crea casos en TheHive
- **Caso de uso**: Análisis automatizado de malware, creación de casos en TheHive

**TheHive Webhook Configuration:**

- **Documentación**: [TheHive Webhook Setup](https://docs.strangebee.com/thehive/api-docs/)
- **Config**: Editar `application.conf` para configurar URL de webhook
- **Endpoint**: POST al webhook de Shuffle con datos del caso/alerta

**Repositorios de Apps Shuffle:**

**OpenAPI Apps:**

- **Repositorio**: [Shuffle/openapi-apps](https://github.com/Shuffle/openapi-apps)
- **Descripción**: Apps generadas desde especificaciones OpenAPI de seguridad
- **Apps Relevantes**: TheHive (OpenAPI v5), Cortex, MISP, VirusTotal, Shodan

**Python Apps:**

- **Repositorio**: [Shuffle/python-apps](https://github.com/Shuffle/python-apps)
- **Descripción**: Apps Python personalizadas para Shuffle
- **Apps Relevantes**: TheHive, Cortex, MISP (versión antigua, ahora en OpenAPI)

**Tutoriales en YouTube:**

**Shuffle SOAR Tutorials:**

- **Automate Everything with Shuffle!** - [Video Tutorial](https://www.youtube.com/watch?v=_riaZjLnoXo)
- **Host Your Own SOAR - Shuffle Install** - [Video Tutorial](https://www.youtube.com/watch?v=YDUKZojg0vk)
- **Shuffle: Automated Workflows** - [Video Tutorial](https://www.youtube.com/watch?v=toqzkIN1urA)
- **SOC Open Source, Build own SOAR with Shuffle, ELK-TheHive-Cortex-MISP
  ** - [Video Tutorial](https://www.youtube.com/watch?v=Nb9_ahZMC5U)
- **Shuffle SOAR Home-Lab | Free Security Automation Tool
  ** - [Video Tutorial](https://www.youtube.com/watch?v=i2rRDB2N2w8)

**TheHive Tutorials:**

- **Installing TheHive 4.1.x in 12 minutes** - [Video Tutorial](https://www.youtube.com/watch?v=V_toQk19PuE)
- **TheHive - Build Your Own Security Operations Center (SOC)
  ** - [Video Tutorial](https://www.youtube.com/watch?v=VqIuP0AOCBg)
- **SOC Open Source, ELK- TheHive- Cortex- MISP Complete Setup Guide
  ** - [Video Tutorial](https://www.youtube.com/watch?v=t6PqjLIVgdA)
- **#1 Cyber-SOC - Configurer TheHive et Cortex pour un SOC avec Wazuh
  ** - [Video Tutorial](https://www.youtube.com/watch?v=OiuTbNhMw1A)

**Cortex Tutorials:**

- **How to enable Cortex analyzers** - [Video Tutorial](https://www.youtube.com/watch?v=YuMn02vTe5k)
- **CORTEX - Analyze Observables (IPs, domains, etc.) at Scale!
  ** - [Video Tutorial](https://www.youtube.com/watch?v=qz6xtINwK3I)
- **TheHive and Cortex Integration** - [Video Tutorial](https://www.youtube.com/watch?v=lzsTSDJhAOw)
- **Leveraging TheHive & Cortex for automated IR** - [Video Tutorial](https://www.youtube.com/watch?v=K6K1fNpbf9w)

**MISP Tutorials:**

- **How to Build Your First MISP Instance From Scratch** - [Video Tutorial](https://www.youtube.com/watch?v=fP28LXD8IU8)
- **Cómo Instalar MISP: Configuración Rápida y Sencilla
  ** - [Video Tutorial](https://www.youtube.com/watch?v=koCj1waK9RM)
- **MISP General Usage Training - Part 1 of 2** - [Video Tutorial](https://www.youtube.com/watch?v=-NuODyh1YJE)
- **How to Create MISP Events and Add Threat Intelligence
  ** - [Video Tutorial](https://www.youtube.com/watch?v=sWOa4Ld4CQM)
- **MISP Install and Intro** - [Video Tutorial](https://www.youtube.com/watch?v=nZcTc60YsIs)

**Wazuh Tutorials:**

- **SOAR-Installation Wazuh - Open Source XDR & SIEM Part3
  ** - [Video Tutorial](https://www.youtube.com/watch?v=p2LCsizVMNI)
- **Deploy Your Open Source SOAR Platform in One Command
  ** - [Video Tutorial](https://www.youtube.com/watch?v=NtBy9u1b7MM)
- **Shuffle + Wazuh + TheHIVE + Cortex = Automation Bliss
  ** - [Video Tutorial](https://www.youtube.com/watch?v=FBISHA7V15c)
- **WAZUH – prezentacja rozwiązania SIEM/SOAR/XDR** - [Video Tutorial](https://www.youtube.com/watch?v=UO5UDG10iSk)

**Issues y Discussions Relevantes:**

**TheHive App Issues:**

- **Issue #205**: [TheHive: update/patch cases](https://github.com/Shuffle/python-apps/issues/205)
- **Descripción**: Feature request para actualizar campos de casos en TheHive desde Shuffle

**TheHive + Shuffle Integration:**

- **Issue #1502**: [Unable to integrate Shuffle with TheHive and Wazuh](https://github.com/Shuffle/Shuffle/issues/1502)
- **Descripción**: Problemas de integración entre Shuffle, TheHive y Wazuh

**Documentación Oficial de APIs:**

**TheHive API:**

- **Documentación**: [TheHive 5 API Documentation](https://docs.strangebee.com/thehive/api-docs/)
- **Endpoints Relevantes**: `POST /api/case`, `POST /api/alert`, `GET /api/case/{id}`, `PATCH /api/case/{id}`

**Cortex API:**

- **Documentación**: [Cortex API Documentation](https://docs.strangebee.com/cortex/api-docs/)
- **Endpoints Relevantes**: `POST /api/analyzer/run`, `GET /api/analyzer/{id}`

**Docker Templates de Referencia:**

**TheHive + Cortex + MISP + Shuffle:**

- **Repositorio**: [TheHive-Project/Docker-Templates](https://github.com/TheHive-Project/Docker-Templates)
- **Template
  **: [docker/thehive4-cortex3-misp-shuffle/README.md](https://github.com/TheHive-Project/Docker-Templates/blob/main/docker/thehive4-cortex3-misp-shuffle/README.md)
- **Descripción**: Configuración Docker completa para TheHive, Cortex, MISP y Shuffle

**Referencias Generales:**

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Docker Compose**: https://docs.docker.com/compose/

## 7. Métricas, versiones, trazabilidad y glosario

Este apéndice consolida la información necesaria para reproducir las métricas del proyecto, identificar versiones verificadas, entender la trazabilidad del código y enlazar con el glosario de acrónimos.

### 7.1 Glosario de acrónimos

Los acrónimos técnicos (MTTR, KPI, E2E, CORS, JWT, SSO, MFA, WAF, IaC, etc.) se definen en [docs/GLOSSARY.md](../GLOSSARY.md). Al introducir un acrónimo en cualquier documento nuevo, escribir la expansión completa la primera vez y enlazar al glosario para la definición detallada.

### 7.2 Métricas observadas, objetivos y umbrales

- **Observada**: valor real obtenido de las ejecuciones del workflow y almacenado en el índice `soar-metrics` (`soar-metrics-v2`).
- **Objetivo**: valor deseado para la mejora continua del laboratorio.
- **Umbral (`threshold_p50`, `threshold_p90`)**: límite que una métrica observada no debería superar.

| Métrica | Definición | Umbral actual | Procedimiento de verificación |
|---------|------------|---------------|-------------------------------|
| **MTTR** | Tiempo medio desde la detección de la alerta hasta la finalización del workflow (segundos) | P50 ≤ 120 s, P90 ≤ 180 s | Ver `soar-metrics` en Elasticsearch o el dashboard de Grafana |
| **P50** | Percentil 50 de los tiempos de respuesta observados | ≤ 120 s | Consulta ES `percentiles` sobre `mttr_seconds` |
| **P90** | Percentil 90 de los tiempos de respuesta observados | ≤ 180 s | Consulta ES `percentiles` sobre `mttr_seconds` |

**Comandos reproducibles para MTTR / percentiles:**

```bash
# Requisito: stack levantado y .env.full cargado
set -a; source .env.full; set +a

# 1. Contar documentos en soar-metrics
curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  "http://localhost:19200/soar-metrics/_count"

# 2. Calcular MTTR promedio y percentiles
curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:19200/soar-metrics/_search?size=0" \
  -d '{
    "aggs": {
      "avg_mttr": {"avg": {"field": "mttr_seconds"}},
      "percentiles_mttr": {"percentiles": {"field": "mttr_seconds", "percents": [50, 90]}}
    }
  }'

# 3. Verificar dashboard de Grafana
# Acceder a http://localhost:8084 y seleccionar "SOAR Ransomware KPI"
```

**Interpretación de las cifras documentadas**:

- Los valores `MTTR 31.85 s` y `P50 17.36 s` son **resultados de ejecuciones de prueba** en el entorno de laboratorio; dependen de la carga, recursos y latencia de red.
- Para validarlas en otro entorno, ejecutar los tests E2E (`pytest tests/e2e/ -m e2e`) y repetir las consultas anteriores.
- La fuente de verdad es el índice `soar-metrics` (`soar-metrics-v2`); Grafana y `artifacts/results/kpis.csv` son vistas derivadas.

### 7.3 Composition Root

El `CompositionRoot` en `src/soar_lab/interfaces/api/composition.py` ensambla los adaptadores de infraestructura con los puertos del dominio. Los elementos principales son:

| Instancia | Puerto / Rol | Implementación | Uso típico |
|-----------|--------------|----------------|------------|
| `config_provider` | Configuración centralizada | `InfrastructureConfigProvider` (`src/soar_lab/infrastructure/config_provider.py`) | Lee `Settings` y `.env.full`; resuelve JWT secret, CORS, URLs de servicios |
| `storage` | Almacenamiento de archivos | `FilesystemStorage` (`src/soar_lab/infrastructure/filesystem_storage.py`) | Guarda resultados CSV, backups temporales, artefactos |
| `alert_repository` | Repositorio de alertas | `SqliteAlertRepository` / `InMemoryAlertRepository` (`src/soar_lab/infrastructure/persistence/` y `src/soar_lab/infrastructure/`) | Persistencia de alertas durante la ejecución del workflow |
| `http_client` | Cliente HTTP genérico | `AioHTTPClient` (`src/soar_lab/infrastructure/http_client.py`) | Peticiones a TheHive, Cortex, Shuffle, MISP, Wazuh |
| `backup_driver` | Backup comprimido | `TarBackupDriver` (`src/soar_lab/infrastructure/tar_backup_driver.py`) | Genera `soar_backup_*.tar.gz` |
| `test_runner` | Ejecutor de tests | `PytestTestRunner` (`src/soar_lab/infrastructure/pytest_test_runner.py`) | Lanza `pytest` con los marcadores adecuados |
| `health_checker` | Chequeos de salud | `HTTPHealthCheckAdapter` + `HealthService` (`src/soar_lab/infrastructure/monitoring/`) | Verifica servicios externos y expone `/health` |
| `websocket_manager` | WebSocket `/ws/logs` | `ConnectionManager` (`src/soar_lab/infrastructure/websocket_manager.py`) | Streaming de logs a clientes conectados |

Las dependencias se inyectan en `src/soar_lab/interfaces/api/main.py` a través de ` lifespan()` o de `get_*` helpers en `src/soar_lab/interfaces/api/dependencies.py`.

### 7.4 Estructura hexagonal del código

La organización de `src/soar_lab/` sigue arquitectura hexagonal/ports-and-adapters:

- `domain/`: entidades, value objects, puertos y reglas de negocio puro.
- `application/`: casos de uso (`auth_service`, `backup_service`, `analytics_service`, `health_service`, etc.).
- `infrastructure/`: adaptadores (clientes HTTP, repositorios, drivers, gestores).
- `interfaces/`: puntos de entrada (FastAPI, CLI, WebSocket).
- `config/`: carga centralizada de variables de entorno y validación.
- `scripts/`: scripts de inicialización, setup y mantenimiento.

Ver detalles en:

- `docs/architecture/hexagonal-structure.md`
- `docs/architecture/code_structure.md`
- `docs/architecture/domain_app_inventory.md`

### 7.5 Distinción entre Elasticsearch, OpenSearch y Wazuh Indexer

| Componente | Rol en el laboratorio | Imagen / versión | Puerto host | Notas |
|------------|-----------------------|------------------|-------------|-------|
| **Elasticsearch** | Motor de búsqueda y persistencia principal (SOAR metrics, Shuffle indices) | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | `19200` | Usado por Shuffle, Grafana, KPIs y Lab API |
| **OpenSearch** | Motor de búsqueda alternativo / migración futura | `opensearchproject/opensearch:2.10.0` | `19201` (por defecto en `.env.example`) | No es el motor principal actual; compite como target de migración |
| **Wazuh Indexer** | Índice interno del stack Wazuh (basado en OpenSearch por parte de Wazuh) | `wazuh/wazuh-indexer:4.14.0` | No expuesto directamente (interno `9200`) | Servicio `wazuh.indexer`; no confundir con el nodo OpenSearch genérico |

La documentación operativa debe referirse al nombre completo del servicio (`elasticsearch` para el core del laboratorio, `wazuh.indexer` para Wazuh) para evitar ambigüedades. No se usa Kibana; Grafana es la herramienta de visualización central.

### 7.6 Estado de capacidades (implementado / simulado / planificado / no verificado)

Esta tabla complementa la matriz de integraciones de la sección 4. Los estados se extraen del código y de los tests; en caso de discrepancia prevalece el comportamiento verificable.

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Webhook Wazuh → Shuffle | Implementado | `src/soar_lab/scripts/setup/init_shuffle_webhook.py` |
| Creación/actualización de casos en TheHive | Implementado | Cliente y tests de integración |
| Ejecución de analyzers en Cortex | Implementado | Requiere API key y apps descargadas |
| Enriquecimiento MISP y correlación de IoCs | Implementado | Sincronización bidireccional puede requerir ajuste manual |
| Cálculo e indexado de KPIs (MTTR) | Implementado | Índice `soar-metrics` (`soar-metrics-v2`) |
| Dashboard de Grafana | Implementado | Datasource y `kpi-dashboard.json` |
| Contención real de endpoints | Simulado | `notify.sh` / `api/v1/contain` registran la acción; no modifican hosts reales sin agente EDR |
| MFA / SSO | Planificado / No verificado | Autenticación actual basada en JWT `HS256` |
| WAF / mTLS avanzado | Planificado / No verificado | Nginx actúa como proxy inverso con certificado autofirmado |
| Alta disponibilidad | Planificado | Despliegue single-host actual |
| Notificaciones por SMS / ticket externo | No implementado | Puede añadirse como workflow futuro |

### 7.7 Trabajo futuro y límites del alcance

Capacidades que quedan fuera del alcance operativo actual y que deben tratarse como trabajo futuro o investigación:

1. **Contención real de endpoints**: integrar un EDR/agente real (Wazuh active-response, GRR, Velociraptor, etc.) o un firewall con API operativa.
2. **MFA/SSO**: evaluar OAuth2 / OIDC para la Lab API y web-management.
3. **WAF**: añadir reglas de seguridad a Nginx o desplegar un WAF dedicado.
4. **mTLS entre servicios**: certificados por servicio y verificación bidireccional.
5. **Alta disponibilidad**: replicación de Elasticsearch, múltiples nodos Shuffle, clustering de Wazuh.
6. **Integraciones adicionales**: ServiceNow, Jira, Slack, Teams, Telegram.

### 7.8 Scripts de mantenimiento

Los scripts de mantenimiento se ubican en `src/soar_lab/scripts/maintenance/`:

- `update_wazuh_compose.py`: regenera `infra/docker/wazuh/docker-compose.yml` y `infra/docker/compose/docker-compose.wazuh.yml` sin incluir contraseñas hardcodeadas; las credenciales se leen de `.env.full` mediante variables de entorno (`${WAZUH_API_PASSWORD}`, `${WAZUH_INDEXER_PASSWORD}`, `${WAZUH_DASHBOARD_PASSWORD}`).
- `check_opensearch.py`: utiliza `OPENSEARCH_URL`, `OPENSEARCH_USERNAME` y `OPENSEARCH_PASSWORD` desde el entorno; si `OPENSEARCH_PASSWORD` no está definida, el script falla con un mensaje claro.

El término "Nivel III" no se utiliza en la documentación operativa actual. Los scripts se clasifican simplemente como **mantenimiento** (modifican artefactos generados) o **diagnóstico** (consultan estado).

### 7.9 Registro de cambios

Cada modificación sustantiva de configuración, código o documentación debe registrarse con:

- Archivo(s) afectado(s).
- Motivo del cambio.
- Evidencia de validación (comando ejecutado, test superado, diff).
- Fecha y entorno.

Para el registro formal del proyecto se usa [CHANGELOG.md](../../CHANGELOG.md) (raíz). Para la trazabilidad técnica detallada se usa [docs/audit/TRACEABILITY_VALIDATION.md](../audit/TRACEABILITY_VALIDATION.md).
