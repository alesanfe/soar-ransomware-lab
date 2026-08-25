# 2. Estado del arte

Este capítulo revisa la literatura sobre respuesta a incidentes, automatización y orquestación en SOC, con especial atención al ransomware y al uso de playbooks. Los equipos de seguridad operan con ecosistemas de herramientas fragmentados y datos heterogéneos, lo que incrementa la intervención manual e introduce variabilidad difícil de cuantificar y controlar. Las plataformas SOAR actúan como capa de integración que complementa al SIEM, permitiendo operacionalizar procedimientos mediante playbooks sin suprimir la supervisión humana en las decisiones críticas (Kinyua & Awuah, 2021).

## 2.1. Respuesta a incidentes y ransomware como dominio de aplicación

La respuesta a incidentes se describe habitualmente como un proceso estructurado en fases de preparación, detección y análisis, contención, erradicación y recuperación (NIST, 2023). La norma ISO/IEC 27035 (ISO/IEC, 2016) recoge una estructura equivalente a nivel internacional. NIST ha sistematizado estas fases y las revisa de forma periódica: en abril de 2025, NIST SP 800-61r2 fue retirada y sustituida por NIST SP 800-61r3, documento que refleja la tendencia a incorporar la respuesta a incidentes en el marco más amplio de gestión del riesgo de ciberseguridad (NIST, 2025).

En ransomware, el impacto principal es la pérdida de disponibilidad por cifrado. En muchos ataques recientes eso se combina con exfiltración previa y doble extorsión, lo que acelera los tiempos de decisión. CISA ofrece guías específicas con listas de verificación que concretan las tareas y evidencias mínimas esperadas (CISA, 2023). El escenario de amenazas europeo, recogido en el ENISA Threat Landscape 2023, confirma esta tendencia hacia la doble extorsión como patrón dominante en campañas de ransomware (ENISA, 2023). Mandiant (Mandiant, 2024) reporta un aumento del 11 % en grupos de ransomware activos entre 2023 y 2024, y CrowdStrike (CrowdStrike, 2024) documenta una media de 79 minutos entre acceso inicial y cifrado, frente a los 147 minutos del año anterior.

Para modelar el comportamiento del adversario y conectar detecciones con acciones, MITRE ATT&CK (MITRE Corporation, 2024; MITRE ATT&CK, n.d.) es una referencia habitual en el sector. La técnica T1486 (Data Encrypted for Impact) describe el cifrado de datos para interrumpir la disponibilidad y extorsionar, e incluye detalles sobre propagación y entornos afectados que orientan la definición de observables e IoCs relevantes (MITRE, 2025).

La progresión del ransomware a través de generaciones muestra una tendencia clara hacia sofisticación creciente y demandas de rescate exponencialmente mayores. Como se observa en la **Tabla 2**, los rescates promedio han aumentado de $300-$700 en la primera generación a $500K-$20M en la cuarta, representando un incremento de más de tres órdenes de magnitud que justifica la inversión en capacidades SOAR para mitigar el coste financiero de estos incidentes (CrowdStrike, 2024; Sophos, 2024).

## Tabla 2: Progresión de Ransomware por Generación

| Generación | Período       | Características Principales            | Técnicas de Distribución         | Rescate Promedio | Ejemplos Notables            |
|------------|---------------|----------------------------------------|----------------------------------|------------------|------------------------------|
| **1ª Gen** | 2013-2016     | Encriptación básica, sin propagación   | Email phishing, exploits simples | $300-$700        | CryptoLocker, CryptoWall     |
| **2ª Gen** | 2016-2019     | Propagación lateral, exploits 0-day    | EternalBlue, exploits red        | $10K-$50K        | WannaCry, NotPetya, Ryuk     |
| **3ª Gen** | 2019-2022     | Modelo RaaS, doble extorsión           | Afiliados, kits de ataque        | $100K-$10M       | Maze, REvil, Conti           |
| **4ª Gen** | 2022-Presente | Triple extorsión, ML/AI, anti-forenses | Acceso inicial, supply chain     | $500K-$20M       | LockBit 3.0, BlackCat, Royal |

La primera generación se caracterizaba por encriptación básica y demandas de rescate modestas, mientras que la cuarta generación actual incorpora técnicas avanzadas de Machine Learning, triple extorsión y capacidades anti-forenses (Sophos, 2024). Esta progresión indica la necesidad de capacidades de respuesta automatizadas, ya que la respuesta manual resulta insuficiente ante amenazas de esta complejidad. Los informes anuales de CrowdStrike (CrowdStrike, 2024) y Sophos (Sophos, 2024) corroboran esta tendencia con datos de telemetría global de sus respectivos clientes.

