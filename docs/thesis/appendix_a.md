# Anexo A: Configuración Técnica del Laboratorio

Aviso de sincronización: este anexo es una instantánea estática de la configuración Docker Compose y variables de
entorno. La versión canónica y actualizada del stack se encuentra en `infra/docker/compose/` (y `.env.example`/`.env.full`).
En caso de discrepancia, prevalecen los archivos Compose del repositorio.

Este anexo contiene la configuración técnica y código fuente de los componentes principales del laboratorio SOAR para
reproducir el sistema.

## A.1. Configuración Completa de Docker Compose

La configuración Docker Compose define los servicios, redes, volúmenes y dependencias del laboratorio SOAR. La
arquitectura modular permite despliegues desde configuraciones mínimas hasta entornos completos, separando
responsabilidades entre componentes.

### A.1.1. Archivo docker-compose.yml (orquestador principal)

El archivo `docker-compose.yml` es el orquestador principal: define las redes Docker (`soar_net` 10.100.0.0/16, `ti_net` 172.22.0.0/16 internal, `logging_net` 172.23.0.0/16), los volúmenes bind-mount centralizados en `runtime/` y el servicio Elasticsearch. Los servicios de aplicación (TheHive, Cortex, Shuffle, Nginx, etc.) se definen en `docker-compose.core.yml` y los restantes compose files (ver §A.6.1). `make up` combina automáticamente todos los archivos.

Nota. Los servicios de aplicación (TheHive, Cortex, Shuffle, Orborus, Redis, Nginx, etc.) se definen en `docker-compose.core.yml` y `docker-compose.api.yml`. El contenido completo de cada compose file está en `infra/docker/compose/`. La sección A.6 proporciona el inventario completo.

### A.1.2. Archivo .env.full

El archivo de entorno `.env.full` contiene todas las variables de configuración necesarias para el despliegue del laboratorio
SOAR. Este archivo permite la personalización del sistema según las necesidades específicas de cada entorno, facilitando
la adaptación a diferentes configuraciones de red, recursos disponibles y requisitos de seguridad. Las variables de
entorno incluyen configuraciones de puertos, credenciales, imágenes Docker y parámetros de red, permitiendo una
configuración modular en el despliegue sin necesidad de modificar los archivos de configuración principales.

```bash
# Project Configuration
COMPOSE_PROJECT_NAME=soar

# Ports — Core SOAR
THEHIVE_HTTP_PORT=8100
CORTEX_HTTP_PORT=8101
SHUFFLE_UI_PORT=8081
SHUFFLE_API_PORT=5001
ELASTICSEARCH_PORT=8200
OPENSEARCH_PORT=8201

# Ports — Management
HTTP_PORT=80
HTTPS_PORT=443
WEB_UI_PORT=8085
API_PORT=8000
DOCS_PORT=8086
MISP_PORT=8083
GRAFANA_PORT=8084

# Elasticsearch
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=<ELASTIC_PASSWORD>
ELASTIC_SECURITY_ENABLED=false
ES_JAVA_OPTS=-Xms2g -Xmx2g

# Shuffle
SHUFFLE_FRONTEND_IMAGE=ghcr.io/shuffle/shuffle-frontend:2.2.1
SHUFFLE_BACKEND_IMAGE=ghcr.io/shuffle/shuffle-backend:2.2.1
SHUFFLE_DEFAULT_USERNAME=admin
SHUFFLE_DEFAULT_PASSWORD=<SHUFFLE_DEFAULT_PASSWORD>
SHUFFLE_DEFAULT_APIKEY=<SHUFFLE_DEFAULT_APIKEY>

# Orborus
ORBORUS_IMAGE=ghcr.io/shuffle/shuffle-orborus:2.2.1-patched

# Docker
DOCKER_API_VERSION=1.44

# Network
OUTER_HOSTNAME=localhost
```

La **Tabla 13** resume las variables de entorno Docker más relevantes para la personalización del despliegue.

## Tabla 13: Variables de Entorno Docker

