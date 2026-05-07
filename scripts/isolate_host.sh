#!/bin/bash

# SOAR Ransomware Lab - Linux Host Isolation Script
# Simulates endpoint containment actions for ransomware response
# This script handles network isolation, process termination, and account lockdown.

set -euo pipefail
set -u

# Configuration
LOG_FILE="${LOG_FILE:-./logs/containment.log}"
SIMULATION_MODE="${SIMULATION_MODE:-true}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary files..."
    # Add cleanup logic here if needed
    rm -f /tmp/isolate_host_*.tmp 2>/dev/null || true
}

# Signal handlers
trap cleanup EXIT INT TERM

# Function to validate hostname format
validate_hostname() {
    local hostname="$1"
    if [[ ! "$hostname" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$ ]]; then
        log "ERROR: Invalid hostname format. Only alphanumeric characters and hyphens allowed"
        return 1
    fi
}

# Function to validate case ID format
validate_case_id() {
    local case_id="$1"
    if [[ ! "$case_id" =~ ^[A-Z]+-[0-9]+$ ]]; then
        log "ERROR: Invalid case ID format. Expected format: CASE-123"
        return 1
    fi
}

# Function to simulate network isolation
isolate_network() {
    local hostname="$1"
    local case_id="$2"
    
    log "NETWORK ISOLATION - Host: $hostname, Case: $case_id"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Disabling network interfaces for $hostname"
        log "[SIMULATION] iptables -A INPUT -s $hostname -j DROP"
        log "[SIMULATION] iptables -A OUTPUT -d $hostname -j DROP"
        log "[SIMULATION] Network isolation completed for $hostname"
    else
        log "WARNING: Real network isolation mode enabled"
        # iptables -A INPUT -s "$hostname" -j DROP
        # iptables -A OUTPUT -d "$hostname" -j DROP
        log "Real network isolation would be executed here"
    fi
}

# Function to simulate process termination
terminate_malicious_processes() {
    local hostname="$1"
    local case_id="$2"
    
    log "PROCESS TERMINATION - Host: $hostname, Case: $case_id"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Scanning for suspicious processes on $hostname"
        log "[SIMULATION] Found processes: ransomware.exe (PID: 1234), cryptolocker.exe (PID: 5678)"
        log "[SIMULATION] Terminating malicious processes"
        log "[SIMULATION] kill -9 1234 5678"
        log "[SIMULATION] Process termination completed"
    else
        log "WARNING: Real process termination mode enabled"
        # pkill -f ransomware
        # pkill -f cryptolocker
        log "Real process termination would be executed here"
    fi
}

# Function to simulate user account lockdown
lockdown_accounts() {
    local hostname="$1"
    local case_id="$2"
    
    log "ACCOUNT LOCKDOWN - Host: $hostname, Case: $case_id"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Locking down user accounts on $hostname"
        log "[SIMULATION] usermod -L infected_user"
        log "[SIMULATION] passwd -l infected_user"
        log "[SIMULATION] Account lockdown completed"
    else
        log "WARNING: Real account lockdown mode enabled"
        # usermod -L infected_user
        # passwd -l infected_user
        log "Real account lockdown would be executed here"
    fi
}

# Function to simulate file system protection
protect_filesystem() {
    local hostname="$1"
    local case_id="$2"
    
    log "FILESYSTEM PROTECTION - Host: $hostname, Case: $case_id"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Mounting filesystems read-only on $hostname"
        log "[SIMULATION] mount -o remount,ro /"
        log "[SIMULATION] mount -o remount,ro /home"
        log "[SIMULATION] Filesystem protection completed"
    else
        log "WARNING: Real filesystem protection mode enabled"
        # mount -o remount,ro /
        # mount -o remount,ro /home
        log "Real filesystem protection would be executed here"
    fi
}

# Function to create forensic backup
create_forensic_backup() {
    local hostname="$1"
    local case_id="$2"
    local backup_path="$BACKUP_DIR/${case_id}_${hostname}_$(date +%Y%m%d_%H%M%S)"
    
    log "FORENSIC BACKUP - Host: $hostname, Case: $case_id"
    mkdir -p "$backup_path"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Creating forensic backup at $backup_path"
        log "[SIMULATION] Copying memory dump: /proc/kcore -> $backup_path/memory.dump"
        log "[SIMULATION] Copying system logs: /var/log -> $backup_path/logs/"
        log "[SIMULATION] Copying process list: ps aux -> $backup_path/processes.txt"
        log "[SIMULATION] Copying network connections: netstat -an -> $backup_path/connections.txt"
        log "[SIMULATION] Forensic backup completed"
    else
        log "Creating real forensic backup at $backup_path"
        # cp /proc/kcore "$backup_path/memory.dump" 2>/dev/null || true
        # cp -r /var/log "$backup_path/logs/"
        # ps aux > "$backup_path/processes.txt"
        # netstat -an > "$backup_path/connections.txt"
        log "Real forensic backup would be created here"
    fi
    
    echo "$backup_path"
}