## 2.2. Automatización, SOAR y playbooks en operaciones de seguridad

La proliferación de herramientas con representaciones de datos dispares obliga al analista a saltar entre sistemas durante una misma investigación, lo que eleva el tiempo de respuesta y dificulta cualquier intento de estandarización.
SIEM y SOAR son complementarios. El SIEM centraliza eventos y genera alertas, y SOAR orquesta las integraciones y ejecuta respuestas automatizadas en las fases de contención y recuperación (Kinyua & Awuah, 2021).
Islam et al. ofrecen la revisión sistemática más completa del área: su multi-vocal literature review clasifica las funcionalidades de las plataformas de orquestación en unificación, orquestación y automatización, e identifica los componentes core, los drivers técnicos y socio-técnicos, y una taxonomía basada en entorno de ejecución, estrategia de automatización y tipo de despliegue (Islam et al., 2019). Esta taxonomía respalda la elección de un despliegue on-premise con orquestación basada en playbooks, como el que se evalúa en este TFM.

Para contextualizar esta elección, la **Tabla 1** compara las plataformas SOAR open source seleccionadas en este TFM con soluciones comerciales representativas según costo, funcionalidad, curva de aprendizaje, comunidad y escalabilidad.

## Tabla 1: Comparativa Detallada de Plataformas SOAR

Comparación de plataformas SOAR open source (TheHive (TheHive Project, 2024), Cortex (Cortex Project, 2024), Shuffle (Shuffle Tools, 2024)) versus comerciales (Palo Alto XSOAR, IBM
Resilient) según costo, funcionalidad, curva de aprendizaje, comunidad y escalabilidad. Las herramientas open source
ofrecen capacidades competitivas sin costos de licencia.

| Característica        | TheHive                  | Cortex                   | Shuffle                  | Palo Alto XSOAR            | IBM Resilient             |
|-----------------------|--------------------------|--------------------------|--------------------------|----------------------------|---------------------------|
| **Licencia**          | Open Source (Apache 2.0) | Open Source (Apache 2.0) | Open Source (Apache 2.0) | Comercial ($50K-$500K/año) | Comercial ($100K-$1M/año) |
| **Gestión de Casos**  | Excelente              | No aplica              | Básica                 | Avanzada                 | Avanzada                |
| **Análisis IoCs**     | No aplica              | Excelente              | Básico                 | Avanzado                 | Avanzado                |
| **Orquestación**      | Limitada               | No aplica              | Excelente              | Excelente                | Excelente               |
| **Curva Aprendizaje** | Media                    | Media                    | Baja                     | Alta                       | Alta                      |
| **Comunidad**         | Activa                   | Activa                   | Creciente                | Empresarial                | Empresarial               |
| **Integraciones**     | 50+                      | 30+ analyzers            | 100+ apps                | 300+                       | 250+                      |
| **Escalabilidad**     | Media                    | Media                    | Alta                     | Alta                       | Alta                      |
| **Soporte**           | Comunidad                | Comunidad                | Comunidad                | 24/7 Enterprise            | 24/7 Enterprise           |

Las plataformas open source seleccionadas ofrecen una combinación funcional adecuada: TheHive gestiona casos, Cortex
analiza IoCs y Shuffle orquesta flujos. Esta combinación permite construir una solución SOAR sin costos de licencia. Las
soluciones comerciales requieren inversiones anuales de seis cifras (IBM Security, 2024), fuera del alcance de muchas organizaciones. La
comunidad activa de las herramientas open source asegura soporte continuo y desarrollo.

Los playbooks son el mecanismo para convertir decisiones tácticas en procedimientos repetibles. Kinyua y Awuah distinguen entre playbook —checklist lineal— y runbook —workflow con control de flujo, condiciones y puntos donde el analista interviene. Esta distinción encaja con diseños que combinan automatización con decisión humana en acciones de mayor consecuencia. En cuanto a la medición del valor operativo, los mismos autores proponen MTTD, MTTR y tiempo de investigación como indicadores, lo que conecta directamente con las evaluaciones basadas en percentiles de este TFM (Kinyua & Awuah, 2021).
Otros trabajos han explorado la aplicación de IA/ML en respuesta a incidentes, con mejoras observadas en detección y clasificación de amenazas en infraestructuras críticas (Obuse et al., 2023), y en la automatización de tareas de seguridad TI para reducir la carga operativa (Mohammad & Lakshmisri, 2018).

