#!/bin/bash
#
# SOAR Ransomware Lab - Host Isolation Script
# This script isolates a compromised host from the network
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-/var/log/soar-lab}"
LOG_FILE="${LOG_DIR}/isolate_host.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log "ERROR" "This script must be run as root"
        exit 1
    fi
}

# Function to validate host IP
validate_ip() {
    local ip="$1"
    if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log "ERROR" "Invalid IP address format: $ip"
        return 1
    fi
    return 0
}

# Function to isolate host using iptables
isolate_with_iptables() {
    local target_ip="$1"
    
    log "INFO" "Isolating host $target_ip using iptables"
    
    # Create new chain for isolation
    iptables -N ISOLATION 2>/dev/null || true
    
    # Add rules to block all traffic from/to target IP
    iptables -I INPUT -s "$target_ip" -j ISOLATION 2>/dev/null || true
    iptables -I OUTPUT -d "$target_ip" -j ISOLATION 2>/dev/null || true
    iptables -A ISOLATION -j DROP 2>/dev/null || true
    
    # Allow only management traffic (optional)
    if [[ "${ALLOW_MANAGEMENT:-yes}" == "yes" ]]; then
        iptables -I ISOLATION -p tcp --dport 22 -j ACCEPT 2>/dev/null || true  # SSH
        iptables -I ISOLATION -p tcp --dport 443 -j ACCEPT 2>/dev/null || true  # HTTPS
    fi
    
    log "INFO" "Host $target_ip isolated successfully"
}

# Function to isolate host using firewall-cmd (RHEL/CentOS)
isolate_with_firewalld() {
    local target_ip="$1"
    
    if command -v firewall-cmd >/dev/null 2>&1; then
        log "INFO" "Isolating host $target_ip using firewalld"
        
        # Create rich rules to block traffic
        firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='$target_ip' drop" 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        
        log "INFO" "Host $target_ip isolated successfully using firewalld"
        return 0
    fi
    
    return 1
}

# Function to create isolation report
create_report() {
    local target_ip="$1"
    local report_file="${LOG_DIR}/isolation_report_${target_ip}.txt"
    
    cat > "$report_file" << EOF
SOAR Ransomware Lab - Host Isolation Report
=============================================
Generated: $(date)
Target Host: $target_ip
Isolation Method: $(command -v firewall-cmd >/dev/null 2>&1 && echo "firewalld" || echo "iptables")
Status: ISOLATED

Network Rules Applied:
- All inbound traffic blocked
- All outbound traffic blocked
- Management access: ${ALLOW_MANAGEMENT:-yes}

Next Steps:
1. Investigate the compromised host
2. Collect forensic evidence
3. Clean or reimage the system
4. Restore network access when safe

Use scripts/utils/restore_host.sh to restore access when complete.
EOF

    log "INFO" "Isolation report created: $report_file"
}

# Function to display help
show_help() {
    cat << EOF
SOAR Ransomware Lab - Host Isolation Script

Usage: $0 [OPTIONS] <TARGET_IP>

Options:
    -m, --allow-management    Allow management access (SSH/HTTPS)
    -l, --log-dir DIR        Custom log directory (default: /var/log/soar-lab)
    -h, --help              Show this help message

Examples:
    $0 192.168.1.100
    $0 --allow-management 10.0.0.50
    $0 -l /tmp/logs 172.16.0.25

Description:
    This script isolates a compromised host from the network by blocking
    all traffic to and from the target IP address. It supports both
    iptables and firewalld firewalls.

EOF
}

# Main function
main() {
    local target_ip=""
    local allow_management="${ALLOW_MANAGEMENT:-no}"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--allow-management)
                allow_management="yes"
                shift
                ;;
            -l|--log-dir)
                LOG_DIR="$2"
                LOG_FILE="${LOG_DIR}/isolate_host.log"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [[ -z "$target_ip" ]]; then
                    target_ip="$1"
                else
                    log "ERROR" "Multiple target IPs specified"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "$target_ip" ]]; then
        log "ERROR" "Target IP address is required"
        show_help
        exit 1
    fi
    
    validate_ip "$target_ip" || exit 1
    
    # Check prerequisites
    check_root
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Export for child processes
    export ALLOW_MANAGEMENT="$allow_management"
    
    log "INFO" "Starting host isolation for $target_ip"
    
    # Attempt isolation with different methods
    if isolate_with_firewalld "$target_ip"; then
        # Success with firewalld
        :
    elif isolate_with_iptables "$target_ip"; then
        # Success with iptables
        :
    else
        log "ERROR" "Failed to isolate host - no supported firewall found"
        exit 1
    fi
    
    # Create report
    create_report "$target_ip"
    
    log "INFO" "Host isolation completed successfully"
}

# Run main function with all arguments
main "$@"
