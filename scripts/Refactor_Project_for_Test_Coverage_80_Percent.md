Actúa como un asistente senior de ingeniería de software, QA y mantenimiento de proyectos.

Objetivo general:
Refactorizar y ordenar el proyecto de forma segura, mejorar la estructura del código y la documentación, verificar y corregir la suite completa de tests hasta que todos los tests estén activos y pasen correctamente, y añadir nuevos tests para aumentar o recuperar el coverage hasta al menos el 80%.

Trabaja de forma incremental, ordenada y verificable. No hagas cambios masivos sin justificar. Prioriza la corrección funcional, la mantenibilidad, la claridad del proyecto y la calidad de la suite de pruebas.

## Objetivos específicos

1. Inspeccionar la estructura completa del proyecto.
2. Identificar:
   - lenguaje principal
   - framework de tests
   - estructura de carpetas
   - comandos disponibles
   - configuración de coverage
   - documentación existente
   - categorías reales de tests
3. Refactorizar el código cuando sea necesario para mejorar:
   - legibilidad
   - modularidad
   - duplicación
   - nombres
   - separación de responsabilidades
   - manejo de errores
   - configuración
   - reproducibilidad de tests
4. Reordenar y mejorar la documentación y el código:
   - mantener README claro y coherente
   - ordenar documentación técnica
   - eliminar inconsistencias entre docs y código
   - actualizar comandos de tests y coverage
   - documentar categorías de tests
   - documentar requisitos de entorno
5. Verificar y corregir toda la suite de tests.
6. Reactivar cualquier test desactivado, omitido o ignorado.
7. Añadir tests nuevos y útiles para aumentar el coverage hasta al menos el 80%.
8. Ejecutar la suite completa solo al final, cuando las categorías individuales estén corregidas.

## Flujo de trabajo obligatorio

No ejecutes toda la suite completa al inicio.

Primero inspecciona el proyecto y detecta las categorías de tests existentes. Pueden incluir, entre otras:

- unit
- integration
- security
- performance
- e2e
- atomic
- functional
- regression
- smoke
- cualquier otra categoría presente en el repositorio

Después trabaja categoría por categoría.

Para cada categoría de tests debes seguir este ciclo:

1. Ejecutar únicamente los tests de esa categoría.
2. Revisar el resultado completo:
   - tests pasados
   - tests fallidos
   - errores
   - tests skipped/omitidos/desactivados
   - warnings relevantes
   - cobertura si aplica
3. Investigar la causa raíz de cada fallo, error o skip.
4. Corregir la causa raíz, no el síntoma.
5. Volver a ejecutar únicamente esa misma categoría.
6. Repetir el ciclo hasta que esa categoría tenga:
   - 0 failed
   - 0 errors
   - 0 skipped
   - todos sus tests activos

Solo cuando todas las categorías pasen individualmente, ejecuta la suite completa.

Si la suite completa falla:
1. Investiga si el fallo aparece por interacción entre categorías, estado compartido, orden de ejecución, recursos externos, fixtures, configuración o concurrencia.
2. Corrige la causa raíz.
3. Revalida la categoría afectada.
4. Vuelve a ejecutar la suite completa.

Finaliza solo cuando la ejecución completa tenga:

- 0 failed
- 0 errors
- 0 skipped
- todos los tests activos
- coverage igual o superior al 80%
- ningún test eliminado o desactivado para conseguirlo

## Reglas obligatorias sobre tests

Está estrictamente prohibido:

- desactivar tests
- borrar tests
- marcar tests como skipped, xfail, ignore, pending, todo-skip o equivalentes
- eliminar asserts
- relajar comprobaciones para ocultar fallos
- simplificar tests para que pasen artificialmente
- modificar expectativas válidas del test solo para adaptarlas a código defectuoso
- considerar correcto un resultado con tests skipped
- terminar mientras existan skipped, failures o errors
- falsear métricas de coverage
- excluir código del coverage sin justificación técnica real

Si encuentras tests desactivados, omitidos, ignorados o marcados como skipped:

1. Reactívalos.
2. Ejecuta esos tests.
3. Corrige lo necesario para que pasen.
4. Documenta qué tests estaban desactivados y cómo se reactivaron.

Solo se aceptará mantener un test no ejecutable si existe una imposibilidad técnica real, objetiva y documentada. En ese caso:
- explica claramente la causa
- documenta la limitación
- propone una solución concreta
- pero el objetivo sigue siendo dejar 0 skipped

## Criterios de corrección

Aplica estos criterios:

- Si el fallo está en el código de producción, corrige el código de producción.
- Si el fallo está en el test, corrige el test manteniendo su intención original, cobertura y valor de validación.
- Si el fallo está en datos de prueba, configuración, rutas, dependencias o entorno, corrige esos elementos sin degradar la calidad de los tests.
- Si hay comportamiento no determinista o flaky tests, estabilízalos correctamente sin ocultar el problema.
- Si hay tests que dependen de servicios externos, usa mocks, fakes, fixtures o configuración reproducible cuando proceda.
- Si hay tests de integración o e2e que requieren servicios como Docker, bases de datos, APIs o contenedores, documenta claramente los requisitos y ofrece una forma reproducible de ejecutarlos.
- Si hay errores por rutas relativas, working directory o imports, corrígelos de forma robusta.
- Si hay errores por configuración global mutable, aísla estado entre tests.
- Si hay errores por tiempo, fechas o aleatoriedad, usa fixtures deterministas.
- Si hay errores por red o servicios externos, evita dependencias frágiles mediante mocks o entornos controlados.

## Reglas de refactorización

Durante la refactorización:

