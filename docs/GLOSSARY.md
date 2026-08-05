# Glosario de Acrónimos del SOAR Ransomware Lab

Este documento define los acrónimos y términos técnicos que se usan en toda la documentación del proyecto. Se recomienda mantenerlo como referencia central y consultarlo antes de introducir nuevos términos en guías, manuales o memoria académica.

## Acrónimos principales

| Acrónimo | Expansión en inglés | Significado en español | Contexto en el proyecto |
|----------|---------------------|------------------------|-------------------------|
| **CORS** | Cross-Origin Resource Sharing | Intercambio de recursos de origen cruzado | Configuración de la Lab API (`src/soar_lab/config/settings.py`); lista de orígenes permitidos en `CORS_ORIGINS`.
|
| **E2E** | End-to-End | Extremo a extremo | Tests que ejecutan workflows completos y validan integraciones reales (`tests/e2e/`).
|
| **IaC** | Infrastructure as Code | Infraestructura como código | Orquestación del laboratorio mediante Docker Compose, Makefiles y Vagrant.
|
| **JWT** | JSON Web Token | Token web JSON | Mecanismo de autenticación de la Lab API; firmado con `HS256` y gestionado por `AuthService` y `JWTTokenProvider`.
|
| **KPI** | Key Performance Indicator | Indicador clave de rendimiento | Métricas observadas del flujo de respuesta, como `MTTR` o porcentajes de respuesta.
|
| **MFA** | Multi-Factor Authentication | Autenticación multifactor | Capacidad **planificada/no verificada** en el laboratorio actual.
|
| **MTTR** | Mean Time to Respond/Recover | Tiempo medio de respuesta (o recuperación) | Métrica principal del dashboard de KPIs; segundos transcurridos desde la detección hasta la finalización del workflow.
|
| **P50** | 50th percentile | Percentil 50 (mediana) | Valor observado por debajo del cual se sitúa el 50 % de las mediciones.
|
| **P90** | 90th percentile | Percentil 90 | Valor observado por debajo del cual se sitúa el 90 % de las mediciones.
|
| **SIEM** | Security Information and Event Management | Gestión de eventos e información de seguridad | Capa de ingestión y correlación de alertas (Elasticsearch/OpenSearch, Wazuh).
|
| **SOAR** | Security Orchestration, Automation and Response | Orquestación, automatización y respuesta de seguridad | Plataforma central del proyecto (Shuffle, Cortex, TheHive, Lab API).
|
| **SSO** | Single Sign-On | Inicio de sesión único | Capacidad **planificada/no verificada** en el laboratorio actual.
|
| **WAF** | Web Application Firewall | Cortafuegos de aplicaciones web | Capacidad **no verificada**; Nginx actúa como proxy inverso sin módulo WAF activo.
|

## Términos relacionados con testing

- **Collección/collected**: casos de prueba encontrados por `pytest` durante la fase de recolección.
- **Deselected**: casos excluidos por marcadores (`-m`) o filtros.
- **Selected**: casos que finalmente se ejecutarán.
- **Skipped**: casos omitidos en runtime mediante `pytest.skip` (por ejemplo, falta de dependencia externa).
- **Xfail**: caso marcado como fallo esperado; no se usa masivamente en este repositorio, pero puede aparecer en pruebas experimentales.
- **Smoke test**: prueba rápida post-despliegue para verificar que el stack está operativo.
- **Atomic test**: prueba aislada de un componente o escenario con dependencias mínimas.

## Términos relacionados con métricas

- **Observada**: valor real obtenido de las ejecuciones del workflow y almacenado en `soar-metrics`.
- **Objetivo**: valor deseado o umbral de mejora continua definido por el equipo.
- **Umbral (`threshold_p50`, `threshold_p90`)**: valor límite que una métrica observada no debería superar.
- **Cobertura (`coverage`)**: porcentaje de código fuente ejecutado por los tests.

## Uso en documentación

- Al usar un acrónimo por primera vez en un documento, escribir la expansión completa seguida del acrónimo entre paréntesis.
- No emplear acrónimos en títulos de sección sin haberlos definido previamente en el documento.
- Mantener este glosario actualizado cuando se introduzcan nuevos términos técnicos.
