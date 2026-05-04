# 3. Objetivos concretos y metodología de trabajo

## 3.1. Objetivo general

Diseñar, implementar y evaluar un laboratorio SOAR funcional que demuestre la reducción del Tiempo Medio de Respuesta (MTTR) en incidentes de ransomware mediante la automatización de procesos de respuesta, validando empíricamente la hipótesis de que la orquestación automatizada mejora significativamente la eficacia en la gestión de incidentes de ciberseguridad.

## 3.2. Objetivos específicos

### 3.2.1. Objetivo Técnico 1: Diseño Arquitectónico
- **Meta**: Diseñar una arquitectura SOAR escalable y modular basada en herramientas open source
- **Criterios de éxito**: 
  - Arquitectura documentada con diagramas técnicos
  - Especificaciones de integración entre componentes
  - Plan de escalabilidad y redundancia
- **Evidencias**: Documentación de arquitectura, diagramas UML, especificaciones técnicas

### 3.2.2. Objetivo Técnico 2: Implementación Funcional
- **Meta**: Implementar un flujo automatizado completo para respuesta a ransomware
- **Criterios de éxito**:
  - Playbook funcional end-to-end en Shuffle
  - Integración operativa TheHive-Cortex-Shuffle
  - Simulador SIEM para pruebas controladas
- **Evidencias**: Scripts funcionales, playbooks implementados, logs de ejecución

### 3.2.3. Objetivo de Validación 3: Evaluación Experimental
- **Meta**: Validar la eficacia mediante métricas cuantitativas (MTTR, tasa de éxito, etc.)
- **Criterios de éxito**:
  - Reducción del MTTR ≥50% vs baseline manual
  - Tasa de éxito de automatización ≥95%
  - Dataset de pruebas con n≥50 ejecuciones
- **Evidencias**: Resultados experimentales, análisis estadístico, KPIs calculados

### 3.2.4. Objetivo Académico 4: Documentación Reproducible
- **Meta**: Documentar el proceso para facilitar su reproducción y aprendizaje
- **Criterios de éxito**:
  - Guía de instalación y configuración completa
  - Documentación de playbooks y flujos
  - Reproducibilidad validada por terceros
- **Evidencias**: Documentación técnica, tutoriales, validación de reproducción

### 3.2.5. Objetivo de Mejora 5: Optimización Iterativa
- **Meta**: Identificar áreas de mejora y optimización del sistema
- **Criterios de éxito**:
  - Análisis sistemático de 44 mejoras potenciales
  - Implementación de mejoras críticas de seguridad
  - Métricas de mejora post-optimización
- **Evidencias**: Análisis de mejoras, implementación validada, métricas comparativas

## 3.3. Metodología del trabajo

### 3.3.1. Enfoque Metodológico Adoptado

El proyecto adopta una metodología híbrida que combina:

**Investigación Aplicada con Desarrollo Tecnológico**
- Enfoque práctico orientado a resultados medibles
- Desarrollo de software como vehículo de investigación
- Validación empírica de hipótesis mediante experimentación

**Metodología Ágil con Principios DevSecOps**
- Desarrollo iterativo en sprints de 2 semanas
- Integración continua de seguridad (Security by Design)
- Automatización de pruebas y despliegue

**Infraestructura como Código (IaC)**
- Todo el entorno definido en código versionado
- Reproducibilidad garantizada mediante Docker
- Gestión de configuración automatizada

### 3.3.2. Fases del Proyecto

#### Fase I: Investigación y Análisis de Requisitos (Semanas 1-2)
**Actividades**:
- Análisis de estado del arte en SOAR y ransomware
- Identificación de requisitos funcionales y no funcionales
- Selección de tecnologías y herramientas
- Definición de métricas de éxito y KPIs

**Entregables**:
- Documentación de requisitos
- Matriz de selección tecnológica
- Especificaciones de métricas
- Plan de proyecto detallado

#### Fase II: Diseño Arquitectónico (Semanas 3-4)
**Actividades**:
- Diseño de arquitectura SOAR modular
- Especificación de integraciones entre componentes
- Diseño de playbooks y flujos de respuesta
- Planificación de infraestructura Docker

**Entregables**:
- Diagramas de arquitectura
- Especificaciones técnicas
- Diseño de playbooks
- Configuración Docker Compose

#### Fase III: Desarrollo e Implementación (Semanas 5-8)
**Actividades**:
- Implementación de infraestructura Docker
- Configuración de TheHive, Cortex y Shuffle
- Desarrollo de scripts de automatización
- Creación de playbooks en Shuffle

**Entregables**:
- Infraestructura funcional
- Scripts de automatización
- Playbooks implementados
- Sistema de monitoreo

