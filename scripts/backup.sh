#!/bin/bash

# SOAR Ransomware Lab - Backup Script
# Creates automated backups of configuration, volumes, and data

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_NAME="${BACKUP_NAME:-soar-lab-backup}"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-soar}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
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
log "Directorio de backup: $BACKUP_DIR"
log "Nombre del backup: ${BACKUP_NAME}_${DATE}"

# Backup 1: Configuration files
log "Backup de archivos de configuración..."
CONFIG_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_config.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    docker/.env \
    docker/*.conf \
    schemas/ \
    scripts/ \
    .gitignore \
    Makefile \
    2>/dev/null || warn "Algunos archivos de configuración no encontrados"

if [ -f "$CONFIG_BACKUP" ]; then
    log "✓ Configuración backup completada: $CONFIG_BACKUP"
    SIZE=$(du -h "$CONFIG_BACKUP" | cut -f1)
    log "  Tamaño: $SIZE"
else
    error "Fallo al backup configuración"
fi

# Backup 2: Certificates
log "Backup de certificados TLS..."
if [ -d "certs" ]; then
    CERT_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_certs.tar.gz"
    tar -czf "$CERT_BACKUP" certs/ 2>/dev/null
    if [ -f "$CERT_BACKUP" ]; then
        log "✓ Certificados backup completados: $CERT_BACKUP"
        SIZE=$(du -h "$CERT_BACKUP" | cut -f1)
        log "  Tamaño: $SIZE"
    else
        warn "No se encontraron certificados para backup"
    fi
else
    warn "Directorio certs/ no encontrado, omitiendo backup de certificados"
fi

# Backup 3: Docker volumes
log "Backup de volúmenes Docker..."
VOLUME_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_volumes.tar.gz"

# Backup Elasticsearch data
if docker volume ls | grep -q "${COMPOSE_PROJECT_NAME}_es_data"; then
    log "  Backup Elasticsearch data..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_es_data:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_${DATE}_es_data.tar.gz" -C /data .
fi

# Backup TheHive files
if docker volume ls | grep -q "${COMPOSE_PROJECT_NAME}_thehive_files"; then
    log "  Backup TheHive files..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_thehive_files:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_${DATE}_thehive_files.tar.gz" -C /data .
fi

# Backup Cortex data
if docker volume ls | grep -q "${COMPOSE_PROJECT_NAME}_cortex_data"; then
    log "  Backup Cortex data..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_cortex_data:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_${DATE}_cortex_data.tar.gz" -C /data .
fi

# Backup Shuffle data
if docker volume ls | grep -q "${COMPOSE_PROJECT_NAME}_shuffle_apps"; then
    log "  Backup Shuffle apps..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_shuffle_apps:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_${DATE}_shuffle_apps.tar.gz" -C /data .
fi

if docker volume ls | grep -q "${COMPOSE_PROJECT_NAME}_shuffle_files"; then
    log "  Backup Shuffle files..."
    docker run --rm \
        -v "${COMPOSE_PROJECT_NAME}_shuffle_files:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${BACKUP_NAME}_${DATE}_shuffle_files.tar.gz" -C /data .
fi

# Combine all volume backups
log "Combinando backups de volúmenes..."
tar -czf "$VOLUME_BACKUP" \
    "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_es_data.tar.gz" \
    "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_thehive_files.tar.gz" \
    "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_cortex_data.tar.gz" \
    "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_shuffle_apps.tar.gz" \
    "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_shuffle_files.tar.gz" \
    2>/dev/null

# Remove individual volume backups
rm -f "${BACKUP_DIR}/${BACKUP_NAME}_${DATE}"_*.tar.gz 2>/dev/null

if [ -f "$VOLUME_BACKUP" ]; then
    log "✓ Volúmenes backup completados: $VOLUME_BACKUP"
    SIZE=$(du -h "$VOLUME_BACKUP" | cut -f1)
    log "  Tamaño: $SIZE"
else
    warn "No se encontraron volúmenes para backup"
fi

# Backup 4: Logs
log "Backup de logs..."
if [ -d "logs" ]; then
    LOG_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_logs.tar.gz"
    tar -czf "$LOG_BACKUP" logs/ 2>/dev/null
    if [ -f "$LOG_BACKUP" ]; then
        log "✓ Logs backup completados: $LOG_BACKUP"
        SIZE=$(du -h "$LOG_BACKUP" | cut -f1)
        log "  Tamaño: $SIZE"
    else
        warn "No se encontraron logs para backup"
    fi
else
    warn "Directorio logs/ no encontrado, omitiendo backup de logs"
fi

# Backup 5: Results
log "Backup de resultados..."
if [ -d "results" ]; then
    RESULTS_BACKUP="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_results.tar.gz"
    tar -czf "$RESULTS_BACKUP" results/ 2>/dev/null
    if [ -f "$RESULTS_BACKUP" ]; then
        log "✓ Resultados backup completados: $RESULTS_BACKUP"
        SIZE=$(du -h "$RESULTS_BACKUP" | cut -f1)
        log "  Tamaño: $SIZE"
    else
        warn "No se encontraron resultados para backup"
    fi
else
    warn "Directorio results/ no encontrado, omitiendo backup de resultados"
fi

# Generate backup manifest
log "Generando manifiesto de backup..."
MANIFEST="${BACKUP_DIR}/${BACKUP_NAME}_${DATE}_manifest.txt"
cat > "$MANIFEST" << EOF
SOAR Lab Backup Manifest
========================
Backup Name: ${BACKUP_NAME}_${DATE}
Date: $(date)
Project: ${COMPOSE_PROJECT_NAME}

Files Included:
- Configuration: ${CONFIG_BACKUP:-N/A}
- Certificates: ${CERT_BACKUP:-N/A}
- Volumes: ${VOLUME_BACKUP:-N/A}
- Logs: ${LOG_BACKUP:-N/A}
- Results: ${RESULTS_BACKUP:-N/A}

Total Size: $(du -sh "$BACKUP_DIR" | cut -f1)

To restore this backup, use:
  ./scripts/restore.sh ${BACKUP_NAME}_${DATE}
EOF

log "✓ Manifiesto generado: $MANIFEST"

# Cleanup old backups (keep last 7 days)
log "Limpiando backups antiguos (mantenemos últimos 7 días)..."
find "$BACKUP_DIR" -name "${BACKUP_NAME}_*" -mtime +7 -delete 2>/dev/null || true

log "=== Backup completado exitosamente ==="
log "Ubicación: $BACKUP_DIR"
log "Archivos creados:"
ls -lh "$BACKUP_DIR"/${BACKUP_NAME}_${DATE}* 2>/dev/null || true

exit 0
