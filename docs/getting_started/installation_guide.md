# Guía de Instalación del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Requisitos previos](#31-requisitos-previos)
        - [3.1.1 Requisitos de hardware](#311-requisitos-de-hardware)
        - [3.1.2 Requisitos de software](#312-requisitos-de-software)
        - [3.1.3 Verificación de instalación](#313-verificación-de-instalación)
    - [3.2 Proceso de instalación](#32-proceso-de-instalación)
        - [3.2.1 Clonar el repositorio](#321-clonar-el-repositorio)
        - [3.2.2 Configurar variables de entorno](#322-configurar-variables-de-entorno)
        - [3.2.3 Desplegar el stack completo](#323-desplegar-el-stack-completo)
        - [3.2.4 Verificar estado de servicios](#324-verificar-estado-de-servicios)
    - [3.3 Configuración inicial](#33-configuración-inicial)
        - [3.3.1 Configuración de Shuffle](#331-configuración-de-shuffle)
        - [3.3.2 Configuración de TheHive](#332-configuración-de-thehive)
        - [3.3.3 Configuración de Cortex](#333-configuración-de-cortex)
    - [3.4 Verificación de instalación](#34-verificación-de-instalación)
        - [3.4.1 Verificación de servicios](#341-verificación-de-servicios)
        - [3.4.2 Verificación de integraciones](#342-verificación-de-integraciones)
    - [3.5 Solución de problemas](#35-solución-de-problemas)
        - [3.5.1 Docker daemon not running](#351-docker-daemon-not-running)
        - [3.5.2 Puertos bloqueados](#352-puertos-bloqueados)
        - [3.5.3 Recursos insuficientes](#353-recursos-insuficientes)
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

Esta guía proporciona instrucciones paso a paso para instalar y configurar el SOAR Ransomware Lab en tu entorno local.

### 1.2 Contexto

El laboratorio SOAR Ransomware Lab se basa en Docker Compose para desplegar múltiples servicios de seguridad
orquestación (SOAR) en un entorno controlado. Esta guía asume que tienes conocimientos básicos de Docker y línea de
comandos.

## 2. Alcance

### 2.1 Qué cubre

Esta guía cubre:

- Requisitos de hardware y software
- Instalación de dependencias
- Clonación del repositorio
- Configuración de variables de entorno
- Despliegue del stack con Docker Compose
- Verificación de la instalación

### 2.2 Límites

Esta guía no cubre:

- Configuración avanzada de cada servicio
- Integración con sistemas externos
- Despliegue en entornos de producción
- Hardening de seguridad adicional

### 2.3 Dependencias

Esta guía depende de:

- [overview.md](overview.md) - Visión general del laboratorio
- [user_guide.md](user_guide.md) - Guía de usuario detallada
- [architecture/docker_architecture.md](../architecture/docker_architecture.md) - Arquitectura Docker detallada

## 3. Contenido principal

### 3.1 Requisitos previos

#### 3.1.1 Requisitos de hardware

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

#### 3.1.2 Requisitos de software

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (versión canónica definida en `pyproject.toml` y en el workflow de CI)
- **Git**: para clonar el repositorio

#### 3.1.3 Verificación de instalación

```bash
docker --version
docker compose version
python --version
# En sistemas donde Python 3 está disponible como `python3`:
python3 --version
git --version
```

Asegúrate de que la salida de `python --version` (o `python3 --version`) indique **3.11 o superior**. En entornos con varias versiones, utiliza el intérprete que cumpla este requisito para ejecutar los scripts del proyecto.

### 3.2 Proceso de instalación

Salvo que se indique lo contrario, **todos los comandos de esta sección se ejecutan desde la raíz del repositorio** (`soar-ransomware-lab`). Tras clonar, sitúate en el directorio del proyecto con:

```bash
cd soar-ransomware-lab
```

#### 3.2.1 Clonar el repositorio

```bash
git clone https://github.com/alesanfe/soar-ransomware-lab.git
cd soar-ransomware-lab
```

#### 3.2.2 Configurar variables de entorno

El archivo canónico de configuración es **`.env.full`**. Se genera automáticamente a partir de `.env.example` (plantilla saneada con marcadores de relleno) y reemplaza todos los secretos por valores aleatorios:

```bash
# Linux / macOS / Windows
make generate-secrets
# o directamente:
python src/soar_lab/scripts/setup/generate_env.py
```

Tras generarlo, revisa `.env.full` y ajusta los valores no secretos (puertos, hosts, perfiles) antes del despliegue.

> **Nota sobre `.env.full` vs `.env` / `docker/.env`:** El proyecto no utiliza un archivo `docker/.env`. Todos los targets de `Makefile` / `Makefile.win` y los comandos `docker compose` documentados cargan explícitamente **`.env.full`** con `--env-file .env.full`. Si existiera un `.env` en la raíz del repositorio, un `docker compose` ejecutado sin `--env-file` podría leerlo por defecto; por eso los ejemplos manuales incluyen siempre `--env-file .env.full`. Mantén la información sensible solo en `.env.full` y nunca la copies a `.env` ni la versiones.

Variables críticas a revisar antes del despliegue:

- `JWT_SECRET_KEY`: Secret preferente de firma de tokens JWT (mínimo 32 caracteres).
- `JWT_EXPIRATION_MINUTES`: Tiempo de expiración del token (por defecto 60 minutos).
- `JWT_ALGORITHM`: Algoritmo de firma (por defecto `HS256`).
- `WEB_UI_USER` / `WEB_UI_PASSWORD`: Credenciales de acceso al Web Management.
- `API_AUTH_SECRET`: Secret legacy de firma JWT; solo se usa si `JWT_SECRET_KEY` no está definido.
- `CORS_ORIGINS`: Orígenes permitidos para CORS (por ejemplo `https://soar.local,http://localhost:8085`).
- `ELASTIC_PASSWORD`: Contraseña de Elasticsearch.
- `REDIS_PASSWORD`: Contraseña de Redis.
- `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD`: Credenciales admin de Shuffle.
- `THEHIVE_SECRET` / `THEHIVE_API_KEY`: Secret y API key de TheHive.
- `CORTEX_SECRET` / `CORTEX_API_KEY`: Secret y API key de Cortex.
- `SIEM_WEBHOOK_TOKEN` / `EDR_SIM_TOKEN` / `FIREWALL_SIM_TOKEN`: Tokens de simulación de integraciones.

> **Nunca subas `.env.full` ni `.env` a Git.** Ambos nombres están en `.gitignore`.

#### 3.2.3 Configurar DNS local y certificados SSL

El laboratorio usa `soar.local` como dominio interno y Nginx termina TLS con certificados autofirmados. Antes de desplegar:

1. Añadir `soar.local` al archivo hosts del sistema operativo:

   **Linux / macOS:**

   ```bash
   sudo sh -c 'echo "127.0.0.1 soar.local" >> /etc/hosts'
   ```

   **Windows:** El archivo hosts está en `C:\Windows\System32\drivers\etc\hosts`. Abre **Notepad como Administrador**, selecciona *Archivo → Abrir* y navega a esa ruta literal. Añade al final:

   ```text
   127.0.0.1 soar.local
   ```

   También puedes ejecutar en una PowerShell con privilegios de administrador:

   ```powershell
   Add-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value "127.0.0.1 soar.local"
   ```

   Valida que la entrada existe:

   ```bash
   # Linux / macOS
   grep soar.local /etc/hosts

   # Windows (PowerShell)
   Select-String -Path "C:\Windows\System32\drivers\etc\hosts" -Pattern "soar.local"
   ```

2. Generar certificados para Nginx (si no existen):

   ```bash
   make certs
   # o manualmente
   src/soar_lab/scripts/setup/gen_certs.sh
   ```

3. (Opcional) Importar `infra/docker/config/nginx/ssl/soar.local.crt` como autoridad de confianza en el navegador para
   evitar advertencias de certificado. En Windows, usa el complemento *Certificados* (`certmgr.msc`) → *Autoridades de certificación raíz de confianza* → *Importar*.

4. Generar certificados de Wazuh Indexer (solo en despliegue nuevo):

   Wazuh utiliza certificados TLS propios para la comunicación segura entre el manager, el indexer y el dashboard. El archivo `infra/docker/wazuh/generate-indexer-certs.yml` levanta temporalmente el generador oficial de certificados de Wazuh y deposita los archivos en el directorio configurado. Ejecuta el siguiente comando desde la raíz del repositorio:

   ```bash
   docker compose -f infra/docker/wazuh/generate-indexer-certs.yml run --rm generator
   ```

   El generador utiliza la imagen `wazuh/wazuh-certs-generator:0.0.2` y crea los certificados necesarios en `infra/docker/wazuh/config/wazuh_indexer_ssl_certs/` para `wazuh.indexer`, `wazuh.dashboard` y `wazuh.manager`, junto con el certificado de la CA (`root-ca.pem`) y el par de claves del administrador (`admin.pem` / `admin-key.pem`). Solo es necesario ejecutarlo una vez por despliegue o cuando se regeneren los certificados.

5. (Opcional) Importar la CA de Wazuh en el almacén de confianza del sistema o del navegador:

   El certificado raíz usado por Wazuh se encuentra en `infra/docker/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem`. Importarlo evita advertencias de seguridad al acceder al Wazuh Dashboard en `https://localhost:15601`.

   - **Windows** (PowerShell como Administrador):

     ```powershell
     Import-Certificate -FilePath "infra\docker\wazuh\config\wazuh_indexer_ssl_certs\root-ca.pem" -CertStoreLocation Cert:\LocalMachine\Root
     ```

   - **Linux** (Debian/Ubuntu):

     ```bash
     sudo cp infra/docker/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem /usr/local/share/ca-certificates/wazuh-root-ca.crt
     sudo update-ca-certificates
     ```

   - **macOS**:

     ```bash
     sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain infra/docker/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem
     ```

   - **Navegadores**: importar `infra/docker/wazuh/config/wazuh_indexer_ssl_certs/root-ca.pem` en las *Autoridades de certificación raíz de confianza*.

6. Validar resolución y certificados:

   ```bash
   ping soar.local
   curl -k https://soar.local/nginx-health
   curl -k https://localhost:15601/app/login
   ```

#### 3.2.4 Despliegue automático

**En Windows (ambos comandos funcionan; `Makefile` delega a `Makefile.win`):**

```bash
make up
# o
make -f Makefile.win up
```

Este comando despliega todos los servicios definidos en los archivos Docker Compose:

- Elasticsearch, Redis, TheHive, Cortex
- Shuffle (frontend + backend + orborus)
- MISP, MISP DB, MISP Modules
- Wazuh Manager, Wazuh Dashboard
- Lab API, Docs Site, Web Management, Nginx
- Stack de logging: Loki, Promtail, Grafana, PostgreSQL (Grafana DB)

**Nota:** El comando `make up` usa el archivo `.env.full` para configuración de variables de entorno.

**Nota:** `make up` incluye automáticamente la creación de directorios, la inicialización de la configuración de Wazuh y la configuración de Cortex/TheHive, además del webhook de Shuffle (`init_shuffle_webhook.py`). No es necesario ejecutar `make init-webhook` manualmente en un despliegue inicial.

**Nota:** En Windows, usar `Makefile.win` que contiene comandos PowerShell compatibles con el sistema operativo.

#### 3.2.5 Despliegue manual (equivalente a `make up`)

Si prefieres no usar `make`, ejecuta los siguientes pasos desde la raíz del repositorio. El orden importa porque varios archivos `-f` se combinan y el último tiene prioridad:

```bash
# 1. Crear redes y directorios necesarios (omite si ya existen)
mkdir -p artifacts/data/{elasticsearch,thehive/files,cortex,shuffle/apps,shuffle/files,redis,misp/db,misp/files,misp/configs,misp/logs,wazuh/{api_config,etc,queue,var_multigroups,integration_files,wodles,logs},loki,grafana} artifacts/{backups,logs,results,coverage}

# 2. Levantar el stack
docker compose -p soar \
  -f infra/docker/compose/docker-compose.yml \
  -f infra/docker/compose/docker-compose.core.yml \
  -f infra/docker/compose/docker-compose.misp.yml \
  -f infra/docker/compose/docker-compose.wazuh.yml \
  -f infra/docker/compose/docker-compose.api.yml \
  -f infra/docker/compose/docker-compose.opensearch.yml \
  -f infra/docker/compose/logging/docker-compose.logging.yml \
  --env-file .env.full up -d --build

# 3. Ejecutar los scripts de inicialización
#    - seed_wazuh.py se ejecuta en el host porque crea directorios y arranca un contenedor Docker temporal.
#    - El resto se ejecutan dentro del contenedor soar_api para poder resolver los nombres de servicio (elasticsearch, cortex, thehive, shuffle-backend) en soar_net.
python src/soar_lab/scripts/setup/seed_wazuh.py

docker exec soar_api python /app/src/soar_lab/scripts/setup/configure_es.py
docker exec soar_api python /app/src/soar_lab/scripts/setup/reset_cortex.py
docker exec soar_api python /app/src/soar_lab/scripts/setup/init_thehive.py
docker exec soar_api python /app/src/soar_lab/scripts/setup/init_shuffle_webhook.py
```

> Si alguno de los scripts de inicialización falla por un servicio aún no listo, espera unos segundos y vuelve a ejecutarlo.

#### 3.2.6 Validación del despliegue

Tras el despliegue, verifica el estado general antes de continuar con la configuración inicial:

```bash
make health
# o
docker compose -p soar ps
```

### 3.3 Configuración inicial

#### 3.3.1 Puertos de acceso a servicios

| Servicio               | URL                            | Notas                               |
|------------------------|--------------------------------|-------------------------------------|
| Web Management (Nginx) | https://soar.local             | Dashboard principal vía HTTPS 443   |
| SOAR API (base)        | http://localhost:8000          | API REST del laboratorio            |
| SOAR API (Swagger UI)  | http://localhost:8000/docs     | Documentación interactiva OpenAPI   |
| SOAR API (ReDoc)       | http://localhost:8000/redoc    | Documentación OpenAPI alternativa   |
| SOAR API (OpenAPI JSON)| http://localhost:8000/openapi.json | Esquema OpenAPI exportable      |
| Shuffle UI             | http://localhost:8081          | Motor SOAR                          |
| MISP                   | http://localhost:8083          | Threat Intelligence                 |
| Grafana                | http://localhost:8084          | KPI Dashboard                       |
| Web Management directo | http://localhost:8085          | Acceso directo sin Nginx            |
| Docs Site              | http://localhost:8086          | Documentación Docusaurus            |
| TheHive                | http://localhost:19000        | Gestión de casos                    |
| Cortex                 | http://localhost:19001         | Analyzers                           |
| Elasticsearch          | http://localhost:19200         | Motor de búsqueda                   |
| Wazuh Dashboard        | https://localhost:15601         | SIEM Dashboard                      |

**Notas de acceso:**

- Nginx escucha en 80 (redirección a HTTPS) y 443 (proxy inverso a Web Management).
- Los servicios con puertos directos (`8081`, `8083`, `8084`, `8085`, `8086`, `19000`, `19001`, `15601`)
  son accesibles directamente sin pasar por Nginx. El Wazuh Dashboard requiere HTTPS (`https://localhost:15601`).
- Wazuh Manager/Indexer/Dashboard requieren una contraseña de alta complejidad: mayúsculas, minúsculas, números y un carácter especial como `.` o `-` (sin `@` ni `!`).
  Ejemplo: `<WAZUH_API_PASSWORD>` (valor real en `.env.full` bajo `WAZUH_API_PASSWORD`, `WAZUH_INDEXER_PASSWORD` y `WAZUH_DASHBOARD_PASSWORD`).

#### 3.3.2 Configuración de Shuffle

1. Acceder a Shuffle: http://localhost:8081/
2. Iniciar sesión con credenciales de `.env.full` (`SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD`)
3. El workflow de ransomware se crea automáticamente durante `make up`.
4. Tras `make reset` y `make up`, Shuffle genera una nueva API key y la almacena en Elasticsearch. `SHUFFLE_DEFAULT_APIKEY` de `.env.full` puede quedar desactualizada.
   - El `ShuffleClient` se auto-sana (`_fetch_real_apikey()`) leyendo la clave real de ES en runtime.
   - Para evitar warnings, actualiza `SHUFFLE_DEFAULT_APIKEY` con el valor de `artifacts/webhook_info.json` o del campo `apikey` del usuario `admin` en el índice `users_<org>` de Elasticsearch.

#### 3.3.3 Configuración de TheHive

1. Acceder a TheHive: http://localhost:19000/
2. Iniciar sesión con credenciales configuradas
3. La inicialización de TheHive se ejecuta automáticamente durante `make up`

#### 3.3.4 Configuración de Cortex

1. Acceder a Cortex: http://localhost:19001/
2. Iniciar sesión con credenciales configuradas
3. La configuración inicial de Cortex se ejecuta automáticamente durante `make up`

### 3.4 Verificación de instalación

#### 3.4.1 Verificación de servicios

```bash
# Verificar Elasticsearch
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:19200/_cluster/health

# Verificar TheHive
curl http://localhost:19000/api/status

# Verificar Cortex
curl http://localhost:19001/api/health

# Verificar API del Lab
curl http://localhost:8000/health

# Verificar Grafana
curl http://localhost:8084/api/health

# Verificar Nginx (HTTP→HTTPS)
curl -I http://localhost
```

#### 3.4.2 Verificación de integraciones

- Ejecutar el playbook de prueba E2E
- Verificar que se crean casos en TheHive
- Verificar que se ejecutan analyzers en Cortex
- Verificar que los workflows de Shuffle se ejecutan correctamente

#### 3.4.3 Checks post-`make up`

Tras ejecutar `make up`, usa este checklist para confirmar que el despliegue es funcional antes de pasar a la configuración inicial:

1. **Contenedores en ejecución:**

   ```bash
   docker compose -p soar ps
   # o
   make ps
   ```

   Todos los servicios críticos (`soar_api`, `soar_nginx`, `soar_elasticsearch`, `soar_thehive`, `soar_cortex`, `soar_shuffle_backend`, `soar_wazuh_*`, `soar_grafana`) deben aparecer como `Up`.

2. **Healthchecks principales:**

   ```bash
   make health
   ```

   `make health` comprueba los endpoints de: TheHive (`:19000`), Cortex (`:19001`), Shuffle (`:15001`), Elasticsearch (`:19200`), API (`:8000/health`), Web Management (`:8085`), MISP (`:8083`), Wazuh Dashboard, Grafana (`:8084`), Redis, Nginx y Tenzir.

3. **URLs de acceso:**

   Revisa la tabla de la sección [3.3.1 Puertos de acceso a servicios](#331-puertos-de-acceso-a-servicios) y confirma que las URLs responden (`curl -I` o navegador).

4. **Credenciales de acceso:**

   - Usa los valores de `.env.full` para los usuarios/contraseñas.
   - Realiza al menos un login en: Web Management (`https://soar.local`), Shuffle (`http://localhost:8081`), TheHive (`http://localhost:19000`) y Grafana (`http://localhost:8084`).
   - (Opcional) Valida la sincronización de credenciales:

     ```bash
     make validate-credentials
     ```

5. **Logs críticos:**

   ```bash
   make logs
   ```

   Si algún servicio falla, inspecciona `soar_api`, `soar_wazuh_indexer`, `soar_elasticsearch` y `soar_shuffle_backend`.

### 3.5 Solución de problemas

#### 3.5.1 Docker daemon not running

**Síntoma**: Error al ejecutar comandos de Docker

**Solución**:

```bash
# Iniciar Docker Desktop (Windows)
# O iniciar servicio Docker (Linux)
sudo systemctl start docker
```

#### 3.5.2 Puertos bloqueados

**Síntoma**: Error al iniciar servicios debido a puertos en uso

**Solución**:

```bash
# Verificar puertos en uso
netstat -tuln | grep LISTEN

# Cambiar puertos en .env.full si es necesario
```

#### 3.5.3 Recursos insuficientes

**Síntoma**: Servicios se cierran o fallan al iniciar

**Solución**:

- Aumentar RAM disponible
- Ajustar límites de recursos en `infra/docker/compose/docker-compose*.yml`
- Desactivar servicios no críticos

#### 3.5.4 CORS, SSL, DNS, memoria y disk watermark

**CORS (errores `403` / `CORS policy` en el navegador)**

- **Síntoma**: El navegador bloquea peticiones desde Web Management hacia la API.
- **Solución**: Asegúrate de que `CORS_ORIGINS` en `.env.full` incluya todos los orígenes desde los que se accede, separados por comas. Ejemplo:

  ```text
  CORS_ORIGINS=https://soar.local,http://localhost:8085,http://localhost:3000
  ```

  Reinicia el contenedor `soar_api` para que tome la nueva variable:

  ```bash
  docker compose -p soar restart api
  ```

**SSL / certificado autofirmado**

- **Síntoma**: El navegador muestra advertencia de seguridad o `curl` falla con error de certificado.
- **Solución**: Importa la CA local en el sistema o navegador (ver sección [3.2.3 Configurar DNS local y certificados SSL](#323-configurar-dns-local-y-certificados-ssl)). Para pruebas con `curl`, usa `-k`/`--insecure`. Verifica la validez del certificado con:

  ```bash
  openssl x509 -in infra/docker/config/nginx/ssl/soar.local.crt -noout -dates
  ```

**DNS no resuelve `soar.local`**

- **Síntoma**: `ping soar.local` no responde.
- **Solución**: Revisa el archivo `hosts` (sección [3.2.3 Configurar DNS local y certificados SSL](#323-configurar-dns-local-y-certificados-ssl)) y limpia la caché DNS:
  - **Windows**: `ipconfig /flushdns`
  - **Linux**: `sudo systemd-resolve --flush-caches` (distros con systemd) o `sudo systemctl restart nscd`
  - **macOS**: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`

**Memoria insuficiente (Elasticsearch / Wazuh / OOM)**

- **Síntoma**: Contenedores se reinician, logs muestran `OutOfMemory` o Elasticsearch/Wazuh no arranca.
- **Solución**:
  - Aumenta la memoria asignada a Docker Desktop (mínimo recomendado **16 GB**, swap **4 GB**).
  - Ajusta `mem_limit` en los archivos `infra/docker/compose/docker-compose*.yml` si es necesario.
  - En Linux, configura `vm.max_map_count=262144` para Elasticsearch y Wazuh:

    ```bash
    sudo sysctl -w vm.max_map_count=262144
    # Persistir tras reinicio:
    echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
    ```

**Disk watermark de Elasticsearch**

- **Síntoma**: Elasticsearch pasa a solo lectura con errores tipo `FORBIDDEN/12/index read-only / allow delete (api)`.
- **Solución**: Libera espacio en disco y elimina el bloqueo de solo lectura:

  ```bash
  curl -X PUT -u elastic:<ELASTIC_PASSWORD> "http://localhost:19200/_all/_settings" -H 'Content-Type: application/json' -d '{"index.blocks.read_only_allow_delete": null}'
  ```

  Si los umbrales por defecto son demasiado bajos para el disco del host, ajústalos temporalmente:

  ```bash
  curl -X PUT -u elastic:<ELASTIC_PASSWORD> "http://localhost:19200/_cluster/settings" -H 'Content-Type: application/json' -d '{"transient":{"cluster.routing.allocation.disk.watermark.low":"85%","cluster.routing.allocation.disk.watermark.high":"90%","cluster.routing.allocation.disk.watermark.flood_stage":"95%"}}'
  ```

## 4. Validación

### 4.1 Verificación

La instalación se considera exitosa cuando:

- Todos los servicios se inician y reportan estado healthy
- Los servicios son accesibles en sus puertos esperados
- Las integraciones básicas funcionan correctamente

### 4.2 Criterios de aceptación

La instalación se considera aceptada cuando:

- El stack completo se despliega sin errores
- Todos los servicios son accesibles vía web o API
- Las credenciales configuradas funcionan correctamente
- El playbook E2E se ejecuta sin errores

### 4.3 Evidencias

Las evidencias de instalación exitosa incluyen:

- Logs de contenedores sin errores críticos
- Acceso web a todos los servicios
- Ejecución exitosa del playbook E2E
- Métricas de rendimiento dentro de umbrales

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de la Guía:**

- Asume entorno Windows + Docker Desktop
- No cubre configuración avanzada
- No cubre integración con sistemas externos

### 5.2 Riesgos o incidencias

**Riesgos de Instalación:**

- Dependencia de servicios externos (Docker Hub)
- Conflictos de puertos con otros servicios
- Requisitos de recursos no cumplidos

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**

- Leer la documentación oficial de cada herramienta
- Verificar requisitos antes de instalar
- Usar entornos aislados para pruebas
- Mantener actualizaciones de seguridad

**Recursos de Soporte:**

- Documentación oficial de Docker: https://docs.docker.com/
- Documentación de Shuffle: https://shuffler.io/docs
- Documentación de TheHive: https://docs.strangebee.com/thehive/
- Documentación de Cortex: https://docs.strangebee.com/cortex/

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker**: https://docs.docker.com/
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
