# Anexo A

> **Aviso de sincronización.** este anexo es una instantánea estática de la configuración Docker Compose y variables de
> entorno. La versión canónica y actualizada del stack se encuentra en `infra/docker/compose/` (y `.env.example`/`.env.full`).
> En caso de discrepancia, prevalecen los archivos Compose del repositorio.

Este anexo contiene la configuración técnica y código fuente de los componentes principales del laboratorio SOAR para
reproducir el sistema.

## A.1. Configuración Completa de Docker Compose

La configuración Docker Compose define los servicios, redes, volúmenes y dependencias del laboratorio SOAR. La
arquitectura modular permite despliegues desde configuraciones mínimas hasta entornos completos, separando
responsabilidades entre componentes.

### A.1.1. Archivo docker-compose.yml (orquestador principal)

El archivo `docker-compose.yml` es el orquestador principal: define las redes Docker (`soar_net`, `ti_net`, `logging_net`), los volúmenes bind-mount centralizados en `runtime/` y el servicio Elasticsearch. Los servicios de aplicación (TheHive, Cortex, Shuffle, Nginx, etc.) se definen en `docker-compose.core.yml` y los restantes compose files (ver §A.7.1). `make up` combina automáticamente todos los archivos.

```yaml
name: soar-lab

# === SOAR Ransomware Lab - Main Orchestrator ===
# This file defines networks, volumes, and elasticsearch service
#
# Usage:
#   docker compose --env-file ../../.env.full -f compose/docker-compose.yml \
#     -f compose/docker-compose.core.yml -f compose/docker-compose.misp.yml \
#     -f compose/docker-compose.api.yml up -d
#
# Compose files:
#   - compose/docker-compose.yml         (networks, volumes, elasticsearch)
#   - compose/docker-compose.core.yml     (redis, thehive, cortex, shuffle)
#   - compose/docker-compose.misp.yml     (MISP threat intelligence)
#   - compose/docker-compose.api.yml      (API, docs, web-management, nginx)
#   - compose/logging/docker-compose.logging.yml  (Loki, Promtail, Grafana)

networks:
  bridge:
    name: bridge
    external: true
  soar_net:
    name: soar_net
    driver: bridge
    ipam:
      config:
        - subnet: 10.100.0.0/16
  ti_net:
    name: ti_net
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.22.0.0/16
  logging_net:
    name: logging_net
    driver: bridge
    ipam:
      config:
        - subnet: 172.23.0.0/16

volumes:
  es_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${RUNTIME_DIR:-runtime}/data/elasticsearch
  thehive_files:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/thehive/files }
  cortex_data:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/cortex }
  shuffle_apps:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/shuffle/apps }
  shuffle_files:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/shuffle/files }
  redis_data:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/redis }
  nginx_logs:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/logs/nginx }
  misp_db:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/misp/db }
  misp_files:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/misp/files }
  misp_logs:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/logs/misp }
  misp_configs:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/misp/configs }
  loki_data:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/loki }
  grafana_data:
    driver: local
    driver_opts: { type: none, o: bind, device: ${RUNTIME_DIR:-runtime}/data/grafana }

services:
  elasticsearch:
    image: ${ELASTICSEARCH_IMAGE:-docker.elastic.co/elasticsearch/elasticsearch:7.10.2}
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=${ELASTIC_SECURITY_ENABLED:-false}
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - action.auto_create_index=true
      - cluster.routing.allocation.disk.threshold_enabled=false
      - "ES_JAVA_OPTS=${ES_JAVA_OPTS:--Xms2g -Xmx2g -Dlog4j2.formatMsgNoLookups=true}"
    ulimits:
      memlock: { soft: -1, hard: -1 }
      nofile: { soft: 65536, hard: 65536 }
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "${ELASTICSEARCH_PORT:-8200}:9200"
    networks: [soar_net, ti_net]
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS -u elastic:${ELASTIC_PASSWORD} 'http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=10s' || exit 1"]
      interval: 30s
      timeout: 15s
      retries: 10
      start_period: 90s
    restart: unless-stopped
    deploy:
      resources:
        limits: { cpus: '2.0', memory: 4G }
        reservations: { cpus: '1.0', memory: 2G }
    logging:
      driver: "json-file"
      options: { max-size: "10m", max-file: "3" }
```

> **Nota.** Los servicios de aplicación (TheHive, Cortex, Shuffle, Orborus, Redis, Nginx, etc.) se definen en `docker-compose.core.yml` y `docker-compose.api.yml`. El contenido completo de cada compose file está en `infra/docker/compose/`. La sección A.7 proporciona el inventario completo.

### A.1.2. Archivo .env.full

El archivo de entorno `.env.full` contiene todas las variables de configuración necesarias para el despliegue del laboratorio
SOAR. Este archivo permite la personalización del sistema según las necesidades específicas de cada entorno, facilitando
la adaptación a diferentes configuraciones de red, recursos disponibles y requisitos de seguridad. Las variables de
entorno incluyen configuraciones de puertos, credenciales, imágenes Docker y parámetros de red, permitiendo una
configuración modular en el despliegue sin necesidad de modificar los archivos de configuración principales.

