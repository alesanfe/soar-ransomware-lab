# Objetivos SMART
> Este documento presenta los objetivos SMART del proyecto y su relación con la EDT, además de indicar dónde se aportarán las pruebas y evidencias en el repositorio.

---

## **Introducción**
El proyecto se basa en la EDT definida y el contexto del laboratorio SOAR para respuesta ante ransomware. Cada objetivo está alineado con las tareas del EDT y se vincula con la estructura del repositorio, asegurando trazabilidad y organización.

Las evidencias se almacenarán en:
- **Pruebas unitarias y E2E**: `tests/`
- **Resultados y métricas**: `results/kpis.csv`
- **Documentación técnica y validación**: `docs/informe_pruebas.md`
- **Logs del flujo**: `logs/`

---

## **Tabla de Objetivos SMART y Ubicación de Evidencias**
| Nº | Objetivo | Descripción | Métrica | Umbral | Método de Medida | Evidencia |
|----|----------|-------------|---------|--------|-------------------|-----------|
| 1  | Implementación del laboratorio | Desplegar entorno reproducible con TheHive, Cortex y Shuffle mediante Docker Compose. | Servicios activos | 100% contenedores funcionando | Verificación con `docker ps` | Capturas en `docs/tecnico.md` |
| 2  | Desarrollo del playbook E2E | Crear flujo automatizado desde alerta hasta contención simulada. | Ejecución completa | 2 escenarios (malicioso y benigno) | Logs del SOAR y casos en TheHive | Evidencias en `tests/e2e/` |
| 3  | Validación de métricas MTTR | Medir tiempo de respuesta desde alerta hasta contención. | Percentiles p50 y p90 | p50 ≤ 120 s; p90 ≤ 180 s | Timestamps y cálculo estadístico | `results/kpis.csv` y `docs/informe_pruebas.md` |
| 4  | Documentación técnica | Generar documentación completa (arquitectura, configuración, resultados). | Documento final | 100% apartados completados | Checklist y revisión del tutor | `docs/` (architecture.md, manual_playbook.md) |
| 5  | Integración SIEM simulada | Configurar SIEM simulado para generar alertas. | Alertas procesadas | 100% sin errores | Logs en Shuffle y casos en TheHive | `scripts/send_alert.py` + capturas en `docs/informe_pruebas.md` |
| 6  | Contención simulada | Implementar scripts para aislamiento y bloqueo. | Acciones ejecutadas | 100% completadas | Logs del script y confirmación en flujo | `scripts/isolate_host.sh` y `isolate_endpoint.ps1` |
| 7  | Seguridad del entorno | Garantizar uso exclusivo de muestras inertes. | Incidentes | 0 incidentes | Revisión del contenido y validación | `docs/security.md` |
| 8  | Automatización opcional | Implementar despliegue con Ansible/Vagrant. | Despliegue automático | 100% servicios levantados | Ejecución del script y verificación | `vagrant/` y `ansible/` |
| 9  | Pruebas funcionales | Ejecutar pruebas completas del laboratorio. | Casos probados | 100% escenarios validados | Informe con evidencias | `tests/e2e/` y `docs/informe_pruebas.md` |
| 10 | KPIs y análisis | Calcular KPIs y presentar resultados. | KPIs calculados | Informe con gráficos | Análisis estadístico y visualización | `results/kpis.csv` y `docs/informe_pruebas.md` |
| 11 | Preparación defensa TFM | Crear presentación y resumen ejecutivo. | Presentación lista | 100% diapositivas completadas | Validación por tutor y ensayo | Carpeta `docs/` (cierre.md) |
| 12 | Evidencia de aprobación | Obtener validación formal del alcance y objetivos. | Archivo firmado | Documento archivado | Confirmación por correo y almacenamiento | Carpeta `docs/` (plan.md) |

---

## **Relación con la EDT y Repositorio**
Cada objetivo corresponde a tareas específicas del EDT:
- **Infraestructura (EDT 4.x)**: Objetivos 1, 8.
- **Playbook y scripts (EDT 5.x, 6.x)**: Objetivos 2, 5, 6.
- **Pruebas y métricas (EDT 7.x)**: Objetivos 3, 9, 10.
- **Documentación y cierre (EDT 8.x)**: Objetivos 4, 11, 12.

La estructura del repositorio soporta esta organización, con carpetas dedicadas para pruebas (`tests/`), resultados (`results/`), documentación (`docs/`) y scripts (`scripts/`).

