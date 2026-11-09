# 18 — Backlog Maestro E2E para alcanzar 9/10

> Backlog específico de la suite E2E (`tests/e2e/`): convierte la evaluación
> estática de 5,6/10 en una ruta de trabajo para llevar la suite a 9/10,
> priorizando falsos verdes, aislamiento, repetibilidad, contratos,
> recuperación, rendimiento y evidencia real. El objetivo no es aumentar el
> número de tests, sino conseguir que cada test pueda fallar por el motivo
> correcto, seleccione sus propios recursos y produzca evidencia
> reproducible. Complementa —no sustituye— el backlog general de `docs/17`.

## 1. Objetivo de calidad

### 1.1 Situación actual

- 49 ficheros E2E.
- Aproximadamente 26 000 líneas.
- Nota estática actual: 5,6/10.
- Nivel de evidencia actual: E2, análisis de código sin ejecución completa.
- Infraestructura compartida fuerte.
- Calidad muy desigual entre casos.
- Aproximadamente uno de cada cuatro tests podría dar verde sin demostrar su finalidad.
- Referencias internas de calidad:
  - TC-18, inyección real de fallos.
  - TC-26, control de concurrencia y reconciliación.
  - TC-31 containment, contrato HTTP preciso.

### 1.2 Objetivo final

Alcanzar al menos:

```text
Nota estática de diseño:       >= 9,0
Nota dinámica de ejecución:    >= 9,0
Evidencia:                     E4
Falsos verdes conocidos:       0
Soft-fails centrales:          0
Tests racy conocidos:          0
Tests críticos flaky:          0
Tests con cleanup probado:     100 %
Propósitos cubiertos:          100 %
E2E críticos ejecutados:       100 %
```

## 2. Modelo de puntuación para conceder el 9

Cada fichero o caso de prueba se evaluará en ocho dimensiones.

| Dimensión | Peso |
| --- | --- |
| Validez del oráculo | 25 % |
| Cobertura del propósito | 15 % |
| Selección y correlación de datos | 15 % |
| Independencia y aislamiento | 10 % |
| Repetibilidad y control temporal | 10 % |
| Gestión de errores | 10 % |
| Limpieza y restauración | 5 % |
| Evidencia y diagnóstico | 10 % |
| Total | 100 % |

### 2.1 Regla de puntuación

Cada dimensión se valora de 0 a 4:

| Nivel | Interpretación |
| --- | --- |
| 0 | Ausente |
| 1 | Declarativo o casi inútil |
| 2 | Parcial, permite falsos positivos |
| 3 | Correcto y automatizado |
| 4 | Verificado, reproducible y resistente a condiciones adversas |

Fórmula:

```text
nota = suma((nivel / 4) × peso) × 10
```

### 2.2 Puertas obligatorias

Aunque la media supere 9, la suite no recibirá esa nota si ocurre cualquiera de estos supuestos:

- Existe un assert central dentro de un `try/except` que lo transforma en warning.
- Un test puede seleccionar recursos de otro test.
- Una prueba crítica acepta `EXECUTING` como éxito.
- Una prueba de seguridad acepta tanto rechazo como aceptación sin comprobar efectos.
- Un test de degradación no inyecta realmente el fallo.
- Un test declara un SLA que no aplica en el assert.
- Una prueba deja servicios detenidos después de fallar.
- Una prueba que descarga malware real no está aislada y desactivada por defecto.
- La suite depende del orden de ejecución.
- Existen tests que se ejecutan dos veces porque una función de test llama a otra.

## 3. Prioridades

| Prioridad | Significado |
| --- | --- |
| P0 | Bloquea el 9 y puede producir falsos verdes |
| P1 | Necesaria para obtener evidencia E4 y repetibilidad |
| P2 | Mejora sustancial de cobertura y mantenibilidad |
| P3 | Excelencia, optimización o ampliación |

Tamaños:

| Tamaño | Esfuerzo orientativo |
| --- | --- |
| XS | Menos de 4 horas |
| S | 1 día |
| M | 2 a 4 días |
| L | 1 a 2 semanas |
| XL | Más de 2 semanas |

## 4. Épica E2E-ORACLE: eliminar falsos verdes

Prioridad global: P0
Impacto estimado: 5,6 → 6,8

Objetivo: garantizar que cada test falle cuando el comportamiento declarado no se cumple.

### E2E-ORACLE-001: inventariar todos los asserts vacuos

Prioridad: P0
Tamaño: M

Buscar:

- `count >= 0`.
- `len(value) >= 0`.
- `isinstance(case, dict)` como única comprobación.
- `status == 200 or status >= 400`.
- `status < 500` donde el contrato debería ser exacto.
- `value == source_value` cuando ambos proceden del mismo objeto local.
- Asserts dentro de un `if` que ya garantiza la condición.
- Asserts sobre payloads que no se han recuperado del sistema.
- Verificaciones que solo comprueban que no hubo excepción.
- `return True` después de capturar cualquier error.
- `assert disconnected` cuando el helper devuelve siempre `True`.

Criterios de aceptación:

- Existe un inventario machine-readable.
- Cada assert sospechoso tiene fichero, línea y categoría.
- Cada uno tiene decisión: corregir, eliminar o justificar.
- No queda ningún `count >= 0`.
- No se valida un payload usando únicamente la copia local.
- CI ejecuta una regla que detecta regresiones.

**Estado (2026-11-06): inventario HECHO + regla CI en marcha.**
Artefacto: `scripts/quality/e2e_oracle_audit.py` →
`reports/test-review/e2e_oracle_audit.{json,md}` (machine-readable,
fichero+línea+categoría+severidad por hallazgo). Inventario vivo:
**377 hallazgos** en 49 ficheros / 1529 asserts — `except_pass` 96,
`verify_false` 86, `swallowed_assert` 62, `hardcoded_url` 55,
`max_id_select` 24, `permissive_status` 16, `test_calls_test` 16,
`arbitrary_sleep` 12, resto <10. Regla CI: `tests/integration/test_e2e_lint.py`
(ratchet sobre baseline, ver §LINT-001). Pendiente: decisión por hallazgo
(corregir/eliminar/justificar) — trabajo de Fase 1/3.

### E2E-ORACLE-002: prohibir soft-fails en invariantes centrales

Prioridad: P0
Tamaño: L

Patrón prohibido:

```python
try:
    assert critical_condition
except AssertionError:
    logger.warning("Condition not met")
```

Patrón permitido:

```python
try:
    diagnostic = collect_optional_diagnostic()
except Exception as exc:
    diagnostic = {"collection_error": str(exc)}
assert critical_condition, format_failure(diagnostic)
```

Criterios de aceptación:

- Los asserts centrales propagan el fallo.
- Los fallos opcionales están etiquetados como diagnóstico.
- Cada test declara qué comprobaciones son obligatorias.
- Los artifacts distinguen `failed`, `warning`, `skipped` y `not_applicable`.
- Un warning nunca convierte una invariante incumplida en PASSED.
- Se corrigen TC-14 traceability, TC-16, TC-23, TC-31 compliance y TC-32 golden thread.

**Estado (2026-11-08, rev. 2): SUBSTANTIAL → 19 hallazgos.** Triaje
completo y **3 clases de defectos corregidas** esta iteración:

1. **Soft-fail real** — TC-02 `test_benign_alert_workflow` aprobaba con
   hasta `n/2` casos fallados (`pytest.fail` solo si `> len/2`); ahora
   cualquier caso fallado hace `pytest.fail`, simétrico a TC-01.
2. **`swallowed_assert` ×2** — TC-04 `test_concurrent_alerts` tenía
   `assert` dentro del `try` del worker thread (el `except Exception`
   los convertía en `ok=False`); reemplazados por `ValueError` tipado —
   el hilo padre sigue fallando vía `assert not failed_submissions` pero
   sin patrón assert-en-try. Score TC-04: 3.0 → 4.0.
3. **Hueco de oráculo de auth** — `_login_shuffle`/`_login_misp` tragaban
   el `wait_for_url` post-login, así un login realmente fallido NO
   marcaba `login_failed` y las páginas capturaban login-walls contando
   como capturadas (riesgo: cobertura inflada >90%). Ahora ambos prueban
   una **ruta protegida** (`/workflows`, `/users/index`) y lanzan
   `AssertionError` si el servidor rebota a login → `login_failed`
   marca el servicio → sus páginas cuentan como fallos. Verificado en
   vivo: `test_all_pages_captured` PASSED 586 s con 27 páginas.
4. **`hardcoded_url` ×9** — el `base` dict de TC-28 duplicaba `_PORTS`;
   ahora deriva de `_ui_url`/`_PORTS` (fuente única, respeta
   `E2E_UI_*_URL`).

