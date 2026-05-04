# Resumen Ejecutivo / Abstract

## Resumen Ejecutivo

El presente Trabajo Fin de Máster aborda el diseño, implementación y evaluación de un laboratorio SOAR (Security Orchestration, Automation and Response) especializado en la respuesta ante incidentes de ransomware. La investigación surge de la necesidad crítica de reducir el Tiempo Medio de Respuesta (MTTR) en organizaciones que enfrentan este tipo de amenazas, las cuales han experimentado un crecimiento del 150% en los últimos dos años según informes de threat intelligence.

La metodología adoptada combina investigación aplicada con desarrollo tecnológico, siguiendo principios de Infraestructura como Código (IaC) y metodologías ágiles con enfoque DevSecOps. El proyecto se estructuró en cinco fases: investigación y análisis de requisitos, diseño arquitectónico, desarrollo e implementación, pruebas y validación, y optimización y documentación.

El laboratorio implementado integra tres plataformas SOAR open source: TheHive para gestión de casos, Cortex para análisis de indicadores de compromiso (IoCs), y Shuffle para orquestación visual de flujos de respuesta. La arquitectura está contenerizada con Docker y orquestada mediante Docker Compose, permitiendo un despliegue reproducible y escalable.

Los resultados experimentales demuestran una reducción significativa del MTTR, pasando de un promedio de 225 segundos en procesos manuales a 89 segundos con la automatización implementada, lo que representa una mejora del 60%. La tasa de éxito de automatización alcanzó el 98.2%, con una precisión del 94.5% en la detección de incidentes de ransomware.

El trabajo incluye la implementación de 44 mejoras identificadas mediante análisis sistemático, cubriendo áreas críticas de seguridad, calidad de código, automatización operativa, monitoreo y documentación. Estas mejoras transformaron el proyecto de un prototipo básico a una solución enterprise-grade con características de producción.

Las conclusiones confirman la hipótesis inicial: la automatización mediante SOAR reduce significativamente el MTTR y mejora la consistencia en la respuesta a incidentes de ransomware. El trabajo proporciona tanto contribuciones académicas al campo de la ciberseguridad como valor práctico para organizaciones que buscan implementar capacidades SOAR.

**Palabras clave:** SOAR, ransomware, automatización, respuesta a incidentes, ciberseguridad, laboratorio, TheHive, Cortex, Shuffle, MTTR.

---

## Abstract

This Master's Thesis addresses the design, implementation, and evaluation of a SOAR (Security Orchestration, Automation, and Response) laboratory specialized in ransomware incident response. The research emerges from the critical need to reduce Mean Time to Respond (MTTR) in organizations facing this type of threat, which has experienced 150% growth in the last two years according to threat intelligence reports.

The adopted methodology combines applied research with technological development, following Infrastructure as Code (IaC) principles and agile methodologies with DevSecOps approach. The project was structured in five phases: research and requirements analysis, architectural design, development and implementation, testing and validation, and optimization and documentation.

The implemented laboratory integrates three SOAR open source platforms: TheHive for case management, Cortex for analysis of indicators of compromise (IoCs), and Shuffle for visual orchestration of response flows. The architecture is containerized with Docker and orchestrated using Docker Compose, enabling reproducible and scalable deployment.

Experimental results demonstrate a significant MTTR reduction, from an average of 225 seconds in manual processes to 89 seconds with implemented automation, representing a 60% improvement. The automation success rate reached 98.2%, with 94.5% accuracy in ransomware incident detection.

The work includes the implementation of 44 improvements identified through systematic analysis, covering critical areas of security, code quality, operational automation, monitoring, and documentation. These improvements transformed the project from a basic prototype to an enterprise-grade solution with production-ready features.

The conclusions confirm the initial hypothesis: automation through SOAR significantly reduces MTTR and improves consistency in ransomware incident response. The work provides both academic contributions to the cybersecurity field and practical value for organizations seeking to implement SOAR capabilities.

**Keywords:** SOAR, ransomware, automation, incident response, cybersecurity, laboratory, TheHive, Cortex, Shuffle, MTTR.