| Variable               | Valor por Defecto | Descripción              | Requerido |
|------------------------|-------------------|--------------------------|-----------|
| `COMPOSE_PROJECT_NAME` | soar              | Nombre del proyecto      | No        |
| `ELASTIC_PASSWORD`     | Ver `.env.full`   | Contraseña Elasticsearch | Sí        |
| `ELASTIC_SECURITY_ENABLED` | false         | Seguridad Elasticsearch  | No        |
| `THEHIVE_HTTP_PORT`    | 8100              | Puerto TheHive           | No        |
| `CORTEX_HTTP_PORT`     | 8101              | Puerto Cortex            | No        |
| `SHUFFLE_UI_PORT`      | 8081              | Puerto Shuffle UI        | No        |
| `SHUFFLE_API_PORT`     | 5001              | Puerto Shuffle API       | No        |
| `ELASTICSEARCH_PORT`   | 8200              | Puerto Elasticsearch     | No        |
| `OPENSEARCH_PORT`      | 8201              | Puerto OpenSearch        | No        |
| `HTTP_PORT`            | 80                | Puerto HTTP público      | No        |
| `HTTPS_PORT`           | 443               | Puerto HTTPS público     | No        |
| `WEB_UI_PORT`          | 8085              | Puerto UI gestión        | No        |
| `API_PORT`             | 8000              | Puerto API FastAPI       | No        |
| `DOCS_PORT`            | 8086              | Puerto Docs Site         | No        |
| `MISP_PORT`            | 8083              | Puerto MISP              | No        |
| `GRAFANA_PORT`         | 8084              | Puerto Grafana           | No        |

## A.2. Scripts de Automatización

Los scripts de automatización desarrollados para el laboratorio SOAR ofrecen las capacidades operativas necesarias para
la simulación de incidentes, el cálculo de métricas y la ejecución de acciones de respuesta. Estos scripts representan
la materialización práctica de la automatización SOAR, permitiendo la validación del sistema mediante simulaciones
controladas y ofreciendo las herramientas necesarias para el análisis de rendimiento. Cada script sigue buenas prácticas
de desarrollo software, incluyendo manejo de errores, logging estructurado y documentación completa.

### A.2.1. Alert Sender CLI (send_alert.py)

El script `send_alert.py` es el CLI que genera y envía alertas de ransomware con datos realistas al webhook de Shuffle
para su procesamiento. El simulador E2E (`src/soar_lab/simulator/simulate_alerts.py`) usa este mismo mecanismo para
inyectar alertas controladas que representan escenarios realistas de ransomware sin exponer el sistema a amenazas reales.
La implementación incluye la generación de alertas con IoCs conocidos, soporte para alertas maliciosas y benignas,
distribución temporal configurable para pruebas de carga, validación de esquemas JSON y autenticación mediante API token.
Este script se utiliza extensivamente en las pruebas E2E del sistema para validar el flujo completo de respuesta a incidentes.

Métodos principales:

| Función | Descripción |
|---------|-------------|
| `_default_webhook_url(base_dir)` | Resuelve la URL del webhook desde `webhook_info.json` o variable de entorno |
| `main()` | Punto de entrada: parsea argumentos, genera alertas y las envía al webhook |

### A.2.2. AnalyticsService (KPI Calculator)

El `AnalyticsService` es el servicio de aplicación responsable de calcular métricas MTTR y KPIs desde logs de ejecución del sistema. Sigue la arquitectura hexagonal del proyecto: recibe sus dependencias por inyección (repositories, log_parser, statistical_calculator, kpi_formatter, kpi_analyzer) y delega los cálculos puros a colaboradores especializados. Este componente es la base para la validación cuantitativa de los beneficios de SOAR, permitiendo el análisis estadístico de tiempos de respuesta, el cálculo de percentiles (p50, p90), la exportación de resultados a CSV y la generación de informes de rendimiento.

Métodos principales:

| Método | Descripción |
|--------|-------------|
| `get_comprehensive_system_stats()` | Estadísticas completas (aplicación + hardware + proceso) |
| `get_performance_kpis(hours=24)` | KPIs de rendimiento para un período dado |
| `get_health_score()` | Score de salud del sistema (CPU, memoria, disco, cobertura) |
| `calculate_mttr_metrics(log_file_path)` | Métricas MTTR (p50, p90, media, std_dev) desde logs |
| `parse_execution_logs(log_file_path)` | Parsea logs de ejecución para extraer timestamps |
| `save_kpis_to_csv(metrics, output_path)` | Exporta KPIs a archivo CSV |
| `get_comprehensive_kpis(log_file_path)` | KPIs comprehensivos (MTTR + performance + health) |

El servicio se compone en `src/soar_lab/interfaces/api/composition.py` con sus dependencias concretas (`SqliteAlertRepository`, `SystemMetricsDriver`, `FilesystemStorage`, `ExecutionLogParser`, `StatisticalCalculator`, `CSVKPIFormatter`, `KPIAnalyzer`). El cálculo estadístico puro (percentiles, media, desviación estándar, coeficiente de variación) se delega a `StatisticalCalculator` (puerto `StatisticalCalculatorInterface`), lo que mantiene el dominio independiente de la infraestructura.

## A.3. Configuración de TheHive

La integración con TheHive se realiza mediante el script `scripts/setup/init_thehive.py`, que crea el índice Elasticsearch con el mapping correcto para TheHive 3.5.2 (join field + keyword fix), configura el usuario administrador y genera la API key que se almacena en `.env.full` como `THEHIVE_API_KEY`. Los casos se crean automáticamente desde el workflow de Shuffle durante la ejecución del playbook E2E.

### A.3.1. Index Template para TheHive (init_thehive.py)

TheHive 3.5.2 requiere un mapping Elasticsearch específico para el campo `relations` (join field) y para evitar conflictos con campos `text` vs `keyword`. El script `init_thehive.py` pre-crea el index template antes del arranque de TheHive. El template define:

- `index_patterns`: `["the_hive_*"]`
- `dynamic_templates`: strings como `text` con subcampo `keyword` (ignore_above 256)
- `relations`: tipo `join` con jerarquía case → case_task → case_task_log, case → case_artifact, más children dummy para alert, user, dashboard, audit, sequence, caseTemplate, dblist
- Campos explícitos: `key`, `password`, `status`, `login` (keyword); `tlp`, `pap`, `severity`, `caseId`, `order` (integer); `startDate`, `endDate`, `createdAt`, `updatedAt`, `date` (date); `flag`, `ioc`, `sighted`, `ignoreSimilarity` (boolean)

Este template se aplica con `PUT _template/thehive_template` antes de que TheHive arranque, evitando el error `mapper_parsing_exception` que ocurre cuando Elasticsearch infiere automáticamente el tipo `text` para campos que TheHive espera como `keyword`.

### A.3.2. Creación de casos desde el workflow

El workflow E2E de Shuffle crea casos en TheHive mediante la app `TheHive_app` con los siguientes campos:

- `title`: `{alert_type}: {hostname} - {alert_id} | MITRE: {mitre_str}` (ej. `Ransomware: DESKTOP-ABC - ALERT-001 | MITRE: T1486, T1490`)
- `description`: Resumen de la alerta con IoCs (IPs, dominios, hashes, MITRE)
- `severity`: 3 (alto/crítico) para la mayoría de alertas maliciosas; 2 (medio) para troyanos
- `tags`: `ransomware`, `soar-lab`, `automated`, `{alert_type}`, `alert_id:{id}`, `priority:critical` (si severity=3) o `priority:high` (si severity=2)
- `tlp`: 2 (AMBER)

Los observables (IoCs) se añaden al caso como artifacts con `dataType` (`ip`, `domain`, `hash`, `url`) y `message` con el valor del IoC. El estado del caso permanece `Open` durante la contención simulada (TheHive 3.5.2 solo soporta `Open`/`Resolved`/`Deleted`; el script `update_inprogress.py` confirma que el caso se mantiene `Open` en la rama maliciosa). En la rama benigna, el caso se marca como `Resolved` con `resolutionStatus: FalsePositive` vía `mark_false_positive.py`.

