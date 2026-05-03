# Guía de Resolución de Problemas (EDT 8.6)

> Esta guía proporciona soluciones a los problemas comunes encontrados al operar el laboratorio SOAR, con procedimientos de diagnóstico paso a paso y estrategias de resolución, diseñada para entornos académicos y formativos.

## Tabla de Contenidos

1. [Problemas de Inicio de Servicios](#problemas-de-inicio-de-servicios)
2. [Red y Conectividad](#red-y-conectividad)
3. [Problemas de Autenticación](#problemas-de-autenticación)
4. [Problemas de Rendimiento](#problemas-de-rendimiento)
5. [Datos y Almacenamiento](#datos-y-almacenamiento)
6. [Fallos de Integración](#fallos-de-integración)
7. [Errores de Ejecución de Scripts](#errores-de-ejecución-de-scripts)
8. [Herramientas de Depuración](#herramientas-de-depuración)

---

## Problemas de Inicio de Servicios

### Problema: Docker Compose Falla al Iniciar

**Síntomas:**
- `docker compose up` falla con errores de permisos
- Los servicios no pueden vincularse a puertos
- Errores de creación de contenedores

**Pasos de Diagnóstico:**
```bash
# Verificar estado del demonio Docker
sudo systemctl status docker

# Verificar permisos de Docker
docker run hello-world

# Verificar versión de Docker Compose
docker compose version

# Verificar sintaxis YAML
docker compose config
```

**Soluciones:**

1. **Corregir Permisos de Docker:**
   ```bash
   # Agregar usuario al grupo docker
   sudo usermod -aG docker $USER
   
   # Cerrar sesión y volver a iniciar
   # o usar newgrp docker
   newgrp docker
   ```

2. **Corregir Conflictos de Puertos:**
   ```bash
   # Verificar uso de puertos
   netstat -tlnp | grep -E "(9000|9001|3001|5001|19200)"
   
   # Matar procesos en conflicto
   sudo kill -9 <PID>
   
   # O cambiar puertos en .env
   nano docker/.env
   ```

3. **Corregir Problemas de Volúmenes:**
   ```bash
   # Verificar espacio en disco
   df -h
   
   # Limpiar volúmenes no utilizados
   docker volume prune -f
   
   # Eliminar contenedores huérfanos
   docker container prune -f
   ```

### Problem: Elasticsearch Fails to Start

**Symptoms:**
- Elasticsearch container exits immediately
- "vm.max_map_count" error
- Memory allocation errors

**Diagnostic Steps:**
```bash
# Check Elasticsearch logs
docker logs soar_elasticsearch

# Check system limits
sysctl vm.max_map_count

# Check available memory
free -h
```

**Solutions:**

1. **Increase Virtual Memory:**
   ```bash
   # Temporary fix
   sudo sysctl -w vm.max_map_count=262144
   
   # Permanent fix
   echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
   ```

2. **Adjust Memory Settings:**
   ```bash
   # Edit docker-compose.yml
   # Reduce ES_HEAP_SIZE in environment variables
   nano docker/docker-compose.yml
   ```

### Problem: TheHive Cannot Connect to Elasticsearch

**Symptoms:**
- TheHive container restarts repeatedly
- Connection refused errors
- "Unable to connect to Elasticsearch" logs

**Diagnostic Steps:**
```bash
# Check network connectivity
docker exec soar_thehive wget -qO- http://elasticsearch:9200

# Check Elasticsearch health
docker exec soar_elasticsearch curl -X GET "localhost:9200/_cluster/health"

# Check network configuration
docker network inspect soar-lab_soar_net
```

**Solutions:**

1. **Fix Network Configuration:**
   ```bash
   # Recreate network
   docker network rm soar-lab_soar_net
   docker compose down
   docker compose up -d
   ```

2. **Check Service Dependencies:**
   ```bash
   # Ensure Elasticsearch starts first
   docker compose up -d elasticsearch
   sleep 30
   docker compose up -d thehive
   ```

---

## Network and Connectivity

### Problem: Webhook Not Receiving Alerts

**Symptoms:**
- SIEM alerts not triggering playbook
- HTTP 401/403 errors
- Connection timeout errors

**Diagnostic Steps:**
```bash
# Test webhook manually
curl -X POST http://localhost:5001/webhook \
  -H "Authorization: Bearer $SIEM_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' -v

# Check Shuffle logs
docker logs soar_shuffle-backend

# Check port exposure
netstat -tlnp | grep 5001
```

**Solutions:**

1. **Fix Authentication:**
   ```bash
   # Verify token in .env
   grep SIEM_WEBHOOK_TOKEN docker/.env
   
   # Update Shuffle configuration
   docker restart soar_shuffle-backend
   ```

2. **Fix Port Exposure:**
   ```bash
   # Check docker-compose.yml port mapping
   grep -A 5 -B 5 "5001:" docker/docker-compose.yml
   
   # Restart with correct mapping
   docker compose down
   docker compose up -d
   ```

### Problem: External API Failures

**Symptoms:**
- VirusTotal analyzer timeouts
- URLHaus connection errors
- PassiveTotal rate limit errors

**Diagnostic Steps:**
```bash
# Test external connectivity
curl -I https://www.virustotal.com

# Check API keys
grep VIRUSTOTAL_API_KEY docker/.env
grep URLHAUS_API_KEY docker/.env

# Test API access
curl -X GET "https://www.virustotal.com/vtapi/v2/file/report?apikey=$VIRUSTOTAL_API_KEY&resource=e3b0c44298fc1c149afbf4c8996fb924"
```

**Solutions:**

1. **Fix API Keys:**
   ```bash
   # Generate new API keys
   # Update .env file
   nano docker/.env
   
   # Restart Cortex
   docker restart soar_cortex
   ```

2. **Handle Rate Limits:**
   ```bash
   # Increase timeouts in Cortex configuration
   docker exec soar_cortex nano /etc/cortex/application.conf
   
   # Implement retry logic in analyzers
   ```

---

## Authentication Problems

### Problem: Invalid API Keys

**Symptoms:**
- 401 Unauthorized errors
- "Invalid API key" messages
- Authentication failures in logs

**Diagnostic Steps:**
```bash
# Check API key format
grep -E "_API_KEY" docker/.env

# Test API key validity
curl -H "Authorization: Bearer $THEHIVE_API_KEY" \
  http://localhost:9000/api/case

# Check token length and format
echo $THEHIVE_API_KEY | wc -c
```

**Solutions:**

1. **Regenerate API Keys:**
   ```bash
   # Generate new secure keys
   openssl rand -hex 32
   
   # Update .env with new keys
   nano docker/.env
   
   # Restart affected services
   docker compose restart
   ```

2. **Fix Token Format:**
   ```bash
   # Ensure tokens are properly formatted
   # No special characters, proper length
   # Store securely in .env
   ```

### Problem: TheHive Login Issues

**Symptoms:**
- Cannot access TheHive UI
- Default credentials not working
- Password reset failures

**Diagnostic Steps:**
```bash
# Check TheHive logs
docker logs soar_thehive

# Verify database connection
docker exec soar_thehive curl -X GET "http://elasticsearch:9200/_cluster/health"

# Check initial setup
docker exec soar_thehive ls -la /etc/thehive/application.conf
```

**Solutions:**

1. **Reset Admin Password:**
   ```bash
   # Access TheHive container
   docker exec -it soar_thehive bash
   
   # Reset password (if available)
   /opt/thehive/bin/thehive reset-password
   ```

2. **Reinitialize TheHive:**
   ```bash
   # Stop services
   docker compose down
   
   # Remove volumes (WARNING: data loss)
   docker volume rm soar-lab_es_data
   
   # Restart services
   docker compose up -d
   ```

---

## Performance Issues

### Problem: Slow Response Times

**Symptoms:**
- MTTR exceeding thresholds
- Analyzer timeouts
- UI sluggishness

**Diagnostic Steps:**
```bash
# Check system resources
docker stats
top
free -h

# Check service response times
time curl http://localhost:9000/api/health
time curl http://localhost:9001/api/health

# Analyze logs for bottlenecks
grep -i timeout logs/*.log
```

**Solutions:**

1. **Optimize Resource Allocation:**
   ```bash
   # Increase container limits
   # Edit docker-compose.yml
   nano docker/docker-compose.yml
   
   # Add resource limits
   deploy:
     resources:
       limits:
         cpus: '2.0'
         memory: 4G
   ```

2. **Optimize Analyzer Configuration:**
   ```bash
   # Reduce analyzer timeouts
   # Edit Cortex configuration
   docker exec soar_cortex nano /etc/cortex/application.conf
   
   # Reduce concurrent analyzers
   ```

### Problem: Memory Exhaustion

**Symptoms:**
- Containers being killed
- Out of memory errors
- System swapping

**Diagnostic Steps:**
```bash
# Check memory usage
free -h
docker stats --no-stream

# Check for memory leaks
docker exec soar_thehive ps aux
docker exec soar_cortex ps aux

# Monitor over time
watch -n 5 'free -h && docker stats --no-stream'
```

**Solutions:**

1. **Increase Available Memory:**
   ```bash
   # Add swap space
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   
   # Make permanent
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

2. **Optimize Memory Usage:**
   ```bash
   # Reduce Java heap sizes
   # Edit environment variables in docker-compose.yml
   nano docker/docker-compose.yml
   
   # Add JVM options
   - JAVA_OPTS: "-Xms2g -Xmx4g"
   ```

---

## Data and Storage

### Problem: Disk Space Exhaustion

**Symptoms:**
- Containers failing to start
- Write errors in logs
- Database corruption

**Diagnostic Steps:**
```bash
# Check disk usage
df -h
du -sh /var/lib/docker/

# Check volume sizes
docker volume ls
docker system df

# Analyze log sizes
du -sh logs/
```

**Solutions:**

1. **Clean Up Docker Resources:**
   ```bash
   # Remove unused images
   docker image prune -a
   
   # Remove unused volumes
   docker volume prune -f
   
   # Remove stopped containers
   docker container prune -f
   ```

2. **Implement Log Rotation:**
   ```bash
   # Configure log rotation
   # Add to docker-compose.yml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### Problem: Data Loss or Corruption

**Symptoms:**
- Missing cases in TheHive
- Elasticsearch cluster red status
- Inconsistent data

**Diagnostic Steps:**
```bash
# Check Elasticsearch health
curl http://localhost:19200/_cluster/health

# Check indices
curl http://localhost:19200/_cat/indices

# Verify data integrity
docker exec soar_thehive curl -X GET "http://elasticsearch:9200/thehive/_search?size=0"
```

**Solutions:**

1. **Restore from Backup:**
   ```bash
   # Restore Elasticsearch data
   docker run --rm -v backup_data:/backup -v soar-lab_es_data:/data \
     alpine tar xzf /backup/es_backup.tar.gz -C /data
   
   # Restart services
   docker compose restart
   ```

2. **Rebuild Indices:**
   ```bash
   # Rebuild Elasticsearch indices
   docker exec soar_elasticsearch curl -X DELETE "http://localhost:9200/*"
   docker restart soar_thehive
   ```

---

## Integration Failures

### Problem: Shuffle Workflow Not Triggering

**Symptoms:**
- Alert received but workflow doesn't start
- Workflow stuck in "running" state
- No case created in TheHive

**Diagnostic Steps:**
```bash
# Check Shuffle logs
docker logs soar_shuffle-backend

# Verify workflow configuration
curl -H "Authorization: Bearer $SHUFFLE_API_KEY" \
  http://localhost:5001/api/v1/workflows

# Test webhook with valid payload
curl -X POST http://localhost:5001/webhook \
  -H "Authorization: Bearer $SIEM_WEBHOOK_TOKEN" \
  -H "Content-Type: application/json" \
  -d @tests/payloads/payload_case1.json
```

**Solutions:**

1. **Fix Workflow Configuration:**
   ```bash
   # Re-import workflow
   # Access Shuffle UI
   # Delete and re-import workflow
   # Verify webhook trigger
   ```

2. **Fix App Connections:**
   ```bash
   # Test TheHive connection
   curl -H "Authorization: Bearer $THEHIVE_API_KEY" \
     http://localhost:9000/api/case
   
   # Test Cortex connection
   curl -H "Authorization: Bearer $CORTEX_API_KEY" \
     http://localhost:9001/api/analyzer
   ```

### Problem: Cortex Analyzers Not Working

**Symptoms:**
- Analyzers stuck in "Waiting" state
- No results returned
- Docker errors in analyzer logs

**Diagnostic Steps:**
```bash
# Check Cortex logs
docker logs soar_cortex

# Check analyzer status
curl -H "Authorization: Bearer $CORTEX_API_KEY" \
  http://localhost:9001/api/analyzer

# Check Docker access in Cortex
docker exec soar_cortex docker ps
```

**Solutions:**

1. **Fix Docker Socket Access:**
   ```bash
   # Add Cortex user to docker group
   docker exec soar_cortex usermod -aG docker cortex
   
   # Restart Cortex
   docker restart soar_cortex
   ```

2. **Fix Analyzer Configuration:**
   ```bash
   # Reconfigure analyzers
   # Access Cortex UI
   # Remove and re-add analyzers
   # Test with known good hash
   ```

---

## Script Execution Errors

### Problem: Containment Scripts Fail

**Symptoms:**
- Scripts exit with error codes
- Permission denied errors
- Missing dependencies

**Diagnostic Steps:**
```bash
# Test script manually
./scripts/isolate_host.sh TEST-HOST TEST-CASE

# Check script permissions
ls -la scripts/

# Check dependencies
which bash
which python3
```

**Solutions:**

1. **Fix Script Permissions:**
   ```bash
   # Make scripts executable
   chmod +x scripts/*.sh
   chmod +x scripts/*.py
   
   # Fix line endings (if needed)
   dos2unix scripts/*.sh
   ```

2. **Fix Dependencies:**
   ```bash
   # Install required packages
   pip3 install requests
   pip3 install jsonschema
   
   # Check Python version
   python3 --version
   ```

### Problem: KPI Calculation Fails

**Symptoms:**
- calc_kpis.py script errors
- Empty kpis.csv file
- Invalid timestamp format

**Diagnostic Steps:**
```bash
# Test KPI calculation
python3 scripts/calc_kpis.py

# Check log format
head -5 logs/notify.log

# Validate timestamps
grep "Alert received" logs/notify.log | head -1
```

**Solutions:**

1. **Fix Log Format:**
   ```bash
   # Ensure consistent timestamp format
   # [YYYY-MM-DD HH:MM:SS] MESSAGE
   
   # Fix malformed entries
   sed -i 's/\[.*\]/[2025-05-03 18:42:15]/' logs/notify.log
   ```

2. **Fix Script Logic:**
   ```bash
   # Update regex pattern
   # Test with sample data
   echo "[2025-05-03 18:42:15] Alert received" | python3 -c "
import re, sys
line = sys.stdin.read().strip()
m = re.match(r'\[(.*?)\]\s(.*)', line)
print(m.groups() if m else 'No match')
"
   ```

---

## Debugging Tools

### System Monitoring

**Real-time Monitoring:**
```bash
# Monitor all containers
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Monitor resource usage
watch -n 5 'docker stats --no-stream'

# Monitor logs
tail -f logs/notify.log logs/containment.log
```

**Performance Analysis:**
```bash
# Generate performance report
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" > performance.txt

# Analyze response times
time curl http://localhost:9000/api/health
time curl http://localhost:9001/api/health
```

### Network Debugging

**Connectivity Testing:**
```bash
# Test all endpoints
for port in 9000 9001 3001 5001 19200; do
  echo "Testing port $port..."
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:$port/health || echo "Failed"
done

# Test internal connectivity
docker exec soar_thehive wget -qO- http://elasticsearch:9200
docker exec soar_cortex wget -qO- http://thehive:9000
```

**Packet Capture:**
```bash
# Capture network traffic (if needed)
sudo tcpdump -i docker0 -n port 5001
sudo tcpdump -i docker0 -n port 9000
```

### Log Analysis

**Error Pattern Detection:**
```bash
# Find all errors
grep -i error logs/*.log

# Find timeouts
grep -i timeout logs/*.log

# Find authentication failures
grep -i "unauthorized\|forbidden\|invalid" logs/*.log

# Analyze response times
grep "Alert received\|Containment executed" logs/notify.log
```

**Statistical Analysis:**
```bash
# Count events by type
grep -c "Alert received" logs/notify.log
grep -c "Containment executed" logs/notify.log
grep -c "Error" logs/notify.log

# Extract timestamps for analysis
grep "Alert received" logs/notify.log | cut -d'[' -f2 | cut -d']' -f1
```

---

## Prevention and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check container health status
- Review logs for errors
- Monitor disk usage
- Test critical functionality

**Monthly:**
- Update Docker images
- Rotate API keys
- Backup configuration
- Performance review

**Quarterly:**
- Security audit
- Capacity planning
- Documentation update
- Disaster recovery test

### Monitoring Setup

**Health Check Script:**
```bash
#!/bin/bash
# health_check.sh
echo "=== SOAR Lab Health Check ==="
echo "Date: $(date)"
echo ""

# Check containers
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""

# Check services
echo "Service Health:"
curl -s http://localhost:9000/api/health && echo "TheHive: OK" || echo "TheHive: FAILED"
curl -s http://localhost:9001/api/health && echo "Cortex: OK" || echo "Cortex: FAILED"
curl -s http://localhost:5001/health && echo "Shuffle: OK" || echo "Shuffle: FAILED"
curl -s http://localhost:19200/_cluster/health && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"
echo ""

# Check resources
echo "Resource Usage:"
df -h | grep -E "(/$|/var)"
free -h
echo ""

# Check recent errors
echo "Recent Errors:"
grep -i error logs/*.log | tail -5
```

**Automated Alerts:**
```bash
# Setup cron job for monitoring
# Add to crontab:
# 0 */6 * * * /path/to/health_check.sh | mail -s "SOAR Lab Health" admin@example.com
```

---

## Emergency Procedures

### Complete System Recovery

**Data Recovery:**
```bash
# Stop all services
docker compose down

# Restore from backup
./scripts/restore.sh backup-$(date +%Y%m%d).tar.gz

# Start services
docker compose up -d

# Verify functionality
make health
make test
```

**Partial Recovery:**
```bash
# Restore only Elasticsearch
docker compose stop
docker volume rm soar-lab_es_data
docker run --rm -v backup_data:/backup -v soar-lab_es_data:/data \
  alpine tar xzf /backup/es_backup.tar.gz -C /data
docker compose up -d
```

### Disaster Scenarios

**Scenario 1: Complete Data Loss**
1. Stop all services
2. Restore from latest backup
3. Verify data integrity
4. Test functionality
5. Document incident

**Scenario 2: Service Unavailable**
1. Check container status
2. Review logs for errors
3. Restart affected services
4. Monitor recovery
5. Escalate if needed

**Scenario 3: Security Incident**
1. Isolate affected systems
2. Preserve evidence
3. Change all credentials
4. Audit access logs
5. Implement additional security measures

---

## Contact and Support

### Getting Help

1. **Check Documentation**: Review this guide and technical documentation
2. **Search Logs**: Look for specific error messages
3. **Test Components**: Isolate the failing component
4. **Create Issue**: Include logs, configuration, and steps to reproduce

### Information to Include in Support Requests

- **System Information**: OS version, Docker version, available resources
- **Error Messages**: Complete error messages and stack traces
- **Configuration**: Sanitized .env file and docker-compose.yml
- **Logs**: Relevant log entries from all services
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected vs Actual**: What you expected vs what actually happened

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share experiences
- **Wiki**: Community-contributed guides and solutions

---

**Last Updated**: 2025-05-03  
**Version**: 1.0  
**Compatible with**: SOAR Lab v1.3.0
