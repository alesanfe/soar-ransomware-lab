---
sidebar_position: 2
---

# Instalación

## Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 16 GB RAM recomendado (mínimo 8 GB)
- 50 GB de espacio en disco

## Inicio Rápido

### 1. Configurar variables de entorno

Edita el archivo `.env.full` en la raíz del proyecto con tus credenciales:

```bash
nano .env.full
```

Variables clave a cambiar antes del primer arranque:

```bash
ELASTIC_PASSWORD=<contraseña_segura>
SHUFFLE_DEFAULT_PASSWORD=<contraseña_segura>
THEHIVE_SECRET=<secreto_seguro>
MISP_ADMIN_PASSWORD=<contraseña_segura>
WAZUH_API_PASSWORD=<contraseña_segura>
```

### 2. Arrancar el stack

```bash
make up
```

### 3. Verificar que todo está healthy

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Todos los contenedores deben mostrar `(healthy)`.

### 4. Parar el stack

```bash
make down
```

## Servicios y URLs

| Servicio            | Acceso recomendado       | Acceso directo              |
|---------------------|--------------------------|-----------------------------|
| Nginx (proxy)       | https://soar.local/      | http://localhost (→ HTTPS)  |
| Web Management UI   | https://soar.local/      | http://localhost:8085       |
| API REST            | https://soar.local/api/  | http://localhost:8000       |
| Documentación       | —                        | http://localhost:8086/docs/ |
| TheHive           | https://soar.local/thehive/ | http://localhost:9000     |
| Cortex            | https://soar.local/cortex/  | http://localhost:19001    |
| Shuffle UI        | —                          | http://localhost:8081      |
| Wazuh Dashboard   | —                          | https://localhost:15601    |
| Grafana           | —                          | http://localhost:8084      |
| MISP              | —                          | https://localhost:8083     |

> Nota: los subpath por Nginx (`/thehive/`, `/cortex/`, `/api/`) solo funcionan a través de `https://soar.local/`. Las interfaces que no soportan subpath (Shuffle, Wazuh Dashboard, MISP, Grafana, docs-site) se acceden por su puerto directo.

## Notas para Windows (Docker Desktop)

Algunos puertos pueden estar reservados por Hyper-V. Comprueba los rangos excluidos con:

```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```

Si un puerto está excluido, cámbialo en `.env.full` y vuelve a ejecutar `make up`.
