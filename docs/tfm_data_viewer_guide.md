# Guía del Visualizador de Datos TFM

## Overview

El sistema de visualización de datos del TFM permite mostrar por terminal todos los datos que se pueden obtener de los placeholders del documento `13_visualizaciones_datos.md` cuando estén disponibles.

## Componentes del Sistema

### 1. TFM Data Viewer (`scripts/tfm_data_viewer.py`)

Script principal para visualizar datos del TFM por terminal.

**Características:**
- Extrae automáticamente todos los placeholders del documento TFM
- Calcula métricas reales desde logs y resultados de tests
- Muestra datos por categorías (MTTR, tasas de éxito, costos, etc.)
- Monitoreo en tiempo real de cambios
- Exportación de datos a JSON

### 2. TFM Data Enhancer (`scripts/tfm_data_enhancer.py`)

Script para generar datos reales ejecutando tests y escenarios.

**Características:**
- Ejecuta escenarios de tests E2E
- Envía alertas de prueba para generar datos
- Calcula KPIs con datos reales
- Genera reportes comprehensivos
- Prepara datos para el visualizador

## Instalación y Configuración

### Prerrequisitos

```bash
# Asegurarse de tener Python 3.8+
python3 --version

# Instalar dependencias
pip install requests python-dotenv
```

### Permisos de Ejecución

```bash
# Hacer ejecutables los scripts
chmod +x scripts/tfm_data_viewer.py
chmod +x scripts/tfm_data_enhancer.py
```

## Uso del Visualizador de Datos

### Comandos Básicos

#### 1. Mostrar Estado de Placeholders

```bash
python scripts/tfm_data_viewer.py --status
```

Muestra qué placeholders tienen datos disponibles y cuáles no.

#### 2. Mostrar Todos los Datos Disponibles

```bash
python scripts/tfm_data_viewer.py --all
```

Despliega todas las métricas calculadas organizadas por categorías.

#### 3. Mostrar Placeholder Específico

```bash
python scripts/tfm_data_viewer.py --placeholder total_time_soaR
```

Muestra el valor de un placeholder específico.

#### 4. Monitorear Cambios en Tiempo Real

```bash
python scripts/tfm_data_viewer.py --watch --interval 5
```

Monitorea cambios en los datos cada 5 segundos.

#### 5. Exportar Datos a JSON

```bash
python scripts/tfm_data_viewer.py --export
```

Exporta todos los datos disponibles a un archivo JSON.

### Ejemplos de Salida

#### Estado de Placeholders

```
📋 ESTADO DE PLACEHOLDERS
============================================================
✅ total_time_soaR: 95.5
✅ p50_soaR: 85.2
✅ p90_soaR: 120.8
❌ p95_soaR: No disponible
✅ success_rate_soaR: 100.0%

📊 Resumen: 45/120 placeholders disponibles (37.5%)
```

#### Datos por Categorías

```
📊 DATOS DEL TFM DISPONIBLES
============================================================

🕒 TIEMPOS DE RESPUESTA (MTTR)
----------------------------------------------
  total_time_manual: 480.0
  total_time_soaR: 95.5
  p50_manual: 420.0
  p50_soaR: 85.2
  p90_manual: 600.0
  p90_soaR: 120.8

📈 PORCENTAJES DE REDUCCIÓN
----------------------------------------------
  reception_reduction: 80.1%
  analysis_reduction: 79.8%
  creation_reduction: 82.3%
  containment_reduction: 81.2%

🎯 TASAS DE ÉXITO
----------------------------------------------
  success_rate_manual: 75.0
  success_rate_soaR: 100.0
  malicious_soaR: 100.0
  benign_soaR: 100.0

💰 MÉTRICAS DE COSTO
----------------------------------------------
  cost_manual: 2500.0
  cost_soaR: 800.0
  roi_improvement: 68.0
  mttr_reduction: 80.1%
```

## Generación de Datos Reales

### Uso del Data Enhancer

#### 1. Generación Completa de Datos

```bash
python scripts/tfm_data_enhancer.py --complete
```

