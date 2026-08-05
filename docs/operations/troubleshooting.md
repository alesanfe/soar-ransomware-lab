# Guía de Troubleshooting del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Problemas comunes de Docker](#31-problemas-comunes-de-docker)
        - [3.1.1 Test paths incorrectos en Makefile.win](#311-test-paths-incorrectos-en-makefilewin)
        - [3.1.2 Elasticsearch initialization script error](#312-elasticsearch-initialization-script-error)
        - [3.1.3 Docker daemon not running](#313-docker-daemon-not-running)
        - [3.1.4 Puertos bloqueados](#314-puertos-bloqueados)
        - [3.1.5 Recursos insuficientes](#315-recursos-insuficientes)
        - [3.1.6 Imágenes no disponibles](#316-imágenes-no-disponibles)
    - [3.2 Problemas de servicios](#32-problemas-de-servicios)
        - [3.2.1 Elasticsearch no inicia](#321-elasticsearch-no-inicia)
        - [3.2.2 Elasticsearch disk watermark assertion failure](#322-elasticsearch-disk-watermark-assertion-failure)
        - [3.2.3 TheHive no responde](#323-thehive-no-responde)
        - [3.2.4 Cortex analyzers fallan](#324-cortex-analyzers-fallan)
        - [3.2.5 Shuffle workflows fallan](#325-shuffle-workflows-fallan)
        - [3.2.6 Credenciales desincronizadas tras fresh deploy](#326-credenciales-desincronizadas-tras-fresh-deploy)
        - [3.2.7 Persistencia de credenciales tras fresh deploy](#327-persistencia-de-credenciales-tras-fresh-deploy)
        - [3.2.8 Docs Site no inicia](#328-docs-site-no-inicia)
    - [3.3 Problemas de integración](#33-problemas-de-integración)
        - [3.3.1 Integración Shuffle → TheHive rota](#331-integración-shuffle--thehive-rota)
        - [3.3.2 Integración Shuffle → Cortex rota](#332-integración-shuffle--cortex-rota)
        - [3.3.3 Webhooks no funcionan](#333-webhooks-no-funcionan)
    - [3.4 Problemas de rendimiento](#34-problemas-de-rendimiento)
        - [3.4.1 Tiempo de respuesta excesivo](#341-tiempo-de-respuesta-excesivo)
        - [3.4.2 Alto uso de CPU/Memoria](#342-alto-uso-de-cpu-memoria)
        - [3.4.3 MISP lento en arranque](#343-misp-lento-en-arranque)
    - [3.5 Recursos de soporte](#35-recursos-de-soporte)
        - [3.5.1 Logs de servicios](#351-logs-de-servicios)
        - [3.5.2 Comandos de diagnóstico](#352-comandos-de-diagnóstico)
        - [3.5.3 Documentación oficial](#353-documentación-oficial)
    - [3.6 Puerto o URL incorrecto para acceder a un servicio](#36-puerto-o-url-incorrecto-para-acceder-a-un-servicio)
    - [3.7 Diagnóstico de Nginx, certificados, hosts, DNS Docker y WebSockets](#37-diagnóstico-de-nginx-certificados-hosts-dns-docker-y-websockets)
    - [3.8 Recuperación de mappings e índices con advertencia de pérdida de datos](#38-recuperación-de-mappings-e-índices-con-advertencia-de-pérdida-de-datos)
    - [3.9 Validación de credenciales con make validate-credentials](#39-validación-de-credenciales-con-make-validate-credentials)
    - [3.10 Problemas de CI/CD](#310-problemas-de-cicd)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Validación de servicios Docker (FASE 3)](#51-validación-de-servicios-docker-fase-3)
    - [5.2 Limitaciones](#52-limitaciones)
    - [5.3 Riesgos o incidencias](#53-riesgos-o-incidencias)
    - [5.4 Recomendaciones / troubleshooting](#54-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Esta guía proporciona soluciones a problemas comunes que pueden surgir durante la operación del SOAR Ransomware Lab.

### 1.2 Contexto

El laboratorio SOAR Ransomware Lab integra múltiples servicios que pueden presentar problemas de configuración,
integración o rendimiento. Esta guía cubre los problemas más frecuentes y sus soluciones.

## 2. Alcance

### 2.1 Qué cubre

Esta guía cubre:

- Problemas comunes de Docker y Docker Compose
- Problemas de inicio y configuración de servicios
- Problemas de integración entre servicios
- Problemas de rendimiento y recursos
- Recursos de soporte adicionales

### 2.2 Límites

Esta guía no cubre:

- Problemas específicos de cada servicio no documentados
- Configuración avanzada de servicios
- Problemas de hardware o red externos
- Problemas de seguridad de producción

### 2.3 Dependencias

Esta guía depende de:

- [configuration_manual.md](configuration_manual.md) - Manual de configuración completo
- [architecture/docker_architecture.md](../architecture/docker_architecture.md) - Arquitectura Docker detallada
- [user_guide.md](../getting_started/user_guide.md) - Guía de usuario

## 3. Contenido principal

### 3.1 Problemas comunes de Docker

#### 3.1.1 Test paths incorrectos en Makefile.win

**Síntoma:**
Error `file or directory not found` al ejecutar `make test-atomic`, `make test-security` o `make test-performance`.

**Diagnóstico:**
Revisar los targets de test en `Makefile.win` y comprobar que los directorios referenciados existen.

**Causa:**
Los targets apuntaban a paths antiguos (`tests/e2e/test_atomic_operations.py`, etc.) que ya no existen; el repositorio ahora organiza los tests en `tests/atomic`, `tests/security` y `tests/performance`.

**Solución:**
Corregir los paths en `Makefile.win`:

```makefile
# test-atomic: de tests/e2e/test_atomic_operations.py a tests/atomic
test-atomic:
	@echo "Running atomic operation tests inside Docker container..."
	docker exec soar_api python3 -m pytest tests/atomic -v

# test-security: de tests/e2e/test_security.py a tests/security
test-security:
	@echo "Running security tests inside Docker container..."
	docker exec soar_api python3 -m pytest tests/security -v

# test-performance: de tests/e2e/test_performance.py a tests/performance
test-performance:
	@echo "Running performance tests inside Docker container..."
	docker exec soar_api python3 -m pytest tests/performance -v
```

**Verificación:**
Ejecutar `make test-atomic`, `make test-security` y `make test-performance` sin errores de path.

#### 3.1.2 Elasticsearch initialization script error

**Síntoma:**
Error de sintaxis en PowerShell al ejecutar `make up` en Windows durante la inicialización de Elasticsearch.

**Diagnóstico:**
Revisar el target de `Makefile.win` que ejecuta la inicialización de Elasticsearch y observar el error de escaping.

**Causa:**
El comando inline de PowerShell en `Makefile.win` tiene problemas de escaping de comillas.

**Solución:**
Reemplazar el comando inline por una llamada al script Python `configure_es.py`:

```makefile
# Antes (inline PowerShell con problemas de escaping)
docker exec soar_elasticsearch bash -c "curl -X PUT ..."

# Después (script Python centralizado)
docker exec soar_api python3 -m soar_lab.scripts.setup.configure_es
```

El script `src/soar_lab/scripts/setup/configure_es.py` centraliza la configuración de Elasticsearch (templates de índice, configuración de réplicas).

**Verificación:**
`make up` completa la inicialización de Elasticsearch sin errores de sintaxis.

#### 3.1.3 Docker daemon not running

**Síntoma:**
Error al ejecutar comandos de Docker; `docker ps` devuelve un error de conexión.

**Diagnóstico:**
Comprobar que Docker Desktop (Windows) o el servicio Docker (Linux) está activo.

**Causa:**
El daemon de Docker no está en ejecución.

**Solución:**
```bash
# Windows: Iniciar Docker Desktop
# Linux: Iniciar servicio Docker
sudo systemctl start docker

# Verificar estado
docker ps
```

**Verificación:**
`docker ps` lista los contenedores sin mostrar errores de conexión.

#### 3.1.4 Puertos bloqueados

**Síntoma:**
Error al iniciar servicios debido a puertos en uso.

**Diagnóstico:**
Listar los puertos en escucha del host e identificar el proceso que usa el puerto conflictivo.

**Causa:**
Otro proceso ocupa un puerto requerido por algún servicio del laboratorio.

**Solución:**
```bash
# Verificar puertos en uso
netstat -tuln | grep LISTEN

# Cambiar puertos en .env.full si es necesario
# Ejemplo: THEHIVE_HTTP_PORT=9001
```

**Verificación:**
`make up` inicia los contenedores sin errores de puerto duplicado.

#### 3.1.5 Recursos insuficientes

**Síntoma:**
Servicios se cierran o fallan al iniciar.

**Diagnóstico:**
Revisar uso de CPU/RAM del host y los logs de salida de los contenedores.

**Causa:**
El host no dispone de suficientes recursos (RAM, CPU) para ejecutar todos los servicios.

**Solución:**
- Aumentar RAM disponible (mínimo 8GB, recomendado 16GB).
- Ajustar límites de recursos en `infra/docker/compose/docker-compose*.yml`.
- Desactivar servicios no críticos (MISP, Wazuh).

**Verificación:**
Los contenedores permanecen estables tras `make up` y `docker stats` no muestra saturación.

#### 3.1.6 Imágenes no disponibles

**Síntoma:**
Error al descargar imágenes Docker (`Error response from daemon: pull access denied` o timeout).

**Diagnóstico:**
Probar un `docker pull` simple para descartar problemas de red o registro.

**Causa:**
Bloqueo de red (LaLiga/Cloudflare), imágenes no publicadas o autenticación incorrecta.

**Solución:**
```bash
# Verificar conexión a Docker Hub
docker pull hello-world

# Usar VPN si hay bloqueo LaLiga/Cloudflare
# Pre-descargar imágenes cuando no hay bloqueo
docker pull thehiveproject/thehive:latest
docker pull cortexproject/cortex:latest
docker pull shuffler/shuffle:latest
```

**Verificación:**
`docker images` muestra las imágenes necesarias y `make up` no reporta errores de pull.

### 3.2 Problemas de servicios

#### 3.2.1 Elasticsearch no inicia

**Síntoma:**
Elasticsearch falla al iniciar.

**Diagnóstico:**
Revisar logs y estado del contenedor `soar_elasticsearch` y comprobar recursos del host.

**Causa:**
Configuración de heap o recursos insuficientes, o errores de mapping/initialization.

**Solución:**
```bash
# Verificar logs
docker logs soar_elasticsearch

# Verificar memoria disponible
free -h

# Aumentar heap size en infra/docker/compose/docker-compose*.yml
# ES_JAVA_OPTS=-Xms512m -Xmx512m
```

**Verificación:**
Ejecutar `docker ps` y acceder a `http://localhost:19200/_cluster/health?pretty` (con credenciales de `.env.full`).

#### 3.2.2 Elasticsearch disk watermark assertion failure

**Síntoma:**
Test de integración `test_elasticsearch_disk_watermark` falla con `AssertionError: ES node disk at 86.0% — flood watermark at 95%`.

**Diagnóstico:**
Revisar el uso de disco del nodo Elasticsearch y el resultado del test en `tests/integration/test_smoke.py`.

**Causa:**
El test usaba un umbral demasiado estricto (`<= 85`) para el uso real de disco del host (86%), o el disco supera el 90%.

**Solución:**
Ajustar el umbral de `<= 85` a `<= 90` en `tests/integration/test_smoke.py` para acomodar el uso real de disco (86%), manteniendo advertencia antes del flood watermark al 95%.

Si el uso de disco es superior al 90%:
```bash
# Verificar uso de disco de Elasticsearch
docker exec soar_elasticsearch df -h

# Limpiar índices antiguos si es necesario
curl -u elastic:<ELASTIC_PASSWORD> -X DELETE "http://localhost:19200/*-2024-*"

# Verificar cluster health
curl -u elastic:<ELASTIC_PASSWORD> "http://localhost:19200/_cluster/health?pretty"
```

**Verificación:**
Re-ejecutar `pytest tests/integration/test_smoke.py` y comprobar que `cluster health` pasa a `green`/`yellow` sin advertencias.

**Notas:**
Después de modificar archivos de prueba, el contenedor del servicio `api` debe ser reconstruido para que los cambios surtan efecto, ya que los tests se copian en la imagen durante el build y no se montan como volúmenes:

```bash
docker compose -p soar -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env build api
docker compose -p soar -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env up -d api
```

#### 3.2.3 TheHive no responde

**Síntoma:**
TheHive no es accesible vía web.

**Diagnóstico:**
Verificar logs, estado del contenedor y respuesta HTTP del API.

**Causa:**
TheHive no ha terminado de arrancar, falló la inicialización o las credenciales/admin no se crearon.

**Solución:**
```bash
# Verificar logs
docker logs soar_thehive

# Verificar estado del servicio
docker ps | grep thehive

# Verificar healthcheck funcional (API básica disponible)
curl -s -o /dev/null -w "%{http_code}" http://localhost:19000/api/status

# Reiniciar servicio
docker restart soar_thehive

# Si persisten errores de autenticación, regenerar índice y admin
docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py
```

**Verificación:**
El healthcheck devuelve `200` y se puede acceder a la UI de TheHive.

#### 3.2.4 Cortex analyzers fallan

**Síntoma:**
Analyzers de Cortex no se ejecutan o fallan.

**Diagnóstico:**
Revisar logs de Cortex y la configuración de analyzers.

**Causa:**
Cortex no puede autenticarse con TheHive/Elasticsearch o faltan API keys externas (VirusTotal, Shodan, etc.).

**Solución:**
```bash
# Verificar logs de Cortex
docker logs soar_cortex

# Verificar configuración de analyzers
# Acceder a http://localhost:19001/#/organization/analyzer

# Verificar API keys de servicios externos
# (VirusTotal, Shodan, etc.)
```

**Verificación:**
Ejecutar un analyzer desde Cortex y comprobar que finaliza correctamente.

#### 3.2.5 Shuffle workflows fallan

**Síntoma:**
Workflows de Shuffle se quedan en "Step is still running".

**Diagnóstico:**
Revisar logs de Shuffle backend, Orborus y la conectividad de red Docker.

**Causa:**
Problemas de autenticación, apps no descargadas, red incorrecta o Orborus sin conectividad a `soar_net`.

**Solución:**
```bash
# Verificar logs de Shuffle
docker logs soar_shuffle_backend

# Verificar logs de orborus
docker logs soar_orborus

# Verificar conexión a redes Docker
docker network inspect soar_net

# Reiniciar servicios
docker restart soar_shuffle_backend soar_orborus
```

**Verificación:**
Re-ejecutar el workflow y confirmar que pasa de "Step is still running" a completado.

#### 3.2.6 Credenciales desincronizadas tras fresh deploy

**Síntoma:**
Tras ejecutar `make reset` y `make up`, TheHive y Grafana retornan errores de autenticación (`401 Unauthorized`).

**Diagnóstico:**
Revisar logs de TheHive/Grafana y los errores `401` en la UI o API.

**Causa:**
TheHive y Grafana generan nuevas credenciales internas tras un fresh deploy, pero las API keys almacenadas en `.env.full` no se actualizan automáticamente.

**Solución:**
**TheHive:**
```bash
# Ejecutar script de inicialización de TheHive dentro del contenedor API
docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py

# Si falla, reiniciar el contenedor TheHive y reintentar
docker restart soar_thehive
# Esperar 30 segundos
docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py
```

**Grafana:**
```bash
# Grafana usa credenciales por defecto admin/<GRAFANA_ADMIN_PASSWORD> en primer inicio (ver .env.full)
# Acceder a http://localhost:8084 y cambiar contraseña
# O reiniciar el contenedor para forzar reconfiguración
docker restart soar_grafana
# Esperar 30 segundos
# Acceder a http://localhost:8084 con admin/<GRAFANA_ADMIN_PASSWORD>
```

**Cortex:**
```bash
# Cortex API key se regenera automáticamente en make up
# Ejecutar reset_cortex.py para generar nueva key
docker exec soar_api python /app/src/soar_lab/scripts/setup/reset_cortex.py
```

**Verificación:**
Acceder a TheHive, Grafana y Cortex con las credenciales correctas sin errores `401`.

**Notas:**
El archivo `.env.full` se preserva tras `make reset`, pero las credenciales internas de los servicios (TheHive, Grafana) se regeneran. Para evitar este problema, se recomienda no ejecutar `make reset` a menos que sea estrictamente necesario, o implementar un mecanismo de persistencia de credenciales (ver sección 3.2.7).

#### 3.2.7 Persistencia de credenciales tras fresh deploy

**Síntoma:**
Se desea preservar credenciales de TheHive, Grafana y otros servicios tras `make reset`.

**Diagnóstico:**
Verificar que los scripts `preserve_credentials.py` y `restore_credentials.py` existen y son accesibles desde el contenedor `soar_api`.

**Causa:**
`make reset` elimina los volúmenes de datos, regenerando credenciales internas de servicios si no se preservan.

**Solución:**
```bash
# Manual: preservar credenciales antes de reset
docker exec soar_api python /app/src/soar_lab/scripts/setup/preserve_credentials.py

# Ejecutar reset
make reset

# Ejecutar up
make up

# Manual: restaurar credenciales después de up
docker exec soar_api python /app/src/soar_lab/scripts/setup/restore_credentials.py
```

**Verificación:**
Tras `make up`, comprobar que se puede acceder a TheHive/Grafana con las credenciales previas.

**Notas:**
El `Makefile.win` ya está configurado para ejecutar estos scripts automáticamente en los targets `reset` y `up`. El script `preserve_credentials.py` se ejecuta antes de detener los servicios y `restore_credentials.py` se ejecuta después de levantar los servicios.

#### 3.2.8 Docs Site no inicia

**Síntoma:**
Contenedor `soar_docs_site` se reinicia continuamente.

**Diagnóstico:**
Revisar logs del contenedor y comprobar que `sidebars.js` coincida con los archivos reales en `docs/`.

**Causa:**
IDs de documentos en `sidebars.js` no coinciden con archivos reales o imagen/docs desactualizados.

**Solución:**
```bash
# Verificar logs de docs-site
docker logs soar_docs_site --tail 50

# Error común: IDs de documentos en sidebars.js no coinciden con archivos reales
# Verificar que los archivos en docs/thesis/ coinciden con sidebars.js

# Si hay error de IDs, reconstruir el contenedor
docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d --build docs-site
```

**Verificación:**
El contenedor `soar_docs_site` permanece estable y `http://localhost:8086` muestra la documentación.

### 3.3 Problemas de integración

#### 3.3.1 Integración Shuffle → TheHive rota

**Síntoma:**
Error al crear casos en TheHive desde Shuffle.

**Diagnóstico:**
Revisar la configuración de TheHive en Shuffle (API key, URL) y los logs de error.

**Causa:**
API key incorrecta, URL mal configurada o esquema de datos incompatible.

**Solución:**
- Verificar API Key de TheHive en Shuffle.
- Verificar URL de TheHive en configuración de Shuffle.
- Validar esquema de datos del caso.
- Ejecutar tests de contrato en `tests/integration/`.

**Verificación:**
Crear un caso de prueba desde Shuffle y confirmar que aparece en TheHive.


#### 3.3.2 Integración Shuffle → Cortex rota

**Síntoma:**
Error al ejecutar analyzers desde Shuffle.

**Diagnóstico:**
Revisar la configuración de Cortex en Shuffle y el estado de los analyzers.

**Causa:**
API key o URL de Cortex incorrecta, o analyzers deshabilitados/no instalados.

**Solución:**
- Verificar API Key de Cortex en Shuffle.
- Verificar URL de Cortex en configuración de Shuffle.
- Validar que los analyzers estén habilitados en Cortex.
- Verificar que los analyzers necesarios estén instalados.

**Verificación:**
Ejecutar un analyzer desde Shuffle y comprobar que finaliza y devuelve resultados.


#### 3.3.3 Webhooks no funcionan

**Síntoma:**
Webhooks no se reciben o procesan.

**Diagnóstico:**
Revisar configuración del webhook en Shuffle, puerto y logs.

**Causa:**
URL/puerto incorrecto, token inválido, firewall o redirección mal configurada.

**Solución:**
- Verificar configuración de webhooks en Shuffle.
- Verificar que el puerto del webhook esté abierto.
- Validar el token de autenticación.
- Verificar logs de Shuffle para errores de webhook.

**Verificación:**
Enviar un evento al webhook y confirmar que Shuffle lo recibe y procesa.


### 3.4 Problemas de rendimiento

#### 3.4.1 Tiempo de respuesta excesivo

**Síntoma:**
Playbook E2E tarda más de 180s (p90).

**Diagnóstico:**
Medir tiempos por paso del workflow y revisar uso de recursos.

**Causa:**
Demasiados analyzers activos, analyzers lentos/online, recursos insuficientes o timeout corto.

**Solución:**
- Reducir número de analyzers activos.
- Priorizar analyzers offline (FileInfo, DomainMailSPFRecord).
- Aumentar timeout en configuración de Cortex.
- Verificar uso de recursos del host.

**Verificación:**
Re-ejecutar el playbook E2E y comprobar que el p90 es menor a 180s.


#### 3.4.2 Alto uso de CPU/Memoria

**Síntoma:**
Host se vuelve lento o inestable.

**Diagnóstico:**
Revisar consumo de recursos por contenedor.

```bash
docker stats
```

**Causa:**
Contenedores sin límites, servicios ineficientes o recursos insuficientes del host.

**Solución:**
- Verificar uso de recursos por contenedor.
- Ajustar límites de recursos en `infra/docker/compose/docker-compose*.yml`.
- Desactivar servicios no críticos.
- Aumentar recursos del host si es posible.

**Verificación:**
El host y los contenedores clave mantienen uso de CPU/memoria dentro de umbrales aceptables.


#### 3.4.3 MISP lento en arranque

**Síntoma:**
MISP tarda más de 3 minutos en iniciar.

**Diagnóstico:**
Revisar logs y estado de salud del contenedor MISP.

**Causa:**
MISP realiza inicializaciones pesadas (base de datos, workers) en el primer arranque.

**Solución:**
- Este comportamiento es conocido y documentado.
- `depends_on: condition: service_healthy` configurado.
- Esperar a que MISP esté healthy antes de ejecutar workflows.
- Documentado en README.md.

**Verificación:**
Comprobar `docker ps` y el healthcheck de MISP; ejecutar workflows una vez esté `healthy`.


### 3.5 Recursos de soporte

#### 3.5.1 Logs de servicios

```bash
# Ver logs de todos los servicios
docker logs soar_thehive
docker logs soar_cortex
docker logs soar_shuffle_backend
docker logs soar_orborus
docker logs soar_elasticsearch
docker logs soar_misp
```

#### 3.5.2 Comandos de diagnóstico

```bash
# Ver estado de contenedores
docker ps -a

# Ver uso de recursos
docker stats

# Ver redes Docker
docker network ls
docker network inspect soar_net

# Ver volúmenes Docker
docker volume ls
```

#### 3.5.3 Documentación oficial

- **Docker**: https://docs.docker.com/
- **Shuffle**: https://shuffler.io/docs
- **TheHive**: https://docs.strangebee.com/thehive/
- **Cortex**: https://docs.strangebee.com/cortex/
- **MISP**: https://www.misp-project.org/documentation/
- **Wazuh**: https://documentation.wazuh.com/
- **Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html

### 3.6 Puerto o URL incorrecto para acceder a un servicio

**Síntoma:**
Al acceder a un servicio se obtiene `404`, `ERR_CONNECTION_REFUSED` o se redirige a una página inesperada; no está claro si usar `http://localhost:<puerto>` o `https://soar.local/<ruta>`.

**Diagnóstico:**
Comprobar en la matriz canónica de puertos la URL y el acceso vía Nginx para el servicio concreto.

**Causa:**
Algunas UIs (Shuffle, MISP, Grafana, Docs Site, Wazuh Dashboard) no soportan subpath y deben accederse directamente por puerto; otras (Web Management, Lab API, TheHive, Cortex, Shuffle Backend) están proxyadas por Nginx bajo `/`, `/api/`, `/thehive/`, `/cortex/` y `/shuffle-api/`.

**Solución:**
Consultar la tabla canónica en `docs/operations/ports_and_urls.md` (fuente de verdad) y las variables de entorno en `docs/operations/configuration_manual.md` y `.env.full`. Usar:
- `https://soar.local` para Web Management y subpaths proxyados.
- `http://localhost:<puerto>` para servicios que no soportan subpath o para diagnóstico directo.
- Para comunicación entre contenedores, usar el nombre del servicio (`api`, `thehive`, `cortex`, `shuffle-backend`, `elasticsearch`, etc.) en `soar_net`.

**Verificación:**
Desde el host probar cada URL esperada y comprobar que devuelve código `2xx` / login.

---

### 3.7 Diagnóstico de Nginx, certificados, `hosts`, DNS Docker y WebSockets

**Síntoma:**
- `https://soar.local` no resuelve o muestra `ERR_CERT_AUTHORITY_INVALID` / `NET::ERR_CERT_COMMON_NAME_INVALID`.
- Peticiones a la API desde `http://localhost:8085` devuelven `CORS error`.
- Workflows de Shuffle fallan con `Connection refused` o `No route to host` hacia `shuffle-backend`, `elasticsearch`, `thehive` o `misp`.
- Conexiones WebSocket se cierran inmediatamente.

**Diagnóstico:**
```bash
# Validez de configuración de nginx
docker exec soar_nginx nginx -t

# Logs de nginx
docker logs soar_nginx

# Resolución DNS de los servicios en la red Docker
docker network inspect soar_net

# Resolución desde dentro de un contenedor
docker exec soar_api getent hosts shuffle-backend
docker exec soar_api getent hosts elasticsearch

# Prueba manual HTTPS con certificado autofirmado
curl -k -I https://soar.local

# Prueba WebSocket con Upgrade/Connection
curl -k -i -N \
  -H "Upgrade: websocket" \
  -H "Connection: Upgrade" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  https://soar.local/api/v1/health
```

**Causa:**
- `soar.local` no está en el archivo `hosts` del sistema operativo.
- El certificado autofirmado de `infra/docker/config/nginx/ssl/soar.local.crt` no ha sido aceptado por el navegador.
- La configuración de `nginx` no transmite correctamente las cabeceras `Upgrade` y `Connection` para WebSocket.
- Un contenedor no está en `soar_net` o el nombre de servicio no se resuelve.

**Solución:**
1. Añadir a `hosts`:
   ```
   127.0.0.1  soar.local
   ```
   - Windows: `C:\Windows\System32\drivers\etc\hosts`
   - Linux/macOS: `/etc/hosts`
2. Instalar o aceptar el certificado autofirmado. El par de claves se encuentra en `infra/docker/config/nginx/ssl/` (`soar.local.crt` / `soar.local.key`).
3. Validar que `nginx.conf` incluye `proxy_set_header Upgrade $http_upgrade;` y `proxy_set_header Connection "upgrade";` en los bloques que requieren WebSocket.
4. Aumentar timeouts si las conexiones WebSocket son cerradas por inactividad:
   ```nginx
   proxy_read_timeout 300s;
   proxy_connect_timeout 10s;
   proxy_send_timeout 300s;
   ```
5. Para CORS, verificar que la variable `CORS_ORIGINS` del contenedor `api` incluye los orígenes utilizados (`http://localhost:8085`, `http://localhost:8086`, etc.).

**Verificación:**
- `curl -k -I https://soar.local` devuelve `HTTP/2 200` (o `HTTP/1.1 200`) sin errores SSL.
- `docker exec soar_api getent hosts shuffle-backend` devuelve una IP.
- El test de WebSocket llega al backend sin cortes de conexión.

---

### 3.8 Recuperación de mappings e índices con advertencia de pérdida de datos

**Síntoma:**
- Dashboard de KPI vacío o métricas sin datos.
- Error `mapper_parsing_exception` o campos con tipo erróneo en Elasticsearch/OpenSearch.
- El índice `workflowexecution-000001` o `soar-metrics` tiene un mapping incompatible.

**Diagnóstico:**
```bash
# Listar índices
curl -s http://localhost:19200/_cat/indices?v

# Revisar mapping de soar-metrics
curl -s http://localhost:19200/soar-metrics/_mapping | python3 -m json.tool

# Logs relevantes
docker logs soar_shuffle_backend | grep -i "mapper\|mapping\|error"
```

**Causa:**
El índice se creó automáticamente con un mapping erróneo (p. ej., `mttr_seconds` como `object` en lugar de `float`, falta `@timestamp`) o un alias apunta a una versión antigua. El `auto_create_index` de Elasticsearch/OpenSearch acepta el primer documento recibido como esquema.

**Solución:**

> **ADVERTENCIA**: eliminar un índice borra todos sus documentos. Siempre realizar un backup (`make backup` o copiar los snapshots) antes de reconstruir.

1. Hacer backup:
   ```bash
   make backup
   ```
2. Eliminar el índice/alias conflictivo (ejemplo con `soar-metrics`):
   ```bash
   # En Linux/macOS desde el contenedor api o host
   curl -X DELETE http://localhost:19200/soar-metrics
   ```
3. Recrear el índice con el mapping correcto:
   ```bash
   docker exec soar_api python /app/src/soar_lab/scripts/setup/init_shuffle_webhook.py
   ```
   O para TheHive/Cortex (índice `the_hive_17` corrupto):
   ```bash
   docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py --reset
   ```
4. Si el problema es solo réplicas en un clúster de un nodo, reconfigurar:
   ```bash
   docker exec soar_api python3 -m soar_lab.scripts.setup.configure_es
   ```

**Verificación:**
- `curl -s http://localhost:19200/_cat/indices` muestra el índice recreado y `health` green/yellow.
- El mapping correcto aparece en `soar-metrics/_mapping` (por ejemplo, `mttr_seconds` tipo `float` y `@timestamp` tipo `date`).
- Grafana/Shuffle muestra datos tras reejecutar los workflows.

---

### 3.9 Validación de credenciales con `make validate-credentials`

**Síntoma:**
Tras un `make reset` / `make up`, accesos a TheHive, Cortex, Grafana o Shuffle devuelven `401 Unauthorized` o las pruebas E2E fallan por credenciales incorrectas.

**Diagnóstico:**
El target `validate-credentials` compara los valores de `.env.full` con los valores por defecto declarados en los `docker-compose.*.yml` y los scripts Python.

```bash
# Ejecutar desde la raíz del repositorio (Windows)
make validate-credentials
# o, en Linux/macOS:
make validate-credentials
```

**Causa:**
`make reset` borra volúmenes y regenera credenciales internas, pero `.env.full` conserva los valores antiguos. Los scripts y contenedores inician con los valores de `.env.full`, mientras que servicios como TheHive o Grafana crean sus propios secretos internos si el volumen de datos es nuevo.

**Solución:**
1. Ejecutar `make validate-credentials` antes y después de un reset.
2. Si detecta discrepancias:
   - Asegurar que `.env.full` contiene las credenciales actualizadas.
   - Restaurar credenciales previamente preservadas:
     ```bash
     docker exec soar_api python /app/src/soar_lab/scripts/setup/preserve_credentials.py
     make reset
     make up
     docker exec soar_api python /app/src/soar_lab/scripts/setup/restore_credentials.py
     ```
3. Regenerar un servicio concreto si es necesario:
   - TheHive: `docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py`
   - Cortex: `docker exec soar_api python /app/src/soar_lab/scripts/setup/reset_cortex.py`

**Verificación:**
`make validate-credentials` finaliza sin errores y se puede acceder a TheHive/Grafana/Shuffle con las credencias definidas en `.env.full`.

---

### 3.10 Problemas de CI/CD

El workflow `.github/workflows/ci.yml` ejecuta `markdownlint`, `lychee`, `docs_quality.py`, la validación del contrato OpenAPI y `pytest --collect-only`. `vale.yml` ejecuta Vale con `fail_on_error: false` (arranque progresivo).

**Síntoma:**

- El job `docs-quality` falla en GitHub Actions.
- `make docs-lint` devuelve errores.
- Se reciben reportes de Vale, enlaces rotos o discrepancias en OpenAPI.

**Diagnóstico:**

```bash
# Ejecutar localmente los mismos controles que CI
make docs-lint

# O paso a paso:
npx markdownlint-cli2 "docs/**/*.md" --config .markdownlint.json || true
lychee --offline docs/ README.md CONTRIBUTING.md
python src/soar_lab/scripts/ci/terminology_check.py docs/
python -m pytest tests/integration/test_openapi_spec_sync.py -v
python src/soar_lab/scripts/ci/docs_quality.py
python -m pytest --collect-only -q
vale docs/
```

**Causas comunes:**

- Markdown con líneas excesivamente largas, espacios al final de línea o encabezados desnivelados (`markdownlint`).
- Enlaces relativos rotos por renombrado de archivos (`lychee`).
- Términos no permitidos por el proyecto (`terminology_check.py`).
- `docs/api/openapi.json` desincronizado respecto a la implementación FastAPI (`test_openapi_spec_sync.py`).
- Bloques Mermaid mal cerrados o patrones prohibidos en documentación (`docs_quality.py`).
- Errores de import o clases de utilidad sin `__test__ = False` (`pytest --collect-only`).

**Solución:**

1. Corregir advertencias de `markdownlint`; mantener líneas dentro del límite configurado.
2. Actualizar enlaces rotos reportados por `lychee`.
3. Ejecutar `python src/soar_lab/scripts/ci/docs_quality.py` y corregir bloques Mermaid/patrones prohibidos.
4. Regenerar el contrato OpenAPI y reemplazar `docs/api/openapi.json`:
   ```bash
   # Linux / macOS
   PYTHONPATH=src python -c "from soar_lab.interfaces.api.composition import create_app; import json; print(json.dumps(create_app().openapi()))" > docs/api/openapi.json
   # PowerShell (Windows)
   $env:PYTHONPATH="src"; python -c "from soar_lab.interfaces.api.composition import create_app; import json; print(json.dumps(create_app().openapi()))" | Out-File -Encoding utf8 docs/api/openapi.json
   ```
5. Si `pytest --collect-only` falla, revisar imports circulares y añadir `__test__ = False` a clases de servicio con nombre `*Test*`.
6. Para Vale, ajustar el estilo o el archivo `.vale.ini`; mantener `fail_on_error: false` hasta que el corpus esté limpio.

**Verificación:**

- `python src/soar_lab/scripts/ci/docs_quality.py` imprime `Documentation quality checks passed`.
- `python -m pytest --collect-only -q` finaliza y muestra el recuento esperado.
- `lychee --offline docs/ README.md CONTRIBUTING.md` no reporta enlaces rotos internos.

### 3.11 Tests fallan por servicios no listos, recursos insuficientes o Docker Desktop

**Síntoma:**

- `make test-integration`, `make test-e2e` o `make test-all` reportan `ConnectionRefusedError`, `skipped`, timeouts o `docker.errors.DockerException`.
- Tests E2E alcanzan el timeout (`--timeout=300` o `600`).
- Resultados inconsistentes entre ejecuciones.

**Diagnóstico y solución:**

1. **Servicios aún no listos:**
   - Ejecutar `make health` antes de lanzar tests de integración/E2E. `docker compose ps` solo muestra contenedores en ejecución, no su salud interna.
   - Consultar logs: `docker compose logs -f <servicio>`.
   - Servicios como Wazuh, TheHive, OpenSearch y MISP pueden tardar varios minutos en iniciar; aumentar `HEALTHCHECK` esperas si es necesario.

2. **Recursos insuficientes:**
   - Asignar al menos 8 GB de RAM y 4 vCPU a Docker Desktop / WSL.
   - Revisar `OOMKilled`: `docker inspect <contenedor> --format='{{.State.OOMKilled}}'`.
   - Limitar memoria heap si es preciso: `ES_JAVA_OPTS`, `OPENSEARCH_JAVA_OPTS`.

3. **Docker Desktop / WSL / Windows:**
   - Activar integración WSL2 y file sharing para el directorio del repo.
   - Ejecutar `make` desde WSL2 o PowerShell (no `cmd`) para evitar problemas de interpretación de `$(...)`.
   - Si `make` no está disponible, usar `make -f Makefile.win <target>` o ejecutar WSL.
   - Algunos tests `requires_docker` requieren acceso al socket Docker (`/var/run/docker.sock`); ejecutar desde host o montar el socket correctamente.

4. **Variables de entorno / `.env.full` desactualizadas:**
   - Tras `make reset`, el `SHUFFLE_DEFAULT_APIKEY` cambia. Actualizar `.env.full` o confiar en el self-heal de `ShuffleClient`.
   - Regenerar secretos: `make generate-secrets`.

5. **Uso directo de `pytest` sin el entorno preparado:**
   - `pytest` directo no configura `.env.full`, perfiles de Compose ni servicios. Para tests que requieren Docker, usar los targets `make test-*`.
   - Verificar recolección sin errores: `python -m pytest --collect-only -q`.

**Verificación:**

- `make health` finaliza con todos los checks `OK`.
- `make test-unit` pasa sin servicios levantados.
- `make test-integration` / `make test-e2e` pasan con el stack completo y saludable.

## 4. Validación

### 4.1 Verificación

La solución de un problema se considera exitosa cuando:

- El servicio o funcionalidad afectado se restaura
- Los logs no muestran errores críticos
- El playbook E2E se ejecuta sin errores
- Las métricas de rendimiento cumplen los umbrales

### 4.2 Criterios de aceptación

El troubleshooting se considera aceptado cuando:

- El problema se resuelve sin afectar otros servicios
- La solución se documenta para futuras referencias
- Se identifican las causas raíz del problema
- Se implementan medidas preventivas

### 4.3 Evidencias

Las evidencias de solución exitosa incluyen:

- Logs de servicios sin errores
- Ejecuciones exitosas de workflows
- Métricas de rendimiento dentro de umbrales
- Documentación de la solución aplicada

## 5. Problemas y consideraciones

### 5.1 Validación de servicios Docker (FASE 3)

#### 5.1.1 Elasticsearch mapping error en Shuffle

**Síntoma:**
Shuffle backend logs muestran error: `No mapping found for [started_at]` en índice `workflowexecution-000001`.

**Diagnóstico:**
Verificar logs de Shuffle backend y consultar el mapping del índice.

**Causa:**
El índice no tiene el mapping correcto para el campo `started_at`.

**Solución:**
- Verificar mapping del índice: `curl -u elastic:<ELASTIC_PASSWORD> http://localhost:19200/workflowexecution-000001/_mapping`
- Si el campo no existe, recrear el índice con el mapping correcto o usar Shuffle API para crear workflows.

**Verificación:**
Documentado como limitación conocida; confirmar que el índice tiene el campo `started_at` antes de crear workflows.

#### 5.1.2 TheHive conector Cortex error

**Síntoma:**
TheHive API status muestra: `{"connectors":{"cortex":{"status":"ERROR"}}}`.

**Diagnóstico:**
Consultar el endpoint `/connectors` de TheHive y verificar la integración con Cortex.

**Causa:**
TheHive no tiene configurada la API key de Cortex.

**Solución:**
Configurar la API key de Cortex en TheHive:
```bash
# Editar configuración de TheHive
docker exec soar_thehive vi /etc/thehive/application.conf
# Agregar configuración de Cortex con API key
docker restart soar_thehive
```

**Verificación:**
Requiere configuración manual de API key; confirmar que el estado del conector pasa a `OK`.

#### 5.1.3 Orborus healthcheck endpoint

**Síntoma:**
Orborus no tiene un endpoint de healthcheck estándar expuesto y no responde a peticiones HTTP.

**Diagnóstico:**
Verificar estado del contenedor y logs de Orborus.

**Causa:**
Orborus no expone un endpoint HTTP público; su salud se verifica mediante Docker healthcheck.

**Solución:**
- Verificar estado del contenedor: `docker ps | grep soar_orborus`
- Verificar logs: `docker logs soar_orborus`
- El servicio funciona correctamente sin endpoint HTTP público.

**Verificación:**
Comportamiento esperado: el contenedor aparece `healthy` y los workflows se ejecutan correctamente.

#### 5.1.4 Shuffle frontend y web management connectivity

**Síntoma:**
Desde el contenedor API, Shuffle frontend y web management no responden; desde el host, ambos responden correctamente (HTTP 200).

**Diagnóstico:**
Probar conectividad desde el host con `Invoke-WebRequest`.

**Causa:**
Los servicios están configurados para acceso desde el host, no desde otros contenedores.

**Solución:**
Validar desde el host:
```powershell
Invoke-WebRequest -Uri http://localhost:8081 -UseBasicParsing  # Shuffle frontend
Invoke-WebRequest -Uri http://localhost:8085 -UseBasicParsing  # Web management
```

**Verificación:**
Resuelto: servicios accesibles desde el host y responden `HTTP 200`.

#### 5.1.5 Wazuh API autenticación JWT

**Síntoma:**
Wazuh API requiere autenticación JWT; sin token responde: `{"title": "Unauthorized", "detail": "No authorization token provided"}`.

**Diagnóstico:**
Intentar acceder sin token y verificar la respuesta `401`.

**Causa:**
Los endpoints protegidos de Wazuh requieren un JWT válido en el header `Authorization`.

**Solución:**
Obtener token JWT:
```bash
docker exec soar_api curl -k -X POST https://soar_wazuh_manager:55000/security/user/authenticate \
  -u wazuh-wui:<WAZUH_API_PASSWORD>
```
Usar el token en requests posteriores con header: `Authorization: Bearer <token>`.

**Verificación:**
Resuelto: autenticación JWT funciona correctamente.

#### 5.1.6 MISP HTTPS puerto no mapeado

**Síntoma:**
MISP está configurado para HTTPS en puerto 443 del contenedor; el puerto 80 redirige a HTTPS, pero el 443 no está mapeado al host.

**Diagnóstico:**
Verificar mapeo de puertos del contenedor MISP y acceso desde el host.

**Causa:**
Solo el puerto 80 está mapeado al host (8083), por lo que el 443 no es accesible desde fuera.

**Solución:**
- Opción 1: Mapear puerto 443 del contenedor al host en `docker-compose.misp.yml`:
  ```yaml
  ports:
    - "${MISP_PORT:-8083}:80"
    - "${MISP_HTTPS_PORT:-8443}:443"
  ```
- Opción 2: Usar MISP vía HTTP desde el contenedor (no recomendado para producción).

**Verificación:**
Limitación conocida; aplicar la opción 1 y confirmar acceso HTTPS desde el host si es necesario.

#### 5.1.7 Promtail health endpoint

**Síntoma:**
Promtail no tiene un endpoint de healthcheck estándar y no responde a peticiones HTTP en puertos conocidos.

**Diagnóstico:**
Verificar estado del contenedor y logs de Promtail.

**Causa:**
Promtail funciona como agente de recolección de logs; no expone API pública.

**Solución:**
- Verificar estado del contenedor: `docker ps | grep soar_promtail`
- Verificar logs: `docker logs soar_promtail`
- Promtail funciona como agente de recolección de logs, no expone API pública.

**Verificación:**
Comportamiento esperado: el contenedor está `running` y Loki recibe logs.

#### 5.1.8 Shuffle healthcheck deshabilitado

**Síntoma:**
Shuffle backend healthcheck retorna: `{"success": false, "reason": "Healthcheck disabled (not default). Set SHUFFLE_HEALTHCHECK_DISABLED=false to re-enable it."}`.

**Diagnóstico:**
Consultar el endpoint `/api/v1/health` del backend de Shuffle o los logs.

**Causa:**
La variable `SHUFFLE_HEALTHCHECK_DISABLED` está establecida en `true`, deshabilitando el healthcheck.

**Solución:**
Habilitar healthcheck en `docker-compose.core.yml`:
```yaml
environment:
  SHUFFLE_HEALTHCHECK_DISABLED: "false"
```
Reiniciar Shuffle backend: `docker restart soar_shuffle_backend`.

**Verificación:**
Resuelto: el endpoint de healthcheck devuelve `success: true`.


### 5.2 Limitaciones

**Limitaciones de la Guía:**

- No cubre todos los problemas posibles
- Las soluciones pueden variar según el entorno
- Algunos problemas requieren conocimientos avanzados

### 5.3 Riesgos o incidencias

**Riesgos de Troubleshooting:**

- Modificaciones de configuración pueden afectar otros servicios
- Reiniciar servicios puede causar pérdida de datos no persistidos
- Cambios en red pueden afectar conectividad

### 5.4 Recomendaciones / troubleshooting

**Recomendaciones:**

- Documentar todas las modificaciones de configuración
- Realizar backups antes de cambios importantes
- Probar soluciones en entorno de prueba primero
- Mantener actualizada la documentación del problema

### 5.5 Análisis de archivos obsoletos e incongruencias

El análisis completo está en [`docs/project/obsolete_files_analysis.md`](../project/obsolete_files_analysis.md) y [`docs/project/inconsistency_matrix.md`](../project/inconsistency_matrix.md). Puntos clave:

- Los scripts temporales de remediación (`_*.py`, `tmp_*.py`, etc.) se mantienen ignorados en `.gitignore` y no se versionan.
- `artifacts/data/` contiene datos de runtime (Elasticsearch, Wazuh, SQLite) y no debe versionarse.
- `.env.full` está en el historial de Git; si el repositorio se publica, rotar todos los secretos y purgar el historial (`git filter-repo` / `git filter-branch`).
- Algunos compose/scripts mantienen valores fallback; `.env.full` debe ser la fuente de verdad y los fallbacks deben ser placeholders, no secretos reales.

### 5.6 Riesgos y limitaciones remanentes

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Historial de Git con `.env.full` | Crítico (filtración de secretos) | No publicar el repo; rotar secretos; purgar historial con `git filter-repo` |
| `openssl` no disponible en Windows | Medio (`make certs` falla en host nativo) | Usar WSL o contenedor; instalar OpenSSL para Windows |
| Docker Desktop/WSL requerido para tests E2E | Medio (tests no ejecutan sin Docker) | Levantar stack con `make up` y `make health` antes de tests |
| Fallbacks de contraseñas en Compose | Medio | Asegurar que `.env.full` sobreescribe cualquier default; revisar `docker-compose.opensearch.yml` y `update_wazuh_compose.py` |
| Logs de contenedores pueden contener secretos si se dejan variables mal configuradas | Medio | Auditar con `docker compose logs <servicio>` y sanitizar `init_shuffle_webhook.py` |

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker**: https://docs.docker.com/
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