Resto justificado con patrón permitido: collect-then-assert
(TC-01/TC-02/TC-18/TC-29 threads → `assert not failed` terminal),
esperas best-effort con oráculo de cobertura posterior (TC-28
`networkidle`/`ready-selector`/spinner-detach solo retrasan el
screenshot), fallback de parseo acotado (TC-KPI-01 TypeError/ValueError
→ ISO parse), cleanup best-effort (TC-KPI-03).
Baseline ratchet 30 → **19 fingerprints** (el gate `baseline_not_stale`
exigió regeneración — comportamiento correcto del ratchet);
`test_e2e_lint` 3/3 verde vía `make e2e-lint`.
Discriminador `failed|warning|skipped|not_applicable` **entregado**
(2026-11-08): `RunContextMixin` deriva `outcome` formal —
`pytest_runtest_makereport` propaga `failed`/`skipped` al artefacto,
`result.json`/TC-summary/assertions lo serializan conservando
`all_passed`+`status` legacy; precedencia verificada (failure > warning,
skipped > failures registrados, all-N/A → `not_applicable`, valores
inválidos rechazados). 16/16 tests `test_e2e_result_outcome` verdes.
Pendiente: validación end-to-end del campo en una corrida E2E real.

### E2E-ORACLE-003: crear assertions negativas reutilizables

Prioridad: P0
Tamaño: M

Helpers:

```text
assert_no_case_created(alert_id)
assert_no_containment_action(execution_id)
assert_no_duplicate_execution(idempotency_key)
assert_secret_not_persisted(secret)
assert_pii_not_present(value)
assert_node_not_executed(node_name)
assert_no_unexpected_side_effects(snapshot)
```

Criterios de aceptación:

- Los tests de rechazo comprueban ausencia de efectos.
- Los tests benignos comprueban ausencia de contención.
- Los tests de seguridad comprueban que el payload no llegó al dominio.
- Las consultas negativas están acotadas por identificador y ventana temporal.
- Existe al menos una prueba unitaria por helper.

**Estado (2026-11-06): HECHO.** `tests/e2e/base/negative_mixin.py` implementa
los 7 helpers + `assert_remains_absent` (ventana acotada de ausencia).
Regla de diseño aplicada: los fallos de consulta **propagan** (una ausencia
no verificable no es ausencia). Cobertura unitaria: 23 tests en
`tests/unit/test_negative_assertions_mixin.py` — todos verdes. Migración
inicial: TC-34 usa `assert_no_case_created`/`assert_remains_absent`/
`assert_no_unexpected_side_effects` (implícito), TC-02
(`no_blocking`/`no_isolation`) usa `assert_no_containment_action` a nivel
nodo Shuffle, el canary `secret_canary` ejerce `_loki_contains_value`.

### E2E-ORACLE-004: crear assertions semánticas por dominio

Prioridad: P1
Tamaño: L

Contratos necesarios:

- Contrato de alerta maliciosa.
- Contrato de falso positivo.
- Contrato de severidad crítica.
- Contrato de contención.
- Contrato de recuperación.
- Contrato de degradación.
- Contrato de trazabilidad.
- Contrato de custodia forense.
- Contrato de privacidad.
- Contrato de persistencia.
- Contrato de backpressure.
- Contrato de SLA.

Ejemplo:

```python
assert_malicious_decision(
    execution,
    minimum_score=80,
    required_actions={"containment"},
    forbidden_actions={"mark_false_positive"},
)
```

Criterios de aceptación:

- Los contratos verifican valores, no solo presencia.
- Los contratos distinguen ausencia de campo y valor vacío.
- Cada incumplimiento identifica la ruta exacta.
- Los contratos se reutilizan entre tests.
- No ocultan errores mediante valores predeterminados.

### E2E-ORACLE-005: mutation testing sobre los propios tests

Prioridad: P1
Tamaño: L

Mutaciones a introducir en fixtures o sistema controlado:

- Cambiar `score=90` por `score=10`.
- Eliminar `containment`.
- Duplicar un caso.
- Cambiar el `alert_id`.
- Eliminar `trace_id`.
- Alterar un hash.
- Persistir PII en claro.
- Cambiar `SUCCESS` por `FAILURE`.
- Marcar una acción como `skipped`.
- Superar el SLA.
- Omitir un observable.
- Introducir una tarea genérica no específica.

Criterios de aceptación:

- Cada mutación relevante provoca al menos un test rojo.
- Se genera una matriz mutación-test.
- El núcleo funcional mata al menos el 90 % de las mutaciones E2E seleccionadas.
- Seguridad y trazabilidad matan el 100 % de mutaciones críticas.
- Ningún test pasa cuando se elimina deliberadamente su efecto objetivo.

## 5. Épica E2E-CORRELATION: selección segura de recursos

Prioridad global: P0
Impacto estimado: 6,8 → 7,3

### E2E-CORR-001: eliminar `max(caseId)` como mecanismo de selección

Prioridad: P0
Tamaño: L

Ficheros afectados:

- TC-07.
- TC-09.
- TC-14 traceability.
- TC-16.
- TC-23.
- TC-24.
- TC-29.
- TC-31 compliance.
- TC-32 golden thread.
- TC-33.

Sustitución:

```python
case = wait_for_case_by_alert_id(
    alert_id=alert_id,
    created_after=test_start,
    timeout=CASE_TIMEOUT,
)
```

Criterios de aceptación:

- Ningún test usa `max(caseId)` para encontrar su caso.
- Cada caso se busca por `alert_id`, `trace_id` o `correlation_id`.
- La consulta se acota por tiempo.
- Si aparecen dos casos, la prueba falla.
- Si no aparece ninguno, la prueba falla con diagnóstico.
- La suite puede ejecutarse con al menos cuatro workers sin cruzar datos.

### E2E-CORR-002: estandarizar identificadores únicos

Prioridad: P0
Tamaño: M

Formato:

```text
<TC>-<run_id>-<worker_id>-<timestamp_ns>-<random_suffix>
```

Identificadores:

- `run_id`.
- `test_id`.
- `alert_id`.
- `trace_id`.
- `correlation_id`.
- `idempotency_key`.
- `resource_namespace`.

Criterios de aceptación:

- Todos los tests generan IDs únicos.
- No existen IDs fijos reutilizados.
- El prefijo corresponde al TC real.
- Se corrigen `TC31-*`, `TC33-*` y otros prefijos incorrectos.
- Los IDs aparecen en artifacts y logs.
- Los recursos se pueden localizar únicamente con el manifiesto del test.

### E2E-CORR-003: crear un `TestResourceManifest`

Prioridad: P1
Tamaño: M

Contenido:

```yaml
run_id: run-2026...
test_id: TC-18-02
alert_ids: []
execution_ids: []
case_ids: []
observable_ids: []
opensearch_documents: []
redis_keys: []
cortex_jobs: []
containers_modified: []
services_stopped: []
files_created: []
```

Criterios de aceptación:

- Cada recurso creado se registra.
- El manifiesto se actualiza durante la ejecución.
- El teardown usa el manifiesto.
- El artifact permanece si el test falla.
- Se puede auditar qué dejó un test.
- Ningún cleanup depende de buscar recursos globalmente.

### E2E-CORR-004: comprobar propagación de IDs en todos los sistemas

Prioridad: P1
Tamaño: L

Sistemas:

- API.
- Cola.
- Shuffle.
- TheHive.
- Cortex.
- MISP.
- Elasticsearch u OpenSearch.
- Loki.
- Redis.
- Tenzir.
- Network Watcher.

Criterios de aceptación:

- `trace_id` se verifica, no solo se registra.
- `alert_id` coincide en todas las fuentes aplicables.
- Se diferencia un sistema que no soporta el ID de uno que lo perdió.
- La ausencia en un sistema obligatorio hace fallar la prueba.
- TC-14 traceability y TC-32 golden thread dejan de usar placeholders.

## 6. Épica E2E-ISOLATION: limpieza e independencia

Prioridad global: P0
Impacto estimado: 7,3 → 7,8

### E2E-ISO-001: introducir namespaces por ejecución

Prioridad: P0
Tamaño: L

Aplicación:

- Prefijo Redis.
- Etiquetas en casos TheHive.
- Campos en documentos OpenSearch.
- Labels Loki.
- Directorios temporales.
- Nombres de artifacts.
- Datos de prueba de Cortex y MISP.

Criterios de aceptación:

- Cada ejecución tiene namespace.
- Los tests no consultan `ioc:*` globalmente.
- TC-12 busca exclusivamente las claves de su run.
- Las consultas históricas excluyen ejecuciones anteriores.
- Dos ejecuciones paralelas no se influyen.

**Estado (2026-11-06): MAYORÍA HECHO.** `IsolationMixin`
(`tests/e2e/base/isolation_mixin.py`) añade `run_id` (uuid-8 por
ejecución, inicializado en `create_run_context`) y `uid(prefix)` →
`{prefix}-{run_id}-{counter}`. Migración mecánica aplicada: **135**
ocurrencias de `f"…-{int(time.time())}"` → `self.uid(…)` en 33 ficheros;
los restantes `int(time.time())` son timestamps legítimos (`base_ts`,
octeto IP) o prefijos dinámicos ya resueltos. TC-12 ahora filtra
`ioc:{hash}` propio + valor con `run_id` (ya no `ioc:*` global).
Redis ya usaba prefijo `e2e:{correlation_id}:*`. Pendiente: labels Loki,
namespaces en MISP/Cortex fixtures, y verificación de paralelismo real
(`-n 2`).

### E2E-ISO-002: implementar cleanup transaccional

Prioridad: P0
Tamaño: XL

Recursos a limpiar:

- Casos TheHive.
- Observables.
- Tareas.
- Jobs Cortex.
- Objetos de prueba MISP.
- Documentos OpenSearch.
- Claves Redis.
- Artifacts temporales.
- Workflows huérfanos.
- Datos importados en Grafana.
- Contenedores o servicios modificados.

Criterios de aceptación:

- El cleanup se ejecuta en `finally`.
- El cleanup continúa aunque falle un recurso.
- Los fallos de cleanup se reportan.
- El test no se marca verde si deja recursos críticos.
- Existe un modo `--preserve-on-failure`.
- Existe un comando para limpiar runs abandonados.
- Un segundo run empieza sin depender del primero.

**Estado (2026-11-06): SUBSTANTIAL.** `CleanupMixin.cleanup_test_data`
corre en teardown, continúa ante fallos por paso (lista `errors`),
reporta a `cleanup.json`/`result.json`, `E2E_CLEANUP_ON_FAILURE` ≙
preserve-on-failure, `E2E_FAIL_ON_CLEANUP_ERROR=true` convierte residuo
crítico en fallo. `run_context.register_resource` + `manifest.resources`
rastrean casos/jobs/eventos/docs/claves por run.
`clean_shuffle_executions.py`/`clean_thehive_cases.py` cubren runs
abandonados de Shuffle/TheHive. Corregido `verify=False` residual en
`cleanup_elasticsearch` (usa `self.s`). Pendiente: cleanup de jobs
Cortex, dashboards Grafana y un comando unificado
`clean-run --correlation-id`.

### E2E-ISO-003: snapshots antes y después

Prioridad: P1
Tamaño: L

Snapshots:

- Casos.
- Cola.
- Ejecuciones.
- Documentos.
- Claves Redis.
- Jobs activos.
- Estado de contenedores.
- Dashboards.
- Objetos MISP.

Criterios de aceptación:

- Cada test destructivo captura estado previo.
- Se verifica la restauración del estado.
- Los tests de restart confirman que el servicio volvió a su configuración original.
- Se identifican recursos residuales.
- El diff se adjunta como artifact.

### E2E-ISO-004: garantizar independencia del orden

Prioridad: P0
Tamaño: M

Pruebas:

- Orden normal.
- Orden inverso.
- Orden aleatorio.
- Test aislado.
- Test repetido.
- Ejecución paralela.

Criterios de aceptación:

- La suite pasa con `pytest-randomly`.
- Cada test pasa aislado.
- Ningún test necesita que otro genere métricas.
- KPI-06 no depende de historia previa.
- TC-30 no depende de que 02 se ejecute antes que 03.
- Las dependencias inevitables se convierten en fixtures explícitos.

## 7. Épica E2E-EXECUTION: eliminar duplicaciones y mejorar la estructura pytest

### E2E-EXEC-001: eliminar el patrón "suite llama a test"

Prioridad: P0
Tamaño: M

Ficheros afectados:

- TC-04.
- TC-15.
- TC-16.
- TC-17.
- KPI-04.
- KPI-05.
- Cualquier otro que invoque métodos `test_*`.

Sustitución — extraer funciones auxiliares sin prefijo `test_`:

```python
def measure_service_latency(...):
    ...

def test_service_latency(...):
    result = measure_service_latency(...)
    assert_latency_contract(result)
```

Criterios de aceptación:

- Ninguna función `test_*` llama a otra función `test_*`.
- Pytest recoge cada escenario una sola vez.
- Se reduce el número de workflows duplicados.
- El tiempo se compara antes y después.
- Una regla AST impide reintroducir el patrón.

### E2E-EXEC-002: definir marcadores obligatorios

Prioridad: P1
Tamaño: M

Marcadores:

```text
e2e
critical
destructive
security
performance
resilience
integration
ui
external
malware
slow
requires_docker
requires_internet
```

Criterios de aceptación:

- Todos los tests tienen marcador.
- `--strict-markers` está activado.
- Los tests de malware no se ejecutan por defecto.
- Los destructivos requieren entorno autorizado.
- CI puede seleccionar suites por finalidad.
- El reporte muestra resultados por marcador.

### E2E-EXEC-003: separar pruebas E2E de linters de configuración

Prioridad: P1
Tamaño: S

Aplicación — mover TC-27 o dividirlo:

- Validación estática a `tests/configuration/`.
- Smoke test de configuración real en `tests/e2e/`.

Criterios de aceptación:

- Las regex YAML se sustituyen por parseo real.
- El test E2E arranca y consulta el servicio configurado.
- Los checks estáticos no inflan el número de E2E.
- Se elimina `.replace("es", "es")`.
- No quedan asserts como `es_count >= 0`.

## 8. Épica E2E-TIME: polling, tiempos y flakiness

### E2E-TIME-001: eliminar sleeps fijos

Prioridad: P0
Tamaño: XL

Casos afectados:

- `sleep(0.2)`.
- `sleep(2)`.
- `sleep(3)`.
- `sleep(10)`.
- `sleep(30)`.
- `sleep(60)`.
- `sleep(120)`.

Sustitución:

```python
wait_until(
    condition=service_is_ready,
    timeout=120,
    interval=2,
    backoff=1.2,
)
```

Criterios de aceptación:

- Los sleeps funcionales se sustituyen por polling.
- Los sleeps que representan comportamiento temporal están justificados.
- Cada polling tiene timeout.
- El diagnóstico muestra el último estado.
- El test termina antes cuando la condición se cumple.
- La suite no depende de tiempos mágicos.

**Estado (2026-11-06): PARCIAL.** `wait_until` en `IsolationMixin`
(condición, deadline, backoff, `timeout_kind` centralizado, `Last state`
en el mensaje). Eliminados todos los `sleep(30/60)` oraculares en
ORACLE-002 (TC-30, TC-05, TC-18, TC-21, TC-22, TC-26). Los ~50
`sleep(N)` restantes son intervalos de poll acotados — la auditoría del
escáner los considera legítimos (no flaggea). Pendiente: migrar los
bucles `while …: sleep(N)` manuales a `wait_until` donde aporta
diagnóstico (TC-04, TC-13, TC-19), y `timeout_kind` en los call-sites.

### E2E-TIME-002: establecer timeouts por clase de operación

Prioridad: P1
Tamaño: M

| Operación | Timeout inicial |
| --- | --- |
| API local | 5 s |
| Healthcheck | 60 s |
| Creación de caso | 120 s |
| Workflow normal | 300 s |
| Cortex analyzer | 120 s |
| MISP query | 60 s |
| Restart MISP | 600 s |
| Test de rendimiento | definido por presupuesto |
| Cleanup | 120 s |

Criterios de aceptación:

- Los timeouts están centralizados.
- No hay `900` dispersos por la suite.
- Cada timeout tiene justificación.
- El mensaje distingue timeout de fallo funcional.
- Se puede sobrescribir mediante configuración.

**Estado (2026-11-06): HECHO (infra).** `tests/e2e/base/timeouts.py`
centraliza la tabla + `timeout_for(kind)` con override por
`E2E_TIMEOUT_<KIND>`; `self.timeout(kind)` la expone en la base y
`wait_until(timeout_kind=…)` la consume. Kinds desconocidos →
`KeyError` (inventar timeouts on-the-fly es justo la deriva que se
elimina). Pendiente: adoptar `timeout_kind` en los call-sites que hoy
usan literales (`timeout=600`, `@pytest.mark.timeout(900)`).

### E2E-TIME-003: medir flakiness

Prioridad: P1
Tamaño: L

Método:

- Ejecutar cada test crítico 20 veces.
- Ejecutar cada test no crítico 5 veces.
- Ejecutar en orden aleatorio.
- Ejecutar con carga de fondo controlada.
- Registrar causa de cada fallo.

Criterios de aceptación:

- Flakiness crítica: 0 %.
- Flakiness global: inferior al 1 %.
- No se usa `rerun` para ocultar defectos.
- Cada cuarentena tiene ticket y fecha de caducidad.
- Se publica un historial por test.

## 9. Épica E2E-HTTP: contratos coherentes

### E2E-HTTP-001: crear una matriz contractual del webhook

Prioridad: P0
Tamaño: M

| Entrada | Respuesta esperada | Efecto esperado |
| --- | --- | --- |
| Válida | 200 o 202, según contrato | ejecución creada |
| JSON malformado | 400 | ningún efecto |
| Esquema inválido | 422 | ningún efecto |
| Sin autenticación | 401 | ningún efecto |
| Sin permisos | 403 | ningún efecto |
| Replay | 200/409 según diseño | sin duplicado |
| Rate limit | 429 | sin nueva ejecución |
| Payload excesivo | 413 | ningún efecto |
| Saturación | 429 o 503 | comportamiento trazable |

Criterios de aceptación:

- Cada test usa la misma matriz.
- Se eliminan combinaciones como `status < 500`.
- Aceptar varios códigos requiere justificación contractual.
- Cada código verifica efectos.
- OpenAPI coincide con la matriz.

