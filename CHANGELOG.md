# Changelog — SOAR Ransomware Lab

Toda la historia detallada de cambios académicos y de implementación se mantiene en:

- [docs/thesis/CHANGELOG_THESIS_UPDATE.md](docs/thesis/CHANGELOG_THESIS_UPDATE.md)

## [Unreleased]

### Documentation
- Revisión exhaustiva y corrección de inconsistencias en toda la documentación del proyecto.
- Sincronización de `README.md` con todos los servicios Docker Compose y estructura del repositorio.
- Corrección de referencias a archivos, clases y rutas en docs de arquitectura y operaciones.
- Actualización de tablas de puertos, versiones y variables de entorno contra compose files reales.

## v1.4.0 (2026-07-18)

- Infraestructura Docker Compose completa con Nginx, TheHive, Cortex, Shuffle, MISP, Elasticsearch,
 Grafana/Loki/Promtail.
- Playbook E2E de respuesta a ransomware (37 escenarios TC: TC-01 a TC-32 + TC-KPI-01 a TC-KPI-05).
- API FastAPI con autenticación JWT, métricas, backups, tests y WebSocket de logs.
- Documentación remediada: métricas de tests, matrices de puertos/versiones, guías de operaciones, arquitectura
 hexagonal y contratos API.
- Matriz de estado real/simulado/planificado documentada.
