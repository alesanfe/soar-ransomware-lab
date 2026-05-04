# Validación del Laboratorio SOAR (EDT 7.x)

> Este documento describe los procedimientos de validación del laboratorio SOAR, incluyendo pruebas unitarias, pruebas de integración y criterios de aceptación para garantizar que el sistema cumple con los requisitos establecidos.

## Tabla de Contenidos

1. [Estrategia de Validación](#estrategia-de-validación)
2. [Pruebas Unitarias](#pruebas-unitarias)
3. [Pruebas de Integración](#pruebas-de-integración)
4. [Pruebas E2E](#pruebas-e2e)
5. [Validación de Rendimiento](#validación-de-rendimiento)
6. [Validación de Seguridad](#validación-de-seguridad)
7. [Criterios de Aceptación](#criterios-de-aceptación)

---

## Estrategia de Validación

### Objetivos de Validación

La validación del laboratorio SOAR tiene como objetivo:

- **Verificar funcionalidad**: Confirmar que todos los componentes funcionan correctamente
- **Validar integraciones**: Asegurar que las integraciones entre servicios operan sin errores
- **Medir rendimiento**: Verificar que los umbrales de MTTR se cumplen
- **Evaluar seguridad**: Confirmar que las medidas de seguridad están implementadas
- **Garantizar reproducibilidad**: Asegurar que el entorno es reproducible

### Matriz de Validación

| Componente | Tipo de Prueba | Frecuencia | Responsable |
|------------|----------------|------------|-------------|
| Scripts Python | Unitarias | Cada cambio | Desarrollador |
| Scripts Bash/PowerShell | Unitarias | Cada cambio | Desarrollador |
| Integración Docker | Integración | Cada despliegue | Desarrollador |
| Flujo E2E | E2E | Cada release | Desarrollador |
| Rendimiento MTTR | Rendimiento | Cada release | Desarrollador |
| Seguridad | Seguridad | Trimestral | Equipo Seguridad |

---

## Pruebas Unitarias

### Scripts Python

#### send_alert.py

**Prueba 1: Generación de alertas maliciosas**
```bash
python3 scripts/send_alert.py --type malicious --single
```

**Criterios:**
- [ ] Alerta generada con hash malicioso
- [ ] IP de origen maliciosa
- [ ] Severidad alta (2 o 3)
- [ ] JSON válido según schema

**Prueba 2: Generación de alertas benignas**
```bash
python3 scripts/send_alert.py --type benign --single
```

**Criterios:**
- [ ] Alerta generada con hash benigno
- [ ] IP de origen benigna
- [ ] Severidad baja (0 o 1)
- [ ] JSON válido según schema

**Prueba 3: Validación de JSON Schema**
```python
import json
import jsonschema

schema = json.load(open('schemas/alert.schema.json'))
alert = json.load(open('tests/payloads/payload_case1.json'))
jsonschema.validate(alert, schema)
```

**Criterios:**
- [ ] Validación exitosa sin errores
- [ ] Todos los campos requeridos presentes
- [ ] Tipos de datos correctos

#### calc_kpis.py

**Prueba 1: Cálculo con datos válidos**
```bash
# Crear log de prueba
echo "[2025-05-03 10:00:00] STEP: Alert received" > logs/notify.log
echo "[2025-05-03 10:01:30] STEP: Containment executed" >> logs/notify.log
python3 scripts/calc_kpis.py
```

**Criterios:**
- [ ] KPIs calculados correctamente
- [ ] p50 = 90s
- [ ] p90 = 90s
- [ ] Archivo kpis.csv generado

**Prueba 2: Cálculo con múltiples ejecuciones**
```bash
# Crear log con múltiples ejecuciones
for i in {1..5}; do
    echo "[$(date -d '+0 seconds' '+%Y-%m-%d %H:%M:%S')] STEP: Alert received" >> logs/notify.log
    echo "[$(date -d '+90 seconds' '+%Y-%m-%d %H:%M:%S')] STEP: Containment executed" >> logs/notify.log
done
python3 scripts/calc_kpis.py
```

**Criterios:**
- [ ] 5 ejecuciones detectadas
- [ ] Estadísticas calculadas correctamente
- [ ] Desviación estándar calculada

### Scripts Bash

#### isolate_host.sh

**Prueba 1: Ejecución en modo simulación**
```bash
./scripts/isolate_host.sh TEST-HOST CASE-12345
```

**Criterios:**
- [ ] Script ejecuta sin errores
- [ ] Logs generados en logs/containment.log
- [ ] Reporte JSON generado en backups/
- [ ] Modo simulación activo

**Prueba 2: Validación de parámetros**
```bash
./scripts/isolate_host.sh
```

**Criterios:**
- [ ] Error por falta de parámetros
- [ ] Mensaje de uso mostrado
- [ ] Exit code = 1

#### notify.sh

**Prueba 1: Notificación de alerta**
```bash
./scripts/notify.sh alert CASE-12345 WIN-001
```

**Criterios:**
- [ ] Notificación enviada (simulada)
- [ ] Log generado en logs/notify.log
- [ ] Timestamp correcto

**Prueba 2: Notificación de error**
```bash
./scripts/notify.sh error CASE-12345 WIN-001 "Test error"
```

**Criterios:**
- [ ] Notificación de error enviada
- [ ] Mensaje de error incluido
- [ ] Log generado

#### gen_certs.sh

**Prueba 1: Generación de certificados**
```bash
./scripts/gen_certs.sh
```

**Criterios:**
- [ ] Directorio certs/ creado
- [ ] Archivo thehive.key generado
- [ ] Archivo thehive.crt generado
- [ ] Archivo shuffle.pem generado
- [ ] Permisos correctos (600 para .key)

### Scripts PowerShell

#### isolate_endpoint.ps1

**Prueba 1: Ejecución en modo simulación**
```powershell
.\scripts\isolate_endpoint.ps1 -Hostname 'WIN-001' -CaseId 'CASE-12345'
```

**Criterios:**
- [ ] Script ejecuta sin errores
- [ ] Logs generados en logs/containment.log
- [ ] Reporte JSON generado
- [ ] Modo simulación activo

---

## Pruebas de Integración

### Integración Docker

**Prueba 1: Inicio de servicios**
```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d
```

**Criterios:**
- [ ] Todos los contenedores iniciados
- [ ] Elasticsearch healthy
- [ ] TheHive healthy
- [ ] Cortex healthy
- [ ] Shuffle healthy
- [ ] Orborus healthy

**Prueba 2: Conectividad entre servicios**
```bash
docker exec soar_thehive wget -qO- http://elasticsearch:9200
docker exec soar_cortex wget -qO- http://thehive:9000
docker exec soar_shuffle-backend wget -qO- http://elasticsearch:9200
```

**Criterios:**
- [ ] TheHive conecta a Elasticsearch
- [ ] Cortex conecta a TheHive
- [ ] Shuffle conecta a Elasticsearch

**Prueba 3: Persistencia de datos**
```bash
# Crear caso en TheHive
# Detener contenedores
docker compose down
# Iniciar contenedores
docker compose up -d
# Verificar caso existe
```

**Criterios:**
- [ ] Datos persisten tras reinicio
- [ ] Volúmenes montados correctamente
- [ ] Sin pérdida de datos

### Integración APIs

**Prueba 1: API TheHive**
```bash
curl -H "Authorization: Bearer $THEHIVE_API_KEY" \
  http://localhost:9000/api/case
```

**Criterios:**
- [ ] Respuesta 200 OK
- [ ] JSON válido
- [ ] Lista de casos retornada

**Prueba 2: API Cortex**
```bash
curl -H "Authorization: Bearer $CORTEX_API_KEY" \
  http://localhost:9001/api/analyzer
```

**Criterios:**
- [ ] Respuesta 200 OK
- [ ] JSON válido
- [ ] Lista de analyzers retornada

**Prueba 3: Webhook Shuffle**
```bash
curl -X POST http://localhost:5001/webhook \
  -H "Authorization: Bearer $SIEM_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d @tests/payloads/payload_case1.json
```

**Criterios:**
- [ ] Respuesta 200 OK
- [ ] Workflow iniciado
- [ ] Caso creado en TheHive

---

## Pruebas E2E

### TC-01: Caso Malicioso

**Objetivo**: Validar el flujo completo para una alerta maliciosa

**Pasos:**
1. Iniciar todos los servicios
2. Enviar alerta maliciosa
3. Verificar caso creado en TheHive
4. Verificar analyzers ejecutados en Cortex
5. Verificar contención ejecutada
6. Verificar notificación enviada
7. Calcular MTTR

**Script de prueba:**
```bash
#!/bin/bash
# tests/e2e/TC-01/test_malicious.sh

echo "=== TC-01: Caso Malicioso ==="

# Enviar alerta maliciosa
python3 scripts/send_alert.py --type malicious --single

# Esperar ejecución del workflow
sleep 30

# Verificar caso en TheHive
curl -H "Authorization: Bearer $THEHIVE_API_KEY" \
  http://localhost:9000/api/case | jq .

# Verificar logs
tail -20 logs/notify.log

# Calcular KPIs
python3 scripts/calc_kpis.py
```

**Criterios de aceptación:**
- [ ] Alerta recibida por Shuffle
- [ ] Caso creado en TheHive con tag "Ransomware"
- [ ] Analyzers ejecutados (score > 80)
- [ ] Contención ejecutada
- [ ] Notificación enviada
- [ ] MTTR ≤ 120s (p50)
- [ ] MTTR ≤ 180s (p90)

### TC-02: Caso Benigno

**Objetivo**: Validar el flujo completo para una alerta benigna

**Pasos:**
1. Iniciar todos los servicios
2. Enviar alerta benigna
3. Verificar caso creado en TheHive
4. Verificar analyzers ejecutados en Cortex
5. Verificar NO contención ejecutada
6. Verificar notificación enviada
7. Calcular MTTR

**Script de prueba:**
```bash
#!/bin/bash
# tests/e2e/TC-02/test_benign.sh

echo "=== TC-02: Caso Benigno ==="

# Enviar alerta benigna
python3 scripts/send_alert.py --type benign --single

# Esperar ejecución del workflow
sleep 30

# Verificar caso en TheHive
curl -H "Authorization: Bearer $THEHIVE_API_KEY" \
  http://localhost:9000/api/case | jq .

# Verificar logs
tail -20 logs/notify.log

# Verificar que NO hubo contención
grep -i "containment" logs/notify.log || echo "No containment - GOOD"
```

**Criterios de aceptación:**
- [ ] Alerta recibida por Shuffle
- [ ] Caso creado en TheHive sin tag "Ransomware"
- [ ] Analyzers ejecutados (score < 80)
- [ ] NO contención ejecutada
- [ ] Caso marcado como "Observe" o "False Positive"
- [ ] Notificación enviada

---

## Validación de Rendimiento

### Métricas MTTR

**Prueba 1: Rendimiento single-thread**
```bash
python3 scripts/send_alert.py --type malicious --single
python3 scripts/calc_kpis.py
```

**Criterios:**
- [ ] p50 ≤ 120s
- [ ] p90 ≤ 180s
- [ ] Media ≤ 150s

**Prueba 2: Rendimiento multi-thread**
```bash
python3 scripts/send_alert.py --type malicious --num-alerts 10 --delay 5
python3 scripts/calc_kpis.py
```

**Criterios:**
- [ ] 10 alertas procesadas
- [ ] p50 ≤ 120s
- [ ] p90 ≤ 180s
- [ ] Sin degradación significativa

### Recursos del Sistema

**Prueba 1: Uso de CPU**
```bash
docker stats --no-stream
```

**Criterios:**
- [ ] CPU ≤ 80% por contenedor
- [ ] Sin picos anormales

**Prueba 2: Uso de memoria**
```bash
docker stats --no-stream
```

**Criterios:**
- [ ] Memoria ≤ límite configurado
- [ ] Sin memory leaks

**Prueba 3: Uso de disco**
```bash
df -h
docker system df
```

**Criterios:**
- [ ] Disco ≥ 20% libre
- [ ] Logs rotados correctamente

---

## Validación de Seguridad

### Validación de Credenciales

**Prueba 1: Sin credenciales por defecto**
```bash
grep "ChangeMe" docker/.env
```

**Criterios:**
- [ ] Sin coincidencias encontradas
- [ ] Todas las credenciales cambiadas

**Prueba 2: Permisos de archivos**
```bash
ls -la docker/.env
ls -la certs/*.key
```

**Criterios:**
- [ ] .env con permisos 600
- [ ] Claves privadas con permisos 600
- [ ] Certificados con permisos 644

### Validación de Red

**Prueba 1: Puertos expuestos**
```bash
netstat -tlnp | grep -E "(9000|9001|3001|5001|19200)"
```

**Criterios:**
- [ ] Solo puertos esperados expuestos
- [ ] Sin puertos inesperados

**Prueba 2: Red interna aislada**
```bash
docker network inspect soar-lab_soar_net
```

**Criterios:**
- [ ] Red marcada como internal
- [ ] Sin exposición al host

### Validación de Contenedores

**Prueba 1: Docker socket read-only**
```bash
docker inspect soar_cortex | grep -A 5 "/var/run/docker.sock"
```

**Criterios:**
- [ ] Mount marcado como :ro
- [ ] Sin acceso de escritura

**Prueba 2: Límites de recursos**
```bash
docker inspect soar_thehive | grep -A 10 "Resources"
```

**Criterios:**
- [ ] Límites de CPU configurados
- [ ] Límites de memoria configurados

---

## Criterios de Aceptación

### Criterios Funcionales

- [ ] **Playbook E2E**: Flujo completo ejecutable sin errores
- [ ] **Integraciones**: Todas las integraciones funcionan correctamente
- [ ] **Scripts**: Todos los scripts ejecutan sin errores
- [ ] **Persistencia**: Datos persisten tras reinicio

### Criterios de Rendimiento

- [ ] **MTTR p50**: ≤ 120 segundos
- [ ] **MTTR p90**: ≤ 180 segundos
- [ ] **Disponibilidad**: ≥ 99% durante pruebas
- [ ] **Recursos**: Uso dentro de límites configurados

### Criterios de Seguridad

- [ ] **Credenciales**: Sin valores por defecto
- [ ] **TLS**: Habilitado y configurado
- [ ] **Permisos**: Correctos en archivos sensibles
- [ ] **Red**: Aislamiento correcto

### Criterios de Calidad

- [ ] **Documentación**: Completa y actualizada
- [ ] **Logs**: Estructurados y con rotación
- [ ] **Errores**: Manejo graceful implementado
- [ ] **Código**: Sin vulnerabilidades críticas

---

## Reporte de Validación

### Plantilla de Reporte

```markdown
# Reporte de Validación - [Fecha]

## Resumen Ejecutivo
- Estado: [PASSED/FAILED]
- Pruebas ejecutadas: X/Y
- Pruebas fallidas: Z
- Tiempo total: X minutos

## Resultados por Categoría

### Pruebas Unitarias
- send_alert.py: [PASSED/FAILED]
- calc_kpis.py: [PASSED/FAILED]
- isolate_host.sh: [PASSED/FAILED]
- notify.sh: [PASSED/FAILED]
- gen_certs.sh: [PASSED/FAILED]

### Pruebas de Integración
- Docker: [PASSED/FAILED]
- APIs: [PASSED/FAILED]

### Pruebas E2E
- TC-01 (Malicioso): [PASSED/FAILED]
- TC-02 (Benigno): [PASSED/FAILED]

### Rendimiento
- MTTR p50: Xs (umbral: 120s) - [PASSED/FAILED]
- MTTR p90: Xs (umbral: 180s) - [PASSED/FAILED]

### Seguridad
- Credenciales: [PASSED/FAILED]
- Red: [PASSED/FAILED]
- Contenedores: [PASSED/FAILED]

## Incidencias Encontradas
1. [Descripción]
2. [Descripción]

## Recomendaciones
1. [Recomendación]
2. [Recomendación]

## Próximos Pasos
- [ ] Acción 1
- [ ] Acción 2
```

---

**Última actualización**: 2025-05-03  
**Versión**: 1.0  
**Responsable**: Equipo de Validación