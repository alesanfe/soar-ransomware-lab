# Auditoría formal — ISO/IEC 25040 sobre SOAR Ransomware Lab

> Auditoría completa ejecutada con el método de evaluación formal
> (evidencia E0–E4, 12 áreas ponderadas, 5 puertas de calidad, escala
> 0–4 por control). A diferencia de `docs/15` (scorecard holístico por
> campos), este informe puntúa **control por control** con la exigencia
> de que solo lo verificado en ejecución real vale 4/4.

## Índice

- [1. Resumen ejecutivo](#1-resumen-ejecutivo)
- [2. Alcance y método](#2-alcance-y-método)
- [3. Puertas de calidad](#3-puertas-de-calidad)
- [4. Matriz de evaluación por áreas](#4-matriz-de-evaluación-por-áreas)
- [5. Hallazgos](#5-hallazgos)
- [6. Referencias y evidencias](#6-referencias-y-evidencias)

## 1. Resumen ejecutivo

### 1.1 Ficha de evaluación

| Campo | Valor |
| --- | --- |
| Proyecto | SOAR Ransomware Lab |
<!-- AUDIT-LIVE:BEGIN -->
| Commit | `b7a05499b3dbf867fe662a94e5ebdd27b258accf` |
| Estado del árbol | 556 ficheros sin commitear (working tree como fuente de verdad — AGENTS.md) |
| Fecha | 2026-11-08 |
| Entorno | Docker 29.7.2, 24 contenedores, perfil hardened por defecto (lab requiere `LAB=1`) |
| Datos generados | `2026-11-08T17:17:19.432263+00:00` por `make audit-report` |
<!-- AUDIT-LIVE:END -->
| Alcance | Aplicación completa + infraestructura + procesos + documentación |
| **Puntuación bruta** | **67/100** |
| **Nota (despliegue lab observado)** | **5.9/10 — C** (GATE-2 cap) |
| **Nota sin el cap (hardened/`API_REQUIRE_AUTH=true`)** | **6.7/10 — B** |
| Confianza | **Alta** — inspección E4 sobre el stack en ejecución |
| Estado | Laboratorio sólido con un gap de postura por defecto corregible en minutos |

### 1.2 Lectura del resultado

La puntuación bruta (67/100 → 6,7) es inferior a la estimación
provisional histórica (8,0–8,7) por tres razones honestas:

1. **El modelo es más estricto**: un control solo llega a 4/4 si se
   verificó ejecutándolo *en esta auditoría* — "implementado+testeado"
   puntúa 3/4 como máximo. Muchos controles sólidos quedan en 3.
2. **Lo observado prevalece sobre lo documentado**: la auditoría corrió
   contra el perfil **lab**, donde la autenticación está OFF, los
   contenedores van como root y el trivy de CI no es bloqueante — el
   perfil hardened existe y está verificado, pero no es lo desplegado.
3. **Las revisiones históricas no reverificaron**: contratos vacíos,
   acciones sin SHA, contenedores anónimos, backend que responde 401 a
   timeouts — hallazgos nuevos de esta inspección.

El gap entre 5,9 y 6,7 es **una variable de entorno**: con
`API_REQUIRE_AUTH=true` (o el perfil hardened ya verificado) el cap de
GATE-2 desaparece. Es la diferencia entre "capaz de ser seguro" y
"seguro tal como está desplegado".

### 1.3 Fortalezas principales (5)

1. **Proceso de defectos failing-first excepcional** — 66 bugs
   confirmados con regresión permanente, evidencia honesta en
   artifacts (BUG-065), clasificación rigurosa de residuales.
2. **Integridad de evidencia E2E** — correlation_id extremo a
   extremo + manifests por test; un incidente se reconstruye de forma
   forense (GATE-5 superado con solvencia).
3. **Rate limiting verificado en vivo (E4)** — 59×422 → **429** al
   superar 60/min en `/api/v1/contain`; enforcement real, no declarativo.
4. **Contención bien guardada por diseño** — `SOAR_CONTAIN_ENFORCE` + allowlist
   `victim_*` + exclusión dura de `soar_*` + snapshot before/after → GATE-3 ok.
5. **Backup/restore probado de verdad** (TC-22) y arquitectura
   hexagonal forzada por tests — no son claims, son propiedades medidas.

### 1.4 Debilidades principales (5)

1. **Autenticación OFF en el despliegue por defecto** — endpoints
   sensibles (`/contain`, `/backup/restore`, `/tests/run`) abiertos
   sin token (observado E4). Único bloqueo de nota.
2. **DevSecOps débil**: GitHub Actions sin fijar por SHA (`@v4`,
   `@master`, `@main`), sin SBOM, sin firma/provenance, sin
   dependabot, sin SECURITY.md, trivy solo `fs` y no bloqueante.
3. **docker.sock sobre-expuesto en lab**: `network_watcher` con rw
   (solo lee eventos), workers de Shuffle heredan rw sin proxy,
   `soar_api` rw — 5+ accesos vs. la mitigación del perfil hardened.
4. **Techo de ingesta medido**: ~2–3 escrituras síncronas
   webhook→OpenSearch → HTTP 500 bajo ráfaga; sin backpressure/cola.
5. **Higiene operacional**: 5 contenedores anónimos no gestionados,
   ejecuciones zombie de Shuffle que requieren GC manual, `401`
   erróneos del backend ante timeouts de OpenSearch.

### 1.5 Recomendación final

Apto como laboratorio académico avanzado. **Acción única de máximo
impacto**: desplegar con auth ON por defecto — elimina el único cap y
sube la nota aplicable a ~6,7 inmediatamente (y a ~7,5+ al cerrar los
hallazgos mayores de DevSecOps, todos de esfuerzo bajo). La
calificación A histórica (8,0–8,7) sigue siendo alcanzable: requiere
cerrar GATE-2 + los 5 hallazgos mayores P0, no trabajo estructural.

## 2. Alcance y método

### 2.1 Qué se ejecutó (fases de la metodología)

| Fase | Ejecutada | Evidencia |
| --- | --- | --- |
| 1 Congelar línea base | Sí | `reports/audit/freeze.txt`, `containers.txt` |
| 2 Inventario | Sí | 30 contenedores, 38 paths OpenAPI, 5 integraciones, 2377 tests |
| 3 Calidad estática | Sí | `reports/audit/static.txt` (ruff/bandit) |
| 4 Pruebas | Parcial | evidencia de sesión (regresiones 66/66) + cadena en curso |
| 5 Stack real | Sí | `docker inspect` ×16 + montajes socket ×30 |
| 6 Seguridad dinámica | Sí | auth/rate-limit/contain/tests-run verificados live |
| 7 E2E | En curso | TC-00 4/4, TC-01 1/2 al momento del informe |
| 8 Rendimiento | Sí | techo medido en TC-04 (sesión previa) + KPIs |
| 9 Mapeo marcos | Sí | §4 + matriz consolidada docs/10-14 |
| 10 Informe+backlog | Sí | este documento |

### 2.2 Regla de puntuación adoptada

Cada control 0–4 (0=ausente, 1=documental, 2=parcial, 3=implementado
y probado, 4=verificado en vivo). **Decisión metodológica**: no se
apila el multiplicador de evidencia — la escala 0–4 ya lo codifica en
sus definiciones (4 exige verificación en vivo); aplicarlo además
penalizaría dos veces el mismo factor. Se indica el nivel de evidencia
(E0–E4) junto a cada puntuación para trazabilidad.

## 3. Puertas de calidad

| Gate | Veredicto | Detalle |
| --- | --- | --- |
| GATE-1 Integridad/reproducibilidad | **CONDICIONAL** | Commit y freeze guardados; 163 ficheros sin commitear — reproducibilidad = commit+working tree, no solo commit. Versiones y estado capturados. |
| GATE-2 Seguridad crítica | **FALLA en lab** | `API_REQUIRE_AUTH=false` en el contenedor desplegado → `/api/v1/contain` (422 sin token), `/backup/restore`, `/tests/run` alcanzables sin autenticación. La acción destructiva de contención está desarmada (`SOAR_CONTAIN_ENFORCE=0`), pero `/backup/restore` es destructiva y abierta. **Cap 5,9 hasta corrección.** |
| GATE-3 Seguridad de la automatización | **SUPERADA** | Contención: autorizada por allowlist `victim_*`/`soar.victim`, scope-limitada (excluye `soar_*`/`api`), trazable (snapshot before/after), idempotente-tolerante (disconnect/pause por red con warning→continúa), recuperable (unpause/reconnect). No puede contener un activo incorrecto. |
| GATE-4 E2E real | **SUPERADA** | Cadena TC-00..33+KPI en ejecución contra stack real (no mocks): TC-00 4/4, TC-01 1/2 al informe. |
| GATE-5 Trazabilidad | **SUPERADA** | correlation_id + manifest por test + honestidad post-BUG-065 → incidente reconstruible. |

## 4. Matriz de evaluación por áreas

Convención: `score/E` = puntos 0–4 / nivel de evidencia. Peso entre
paréntesis. La puntuación de área = (Σscores / (4×N)) × peso.

### 4.1 Adecuación funcional y SOAR — peso 14 → **10,3**

| Control | Score/E | Base |
| --- | --- | --- |
| Recepción de alertas | 4/E4 | webhook→workflow verificado TC-00/01 |
| Validación de esquema | 4/E4 | 422 Pydantic observado live |
| Normalización/dedup | 2/E2 | normalización en pipeline; dedup no evidenciada |
| Correlación | 4/E4 | correlation_id e2e |
| Extracción de observables | 4/E4 | enrichment TC-01 IoCs reales |
| Enriquecimiento multifuente | 4/E4 | Cortex+MISP+ES+Tenzir |
| Timeouts | 3/E3 | clientes con timeout+retry |
| Resultados contradictorios | 2/E2 | sin política explícita de conflicto |
| Modelo de puntuación | 3/E3 | decisión en workflow |
| Explicabilidad del veredicto | 2/E2 | veredicto sin `reasons`/`confidence` rico |
| Decisión contain/observe | 4/E4 | verificado |
| Ejecución de acciones | 4/E4 | enforce real verificado |
| Registro de evidencias | 4/E4 | manifests |
| Reintentos | 3/E3 | retry+backoff clientes |
| Idempotencia | 3/E3 | pause/disconnect tolerantes |
| Rollback/compensación | 2/E2 | reversible manual; sin acción rollback |
| Intervención humana / aprobación | 1/E1 | TheHive tasks; sin gate de aprobación |
| Finalización/cierre | 3/E3 | caso en TheHive |

Σ≈59/80 → 0,74×14. **Brechas**: explicabilidad rica del veredicto,
aprobación humana, rollback formal, deduplicación.

### 4.2 Respuesta a incidentes y ransomware — peso 14 → **8,4**

| Control | Score/E | Base |
| --- | --- | --- |
| Preparación | 4/E4 | stack+playbook+secrets automáticos |
| Detección | 3/E3 | alerta inyectada por simulador (sin IDS real) |
| Notificación | 3/E3 | nodos notificación en workflow |
| Evaluación/decisión | 4/E4 | enriquecimiento→decisión verificada |
| Contención | 4/E4 | enforce+simulated |
| Erradicación | 1/E1 | no hay fase de erradicación real |
| Recuperación | 3/E4 | backup/restore TC-22 |
| Cierre | 3/E3 | cierre de caso |
| Lecciones aprendidas | 2/E2 | parcial (NIST IR 8374 hallazgo previo) |
| T1486 + ATT&CK | 4/E4 | 53 IDs verificados, STIX export |
| Inhibición de backups / doble extorsión / exfiltración | 1/E1 | escenarios no cubiertos (CISA) |
| Movimiento lateral / SMB / credenciales | 2/E2 | mapeados en ATT&CK, no simulados |
| Aislamiento endpoint / bloqueo IoCs / preservación | 4/E4 | disconnect+pause+case evidence |
| Métricas MTTD/MTTR/latencias/éxito | 4/E4 | TC-KPI + node-timings |
| Tasas FP/FN / escalado humano / revertidas | 1/E1 | no medidas |

Σ≈45/72 → 0,60×14. **Brechas**: erradicación, doble extorsión,
FP/FN medidos, escalado humano, telemetría real (IDS).

### 4.3 Seguridad de aplicación y API — peso 10 → **4,6**

| Control | Score/E | Base |
| --- | --- | --- |
| Autenticación | 2/E4 | implementada+testeada pero **OFF observado** |
| Autorización por endpoint | 2/E4 | `Depends(require_api_auth)` presente, no-op |
| JWT (exp/iat/iss/aud) | 3/E3 | implementado+tests; no verificable con auth off |
| Validación de entradas | 4/E4 | 422 Pydantic live; whitelist en `/tests/run` |
| Rate limiting real | 4/E4 | **429 verificado live a 60/min** |
| Inyección / deserialización | 3/E3 | whitelist+Pydantic+security tests |
| TLS | 3/E4 | nginx 1.2/1.3 HIGH:!aNULL |
| Errores sin filtración | 3/E3 | 500 genérico + log interno |
| OpenAPI sincronizado | 4/E4 | 38 paths vivos |
| Límites de tamaño / archivos / SSRF / CORS | 2/E2 | parciales, no verificados exhaustivamente |
| Logs sin secretos | 3/E3 | scrub Promtail (regex) |
| Sesiones/revocación/audiencia/rotación | 2/E2 | JWT sin revocación; rotación env (BUG-062 fix) |

Σ≈37/64 → 0,55×10. El área más castigada por la regla de coherencia:
la implementación existe pero el sistema observado la desactiva.

### 4.4 Arquitectura y mantenibilidad — peso 10 → **8,2**

| Control | Score/E | Base |
| --- | --- | --- |
| Hexagonal real (deps→domain, sin imports prohibidos) | 4/E4 | tests/architecture lo fuerzan |
| Puertos/adaptadores, integraciones reemplazables | 4/E3 | composition root + clientes uniformes |
| Modelo de errores / config desacoplada | 3/E3 | HTTPException uniforme, settings |
| Testeable sin servicios externos | 4/E4 | suite unit+integration lo prueba |
| Complejidad/duplicación/dead code | 3/E3 | radon/xenon/vulture en gates |
| Sin módulos omniscientes | 3/E3 | mayor módulo ~600 LOC; sin god-objects |
| Lógica en scripts fuera del modelo | 2/E2 | 103 scripts con responsabilidad operativa |

Σ≈23/28 → 0,82×10. Área más fuerte junto a observabilidad.

### 4.5 Pruebas y aseguramiento — peso 12 → **8,0**

| Control | Score/E | Base |
| --- | --- | --- |
| Unitarias | 4/E4 | suite masiva verificada |
| Propiedad/mutación | 3/E3 | existen (mutación on-demand, no en gate) |
| Contratos | 1/E2 | `tests/contracts/` **vacío** |
| Integración/componentes | 4/E4 | 103/103 externos verificados |
| Seguridad | 4/E4 | suite dedicada |
| Arquitectura | 4/E4 | guardián activo |
| E2E | 4/E4 | cadena en ejecución real |
| Rendimiento | 3/E4 | TC-04 mide (y revela) el techo |
| Resiliencia/caos | 2/E2 | restarts probados; sin caos |
| Aceptación | 3/E3 | TCs como aceptación |
| Cobertura ≥80 / e2e críticos | 4/E4 | gate 80 %, cadena completa |
| Flakiness / reproducibilidad | 3/E4 | tracking+clasificación; TC-04 intermitente |

Σ≈43/52 → 0,79×12. **Brecha**: contratos vacíos, mutación fuera de
gate, caos ausente, cadena lenta (horas).

### 4.6 Fiabilidad, resiliencia y recuperación — peso 10 → **5,6**

| Control | Score/E | Base |
| --- | --- | --- |
| Timeout/retry/backoff/CB | 4/E4 | base_client uniforme, verificado |
| Idempotencia de acciones | 3/E3 | tolerante, no "limpia" |
| Persistencia de estado | 3/E3 | ejecuciones en OpenSearch |
| Dead-letter queue | 0/E0 | ausente |
| Recuperación tras reinicio | 2/E3 | TC-22 restore; sin resume de playbook |
| No duplicación de acciones | 3/E3 | correlation dedup parcial |
| Degradación controlada | 3/E4 | CB observado; backend 401-a-timeout es degradación deshonesta |
| Cierre consistente / estado parcial | 3/E3 | artifacts honestos post-BUG-065 |
| Fallo de integraciones (Cortex/MISP/TheHive/Loki/Tenzir) | 3/E3 | CB+retry por cliente |
| Escenarios no cubiertos (OOM, disco, clock skew, API restart mid-exec, msg duplicado) | 1/E1 | sin pruebas |

Σ≈32/56 → 0,55×10. **Brechas**: DLQ, resume tras reinicio,
idempotencia limpia, cobertura de escenarios de fallo exóticos.

### 4.7 Infraestructura y Docker — peso 8 → **4,8**

| Control | Score/E | Base |
| --- | --- | --- |
| privileged=false | 4/E4 | 0/30 privilegiados observado |
| Usuario no-root | 2/E4 | lab: api/redis root; hardened uid1000 (E4, no desplegado) |
| read_only / cap_drop / no-new-privileges | 2/E4 | solo hardened (E4 verificado antes) |
| Límites RAM / CPU / PIDs | 3/E4 | mem 100 %, PIDs nil, CPU parcial |
| Healthchecks | 4/E4 | 23/23 |
| Redes / puertos mínimos | 4/E4 | 3 redes segregadas |
| **docker.sock** | 2/E4 | api+orborus+network_watcher rw, promtail ro, cortex+shuffle proxy rw, workers rw |
| Secretos fuera de vistas | 3/E3 | `.env.container` ro; env visible por exec |
| Imágenes fijadas | 4/E4 | digest pinning + verificador |
| Escaneo imágenes | 1/E2 | trivy **fs** no-gating; sin image scan |
| Firma/provenance | 1/E1 | ausente |
| Restart/logs rotados/backups/restore | 4/E4 | TC-22 + políticas |

Σ≈38/64 → 0,58×8. El socket rw en `network_watcher` (solo lee) y la
herencia rw en workers son sobre-privilegio real, no justificado.

### 4.8 Rendimiento y eficiencia — peso 7 → **3,9**

| Control | Score/E | Base |
| --- | --- | --- |
| Latencia total/decisión/contención | 4/E4 | TC-04 + KPIs medidos |
| Percentiles p50-p99 | 3/E3 | StatisticalCalculator (std_dev verificado) |
| Throughput / CPU / mem | 3/E4 | techo ~2-3 writes medido live |
| Colas / recuperación post-saturación | 2/E2 | cola larga documentada (Cortex backlog) |
| Cargas: 1 y 10 alertas | 4/E4 | ejecutadas (10-way falla por techo = evidencia) |
| Cargas: 50/100/burst | 0/E0 | no ejecutadas |
| Integración lenta/caída | 3/E3 | CB+timeout; degradación observada |
| Umbrales de regresión | 1/E2 | KPIs miden pero no gatean |

Σ≈23/48 → 0,56×7. **Brecha estructural**: sin backpressure, cliff a
~10 concurrentes, sin pruebas de carga media/alta.

### 4.9 DevSecOps y cadena de suministro — peso 6 → **1,9**

| Control | Score/E | Base |
| --- | --- | --- |
| Dependabot/Renovate | 0/E0 | ausente |
| Actions fijadas por SHA | 1/E4 | `@v4`/`@master`/`@main` — mutables, observado |
| SAST | 4/E4 | ruff/bandit/mypy ejecutados en auditoría |
| SCA / escaneo contenedores | 2/E4 | trivy fs existe pero `continue-on-error`, sin image |
| Secretos | 4/E4 | trufflehog+scan-secrets en CI |
| SBOM / licencias / firma / provenance | 0/E0 | ausentes |
| Branch protection / revisión / permisos CI | 1/E1 | plantillas PR; no verificable |
| Entornos/artefactos versionados/build reproducible | 2/E2 | imágenes pinneadas; build no attestado |
| SECURITY.md / gestión CVE | 0/E0 | ausente |
| OpenSSF Scorecard | 0/E0 | no ejecutado |

Σ≈14/60 → 0,32×6. **Área más débil del proyecto** — consistente con
SLSA L1 y SSDF parciales de rondas previas.

### 4.10 Observabilidad, auditoría y evidencias — peso 5 → **4,1**

| Control | Score/E | Base |
| --- | --- | --- |
| Correlation/incident/execution ID | 4/E4 | e2e verificado |
| Timestamps/logs estructurados/severidad/fuente | 4/E4 | Loki+structured logger |
| Acción/resultado/duración | 4/E4 | manifests honestos post-BUG-065 |
| Errores tipados | 3/E3 | HTTPException+logger |
| Métricas | 4/E4 | /metrics+Grafana+KPIs |
| Trazas distribuidas | 1/E1 | sin OTel (correlación por ID, no spans) |
| Integridad/retención/anti-modificación de logs | 2/E2 | Loki estándar, sin sellado |
| Exportación | 3/E3 | CACAO/STIX exports implementados |

Σ≈29/40 → 0,81×5. Segundo área más fuerte.

### 4.11 Documentación y reproducibilidad — peso 2 → **1,7**

| Control | Score/E | Base |
| --- | --- | --- |
| README/instalación/arquitectura/integraciones | 4/E4 | docs/01-04 + verificados |
| Threat model/runbooks/playbooks/testing/ops/troubleshooting | 4/E4 | STRIDE + docs/04/05 + Make targets |
| API ref/OpenAPI/env vars/secretos/recovery | 4/E4 | openapi 38 paths + docs |
| Limitaciones/resultados experimentales | 4/E4 | honestidad documentada |
| Versiones/licencia/contribución | 3/E3 | presentes |
| SECURITY.md (política divulgación) | 0/E0 | ausente |
| Prueba "externo lo levanta solo" | 3/E2 | `make up` automatizado; no validado por tercero |

Σ≈30/36 → 0,84×2.

### 4.12 Calidad experimental y validez — peso 2 → **1,4**

| Control | Score/E | Base |
| --- | --- | --- |
| Pregunta/variables/diseño experimental | 3/E3 | TFM con métricas definidas |
| N ejecuciones / warm-up / independencia | 2/E2 | muestras limitadas, warm-up no declarado |
| Media/mediana/p50-p99/desv/CV/IC | 3/E3 | StatisticalCalculator (std_dev ✓) |
| Repetibilidad / datos brutos / scripts análisis | 4/E4 | artifacts+KPI scripts |
| Limitaciones / amenazas a la validez | 4/E4 | documentadas honestamente |
| Comparación manual-vs-automatizada | 1/E2 | MTTR auto medido; manual = referencia, NO ensayo controlado |

Σ≈17/24 → 0,68×2. La mejora 92,3 % MTTR es válida como comparación
contra referencia, no como ensayo — el doc lo reconoce.

### 4.13 Puntuación consolidada

| Área | Peso | Obtenido | % |
| --- | --- | --- | --- |
| 1 Funcional SOAR | 14 | 10,3 | 73 % |
| 2 IR y ransomware | 14 | 8,4 | 60 % |
| 3 Seguridad API | 10 | 4,6 | 46 % |
| 4 Arquitectura | 10 | 8,2 | 82 % |
| 5 Pruebas | 12 | 8,0 | 79 % |
| 6 Fiabilidad | 10 | 5,6 | 55 % |
| 7 Infra/Docker | 8 | 4,8 | 58 % |
| 8 Rendimiento | 7 | 3,9 | 56 % |
| 9 DevSecOps | 6 | 1,9 | 32 % |
| 10 Observabilidad | 5 | 4,1 | 81 % |
| 11 Documentación | 2 | 1,7 | 84 % |
| 12 Experimental | 2 | 1,4 | 68 % |
| **TOTAL** | **100** | **67,0** | **6,7/10** |

Con GATE-2 (auth omitida en endpoints sensibles, observada en el
despliegue lab): **nota final 5.9/10 — C** hasta corrección. Con
`API_REQUIRE_AUTH=true` o el perfil hardened: **6.7/10 — B**.

### 4.14 Cobertura de marcos (los 12 del método)

| Marco | Cobertura | Fuente |
| --- | --- | --- |
| ISO/IEC 25010 | Evaluado como modelo de campos (docs/15) + esta auditoría | ✅ |
| ISO/IEC 25040 | Proceso de esta auditoría | ✅ |
| ISO/IEC 27035 | ✅ fases mapeadas (docs/10); erradicación/lecciones parciales | ✅🟡 |
| NIST CSF 2.0 | ✅ funciones mapeadas (docs/10); Govern organizacional ➖ | ✅ |
| NIST 800-61r3 | ✅ ciclo Detect/Respond/Recover cubierto; r2→r3 actualizado | ✅ |
| MITRE ATT&CK | 53 IDs verificados con STIX export | ✅ |
| MITRE D3FEND | Matriz ofensiva→defensiva (docs/10); no formalizada como grafo | 🟡 |
| CISA #StopRansomware | Cifrado/aislamiento/evidencia ✅; doble extorsión/exfiltración ❌ | 🟡 |
| OWASP ASVS | Controles API mapeados (docs/12); nivel 1+2 parcial | 🟡 |
| CIS Docker | hardening verificado; socket/escaneo pendientes | 🟡 |
| NIST SSDF | SAST/secretos ✅; SBOM/firma/provenance ❌ | 🟡 |
| OpenSSF Scorecard | No ejecutado | ❌ |

## 5. Hallazgos

### 5.1 Críticos

**AUD-CRIT-01 — Autenticación omitida en endpoints sensibles
(despliegue por defecto)**
- Evidencia E4: `API_REQUIRE_AUTH=false` en `soar_api` desplegado;
  `/services/status`→200 y `/api/v1/contain`→422 sin token;
  `/backup/restore` y `/tests/run` abiertos.
- Riesgo: cualquier cliente con acceso a :8000 puede restaurar
  backups o disparar acciones — destrucción de estado sin identidad.
- Marco: GATE-2, ASVS V1/V4, CSF PR.AA.
- Corrección: `API_REQUIRE_AUTH=true` por defecto (opt-out explícito)
  o documentar que el despliegue canónico seguro es el hardened —
  **minutos, elimina el cap de nota**.
- Prioridad: **P0**.

### 5.2 Mayores

| ID | Hallazgo | Evidencia | Marco | Prioridad |
| --- | --- | --- | --- | --- |
| AUD-MAJ-01 | `network_watcher` monta docker.sock **rw** (solo lee eventos) + workers Shuffle heredan rw sin proxy | inspect E4 | CIS Docker, ZT | P0 |
| AUD-MAJ-02 | GitHub Actions sin SHA (`@v4`, `@master`, `@main`) | workflows E4 | SSDF, SLSA | P0 |
| AUD-MAJ-03 | Trivy solo `fs` + `continue-on-error` — sin escaneo de imágenes ni gate | ci.yml E4 | SSDF, 800-190 | P0 |
| AUD-MAJ-04 | Techo de ingesta ~2-3 writes síncronos → 500s; sin backpressure | TC-04 medido | ISO25010 eficiencia | P0 |
| AUD-MAJ-05 | 5 contenedores anónimos + workers sin GC automática | `docker ps` E4 | operación | P1 |
| AUD-MAJ-06 | Backend devuelve 401 ante timeouts OpenSearch (clasificación errónea) | logs E4 | fiabilidad | P1 |
| AUD-MAJ-07 | Sin SBOM/firma/provenance (SLSA L1) | inventario E4 | SSDF, SLSA | P1 |
| AUD-MAJ-08 | Hardened no es el desplegado por defecto (root, sin cap_drop, sin read_only) | inspect E4 | CIS, 800-190 | P0 |

### 5.3 Menores

| ID | Hallazgo | Prioridad |
| --- | --- | --- |
| AUD-MIN-01 | Sin SECURITY.md (canal de divulgación) | P1 |
| AUD-MIN-02 | `tests/contracts/` y `tests/baseline/` vacíos | P1 |
| AUD-MIN-03 | 109 EXE002 (+x sin shebang) + 1 F023 en ruff | P2 |
| AUD-MIN-04 | Sin dependabot | P1 |
| AUD-MIN-05 | CISA: doble extorsión/exfiltración/nube no cubiertos | P2 |
| AUD-MIN-06 | Sin OpenTelemetry (correlación por ID, no spans) | P2 |
| AUD-MIN-07 | Dual Makefile divergente | P2 |
| AUD-MIN-08 | MTTR manual=referencia, no condición experimental controlada | P2 |
| AUD-MIN-09 | Sin DLQ en ingesta | P1 |
| AUD-MIN-10 | Secretos visibles vía `docker exec env` | P2 (residual documentado) |

### 5.4 Riesgos residuales

- **Perfil lab asume entorno de confianza** — el stack es
  educativo por diseño; el riesgo es que "lab" se use como
  plantilla de producción sin activar hardened. Mitigación: hacer
  hardened el perfil por defecto.
- **TheHive 3.5.2 legacy** — sin mantenimiento upstream; aislado
  pero presente.
- **`.env.full` versionado por decisión** — exposición residual
  aceptada y documentada (SOAR-018); aun así es material sensible en
  el working tree.
- **Apps de terceros en Shuffle workers** — código externo corre con
  socket rw; el modelo de amenaza lo asume para el lab.
- **SEC-004: clave TLS vieja en historial Git (riesgo aceptado
  2026-11-09)** — `soar.local.key` quedó versionada en commits antiguos.
  La key fue rotada (par nuevo RSA-2048 con SANs, BUG-080) y la antigua
  está fuera de uso; purgar el historial reescribe todos los commits y
  se decidió NO hacerlo. El riesgo residual es que alguien firme un
  cert nuevo con la CA vieja — mitigado porque (a) la CA del lab es
  interna y offline, (b) el par rotado es el único desplegado, (c) los
  ficheros están untracked+gitignored desde el fix. Si el repo se hace
  público algún día, reabrir este ítem.

### 5.5 Backlog priorizado (para alcanzar A)

**P0 — desbloquea el cap y los mayores de mayor riesgo:**
1. `API_REQUIRE_AUTH=true` por defecto (elimina GATE-2 → nota 6,7)
2. docker.sock ro en `network_watcher`; socket-proxy para workers
3. Fijar todas las Actions por SHA
4. Trivy image scan gating (no solo fs+continue-on-error)
5. Cola de admisión+idempotencia en el webhook (elimina el techo 500)
6. Documentar hardened como despliegue canónico seguro

**P1 — cierra el grueso de brechas:**
7. SBOM CycloneDX + attestation en CI
8. SECURITY.md + dependabot
9. Rellenar tests/contracts/ (Schemathesis) + baseline (golden KPI)
10. GC automática de ejecuciones zombie + workers
11. 503 honesto en backend ante timeouts OpenSearch
12. DLQ + resume de playbook tras reinicio
13. Mutación en gate (subset acotado)

**P2 — excelencia:**
14. OpenTelemetry spans
15. Escenarios CISA restantes (doble extorsión/exfil)
16. FP/FN medidos + escalado humano
17. OpenSSF Scorecard en CI
18. Ensayo controlado manual-vs-automatizado (o reformular como
    comparación contra referencia — ya documentado honestamente)

### 5.6 Nivel de confianza

**Alta.** A diferencia de la estimación provisional (que partía de
revisiones históricas), esta auditoría verificó el stack en ejecución:
auth/rate-limit/validación probados con requests reales, docker.sock
inspeccionado en los 30 contenedores, ruff/bandit ejecutados,
`docker inspect` del perfil desplegado, cadena E2E corriendo contra
infra real. Lo no verificado se marca E0–E2 explícitamente, no se
presume.

## 6. Referencias y evidencias

- `reports/audit/freeze.txt` — commit, versiones, pip freeze, estado.
- `reports/audit/containers.txt` — 30 contenedores en ejecución.
- `reports/audit/container_security.txt` — inspect ×16 (privilegios,
  usuario, caps, límites).
- `reports/audit/docker_sock.txt` — montajes de socket por contenedor.
- `reports/audit/static.txt` — ruff (109 EXE002+1 F023), bandit (B105
  falsos positivos), pip-audit ausente.
- Verificación live: `/services/status` 200 sin token; `/api/v1/contain`
  422→429 a ~60 req/min; openapi.json 38 paths; env `API_REQUIRE_AUTH=false`,
  `SOAR_CONTAIN_ENFORCE=0`.
- `docs/13` — 66 bugs con regresión; `docs/10/12/14` — veredictos por
  marco; `docs/15` — scorecard holístico (complementario: evalúa la
  app por campos, este doc puntúa controles con exigencia E4).
- Cadena E2E en curso: TC-00 4/4, TC-01 1/2 al momento del informe.

## 7. Anexo — estado post-auditoría (verificado 2026-11-07)

La auditoría de 2026-11-05 es una foto del perfil lab desplegado en ese
momento. Desde entonces se remediaron y **re-verificaron live** varios
hallazgos — el texto original queda intacto como registro; esta tabla
refleja el estado comprobado, no el declarado:

| Hallazgo original | Estado 2026-11-07 | Evidencia |
| --- | --- | --- |
| **GATE-2**: `API_REQUIRE_AUTH=false` → `/contain`, `/backup/restore` abiertos | **RESUELTO** | `API_REQUIRE_AUTH=true` en el contenedor desplegado; `POST /api/v1/alerts` → 401 sin token, 202 con `X-Service-Token`; comparación constant-time; tests adversariales 7/7. **El cap 5,9 desaparece → nota aplicable ≥6,7.** |
| Debilidad #4: techo de ingesta ~2-3 writes síncronos, sin cola ni backpressure | **RESUELTO** | Cola Redis Streams + `202 Accepted` + worker async (PERF-001): P50=167 ms / P95=174 ms a 60 concurrentes; backpressure 503+`Retry-After` a los 50k (PERF-003); idempotencia dedup + `X-Idempotency-Key` (PERF-002). Queue-wait medido: 7 ms. |
| AUD-MAJ-03: Trivy solo `fs`, sin escaneo de imagen ni SBOM | **PARCIAL** | Trivy imagen ejecutado (`reports/trivy-api.json`: 0 CRITICAL tras `apt upgrade`, 58 HIGH documentados) + SBOM (`reports/sbom-api.json`, 97 comp.). **Falta**: gate en CI. |
| "401 erróneos del backend ante timeouts de OpenSearch" | **CAUSA RAÍZ DIAGNOSTICADA** | No era auth: OpenSearch en **flood-stage** (disco ~95 %) → índices read-only → lookup de apikey de Shuffle vacío → 401 de observabilidad. Mitigado: prune (~16 GB), `clean-containers` en prep e2e, guardarraíl `check-disk` (WARN≥88/CRIT≥95 + bloques read_only_allow_delete). |
| Higiene: workers Orborus acumulados (2370 parados) | **MITIGADO** | `make clean-containers` (prune >1 h) enganchado a `test-e2e`; `CLEANUP: true` ya estaba en Orborus — el leak era acumulación histórica. |
| Mutación on-demand, no en gate | **PARCIAL** | Ejecutado con **score efectivo 96.9 %** (1937 killed / 63 survived — mayoría equivalentes catalogados; `reports/mutmut-final-status.txt`). Sigue fuera del gate CI por duración. |
| Coverage gate 80 % | **SUPERADO** | 93.09 % global / 85.66 % branch, críticos ≥95 %, 2188 tests verdes. |

**Gates actualizados**: GATE-2 pasa de FALLA a **SUPERADA** (auth ON
verificada en el despliegue real, no solo en el perfil hardened).
GATE-1/3/4/5 sin cambios.

**Debilidades que siguen abiertas** (honestas): GitHub Actions sin pin
por SHA, sin SECURITY.md, docker.sock sobre-expuesto en lab (5+ rw),
contenedores anónimos, e2e fuera de CI, Schemathesis/Pact vacíos,
soak/chaos ausentes, `X-Service-Token` sin scopes RBAC.
