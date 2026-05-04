#!/bin/bash

# SOAR Ransomware Lab - Automated Backup Script
# Performs automated backups with scheduling and retention

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
COMPRESS="${COMPRESS:-true}"
SCHEDULE="${SCHEDULE:-daily}"
LOG_FILE="${LOG_FILE:-./logs/backup.log}"

# Ensure directories exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        error "Backup failed with exit code $exit_code"
    fi
    # Remove temporary files
    rm -f /tmp/backup_*.tmp 2>/dev/null || true
}

# Signal handlers
trap cleanup EXIT INT TERM

# Check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        error "Docker is not running or not accessible"
        return 1
    fi
}

# Create backup of Docker volumes
backup_volumes() {
    local backup_date="$1"
    local volume_backup_dir="$BACKUP_DIR/volumes_$backup_date"
    
    log "Backing up Docker volumes..."
    mkdir -p "$volume_backup_dir"
    
    # List of volumes to backup
    local volumes=("soar_es_data" "soar_thehive_files" "soar_cortex_data" "soar_shuffle_apps" "soar_shuffle_files")
    
    for volume in "${volumes[@]}"; do
        if docker volume inspect "$volume" &> /dev/null; then
            log "Backing up volume: $volume"
            
            # Create temporary container to access volume
            local temp_container="backup_$(date +%s)"
            docker run --rm -d --name "$temp_container" -v "$volume":/data:ro alpine sleep 3600 &> /dev/null
            
            # Wait for container to be ready
            sleep 2
            
            # Backup volume data
            if docker cp "$temp_container:/data" "$volume_backup_dir/$volume"; then
                log "✓ Successfully backed up $volume"
            else
                error "✗ Failed to backup $volume"
            fi
            
            # Stop and remove temporary container
            docker stop "$temp_container" &> /dev/null || true
        else
            warn "Volume $volume not found, skipping"
        fi
    done
    
    # Compress volume backups
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing volume backups..."
        cd "$BACKUP_DIR"
        tar -czf "volumes_$backup_date.tar.gz" "volumes_$backup_date"
        rm -rf "volumes_$backup_date"
        cd - &> /dev/null
    fi
}

# Backup configuration files
backup_config() {
    local backup_date="$1"
    local config_backup_dir="$BACKUP_DIR/config_$backup_date"
    
    log "Backing up configuration files..."
    mkdir -p "$config_backup_dir"
    
    # Files to backup
    local files=(
        "docker/.env"
        "docker/docker-compose.yml"
        "docker/thehive.application.conf"
        "docker/cortex.application.conf"
        "certs/"
        "schemas/"
    )
    
    for file in "${files[@]}"; do
        if [[ -e "$file" ]]; then
            log "Backing up: $file"
            cp -r "$file" "$config_backup_dir/"
        else
            warn "File $file not found, skipping"
        fi
    done
    
    # Compress config backups
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing configuration backups..."
        cd "$BACKUP_DIR"
        tar -czf "config_$backup_date.tar.gz" "config_$backup_date"
        rm -rf "config_$backup_date"
        cd - &> /dev/null
    fi
}