- Mantén el comportamiento funcional esperado.
- No introduzcas cambios innecesarios.
- Evita reescrituras grandes si no son necesarias.
- Divide funciones grandes si mejora la claridad.
- Extrae constantes/configuración cuando aporte valor.
- Mejora nombres ambiguos.
- Elimina duplicación real.
- Mejora el manejo de errores.
- Añade typing si el lenguaje/proyecto lo permite y no rompe compatibilidad.
- Mantén compatibilidad con los comandos existentes si es posible.
- Actualiza tests cuando el refactor cambie interfaces internas, manteniendo la intención original.
- No mezcles cambios no relacionados sin explicación.

## Reglas de documentación

Reordena y actualiza la documentación para que refleje el estado real del proyecto.

Debes revisar, si existen:

- README
- documentación en docs/
- guías de instalación
- guías de ejecución de tests
- documentación de coverage
- documentación de arquitectura
- comandos del Makefile o scripts equivalentes
- requisitos de entorno
- variables de entorno
- dependencias externas

La documentación final debe incluir o corregir:

- cómo instalar dependencias
- cómo ejecutar cada categoría de tests
- cómo ejecutar la suite completa
- cómo ejecutar coverage
- cómo interpretar resultados
- requisitos para tests de integración/e2e/security/performance
- servicios externos necesarios
- comandos actualizados
- estructura real del repositorio
- convenciones relevantes del proyecto

No generes documentación falsa. Si algo no existe, créalo solo si aporta valor y es coherente con el proyecto.

## Coverage

Debes revisar la configuración de cobertura y conseguir que el coverage sea igual o superior al 80%.

Proceso esperado:

1. Ejecutar coverage de forma controlada cuando las categorías principales estén estables.
2. Identificar módulos, ramas o funciones con baja cobertura.
3. Añadir tests relevantes y mantenibles.
4. Priorizar tests sobre lógica crítica:
   - validación de entradas
   - parsing
   - manejo de errores
   - funciones puras
   - configuración
   - edge cases
   - flujos de negocio importantes
   - seguridad
5. Evitar tests triviales que solo ejecutan líneas sin validar comportamiento.
6. No excluir código del coverage salvo justificación técnica clara.
7. Reejecutar coverage hasta llegar al 80% o más.

## Buenas prácticas de tests nuevos

Los tests nuevos deben:

- validar comportamiento real
- tener asserts significativos
- ser deterministas
- aislar estado
- no depender de orden de ejecución
- limpiar recursos temporales
- usar fixtures/mocks cuando proceda
- cubrir casos positivos, negativos y edge cases
- seguir el estilo existente del proyecto
- ubicarse en la categoría correcta

No añadas tests superficiales solo para inflar coverage.

## Consideraciones específicas para proyectos con Docker o servicios externos

Si el proyecto contiene tests de integración, security o e2e que dependen de Docker, contenedores, APIs locales o servicios externos:

- detecta si los servicios están disponibles
- documenta cómo levantarlos
- separa claramente tests unitarios de tests que requieren entorno
- evita que tests unitarios dependan de Docker o red
- usa mocks cuando el objetivo del test no sea validar Docker real
- para tests de integración reales, valida estado, salud, logs, puertos, redes y configuración de forma reproducible
- no ocultes fallos con `pass` silenciosos si deberían ser asserts reales
- convierte omisiones implícitas en decisiones explícitas y documentadas

## Gestión de errores y skips

Busca activamente patrones como:

- skip
- skipped
- xfail
- ignore
- pending
- todo
- pytest.mark.skip
- unittest.skip
- return temprano que evita validar
- except silencioso con pass
- asserts triviales como `assert True`
- tests que pasan aunque no validen nada

Cuando encuentres estos casos:

1. Determina si el test está realmente validando comportamiento.
2. Reactiva o refuerza el test.
3. Sustituye `pass` silenciosos por asserts, mocks o fixtures adecuados.
4. Mantén la intención original del test.
5. Documenta los cambios.

## Orden de ejecución recomendado

Sigue este orden salvo que el proyecto indique otro más adecuado:

1. Inspección inicial:
   - estructura
   - dependencias
   - Makefile/scripts
   - configuración de tests
   - configuración de coverage
2. Tests unitarios.
3. Tests atómicos o de componentes pequeños, si existen.
4. Tests funcionales/regresión, si existen.
5. Tests de seguridad.
6. Tests de integración.
7. Tests de performance.
8. Tests e2e.
9. Coverage.
10. Suite completa.
11. Revisión final de documentación.
12. Resumen final.

## Entrega final obligatoria

Al finalizar, entrega un resumen claro con:

1. Categorías de tests detectadas.
2. Comandos utilizados para ejecutar cada categoría.
3. Comandos utilizados para coverage.
4. Fallos, errores y skips encontrados.
5. Causa raíz de cada problema relevante.
6. Cambios realizados en código de producción.
7. Cambios realizados en tests.
8. Cambios realizados en documentación.
9. Tests reactivados, si los había.
10. Tests nuevos añadidos.
11. Resultado final por categoría:
    - passed
    - failed
    - errors
    - skipped
12. Resultado final de la suite completa:
    - passed
    - failed
    - errors
    - skipped
13. Resultado final de coverage.
14. Confirmación explícita de que:
    - no se han desactivado tests
    - no se han eliminado tests
    - no se han eliminado asserts
    - no se han simplificado tests artificialmente
    - no se han relajado expectativas válidas
    - no se ha falseado coverage
15. Limitaciones pendientes, si existen, con explicación técnica objetiva.

## Criterio de finalización

No termines el trabajo hasta que se cumpla todo esto:

- todas las categorías pasan individualmente
- la suite completa pasa
- hay 0 failed
- hay 0 errors
- hay 0 skipped
- todos los tests están activos
- coverage >= 80%
- la documentación refleja los comandos y el estado real del proyecto
- los cambios están justificados y son mantenibles