# Function to generate containment report
generate_report() {
    local hostname="$1"
    local case_id="$2"
    local backup_path="$3"
    
    log "CONTAINMENT REPORT - Host: $hostname, Case: $case_id"
    
    local report_file="$BACKUP_DIR/${case_id}_${hostname}_containment_report.json"
    
    cat > "$report_file" << EOF
{
  "case_id": "$case_id",
  "hostname": "$hostname",
  "containment_timestamp": "$(date -Iseconds)",
  "actions_performed": [
    "network_isolation",
    "process_termination", 
    "account_lockdown",
    "filesystem_protection",
    "forensic_backup"
  ],
  "backup_location": "$backup_path",
  "simulation_mode": "$SIMULATION_MODE",
  "status": "completed",
  "next_steps": [
    "Analyze forensic evidence",
    "Restore from backup",
    "Update security policies",
    "User education"
  ]
}
EOF
    
    log "Containment report generated: $report_file"
    echo "$report_file"
}

# Main containment function
contain_host() {
    local hostname="$1"
    local case_id="$2"
    
    log "=== STARTING CONTAINMENT PROCEDURE ==="
    log "Host: $hostname"
    log "Case ID: $case_id"
    log "Simulation Mode: $SIMULATION_MODE"
    
    # Validate inputs
    if [ -z "$hostname" ] || [ -z "$case_id" ]; then
        log "ERROR: Missing required parameters: hostname and case_id"
        exit 1
    fi
    
    # Validate hostname format (alphanumeric, hyphens, underscores)
    if ! [[ "$hostname" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        log "ERROR: Invalid hostname format. Only alphanumeric, hyphens and underscores allowed"
        exit 1
    fi
    
    # Validate case_id format (alphanumeric, hyphens)
    if ! [[ "$case_id" =~ ^[a-zA-Z0-9-]+$ ]]; then
        log "ERROR: Invalid case_id format. Only alphanumeric and hyphens allowed"
        exit 1
    fi
    
    # Execute containment steps
    isolate_network "$hostname" "$case_id"
    terminate_malicious_processes "$hostname" "$case_id"
    lockdown_accounts "$hostname" "$case_id"
    protect_filesystem "$hostname" "$case_id"
    
    # Create forensic backup
    backup_path=$(create_forensic_backup "$hostname" "$case_id")
    
    # Generate report
    report_file=$(generate_report "$hostname" "$case_id" "$backup_path")
    
    log "=== CONTAINMENT PROCEDURE COMPLETED ==="
    log "Backup location: $backup_path"
    log "Report file: $report_file"
    
    # Log to notify.log for KPI calculation
    echo "$(date '+%Y-%m-%d %H:%M:%S') STEP: Containment executed" | tee -a logs/notify.log
    
    # Return success
    echo "SUCCESS: Host $hostname contained successfully"
    echo "Case ID: $case_id"
    echo "Backup: $backup_path"
    echo "Report: $report_file"
}

# Function to show usage
usage() {
    echo "Usage: $0 <hostname> <case_id>"
    echo "  hostname: Target hostname to contain"
    echo "  case_id: Case identifier for tracking"
    echo ""
    echo "Environment variables:"
    echo "  SIMULATION_MODE: true (default) or false"
    echo "  LOG_FILE: Path to log file (default: ./logs/containment.log)"
    echo "  BACKUP_DIR: Directory for backups (default: ./backups)"
    echo ""
    echo "Examples:"
    echo "  $0 WIN-001 CASE-12345"
    echo "  SIMULATION_MODE=false $0 WIN-001 CASE-12345"
}

# Parse command line arguments
if [ $# -lt 2 ]; then
    usage
    exit 1
fi

HOSTNAME="$1"
CASE_ID="$2"

# Execute main function
contain_host "$HOSTNAME" "$CASE_ID"