```bash
# Project Configuration
COMPOSE_PROJECT_NAME=soar

# Ports — Core SOAR
THEHIVE_HTTP_PORT=8100
CORTEX_HTTP_PORT=8101
SHUFFLE_UI_PORT=8081
SHUFFLE_API_PORT=5001
ELASTICSEARCH_PORT=8200
OPENSEARCH_PORT=8201

# Ports — Management
HTTP_PORT=80
HTTPS_PORT=443
WEB_UI_PORT=8085
API_PORT=8000
DOCS_PORT=8086
MISP_PORT=8083
GRAFANA_PORT=8084

# Elasticsearch
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=<ELASTIC_PASSWORD>
ELASTIC_SECURITY_ENABLED=false
ES_JAVA_OPTS=-Xms2g -Xmx2g

# Shuffle
SHUFFLE_FRONTEND_IMAGE=ghcr.io/shuffle/shuffle-frontend:2.2.1
SHUFFLE_BACKEND_IMAGE=ghcr.io/shuffle/shuffle-backend:2.2.1
SHUFFLE_DEFAULT_USERNAME=admin
SHUFFLE_DEFAULT_PASSWORD=<SHUFFLE_DEFAULT_PASSWORD>
SHUFFLE_DEFAULT_APIKEY=<SHUFFLE_DEFAULT_APIKEY>

# Orborus
ORBORUS_IMAGE=ghcr.io/shuffle/shuffle-orborus:2.2.1-patched

# Docker
DOCKER_API_VERSION=1.44

# Network
OUTER_HOSTNAME=localhost
```

La **Tabla 13** resume las variables de entorno Docker más relevantes para la personalización del despliegue.

## Tabla 13: Variables de Entorno Docker

| Variable               | Valor por Defecto | Descripción              | Requerido |
|------------------------|-------------------|--------------------------|-----------|
| `COMPOSE_PROJECT_NAME` | soar              | Nombre del proyecto      | No        |
| `ELASTIC_PASSWORD`     | Ver `.env.full`   | Contraseña Elasticsearch | Sí        |
| `ELASTIC_SECURITY_ENABLED` | false         | Seguridad Elasticsearch  | No        |
| `THEHIVE_HTTP_PORT`    | 8100              | Puerto TheHive           | No        |
| `CORTEX_HTTP_PORT`     | 8101              | Puerto Cortex            | No        |
| `SHUFFLE_UI_PORT`      | 8081              | Puerto Shuffle UI        | No        |
| `SHUFFLE_API_PORT`     | 5001              | Puerto Shuffle API       | No        |
| `ELASTICSEARCH_PORT`   | 8200              | Puerto Elasticsearch     | No        |
| `HTTP_PORT`            | 80                | Puerto HTTP público      | No        |
| `HTTPS_PORT`           | 443               | Puerto HTTPS público     | No        |
| `WEB_UI_PORT`          | 8085              | Puerto UI gestión        | No        |
| `API_PORT`             | 8000              | Puerto API FastAPI       | No        |
| `GRAFANA_PORT`         | 8084              | Puerto Grafana           | No        |

Las variables de entorno Docker especificadas en esta tabla permiten la personalización del despliegue del laboratorio
SOAR según las necesidades específicas de cada entorno. La única variable obligatoria es `ELASTIC_PASSWORD`, que debe
configurarse con un valor seguro antes del despliegue para proteger elasticsearch. Las variables de puerto permiten
ajustar el despliegue a puertos disponibles en el sistema host, evitando conflictos con otros servicios. La variable
`COMPOSE_PROJECT_NAME` facilita el despliegue de múltiples instancias del laboratorio en el mismo host mediante prefijos
de contenedor distintos. Esta configuración modular posibilita la adopción del laboratorio en
diferentes contextos organizacionales y técnicos.

## A.2. Scripts de Automatización

Los scripts de automatización desarrollados para el laboratorio SOAR ofrecen las capacidades operativas necesarias para
la simulación de incidentes, el cálculo de métricas y la ejecución de acciones de respuesta. Estos scripts representan
la materialización práctica de la automatización SOAR, permitiendo la validación del sistema mediante simulaciones
controladas y ofreciendo las herramientas necesarias para el análisis de rendimiento. Cada script sigue buenas prácticas
de desarrollo software, incluyendo manejo de errores, logging estructurado y documentación completa.

### A.2.1. SIEM Simulator (send_alert.py)

El script SIEM Simulator simula alertas de ransomware con datos realistas y las envía al webhook de Shuffle para su
procesamiento. Este componente es necesario para la validación del sistema, ya que permite generar alertas controladas
que representan escenarios realistas de ransomware sin exponer el sistema a amenazas reales. La implementación incluye
la generación de alertas con IoCs conocidos, soporte para alertas maliciosas y benignas, distribución temporal
configurable para pruebas de carga, validación de esquemas JSON y autenticación mediante API token. Este script se
utiliza extensivamente en las pruebas E2E del sistema para validar el flujo completo de respuesta a incidentes.

```python
#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Alert Sender CLI
Generates and sends alert payloads to the SOAR webhook.
"""

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Send SOAR alert payloads to webhook")
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--num-alerts", type=int, default=1)
    parser.add_argument("--delay", type=int, default=3)
    parser.add_argument("--webhook-url",
                        default=os.environ.get("SHUFFLE_WEBHOOK_URL", ""))
    args = parser.parse_args()

    # Bootstrap dependencies
    base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).parent.parent.parent.parent))
    sys.path.insert(0, str(base_dir / "src"))
    os.environ.setdefault("BASE_DIR", str(base_dir))
    os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

    from soar_lab.simulator.simulate_alerts import generate_malicious_alert, send_alert
    from soar_lab.config.logging import get_logger

    logger = get_logger(__name__)

    num_alerts = 1 if args.single else args.num_alerts
    webhook_url = args.webhook_url

    logger.info(f"Sending {num_alerts} alert(s) to {webhook_url}")

    sent = 0
    failed = 0
    for i in range(1, num_alerts + 1):
        alert = generate_malicious_alert(i)
        ok, status = send_alert(alert, webhook_url)
        if ok:
            sent += 1
            print(f"[{i}/{num_alerts}] Alert sent successfully: {alert.get('alert_id')}")
        else:
            failed += 1
            print(f"[{i}/{num_alerts}] Failed to send alert: HTTP {status}")
            sys.exit(1)

        if i < num_alerts and args.delay > 0:
            time.sleep(args.delay)

    print(f"\nSummary: {sent} sent, {failed} failed")


if __name__ == "__main__":
    main()
```

