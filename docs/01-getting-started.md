# Getting Started — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
 - [1.1 Objetivo](#11-objetivo)
 - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
 - [2.1 Qué cubre](#21-qué-cubre)
 - [2.2 Límites](#22-límites)
 - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
 - [3.1 Visión general](#31-visión-general)
 - [3.2 Requisitos previos](#32-requisitos-previos)
 - [3.3 Instalación](#33-instalación)
 - [3.4 Primer acceso](#34-primer-acceso)
 - [3.5 Flujo básico de uso](#35-flujo-básico-de-uso)
 - [3.6 Guía rápida de usuario](#36-guía-rápida-de-usuario)
- [4. Validación](#4-validación)
 - [4.1 Verificación](#41-verificación)
 - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
 - [4.3 Evidencias](#43-evidencias)
- [5. Problemas](#5-problemas)
 - [5.1 Limitaciones](#51-limitaciones)
 - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
 - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones-troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento proporciona una visión general, guía de instalación y guía de usuario del SOAR Ransomware Lab, un laboratorio mínimo viable (MSV) diseñado para la respuesta automatizada ante incidentes de ransomware. Integra instrucciones paso a paso para instalar, configurar y utilizar el entorno en tu máquina local.

### 1.2 Contexto

El SOAR Ransomware Lab es un entorno de laboratorio basado en Docker Compose que integra múltiples herramientas de seguridad: orquestación (Shuffle SOAR), gestión de casos (TheHive), análisis de amenazas (Cortex), inteligencia de amenazas (MISP), Elasticsearch, Grafana y una API propia (FastAPI). El laboratorio automatiza la respuesta ante incidentes de ransomware en un entorno controlado y seguro.

> **Nota:** Las acciones de contención activa sobre endpoints (aislamiento de red, bloqueo de cuentas, contención de endpoints) están **simuladas** salvo que se desplieguen agentes EDR reales en endpoints gestionados.

---

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Propósito y objetivos del laboratorio
- Componentes principales y su función
- Casos de uso típicos
- Requisitos de hardware y software
- Arquitectura de alto nivel del sistema
- Instalación de dependencias y despliegue del stack
- Configuración inicial de servicios
- Guía de usuario: acceso a servicios, comandos principales y flujo de uso

### 2.2 Límites

Este documento no cubre:

- Detalle de configuración avanzada de cada servicio
- Integración con sistemas externos
- Despliegue en entornos de producción
- Hardening de seguridad adicional
- Arquitectura técnica detallada (ver `docs/02-architecture.md`)

### 2.3 Dependencias

Este documento depende de:

- `docs/02-architecture.md` — Arquitectura detallada
- `docs/02-architecture.md` — Arquitectura Docker detallada
- `docs/04-operations.md` — Tabla canónica de puertos y URLs

---

## 3. Contenido principal

### 3.1 Visión general

#### 3.1.1 Propósito del laboratorio

El SOAR Ransomware Lab tiene como propósito principal:

- **Automatización**: Orquestar respuestas automatizadas ante incidentes de ransomware
- **Validación**: Validar la integración de herramientas SOAR en un entorno controlado
- **Aprendizaje**: Proporcionar un entorno educativo para aprender sobre SOAR y respuesta a incidentes
- **Investigación**: Permitir experimentación con workflows de seguridad y análisis de amenazas

#### 3.1.2 Componentes principales

El laboratorio integra los siguientes componentes principales:

**Plataformas de orquestación y gestión de casos:**

- **Shuffle SOAR**: plataforma de orquestación de workflows de seguridad (v2.2.1).
- **TheHive**: plataforma de gestión de casos e incidentes (v3.5.2).
- **Cortex**: motor de análisis de observables e IOCs (v3.1.4).

**Inteligencia de amenazas y SIEM:**

- **MISP**: plataforma de inteligencia de amenazas.
- **Elasticsearch**: motor de búsqueda y métricas usado por TheHive, Cortex, Shuffle y Grafana.

**Aplicaciones propias:**

- **Lab API** (`apps/api`): API FastAPI con autenticación JWT, alertas, métricas, backups, tests y WebSocket de logs.
- **Web Management** (`apps/web-management`): SPA HTML/JS consumidora de la API; acceso por Nginx (`/`) y directo (`8085`).
- **Docs Site** (`apps/docs-site`): portal Docusaurus con la documentación del proyecto (`8086`).

**Infraestructura y soporte:**

- **Redis**: cache/cola con autenticación por contraseña.
- **MariaDB**: base de datos de MISP (`misp_db`).
- **PostgreSQL**: base de datos de Grafana (`grafana-db`).
- **Nginx**: proxy inverso y terminación TLS; punto de entrada canónico `https://soar.local`.
- **Loki + Promtail + Grafana**: stack de observabilidad centralizado (logs y KPIs).
- **Network Watcher**: servicio de diagnóstico y recuperación de conectividad para Shuffle workers.
- **Orborus**: ejecutor de contenedores de analizadores de Shuffle/Cortex.
- **Tenzir Node**: nodo de ingestión de logs/alertas (modo desarrollo).

> **Estado funcional:** Las capacidades de respuesta activa (aislamiento de red, bloqueo de cuentas, contención de endpoints) están **simuladas** salvo que se desplieguen agentes reales en endpoints gestionados.

#### 3.1.3 Casos de uso

El laboratorio soporta los siguientes casos de uso:

**Respuesta a incidentes:**

- **Respuesta a ransomware** (simulada/parcial): detección y contención automatizada de incidentes de ransomware. Los workflows generan casos, notificaciones e IOCs, pero el aislamiento real de endpoints requiere agentes EDR desplegados.
- **Gestión de casos** (implementada): creación, enriquecimiento y seguimiento de casos en TheHive a partir de alertas del SOAR.

**Análisis de amenazas:**

- **Análisis de IoCs** (implementada): ejecución de analizadores de Cortex sobre IPs, dominios, hashes y URLs.
- **Enriquecimiento de alertas** (implementada): consulta de MISP y otras fuentes de inteligencia desde Shuffle para enriquecer observables.

**Validación y aprendizaje:**

- **Validación de integraciones** (implementada): pruebas unitarias, de integración, E2E, atómicas y de rendimiento ejecutadas con pytest y validadas vía Makefile.
- **Aprendizaje** (implementada): entorno educativo para experimentar con arquitectura hexagonal, pipelines SOAR e integraciones de seguridad.

#### 3.1.4 Arquitectura de alto nivel

El laboratorio sigue una arquitectura basada en contenedores Docker con las siguientes características:

**Modelo de despliegue:**

- **Single-host**: Todos los servicios ejecutan en un único host
- **Contenedores Docker**: Cada servicio se ejecuta en un contenedor aislado
- **Docker Compose**: Orquestación de servicios mediante `docker compose`

**Redes y comunicación:**

- **Redes Docker**: Múltiples redes aisladas (`soar_net`, `logging_net`, `ti_net`, `misp_net`) para comunicación entre servicios
- **Health checks**: Verificación de salud de servicios
- **Reverse proxy**: Nginx para acceso centralizado a servicios web

**Persistencia y almacenamiento:**

- **Persistencia de datos**: bind mounts bajo `runtime/data/` para mayoría de servicios; volúmenes Docker normales para `misp_db` y dashboard.
- **Elasticsearch**: motor de búsqueda y métricas usado por TheHive, Cortex, Shuffle y Grafana.
- **PostgreSQL**: base de datos de Grafana (`grafana-db`).
- **MariaDB**: base de datos de MISP (`misp_db`).
- **Redis**: cache/cola con autenticación por contraseña.

---

### 3.2 Requisitos previos

#### 3.2.1 Requisitos de hardware

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

#### 3.2.2 Requisitos de software

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+ (versión canónica definida en `pyproject.toml` y en el workflow de CI)
- **Git**: para clonar el repositorio

#### 3.2.3 Verificación de instalación

```bash
docker --version
docker compose version
python --version
# En sistemas donde Python 3 está disponible como `python3`:
python3 --version
git --version
```

Asegúrate de que la salida de `python --version` (o `python3 --version`) indique **3.11 o superior**. En entornos con varias versiones, utiliza el intérprete que cumpla este requisito para ejecutar los scripts del proyecto.

---

### 3.3 Instalación

Salvo que se indique lo contrario, **todos los comandos de esta sección se ejecutan desde la raíz del repositorio** (`soar-ransomware-lab`).

#### 3.3.1 Clonar el repositorio

```bash
git clone https://github.com/alesanfe/soar-ransomware-lab.git
cd soar-ransomware-lab
```

#### 3.3.2 Configurar variables de entorno

El archivo canónico de configuración es **`.env.full`**. Se genera automáticamente a partir de `.env.example` (plantilla saneada con marcadores de relleno) y reemplaza todos los secretos por valores aleatorios:

```bash
# Linux / macOS / Windows
make generate-secrets
# o directamente:
python scripts/setup/generate_env.py
```

Tras generarlo, revisa `.env.full` y ajusta los valores no secretos (puertos, hosts, perfiles) antes del despliegue.

> **Nota sobre `.env.full` vs `.env` / `docker/.env`:** El proyecto no utiliza un archivo `docker/.env`. Los comandos `docker compose` manuales documentados cargan explícitamente **`.env.full`** con `--env-file .env.full`. Los targets de `Makefile` / `Makefile.win` generan una copia local `.env` (con paths absolutos resueltos) desde `.env.full` en el paso [3/19] de `make up`, y usan `--env-file .env`. Si existiera un `.env` adicional en la raíz, podría interferir; por eso los ejemplos manuales incluyen siempre `--env-file .env.full`. Mantén la información sensible solo en `.env.full` (la copia `.env` se regenera automáticamente y no debe editarse manualmente).

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

#### 3.3.3 Configurar DNS local y certificados SSL

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
   scripts/setup/gen_certs.sh
   ```

3. (Opcional) Importar `infra/docker/config/nginx/ssl/soar.local.crt` como autoridad de confianza en el navegador para evitar advertencias de certificado. En Windows, usa el complemento *Certificados* (`certmgr.msc`) → *Autoridades de certificación raíz de confianza* → *Importar*.

4. Generar certificados del indexer (solo en despliegue nuevo):

   El generador utiliza certificados TLS propios para la comunicación segura entre el manager, el indexer y el dashboard. El archivo `infra/docker/compose/docker-compose.yml` levanta temporalmente el generador oficial de certificados y deposita los archivos en el directorio configurado. Ejecuta el siguiente comando desde la raíz del repositorio:

   ```bash
   docker compose -f infra/docker/compose/docker-compose.yml run --rm generator
   ```

   El generador crea los certificados necesarios para `.indexer`, `.dashboard` y `.manager`, junto con el certificado de la CA (`root-ca.pem`) y el par de claves del administrador (`admin.pem` / `admin-key.pem`). Solo es necesario ejecutarlo una vez por despliegue o cuando se regeneren los certificados.

5. (Opcional) Importar la CA del indexer en el almacén de confianza del sistema o del navegador:

   - **Windows** (PowerShell como Administrador):

     ```powershell
     Import-Certificate -FilePath "infra\docker\config\root-ca.pem" -CertStoreLocation Cert:\LocalMachine\Root
     ```

   - **Linux** (Debian/Ubuntu):

     ```bash
     sudo cp root-ca.pem /usr/local/share/ca-certificates/indexer-root-ca.crt
     sudo update-ca-certificates
     ```

   - **macOS**:

     ```bash
     sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain root-ca.pem
     ```

6. Validar resolución y certificados:

   ```bash
   ping soar.local
   curl -k https://soar.local/nginx-health
   curl -k https://localhost:8202/app/login
   ```

#### 3.3.4 Desplegar el stack

**Despliegue automático (recomendado):**

En Windows (ambos comandos funcionan; `Makefile` delega a `Makefile.win`):

```bash
make up
# o
make -f Makefile.win up
```

Este comando despliega todos los servicios definidos en los archivos Docker Compose:

- Elasticsearch, Redis, TheHive, Cortex
- Shuffle (frontend + backend + orborus)
- MISP, MISP DB, MISP Modules
- Lab API, Docs Site, Web Management, Nginx
- Stack de logging: Loki, Promtail, Grafana, PostgreSQL (Grafana DB)

> **Nota:** El comando `make up` usa `.env.full` como fuente de configuración (genera una copia local `.env` con paths absolutos resueltos y la pasa a `docker compose` con `--env-file .env`). Incluye automáticamente la creación de directorios, la inicialización de la configuración del indexer y la configuración de Cortex/TheHive, además del webhook de Shuffle (`init_shuffle_webhook.py`). No es necesario ejecutar `make init-webhook` manualmente en un despliegue inicial.

**Despliegue manual (equivalente a `make up`):**

Si prefieres no usar `make`, ejecuta los siguientes pasos desde la raíz del repositorio. El orden importa porque varios archivos `-f` se combinan y el último tiene prioridad:

```bash
# 1. Crear redes y directorios necesarios (omite si ya existen)
mkdir -p runtime/data/{elasticsearch,thehive/files,cortex,shuffle/apps,shuffle/files,redis,misp/db,misp/files,misp/configs,misp/logs/{api_config,etc,queue,var_multigroups,integration_files,wodles,logs},loki,grafana} runtime/{backups,logs,results,coverage}

# 2. Levantar el stack
docker compose -p soar \
  -f infra/docker/compose/docker-compose.yml \
  -f infra/docker/compose/docker-compose.core.yml \
  -f infra/docker/compose/docker-compose.misp.yml \
  -f infra/docker/compose/docker-compose.api.yml \
  -f infra/docker/compose/docker-compose.opensearch.yml \
  -f infra/docker/compose/logging/docker-compose.logging.yml \
  --env-file .env.full up -d --build

# 3. Ejecutar los scripts de inicialización
# El resto se ejecutan dentro del contenedor soar_api para poder resolver los nombres de servicio
docker exec soar_api python /app/scripts/setup/configure_es.py
docker exec soar_api python /app/scripts/setup/reset_cortex.py
docker exec soar_api python /app/scripts/setup/init_thehive.py
docker exec soar_api python /app/scripts/setup/init_shuffle_webhook.py
```

> Si alguno de los scripts de inicialización falla por un servicio aún no listo, espera unos segundos y vuelve a ejecutarlo.

#### 3.3.5 Verificar despliegue

Tras el despliegue, verifica el estado general antes de continuar con la configuración inicial:

```bash
make health
# o
docker compose -p soar ps
```

**Verificación de servicios individuales:**

```bash
# Verificar Elasticsearch
curl -u elastic:<ELASTIC_PASSWORD> http://localhost:8200/_cluster/health

# Verificar TheHive
curl http://localhost:8100/api/status

# Verificar Cortex
curl http://localhost:8101/api/health

# Verificar API del Lab
curl http://localhost:8000/health

# Verificar Grafana
curl http://localhost:8084/api/health

# Verificar Nginx (HTTP→HTTPS)
curl -I http://localhost
```

**Verificación de integraciones:**

- Ejecutar el playbook de prueba E2E
- Verificar que se crean casos en TheHive
- Verificar que se ejecutan analyzers en Cortex
- Verificar que los workflows de Shuffle se ejecutan correctamente

**Checks post-`make up`:**

Tras ejecutar `make up`, usa este checklist para confirmar que el despliegue es funcional:

1. **Contenedores en ejecución:**

   ```bash
   docker compose -p soar ps
   # o
   make ps
   ```

2. **Healthchecks principales:**

   ```bash
   make health
   ```

   `make health` comprueba los endpoints de: TheHive (`:8100`), Cortex (`:8101`), Shuffle (`:5001`), Elasticsearch (`:8200`), API (`:8000/health`), Web Management (`:8085`), MISP (`:8083`), Dashboard del indexer, Grafana (`:8084`), Redis, Nginx y Tenzir.

3. **URLs de acceso:** Revisa la tabla de la sección [3.4.1 Puertos de acceso a servicios](#341-puertos-de-acceso-a-servicios) y confirma que las URLs responden (`curl -I` o navegador).

4. **Credenciales de acceso:**
   - Usa los valores de `.env.full` para los usuarios/contraseñas.
   - Realiza al menos un login en: Web Management (`https://soar.local`), Shuffle (`http://localhost:8081`), TheHive (`http://localhost:8100`) y Grafana (`http://localhost:8084`).
   - (Opcional) Valida la sincronización de credenciales:

     ```bash
     make validate-credentials
     ```

5. **Logs críticos:**

   ```bash
   make logs
   ```

   Si algún servicio falla, inspecciona `soar_api`, el indexer, `soar_elasticsearch` y `soar_shuffle_backend`.

---

### 3.4 Primer acceso

#### 3.4.1 Puertos de acceso a servicios

> **Fuente canónica:** consultar `docs/04-operations.md` para el listado completo de puertos, URLs y credenciales actualizadas.

| Servicio | Acceso directo (host) | Acceso vía Nginx (`https://soar.local`) | Credenciales |
|---|---|---|---|
| Nginx / Proxy | `http://localhost`, `https://localhost` | `/` | — |
| Web Management | `http://localhost:8085` | `/` | `.env.full` → `WEB_UI_USER` / `WEB_UI_PASSWORD` |
| SOAR API | `http://localhost:8000` | `/api/` | Token JWT en `Authorization: Bearer <token>` |
| SOAR API (Swagger UI) | `http://localhost:8000/docs` | — | — |
| SOAR API (ReDoc) | `http://localhost:8000/redoc` | — | — |
| SOAR API (OpenAPI JSON) | `http://localhost:8000/openapi.json` | — | — |
| Shuffle UI | `http://localhost:8081` | No soportado (SPA con rutas absolutas) | `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD` |
| MISP | `http://localhost:8083` | No soportado | `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD` |
| Grafana | `http://localhost:8084` | No soportado | `admin` / `${GRAFANA_ADMIN_PASSWORD}` |
| Docs Site | `http://localhost:8086` | No soportado | Sin autenticación |
| TheHive | `http://localhost:8100` | `/thehive/` | `admin` / contraseña generada por `init_thehive.py` (ver `.env.full`) |
| Cortex | `http://localhost:8101` | `/cortex/` | `admin` / contraseña generada por `reset_cortex.py` (ver `.env.full`) |
| Elasticsearch | `http://localhost:8200` | No expuesto | `elastic` / `ELASTIC_PASSWORD` |
| Indexer Dashboard | `https://localhost:8202` | No soportado | Ver `.env.full` |

> **Notas de acceso:**
> - El acceso recomendado para usuarios es `https://soar.local` (requiere `127.0.0.1 soar.local` en el archivo `hosts` y confianza en `soar.local.crt`).
> - Nginx escucha en 80 (redirección a HTTPS) y 443 (proxy inverso a Web Management).
> - Los puertos directos (`8081`, `8083`, `8084`, `8085`, `8086`, `8100`, `8101`, `8202`) son accesibles directamente sin pasar por Nginx. El dashboard del indexer requiere HTTPS (`https://localhost:8202`).
> - El despliegue incluye **Elasticsearch 7.10.2** para TheHive/Cortex/KPI y **OpenSearch 2.10.0** para Shuffle; el indexer es otro clúster OpenSearch interno. Ver `docs/02-architecture.md`.

#### 3.4.2 Configuración inicial de servicios

**Shuffle:**

1. Acceder a Shuffle: `http://localhost:8081/`
2. Iniciar sesión con credenciales de `.env.full` (`SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD`)
3. El workflow de ransomware se crea automáticamente durante `make up`.
4. Tras `make reset` y `make up`, Shuffle genera una nueva API key y la almacena en Elasticsearch. `SHUFFLE_DEFAULT_APIKEY` de `.env.full` puede quedar desactualizada.
   - El `ShuffleClient` se auto-sana (`_fetch_real_apikey`) leyendo la clave real de ES en runtime.
   - Para evitar warnings, actualiza `SHUFFLE_DEFAULT_APIKEY` con el valor de `reports/validation/results/webhook_info.json` o del campo `apikey` del usuario `admin` en el índice `users_<org>` de Elasticsearch.

**TheHive:**

1. Acceder a TheHive: `http://localhost:8100/`
2. Iniciar sesión con credenciales configuradas
3. La inicialización de TheHive se ejecuta automáticamente durante `make up`

**Cortex:**

1. Acceder a Cortex: `http://localhost:8101/`
2. Iniciar sesión con credenciales configuradas
3. La configuración inicial de Cortex se ejecuta automáticamente durante `make up`

---

### 3.5 Flujo básico de uso

1. `make up` — levanta todos los servicios (~5-10 min en primer arranque)
2. Abrir `http://localhost:8085` (Web Management) para verificar el estado
3. `make simulate` — envía alertas de prueba al SOAR
4. Verificar casos creados en TheHive (`http://localhost:8100`)
5. Verificar KPIs en Grafana (`http://localhost:8084`)
6. `make metrics` — genera `runtime/results/kpis.csv` con métricas

#### 3.5.1 Comandos principales

**Entorno:**

```bash
make up                # Levantar todos los servicios
make down              # Parar servicios y eliminar volúmenes
make reset             # Reset completo (destruye y recrea)
make reset && make up  # Reset seguido de levantar
make ps                # Estado de contenedores
make health            # Health checks
make logs              # Logs en tiempo real
make restart           # Reiniciar servicios
```

**Simulación y métricas:**

```bash
make simulate          # Simular 5 alertas por defecto
make simulate-malicious  # 1 alerta maliciosa
make simulate-benign     # 1 alerta benigna
make simulate-batch N=10 # N alertas
make metrics           # Calcular KPIs
```

**Tests:**

```bash
make test-unit
make test-atomic
make test-integration
make test-e2e
make test-all
make test-coverage
```

**Mantenimiento:**

```bash
make clean             # Limpiar archivos temporales
make clean-shuffle     # Limpiar ejecuciones stale de Shuffle
make backup            # Crear backup
make restore BACKUP=<nombre_del_backup>
make validate-credentials  # Validar sincronización de credenciales
make certs             # Generar certificados TLS para Nginx
make generate-secrets  # Generar contraseñas/tokens seguros
make init-webhook      # (Re)inicializar webhook de Shuffle
```

> **Windows:** usar `make -f Makefile.win` si `make` no está en PATH o hay problemas de compatibilidad.

---

### 3.6 Guía rápida de usuario

#### 3.6.1 Interfaces del sistema

**Web Management**

- **URLs:** Directa: `http://localhost:8085` · Por Nginx: `https://soar.local/`
- **Credenciales:** Ver `.env.full` → `WEB_UI_USER` / `WEB_UI_PASSWORD`
- **Descripción:** Interfaz web principal para gestión del entorno SOAR. Permite verificar el estado de los servicios, ver logs en tiempo real, ejecutar tests, crear/restaurar backups y consultar KPIs. Está implementada como SPA HTML/JS en `apps/web-management/`.

Características principales:

- Dashboard con estado de todos los servicios (online/offline).
- Visualización de métricas de CPU, RAM y disco (`/analytics/metrics`).
- KPIs (`/analytics/kpis`) y resumen de tests (`/tests/run`).
- Logs en vivo mediante WebSocket (`/api/ws/logs` vía Nginx, `/ws/logs` en acceso directo a la API).
- Creación, listado y restauración de backups (`/backup/create`, `/backup/list`, `/backup/restore`).

Comportamiento de `apps/web-management/script.js`:

- `API_BASE = '/api'` permite que la SPA funcione tanto detrás de Nginx como por acceso directo a `http://localhost:8000` (cuando `CORS_ORIGINS` lo permite).
- El login se realiza contra `POST /api/auth/login`; el token JWT se almacena en `localStorage` bajo `auth_token`.
- Al cargar, `checkAuthStatus` verifica el token con `POST /api/auth/verify`; si es inválido, lo elimina.
- Actualizaciones periódicas: métricas cada 5 s, servicios cada 10 s, KPIs cada 30 s.
- El WebSocket se abre con `wss://` o `ws://` según el protocolo de la página y la ruta `/api/ws/logs`.
- La ejecución remota de tests invoca `POST /api/tests/run` con `{category}` y muestra `passed`, `failed`, `skipped` y `coverage`.
- Los backups se gestionan con `POST /api/backup/create`, `GET /api/backup/list` y `POST /api/backup/restore`.

> **Seguridad:** El token JWT se guarda en `localStorage`; para evitar robo por XSS, el panel debe ejecutarse en un origen de confianza y no debe almacenarse en cookies sin `HttpOnly` sin otras contramedidas.

**SOAR API**

- **URL:** `http://localhost:8000`
- **Credenciales:** Token en cabecera `Authorization: Bearer <token>`
- **Descripción:** API REST principal del sistema. Proporciona endpoints programáticos para envío de alertas, consulta de métricas, gestión de casos, integración con servicios externos y más.

Endpoints principales:

- `POST /auth/login` — Autenticación y obtención de token JWT.
- `POST /auth/verify` — Verificación de token JWT.
- `GET /health` — Verificación de salud del servicio API.
- `GET /analytics/metrics` — Métricas de CPU, RAM y disco del host Docker.
- `GET /analytics/kpis` — KPIs de alertas procesadas (MTTR, detección, benignas/maliciosas).
- `GET /services/status` — Estado online/offline de los servicios principales.
- `POST /backup/create` — Creación de backups.
- `GET /backup/list` — Listado de backups disponibles.
- `POST /backup/restore` — Restauración de backups.
- `POST /tests/run` — Ejecución remota de tests Pytest (requiere token).
- `GET /docs` / `GET /openapi.json` — Documentación Swagger/OpenAPI.

> Fuente de verdad de contratos: `/openapi.json` expuesto por la propia API.

**TheHive**

- **URL:** `http://localhost:8100`
- **Credenciales:** `admin` / contraseña generada por `init_thehive.py` (ver `.env.full`)
- **Descripción:** Plataforma de gestión de casos de seguridad (SIRP). Permite crear, investigar, asignar y cerrar casos de incidentes de seguridad. Integra automáticamente alertas del sistema SOAR.

Características principales:

- Gestión de casos de seguridad con estados (Open, In Progress, Resolved, Closed)
- Asignación de casos a usuarios y equipos
- Observables (IOCs) enlazados a casos
- Integración con Cortex para análisis de amenazas
- Timeline de actividades en cada caso
- Alertas automáticas desde Shuffle workflows
- Búsqueda avanzada de casos y observables

**Cortex**

- **URL:** `http://localhost:8101`
- **Credenciales:** `admin` / contraseña generada por `reset_cortex.py` (ver `.env.full`)
- **Descripción:** Plataforma de análisis de amenazas (TIAM). Permite ejecutar analizadores sobre IOCs para obtener información de inteligencia de amenazas. Integra automáticamente con TheHive para enriquecer casos.

Características principales:

- Ejecución de analizadores sobre diferentes tipos de IOCs (IP, dominio, hash, URL, email)
- Integración con servicios de inteligencia de amenazas (VirusTotal, AlienVault, etc.)
- Resultados de análisis enlazados a casos en TheHive
- Gestión de analizadores y configuración de API keys externas
- Historial de análisis realizados
- Soporte para analizadores personalizados

**Shuffle**

- **URL:** `http://localhost:8081`
- **Credenciales:** `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD`
- **Descripción:** Plataforma de automatización de seguridad (SOAR). Permite crear workflows de respuesta automatizada a incidentes mediante una interfaz visual drag-and-drop.

Características principales:

- Editor visual de workflows drag-and-drop
- Integración con múltiples servicios (TheHive, Cortex, MISP, Elasticsearch, etc.)
- Ejecución de workflows basada en triggers (webhooks, alertas, schedules)
- Apps predefinidas para operaciones comunes (HTTP, Python, Email, Slack, etc.)
- Variables y condiciones para lógica compleja
- Historial de ejecuciones de workflows
- Workflows preconfigurados para respuesta a ransomware

**MISP**

- **URL:** `http://localhost:8083`
- **Credenciales:** `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD`
- **Descripción:** Plataforma de inteligencia de amenazas. Permite compartir y consultar IOCs con la comunidad de seguridad. Integra automáticamente con Shuffle workflows para enriquecer alertas.

Características principales:

- Gestión de eventos de amenazas con IOCs
- Sincronización con feeds de inteligencia de amenazas externos
- Enrichment automático de IOCs con información de múltiples fuentes
- Integración con Shuffle para verificación de IOCs en workflows
- API para consulta de IOCs desde otros servicios
- Gestión de organizaciones y permisos de compartición
- Soporte para diferentes tipos de IOCs (IP, dominio, hash, email, URL, etc.)

**Grafana**

- **URL:** `http://localhost:8084`
- **Credenciales:** `admin` / `${GRAFANA_ADMIN_PASSWORD}`
- **Descripción:** Plataforma de visualización de métricas. Permite crear dashboards con KPIs del sistema SOAR. Integra automáticamente con Elasticsearch para visualizar métricas de alertas procesadas, tiempos de respuesta, tasas de éxito y más.

Características principales:

- Dashboard SOAR KPI con métricas clave del sistema
- Visualización de alertas procesadas por tipo y severidad
- Gráficas de MTTR (Mean Time To Respond) por tipo de alerta
- Tasa de éxito por severidad de alerta
- Evolución temporal de alertas por tipo
- Integración con Elasticsearch como datasource
- Alertas y notificaciones basadas en umbrales
- Exportación de dashboards y configuraciones

**Indexer Dashboard**

- **URL:** `https://localhost:8202`
- **Descripción:** Plataforma de análisis de logs y seguridad. Proporciona una interfaz para visualizar y analizar logs de todos los servicios del sistema SOAR. Integra detección de amenazas, respuesta a incidentes y monitoreo de integridad de archivos.

Características principales:

- Visualización de logs de todos los servicios SOAR en tiempo real
- Reglas de detección de amenazas y alertas
- Monitoreo de integridad de archivos (FIM)
- Detección de intrusiones y vulnerabilidades
- Integración con Elasticsearch para almacenamiento de logs
- Búsqueda avanzada y filtrado de logs
- Alertas y notificaciones de seguridad

#### 3.6.2 Verificación de contenedores Docker

**Comando:** `make ps` o `docker ps --filter name=soar_`

Verificación del estado de todos los contenedores Docker del proyecto.

#### 3.6.3 Notas sobre tests E2E y el entorno

- Los tests E2E (`tests/e2e/TC-10` a `TC-14`) detectan automáticamente si se ejecutan dentro del contenedor Docker (`soar_api`) o en el host y usan las URLs correctas de Tenzir, Network Watcher, Redis y Loki gracias a `tests/e2e/conftest.py`.
- El test de disk watermark de Elasticsearch salta (`skip`) cuando el porcentaje reportado proviene del disco del host (>90%) en lugar del volumen del contenedor, ya que `_cat/allocation` puede reflejar el filesystem del host en Docker Desktop.
- El test `test_concurrent_execution_with_new_features` se salta si el entorno no puede ejecutar webhooks concurrentes bajo carga; no indica una falla funcional del workflow.
- Para ejecutar la suite completa: `make test-all`
- Última recolección: **2233 items / 328 deselected / 1905 seleccionados** (184 archivos `test_*.py`, ~2092 funciones definidas). Ver `docs/05-testing.md` y `baseline/tests_inventory.json`.

#### 3.6.4 Estado operativo final (FASE 50)

- **Credenciales:** Todos los scripts de setup e integración leen de `.env.full`; no hay contraseñas hardcodeadas en los archivos revisados.
- **Nginx / SSL:** Configuración validada con `nginx -t`; certificado `soar.local.crt` válido hasta 2027-05-18.
- **Redes Docker:** `soar_net`, `logging_net`, `ti_net` y `misp_net` correctamente definidas; `nginx` en `soar_net` y `logging_net`.
- **Logging stack:** Grafana accede a Elasticsearch `soar-metrics` y Loki recoge logs de todos los contenedores; plugin ES incluido en `docker-compose.logging.yml`.
- **Tests E2E:** Última ejecución documentada: 16/16 passed (con credenciales de `.env.full`).
- **Limpieza de archivos:** `.gitignore` ignora `runtime/data/`, scripts temporales de remediación y artefactos de pruebas; `git status` reducido de ~600 a ~520 entradas.
- **Limitación remanente:** `.env.full` permanece en el historial de Git. Rotar secretos y purgar el historial si se publica el repositorio.
- **Documentos clave generados:**
  - `docs/06-project-management.md`
  - `docs/06-project-management.md`
  - `docs/06-project-management.md`
  - `docs/06-project-management.md`

---

## 4. Validación

### 4.1 Verificación

El laboratorio se considera funcional cuando:

- Todos los servicios se inician correctamente
- Los health checks reportan estado healthy
- Los servicios son accesibles en sus puertos esperados
- Las integraciones básicas funcionan correctamente
- El playbook E2E se ejecuta sin errores

### 4.2 Criterios de aceptación

El laboratorio se considera aceptado cuando:

- El stack completo se despliega sin errores
- Todos los servicios son accesibles vía web o API
- Las credenciales configuradas funcionan correctamente
- El playbook E2E se ejecuta en ≤ 180s (p90)
- Las métricas de rendimiento cumplen los umbrales establecidos
- La documentación está completa y actualizada

### 4.3 Evidencias

Las evidencias de funcionamiento incluyen:

- Logs de contenedores sin errores críticos
- Acceso web a todos los servicios
- Ejecuciones de workflows exitosas en Shuffle
- Casos creados en TheHive
- Análisis ejecutados en Cortex
- Métricas de rendimiento recopiladas
- Ejecución exitosa del playbook E2E

---

#### 5. Problemas

##### 5.1 Limitaciones

**Limitaciones del entorno:**

- **Single-host**: el stack completo se ejecuta en un único nodo Docker; no soporta alta disponibilidad ni clustering.
- **Recursos limitados**: requiere al menos 16 GB de RAM y 4 cores para el stack completo; con 8 GB se pueden omitir perfiles opcionales.
- **Respuesta activa simulada**: el aislamiento de red, bloqueo de cuentas y contención de endpoints se simulan mediante workflows; no se ejecutan acciones reales sobre endpoints sin agentes EDR desplegados.
- **Entorno de laboratorio**: no es apto para producción sin hardening adicional (TLS revalidado, secretos rotados, firewalls, RBAC, etc.).
- **Asume entorno Windows + Docker Desktop**: la guía no cubre configuración avanzada ni integración con sistemas externos.

##### 5.2 Riesgos o incidencias

**Riesgos de seguridad:**

- Uso de contraseñas predeterminadas que deben cambiarse
- Exposición de servicios en puertos conocidos
- Necesidad de hardening adicional para producción

**Riesgos de instalación:**

- Dependencia de servicios externos (Docker Hub)
- Conflictos de puertos con otros servicios
- Requisitos de recursos no cumplidos

##### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**

- Cambiar todas las contraseñas predeterminadas
- Usar en entornos aislados o de prueba
- No desplegar en producción sin hardening adicional
- Mantener actualizaciones de seguridad de imágenes Docker
- Verificar requisitos antes de instalar
- Leer la documentación oficial de cada herramienta

**Docker daemon not running:**

```bash
# Windows
wsl --shutdown
# Linux/macOS
sudo systemctl restart docker
```

**Puertos bloqueados:**

- WSL/Hyper-V reservan puertos dinámicamente. Ejecutar como admin:

  ```powershell
  netsh int ipv4 add excludedportrange protocol=tcp startport=5001 numberofports=1
  ```

- Verificar puertos en uso:

  ```bash
  netstat -tuln | grep LISTEN
  ```

- Si eso falla, cambiar el puerto en `.env.full` y reiniciar.

**Recursos insuficientes:**

- Asignar al menos 8 GB de RAM y 4 vCPU a Docker / WSL.
- Elasticsearch consume varios GB.
- Revisar OOM: `docker inspect <contenedor> --format='{{.State.OOMKilled}}'`.
- Ajustar límites de recursos en `infra/docker/compose/docker-compose*.yml`.
- Aumentar la memoria asignada a Docker Desktop (mínimo recomendado **16 GB**, swap **4 GB**).

  ```bash
  sudo sysctl -w vm.max_map_count=262144
  # Persistir tras reinicio:
  echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
  ```

**Credenciales desactualizadas:**

```bash
cp .env.example .env.full
make generate-secrets
```

Tras `make reset`, `SHUFFLE_DEFAULT_APIKEY` puede cambiar. `ShuffleClient._fetch_real_apikey` lo lee de OpenSearch.

**CORS (errores `403` / `CORS policy` en el navegador):**

- **Síntoma**: El navegador bloquea peticiones desde Web Management hacia la API.
- **Solución**: Asegúrate de que `CORS_ORIGINS` en `.env.full` incluya todos los orígenes desde los que se accede, separados por comas. Ejemplo:

  ```text
  CORS_ORIGINS=https://soar.local,http://localhost:8085,http://localhost:3000
  ```

  Reinicia el contenedor `soar_api` para que tome la nueva variable:

  ```bash
  docker compose -p soar restart api
  ```

**SSL / certificado autofirmado:**

- **Síntoma**: El navegador muestra advertencia de seguridad o `curl` falla con error de certificado.
- **Solución**: Importa la CA local en el sistema o navegador (ver sección [3.3.3 Configurar DNS local y certificados SSL](#333-configurar-dns-local-y-certificados-ssl)). Para pruebas con `curl`, usa `-k`/`--insecure`. Verifica la validez del certificado con:

  ```bash
  openssl x509 -in infra/docker/config/nginx/ssl/soar.local.crt -noout -dates
  ```

**DNS no resuelve `soar.local`:**

- **Síntoma**: `ping soar.local` no responde.
- **Solución**: Revisa el archivo `hosts` (sección [3.3.3 Configurar DNS local y certificados SSL](#333-configurar-dns-local-y-certificados-ssl)) y limpia la caché DNS:
  - **Windows**: `ipconfig /flushdns`
  - **Linux**: `sudo systemd-resolve --flush-caches` (distros con systemd) o `sudo systemctl restart nscd`
  - **macOS**: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`

**Memoria insuficiente (Elasticsearch / Indexer / OOM):**

- Aumenta la memoria asignada a Docker Desktop (mínimo recomendado **16 GB**, swap **4 GB**).
- Ajusta `mem_limit` en los archivos `infra/docker/compose/docker-compose*.yml` si es necesario.

**Disk watermark de Elasticsearch:**

- **Síntoma**: Elasticsearch pasa a solo lectura con errores tipo `FORBIDDEN/12/index read-only / allow delete (api)`.
- **Solución**: Libera espacio en disco y elimina el bloqueo de solo lectura:

  ```bash
  curl -X PUT -u elastic:<ELASTIC_PASSWORD> "http://localhost:8200/_all/_settings" -H 'Content-Type: application/json' -d '{"index.blocks.read_only_allow_delete": null}'
  ```

  Si los umbrales por defecto son demasiado bajos para el disco del host, ajústalos temporalmente:

  ```bash
  curl -X PUT -u elastic:<ELASTIC_PASSWORD> "http://localhost:8200/_cluster/settings" -H 'Content-Type: application/json' -d '{"transient":{"cluster.routing.allocation.disk.watermark.low":"85%","cluster.routing.allocation.disk.watermark.high":"90%","cluster.routing.allocation.disk.watermark.flood_stage":"95%"}}'
  ```

**Tests E2E timeout:**

```bash
pytest tests/e2e/ -v --timeout=600
```

**Webhook no inicializado:**

```bash
make init-webhook
```

---

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Entorno single-host**: Docker Compose desplegado en una sola máquina; no soporta alta disponibilidad nativa.
- **Recursos mínimos**: 16 GB RAM para stack completo (Elasticsearch + TheHive + Cortex + Shuffle + MISP); 8 GB sin perfiles opcionales (logging, MISP).
- **Certificados autofirmados**: Nginx usa certificados generados por `scripts/setup/gen_certs.sh`; los navegadores mostrarán advertencias.
- **Shuffle webhook**: Tras `make reset`, el webhook debe regenerarse con `make init-webhook`.

### 5.2 Riesgos o incidencias

- **Puertos en uso**: Hyper-V en Windows reserva rangos 2976-3075, 5500-55099; verificar con `netstat -ano | findstr :<puerto>`.
- **Elasticsearch yellow**: Estado `yellow` es normal en single-node (no puede asignar réplicas).
- **MISP lento en arranque**: MariaDB y `misp-modules` pueden tardar > 3 min en estar healthy.
- **Bloqueo Cloudflare/LaLiga**: Durante jornadas de fútbol, los ISP españoles pueden bloquear rangos de Cloudflare, impidiendo `docker pull`.

### 5.3 Recomendaciones / troubleshooting

- **Verificar servicios**: Usar `make health` y `make ps` tras `make up`.
- **Logs**: `make logs` o `docker logs <contenedor>` para diagnosticar problemas.
- **Reset completo**: `make reset` (down + clean + up) si los servicios no responden.
- **Regenerar API keys**: `python scripts/setup/init_thehive.py` (TheHive) y `python scripts/setup/reset_cortex.py` (Cortex) tras reset.

---

#### Navegación

- [Arquitectura hexagonal, Docker, código, seguridad](02-architecture.md)
- [API REST, endpoints e integraciones](03-api-and-integrations.md)
- [Configuración, infraestructura, backups, troubleshooting](04-operations.md)
- [Estrategia de pruebas y suite](05-testing.md)
- [Objetivos, plan, riesgos, auditorías](06-project-management.md)
- [Glosario central](glossary.md)
- [Índice](index.md)
## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker**: https://docs.docker.com/
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **API**: `docs/03-api-and-integrations.md`
- **Integraciones**: `docs/03-api-and-integrations.md`
- **Testing**: `docs/05-testing.md`
- **Operaciones**: `docs/04-operations.md`
- **Proyecto**: `docs/06-project-management.md`
- **Riesgos**: `docs/06-project-management.md`
- **Arquitectura**: `docs/02-architecture.md`
- **Arquitectura Docker**: `docs/02-architecture.md`
- **Puertos y URLs**: `docs/04-operations.md`
- **Coexistencia de motores de búsqueda**: `docs/02-architecture.md`
