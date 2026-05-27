# 1. Introducción

Este trabajo diseña un laboratorio para responder a incidentes de ransomware. El objetivo es ver si la automatización acelera la respuesta. También examina si mejoraría la consistencia en el manejo de alertas. El trabajo se encuentra en los centros de operaciones de seguridad, SOC. En estas ubicaciones, la utilización simultánea de múltiples herramientas conlleva problemas y dificulta el seguimiento de acciones.

El problema esencial está relacionado con el proceso de respuesta a alertas de ransomware. Generalmente, el manejo depende de tareas realizadas manualmente e intervención humana. Además, los criterios varían y existen problemas para lograr la trazabilidad. Estos inconvenientes reducen la calidad de la respuesta y limitan la capacidad de auditar la acción. Un plan de procedimientos documentado no es suficiente. Debe aplicarse en un contexto práctico para dar lugar a evidencias adecuadas.

Se presenta una contribución central que constituye un manual automatizado dedicado al manejo de una alerta. El procedimiento comienza cuando el evento llega por medio de un webhook. Se verifican los datos, se crea un caso en TheHive e incluyen también los marcadores de compromiso. Para el enriquecimiento de la información se emplean herramientas como AbuseIPDB, VirusTotal y MISP, proporcionando contexto respecto a IPs, dominios o hashes. Así, con esta data, el procedimiento decida activar la simulación de una contención o cerrar el caso como inofensivo. En ese momento, se registra el resultado en TheHive y se comunica.

El laboratorio está diseñado para un proyecto independiente. Evita dependencias complicadas y utiliza Docker Compose para replicar el ambiente. La arquitectura combina TheHive, Cortex y Shuffle como servicios clave. El código está organizado en bloques separando la lógica de negocio de la infraestructura. Esta separación facilita las pruebas y reduce la adhesión.

El despliegue es gestionado mediante múltiples archivos Docker Compose. Esta estrategia simplifica la creación de componentes solapados únicos durante cada prueba. Las redes son diferenciadas en múltiples áreas para limitar la exposal entre servicios.

La validación consiste en ejecutar el script de playbooks en dos situaciones, una maliciosa y otra benévola. La duración desde el aviso hasta la contención virtual o cerrado de la incidencia es medible. Los servicios especializados procesan registros de ejecución, realizan las cuentas estadísticas e implementan los cálculos para llegar a los porcentilios. El análisis usa pruebas como registros de ejecución, grabaciones y métricas. La memoria registra el desarrollo de ambos el laboratorio y del script de playbooks utilizando este marco como base de conclusión.

## 1.1. Motivación

Los incidentes de ransomware han aumentado en los últimos años. El Global Threat Intelligence Report 2024 indica un incremento del 67% en incidentes de seguridad. Según el informe, el ransomware representa el 23% del total [18]. Aun así, en muchos entornos la gestión de estos incidentes sigue basándose en tareas manuales. Esto genera retrasos, aumenta la carga del analista y dificulta conservar una traza del proceso.

En la práctica, una alerta de ransomware exige varias tareas. Primero se valida la información. Luego se abre un caso, se añaden los observables y se consulta información contextual. Solo entonces se toma una decisión sobre la contención. Cuando estas actividades se ejecutan manualmente, el tiempo de respuesta aumenta. También aparecen diferencias entre analistas, lo que dificulta la mejora continua.

La fragmentación de herramientas obliga al analista a usar varios sistemas a la vez [2]. Algunas tareas se repiten en casi todos los casos, como triage, enriquecimiento o actualización de tickets. Si se hacen a mano, consumen tiempo y aumentan los errores [11]. Sin un flujo estandarizado, es difícil medir la respuesta y comparar ejecuciones [85].

La literatura sobre respuesta a incidentes apunta en esa dirección. NIST SP 800-61 y los estudios sobre plataformas SOAR destacan el valor de centralizar datos, análisis y respuesta en un mismo flujo. Esta integración puede reducir tiempos y limitar errores de la intervención manual [11, 12].

En ransomware, el tiempo entre detección y contención condiciona el daño. El cifrado de archivos puede propagarse rápido a través de unidades compartidas [25]. Por ello, un entorno controlado y reproducible sirve para probar configuraciones del flujo y comparar ejecuciones bajo las mismas condiciones.

Un laboratorio mínimo viable permite estudiar cómo un playbook integra herramientas y automatiza tareas sin los riesgos de un entorno productivo. En este trabajo, Cortex actúa como motor de análisis centralizando la consulta de observables mediante APIs. Es un patrón usado en contextos de SOC y CSIRT que aquí se evalúa en un entorno acotado.

## 1.2. Planteamiento del problema

En muchos SOC, la gestión de incidentes de ransomware se basa en procesos manuales, integraciones parciales y criterios no estandarizados [2, 11]. Esta situación incrementa los tiempos de respuesta, introduce variabilidad y dificulta generar evidencias completas. Como la demora en la contención amplifica el impacto del cifrado, esa variabilidad puede afectar a la severidad del incidente [25].

La automatización mediante plataformas SOAR y playbooks aparece en la literatura como una alternativa para reducir carga manual y ordenar los procesos de decisión [11, 12]. Esto no implica eliminar la supervisión humana, especialmente en acciones de mayor impacto. Pero su adopción plantea dificultades como la complejidad de los entornos productivos, las licencias comerciales y la dificultad de medir su impacto en condiciones controladas.

Este trabajo propone el diseño e implementación de un laboratorio SOAR mínimo viable, reproducible y autocontenido que materialice un playbook orientado a ransomware. No se pretende desplegar una solución de producción completa. El objetivo es mostrar cómo un flujo automatizado puede integrar la recepción de alertas, la normalización de datos, la gestión de casos, el enriquecimiento de observables y la contención simulada de manera coherente y trazable.

Al ser reproducible, el laboratorio permite evaluar cambios del playbook sobre una misma línea base. Esto facilita comparaciones y deja margen para extensiones futuras.

## 1.3. Estructura del trabajo

El documento está compuesto por cinco capítulos.
- Capítulo 2 revisa la literatura sobre respuesta a incidentes, ransomware y plataformas SOAR y identifica las lagunas que esta investigación aborda.
- Capítulo 3 presenta los objetivos y método de la investigación.
- Capítulo 4 detalla los elementos técnicos del ensayo, incluyendo requisitos, arquitectura, implementación del playbook y resultados.
- Capítulo 5 presenta los hallazgos y debatir las limitaciones del estudio. Además, formulará sugerencias para entornos que deseen aplicar capacidades SOAR similares.
- Anexo A contiene la documentación técnica requerida para reproducir el ensayo.