### A.2.2. KPI Calculator (AnalyticsService)

El script KPI Calculator calcula métricas MTTR desde logs de ejecución del sistema, ofreciendo la base para evaluar la
eficacia de la automatización. Este componente es importante para la validación cuantitativa de los beneficios de SOAR,
permitiendo el análisis estadístico de tiempos de respuesta, el cálculo de percentiles, la exportación de resultados a
CSV y JSON, y la generación de informes de rendimiento. El script implementa algoritmos de análisis de logs
estructurados, extrayendo automáticamente los timestamps de cada etapa del ciclo de respuesta y calculando las
duraciones correspondientes. El análisis de rendimiento permite identificar áreas de mejora y optimizar el sistema.

```python
#!/usr/bin/env python3
"""
SOAR Ransomware Lab - KPI Calculator
Calculates MTTR metrics from workflow execution logs
"""
import re
import csv
import statistics
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/kpi_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
LOG_PATH = Path('logs/notify.log')
RESULTS_PATH = Path('results')
RESULTS_PATH.mkdir(parents=True, exist_ok=True)

class KPICalculator:
    def __init__(self):
        self.log_entries = []
        self.response_times = []
        self.success_rate = 0
        self.error_rate = 0
        
    def parse_log_file(self) -> bool:
        """Parse log file and extract response times"""
        try:
            with open(LOG_PATH, 'r') as f:
                content = f.read()
                
            # Regex pattern to extract timestamps and events
            pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{3}) - (\w+) - (\w+) - (.+)'
            matches = re.findall(pattern, content)
            
            for match in matches:
                timestamp_str, level, component, message = match
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                
                entry = {
                    'timestamp': timestamp,
                    'level': level,
                    'component': component,
                    'message': message
                }
                
                self.log_entries.append(entry)
            
            logger.info(f"Parsed {len(self.log_entries)} log entries")
            return True
            
        except FileNotFoundError:
            logger.error(f"Log file not found: {LOG_PATH}")
            return False
        except Exception as e:
            logger.error(f"Error parsing log file: {e}")
            return False
    
    def calculate_response_times(self) -> List[float]:
        """Calculate response times from log entries"""
        alert_received_times = {}
        case_closed_times = {}
        
        for entry in self.log_entries:
            message = entry['message']
            timestamp = entry['timestamp']
            
            # Extract alert received events
            if 'Alert received' in message:
                alert_id = self.extract_alert_id(message)
                if alert_id:
                    alert_received_times[alert_id] = timestamp
            
            # Extract case closed events
            elif 'Case closed' in message:
                alert_id = self.extract_alert_id(message)
                if alert_id and alert_id in alert_received_times:
                    response_time = (timestamp - alert_received_times[alert_id]).total_seconds()
                    self.response_times.append(response_time)
                    logger.info(f"Alert {alert_id}: {response_time:.2f}s response time")
        
        return self.response_times
    
    def extract_alert_id(self, message: str) -> Optional[str]:
        """Extract alert ID from message"""
        match = re.search(r'ALERT-(\d+)-(\d+)', message)
        if match:
            return f"ALERT-{match.group(1)}-{match.group(2)}"
        return None
    
    def calculate_statistics(self) -> Dict[str, float]:
        """Calculate statistical metrics"""
        if not self.response_times:
            return {}
        
        stats = {
            'mean': statistics.mean(self.response_times),
            'median': statistics.median(self.response_times),
            'min': min(self.response_times),
            'max': max(self.response_times),
            'std_dev': statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0
        }
        
        # Calculate percentiles
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        stats['p50'] = sorted_times[int(n * 0.5)]
        stats['p75'] = sorted_times[int(n * 0.75)]
        stats['p90'] = sorted_times[int(n * 0.9)]
        stats['p95'] = sorted_times[int(n * 0.95)]
        stats['p99'] = sorted_times[int(n * 0.99)]
        
        return stats
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate from log entries"""
        total_alerts = 0
        successful_alerts = 0
        
        for entry in self.log_entries:
            message = entry['message']
            
            if 'Alert received' in message:
                total_alerts += 1
            elif 'Case closed successfully' in message:
                successful_alerts += 1
        
        if total_alerts > 0:
            self.success_rate = (successful_alerts / total_alerts) * 100
            self.error_rate = 100 - self.success_rate
        else:
            self.success_rate = 0
            self.error_rate = 0
        
        return self.success_rate
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive KPI report"""
        # Parse log and calculate metrics
        if not self.parse_log_file():
            return {'error': 'Failed to parse log file'}
        
        response_times = self.calculate_response_times()
        statistics = self.calculate_statistics()
        success_rate = self.calculate_success_rate()
        
        # Generate report
        report = {
            'summary': {
                'total_alerts': len(response_times),
                'success_rate': success_rate,
                'error_rate': self.error_rate,
                'report_generated': datetime.now().isoformat()
            },
            'response_time_metrics': statistics,
            'performance_analysis': self.analyze_performance(statistics),
            'recommendations': self.generate_recommendations(statistics, success_rate)
        }
        
        return report
    
    def analyze_performance(self, stats: Dict[str, float]) -> Dict[str, str]:
        """Analyze performance and provide insights"""
        analysis = {}
        
        if not stats:
            return {'status': 'No data available'}
        
        # MTTR analysis
        mttr = stats.get('mean', 0)
        if mttr < 60:
            analysis['mttr_status'] = 'Excellent'
        elif mttr < 120:
            analysis['mttr_status'] = 'Good'
        elif mttr < 180:
            analysis['mttr_status'] = 'Needs Improvement'
        else:
            analysis['mttr_status'] = 'Poor'
        
        # Consistency analysis
        std_dev = stats.get('std_dev', 0)
        if std_dev < 30:
            analysis['consistency'] = 'High'
        elif std_dev < 60:
            analysis['consistency'] = 'Medium'
        else:
            analysis['consistency'] = 'Low'
        
        # Outlier analysis
        p95 = stats.get('p95', 0)
        max_time = stats.get('max', 0)
        if max_time > p95 * 2:
            analysis['outliers'] = 'Significant outliers detected'
        else:
            analysis['outliers'] = 'Normal distribution'
        
        return analysis
    
    def generate_recommendations(self, stats: Dict[str, float], success_rate: float) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if not stats:
            return ['No data available for analysis']
        
        mttr = stats.get('mean', 0)
        std_dev = stats.get('std_dev', 0)
        
        # MTTR recommendations
        if mttr > 120:
            recommendations.append('Consider optimizing playbook execution to reduce MTTR below 120 seconds')
        elif mttr > 60:
            recommendations.append('Good MTTR performance, but further optimization possible')
        
        # Consistency recommendations
        if std_dev > 60:
            recommendations.append('High variability detected - standardize procedures and improve error handling')
        
        # Success rate recommendations
        if success_rate < 95:
            recommendations.append('Investigate failed executions to improve success rate above 95%')
        elif success_rate < 98:
            recommendations.append('Good success rate, aim for >98% for production readiness')
        
        # Performance recommendations
        p95 = stats.get('p95', 0)
        if p95 > 180:
            recommendations.append('Address outliers affecting P95 response time')
        
        if not recommendations:
            recommendations.append('Excellent performance - consider advanced optimizations and ML integration')
        
        return recommendations
    
    def save_report(self, report: Dict[str, Any], format: str = 'csv') -> Path:
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            filename = f'kpis_{timestamp}.csv'
            filepath = RESULTS_PATH / filename
            
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write summary
                writer.writerow(['Metric', 'Value'])
                for key, value in report['summary'].items():
                    writer.writerow([key, value])
                
                writer.writerow([])
                writer.writerow(['Response Time Metrics', 'Value'])
                for key, value in report['response_time_metrics'].items():
                    writer.writerow([key, value])
        
        elif format == 'json':
            filename = f'kpis_{timestamp}.json'
            filepath = RESULTS_PATH / filename
            
            with open(filepath, 'w') as jsonfile:
                import json
                json.dump(report, jsonfile, indent=2, default=str)
        
        logger.info(f"Report saved to {filepath}")
        return filepath

def main():
    calculator = KPICalculator()
    
    # Generate report
    report = calculator.generate_report()
    
    if 'error' in report:
        logger.error(report['error'])
        return
    
    # Save reports
    csv_file = calculator.save_report(report, 'csv')
    json_file = calculator.save_report(report, 'json')
    
    # Display summary
    print("\n=== SOAR Ransomware Lab - KPI Report ===")
    print(f"Total Alerts: {report['summary']['total_alerts']}")
    print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
    
    if report['response_time_metrics']:
        print(f"Mean MTTR: {report['response_time_metrics']['mean']:.2f}s")
        print(f"Median MTTR: {report['response_time_metrics']['median']:.2f}s")
        print(f"P95 MTTR: {report['response_time_metrics']['p95']:.2f}s")
    
    print("\nPerformance Analysis:")
    for key, value in report['performance_analysis'].items():
        print(f"  {key}: {value}")
    
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    print(f"\nReports saved:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")

if __name__ == '__main__':
    main()
```

