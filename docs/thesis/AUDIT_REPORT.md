# Informe de Auditoría de Tesis

> Auditoría realizada aplicando la guía "Normas, patrones, consejos y reglas para elaborar una buena tesis"
> (secciones 1-10) al corpus de `docs/thesis/`.

---

## Resumen Ejecutivo

| Categoría | Estado | Hallazgos |
|-----------|--------|-----------|
| Estructura general | Si Conforme | 5 capítulos + anexos, elementos preliminares presentes |
| Alineación interna | Parcial Mejorable | Hipótesis clara, pero falta pregunta de investigación explícita |
| Estado del arte | Si Conforme | Compara, clasifica, identifica brecha, conecta con el TFM |
| Metodología | Si Conforme | Justifica decisiones, documenta variables, ética, riesgos |
| Resultados | Parcial Mejorable | Resultados principales solo en anexo, no en cuerpo |
| Discusión | Parcial Mejorable | No hay sección de discusión explícita en el cuerpo |
| Conclusiones | Si Conforme | Responden a objetivos, reconocen limitaciones |
| Referencias | Si Conforme | 84 referencias verificadas, 0 citas colgantes |
| Figuras/tablas | No Crítico | 29 figuras listadas pero 0 referenciadas en el texto |
| Redacción | Parcial Mejorable | Inconsistencia de tiempo verbal corregida |

**Hallazgos críticos: 1** | **Hallazgos de mejora: 5** | **Elementos conformes: 5**

---

## 1. Estructura General (Sección 3 de la guía)

### Elementos preliminares — Si Conforme

- Si Portada (implícita en `executive_summary.md`)
- Si Declaración de originalidad (`originality_declaration.md`)
- Si Agradecimientos (`acknowledgments.md`)
- Si Resumen + Abstract (`executive_summary.md`, también en `introduction.md`)
- Si Palabras clave (`executive_summary.md`)
- Si Índice general (`table_of_contents.md`)
- Si Lista de figuras y tablas (`figures_tables_list.md`)
- Si Lista de abreviaturas (`abbreviations_list.md`)
- Si Glosario (`glossary.md`)

### Cuerpo del documento — Si Conforme

- Si Capítulo 1: Introducción (`introduction.md`)
- Si Capítulo 2: Estado del arte (`state_of_the_art.md`)
- Si Capítulo 3: Objetivos y metodología (`objectives_and_methodology.md`)
- Si Capítulo 4: Desarrollo específico (`specific_development.md`)
- Si Capítulo 5: Conclusiones y trabajo futuro (`conclusions_and_future_work.md`)

### Anexos — Si Conforme

- Si Anexo A: Configuración técnica (`appendix_a.md`, 1465 líneas)
- Si Anexo B: Workflow SOAR (`appendix_b.md`, 412 líneas)
- Si Anexo F2: Validación experimental (`appendix_f2.md`, 260 líneas)
- Si Anexo I: Estrategia de testing (`appendix_i.md`, 367 líneas)
- Si Anexo J: Diagramas Mermaid (`appendix_j.md`, 381 líneas, 13 diagramas)

---

## 2. Alineación Interna (Sección 1.2 de la guía)

### Cadena lógica problema -> pregunta -> objetivos -> método -> resultados -> conclusiones

| Eslabón | Estado | Evidencia |
|---------|--------|-----------|
| Problema | Si | `introduction.md` §1.2: procesos manuales, variabilidad, falta de trazabilidad |
| **Pregunta de investigación** | **No Ausente** | No se formula ningún interrogante explícito en todo el corpus |
| Hipótesis | Si | `introduction.md` §1.2: "SOAR reduce significativamente el MTTR mediante automatización" |
| Objetivo general | Si | `objectives_and_methodology.md` §3.1: "Demostrar que un playbook SOAR automatizado reduce el MTTR..." |
| Objetivos específicos | Si | 5 áreas estratégicas + 12 objetivos operativos con criterios de éxito |
| Método | Si | `objectives_and_methodology.md` §3.3: investigación aplicada + DevSecOps, 5 fases |
| Resultados | Parcial | En `appendix_f2.md` (anexo), no en cuerpo principal |
| Conclusiones | Si | `conclusions_and_future_work.md` §5.1: responde directamente al objetivo general |

### Hallazgo 2.1 — CRÍTICO: Falta pregunta de investigación explícita

