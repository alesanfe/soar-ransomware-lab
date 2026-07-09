# Documentación de Arquitectura Docker

> Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos
> Compose, configuración de redes, persistencia de datos y procedimientos de despliegue.

## Índice

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
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos Compose,
configuración de redes, persistencia de datos y procedimientos de despliegue.

### 1.2 Contexto

El SOAR Ransomware Lab utiliza Docker Compose para orquestar 16 servicios a través de 4 redes con mejoras en networking,
persistencia de datos y logging. Para la arquitectura completa del sistema, ver [README.md](README.md).

## 2. Alcance

### 2.1 Qué cubre

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

### 2.2 Límites

Este documento no cubre:

- Arquitectura de alto nivel del sistema (ver docs/architecture/overview.md)
- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver docs/getting_started/user_guide.md)
- Estrategias de pruebas específicas (ver docs/testing/)

### 2.3 Dependencias

Este documento depende de:

- Documentación oficial de Docker Compose
- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de seguridad (docs/architecture/security.md)
- Guía de usuario (docs/getting_started/user_guide.md)

## 3. Contenido principal

### 3.1 Estrategia de contenerización

#### Organización de Archivos Compose

Los archivos Docker Compose están organizados en `infra/docker/compose/` para mejor mantenibilidad:

```
infra/docker/compose/
├── docker-compose.yml           # Main orchestrator (networks, volumes, elasticsearch)
├── docker-compose.core.yml      # Redis, TheHive, Cortex, Shuffle
├── docker-compose.misp.yml      # MISP threat intelligence stack
├── docker-compose.wazuh.yml     # Wazuh SIEM stack
├── docker-compose.api.yml       # API, docs, web-management, nginx
└── logging/
    ├── docker-compose.logging.yml  # Loki, Promtail, Grafana, PostgreSQL
    ├── loki-config.yml             # Loki configuration
    ├── promtail-config.yml         # Promtail configuration
    └── grafana-datasources.yml     # Grafana datasource configuration
```

#### Iniciar Servicios

Para iniciar todos los servicios usando el Makefile (recomendado):

```bash
make up
```

Este comando inicia todos los servicios incluyendo el stack de logging (Grafana, Loki, Promtail).

Para iniciar manualmente con Docker Compose:

```bash
docker compose --env-file .env.full -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml up -d
```

#### Consideraciones de Seguridad Docker

- Redes internas aisladas con `internal: true`
- Servicios solo expuestos en redes necesarias
- Límites de recursos previenen agotamiento de recursos
- Healthchecks detectan servicios no saludables
- Bind mounts para control directo de datos

### 3.2 Servicios y composición

#### Servicios SOAR Core

| Servicio         | Imagen                         | Puertos | Redes               | Propósito             |
|------------------|--------------------------------|---------|---------------------|-----------------------|
| elasticsearch    | elasticsearch:7.17.29          | 9201    | soar_net, ti_net    | Búsqueda y análisis   |
| redis            | redis:7-alpine                 | 6379    | ti_net, soar_net    | Caching y cola        |
| thehive          | thehiveproject/thehive:3.5.2-1 | 9000    | soar_edge, soar_net | Gestión de casos      |
| cortex           | thehiveproject/cortex:3.1.4-1  | 9001    | soar_edge, soar_net | Motor de análisis     |
| shuffle-frontend | shuffle-frontend:latest        | 8081    | soar_edge, soar_net | UI de workflows       |
| shuffle-backend  | shuffle-backend:latest         | 5001    | soar_edge, soar_net | Motor de workflows    |
| orborus          | shuffle-orborus:latest         | -       | soar_net            | Ejecutor de workflows |

#### Stack de Inteligencia de Amenazas

| Servicio     | Imagen              | Puertos | Redes               | Propósito                              |
|--------------|---------------------|---------|---------------------|----------------------------------------|
| misp-db      | mariadb:10.11       | -       | soar_net            | Base de datos MISP                     |
| misp-modules | misp-modules:latest | -       | soar_net            | Analizadores MISP                      |
| misp         | misp-core:latest    | 8082    | soar_edge, soar_net | Plataforma de inteligencia de amenazas |