**Estado (2026-11-06): HECHO con desviaciones documentadas.** Matriz
canónica en `tests/e2e/base/webhook_contract.py` (`WEBHOOK_CONTRACT`,
9 filas); suite TC-34 (10 tests parametrizados, `test-e2e-tc34*`) la
ejecuta entera en vivo — **10/10 verde (172 s)**. Desviaciones reales
del documento aspiracional, ya verificadas: `malformed_json`→**422**
(FastAPI, no 400); `oversized`→**422** (`AdmissionValidationError`, no
413); `bad_token`→**401** (no hay tier 403); `replay`→**202** con el
mismo `admission_id` (dedup por idempotency_key). La matriz cazó
**BUG-071**: el handler global de `HTTPException` descartaba
`exc.headers` → 401 sin `WWW-Authenticate` (RFC 7235) en dos paths.
`test_rate_limited` lee el budget real del header `X-RateLimit-Limit`
(300/min en despliegue) y verifica 429 + `Retry-After`.

### E2E-HTTP-002: helpers de respuesta estricta

Prioridad: P1
Tamaño: M

```python
assert_problem_details(response, status=422, field="hash")
assert_accepted(response)
assert_rejected_without_side_effects(response, alert_id)
assert_rate_limited(response)
assert_replay_deduplicated(first, second)
```

Criterios de aceptación:

- Se verifica `Content-Type`.
- Se verifica el esquema.
- Se verifica `Retry-After` para 429.
- Se verifica `correlation_id`.
- Los errores no exponen stack traces.
- Se comprueban efectos posteriores.

**Estado (2026-11-06): PARCIAL dentro de TC-34.** Ya verificado en vivo:
`Content-Type: application/json` en 202, `admission_id`/`status_url` en el
body, `WWW-Authenticate` en 401, `Retry-After` + `X-RateLimit-*` en 429,
`x-request-id` presente en respuestas, efectos posteriores por fila.
Pendiente: helpers nombrados (`assert_problem_details`,
`assert_rejected_without_side_effects`) como API reutilizable, esquema de
error formal (problem-details/RFC 7807) y verificación explícita de
ausencia de stack traces en bodies de error.

## 10. Épica E2E-EVIDENCE: artifacts forenses E4

### E2E-EVID-001: generar un paquete por test

Prioridad: P1
Tamaño: L

Estructura:

```text
e2e-results/
  <run_id>/
    manifest.json
    environment.json
    junit.xml
    summary.json
    TC-18-01/
      request.json
      response.json
      execution.json
      case.json
      opensearch.json
      logs.jsonl
      trace.json
      cleanup.json
      verdict.json
```

Criterios de aceptación:

- Cada test tiene carpeta propia.
- Los secretos están redactados.
- Los archivos llevan timestamps.
- Se calcula SHA-256 de cada artifact.
- El resumen enlaza las evidencias.
- La evidencia se conserva aunque falle el test.
- Se registra el commit.

### E2E-EVID-002: registrar el entorno completo

Prioridad: P1
Tamaño: M

Datos:

- Commit.
- Rama.
- Estado de Git.
- Python.
- Pytest.
- Plugins.
- Host.
- CPU.
- RAM.
- Docker.
- Compose.
- Imágenes y digests.
- Configuración efectiva redactada.
- Hora de inicio.
- Zona horaria.
- Semilla aleatoria.
- Número de workers.

Criterios de aceptación:

- El entorno se registra antes de ejecutar.
- Se detecta un repositorio sucio.
- Se guardan digests, no solo tags.
- La reproducción usa el mismo manifiesto.
- Los resultados no mezclan commits.

### E2E-EVID-003: puntuación automática de calidad

Prioridad: P2
Tamaño: L

Criterios de aceptación:

- Se calcula nota por test.
- Se muestran gates incumplidos.
- Se diferencia evidencia E2, E3 y E4.
- La nota no usa tests omitidos como aprobados.
- Se publica la evolución histórica.
- La nota final incluye intervalo de confianza operativo.

## 11. Correcciones específicas por caso de prueba

### 11.1 Núcleo funcional

**TC00-001: corregir consistencia entre workflows** — Prioridad: P1

- Asentar que la intersección de campos no está vacía.
- Comparar valores semánticos, no solo nombres de campos.
- Sustituir la heurística de varianza por tolerancia declarada.
- Verificar ausencia de duplicados en cada sistema.
- Mantener el paralelismo de tres ejecuciones.
- Puntaje objetivo: 9,0.

**TC01-001: activar o eliminar los `_step_verify_*` muertos** — Prioridad: P0

- Todos los pasos definidos se ejecutan o se eliminan.
- Las verificaciones de observables se realizan contra datos recuperados.
- El mismatch estricto deja de ser warning.
- Se añade cleanup de casos y jobs.
- Se conserva el contrato `score >= 80`.
- Puntaje objetivo: 9,3.

**TC02-001: endurecer el path benigno** — Prioridad: P0

- Eliminar tolerancia de hasta 50 % de fallos.
- Validar cada ejecución, no solo la última.
- Corregir el mapeo `file`.
- Hacer fallar la comprobación MISP cuando sea obligatoria.
- Verificar que no hay acciones de contención.
- Puntaje objetivo: 9,2.

**TC03-001: convertir payloads límite en pruebas con oráculo real** — Prioridad: P0

- Definir el resultado esperado para cada uno de los nueve payloads.
- Eliminar `except: pass`.
- Verificar que los rechazados no crean ejecuciones.
- Verificar recuperación tras el barrage.
- Limpiar ejecuciones stale.
- Puntaje objetivo: 9,0.

**TC04-001: rehacer rendimiento como prueba contractual** — Prioridad: P0

- Sustituir 900 s por presupuestos reales.
- Aplicar el SLA declarado en los asserts.
- Usar al menos 30 muestras para percentiles.
- Evitar `p95=p99=max` por tamaño insuficiente.
- Fallar si `docker stats` no está disponible cuando es requisito.
- Usar exactamente el mismo payload para cache hit.
- Eliminar suite-llama-test.
- Guardar dataset bruto.
- Puntaje objetivo: 9,0.

**TC05-001: consolidar envío concurrente** — Prioridad: P1

- Unificar tres `_send_with_retry`.
- Cancelar esperas imposibles si un envío falla definitivamente.
- No contar `EXECUTING` como éxito.
- Separar admisión aceptada y ejecución completada.
- Mantener unicidad 1:1.
- Puntaje objetivo: 9,2.

**TC06-001: endurecer severidad crítica** — Prioridad: P1

- Parsear JSON en vez de buscar `"skipped": true`.
- Eliminar asserts compuestos tautológicos.
- Usar un hash hexadecimal válido.
- Aplicar SLA de 15 segundos o cambiar el requisito.
- Verificar tareas específicas por ID o tipo.
- Puntaje objetivo: 9,0.

**TC07-001: especificar contratos para campos ausentes** — Prioridad: P0

- Definir qué campos son obligatorios.
- Definir cuándo corresponde 422.
- Definir qué defaults puede derivar el sistema.
- No retornar sin verificar efectos.
- Seleccionar caso por `alert_id`.
- Puntaje objetivo: 9,0.

**TC08-001: completar round-trip de campos adicionales** — Prioridad: P1

- Recuperar el campo desconocido o verificar explícitamente su descarte.
- Exigir persistencia de metadata cuando el contrato lo establezca.
- Hacer fallar un override no permitido.
- Verificar protección de campos internos.
- Puntaje objetivo: 9,1.

**TC09-001: reparar escenario ransomware multi-etapa** — Prioridad: P0

- Sustituir `"g"*64` por SHA-256 válido.
- Validar status de cada workflow.
- Implementar helpers actualmente no-op.
- Convertir warnings centrales en errores.
- Comprobar correlación entre las tres etapas.
- Verificar progresión de severidad.
- Puntaje objetivo: 9,0.

### 11.2 Integraciones

**TC10-001: validar integración Tenzir con un contrato soportado**

- Usar una API o CLI real documentada para la versión desplegada.
- No aceptar HTTP 500 como manejo correcto.
- Inyectar el evento que después se consulta.
- Eliminar `returncode==0 or no error`.
- Verificar datos exportados, no solo existencia de la acción.
- Objetivo: 9,0.

**TC11-001: comprobar captura Network Watcher durante el workflow**

- Muestrear mientras el workflow está activo.
- Inyectar tráfico conocido.
- Verificar origen, destino, protocolo y ventana temporal.
- Evitar que lista vacía convierta el filtro en verdad vacua.
- Objetivo: 9,0.

**TC12-001: aislar Redis**

- Usar namespace por run.
- Sustituir `KEYS` por `SCAN`.
- Verificar la clave exacta derivada del IoC enviado.
- Integrar el workflow validator.
- Limpiar claves.
- Objetivo: 9,2.

**TC13-001: validar Loki con labels reales**

- Detectar labels disponibles antes de construir queries.
- Inyectar un log con correlation ID.
- Consultar ese ID.
- Fallar si el dato no aparece.
- Sustituir `sleep(10)` por polling.
- Objetivo: 9,0.

**TC14-INT-001: exigir resultado por integración**

- Eliminar el umbral agregado de 3/4.
- Reportar resultado individual.
- Fallar si una integración obligatoria no funciona.
- Usar `verify_redis_cache()` realmente.
- Establecer contrato exacto para alertas malformadas.
- Objetivo: 9,0.

**TC14-TRACE-001: reconstruir trazabilidad**

