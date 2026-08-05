# Inventario de dominio, aplicación, interfaces e infraestructura

Este documento inventaria las clases y responsabilidades de las capas internas del proyecto, sirviendo de mapa rápido para
mantenedores y revisores.

## Domain Layer (`src/soar_lab/domain/`)

Responsabilidad: modelos de negocio, reglas puras, contratos de puertos y servicios del dominio.

| Archivo / Módulo | Responsabilidad principal |
|------------------|---------------------------|
| `models.py` | Entidades y value objects del dominio (`Alert`, `Observable`, `Case`, `KPI`, etc.) |
| `ports.py` | Contratos de puertos (driven/driving) para persistencia, mensajería, backups y KPIs |
| `ports/` | Submódulos organizados por categoría de puerto |
| `services/ioc_generator.py` | Generación de IoCs de ejemplo para tests y simulación |
| `services/kpi_analyzer.py` | Cálculo de MTTR, percentiles y métricas de respuesta |
| `services/statistical_calculator.py` | Utilidades estadísticas para comparaciones y tests |
| `value_objects/` | Objetos de valor inmutables usados por entidades |

## Application Layer (`src/soar_lab/application/`)

Responsabilidad: casos de uso, orquestación de dominio, coordinación de adaptadores.

| Archivo / Módulo | Responsabilidad principal |
|------------------|---------------------------|
| `use_cases/analytics_service.py` | Casos de uso de analytics y generación de KPIs |
| `use_cases/auth_service.py` | Casos de uso de autenticación (login, validación JWT) |
| `use_cases/backup_service.py` | Casos de uso de backup/restore |
| `dto/` | Objetos de transferencia de datos (DTOs) entre capas |

## Interface/API Layer (`src/soar_lab/interfaces/api/`)

Responsabilidad: exponer la aplicación como CLI y API REST.

| Archivo | Responsabilidad principal |
|---------|---------------------------|
| `main.py` | Aplicación FastAPI: endpoints REST, routers, health y wiring general |
| `composition.py` | `CompositionRoot` / `create_app`: creación y cableado de dependencias |
| `cli.py` | CLI nativo `soar-lab` (api, generate-secrets, generate-iocs, version) |
| `auth.py` | Dependencias de autenticación y autorización FastAPI |
| `dependencies.py` | Inyección de dependencias comunes para endpoints |
| `models.py` | Modelos Pydantic para request/response |
| `static/` | Recursos estáticos servidos por la API |
| `__init__.py` | Package init con exports y metadata del módulo API |

## Infrastructure Layer (`src/soar_lab/infrastructure/`)

Responsabilidad: implementar los puertos del dominio y conectar con sistemas externos.

| Archivo / Módulo | Responsabilidad principal |
|------------------|---------------------------|
| `external/` | Clientes HTTP de Elasticsearch, Shuffle, TheHive, Cortex, MISP, Wazuh |
| `messaging/` | Transporte de alertas (`send_alert.py`, `simulate_alerts.py`) |
| `monitoring/` | Health checks, `HealthService`, `SystemMetricsDriver`, `KPIAlertManager` |
| `network_watcher/` | Servicio para conectar workers de Shuffle a `soar_net` |
| `persistence/` | Implementaciones de repositorios (`SqliteAlertRepository`, `InMemoryAlertRepository`) |
| `persistence_backup/` | Respaldo de datos de persistencia |
| `scripts/` | Scripts auxiliares **legacy** (`patch.ps1`, `test_edge_cases.sh`, `test_performance.sh`) |
| `security/scan_vulnerabilities.sh` | Escaneo de vulnerabilidades en contenedores e imágenes |
| `security/setup_firewall.sh` | Configuración de reglas de firewall para el lab |
| `artifacts/` | Artefactos generados en runtime (p. ej. `webhook_info.json`) |
| `templates/` | Plantillas de configuración |
| `jwt_token_provider.py` | `JwtTokenProvider`: generación y validación de tokens JWT |
| `pytest_test_runner.py` | `PytestTestRunner`: ejecución remota de pruebas |
| `tar_backup_driver.py` | `TarBackupDriver`: copias de seguridad en tar |
| `validate_credentials.py` | Validación de credenciales de servicios externos |
| `websocket_manager.py` | Gestión de WebSockets para logs y eventos en tiempo real |
| `config_provider.py` | Proveedor centralizado de configuración basado en variables de entorno |
| `filesystem_storage.py` | Almacenamiento basado en filesystem |
| `in_memory_storage.py` | Almacenamiento en memoria para tests |
| `log_parser.py` | Parsing de logs de ejecución |
| `kpi_formatter.py` | Formateo de resultados de KPI |
| `file_log_reader.py` | Lectura de archivos de log para análisis |
| `subprocess_runner.py` | Ejecución de subprocesos con manejo de salida |
| `cleanup_service.py` | Limpieza de artefactos temporales |
| `path_service.py` | Utilidades de resolución de rutas |
| `checksum_utils.py` | Cálculo y verificación de checksums |
| `http_client.py` | Cliente HTTP reutilizable |
| `clients.py` | Fábricas de clientes externos |
| `pytest_output_parser.py` | Parser de salida de pytest |

## Notas de coherencia

- `src/soar_lab/interfaces/api/models.py` contiene los modelos Pydantic de la API REST; los modelos de negocio viven en
  `src/soar_lab/domain/models.py`.
- Los servicios `analytics_service.py` y `auth_service.py` en `application/use_cases/` actúan como fachadas que
  orquestan adaptadores de infraestructura; las implementaciones finales están en `infrastructure/`.
- `infrastructure/security/` contiene únicamente scripts de hardening; no contiene lógica de aplicación Python.
- `infrastructure/scripts/` está marcado como **legacy**; para scripts canónicos ver `src/soar_lab/scripts/`.