## A.4. Configuración de Monitoreo

El laboratorio usa un stack de observabilidad basado en **Loki + Promtail + Grafana** (no Prometheus). Los logs de los contenedores se recogen con Promtail, se agregan en Loki y se visualizan en Grafana mediante el dashboard KPI definido en `infra/docker/compose/logging/kpi-dashboard.json`.

### A.4.1. Stack de Logging (Loki + Promtail + Grafana)

El servicio `loki` (imagen `grafana/loki:2.9.10`) agrega logs de todos los contenedores. `promtail` (`grafana/promtail:2.9.9`) los recoge vía Docker API y los envía a Loki con labels por servicio. `grafana` (`grafana/grafana:10.3.4`) visualiza los datos y `grafana-renderer` (`grafana/grafana-image-renderer:3.10.4`) renderiza paneles para alertas. `grafana-db` (`postgres:14-alpine`) persiste dashboards y usuarios.

### A.4.2. Dashboard KPI de Grafana (kpi-dashboard.json)

El dashboard KPI principal está en `infra/docker/compose/logging/kpi-dashboard.json` y consulta el índice `soar-metrics` de Elasticsearch (datasource `Elasticsearch`, uid `${DS_ELASTICSEARCH}`). Contiene 15 paneles:

| Panel | Título | Tipo |
|-------|--------|------|
| 1 | Total Alerts Processed | stat |
| 2 | MTTR Medio (s) | stat |
| 3 | Alertas Críticas (severity=3) | stat |
| 4 | MTTR p50 (Mediana) | stat |
| 5 | MTTR p90 | stat |
| 6 | Análisis de Percentiles MTTR (distribución completa) | timeseries |
| 7 | Evolución MTTR (tendencia diaria) | timeseries |
| 8 | Tasa de Éxito por Tipo de Alerta | piechart |
| 9 | Alertas por Severidad (distribución SOAR) | barchart |
| 10 | Tasa de Éxito Servicios (TheHive / Cortex / MISP) | timeseries |
| 11 | MTTR Max / Min (rango de variabilidad) | stat |
| 12 | Alertas procesadas por hora (throughput SOAR) | timeseries |
| 13 | MTTR por Tipo de Alerta | barchart |
| 14 | Tasa de Éxito por Severidad | barchart |
| 15 | Evolución de Alertas por Tipo | timeseries |

Las consultas usan Lucene/Elasticsearch Query DSL sobre el índice `soar-metrics`, que se pobla desde el workflow de Shuffle tras cada ejecución del playbook. El campo `mttr_seconds` (float) almacena el MTTR por ejecución, `verdict.keyword` el veredicto (malicious/suspicious) y `decision.keyword` la decisión (contain/observe).

### A.4.3. Configuración de Promtail

Promtail recoge logs de todos los contenedores Docker vía el socket `/var/run/docker.sock` y los envía a Loki. La configuración se define en `infra/docker/config/templates/promtail-config.yml.template` y etiqueta cada línea de log con `container` (nombre del contenedor), `container_id` (ID del contenedor), `service` (nombre del servicio sin sufijo de réplica), `network` (nombre de la red Docker), `compose_service` (label Docker Compose) y `compose_project` (nombre del proyecto), permitiendo filtrar en Grafana por servicio, red o proyecto.

## A.5. Troubleshooting Común

### A.5.1. Problemas Frecuentes

A continuación se recogen los problemas más frecuentes detectados durante el despliegue y operación del laboratorio, junto con pasos operativos concretos, criterios de verificación y casos de error asociados.

#### 1. Contenedores no inician

Causas típicas.

- Docker daemon no está en ejecución.
- Falta de espacio en disco o memoria insuficiente.
- Límites de recursos (`deploy.resources`) superan los disponibles en el host.
- Volúmenes huérfanos de una ejecución anterior en estado inconsistente.

Pasos operativos.

