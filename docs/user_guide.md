# Guía de Usuario (EDT 8.5)

> Esta guía proporciona instrucciones paso a paso para que los usuarios operen el laboratorio SOAR, desde la configuración inicial hasta la ejecución de escenarios de respuesta a ransomware, con un enfoque académico y formativo.

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración Inicial](#configuración-inicial)
3. [Configuración del Sistema](#configuración-del-sistema)
4. [Ejecución de Escenarios](#ejecución-de-escenarios)
5. [Monitoreo y Resolución de Problemas](#monitoreo-y-resolución-de-problemas)
6. [Uso Avanzado](#uso-avanzado)

---

## Requisitos Previos

### Requisitos del Sistema

**Hardware Mínimo:**
- CPU: 4 núcleos (8+ recomendado)
- RAM: 8GB (16GB+ recomendado)
- Almacenamiento: 50GB SSD (100GB+ recomendado)
- Red: Conexión a internet estable

**Requisitos de Software:**
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.8+ (para scripts)
- Bash 4.0+ (Linux) o PowerShell 5.0+ (Windows)
- Git (para clonar repositorio)

### Requisitos de Red

- Acceso a internet saliente para APIs externas (VirusTotal, URLHaus)
- Puertos 9000-9001, 3001, 5001, 19200 disponibles en el host
- Sin firewall que bloquee la comunicación entre contenedores Docker

---

## Configuración Inicial

### Paso 1: Clonar Repositorio

```bash
git clone https://github.com/your-org/soar-ransomware-lab.git
cd soar-ransomware-lab
```

### Paso 2: Configuración del Entorno

```bash
# Copiar plantilla de entorno
cp docker/.env.example docker/.env

# Editar configuración
nano docker/.env
```

**Elementos de Configuración Críticos:**
- `SHUFFLE_DEFAULT_PASSWORD`: Cambiar del valor predeterminado
- `THEHIVE_API_KEY`: Generar clave única
- `CORTEX_API_KEY`: Generar clave única
- `SIEM_WEBHOOK_TOKEN`: Establecer token de webhook
- `DECISION_SCORE_THRESHOLD`: Ajustar si es necesario (predeterminado: 80)

### Paso 3: Generar Certificados TLS

```bash
# Generar certificados autofirmados
./scripts/gen_certs.sh

# Verificar certificados
ls -la certs/
```

### Paso 4: Iniciar Servicios

```bash
# Iniciar todos los servicios
make up

# Verificar que todos los contenedores estén en ejecución
docker compose ps

# Verificar salud de los servicios
make health
```

La salida esperada debe mostrar todos los servicios como "healthy":
- thehive (running/healthy)
- cortex (running/healthy)
- shuffle-frontend (running/healthy)
- shuffle-backend (running/healthy)
- elasticsearch (running/healthy)

---

## System Configuration

### TheHive Setup

1. **Access TheHive**: Open http://localhost:9000
2. **Initial Login**: Use admin credentials from `.env`
3. **Change Password**: Immediately change default password
4. **Import Template**: 
   ```bash
   # Import ransomware case template
   curl -X POST http://localhost:9000/api/case/template \
     -H "Authorization: Bearer $THEHIVE_API_KEY" \
     -H "Content-Type: application/json" \
     -d @docs/thehive_template.json
   ```

### Cortex Setup

1. **Access Cortex**: Open http://localhost:9001
2. **Initial Configuration**: Create admin user
3. **Configure Analyzers**:
   - HashInfo: Basic hash information
   - VirusTotal: Requires API key (free tier available)
   - URLHaus: URL/domain reputation
   - PassiveTotal: DNS history (requires API key)

### Shuffle Setup

1. **Access Shuffle**: Open http://localhost:3001
2. **Initial Setup**: Create admin account
3. **Configure Apps**:
   - TheHive: API connection
   - Cortex: Analyzer integration
   - Email: SMTP configuration (optional)
   - Slack: Webhook configuration (optional)

4. **Import Workflow**: 
   - Navigate to Workflows
   - Import from `playbooks/shuffle/playbook.json`
   - Configure webhook endpoint: http://localhost:5001/webhook

---

## Running Scenarios

### Scenario 1: Malicious Ransomware Alert

**Objective**: Test complete ransomware response flow with malicious indicators.

**Steps:**

1. **Send Malicious Alert**:
   ```bash
   python3 scripts/send_alert.py --type malicious --single
   ```

2. **Monitor Flow Execution**:
   - Check Shuffle UI for workflow execution
   - Verify case creation in TheHive
   - Monitor analyzer execution in Cortex

3. **Verify Containment**:
   ```bash
   # Check containment logs
   tail -f logs/containment.log
   
   # Verify containment report
   ls -la backups/
   ```

4. **Check Notifications**:
   ```bash
   # View notification logs
   tail -f logs/notify.log
   ```

**Expected Results:**
- Case created in TheHive with "Ransomware" tag
- Analyzers executed (score > 80)
- Containment script executed
- Notifications sent
- MTTR calculated and logged

### Scenario 2: Benign False Positive

**Objective**: Test false positive handling without containment.

**Steps:**

1. **Send Benign Alert**:
   ```bash
   python3 scripts/send_alert.py --type benign --single
   ```

2. **Monitor Flow Execution**:
   - Check Shuffle UI for workflow execution
   - Verify case creation in TheHive
   - Monitor analyzer execution in Cortex

3. **Verify No Containment**:
   ```bash
   # Check that containment was NOT executed
   grep -i "containment" logs/notify.log || echo "No containment - GOOD"
   ```

**Expected Results:**
- Case created in TheHive without "Ransomware" tag
- Analyzers executed (score < 80)
- NO containment script executed
- Case marked as "Observe" or "False Positive"
- Notifications sent

### Scenario 3: Batch Testing

**Objective**: Test system performance with multiple alerts.

**Steps:**

1. **Send Multiple Alerts**:
   ```bash
   python3 scripts/send_alert.py --type malicious --num-alerts 5 --delay 30
   ```

2. **Monitor System Performance**:
   ```bash
   # Monitor resource usage
   docker stats
   
   # Check for bottlenecks
   docker logs soar_shuffle-backend
   ```

3. **Calculate KPIs**:
   ```bash
   # Calculate MTTR metrics
   python3 scripts/calc_kpis.py
   
   # View results
   cat results/kpis.csv
   ```

---

## Monitoring and Troubleshooting

### Service Health Monitoring

**Check All Services**:
```bash
make health
```

**Individual Service Checks**:
```bash
# TheHive
curl -f http://localhost:9000/api/health

# Cortex
curl -f http://localhost:9001/api/health

# Shuffle
curl -f http://localhost:5001/health

# Elasticsearch
curl -f http://localhost:19200/_cluster/health
```

### Log Analysis

**Key Log Files**:
- `logs/notify.log` - Main workflow execution
- `logs/containment.log` - Containment actions
- `docker-compose.log` - Container startup issues

**Log Monitoring**:
```bash
# Real-time monitoring
tail -f logs/notify.log

# Search for errors
grep -i error logs/*.log

# Find specific events
grep "Alert received" logs/notify.log
grep "Containment executed" logs/notify.log
```

### Common Issues and Solutions

**Issue 1: Containers Not Starting**
```bash
# Check Docker status
docker version
docker compose version

# Check port conflicts
netstat -tlnp | grep -E "(9000|9001|3001|5001|19200)"

# Check disk space
df -h
```

**Issue 2: TheHive Cannot Connect to Elasticsearch**
```bash
# Check network connectivity
docker exec soar_thehive wget -qO- http://elasticsearch:9200

# Check Elasticsearch health
docker exec soar_elasticsearch curl -X GET "localhost:9200/_cluster/health"
```

**Issue 3: Cortex Analyzers Failing**
```bash
# Check Cortex configuration
docker exec soar_cortex cat /etc/cortex/application.conf

# Check Docker access in Cortex
docker exec soar_cortex docker ps

# Verify API keys
docker exec soar_cortex env | grep API_KEY
```

**Issue 4: Shuffle Webhook Not Receiving**
```bash
# Test webhook manually
curl -X POST http://localhost:5001/webhook \
  -H "Authorization: Bearer $SIEM_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check Shuffle logs
docker logs soar_shuffle-backend
```

---

## Advanced Usage

### Custom Alert Payloads

Create custom alert scenarios:

```python
# scripts/custom_alert.py
import json
import requests

payload = {
    "alert_id": "CUSTOM-001",
    "hostname": "CUSTOM-HOST",
    "hash": "e3b0c44298fc1c149afbf4c8996fb924",
    "src_ip": "192.168.1.100",
    "severity": 2,
    "event_type": "ransomware_detection",
    "description": "Custom ransomware scenario"
}

response = requests.post(
    "http://localhost:5001/webhook",
    headers={"Authorization": "Bearer TOKEN"},
    json=payload
)
```

### Performance Tuning

**Resource Limits**:
```yaml
# docker/docker-compose.override.yml
services:
  thehive:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

**Analyzer Optimization**:
```bash
# Reduce analyzer timeouts
# Edit Cortex configuration to decrease timeouts from 60s to 30s
```

### Integration with Real SIEM

To integrate with a real SIEM instead of the simulated one:

1. **Configure SIEM Webhook**:
   - Set SIEM to POST to http://your-host:5001/webhook
   - Include required fields: alert_id, hostname, hash, src_ip

2. **Update Authentication**:
   - Update `SIEM_WEBHOOK_TOKEN` in `.env`
   - Configure SIEM to use Bearer token authentication

3. **Test Integration**:
   ```bash
   # Test with real SIEM alert format
   curl -X POST http://localhost:5001/webhook \
     -H "Authorization: Bearer $SIEM_WEBHOOK_TOKEN" \
     -H "Content-Type: application/json" \
     -d @real_siem_alert.json
   ```

### Backup and Recovery

**Backup Configuration**:
```bash
# Backup all data
./scripts/backup.sh

# Backup specific components
tar -czf backup-$(date +%Y%m%d).tar.gz \
  docker/.env \
  certs/ \
  logs/ \
  results/
```

**Restore Configuration**:
```bash
# Restore from backup
./scripts/restore.sh backup-20250503.tar.gz
```

---

## Best Practices

### Security Practices

1. **Regularly Rotate Credentials**:
   - Change API keys every 90 days
   - Update passwords quarterly
   - Rotate TLS certificates annually

2. **Monitor Access Logs**:
   - Review authentication logs weekly
   - Monitor for failed login attempts
   - Set up alerts for suspicious activity

3. **Network Security**:
   - Use firewall to restrict access to management ports
   - Implement VPN access for remote management
   - Regular security updates

### Performance Practices

1. **Resource Monitoring**:
   - Monitor CPU and memory usage
   - Set up alerts for resource exhaustion
   - Regular performance testing

2. **Log Management**:
   - Implement log rotation
   - Archive old logs regularly
   - Monitor disk space usage

3. **Maintenance Schedule**:
   - Weekly container health checks
   - Monthly security updates
   - Quarterly performance reviews

---

## Support and Resources

### Documentation

- **[Technical Guide](technical.md)** - Detailed technical configuration
- **[Architecture Guide](architecture.md)** - System design overview
- **[API Documentation](api.md)** - Integration details
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share experiences
- **Wiki**: Community-contributed guides and tips

### Getting Help

1. **Check Documentation**: Review relevant guides first
2. **Search Issues**: Look for similar problems in GitHub issues
3. **Create Issue**: Include logs, configuration, and steps to reproduce
4. **Community Forum**: Post questions with detailed information

---

## Quick Reference

### Essential Commands

```bash
# Start/Stop Services
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services

# Health Checks
make health      # Check all services
docker compose ps # List containers

# Testing
make test        # Run E2E tests
make metrics     # Calculate KPIs

# Logs
make logs        # View all logs
tail -f logs/notify.log  # Monitor workflow

# Utilities
make clean       # Clean up resources
make backup      # Backup data
```

### Important URLs

- **TheHive**: http://localhost:9000
- **Cortex**: http://localhost:9001
- **Shuffle UI**: http://localhost:3001
- **Shuffle API**: http://localhost:5001
- **Elasticsearch**: http://localhost:19200

### Configuration Files

- **Environment**: `docker/.env`
- **Docker Compose**: `docker/docker-compose.yml`
- **TLS Certificates**: `certs/`
- **Logs**: `logs/`
- **Results**: `results/`

---

**Last Updated**: 2025-05-03  
**Version**: 1.0  
**Compatible with**: SOAR Lab v1.3.0
