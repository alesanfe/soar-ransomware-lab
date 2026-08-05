# Aplicaciones del Proyecto

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. `apps/api`](#2-appsapi)
- [3. `apps/docs-site`](#3-appsdocs-site)
- [4. `apps/web-management`](#4-appsweb-management)
- [5. Tabla resumen](#5-tabla-resumen)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe las aplicaciones del proyecto ubicadas en `apps/`. Cada aplicación se empaqueta como un
contenedor Docker independiente y cumple una función específica dentro del laboratorio SOAR.

### 1.2 Contexto

La carpeta `apps/` contiene tres aplicaciones:

- `api/` — API REST del laboratorio basada en FastAPI.
- `docs-site/` — Sitio de documentación estática generado con Docusaurus.
- `web-management/` — Panel de gestión web con HTML, CSS y JavaScript.

Cada aplicación tiene su propio `Dockerfile` y se despliega mediante `infra/docker/compose/docker-compose.api.yml`.

---

## 2. `apps/api`

**Propósito:** Contenedor principal de la API REST del laboratorio.

**Base:** `python:3.11-slim`

**Componentes:**

- `Dockerfile` — Imagen Docker con dependencias Python, pytest y código fuente.
- `api-docs.html` — Documentación HTML de la API (legacy; la documentación actual está en `docs/` y `docs/integrations/api_contracts.md`).
- `docs/` — Documentación adicional empaquetada en el contenedor (legacy).
- `pyproject.toml` — Dependencias Python del servicio.

**Punto de entrada:**

```bash
uvicorn soar_lab.interfaces.api.composition:create_app --host 0.0.0.0 --port 8000 --factory
```

**Puerto expuesto:** `8000`

**Health check:** `curl -f http://localhost:8000/health || exit 1`

**Variables de entorno principales (`.env.full`):**

- `API_PORT` — puerto host para la API (por defecto `8000`).
- `CORS_ORIGINS` — orígenes permitidos para peticiones CORS.
- `JWT_SECRET_KEY` — secret preferente para firma JWT (mínimo 32 caracteres).
- `API_AUTH_SECRET` — secret legacy para firma JWT; solo se usa si `JWT_SECRET_KEY` no está definido.
- `WEB_UI_USER` / `WEB_UI_PASSWORD` — credenciales de acceso al Web Management.
- `THEHIVE_API_KEY`, `CORTEX_API_KEY`, `SHUFFLE_DEFAULT_APIKEY`, `MISP_API_KEY`, etc.

**Redes Docker:** `soar_net`, `ti_net`, `logging_net`.

**Acceso:**

- Directo: `http://localhost:8000`.
- A través de Nginx: `https://soar.local/api/`.
- Swagger/OpenAPI: `http://localhost:8000/docs` o `https://soar.local/api/docs`.

**Funciones expuestas:**

- `/health`, `/auth/login`, `/auth/verify`.
- `/analytics/metrics`, `/analytics/kpis`.
- `/services/status`.
- `/backup/create`, `/backup/list`, `/backup/restore`.
- `/tests/run`.
- `/ws/logs` (WebSocket de logs).
- Proxy a integraciones bajo `/soar/thehive/`, `/soar/cortex/`, `/soar/misp/`, `/soar/shuffle/`, etc.

**Notas:**

- El `Dockerfile` copia `src/` y `tests/` dentro del contenedor.
- Se usa el usuario `app` para ejecutar el servicio.
- El contenedor también se utiliza para ejecutar tests.

---

## 3. `apps/docs-site`

**Propósito:** Sitio de documentación del proyecto construido con Docusaurus.

**Archivos principales:**

- `Dockerfile` — Imagen Docker basada en Node.js para servir el sitio estático.
- `docusaurus.config.js` — Configuración de Docusaurus.
- `package.json` — Dependencias Node.js.
- `sidebars.js` — Configuración de la barra lateral.
- `src/` — Código fuente y páginas del sitio.
- `docs/` — Documentación en formato Markdown.

**Puerto expuesto:** `8086` (mapeado al puerto `3000` del contenedor)

**Acceso:**

- Directo: `http://localhost:8086`.
- **No** se expone a través de Nginx con subpath; acceso directo únicamente.

**Dependencias:** Ninguna obligatoria; solo requiere la documentación Markdown en `docs/` montada en `/opt/docusaurus/docs`.

---

## 4. `apps/web-management`

**Propósito:** Panel de gestión web estático del laboratorio.

**Archivos principales:**

- `Dockerfile` — Imagen ligera basada en Nginx.
- `index.html` — Página principal del panel.
- `script.js` — Lógica JavaScript del frontend.
- `styles.css` — Hojas de estilo.
- `nginx.conf` — Configuración de Nginx para servir la aplicación.

**Puerto expuesto:** `8085` (mapeado al puerto `80` del contenedor)

**Acceso:**

- Directo: `http://localhost:8085`.
- A través de Nginx: `https://soar.local/` (raíz del proxy).

**Comunicación con la API:**

- `script.js` usa `const API_BASE = '/api'` (ruta relativa), por lo que depende de que Nginx reescriba `https://soar.local/api/` a `http://soar_api:8000`.
- El acceso directo `http://localhost:8085` **no expone `/api`**; en ese modo `script.js` intentará `http://localhost:8000/api/...`, que tampoco estará disponible en el puerto 8085. Para desarrollo o pruebas directas, setear `API_BASE = 'http://localhost:8000'` temporalmente y permitir `CORS_ORIGINS`.
- El token JWT se almacena en `localStorage`; no debe guardarse en cookies sin `HttpOnly`.
- Reconexión WebSocket contra `/ws/logs` (o `/api/ws/logs` si pasa por Nginx); Nginx transmite `Upgrade` y `Connection`.

**Nota:** Si se accede directamente por `http://localhost:8085`, asegúrate de que `CORS_ORIGINS` incluye `http://localhost:8085` y considera que `/api` no estará disponible sin un proxy inverso.

---

## 5. Tabla resumen

| Aplicación | Servicio Compose | Contenedor (proyecto `soar`) | Tecnología | Puerto host | Puerto contenedor | Acceso recomendado | Vía Nginx |
|------------|------------------|------------------------------|------------|-------------|-------------------|--------------------|-----------|
| `apps/api` | `api` | `soar_api` | FastAPI / Python 3.11 | `8000` | `8000` | `http://localhost:8000` | Sí (`/api/`) |
| `apps/docs-site` | `docs-site` | `soar_docs_site` | Docusaurus / Node.js | `8086` | `3000` | `http://localhost:8086` | No |
| `apps/web-management` | `web-management` | `soar_web_management` | HTML / JS / Nginx | `8085` | `80` | `http://localhost:8085` | Sí (`/`) |

---

## 6. Referencias

- [Arquitectura Docker](docker_architecture.md)
- [Arquitectura general](overview.md)
- [Guía de infraestructura](../operations/infrastructure_guide.md)
- [README principal](/README.md)