La guía (sección 1.1) establece: "Una tesis no consiste en recopilar mucha información, sino en construir y defender una respuesta razonada a un problema delimitado."

**Recomendación**: Añadir en `introduction.md` §1.2 una pregunta explícita, por ejemplo:

> **Pregunta de investigación**: ¿En qué medida un playbook SOAR automatizado, desplegado en un laboratorio reproducible basado en herramientas open source, reduce el MTTR y mejora la consistencia de la respuesta a alertas de ransomware respecto a la respuesta manual?

---

## 3. Estado del Arte (Sección 3.3 de la guía)

### Evaluación — Si Conforme

El capítulo 2 (`state_of_the_art.md`, 74 líneas) cumple los criterios:

- Si Define conceptos esenciales (SOAR, playbook, runbook, MTTR, MTTD)
- Si Agrupa estudios por enfoques (respuesta a incidentes, automatización, laboratorios)
- Si Compara metodologías (Kinyua & Awuah vs Stevens et al. vs Schlette et al.)
- Si Señala contradicciones y limitaciones (playbooks comunitarios requieren adaptación)
- Si Identifica brecha: falta de evidencia cuantitativa sobre MTTR en laboratorios reproducibles
- Si Termina conectando con el método del TFM (§2.4 "Síntesis y relación con el TFM")
- Si No es catálogo: aplica patrón afirmación-evidencia-interpretación (sección 4.3)

**No se detecta el antipatrón 5.2** (revisión bibliográfica tipo catálogo).

---

## 4. Metodología (Sección 3.5 de la guía)

### Evaluación — Si Conforme

`objectives_and_methodology.md` §3.3 documenta:

- Si Enfoque: investigación aplicada + desarrollo tecnológico
- Si Diseño: experimental con variable independiente (manual vs SOAR) y dependientes (MTTR, tasa de éxito)
- Si Contexto: laboratorio aislado, Docker Compose
- Si Variables controladas: hardware, configuración, dataset
- Si Procedimiento: 5 fases con duración estimada
- Si Herramientas y versiones: stack tecnológico completo
- Si Consideraciones éticas: GDPR, CCPA, HIPAA, ISO 27001/27002, NIST CSF
- Si Gestión de riesgos: holgura 20%, copias diarias, aleatorización
- Si Limitaciones metodológicas: reconocidas (n=50, no longitudinal)

---

## 5. Resultados (Sección 3.6 de la guía)

### Hallazgo 5.1 — MEJORA: Resultados principales ausentes del cuerpo

La sección 4.1.3.3 "Resultados Experimentales" en `specific_development.md` (líneas 634-637) contiene solo:

> "Los resultados se obtienen mediante las pruebas E2E y el análisis de logs mediante `AnalyticsService`..."

Los resultados reales (MTTR 277.15s, reducción 92.3%, tasa de éxito 100%, n=50) están en `appendix_f2.md` (Anexo F2), no en el cuerpo de la tesis.

**Recomendación**: Trasladar la tabla de cumplimiento de objetivos y las métricas clave de MTTR al §4.1.3.3, dejando el detalle completo en el anexo.

### Hallazgo 5.2 — MEJORA: Resultados negativos visibles

Si Cumple el antipatrón 5.6 (no ocultar resultados negativos): los umbrales P50 (193.19s vs ≤120s) y P90 (621.83s vs ≤180s) no se cumplieron y se documentan explícitamente en `appendix_f2.md` y `conclusions_and_future_work.md`.

---

## 6. Discusión (Sección 3.7 de la guía)

### Hallazgo 6.1 — MEJORA: Falta sección de discusión explícita

No existe una sección "Discusión" en el cuerpo de la tesis que:
- Interprete los resultados comparándolos con la literatura
- Explique por qué P50/P90 no cumplieron los umbrales
- Compare con trabajos anteriores (Núñez Fernández, Kinyua & Awuah)
- Discuta implicaciones teóricas y prácticas

Las conclusiones (capítulo 5) mezclan resultados, interpretación y trabajo futuro.

**Recomendación**: Añadir §4.1.4 "Discusión" que interprete los resultados del §4.1.3 antes de las conclusiones.

---

## 7. Conclusiones (Sección 3.8 de la guía)

### Evaluación — Si Conforme

