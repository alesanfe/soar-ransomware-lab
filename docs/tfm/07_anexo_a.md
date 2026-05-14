# Anexo A

## A.1. Configuración Completa de Docker Compose

### A.1.1. Archivo docker-compose.yml

```yaml
version: "3.9"
name: soar-lab

services:
  # === Data layer ===
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.17
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=${ELASTIC_SECURITY_ENABLED:-true}
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - ES_JAVA_OPTS=${ES_JAVA_OPTS:-"-Xms1g -Xmx1g"}
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "${ELASTICSEARCH_PORT:-19200}:9200"
    networks:
      - soar_net
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=5s | grep -q '\"status\":\"green\\|yellow\"' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # === Apps ===
  thehive:
    image: thehiveproject/thehive:3.5.2-1
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_thehive
    depends_on:
      elasticsearch:
        condition: service_healthy
    ports:
      - "${THEHIVE_HTTP_PORT:-9000}:9000"
    volumes:
      - thehive_files:/opt/thp/thehive/files
      - ./thehive.application.conf:/etc/thehive/application.conf:ro
    networks:
      - soar_edge
      - soar_net
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  cortex:
    image: thehiveproject/cortex:3.1.0-1
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_cortex
    depends_on:
      elasticsearch:
        condition: service_healthy
    ports:
      - "${CORTEX_HTTP_PORT:-9001}:9001"
    volumes:
      - cortex_data:/var/lib/cortex
      - ./cortex.application.conf:/etc/cortex/application.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - soar_edge
      - soar_net
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9001/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  shuffle-frontend:
    image: ${SHUFFLE_FRONTEND_IMAGE:-shuffler.io/frontend:1.3.0}
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_shuffle_frontend
    environment:
      BACKEND_HOSTNAME: shuffle-backend
    ports:
      - "${SHUFFLE_UI_PORT:-3001}:3001"
    networks:
      - soar_edge
      - soar_net
    depends_on:
      shuffle-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3001 || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  shuffle-backend:
    image: ${SHUFFLE_BACKEND_IMAGE:-shuffler.io/shuffle:1.3.0}
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_shuffle_backend
    environment:
      SHUFFLE_ELASTIC: "true"
      SHUFFLE_OPENSEARCH_URL: http://elasticsearch:9200
      SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY: "true"
      OUTER_HOSTNAME: ${OUTER_HOSTNAME:-localhost}
      SHUFFLE_APP_HOTLOAD_FOLDER: /shuffle-apps
      SHUFFLE_FILE_LOCATION: /shuffle-files
      SHUFFLE_APP_DOWNLOAD_LOCATION: ${SHUFFLE_APP_DOWNLOAD_LOCATION:-https://github.com/shuffle/python-apps}
      SHUFFLE_DEFAULT_USERNAME: ${SHUFFLE_DEFAULT_USERNAME:-admin}
      SHUFFLE_DEFAULT_PASSWORD: ${SHUFFLE_DEFAULT_PASSWORD:-ChangeMe!}
      SHUFFLE_DEFAULT_APIKEY: ${SHUFFLE_DEFAULT_APIKEY:-changeme-api-key}
      DOCKER_API_VERSION: ${DOCKER_API_VERSION:-1.44}
    volumes:
      - shuffle_app_storage:/shuffle-apps
      - shuffle_file_storage:/shuffle-files
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - "${SHUFFLE_API_PORT:-5001}:5001"
    networks:
      - soar_edge
      - soar_net
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:5001/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  orborus:
    image: ${ORBORUS_IMAGE:-shuffler.io/orborus:1.3.0}
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_orborus
    environment:
      ORG_ID: Shuffle
      ENVIRONMENT_NAME: Shuffle
      BASE_URL: http://shuffle-backend:5001
      DOCKER_API_VERSION: ${DOCKER_API_VERSION:-1.44}
      SHUFFLE_OPENSEARCH_URL: http://elasticsearch:9200
    networks:
      - soar_net
    depends_on:
      shuffle-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://shuffle-backend:5001/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 10
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:1.25-alpine
    container_name: ${COMPOSE_PROJECT_NAME:-soar}_nginx
    ports:
      - "${HTTP_PORT:-80}:80"
      - "${HTTPS_PORT:-443}:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - certs:/etc/ssl/certs:ro
      - certs:/etc/ssl/private:ro
      - nginx_logs:/var/log/nginx
    networks:
      - soar_edge
      - soar_net
    depends_on:
      thehive:
        condition: service_healthy
      cortex:
        condition: service_healthy
      shuffle-frontend:
        condition: service_healthy
      shuffle-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost/nginx-health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  es_data:
  thehive_files:
  cortex_data:
  shuffle_app_storage:
  shuffle_file_storage:
  nginx_logs:
  certs:

networks:
  soar_edge:
    driver: bridge
  soar_net:
    driver: bridge
    internal: true
```

### A.1.2. Archivo .env