## A.3. Plantilla de Caso TheHive

La plantilla de caso TheHive para incidentes de ransomware define la estructura estándar para la documentación forense y
la coordinación de respuesta. Esta plantilla asegura que cada incidente capture la información específica necesaria para
este tipo de amenazas, incluyendo vectores de entrada, variantes identificadas, estado de cifrado, demanda de rescate y
estado de contención. La implementación de campos personalizados permite la captura de información específica de
ransomware que no está disponible en plantillas genéricas, mientras que la definición de fases y tareas establece un
proceso estructurado de respuesta que guía a los analistas a través de las acciones necesarias desde la detección
inicial hasta la recuperación final.

### A.3.1. Plantilla Ransomware (thehive_template.json)

```json
{
  "name": "Ransomware Incident Template",
  "description": "Template for ransomware incident response with automated analysis",
  "version": "1.0",
  "status": "Ok",
  "tags": ["ransomware", "malware", "encryption"],
  "severity": 2,
  "tlp": 2,
  "pap": 2,
  "customFields": [
    {
      "name": "encryption_status",
      "description": "Current encryption status",
      "type": "string",
      "options": ["Not Encrypted", "Partially Encrypted", "Fully Encrypted", "Unknown"],
      "defaultValue": "Unknown"
    },
    {
      "name": "ransomware_variant",
      "description": "Identified ransomware variant",
      "type": "string",
      "options": ["Unknown", "WannaCry", "LockBit", "REvil", "Conti", "Ryuk", "Other"],
      "defaultValue": "Unknown"
    },
    {
      "name": "payment_demand",
      "description": "Ransom payment demand",
      "type": "string",
      "options": ["No Demand", "Bitcoin", "Monero", "Other Cryptocurrency", "Unknown"],
      "defaultValue": "Unknown"
    },
    {
      "name": "data_exfiltrated",
      "description": "Data exfiltration confirmed",
      "type": "boolean",
      "defaultValue": false
    },
    {
      "name": "backup_available",
      "description": "Clean backups available",
      "type": "boolean",
      "defaultValue": false
    },
    {
      "name": "containment_status",
      "description": "Containment actions status",
      "type": "string",
      "options": ["Not Started", "In Progress", "Partially Contained", "Fully Contained"],
      "defaultValue": "Not Started"
    },
    {
      "name": "recovery_time",
      "description": "Estimated recovery time (hours)",
      "type": "number",
      "defaultValue": 0
    },
    {
      "name": "business_impact",
      "description": "Business impact assessment",
      "type": "string",
      "options": ["Low", "Medium", "High", "Critical"],
      "defaultValue": "Unknown"
    }
  ],
  "phases": [
    {
      "name": "Initial Assessment",
      "description": "Initial triage and assessment of the incident",
      "order": 1,
      "tasks": [
        {
          "title": "Verify Alert",
          "description": "Confirm ransomware activity and assess scope",
          "status": "Waiting",
          "order": 1
        },
        {
          "title": "Initial Triage",
          "description": "Classify severity and determine immediate actions",
          "status": "Waiting",
          "order": 2
        },
        {
          "title": "Stakeholder Notification",
          "description": "Notify relevant stakeholders and leadership",
          "status": "Waiting",
          "order": 3
        }
      ]
    },
    {
      "name": "Containment",
      "description": "Immediate containment actions to prevent further spread",
      "order": 2,
      "tasks": [
        {
          "title": "Network Isolation",
          "description": "Isolate affected systems from network",
          "status": "Waiting",
          "order": 1
        },
        {
          "title": "Account Lockdown",
          "description": "Lock affected user accounts",
          "status": "Waiting",
          "order": 2
        },
        {
          "title": "System Shutdown",
          "description": "Shutdown critical systems if necessary",
          "status": "Waiting",
          "order": 3
        }
      ]
    },
    {
      "name": "Investigation",
      "description": "Detailed investigation and analysis",
      "order": 3,
      "tasks": [
        {
          "title": "Malware Analysis",
          "description": "Analyze malware samples and identify variant",
          "status": "Waiting",
          "order": 1
        },
        {
          "title": "IoC Extraction",
          "description": "Extract and analyze indicators of compromise",
          "status": "Waiting",
          "order": 2
        },
        {
          "title": "Timeline Reconstruction",
          "description": "Reconstruct incident timeline",
          "status": "Waiting",
          "order": 3
        },
        {
          "title": "Data Impact Assessment",
          "description": "Assess data encryption and exfiltration",
          "status": "Waiting",
          "order": 4
        }
      ]
    },
    {
      "name": "Recovery",
      "description": "System recovery and restoration",
      "order": 4,
      "tasks": [
        {
          "title": "Backup Verification",
          "description": "Verify backup integrity and availability",
          "status": "Waiting",
          "order": 1
        },
        {
          "title": "System Restoration",
          "description": "Restore systems from clean backups",
          "status": "Waiting",
          "order": 2
        },
        {
          "title": "Data Recovery",
          "description": "Recover encrypted data if possible",
          "status": "Waiting",
          "order": 3
        },
        {
          "title": "System Hardening",
          "description": "Apply security patches and hardening",
          "status": "Waiting",
          "order": 4
        }
      ]
    },
    {
      "name": "Post-Incident",
      "description": "Post-incident activities and lessons learned",
      "order": 5,
      "tasks": [
        {
          "title": "Final Report",
          "description": "Prepare comprehensive incident report",
          "status": "Waiting",
          "order": 1
        },
        {
          "title": "Lessons Learned",
          "description": "Conduct lessons learned session",
          "status": "Waiting",
          "order": 2
        },
        {
          "title": "Security Improvements",
          "description": "Implement security improvements",
          "status": "Waiting",
          "order": 3
        },
        {
          "title": "Case Closure",
          "description": "Close case and archive evidence",
          "status": "Waiting",
          "order": 4
        }
      ]
    }
  ]
}
```