La primera evaluación empírica de SOAR en uso real la aportan Gutzwiller et al., quienes diseñan y administran el primer estudio de usuario hands-on con herramientas SOAR, involucrando a 24 participantes y seis herramientas comerciales en un cyber range. Sus resultados muestran una reducción del context switching del orden del 30 %, pero también un aumento en errores de omisión del 23 % al 78 % en analistas junior cuando la automatización simplifica demasiado la tarea. Los autores observan además que la configuración específica de cada SOC es crítica y que los analistas senior prefieren combinar automatización con asistencia a la decisión (Gutzwiller et al., 2023). Este resultado respalda la decisión de este TFM de automatizar tareas repetitivas manteniendo la supervisión humana en decisiones de mayor consecuencia.

Sin embargo, la evidencia empírica muestra que tener un playbook no garantiza efectividad. Stevens et al. analizan frameworks de diseño de playbooks y concluyen que producen con frecuencia artefactos insuficientemente detallados para uso real, especialmente para perfiles junior. Los fallos típicos incluyen tareas implícitas omitidas, lenguaje ambiguo y ausencia de ramificación o paralelismo. Cuando los playbooks se iteran junto con los procesos organizativos, la utilidad mejora, lo que implica que el nivel de detalle del diseño afecta al rendimiento real bajo estrés (Stevens et al., 2022).

Schlette et al. analizan 1217 playbooks de múltiples fuentes y detectan ambigüedad sobre qué constituye exactamente un playbook en la práctica. Su conclusión principal es que los playbooks comunitarios suelen requerir adaptación antes de ser operativos: herramientas disponibles, requisitos legales, estructura del equipo y procesos internos condicionan esa adaptación. Este resultado justifica que el laboratorio del TFM defina explícitamente su contexto y que el playbook E2E se diseñe para ese entorno, sin asumir reutilización directa (Schlette et al., 2024).

Akbari Gurabi et al. abordan la transición de playbooks textuales a formatos machine-readable e interoperables, y definen requisitos formales para playbooks que asistan la respuesta a incidentes, el reporting y la automatización. Su trabajo, financiado por el programa Horizon 2020 de la UE, destaca la necesidad de que los playbooks sean portables entre organizaciones y herramientas, un objetivo aún no resuelto que refuerza la relevancia de evaluar playbooks en entornos específicos como el de este TFM (Akbari Gurabi et al., 2024). Por su parte, Karlzén y Sommestad revisan 45 soluciones académicas de respuesta automática a incidentes publicadas desde 2000 y las comparan con cuatro soluciones comerciales, categorizándolas por entrada (señales de intrusión, inventarios de activos) y salida (aislamiento de red, reconfiguración de firewalls) según el framework D3FEND. Su conclusión principal es que muchas soluciones describen entradas y salidas en términos vagos, y que las soluciones comerciales se centran más en reputación de indicadores y análisis de archivos (Karlzén & Sommestad, 2023). Esta revisión contextualiza la contribución de este TFM: el uso de analyzers de Cortex para enriquecer IoCs mediante fuentes de reputación coincide con el patrón dominante en soluciones comerciales, pero la medición cuantitativa del MTTR con percentiles aporta el rigor que Karlzén y Sommestad identifican como ausente en la literatura.

En el terreno específico del ransomware, Kok et al. presentan un framework detallado para diseñar estrategias de respuesta a ransomware que equilibra adaptabilidad y accionabilidad, identificando diferencias entre clases de ransomware y destacando la importancia de la preparación específica, la comunicación rápida y la documentación previa de procesos (Kok et al., 2023). Complementariamente, Brown et al. introducen el concepto de playbook operations-informed, que incorpora el contexto operacional en el playbook para reflejar las interdependencias entre las actividades de respuesta a incidentes y las operaciones de la organización, con un caso de estudio aplicado a ransomware (Brown et al., 2023).

En cuanto a estandarización, OASIS CACAO 2.0 (noviembre de 2023) define un esquema y taxonomía para describir playbooks de ciberseguridad desde la detección hasta la remediación (OASIS, 2023). Microsoft y el Automation SIG de FIRST complementan este marco con guías prácticas e intercambio de experiencias entre CSIRT (Microsoft, 2024; FIRST, n.d.). La coexistencia de iniciativas paralelas en este campo refleja que el sector aún no ha alcanzado convergencia en torno a un estándar único (OASIS, 2023; Schlette et al., 2024), lo que justifica la necesidad de ajustar cualquier playbook al contexto operativo concreto en que va a desplegarse. Sigma (Sigma Project, n.d.)
representa un esfuerzo complementario para estandarizar reglas de detección, y Shuffle (Shuffle Tools, 2024; Shuffle Tools, n.d.) implementa un motor de orquestación open source que materializa estos conceptos en flujos ejecutables.

## 2.3. Laboratorios reproducibles, herramientas open source y evaluación

