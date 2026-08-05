# Estructura del Código Fuente

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Visión general de `src/soar_lab`](#2-visión-general-de-srcsoar_lab)
- [3. Domain Layer](#3-domain-layer)
- [4. Application Layer](#4-application-layer)
- [5. Infrastructure Layer](#5-infrastructure-layer)
- [6. Interface Layer](#6-interface-layer)
- [7. Código compartido](#7-código-compartido)
- [8. Scripts y simulador](#8-scripts-y-simulador)
- [9. Referencias](#9-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe la organización del código fuente en `src/soar_lab/` siguiendo una arquitectura hexagonal
(ports and adapters). El objetivo es separar la lógica de negocio pura de los detalles de infraestructura e interfaces.

### 1.2 Contexto

Tras la refactorización, el código se reorganizó en cuatro capas principales:

- **Domain** — Lógica de negocio pura e interfaces abstractas.
- **Application** — Casos de uso y orquestación de servicios.
- **Infrastructure** — Implementaciones concretas, adaptadores y clientes externos.
- **Interfaces** — Puntos de entrada (API REST, CLI, webhooks).

---

## 2. Visión general de `src/soar_lab`

```
src/soar_lab/
├── __init__.py
├── application/              # Capa de aplicación
│   ├── dto/                  # Objetos de transferencia (DTOs)
│   └── use_cases/            # analytics_service, auth_service, backup_service, etc.
├── common/                   # Excepciones y utilidades compartidas
├── config/                   # Configuración, esquemas y logging
├── data/                     # Esquemas y utilidades de datos
├── domain/                   # Capa de dominio
│   ├── models.py             # Entidades: IOC, Alert, Case
│   ├── ports/                # Protocolos (repositories, integrations, infrastructure)
│   ├── ports.py              # Protocolos alternativos/concentrados
│   ├── services/             # kpi_analyzer, ioc_generator
│   ├── statistical_calculator.py  # Cálculos estadísticos puros
│   └── value_objects/
├── infrastructure/           # Capa de infraestructura
│   ├── artifacts/            # Artefactos generados en runtime
│   ├── external/             # Clientes externos (Shuffle, TheHive, Cortex, MISP, Wazuh)
│   ├── messaging/            # Envío de alertas
│   ├── monitoring/           # Health checks, HealthService, SystemMetricsDriver, KPIAlertManager
│   ├── network_watcher/      # Conectividad dinámica de workers Shuffle
│   ├── persistence/          # Repositorios (SQLite, InMemory)
│   ├── persistence_backup/   # Respaldo de datos de persistencia
│   ├── scripts/              # Scripts auxiliares (patch, edge cases, performance)
│   ├── security/             # Scripts de hardening
│   ├── templates/            # Plantillas de configuración
│   ├── utils/                # Utilidades de archivos
│   ├── jwt_token_provider.py # Generación y validación de tokens JWT
│   ├── pytest_test_runner.py # Ejecución remota de pruebas
│   ├── tar_backup_driver.py  # Driver de backups en tar
│   └── validate_credentials.py # Validación de credenciales de servicios
├── interfaces/               # Capa de interfaces
│   └── api/                  # FastAPI: routes, dependencies, models, auth, cli, composition
├── scripts/                  # Scripts del laboratorio
│   ├── debug/                # Scripts de depuración
│   ├── maintenance/          # Scripts de mantenimiento
│   ├── setup/                # Scripts de inicialización y despliegue
│   ├── generate_kpi_data.py
│   ├── send_to_both_workflows.py
│   ├── send_wazuh_alert.py
│   └── test_service.py
├── simulator/                # Simulador de alertas SIEM
└── validation/               # Validadores
```

### 2.1 Correspondencia puertos → adaptadores

Tabla one-to-one entre los protocolos del dominio y sus implementaciones concretas en infraestructura. Cada fila muestra el contrato (puerto), el adaptador que lo materializa y el archivo principal.

| Puerto (Protocol) | Definición | Adaptador / Implementación | Archivo principal |
|---|---|---|---|
| `AlertRepository` | `domain/ports/repositories.py` | `SqliteAlertRepository`, `InMemoryAlertRepository` | `infrastructure/persistence/sqlite_alert_repository.py`, `infrastructure/in_memory_alert_repository.py` |
| `BackupDriver` | `domain/ports/infrastructure.py` | `TarBackupDriver` | `infrastructure/tar_backup_driver.py` |
| `StorageProvider` | `domain/ports/infrastructure.py` | `FilesystemStorage` | `infrastructure/filesystem_storage.py` |
| `TestRunner` | `domain/ports/infrastructure.py` | `PytestTestRunner` | `infrastructure/pytest_test_runner.py` |
| `TestResultParserInterface` | `domain/ports/infrastructure.py` | `PytestOutputParser` | `infrastructure/pytest_output_parser.py` |
| `ConfigProvider` | `domain/ports/infrastructure.py` | `InfrastructureConfigProvider` | `infrastructure/config_provider.py` |
| `TokenProviderInterface` | `domain/ports/infrastructure.py` | `JWTTokenProvider` | `infrastructure/jwt_token_provider.py` |
| `HTTPClient` | `domain/ports/infrastructure.py` | `AioHTTPClient` | `infrastructure/http_client.py` |
| `SyncHTTPClient` | `domain/ports/infrastructure.py` | `BaseHTTPClient` | `infrastructure/external/integrations/base_client.py` |
| `WebSocketManager` | `domain/ports/infrastructure.py` | `ConnectionManager` | `infrastructure/websocket_manager.py` |
| `SystemMetricsInterface` | `domain/ports/infrastructure.py` | `SystemMetricsDriver` | `infrastructure/monitoring/system_metrics_driver.py` |
| `HealthCheckInterface` | `domain/ports/infrastructure.py` | `HTTPHealthCheckAdapter`, `HealthService` | `infrastructure/monitoring/health_check_adapter.py`, `infrastructure/monitoring/health_service.py` |
| `SubprocessRunner` | `domain/ports/infrastructure.py` | `SubprocessRunner` | `infrastructure/subprocess_runner.py` |
| `LogReader` | `domain/ports/infrastructure.py` | `FileLogReader` | `infrastructure/file_log_reader.py` |
| `LogParser` | `domain/ports/infrastructure.py` | `LogParser` | `infrastructure/log_parser.py` |
| `KPIFormatter` | `domain/ports/infrastructure.py` | `KpiFormatter` | `infrastructure/kpi_formatter.py` |
| `ChecksumService` | `domain/ports/infrastructure.py` | `ChecksumUtils` | `infrastructure/checksum_utils.py` |
| `CacheInterface` | `domain/ports/infrastructure.py` | `Redis` client wrapper | `infrastructure/clients.py` |
| `PathProviderInterface` | `domain/ports/infrastructure.py` | `PathService` | `infrastructure/path_service.py` |
| `FileSystemInterface` | `domain/ports/infrastructure.py` | `FilesystemStorage` | `infrastructure/filesystem_storage.py` |
| `IOCGenerator` | `domain/ports/integrations.py` | `IOCGenerator` | `domain/services/ioc_generator.py` |
| `AlertTransporter` | `domain/ports/integrations.py` | `HttpAlertSender` | `infrastructure/messaging/http_alert_sender.py` |
| `ShuffleClient`, `TheHiveClient`, `CortexClient`, `MISPClient`, `ElasticsearchClient`, `WazuhClient` | `external/integrations/` | Clientes HTTP externos | `infrastructure/external/integrations/shuffle_client.py`, `thehive_client.py`, `cortex_client.py`, `misp_client.py`, `elasticsearch_client.py`, `wazuh_client.py` |

> Nota: el dominio depende únicamente de los protocolos (`Protocol`). El `CompositionRoot` (`src/soar_lab/interfaces/api/composition.py`) es el único lugar donde se inyectan las implementaciones reales, manteniendo la independencia de capas.

### 2.2 Paquetes auxiliares en la raíz de `src/soar_lab/`

Además de las cuatro capas hexagonales, el código fuente contiene paquetes de conveniencia y soporte:

| Paquete | Contenido destacado | Responsabilidad |
|---|---|---|
| `api/` | `main.py`, `composition.py`, `cli.py` | Re-exporta `create_app`, `CompositionRoot` y `main` desde `interfaces/api/` para el entrypoint `soar-lab` y la imagen Docker. |
| `analytics/` | `metrics.py` | `MetricsExporter` (stub/plantilla para exportación de métricas). |
| `auth/` | `service.py`, `models.py` | Re-exporta `AuthService` y modelos de autenticación desde `application/use_cases/auth_service.py`. |
| `common/` | `exceptions.py` | Excepciones base compartidas por todas las capas. |
| `config/` | `settings.py`, `schemas.py`, `logging.yaml` | Configuración central, Pydantic settings y logging. |
| `data/` | esquemas y utilidades | Esquemas de datos y helpers de transformación. |
| `db/` | `transaction.py` | `Transaction` / `TransactionManager` (plantilla para unidad de trabajo). |
| `logging/` | `structured.py` | `StructuredLogger` wrapper sobre `logging`. |
| `resilience/` | `circuit_breaker.py`, `retry.py`, `timeout.py` | Patrones de tolerancia a fallos (reintentos, circuit breaker, timeouts). |
| `security/` | `sanitization.py` | `PayloadSanitizer` para saneamiento básico de entradas. |
| `validation/` | `validators.py` | Validadores centralizados (IP, hash, rutas, alertas). |

---

## 3. Domain Layer

Ubicación: `src/soar_lab/domain/`

Responsabilidad: Contener la lógica de negocio pura sin dependencias externas.

| Módulo | Propósito |
|--------|-----------|
| `models.py` | Entidades de dominio (`IOC`, `Alert`, `Case`) con validación |
| `ports/repositories.py` | Protocolos de repositorios (`AlertRepository`, `CaseRepository`, etc.) |
| `ports/infrastructure.py` | Protocolos de infraestructura (`ConfigProvider`, `HTTPClient`, etc.) |
| `ports/integrations.py` | Protocolos de integraciones (`IOCGenerator`, `AlertTransporter`) |
| `ports.py` | Protocolos alternativos/concentrados del dominio |
| `services/kpi_analyzer.py` | Cálculo de métricas KPI |
| `services/ioc_generator.py` | Generación de IOCs simulados |
| `statistical_calculator.py` | Cálculos estadísticos puros |

---

## 4. Application Layer

Ubicación: `src/soar_lab/application/`

Responsabilidad: Orquestar casos de uso utilizando los puertos del dominio.

| Módulo | Propósito |
|--------|-----------|
| `dto/` | Objetos de transferencia entre capas |
| `use_cases/analytics_service.py` | Cálculo y exportación de estadísticas y KPIs |
| `use_cases/auth_service.py` | Autenticación JWT y verificación de credenciales |
| `use_cases/backup_service.py` | Creación, listado y restauración de backups |

---

## 5. Infrastructure Layer

Ubicación: `src/soar_lab/infrastructure/`

Responsabilidad: Implementar los puertos del dominio y conectar con sistemas externos.

| Módulo | Propósito |
|--------|-----------|
| `external/` | Clientes HTTP de Elasticsearch, Shuffle, TheHive, Cortex, MISP, Wazuh |
| `messaging/` | Transporte de alertas (`send_alert.py`, `simulate_alerts.py`) |
| `monitoring/` | Health checks, `HealthService`, `SystemMetricsDriver`, `KPIAlertManager` |
| `network_watcher/` | Servicio para conectar workers de Shuffle a `soar_net` |
| `persistence/` | Implementaciones de repositorios (`SqliteAlertRepository`, `InMemoryAlertRepository`) |
| `persistence_backup/` | Respaldo de datos de persistencia |
| `scripts/` | Scripts auxiliares **legacy** (`patch.ps1`, `test_edge_cases.sh`, `test_performance.sh`). Se mantienen por compatibilidad; los scripts canónicos vivos están en `src/soar_lab/scripts/` (setup, debug, maintenance). |
| `security/` | Scripts de hardening: `scan_vulnerabilities.sh`, `setup_firewall.sh` |
| `artifacts/` | Artefactos generados en runtime (p. ej. `webhook_info.json`) |
| `templates/` | Plantillas de configuración |
| `utils/` | Utilidades de archivos |
| `jwt_token_provider.py` | `JwtTokenProvider`: generación y validación de tokens JWT |
| `pytest_test_runner.py` | `PytestTestRunner`: ejecución remota de pruebas |
| `tar_backup_driver.py` | `TarBackupDriver`: copias de seguridad en tar |
| `validate_credentials.py` | Validación de credenciales de servicios externos |

---

## 6. Interface Layer

Ubicación: `src/soar_lab/interfaces/`

Responsabilidad: Exponer la funcionalidad al exterior.

| Módulo | Propósito |
|--------|-----------|
| `api/composition.py` | `CompositionRoot` y `create_app`: cableado de dependencias de la app FastAPI |
| `api/main.py` | Aplicación FastAPI principal con todos los endpoints REST |
| `api/cli.py` | CLI nativo `soar-lab` (api, generate-secrets, generate-iocs, version) |
| `api/models.py` | Modelos Pydantic para request/response |
| `api/auth.py` | Dependencias de autenticación |

---

## 7. Código compartido

| Módulo | Propósito |
|--------|-----------|
| `common/` | Excepciones y utilidades compartidas |
| `config/` | `settings.py`, `logging.py`, `schemas.py` |
| `data/` | Esquemas de datos y utilidades |
| `validation/` | Validadores reutilizables |

---

## 8. Scripts y simulador

| Módulo | Propósito |
|--------|-----------|
| `scripts/` | Scripts del laboratorio: `setup/`, `debug/`, `maintenance/`, generación de KPI/alertas, tests |
| `simulator/simulate_alerts.py` | Simulador de alertas SIEM para pruebas (genera y envía payloads al webhook de Shuffle) |

---

## 9. Referencias

- [Arquitectura hexagonal](hexagonal-structure.md)
- [Arquitectura general del sistema](overview.md)
- [Aplicaciones del proyecto](applications.md)
- [Composition Root](composition_root.md)
- [Guía de infraestructura](../operations/infrastructure_guide.md)