```bash
# 1. Verificar el daemon de Docker
sudo systemctl status docker

# 2. Comprobar espacio en disco y memoria libre
df -h
free -h

# 3. Listar contenedores y volúmenes detenidos/huérfanos
docker ps -a
docker volume ls

# 4. Limpiar (solo en desarrollo; conservar .env.full)
docker system prune -f

# 5. Reiniciar Docker si es necesario
sudo systemctl restart docker
```

Criterio de verificación.

- `docker ps` muestra el contenedor en estado `Up` o `healthy` tras `make up`.
- `docker compose ps` no reporta `Exit` o `unhealthy` persistentes.

---

#### 2. Elasticsearch/OpenSearch falla o se reinicia continuamente

Causas típicas.

- `vm.max_map_count` insuficiente en Linux.
- Permisos incorrectos en los volúmenes de datos.
- Configuración de memoria JVM inadecuada para el host.
- Volcado de heap por falta de RAM.

Pasos operativos.

```bash
# 1. Verificar opciones JVM
docker exec soar_elasticsearch env | grep ES_JAVA_OPTS

# 2. Verificar permisos del volumen
ls -la runtime/data/elasticsearch/

# 3. Aumentar el límite de map_count en Linux
sudo sysctl -w vm.max_map_count=262144

# 4. Para Windows/WSL
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
```

Criterio de verificación.

- `docker logs soar_elasticsearch` termina con `"Cluster health status changed from [YELLOW] to [GREEN]"`.
- `curl -f http://localhost:8200/_cluster/health` devuelve `status` `green` o `yellow`.

---

#### 3. Conexión entre servicios (DNS/red)

Causas típicas.

- Un servicio no se conectó a `soar_net`.
- El `network-watcher` no inyectó entradas `/etc/hosts` en los workers de Shuffle.
- Un servicio arrancó antes de que sus dependencias estuvieran realmente listas.

Pasos operativos.

```bash
# 1. Listar redes
docker network ls

# 2. Inspeccionar la red principal
docker network inspect soar_net

# 3. Probar resolución DNS entre contenedores
docker exec soar_thehive nslookup elasticsearch
docker exec soar_shuffle_backend nslookup redis

# 4. Verificar logs del network-watcher
docker logs -f soar_network_watcher

# 5. Reconectar manualmente un worker si falla
WORKER_ID=$(docker ps -q --filter name=worker- | head -1)
docker network connect soar_net $WORKER_ID
docker restart $WORKER_ID
```

Criterio de verificación.

- Los `healthcheck` de los servicios afectados pasan.
- `docker exec <contenedor> getent hosts <servicio>` resuelve correctamente.

---

#### 4. Errores E2E en `soar_shuffle_backend`

Causas típicas.

- Workflow no creado o trigger no activado.
- `SHUFFLE_DEFAULT_APIKEY` desactualizada tras `make reset && make up`.
- Timeouts por concurrencia insuficiente (`SHUFFLE_ORBORUS_EXECUTION_CONCURRENCY`).

Pasos operativos.

```bash
# 1. Verificar estado de Shuffle
docker logs -f soar_shuffle_backend

# 2. Comprobar que el workflow existe y su ID
cat reports/validation/results/webhook_info.json

# 3. Actualizar SHUFFLE_DEFAULT_APIKEY si es necesario
docker exec soar_api cat /app/.env.full | grep SHUFFLE_DEFAULT_APIKEY

# 4. Verificar ejecuciones del workflow desde Shuffle UI o ES
curl http://localhost:8200/soar-alerts/_count -u elastic:$ELASTIC_PASSWORD
```

Criterio de verificación.

- La ejecución del workflow finaliza con estado `SUCCESS`.
- `make test-e2e` pasa sin fallos (ver `reports/e2e/` para el total actual de TCs).

---

#### 5. Grafana no muestra métricas (`soar-metrics` vacío)

Causas típicas.