## A.4. Configuración de Monitoreo

### A.4.1. Prometheus Configuration (prometheus.yml)

```yaml
# Prometheus Configuration for SOAR Ransomware Lab
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter for system metrics
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor for container metrics
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # TheHive metrics
  - job_name: 'thehive'
    static_configs:
      - targets: ['thehive:9000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Cortex metrics
  - job_name: 'cortex'
    static_configs:
      - targets: ['cortex:9001']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Shuffle Frontend metrics
  - job_name: 'shuffle-frontend'
    static_configs:
      - targets: ['shuffle-frontend:80']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Shuffle Backend metrics
  - job_name: 'shuffle-backend'
    static_configs:
      - targets: ['shuffle-backend:5001']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Elasticsearch metrics
  - job_name: 'elasticsearch'
    static_configs:
      - targets: ['elasticsearch:9200']
    metrics_path: '/_prometheus/metrics'
    scrape_interval: 30s

  # Nginx metrics
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 30s

  # Docker metrics
  - job_name: 'docker'
    static_configs:
      - targets: ['docker-exporter:9323']
    scrape_interval: 30s

  # Custom SOAR application metrics
  - job_name: 'soar-app'
    static_configs:
      - targets: ['soar-app:8080']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 15s

  # Blackbox exporter for endpoint monitoring
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://nginx/nginx-health
        - http://thehive:9000/api/status
        - http://cortex:9001/api/health
        - http://shuffle-frontend:80/health
        - http://shuffle-backend:5001/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

### A.4.2. Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "id": null,
    "title": "SOAR Ransomware Lab Dashboard",
    "tags": ["soar", "ransomware", "security"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"thehive\"}",
            "legendFormat": "TheHive"
          },
          {
            "expr": "up{job=\"cortex\"}",
            "legendFormat": "Cortex"
          },
          {
            "expr": "up{job=\"shuffle-backend\"}",
            "legendFormat": "Shuffle"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {
                "options": {
                  "0": {
                    "text": "DOWN",
                    "color": "red"
                  },
                  "1": {
                    "text": "UP",
                    "color": "green"
                  }
                },
                "type": "value"
              }
            ]
          }
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "Response Time Distribution",
        "type": "histogram",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(soar_response_time_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(soar_response_time_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 0
        }
      },
      {
        "id": 3,
        "title": "Alert Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(soar_alerts_processed_total[5m])",
            "legendFormat": "Alerts/sec"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 24,
          "x": 0,
          "y": 8
        }
      },
      {
        "id": 4,
        "title": "Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(soar_alerts_successful_total[5m]) / rate(soar_alerts_processed_total[5m]) * 100",
            "legendFormat": "Success Rate %"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 16
        }
      },
      {
        "id": 5,
        "title": "Resource Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_cpu_usage_seconds_total",
            "legendFormat": "{{container_label_com_docker_compose_service}}"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 16
        }
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}
```