- Hacer obligatorio el `trace_id`.
- Implementar Cortex y MISP, no placeholders.
- Eliminar try/except que transforma errores en warnings.
- Seleccionar casos por alerta.
- Verificar igualdad cross-system.
- Objetivo: 9,3.

**TC15-001: estabilizar latencias externas**

- Eliminar suite-llama-test.
- Usar fixture compartida por clase cuando sea válido.
- Tomar al menos 30 muestras.
- Separar warm-up.
- Registrar P50, P90, P95 y P99.
- Limpiar observables.
- Objetivo: 9,0.

**TC16-ERR-001: corregir el error de tipos**

- No iterar strings como diccionarios.
- Añadir tipado sobre nodos de error.
- Inyectar fallos reales.
- No aceptar `FAILURE` como éxito genérico.
- Dejar de capturar el validator.
- Objetivo: 9,1.

**TC16-RATE-001: aislar la ventana de errores**

- Filtrar por `run_id`.
- No usar 24 horas de historia.
- Inyectar errores contra componentes del sistema.
- Eliminar SSL contra un puerto ajeno.
- Verificar numerador y denominador.
- Objetivo: 9,0.

**TC17-001: monitorización en tiempo real real**

- Muestrear durante la ejecución.
- Eliminar `count >= 0`.
- Parametrizar nombres de contenedor.
- Verificar puerto y protocolo esperados.
- Mantener restart real y restauración.
- Objetivo: 9,0.

### 11.3 Resiliencia, seguridad y escenarios

**TC18-001: cerrar huecos del mejor test de resiliencia**

- Incluir Orborus en teardown de seguridad.
- Recuperar o terminar ejecuciones huérfanas.
- Sustituir `sleep(30)` por polling.
- Verificar ausencia de acciones duplicadas tras restaurar.
- Objetivo: 9,5.

**TC19-001: rediseñar seguridad por propiedades**

- Cada ataque tendrá resultado esperado.
- JWT expirado debe devolver 401.
- API key revocada debe devolver 401 o 403.
- Rate limit debe producir 429.
- SQLi/XSS aceptados por el esquema deben persistirse de forma segura o rechazarse según contrato.
- Replay no debe duplicar ejecución.
- Oversized debe devolver 413.
- Usar IDs únicos.
- Verificar efectos negativos.
- Objetivo: 9,3.

**TC20-001: corregir Zero Trust**

- Usar `_expected_port` o eliminarlo.
- Diferenciar bloqueo de red, timeout y error DNS.
- No interpretar cualquier excepción como control exitoso.
- No aceptar 404 como prueba de privilegio mínimo.
- Ejecutar pruebas desde la red correcta.
- Objetivo: 9,1.

**TC21-001: cadena de custodia real**

- Recuperar eventos de custodia del sistema.
- Eliminar estructuras construidas localmente.
- Intentar mutaciones reales donde sea seguro.
- Comparar timestamps parseados.
- Eliminar duplicación con TC-22 y TC-26.
- Objetivo: 9,2.

**TC22-001: persistencia, backup y restore reales**

- Los tests de reinicio deben reiniciar realmente.
- El backup debe provenir del mecanismo productivo.
- Restaurar en almacenamiento limpio.
- Comparar hashes y conteos.
- Evitar que `docker compose down` destruya al runner.
- Usar un controlador externo o entorno anidado autorizado.
- Sustituir sleeps por health polling.
- Objetivo: 9,3.

**TC23-001: endurecer privacidad**

- PII en claro debe fallar.
- Ampliar patrones de secretos a JSON, cabeceras y URLs.
- Definir transformación esperada.
- Distinguir redacción, hashing y eliminación.
- Eliminar skips silenciosos.
- Verificar logs, documentos y casos.
- Objetivo: 9,2.

**TC24-001: respuestas específicas por malware**

- Sustituir palabras genéricas por códigos o tipos de tarea.
- Definir acciones esperadas por ransomware, RAT, worm y cryptominer.
- Filtrar todos los casos por `alert_id`.
- Añadir polling.
- Añadir assertions negativas contra acciones de otro tipo.
- Objetivo: 9,0.

**TC25-001: detección conductual comprobable**

- No verificar inputs locales.
- Definir el evento o correlación que constituye detección.
- Simular low-and-slow con timestamps controlados.
- Verificar ventana temporal.
- Verificar canary mediante evento observable.
- Ajustar timeout para diez workflows o paralelizar de forma segura.
- Objetivo: 9,0.

**TC26-001: reforzar carga extrema**

- No acceder a miembros privados.
- Esperar las ejecuciones del límite de concurrencia.
- La deduplicación debe exigir exactamente un caso.
- Enviar backpressure realmente en paralelo.
- Verificar `Retry-After`.
- Comprobar recuperación de cola.
- Objetivo: 9,5.

**TC27-001: convertir configuración en smoke test real**

- Aplicar cambios permitidos en un entorno temporal.
- Arrancar el servicio.
- Consultar configuración efectiva.
- Detectar drift.
- Retirar regex frágiles.
- Objetivo E2E: 8,8.

**TC28-001: UI E2E con navegador**

Herramienta recomendada: Playwright.

- Abrir las UIs en navegador real.
- Verificar login.
- Navegar a una pantalla significativa.
- Verificar ausencia de errores de consola críticos.
- Ejecutar accesibilidad con axe-core.
- No aceptar 404.
- Limpiar casos creados.
- Capturar screenshot y trace.
- Objetivo: 9,0.

**TC29-COMP-001: integridad MITRE**

- Corregir prefijos.
- La ausencia de técnicas almacenadas debe fallar.
- Seleccionar casos por alerta.
- Sustituir keywords genéricas por mappings definidos.
- Verificar ATT&CK técnica por técnica.
- Objetivo: 9,0.

**TC29-EVID-001: evidencia grande real**

- Renombrar el caso si solo prueba hashes.
- O añadir subida real de ficheros sintéticos.
- Distinguir 413 de fallo de red.
- Monitorizar el workflow provocado por 900 KB.
- Limpiar caso y observables.
- Verificar checksum después de recuperación.
- Objetivo: 9,0.

**TC30-001: modo offline fiable**

- `_disconnect` y `_reconnect` deben fallar si Docker falla.
- Verificar estado real de contenedor.
- Polling de MISP hasta readiness.
- Eliminar dependencia de orden.
- No tratar `FAILED` como `skipped`.
- Verificar recuperación de funcionalidad.
- Objetivo: 9,2.

**TC31-COMP-001: reparar compliance**

- Inicializar cliente Loki.
- Eliminar fallback global por caso máximo.
- Implementar verificación D3FEND real.
- Acotar logs por correlation ID.
- Evitar patrones genéricos.
- Objetivo: 9,1.

**TC31-CONTAIN-001: ampliar contrato containment**

- Validar timestamp con parser.
- Corregir prefijos.
- Probar modo no simulado en entorno seguro.
- Probar JSON malformado.
- Probar autenticación y autorización.
- Probar idempotencia.
- Mantener ausencia de efectos en simulation.
- Objetivo: 9,5.

**TC32-GOLDEN-001: convertir golden thread en gate**

- Eliminar captura de `AssertionError`.
- Sustituir `assert_no_data_loss` tautológico.
- Correlacionar cada sistema.
- Verificar contenido, no solo existencia.
- Fallar si una fuente obligatoria pierde datos.
- Objetivo: 9,5.

**TC32-IOTIME-001: robustecer análisis por IoC**

- Descubrir nodos por contrato, no por labels rígidos.
- Eliminar fallback `total/2`.
- Rechazar duraciones no válidas.
- Ejecutar varias muestras.
- Separar cola, ejecución y persistencia.
- Objetivo: 9,0.

**TC33-001: aislar IoCs reales**

- No descargar 844 MiB por defecto.
- El test requiere marcador `malware`, permiso explícito y sandbox.
- Activar TLS verification.
- Fijar hash esperado.
- Usar una muestra segura o fixture sintético por defecto.
- Implementar `list_case_observables`.
- Seleccionar caso por alerta.
- Verificar cada tipo de IoC.
- Limpiar todos los recursos.
- Objetivo: 9,0.

## 12. Backlog específico de KPI

**KPI01-001: corregir MTTR**

- Definir inicio y fin del MTTR.
- No incluir esperas del propio test.
- Polling del documento.
- Comparar con timestamps del sistema.
- Reducir tolerancia de 60 s.
- Objetivo: 9,0.

**KPI02-DASH-001: dashboard determinista**

- No sobrescribir dashboards compartidos.
- Usar namespace o carpeta temporal.
- Fallar si el dashboard no existe.
- Verificar paneles y consultas.
- Verificar autenticación real.
- Limpiar dashboard temporal.
- Objetivo: 9,0.

**KPI02-PERC-001: percentiles estadísticamente útiles**

- Usar al menos 30 muestras.
- No mezclar runs si faltan muestras.
- Mantener población homogénea.
- El cross-check con analytics debe ser obligatorio.
- Publicar método de percentil usado.
- Objetivo: 9,2.

**KPI03-001: inyectar violaciones de KPI**

- Crear escenario saludable.
- Crear escenario de warning.
- Crear escenario crítico.
- Verificar alerta, severidad y mensaje.
- Verificar recuperación.
- Objetivo: 9,0.

