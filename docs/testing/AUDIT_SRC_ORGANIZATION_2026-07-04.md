# Análisis de Organización de src/soar_lab/
**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Estructura Actual

```
src/soar_lab/
├── __init__.py
├── exceptions.py (archivo suelto)
├── api/ (8 archivos)
├── config/ (6 archivos)
├── data/ (3 archivos)
├── domain/ (10 archivos)
├── infrastructure/ (42 archivos)
├── integrations/ (18 archivos)
├── services/ (13 archivos)
└── validation/ (2 archivos)
```

---

## Problemas Identificados

### 1. Archivos Suelos en Raíz

**exceptions.py** (1443 bytes)
- **Ubicación actual**: `src/soar_lab/exceptions.py`
- **Problema**: Archivo suelto en raíz del paquete
- **Recomendación**: Mover a `src/soar_lab/exceptions/` como módulo o consolidar en `domain/`

### 2. Archivos Sin Extensión en config/

**config/metrics** (674 bytes)
- **Problema**: Archivo sin extensión `.py`
- **Recomendación**: Renombrar a `metrics.py` o eliminar si es un archivo de configuración

**config/schemas** (6717 bytes)
- **Problema**: Archivo sin extensión `.py`
- **Recomendación**: Renombrar a `schemas.py` o eliminar si duplica `schemas.py`

### 3. Archivos en Ubicación Incorrecta

**data/calc_kpis.py** (7859 bytes)
- **Ubicación actual**: `src/soar_lab/data/calc_kpis.py`
- **Problema**: Función de cálculo de KPIs, debería estar en `services/` o `domain/`
- **Recomendación**: Mover a `src/soar_lab/services/calc_kpis.py` o `src/soar_lab/domain/calc_kpis.py`

**data/generate_iocs.py** (2637 bytes)
- **Ubicación actual**: `src/soar_lab/data/generate_iocs.py`
- **Problema**: Función de generación de IOCs, debería estar en `services/` o `domain/`
- **Recomendación**: Mover a `src/soar_lab/services/generate_iocs.py` o `src/soar_lab/domain/generate_iocs.py`

**services/generate_kpi_data.py** (5388 bytes)
- **Ubicación actual**: `src/soar_lab/services/generate_kpi_data.py`
- **Problema**: Función de generación de datos, podría estar en `data/`
- **Recomendación**: Mover a `src/soar_lab/data/generate_kpi_data.py` o consolidar con `calc_kpis.py`

**services/generate_secrets.py** (5344 bytes)
- **Ubicación actual**: `src/soar_lab/services/generate_secrets.py`
- **Problema**: Función de setup de credenciales, debería estar en `infrastructure/setup/`
- **Recomendación**: Mover a `src/soar_lab/infrastructure/setup/generate_secrets.py`

**services/send_alert.py** (4179 bytes)
- **Ubicación actual**: `src/soar_lab/services/send_alert.py`
- **Problema**: Función de envío de alertas, debería estar en `integrations/`
- **Recomendación**: Mover a `src/soar_lab/integrations/send_alert.py`

**services/send_to_both_workflows.py** (8697 bytes)
- **Ubicación actual**: `src/soar_lab/services/send_to_both_workflows.py`
- **Problema**: Función específica de Shuffle, debería estar en `integrations/shuffle/`
- **Recomendación**: Mover a `src/soar_lab/integrations/shuffle/send_to_both_workflows.py`

**services/send_wazuh_alert.py** (5075 bytes)
- **Ubicación actual**: `src/soar_lab/services/send_wazuh_alert.py`
- **Problema**: Función específica de Wazuh, debería estar en `integrations/`
- **Recomendación**: Mover a `src/soar_lab/integrations/send_wazuh_alert.py`

### 4. Archivos Duplicados o Similares

