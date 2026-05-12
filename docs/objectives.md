# Objetivos SMART (EDT 1.2)

> Este documento presenta los objetivos SMART del proyecto y su relación con la Estructura de Desglose del Trabajo (EDT), indicando dónde se almacenarán las pruebas y evidencias en el repositorio para garantizar la trazabilidad y validación académica.

---

## Introducción

El proyecto se basa en la EDT definida y el contexto del laboratorio SOAR para respuesta ante incidentes de ransomware. Cada objetivo está alineado con las tareas del EDT y vinculado con la estructura del repositorio, asegurando trazabilidad y organización académica rigurosa.

Las evidencias se almacenarán en:
- **Pruebas Unitarias y E2E**: `tests/`
- **Resultados y Métricas**: `artifacts/results/kpis.csv`
- **Documentación Técnica y Validación**: `docs/test_report.md`
- **Logs del Flujo**: `artifacts/logs/`

---

## Tabla de Objetivos SMART y Ubicación de Evidencias

| Nº | Objetivo | Descripción | Métrica | Umbral | Método de Medida | Evidencia |
|----|----------|-------------|---------|--------|-------------------|-----------|
| 1  | Implementación del Laboratorio | Desplegar entorno reproducible con TheHive, Cortex y Shuffle mediante Docker Compose. | Servicios activos | 100% contenedores funcionando | Verificación con `docker ps` | Capturas en `docs/technical.md` |
| 2  | Desarrollo del Playbook E2E | Crear flujo automatizado desde alerta hasta contención simulada. | Ejecución completa | 2 escenarios (malicioso y benigno) | Logs del SOAR y casos en TheHive | Evidencias en `tests/e2e/` |
| 3  | Validación de Métricas MTTR | Medir tiempo de respuesta desde alerta hasta contención. | Percentiles p50 y p90 | p50 ≤ 120 s; p90 ≤ 180 s | Timestamps y cálculo estadístico | `artifacts/results/kpis.csv` y `docs/test_report.md` |
| 4  | Documentación Técnica | Generar documentación completa (arquitectura, configuración, resultados). | Documento final | 100% apartados completados | Checklist y revisión del tutor | `docs/` (architecture.md, playbook_manual.md) |
| 5  | Integración SIEM Simulada | Configurar SIEM simulado para generar alertas. | Alertas procesadas | 100% sin errores | Logs en Shuffle y casos en TheHive | `scripts/send_alert.py` + capturas en `docs/test_report.md` |
| 6  | Contención Simulada | Implementar scripts para aislamiento y bloqueo. | Acciones ejecutadas | 100% completadas | Logs del script y confirmación en flujo | `scripts/isolate_host.sh` y `isolate_endpoint.ps1` |
| 7  | Seguridad del Entorno | Garantizar uso exclusivo de muestras inertes. | Incidentes | 0 incidentes | Revisión del contenido y validación | `docs/security.md` |
| 8  | Automatización Opcional | Implementar despliegue con Ansible/Vagrant. | Despliegue automático | 100% servicios levantados | Ejecución del script y verificación | `vagrant/` y `ansible/` |
| 9  | Pruebas Funcionales | Ejecutar pruebas completas del laboratorio. | Casos probados | 100% escenarios validados | Informe con evidencias | `tests/e2e/` y `docs/test_report.md` |
| 10 | KPIs y Análisis | Calcular KPIs y presentar resultados. | KPIs calculados | Informe con gráficos | Análisis estadístico y visualización | `artifacts/results/kpis.csv` y `docs/test_report.md` |
| 11 | Preparación Defensa TFM | Crear presentación y resumen ejecutivo. | Presentación lista | 100% diapositivas completadas | Validación por tutor y ensayo | Carpeta `docs/` (closure.md) |
| 12 | Evidencia de Aprobación | Obtener validación formal del alcance y objetivos. | Archivo firmado | Documento archivado | Confirmación por correo y almacenamiento | Carpeta `docs/` (plan.md) |

---

## Relación con EDT y Repositorio

Cada objetivo corresponde a tareas específicas del EDT:
- **Infraestructura (EDT 4.x)**: Objetivos 1, 8.
- **Playbook y scripts (EDT 5.x, 6.x)**: Objetivos 2, 5, 6.
- **Pruebas y métricas (EDT 7.x)**: Objetivos 3, 9, 10.
- **Documentación y cierre (EDT 8.x)**: Objetivos 4, 11, 12.

La estructura del repositorio soporta esta organización, con carpetas dedicadas para pruebas (`tests/`), resultados (`artifacts/results/`), documentación (`docs/`) y scripts (`scripts/`), garantizando la trazabilidad necesaria para un TFM académico riguroso.