**KPI04-PERC-001: alinear SLA y asserts**

- Elegir 120/180 o 300/1800.
- Un resultado `p50_ok=False` debe fallar.
- Permitir percentiles empatados con `<=`.
- Eliminar suite-llama-test.
- Objetivo: 9,0.

**KPI04-SVC-001: medir éxito por servicio correctamente**

- Generar tráfico propio.
- Filtrar por run.
- Definir tratamiento de cero llamadas.
- Llamar al guardado del reporte.
- Corregir cabeceras KPI.
- Objetivo: 9,0.

**KPI05-NODE-001: parametrizar timings**

- Eliminar URL hardcodeada.
- Alinear comentario y umbral.
- Exigir duración positiva para nodos ejecutados.
- Descubrir nodos críticos mediante contrato.
- Objetivo: 9,1.

**KPI05-SVC-001: controlar denominadores pequeños**

- Definir muestra mínima.
- No asumir `success=True` si falta el campo.
- Filtrar por run.
- Eliminar suite-llama-test.
- Reportar intervalo o número de observaciones.
- Objetivo: 9,0.

**KPI06-COH-001: coherencia de datos real**

- Compartir fixture por clase donde corresponda.
- Sustituir comparación OR-substring por normalización.
- Comparar timestamps.
- Verificar continuidad temporal.
- Diferenciar campos equivalentes con vocabularios distintos.
- Objetivo: 9,2.

**KPI06-HEALTH-001: funcionar en entorno limpio**

- Generar historia controlada.
- Parametrizar índices y URLs.
- Normalizar timestamps.
- Mantener job real de Cortex.
- Separar salud actual e histórico de éxito.
- Objetivo: 9,2.

## 13. Automatizaciones de control de calidad de los tests

### E2E-LINT-001: linter AST específico

Prioridad: P1
Tamaño: L

Debe detectar:

- `except AssertionError`.
- `except Exception: pass`.
- Funciones `test_*` que llaman a `test_*`.
- `count >= 0`.
- `sleep()` no autorizado.
- `max(caseId)`.
- IDs fijos.
- `verify=False`.
- `return True` dentro de un `except`.
- URLs hardcodeadas.
- Índices hardcodeados.
- `EXECUTING` dentro de estados de éxito.
- Asserts sobre variables locales sin lectura del sistema.
- `pytest.skip` dentro de rutas críticas.

Criterios de aceptación:

- Se ejecuta en CI.
- Tiene una línea base temporal.
- El código nuevo no puede incrementar infracciones.
- P0 termina con cero infracciones críticas.

**Estado (2026-11-06): EN CURSO, implementado como ratchet.**
`scripts/quality/e2e_oracle_audit.py` detecta 13 categorías
(vacuous_bound, permissive_status, tautology, swallowed_assert,
isinstance_only, none_and_type_only, executing_success, arbitrary_sleep,
test_calls_test, max_id_select, except_pass, return_true_except, fixed_id,
verify_false, hardcoded_url). Baseline: `tests/e2e/oracle_baseline.json`
(**19 fingerprints** tras la limpieza 2026-11-08; regenerar con
`--baseline … --write-baseline`; ejecución canónica `make e2e-lint`).
Guardián: `tests/integration/test_e2e_lint.py` 3/3 — falla ante hallazgos
nuevos, exige regenerar baseline si >25 % stale (demostrado en vivo: la
limpieza de 11 findings disparó el gate hasta regenerar), verificado por
mutación (sonda con 4 anti-patrones → 4 hallazgos nuevos detectados).
Cobertura actual de la lista: falta aún "índices hardcodeados",
"asserts sobre variables locales sin lectura" y "pytest.skip en ruta
crítica". Inventario vivo: 19 hallazgos en 8 ficheros, todos
`except_pass` justificados (TC-28 peor score 1,0/4 — best-effort waits
legítimos tras la mejora del oráculo de auth).

### E2E-LINT-002: validar nombres y trazabilidad

- El nombre del fichero coincide con TC.
- Los IDs generados usan el mismo TC.
- El encabezado del reporte coincide.
- El marcador corresponde a la categoría.
- No existen duplicidades ambiguas como dos TC-14 sin sufijo oficial.
- El catálogo oficial identifica cada fichero de forma única.

## 14. Reorganización propuesta de la suite

```text
tests/e2e/
  contracts/
    alert_contracts.py
    execution_contracts.py
    http_contracts.py
    integration_contracts.py
  fixtures/
    alerts/
    observables/
    stix/
    large_payloads/
  infrastructure/
    base.py
    polling.py
    resources.py
    evidence.py
    cleanup.py
    correlation.py
    fault_injection.py
  functional/
    test_tc00_workflows.py
    ...
  integrations/
    test_tc10_tenzir.py
    ...
  resilience/
    test_tc18_fault_injection.py
    test_tc30_offline.py
  security/
    test_tc19_webhook_security.py
    test_tc20_zero_trust.py
    test_tc23_privacy.py
  performance/
    test_tc04_performance.py
    test_tc26_extreme_load.py
  ui/
    test_tc28_ui.py
  kpi/
    test_kpi01_mttr.py
    ...
  static/
  configuration/
```

## 15. Pipeline CI propuesto

### 15.1 Pipeline de pull request

Objetivo: menos de 20 minutos.

- Lint AST de tests.
- Validación de catálogo.
- Unit tests de infraestructura E2E.
- Contract tests.
- Smoke E2E:
  - TC-01.
  - TC-02.
  - TC-06.
  - TC-31 containment.
- Verificación de cleanup.
- Publicación de artifacts.

### 15.2 Pipeline nocturno

- Suite funcional completa.
- Integraciones.
- Seguridad.
- Resiliencia.
- UI con Playwright.
- KPIs.
- Orden aleatorio.
- Dos repeticiones de tests críticos.
- Informe de flakiness.
- Comprobación de residuos.

### 15.3 Pipeline semanal

- Rendimiento.
- Carga extrema.
- Backup y restauración.
- Restarts.
- Fault injection.
- Mutation testing E2E.
- Veinte repeticiones de tests críticos.
- Evaluación ISO automática.
- Actualización de nota.

### 15.4 Pipeline manual restringido

- Descarga o uso de malware real.
- Acciones de contención no simuladas.
- Pruebas destructivas.
- `docker compose down`.
- Pruebas que requieren Internet.
- Escenarios que interactúan con infraestructura no efímera.

## 16. Fases de ejecución

### Fase 1: eliminar falsos verdes

Duración estimada: 2 a 3 semanas.

Incluye:

- ORACLE-001 a ORACLE-004.
- CORR-001 y CORR-002.
- EXEC-001.
- HTTP-001.
- Corrección de bugs agudos.

Salida esperada:

- Nota estática aproximada: 7,0.
- Cero asserts centrales tragados.
- Cero `max(caseId)`.
- Cero llamadas test-a-test.
- Todos los bugs agudos corregidos.

### Fase 2: aislamiento y cleanup

Duración: 2 a 4 semanas.

Incluye:

- `TestResourceManifest`.
- Namespaces.
- Cleanup transaccional.
- Snapshots.
- Orden aleatorio.
- Polling.
- Timeouts centralizados.

Salida esperada:

- Nota: 7,8 a 8,1.
- Ejecución repetible.
- Suite paralelizable.
- Sin dependencia de datos stale.
- Cero recursos críticos residuales.

### Fase 3: reforzar tests de 4 a 6 puntos

Duración: 3 a 5 semanas.

Prioridad:

- TC-14 traceability.
- TC-16 error handling.
- TC-19 security.
- KPI-02 dashboard.
- KPI-03 alerts.
- TC-24 malware specific.
- TC-31 compliance.
- TC-32 golden thread.
- TC-04 performance.
- TC-10 Tenzir.
- TC-13 Loki.
- TC-22 persistence.
- TC-28 UI.

**Estado (2026-11-06), tras ORACLE-002 en §7:**

- TC-23 privacidad: oráculo PII por valor (ES+Loki+TheHive) + `notify.log`
  estricto — **verde en vivo 99 s**.
- TC-19 seguridad: `status_code > 0` eliminado; marcadores `uid()`;
  `test_replay_attack(_prevention)` verifican ≤1 doc en `soar-alerts`
  (dedup por `alert_id` confirmada E4, 47 s); `expired_jwt`/`revoked_api_key`
  re-encauzados a `POST /api/v1/alerts` (el webhook Shuffle ignora
  `Authorization`) → 401 + `WWW-Authenticate` + ausencia acotada de
  efectos; `unexpected_xml`/`excessive_payload` con oráculo de efecto;
  `rate_limiting` documenta que el limiter vive en la API (TC-34).
  Hallazgo corregido en `negative_mixin`: `match` fuzzy tokenizaba los
  marcadores y colaba docs ajenos → query amplia + filtro exacto en
  `_source` (falso positivo del oráculo, no bug de producto).
- KPI-03: oráculo de violación real — inyecta `mttr_seconds=1e9` y
  `health_score=1` en `soar-metrics` → el manager debe devolver
  `status="alert"` en ambos checks y `overall_status="alert"`
  (**verde en vivo 8,8 s**, sondas eliminadas vía `register_resource`).