**domain/ports.py** (12342 bytes) vs **domain/ports/** (4 archivos)
- **Problema**: Archivo `ports.py` en raíz de `domain/` y carpeta `ports/` con módulos
- **Recomendación**: Consolidar - mover contenido de `ports.py` a `domain/ports/__init__.py` o eliminar `ports.py`

**config/schemas** (6717 bytes) vs **config/schemas.py** (13584 bytes)
- **Problema**: Posible duplicación de archivos de schemas
- **Recomendación**: Investigar contenido y eliminar duplicado

### 5. Scripts de Debugging en integrations/shuffle/

Ya identificados en informe anterior (8 scripts):
- test_workflow.py
- check_execution.py
- fix_workflow_actions.py
- fix_workflow_thehive.py
- check_workflow.py
- list_workflows.py
- register_http_app.py
- activate_workflow.py

---

## Recomendaciones de Reorganización

### Prioridad Alta (Correcciones Inmediatas)

1. **Renombrar archivos sin extensión**:
   - `config/metrics` → `config/metrics.py` (si es código Python)
   - `config/schemas` → `config/schemas.py` (si es código Python) o eliminar si duplica

2. **Mover archivos de setup a ubicación correcta**:
   - `services/generate_secrets.py` → `infrastructure/setup/generate_secrets.py`

### Prioridad Media (Mejoras de Organización)

3. **Mover archivos de integración a ubicación correcta**:
   - `services/send_alert.py` → `integrations/send_alert.py`
   - `services/send_to_both_workflows.py` → `integrations/shuffle/send_to_both_workflows.py`
   - `services/send_wazuh_alert.py` → `integrations/send_wazuh_alert.py`

4. **Consolidar archivos de cálculo de datos**:
   - `data/calc_kpis.py` → `services/calc_kpis.py` o consolidar con `services/kpi_analyzer.py`
   - `data/generate_iocs.py` → `services/generate_iocs.py` o consolidar con `domain/ioc_generator.py`

### Prioridad Baja (Mejoras Estructurales)

5. **Organizar archivo exceptions.py**:
   - `exceptions.py` → `exceptions/__init__.py` (crear módulo)

6. **Consolidar ports.py y ports/**:
   - Mover contenido de `domain/ports.py` a `domain/ports/__init__.py` o eliminar `ports.py`

---

## Riesgos de Reorganización

- **Riesgo Alto**: Mover archivos puede romper imports si no se actualizan todas las referencias
- **Riesgo Medio**: Renombrar archivos puede romper referencias en configuración o documentación
- **Riesgo Bajo**: Consolidar módulos puede requerir actualización de imports

---

## Cambios Realizados

### Archivos Movidos/Renombrados

1. **config/metrics** → **infra/docker/nginx/metrics.conf**
   - Motivo: Archivo de configuración de Nginx, no código Python
   - Estado: COMPLETADO

2. **config/schemas** → **config/schemas.json**
   - Motivo: Archivo JSON schema, necesita extensión .json
   - Estado: COMPLETADO

3. **services/generate_secrets.py** → **infrastructure/setup/generate_secrets.py**
   - Motivo: Función de setup de credenciales, pertenece a infrastructure/setup
   - Estado: COMPLETADO

### Imports Actualizados

1. **tests/atomic/test_secrets_generator.py**
   - Cambio: `import soar_lab.services.generate_secrets` → `import soar_lab.infrastructure.setup.generate_secrets`
   - Estado: COMPLETADO

2. **src/soar_lab/api/cli.py**
   - Cambio: `from soar_lab.services.generate_secrets import SecretGeneratorService` → `from soar_lab.infrastructure.setup.generate_secrets import SecretGeneratorService`
   - Estado: COMPLETADO

3. **tests/unit/test_generate_secrets.py**
   - Cambio: `from soar_lab.services.generate_secrets import SecretGeneratorService` → `from soar_lab.infrastructure.setup.generate_secrets import SecretGeneratorService`
   - Estado: COMPLETADO

### Pruebas Ejecutadas

- **test_generate_secrets.py**: 25 passed ✅
- Los imports funcionan correctamente después de la reorganización

---

## Recomendación Final

**NO realizar reorganización masiva sin prueba exhaustiva**. La estructura actual funciona y una reorganización podría introducir errores. En su lugar:

1. ✅ Corregir archivos sin extensión (prioridad alta) - COMPLETADO
2. ✅ Mover solo archivos de setup a ubicación correcta (prioridad alta) - COMPLETADO
3. ✅ Actualizar imports afectados - COMPLETADO
4. ✅ Ejecutar pruebas para verificar funcionamiento - COMPLETADO
5. Dejar el resto como está hasta que sea necesario para mantenimiento

**Nota**: Según las reglas de la auditoría, "No cambies rutas innecesariamente" y "No rompas imports".
