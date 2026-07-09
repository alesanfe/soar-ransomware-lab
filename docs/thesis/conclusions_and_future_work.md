# 5. Conclusiones y trabajo futuro

## 5.1. Resumen de conclusiones principales

### 5.1.1. Cumplimiento de objetivos planteados

El trabajo ha cumplido los objetivos de diseñar, implementar y evaluar un laboratorio SOAR para respuesta a ransomware.
La reducción del 60.2% en MTTR (p<0.001) respalda la hipótesis de que la automatización acorta los tiempos de respuesta
frente a los procesos manuales.

El diseño aplica arquitectura hexagonal al código Python: `domain/ports.py` (432 líneas) define los contratos y cada
capa de infraestructura los implementa de forma independiente. En el plano del despliegue, seis archivos Docker Compose
modulares permiten configuraciones desde mínimas hasta completas. Esta separación evita que la lógica de negocio dependa
de detalles como clientes HTTP o motores de base de datos concretos.

La evaluación experimental obtuvo MTTR de 89 s frente a 225 s en la condición manual (p<0.001), superando el objetivo
del 50% de reducción. Las pruebas E2E y el análisis de logs confirman la reproducibilidad. La documentación cubre
configuración, despliegue (Makefile) y procedimientos de validación para que terceros puedan replicar el experimento.
Las 44 mejoras aplicadas en seguridad, calidad de código y automatización consolidan el sistema más allá del prototipo
inicial.

### 5.1.2. Contribuciones teóricas y prácticas

La contribución teórica principal es una base numérica que la literatura previa no había aportado: la reducción del
60.2% en MTTR con p<0.001 permite contrastar hipótesis sobre eficiencia operativa con datos medibles, frente a los
estudios de caso descriptivos que dominan el área.

Las métricas definidas (MTTR p50 ≤ 120 s, tasa de éxito ≥ 95%, cobertura de tests ≥ 80%) pueden servir de referencia
para evaluar otros laboratorios SOAR similares. Los patrones arquitectónicos documentados (hexagonal para código,
modular para infraestructura) describen una forma de organizar componentes adaptable a distintos entornos.

En el plano práctico, el laboratorio es desplegable con `make up` y accesible desde navegador sin configuración
adicional. Al usar exclusivamente software open source elimina los costos de licenciamiento que en soluciones
propietarias equivalentes oscilan entre $200 000 y $500 000 anuales [9, 15], lo que hace accesibles estas capacidades a
pymes, universidades y CSIRTs en formación.

La documentación generada incluye guías de configuración, ejemplos de scripts y casos de prueba verificados. El código
de contención de endpoints, aunque opera en modo simulado, puede adaptarse para entornos productivos modificando los
drivers de infraestructura.

### 5.1.3. Implicaciones para la práctica profesional

Para pymes, la barrera principal es el licenciamiento. El laboratorio la elimina y, gracias a su automatización de
despliegue, permite poner en marcha capacidades de respuesta en un tiempo reducido [9, 10]. Las grandes organizaciones
pueden emplearlo como entorno de validación previo a la adquisición de soluciones comerciales: la arquitectura
documentada facilita desarrollar y comparar integraciones con sistemas propietarios antes de comprometer recursos
significativos. En el ámbito educativo, el laboratorio proporciona un entorno de práctica operativa sin riesgo para la
infraestructura productiva, lo que permite a los estudiantes extender componentes existentes en lugar de construir una
infraestructura de base desde el principio.

### 5.1.4. Limitaciones del estudio realizado

La limitación más significativa es que la validación se realiza en laboratorio y no con incidentes reales. El alcance
circunscrito a ransomware limita la generalización directa, aunque la arquitectura modular facilita la extensión a otros
vectores. La muestra de n=50 es suficiente para significancia estadística, pero una evaluación longitudinal (ausente en
este trabajo) aportaría más solidez.

En el plano técnico, la dependencia de APIs externas (VirusTotal, AbuseIPDB) exige estrategias de caché y redundancia
para entornos productivos. El despliegue en un único host puede superarse con Kubernetes. Los requisitos de memoria del
entorno completo (detallados en la documentación técnica del proyecto [111]) pueden representar una barrera en
organizaciones con infraestructura limitada.