- TC-24: assert redundante por contador eliminado (el marcador es el
  oráculo); TC-31: alert_ids a `uid()`.
- TC-28: smoke HTTP de UIs verificado; la pata browser real
  (Playwright) sigue pendiente — no hay dependencia en el repo.
- KPI-02/KPI-04: `float()` sin guardia (violación de esquema = fail) y
  filtro out-of-range eliminado (sesgo de supervivencia en percentiles).

**Ejecución E4 real (2026-11-06, stack desplegado):**

- **TC-02 benign**: `assert_no_containment_action` refinado — el nodo
  `containment` marca `SUCCESS` en bookkeeping de Shuffle pero su resultado
  es `{"skipped": true, "decision=observe"}`; un skip auto-reportado ya no
  cuenta como efecto. `test_no_isolation` **verde en vivo 459 s**.
- **TC-31**: 11/11 en orden aleatorio (`pytest-randomly`, seed
  3617741622) — **verde en vivo 1360 s**.
- **KPI-01**: oráculo reescrito — `mttr_seconds` se acota contra la
  ejecución OpenSearch (`started−detection ≤ mttr ≤ completed−detection`),
  no contra el wall-clock del test (incluía cola+polling+evidencias).
  MTTR medido **71,5 s < 300 s** — **verde en vivo 165 s**. Primer run
  bajo contención midió 325,8 s (evidencia de sensibilidad a carga).
- **KPI-04**: **verde en vivo 54 s** (primer intento falló con 500
  transitorio de `/analytics/kpis/aggregated` bajo 4 runs concurrentes —
  techo de capacidad OpenSearch ya documentado, no defecto del test).
- **KPI-05**: `/analytics/node-timings` **verde en vivo 153 s**.
- **KPI-06**: 4/5 — `test_cortex_analyzer_images_available` verde tras
  corregir la precedencia de auth (org API key sobre superadmin Basic;
  Cortex devuelve 403 en `/run` para superadmin). El quinto test mide la
  tasa real de analyzers: **45,8 % < 50 %** — hallazgo de infraestructura
  **BUG-072** (wires stale de analyzers excluidos + dedup por nombre
  exacto que ignoraba sufijos de versión; corregido en `cortex_setup.py`
  con matching por nombre base + regresión unitaria).
- **TC-19 reforzado**: 8 tests re-verificados en vivo (JWT/revoked → 401
  - challenge; XML/payload excesivo → sin efectos; replay → dedup
  `alert_id` E4) — **verde 410 s**.
- **TC-02 `test_no_blocking`**: **verde en vivo 138 s** (ambos tests
  benignos E4 con el helper corregido).
- **KPI-02**: dashboard **verde en vivo 20 s**. Percentiles: 2 corridas
  — run limpio {82,8–148,0 s}, media **109,7 s ✓**; run bajo carga
  (mutmut+TC-13 concurrentes) {104,6–161,8 s}, media **136,5 s ✗** —
  **violación real de RNF-01 bajo concurrencia** (el MTTR del lab está
  en el límite de 120 s y es muy sensible a carga; analyzers Cortex son
  la cola larga ~90–160 s/alerta). El oráculo exigía p90<120 — RNF-01
  documenta **p50 ≤ 120, p90 ≤ 180** (docs/02 §rendimiento, docs/04):
  umbrales corregidos + Step 7 ya no compara percentiles del endpoint
  (agregado de toda la ventana) contra los 5 valores del test, sino
  consistencia interna; Step 8 acota valores individuales a la cola
  documentada (180 s). Hallazgo colateral: `load_env` solo leía
  `.env.full`, no montado en contenedor → credenciales Grafana vacías →
  401; ahora cae a `.env.container`. Param `period_hours` → `hours` en
  KPI-04. **Run quiescente N=30** (`E2E_KPI02_NUM_ALERTS=30`, 54:45):
  min 62,5 / p50 **74,3** / p90 **109,5** / p95 110,2 / p99 140,8 /
  media **78,5 s** — RNF-01 cumplido con muestra estadística real
  (n≥30); la purga de analyzers stale recortó ~31 s/alerta de media
  respecto al run pre-regeneración (109,7 s).
- **TC-13 Loki**: labels `job=~".+"` inexistentes sustituidos por
  `container` (Promtail etiqueta `compose_service`/`container`/`network`);
  `test_loki_ingestion` e `integration_completeness` verdes con oráculos
  de marcador real; `trace_id_search` usa `container=worker-<exec_id>`
  con fallback a `|= alert_id` y ventana de 180 s (spawn de worker +
  scrape + ingest > 60 s bajo carga); `log_aggregation` endurecido —
  series obligatorias con label `container` y valores no vacíos (antes
  era `if status=="success"` condicional + label `job` inexistente).
  **15/15 verde en vivo (478 s).**
- **TC-22 backup**: ambos tests re-hechos E4 — `test_backup_integrity`
  crea un tar.gz real vía `/backup/create`, lo verifica en `/backup/list`
  y en disco (magic gzip) — **verde 48 s**; `test_backup_restore` hace
  canario real (archivo → backup → delete → restore → reaparece
  idéntico) — **verde 281 s**. El primer oráculo real cazó **BUG-075**
  (restore siempre 500: tar no podía escribir bajo bind mounts RO —
  `infra/`, `docs/`, `.env.container`); corregido en
  `tar_backup_driver.extract` excluyendo mounts RO detectados vía
  `/proc/mounts` + regresión unitaria. Eliminado el patrón vacuo que
  fabricaba JSON falso y se releía a sí mismo.
- **TC-16**: oráculo de linkage endurecido (caso TheHive DEBE referenciar
  el `alert_id`, no solo loguearlo); contador de errores por tipo ya no
  afirma tracking que no existe (probes de transporte no indexan en
  soar-metrics — aclarado).
- **TC-14**: re-escrito contra el contrato real — `alert_id` como
  marcador cross-system (ES/TheHive/Cortex/MISP) tras descubrir que
  `trace_id` no se persistía. Verificado en vivo.
- **Propagación real de `trace_id` implementada** (antes brecha
  documentada): `normalize_inputs` pasa `trace_id`, `build_es_json` lo
  indexa en `soar-alerts`, `build_case_json` lo añade a tags y
  descripción del caso TheHive. Workflow regenerado `d84ad148` con los
  scripts embebidos nuevos (20 ocurrencias `trace_id` en el JSON
  desplegado); API key rotada y resincronizada en `.env`/`.env.full`/
  `.env.container`. TC-32/TC-14 re-verificados sobre la nueva
  propagación.
- **KPI-06**: `test_service_health` **5/5 verde en vivo 75,8 s** — tasa
  de éxito de analyzers ≥50 % confirmada sobre datos en vivo tras la
  regeneración del workflow (BUG-072 cerrado).
- **BUG-074 CERRADO — propagación `trace_id` end-to-end**: además de
  `build_case_json`/`build_es_json`, `build_hive_summary` (que
  sobreescribe la descripción del caso) añade fila `Trace ID`,
  `enrich_case` preserva `alert_id:`/`trace_id:` en tags (la lista
  estática los perdía) y `build_metrics_json` lo indexa en
  `soar-metrics`. Workflow `41bf5837` regenerado (35 refs).
  **TC-32 golden-thread PASSED 117 s** con `assert_trace_id_consistent`
  real sobre UUID propagado; **TC-14 10/10 PASSED** (`test_traceability`
  verifica trace_id en caso TheHive + doc ES, `test_complete_*` 9/9).
- **TC-28 Playwright real (host)**: `test_ui_playwright.py` — Chromium
  real sobre las UIs desplegadas: Shuffle `/login` monta el formulario,
  TheHive/Cortex sirven login, y **login real en Grafana + dashboard
  `soar-kpi-main` renderiza sus 15 paneles en navegador** (E4 de verdad,
  no probe HTTP). **4/4 PASSED 103 s**. La suite salta honestamente en
  contenedor (dependencia host-only); `timeout_method=signal` del
  `pytest.ini` de e2e impide correr bajo Windows host salvo override.
- **Grafana dashboard 401 resuelto**: dos causas raíz —
  `GRAFANA_ADMIN_PASSWORD` no está en el env del contenedor api (solo en
  `.env.container`) → auth `admin:""` → 401; y `import_grafana_dashboard`
  hacía POST del modelo crudo sobre un dashboard **provisionado**
  (`Cannot save provisioned dashboard`). Corregido: `_env_or_file` lee
  credenciales del env-file montado, envelope `{"dashboard":…}` correcto
  y no-op idempotente cuando el UID ya existe. Verificado live.
- **TC-30 helpers endurecidos**: `_disconnect_container`/
  `_reconnect_container` ya no devuelven `True` ante `docker stop/start`
  con rc≠0, y ahora verifican `State.Running` real vía `docker inspect`
  (el exit code no prueba el outage). Pendiente run live pesado.

Salida esperada:

- Ningún fichero por debajo de 8.
- Nota media: 8,5 a 8,7.

### Fase 4: evidencia E4 y estabilización

Duración: 2 a 4 semanas.

Incluye:

- Paquetes de evidencia.
- Entorno reproducible.
- Repeticiones.
- Flakiness.
- Rendimiento con muestra suficiente.
- Mutation testing.
- Playwright.
- Fault injection completo.
- Backup y restore real.