Ejecuta el proceso completo:
- Escenarios de tests E2E
- Envío de alertas de prueba
- Cálculo de KPIs
- Generación de reportes

#### 2. Ejecutar Escenarios de Tests

```bash
python scripts/tfm_data_enhancer.py --scenarios
```

Ejecuta los tres escenarios principales:
- TC-01: Malicious
- TC-02: Benign
- TC-03: Edge Cases

#### 3. Enviar Alertas de Prueba

```bash
python scripts/tfm_data_enhancer.py --alerts 10
```

Envía 10 alertas de prueba (5 maliciosas, 5 benignas).

#### 4. Calcular KPIs

```bash
python scripts/tfm_data_enhancer.py --kpis
```

Calcula KPIs desde los logs disponibles.

#### 5. Verificar Estado del Sistema

```bash
python scripts/tfm_data_enhancer.py --status
```

Muestra el estado de archivos y servicios.

## Flujo de Trabajo Recomendado

### 1. Preparación del Entorno

```bash
# Iniciar servicios SOAR
make up

# Verificar que los servicios estén funcionando
make health
```

### 2. Generación de Datos

```bash
# Generar datos completos
python scripts/tfm_data_enhancer.py --complete
```

### 3. Visualización de Resultados

```bash
# Ver estado de placeholders
python scripts/tfm_data_viewer.py --status

# Ver todos los datos disponibles
python scripts/tfm_data_viewer.py --all
```

### 4. Monitoreo Continuo

```bash
# Monitorear cambios en tiempo real
python scripts/tfm_data_viewer.py --watch
```

## Categorías de Datos Disponibles

### 🕒 Tiempos de Respuesta (MTTR)

- `total_time_manual`: Tiempo total manual (baseline: 480s)
- `total_time_soaR`: Tiempo total SOAR (calculado desde logs)
- `p50_manual`, `p50_soaR`: Medianas de MTTR
- `p90_manual`, `p90_soaR`: Percentil 90 de MTTR
- `p95_manual`, `p95_soaR`: Percentil 95 de MTTR

### 📈 Porcentajes de Reducción

- `reception_reduction`: Reducción en recepción/triaje
- `analysis_reduction`: Reducción en análisis de IoCs
- `creation_reduction`: Reducción en creación de casos
- `containment_reduction`: Reducción en contención
- `p50_reduction`, `p90_reduction`: Reducciones de percentiles

### 🎯 Tasas de Éxito

- `success_rate_manual`: Tasa éxito manual (baseline: 75%)
- `success_rate_soaR`: Tasa éxito SOAR (calculada desde tests)
- `malicious_soaR`: Tasa éxito en alertas maliciosas
- `benign_soaR`: Tasa éxito en alertas benignas
- `total_soaR`: Tasa éxito total

### 💰 Métricas de Costo

- `cost_manual`: Costo por incidente manual (baseline: $2500)
- `cost_soaR`: Costo por incidente SOAR (calculado: $800)
- `roi_improvement`: Mejora en ROI (calculada: 68%)
- `mttr_reduction`: Reducción general de MTTR

## Archivos Generados

### Archivos de Resultados

```
results/
├── tfm_comprehensive_report_YYYYMMDD_HHMMSS.json  # Reporte completo
├── tfm_viewer_data.json                           # Datos para visualizador
├── kpis.csv                                       # KPIs calculados
└── tfm_data_YYYYMMDD_HHMMSS.json                 # Exportación de datos
```

### Archivos de Logs

```
logs/
├── notify.log                                     # Logs de ejecución
├── containment.log                               # Logs de contención
└── siem_simulator.log                            # Logs del simulador SIEM
```

## Troubleshooting

### Problemas Comunes

#### 1. "No se encuentran los archivos de logs"

**Solución:**
```bash
# Verificar que los logs existan
ls -la logs/

# Generar datos si no existen
python scripts/tfm_data_enhancer.py --complete
```

#### 2. "Los servicios no están disponibles"

**Solución:**
```bash
# Iniciar servicios
make up

# Verificar estado
make health

# Revisar logs
make logs
```

#### 3. "Los placeholders no tienen datos"

