#!/bin/bash

# SOAR Ransomware Lab - Backup Script
# Creates comprehensive backups of the SOAR lab environment

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-soar}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="soar_backup_${DATE}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "=== Iniciando backup del Laboratorio SOAR ==="
log "Directorio: $BACKUP_DIR"
log "Nombre del backup: $BACKUP_NAME"

# Stop services
log "Deteniendo servicios Docker..."
docker compose -f infra/docker/docker-compose.yml --env-file .env.full down

# Backup 1: Configuration files
log "Creando backup de archivos de configuración..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_config.tar.gz" \
    infra/docker/docker-compose.yml \
    .env.full \
    infra/docker/nginx.conf \
    infra/docker/docker/cortex.application.conf 2>/dev/null || true
log "✓ Configuración respaldada"

# Backup 2: TLS Certificates
log "Creando backup de certificados TLS..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_certs.tar.gz" \
    certs/ 2>/dev/null || true
log "✓ Certificados respaldados"

# Backup 3: Docker volumes
log "Creando backup de volúmenes Docker..."
TEMP_DIR=$(mktemp -d)

# Backup Elasticsearch data
if docker volume inspect "${COMPOSE_PROJECT_NAME}_es_data" >/dev/null 2>&1; then
    log "  Respaldando Elasticsearch data..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_es_data:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_es_data.tar.gz" -C /data .
    log "  ✓ Elasticsearch data respaldado"
fi

# Backup Kibana data
if docker volume inspect "kibana_data" >/dev/null 2>&1; then
    log "  Respaldando Kibana data..."
    docker run --rm \
        -v "kibana_data:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_kibana_data.tar.gz" -C /data .
    log "  ✓ Kibana data respaldado"
fi

# Backup Wazuh data
if docker volume inspect "wazuh_db" >/dev/null 2>&1; then
    log "  Respaldando Wazuh data..."
    docker run --rm \
        -v "wazuh_db:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_wazuh_db.tar.gz" -C /data .
    log "  ✓ Wazuh data respaldado"
fi

# Backup MISP database
if docker volume inspect "misp_db_data" >/dev/null 2>&1; then
    log "  Respaldando MISP database..."
    docker run --rm \
        -v "misp_db_data:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_misp_db_data.tar.gz" -C /data .
    log "  ✓ MISP database respaldado"
fi

# Backup TheHive files
if docker volume inspect "${COMPOSE_PROJECT_NAME}_thehive_files" >/dev/null 2>&1; then
    log "  Respaldando TheHive files..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_thehive_files:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_thehive_files.tar.gz" -C /data .
    log "  ✓ TheHive files respaldado"
fi

# Backup Cortex data
if docker volume inspect "${COMPOSE_PROJECT_NAME}_cortex_data" >/dev/null 2>&1; then
    log "  Respaldando Cortex data..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_cortex_data:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_cortex_data.tar.gz" -C /data .
    log "  ✓ Cortex data respaldado"
fi

# Backup Shuffle apps
if docker volume inspect "shuffle_app_storage" >/dev/null 2>&1; then
    log "  Respaldando Shuffle apps..."
    docker run --rm \
        -v "shuffle_app_storage:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_shuffle_apps.tar.gz" -C /data .
    log "  ✓ Shuffle apps respaldado"
fi

# Backup Shuffle files
if docker volume inspect "shuffle_file_storage" >/dev/null 2>&1; then
    log "  Respaldando Shuffle files..."
    docker run --rm \
        -v "shuffle_file_storage:/data:ro" \
        -v "$TEMP_DIR:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_shuffle_files.tar.gz" -C /data .
    log "  ✓ Shuffle files respaldado"
fi

# Create volumes backup
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_volumes.tar.gz" -C "$TEMP_DIR" .
rm -rf "$TEMP_DIR"
log "✓ Volúmenes Docker respaldados"

# Backup 4: Logs
log "Creando backup de logs..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_logs.tar.gz" \
    artifacts/logs/ 2>/dev/null || true
log "✓ Logs respaldados"

# Backup 5: Test results
log "Creando backup de resultados..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_results.tar.gz" \
    artifacts/results/ 2>/dev/null || true
log "✓ Resultados respaldados"

# Clean old backups (keep last 5)
log "Limpiando backups antiguos..."
find "$BACKUP_DIR" -name "*_manifest.txt" -type f | sort -r | tail -n +6 | while read -r manifest; do
    backup_base=$(basename "$manifest" _manifest.txt)
    log "  Eliminando backup antiguo: $backup_base"
    rm -f "${BACKUP_DIR}/${backup_base}_config.tar.gz"
    rm -f "${BACKUP_DIR}/${backup_base}_certs.tar.gz"
    rm -f "${BACKUP_DIR}/${backup_base}_volumes.tar.gz"
    rm -f "${BACKUP_DIR}/${backup_base}_logs.tar.gz"
    rm -f "${BACKUP_DIR}/${backup_base}_results.tar.gz"
    rm -f "$manifest"
done

# Create manifest
log "Creando manifiesto del backup..."
cat > "${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt" << EOF
SOAR Lab Backup Manifest
=====================
Backup Name: $BACKUP_NAME
Date: $(date)
Created by: $(whoami)@$(hostname)

Components:
- Configuration files: ${BACKUP_NAME}_config.tar.gz
- TLS Certificates: ${BACKUP_NAME}_certs.tar.gz
- Docker Volumes: ${BACKUP_NAME}_volumes.tar.gz
- Logs: ${BACKUP_NAME}_logs.tar.gz
- Results: ${BACKUP_NAME}_results.tar.gz

Docker Volumes:
- Elasticsearch: $(docker volume inspect "${COMPOSE_PROJECT_NAME}_es_data" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- Kibana: $(docker volume inspect "kibana_data" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- Wazuh DB: $(docker volume inspect "wazuh_db" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- MISP DB: $(docker volume inspect "misp_db_data" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- TheHive Files: $(docker volume inspect "${COMPOSE_PROJECT_NAME}_thehive_files" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- Cortex Data: $(docker volume inspect "${COMPOSE_PROJECT_NAME}_cortex_data" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- Shuffle Apps: $(docker volume inspect "shuffle_app_storage" >/dev/null 2>&1 && echo "Present" || echo "Not found")
- Shuffle Files: $(docker volume inspect "shuffle_file_storage" >/dev/null 2>&1 && echo "Present" || echo "Not found")

Notes:
- Use restore.sh with backup name to restore
- Verify Docker daemon is running before restore
- Check disk space: $(du -sh "$BACKUP_DIR" | cut -f1)
EOF

log "✓ Manifiesto creado"

# Start services
log "Iniciando servicios Docker..."
docker compose -f infra/docker/docker-compose.yml --env-file .env.full up -d

# Wait for services to be healthy
log "Esperando que los servicios estén saludables..."
sleep 30

# Check service health
log "Verificando salud de los servicios..."
docker compose -f infra/docker/docker-compose.yml --env-file .env.full ps

log "=== Backup completado exitosamente ==="
log "Ubicación: $BACKUP_DIR"
log "Tamaño: $(du -sh "$BACKUP_DIR" | cut -f1)"
log "Para restaurar use: ./scripts/infra/restore.sh $BACKUP_NAME"

exit 0
