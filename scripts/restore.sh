#!/bin/bash

# SOAR Ransomware Lab - Restore Script
# Restores backups created by backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
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

# Check if backup name is provided
if [ $# -lt 1 ]; then
    error "Se requiere el nombre del backup como argumento"
    echo ""
    echo "Uso: $0 <backup_name>"
    echo ""
    echo "Backups disponibles:"
    ls -1 "$BACKUP_DIR" | grep -E "_manifest.txt$" | sed 's/_manifest.txt//' || echo "  No se encontraron backups"
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

log "=== Iniciando restauración del Laboratorio SOAR ==="
log "Backup: $BACKUP_NAME"
log "Directorio: $BACKUP_DIR"

# Check if backup exists
if [ ! -f "${BACKUP_PATH}_manifest.txt" ]; then
    error "Backup no encontrado: ${BACKUP_PATH}_manifest.txt"
    exit 1
fi

# Display manifest
log "Manifiesto del backup:"
cat "${BACKUP_PATH}_manifest.txt"
echo ""

# Confirm restore
read -p "¿Desea continuar con la restauración? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    log "Restauración cancelada por el usuario"
    exit 0
fi

# Stop services
log "Deteniendo servicios Docker..."
docker compose -f docker/docker-compose.yml --env-file docker/.env down

# Restore 1: Configuration files
if [ -f "${BACKUP_PATH}_config.tar.gz" ]; then
    log "Restaurando archivos de configuración..."
    tar -xzf "${BACKUP_PATH}_config.tar.gz" -C .
    log "✓ Configuración restaurada"
else
    warn "No se encontró backup de configuración, omitiendo"
fi

# Restore 2: Certificates
if [ -f "${BACKUP_PATH}_certs.tar.gz" ]; then
    log "Restaurando certificados TLS..."
    tar -xzf "${BACKUP_PATH}_certs.tar.gz" -C .
    log "✓ Certificados restaurados"
else
    warn "No se encontró backup de certificados, omitiendo"
fi

# Restore 3: Docker volumes
if [ -f "${BACKUP_PATH}_volumes.tar.gz" ]; then
    log "Restaurando volúmenes Docker..."
    
    # Extract to temp directory
    TEMP_DIR=$(mktemp -d)
    tar -xzf "${BACKUP_PATH}_volumes.tar.gz" -C "$TEMP_DIR"
    
    # Restore Elasticsearch data
    if [ -f "${TEMP_DIR}/${BACKUP_NAME}_es_data.tar.gz" ]; then
        log "  Restaurando Elasticsearch data..."
        docker volume create "${COMPOSE_PROJECT_NAME}_es_data" 2>/dev/null || true
        docker run --rm \
            -v "${COMPOSE_PROJECT_NAME}_es_data:/data" \
            -v "$TEMP_DIR:/backup" \
            alpine tar xzf "/backup/${BACKUP_NAME}_es_data.tar.gz" -C /data
        log "  ✓ Elasticsearch data restaurado"
    fi
    
    # Restore TheHive files
    if [ -f "${TEMP_DIR}/${BACKUP_NAME}_thehive_files.tar.gz" ]; then
        log "  Restaurando TheHive files..."
        docker volume create "${COMPOSE_PROJECT_NAME}_thehive_files" 2>/dev/null || true
        docker run --rm \
            -v "${COMPOSE_PROJECT_NAME}_thehive_files:/data" \
            -v "$TEMP_DIR:/backup" \
            alpine tar xzf "/backup/${BACKUP_NAME}_thehive_files.tar.gz" -C /data
        log "  ✓ TheHive files restaurado"
    fi
    
    # Restore Cortex data
    if [ -f "${TEMP_DIR}/${BACKUP_NAME}_cortex_data.tar.gz" ]; then
        log "  Restaurando Cortex data..."
        docker volume create "${COMPOSE_PROJECT_NAME}_cortex_data" 2>/dev/null || true
        docker run --rm \
            -v "${COMPOSE_PROJECT_NAME}_cortex_data:/data" \
            -v "$TEMP_DIR:/backup" \
            alpine tar xzf "/backup/${BACKUP_NAME}_cortex_data.tar.gz" -C /data
        log "  ✓ Cortex data restaurado"
    fi
    
    # Restore Shuffle apps
    if [ -f "${TEMP_DIR}/${BACKUP_NAME}_shuffle_apps.tar.gz" ]; then
        log "  Restaurando Shuffle apps..."
        docker volume create "${COMPOSE_PROJECT_NAME}_shuffle_apps" 2>/dev/null || true
        docker run --rm \
            -v "${COMPOSE_PROJECT_NAME}_shuffle_apps:/data" \
            -v "$TEMP_DIR:/backup" \
            alpine tar xzf "/backup/${BACKUP_NAME}_shuffle_apps.tar.gz" -C /data
        log "  ✓ Shuffle apps restaurado"
    fi
    
    # Restore Shuffle files
    if [ -f "${TEMP_DIR}/${BACKUP_NAME}_shuffle_files.tar.gz" ]; then
        log "  Restaurando Shuffle files..."
        docker volume create "${COMPOSE_PROJECT_NAME}_shuffle_files" 2>/dev/null || true
        docker run --rm \
            -v "${COMPOSE_PROJECT_NAME}_shuffle_files:/data" \
            -v "$TEMP_DIR:/backup" \
            alpine tar xzf "/backup/${BACKUP_NAME}_shuffle_files.tar.gz" -C /data
        log "  ✓ Shuffle files restaurado"
    fi
    
    # Cleanup temp directory
    rm -rf "$TEMP_DIR"
    log "✓ Volúmenes Docker restaurados"
else
    warn "No se encontró backup de volúmenes, omitiendo"
fi

# Restore 4: Logs
if [ -f "${BACKUP_PATH}_logs.tar.gz" ]; then
    log "Restaurando logs..."
    tar -xzf "${BACKUP_PATH}_logs.tar.gz" -C .
    log "✓ Logs restaurados"
else
    warn "No se encontró backup de logs, omitiendo"
fi

# Restore 5: Results
if [ -f "${BACKUP_PATH}_results.tar.gz" ]; then
    log "Restaurando resultados..."
    tar -xzf "${BACKUP_PATH}_results.tar.gz" -C .
    log "✓ Resultados restaurados"
else
    warn "No se encontró backup de resultados, omitiendo"
fi

# Start services
log "Iniciando servicios Docker..."
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d

# Wait for services to be healthy
log "Esperando que los servicios estén saludables..."
sleep 30

# Check service health
log "Verificando salud de los servicios..."
docker compose -f docker/docker-compose.yml --env-file docker/.env ps

log "=== Restauración completada exitosamente ==="
log "Por favor, verifique que todos los servicios estén funcionando correctamente"
log "URLs importantes:"
echo "  TheHive: http://localhost:9000"
echo "  Cortex: http://localhost:9001"
echo "  Shuffle UI: http://localhost:3001"
echo "  Elasticsearch: http://localhost:19200"

exit 0
