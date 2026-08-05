# Composition Root

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Ubicación](#2-ubicación)
- [3. Responsabilidades](#3-responsabilidades)
- [4. Componentes cableados](#4-componentes-cableados)
- [5. Cómo añadir un nuevo adaptador](#5-cómo-añadir-un-nuevo-adaptador)
- [6. Ejemplo de flujo](#6-ejemplo-de-flujo)
- [7. Referencias](#7-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe el **Composition Root** del proyecto: el punto único donde se instancian y conectan las
dependencias de la aplicación siguiendo el patrón de arquitectura hexagonal.

### 1.2 Contexto

En arquitectura hexagonal, el dominio define puertos (interfaces) y la infraestructura proporciona adaptadores
(implementaciones). El Composition Root es el único lugar con permiso para conocer ambos lados y cablearlos juntos.
Esto garantiza que el dominio y la aplicación permanezcan independientes de detalles técnicos.

---

## 2. Ubicación

**Archivo:** `src/soar_lab/interfaces/api/composition.py`

**Clase principal:** `CompositionRoot`

**Factory pública:** `create_app()` — crea y configura la aplicación FastAPI con todas las dependencias resueltas.

---

## 3. Responsabilidades

El `CompositionRoot` realiza las siguientes tareas:

1. **Configuración:** Carga ajustes mediante `create_settings()` y `InfrastructureConfigProvider`.
2. **Logging:** Inicializa el sistema de logging con `setup_logging()`.
3. **Directorios:** Garantiza que los directorios necesarios existen a través de `PathService`.
4. **Adaptadores de infraestructura:** Crea repositorios, clientes HTTP, almacenamiento, etc.
5. **Servicios de dominio:** Instancia `KPIAnalyzer` y `StatisticalCalculator`.
6. **Servicios de aplicación:** Crea `AnalyticsService`, `AuthService`, `BackupService` y `TestService`.
7. **Clientes utilitarios:** Crea `docker_client` y `redis_client`.
8. **Integración externa:** Inicializa clientes para Shuffle, TheHive, Cortex, MISP, Elasticsearch y Wazuh.
9. **Aplicación FastAPI:** Construye la API con `create_app()` y le inyecta todas las dependencias.

---

## 4. Componentes cableados

| Componente | Tipo | Rol |
|------------|------|-----|
| `InfrastructureConfigProvider` | Adaptador de config | Lee variables de entorno y `.env.full` |
| `PathService` | Utilidad | Resuelve rutas del proyecto y crea directorios |
| `FilesystemStorage` | Adaptador de almacenamiento | Acceso a archivos del sistema |
| `SqliteAlertRepository` | Adaptador de persistencia | Almacena alertas en SQLite |
| `AioHTTPClient` | Adaptador HTTP | Cliente HTTP asíncrono |
| `HTTPHealthCheckAdapter` | Adaptador de health | Realiza health checks HTTP |
| `SystemMetricsDriver` | Adaptador de métricas | Recolecta CPU, RAM, disco |
| `JWTTokenProvider` | Adaptador de seguridad | Genera y valida tokens JWT |
| `TarBackupDriver` | Adaptador de backup | Crea backups comprimidos |
| `ConnectionManager` (`websocket_manager.py`) | Adaptador WebSocket | Gestiona conexiones WS para logs |
| `Docker Client` | Cliente utilitario | Interacción con Docker |
| `Redis Client` | Cliente utilitario | Conexión a Redis |
| `KPIAnalyzer` | Servicio de dominio | Calcula métricas KPI |
| `StatisticalCalculator` | Servicio de dominio | Cálculos estadísticos |
| `AnalyticsService` | Servicio de aplicación | Orquesta analytics y exportación |
| `AuthService` | Servicio de aplicación | Autenticación JWT |
| `BackupService` | Servicio de aplicación | Crea, lista y restaura backups |
| `TestService` | Servicio de aplicación | Ejecuta tests y parsea resultados |
| `HealthService` | Servicio de aplicación | Verifica salud de todos los servicios |
| `ShuffleClient` | Cliente externo | Integración con Shuffle SOAR |
| `TheHiveClient` | Cliente externo | Integración con TheHive |
| `CortexClient` | Cliente externo | Integración con Cortex |
| `MISPClient` | Cliente externo | Integración con MISP |
| `ElasticsearchClient` | Cliente externo | Integración con Elasticsearch |
| `WazuhClient` | Cliente externo | Integración con Wazuh |

---

## 5. Cómo añadir un nuevo adaptador

Para añadir una nueva dependencia sin romper la arquitectura:

1. Define un **puerto** en `src/soar_lab/domain/ports/` (Protocol).
2. Implementa el **adaptador** en `src/soar_lab/infrastructure/`.
3. Registra el adaptador en `CompositionRoot.__init__()`.
4. Inyecta el adaptador en el servicio de aplicación o dominio correspondiente.
5. Expón el servicio a `create_app()` si debe usarse desde la API.

---

## 6. Ejemplo de flujo

```python
# Punto de entrada de la aplicación
from soar_lab.interfaces.api.composition import create_app

app = create_app()
```

Dentro de `CompositionRoot`:

1. Se crea `settings` y `config_provider`.
2. Se instancian `SqliteAlertRepository`, `SystemMetricsDriver`, `AioHTTPClient`.
3. Se crea `AnalyticsService` con `KPIAnalyzer` y `StatisticalCalculator`.
4. Se crean los clientes utilitarios (`docker_client`, `redis_client`) y los clientes externos (Shuffle, TheHive, Cortex, MISP, Elasticsearch, Wazuh).
5. Se construye `create_app(...)` y se le pasan todas las dependencias.

---

## 7. Referencias

- [Arquitectura general](overview.md)
- [Estructura del código fuente](code_structure.md)
- [Arquitectura hexagonal](hexagonal-structure.md)
- [src/soar_lab/interfaces/api/composition.py](/src/soar_lab/interfaces/api/composition.py)