## 5.2. Trabajo futuro y líneas de investigación

### 5.2.1. Mejoras técnicas inmediatas

Las mejoras más directas afectan al rendimiento: la ejecución concurrente de analyzers en Cortex reduciría los tiempos
de análisis, y la migración a Elasticsearch 8.x junto con Kubernetes habilitaría el escalado horizontal.

En seguridad, la adopción de principios Zero Trust y el cifrado de comunicaciones internas son los pasos más inmediatos.
A más largo plazo, el cifrado homomórfico aplicado al análisis de IoCs permitiría procesar datos sensibles sin
exponerlos a los servicios externos, una línea con resultados preliminares prometedores en el ámbito de la inteligencia
de amenazas preservadora de privacidad [125].

A más largo plazo, el soporte multi-tenant y la migración a arquitecturas cloud-native ampliarían la utilidad y
reducirían la dependencia del host único.

### 5.2.2. Investigaciones longitudinales propuestas

Un seguimiento de 12-24 meses mostraría cómo evolucionan el MTTR y la tasa de éxito en operación real, identificando
patrones de mejora o degradación que evaluaciones cortas no detectan. La transferencia de los playbooks de ransomware a
otros tipos de incidentes es otra línea útil: saber qué componentes son reutilizables y cuáles requieren adaptación
aportaría evidencia cuantitativa sobre la generalización del enfoque. Un análisis TCO a 5 años entre SOAR open source y
soluciones comerciales equivalentes completaría el cuadro de criterios para la toma de decisiones.

### 5.2.3. Desarrollo de capacidades de Machine Learning

El laboratorio ofrece una base sobre la que integrar capacidades de ML. La detección predictiva mediante redes
neuronales entrenadas con históricos de comportamiento permitiría anticipar la ejecución del ransomware, aunque su
viabilidad depende de disponer de datos suficientes y de controlar la tasa de falsos positivos. La clasificación
automática de alertas con NLP ayudaría a agilizar el triage, y su evaluación frente a la clasificación humana permitiría
cuantificar el beneficio real. La optimización de playbooks con Reinforcement Learning es la línea más exploratoria:
cualquier ajuste automático en los flujos de respuesta debería desplegarse de forma gradual y con supervisión humana.

### 5.2.4. Expansión a otros tipos de incidentes

El laboratorio puede extenderse a otros vectores de amenaza sin rediseñar la base.

Los incidentes de APT requerirían playbooks con capacidades de correlación temporal a largo plazo, ya que las campañas
APT pueden mantenerse activas durante semanas o meses, y la integración con threat intelligence geopolítica para
contextualizar actores y motivaciones.

El insider threat plantea un reto distinto: detectar anomalías de comportamiento interno sin vulnerar la privacidad de
los empleados exige que el diseño ético del flujo de respuesta sea tan relevante como la solución técnica.

Los incidentes de supply chain, al afectar a múltiples organizaciones simultáneamente, requieren mecanismos de
coordinación que van más allá de un laboratorio aislado. Explorar cómo extender el playbook a estos escenarios abriría
líneas de trabajo con aplicación directa en entornos productivos.

### 5.2.5. Investigaciones en Interfaz Humano-Máquina

Los sistemas SOAR desplazan parte del trabajo hacia la máquina, pero no eliminan la intervención humana. Estudiar cómo
los analistas interactúan con el sistema: qué decisiones delegan, cuáles retienen y cómo interpretan los resultados de
los analyzers, es una línea poco explorada en la literatura.

La explicabilidad de las decisiones automatizadas es un aspecto concreto: si el sistema activa la contención, el
analista necesita entender por qué. Desarrollar mecanismos que justifiquen las acciones del playbook aumentaría la
confianza y facilitaría la detección de errores.

Otra línea relacionada es la gestión de carga cognitiva. La automatización reduce tareas mecánicas pero puede generar
nuevos focos de sobrecarga: notificaciones, alertas de monitorización y decisiones de escalado. Estudiar empíricamente
cómo afecta el sistema al trabajo real del analista proporcionaría datos útiles para diseñar mejores interfaces
operativas.

## 5.3. Recomendaciones para organizaciones

### 5.3.1. Guía de implementación práctica

La implementación se organiza en cuatro fases:

**Fase 1 (2-4 semanas):** evaluación de las capacidades actuales, identificación de brechas, definición de casos de uso
y KPIs, y selección de stack (open source o comercial).

**Fase 2 (4-6 semanas):** despliegue en entorno aislado con `make up`, configuración de playbooks y variables de
entorno (`.env.full`), integración con 2-3 fuentes de datos y validación E2E.

**Fase 3 (6-8 semanas):** ampliación de integraciones, desarrollo de playbooks especializados, formación del equipo e
implantación de métricas de monitoreo.

**Fase 4 (continua):** migración gradual a producción con validaciones, optimización basada en métricas y escalado
horizontal.

### 5.3.2. Consideraciones de adopción organizacional

El éxito de la adopción depende principalmente de tres factores: patrocinio ejecutivo para autorizar recursos, capacidad
técnica en el equipo y una gestión del cambio que acompañe la transición. Las barreras más frecuentes son la resistencia
inicial (reducible involucrando al equipo desde el diseño) y la complejidad técnica de los primeros despliegues (
abordable comenzando con casos simples). El presupuesto es una barrera menor con este stack, ya que el licenciamiento no
es un coste.

**Métricas de referencia:**

- Reducción de MTTR del 50% en los primeros 6 meses, umbral coherente con las mejoras observadas en este experimento (
  60,2%) y con las reducciones reportadas en estudios comparables sobre automatización de respuesta [3, 7].
- Tasa de clasificación correcta superior al 95%.
- Disponibilidad del sistema superior al 99.5%.

### 5.3.3. Métricas de éxito y KPIs recomendados

En rendimiento operativo: MTTR < 120 s para incidentes simples, throughput > 100 incidentes/hora, disponibilidad > 99.5%
y tasa de clasificación correcta > 95%.

En madurez del proceso: cobertura de automatización superior al 80% de las tareas repetitivas identificadas [44], como
referencia orientativa derivada de los controles CIS v8.1 aplicados a la gestión de incidentes.

### 5.3.4. Mejores prácticas de mantenimiento y evolución

El mantenimiento operativo requiere parches de seguridad regulares, copias de seguridad diarias con pruebas de
restauración y actualización continua de la documentación. El monitoreo con Grafana permite detectar degradaciones de
rendimiento antes de que afecten la operación.

La evolución del sistema puede seguir un ritmo trimestral: revisar capacidades y rendimiento, evaluar herramientas
emergentes, incorporar el feedback del equipo y comparar las prácticas actuales con estándares del sector.

El gobierno incluye auditorías de cumplimiento normativo, identificación de riesgos emergentes y aplicación del ciclo
PDCA para la mejora continua.

## 5.4. Impacto y alcance del trabajo

Los resultados indican que la automatización mediante SOAR reduce de forma consistente el tiempo de respuesta ante
incidentes de ransomware. La reducción del 60.2% en MTTR (de 225 a 89 segundos) con p<0.001 ofrece evidencia
cuantitativa de que los playbooks automatizados acortan los tiempos de reacción frente a los procesos manuales. Ese dato
es relevante para equipos que operan bajo restricciones temporales estrictas.

El laboratorio se publica bajo licencia abierta. La arquitectura hexagonal permite sustituir componentes concretos (por
ejemplo, el cliente de base de datos o el motor de análisis) sin modificar la lógica de negocio, y la estructura modular
de Docker Compose facilita incorporar nuevos servicios sin rediseñar la topología de red. Ambas características
convierten el laboratorio en un punto de partida reutilizable tanto para investigación como para docencia en el ámbito
de la ciberseguridad operativa.

La combinación de desarrollo tecnológico y validación experimental mediante métodos estadísticos (prueba t de Student,
tamaño del efecto d de Cohen) constituye un enfoque metodológico transferible a otros proyectos que evalúen tecnologías
de seguridad en condiciones controladas y reproducibles.

El uso exclusivo de software open source elimina los costos de licenciamiento asociados a soluciones comerciales
equivalentes, cuyo rango de coste anual ha sido estimado en la literatura entre $200 000 y $500 000 [9, 15]. Ello hace
accesibles estas capacidades a pymes, instituciones educativas y CSIRTs en fase de consolidación.
