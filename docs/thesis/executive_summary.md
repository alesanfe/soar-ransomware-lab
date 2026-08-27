# Resumen Ejecutivo / Abstract

## Resumen Ejecutivo

Este Trabajo Fin de Máster diseña e implementa un laboratorio SOAR mínimo viable, reproducible
con Docker Compose (Docker Inc., 2024), para
automatizar la respuesta ante alertas de ransomware. El laboratorio integra TheHive (TheHive Project, 2024) para
gestión de casos, Cortex (Cortex Project, 2024) para
enriquecimiento y Shuffle (Shuffle Tools, 2024) para orquestación. Estas herramientas se combinan en un playbook de
extremo a extremo que
normaliza alertas, crea y actualiza casos, enriquece indicadores de compromiso y aplica una lógica de decisión con
contención simulada.

La propuesta se valida mediante escenarios benigno y malicioso, midiendo el tiempo desde la alerta hasta la contención
simulada usando percentiles p50 y p90. El trabajo genera evidencias verificables como logs y métricas. Con un alcance
académico y educativo, el estudio aporta evidencia de que la automatización mejora la consistencia, la trazabilidad y
la eficiencia operativa en un entorno controlado. La suite de pruebas contiene 2041 tests (9 marcadores pytest,
coverage 84.6 %, 39 TCs E2E) y 281 tests E2E del playbook ejecutados correctamente.

**Palabras clave:** SOAR, ransomware, automatización, playbook, MTTR


## Abstract

This Master's Thesis designs and implements a minimum viable SOAR laboratory, deployable via Docker Compose, to automate
ransomware alert response. The laboratory integrates TheHive for case management, Cortex for enrichment, and Shuffle for
orchestration. These tools work together in an end-to-end playbook that normalizes alerts, creates and updates cases,
enriches indicators of compromise, and applies decision logic with simulated containment.

The proposal is validated through benign and malicious scenarios, measuring elapsed time from alert reception to
containment using p50 and p90 percentiles. The work generates verifiable evidence including logs and metrics. With an
academic and educational scope, the study demonstrates that automation improves consistency, traceability, and
operational efficiency in a controlled environment.

**Keywords:** SOAR, ransomware, automation, playbook, MTTR