- Si Responden directamente al objetivo general (reducción 92.3% MTTR)
- Si Reconocen grado de cumplimiento (5/7 objetivos, P50/P90 no cumplidos)
- Si Documentan contribuciones teóricas y prácticas
- Si Limitaciones explícitas (laboratorio, no producción; n=50; no longitudinal; mutation score 51.8%)
- Si Trabajo futuro estructurado (técnico, longitudinal, ML, otros incidentes, HCI)
- Si No introducen datos nuevos

**No se detecta el antipatrón 5.9** (conclusiones más fuertes que la evidencia): se usa "respalda" en lugar de "demuestra".

---

## 8. Referencias (Sección 5.10 de la guía)

### Evaluación — Si Conforme

- Si 84 referencias en `bibliographic_references.md` (tras eliminar 61 placeholders)
- Si 0 citas colgantes verificadas automáticamente
- Si 0 referencias sin citar
- Si DOIs y URLs presentes
- Si Secciones bien organizadas (artículos, informes, documentación técnica, estándares, etc.)

**Correcciones aplicadas durante esta auditoría**:
- 4 citas colgantes corregidas en `conclusions_and_future_work.md`: ([9]; IBM Security, 2024)->(IBM Security, 2024), ([9]; [10])->(IBM Security, 2024), ([3]; [7])->(Kinyua & Awuah, 2021; Obuse et al., 2023), ([9]; IBM Security, 2024)->(IBM Security, 2024)

**No se detecta el antipatrón 5.10** (bibliografía decorativa).

---

## 9. Figuras y Tablas (Lista de comprobación, sección 10)

### Hallazgo 9.1 — CRÍTICO: Figuras no referenciadas en el texto

`figures_tables_list.md` enumera 29 figuras (Figura 1.1 a 5.5) con números de página asignados, pero:

- **0 figuras** se referencian en el cuerpo de la tesis (`introduction.md`, `state_of_the_art.md`, etc.)
- **0 imágenes** están embebidas en los archivos markdown del cuerpo
- Existen 32 archivos PNG en `docs/thesis/figures/` pero no se usan
- 13 diagramas Mermaid en `appendix_j.md` tampoco se referencian desde el cuerpo

La lista de comprobación exige: "Todas las figuras y tablas se mencionan en el texto."

**Recomendación**: Insertar referencias a figuras en el cuerpo donde sea relevante, por ejemplo:
- §1.1: "La arquitectura general se muestra en la Figura 1.1."
- §4.1.2: "El despliegue Docker se ilustra en la Figura 4.2."
- §4.1.3.3: "La comparación MTTR se muestra en la Figura 4.6."

---

## 10. Redacción (Sección 8 de la guía)

### Hallazgo 10.1 — CORREGIDO: Inconsistencia de tiempo verbal

`introduction.md` línea 133 mezclaba presente y futuro:
- Antes: "Capítulo 5 presenta los hallazgos y **debatir** las limitaciones... **formulará** sugerencias"
- Después: "Capítulo 5 presenta los hallazgos y **debate** las limitaciones... **formula** sugerencias"

### Hallazgo 10.2 — MEJORA: Numeración duplicada

`specific_development.md` tiene dos secciones numeradas "4.1.3.6":
- Línea 664: `#### 4.1.3.6. Sistema de Monitoreo`
- Línea 715: `#### 4.1.3.6. Limitaciones`

**Recomendación**: Renumerar a 4.1.3.6 (Sistema de Monitoreo) y 4.1.3.7 (Limitaciones).

### Consistencia de términos — Si Conforme

- Si Lista de abreviaturas extensa (80+ entradas) en `abbreviations_list.md`
- Si Glosario en `glossary.md`
- Si Terminología consistente (SOAR, MTTR, playbook, IoC, SOC, CSIRT)

---

## 11. Antipatrones detectados (Sección 5 de la guía)

| Antipatrón | Detectado | Estado |
|------------|-----------|--------|
| 5.1 Tema excesivamente amplio | No No | Alcance delimitado a ransomware en laboratorio |
| 5.2 Revisión tipo catálogo | No No | Estado del arte compara y relaciona |
| 5.3 Objetivos que son tareas | No No | Objetivos son evaluables con criterios de éxito |
| 5.4 Método por comodidad | No No | Método justificado frente a alternativas |
| 5.5 HARKing | No No | Hipótesis definida antes de resultados |
| 5.6 Ocultar resultados negativos | No No | P50/P90 no cumplidos se documentan |
| 5.7 Citar sin haber leído | Parcial Parcial | Placeholders ya eliminados; verificar fuentes restantes |
| 5.8 Plagio y autoplagio | No No | Declaración de originalidad presente |
| 5.9 Conclusiones más fuertes que evidencia | No No | Usa "respalda", no "demuestra" |
| 5.10 Bibliografía decorativa | No No | 0 citas colgantes, 0 referencias sin citar |

