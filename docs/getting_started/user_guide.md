
# Guía de Usuario — SOAR Ransomware Lab

## Acceso a Servicios

| Servicio       | URL                    | Credenciales                                            |
|----------------|------------------------|---------------------------------------------------------|
| Web Management | https://localhost      | Ver `.env.full` → `WEB_UI_USER` / `WEB_UI_PASSWORD`     |
| SOAR API       | http://localhost:8000  | Token en cabecera `Authorization: Bearer <token>`       |
| Shuffle UI     | http://localhost:8081  | `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD` |
| MISP           | http://localhost:8083  | `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD`              |
| Grafana        | http://localhost:8084  | `admin` / `GrafanaLab2024Secure`                        |
| Docs Site      | http://localhost:8086  | Sin autenticación                                        |
| TheHive        | http://localhost:19000 | `THEHIVE_ADMIN_USER` / `THEHIVE_ADMIN_PASSWORD`        |
| Cortex         | http://localhost:19001 | `CORTEX_ADMIN_USER` / `CORTEX_ADMIN_PASSWORD`          |
| Kibana/Wazuh   | http://localhost:15601 | `admin` / `WAZUH_API_PASSWORD`                          |

## Comandos principales

```bash
# Levantar el entorno
make up

# Parar el entorno
make down

# Reset completo (destruye y recrea)
make reset && make up

# Ver estado de contenedores
make ps

# Simular alerta de ransomware
make simulate

# Calcular KPIs
make metrics

# Ejecutar tests E2E
make test-all
```

## Flujo de uso básico