# Backup logs
backup_logs() {
    local backup_date="$1"
    local logs_backup_dir="$BACKUP_DIR/logs_$backup_date"
    
    log "Backing up logs..."
    mkdir -p "$logs_backup_dir"
    
    if [[ -d "logs" ]]; then
        cp -r logs/* "$logs_backup_dir/"
    else
        warn "Logs directory not found, skipping"
    fi
    
    # Compress log backups
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing log backups..."
        cd "$BACKUP_DIR"
        tar -czf "logs_$backup_date.tar.gz" "logs_$backup_date"
        rm -rf "logs_$backup_date"
        cd - &> /dev/null
    fi
}

# Backup results and analysis
backup_results() {
    local backup_date="$1"
    local results_backup_dir="$BACKUP_DIR/results_$backup_date"
    
    log "Backing up results and analysis..."
    mkdir -p "$results_backup_dir"
    
    if [[ -d "results" ]]; then
        cp -r results/* "$results_backup_dir/"
    else
        warn "Results directory not found, skipping"
    fi
    
    # Compress results backups
    if [[ "$COMPRESS" == "true" ]]; then
        log "Compressing results backups..."
        cd "$BACKUP_DIR"
        tar -czf "results_$backup_date.tar.gz" "results_$backup_date"
        rm -rf "results_$backup_date"
        cd - &> /dev/null
    fi
}

# Create backup manifest
create_manifest() {
    local backup_date="$1"
    local manifest_file="$BACKUP_DIR/manifest_$backup_date.json"
    
    log "Creating backup manifest..."
    
    cat > "$manifest_file" << EOF
{
    "backup_date": "$backup_date",
    "timestamp": "$(date -Iseconds)",
    "backup_type": "automated",
    "schedule": "$SCHEDULE",
    "compression": $COMPRESS,
    "components": {
        "volumes": $(ls "$BACKUP_DIR/volumes_$backup_date.tar.gz" &> /dev/null && echo "true" || echo "false"),
        "config": $(ls "$BACKUP_DIR/config_$backup_date.tar.gz" &> /dev/null && echo "true" || echo "false"),
        "logs": $(ls "$BACKUP_DIR/logs_$backup_date.tar.gz" &> /dev/null && echo "true" || echo "false"),
        "results": $(ls "$BACKUP_DIR/results_$backup_date.tar.gz" &> /dev/null && echo "true" || echo "false")
    },
    "docker_version": "$(docker --version)",
    "docker_compose_version": "$(docker compose version)",
    "hostname": "$(hostname)",
    "user": "$(whoami)"
}
EOF
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Find and remove old backup files
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "manifest_*.json" -mtime +$RETENTION_DAYS -delete
    
    # Count remaining backups
    local backup_count=$(find "$BACKUP_DIR" -name "*.tar.gz" | wc -l)
    log "Retained $backup_count backup(s)"
}

# Verify backup integrity
verify_backup() {
    local backup_date="$1"
    local errors=0
    
    log "Verifying backup integrity..."
    
    # Check if all expected files exist
    local expected_files=(
        "volumes_$backup_date.tar.gz"
        "config_$backup_date.tar.gz"
        "logs_$backup_date.tar.gz"
        "results_$backup_date.tar.gz"
        "manifest_$backup_date.json"
    )
    
    for file in "${expected_files[@]}"; do
        if [[ -f "$BACKUP_DIR/$file" ]]; then
            # Verify tar.gz integrity
            if tar -tzf "$BACKUP_DIR/$file" &> /dev/null; then
                log "✓ $file integrity verified"
            else
                error "✗ $file is corrupted"
                errors=$((errors + 1))
            fi
        else
            warn "$file not found"
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        log "✓ Backup verification successful"
        return 0
    else
        error "✗ Backup verification failed with $errors errors"
        return 1
    fi
}

# Setup cron job for automatic scheduling
setup_schedule() {
    local cron_schedule="$1"
    
    log "Setting up automatic backup schedule: $cron_schedule"
    
    # Create cron entry
    local cron_entry="$cron_schedule $(pwd)/scripts/auto_backup.sh"
    local temp_cron="/tmp/soar_backup_cron"
    
    # Export current crontab
    crontab -l 2>/dev/null > "$temp_cron" || touch "$temp_cron"
    
    # Check if entry already exists
    if grep -F "auto_backup.sh" "$temp_cron"; then
        warn "Backup schedule already exists"
        return 0
    fi
    
    # Add new entry
    echo "$cron_entry" >> "$temp_cron"
    
    # Install new crontab
    crontab "$temp_cron"
    
    # Cleanup
    rm -f "$temp_cron"
    
    log "✓ Automatic backup schedule installed"
}

# Main backup function
perform_backup() {
    local backup_date
    backup_date=$(date '+%Y%m%d_%H%M%S')
    
    log "Starting automated backup: $backup_date"
    
    # Check prerequisites
    check_docker || exit 1
    
    # Perform backup components
    backup_volumes "$backup_date"
    backup_config "$backup_date"
    backup_logs "$backup_date"
    backup_results "$backup_date"
    
    # Create manifest
    create_manifest "$backup_date"
    
    # Verify backup
    if verify_backup "$backup_date"; then
        log "✓ Backup completed successfully: $backup_date"
        
        # Cleanup old backups
        cleanup_old_backups
        
        # Calculate backup size
        local backup_size
        backup_size=$(du -sh "$BACKUP_DIR"/*"$backup_date"* 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")
        log "Backup size: $backup_size"
    else
        error "Backup verification failed"
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
SOAR Ransomware Lab - Automated Backup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -s, --schedule CRON     Setup automatic backup schedule (e.g., "0 2 * * *" for daily at 2 AM)
    -r, --retention DAYS    Set retention period in days (default: 7)
    -c, --compress BOOL     Enable/disable compression (default: true)
    -d, --dir DIRECTORY     Set backup directory (default: ./backups)
    --dry-run               Show what would be backed up without actually doing it

EXAMPLES:
    $0                      # Perform backup now
    $0 -s "0 2 * * *"      # Setup daily backup at 2 AM
    $0 -r 30               # Set 30-day retention
    $0 -c false            # Disable compression
    $0 -d /backup/soar     # Use custom backup directory

SCHEDULE EXAMPLES:
    "0 2 * * *"            # Daily at 2:00 AM
    "0 2 * * 0"            # Weekly on Sunday at 2:00 AM
    "0 2 1 * *"            # Monthly on 1st at 2:00 AM
    "*/6 * * * *"          # Every 6 hours

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--schedule)
            setup_schedule "$2"
            exit 0
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -c|--compress)
            COMPRESS="$2"
            shift 2
            ;;
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run backup or dry run
if [[ "${DRY_RUN:-}" == "true" ]]; then
    log "DRY RUN - Would backup the following:"
    log "  - Docker volumes: es_data, thehive_files, cortex_data, shuffle_apps, shuffle_files"
    log "  - Configuration files: docker/.env, docker-compose.yml, *.conf"
    log "  - Logs directory"
    log "  - Results directory"
    log "  - Backup directory: $BACKUP_DIR"
    log "  - Retention: $RETENTION_DAYS days"
    log "  - Compression: $COMPRESS"
else
    perform_backup
fi
