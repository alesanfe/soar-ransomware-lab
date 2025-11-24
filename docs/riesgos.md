
# Riesgos

## 1. Descripción breve
Identificar riesgos técnicos y de tiempo que pueden afectar el desarrollo del TFM, proponiendo mitigaciones factibles para un proyecto unipersonal.

## 2. Riesgos identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Imágenes Docker inestables | Alta | Alto | Usar versiones LTS y fijar tags estables; probar local antes de producción |
| Timeouts en analyzers de Cortex | Media | Medio | Configurar límites de tiempo y reintentos; reducir número de analyzers simultáneos |
| Errores de autenticación en APIs | Alta | Alto | Validar tokens y scopes; implementar scripts de healthcheck y rotación de credenciales |
| Falta de recursos hardware en VM | Media | Alto | Ajustar tamaño de contenedores; optimizar servicios; usar entornos ligeros |
| Licencias Windows | Baja | Medio | Verificar disponibilidad de licencias antes de iniciar; usar versiones de evaluación si es necesario |
| Retrasos por curva de aprendizaje | Alta | Medio | Planificar tiempo para pruebas; usar documentación oficial y ejemplos |
| Fallos en integración entre servicios | Media | Alto | Probar conexiones paso a paso; usar logs detallados y fallback manual |
| Deriva de alcance | Media | Medio | Definir alcance en documento inicial; aplicar checklist y priorizar tareas críticas |
| Fallos en configuración de red interna | Baja | Alto | Validar puertos y reglas de firewall; usar scripts de verificación |
| Problemas con almacenamiento persistente | Media | Medio | Configurar volúmenes en Docker correctamente; realizar pruebas de backup |
| Dependencia de servicios externos (APIs públicas) | Baja | Medio | Implementar manejo de errores y fallback local; limitar llamadas externas |
| Puertos en uso | Alta | Alto | Ajustar `.env` con puertos configurables; verificar disponibilidad antes de levantar servicios |
| Analyzers lentos | Alta | Alto | Limitar analyzers, configurar `timeout` y reintentos; priorizar los más rápidos |
| Postgres caído | Media | Alto | Healthcheck y uso de volúmenes SSD; plan de restauración desde backups |
| Redis caído | Media | Alto | Healthcheck y reinicio rápido; opción de usar sin persistencia en entornos demo |
| Tokens inválidos | Alta | Alto | Rotación periódica y pruebas desde Shuffle; fallback a token previo documentado |

---

## 3. Matriz de riesgos (Impacto vs Probabilidad)

```mermaid
graph TD
    A[Alta Probabilidad / Alto Impacto] --> |Críticos| R1(Imágenes Docker inestables) & R3(Errores autenticación APIs) & R12(Puertos en uso) & R13(Analyzers lentos)
    B[Alta Probabilidad / Medio Impacto] --> R6(Retrasos curva aprendizaje)
    C[Media Probabilidad / Alto Impacto] --> R4(Falta recursos VM) & R7(Fallos integración) & R14(Postgres caído) & R15(Redis caído)
    D[Media Probabilidad / Medio Impacto] --> R2(Timeout analyzers) & R10(Problemas almacenamiento)
    E[Baja Probabilidad / Alto Impacto] --> R9(Fallos red interna)
    F[Baja Probabilidad / Medio Impacto] --> R5(Licencias Windows) & R11(Dependencia APIs externas)