1. `make up` — levanta todos los servicios (~5-10 min en primer arranque)
2. Acceder a http://localhost:8085 (Web Management) para verificar estado
3. `make simulate` — envía alertas de prueba al SOAR
4. Verificar en TheHive (http://localhost:19000) que se han creado casos
5. Verificar en Grafana (http://localhost:8084) los KPI dashboards
6. `make metrics` — genera `artifacts/results/kpis.csv` con métricas

## Interfaces del Sistema

### Web Management
**URL:** http://localhost:8085  
**Credenciales:** Ver `.env.full` → `WEB_UI_USER` / `WEB_UI_PASSWORD`  
**Descripción:** Interfaz web principal para gestión del entorno SOAR. Permite verificar el estado de todos los servicios, ver logs en tiempo real, gestionar alertas y monitorear la salud del sistema. Proporciona una vista consolidada de toda la infraestructura SOAR.

**Características principales:**
- Dashboard con estado de todos los servicios (healthy/unhealthy)
- Visualización de logs en tiempo real por servicio
- Gestión de alertas enviadas al sistema
- Métricas de rendimiento y disponibilidad
- Configuración de parámetros del entorno

**Captura pendiente:** docs/img/web_management_dashboard.png

### SOAR API
**URL:** http://localhost:8000  
**Credenciales:** Token en cabecera `Authorization: Bearer <token>`  
**Descripción:** API REST principal del sistema. Proporciona endpoints programáticos para envío de alertas, consulta de métricas, gestión de casos, integración con servicios externos y más. Permite la automatización de operaciones SOAR mediante llamadas HTTP.

**Endpoints principales:**
- `POST /alert` - Envío de alertas al sistema SOAR
- `GET /health` - Verificación de salud del servicio API
- `GET /metrics` - Consulta de métricas del sistema
- `POST /backup/create` - Creación de backups
- `POST /backup/restore` - Restauración de backups
- Documentación Swagger disponible en `/docs`

**Captura pendiente:** docs/img/api_swagger.png

### TheHive
**URL:** http://localhost:19000  
**Credenciales:** `THEHIVE_ADMIN_USER` / `THEHIVE_ADMIN_PASSWORD`  
**Descripción:** Plataforma de gestión de casos de seguridad (SIRP - Security Incident Response Platform). Permite crear, investigar, asignar y cerrar casos de incidentes de seguridad. Integra automáticamente alertas del sistema SOAR y proporciona herramientas para la colaboración entre equipos de respuesta a incidentes.

**Características principales:**
- Gestión de casos de seguridad con estados (Open, In Progress, Resolved, Closed)
- Asignación de casos a usuarios y equipos
- Observables (IOCs) enlazados a casos
- Integración con Cortex para análisis de amenazas
- Timeline de actividades en cada caso
- Alertas automáticas desde Shuffle workflows
- Búsqueda avanzada de casos y observables

**Configuración inicial:**
1. Crear usuario administrador  
   ![TheHive - Crear administrador](img/thehive_create_admin.png)
2. Iniciar sesión  
   ![TheHive - Login](img/thehive_login.png)
3. Actualizar base de datos (si es necesario)  
   ![TheHive - Actualizar base de datos](img/thehive_update_database.png)
4. Generar API key  
   ![TheHive - API Key](img/thehive_apikey.png)
5. Dashboard principal  
   ![TheHive - Dashboard](img/thehive_dashboard.png)

### Cortex
**URL:** http://localhost:19001  
**Credenciales:** `CORTEX_ADMIN_USER` / `CORTEX_ADMIN_PASSWORD`  
**Descripción:** Plataforma de análisis de amenazas (TIAM - Threat Intelligence Analysis Module). Permite ejecutar analizadores sobre IOCs (Indicators of Compromise) para obtener información de inteligencia de amenazas. Integra automáticamente con TheHive para enriquecer casos con análisis de observables.

**Características principales:**
- Ejecución de analizadores sobre diferentes tipos de IOCs (IP, dominio, hash, URL, email)
- Integración con servicios de inteligencia de amenazas (VirusTotal, AlienVault, etc.)
- Resultados de análisis enlazados a casos en TheHive
- Gestión de analizadores y configuración de API keys externas
- Historial de análisis realizados
- Soporte para analizadores personalizados

**Configuración inicial:**
1. Crear usuario administrador  
   ![Cortex - Crear administrador](img/cortex_create_admin.png)
2. Iniciar sesión  
   ![Cortex - Login](img/cortex_login.png)
3. Actualizar base de datos (si es necesario)  
   ![Cortex - Actualizar base de datos](img/cortex_update_database.png)
4. Dashboard principal  
   ![Cortex - Dashboard](img/cortex_dashboard.png)

### Shuffle
**URL:** http://localhost:8081  
**Credenciales:** `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD`  
**Descripción:** Plataforma de automatización de seguridad (SOAR - Security Orchestration, Automation and Response). Permite crear workflows de respuesta automatizada a incidentes de seguridad mediante una interfaz visual drag-and-drop. Integra automáticamente con TheHive, Cortex, MISP, Wazuh y otros servicios del ecosistema SOAR.

**Características principales:**
- Editor visual de workflows drag-and-drop
- Integración con múltiples servicios (TheHive, Cortex, MISP, Wazuh, Elasticsearch, etc.)
- Ejecución de workflows basada en triggers (webhooks, alertas, schedules)
- Apps predefinidas para operaciones comunes (HTTP, Python, Email, Slack, etc.)
- Variables y condiciones para lógica compleja
- Historial de ejecuciones de workflows
- Workflows preconfigurados para respuesta a ransomware

**Configuración inicial:**
1. Iniciar sesión  
   ![Shuffle - Login](img/shuffle_login.png)

**Capturas pendientes:**
- docs/img/shuffle_dashboard.png
- docs/img/shuffle_workflow_editor.png
- docs/img/shuffle_workflow_execution.png

### MISP
**URL:** http://localhost:8083  
**Credenciales:** `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD`  
**Descripción:** Plataforma de inteligencia de amenazas (Threat Intelligence Platform). Permite compartir y consultar IOCs (Indicators of Compromise) con la comunidad de seguridad. Integra automáticamente con Shuffle workflows para enriquecer alertas con inteligencia de amenazas y verificar IOCs contra bases de datos de amenazas conocidas.

**Características principales:**
- Gestión de eventos de amenazas con IOCs
- Sincronización con feeds de inteligencia de amenazas externos
- Enrichment automático de IOCs con información de múltiples fuentes
- Integración con Shuffle para verificación de IOCs en workflows
- API para consulta de IOCs desde otros servicios
- Gestión de organizaciones y permisos de compartición
- Soporte para diferentes tipos de IOCs (IP, dominio, hash, email, URL, etc.)

**Capturas pendientes:**
- docs/img/misp_login.png
- docs/img/misp_dashboard.png
- docs/img/misp_create_event.png

### Grafana
**URL:** http://localhost:8084  
**Credenciales:** `admin` / `GrafanaLab2024Secure`  
**Descripción:** Plataforma de visualización de métricas. Permite crear dashboards con KPIs del sistema SOAR. Integra automáticamente con Elasticsearch para visualizar métricas de alertas procesadas, tiempos de respuesta, tasas de éxito y más. Proporciona visualizaciones en tiempo real del rendimiento y salud del sistema SOAR.

**Características principales:**
- Dashboard SOAR KPI con métricas clave del sistema
- Visualización de alertas procesadas por tipo y severidad
- Gráficas de MTTR (Mean Time To Respond) por tipo de alerta
- Tasa de éxito por severidad de alerta
- Evolución temporal de alertas por tipo
- Integración con Elasticsearch como datasource
- Alertas y notificaciones basadas en umbrales
- Exportación de dashboards y configuraciones

**Capturas pendientes:**
- docs/img/grafana_login.png
- docs/img/grafana_kpi_dashboard.png
- docs/img/grafana_datasources.png

### Kibana/Wazuh
**URL:** http://localhost:15601  
**Credenciales:** `admin` / `WAZUH_API_PASSWORD`  
**Descripción:** Plataforma de análisis de logs y seguridad. Kibana proporciona una interfaz para visualizar y analizar logs de todos los servicios del sistema SOAR. Wazuh es una plataforma de seguridad que integra detección de amenazas, respuesta a incidentes y monitoreo de integrididad de archivos. Juntos proporcionan visibilidad completa de la seguridad del entorno.

**Características principales:**
- Visualización de logs de todos los servicios SOAR en tiempo real
- Dashboards preconfigurados de Wazuh para seguridad
- Reglas de detección de amenazas y alertas
- Monitoreo de integrididad de archivos (FIM)
- Detección de intrusiones y vulnerabilidades
- Integración con Elasticsearch para almacenamiento de logs
- Búsqueda avanzada y filtrado de logs
- Alertas y notificaciones de seguridad

**Capturas pendientes:**
- docs/img/kibana_login.png
- docs/img/kibana_dashboard.png
- docs/img/wazuh_dashboard.png

### Verificación de Contenedores Docker
**Comando:** `make ps` o `docker ps --filter name=soar_`  
**Descripción:** Verificación del estado de todos los contenedores Docker del proyecto.

![Docker - Contenedores healthy](img/docker_ps_healthy.png)

## Uso del Sistema con Comandos Makefile

### Inicio y Parada del Entorno

```bash
# Levantar todos los servicios
make up

# Verificar estado de contenedores
make ps

# Verificar health de servicios core
make health

# Ver logs de servicios en tiempo real
make logs

# Reiniciar todos los servicios
make restart

# Parar servicios y eliminar volúmenes
make down

# Reset completo (destruye y recrea)
make reset && make up
```

### Simulación de Alertas

```bash
# Simular 5 alertas de ransomware (por defecto)
make simulate

# Enviar 1 alerta maliciosa
make simulate-malicious

# Enviar 1 alerta benigna
make simulate-benign

# Enviar N alertas (ejemplo: 10)
make simulate-batch N=10
```

### Gestión de Métricas

```bash
# Calcular KPIs desde logs
make metrics

# Ver resultados en artifacts/results/kpis.csv
```

### Ejecución de Tests

```bash
# Ejecutar tests unitarios
make test-unit

# Ejecutar tests de integración
make test-integration

# Ejecutar tests E2E
make test-e2e

# Ejecutar TODOS los tests
make test-all

# Ejecutar tests con coverage report
make test-coverage
```

### Mantenimiento

```bash
# Limpiar archivos temporales
make clean

# Limpiar todos los artifacts
make clean-full

# Limpiar artifacts + recursos Docker
make clean-all

# Crear backup de artifacts
make backup

# Restaurar desde backup
make restore BACKUP=<nombre_del_backup>

# Validar sincronización de credenciales
make validate-credentials

# Generar certificados TLS para Nginx
make certs

# Generar contraseñas/tokens seguros
make generate-secrets
```

### Inicialización de Webhook

```bash
# Inicializar Shuffle webhook para alertas
make init-webhook
```

## Vagrant (entorno alternativo)

```bash
# Levantar VM Ubuntu con el stack completo
make vagrant-up

# Simular alertas desde la VM
make vagrant-simulate

# Destruir la VM
make vagrant-down
```

Los puertos Vagrant se mapean en rango 9000-9443 para evitar conflictos con el stack Docker:

- https://localhost:9443 — Web Management / Nginx
- http://localhost:9081 — Shuffle UI
- http://localhost:9001 — Shuffle API
