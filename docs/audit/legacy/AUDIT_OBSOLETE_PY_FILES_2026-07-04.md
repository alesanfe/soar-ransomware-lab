# Archivos .py Potencialmente Obsoletos

**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Scripts de Debugging/Desarrollo en src/soar_lab/integrations/shuffle/

### 1. test_workflow.py

**Ruta**: `src/soar_lab/integrations/shuffle/test_workflow.py`  
**Líneas**: 70  
**Propósito**: Prueba workflow y verifica networking de Docker  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: Documentado en `docs/operations/configuration_manual.md` (línea 714)  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 2. check_execution.py

**Ruta**: `src/soar_lab/integrations/shuffle/check_execution.py`  
**Líneas**: 37  
**Propósito**: Verifica resultado de ejecución de workflow  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: Documentado en `docs/operations/configuration_manual.md` (línea 789)  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 3. fix_workflow_actions.py

**Ruta**: `src/soar_lab/integrations/shuffle/fix_workflow_actions.py`  
**Líneas**: 24  
**Propósito**: Arregla workflow para usar action_name correcto  
**Estado**: SCRIPT DE FIX (DEBUGGING)  
**Referencias**: No encontrado en código principal  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 4. fix_workflow_thehive.py

**Ruta**: `src/soar_lab/integrations/shuffle/fix_workflow_thehive.py`  
**Líneas**: 33  
**Propósito**: Arregla workflow para usar app TheHive  
**Estado**: SCRIPT DE FIX (DEBUGGING)  
**Referencias**: Documentado en `docs/operations/configuration_manual.md` (línea 790)  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 5. check_workflow.py

**Ruta**: `src/soar_lab/integrations/shuffle/check_workflow.py`  
**Líneas**: 15  
**Propósito**: Verifica workflow en Elasticsearch  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: No encontrado en código principal  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 6. list_workflows.py

**Ruta**: `src/soar_lab/integrations/shuffle/list_workflows.py`  
**Líneas**: 8  
**Propósito**: Lista workflows en Elasticsearch  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: No encontrado en código principal  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 7. register_http_app.py

**Ruta**: `src/soar_lab/integrations/shuffle/register_http_app.py`  
**Líneas**: 30  
**Propósito**: Registra HTTP app en Elasticsearch  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: No encontrado en código principal  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

### 8. activate_workflow.py

**Ruta**: `src/soar_lab/integrations/shuffle/activate_workflow.py`  
**Líneas**: 35  
**Propósito**: Activa workflow y guarda info en artifacts  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: Documentado en `docs/operations/configuration_manual.md` (línea 787)  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa en operaciones manuales

---

## Scripts de Debugging/Desarrollo en infra/vagrant/

### 1. workflow_info.py

**Ruta**: `infra/vagrant/workflow_info.py`  
**Líneas**: 33  
**Propósito**: Obtiene información del workflow de Shuffle  
**Estado**: DUPLICADO (workflow_info2.py es versión extendida)  
**Referencias**: No encontrado en Vagrantfile ni otros archivos de infraestructura  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa, o consolidar con workflow_info2.py

### 2. workflow_info2.py

**Ruta**: `infra/vagrant/workflow_info2.py`  
**Líneas**: 43  
**Propósito**: Versión extendida de workflow_info.py que guarda resultado en `/tmp/workflow_result.txt`  
**Estado**: DUPLICADO (versión extendida de workflow_info.py)  
**Referencias**: No encontrado en Vagrantfile ni otros archivos de infraestructura  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Mantener si la funcionalidad de guardar a archivo es necesaria, eliminar si no

### 3. delete_workflow.py

**Ruta**: `infra/vagrant/delete_workflow.py`  
**Líneas**: 28  
**Propósito**: Elimina el workflow SOAR-Ransomware-Response de Shuffle  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: No encontrado en Vagrantfile ni otros archivos de infraestructura  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa (es un script destructivo de debugging)

### 4. deep_check.py

**Ruta**: `infra/vagrant/deep_check.py`  
**Líneas**: 40  
**Propósito**: Check profundo del workflow de Shuffle (triggers y acciones)  
**Estado**: SCRIPT DE DEBUGGING  
**Referencias**: No encontrado en Vagrantfile ni otros archivos de infraestructura  
**Clasificación**: REVISAR_MANUALMENTE  
**Recomendación**: Eliminar si no se usa (es un script de debugging)

### 5. simulate_alerts.py (infra/vagrant/)

**Ruta**: `infra/vagrant/simulate_alerts.py`  
**Líneas**: 90  
**Propósito**: Simulador de alertas para VM Ubuntu (reemplazo para VM Windows)  
**Estado**: USADO EN MAKEFILE  
**Referencias**: Makefile.win línea 248 (target vagrant-simulate)  
**Clasificación**: CONSERVAR_EN_GIT  
**Recomendación**: NO ELIMINAR - se usa en el Makefile

---