## A.5. Guía de Instalación Rápida

### A.5.1. Prerrequisitos

```bash
# System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 8GB+ RAM (16GB+ recomendado)
- 50GB+ SSD (100GB+ recomendado)
- Linux, macOS, or Windows with WSL2

# Software Installation (Ubuntu/Debian)
sudo apt update
sudo apt install -y docker.io docker-compose-plugin python3 python3-pip

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Python dependencies
pip3 install requests jsonschema pytest

# Verify installation
docker --version
docker compose version
python3 --version
```

### A.5.2. Proceso de Instalación

```bash
# 1. Clone repository
git clone https://github.com/your-org/soar-ransomware-lab.git
cd soar-ransomware-lab

# 2. Configure environment
cp .env.example .env.full
nano .env.full  # Edit with your configuration

# 3. Generate TLS certificates
bash scripts/setup/gen_certs.sh

# 4. Start services
make up

# 5. Verify services
make health

# 6. Run initial tests
make simulate-malicious

# 7. Check metrics
make metrics
```

### A.5.3. Verificación de Instalación

```bash
# Check service status
docker compose -f infra/docker/compose/docker-compose.yml ps

# Check logs
docker compose -f infra/docker/compose/docker-compose.yml logs -f

# Test web interfaces (ajustar puertos según .env.full)
curl -f http://localhost:8100/api/status  # TheHive
curl -f http://localhost:8101/api/health  # Cortex
curl -f http://localhost:5001/api/v1/health      # Shuffle
curl -f http://localhost:8200/_cluster/health  # Elasticsearch
```

La **Tabla 14** recopila los comandos Make disponibles para la operación del laboratorio SOAR.

## Tabla 14: Comandos Make Disponibles

| Comando                 | Descripción                 | Uso Típico         |
|-------------------------|-----------------------------|--------------------|
| `make up`               | Iniciar todos los servicios | Despliegue inicial |
| `make down`             | Detener todos los servicios | Mantenimiento      |
| `make health`           | Verificar salud servicios   | Diagnóstico        |
| `make test-all`         | Suite completa de tests     | Validación         |
| `make simulate-malicious` | Enviar alerta maliciosa   | Testing            |
| `make simulate-benign`  | Enviar alerta benigna       | Testing            |
| `make metrics`          | Calcular KPIs               | Análisis           |
| `make backup`           | Crear backup                | Mantenimiento      |
| `make clean`            | Limpiar temporales          | Reset              |
| `make logs`             | Ver logs                    | Depuración         |

Los comandos Make disponibles en esta tabla proporcionan una interfaz simplificada para todas las operaciones comunes
del laboratorio SOAR, reduciendo la complejidad operativa y facilitando la adopción por usuarios con diferentes niveles
de experiencia técnica. Los comandos de despliegue (`make up`, `make down`) simplifican la orquestación de múltiples
servicios Docker. Los comandos de prueba (`make test-all`, `make simulate-malicious`, `make simulate-benign`) facilitan la
validación del sistema sin requerir conocimiento detallado de la configuración de pruebas. Los comandos de
mantenimiento (`make health`, `make backup`, `make clean`, `make logs`) proporcionan las herramientas necesarias para
operación continua. Esta automatización mediante Makefile es un factor determinante en la reproducibilidad y facilidad de uso
del laboratorio.

## A.6. Troubleshooting Común

### A.6.1. Problemas Frecuentes

A continuación se recogen los problemas más frecuentes detectados durante el despliegue y operación del laboratorio, junto con pasos operativos concretos, criterios de verificación y casos de error asociados.

#### 1. Contenedores no inician

**Causas típicas.**

- Docker daemon no está en ejecución.
- Falta de espacio en disco o memoria insuficiente.
- Límites de recursos (`deploy.resources`) superan los disponibles en el host.
- Volúmenes huérfanos de una ejecución anterior en estado inconsistente.

**Pasos operativos.**

```bash
# 1. Verificar el daemon de Docker
sudo systemctl status docker

# 2. Comprobar espacio en disco y memoria libre
df -h
free -h

# 3. Listar contenedores y volúmenes detenidos/huérfanos
docker ps -a
docker volume ls

# 4. Limpiar (solo en desarrollo; conservar .env.full)
docker system prune -f

# 5. Reiniciar Docker si es necesario
sudo systemctl restart docker
```

**Criterio de verificación.**

- `docker ps` muestra el contenedor en estado `Up` o `healthy` tras `make up`.
- `docker compose ps` no reporta `Exit` o `unhealthy` persistentes.

---

#### 2. Elasticsearch/OpenSearch falla o se reinicia continuamente

**Causas típicas.**

- `vm.max_map_count` insuficiente en Linux.
- Permisos incorrectos en los volúmenes de datos.
- Configuración de memoria JVM inadecuada para el host.
- Volcado de heap por falta de RAM.

**Pasos operativos.**

```bash
# 1. Verificar opciones JVM
docker exec soar_elasticsearch env | grep ES_JAVA_OPTS

# 2. Verificar permisos del volumen
ls -la runtime/data/elasticsearch/

# 3. Aumentar el límite de map_count en Linux
sudo sysctl -w vm.max_map_count=262144

# 4. Para Windows/WSL
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
```

**Criterio de verificación.**

- `docker logs soar_elasticsearch` termina con `"Cluster health status changed from [YELLOW] to [GREEN]"`.
- `curl -f http://localhost:8200/_cluster/health` devuelve `status` `green` o `yellow`.

---