Para investigación aplicada, la reproducibilidad condiciona la validez. Si el entorno cambia entre ejecuciones, las diferencias en resultados no son atribuibles al factor estudiado. Núñez Fernández desarrolla una plataforma SIRP reproducible con Docker Compose para pymes, con un stack casi idéntico al de este TFM (TheHive Project, 2024; Cortex Project, 2024; MISP Project, 2024; Wazuh, 2024) y un motor de workflows con monitoreo por contenedores, lo que valida la viabilidad tecnológica de la solución (Núñez Fernández, 2023). La compartición de información de amenazas entre organizaciones, estandarizada por NIST SP 800-150 (NIST, 2024b), es un habilitador clave para que plataformas como MISP y Cortex aporten valor en la respuesta a incidentes.

Quintero Tamayo et al. plantean playbooks como base de conocimiento para CSIRT, enfatizando la importancia de la estandarización, la claridad en los pasos y el mantenimiento continuo con indicadores de evaluación (Quintero Tamayo et al., 2023). Atluri y Warner añaden que el control de acceso debe sincronizarse con el flujo del workflow para evitar privilegios residuales, lo que importa para garantizar la trazabilidad de un playbook E2E incluso cuando las acciones de contención son simuladas (Atluri & Warner, 2008).

La literatura de SOAR y la de playbooks coinciden en un punto. Las métricas temporales son necesarias, pero no suficientes para evaluar la eficacia operativa. La claridad del trigger y el nivel de detalle del flujo condicionan la ejecución real en la misma medida que el tiempo de respuesta (Stevens et al., 2022). Esta consideración respalda el uso de percentiles p50 y p90 como indicadores primarios, complementados con logs y artefactos del caso para permitir la verificación y el análisis post-hoc (Kinyua & Awuah, 2021; Stevens et al., 2022).

## 2.4. Síntesis y relación con el TFM

Tres ideas articulan la literatura revisada. Primera: en ransomware, el tiempo de reacción condiciona el daño, lo que convierte los procesos repetibles y medibles en una necesidad operativa, no en una preferencia metodológica. Segunda:
SOAR responde a la fragmentación de herramientas, pero la efectividad depende del nivel de detalle del playbook y de su adaptación al contexto concreto, no solo de su existencia. Tercera: marcos como CACAO y ATT&CK, y trabajos como el de Núñez Fernández, confirman que un laboratorio reproducible con herramientas open source es viable para generar evidencias contrastables (Schlette et al., 2024; Núñez Fernández, 2023; Kinyua & Awuah, 2021; CISA, 2023).

**Brecha identificada.** La literatura revisada aporta modelos conceptuales (CACAO, ATT&CK), guías prácticas (NIST,
CISA), una taxonomía de orquestación (Islam et al., 2019), el primer estudio empírico de SOAR en uso (Gutzwiller et al., 2023), frameworks de respuesta a ransomware (Kok et al., 2023; Brown et al., 2023), una revisión de 45 soluciones automáticas (Karlzén & Sommestad, 2023) y validaciones cualitativas de plataformas SIRP (Núñez Fernández). Sin embargo, falta evidencia cuantitativa rigurosa sobre el efecto de un playbook SOAR específico para ransomware en condiciones controladas y reproducibles: la mayoría de los estudios reportan mejoras observadas sin medir MTTR con percentiles, desviación estándar o consistencia entre ejecuciones. Gutzwiller et al. confirman que las herramientas SOAR aumentan la eficiencia, pero no reportan MTTR cuantitativo; Karlzén y Sommestad detectan vaguedad en la descripción de entradas y salidas; y los frameworks de ransomware (Kok, Brown) se centran en el diseño, no en la medición. Esta tesis aborda esa brecha diseñando un laboratorio reproducible, ejecutando un playbook E2E sobre 50 alertas y reportando métricas estadísticas descriptivas que permiten contrastar la hipótesis de que la automatización reduce el MTTR y mejora la consistencia frente a la respuesta manual.

Estas tres conclusiones sustentan el diseño del TFM. El **Anexo J** (`appendix_j.md`) recopila 13 diagramas Mermaid canónicos que ilustran la arquitectura y los flujos de respuesta referenciados en esta revisión.

---

## Índice de Figuras del Capítulo 2

Este capítulo no contiene figuras. Los diagramas de arquitectura referenciados se encuentran en el Anexo J.

## Índice de Tablas del Capítulo 2

| Tabla   | Título                                      |
|---------|---------------------------------------------|
| Tabla 1 | Comparativa Detallada de Plataformas SOAR   |
| Tabla 2 | Progresión de Ransomware por Generación     |