**Solución:**
```bash
# Ejecutar tests para generar datos
python scripts/tfm_data_enhancer.py --scenarios

# Enviar alertas de prueba
python scripts/tfm_data_enhancer.py --alerts 5

# Calcular KPIs
python scripts/tfm_data_enhancer.py --kpis
```

#### 4. "Error de permisos"

**Solución:**
```bash
# Dar permisos de ejecución
chmod +x scripts/tfm_data_viewer.py
chmod +x scripts/tfm_data_enhancer.py

# Verificar permisos de directorios
chmod 755 results/ logs/
```

### Depuración

#### Modo Verbose

```bash
# Ejecutar con logging detallado
python -v scripts/tfm_data_viewer.py --all

# Ver logs del sistema
tail -f logs/notify.log
```

#### Verificación de Datos

```bash
# Verificar archivos de datos
cat results/kpis.csv
cat results/tfm_viewer_data.json

# Verificar logs recientes
tail -20 logs/notify.log
```

## Integración con Makefile

### Comandos Adicionales para Makefile

```makefile
# TFM Data Commands
tfm-status:
	python3 scripts/tfm_data_viewer.py --status

tfm-data:
	python3 scripts/tfm_data_enhancer.py --complete

tfm-view:
	python3 scripts/tfm_data_viewer.py --all

tfm-watch:
	python3 scripts/tfm_data_viewer.py --watch

tfm-export:
	python3 scripts/tfm_data_viewer.py --export
```

### Uso con Makefile

```bash
# Ver estado de datos TFM
make data-status

# Generar datos completos
make data-generate

# Ver todos los datos
make data-view

# Monitorear cambios
make data-watch
```

## Automatización

### Script de Automatización

```bash
#!/bin/bash
# auto_tfm_data.sh

echo "🔄 Generando datos TFM automáticamente..."

# 1. Verificar servicios
make health

# 2. Generar datos
python scripts/tfm_data_enhancer.py --complete

# 3. Mostrar resultados
python scripts/tfm_data_viewer.py --all

# 4. Monitorear por 5 minutos
timeout 300 python scripts/tfm_data_viewer.py --watch --interval 10

echo "✅ Proceso completado"
```

### Cron Job para Actualización Automática

```bash
# Agregar al crontab para ejecución cada hora
0 * * * * cd /path/to/soar-ransomware-lab && ./auto_tfm_data.sh
```

## Mejores Prácticas

### 1. Ejecución Ordenada

1. Iniciar servicios (`make up`)
2. Verificar salud (`make health`)
3. Generar datos (`--complete`)
4. Visualizar resultados (`--all`)
5. Monitorear si es necesario (`--watch`)

### 2. Validación de Datos

```bash
# Siempre verificar estado después de generar datos
python scripts/tfm_data_viewer.py --status

# Verificar KPIs específicos
python scripts/tfm_data_viewer.py --placeholder p90_soaR
```

### 3. Documentación de Resultados

```bash
# Exportar datos para documentación
python scripts/tfm_data_viewer.py --export

# Generar timestamp para referencia
date "+%Y-%m-%d %H:%M:%S"
```

### 4. Limpieza de Datos Antiguos

```bash
# Limpiar resultados antiguos (mantener últimos 7 días)
find results/ -name "tfm_*.json" -mtime +7 -delete
find results/ -name "*report*.json" -mtime +7 -delete
```

## Soporte y Ayuda

### Obtener Ayuda

```bash
# Ayuda del visualizador
python scripts/tfm_data_viewer.py --help

# Ayuda del enhancer
python scripts/tfm_data_enhancer.py --help
```

### Reporte de Problemas

Si encuentras problemas:

1. Verifica el estado del sistema con `--status`
2. Revisa los logs en `logs/`
3. Ejecuta con modo verbose si es necesario
4. Documenta los pasos reproducibles

### Comunidad y Contribuciones

- Contribuciones welcome en el repositorio
- Reportar issues con logs completos
- Sugerir mejoras en los scripts

---

**Última Actualización**: 2025-05-04  
**Versión**: 1.0  
**Compatible con**: SOAR Lab v1.3.0+
