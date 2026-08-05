# Glosario del Proyecto SOAR Ransomware Lab

Glosario central de acrónimos, términos técnicos y componentes usados en el proyecto. Sirve como referencia única para documentación, código, tesis y operación.

## Acrónimos

| Acrónimo | Definición |
|----------|------------|
| **API** | Application Programming Interface. Contrato de comunicación entre la API FastAPI y los consumidores. |
| **CI/CD** | Continuous Integration / Continuous Deployment. Pipeline de integración y despliegue continuo. |
| **CORS** | Cross-Origin Resource Sharing. Permite peticiones desde orígenes distintos a `soar.local`/`localhost`. |
| **CSV** | Comma-Separated Values. Formato de exportación de métricas (`artifacts/results/kpis.csv`). |
| **E2E** | End-to-End. Pruebas que recorren el flujo completo del playbook. |
| **EDR** | Endpoint Detection and Response. Tecnología de detección en endpoints (referencia futura). |
| **IaC** | Infrastructure as Code. Infraestructura definida en Docker Compose, Dockerfiles y scripts. |
| **IoC** | Indicator of Compromise. Indicadores (hash, IP, dominio) usados para enriquecimiento. |
| **IP** | Internet Protocol. Dirección de red usada en observables y reglas. |
| **JSON** | JavaScript Object Notation. Formato de intercambio entre servicios y la API. |
| **JWT** | JSON Web Token. Token firmado con HS256 para autenticación en la API. |
| **KPI** | Key Performance Indicator. Métricas como MTTR, tasa de éxito y cobertura. |
| **MTTR** | Mean Time to Respond. Tiempo medio desde alerta hasta contención o cierre. |
| **MFA** | Multi-Factor Authentication. Autenticación con varios factores (futura). |
| **RBAC** | Role-Based Access Control. Control de acceso basado en roles (futuro). |
| **REST** | Representational State Transfer. Estilo arquitectónico de la API. |
| **SIEM** | Security Information and Event Management. Wazuh actúa como SIEM/XDR en el stack. |
| **SLA** | Service Level Agreement. Acuerdo de nivel de servicio, aplica a umbrales de MTTR. |
| **SOAR** | Security Orchestration, Automation and Response. Categoría del proyecto. |
| **TLS** | Transport Layer Security. Cifrado de comunicaciones Nginx/servicios. |
| **UI** | User Interface. Interfaces web (`apps/web-management`, Grafana, Shuffle). |
| **URL** | Uniform Resource Locator. Dirección de acceso a servicios. |
| **VM** | Virtual Machine. Opción de despliegue alternativa a Docker. |
| **WAF** | Web Application Firewall. Protección perimetral (referencia futura). |
| **XDR** | Extended Detection and Response. Extensión de EDR/SIEM. |
| **YAML** | YAML Ain't Markup Language. Formato de configuración de Compose y CI. |

## Componentes del stack

| Término | Descripción |
|---------|-------------|
| **TheHive** | Plataforma de gestión de casos e incidentes. |
| **Cortex** | Motor de análisis de observables e IoCs. |
| **Shuffle** | Plataforma de orquestación SOAR con flujos visuales. |
| **MISP** | Malware Information Sharing Platform. |
| **Wazuh** | SIEM/XDR open source. |
| **Elasticsearch** | Almacén de búsqueda y métricas (`soar-metrics`). |
| **Grafana** | Visualización de métricas y logs. |
| **Loki** | Agregación de logs accedida desde Grafana. |
| **Promtail** | Agente de envío de logs a Loki. |
| **Nginx** | Proxy inverso y terminación TLS. |
| **MariaDB** | Base de datos de TheHive. |
| **PostgreSQL** | Base de datos de Cortex y Grafana. |
| **Redis** | Caché y broker de mensajes. |
| **FastAPI** | Framework de la API de gestión. |
| **Pytest** | Framework de testing. |

## Estados funcionales

- **Implementado**: componente operativo y verificado en CI/E2E.
- **Parcial**: funcionalidad básica operativa con limitaciones documentadas.
- **Simulado**: respuesta o acción simulada (p. ej. contención) sin efecto real sobre endpoints.
- **Planificado**: aprobado para futura implementación, no desplegado aún.
- **No verificado**: documentado pero pendiente de validación reproducible.
- **Histórico**: documentación o artefacto de referencia anterior, posiblemente obsoleto.

## Fuentes de verdad

- **Código**: `src/soar_lab/`, `apps/`, `infra/`.
- **Contratos API**: `docs/api/openapi.json`.
- **Inventario de tests**: `baseline/tests_inventory.json` / salida de `pytest --collect-only`.
- **Infraestructura**: archivos `docker-compose*.yml`, `.env.example` y `pyproject.toml`.
- **Configuración de CI**: `.github/workflows/ci.yml`, `.github/workflows/vale.yml`.

> Para el glosario académico de la tesis, ver [`docs/thesis/glossary.md`](../thesis/glossary.md).