- Plugin Elasticsearch no instalado en Grafana 10.3.4.
- Grafana no puede resolver `elasticsearch`.
- Mapping incorrecto del índice (`mttr_seconds` como `object` en lugar de `float`).
- Falta `@timestamp` en los documentos.

Pasos operativos.

```bash
# 1. Verificar que Grafana tiene el plugin
docker exec soar_grafana grafana-cli plugins ls | grep elasticsearch

# 2. Comprobar redes de Grafana
docker network inspect logging_net
docker network inspect soar_net

# 3. Verificar mapping del índice
curl http://localhost:8200/soar-metrics/_mapping -u elastic:$ELASTIC_PASSWORD

# 4. Reindexar si es necesario (ver docs/04-operations.md sección logging)
```

Criterio de verificación.

- `curl http://localhost:8200/soar-metrics/_count` devuelve documentos.
- Grafana muestra datos en el dashboard KPI.

---

#### 6. MISP DB: error `Permission denied` en operaciones de MariaDB

Causas típicas.

- `misp_db` se configura como bind mount en Windows/Docker Desktop.
- Permisos de `rename` sobre bind mounts NTFS.

Pasos operativos.

```bash
# 1. Comprobar que misp_db es volumen Docker normal
docker volume ls | grep misp_db

# 2. Si existía un bind mount antiguo, eliminarlo manualmente (Windows)
Remove-Item -Recurse -Force runtime/data/misp/db   # PowerShell

# 3. Recrear volumen
make down -v
make up
```

Criterio de verificación.

- `docker inspect soar_misp_db` muestra `"Type": "volume"`.
- `docker compose ps` marca `misp-db` como `healthy`.

---

#### 7. Autenticación JWT / Lab API (`401 Unauthorized`)

Causas típicas.

- `API_AUTH_SECRET` / `JWT_SECRET_KEY` no definidos o desfasados.
- Ejemplos con contraseñas por defecto no actualizadas.

Pasos operativos.

```bash
# 1. Verificar secretos en .env.full
grep -E 'JWT_SECRET_KEY|API_AUTH_SECRET|WEB_UI_PASSWORD' .env.full

# 2. Probar login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<WEB_UI_PASSWORD>"}'

# 3. Verificar token
export TOKEN=<token>
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/verify
```

Criterio de verificación.

- `POST /auth/login` devuelve `200` con `token`.
- `POST /auth/verify` devuelve `{"valid": true, ...}`.

---

#### 8. Certificado SSL de `soar.local` no es confiado

Causas típicas.

- Certificado autofirmado no instalado en el almacén de confianza del host.
- Nginx expira el certificado.

Pasos operativos.

```bash
# 1. Comprobar validez del certificado
openssl x509 -in infra/docker/config/nginx/ssl/soar.local.crt -noout -dates -subject

# 2. Verificar nginx -t
docker exec soar_nginx nginx -t

# 3. Instalar certificado en Windows
Import-Certificate -FilePath "infra\docker\config\nginx\ssl\soar.local.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

Criterio de verificación.

- `nginx -t` devuelve `syntax is ok` / `test is successful`.
- `curl -k https://soar.local` devuelve la página correspondiente.

---

## A.6. Inventario Completo de Archivos Docker Compose

El laboratorio SOAR usa **6 archivos Docker Compose** principales
que se combinan automáticamente con `make up`, totalizando 23 servicios.
La sección A.1.1 muestra el archivo principal (`docker-compose.yml`); los restantes se documentan aquí
como referencia. La versión canónica está en `infra/docker/compose/`.

### A.6.1. Mapa de Archivos Compose