#### Stack SIEM

| Servicio      | Imagen               | Puertos         | Redes               | Propósito     |
|---------------|----------------------|-----------------|---------------------|---------------|
| wazuh-manager | wazuh-manager:4.14.0 | 15141,1515-1516 | soar_net, soar_edge | Gestor SIEM   |
| kibana        | kibana:7.17.29       | 15601           | soar_edge, soar_net | Visualización |

#### API y Documentación

| Servicio       | Imagen              | Puertos | Redes                       | Propósito           |
|----------------|---------------------|---------|-----------------------------|---------------------|
| api            | soar-api            | 8000    | soar_edge, soar_net, ti_net | API del laboratorio |
| docs-site      | soar-docs-site      | 8086    | soar_edge, soar_net         | Documentación       |
| web-management | soar-web-management | 8085    | soar_edge, soar_net         | UI de gestión       |

#### Proxy Inverso

| Servicio | Imagen            | Puertos | Redes               | Propósito     |
|----------|-------------------|---------|---------------------|---------------|
| nginx    | nginx:1.25-alpine | 80,443  | soar_edge, soar_net | Proxy inverso |

#### Healthchecks

Todos los servicios tienen healthchecks configurados:

- **elasticsearch**: Verificación de salud del cluster
- **redis**: Redis ping
- **thehive**: Endpoint de salud de API
- **cortex**: Verificación de estado HTTP
- **shuffle-frontend**: Verificación HTTP
- **shuffle-backend**: Verificación de endpoint de login
- **orborus**: Verificación de salud del backend de Shuffle
- **misp-db**: MySQL ping
- **misp-modules**: Verificación de puerto 6666
- **misp**: Endpoint de heartbeat
- **wazuh-manager**: Verificación de endpoint de API
- **kibana**: Verificación de API de estado
- **api**: Verificación de endpoint de salud
- **docs-site**: Verificación de puerto 8080
- **web-management**: Verificación de proceso Nginx
- **nginx**: Verificación de endpoint de salud

#### Límites de Recursos

Los servicios tienen límites de recursos configurados:

- **Servicios grandes** (elasticsearch, thehive, cortex, shuffle-backend, misp):
    - CPU: límite de 2.0 cores, 1.0 cores reservados
    - Memoria: límite de 4GB, 2GB reservados

- **Servicios medianos** (redis, shuffle-frontend, orborus, wazuh-manager, kibana, nginx, api):
    - CPU: límite de 1.0 cores, 0.5 cores reservados
    - Memoria: límite de 1-2GB, 512MB-1GB reservados

- **Servicios pequeños** (docs-site, web-management):
    - CPU: límite de 0.5 cores, 0.25 cores reservados
    - Memoria: límite de 256-512MB, 128-256MB reservados

### 3.3 Redes y volúmenes

#### Topología de Red

- **soar_edge** (172.18.0.0/16)
    - Red orientada al exterior
    - Servicios expuestos al host: nginx, thehive, cortex, shuffle-frontend, shuffle-backend, wazuh-manager, kibana,
      misp, api, docs-site, web-management
    - Propósito: Acceso a Internet y exposición de servicios externos

- **soar_net** (172.20.0.0/16)
    - Red interna para servicios SOAR
    - Servicios: elasticsearch, redis, thehive, cortex, shuffle services, api, nginx
    - Aislada del acceso externo
    - Propósito: Comunicación interna segura entre componentes SOAR

- **ti_net** (172.21.0.0/16)
    - Red interna para Inteligencia de Amenazas
    - Servicios: redis, misp, misp-modules, api
    - Aislada del acceso externo
    - Propósito: Comunicación segura para componentes de inteligencia de amenazas