```bash
# Project Configuration
COMPOSE_PROJECT_NAME=soar

# Elasticsearch Configuration
ELASTICSEARCH_PORT=19200
ELASTIC_SECURITY_ENABLED=true
ELASTIC_PASSWORD=changeme_elastic_password
ES_JAVA_OPTS=-Xms1g -Xmx1g

# TheHive Configuration
THEHIVE_HTTP_PORT=9000

# Cortex Configuration
CORTEX_HTTP_PORT=9001

# Shuffle Configuration
SHUFFLE_UI_PORT=3001
SHUFFLE_API_PORT=5001
SHUFFLE_FRONTEND_IMAGE=shuffler.io/frontend:1.3.0
SHUFFLE_BACKEND_IMAGE=shuffler.io/shuffle:1.3.0
SHUFFLE_APP_DOWNLOAD_LOCATION=https://github.com/shuffle/python-apps
SHUFFLE_DEFAULT_USERNAME=admin
SHUFFLE_DEFAULT_PASSWORD=ChangeMe!
SHUFFLE_DEFAULT_APIKEY=changeme-api-key

# Orborus Configuration
ORBORUS_IMAGE=shuffler.io/orborus:1.3.0

# Nginx Configuration
HTTP_PORT=80
HTTPS_PORT=443

# Docker Configuration
DOCKER_API_VERSION=1.44

# Network Configuration
OUTER_HOSTNAME=localhost
```

## A.2. Scripts de Automatización

### A.2.1. SIEM Simulator (send_alert.py)

```python
#!/usr/bin/env python3
"""
SOAR Ransomware Lab - SIEM Simulator
Sends simulated ransomware alerts to Shuffle webhook
"""

import json
import os
import time
import argparse
import random
import hashlib
import requests
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/siem_simulator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SIEMSimulator:
    def __init__(self, webhook_url: str, api_token: str) -> None:
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Sample data for realistic simulation
        self.malicious_hashes = [
            '44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f',
            'd41d8cd98f00b204e9800998ecf8427ed41d8cd98f00b204e9800998ecf8427e',
            '098f6bcd4621d373cade4e832627b4f6098f6bcd4621d373cade4e832627b4f6',
            '5d41402abc4b2a76b9719d911017c5925d41402abc4b2a76b9719d911017c592'
        ]
        
        self.benign_hashes = [
            'e3b0c44298fc1c149afbf4c8996fb924e3b0c44298fc1c149afbf4c8996fb924',
            'a665a45920422f9d417e4867efdc4fb8a665a45920422f9d417e4867efdc4fb8',
            '7c222fb2927d828af22f592134e8932480637c0d495eebff1a464e2570f5c440',
            '6b3b8c3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b'
        ]
        
        self.malicious_ips = [
            '192.168.1.100', '10.0.0.50', '172.16.0.25',
            '203.0.113.10', '198.51.100.20'
        ]
        
        self.malicious_domains = [
            'malicious-domain.com', 'ransomware-c2.net',
            'evil-site.org', 'malware-hosting.info'
        ]

    def generate_alert(self, alert_type: str = 'malicious') -> Dict[str, Any]:
        """Generate realistic ransomware alert"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if alert_type == 'malicious':
            hash_value = random.choice(self.malicious_hashes)
            ip_address = random.choice(self.malicious_ips)
            domain = random.choice(self.malicious_domains)
            severity = random.choice(['high', 'critical'])
            confidence = random.uniform(0.8, 1.0)
        else:
            hash_value = random.choice(self.benign_hashes)
            ip_address = f'192.168.1.{random.randint(1, 254)}'
            domain = f'internal-host-{random.randint(1, 100)}.local'
            severity = 'low'
            confidence = random.uniform(0.1, 0.3)
        
        alert = {
            'timestamp': timestamp,
            'alert_id': f'ALERT-{int(time.time())}-{random.randint(1000, 9999)}',
            'source': 'SIEM',
            'event_type': 'ransomware_detection',
            'severity': severity,
            'confidence': confidence,
            'description': f'Ransomware activity detected on endpoint {ip_address}',
            'host': {
                'hostname': f'ENDPOINT-{random.randint(100, 999)}',
                'ip_address': ip_address,
                'os': random.choice(['Windows 10', 'Windows Server 2019', 'Ubuntu 20.04'])
            },
            'file': {
                'name': f'suspicious_file_{random.randint(1, 1000)}.exe',
                'path': f'C:\\Users\\user\\Downloads\\',
                'hash_md5': hash_value[:32],
                'hash_sha256': hash_value,
                'size': random.randint(1024, 10485760)
            },
            'network': {
                'src_ip': ip_address,
                'dst_ip': random.choice(self.malicious_ips),
                'dst_port': random.choice([443, 8080, 9999]),
                'protocol': 'TCP',
                'domain': domain
            },
            'indicators': {
                'file_hashes': [hash_value],
                'ip_addresses': [ip_address],
                'domains': [domain]
            },
            'tags': ['ransomware', 'malware', 'encryption'] if alert_type == 'malicious' else ['false_positive']
        }
        
        return alert

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert to Shuffle webhook"""
        try:
            response = requests.post(
                self.webhook_url,
                headers=self.headers,
                json=alert,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Alert {alert['alert_id']} sent successfully")
                return True
            else:
                logger.error(f"Failed to send alert {alert['alert_id']}: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending alert {alert['alert_id']}: {e}")
            return False

    def run_batch(self, num_alerts: int, alert_type: str, delay: float = 1.0) -> Dict[str, int]:
        """Send batch of alerts"""
        results = {'success': 0, 'failed': 0}
        
        logger.info(f"Starting batch: {num_alerts} {alert_type} alerts")
        
        for i in range(num_alerts):
            alert = self.generate_alert(alert_type)
            success = self.send_alert(alert)
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            if delay > 0 and i < num_alerts - 1:
                time.sleep(delay)
        
        logger.info(f"Batch completed: {results['success']} successful, {results['failed']} failed")
        return results

def main():
    parser = argparse.ArgumentParser(description='SOAR Ransomware Lab - SIEM Simulator')
    parser.add_argument('--type', choices=['malicious', 'benign'], default='malicious',
                       help='Type of alerts to generate')
    parser.add_argument('--num-alerts', type=int, default=1,
                       help='Number of alerts to send')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between alerts in seconds')
    parser.add_argument('--single', action='store_true',
                       help='Send single alert and exit')
    
    args = parser.parse_args()
    
    # Configuration from environment
    webhook_url = os.getenv('SHUFFLE_WEBHOOK_URL', 'http://localhost:5001/api/v1/hooks/webhook')
    api_token = os.getenv('SHUFFLE_API_TOKEN', 'changeme-api-key')
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    # Initialize simulator
    simulator = SIEMSimulator(webhook_url, api_token)
    
    # Run simulation
    if args.single:
        alert = simulator.generate_alert(args.type)
        simulator.send_alert(alert)
    else:
        simulator.run_batch(args.num_alerts, args.type, args.delay)

if __name__ == '__main__':
    main()
```