| Archivo | Ubicación | Servicios | Propósito |
|---------|-----------|-----------|-----------|
| `docker-compose.yml` | `infra/docker/compose/` | elasticsearch | Orquestador: redes, volúmenes, Elasticsearch (ver A.1.1) |
| `docker-compose.core.yml` | `infra/docker/compose/` | redis, thehive, cortex, shuffle-frontend, shuffle-backend, network-watcher, tenzir-node, orborus | Servicios SOAR principales |
| `docker-compose.misp.yml` | `infra/docker/compose/` | misp, misp-db, misp-modules | Threat intelligence (MISP) |
| `docker-compose.api.yml` | `infra/docker/compose/` | api, web-management, docs-site, nginx | API FastAPI + UI + docs + proxy |
| `docker-compose.opensearch.yml` | `infra/docker/compose/` | opensearch, opensearch-dashboards | OpenSearch para Shuffle |
| `docker-compose.logging.yml` | `infra/docker/compose/logging/` | loki, promtail, grafana, grafana-db, grafana-renderer | Observabilidad (subdirectorio) |

### A.6.2. Servicios Adicionales (no en A.1.1)

Los siguientes servicios se definen en los compose files adicionales y no aparecen en la
sección A.1.1:

| Servicio | Imagen | Compose File | Función |
|----------|--------|--------------|---------|
| `redis` | `redis:7-alpine` | core | Cache/cola con autenticación |
| `thehive` | `thehiveproject/thehive:3.5.2-1` | core | Gestión de casos |
| `cortex` | build (local) | core | Análisis de IoCs |
| `shuffle-frontend` | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | core | UI Shuffle |
| `shuffle-backend` | `ghcr.io/shuffle/shuffle-backend:2.2.1` | core | Backend Shuffle |
| `network-watcher` | build (local) | core | Diagnóstico/recuperación de red |
| `tenzir-node` | `tenzir/tenzir:v6.8.1` | core | Nodo Tenzir (modo dev) |
| `orborus` | `ghcr.io/shuffle/shuffle-orborus:2.2.1-patched` | core | Orquestador de workers Shuffle |
| `misp` | `ghcr.io/misp/misp-docker/misp-core:v2.5.44` | misp | Threat intelligence |
| `misp-db` | `mariadb:10.11` | misp | BD MISP |
| `misp-modules` | `ghcr.io/misp/misp-docker/misp-modules:v3.0.9` | misp | Módulos MISP |
| `api` | build `apps/api/Dockerfile` | api | API FastAPI (Lab API) |
| `web-management` | build `apps/web-management/Dockerfile` | api | UI de gestión web |
| `docs-site` | build `apps/docs-site/Dockerfile` | api | Docusaurus (docs) |
| `nginx` | `nginx:1.25-alpine` | api | Proxy inverso + TLS |
| `opensearch` | `opensearchproject/opensearch:2.10.0` | opensearch | Motor de búsqueda Shuffle |
| `opensearch-dashboards` | `opensearchproject/opensearch-dashboards:2.10.0` | opensearch | Dashboard OpenSearch |
| `loki` | `grafana/loki:2.9.10` | logging | Agregación de logs |
| `promtail` | `grafana/promtail:2.9.9` | logging | Shipper de logs |
| `grafana` | `grafana/grafana:10.3.4` | logging | Visualización |
| `grafana-db` | `postgres:14-alpine` | logging | BD Grafana |
| `grafana-renderer` | `grafana/grafana-image-renderer:3.10.4` | logging | Renderizado de imágenes para alertas |

### A.6.3. Redes Docker

| Red | CIDR | Tipo | Propósito |
|-----|------|------|-----------|
| `soar_net` | `10.100.0.0/16` | bridge | Red principal del laboratorio |
| `ti_net` | `172.22.0.0/16` | internal | Threat intelligence (sin acceso externo) |
| `logging_net` | `172.23.0.0/16` | bridge | Observabilidad (Loki, Grafana) |
| `bridge` | — | external | Red por defecto Docker (compatibilidad) |

### A.6.4. Resumen del Stack Completo

| Métrica | Valor |
|---------|-------|
| Archivos compose | 6 |
| Servicios totales | 23 |
| Redes | 4 (soar_net, ti_net, logging_net + bridge) |
| Volúmenes persistentes | 15 |
| Imágenes Docker | 23 (6 builds locales + 17 pulls) |
| Versiones pinned | 100% (todas las imágenes tienen tag fijo) |

Nota. Para el contenido completo de cada compose file, ver `infra/docker/compose/`.
