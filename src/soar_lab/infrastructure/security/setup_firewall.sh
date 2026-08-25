#!/bin/bash

# SOAR Ransomware Lab - Firewall Configuration Script
# Configures UFW firewall for secure deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ARTIFACTS_DIR="${ARTIFACTS_DIR:-./runtime}"
LOG_FILE="${LOG_FILE:-${ARTIFACTS_DIR}/logs/firewall.log}"
BACKUP_RULES_FILE="/etc/ufw/before.rules.backup"

# Ensure log directory exists
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if UFW is installed
check_ufw() {
    if ! command -v ufw &> /dev/null; then
        error "UFW (Uncomplicated Firewall) not found. Installing..."
        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y ufw
        elif command -v yum &> /dev/null; then
            yum install -y ufw
        else
            error "Unsupported package manager. Please install UFW manually."
            exit 1
        fi
    fi
}

# Backup existing rules
backup_rules() {
    if [[ -f "/etc/ufw/before.rules" ]]; then
        cp "/etc/ufw/before.rules" "$BACKUP_RULES_FILE"
        log "Existing UFW rules backed up to $BACKUP_RULES_FILE"
    fi
}

# Configure UFW basic settings
configure_ufw_basic() {
    log "Configuring basic UFW settings..."
    
    # Reset UFW to default settings
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    ufw default deny forwarded
    
    # Allow loopback
    ufw allow in on lo
    
    # Allow established and related connections
    ufw allow in from any to any state ESTABLISHED,RELATED
    
    log "Basic UFW configuration completed"
}

# Configure Docker network rules
configure_docker_rules() {
    log "Configuring Docker network rules..."
    
    # Create custom UFW before.rules for Docker
    cat > /etc/ufw/before.rules << 'EOF'
#
# rules.before
#
# Rules that should be run before the ufw command line added rules.
# Rules that want to masquerade should use this chain.
#
# Don't delete these required lines, otherwise there will be errors
*filter
:ufw-before-input - [0:0]
:ufw-before-output - [0:0]
:ufw-before-forward - [0:0]
:ufw-not-local - [0:0]

# Don't attempt to firewall internal loopback traffic
-A ufw-before-input -i lo -j ACCEPT

# Accept packets from DHCP server
-A ufw-before-input -p udp -s 0.0.0.0/0 --sport 67 --dport 68 -j ACCEPT

# Allow Docker internal traffic
-A ufw-before-forward -i docker0 -o docker0 -j ACCEPT
-A ufw-before-forward -s 172.17.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.18.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.19.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.20.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.21.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.22.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.23.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.24.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.25.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.26.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.27.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.28.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.29.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.30.0.0/16 -j ACCEPT
-A ufw-before-forward -s 172.31.0.0/16 -j ACCEPT

# Allow Docker container traffic to host
-A ufw-before-input -i docker0 -j ACCEPT
-A ufw-before-input -i br-+ -j ACCEPT

# Don't delete these required lines, otherwise there will be errors
COMMIT
EOF

    log "Docker network rules configured"
}

# Configure SOAR service ports
configure_soaR_ports() {
    log "Configuring SOAR service ports..."
    
    # HTTP/HTTPS (through Nginx)
    ufw allow 80/tcp comment "HTTP"
    ufw allow 443/tcp comment "HTTPS"
    
    # SSH (management)
    ufw allow 22/tcp comment "SSH"
    
    # Optional: Direct access to services (commented out for security)
    # Uncomment if direct access is needed without Nginx proxy
    # ufw allow 9000/tcp comment "TheHive (direct)"
    # ufw allow 9001/tcp comment "Cortex (direct)"
    # ufw allow 8081/tcp comment "Shuffle Frontend (direct)"
    # ufw allow 5001/tcp comment "Shuffle API (direct)"
    # ufw allow 19200/tcp comment "Elasticsearch (direct)"
    
    log "SOAR service ports configured"
}

# Configure rate limiting
configure_rate_limiting() {
    log "Configuring rate limiting..."
    
    # Rate limit SSH to prevent brute force
    ufw limit ssh
    
    # Rate limit HTTP/HTTPS
    ufw limit 80/tcp
    ufw limit 443/tcp
    
    log "Rate limiting configured"
}

# Configure logging
configure_logging() {
    log "Configuring UFW logging..."
    
    # Enable logging
    ufw logging medium
    
    # Log denied packets
    ufw logging on
    
    log "UFW logging configured"
}

# Enable UFW
enable_ufw() {
    log "Enabling UFW firewall..."
    
    # Enable UFW
    ufw --force enable
    
    log "UFW firewall enabled successfully"
}