- **logging_net** (172.23.0.0/16)
    - Red dedicada para infraestructura de logging
    - Servicios: Loki, Promtail, Grafana, PostgreSQL
    - Propósito: Tráfico de logging aislado

#### Seguridad de Red

- Las redes internas (soar_net, ti_net) están configuradas con `internal: true` para prevenir acceso externo
- Nombres de bridge personalizados para identificación más fácil de redes
- Subredes IPAM definidas para direccionamiento IP predecible
- Servicios solo expuestos en redes necesarias

#### Estrategia de Volúmenes

Todos los datos críticos se persisten usando bind mounts a `artifacts/data/` para mejor control:

```
artifacts/
├── data/
│   ├── elasticsearch/     # Elasticsearch data
│   ├── thehive/
│   │   └── files/         # TheHive file storage
│   ├── cortex/            # Cortex data
│   ├── shuffle/
│   │   ├── apps/         # Shuffle applications
│   │   └── files/        # Shuffle file storage
│   ├── redis/            # Redis persistence
│   ├── misp/
│   │   ├── db/           # MISP database
│   │   ├── files/        # MISP files
│   │   └── configs/      # MISP configurations
│   ├── wazuh/
│   │   ├── config/       # Wazuh configuration
│   │   ├── api_config/   # Wazuh API config
│   │   ├── etc/          # Wazuh etc directory
│   │   ├── queue/        # Wazuh queue
│   │   ├── var_multigroups/ # Wazuh multigroups
│   │   ├── integration_files/ # Wazuh integrations
│   │   ├── active_response/    # Wazuh active response
│   │   └── wodles/       # Wazuh wodles
│   └── kibana/           # Kibana data
│   ├── loki/             # Loki logs storage
│   └── grafana/          # Grafana data
└── logs/
    ├── nginx/            # Nginx logs
    └── wazuh/            # Wazuh logs
```

**Nota Importante:** Los datos se almacenan en `artifacts/data/` en el host. Esto permite backup directo del directorio
`artifacts/` para preservar todos los datos del laboratorio.

**Advertencia:** El uso de bind mounts a `artifacts/data/` crea una dependencia fuerte entre el código y la estructura
de directorios del host. Esto puede causar problemas si la estructura de `artifacts/` cambia.

#### Benefits of Bind Mounts

- Direct access to data from host system
- Easier backup and recovery
- Better control over data location
- Simplified data migration
- Integration with existing backup scripts (now pointing to `artifacts/backups/`)

#### Logging

**Configuración Actual:**

Cada servicio usa el driver json-file con:

- Tamaño máximo: 10MB por archivo
- Archivos máximos: 3 por servicio
- Total: ~30MB por servicio

**Ubicaciones de Logs:**

Los logs se almacenan en:

- `artifacts/logs/nginx/` - Logs de Nginx
- `artifacts/logs/wazuh/` - Logs de Wazuh
- Logs de contenedores accesibles vía `docker logs`

**Futuro: Logging Centralizado:**

El logging centralizado está disponible vía el archivo compose de logging:

- Loki para agregación de logs (activo)
- Promtail para recolección de logs (activo)
- Grafana para visualización de logs (activo con PostgreSQL)
- Base de datos PostgreSQL para Grafana (activo)
- Archivos de configuración en `compose/logging/`
- Logs almacenados en `artifacts/data/loki/` y `artifacts/data/grafana/`

**Nota:** Grafana usa PostgreSQL en lugar de SQLite para evitar errores de I/O de disco en Windows Docker Desktop. El
servicio PostgreSQL está incluido en el stack de logging.

Para habilitar:

```bash
docker compose --env-file ../../.env.full -f compose/docker-compose.yml -f compose/docker-compose.core.yml -f compose/docker-compose.misp.yml -f compose/docker-compose.wazuh.yml -f compose/docker-compose.api.yml -f compose/logging/docker-compose.logging.yml up -d
```

#### Estrategia de Backup

**Configuración Actual:**

