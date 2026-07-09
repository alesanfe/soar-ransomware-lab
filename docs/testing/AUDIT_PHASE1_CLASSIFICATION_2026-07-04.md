# FASE 1: Clasificación de Carpetas y Archivos
**Fecha**: 2026-07-04  
**Auditor**: Cascade AI Assistant

---

## Tabla de Clasificación de Carpetas Principales

| Ruta actual | Tipo | Acción recomendada | Motivo | Riesgo | Comando sugerido |
|-------------|------|-------------------|--------|--------|-----------------|
| **apps/** | Directorio | NO_TOCAR | Código fuente de aplicaciones (api, docs-site, web-management) | Ninguno | Mantener |
| **src/** | Directorio | NO_TOCAR | Código fuente principal del proyecto | Ninguno | Mantener |
| **tests/** | Directorio | NO_TOCAR | Suites de pruebas completas (unit, integration, e2e, security, performance) | Ninguno | Mantener |
| **infra/** | Directorio | NO_TOCAR | Infraestructura como código (Docker, Vagrant, Nginx) | Ninguno | Mantener |
| **docs/** | Directorio | NO_TOCAR | Documentación técnica completa | Ninguno | Mantener |
| **schemas/** | Directorio | NO_TOCAR | Esquemas de datos | Ninguno | Mantener |
| **simulator/** | Directorio | NO_TOCAR | Simulador de ransomware | Ninguno | Mantener |
| **artifacts/** | Directorio | REVISAR_MANUALMENTE | Contiene mezcla de datos runtime y artefactos generados | Medio | Analizar subdirectorios |
| **artifacts/data/** | Directorio | PROPONER_IGNORAR_AL_FINAL | 4255 items de datos runtime (Elasticsearch, Wazuh, MISP, Grafana) | Bajo | Ignorar en .gitignore |
| **artifacts/logs/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Logs de ejecución (ya en .gitignore) | Bajo | Ya ignorado |
| **artifacts/results/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Resultados de pruebas (ya en .gitignore) | Bajo | Ya ignorado |
| **artifacts/coverage/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Reportes de cobertura (ya en .gitignore) | Bajo | Ya ignorado |
| **artifacts/temp/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Archivos temporales (ya en .gitignore) | Bajo | Ya ignorado |
| **artifacts/backups/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Backups (ya en .gitignore) | Bajo | Ya ignorado |
| **backups/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Backups adicionales (ya en .gitignore) | Bajo | Ya ignorado |
| **htmlcov/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Reportes de cobertura HTML (ya en .gitignore) | Bajo | Ya ignorado |
| **infra/infra/** | Directorio | BORRAR_SEGURO | Directorio duplicado (nginx/ssl/) | Bajo | Eliminar tras verificación |
| **infra/vagrant/.vagrant/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Estado de Vagrant runtime | Bajo | Ignorar en .gitignore |
| **src/soar_lab/infrastructure/artifacts/** | Directorio | REVISAR_MANUALMENTE | Archivos generados por scripts (credentials_backup.json, webhook_info.json) | Medio | Revisar si deben ignorarse |
| **src/soar_lab/infrastructure/setup/** | Directorio | CONSERVAR_EN_GIT | Scripts de setup y configuración | Ninguno | Mantener |
| **infra/vagrant/*.sh, *.py** | Archivos | CONSERVAR_EN_GIT | Scripts de Vagrant | Ninguno | Mantener |
| **infra/docker/nginx/ssl/** | Directorio | REVISAR_MANUALMENTE | Certificados SSL (misp.crt, soar.local.crt, soar.local.key, soar.local.pfx) | Medio | Revisar si son generados o versionados |
| **infra/docker/compose/logging/*.json** | Archivos | REVISAR_MANUALMENTE | Dashboards Grafana generados | Bajo | Revisar si deben ignorarse |
| **docs/testing/*.md** | Archivos | REVISAR_MANUALMENTE | Informes de auditoría generados | Bajo | Revisar si deben ignorarse |
| **.env** | Archivo | PROPONER_IGNORAR_AL_FINAL | Variables de entorno con secretos (ya en .gitignore) | Alto | Ya ignorado |
| **.env.full** | Archivo | REVISAR_MANUALMENTE | Variables de entorno completas con secretos | Alto | Revisar si debe ignorarse |
| **.env.example** | Archivo | CONSERVAR_EN_GIT | Plantilla de variables de entorno | Ninguno | Mantener |
| **README.md** | Archivo | NO_TOCAR | Documentación principal | Ninguno | Mantener |
| **LICENSE** | Archivo | NO_TOCAR | Licencia del proyecto | Ninguno | Mantener |
| **Makefile** | Archivo | NO_TOCAR | Comandos Make (Linux/Mac) | Ninguno | Mantener |
| **Makefile.win** | Archivo | NO_TOCAR | Comandos Make (Windows) | Ninguno | Mantener |
| **pyproject.toml** | Archivo | NO_TOCAR | Configuración de proyecto Python | Ninguno | Mantener |
| **pytest.ini** | Archivo | NO_TOCAR | Configuración de pytest | Ninguno | Mantener |
| **requirements-test.txt** | Archivo | NO_TOCAR | Dependencias para testing | Ninguno | Mantener |
| **docker-compose*.yml** | Archivos | NO_TOCAR | Configuración Docker Compose | Ninguno | Mantener |
| **Vagrantfile** | Archivo | NO_TOCAR | Configuración Vagrant | Ninguno | Mantener |
| **.gitignore** | Archivo | NO_TOCAR | Archivos ignorados por git | Ninguno | Mantener |
| **.pytest_cache/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Caché de pytest (ya en .gitignore) | Bajo | Ya ignorado |
| **__pycache__/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Caché de Python (ya en .gitignore) | Bajo | Ya ignorado |
| **.coverage** | Archivo | PROPONER_IGNORAR_AL_FINAL | Archivo de cobertura (ya en .gitignore) | Bajo | Ya ignorado |
| **.idea/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Configuración IDE (ya en .gitignore) | Bajo | Ya ignorado |
| **.vscode/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Configuración IDE (ya en .gitignore) | Bajo | Ya ignorado |
| **.junie/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Configuración IDE (ya en .gitignore) | Bajo | Ya ignorado |
| **.refact/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Configuración IDE (ya en .gitignore) | Bajo | Ya ignorado |
| **nul** | Archivo | PROPONER_IGNORAR_AL_FINAL | Archivo temporal (ya en .gitignore) | Bajo | Ya ignorado |
| **.cache/** | Directorio | PROPONER_IGNORAR_AL_FINAL | Caché general (ya en .gitignore) | Bajo | Ya ignorado |

---

## Resumen por Categoría

### NO_TOCAR (9 items)
- apps/
- src/
- tests/
- infra/
- docs/
- schemas/
- simulator/
- README.md
- LICENSE
- Makefile
- Makefile.win
- pyproject.toml
- pytest.ini
- requirements-test.txt
- docker-compose*.yml
- Vagrantfile
- .gitignore

### CONSERVAR_EN_GIT (3 items)
- src/soar_lab/infrastructure/setup/ (scripts de setup)
- infra/vagrant/*.sh, *.py (scripts de Vagrant)
- .env.example (plantilla de variables de entorno)

### PROPONER_IGNORAR_AL_FINAL (10 items)
- artifacts/data/ (4255 items de datos runtime)
- artifacts/logs/ (ya en .gitignore)
- artifacts/results/ (ya en .gitignore)
- artifacts/coverage/ (ya en .gitignore)
- artifacts/temp/ (ya en .gitignore)
- artifacts/backups/ (ya en .gitignore)
- backups/ (ya en .gitignore)
- htmlcov/ (ya en .gitignore)
- infra/vagrant/.vagrant/ (estado Vagrant)
- .env (ya en .gitignore)

### BORRAR_SEGURO (1 item)
- infra/infra/ (directorio duplicado)

### REVISAR_MANUALMENTE (5 items)
- artifacts/ (contenedor general)
- src/soar_lab/infrastructure/artifacts/ (archivos generados)
- infra/docker/nginx/ssl/ (certificados SSL)
- infra/docker/compose/logging/*.json (dashboards Grafana)
- docs/testing/*.md (informes de auditoría)
- .env.full (variables de entorno con secretos)

---

## Observaciones Críticas

### 1. Datos Runtime Masivos
- `artifacts/data/` contiene 4255 items de datos runtime
- NO está en .gitignore actual
- Debe agregarse a .gitignore al final

### 2. Directorio Duplicado
- `infra/infra/` es un duplicado de `infra/docker/nginx/`
- Puede eliminarse de forma segura

### 3. Certificados SSL
- `infra/docker/nginx/ssl/` contiene certificados
- Deben revisarse si son generados o versionados
- Si son generados, deben ignorarse

### 4. Archivos Generados
- `src/soar_lab/infrastructure/artifacts/` contiene archivos generados
- Deben revisarse si deben ignorarse

### 5. Informes de Auditoría
- `docs/testing/` contiene informes de auditoría generados
- Deben revisarse si deben ignorarse

---

## Conclusión de FASE 1

La estructura del repositorio está bien organizada en general. Los principales problemas identificados son:

1. **Datos runtime masivos no ignorados**: `artifacts/data/` con 4255 items
2. **Directorio duplicado**: `infra/infra/`
3. **Certificados SSL**: Deben revisarse si son generados o versionados
4. **Archivos generados**: Deben clasificarse correctamente

Las carpetas principales (apps/, src/, tests/, infra/, docs/, schemas/, simulator/) deben mantenerse sin cambios.
