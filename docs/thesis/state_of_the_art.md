# 2. Estado del arte

Este capítulo revisa la literatura sobre respuesta a incidentes, automatización y orquestación en SOC, con especial atención al ransomware y al uso de playbooks. Los equipos de seguridad operan con ecosistemas de herramientas fragmentados y datos heterogéneos, lo que incrementa la intervención manual e introduce variabilidad difícil de cuantificar y controlar. Las plataformas SOAR actúan como capa de integración que complementa al SIEM, permitiendo operacionalizar procedimientos mediante playbooks sin suprimir la supervisión humana en las decisiones críticas [11].

## 2.1. Respuesta a incidentes y ransomware como dominio de aplicación

La respuesta a incidentes se describe habitualmente como un proceso estructurado en fases de preparación, detección y análisis, contención, erradicación y recuperación [49]. NIST ha sistematizado estas fases y las revisa de forma periódica: en abril de 2025, NIST SP 800-61r2 fue retirada y sustituida por NIST SP 800-61r3, documento que refleja la tendencia a integrar la respuesta a incidentes en el marco más amplio de gestión del riesgo de ciberseguridad [50].

En ransomware, el impacto principal es la pérdida de disponibilidad por cifrado. En muchos ataques recientes eso se combina con exfiltración previa y doble extorsión, lo que acelera los tiempos de decisión. CISA ofrece guías específicas con listas de verificación que concretan las tareas y evidencias mínimas esperadas [25].

Para modelar el comportamiento del adversario y alinear detecciones y acciones, MITRE ATT&CK es una referencia habitual en el sector. La técnica T1486 (Data Encrypted for Impact) describe el cifrado de datos para interrumpir la disponibilidad y extorsionar, e incluye detalles sobre propagación y entornos afectados que orientan la definición de observables e IoCs relevantes [26].

## 2.2. Automatización, SOAR y playbooks en operaciones de seguridad

La proliferación de herramientas con representaciones de datos dispares obliga al analista a saltar entre sistemas durante una misma investigación, lo que eleva el tiempo de respuesta y dificulta cualquier intento de estandarización. SIEM y SOAR son complementarios en este contexto: el SIEM centraliza eventos y genera alertas, y SOAR orquesta las integraciones y ejecuta respuestas automatizadas en las fases de contención y recuperación [11].

Los playbooks son el mecanismo para convertir decisiones tácticas en procedimientos repetibles. Kinyua y Awuah distinguen entre playbook como checklist lineal y runbook como workflow con control de flujo y condiciones, incluyendo puntos de intervención del analista. Esta distinción encaja con diseños que combinan automatización con decisión humana en acciones de alto impacto. Los autores identifican MTTD, MTTR y tiempo de investigación como métricas habituales para evaluar el valor operativo, lo que conecta directamente con las evaluaciones basadas en percentiles de este TFM [11]. Otros trabajos han explorado la aplicación de IA/ML en respuesta a incidentes, con mejoras observadas en detección y clasificación de amenazas en infraestructuras críticas [13], y en la automatización de tareas de seguridad TI para reducir la carga operativa [12].

Sin embargo, la evidencia empírica muestra que tener un playbook no garantiza efectividad. Stevens et al. analizan frameworks de diseño de playbooks y concluyen que producen con frecuencia artefactos insuficientemente detallados para uso real, especialmente para perfiles junior. Los fallos típicos incluyen tareas implícitas omitidas, lenguaje ambiguo y ausencia de ramificación o paralelismo. Cuando los playbooks se iteran junto con los procesos organizativos, la utilidad mejora, lo que implica que el nivel de detalle del diseño afecta al rendimiento real bajo estrés [85].

Schlette et al. analizan 1217 playbooks de múltiples fuentes y detectan ambigüedad sobre qué constituye exactamente un playbook en la práctica. Su conclusión principal es que los playbooks comunitarios suelen requerir transformación antes de ser operativos: herramientas disponibles, requisitos legales, estructura del equipo y procesos internos condicionan esa adaptación. Este resultado justifica que el laboratorio del TFM defina explícitamente su contexto y que el playbook E2E se diseñe para ese entorno, sin asumir reutilización directa [84].

En cuanto a estandarización, OASIS CACAO 2.0 (noviembre de 2023) define un esquema y taxonomía para describir playbooks de ciberseguridad desde la detección hasta la remediación [51]. Microsoft y el Automation SIG de FIRST complementan este marco con guías prácticas e intercambio de experiencias entre CSIRT [27, 38]. La coexistencia de iniciativas paralelas en este ámbito refleja que el sector aún no ha alcanzado convergencia en torno a un estándar único [51, 84], lo que justifica la necesidad de adaptar cualquier playbook al contexto operativo concreto en que va a desplegarse.

## 2.3. Laboratorios reproducibles, herramientas open source y evaluación

Para investigación aplicada, la reproducibilidad condiciona la validez: si el entorno cambia entre ejecuciones, las diferencias en resultados no son atribuibles al factor estudiado. Núñez Fernández desarrolla una plataforma SIRP reproducible con Docker Compose para pymes, con un stack casi idéntico al de este TFM (TheHive, Cortex, MISP, Wazuh y un motor de workflows con monitoreo por contenedores), lo que valida la viabilidad tecnológica del enfoque [73].

Quintero Tamayo et al. plantean playbooks como base de conocimiento para CSIRT, subrayando la importancia de la estandarización, la claridad en los pasos y el mantenimiento continuo con indicadores de evaluación [14]. Atluri y Warner añaden que el control de acceso debe sincronizarse con el flujo del workflow para evitar privilegios residuales, lo que es relevante para garantizar la trazabilidad de un playbook E2E incluso cuando las acciones de contención son simuladas [62].

La literatura de SOAR y la de playbooks coinciden en un punto: las métricas temporales son necesarias, pero no suficientes para evaluar la eficacia operativa. La claridad del trigger y el nivel de detalle del flujo condicionan la ejecución real en la misma medida que el tiempo de respuesta [85]. Esta consideración respalda el uso de percentiles p50 y p90 como indicadores primarios, complementados con logs y artefactos del caso para permitir la verificación y el análisis post-hoc [11, 85].

## 2.4. Síntesis y relación con el TFM

Tres ideas articulan la literatura revisada. Primera: en ransomware, el tiempo de reacción condiciona el impacto, lo que convierte los procesos repetibles y medibles en una necesidad operativa, no en una preferencia metodológica. Segunda: SOAR responde a la fragmentación de herramientas, pero la efectividad depende del nivel de detalle del playbook y de su adaptación al contexto concreto, no solo de su existencia. Tercera: marcos como CACAO y ATT&CK, y trabajos como el de Núñez Fernández, confirman que un laboratorio reproducible con herramientas open source es viable para generar evidencias contrastables [84, 73, 11, 25]. Estas tres conclusiones sustentan el enfoque del TFM.

