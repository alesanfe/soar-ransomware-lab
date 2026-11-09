# Matriz común de roles y permisos (UI-GLOBAL-002)

> Modelo objetivo RBAC del laboratorio. La columna "implementación actual"
> muestra cómo se aproxima hoy cada rol; la columna "objetivo" el estado
> deseado tras UI-GLOBAL-003 (SSO) y OSD-001.

## Roles

| Rol | Descripción | Implementación actual |
| --- | --- | --- |
| `platform-admin` | Administrador de plataforma | admin Shuffle, admin Grafana, OrgAdmin Cortex, admin MISP, admin web-management, admin TheHive |
| `soc-analyst-l2` | Analista con capacidad de respuesta | TheHive analyst + web-management JWT |
| `soc-analyst-l1` | Triage, lectura de alertas/casos | TheHive read + web-management JWT |
| `incident-responder` | Acciones de contención | — (pendiente: acciones operativas WEB-006) |
| `auditor` | Solo lectura global | — (pendiente: rol read-only transversal) |
| `infra-operator` | Estado de servicios, sin datos de casos | web-management JWT (services view) |
| `service-account` | Integración API | API keys TheHive/Cortex/MISP, Shuffle apikey, elastic |

## Permisos por vista/acción

| Vista / acción | L1 | L2 | Responder | Auditor | Infra-op | Platform-admin |
| --- | --- | --- | --- | --- | --- | --- |
| Dashboard estado/KPIs | R | R | R | R | R | RW |
| Cola admisión/DLQ | R | R | R | R | RW | RW |
| Feed de decisiones | R | R | R | R | R | RW |
| Detalle ejecución | R | R | R | R | R | RW |
| Casos/alerts TheHive | R | RW | RW | R | — | RW |
| Jobs Cortex | R | R | R | R | — | RW |
| Eventos MISP | R | RW | RW | R | — | RW |
| Workflows Shuffle | R | R | RW | R | — | RW |
| Dashboards Grafana | R | R | R | R | R | RW |
| OpenSearch Discover | R | R | R | R | R | RW |
| Docs-site | R | R | R | R | R | R |
| Reintentar/cancelar ejecución | — | — | RW | — | — | RW |
| Reprocesar DLQ | — | — | RW | — | RW | RW |
| Gestión backups | — | — | — | — | RW | RW |
| Configuración/secrets | — | — | — | — | — | RW |
| Exportaciones | — | R | R | — | — | RW |

R = lectura · RW = lectura+escritura · — = sin acceso.

## Controles exigidos (verificables)

1. Un usuario de solo lectura no puede modificar configuración — test:
   llamada autenticada con rol `auditor` a endpoints POST/PUT/DELETE → 403.
2. Un usuario no autenticado no accede a información operativa — test:
   sin credenciales → 401/redirect en todas las superficies salvo
   docs-site y excepciones del risk-register (OSD-002).
3. Acciones críticas solo por métodos mutadores con CSRF/confirmación
   (WEB-006, WEB-012).