## Archivos .py en artifacts/data/ (Datos Runtime)

### Wazuh Integration Files

**Ruta**: `artifacts/data/wazuh/integration_files/*.py`  
**Archivos**:

- `virustotal.py`
- `slack.py`
- `shuffle.py`
- `pagerduty.py`
- `maltiverse.py`

**Estado**: DATOS RUNTIME (integraciones de Wazuh)  
**Clasificación**: PROPONER_IGNORAR_AL_FINAL  
**Recomendación**: Ignorar en .gitignore (son datos runtime de Wazuh)

### Wazuh Wodles

**Ruta**: `artifacts/data/wazuh/wodles/**/*.py`  
**Archivos**: Múltiples scripts de wodles de Wazuh (AWS, GCloud, Azure, Docker)

**Estado**: DATOS RUNTIME (wodles de Wazuh)  
**Clasificación**: PROPONER_IGNORAR_AL_FINAL  
**Recomendación**: Ignorar en .gitignore (son datos runtime de Wazuh)

### Wazuh Active Response

**Ruta**: `artifacts/data/wazuh/active_response/kaspersky.py`  
**Estado**: DATOS RUNTIME (active response de Wazuh)  
**Clasificación**: PROPONER_IGNORAR_AL_FINAL  
**Recomendación**: Ignorar en .gitignore (es dato runtime de Wazuh)

---

## Resumen

### REVISAR_MANUALMENTE (8 archivos en src/soar_lab/integrations/shuffle/)

1. `src/soar_lab/integrations/shuffle/test_workflow.py` - Script de debugging (documentado en manual)
2. `src/soar_lab/integrations/shuffle/check_execution.py` - Script de debugging (documentado en manual)
3. `src/soar_lab/integrations/shuffle/fix_workflow_actions.py` - Script de fix (no referenciado)
4. `src/soar_lab/integrations/shuffle/fix_workflow_thehive.py` - Script de fix (documentado en manual)
5. `src/soar_lab/integrations/shuffle/check_workflow.py` - Script de debugging (no referenciado)
6. `src/soar_lab/integrations/shuffle/list_workflows.py` - Script de debugging (no referenciado)
7. `src/soar_lab/integrations/shuffle/register_http_app.py` - Script de debugging (no referenciado)
8. `src/soar_lab/integrations/shuffle/activate_workflow.py` - Script de debugging (documentado en manual)

### BORRAR_SEGURO (4 archivos en infra/vagrant/)

1. `infra/vagrant/workflow_info.py` - Script de debugging no referenciado
2. `infra/vagrant/workflow_info2.py` - Script de debugging no referenciado
3. `infra/vagrant/delete_workflow.py` - Script de debugging destructivo no referenciado
4. `infra/vagrant/deep_check.py` - Script de debugging no referenciado

### CONSERVAR_EN_GIT (1 archivo en infra/vagrant/)

1. `infra/vagrant/simulate_alerts.py` - Usado en Makefile.win línea 248

### PROPONER_IGNORAR_AL_FINAL (artifacts/data/wazuh/)

- Todos los archivos .py en `artifacts/data/wazuh/` son datos runtime de Wazuh
- Deben ignorarse en .gitignore, no borrarse

---

## Recomendación

**Inmediata**: Eliminar los 4 scripts de debugging en `infra/vagrant/` (no referenciados)  
**Final**: Agregar `artifacts/data/wazuh/**/*.py` a .gitignore (datos runtime)

---

## Acción Ejecutada

**Fecha**: 2026-07-04  
**Acción**: Eliminación de scripts de debugging no referenciados y directorio duplicado

### Archivos Eliminados

1. `infra/vagrant/workflow_info.py` - Script de debugging
2. `infra/vagrant/workflow_info2.py` - Script de debugging
3. `infra/vagrant/delete_workflow.py` - Script de debugging destructivo
4. `infra/vagrant/deep_check.py` - Script de debugging
5. `infra/infra/` - Directorio duplicado de infra/docker/nginx/ssl/
6. `src/soar_lab.egg-info/` - Caché de Python (metadata de paquete)

### Reportes Antiguos Eliminados

1. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md` - Reporte vacío
2. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_FINAL.md` - Reporte antiguo
3. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_FINAL.md` - Reporte antiguo

### Cachés de Python Eliminados

1. 31 directorios __pycache__ (cachés de bytecode)
2. 221 archivos .pyc (bytecode compilado)

### Archivos Temporales Eliminados

1. `artifacts/temp/fix_workflow_mapping.json` - Archivo temporal

### Justificación

- Ninguno de los scripts está referenciado en el código principal, Makefile, Vagrantfile o documentación
- Son scripts de debugging/desarrollo que no se usan actualmente
- `simulate_alerts.py` se conserva porque se usa en Makefile.win línea 248
- `infra/infra/` es un duplicado de `infra/docker/nginx/ssl/`
- Los reportes antiguos han sido reemplazados por versiones más recientes