#### Fase IV: Pruebas y Validación (Semanas 9-10)
**Actividades**:
- Desarrollo de suite de pruebas automatizadas
- Ejecución de experimentos controlados
- Recolección y análisis de datos
- Validación de hipótesis

**Entregables**:
- Suite de pruebas completa
- Resultados experimentales
- Análisis estadístico
- Informe de validación

#### Fase V: Optimización y Documentación (Semanas 11-12)
**Actividades**:
- Análisis e implementación de mejoras
- Documentación completa del proyecto
- Preparación de materiales académicos
- Validación final de entregables

**Entregables**:
- Sistema optimizado
- Documentación completa
- Materiales académicos
- Informe final

### 3.3.3. Tecnologías y Herramientas Utilizadas

#### Tecnologías Core
- **Docker & Docker Compose**: Contenerización y orquestación
- **Python 3.8+**: Desarrollo de scripts y automatización
- **Elasticsearch**: Motor de búsqueda y almacenamiento
- **Nginx**: Reverse proxy y terminación TLS

#### Plataformas SOAR
- **TheHive 3.5.2**: Gestión de casos y colaboración
- **Cortex 3.1.0**: Análisis de IoCs y analyzers
- **Shuffle 1.3.0**: Orquestación visual y workflows

#### Herramientas de Desarrollo
- **Git**: Control de versiones
- **VS Code**: IDE de desarrollo
- **Make**: Automatización de tareas
- **pytest**: Framework de pruebas

#### Herramientas de Monitoreo
- **Prometheus**: Recolección de métricas
- **Grafana**: Visualización y dashboards
- **cAdvisor**: Monitoreo de contenedores

### 3.3.4. Diseño Experimental

#### Variables Independientes
- **Tipo de respuesta**: Manual vs Automatizada SOAR
- **Complejidad del incidente**: Simple, Medio, Complejo
- **Carga del sistema**: Baja, Media, Alta
- **Tipo de alerta**: Maliciosa, Benigna, Falso positivo

#### Variables Dependientes
- **MTTR**: Tiempo medio de respuesta (segundos)
- **Tasa de éxito**: Porcentaje de respuestas exitosas
- **Precisión**: Tasa de verdaderos positivos
- **Uso de recursos**: CPU, memoria, red

#### Variables Controladas
- **Entorno de pruebas**: Laboratorio controlado Docker
- **Dataset**: 50 ejecuciones por escenario
- **Hardware**: Recursos fijos y documentados
- **Configuración**: Parámetros constantes

#### Procedimientos de Control
- **Randomización**: Orden aleatorio de ejecuciones
- **Replicación**: Múltiples ejecuciones por condición
- **Validación**: Verificación independiente de resultados
- **Blinding**: Análisis ciego de datos cuando aplicable

### 3.3.5. Consideraciones Éticas y de Seguridad

#### Aspectos Éticos
- **Uso responsable**: Laboratorio exclusivamente para fines académicos
- **No producción**: Entorno aislado sin datos reales
- **Transparencia**: Documentación completa de métodos
- **Reproducibilidad**: Facilitar validación por pares

#### Consideraciones de Seguridad
- **Datos sintéticos**: Sin información real de usuarios
- **Aislamiento de red**: Segmentación completa del laboratorio
- **Credenciales seguras**: Gestión apropiada de secretos
- **Hardening**: Configuración segura de todos los componentes

#### Cumplimiento Normativo
- **GDPR**: Protección de datos sintéticos
- **ISO 27001**: Buenas prácticas de seguridad
- **NIST Cybersecurity Framework**: Referencia de mejores prácticas
- **MITRE ATT&CK**: Framework de tácticas y técnicas

### 3.3.6. Plan de Gestión de Riesgos

#### Riesgos Técnicos
- **Fallo de integración**: Mitigación con pruebas tempranas
- **Problemas de rendimiento**: Monitoreo continuo y optimización
- **Vulnerabilidades de seguridad**: Escaneo regular y actualización

#### Riesgos de Proyecto
- **Retrasos en cronograma**: Buffer temporal del 20%
- **Cambios en requisitos**: Gestión ágil de cambios
- **Pérdida de datos**: Backup automatizado diario

#### Riesgos de Validación
- **Sesgo en resultados**: Diseño experimental riguroso
- **Dataset insuficiente**: Power analysis estadístico
- **Generalización limitada**: Análisis honesto de limitaciones

Esta metodología proporciona un marco estructurado y riguroso para abordar los objetivos del proyecto, garantizando tanto la calidad técnica como la validez académica de los resultados obtenidos.
