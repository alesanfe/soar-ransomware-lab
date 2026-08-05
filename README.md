# Laboratorio SOAR para Respuesta ante Ransomware

**Trabajo Fin de Máster (TFM) - Máster en Ciberseguridad**

Este repositorio contiene la **Infraestructura como Código (IaC)** completa y los scripts necesarios para implementar un
laboratorio **SOAR (Security Orchestration, Automation and Response)** especializado en la respuesta ante incidentes de
ransomware. El laboratorio integra múltiples herramientas de seguridad desplegadas mediante **Docker**, con suites de
pruebas completas y automatización mediante **Makefile**.

> ⚠️ **Advertencia**: Este laboratorio está diseñado exclusivamente para entornos de pruebas y formación académica. No
> se recomienda su uso en entornos de producción sin aplicar las guías oficiales y medidas de seguridad adicionales.

---

## Índice

- [Objetivos del Laboratorio](#objetivos-del-laboratorio)
- [Arquitectura General](#arquitectura-general)
- [Resumen de Arquitectura](#resumen-de-arquitectura)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Documentación del Proyecto](#documentación-del-proyecto)
- [Instalación Rápida](#instalación-rápida)
- [Automatización Opcional](#automatización-opcional)
- [Buenas Prácticas](#buenas-prácticas)
- [Métricas y Pruebas](#métricas-y-pruebas)
- [Contexto Académico](#contexto-académico)
- [Referencias Clave](#referencias-clave)
- [Licencia y Uso](#licencia-y-uso)

---

## 🎯 Objetivos del Laboratorio

- Simular incidentes de ransomware en un entorno controlado y seguro
- Automatizar la respuesta mediante **playbooks SOAR** con múltiples orquestadores
- Reducir el Tiempo Medio de Respuesta (**MTTR**) y mejorar la trazabilidad
- Proporcionar un entorno reproducible para pruebas y formación en ciberseguridad
- Validar la eficacia de la orquestación automatizada en incidentes reales
- Integrar herramientas de Threat Intelligence para análisis automatizado

---

## 🏗️ Arquitectura General

El laboratorio sigue una **arquitectura hexagonal (Ports and Adapters)** en el código Python y una **arquitectura modular de
Docker Compose** en el despliegue. El dominio (`src/soar_lab/domain/`) define modelos, puertos y casos de uso; la
infraestructura (`src/soar_lab/infrastructure/`) provee los adaptadores concretos (clientes HTTP, repositorios, drivers, JWT,
backup); y las interfaces (`src/soar_lab/interfaces/`) exponen una API FastAPI, un panel web y la CLI. El cableado de
dependencias se centraliza en `src/soar_lab/interfaces/api/composition.py`.

```mermaid
flowchart LR
  SIEM[(SIEM/XDR)] -- Webhook/Feeder --> Shuffle
  Shuffle -- API --> TheHive
  TheHive -- Observables --> Cortex
  Cortex -- Analyzers --> TI[(Threat Intel)]
  Shuffle -- Responder/API --> EDR[(EDR/Defender for Endpoint)]
  TheHive <--> Elasticsearch
  Cortex <--> Redis
  Shuffle <--> OpenSearch[OpenSearch]
  Wazuh[Wazuh Manager] --> WazuhIndexer[Wazuh Indexer]
  Wazuh --> Shuffle
  Wazuh --> WazuhDashboard[Wazuh Dashboard]
  WazuhIndexer --> WazuhDashboard
  Shuffle -- Metrics --> Elasticsearch
  Elasticsearch --> Grafana[Grafana]
  Promtail[Promtail] --> Loki[Loki]
  Loki --> Grafana
  Promtail --> Elasticsearch
  Grafana --> Elasticsearch
```

### Resumen de Arquitectura

En el flujo operativo, Wazuh o el simulador generan alertas que Shuffle consume mediante webhook. Shuffle orquesta la
creación de casos en TheHive, el enriquecimiento de observables en Cortex y la decisión de contención simulada. Las
métricas se indexan en Elasticsearch y se visualizan en Grafana; los logs se agregan en Loki. Nginx actúa como proxy
inverso HTTPS para los servicios que lo soportan, mientras que otros servicios se acceden directamente por puerto.

**Componentes Principales:**

- **Shuffle**: Orquestador principal, recibiendo alertas y ejecutando flujos automatizados
- **TheHive**: Gestiona casos de incidentes y evidencias forenses
- **Cortex**: Analiza Indicadores de Compromiso (IoCs) mediante analyzers especializados
- **Wazuh Manager**: Plataforma SIEM/XDR para detección de amenazas y respuesta a incidentes
- **Wazuh Dashboard**: Dashboard de visualización de datos y logs de Wazuh/Wazuh Indexer
- **Elasticsearch 7.10.2**: Motor de búsqueda para TheHive, Cortex y las métricas indexadas por Shuffle
- **OpenSearch 2.10.0**: Motor de búsqueda usado por Shuffle y el backend del stack de logging
- **Wazuh Indexer**: Clúster OpenSearch interno de Wazuh para almacenar alertas y logs del SIEM
- **Redis**: Servicio de soporte para persistencia y caché
- **PostgreSQL**: Base de datos para TheHive y Grafana
- **MariaDB**: Base de datos para MISP
- **MISP**: Plataforma de inteligencia de amenazas (Threat Intelligence)
- **Nginx**: Reverse proxy centralizado para acceso a todos los servicios
- **API**: API REST (FastAPI) para gestión y automatización del laboratorio
- **Web Management**: Panel de control web centralizado
- **Docs Site**: Sitio de documentación Docusaurus
- **Grafana**: Dashboards de KPIs y observabilidad
- **Loki**: Agregación de logs
- **Promtail**: Recolección de logs de contenedores

---

## 📁 Estructura del Repositorio

```
soar-ransomware-lab/
├── README.md                    # Documentación principal del proyecto
├── LICENSE                      # Licencia del proyecto
├── Makefile                     # Comandos rápidos: up/down/test/metrics (Linux/Mac)
├── Makefile.win                 # Comandos rápidos: up/down/test/metrics (Windows)
├── pyproject.toml               # Configuración de proyecto Python
├── pytest.ini                  # Configuración de pytest
├── requirements-test.txt         # Dependencias para testing
├── .gitignore                  # Archivos ignorados por git
├── .env.full                   # Variables de entorno completas (generado por `make generate-secrets`, .gitignore)
├── .env.example                # Plantilla saneada de variables de entorno con marcadores de relleno
├── CHANGELOG.md                # Historial de cambios
├── CONTRIBUTING.md              # Guía de contribución
├── docs/API_DOCUMENTATION.md   # Documentación de la API
├── infra/                      # Infraestructura como código
│   ├── docker/                # Configuración Docker
│   │   ├── compose/           # Archivos docker-compose yml
│   │   │   ├── docker-compose.yml
│   │   │   ├── docker-compose.core.yml
│   │   │   ├── docker-compose.misp.yml
│   │   │   ├── docker-compose.opensearch.yml
│   │   │   ├── docker-compose.vagrant.yml
│   │   │   ├── docker-compose.wazuh.yml
│   │   │   ├── docker-compose.api.yml
│   │   │   └── logging/       # Stack de logging (Loki, Promtail, Grafana)
│   │   ├── config/            # Configuraciones centralizadas
│   │   │   ├── nginx/
│   │   │   ├── cortex.application.conf/
│   │   │   └── thehive.application.conf/
│   │   ├── images/            # Dockerfiles personalizados
│   │   │   └── cortex/
│   │   └── wazuh/             # Configuración Wazuh + certificados
│   └── vagrant/              # Automatización con Vagrant
│       ├── Vagrantfile
│       ├── provision.sh
│       └── provision-windows.ps1
├── apps/                       # Aplicaciones del proyecto
│   ├── api/                   # Contenedor API FastAPI (Dockerfile)
│   ├── docs-site/             # Sitio de documentación Docusaurus
│   └── web-management/        # Panel de gestión web (HTML/JS estático)
├── src/soar_lab/             # Código fuente principal (Hexagonal Architecture)
│   ├── application/           # Casos de uso y servicios de aplicación
│   │   └── use_cases/         # analytics, auth, backup, etc.
│   ├── common/                # Excepciones y utilidades compartidas
│   ├── config/                # Configuración y logging
│   ├── data/                  # Esquemas y utilidades de datos
│   ├── domain/                # Lógica de negocio pura
│   │   ├── models.py          # Entidades de dominio (dataclasses)
│   │   ├── ports/             # Interfaces (Protocolos)
│   │   ├── services/          # Servicios de dominio (kpi_analyzer, ioc_generator)
│   │   ├── statistical_calculator.py
│   │   └── value_objects/
│   ├── infrastructure/        # Adaptadores e implementaciones
│   │   ├── external/          # Clientes de integraciones (Shuffle, MISP, etc.)
│   │   ├── messaging/         # Envío de alertas
│   │   ├── monitoring/        # Health checks, métricas, KPI alerts
│   │   ├── network_watcher/   # Conectividad dinámica de workers Shuffle
│   │   ├── persistence/       # Repositorios (SQLite)
│   │   ├── scripts/           # Scripts de setup y utilidades
│   │   └── security/          # JWT y credenciales
│   ├── interfaces/            # Puntos de entrada (API, CLI, Webhooks)
│   │   └── api/               # FastAPI routes, models, auth
│   ├── scripts/               # Scripts CLI del laboratorio
│   ├── simulator/             # Simulador de alertas SIEM
│   └── validation/            # Validadores
├── tests/                      # Suite de pruebas completa
│   ├── unit/                  # Pruebas unitarias
│   ├── atomic/                # Pruebas atómicas
│   ├── integration/           # Pruebas de integración
│   ├── e2e/                   # Pruebas end-to-end
│   ├── general/               # Pruebas generales
│   ├── performance/           # Pruebas de rendimiento
│   ├── security/              # Pruebas de seguridad
│   ├── fixtures/              # Datos de prueba
│   ├── runners/               # Ejecutores de tests
│   └── conftest.py            # Configuración pytest
├── docs/                       # Documentación completa
│   ├── architecture/          # Documentación de arquitectura
│   ├── audit/                 # Informes de auditoría
│   ├── getting_started/       # Guías de inicio
│   ├── integrations/          # Integraciones y contratos
│   ├── operations/            # Guías operativas
│   ├── project/               # Documentación de proyecto
│   ├── testing/               # Documentación de pruebas
│   └── thesis/                # Documentación académica TFM
└── artifacts/                  # Artefactos generados
    ├── backups/               # Copias de seguridad
    ├── coverage/              # Reportes de cobertura
    ├── data/                  # Datos persistentes
    ├── logs/                  # Logs de ejecución
    └── results/               # Resultados de pruebas
```

---

## Estado Documental

| Área | Documento principal | Estado |
|------|---------------------|--------|
| Arquitectura | [architecture/overview.md](docs/architecture/overview.md) | En revisión |
| Operaciones | [operations/configuration_manual.md](docs/operations/configuration_manual.md) | En revisión |
| Integraciones | [integrations/overview.md](docs/integrations/overview.md) | En revisión |
| Pruebas | [testing/test_suite.md](docs/testing/test_suite.md) | Actualizado |
| Proyecto | [project/glossary.md](docs/project/glossary.md) | En revisión |
| Tesis | [thesis/introduction.md](docs/thesis/introduction.md) | En revisión |
| Índice completo | [docs/README.md](docs/README.md) | En revisión |

> La tabla detallada con fechas de última revisión y responsable está en [`docs/README.md`](docs/README.md).

---

## 📚 Documentación del Proyecto

Este proyecto incluye documentación técnica completa organizada en el directorio `docs/`:

### Documentación Principal

- **[Índice de Documentación](docs/README.md)** - Índice completo de toda la documentación del proyecto
- **[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** - Documentación completa de todas las APIs del sistema. La fuente de verdad de contratos es `docs/api/openapi.json` generado por FastAPI.
- **[CHANGELOG.md](docs/thesis/CHANGELOG_THESIS_UPDATE.md)** - Historial de cambios y versiones del proyecto
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Guía para desarrolladores y contribuidores

### Documentación Técnica

- **[Índice de Documentación](docs/README.md)** - Índice completo de toda la documentación del proyecto
- **[Arquitectura](docs/architecture/overview.md)** - Diseño detallado del sistema y relaciones entre componentes
- **[Arquitectura Docker](docs/architecture/docker_architecture.md)** - Arquitectura Docker, archivos compose y
  despliegue
- **[Seguridad](docs/architecture/security.md)** - Consideraciones de seguridad y mejores prácticas

### Guías de Usuario

- **[Visión General](docs/getting_started/overview.md)** - Visión general del laboratorio
- **[Guía de Instalación](docs/getting_started/installation_guide.md)** - Guía paso a paso de instalación
- **[Guía de Usuario](docs/getting_started/user_guide.md)** - Manual completo de operación del laboratorio

### Operaciones

- **[Manual de Configuración](docs/operations/configuration_manual.md)** - Configuración completa del laboratorio
- **[Playbooks](docs/operations/playbooks/)** - Documentación de playbooks
- **[Troubleshooting](docs/operations/troubleshooting.md)** - Guía de diagnóstico y soluciones

### Integraciones

- **[Integraciones](docs/integrations/)** - Documentación de integraciones y contratos de APIs

### Pruebas

- **[Testing](docs/testing/)** - Documentación de pruebas y estrategias de testing

### Gestión de Proyecto

- **[Proyecto](docs/project/)** - Documentación de gestión de proyecto (alcance, objetivos, planificación, riesgos)

### Documentación Académica (TFM)

- **[Thesis](docs/thesis/)** - Documentación completa de la Tesis de Máster (múltiples archivos)

---

## 🚀 Instalación Rápida

### Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 16GB+ RAM recomendado (mínimo 8GB)
- 50GB+ SSD

### Pasos de Instalación

1. **Configurar Variables de Entorno**:
   ```bash
   # Generar .env.full desde .env.example con todos los secretos (incluido JWT)
   make generate-secrets
   # o manualmente
   python src/soar_lab/scripts/setup/generate_env.py
   ```
   Edita `.env.full` para ajustar puertos, hosts y credenciales.

2. **Iniciar el Stack Completo**:
   ```bash
   # Windows (make uses Makefile, which delegates to Makefile.win)
   make up
   # o
   make -f Makefile.win up
   ```

3. **Detener Servicios**:
   ```bash
   # Windows
   make down
   # o
   make -f Makefile.win down
   ```

### Servicios y Accesos

| Servicio              | URL                                    | Vía Nginx | Descripción                            |
|-----------------------|----------------------------------------|-----------|----------------------------------------|
| **Nginx Proxy**       | `https://soar.local`                   | —         | Proxy inverso HTTPS principal          |
| **Web Management UI** | `http://localhost:8085` / `/`        | Sí (/)    | Panel de gestión principal             |
| **API REST**          | `http://localhost:8000` / `/api/`    | Sí        | API de gestión del laboratorio         |
| **Shuffle UI**        | `http://localhost:8081`                | No        | Orquestador SOAR                       |
| **Shuffle API**       | `http://localhost:15001` / `/shuffle-api/` | Sí     | API REST de Shuffle                    |
| **TheHive**           | `http://localhost:19000` / `/thehive/`| Sí        | Gestión de casos e incidentes          |
| **Cortex**            | `http://localhost:19001` / `/cortex/` | Sí        | Análisis de IoCs y analyzers           |
| **MISP**              | `http://localhost:8083`                | No        | Inteligencia de amenazas               |
| **Grafana**           | `http://localhost:8084`                | No        | Dashboards de KPIs y logging           |
| **Wazuh Dashboard**   | `https://localhost:15601`               | No        | Dashboards y visualización de logs (TLS)     |
| **Docs Site**         | `http://localhost:8086`                | No        | Documentación Docusaurus               |
| **Elasticsearch**     | `http://localhost:19200`               | No        | Motor de búsqueda (puerto externo)     |
| **Wazuh Manager**     | `https://localhost:55100`              | No        | SIEM/XDR API                           |

> **Swagger/OpenAPI** de la API: `http://localhost:8000/docs` (o `https://soar.local/api/docs` a través de Nginx).

> Servicios marcados como *No* en la columna *Vía Nginx* usan SPA/assets absolutos o no soportan subpath proxy; accede a ellos directamente por puerto.

> **Nota Windows/Docker Desktop**: Los puertos de Wazuh API (55000) y Elasticsearch están bloqueados por rangos de
> exclusión de Hyper-V. Todos los servicios internos funcionan correctamente a través de la red Docker.

---

## 🔧 Automatización Opcional

### Lint de documentación

El target `make docs-lint` ejecuta las validaciones documentales antes de un commit:

- `markdownlint` sobre `docs/`
- `lychee` (comprobación de enlaces rotos)
- `src/soar_lab/scripts/ci/docs_quality.py` (calidad de docs, OpenAPI, tests)
- `pytest --collect-only` (verificación de la suite de pruebas)

Windows:
```powershell
make -f Makefile.win docs-lint
```

Linux/macOS:
```bash
make docs-lint
```

### Vagrant

```bash
# Crear entorno automatizado
make vagrant-up
# o directamente
vagrant up soar-ubuntu

# La VM Windows victima está deshabilitada por incompatibilidades
# (ver infra/vagrant/Vagrantfile)
```

> **Nota:** Ansible no está configurado en este repositorio.

---

## 🛡️ Buenas Prácticas

- No subir archivos `.env` ni certificados al repositorio (usar `.gitignore`)
- Documentar pruebas en `tests/e2e` y resultados en `docs/testing/test_suite.md`
- Utilizar TLS y credenciales seguras en todo momento
- Realizar copias de seguridad periódicas de la configuración
- Mantener actualizadas las dependencias y Docker images

---

## 📊 Métricas y Pruebas

### Ejecución de Pruebas

Para ejecutar pruebas, consultar la documentación completa en **[docs/testing/test_suite.md](docs/testing/test_suite.md)
**:

```bash
# Windows - Ejecutar todas las pruebas
make test-all
# o
make -f Makefile.win test-all

# Ejecutar categorías específicas (Windows)
make -f Makefile.win test-unit
make -f Makefile.win test-atomic
make -f Makefile.win test-security
make -f Makefile.win test-integration
make -f Makefile.win test-performance
make -f Makefile.win test-e2e

# Ejecutar con cobertura (mínimo 80% requerido)
make -f Makefile.win test-coverage

# Enviar alerta maliciosa de prueba
python src/soar_lab/infrastructure/messaging/send_alert.py --type malicious --single

# Enviar alerta benigna de prueba
python src/soar_lab/infrastructure/messaging/send_alert.py --type benign --single
```

**Estado Actual de Tests (v1.4.0):**

- Archivos de prueba (`test_*.py`): 157
  - Unit: 66 · Atomic: 4 · Integration: 36 · E2E: 44 · Security: 1 · Performance: 4 · General: 2
- Funciones definidas: ~1884
- Recolección reproducible (`python -m pytest --collect-only -q`): 1944 items / 33 deselected / 1911 seleccionados (0 errores de colección).
- Todos los errores previos de recolección (`ModuleNotFoundError`, `NameError`, `SyntaxError`) han sido resueltos.
- El desglose completo se mantiene en `docs/testing/test_suite.md` y `baseline/tests_inventory.json`.
- Última sincronización documental: 2026-07-18.

### Cálculo de KPIs

```bash
# Calcular métricas MTTR (Linux/Mac)
make metrics

# Calcular métricas MTTR (Windows)
make -f Makefile.win metrics

# Ver resultados
cat artifacts/results/kpis.csv
```

### Análisis de Datos

```bash
# Ver estado de datos disponibles
make data-status

# Generar análisis completo
make data-generate

# Ver todos los datos disponibles
make data-view

# Monitorear cambios en tiempo real
make data-watch
```

### Análisis de Resultados

- Documentar resultados en `artifacts/results/kpis.csv` y `docs/test_report.md`
- Verificar cumplimiento de umbrales: p50 ≤ 120s, p90 ≤ 180s
- Analizar logs de ejecución en `artifacts/logs/notify.log`
- Ver documentación completa de pruebas en **[docs/testing/test_suite.md](docs/testing/test_suite.md)**

---

## 🎓 Contexto Académico

Este laboratorio SOAR ha sido desarrollado como **Trabajo Fin de Máster** en el área de ciberseguridad, cumpliendo con
los siguientes objetivos académicos:

- **Aplicación Práctica**: Implementación de conceptos teóricos de SOAR en entorno realista
- **Investigación Aplicada**: Validación de la eficacia de la automatización en respuesta a incidentes
- **Innovación Tecnológica**: Desarrollo de un laboratorio reproducible para formación especializada
- **Contribución Académica**: Creación de recursos educativos reutilizables

---

## 🔗 Referencias Clave

### Documentación Oficial

- [TheHive Docker](https://docs.strangebee.com/thehive/installation/docker/)
- [Cortex Analyzers](https://docs.strangebee.com/cortex/)
- [Shuffle SOAR](https://shuffler.io/docs)

### Tecnologías Utilizadas

- [Docker Volumes](https://docs.docker.com/engine/storage/volumes/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres/)
- [Redis Docker](https://hub.docker.com/_/redis/)
- [Docker Compose](https://docs.docker.com/compose/)

---

## 📄 Licencia y Uso

Este proyecto está licenciado bajo los términos especificados en el archivo `LICENSE`. El uso académico y educativo está
fomentado, siempre que se cite adecuadamente la fuente.

---

**Autor**: [Nombre del Autor]  
**Director/a**: [Nombre del Director/a]  
**Universidad**: [Nombre de la Universidad]  
**Año Académico**: 2025-2026  
**Versión**: 1.4.0