### A.2.2. KPI Calculator (calc_kpis.py)

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
      - targets: ['shuffle-frontend:3001']
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
      - targets: ['elasticsearch:19200']
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
        - http://thehive:9000/api/health
        - http://cortex:9001/api/health
        - http://shuffle-frontend:3001/health
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
- Python 3.8+
- 8GB+ RAM (16GB+ recomendado)
- 50GB+ SSD (100GB+ recomendado)
- Linux, macOS, or Windows with WSL2

# Software Installation (Ubuntu/Debian)
sudo apt update
sudo apt install -y docker.io docker-compose python3 python3-pip

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Python dependencies
pip3 install requests jsonschema pytest

# Verify installation
docker --version
docker-compose --version
python3 --version
```

### A.5.2. Proceso de Instalación

```bash
# 1. Clone repository
git clone https://github.com/your-org/soar-ransomware-lab.git
cd soar-ransomware-lab

# 2. Configure environment
cp docker/.env.example docker/.env
nano docker/.env  # Edit with your configuration

# 3. Generate TLS certificates
./scripts/gen_certs.sh

# 4. Start services
make up

# 5. Verify services
make health

# 6. Run initial tests
make test-malicious

# 7. Check metrics
make metrics
```

### A.5.3. Verificación de Instalación

```bash
# Check service status
docker compose -f docker/docker-compose.yml ps

# Check logs
docker compose -f docker/docker-compose.yml logs -f

# Test web interfaces
curl -f http://localhost:9000/api/health  # TheHive
curl -f http://localhost:9001/api/health  # Cortex
curl -f http://localhost:5001/health      # Shuffle
curl -f http://localhost:19200/_cluster/health  # Elasticsearch
```

## A.6. Troubleshooting Común

### A.6.1. Problemas Frecuentes

**Problema: Contenedores no inician**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check disk space
df -h

# Check memory usage
free -h

# Restart Docker
sudo systemctl restart docker
```

**Problema: Elasticsearch falla**
```bash
# Check JVM memory settings
docker exec soar_elasticsearch env | grep ES_JAVA_OPTS

# Check disk permissions
ls -la docker/volumes/

# Increase virtual memory
sudo sysctl -w vm.max_map_count=262144
```

**Problema: Conexión entre servicios**
```bash
# Check network configuration
docker network ls
docker network inspect soar-lab_soar_net

# Check DNS resolution
docker exec soar_thehive nslookup elasticsearch
```

### A.6.2. Logs de Depuración

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

**Nota**: Esta documentación técnica complementaria proporciona detalles específicos de implementación, configuración y operación del laboratorio SOAR. Para información adicional sobre conceptos teóricos y metodología, consulte los capítulos principales del documento.