**Estado (2026-11-06):**

- **EVID-001/002/003 entregado** (2026-11-08): `run_context_mixin` escribe
  por test `manifest.json` (rutas + SHA-256 de cada artefacto),
  `environment.json` (python, pytest, plugins, plataforma, git
  commit/branch/dirty, digests de imágenes Docker vía socket montado,
  RAM, versión del daemon Docker, `randomly_seed` y workers xdist de la
  sesión), `result.json` con `outcome` formal
  `passed|failed|warning|skipped|not_applicable`, `assertions.json`,
  `cleanup.json`, `evidence/`; secretos del entorno redactados antes de
  serializar. `scripts/quality/score_evidence.py` (`make evidence-score`)
  puntúa 5 dimensiones por paquete, clasifica tier E1–E4, excluye
  skipped/N-A del denominador de aprobados, publica IC95 y gates —
  baseline histórica 1272 paquetes: mean 58.8 FAIL honesto (los
  artefactos pre-campos puntúan bajo). Verificado en vivo (TC-31) +
  16/16 tests outcome + 15/15 tests scorer.
- **Orden aleatorio**: `pytest-randomly` instalado en contenedor y en
  `pyproject.toml`; runs con seed registrado (3617741622, 4109098534…).
  Expuso el defecto semántico del oráculo de contención (TC-02).
- **Paralelismo**: `pytest-xdist` verificado `-n 2` (4/4 verde, 37 s,
  LoadScheduling) — aislamiento `run_id`/`uid()` sin cross-talk.
- **Mutation testing**: `security/sanitization.py` — **146/146 mutantes
  KILLED (100 %)** contra `test_payload_sanitization.py` +
  `test_property_based.py` + `test_automated_security.py`.
  Harness manual por mutante (`MUTANT_UNDER_TEST` +
  `-o pythonpath=/app/mutants/src`) porque el runner de mutmut falla
  coleccionando bajo `mutants/`; cada veredicto ambiguo se re-verificó
  con ejecución fresca (66 re-runs). Una corrida previa del harness
  reportaba falsos SURVIVED (pytest resolvía site-packages en vez de la
  copia mutada) — corregido. Evidencia:
  `reports/mutation/sanitization_summary.json` +
  `sanitization_mutants_verdicts.tsv`.
- **Flakiness medida (N≥3 secuencial, pytest-randomly)**: TC-13
  **15/15 ×3** (503/409/474 s) — 0 % flake. KPI-06 iter1 **7/9 — dos
  races reales cazadas**: (a) `test_elasticsearch_opensearch_coherence`
  leía el doc OpenSearch una sola vez y veía `EXECUTING` — el write-back
  de estado llega tras el FINISHED del API de Shuffle (consistencia
  eventual); (b) `test_loki_workflow_coherence` consultaba el
  correlation_id una sola vez antes de que Promtail ingiriera (lag
  documentado >60 s). Ambas corregidas con `wait_until` acotado
  (`es_index`×2, `loki_ingest`×2) — **KPI-06 9/9 ×2 consecutivo
  post-fix (567/662 s)**. También el 500 transitorio de
  `/analytics/kpis/aggregated` y MTTR inflado bajo concurrencia
  (techo de capacidad, BUG-073).
- **Playwright ENTREGADO (perfil host)**: `test_ui_playwright.py` —
  4/4 en Chromium real (103 s); skip honesto en contenedor.
- **Backup/restore real ENTREGADO**: TC-22 E4 + BUG-075 corregido.
- Pendientes: fault injection completo (TC-30 live run), repetición
  N≥3 de suites en curso, muestras KPI N≥30.

Salida esperada:

- Nota dinámica: 9,0 a 9,2.
- Evidencia E4.
- Flakiness crítica 0 %.
- Capacidad de reproducir cada resultado.

## 17. Camino mínimo para llegar al 9

Si hay que recortar alcance, estas son las tareas irrenunciables:

- Eliminar todos los soft-fails centrales.
- Eliminar asserts tautológicos.
- Eliminar `max(caseId)`.
- Introducir IDs únicos y namespaces.
- Implementar cleanup.
- Eliminar suite-llama-test.
- Sustituir sleeps por polling.
- Unificar contratos HTTP.
- Corregir los bugs agudos.
- Rehacer TC-04 con SLAs reales.
- Rehacer TC-14 traceability.
- Rehacer TC-16 error handling.
- Rehacer TC-19 security.
- Rehacer TC-22 backup y restore.
- Rehacer TC-23 privacy.
- Rehacer TC-24 malware specific.
- Rehacer TC-28 con Playwright.
- Convertir TC-32 golden thread en gate.
- Corregir KPI-02 dashboard.
- Corregir KPI-03 alerts.
- Aumentar muestras de percentiles a 30 o más.
- Generar evidencia por test.
- Medir flakiness.
- Ejecutar tests en orden aleatorio.
- Ejecutar mutation testing sobre invariantes críticas.

## 18. Definition of Done para cada test E2E

Un test no se considera finalizado hasta que:

- Tiene un propósito único y explícito.
- Mapea a ISO 25010.
- Define precondiciones.
- Define entradas.
- Define resultados esperados.
- Define efectos prohibidos.
- Usa IDs únicos.
- Selecciona únicamente sus recursos.
- No depende del orden.
- No depende de estado histórico.
- No usa asserts tautológicos.
- No convierte fallos centrales en warnings.
- No acepta estados ambiguos.
- Usa polling con timeout.
- Limpia todos sus recursos.
- Restaura servicios modificados.
- Produce artifacts.
- Redacta secretos.
- Incluye diagnóstico útil.
- Pasa aislado.
- Pasa en orden aleatorio.
- Pasa en paralelo cuando está declarado como paralelizable.
- Falla al mutar deliberadamente el comportamiento objetivo.
- Tiene nota individual mínima de 8,5.
- Los tests críticos tienen nota mínima de 9.

## 19. Gates finales para conceder el 9

### Gate 1: validez

- Cero falsos verdes conocidos.
- Cero invariantes centrales tragadas.
- Cero asserts tautológicos críticos.
- Todas las mutaciones críticas provocan rojo.

### Gate 2: independencia

- Todos los tests pasan aislados.
- La suite pasa en orden aleatorio.
- No se seleccionan recursos por máximos globales.
- No se usan datos stale de ejecuciones anteriores.

### Gate 3: repetibilidad

- Flakiness crítica 0 %.
- Flakiness global inferior al 1 %.
- Tres ejecuciones completas consecutivas pasan.
- Los fallos conservan evidencias suficientes.

### Gate 4: limpieza

- Cero servicios detenidos tras la suite.
- Cero ejecuciones zombie creadas por los tests.
- Cero claves, casos o documentos no registrados.
- Los residuos deliberadamente preservados están identificados.

### Gate 5: contratos

- HTTP coherente.
- OpenAPI alineada.
- SLAs declarados iguales a los aplicados.
- Los estados terminales están definidos.
- `EXECUTING` no cuenta como éxito final.

### Gate 6: evidencia E4

- Stack real ejecutado.
- Commit y entorno registrados.
- Artifacts por test.
- Pruebas E2E completas.
- Resultados reproducibles.
- Informe ISO generado automáticamente.

## 20. Resultado esperado

Aplicando este backlog, la distribución objetivo sería:

| Grupo | Nota actual aproximada | Objetivo |
| --- | --- | --- |
| TC-00 a TC-09 | 6,2 | 9,1 |
| TC-10 a TC-17 | 5,3 | 9,0 |
| TC-18 a TC-33 | 5,7 | 9,2 |
| KPIs | 5,5 | 9,0 |
| Infraestructura compartida | 8,5 | 9,5 |
| Global | 5,6 | 9,1 |

El cambio decisivo no será añadir más ficheros. Será transformar la suite desde:

> "el workflow respondió y no se produjo una excepción"

hacia:

> "esta entrada produjo exactamente esta ejecución, estos datos,
> esta decisión y estos efectos, no produjo ningún efecto prohibido,
> se conservó la trazabilidad entre sistemas, se restauró el entorno
> y una mutación deliberada del resultado hace fallar el test".

Mejoras principales del backlog:

- Validez: elimina asserts que no pueden fallar y soft-fails.
- Aislamiento: cada test identifica y limpia exclusivamente sus recursos.
- Repetibilidad: sustituye sleeps, estado histórico y orden implícito por polling y fixtures explícitos.
- Profundidad: mide efectos del sistema, no copias locales del payload.
- Evidencia: eleva la evaluación de E2 estática a E4 ejecutada y reproducible.
- Orientación al 9: establece gates que impiden obtener una nota alta mientras sobrevivan falsos verdes, carreras o resultados no verificables.

## 21. Referencias

- `docs/17-technical-backlog-9of10.md` — backlog general del proyecto.
- `docs/16-formal-audit-iso25040.md` — auditoría formal y modelo E0–E4.
- `docs/15-project-evaluation-scorecard.md` — scorecard de 16 campos.
- `docs/13-defect-driven-testing.md` — proceso de defectos failing-first.
- `tests/e2e/` — suite objeto de este backlog (49 ficheros, ~26 000 líneas).
