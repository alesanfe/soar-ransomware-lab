# Guía de Usuario del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
  - [2.1 Qué cubre](#21-qué-cubre)
  - [2.2 Límites](#22-límites)
  - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Instalación y configuración inicial](#31-instalación-y-configuración-inicial)
  - [3.2 Uso básico y flujo de trabajo](#32-uso-básico-y-flujo-de-trabajo)
  - [3.3 Funcionalidades avanzadas](#33-funcionalidades-avanzadas)
  - [3.4 Solución de problemas](#34-solución-de-problemas)
  - [3.5 Referencias rápidas](#35-referencias-rápidas)
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

Esta guía proporciona instrucciones paso a paso para instalar, configurar y utilizar el SOAR Ransomware Lab. Su objetivo es ayudar a los usuarios a comenzar con la plataforma y comprender sus características clave.

### 1.2 Contexto

El SOAR Ransomware Lab es una plataforma integral de orquestación, automatización y respuesta de seguridad diseñada para el manejo de incidentes de ransomware. Integra múltiples herramientas de seguridad (Shuffle, TheHive, Cortex, MISP, Wazuh, Kibana) en un entorno Docker Compose unificado para proporcionar capacidades de detección, análisis y respuesta automatizada.

## 2. Alcance

### 2.1 Qué cubre

Esta guía cubre:
- Requisitos previos de instalación
- Pasos de instalación y configuración inicial
- URLs de acceso a servicios y configuración de proxy
- Flujo de trabajo básico y características principales
- Configuración de variables de entorno y archivos de servicio
- Consideraciones de seguridad y mejores prácticas
- Solución de problemas comunes
- Uso avanzado (playbooks personalizados, integración API)
- Optimización de rendimiento y escalabilidad

### 2.2 Límites

Esta guía no cubre:
- Detalles de arquitectura técnica (ver docs/architecture/overview.md)
- Estrategias de seguridad detalladas (ver docs/architecture/security.md)
- Estrategias de Docker específicas (ver docs/architecture/docker_architecture.md)
- Planificación del proyecto (ver docs/project/)
- Estrategias de pruebas (ver docs/testing/)
- Implementación de código Python (ver src/soar_lab/)

### 2.3 Dependencias

Esta guía depende de:
- Documentación oficial de cada componente (Shuffle, TheHive, Cortex, MISP, Wazuh)
- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de seguridad (docs/architecture/security.md)
- Estrategia de Docker (docs/architecture/docker_architecture.md)

## 3. Contenido principal

### 3.1 Instalación y configuración inicial

#### Requisitos Previos

- Docker Engine 20.10+ y Docker Compose 2.0+
- Python 3.11+ 
- Git
- Al menos 16GB de RAM (mínimo 8GB)
- 50GB de espacio libre en disco SSD

#### Características Principales

**Gestión de Alertas:**
- Ingestión multi-fuente: TheHive, Cortex, APIs personalizadas
- Enriquecimiento de alertas: Extracción de IoCs, inteligencia de amenazas
- Scoring de prioridad: Evaluación automatizada de severidad
- Gestión de casos: Rastree incidentes desde detección hasta resolución

**Motor de Automatización:**
- Ejecución de playbooks: Procedimientos de respuesta automatizados
- Workflows personalizados: Cree sus propias secuencias de respuesta
- Soporte de integración: Conecte con herramientas de seguridad externas
- Programación: Tareas periódicas automatizadas y health checks

**Analytics y Reportes:**
- Dashboard de KPIs: Métricas en tiempo real e indicadores de rendimiento
- Análisis histórico: Análisis de tendencias y patrones de incidentes
- Reportes personalizados: Exporte datos en múltiples formatos
- Reportes de cumplimiento: Genere documentación lista para auditoría

**Características de Seguridad:**
- Control de acceso basado en roles: Permisos granulares
- Logging de auditoría: Rastreo completo de actividad
- Encriptación: Datos en reposo y en tránsito
- Aislamiento de red: Canales de comunicación seguros

### 3.2 Uso básico y flujo de trabajo

#### Pasos de Instalación

1. Clone el repositorio:
   ```bash
   git clone https://github.com/alesanfe/soar-ransomware-lab.git
   cd soar-ransomware-lab
   ```

2. Revise y edite la configuración del entorno:
   ```bash
   nano .env.full
   ```

3. Inicie el stack completo:
   ```bash
   make up
   ```

4. Verifique que todos los servicios estén saludables:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

#### Configuración Inicial

1. Acceda a TheHive en `http://localhost:9000` — credenciales de admin por defecto en `.env.full`
   - [Screenshot: TheHive dashboard principal mostrando lista de casos] - Capturar desde http://localhost:9000 tras login, mostrar vista de casos recientes con filtros de severidad
2. Acceda a Kibana en `http://localhost:15601` — configure patrones de índice para logs de Wazuh
   - [Screenshot: Kibana dashboard de Wazuh con gráficos de alertas] - Capturar desde http://localhost:15601/wazuh, mostrar dashboard principal con gráficos de alertas por tipo
3. Acceda a Shuffle en `http://localhost:3001` — importe o cree playbooks de respuesta
   - [Screenshot: Shuffle UI mostrando editor de workflows] - Capturar desde http://localhost:3001, mostrar editor visual de workflows con nodos de conexión
4. Acceda a MISP en `http://localhost:8082` — configure feeds de inteligencia de amenazas
   - [Screenshot: MISP event list mostrando eventos de amenazas] - Capturar desde http://localhost:8082/events, mostrar lista de eventos con indicadores de amenaza

#### Flujo de Trabajo Básico

1. **Ingestión de Alertas**: Reciba alertas de varias fuentes
2. **Análisis**: Analice alertas usando herramientas automatizadas
3. **Respuesta**: Ejecute playbooks de respuesta
4. **Reporte**: Genere reportes de incidentes

#### Configuración

**Variables de Entorno:**

Toda la configuración vive en `.env.full` en el directorio raíz del proyecto:

```bash
# Puertos de Servicios
THEHIVE_HTTP_PORT=9000
CORTEX_HTTP_PORT=9001
SHUFFLE_UI_PORT=3001
SHUFFLE_API_PORT=5001
WAZUH_DASHBOARD_PORT=15601   # Kibana
ELASTICSEARCH_PORT=9201      # Internal only on Docker Desktop/Windows
REDIS_PORT=6379
DOCS_PORT=3000
API_PORT=8000
HTTP_PORT=80
HTTPS_PORT=443
WEB_UI_PORT=8080

# Wazuh
WAZUH_EVENTS_PORT=1514

# Credentials (change before deploying!)
ELASTIC_PASSWORD=...
SHUFFLE_DEFAULT_PASSWORD=...
THEHIVE_SECRET=...
```

**Service Configuration Files:**

- **Nginx**: `infra/docker/nginx.conf`
- **Cortex**: `infra/docker/docker/cortex.application.conf`
- **TheHive**: configured via environment variables
- **Kibana**: configured via environment variables in `docker-compose.yml`
- **Elasticsearch**: configured via environment variables

**Custom Integrations:**

Add new integrations by:

#### Procedimientos Específicos de Configuración por Servicio

**Configuración de TheHive:**
```bash
# 1. Cambiar credenciales de admin por defecto
# Editar .env.full:
THEHIVE_ADMIN_USER=admin
THEHIVE_ADMIN_PASSWORD=ChangeMe!

# 2. Configurar organizaciones y usuarios
# Acceder a http://localhost:9000/#/administration/users
# Crear usuarios con roles: read, write, admin

# 3. Configurar analizadores de Cortex
# Acceder a http://localhost:9000/#/administration/analyzers
# Habilitar analyzers: FileInfo_8_0, DomainMailSPFRecord_2_1
```

**Configuración de Cortex:**
```bash
# 1. Configurar API keys para TheHive
# Editar .env.full:
THEHIVE_API_KEY=<generar desde TheHive UI>
CORTEX_API_KEY=<generar desde Cortex UI>

# 2. Configurar analyzers activos
# Editar .env.full:
MAX_CONCURRENT_ANALYZERS=3
ANALYZER_TIMEOUT=60

# 3. Habilitar analyzers específicos
# Acceder a http://localhost:9001/#/management/analyzers
# Habilitar: FileInfo, DomainMailSPFRecord, VirusTotal_2
```

**Configuración de Shuffle:**
```bash
# 1. Configurar API key para webhooks
# Editar .env.full:
SHUFFLE_DEFAULT_APIKEY=e18f1fe3-1591-44ec-aff4-c6e759b3a8bf
SIEM_WEBHOOK_TOKEN=SiemToken123!@#

# 2. Configurar URL del webhook
# Acceder a http://localhost:3001/#/apps
# Crear webhook: http://localhost:5001/api/v1/hooks/webhook

# 3. Importar playbook E2E
# Acceder a http://localhost:3001/#/workflows
# Importar desde: docs/operations/playbooks/ransomware_playbook_e2e.md
```

**Configuración de MISP:**
```bash
# 1. Cambiar credenciales por defecto
# Editar .env.full:
MISP_ADMIN_EMAIL=admin@admin.test
MISP_ADMIN_PASSPHRASE=ChangeMe!

# 2. Configurar feeds de inteligencia
# Acceder a http://localhost:8082/servers/index
# Añadir feeds: CIRCL, MISP-Project, VirusTotal

# 3. Configurar sincronización automática
# Acceder a http://localhost:8082/feeds/index
# Habilitar cron jobs para actualización cada 6 horas
```

**Configuración de Wazuh:**
```bash
# 1. Configurar API de Wazuh
# Editar .env.full:
WAZUH_API_USER=wazuh-wui
WAZUH_API_PASSWORD=ChangeMe!

# 2. Configurar reglas de detección
# Editar infra/docker/wazuh/rules/local_rules.xml
# Añadir reglas específicas para ransomware

# 3. Configurar integración con Elasticsearch
# Ya configurado en docker-compose.wazuh.yml
# Kibana accesible en http://localhost:15601
```

Add new integrations by:

1. Creating configuration files in `infra/docker/docker/`
2. Updating Docker Compose services
3. Adding validation tests in `tests/integration/`

### 3.3 Funcionalidades avanzadas

#### URLs de Acceso a Servicios

| Servicio | URL | Propósito |
|---|---|---|
| **UI de Gestión Web** | http://localhost:8081 | Dashboard de gestión principal |
| **Proxy Nginx** | http://localhost:80 | Proxy inverso unificado a todos los servicios |
| **TheHive** | http://localhost:9000 | Gestión de casos de incidentes |
| **Cortex** | http://localhost:9001 | Análisis y enriquecimiento de IoCs |
| **UI de Shuffle** | http://localhost:3001 | Workflows de orquestación SOAR |
| **API de Shuffle** | http://localhost:5001 | API REST de Shuffle |
| **Kibana** | http://localhost:15601 | Visualización de logs y dashboards |
| **MISP** | http://localhost:8082 | Plataforma de inteligencia de amenazas |
| **API del Laboratorio** | http://localhost:8000 | API REST de gestión del laboratorio |
| **Documentación** | http://localhost:3000 | Sitio de documentación del proyecto |
| **Grafana** | http://localhost:3002 | Dashboards de observabilidad (opcional) |
| **Loki** | http://localhost:3100 | Agregación de logs (opcional) |

#### Vía Proxy Nginx (puerto 80)

Todos los servicios también son accesibles a través del proxy inverso Nginx:

| Path | Proxy hacia |
|---|---|
| http://localhost/ | UI de Gestión Web |
| http://localhost/thehive/ | TheHive |
| http://localhost/cortex/ | Cortex |
| http://localhost/shuffle/ | UI de Shuffle |
| http://localhost/kibana/ | Kibana |
| http://localhost/api/ | API del Laboratorio |
| http://localhost/misp/ | MISP |
| http://localhost/docs/ | Documentación |
| http://localhost/grafana/ | Grafana |

#### Ejemplos de Playbooks Preconfigurados

**Playbook E2E de Ransomware (Shuffle):**

Este playbook implementa el flujo completo de respuesta a ransomware:

```
1. Webhook SIEM → Shuffle (recepción de alerta)
2. Validación de esquema (JSON schema validation)
3. Creación de caso en TheHive
4. Extracción de IoCs (IPs, dominios, hashes)
5. Ejecución de analyzers en Cortex:
   - FileInfo (análisis de archivo)
   - DomainMailSPFRecord (análisis de dominio)
   - VirusTotal (reputación de IoC)
6. Decisión basada en score/verdict:
   - Si score ≥ 80 o verdict = malicioso → Contención
   - Si score < 80 y verdict = benigno → Marcar como benigno
7. Ejecución de contención simulada:
   - src/soar_lab/services/containment_service.py
8. Actualización de caso en TheHive
9. Notificación a equipo de seguridad
```

**Configuración del Playbook en Shuffle:**
```bash
# 1. Acceder a http://localhost:3001/#/workflows
# 2. Crear nuevo workflow llamado "ransomware_response_e2e"
# 3. Configurar trigger: Webhook HTTP
# 4. URL del webhook: http://localhost:5001/api/v1/hooks/webhook
# 5. Token de autenticación: SiemToken123!@#
# 6. Añadir nodos en orden:
#    - Validator Node (JSON schema validation)
#    - TheHive Create Case
#    - Extract IoCs
#    - Cortex Analyzers (FileInfo, DomainMailSPFRecord)
#    - Decision Node (if score >= 80)
#    - Execute Script (isolate_host.sh)
#    - TheHive Update Case
#    - Send Notification
```

**Playbook de Escaneo de Vulnerabilidades:**

```
1. Recepción de solicitud de escaneo
2. Ejecución de src/soar_lab/services/containment_service.py
3. Análisis de resultados
4. Generación de reporte en artifacts/results/
5. Notificación de hallazgos críticos
```

**Playbook de Backup Automatizado:**

```
1. Trigger: Cron job (diario a las 2 AM)
2. Ejecución de scripts/infra/backup.sh
3. Verificación de integridad del backup
4. Limpieza de backups antiguos (> 30 días)
5. Notificación de estado del backup
```

#### Custom Playbooks

Create custom response playbooks:

```python
# Example: Custom ransomware response playbook
def ransomware_response(alert):
    """
    Automated response to ransomware alerts
    """
    # Isolate affected host
    isolate_host(alert.hostname)
    
    # Collect forensic evidence
    collect_evidence(alert.hostname)
    
    # Notify security team
    send_notification(alert)
    
    # Create incident case
    create_case(alert)
```

#### API Integration

Use the REST API for programmatic access:

```bash
# Get all alerts
curl -X GET "http://localhost:9000/api/alerts" \
     -H "Authorization: Bearer $TOKEN"

# Create new alert
curl -X POST "http://localhost:9000/api/alerts" \
     -H "Content-Type: application/json" \
     -d '{"alert_type": "ransomware", "severity": "high"}'
```

#### Best Practices

**Operational:**
1. **Actualizaciones Regulares**: Mantenga las dependencias actualizadas
2. **Estrategia de Backup**: Backups automatizados diarios
3. **Monitoreo**: Configure alertas para métricas críticas
4. **Pruebas**: Simulacros y ejercicios de seguridad regulares

**Seguridad:**
1. **Principio de Mínimo Privilegio**: Permisos mínimos requeridos
2. **Auditorías Regulares**: Evaluaciones de seguridad trimestrales
3. **Respuesta a Incidentes**: Mantenga planes de respuesta actualizados
4. **Capacitación**: Capacitación regular de conciencia de seguridad

**Desarrollo:**
1. **Revisión de Código**: Todos los cambios requieren revisión de pares
2. **Pruebas**: Cobertura de pruebas integral
3. **Documentación**: Mantenga los documentos actualizados con las características
4. **Control de Versiones**: Prácticas de versionamiento semántico

### 3.4 Solución de problemas

#### Problemas Comunes de Instalación

**Docker no inicia:**
```bash
# Verificar que Docker esté corriendo
docker ps
# Si hay error, reiniciar Docker Desktop
```

**Puertos ya en uso:**
```bash
# Verificar puertos en uso
netstat -ano | findstr :9000
# Cambiar puertos en .env.full
```

**Contenedores no se comunican:**
```bash
# Verificar redes Docker
docker network ls
docker network inspect soar_net
```

### 3.5 Referencias rápidas

#### Comandos Útiles

```bash
# Ver estado de todos los servicios
docker ps --format "table {{.Names}}\t{{.Status}}"

# Ver logs de un servicio específico
docker logs soar_thehive --tail 50

# Reiniciar el stack completo
make down && make up

# Acceder a un contenedor
docker exec -it soar_thehive bash
```

#### Contacto y Soporte

Para problemas o preguntas:
- Documentación oficial: https://shuffler.io/docs
- Issues del proyecto: https://github.com/alesanfe/soar-ransomware-lab/issues
- Revisar logs: `docker logs <container_name>`

## 4. Validación

### 4.1 Verificación

La instalación y configuración se verifican mediante:
- Verificación de que todos los contenedores estén en ejecución (`docker ps`)
- Verificación de health checks de cada servicio
- Acceso a URLs de servicios para confirmar disponibilidad
- Revisión de logs de Docker Compose para errores
- Ejecución de pruebas de configuración Docker (`tests/unit/test_docker_services_validation.py`)

### 4.2 Criterios de aceptación

La instalación se considera válida cuando:
- Todos los servicios inician correctamente
- Las URLs de servicios son accesibles
- Las credenciales por defecto funcionan
- El proxy Nginx redirige correctamente
- Los logs no muestran errores críticos
- Las pruebas de configuración pasan

### 4.3 Evidencias

Las evidencias de validación incluyen:
- Salida de `docker ps` mostrando contenedores en ejecución
- Capturas de pantalla de interfaces web accesibles
- Logs de Docker Compose sin errores
- Resultados de pruebas de configuración
- Confirmación de acceso a cada servicio

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Requisitos de recursos**: Mínimo 8GB RAM requerido para stack completo
- **Windows/Hyper-V**: Restricciones en rangos de puertos debido a reservas de Hyper-V
- **Single-node Elasticsearch**: Configuración actual no soporta clustering
- **Configuración por defecto**: Credenciales por defecto deben cambiarse antes de despliegue en producción

### 5.2 Riesgos o incidencias

- **Servicios no inician**: Puede ser debido a puertos ya en uso o conflictos de configuración
- **Puerto ya asignado (Windows/Docker Desktop)**: Algunos puertos pueden estar reservados por Hyper-V
- **Elasticsearch no accesible desde host (Windows)**: Bug conocido de Docker Desktop en Windows con redes personalizadas
- **Problemas de rendimiento**: Recursos insuficientes o configuración subóptima de Elasticsearch

### 5.3 Recomendaciones / troubleshooting

**Services Won't Start:**

```bash
# Check status of all containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs for a specific service
docker logs soar_thehive --tail 50
docker logs soar_elasticsearch --tail 50

# Restart the full stack
make down && make up
```

**Port Already Allocated (Windows/Docker Desktop):**

Some ports may be reserved by Hyper-V on Windows. Check excluded ranges:
```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```
If a port is in an excluded range, change it in `.env.full` and re-run `make up`.

**Elasticsearch Not Accessible from Host (Windows):**

This is a known Docker Desktop bug on Windows with custom networks. Elasticsearch is only accessible internally. All services that need it (Kibana, Shuffle, TheHive) connect through the Docker network and work correctly.

**Performance Issues:**

1. Monitor resource usage: `docker stats`
2. Check Elasticsearch cluster health
3. Review log files for errors

**Debug Mode:**

Enable debug logging:

```bash
# Set log level
LOG_LEVEL=DEBUG

# View detailed logs
docker-compose logs -f --tail=100
```

**Getting Help:**

- Check the [Architecture Documentation](../architecture/overview.md)
- Review [Security Guidelines](../architecture/security.md)
- Open an issue on GitHub
- Join our community Discord

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Docker Compose Documentation**: https://docs.docker.com/compose/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Documentación de Arquitectura**: [docs/architecture/overview.md](overview.md)
- **Documentación de Seguridad**: [docs/architecture/security.md](security.md)
- **Estrategia de Docker**: [docs/architecture/docker_architecture.md](docker_architecture.md)

---

**Mejoras implementadas:**
- Corregidas referencias a docs/core/ a rutas correctas (docs/architecture/, docs/getting_started/)
- Añadidos placeholders para screenshots de interfaces web con descripciones en formato []
- Documentados procedimientos específicos de configuración para cada servicio (TheHive, Cortex, Shuffle, MISP, Wazuh)
- Añadidos ejemplos de playbooks preconfigurados (E2E ransomware, escaneo de vulnerabilidades, backup automatizado)