#### 3. Conexión entre servicios (DNS/red)

**Causas típicas.**

- Un servicio no se conectó a `soar_net`.
- El `network-watcher` no inyectó entradas `/etc/hosts` en los workers de Shuffle.
- Un servicio arrancó antes de que sus dependencias estuvieran realmente listas.

**Pasos operativos.**

```bash
# 1. Listar redes
docker network ls

# 2. Inspeccionar la red principal
docker network inspect soar-lab_soar_net

# 3. Probar resolución DNS entre contenedores
docker exec soar_thehive nslookup elasticsearch
docker exec soar_shuffle_backend nslookup redis

# 4. Verificar logs del network-watcher
docker logs -f soar_network_watcher

# 5. Reconectar manualmente un worker si falla
WORKER_ID=$(docker ps -q --filter name=worker- | head -1)
docker network connect soar_net $WORKER_ID
docker restart $WORKER_ID
```

**Criterio de verificación.**

- Los `healthcheck` de los servicios afectados pasan.
- `docker exec <contenedor> getent hosts <servicio>` resuelve correctamente.

---

#### 4. Errores E2E en `soar_shuffle-backend`

**Causas típicas.**

- Workflow no creado o trigger no activado.
- `SHUFFLE_DEFAULT_APIKEY` desactualizada tras `make reset && make up`.
- Timeouts por concurrencia insuficiente (`SHUFFLE_ORBORUS_EXECUTION_CONCURRENCY`).

**Pasos operativos.**

```bash
# 1. Verificar estado de Shuffle
docker logs -f soar_shuffle_backend

# 2. Comprobar que el workflow existe y su ID
cat reports/validation/results/webhook_info.json

# 3. Actualizar SHUFFLE_DEFAULT_APIKEY si es necesario
docker exec soar_api cat /app/.env.full | grep SHUFFLE_DEFAULT_APIKEY

# 4. Verificar ejecuciones del workflow desde Shuffle UI o ES
curl http://localhost:8200/users* -u elastic:$ELASTIC_PASSWORD
```

**Criterio de verificación.**

- La ejecución del workflow finaliza con estado `SUCCESS`.
- `pytest tests/e2e/` devuelve 281/281 PASSED (o el total actual del proyecto).

---

#### 5. Grafana no muestra métricas (`soar-metrics` vacío)

**Causas típicas.**

- Plugin Elasticsearch no instalado en Grafana 13.
- Grafana no puede resolver `elasticsearch`.
- Mapping incorrecto del índice (`mttr_seconds` como `object` en lugar de `float`).
- Falta `@timestamp` en los documentos.

**Pasos operativos.**

```bash
# 1. Verificar que Grafana tiene el plugin
docker exec soar_grafana grafana-cli plugins ls | grep elasticsearch

# 2. Comprobar redes de Grafana
docker network inspect soar-lab_logging_net
docker network inspect soar-lab_soar_net

# 3. Verificar mapping del índice
curl http://localhost:8200/soar-metrics-v2/_mapping -u elastic:$ELASTIC_PASSWORD

# 4. Reindexar si es necesario (ver docs/04-operations.md sección logging)
```

**Criterio de verificación.**

- `curl http://localhost:8200/soar-metrics/_count` devuelve documentos.
- Grafana muestra datos en el dashboard KPI.

---

#### 6. MISP DB: error `Permission denied` en operaciones de MariaDB

**Causas típicas.**

- `misp_db` se configura como bind mount en Windows/Docker Desktop.
- Permisos de `rename` sobre bind mounts NTFS.

**Pasos operativos.**

```bash
# 1. Comprobar que misp_db es volumen Docker normal
docker volume ls | grep misp_db

# 2. Si existía un bind mount antiguo, eliminarlo manualmente (Windows)
Remove-Item -Recurse -Force runtime/data/misp/db   # PowerShell

# 3. Recrear volumen
make down -v
make up
```

**Criterio de verificación.**

- `docker inspect soar_misp_db` muestra `"Type": "volume"`.
- `docker compose ps` marca `misp-db` como `healthy`.

---

#### 7. Autenticación JWT / Lab API (`401 Unauthorized`)

**Causas típicas.**

- `API_AUTH_SECRET` / `JWT_SECRET_KEY` no definidos o desfasados.
- Ejemplos con contraseñas por defecto no actualizadas.

**Pasos operativos.**

```bash
# 1. Verificar secretos en .env.full
grep -E 'JWT_SECRET_KEY|API_AUTH_SECRET|WEB_UI_PASSWORD' .env.full

# 2. Probar login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<WEB_UI_PASSWORD>"}'

# 3. Verificar token
export TOKEN=<token>
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/verify
```

**Criterio de verificación.**

- `POST /auth/login` devuelve `200` con `token`.
- `POST /auth/verify` devuelve `{"valid": true, ...}`.

---

#### 8. Certificado SSL de `soar.local` no es confiado

**Causas típicas.**

- Certificado autofirmado no instalado en el almacén de confianza del host.
- Nginx expira el certificado.

**Pasos operativos.**

```bash
# 1. Comprobar validez del certificado
openssl x509 -in infra/docker/config/nginx/ssl/soar.local.crt -noout -dates -subject

# 2. Verificar nginx -t
docker exec soar_nginx nginx -t

# 3. Instalar certificado en Windows
Import-Certificate -FilePath "infra\docker\config\nginx\ssl\soar.local.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

**Criterio de verificación.**

- `nginx -t` devuelve `syntax is ok` / `test is successful`.
- `curl -k https://soar.local` devuelve la página correspondiente.

---

### A.6.2. Criterios generales de aceptación para troubleshooting

1. Se ha identificado la causa raíz del problema.
2. Los pasos documentados son reproducibles en un entorno limpio.
3. Se han recogido evidencias (logs, capturas, salidas de comando) con fecha y entorno.
4. La solución no introduce fugas de secretos ni cambios no versionados en configuraciones canónicas.
5. Tras aplicar la solución, los healthchecks y tests relacionados pasan.