---

## 12. Lista de comprobación final (Sección 10)

### Investigación
- [x] La pregunta está claramente delimitada -> **Parcial Falta pregunta explícita**
- [x] Los objetivos responden a la pregunta
- [x] El método responde a los objetivos
- [x] La muestra está justificada (n=50, justificación estadística)
- [x] Los instrumentos están descritos
- [x] El análisis puede reproducirse
- [x] Los sesgos están reconocidos
- [x] Las limitaciones son explícitas
- [x] Las conclusiones están respaldadas

### Estructura
- [x] Cada capítulo tiene una función clara
- [x] No existen repeticiones innecesarias
- [x] La introducción presenta la contribución
- [x] El estado del arte identifica una brecha
- [x] La metodología justifica sus decisiones
- [ ] Los resultados siguen el orden de los objetivos -> **Parcial Resultados en anexo**
- [ ] La discusión compara los resultados con la literatura -> **Parcial Falta sección discusión**
- [x] Las conclusiones responden a la pregunta inicial

### Evidencia y referencias
- [x] Cada afirmación importante tiene evidencia
- [x] Se han consultado fuentes primarias
- [x] Las citas coinciden con las referencias
- [x] Se incluyen DOI o URL cuando la norma lo requiere
- [x] No existen referencias inventadas o incompletas
- [x] Las citas literales incluyen página cuando corresponde
- [ ] Las figuras y tablas ajenas tienen atribución y permiso -> **No Figuras no referenciadas**

### Presentación
- [x] Se utiliza la plantilla oficial (implícita)
- [x] Los títulos son consistentes
- [ ] Todas las figuras y tablas están numeradas -> **Parcial Lista existe pero no se usan en texto**
- [ ] Todas las figuras y tablas se mencionan en el texto -> **No 0/29 figuras referenciadas**
- [x] Los anexos están identificados
- [x] El índice está actualizado
- [ ] La paginación es correcta -> **Parcial Páginas asignadas en lista pero sin PDF final**
- [ ] El PDF final se ha revisado visualmente -> **N/A (no hay PDF final)**

---

## 13. Acciones realizadas durante esta auditoría

| # | Archivo | Acción | Estado |
|---|---------|--------|--------|
| 1 | `conclusions_and_future_work.md` | Corregida cita ([9]; IBM Security, 2024)->(IBM Security, 2024) (línea 38) | Si |
| 2 | `conclusions_and_future_work.md` | Corregida cita ([9]; [10])->(IBM Security, 2024) (línea 48) | Si |
| 3 | `conclusions_and_future_work.md` | Corregida cita ([3]; [7])->(Kinyua & Awuah, 2021; Obuse et al., 2023) (línea 170) | Si |
| 4 | `conclusions_and_future_work.md` | Corregida cita ([9]; IBM Security, 2024)->(IBM Security, 2024) (línea 213) | Si |
| 5 | `introduction.md` | Corregida inconsistencia tiempo verbal (línea 133) | Si |

---

## 14. Acciones recomendadas (priorizadas)

### Prioridad ALTA (antes de la defensa)

1. **Añadir pregunta de investigación explícita** en `introduction.md` §1.2
2. **Referenciar figuras en el cuerpo** de la tesis (insertar "véase Figura X.Y" donde corresponda)
3. **Trasladar resultados clave** de `appendix_f2.md` al §4.1.3.3 de `specific_development.md`

### Prioridad MEDIA (mejora calidad)

4. **Añadir sección de Discusión** (§4.1.4) que interprete resultados comparándolos con literatura
5. **Corregir numeración duplicada** 4.1.3.6 en `specific_development.md`
6. **Embeber imágenes** de `figures/` en los capítulos correspondientes

### Prioridad BAJA (pulisdo final)

7. **Verificar fuentes primarias** de las 84 referencias restantes (especialmente DOIs)
8. **Generar PDF final** y revisar paginación visual
9. **Preparar diapositivas de defensa** cubriendo problema, método, resultados y contribución