# Show firewall status
show_status() {
    log "Current firewall status:"
    ufw status verbose
    
    log "Active rules:"
    ufw status numbered
}

# Test firewall configuration
test_firewall() {
    log "Testing firewall configuration..."
    
    # Test basic connectivity
    if ping -c 1 127.0.0.1 &> /dev/null; then
        log "✓ Loopback connectivity test passed"
    else
        error "✗ Loopback connectivity test failed"
        return 1
    fi
    
    # Test UFW status
    if ufw status | grep -q "Status: active"; then
        log "✓ UFW is active"
    else
        error "✗ UFW is not active"
        return 1
    fi
    
    # Test port accessibility (if services are running)
    local ports=(80 443)
    for port in "${ports[@]}"; do
        if netstat -ln | grep -q ":$port "; then
            log "✓ Port $port is listening"
        else
            warn "Port $port is not listening (services may not be running)"
        fi
    done
    
    log "Firewall configuration test completed"
}

# Restore backup rules
restore_backup() {
    if [[ -f "$BACKUP_RULES_FILE" ]]; then
        log "Restoring backup rules from $BACKUP_RULES_FILE"
        cp "$BACKUP_RULES_FILE" "/etc/ufw/before.rules"
        ufw --force reload
        log "Backup rules restored"
    else
        error "No backup file found at $BACKUP_RULES_FILE"
        exit 1
    fi
}

# Generate firewall report
generate_report() {
    local report_file="reports/firewall_report_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p reports
    
    cat > "$report_file" << EOF
SOAR Ransomware Lab - Firewall Configuration Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

=== Firewall Status ===
$(ufw status verbose)

=== Active Rules ===
$(ufw status numbered)

=== Docker Network Configuration ===
$(docker network ls 2>/dev/null || echo "Docker not running")

=== Listening Ports ===
$(netstat -tlnp 2>/dev/null | grep LISTEN || echo "netstat not available")

=== UFW Configuration Files ===
/etc/ufw/before.rules
/etc/ufw/user.rules
/etc/ufw/user6.rules

=== Recommendations ===
1. Regularly review firewall logs: sudo tail -f /var/log/ufw.log
2. Monitor for unusual connection attempts
3. Consider implementing fail2ban for additional protection
4. Regular security audits of firewall rules
5. Document any custom rules for team awareness

EOF
    
    log "Firewall report generated: $report_file"
}

# Help function
show_help() {
    cat << EOF
SOAR Ransomware Lab - Firewall Configuration Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -s, --status        Show current firewall status
    -t, --test          Test firewall configuration
    -r, --report        Generate firewall report
    -b, --backup        Backup current rules
    --restore           Restore from backup
    --dry-run           Show what would be configured without applying

EXAMPLES:
    $0                  # Configure firewall with default settings
    $0 -s              # Show current status
    $0 -t              # Test configuration
    $0 -r              # Generate report
    $0 --dry-run       # Preview configuration

REQUIREMENTS:
    - Root privileges (sudo)
    - UFW firewall package
    - Docker (if running containers)

SECURITY NOTES:
    - This script configures a restrictive firewall policy
    - Only essential ports are opened (80, 443, 22)
    - All other inbound traffic is denied by default
    - Docker internal traffic is properly handled
    - Rate limiting is enabled for common services

EOF
}

# Main function
main() {
    log "Starting SOAR Lab firewall configuration..."
    
    # Check prerequisites
    check_root
    check_ufw
    
    # Backup existing rules
    backup_rules
    
    # Configure firewall
    configure_ufw_basic
    configure_docker_rules
    configure_soaR_ports
    configure_rate_limiting
    configure_logging
    
    # Enable firewall
    enable_ufw
    
    # Show status
    show_status
    
    # Test configuration
    test_firewall
    
    # Generate report
    generate_report
    
    log "Firewall configuration completed successfully"
    log "Review the status above and adjust if necessary"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--status)
            check_root
            show_status
            exit 0
            ;;
        -t|--test)
            check_root
            test_firewall
            exit 0
            ;;
        -r|--report)
            generate_report
            exit 0
            ;;
        -b|--backup)
            check_root
            backup_rules
            log "Rules backed up successfully"
            exit 0
            ;;
        --restore)
            check_root
            restore_backup
            exit 0
            ;;
        --dry-run)
            log "DRY RUN - Would configure:"
            log "  - Reset UFW to default settings"
            log "  - Set default deny policies"
            log "  - Allow loopback traffic"
            log "  - Configure Docker network rules"
            log "  - Open ports: 80 (HTTP), 443 (HTTPS), 22 (SSH)"
            log "  - Configure rate limiting"
            log "  - Enable logging"
            log "  - Enable UFW firewall"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main