### A.6.3. Logs de Depuración

```bash
# TheHive logs
docker logs soar_thehive -f

# Cortex logs
docker logs soar_cortex -f

# Shuffle logs
docker logs soar_shuffle_backend -f

# Elasticsearch logs
docker logs soar_elasticsearch -f

# Nginx logs
docker logs soar_nginx -f
```

---

## A.7. Inventario Completo de Archivos Docker Compose

El laboratorio SOAR usa **5 archivos Docker Compose** principales (más 1 de logging en subdirectorio)
que se combinan automáticamente con `make up`, totalizando 23 servicios.
La sección A.1.1 muestra el archivo principal (`docker-compose.yml`); los restantes se documentan aquí
como referencia. La versión canónica está en `infra/docker/compose/`.

### A.7.1. Mapa de Archivos Compose

| Archivo | Ubicación | Servicios | Propósito |
|---------|-----------|-----------|-----------|
| `docker-compose.yml` | `infra/docker/compose/` | elasticsearch | Orquestador: redes, volúmenes, Elasticsearch (ver A.1.1) |
| `docker-compose.core.yml` | `infra/docker/compose/` | redis, thehive, cortex, shuffle-frontend, shuffle-backend, network-watcher, tenzir-node, orborus | Servicios SOAR principales |
| `docker-compose.misp.yml` | `infra/docker/compose/` | misp, misp-db, misp-modules | Threat intelligence (MISP) |
| `docker-compose.api.yml` | `infra/docker/compose/` | api, web-management, docs-site, nginx | API FastAPI + UI + docs + proxy |
| `docker-compose.opensearch.yml` | `infra/docker/compose/` | opensearch, opensearch-dashboards | OpenSearch para Shuffle |
| `docker-compose.logging.yml` | `infra/docker/compose/logging/` | loki, promtail, grafana, grafana-db, grafana-renderer | Observabilidad (subdirectorio) |

### A.7.2. Servicios Adicionales (no en A.1.1)

Los siguientes servicios se definen en los compose files adicionales y no aparecen en la
sección A.1.1:

| Servicio | Imagen | Compose File | Función |
|----------|--------|--------------|---------|
| `redis` | `redis:7-alpine` | core | Cache/cola con autenticación |
| `thehive` | `thehiveproject/thehive:3.5.2-1` | core | Gestión de casos |
| `cortex` | build (local) | core | Análisis de IoCs |
| `shuffle-frontend` | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | core | UI Shuffle |
| `shuffle-backend` | `ghcr.io/shuffle/shuffle-backend:2.2.1` | core | Backend Shuffle |
| `network-watcher` | build (local) | core | Diagnóstico/recuperación de red |
| `tenzir-node` | `tenzir/tenzir:v6.8.1` | core | Nodo Tenzir (modo dev) |
| `orborus` | `ghcr.io/shuffle/shuffle-orborus:2.2.1-patched` | core | Orquestador de workers Shuffle |
| `misp` | `ghcr.io/misp/misp-docker/misp-core:v2.5.44` | misp | Threat intelligence |
| `misp-db` | `mariadb:10.11` | misp | BD MISP |
| `misp-modules` | `ghcr.io/misp/misp-docker/misp-modules:v3.0.9` | misp | Módulos MISP |
| `api` | build `apps/api/Dockerfile` | api | API FastAPI (Lab API) |
| `web-management` | build `apps/web-management/Dockerfile` | api | UI de gestión web |
| `docs-site` | build `apps/docs-site/Dockerfile` | api | Docusaurus (docs) |
| `nginx` | `nginx:1.25-alpine` | api | Proxy inverso + TLS |
| `opensearch` | `opensearchproject/opensearch:2.10.0` | opensearch | Motor de búsqueda Shuffle |
| `opensearch-dashboards` | `opensearchproject/opensearch-dashboards:2.10.0` | opensearch | Dashboard OpenSearch |
| `loki` | `grafana/loki:2.9.10` | logging | Agregación de logs |
| `promtail` | `grafana/promtail:2.9.9` | logging | Shipper de logs |
| `grafana` | `grafana/grafana:10.3.4` | logging | Visualización |
| `grafana-db` | `postgres:14-alpine` | logging | BD Grafana |
| `grafana-renderer` | `grafana/grafana-image-renderer:3.10.4` | logging | Renderizado de imágenes para alertas |

### A.7.3. Redes Docker

| Red | CIDR | Tipo | Propósito |
|-----|------|------|-----------|
| `soar_net` | `10.100.0.0/16` | bridge | Red principal del laboratorio |
| `ti_net` | `172.22.0.0/16` | internal | Threat intelligence (sin acceso externo) |
| `logging_net` | `172.23.0.0/16` | bridge | Observabilidad (Loki, Grafana) |
| `bridge` | — | external | Red por defecto Docker (compatibilidad) |

### A.7.4. Resumen del Stack Completo

| Métrica | Valor |
|---------|-------|
| Archivos compose | 5 (+1 logging en subdirectorio) |
| Servicios totales | 23 |
| Redes | 4 (soar_net, ti_net, logging_net + bridge) |
| Volúmenes persistentes | 15 |
| Imágenes Docker | 23 (6 builds locales + 17 pulls) |
| Versiones pinned | 100% (todas las imágenes tienen tag fijo) |

> **Nota.** Para el contenido completo de cada compose file, ver `infra/docker/compose/`.
> Esta sección es un inventario de referencia; el archivo A.1.1 muestra el compose
> principal como ejemplo representativo.

---

**Nota.** Esta documentación técnica complementaria incluye detalles específicos de implementación, configuración y
operación del laboratorio SOAR. Para información adicional sobre conceptos teóricos y metodología, consulte los
capítulos principales del documento.
