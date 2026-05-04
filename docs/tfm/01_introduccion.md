# 1. Introducción

## 1.1. Motivación

El panorama actual de ciberseguridad se caracteriza por una creciente sofisticación de las amenazas, con el ransomware emergiendo como una de las más significativas y destructivas. Según el informe Global Threat Intelligence Report 2024, los incidentes de seguridad han aumentado un 67% en comparación con el año anterior, con los ataques de ransomware representando el 23% del total de incidentes reportados.

Las organizaciones modernas enfrentan un volumen de alertas que supera la capacidad de procesamiento humano tradicional. Un estudio de Ponemon Institute (2024) indica que el 68% de las organizaciones reciben más de 1,000 alertas de seguridad diarias, de las cuales solo el 12% son investigadas adecuadamente debido a limitaciones de recursos.

Esta situación crea una brecha crítica entre la detección de amenazas y la respuesta efectiva, especialmente en incidentes de ransomware donde cada segundo cuenta. El tiempo medio de respuesta (MTTR) en procesos manuales puede alcanzar los 225 segundos, un período durante el cual el ransomware puede propagarse y causar daños irreparables.

La motivación de este trabajo surge de la necesidad crítica de abordar esta brecha mediante la automatización inteligente, aprovechando las capacidades de las plataformas SOAR (Security Orchestration, Automation and Response) para reducir significativamente el tiempo de respuesta y mejorar la consistencia en la gestión de incidentes.

## 1.2. Planteamiento del problema

### Problema Central

La respuesta manual a incidentes de ransomware presenta múltiples limitaciones críticas que afectan la eficacia de los equipos de seguridad:

**Tiempo de Respuesta Elevado**
- Procesos secuenciales que requieren intervención humana en cada paso
- Tiempo promedio de 225 segundos desde detección a contención
- Alta variabilidad entre diferentes analistas (±45 segundos)

**Falta de Estandarización**
- Procedimientos inconsistentes entre diferentes equipos
- Dependencia del conocimiento individual del analista
- Dificultad para mantener consistencia en escalas operativas

**Sobrecarga de Personal**
- Volumen de alertas que supera la capacidad humana (1,000+ diarias)
- Burnout y rotación de personal especializado (tasa anual del 28%)
- Degradación del rendimiento bajo carga (reducción del 40% en eficacia)

**Errores Humanos**
- Procedimientos complejos susceptibles a cometer errores
- Falta de validación cruzada de acciones críticas
- Dificultad para auditoría y cumplimiento normativo

### Impacto Económico

El impacto económico del ransomware es sustancial. Según IBM Security (2024):
- Costo promedio por incidente: $5.13 millones
- Tiempo medio de recuperación: 16 días
- Impacto en operaciones: 22 días de interrupción promedio

### Hipótesis de Trabajo

La implementación de un laboratorio SOAR especializado en ransomware puede reducir significativamente el Tiempo Medio de Respuesta (MTTR) mediante la automatización de tareas repetitivas, la estandarización de procedimientos y la mejora en la trazabilidad de las acciones de respuesta.

## 1.3. Estructura del trabajo

El presente Trabajo Fin de Máster se estructura en cinco capítulos principales que siguen una progresión lógica desde la fundamentación teórica hasta la validación práctica y conclusiones:

**Capítulo 1: Introducción**
- Presenta la motivación y planteamiento del problema
- Establece la hipótesis de trabajo y objetivos
- Describe la estructura del documento

**Capítulo 2: Estado del arte**
- Analiza la evolución del ransomware y sus características
- Revisa plataformas SOAR existentes y sus capacidades
- Examina investigaciones previas en automatización de respuesta

**Capítulo 3: Objetivos concretos y metodología de trabajo**
- Define el objetivo general y objetivos específicos
- Detalla la metodología de investigación y desarrollo
- Establece las métricas de evaluación y criterios de éxito

**Capítulo 4: Desarrollo específico de la contribución**
- Describe la identificación de requisitos del laboratorio SOAR
- Detalla la herramienta software desarrollada
- Presenta la evaluación experimental y resultados obtenidos

**Capítulo 5: Conclusiones y trabajo futuro**
- Resume las conclusiones principales del trabajo
- Evalúa el cumplimiento de los objetivos propuestos
- Propone líneas de trabajo futuro y mejoras

**Referencias bibliográficas**
- Lista completa de fuentes académicas y técnicas consultadas

**Anexo A**
- Documentación técnica complementaria y detalles de implementación

Esta estructura permite una presentación sistemática tanto de la fundamentación teórica como de la contribución práctica, facilitando la comprensión del problema, la solución propuesta y su validación experimental.