- Script de backup: `scripts/infra/backup.sh`
- Script de restore: `scripts/infra/restore.sh`
- Ubicación de backup: `artifacts/backups/`
- Componentes con backup:
    - Archivos de configuración
    - Volúmenes Docker
    - Logs
    - Resultados de tests

**Automatización de Backup:**

Para automatizar backups:

```bash
# Añadir a crontab para backups diarios a las 2 AM
0 2 * * * /path/to/soar-ransomware-lab/scripts/infra/backup.sh
```

### 3.4 Comandos y operaciones

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
- Revisar y actualizar archivos docker-compose.yml
- Aplicar parches de seguridad a contenedores

**Monitoreo:**

- Verificar health checks de servicios
- Monitorear uso de recursos con `docker stats`
- Revisar logs regularmente

### 3.5 Troubleshooting Docker

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
ls -la artifacts/data/
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

# Ajustar límites de recursos en docker-compose.yml
```

#### Elasticsearch lento

```bash
# Verificar salud de Elasticsearch
curl http://localhost:9201/_cluster/health

# Aumentar límite de memoria en docker-compose.yml
```

#### Problema de Índice de Elasticsearch en TheHive

**Problema:** TheHive requiere el índice de Elasticsearch `the_hive_17` que puede no existir en una instalación fresca.

**Solución Actual:** El healthcheck se cambió para usar `/api/status` en lugar de `/api/health` para evitar la
dependencia del índice. El índice se creará automáticamente por TheHive al iniciar.

## 4. Validación

### 4.1 Verificación

La configuración Docker se verifica mediante:

- Ejecución de `docker compose config` para validar sintaxis
- Verificación de que todas las redes se crean correctamente (`docker network ls`)
- Verificación de que todos los volúmenes se montan correctamente (`docker volume ls`)
- Ejecución de health checks para cada servicio
- Pruebas de conectividad entre servicios en redes específicas

### 4.2 Criterios de aceptación

La configuración Docker se considera válida cuando:

- Todos los servicios inician sin errores
- Los health checks pasan para todos los servicios
- Las redes están correctamente configuradas y aisladas
- Los volúmenes se montan correctamente
- Los servicios pueden comunicarse entre sí según la topología de red
- Los logs se generan correctamente

### 4.3 Evidencias

Las evidencias de validación incluyen:

- Salida de `docker compose config` sin errores
- Salida de `docker compose ps` mostrando servicios en ejecución
- Salida de `docker network ls` mostrando las 4 redes
- Salida de `docker volume ls` mostrando volúmenes montados
- Logs de Docker Compose sin errores críticos
- Resultados de health checks (`docker inspect`)

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Bind mounts en Windows**: El rendimiento de bind mounts puede ser menor en Windows Docker Desktop
- **Single-node Elasticsearch**: Configuración actual no soporta clustering
- **Recursos limitados**: Mínimo 8GB RAM requerido para stack completo

### 5.2 Riesgos o incidencias

- **Servicios no inician**: Puede ser debido a puertos ya en uso o conflictos de configuración
- **Problemas de conectividad de red**: Configuración incorrecta de redes internas
- **Problemas de persistencia de datos**: Montajes de volúmenes fallidos
- **Conflictos de puertos**: Puertos ya en uso por otros servicios
- **Problemas de rendimiento**: Recursos insuficientes o configuración subóptima

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones Generales:**

- Para troubleshooting específico de Docker, ver sección 3.5
- Mantener las imágenes Docker actualizadas regularmente
- Monitorear el uso de recursos con `docker stats`
- Revisar logs regularmente para detectar problemas temprano
- Implementar una estrategia de backup regular

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Docker Networking**: https://docs.docker.com/network/
- **Documentación de Docker Volumes**: https://docs.docker.com/storage/volumes/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Arquitectura**: [docs/architecture/overview.md](overview.md)
- **Documentación de Seguridad**: [docs/architecture/security.md](security.md)
- **Guía de Usuario**: [docs/getting_started/user_guide.md](../getting_started/user_guide.md)
