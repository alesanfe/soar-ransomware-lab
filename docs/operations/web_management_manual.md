# Manual de Web Management

## 1. Resumen

`apps/web-management` es el dashboard web central del SOAR Ransomware Lab. Se sirve a través de Nginx en
`https://soar.local` (puertos 80/443) y, de forma directa, en `http://localhost:8085`.

## 2. Acceso

| Modo | URL | Credenciales |
|---|---|---|
| Via Nginx (recomendado) | `https://soar.local` | `admin` / `WEB_UI_PASSWORD` (`.env.full`) |
| Directo | `http://localhost:${WEB_UI_PORT:-8085}` | `admin` / `WEB_UI_PASSWORD` (`.env.full`) |

> Requisito: tener `soar.local` resuelto a `127.0.0.1` en `/etc/hosts` o `C:\Windows\System32\drivers\etc\hosts`.

El SPA usa rutas relativas (`const API_BASE = '/api'`) para funcionar tanto por puerto directo como detrás de Nginx. Nginx expone el Lab API bajo el subpath `/api/`.

## 3. Funcionalidades principales

- **Estado de servicios**: tabla con salud de cada contenedor, basada en `GET /services/status` de la API.
- **Métricas del host**: CPU, memoria y disco (`GET /analytics/metrics`).
- **KPIs del laboratorio**: MTTR, detecciones, histogramas (`GET /analytics/kpis` y `GET /analytics/kpis/aggregated`).
- **Tests**: lanzar suites de pruebas desde el navegador (`POST /tests/run`) con categoría `unit`, `integration`, `e2e`, `smoke`, `all`.
- **Backups**: crear (`POST /backup/create`) y restaurar (`POST /backup/restore`) backups con un nombre.
- **Logs en tiempo real**: WebSocket `/ws/logs` que transmite logs del contenedor `soar_api`.
- **Acciones de contención**: registro de acciones simuladas `pending`, `executed`, `failed`.

## 4. Autenticación y flujo WebSocket

La aplicación web (`apps/web-management/script.js`) implementa un SPA que se autentica contra la Lab API.

### 4.1 Llamadas a la API

- **Base URL**: `const API_BASE = '/api'` (ruta relativa). Esto funciona cuando el SPA se sirve a través de Nginx (`https://soar.local`), que enruta `/api/` al contenedor `soar_api:8000`.
- **URLs exactas** usadas por el front:
  - Login: `POST /api/auth/login` con `{username, password}`
  - Verificar token: `POST /api/auth/verify` con `Authorization: Bearer <token>`
  - Métricas: `GET /api/analytics/metrics`
  - KPIs: `GET /api/analytics/kpis`
  - Estado de servicios: `GET /api/services/status`
  - Lanzar tests: `POST /api/tests/run`
  - Backups: `POST /api/backup/create`, `POST /api/backup/restore`, `GET /api/backup/list`
- **Acceso directo por `http://localhost:8085`**: Nginx no está en medio, por lo que `/api` no se enruta automáticamente a `soar_api`. Se recomienda acceder a través de `https://soar.local` para que las rutas relativas funcionen correctamente.

### 4.2 Manejo del token

- Tras un login exitoso, el front almacena `data.token` en `localStorage` como `auth_token`.
- Cada petición a la API incluye la cabecera `Authorization: Bearer <auth_token>` a través de `getAuthHeaders()`.
- Al cargar la página, `checkAuthStatus()` envía el token a `POST /api/auth/verify`. Si el token es inválido o ha expirado, se elimina de `localStorage` y se vuelve a la pantalla de login.
- `logout()` elimina `auth_token` y detiene las actualizaciones periódicas.

### 4.3 WebSocket de logs (`/ws/logs`)

- **URL construida dinámicamente**:
  ```javascript
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`;
  ```
- La conexión se abre al pulsar el botón *Start Live Logs* y se cierra al pulsar *Stop Live Logs*.
- `ws.onmessage` recibe entradas JSON del log parser y las añade a la interfaz.
- `ws.onerror` y `ws.onclose` muestran un mensaje de error y resetean el botón a *Start Live Logs*.
- **Reconexión**: actualmente no existe reconexión automática; si el WebSocket se cierra, el usuario debe volver a pulsar *Start Live Logs*. Si se desea reconexión automática, implementar un backoff exponencial en `startWebSocketLogs()`.

### 4.4 Seguridad del front

- El token JWT reside en `localStorage`, por lo que una vulnerabilidad XSS podría comprometer la sesión. El frontend no almacena contraseñas.
- Se recomienda servir siempre la web-management a través de Nginx con HTTPS (`https://soar.local`).

## 5. Requisitos previos

- Todos los servicios levantados con `make up`.
- La API en `http://localhost:8000` (o por Nginx `https://soar.local/api`) debe estar saludable.
- Variables `API_AUTH_SECRET`, `WEB_UI_USER` y `WEB_UI_PASSWORD` en `.env.full`.

## 6. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ERR_CONNECTION_REFUSED` en `https://soar.local` | Nginx no arrancó o `soar.local` no está en hosts | `docker compose ps nginx`; añadir `127.0.0.1 soar.local` |
| Login incorrecto | Contraseña distinta a `.env.full` | Actualizar `WEB_UI_PASSWORD` y reiniciar `web-management` |
| Logs vacíos | WebSocket cerrado o API no inyectó `websocket_manager` | Verificar `docker logs soar_api` |
| Tests no devuelven resultado | `test_runner` no disponible o contenedor sin tests | Revisar `pytest` en contenedor `soar_api` |
| Métricas a 0 | `system_metrics` no configurado | Verificar que `psutil` esté instalado y `system_metrics` esté en `CompositionRoot` |

## 7. Referencias

- [Especificación de APIs](../integrations/api_contracts.md)
- [Arquitectura general](../architecture/overview.md)
- [Composition Root](../architecture/composition_root.md)
