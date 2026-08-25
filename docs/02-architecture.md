# Arquitectura — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
 - [1.1 Objetivo](#11-objetivo)
 - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
 - [2.1 Qué cubre](#21-qué-cubre)
 - [2.2 Límites](#22-límites)
 - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
 - [3.1 Visión general de arquitectura](#31-visión-general-de-arquitectura)
 - [3.2 Aplicaciones y componentes](#32-aplicaciones-y-componentes)
 - [3.3 Estructura de código](#33-estructura-de-código)
 - [3.4 Composition root](#34-composition-root)
 - [3.5 Arquitectura Docker](#35-arquitectura-docker)
 - [3.6 Arquitectura hexagonal](#36-arquitectura-hexagonal)
 - [3.7 Inventario de dominio y aplicaciones](#37-inventario-de-dominio-y-aplicaciones)
 - [3.8 Coexistencia de motores de búsqueda](#38-coexistencia-de-motores-de-búsqueda)
 - [3.9 Seguridad](#39-seguridad)
 - [3.10 Matriz de versiones](#310-matriz-de-versiones)
- [4. Validación](#4-validación)
 - [4.1 Verificación](#41-verificación)
 - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
 - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
 - [5.1 Limitaciones](#51-limitaciones)
 - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
 - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones-troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Describir la arquitectura del sistema, componentes y principios de diseño del SOAR Ransomware Lab.

### 1.2 Contexto

Plataforma de orquestación de seguridad integral para respuesta ante incidentes de ransomware. Integra Shuffle, TheHive, Cortex y MISP en un entorno Docker Compose unificado.

---

## 2. Alcance

### 2.1 Qué cubre

- Arquitectura de alto nivel del sistema
- Componentes principales y sus interacciones
- Arquitectura de código (hexagonal) y de despliegue (Docker)
- Seguridad y matriz de versiones

### 2.2 Límites

- No cubre detalles de configuración específicos de cada herramienta
- No cubre procedimientos operativos paso a paso (ver 04-operations.md)

### 2.3 Dependencias

- Archivos Docker Compose en `infra/docker/compose/`
- Código fuente en `src/soar_lab/`

---

## 3. Contenido principal

### 3.1 Visión general de arquitectura


Este documento describe la arquitectura del sistema, componentes y principios de diseño del SOAR Ransomware Lab. Su
objetivo es proporcionar una visión integral de la plataforma para comprender su estructura, flujo de datos, seguridad y
despliegue.


El SOAR Ransomware Lab es una plataforma de orquestación de seguridad integral diseñada específicamente para la
respuesta ante incidentes de ransomware. Integra múltiples herramientas de seguridad (Shuffle, TheHive, Cortex, MISP) en un entorno Docker Compose unificado para proporcionar capacidades de detección, análisis y
respuesta
automatizada.


Este documento cubre:

- Arquitectura de alto nivel del sistema
- Componentes principales y sus interacciones
- Flujo de datos y procesamiento de alertas
- Arquitectura de seguridad y defensa en profundidad
- Estrategias de escalabilidad y rendimiento
- Arquitectura de integración y patrones
- Configuración de despliegue (Docker Compose)
- Stack tecnológico y herramientas de desarrollo
- Consideraciones de arquitectura futura


Este documento no cubre:

- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver user_guide.md)
- Estrategias de pruebas específicas (ver testing/)
- Planificación del proyecto (ver docs/06-project-management.md)
- Contratos de API detallados (ver docs/03-api-and-integrations.md)


Este documento depende de:

- Documentación oficial de cada componente (Shuffle, TheHive, Cortex, MISP)
- Archivos de configuración Docker Compose en `infra/docker/compose/`
- Documentación de seguridad (docs/02-architecture.md)
- Guía de usuario (docs/01-getting-started.md)
- Estrategia de Docker (docs/02-architecture.md)
- Estructura del paquete Python (docs/02-architecture.md)
- Estructura del código fuente (docs/02-architecture.md)


#### 3.1 Arquitectura general

#### Arquitectura de Código (Python)

El código Python sigue una **arquitectura hexagonal (Ports and Adapters)**. Las dependencias apuntan siempre hacia el
interior; el dominio no conoce detalles de infraestructura ni de interfaces de usuario.

```
src/soar_lab/
├── application/ # Capa de aplicación
│ ├── ports/ # Definición de puertos (interfaces) de entrada/salida
│ └── use_cases/ # analytics_service, auth_service, backup_service, etc.
├── auth/ # Re-export de AuthService (fachada)
├── common/ # Excepciones y utilidades compartidas
├── config/ # Configuración, esquemas y logging
├── data/ # Esquemas y utilidades de datos
├── domain/ # Capa de dominio
│ ├── models.py # Entidades: IOC, Alert, Case
│ ├── ports/ # Protocolos (repositories, integrations, infrastructure)
│ ├── services/ # kpi_analyzer, ioc_generator
│ └── statistical_calculator.py # Cálculos estadísticos puros
├── infrastructure/ # Capa de infraestructura
│ ├── integrations/ # Clientes externos (Shuffle, TheHive, Cortex, MISP, Elasticsearch)
│ ├── messaging/ # Envío de alertas
│ ├── monitoring/ # Health checks, HealthService, SystemMetricsDriver, KPIAlertManager
│ ├── network_watcher/ # Conectividad dinámica de workers Shuffle
│ ├── persistence/ # Repositorios (SQLite, InMemory)
│ ├── scripts/ # Scripts auxiliares de infraestructura
│ ├── security/ # Hardening (no implementado; escaneo vía Trivy en CI)
│ ├── templates/ # Plantillas de configuración
│ ├── jwt_token_provider.py # Generación y validación de tokens JWT
│ ├── pytest_test_runner.py # Ejecución remota de pruebas
│ ├── tar_backup_driver.py # Driver de backups en tar
│ └── validate_credentials.py # Validación de credenciales de servicios
├── interfaces/ # Capa de interfaces
│ └── api/ # FastAPI: main.py, auth.py, models.py, cli.py, composition.py
├── logging/ # StructuredLogger wrapper
├── resilience/ # Circuit breaker, retry, timeout
├── security/ # PayloadSanitizer
├── simulator/ # Simulador de alertas SIEM
└── validation/ # Validadores reutilizables
```

**Composition Root:** `src/soar_lab/interfaces/api/composition.py` centraliza el cableado de dependencias. Es el único
lugar donde se instancian adaptadores de infraestructura y se inyectan en los servicios de aplicación y dominio.
Nuevos adaptadores o servicios deben registrarse aquí para mantener la separación de capas.

> **Matrices de referencia**: versiones en [`02-architecture.md`](02-architecture.md) y mapeo de puertos/URLs en
> [`04-operations.md`](04-operations.md).

#### Arquitectura de Despliegue (Docker)

```mermaid
graph TD
 subgraph "Acceso recomendado (soar.local 443 / Nginx)"
 User -->|https://soar.local| Nginx
 Nginx -->|/| WebMgmt[Web Management]
 Nginx -->|/api/| LabAPI[Lab API]
 Nginx -->|/thehive/| TheHive
 Nginx -->|/cortex/| Cortex
 Nginx -->|/shuffle-api/| ShuffleBackend
 end

 subgraph "Acceso directo (solo diagnóstico)"
 ShuffleUI[Shuffle UI :8081]
 MISP[MISP :8083]
 Grafana[Grafana :8084]
 DocsSite[Docs Site :8086]
 end

 subgraph "Docker network: soar_net"
 LabAPI -- HTTP --> ShuffleBackend[Shuffle Backend :5001]
 LabAPI -- HTTP --> TheHive[TheHive :9000]
 LabAPI -- HTTP --> Cortex[Cortex :9001]
 LabAPI -- HTTP --> ES[Elasticsearch :9200]
 LabAPI -- HTTP --> Redis[Redis :6379]
 LabAPI -- HTTP --> MISPInternal[MISP :80]
 LabAPI -- HTTP --> GrafanaInternal[Grafana :3000]

 ShuffleBackend -- HTTP --> ES
 ShuffleBackend -- HTTP --> Redis
 ShuffleBackend -- HTTP --> Orborus[Orborus :5000]

 TheHive -- HTTP --> ES
 TheHive -- HTTP --> Cortex

 Cortex -- HTTP --> ES
 Cortex -- HTTP --> MISPInternal


 MISPInternal -- SQL --> MariaDB[MariaDB :3306]

 GrafanaInternal -- HTTP --> ES
 GrafanaInternal -- HTTP --> Loki[Loki :3100]
 Promtail[Promtail] --> Loki
 end

 subgraph "Docker network: logging_net"
 Promtail
 Loki
 GrafanaInternal
 end

 Nginx -. Directo .-> LabAPI
```

> **Nota sobre accesos directos:** Shuffle UI Dashboard, MISP, Grafana y Docs Site usan SPA/assets absolutos y no funcionan correctamente bajo subpath en Nginx. Se acceden por sus puertos de host (`8081`, `8202`, `8083`, `8084`, `8086`).

#### Servicios SOAR Core

1. **Shuffle** (`:8081` UI host / `:5001` API host)
 - Orquestador SOAR principal
 - Constructor de workflows drag-and-drop
 - Ejecuta playbooks de respuesta automatizada
 - Orborus ejecuta contenedores de apps como workers

2. **TheHive** (`:8100` host → `:9000` container)
 - Plataforma de gestión de casos de incidentes
 - Seguimiento de evidencias y observables
 - Asignación de tareas y línea de tiempo
 - Se integra con Cortex para enriquecimiento

3. **Cortex** (`:8101` host → `:9001` container)
 - Motor de análisis de IoCs
 - Ejecuta analyzers y responders
 - Se integra con MISP, VirusTotal, etc.
 - Soporte para analyzers personalizados en Python

#### SIEM / Detección

4. **OpenSearch Dashboards** (`:8202` host → `:5601` container)
 - Exploración de logs vía Discover

#### Inteligencia de Amenazas

5. **MISP** (`:8083`)
 - Plataforma de inteligencia de amenazas open-source
 - Compartición y gestión de IoCs
 - Integración de feeds
 - Conectado a analyzers de Cortex

#### Capa de Datos

7. **Elasticsearch** (red Docker interna)
 - `docker.elastic.co/elasticsearch/elasticsearch:7.10.2`
 - Backend para TheHive, Cortex, métricas del Lab API (`soar-metrics`) y datasource de Grafana
 - Agregación de logs y búsqueda full-text
 - Configuración single-node con `xpack.security.enabled=false`; se mantiene un password canónico `ELASTIC_PASSWORD=ElasticLab2024SecurePass` en `.env.full` y en las aplicaciones para compatibilidad con clientes que sí envían credenciales.
 - **No es redundancia**: OpenSearch 2.10.0 se despliega en paralelo porque Shuffle requiere un motor OpenSearch nativo, mientras que TheHive/Cortex dependen de `elastic4play` / ES 7.x (ver [Motores de búsqueda: coexistencia de Elasticsearch y OpenSearch](#38-coexistencia-de-motores-de-búsqueda)).

8. **Redis** (interno)
 - Almacenamiento de sesiones y caché para Shuffle
 - Cola de mensajes

9. **MariaDB** (interno)
 - Backend de base de datos para MISP

10. **Tenzir** (nodo de desarrollo, opcional)
 - Imagen: `tenzir/tenzir:v6.8.1`
 - Puertos host: `15160` → `5160`, `15140` → `1514/udp`
 - Estado: desplegado en `docker-compose.core.yml` pero su pipeline de ingestión no está integrado en los playbooks activos del laboratorio.

#### Acceso y Gestión

10. **Nginx** (`:80`, `:443`)
 - Terminación TLS y proxy inverso en `:443`; `:80` redirige a HTTPS
 - Expone `/` → Web Management, `/thehive/` → TheHive, `/cortex/` → Cortex, `/shuffle-api/` → Shuffle Backend
 - Shuffle UI (`:8081`), Web Management (`:8085`), Docs Site (`:8086`) y Grafana (`:8084`) se acceden directamente por sus puertos
 - **Shuffle UI no soporta subpath en Nginx** (`/shuffle` no funciona por rutas SPA absolutas); usar siempre `http://localhost:8081`

11. **Lab API** (`:8000`)
 - Aplicación FastAPI (`src/soar_lab/interfaces/api/main.py`)
 - Endpoints de gestión y automatización del laboratorio
 - Health check en `/health`
 - WebSocket `/api/ws/logs` para streaming de logs en vivo

12. **Docs Site** (`:8086`)
 - Sitio estático Docusaurus
 - Servido directamente en puerto 8086

#### Zonas de Seguridad

```
┌─────────────────────────────────────────────────────────────┐
│ Zona DMZ │
│ Web UI │ API Gateway │ Load Balancer │
├─────────────────────────────────────────────────────────────┤
│ Zona de Aplicación │
│ FastAPI │ Lógica de Negocio │ Autenticación │
├─────────────────────────────────────────────────────────────┤
│ Zona de Datos │
│ TheHive │ Cortex │ OpenSearch │ PostgreSQL │
├─────────────────────────────────────────────────────────────┤
│ Zona de Gestión │
│ Docker │ Monitoreo │ Logging │ Backup │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Componentes y servicios

#### Estado Actual de la Arquitectura Hexagonal

El proyecto organiza el código en capas con dirección de dependencias hacia el interior:

- **`src/soar_lab/domain/`**: modelos (`models.py`), puertos (`ports/`) y servicios de dominio (`services/`).
- **`src/soar_lab/application/`**: casos de uso (`use_cases/`) que dependen de los puertos del dominio.
- **`src/soar_lab/infrastructure/`**: adaptadores concretos (`integrations/*`, `persistence/*`, `monitoring/`, `messaging/`, `jwt_token_provider.py`, etc.).
- **`src/soar_lab/interfaces/api/composition.py`**: Composition Root que crea los adaptadores, repositorios y servicios y los inyecta en la aplicación FastAPI.

**Deuda Técnica:**

- `domain/ports/` es extenso; su adopción parcial hace que algunos scripts y helpers aún usen implementaciones concretas.
- Los clientes externos (`infrastructure/integrations/`) se usan mayoritariamente vía la fachada de la API y tests; parte del wiring legacy queda por migrar al CompositionRoot.
- La trayectoria es seguir consolidando el CompositionRoot como único punto de creación de instancias.

#### Lógica de Negocio / Servicios (Python)

**Servicios Actuales:**

- **`src/soar_lab/application/use_cases/analytics_service.py`**: Servicio de análisis de alertas y métricas. Depende de domain/ports (AlertRepository,
 MetricRepository, IocRepository, IOCGenerator, StatisticalCalculatorInterface)
- **`src/soar_lab/application/use_cases/auth_service.py`**: Servicio de autenticación y autorización. Depende de domain/ports (TokenProviderInterface)
- **`src/soar_lab/application/use_cases/backup_service.py`**: Servicio de backup y restauración. Depende de domain/ports (BackupDriver,
 BackupStorageProvider)
- **`src/soar_lab/infrastructure/monitoring/health_service.py`**: Servicio de health checks. Depende de domain/ports (HealthCheckInterface,
 SystemMetricsInterface)
- **`src/soar_lab/domain/services/kpi_analyzer.py`**: Analizador de KPIs y métricas. Depende de domain/ports (StatisticalCalculatorInterface)
- **`scripts/test_service.py`**: Servicio de ejecución de pruebas. Depende de domain/ports (CacheInterface, TestRunner,
 TestResultParserInterface)
- **`scripts/setup/generate_secrets.py`**: Generador de secretos y claves. Depende de domain/ports (FileSystemInterface)

**Dependencias:**

- Los servicios dependen correctamente de domain/ports/ para interfaces (no de infrastructure directamente)
- Esto es consistente con el patrón hexagonal
- Sin embargo, la inyección de dependencias no está completamente implementada en toda la aplicación

#### Servicios SOAR Core

1. **Shuffle** (`:8081` UI host / `:5001` API host)
 - Orquestador SOAR principal
 - Constructor de workflows drag-and-drop
 - Ejecuta playbooks de respuesta automatizada
 - Orborus ejecuta contenedores de apps como workers

2. **TheHive** (`:8100` host → `:9000` container)
 - Plataforma de gestión de casos de incidentes
 - Seguimiento de evidencias y observables
 - Asignación de tareas y línea de tiempo
 - Se integra con Cortex para enriquecimiento

3. **Cortex** (`:8101` host → `:9001` container)
 - Motor de análisis de IoCs
 - Ejecuta analyzers y responders
 - Se integra con MISP, VirusTotal, etc.
 - Soporte para analyzers personalizados en Python

#### SIEM / Detección

4. **OpenSearch Dashboards** (`:8202` host → `:5601` container)
 - Exploración de logs vía Discover

#### Inteligencia de Amenazas

5. **MISP** (`:8083`)
 - Plataforma de inteligencia de amenazas open-source
 - Compartición y gestión de IoCs
 - Integración de feeds
 - Conectado a analyzers de Cortex

#### Capa de Datos

7. **Elasticsearch** (red Docker interna)
 - `docker.elastic.co/elasticsearch/elasticsearch:7.10.2`
 - Backend para TheHive, Cortex, métricas del Lab API (`soar-metrics`) y datasource de Grafana
 - Agregación de logs y búsqueda full-text
 - Configuración single-node con `xpack.security.enabled=false`; se mantiene un password canónico `ELASTIC_PASSWORD=ElasticLab2024SecurePass` en `.env.full` y en las aplicaciones para compatibilidad con clientes que sí envían credenciales.
 - **No es redundancia**: OpenSearch 2.10.0 se despliega en paralelo porque Shuffle requiere un motor OpenSearch nativo, mientras que TheHive/Cortex dependen de `elastic4play` / ES 7.x (ver [Motores de búsqueda: coexistencia de Elasticsearch y OpenSearch](#38-coexistencia-de-motores-de-búsqueda)).

8. **Redis** (interno)
 - Almacenamiento de sesiones y caché para Shuffle
 - Cola de mensajes

9. **MariaDB** (interno)
 - Backend de base de datos para MISP

10. **Tenzir** (nodo de desarrollo, opcional)
 - Imagen: `tenzir/tenzir:v6.8.1`
 - Puertos host: `15160` → `5160`, `15140` → `1514/udp`
 - Estado: desplegado en `docker-compose.core.yml` pero su pipeline de ingestión no está integrado en los playbooks activos del laboratorio.

#### Acceso y Gestión

10. **Nginx** (`:80`, `:443`)
 - Terminación TLS y proxy inverso en `:443`; `:80` redirige a HTTPS
 - Expone `/` → Web Management, `/thehive/` → TheHive, `/cortex/` → Cortex, `/shuffle-api/` → Shuffle Backend
 - Shuffle UI (`:8081`), Web Management (`:8085`), Docs Site (`:8086`) y Grafana (`:8084`) se acceden directamente por sus puertos

11. **Lab API** (`:8000`)
 - Aplicación FastAPI (`src/soar_lab/interfaces/api/main.py`)
 - Endpoints de gestión y automatización del laboratorio
 - Health check en `/health`
 - WebSocket `/api/ws/logs` para streaming de logs en vivo

12. **Docs Site** (`:8086`)
 - Sitio estático Docusaurus
 - Servido directamente en puerto 8086

#### 3.4 Flujos principales

#### Pipeline de Procesamiento de Alertas

```
Fuentes de Alertas → API de Ingestión → Validación → Enriquecimiento → Scoring → Almacenamiento → Análisis → Respuesta
```

1. **Ingestión**: Múltiples fuentes de alertas (SIEM, EDR, APIs personalizadas)
2. **Validación**: Validación de esquema y normalización de datos
3. **Enriquecimiento**: Extracción de IoCs, búsqueda de inteligencia de amenazas
4. **Scoring**: Evaluación automatizada de severidad
5. **Almacenamiento**: Almacenamiento persistente en TheHive/OpenSearch
6. **Análisis**: Reconocimiento de patrones y detección de anomalías
7. **Respuesta**: Ejecución automatizada de playbooks

#### Flujo de Respuesta

```
Detección de Alerta → Triage → Investigación → Contención → Erradicación → Recuperación → Reporte
```

#### Real vs. Simulado en la Respuesta

| Fase | Estado | Evidencia / Notas | |------|--------|-------------------| | Detección | Real | Agentes y manager levantados en Docker; alertas generadas por simulador o agente real | | Ingesta Webhook (Shuffle) | Real | `init_shuffle_webhook.py` crea workflow y webhook en Shuffle | | Triage (Shuffle) | Real | Reglas del workflow evalúan severidad y contexto | | Enriquecimiento (Cortex/MISP) | Real | Analyzers y búsquedas en MISP ejecutados en contenedores | | Creación de caso (TheHive) | Real | Caso, observables y tareas creados por API | | Contención de endpoint | Simulado | `notify.sh` / acciones de contención notifican pero no aíslan la red real; requiere agente EDR real para acción real | | Erradicación/Recuperación | Simulado | Scripts de notificación y métricas; no se eliminan amenazas reales | | Métricas (MTTR/KPIs) | Real | Cálculo e indexación en `soar-metrics` y Grafana |

> Ver también [`docs/02-architecture.md`](#39-seguridad) para la matriz de controles de seguridad.

#### Integraciones Externas

1. **Herramientas de Seguridad**
 - Sistemas SIEM (Splunk, ELK)
 - Soluciones EDR (CrowdStrike, SentinelOne)
 - Plataformas de inteligencia de amenazas
 - Escáners de vulnerabilidades

2. **Sistemas de Comunicación**
 - Notificaciones por email
 - Integración Slack/Teams
 - Alertas SMS
 - Callbacks de webhook

3. **Infraestructura**
 - Proveedores cloud (AWS, Azure, GCP)
 - Orquestación de contenedores (Kubernetes)
 - Plataformas de logging (Splunk, ELK)

#### Patrones de Integración

1. **Integración basada en API**
 - APIs RESTful
 - Interfaces GraphQL
 - Suscripciones de webhook
 - Arquitectura event-driven

2. **Integración basada en Mensajes**
 - Colas RabbitMQ
 - Streams Apache Kafka
 - Redis pub/sub
 - Event sourcing

3. **Integración basada en Archivos**
 - Importaciones CSV/JSON
 - Parsing de archivos de log
 - Sincronización de configuración
 - Operaciones de backup/restore

#### Diagramas de Secuencia de Integración

**Flujo de Alerta SIEM → Shuffle → TheHive → Cortex:**

```mermaid
sequenceDiagram
 participant SIEM as SIEM Simulado
 participant Shuffle as Shuffle Webhook
 participant Backend as Shuffle Backend
 participant TheHive as TheHive API
 participant Cortex as Cortex API
 participant ES as OpenSearch

 SIEM->>Shuffle: POST /api/v1/hooks/webhook (alert)
 Shuffle->>Backend: Reenvía alerta
 Backend->>ES: Valida y almacena alerta
 Backend->>TheHive: POST /api/case (crear caso)
 TheHive->>ES: Almacena caso
 Backend->>Cortex: POST /api/analyzer/run (analyzers)
 Cortex->>ES: Consulta IoCs
 Cortex-->>Backend: Resultados de análisis
 Backend->>TheHive: PATCH /api/case (actualizar con IoCs)
 Backend-->>SIEM: Confirmación de procesamiento
```

**Flujo de Respuesta Automatizada:**

```mermaid
sequenceDiagram
 participant Shuffle as Shuffle Orborus
 participant TheHive as TheHive
 participant Cortex as Cortex
 participant Scripts as Scripts de Contención
 participant as

 Shuffle->>TheHive: Consulta caso y observables
 TheHive-->>Shuffle: Datos del caso
 Shuffle->>Cortex: Ejecuta analyzers en IoCs
 Cortex-->>Shuffle: Resultados (score, verdict)
 alt Score ≥ 80 o verdict malicioso
 Shuffle->>Scripts: Ejecuta contención simulada
 Scripts->>: Notificación de aislamiento
 Shuffle->>TheHive: Marca como "contención activada"
 else Score < 80 y verdict benigno
 Shuffle->>TheHive: Marca como "benigno"
 end
 Shuffle-->>TheHive: Actualización final del caso
```

#### 3.3 Redes, puertos y dependencias

#### Servicios, Puertos y Redes

| Servicio | Imagen | Puerto host→contenedor | Redes | |--------------------|-------------------------------------------------------|---------------------------------------|-----------------------| | `nginx` | nginx:1.25-alpine | `80:80`, `443:443` | soar_net, logging_net | | `thehive` | thehiveproject/thehive:3.5.2-1 | `${THEHIVE_HTTP_PORT:-8100}:9000` | soar_net | | `cortex` | build `infra/docker/images/cortex/Dockerfile` (FROM `thehiveproject/cortex:3.2.0-1`) | `${CORTEX_HTTP_PORT:-8101}:9001` | soar_net | | `shuffle-backend` | ghcr.io/shuffle/shuffle-backend:2.2.1* | `${SHUFFLE_API_PORT:-5001}:5001` | soar_net | | `shuffle-frontend` | ghcr.io/shuffle/shuffle-frontend:2.2.1* | `${SHUFFLE_UI_PORT:-8081}:80` | soar_net | | `orborus` | build `infra/docker/images/orborus/Dockerfile` (tag `ghcr.io/shuffle/shuffle-orborus:2.2.1-patched`) | — (interno) | soar_net | | `elasticsearch` | docker.elastic.co/elasticsearch/elasticsearch:7.10.2 | `${ELASTICSEARCH_PORT:-8200}:9200` | soar_net, ti_net | | `redis` | redis:7-alpine | `${REDIS_PORT:-6379}:6379` | soar_net, ti_net | | `misp` | ghcr.io/misp/misp-docker/misp-core:v2.5.44* | `${MISP_PORT:-8083}:80` | soar_net | | `misp-db` | mariadb:10.11 | — (interno) | soar_net | | `misp-modules` | ghcr.io/misp/misp-docker/misp-modules:v3.0.9* | — (interno) | soar_net | | `api` | build: apps/api/Dockerfile | `${API_PORT:-8000}:8000` | soar_net, ti_net | | `web-management` | build: apps/web-management/Dockerfile | `8085:80` | soar_net | | `docs-site` | build: apps/docs-site/Dockerfile | `${DOCS_PORT:-8086}:8080` | soar_net | | `loki` | grafana/loki:2.9.10 | — (interno) | logging_net | | `promtail` | grafana/promtail:2.9.9 | — (interno) | logging_net | | `grafana` | grafana/grafana:10.3.4 | `${GRAFANA_PORT:-8084}:3000` | logging_net, soar_net | | `grafana-db` | postgres:14-alpine | — (interno) | logging_net |

#### Redes Docker

| Red | Driver | Subred | Propósito | |---------------|-------------------|-----------------|-----------------------------------------------------------------------------------| | `soar_net` | bridge | `10.100.0.0/16` | Red interna principal — todos los servicios SOAR | | `ti_net` | bridge (internal) | `172.22.0.0/16` | Red de Threat Intelligence — Elasticsearch, Redis, API, MISP (sin acceso externo) | | `logging_net` | bridge | `172.23.0.0/16` | Red de logging — Loki, Promtail, Grafana |

> ⚠️ **Windows/Hyper-V**: rangos de puertos 55000–55099 y 5600–5699 están excluidos por reservas de Hyper-V. Los puertos
> del stack están configurados fuera de esos rangos (ver `.env.full`).

#### Volúmenes Persistentes

| Volumen | Servicio | Contenido persistido | |---------------------------|-----------------|------------------------------------------------------------------| | `thehive_files` | thehive | Ficheros adjuntos a casos e incidentes | | `cortex_data` | cortex | Configuración y datos de analyzers | | `es_data` | elasticsearch | Índices y datos de búsqueda (TheHive, Shuffle, métricas del Lab API) | | `redis_data` | redis | Persistencia de sesiones y caché de Shuffle | | `shuffle_apps` | shuffle-backend | Apps y workflows de Shuffle | | `shuffle_files` | shuffle-backend | Ficheros subidos al orquestador | | `misp_files` | misp | Eventos e IoCs de MISP | | `misp_db` | misp-db | Base de datos MariaDB de MISP | | `misp_configs` | misp | Configuración de MISP | | `misp_logs` | misp | Logs de aplicación de MISP | | `nginx_logs` | nginx | Logs de acceso y error del proxy | | `loki_data` | loki | Logs almacenados en Loki | | `grafana_data` | grafana | Configuración y dashboards de Grafana | | `grafana_db_data` | grafana-db | Base de datos PostgreSQL de Grafana |

#### Stack Tecnológico

**Tecnologías principales**

- **Backend**: Python 3.11, FastAPI (`src/soar_lab/interfaces/api/main.py`)
- **Frontend**: HTML/JS estático (Web Management), React (Shuffle)
- **Orquestación SOAR**: Shuffle (`ghcr.io/shuffle/shuffle-backend`, `-frontend`, `-orborus` 2.2.1)
- **Gestión de casos**: TheHive 3.5.2-1 + Cortex 3.2.0-1
- **Inteligencia de amenazas**: MISP 2.5.44 (`ghcr.io/misp/misp-docker/misp-core`)
- **Búsqueda e índices**: Elasticsearch 7.10.2
- **Caché**: Redis 7
- **Proxy inverso / TLS**: Nginx 1.25
- **Documentación**: Docusaurus 3 (`apps/docs-site`)
- **Contenerización**: Docker Compose 2

**Tecnologías de seguridad**

- **Autenticación**: JWT con `PyJWT`, algoritmo `HS256`
- **Cifrado en tránsito**: TLS 1.2/1.3 vía Nginx con certificados autofirmados
- **Escaneo de vulnerabilidades**: Trivy en CI (`.github/workflows/ci.yml`, job `security-scan`)
- **Gestión de secretos**: Variables de entorno `.env.full`; generación mediante `soar-lab generate-secrets`

**Herramientas de desarrollo**

- **Control de versiones**: Git, GitHub
- **CI/CD**: GitHub Actions
- **Pruebas**: pytest (unit, integration, atomic, e2e, contracts, security, performance)
- **Documentación**: Docusaurus (portal oficial); Swagger/OpenAPI como fuente de contratos HTTP

#### 3.5 Diagramas y tablas de apoyo

#### Diagrama de Arquitectura de Capas

El diagrama de arquitectura de alto nivel presentado en la sección 3.1 muestra la organización en capas del sistema,
desde la capa de acceso hasta la capa de datos e infraestructura.

#### Zonas de Seguridad

El diagrama de zonas de seguridad presentado en la sección 3.1 muestra la segmentación de red en cuatro zonas
principales: DMZ, Aplicación, Datos y Gestión.

#### Matriz de estado funcional por componente

| Componente / Capacidad | Estado | Evidencia / Notas | |------------------------|--------|---------------------| | Nginx (proxy inverso + TLS) | Parcial | Termina TLS en `https://soar.local`; no incluye WAF ni rate limiting avanzado | | Lab API (FastAPI) | Implementado | Endpoints de auth, analytics, backups, tests y proxy SOAR en `src/soar_lab/interfaces/api/main.py` | | Shuffle (workflows + webhook) | Implementado | Contenedores `shuffle-frontend`, `shuffle-backend`, `orborus`; workflow creado por `init_shuffle_webhook.py` | | TheHive | Implementado | Gestión de casos vía API en `soar_thehive:9000`; conexión con Cortex | | Cortex | Implementado | Analyzers ejecutados en contenedor; conexión con TheHive y MISP | | MISP | Implementado | Servicio `misp` en Docker; enriquecimiento de IoCs | | Elasticsearch | Implementado | `elasticsearch:9200`; backend para Shuffle, TheHive, métricas `soar-metrics` | | Redis | Implementado | Sesiones/caché de Shuffle | | Grafana + Loki + Promtail | Implementado | Dashboards en `:8084`; logs centralizados; plugin ES instalado | | Web Management | Implementado | SPA en `:8085` | | Network Watcher | Implementado | Reconecta workers de Shuffle a `soar_net` | | Tenzir Node | Parcial / No verificado | Desplegado en `docker-compose.core.yml` pero pipeline no integrado en playbooks activos | | Autenticación JWT | Implementado | Firma `HS256`; secret en `.env.full`; endpoints `/auth/login` y `/auth/verify` | | Autenticación MFA | Planificado | No hay implementación operativa | | Single Sign-On (SSO/SAML/OIDC) | Planificado | No implementado | | WAF | No verificado / Planificado | Nginx no está configurado como WAF | | DMZ / segmentación de red real | Simulado | Diagramas conceptuales; contenedores comparten Docker networks | | Contención de endpoints | Simulado | Acciones de contención son notificaciones/logs; no aísla endpoints reales sin agente EDR | | Erradicación / recuperación automatizada | Simulado | Backups y métricas reales; la erradicación real no se ejecuta | | Cifrado en tránsito (TLS) | Parcial | TLS en Nginx y ; tráfico interno Docker mayoritariamente HTTP | | Cifrado en reposo | Parcial / No verificado | Depende de configuración de Elasticsearch/OpenSearch/ |

### 3.2 Aplicaciones y componentes

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe las aplicaciones del proyecto ubicadas en `apps/`. Cada aplicación se empaqueta como un
contenedor Docker independiente y cumple una función específica dentro del laboratorio SOAR.

#### 1.2 Contexto

La carpeta `apps/` contiene tres aplicaciones:

- `api/` — API REST del laboratorio basada en FastAPI.
- `docs-site/` — Sitio de documentación estática generado con Docusaurus.
- `web-management/` — Panel de gestión web con HTML, CSS y JavaScript.

Cada aplicación tiene su propio `Dockerfile` y se despliega mediante `infra/docker/compose/docker-compose.api.yml`.

---

#### 2. `apps/api`

**Propósito:** Contenedor principal de la API REST del laboratorio.

**Base:** `python:3.11-slim`

**Componentes:**

- `Dockerfile` — Imagen Docker con dependencias Python, pytest y código fuente.
- `api-docs.html` — Documentación HTML de la API (legacy; la documentación actual está en `docs/` y `docs/03-api-and-integrations.md`).
- `docs/` — Documentación adicional empaquetada en el contenedor (legacy).
- `pyproject.toml` — Dependencias Python del servicio.

**Punto de entrada:**

```bash
uvicorn soar_lab.interfaces.api.composition:create_app --host 0.0.0.0 --port 8000 --factory
```

**Puerto expuesto:** `8000`

**Health check:** `curl -f http://localhost:8000/health || exit 1`

**Variables de entorno principales (`.env.full`):**

- `API_PORT` — puerto host para la API (por defecto `8000`).
- `CORS_ORIGINS` — orígenes permitidos para peticiones CORS.
- `JWT_SECRET_KEY` — secret preferente para firma JWT (mínimo 32 caracteres).
- `API_AUTH_SECRET` — secret legacy para firma JWT; solo se usa si `JWT_SECRET_KEY` no está definido.
- `WEB_UI_USER` / `WEB_UI_PASSWORD` — credenciales de acceso al Web Management.
- `THEHIVE_API_KEY`, `CORTEX_API_KEY`, `SHUFFLE_DEFAULT_APIKEY`, `MISP_API_KEY`, etc.

**Redes Docker:** `soar_net`, `ti_net`, `logging_net`.

**Acceso:**

- Directo: `http://localhost:8000`.
- A través de Nginx: `https://soar.local/api/`.
- Swagger/OpenAPI: `http://localhost:8000/docs` o `https://soar.local/api/docs`.

**Funciones expuestas:**

- `/health`, `/auth/login`, `/auth/verify`.
- `/analytics/metrics`, `/analytics/kpis`.
- `/services/status`.
- `/backup/create`, `/backup/list`, `/backup/restore`.
- `/tests/run`.
- `/ws/logs` (WebSocket de logs).
- Proxy a integraciones bajo `/soar/thehive/`, `/soar/cortex/`, `/soar/misp/`, `/soar/shuffle/`, etc.

**Notas:**

- El `Dockerfile` copia `src/` y `tests/` dentro del contenedor.
- Se usa el usuario `app` para ejecutar el servicio.
- El contenedor también se utiliza para ejecutar tests.

---

#### 3. `apps/docs-site`

**Propósito:** Sitio de documentación del proyecto construido con Docusaurus.

**Archivos principales:**

- `Dockerfile` — Imagen Docker basada en Node.js para servir el sitio estático.
- `docusaurus.config.js` — Configuración de Docusaurus.
- `package.json` — Dependencias Node.js.
- `sidebars.js` — Configuración de la barra lateral.
- `src/` — Código fuente y páginas del sitio.
- `docs/` — Documentación en formato Markdown.

**Puerto expuesto:** `8086` (mapeado al puerto `8080` del contenedor)

**Acceso:**

- Directo: `http://localhost:8086`.
- **No** se expone a través de Nginx con subpath; acceso directo únicamente.

**Dependencias:** Ninguna obligatoria; solo requiere la documentación Markdown en `docs/` montada en `/opt/docusaurus/docs`.

---

#### 4. `apps/web-management`

**Propósito:** Panel de gestión web estático del laboratorio.

**Archivos principales:**

- `Dockerfile` — Imagen ligera basada en Nginx.
- `index.html` — Página principal del panel.
- `script.js` — Lógica JavaScript del frontend.
- `styles.css` — Hojas de estilo.
- `nginx.conf` — Configuración de Nginx para servir la aplicación.

**Puerto expuesto:** `8085` (mapeado al puerto `80` del contenedor)

**Acceso:**

- Directo: `http://localhost:8085`.
- A través de Nginx: `https://soar.local/` (raíz del proxy).

**Comunicación con la API:**

- `script.js` usa `const API_BASE = '/api'` (ruta relativa), por lo que depende de que Nginx reescriba `https://soar.local/api/` a `http://api:8000`.
- El acceso directo `http://localhost:8085` **no expone `/api`**; en ese modo `script.js` intentará `http://localhost:8000/api/...`, que tampoco estará disponible en el puerto 8085. Para desarrollo o pruebas directas, setear `API_BASE = 'http://localhost:8000'` temporalmente y permitir `CORS_ORIGINS`.
- El token JWT se almacena en `localStorage`; no debe guardarse en cookies sin `HttpOnly`.
- Reconexión WebSocket contra `/ws/logs` (o `/api/ws/logs` si pasa por Nginx); Nginx transmite `Upgrade` y `Connection`.

**Nota:** Si se accede directamente por `http://localhost:8085`, asegúrate de que `CORS_ORIGINS` incluye `http://localhost:8085` y considera que `/api` no estará disponible sin un proxy inverso.

---

#### 5. Tabla resumen

| Aplicación | Servicio Compose | Contenedor (proyecto `soar`) | Tecnología | Puerto host | Puerto contenedor | Acceso recomendado | Vía Nginx | |------------|------------------|------------------------------|------------|-------------|-------------------|--------------------|-----------| | `apps/api` | `api` | `soar_api` | FastAPI / Python 3.11 | `8000` | `8000` | `http://localhost:8000` | Sí (`/api/`) | | `apps/docs-site` | `docs-site` | `soar_docs_site` | Docusaurus / Node.js | `8086` | `8080` | `http://localhost:8086` | No | | `apps/web-management` | `web-management` | `soar_web_management` | HTML / JS / Nginx | `8085` | `80` | `http://localhost:8085` | Sí (`/`) |

---

#### 6. Referencias

- [Arquitectura Docker](#35-arquitectura-docker)
- [Arquitectura general](#31-visión-general-de-arquitectura)
- [Guía de infraestructura](04-operations.md)
- [README principal](../README.md)


### 3.3 Estructura de código

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe la organización del código fuente en `src/soar_lab/` siguiendo una arquitectura hexagonal
(ports and adapters). El objetivo es separar la lógica de negocio pura de los detalles de infraestructura e interfaces.

#### 1.2 Contexto

Tras la refactorización, el código se reorganizó en cuatro capas principales:

- **Domain** — Lógica de negocio pura e interfaces abstractas.
- **Application** — Casos de uso y orquestación de servicios.
- **Infrastructure** — Implementaciones concretas, adaptadores y clientes externos.
- **Interfaces** — Puntos de entrada (API REST, CLI, webhooks).

---

#### 2. Visión general de `src/soar_lab`

```
src/soar_lab/
├── __init__.py
├── application/ # Capa de aplicación
│ ├── ports/ # Definición de puertos (interfaces) de entrada/salida
│ └── use_cases/ # analytics_service, auth_service, backup_service, etc.
├── auth/ # Re-export de AuthService (fachada)
├── common/ # Excepciones y utilidades compartidas
├── config/ # Configuración, esquemas y logging
├── data/ # Esquemas y utilidades de datos
├── domain/ # Capa de dominio
│ ├── models.py # Entidades: IOC, Alert, Case
│ ├── ports/ # Protocolos (repositories, integrations, infrastructure)
│ ├── services/ # kpi_analyzer, ioc_generator
│ └── statistical_calculator.py # Cálculos estadísticos puros
├── infrastructure/ # Capa de infraestructura
│ ├── integrations/ # Clientes externos (Shuffle, TheHive, Cortex, MISP, Elasticsearch)
│ ├── messaging/ # Envío de alertas
│ ├── monitoring/ # Health checks, HealthService, SystemMetricsDriver, KPIAlertManager
│ ├── network_watcher/ # Conectividad dinámica de workers Shuffle
│ ├── persistence/ # Repositorios (SQLite, InMemory)
│ ├── scripts/ # Scripts auxiliares de infraestructura
│ ├── security/ # Hardening (no implementado; escaneo vía Trivy en CI)
│ ├── templates/ # Plantillas de configuración
│ ├── jwt_token_provider.py # Generación y validación de tokens JWT
│ ├── pytest_test_runner.py # Ejecución remota de pruebas
│ ├── tar_backup_driver.py # Driver de backups en tar
│ └── validate_credentials.py # Validación de credenciales de servicios
├── interfaces/ # Capa de interfaces
│ └── api/ # FastAPI: routes, models, auth, cli, composition
├── logging/ # StructuredLogger wrapper
├── resilience/ # Circuit breaker, retry, timeout
├── security/ # PayloadSanitizer
├── simulator/ # Simulador de alertas SIEM
└── validation/ # Validadores
```

#### 2.1 Correspondencia puertos → adaptadores

Tabla one-to-one entre los protocolos del dominio y sus implementaciones concretas en infraestructura. Cada fila muestra el contrato (puerto), el adaptador que lo materializa y el archivo principal.

| Puerto (Protocol) | Definición | Adaptador / Implementación | Archivo principal | |---|---|---|---| | `AlertRepository` | `domain/ports/repositories.py` | `SqliteAlertRepository`, `InMemoryAlertRepository` | `infrastructure/persistence/sqlite_alert_repository.py`, `infrastructure/in_memory_alert_repository.py` | | `BackupDriver` | `domain/ports/infrastructure.py` | `TarBackupDriver` | `infrastructure/tar_backup_driver.py` | | `StorageProvider` | `domain/ports/infrastructure.py` | `FilesystemStorage` | `infrastructure/filesystem_storage.py` | | `TestRunner` | `domain/ports/infrastructure.py` | `PytestTestRunner` | `infrastructure/pytest_test_runner.py` | | `TestResultParserInterface` | `domain/ports/infrastructure.py` | `PytestOutputParser` | `infrastructure/pytest_output_parser.py` | | `ConfigProvider` | `domain/ports/infrastructure.py` | `InfrastructureConfigProvider` | `infrastructure/config_provider.py` | | `TokenProviderInterface` | `domain/ports/infrastructure.py` | `JWTTokenProvider` | `infrastructure/jwt_token_provider.py` | | `HTTPClient` | `domain/ports/infrastructure.py` | `AioHTTPClient` | `infrastructure/http_client.py` | | `SyncHTTPClient` | `domain/ports/infrastructure.py` | `BaseHTTPClient` | `infrastructure/integrations/base_client.py` | | `WebSocketManager` | `domain/ports/infrastructure.py` | `ConnectionManager` | `infrastructure/websocket_manager.py` | | `SystemMetricsInterface` | `domain/ports/infrastructure.py` | `SystemMetricsDriver` | `infrastructure/monitoring/system_metrics_driver.py` | | `HealthCheckInterface` | `domain/ports/infrastructure.py` | `HTTPHealthCheckAdapter`, `HealthService` | `infrastructure/monitoring/health_check_adapter.py`, `infrastructure/monitoring/health_service.py` | | `SubprocessRunner` | `domain/ports/infrastructure.py` | `SubprocessRunner` | `infrastructure/subprocess_runner.py` | | `LogReader` | `domain/ports/infrastructure.py` | `FileLogReader` | `infrastructure/file_log_reader.py` | | `LogParser` | `domain/ports/infrastructure.py` | `LogParser` | `infrastructure/log_parser.py` | | `KPIFormatter` | `domain/ports/infrastructure.py` | `CSVKPIFormatter` | `infrastructure/kpi_formatter.py` | | `ChecksumService` | `domain/ports/infrastructure.py` | `ChecksumService` | _no implementado_ | | `CacheInterface` | `domain/ports/infrastructure.py` | `Redis` client wrapper | `infrastructure/clients.py` | | `PathProviderInterface` | `domain/ports/infrastructure.py` | *(sin adaptador — puerto sin implementación)* | — | | `FileSystemInterface` | `domain/ports/infrastructure.py` | `FilesystemStorage` | `infrastructure/filesystem_storage.py` | | `IOCGenerator` | `domain/ports/integrations.py` | `IOCGenerator` | `domain/services/ioc_generator.py` | | `AlertTransporter` | `domain/ports/integrations.py` | `HTTPAlertSender` | `infrastructure/http_alert_sender.py` |

> Nota: el dominio depende únicamente de los protocolos (`Protocol`). El `CompositionRoot` (`src/soar_lab/interfaces/api/composition.py`) es el único lugar donde se inyectan las implementaciones reales, manteniendo la independencia de capas.

#### 2.2 Paquetes auxiliares en la raíz de `src/soar_lab/`

Además de las cuatro capas hexagonales, el código fuente contiene paquetes de conveniencia y soporte:

| Paquete | Contenido destacado | Responsabilidad | |---|---|---| | `auth/` | `models.py` | Modelos de autenticación/RBAC (`Permission`, `Role`, `User`). `AuthService` vive en `application/use_cases/auth_service.py`. | | `common/` | `exceptions.py` | Excepciones base compartidas por todas las capas. | | `config/` | `settings.py`, `schemas/`, `logging.py` | Configuración central, Pydantic settings y logging. | | `data/` | `generate_iocs.py`, `calc_kpis.py` | Esquemas de datos y helpers de transformación. | | `db/` | `transaction.py` | Inicialización y gestión de transacciones de BD. | | `logging/` | `structured.py` | `StructuredLogger` wrapper sobre `logging`. | | `resilience/` | `circuit_breaker.py`, `retry.py`, `timeout.py` | Patrones de tolerancia a fallos (reintentos, circuit breaker, timeouts). | | `security/` | `sanitization.py` | `PayloadSanitizer` para saneamiento básico de entradas. | | `validation/` | `validators.py` | Validadores centralizados (IP, hash, rutas, alertas). |

---

#### 3. Domain Layer

Ubicación: `src/soar_lab/domain/`

Responsabilidad: Contener la lógica de negocio pura sin dependencias externas.

| Módulo | Propósito | |--------|-----------| | `models.py` | Entidades de dominio (`IOC`, `Alert`, `Case`) con validación | | `ports/repositories.py` | Protocolos de repositorios (`AlertRepository`, `CaseRepository`, etc.) | | `ports/infrastructure.py` | Protocolos de infraestructura (`ConfigProvider`, `HTTPClient`, etc.) | | `ports/integrations.py` | Protocolos de integraciones (`IOCGenerator`, `AlertTransporter`) | | `ports/` | Submódulos organizados por categoría de puerto | | `services/kpi_analyzer.py` | Cálculo de métricas KPI | | `services/ioc_generator.py` | Generación de IOCs simulados | | `statistical_calculator.py` | Cálculos estadísticos puros |

---

#### 4. Application Layer

Ubicación: `src/soar_lab/application/`

Responsabilidad: Orquestar casos de uso utilizando los puertos del dominio.

| Módulo | Propósito | |--------|-----------| | `ports/` | Definición de puertos (interfaces) de entrada/salida | | `use_cases/analytics_service.py` | Cálculo y exportación de estadísticas y KPIs | | `use_cases/auth_service.py` | Autenticación JWT y verificación de credenciales | | `use_cases/backup_service.py` | Creación, listado y restauración de backups | | `use_cases/aggregated_kpis.py` | Agregación de KPIs | | `use_cases/node_timings.py` | Métricas de tiempos por nodo del workflow | | `use_cases/node_timing_extractor.py` | Extracción de tiempos de ejecución por nodo |

---

#### 5. Infrastructure Layer

Ubicación: `src/soar_lab/infrastructure/`

Responsabilidad: Implementar los puertos del dominio y conectar con sistemas externos.

| Módulo | Propósito | |--------|-----------| | `integrations/` | Clientes HTTP de Elasticsearch, Shuffle, TheHive, Cortex, MISP | | `messaging/` | Transporte de alertas (`send_alert.py`) | | `monitoring/` | Health checks, `HealthService`, `SystemMetricsDriver`, `KPIAlertManager` | | `network_watcher/` | Servicio para conectar workers de Shuffle a `soar_net` | | `persistence/` | Implementaciones de repositorios (`SqliteAlertRepository`) | | `security/` | Hardening (no implementado; escaneo vía Trivy en CI) | | `templates/` | Plantillas de configuración | | `jwt_token_provider.py` | `JWTTokenProvider`: generación y validación de tokens JWT | | `pytest_test_runner.py` | `PytestTestRunner`: ejecución remota de pruebas | | `tar_backup_driver.py` | `TarBackupDriver`: copias de seguridad en tar | | `validate_credentials.py` | Validación de credenciales de servicios externos |

---

#### 6. Interface Layer

Ubicación: `src/soar_lab/interfaces/`

Responsabilidad: Exponer la funcionalidad al exterior.

| Módulo | Propósito | |--------|-----------| | `api/composition.py` | `CompositionRoot` y `create_app`: cableado de dependencias de la app FastAPI | | `api/main.py` | Aplicación FastAPI principal con todos los endpoints REST | | `api/cli.py` | CLI nativo `soar-lab` (api, generate-secrets, generate-iocs, version) | | `api/models.py` | Modelos Pydantic para request/response | | `api/auth.py` | Dependencias de autenticación |

---

#### 7. Código compartido

| Módulo | Propósito | |--------|-----------| | `common/` | Excepciones y utilidades compartidas | | `config/` | `settings.py`, `logging.py`, `schemas/` | | `data/` | Esquemas de datos y utilidades | | `validation/` | Validadores reutilizables |

---

#### 8. Scripts y simulador

| Módulo | Propósito | |--------|-----------| | `scripts/` | Scripts del laboratorio: `setup/`, `debug/`, `maintenance/`, generación de KPI/alertas, tests | | `simulator/simulate_alerts.py` | Simulador de alertas SIEM para pruebas (genera y envía payloads al webhook de Shuffle) |

---

#### 9. Referencias

- [Arquitectura hexagonal](#36-arquitectura-hexagonal)
- [Arquitectura general del sistema](#31-visión-general-de-arquitectura)
- [Aplicaciones del proyecto](#32-aplicaciones-y-componentes)
- [Composition Root](#34-composition-root)
- [Guía de infraestructura](04-operations.md)


### 3.4 Composition root

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe el **Composition Root** del proyecto: el punto único donde se instancian y conectan las
dependencias de la aplicación siguiendo el patrón de arquitectura hexagonal.

#### 1.2 Contexto

En arquitectura hexagonal, el dominio define puertos (interfaces) y la infraestructura proporciona adaptadores
(implementaciones). El Composition Root es el único lugar con permiso para conocer ambos lados y cablearlos juntos.
Esto garantiza que el dominio y la aplicación permanezcan independientes de detalles técnicos.

---

#### 2. Ubicación

**Archivo:** `src/soar_lab/interfaces/api/composition.py`

**Clase principal:** `CompositionRoot`

**Factory pública:** `create_app` — crea y configura la aplicación FastAPI con todas las dependencias resueltas.

---

#### 3. Responsabilidades

El `CompositionRoot` realiza las siguientes tareas:

1. **Configuración:** Carga ajustes mediante `create_settings` y `InfrastructureConfigProvider`.
2. **Logging:** Inicializa el sistema de logging con `setup_logging`.
3. **Directorios:** Garantiza que los directorios necesarios existen a través de `PathService`.
4. **Adaptadores de infraestructura:** Crea repositorios, clientes HTTP, almacenamiento, etc.
5. **Servicios de dominio:** Instancia `KPIAnalyzer` y `StatisticalCalculator`.
6. **Servicios de aplicación:** Crea `AnalyticsService`, `AuthService`, `BackupService` y `TestService`.
7. **Clientes utilitarios:** Crea `docker_client` y `redis_client`.
8. **Integración externa:** Inicializa clientes para Shuffle, TheHive, Cortex, MISP, Elasticsearch y .
9. **Aplicación FastAPI:** Construye la API con `create_app` y le inyecta todas las dependencias.

---

#### 4. Componentes cableados

| Componente | Tipo | Rol | |------------|------|-----| | `InfrastructureConfigProvider` | Adaptador de config | Lee variables de entorno y `.env.full` | | `PathService` | Utilidad | Resuelve rutas del proyecto y crea directorios | | `FilesystemStorage` | Adaptador de almacenamiento | Acceso a archivos del sistema | | `SqliteAlertRepository` | Adaptador de persistencia | Almacena alertas en SQLite | | `AioHTTPClient` | Adaptador HTTP | Cliente HTTP asíncrono | | `HTTPHealthCheckAdapter` | Adaptador de health | Realiza health checks HTTP | | `SystemMetricsDriver` | Adaptador de métricas | Recolecta CPU, RAM, disco | | `JWTTokenProvider` | Adaptador de seguridad | Genera y valida tokens JWT | | `TarBackupDriver` | Adaptador de backup | Crea backups comprimidos | | `ConnectionManager` (`websocket_manager.py`) | Adaptador WebSocket | Gestiona conexiones WS para logs | | `Docker Client` | Cliente utilitario | Interacción con Docker | | `Redis Client` | Cliente utilitario | Conexión a Redis | | `KPIAnalyzer` | Servicio de dominio | Calcula métricas KPI | | `StatisticalCalculator` | Servicio de dominio | Cálculos estadísticos | | `AnalyticsService` | Servicio de aplicación | Orquesta analytics y exportación | | `AuthService` | Servicio de aplicación | Autenticación JWT | | `BackupService` | Servicio de aplicación | Crea, lista y restaura backups | | `TestService` | Servicio de aplicación | Ejecuta tests y parsea resultados | | `HealthService` | Servicio de aplicación | Verifica salud de todos los servicios | | `ShuffleClient` | Cliente externo | Integración con Shuffle SOAR | | `TheHiveClient` | Cliente externo | Integración con TheHive | | `CortexClient` | Cliente externo | Integración con Cortex | | `MISPClient` | Cliente externo | Integración con MISP | | `ElasticsearchClient` | Cliente externo | Integración con Elasticsearch |

---

#### 5. Cómo añadir un nuevo adaptador

Para añadir una nueva dependencia sin romper la arquitectura:

1. Define un **puerto** en `src/soar_lab/domain/ports/` (Protocol).
2. Implementa el **adaptador** en `src/soar_lab/infrastructure/`.
3. Registra el adaptador en `CompositionRoot.__init__`.
4. Inyecta el adaptador en el servicio de aplicación o dominio correspondiente.
5. Expón el servicio a `create_app` si debe usarse desde la API.

---

#### 6. Ejemplo de flujo

```python
# Punto de entrada de la aplicación
from soar_lab.interfaces.api.composition import create_app

app = create_app
```

Dentro de `CompositionRoot`:

1. Se crea `settings` y `config_provider`.
2. Se instancian `SqliteAlertRepository`, `SystemMetricsDriver`, `AioHTTPClient`.
3. Se crea `AnalyticsService` con `KPIAnalyzer` y `StatisticalCalculator`.
4. Se crean los clientes utilitarios (`docker_client`, `redis_client`) y los clientes externos (Shuffle, TheHive, Cortex, MISP, Elasticsearch).
5. Se construye `create_app(...)` y se le pasan todas las dependencias.

---

#### 7. Referencias

- [Arquitectura general](#31-visión-general-de-arquitectura)
- [Estructura del código fuente](#33-estructura-de-código)
- [Arquitectura hexagonal](#36-arquitectura-hexagonal)
- [src/soar_lab/interfaces/api/composition.py](../src/soar_lab/interfaces/api/composition.py)


### 3.5 Arquitectura Docker

> Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos
> Compose, configuración de redes, persistencia de datos y procedimientos de despliegue.

#### Índice

- [1. Resumen](#1-resumen)
 - [1.1 Objetivo](#11-objetivo)
 - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
 - [2.1 Qué cubre](#21-qué-cubre)
 - [2.2 Límites](#22-límites)
 - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
 - [3.1 Estrategia de contenerización](#31-estrategia-de-contenerización)
 - [3.2 Servicios y composición](#32-servicios-y-composición)
 - [3.3 Redes y volúmenes](#33-redes-y-volúmenes)
 - [3.4 Comandos y operaciones](#34-comandos-y-operaciones)
 - [3.5 Troubleshooting Docker](#35-troubleshooting-docker)
- [4. Validación](#4-validación)
 - [4.1 Verificación](#41-verificación)
 - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
 - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
 - [5.1 Limitaciones](#51-limitaciones)
 - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
 - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones-troubleshooting)
- [6. Referencias](#6-referencias)

---

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos Compose,
configuración de redes, persistencia de datos y procedimientos de despliegue.

#### 1.2 Contexto

El SOAR Ransomware Lab utiliza Docker Compose para orquestar 18 servicios a través de 4 redes con mejoras en networking,
persistencia de datos y logging. Para la arquitectura completa del sistema, ver [README.md](../README.md).

#### 2. Alcance

#### 2.1 Qué cubre

Este documento cubre:

- Organización de archivos Docker Compose
- Configuración de redes Docker
- Estrategia de persistencia de datos
- Configuración de servicios y healthchecks
- Límites de recursos
- Configuración de logging
- Estrategia de backup
- Consideraciones de seguridad
- Procedimientos de mantenimiento

#### 2.2 Límites

Este documento no cubre:

- Arquitectura de alto nivel del sistema (ver docs/02-architecture.md)
- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver docs/01-getting-started.md)
- Estrategias de pruebas específicas (ver docs/05-testing.md)

#### 2.3 Dependencias

Este documento depende de:

- Documentación oficial de Docker Compose
- Documentación de arquitectura (docs/02-architecture.md)
- Documentación de seguridad (docs/02-architecture.md)
- Guía de usuario (docs/01-getting-started.md)

#### 3. Contenido principal

#### 3.1 Estrategia de contenerización

#### Organización de archivos Compose

La orquestación se divide en varios archivos `docker-compose*.yml` bajo `infra/docker/compose/` para facilitar perfiles y arranque selectivo:

| Archivo | Propósito | Servicios principales | |---|---|---| | `infra/docker/compose/docker-compose.yml` | Redes, volúmenes globales y `elasticsearch` | `elasticsearch` | | `infra/docker/compose/docker-compose.core.yml` | Core SOAR | `redis`, `thehive`, `cortex`, `shuffle-frontend`, `shuffle-backend`, `orborus`, `network-watcher`, `tenzir-node` | | `infra/docker/compose/docker-compose.misp.yml` | Inteligencia de amenazas | `misp-db`, `misp-modules`, `misp` | | `infra/docker/compose/docker-compose.api.yml` | API, portal y proxy | `api`, `docs-site`, `web-management`, `nginx` | | `infra/docker/compose/logging/docker-compose.logging.yml` | Observabilidad | `grafana-db`, `grafana`, `loki`, `promtail` |

> Nota: Todos los comandos se ejecutan desde la raíz del repositorio, salvo indicación expresa.

#### Configuración auxiliar de logging

```
infra/docker/compose/logging/
├── docker-compose.logging.yml
├── promtail-config.yml # descubrimiento de contenedores Docker → Loki
├── loki-config.yml # archivo de referencia; compose usa la config por defecto de la imagen
├── grafana-datasources.yml # datasource Elasticsearch para KPIs
├── grafana-kpi-dashboard.yml # provisioning del dashboard
└── kpi-dashboard.json # definición del dashboard de KPIs
```

#### Iniciar servicios

Desde la raíz, con `make up` (recomendado, incluye logging):

```bash
make up
```

Equivalente manual:

```bash
docker compose --env-file .env -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.opensearch.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml up -d
```

#### Consideraciones de seguridad

- `ti_net` es `internal: true`; `soar_net` y `logging_net` no son internas en esta versión de laboratorio.
- La exposición externa se realiza mediante `ports:` mapeadas; no se usa una red edge dedicada.
- `orborus` y `cortex` montan el socket Docker del host para lanzar analizadores; implica riesgo de escalada de privilegios y está limitado a entornos controlados.
- Los healthchecks se ejecutan dentro del contenedor y deben distinguirse entre *liveness*, *readiness* y salud funcional completa.

#### 3.2 Servicios y composición

#### Tabla canónica de servicios

| Servicio | Imagen / build | Contenedor (por defecto) | Puerto host → contenedor | Redes | Healthcheck | Propósito | |---|---|---|---|---|---|---| | elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | `soar_elasticsearch` | `${ELASTICSEARCH_PORT:-8200}` → 9200 | `soar_net`, `ti_net` | `GET /_cluster/health` | Motor de búsqueda y métricas | | redis | `redis:7-alpine` | `soar_redis` | 6379 → 6379 | `ti_net`, `soar_net` | `nc -z 127.0.0.1 6379` | Cache/cola con autenticación | | thehive | `thehiveproject/thehive:3.5.2-1` | `soar_thehive` | `${THEHIVE_HTTP_PORT:-8100}` → 9000 | `soar_net` | `GET /api/status` | Gestión de casos | | cortex | build `infra/docker/images/cortex/Dockerfile` | `soar_cortex` | `${CORTEX_HTTP_PORT:-8101}` → 9001 | `soar_net` | HTTP 2xx/3xx en `:9001/` | Motor de analizadores; monta `/var/run/docker.sock` | | shuffle-frontend | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | `soar_shuffle_frontend` | `${SHUFFLE_UI_PORT:-8081}` → 80 | `soar_net`, `ti_net` | `GET http://localhost:80` | UI de workflows | | shuffle-backend | `ghcr.io/shuffle/shuffle-backend:2.2.1` | `soar_shuffle_backend` | `${SHUFFLE_API_PORT:-5001}` → 5001 | `soar_net`, `ti_net` | deshabilitado | Motor de workflows | | orborus | build `infra/docker/images/orborus/Dockerfile` (tag `ghcr.io/shuffle/shuffle-orborus:2.2.1-patched`) | `soar_orborus` | — | `soar_net` | `nc -z shuffle-backend 5001` | Ejecutor de contenedores de analizadores | | network-watcher | build `src/soar_lab/infrastructure/network_watcher` | `soar_network_watcher` | `${NETWORK_WATCHER_PORT:-15130}` → 8080 | `soar_net` | `GET /health` en `:8080` | Diagnóstico/recuperación de red (sincroniza `/etc/hosts` de workers) | | tenzir-node | `tenzir/tenzir:v6.8.1` | `soar_tenzir_node` | 15160 → 5160, 15140 → 1514 | `soar_net` | `tenzir 'api "/ping"'` | Nodo Tenzir (modo dev) | | misp-db | `mariadb:10.11` | `soar_misp_db` | — | `soar_net` | `mysqladmin ping` | BD MISP (volumen Docker, no bind) | | misp-modules | `ghcr.io/misp/misp-docker/misp-modules:v3.0.9` | `soar_misp_modules` | — | `soar_net` | socket `localhost:6666` | Módulos MISP | | misp | `ghcr.io/misp/misp-docker/misp-core:v2.5.44` | `soar_misp` | `${MISP_PORT:-8083}` → 80 | `soar_net` | `GET /users/heartbeat` | Plataforma de inteligencia de amenazas | | api | build `apps/api/Dockerfile` (contexto raíz) | `soar_api` | `${API_PORT:-8000}` → 8000 | `soar_net`, `ti_net`, `logging_net` | `GET /health` | API FastAPI | | docs-site | build `apps/docs-site/Dockerfile` (contexto raíz) | `soar_docs_site` | `${DOCS_PORT:-8086}` → 8080 | `soar_net` | deshabilitado | Portal Docusaurus | | web-management | build `apps/web-management/Dockerfile` | `soar_web_management` | 8085 → 80 | `soar_net` | `pgrep nginx` | SPA web de operación | | nginx | `nginx:1.25-alpine` | `soar_nginx` | 80 → 80, 443 → 443 | `soar_net`, `logging_net` | `GET /nginx-health` | Proxy inverso y TLS | | grafana-db | `postgres:14-alpine` | `soar_grafana_db` | — | `logging_net` | `pg_isready -U grafana` | BD Grafana | | grafana | `grafana/grafana:10.3.4` | `soar_grafana` | `${GRAFANA_PORT:-8084}` → 3000 | `logging_net`, `soar_net` | `GET /api/health` | Visualización KPIs/logs | | loki | `grafana/loki:2.9.10` | `soar_loki` | — | `logging_net` | — (imagen sin shell) | Agregación de logs | | promtail | `grafana/promtail:2.9.9` | `soar_promtail` | — | `logging_net`, `soar_net` | — | Envío de logs Docker a Loki |

**Notas de nomenclatura**:
- Los nombres de contenedor usan el prefijo `${COMPOSE_PROJECT_NAME:-soar}_` y `_` como separador (ej. `soar_api`).
- Los nombres de servicio con guión (`shuffle-frontend`, `.manager`) son los nombres internos de Docker Compose.
- `soar_api` es el nombre del **contenedor**; el **servicio** Compose es `api` y el **hostname** interno es `api`.

#### Healthchecks y dependencias

- `shuffle-backend` no tiene healthcheck configurado; `orborus` lo monitoriza mediante `nc -z shuffle-backend 5001`.
- `loki` usa la imagen mínima de Grafana Loki (`2.9.10`), sin shell ni curl, por lo que no dispone de healthcheck.
- `thehive` usa `/api/status` para evitar falsos negativos mientras Elasticsearch prepara sus índices.

#### Límites de recursos

Valores extraídos de los archivos Compose; pueden ajustarse en `.env.full` o directamente en `deploy.resources`:

| Grupo | Servicios | CPU límite / reserva | Memoria límite / reserva | |---|---|---|---| | Grandes | `elasticsearch`, `thehive`, `cortex`, `shuffle-backend`, `misp` | 2.0 / 1.0 cores | 4GB / 2GB | | Medianos | `redis`, `shuffle-frontend`, `orborus`, `.manager`, `.indexer`, `grafana`, `api` | 1.0 / 0.5 cores | 1-2GB / 0.5-1GB | | Pequeños | `docs-site`, `web-management`, `promtail` | 0.5 / 0.25 cores | 256-512MB / 128-256MB |

#### 3.3 Redes y volúmenes

#### Topología de red

| Red | CIDR | Tipo | Servicios | Propósito | |---|---|---|---|---| | `bridge` | — | `external: true` | Ninguno directamente | Red por defecto de Docker; declarada por compatibilidad | | `soar_net` | `10.100.0.0/16` | bridge | `elasticsearch`, `redis`, `thehive`, `cortex`, `shuffle-*`, `orborus`, `network-watcher`, `tenzir-node`, `misp*`, `.*`, `api`, `web-management`, `nginx`, `grafana`, `promtail` | Red principal del laboratorio | | `ti_net` | `172.22.0.0/16` | `internal: true` | `elasticsearch`, `redis`, `api` | Aislada del exterior; tráfico de inteligencia de amenazas | | `logging_net` | `172.23.0.0/16` | bridge | `grafana-db`, `grafana`, `loki`, `promtail`, `nginx` | Tráfico de observabilidad |

> **Importante:** El acceso externo se controla mediante mapeos de puertos del host; no se usa una red edge dedicada.

#### DNS y aliases

- Docker Compose crea un servidor DNS interno (`127.0.0.11`) en cada red.
- Los nombres de servicio (`api`, `thehive`, `elasticsearch`) resuelven a la IP del contenedor dentro de la red.
- `orborus` lanza contenedores de analizadores en la red `soar_net` (o `${COMPOSE_PROJECT_NAME}_net` según `SHUFFLE_APP_NETWORK`); requiere que exista la red y que el socket Docker tenga permisos adecuados.
- `network-watcher` puede modificar `/etc/hosts` o DNS de contenedores dependientes para resolver problemas de conectividad (ver `docs/04-operations.md`).

#### Seguridad de red

- `ti_net` es la única red marcada como `internal: true`; no tiene salida a Internet.
- Los servicios expuestos al host (`ports:`) no están necesariamente en una red externa; el aislamiento depende del firewall del host.
- `api` pertenece a `soar_net`, `ti_net` y `logging_net` para orquestar integraciones y consumir métricas/logs.
- `nginx` conecta a `soar_net` y `logging_net`; termina TLS y enruta a `api` y `web-management`.

#### Estrategia de volúmenes

Los volúmenes se declaran en `infra/docker/compose/docker-compose.yml`. La mayoría son bind mounts que apuntan a `runtime/`:

```
runtime/
├── data/
│ ├── elasticsearch/ # es_data
│ ├── thehive/files/ # thehive_files
│ ├── cortex/ # cortex_data
│ ├── shuffle/apps/ # shuffle_apps
│ ├── shuffle/files/ # shuffle_files
│ ├── redis/ # redis_data
│ ├── misp/files/ # misp_files
│ ├── misp/configs/ # misp_configs
│ ├── /... # múltiples bind mounts
│ ├── loki/ # loki_data
│ └── grafana/ # grafana_data
├── logs/
│ ├── nginx/ # nginx_logs
│ └── misp/ # misp_logs
└── backups/ # montado en /app/backups (api)
```

**Casos especiales:**

- `misp_db` es un **volumen Docker normal** (no bind mount). En Windows/Docker Desktop, bind mounts de MariaDB generan errores de permisos (`rename`). Usar `docker compose down -v` elimina el volumen lógico, no un directorio local.
- El logging stack usa volúmenes Docker normales para `grafana_db_data`, `grafana_data` y `loki_data`.

#### Logging

Cada servicio utiliza el driver `json-file` con rotación:

- `max-size`: 10 MB
- `max-file`: 3 archivos
- Total aproximado: ~30 MB por servicio en disco de Docker.

Ubicaciones adicionales:

- Host: `runtime/logs/nginx/` y `runtime/logs/misp/` (bind mounts explícitos).
- Streaming en vivo: `api` expone `/ws/logs` (WebSocket) y `/api/ws/logs` vía Nginx.
- Logging centralizado:
 - `promtail` descubre contenedores por el socket Docker y envía a `loki`.
 - `grafana` consulta `loki` y `elasticsearch` (`soar-metrics`) para logs y KPIs.

#### Estrategia de backup

- El servicio de backup reside en `src/soar_lab/application/use_cases/backup_service.py` y se expone en `/backup/create` y `/backup/restore`.
- Los artefactos se escriben en `runtime/backups/` (montado en `/app/backups` del contenedor `api`).
- Para backup completo del laboratorio se recomienda detener el stack y copiar `runtime/` (incluidos `data/` y `logs/`), además de exportar volúmenes Docker normales (`misp_db`, `-indexer-data`, etc.).


#### 3.4 Comandos y operaciones

#### Comandos de Gestión

```bash
# Iniciar todos los servicios
make up

# Detener todos los servicios
make down

# Reiniciar el stack completo
make down && make up

# Ver estado de todos los servicios
docker ps --format "table {{.Names}}\t{{.Status}}"

# Ver logs de un servicio específico
docker logs soar_thehive --tail 50

# Acceder a un contenedor
docker exec -it soar_thehive bash
```

#### Mantenimiento

**Actualizaciones:**

- Actualizar imágenes Docker regularmente
- Revisar y actualizar archivos `infra/docker/compose/docker-compose*.yml`
- Aplicar parches de seguridad a contenedores

**Monitoreo:**

- Verificar health checks de servicios
- Monitorear uso de recursos con `docker stats`
- Revisar logs regularmente

#### 3.5 Troubleshooting Docker

#### El servicio no inicia

```bash
# Revisar logs
docker logs <service_name>

# Verificar estado de salud
docker compose ps

# Reiniciar servicio específico
docker compose restart <service_name>
```

#### Problemas de conectividad de red

```bash
# Verificar conectividad de red
docker network inspect soar_net

# Probar conexión entre contenedores
docker exec <container1> ping <container2>
```

#### Problemas de persistencia de datos

```bash
# Verificar montajes de volúmenes
docker inspect <container_name> | grep -A 10 Mounts

# Verificar que existe el directorio de datos
ls -la runtime/data/
```

#### Conflictos de puertos

```bash
# Verificar uso de puertos
netstat -tuln | grep <port>

# Cambiar puerto en .env.full
```

#### Alto uso de memoria

```bash
# Verificar uso de recursos
docker stats

# Ajustar límites de recursos en infra/docker/compose/docker-compose*.yml
```

#### Elasticsearch lento

```bash
# Verificar salud de Elasticsearch
curl http://localhost:8200/_cluster/health

# Aumentar límite de memoria en infra/docker/compose/docker-compose*.yml
```

#### Problema de Índice de Elasticsearch en TheHive

**Problema:** TheHive requiere el índice de Elasticsearch `the_hive_17` que puede no existir en una instalación fresca.

**Solución Actual:** El healthcheck se cambió para usar `/api/status` en lugar de `/api/health` para evitar la
dependencia del índice. El índice se creará automáticamente por TheHive al iniciar.

#### 4. Validación

##### 4.1 Verificación

La configuración Docker se verifica mediante:

- Ejecución de `docker compose config` para validar sintaxis
- Verificación de que todas las redes se crean correctamente (`docker network ls`)
- Verificación de que todos los volúmenes se montan correctamente (`docker volume ls`)
- Ejecución de health checks para cada servicio
- Pruebas de conectividad entre servicios en redes específicas

#### 4.2 Criterios de aceptación

La configuración Docker se considera válida cuando:

- Todos los servicios inician sin errores
- Los health checks pasan para todos los servicios
- Las redes están correctamente configuradas y aisladas
- Los volúmenes se montan correctamente
- Los servicios pueden comunicarse entre sí según la topología de red
- Los logs se generan correctamente

#### 4.3 Evidencias

Las evidencias de validación incluyen:

- Salida de `docker compose config` sin errores
- Salida de `docker compose ps` mostrando servicios en ejecución
- Salida de `docker network ls` mostrando las 4 redes
- Salida de `docker volume ls` mostrando volúmenes montados
- Logs de Docker Compose sin errores críticos
- Resultados de health checks (`docker inspect`)

#### 5. Problemas y consideraciones

##### 5.1 Limitaciones

- **Bind mounts en Windows**: El rendimiento de bind mounts puede ser menor en Windows Docker Desktop
- **Single-node Elasticsearch**: Configuración actual no soporta clustering
- **Recursos limitados**: Mínimo 8GB RAM requerido para stack completo

#### 5.2 Riesgos o incidencias

- **Servicios no inician**: Puede ser debido a puertos ya en uso o conflictos de configuración
- **Problemas de conectividad de red**: Configuración incorrecta de redes internas
- **Problemas de persistencia de datos**: Montajes de volúmenes fallidos
- **Conflictos de puertos**: Puertos ya en uso por otros servicios
- **Problemas de rendimiento**: Recursos insuficientes o configuración subóptima

#### 5.3 Recomendaciones / troubleshooting

**Recomendaciones Generales:**

- Para troubleshooting específico de Docker, ver sección 3.5
- Mantener las imágenes Docker actualizadas regularmente
- Monitorear el uso de recursos con `docker stats`
- Revisar logs regularmente para detectar problemas temprano
- Implementar una estrategia de backup regular

#### 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Docker Networking**: https://docs.docker.com/network/
- **Documentación de Docker Volumes**: https://docs.docker.com/storage/volumes/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Arquitectura**: [docs/02-architecture.md](#31-visión-general-de-arquitectura)
- **Documentación de Seguridad**: [docs/02-architecture.md](#39-seguridad)
- **Guía de Usuario**: [docs/01-getting-started.md](01-getting-started.md)


### 3.6 Arquitectura hexagonal

El paquete `soar_lab` sigue una arquitectura hexagonal: el dominio define puertos, la aplicación orquesta casos de uso,
y la infraestructura e interfaces implementan los adaptadores.

#### Capas principales

| Capa | Ubicación | Responsabilidad | |------|-----------|----------------| | **Dominio** | `src/soar_lab/domain/` | Entidades, value objects, reglas puras y contratos de puertos (`ports/`) | | **Aplicación** | `src/soar_lab/application/` | Casos de uso, coordinación de adaptadores y DTOs | | **Infraestructura** | `src/soar_lab/infrastructure/` | Implementaciones de puertos: clientes externos, persistencia, mensajería, monitoreo | | **Interfaces** | `src/soar_lab/interfaces/` | Puntos de entrada: API REST FastAPI y CLI | | **Scripts** | `scripts/` | Setup, mantenimiento y depuración (no son runtime) | | **Soporte / utilidades** | `src/soar_lab/{auth,common,config,data,db,logging,resilience,security,validation,simulator}` | Paquetes de soporte: autenticación/RBAC, excepciones compartidas, configuración, datos, BD, logging estructurado, resiliencia, validaciones, sanitización y simulador. La lógica de negocio pura permanece en `domain/`. |

> **Nota:** El entrypoint `soar-lab` y la imagen Docker usan `src/soar_lab/interfaces/api/` directamente (no hay paquete `src/soar_lab/api/` separado). `composition.py` expone `create_app` y `CompositionRoot`; `main.py` expone la app FastAPI; `cli.py` expone el CLI.

#### Diagrama de arquitectura hexagonal

```mermaid
flowchart TD
 subgraph Entrada["Adaptadores de entrada"]
 F[FastAPI routes<br/>src/soar_lab/interfaces/api/main.py]
 C[CLI soar-lab<br/>src/soar_lab/interfaces/api/cli.py]
 W[Web Management SPA<br/>apps/web-management/]
 end

 subgraph Aplicación["Capa de aplicación"]
 AS[AuthService]
 BS[BackupService]
 ANS[AnalyticsService]
 end

 subgraph Dominio["Capa de dominio"]
 PORTS[Puertos: AlertRepository<br/>BackupDriver, TokenProvider<br/>SystemMetricsInterface...]
 ALERT[Alert / IOC]
 KPI[KPIAnalyzer]
 IOC[SimulatedIOCGenerator]
 end

 subgraph Salida["Adaptadores de salida"]
 SQLITE[SqliteAlertRepository]
 TAR[TarBackupDriver]
 JWT[JWTTokenProvider]
 HTTP[HTTPClient → Shuffle/TheHive/Cortex/MISP//ES]
 end

 F -->|/auth/login| AS
 F -->|/backup/create| BS
 F -->|/analytics/kpis| ANS
 C --> AS
 W --> F
 AS -->|TokenProviderInterface| JWT
 BS -->|BackupDriver| TAR
 ANS -->|AlertRepository| SQLITE
 ANS -->|SystemMetricsInterface| HTTP
 KPI -->|StatisticalCalculatorInterface| STAT[StatisticalCalculator]
```

#### Dominio

Entidades y value objects (`src/soar_lab/domain/models.py`):

- `Alert`: entidad principal de alerta de seguridad (`alert_id`, `hostname`, `src_ip`, `severity`, `iocs`, ...).
- `Case`: entidad de caso de incidente (`case_id`, `title`, `severity`, `tags`, `tlp`, `alerts`, ...).
- `IOC`: indicador de compromiso con tipo, valor, confianza y tags.
- `AlertSeverity` / `AlertStatus`: enumeraciones de severidad y estado.

Servicios de dominio puros (`src/soar_lab/domain/services/`):

- `KPIAnalyzer`: cálculo de MTTR, percentiles, health score y KPIs agregados.
- `SimulatedIOCGenerator`: generación de IOCs sintéticos (hash, IP, dominio, URL).
- `StatisticalCalculator`: operaciones estadísticas usadas por `KPIAnalyzer`.

Puertos (`src/soar_lab/domain/ports/`): `AlertRepository`, `IocRepository`, `MetricRepository`, `CaseRepository`, `BackupRepository`, `TestResultRepository`, `ChecksumService`, `StorageProvider`, `BackupDriver`, `TokenProviderInterface`, `SystemMetricsInterface`, `FileSystemInterface`, `LogReader`, `LogParser`, `KPIFormatter`, `StatisticalCalculatorInterface`.

#### Aplicación

Casos de uso (`src/soar_lab/application/use_cases/`):

- `AuthService`: autenticación, verificación de credenciales (`WEB_UI_USER`/`WEB_UI_PASSWORD`) y creación/validación de JWT a través de `TokenProviderInterface`.
- `BackupService`: creación, listado y restauración de backups `.tar.gz` usando `BackupDriver` y `BackupStorageProvider`.
- `AnalyticsService`: recopilación de métricas del sistema, KPIs y estadísticas, orquestando `KPIAnalyzer`, repositorios y lectores de logs.
- `AggregatedKpisUseCase`: obtención de KPIs agregados desde Elasticsearch.
- `NodeTimingsUseCase`: obtención de timings por nodo de ejecuciones de workflow desde Elasticsearch/OpenSearch.
- `NodeTimingExtractor`: extracción de métricas de timing por nodo desde Shuffle (OpenSearch) para dashboards y análisis.

#### Puerto → adaptador → implementación


#### Ejemplo real de flujo: recepción y contención de una alerta

> **Nota**: el ingreso de alertas no pasa por la Lab API. El `main.py` de FastAPI expone métricas, estado y orquestación de casos; la ingestión real ocurre a través del webhook de Shuffle generado por `init_shuffle_webhook.py`.

```text
[src/soar_lab/simulator/simulate_alerts.py] genera alerta (dict JSON)
 │
 ▼
[infrastructure/messaging/send_alert.py] POST al webhook de Shuffle
 │
 ▼
[Shuffle workflow] recibe la alerta y ejecuta el workflow de respuesta
 │
 ▼
[infrastructure/integrations/thehive/client.py] crea caso en TheHive
 │
 ▼
[infrastructure/integrations/cortex/client.py] ejecuta analyzers
 │
 ▼
[infrastructure/integrations/misp/client.py] enriquece IoCs
 │
 ▼
[Shuffle workflow] ejecuta lógica de decisión y contención simulada
 │
 ▼
[infrastructure/integrations/thehive/client.py] actualiza caso con resultado
 │
 ▼
[domain/services/kpi_analyzer.py] calcula MTTR
 │
 ▼
[Shuffle workflow] indexa métricas KPI en Elasticsearch (`soar-metrics`)
```

#### Convenciones de importación

```python
# Lógica pura de dominio
from soar_lab.domain.services.ioc_generator import SimulatedIOCGenerator
from soar_lab.domain.services.kpi_analyzer import KPIAnalyzer

# Puertos e interfaces del dominio
from soar_lab.domain.ports import BackupDriver, AlertRepository

# Adaptadores de infraestructura
from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient
from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender
from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider
from soar_lab.infrastructure.persistence.sqlite_alert_repository import SqliteAlertRepository

# Casos de uso
from soar_lab.application.use_cases.backup_service import BackupService

# Interfaces (API/CLI)
from soar_lab.interfaces.api.composition import create_app
```

#### Notas de migración

- `api/` quedó en `src/soar_lab/interfaces/api/`.
- `integrations/` se reubicó en `src/soar_lab/infrastructure/integrations/`.
- `services/` se dividió en `application/use_cases/` (orquestación) y `domain/services/` (lógica pura).
- `infrastructure/setup/` se movió a `scripts/setup/`; la carpeta `infrastructure/scripts/` se
 considera legacy y no forma parte del runtime.
- `exceptions.py` centralizado en `src/soar_lab/common/exceptions.py`.


### 3.7 Inventario de dominio y aplicaciones

Este documento inventaria las clases y responsabilidades de las capas internas del proyecto, sirviendo de mapa rápido para
mantenedores y revisores.

#### Domain Layer (`src/soar_lab/domain/`)

Responsabilidad: modelos de negocio, reglas puras, contratos de puertos y servicios del dominio.

| Archivo / Módulo | Responsabilidad principal | |------------------|---------------------------| | `models.py` | Entidades de dominio (`Alert`, `IOC`, `Case`, `AlertSeverity`, `AlertStatus`) | | `alert_generator.py` | Generación de alertas de prueba para simulación | | `statistical_calculator.py` | Utilidades estadísticas para comparaciones y tests | | `ports/` | Contratos de puertos (driven/driving) para persistencia, mensajería, backups y KPIs, organizados por categoría (`infrastructure.py`, `integrations.py`, `repositories.py`) | | `services/ioc_generator.py` | Generación de IoCs de ejemplo para tests y simulación | | `services/kpi_analyzer.py` | Cálculo de MTTR, percentiles y métricas de respuesta | | `services/_ioc_helpers.py` | Funciones auxiliares para generación de IoCs |

#### Application Layer (`src/soar_lab/application/`)

Responsabilidad: casos de uso, orquestación de dominio, coordinación de adaptadores.

| Archivo / Módulo | Responsabilidad principal | |------------------|---------------------------| | `use_cases/analytics_service.py` | Casos de uso de analytics y generación de KPIs | | `use_cases/auth_service.py` | Casos de uso de autenticación (login, validación JWT) | | `use_cases/backup_service.py` | Casos de uso de backup/restore | | `dto/` | Objetos de transferencia de datos (DTOs) entre capas |

#### Interface/API Layer (`src/soar_lab/interfaces/api/`)

Responsabilidad: exponer la aplicación como CLI y API REST.

| Archivo | Responsabilidad principal | |---------|---------------------------| | `main.py` | Aplicación FastAPI: endpoints REST, routers, health y wiring general | | `composition.py` | `CompositionRoot` / `create_app`: creación y cableado de dependencias | | `cli.py` | CLI nativo `soar-lab` (api, generate-secrets, generate-iocs, version) | | `auth.py` | Dependencias de autenticación y autorización FastAPI | | `route_helpers.py` | Constantes compartidas y factorías de dependencias para los módulos de rutas | | `routes_soar.py` | Endpoints `/soar/*` (TheHive, Cortex, MISP, Shuffle, Elasticsearch) | | `routes_services.py` | Endpoints `/services/status`, `/api/v1/contain`, `/api/v1/cache/ioc` | | `routes_analytics.py` | Endpoints de analíticas y KPIs | | `models.py` | Modelos Pydantic para request/response | | `contracts.py` | Validación de contratos OpenAPI y sincronización de schemas | | `validation.py` | Validadores de request/response reutilizables | | `middleware/trace_id.py` | Middleware de trace ID para correlación de logs | | `static/` | Recursos estáticos servidos por la API | | `__init__.py` | Package init con exports y metadata del módulo API |

#### Infrastructure Layer (`src/soar_lab/infrastructure/`)

Responsabilidad: implementar los puertos del dominio y conectar con sistemas externos.

| Archivo / Módulo | Responsabilidad principal | |------------------|---------------------------| | `integrations/` | Clientes HTTP de Elasticsearch, Shuffle, TheHive, Cortex, MISP | | `messaging/` | Transporte de alertas (`send_alert.py`) | | `monitoring/` | Health checks, `HealthService`, `SystemMetricsDriver`, `KPIAlertManager` | | `network_watcher/` | Servicio para conectar workers de Shuffle a `soar_net` | | `persistence/` | Implementaciones de repositorios (`SqliteAlertRepository`) | | `scripts/` | Scripts auxiliares de infraestructura (setup, utilidades) | | `security/` | Hardening (no implementado; escaneo vía Trivy en CI) | | `templates/` | Plantillas de configuración | | `jwt_token_provider.py` | `JWTTokenProvider`: generación y validación de tokens JWT | | `pytest_test_runner.py` | `PytestTestRunner`: ejecución remota de pruebas | | `tar_backup_driver.py` | `TarBackupDriver`: copias de seguridad en tar | | `validate_credentials.py` | Validación de credenciales de servicios externos | | `websocket_manager.py` | Gestión de WebSockets para logs y eventos en tiempo real | | `config_provider.py` | Proveedor centralizado de configuración basado en variables de entorno | | `filesystem_storage.py` | Almacenamiento basado en filesystem | | `in_memory_storage.py` | Almacenamiento en memoria para tests | | `log_parser.py` | Parsing de logs de ejecución | | `kpi_formatter.py` | Formateo de resultados de KPI | | `file_log_reader.py` | Lectura de archivos de log para análisis | | `subprocess_runner.py` | Ejecución de subprocesos con manejo de salida | | `path_service.py` | Utilidades de resolución de rutas | | `http_client.py` | Cliente HTTP reutilizable | | `clients.py` | Fábricas de clientes externos | | `pytest_output_parser.py` | Parser de salida de pytest | | `http_alert_sender.py` | Envío de alertas por HTTP | | `in_memory_alert_repository.py` | Repositorio en memoria de alertas (para tests) | | `auth_defaults.py` | Valores por defecto de autenticación | | `cleanup_service.py` | Servicio de limpieza de recursos |

#### Notas de coherencia

- `src/soar_lab/interfaces/api/models.py` contiene los modelos Pydantic de la API REST; los modelos de negocio viven en
 `src/soar_lab/domain/models.py`.
- Los servicios `analytics_service.py` y `auth_service.py` en `application/use_cases/` actúan como fachadas que
 orquestan adaptadores de infraestructura; las implementaciones finales están en `infrastructure/`.
- `infrastructure/security/` contiene únicamente scripts de hardening; no contiene lógica de aplicación Python.
- `infrastructure/scripts/` está marcado como **legacy**; para scripts canónicos ver `scripts/`.


### 3.8 Coexistencia de motores de búsqueda

#### Resumen de la decisión

El laboratorio despliega **dos motores de búsqueda simultáneamente**: Elasticsearch 7.10.2 y OpenSearch 2.10.0. Esta no es una redundancia accidental, sino una decisión técnica forzada por las incompatibilidades de las dependencias de cada servicio.

| Servicio | Motor de búsqueda | Motivo | |---|---|---| | TheHive 3.5.2 | Elasticsearch 7.10.2 | `elastic4play` no envía credenciales REST de forma fiable con `xpack.security.enabled=true` y presenta problemas de mapeo (`include_type_name`) con ES 8.x/OpenSearch 2.x. | | Cortex 3.2.0 | Elasticsearch 7.10.2 | Misma librería subyacente que TheHive (`elastic4play` / `elastic4s`). Requiere API 7.x. | | Lab API / KPI / Grafana | Elasticsearch 7.10.2 | Los datasources de Grafana y los índices de KPI (`soar-metrics`, `soar-alerts`) se crean sobre Elasticsearch. | | Shuffle 2.2.1 | OpenSearch 2.10.0 | El backend y `orborus` de Shuffle usan el cliente de OpenSearch y no funcionan correctamente con Elasticsearch 8.x. |

#### Por qué no se consolidó en un único motor

- **Shuffle** migró a OpenSearch porque el cliente/ backend no era compatible con Elasticsearch 8.x y la gestión de `include_type_name` era problemática.
- **TheHive/Cortex** permanecen en Elasticsearch 7.10.2 porque `elastic4play` está atado a la API 7.x. Subir a Elasticsearch 8.x o a OpenSearch 2.x genera errores de mapeo y autenticación REST.

#### Configuración actual

#### Elasticsearch (`soar_elasticsearch`)

- Imagen: `docker.elastic.co/elasticsearch/elasticsearch:7.10.2`
- Red: `soar_net`
- Seguridad: `xpack.security.enabled=false` (necesario para evitar errores de *missing authentication credentials* en TheHive/Cortex).
- Credenciales en `.env.full`:
 - `ELASTIC_USERNAME=elastic`
 - `ELASTIC_PASSWORD=ElasticLab2024SecurePass`
- Configuración de aplicaciones (templates renderizados a `runtime/config/` por `scripts/setup/render_configs.py`):
 - `infra/docker/config/templates/thehive.conf.template` → montado en `/etc/thehive/application.conf`
 - `infra/docker/config/templates/cortex.conf.template` → montado en `/etc/cortex/application.conf`
- Scripts que interactúan con ES:
 - `scripts/setup/configure_es.py`
 - `scripts/setup/reset_cortex.py`
 - `scripts/setup/init_thehive.py`
 - `scripts/setup/init_shuffle_webhook.py`

#### OpenSearch (`soar_opensearch`)

- Imagen: `opensearchproject/opensearch:2.10.0`
- Red: `soar_net`
- Seguridad: `plugins.security.disabled=true`
- Credenciales en `.env.full`:
 - `OPENSEARCH_USERNAME=admin`
 - `OPENSEARCH_PASSWORD=<generado por make generate-secrets>`
- Servicios consumidores:
 - `shuffle-backend` (`SHUFFLE_OPENSEARCH_URL=http://opensearch:9200`)
 - `orborus` (`SHUFFLE_OPENSEARCH_URL=http://opensearch:9200`)

#### Dependencias en Docker Compose

- `thehive` y `cortex` dependen de `elasticsearch`.
- `shuffle-backend` y `orborus` dependen de `opensearch`.
- `api` se comunica con `elasticsearch` para health-checks y métricas.

#### Riesgos y consideraciones

- **Doble consumo de recursos**: cada nodo aloca ~2 GB de heap (`ES_JAVA_OPTS` / `OPENSEARCH_JAVA_OPTS`). En entornos con poca RAM puede ser necesario escalar verticalmente.
- **Backups coherentes**: hay que respaldar dos conjuntos de datos (`soar_es_data` y `soar_opensearch_data`).
- **Hoja de ruta futura**: cuando TheHive/Cortex o sus forks soporten OpenSearch 2.x de forma nativa, Elasticsearch podrá eliminarse y Shuffle/OpenSearch/ podrían compartir un único clúster.

#### Cómo verificar el estado de ambos motores

```powershell
# Elasticsearch
curl -sf http://localhost:8200/_cluster/health

# OpenSearch
curl -sf http://localhost:8200/_cluster/health # OpenSearch escucha en 9200 interno, mapeado a 8200 en host según .env.full
```

Para ver qué servicios usan cada motor, consultar:

- `infra/docker/compose/docker-compose.yml` (Elasticsearch)
- `infra/docker/compose/docker-compose.opensearch.yml` (OpenSearch)
- `infra/docker/compose/docker-compose.core.yml` (TheHive, Cortex, Shuffle)


### 3.9 Seguridad

#### 1. Resumen

#### 1.1 Objetivo

Este documento describe la estrategia de seguridad defensa en profundidad implementada para proteger contra ataques de
ransomware y garantizar la integridad de las operaciones de seguridad del SOAR Ransomware Lab.

#### 1.2 Contexto

El SOAR Ransomware Lab implementa una estrategia de seguridad defensa en profundidad para proteger contra ataques de
ransomware y garantizar la integridad de las operaciones de seguridad. Este documento describe los controles de
seguridad, políticas y procedimientos implementados en la plataforma.

**Principios de Seguridad:**

- **Arquitectura Zero Trust**: Nunca confiar, siempre verificar
- **Principio de Mínimo Privilegio**: Acceso mínimo requerido
- **Defensa en Profundidad**: Múltiples capas de seguridad
- **Seguridad por Diseño**: Seguridad integrada en cada componente
- **Monitoreo Continuo**: Detección de amenazas en tiempo real

#### 2. Alcance

#### 2.1 Qué cubre

Este documento cubre:

- Modelo de amenazas y vectores de ataque
- Arquitectura de seguridad y zonas de seguridad
- Autenticación y autorización (MFA, SSO, RBAC)
- Protección de datos (clasificación, encriptación, gestión del ciclo de vida)
- Seguridad de red (firewalls, IDS/IPS, segmentación)
- Seguridad de aplicación (SDLC, validación de entrada)
- Seguridad de infraestructura (contenedores, cloud)
- Cumplimiento regulatorio (GDPR, SOC 2, ISO 27001)
- Operaciones de seguridad (monitoreo, mantenimiento)
- Respuesta a incidentes (procedimientos, protocolos)
- Pruebas de seguridad (evaluaciones, pentesting)

#### 2.2 Límites

Este documento no cubre:

- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver user_guide.md)
- Estrategias de pruebas específicas (ver testing/)
- Planificación del proyecto (ver docs/06-project-management.md)
- Contratos de API detallados (ver docs/03-api-and-integrations.md)

#### 2.3 Dependencias

Este documento depende de:

- Documentación oficial de cada componente (Shuffle, TheHive, Cortex, MISP)
- Documentación de arquitectura (docs/02-architecture.md)
- Guía de usuario (docs/01-getting-started.md)
- Estrategia de Docker (docs/02-architecture.md)
- Documentación de pruebas (docs/05-testing.md)
- Contratos de API (docs/03-api-and-integrations.md)

#### 3. Contenido principal

#### 3.1 Principios de seguridad

Los principios de seguridad fundamentales que guían el diseño y operación del SOAR Ransomware Lab son:

- **Arquitectura Zero Trust**: Nunca confiar, siempre verificar
- **Principio de Mínimo Privilegio**: Acceso mínimo requerido
- **Defensa en Profundidad**: Múltiples capas de seguridad
- **Seguridad por Diseño**: Seguridad integrada en cada componente
- **Monitoreo Continuo**: Detección de amenazas en tiempo real

#### 3.2 Modelo de amenazas

#### Amenazas Principales

**Amenazas Principales:**

1. **Ataques de Ransomware**
 - Encriptación de archivos
 - Exfiltración de datos
 - Disrupción del sistema
 - Impacto de negocio

2. **Amenazas Internas**
 - Insiders maliciosos
 - Exposición accidental de datos
 - Escalada de privilegios
 - Robo de datos

3. **Ataques Externos**
 - Intrusión de red
 - Abuso de API
 - Denegación de servicio
 - Ataques a la cadena de suministro

4. **Violaciones de Datos**
 - Acceso no autorizado
 - Fuga de datos
 - Violaciones de privacidad
 - Incumplimiento regulatorio

#### Arquitectura de Seguridad

**Zonas de Seguridad:**

```
┌─────────────────────────────────────────────────────────────┐
│ Zona DMZ │
│ Load Balancer │ Web Firewall │ SSL Termination │
├─────────────────────────────────────────────────────────────┤
│ Zona de Aplicación │
│ API Gateway │ WAF │ Rate Limiting │
├─────────────────────────────────────────────────────────────┤
│ Zona de Datos │
│ Database │ File Storage │ Encryption │
├─────────────────────────────────────────────────────────────┤
│ Zona de Gestión │
│ Monitoring │ Logging │ Backup Systems │
└─────────────────────────────────────────────────────────────┘
```

**Controles de Seguridad:**

1. **Controles Preventivos**
 - Firewalls y segmentación de red
 - Validación y saneamiento de entrada
 - Mecanismos de control de acceso
 - Encriptación y protección de datos

2. **Controles Detectivos**
 - Sistemas de detección de intrusiones
 - Monitoreo de seguridad y logging
 - Algoritmos de detección de anomalías
 - Analytics de comportamiento de usuario

3. **Controles Correctivos**
 - Procedimientos de respuesta a incidentes
 - Mecanismos de recuperación de sistemas
 - Gestión de parches de seguridad
 - Herramientas de análisis forense

#### Seguridad de Infraestructura

**Seguridad de Contenedores:**

1. **Seguridad de Imágenes**
 - Escaneo de imágenes base
 - Evaluación de vulnerabilidades
 - Superficie de ataque mínima
 - Actualizaciones regulares

2. **Seguridad en Runtime**
 - Aislamiento de contenedores
 - Límites de recursos
 - Políticas de red
 - Monitoreo en runtime

3. **Seguridad de Orquestación**
 - Implementación de RBAC
 - Gestión de secrets
 - Segmentación de red
 - Logging de auditoría

#### Estado de implementación de controles clave

> Matriz de clasificación funcional del despliegue de laboratorio, siguiendo la taxonomía: Implementado, Parcialmente implementado, Simulado, Planificado, No verificado, Histórico/Obsoleto.

| Control | Estado | Evidencia / Notas | |---------|--------|---------------------| | Autenticación JWT (`JWTTokenProvider`) | Implementado | `src/soar_lab/infrastructure/jwt_token_provider.py`; algoritmo `HS256`; secretos gestionados por `AuthService` en `src/soar_lab/application/use_cases/auth_service.py`; rutas críticas protegidas en `interfaces/api/main.py` | | Autorización / RBAC | Parcial | JWT valida identidad; granularidad de permisos limitada; roles definidos solo a nivel documental | | Autenticación MFA | Planificado / No verificado | No existe implementación operativa en el laboratorio | | Single Sign-On (SSO/SAML/OIDC) | Planificado | No implementado en el laboratorio actual | | WAF | No verificado | Nginx actúa como proxy inverso; módulo WAF no configurado | | DMZ / segmentación de red | Simulado | Diagramas conceptuales; sin zonas de red reales entre contenedores | | Contención real de endpoints | Simulado | `scripts/setup/notify.sh` registra notificaciones; no hay agente EDR ni aislamiento de red real | | Escaneo de vulnerabilidades | Implementado (script + CI) | `scripts/` y `.github/workflows/ci.yml` (`aquasecurity/trivy-action@master`, `scan-type: fs`) | | TLS/SSL en tránsito | Parcial | Certificados autofirmados vía Nginx (`soar.local.crt`); tráfico interno entre contenedores es mayoritariamente HTTP | | Encriptación en reposo | Parcial / No verificado | Depende de configuración de Elasticsearch/OpenSearch/ en Compose | | Network Watcher | Implementado | `src/soar_lab/infrastructure/network_watcher/` conecta workers de Shuffle a `soar_net` | | Logging centralizado | Implementado | Loki + Promtail + Grafana (`infra/docker/compose/logging/docker-compose.logging.yml`) | | Trivy / escaneo de imágenes en CI | Implementado | Job `security-scan` en `.github/workflows/ci.yml` genera `trivy-results.sarif` | | Secretos estáticos / tokens SIEM | Mitigado | Los valores operativos han sido sustituidos en documentación por placeholders (`<...>`) y `<SIEM_TOKEN>`; se recomienda auditar historial Git, logs y artefactos |

> **Nota:** Las recomendaciones de producción (MFA, SSO, WAF, DMZ real, RBAC completo, TLS mútuo, encriptación forzada) deben tratarse como trabajo futuro, no como capacidades activas del laboratorio.

---

#### 3.3 Controles implementados

#### Autenticación y Autorización

> **Ámbito real del laboratorio:** La autenticación operativa de la Lab API se basa únicamente en **JWT**. Los siguientes mecanismos se listan como capacidades futuras o arquitectónicas; **no deben afirmarse como implementados** hasta que cuenten con evidencia de prueba.

**Implementado:**

1. **Autenticación JWT**
 - Tokens firmados con `HS256`
 - Secret gestionado por `JWT_SECRET_KEY` / fallback `API_AUTH_SECRET` en `.env.full`
 - Expiración configurable mediante `JWT_EXPIRATION_MINUTES` (default 60)
 - Endpoints `/auth/login` y `/auth/verify`

**Futuro / No verificado en este despliegue:**

2. **Autenticación Multi-Factor (MFA)**
 - Planificada: OTP basado en tiempo, SMS, tokens de hardware, biometría

3. **Single Sign-On (SSO)**
 - Planificado: SAML 2.0, OAuth 2.0 / OpenID Connect, LDAP/Active Directory

**Control de Acceso:**

- **Principio de Mínimo Privilegio**: aplicado a nivel de configuración y variables `.env`; RBAC con roles granulares no está implementado.
- **Separación de Deberes**: conceptual en los workflows; no cuenta con aprobaciones automáticas en este despliegue.

#### Implementación de JWT

La autenticación de la API se implementa mediante tokens JWT gestionados por `AuthService` y `JWTTokenProvider`.

| Aspecto | Valor / Comportamiento | Ubicación | |---------|------------------------|-----------| | Algoritmo | `HS256` | `src/soar_lab/infrastructure/jwt_token_provider.py` | | Librería | `PyJWT` | `src/soar_lab/infrastructure/jwt_token_provider.py` | | Secret | `config_provider.get('jwt_secret_key')` o fallback `api_auth_secret` | `src/soar_lab/application/use_cases/auth_service.py` | | Longitud mínima | 32 caracteres (se rechaza si es menor, salvo `API_AUTH_SECRET` legacy) | `auth_service.py` | | Expiración | `JWT_EXPIRATION_MINUTES` (por defecto 60 minutos) | `auth_service.py` | | Claims | `sub` (usuario), `iat`, `exp`, `scope: access` | `jwt_token_provider.py` | | Verificación | `POST /auth/verify` con `Authorization: Bearer <token>` | `src/soar_lab/interfaces/api/main.py` |

**Rotación, almacenamiento y buenas prácticas:**

- El secreto JWT (`JWT_SECRET_KEY` o fallback `API_AUTH_SECRET`) se almacena únicamente en `.env.full` y se inyecta vía `config_provider`; nunca se codifica en fuente.
- La longitud mínima recomendada es 32 caracteres; `auth_service.py` rechaza secretos más cortos salvo que se use `API_AUTH_SECRET` legacy.
- El secreto debe regenerarse con `soar-lab generate-secrets --env > .env.full` (o el `Makefile` equivalente) y nunca publicarse en repositorios.
- Tras cambiar `JWT_SECRET_KEY` / `API_AUTH_SECRET`, los tokens emitidos con el secreto anterior quedan inválidos; los usuarios deben volver a autenticarse.
- Los endpoints protegidos usan el dependency `create_get_current_user(auth_service)`.
- JWT no cifra los claims; solo garantiza integridad. No debe transmitirse información sensible (PII, contraseñas) dentro del token.

#### Seguridad de WebSocket (`/ws/logs`)

- El endpoint `/ws/logs` de la Lab API transmite logs en tiempo real usando WebSocket.
- Actualmente no implementa autenticación en la apertura del socket; la autorización se basa en que la API esté levantada y accesible dentro de la red interna o vía Nginx.
- El SPA web-management construye la URL dinámicamente:
 ```javascript
 const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
 const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`;
 ```
- Si el cliente se accede por `https://soar.local`, la conexión usa `wss://soar.local/api/ws/logs`; si es por `http://localhost:8000`, usa `ws://localhost:8000/ws/logs`.
- Nginx reenvía `/api/ws/logs` al backend y añade las cabeceras `Upgrade` y `Connection`.
- **Consideraciones de seguridad**:
 - Usar siempre HTTPS/WSS en entornos no locales para evitar exposición del token y los logs.
 - Validar origen en el servidor (`Origin`/`Host`) antes de aceptar conexiones si se expone la API fuera de `localhost`.
 - Limitar el tamaño y frecuencia de mensajes para mitigar DoS.
 - No enviar credenciales, PII ni datos clasificados a través del canal de logs.
 - La reconexión es manual en `apps/web-management/script.js`; en producción se recomienda implementar reconexión con backoff y notificación de desconexión.

#### Credenciales de ejemplo y valores por defecto del laboratorio

> **Ámbito:** Los siguientes valores son **funcionales para el entorno de laboratorio local**. Están codificados o configurados como *fallbacks* para que el stack arranque cuando `.env.full` no sobrescribe una variable, **pero no deben considerarse secretos operativos**.

| Variable / secreto | Valor por defecto en el laboratorio | Ubicación típica | |--------------------|--------------------------------------|------------------| | `ELASTIC_PASSWORD` | `<ELASTIC_PASSWORD>` (generado por `make generate-secrets`) | `.env.full`, `grafana-datasources.yml` (provisioning) | | `GRAFANA_ADMIN_PASSWORD` | `<GRAFANA_ADMIN_PASSWORD>` (generado; ejemplo: `${GRAFANA_ADMIN_PASSWORD}`) | `.env.full`, scripts de setup de Grafana | | OpenSearch `AUTH` | `admin` / `<OPENSEARCH_PASSWORD>` (fallback `<OPENSEARCH_PASSWORD>`) | `.env.full`, `docker-compose.core.yml` y `docker-compose.opensearch.yml` | | `API_AUTH_SECRET` (fallback) | `<API_AUTH_SECRET>` | `.env.full`, `infra/docker/compose/docker-compose.api.yml` | | `JWT_SECRET_KEY` (fallback) | `<JWT_SECRET_KEY>` (mínimo 32 caracteres) | `.env.full`, `src/soar_lab/config/settings.py` |

**Recomendaciones:**

- Antes de cualquier despliegue no local, generar valores seguros con `soar-lab generate-secrets --env > .env.full` y sobrescribir todos los valores anteriores.
- La documentación y los ejemplos de comandos deben usar placeholders inequívocos del tipo `<ELASTIC_PASSWORD>`, `<JWT_SECRET_KEY>`, etc.
- No publicar capturas de pantalla, logs, artefactos ni backups que contengan estas credenciales sin enmascararlas.

#### Protección de Datos

**Gestión del Ciclo de Vida de Datos:**

1. **Retención de Datos**
 - Políticas de retención automatizadas
 - Procedimientos de legal hold
 - Eliminación segura de datos
 - Documentación de cumplimiento

2. **Privacidad de Datos**
 - Identificación y enmascaramiento de PII
 - Cumplimiento GDPR
 - Principios de minimización de datos
 - Privacidad por diseño

#### Seguridad de Aplicación

**Ciclo de Vida de Desarrollo Seguro:**

1. **Fase de Diseño**
 - Modelado de amenazas
 - Revisión de arquitectura de seguridad
 - Definición de requisitos de seguridad
 - Evaluación de impacto de privacidad

2. **Fase de Desarrollo**
 - Estándares de codificación segura
 - Procesos de revisión de código
 - Escaneo de análisis estático
 - Escaneo de vulnerabilidades de dependencias

3. **Fase de Pruebas**
 - Automatización de pruebas de seguridad
 - Pruebas de penetración
 - Evaluación de vulnerabilidades
 - Pruebas de regresión de seguridad

4. **Fase de Despliegue**
 - Revisión de configuración de seguridad
 - Hardening de producción
 - Configuración de monitoreo de seguridad
 - Preparación de respuesta a incidentes

#### Respuesta a Incidentes

**Proceso de Respuesta a Incidentes:**

```
┌─────────────────────────────────────────────────────────────┐
│ Ciclo de Vida de Respuesta a Incidentes │
├─────────────────────────────────────────────────────────────┤
│ Preparación → Detección → Análisis → Contención → Erradicación │
├─────────────────────────────────────────────────────────────┤
│ Recuperación → Post-incidente → Lecciones Aprendidas → Mejora │
└─────────────────────────────────────────────────────────────┘
```

**Procedimientos de Respuesta:**

1. **Respuesta a Ransomware**
 - Aislamiento inmediato
 - Preservación de evidencia
 - Protocolos de comunicación
 - Procedimientos de recuperación

2. **Respuesta a Violación de Datos**
 - Medidas de contención
 - Evaluación de impacto
 - Procedimientos de notificación
 - Acciones de remediación

3. **Respuesta a Incidente de Seguridad**
 - Triage y priorización
 - Procedimientos de investigación
 - Análisis forense
 - Requisitos de documentación

#### Procedimientos Específicos de Respuesta a Ransomware

**Fase 1: Detección y Aislamiento (0-15 minutos)**

```bash
# 1. Identificar sistemas afectados
docker ps | grep -E "thehive|cortex|shuffle"

# 2. Aislar contenedores afectados
docker stop soar_thehive soar_cortex soar_shuffle_backend

# 3. Preservar evidencia forense
docker commit soar_thehive soar_thehive_forensic_<timestamp>
docker logs soar_thehive > runtime/forensic/thehive_<timestamp>.log
```

**Fase 2: Análisis y Contención (15-60 minutos)**

> **Nota sobre contención activa:** No existe un `containment_service.py` en el repositorio. La contención real de endpoints (aislamiento de red, bloqueo de cuentas, terminación de procesos) **está simulada**: el workflow de Shuffle decide y, en caso malicioso, invoca `scripts/setup/notify.sh` para registrar la notificación y generar métricas. Una respuesta activa real requeriría un agente EDR o responder conectado.

```bash
# 1. Analizar logs de alertas
cat runtime/logs/notify.log | grep -i ransomware

# 2. Verificar integridad de datos
bash scripts/

# 3. Ejecutar scripts de contención simulada
bash scripts/setup/notify.sh
```

**Fase 3: Erradicación y Recuperación (1-4 horas)**

```bash
# 1. Restaurar desde backup limpio
curl -X POST http://localhost:8000/backup/restore \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"name": "<clean_backup_name>"}'

# 2. Verificar integridad de servicios
make health

# 3. Actualizar credenciales comprometidas
soar-lab generate-secrets --env > .env.full
```

#### 3.4 Cumplimiento y protección de datos

#### Clasificación de Datos

```
┌─────────────────────────────────────────────────────────────┐
│ Clasificación de Datos │
├─────────────────────────────────────────────────────────────┤
│ Público │ Interno │ Confidencial │ Secreto │
│ - Marketing │ - Operaciones │ - Datos de Cliente │ - Claves │
│ - Documentación│ - Procedimientos│ - Incidentes │ - Cripto│
│ - APIs Públicas │ - Documentos Internos│ - Forensics │ - Admin │
└─────────────────────────────────────────────────────────────┘
```

#### Matriz de Trazabilidad: Controles de Seguridad vs Requisitos Regulatorios

| Control de Seguridad | GDPR Art. 32 | SOC 2 CC6.1 | ISO 27001 A.12 | NIST CSF PR.AC | Implementación | |-----------------------------|--------------|-------------|----------------|----------------|-------------------------------------------------------------| | Autenticación MFA | ✓ | ✓ | ✓ | ✓ | Shuffle, TheHive (pendiente) | | Encriptación AES-256 | ✓ | ✓ | ✓ | ✓ | Elasticsearch (pendiente) | | TLS 1.3 en tránsito | ✓ | ✓ | ✓ | ✓ | Nginx (pendiente) | | RBAC | ✓ | ✓ | ✓ | ✓ | Todos los servicios (parcial) | | Logging de auditoría | ✓ | ✓ | ✓ | ✓ | Docker logs (implementado) | | Retención de datos | ✓ | ✓ | ✓ | ✓ | Configuración por definir | | Respuesta a incidentes | ✓ | ✓ | ✓ | ✓ | Playbook E2E (implementado) | | Backups automatizados | ✓ | ✓ | ✓ | ✓ | API `/backup/create` (implementado) | | Escaneo de vulnerabilidades | ✓ | ✓ | ✓ | ✓ | `scripts/` (implementado) |

**Nota:** Los controles marcados como "pendiente" son recomendaciones para producción que no están implementados en el
laboratorio actual.

#### Cumplimiento Regulatorio

El laboratorio está orientado hacia los siguientes marcos de referencia, pero **no constituye una certificación** ni garantía formal:

- **GDPR**: Protección de datos personales
- **SOC 2**: Seguridad y disponibilidad
- **ISO 27001**: Gestión de seguridad de la información

#### 3.5 Diagramas o matrices

#### Vectores de Ataque

```
┌─────────────────────────────────────────────────────────────┐
│ Superficie de Ataque │
├─────────────────────────────────────────────────────────────┤
│ Web Interface │ API Endpoints │ File Uploads │ Email │
├─────────────────────────────────────────────────────────────┤
│ Network Ports │ Authentication │ Data Storage │ Logs │
├─────────────────────────────────────────────────────────────┤
│ Third-party │ Dependencies │ Backups │ Config │
└─────────────────────────────────────────────────────────────┘
```

#### Procedimientos de Hardening por Componente

**Shuffle SOAR:**

- Cambiar credenciales por defecto (SHUFFLE_DEFAULT_APIKEY)
- Habilitar autenticación multi-factor
- Configurar HTTPS con certificados TLS válidos
- Limitar acceso a IPs específicas
- Deshabilitar analyzers no necesarios

**TheHive:**

- Cambiar credenciales por defecto de admin
- Configurar HTTPS con certificados TLS
- Implementar políticas de retención de datos
- Habilitar auditoría de acciones
- Configurar CORS restrictivo

**Cortex:**

- Cambiar credenciales por defecto
- Limitar analyzers activos
- Configurar rate limiting
- Habilitar autenticación fuerte
- Revisar y actualizar analyzers regularmente

**Elasticsearch:**

- Habilitar xpack.security (actualmente deshabilitado para desarrollo)
- Configurar autenticación básica o TLS
- Implementar encriptación de datos en reposo
- Configurar firewall de red
- Limitar acceso a puertos (9201)

**MISP:**

- Cambiar credenciales por defecto
- Configurar HTTPS
- Implementar autenticación SAML/LDAP
- Configurar políticas de feed
- Habilitar logging de auditoría

**:**

- Configurar autenticación API
- Implementar reglas de firewall
- Configurar políticas de retención
- Habilitar encriptación de comunicaciones
- Limitar acceso a puertos (15141-1516)

**Nginx:**

- Configurar HTTPS con TLS 1.3
- Implementar HSTS
- Configurar WAF básico
- Limitar tamaño de uploads
- Configurar rate limiting

#### Framework de Autorización (RBAC)

```python
# Control de acceso basado en roles (RBAC)
ROLES = {
 'admin': ['read', 'write', 'delete', 'manage'],
 'analyst': ['read', 'write', 'analyze'],
 'operator': ['read', 'execute'],
 'viewer': ['read']
}

PERMISSIONS = {
 'alerts': ['read', 'write', 'delete'],
 'cases': ['read', 'write', 'delete', 'assign'],
 'playbooks': ['read', 'write', 'execute'],
 'users': ['read', 'write', 'delete'],
 'system': ['read', 'write', 'manage']
}
```

#### Estándares de Encriptación

**Datos en Reposo:**

- Encriptación AES-256
- Encriptación de disco completo
- Encriptación de base de datos
- Encriptación de filesystem

**Datos en Tránsito:**

- TLS 1.3 para todas las comunicaciones
- Certificate pinning
- Autenticación TLS mutua
- VPN para acceso remoto

**Gestión de Claves:**

- Módulos de Seguridad de Hardware (HSM)
- Políticas de rotación de claves
- Almacenamiento seguro de claves
- Procedimientos de escrow y recuperación

#### Seguridad de Red

**Arquitectura de Red:**

```
┌─────────────────────────────────────────────────────────────┐
│ Internet │
├─────────────────────────────────────────────────────────────┤
│ Firewall │ IDS/IPS │ Load Balancer │ WAF │
├─────────────────────────────────────────────────────────────┤
│ Red DMZ │
│ Web Servers │ API Gateways │ Reverse Proxies │
├─────────────────────────────────────────────────────────────┤
│ Red de Aplicación │
│ App Servers │ Microservices │ Internal APIs │
├─────────────────────────────────────────────────────────────┤
│ Red de Datos │
│ Databases │ File Storage │ Backup Systems │
└─────────────────────────────────────────────────────────────┘
```

#### Marcos Regulatorios

**GDPR (Regulación General de Protección de Datos):**

- Derechos del sujeto de datos
- Gestión de consentimiento
- Notificación de violación de datos
- Privacidad por diseño

**SOC 2 (Service Organization Control 2):**

- Controles de seguridad
- Controles de disponibilidad
- Integridad de procesamiento
- Controles de privacidad

**ISO 27001 (Gestión de Seguridad de la Información):**

- Implementación de ISMS
- Gestión de riesgos
- Mejora continua
- Mantenimiento de certificación

#### 4. Validación

#### 4.1 Verificación

La seguridad se verifica mediante:

- Escaneos automatizados de vulnerabilidades
- Pruebas de penetración periódicas
- Auditorías de seguridad internas y externas
- Revisiones de código de seguridad
- Monitoreo continuo de seguridad
- Evaluaciones de cumplimiento

#### 4.2 Criterios de aceptación

La seguridad se considera válida cuando:

- Todos los controles de seguridad están implementados
- Las pruebas de seguridad pasan sin vulnerabilidades críticas
- El monitoreo de seguridad detecta anomalías
- Los procedimientos de respuesta a incidentes están documentados y probados
- El cumplimiento regulatorio se mantiene
- Los usuarios están capacitados en políticas de seguridad

#### 4.3 Evidencias

Las evidencias de validación incluyen:

- Reportes de escaneo de vulnerabilidades
- Reportes de pruebas de penetración
- Logs de auditoría de seguridad
- Certificados de cumplimiento
- Documentación de políticas y procedimientos
- Registros de capacitación de seguridad

#### 5. Problemas y consideraciones

#### 5.1 Limitaciones

- **Configuración por defecto**: Las configuraciones por defecto de las herramientas pueden no ser adecuadas para
 producción
- **Recursos limitados**: Monitoreo y respuesta a incidentes requieren personal dedicado
- **Dependencias de terceros**: Seguridad depende de la seguridad de componentes de terceros
- **Evolución de amenazas**: Las amenazas evolucionan constantemente, requiriendo actualizaciones continuas

#### 5.2 Riesgos o incidencias

- **Falta de hardening**: Configuraciones inseguras pueden exponer vulnerabilidades
- **Fuga de datos**: Brechas de seguridad pueden resultar en pérdida de datos sensibles
- **Disponibilidad**: Ataques DDoS pueden afectar la disponibilidad del sistema
- **Cumplimiento**: Falta de cumplimiento puede resultar en sanciones regulatorias
- **Insiders**: Usuarios maliciosos internos pueden eludir controles de seguridad

#### 5.3 Recomendaciones / troubleshooting

- **Hardening**: Implementar hardening de seguridad antes de despliegue en producción
- **Monitoreo**: Configurar alertas de seguridad para detección temprana
- **Capacitación**: Proporcionar capacitación regular de seguridad a todos los usuarios
- **Actualizaciones**: Mantener todos los componentes actualizados con parches de seguridad
- **Pruebas**: Ejecutar pruebas de seguridad regularmente para identificar vulnerabilidades

#### 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Seguridad de Shuffle**: https://shuffler.io/docs/security
- **Documentación de Seguridad de TheHive**: https://docs.strangebee.com/thehive/admin-guide/security/
- **Documentación de Seguridad de Cortex**: https://docs.strangebee.com/cortex/admin-guide/security/
- **Documentación de Seguridad de MISP**: https://www.misp-project.org/guides/admin/
- **Documentación de Seguridad de Elasticsearch
 **: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-settings.html
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Marco de Ciberseguridad NIST**: https://www.nist.gov/cyberframework
- **Benchmarks CIS**: https://www.cisecurity.org/cis-benchmarks/
- **Documentación de Arquitectura**: [docs/02-architecture.md](#31-visión-general-de-arquitectura)
- **Guía de Usuario**: [docs/01-getting-started.md](01-getting-started.md)

---

**Mejoras implementadas:**

- Corregidas referencias a docs/core/ a rutas correctas (docs/02-architecture.md, docs/01-getting-started.md)
- Añadidos procedimientos detallados de hardening para cada componente (Shuffle, TheHive, Cortex, Elasticsearch, MISP, Nginx)
- Documentados procedimientos específicos de respuesta a ransomware con 3 fases (detección, análisis, recuperación)
- Añadida matriz de trazabilidad entre controles de seguridad y requisitos regulatorios (GDPR, SOC 2, ISO 27001, NIST
 CSF)


### 3.10 Matriz de versiones

Esta matriz resume las versiones canónicas de las dependencias, imágenes Docker y herramientas utilizadas en el repositorio. La fuente de verdad sigue siendo `pyproject.toml`, los archivos `docker-compose*.yml` y `.github/workflows/ci.yml`.

#### Proyecto

| Componente | Versión / Requisito | Fuente | |------------|---------------------|--------| | `soar-lab` (proyecto) | `1.4.0` | `pyproject.toml` | | Python | `>=3.11` | `pyproject.toml` | | Node.js (docs-site) | `>=18.0` | `apps/docs-site/package.json` | | Docusaurus | `^3.0.0` | `apps/docs-site/package.json` | | React | `^18.2.0` | `apps/docs-site/package.json` |

#### Dependencias principales (Python)

| Paquete | Versión mínima | Fuente | |---------|----------------|--------| | FastAPI | `>=0.100.0` | `pyproject.toml` | | Uvicorn | `>=0.23.0` | `pyproject.toml` | | Pydantic | `>=2.0.0` | `pyproject.toml` | | Redis (cliente) | `>=4.0.0` | `pyproject.toml` | | Docker SDK | `>=6.0.0` | `pyproject.toml` | | psutil | `>=5.9.0` | `pyproject.toml` |

#### Calidad de código y tests

| Herramienta | Versión / Configuración | Fuente | |-------------|-------------------------|--------| | pytest | `>=7.0.0` | `pyproject.toml` (`[tool.pytest.ini_options]`) | | pytest-cov | `>=4.0.0` | `pyproject.toml` | | pytest-asyncio | `>=0.21.0` | `pyproject.toml` | | Black | `>=23.0.0` / longitud `100` / `py311` | `pyproject.toml`, `.pre-commit-config.yaml` | | isort | `>=5.12.0` / perfil `black` | `pyproject.toml`, `.pre-commit-config.yaml` | | flake8 | `>=6.0.0` / `max-line-length=100` | `pyproject.toml`, `.pre-commit-config.yaml` | | mypy | `>=1.0.0` / `python_version=3.11` | `pyproject.toml` | | pre-commit | `>=3.0.0` | `pyproject.toml` | | ShellCheck | (versión del runner) | `.github/workflows/ci.yml` |

#### Imágenes Docker

#### Core / SOAR

| Servicio | Imagen | Fuente | |----------|--------|--------| | Redis | `redis:7-alpine` | `infra/docker/compose/docker-compose.core.yml` | | TheHive | `thehiveproject/thehive:3.5.2-1` | `infra/docker/compose/docker-compose.core.yml` | | Shuffle Frontend | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | `infra/docker/compose/docker-compose.core.yml` | | Shuffle Backend | `ghcr.io/shuffle/shuffle-backend:2.2.1` | `infra/docker/compose/docker-compose.core.yml` | | Shuffle Orborus | `ghcr.io/shuffle/shuffle-orborus:2.2.1-patched` | `infra/docker/compose/docker-compose.core.yml` | | Tenzir Node | `tenzir/tenzir:v6.8.1` | `infra/docker/compose/docker-compose.core.yml` | | Nginx | `nginx:1.25-alpine` | `infra/docker/compose/docker-compose.api.yml` |

#### Bases de datos e índices

| Servicio | Imagen | Fuente | |----------|--------|--------| | Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | `infra/docker/compose/docker-compose.yml` | | OpenSearch | `opensearchproject/opensearch:2.10.0` | `infra/docker/compose/docker-compose.opensearch.yml` | | OpenSearch Dashboards | `opensearchproject/opensearch-dashboards:2.10.0` | `infra/docker/compose/docker-compose.opensearch.yml` | | Grafana DB (Postgres) | `postgres:14-alpine` | `infra/docker/compose/logging/docker-compose.logging.yml` |

#### Logging y observabilidad

| Servicio | Imagen | Fuente | |----------|--------|--------| | Grafana | `grafana/grafana:10.3.4` | `infra/docker/compose/logging/docker-compose.logging.yml` | | Loki | `grafana/loki:2.9.10` | `infra/docker/compose/logging/docker-compose.logging.yml` | | Promtail | `grafana/promtail:2.9.9` | `infra/docker/compose/logging/docker-compose.logging.yml` |

#### MISP

| Servicio | Imagen | Fuente | |----------|--------|--------| | MISP DB | `mariadb:10.11` | `infra/docker/compose/docker-compose.misp.yml` | | MISP Core | `ghcr.io/misp/misp-docker/misp-core:v2.5.44` | `infra/docker/compose/docker-compose.misp.yml` | | MISP Modules | `ghcr.io/misp/misp-docker/misp-modules:v3.0.9` | `infra/docker/compose/docker-compose.misp.yml` |

###

| Servicio | Imagen | Fuente | |----------|--------|--------|

#### CI/CD y runners

| Componente | Versión | Fuente | |------------|---------|--------| | GitHub Actions runner | `ubuntu-latest` | `.github/workflows/ci.yml` | | Python CI | `3.11` | `.github/workflows/ci.yml` | | Node.js CI | `20` | `.github/workflows/ci.yml` | | Trivy | `master` (`aquasecurity/trivy-action`) | `.github/workflows/ci.yml` |

#### Notas de coherencia

- El proyecto requiere **Python 3.11+** en `pyproject.toml` y en `.github/workflows/ci.yml`.
- `apps/docs-site/package.json` declara `node>=18.0`, mientras que CI usa `node-version: '20'`; ambas son compatibles.
- `tenzir/tenzir:v6.8.1` está fijada a una etiqueta de versión; para mayor reproducibilidad se recomienda fijar a un digest SHA en producción.
- Las imágenes `misp-core:v2.5.44` y `misp-modules:v3.0.9` están fijadas a etiquetas de versión; para mayor reproducibilidad se recomienda fijar a un digest SHA.
- Las versiones de Shuffle (`2.2.1`) y TheHive (`3.5.2-1`) coinciden con las variables documentadas en `docs/03-api-and-integrations.md` y `docs/02-architecture.md`.


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

#### 5. Problemas y consideraciones

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

#### 6. Referencias

- [01-getting-started.md](01-getting-started.md)
- [03-api-and-integrations.md](03-api-and-integrations.md)
- [04-operations.md](04-operations.md)
- [glossary.md](glossary.md)

## 4. Validación

### 4.1 Verificación

La arquitectura se verifica mediante:

- Pruebas de configuración Docker (`tests/integration/test_docker_runtime_status.py`)
- Pruebas de runtime Docker (`tests/integration/test_docker_runtime_status.py`)
- Pruebas de navegador (`tests/integration/test_docker_runtime_status.py`)
- Health checks de cada servicio
- Verificación de conectividad entre redes Docker

### 4.2 Criterios de aceptación

La arquitectura se considera válida cuando:

- Todos los servicios inician correctamente
- Los puertos configurados son accesibles
- Las redes Docker permiten la comunicación requerida
- Los volúmenes persistentes montan correctamente
- Los servicios de logging y monitoreo funcionan
- Los health checks pasan para todos los servicios

### 4.3 Evidencias

Las evidencias de validación incluyen:

- Logs de Docker Compose (`docker compose up`)
- Salida de `docker ps` mostrando contenedores en ejecución
- Logs de health checks
- Resultados de pruebas automatizadas
- Capturas de pantalla de interfaces web accesibles

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Single-node Elasticsearch**: Configuración actual no soporta clustering
- **Requisitos de recursos**: Mínimo 8GB RAM requerido para stack completo
- **Windows/Hyper-V**: Restricciones en rangos de puertos debido a reservas de Hyper-V
- **Escalabilidad**: Diseño actual no soporta alta disponibilidad nativa
- **Persistencia**: Los volúmenes Docker requieren backup manual

### 5.2 Riesgos o incidencias

- **Pérdida de datos**: Si los volúmenes Docker no se respaldan regularmente
- **Conflictos de puertos**: Puertos ya en uso en el host pueden causar fallos
- **Dependencias de red**: Requiere conectividad a internet para pulls de imágenes
- **Versiones de componentes**: Actualizaciones pueden romper compatibilidad
- **Seguridad**: Configuración por defecto puede no ser adecuada para producción

### 5.3 Recomendaciones / troubleshooting

- **Backup**: Implementar backup automatizado de volúmenes persistentes
 ```bash
 # Crear backup vía API
 curl -X POST http://localhost:8000/api/backup/create \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"name": "manual-backup"}'
 ```
- **Procedimiento de Backup de Volúmenes**:
 - Los volúmenes Docker usan bind mounts a `runtime/data/`
 - Backup manual: Copiar directorio `runtime/data/` a ubicación segura
 - Backup automatizado: Llamar al endpoint `/api/backup/create` o programar tarea con `curl`
 - Restauración: Llamar al endpoint `/api/backup/restore` con el nombre del backup
- **Monitoreo**: Configurar alertas para health checks y métricas de recursos
- **Seguridad**: Revisar y hardening de configuración antes de despliegue en producción
- **Documentación**: Mantener documentación actualizada con cambios de configuración
- **Testing**: Ejecutar pruebas de configuración antes de cambios en Docker Compose

---

#### Navegación

- [Instalación y guía rápida](01-getting-started.md)
- [API REST, endpoints e integraciones](03-api-and-integrations.md)
- [Configuración, infraestructura, backups, troubleshooting](04-operations.md)
- [Estrategia de pruebas y suite](05-testing.md)
- [Objetivos, plan, riesgos, auditorías](06-project-management.md)
- [Glosario central](glossary.md)
- [Índice](index.md)
## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de FastAPI**: https://fastapi.tiangolo.com/
- **Documentación de Nginx**: https://nginx.org/en/docs/
- **Documentación de Seguridad**: [docs/02-architecture.md](#39-seguridad)
- **Guía de Usuario**: [docs/01-getting-started.md](01-getting-started.md)
- **Estrategia de Docker**: [docs/02-architecture.md](#35-arquitectura-docker)

---

**Mejoras implementadas:**

- Corregidas referencias a docs/core/ a rutas correctas (docs/02-architecture.md)
- Documentados procedimientos de backup de volúmenes en sección 5.3
- Añadidos diagramas de secuencia Mermaid para flujos de integración en sección 3.4
