#!/bin/bash
#
# SOAR Ransomware Lab - Certificate Generation Script
# This script generates SSL/TLS certificates for secure communications
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${CERT_DIR:-$(dirname "$SCRIPT_DIR")/../certs}"
LOG_DIR="${LOG_DIR:-/var/log/soar-lab}"
LOG_FILE="${LOG_DIR}/gen_certs.log"

# Certificate settings
COUNTRY="${CERT_COUNTRY:-US}"
STATE="${CERT_STATE:-California}"
CITY="${CERT_CITY:-San Francisco}"
ORGANIZATION="${CERT_ORG:-SOAR Ransomware Lab}"
ORG_UNIT="${CERT_ORG_UNIT:-Security Team}"
COMMON_NAME="${CERT_CN:-localhost}"
EMAIL="${CERT_EMAIL:-security@soar-lab.local}"

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

# Function to check if OpenSSL is available
check_openssl() {
    if ! command -v openssl >/dev/null 2>&1; then
        log "ERROR" "OpenSSL is not installed or not in PATH"
        exit 1
    fi
}

# Function to create directories
create_directories() {
    mkdir -p "$CERT_DIR"
    mkdir -p "$LOG_DIR"
    log "INFO" "Created directories: $CERT_DIR, $LOG_DIR"
}

# Function to generate CA certificate
generate_ca() {
    log "INFO" "Generating CA certificate"
    
    # Generate CA private key
    openssl genrsa -out "$CERT_DIR/ca.key" 4096 2>/dev/null
    chmod 600 "$CERT_DIR/ca.key"
    
    # Generate CA certificate
    openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" \
        -out "$CERT_DIR/ca.crt" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORG_UNIT/CN=$ORGANIZATION CA/emailAddress=$EMAIL" \
        2>/dev/null
    
    log "INFO" "CA certificate generated successfully"
}

# Function to generate server certificate
generate_server_cert() {
    local hostname="$1"
    log "INFO" "Generating server certificate for $hostname"
    
    # Create config file for SAN
    local config_file="$CERT_DIR/${hostname}.conf"
    cat > "$config_file" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORGANIZATION
OU = $ORG_UNIT
CN = $hostname
emailAddress = $EMAIL

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $hostname
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

    # Generate private key
    openssl genrsa -out "$CERT_DIR/${hostname}.key" 2048 2>/dev/null
    chmod 600 "$CERT_DIR/${hostname}.key"
    
    # Generate certificate signing request
    openssl req -new -key "$CERT_DIR/${hostname}.key" \
        -out "$CERT_DIR/${hostname}.csr" \
        -config "$config_file" \
        2>/dev/null
    
    # Sign certificate with CA
    openssl x509 -req -days 365 -in "$CERT_DIR/${hostname}.csr" \
        -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
        -CAcreateserial -out "$CERT_DIR/${hostname}.crt" \
        -extensions v3_req -extfile "$config_file" \
        2>/dev/null
    
    # Clean up CSR and config
    rm -f "$CERT_DIR/${hostname}.csr" "$config_file"
    
    log "INFO" "Server certificate for $hostname generated successfully"
}

# Function to generate client certificate
generate_client_cert() {
    local client_name="$1"
    log "INFO" "Generating client certificate for $client_name"
    
    # Create config file
    local config_file="$CERT_DIR/${client_name}.conf"
    cat > "$config_file" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORGANIZATION
OU = $ORG_UNIT
CN = $client_name
emailAddress = $EMAIL

[v3_req]
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

    # Generate private key
    openssl genrsa -out "$CERT_DIR/${client_name}.key" 2048 2>/dev/null
    chmod 600 "$CERT_DIR/${client_name}.key"
    
    # Generate certificate signing request
    openssl req -new -key "$CERT_DIR/${client_name}.key" \
        -out "$CERT_DIR/${client_name}.csr" \
        -config "$config_file" \
        2>/dev/null
    
    # Sign certificate with CA
    openssl x509 -req -days 365 -in "$CERT_DIR/${client_name}.csr" \
        -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
        -CAcreateserial -out "$CERT_DIR/${client_name}.crt" \
        -extensions v3_req -extfile "$config_file" \
        2>/dev/null
    
    # Clean up CSR and config
    rm -f "$CERT_DIR/${client_name}.csr" "$config_file"
    
    log "INFO" "Client certificate for $client_name generated successfully"
}

# Function to verify certificates
verify_certificates() {
    log "INFO" "Verifying generated certificates"
    
    # Verify CA certificate
    if openssl x509 -in "$CERT_DIR/ca.crt" -text -noout >/dev/null 2>&1; then
        log "INFO" "CA certificate verified"
    else
        log "ERROR" "CA certificate verification failed"
        return 1
    fi
    
    # Verify server certificates
    for cert in "$CERT_DIR"/*.crt; do
        if [[ "$cert" != "$CERT_DIR/ca.crt" ]]; then
            local hostname=$(basename "$cert" .crt)
            if openssl verify -CAfile "$CERT_DIR/ca.crt" "$cert" >/dev/null 2>&1; then
                log "INFO" "Certificate for $hostname verified"
            else
                log "ERROR" "Certificate verification failed for $hostname"
                return 1
            fi
        fi
    done
    
    log "INFO" "All certificates verified successfully"
}

# Function to create certificate bundle
create_bundle() {
    log "INFO" "Creating certificate bundle"
    
    # Create full chain file
    cat "$CERT_DIR/ca.crt" > "$CERT_DIR/fullchain.pem"
    
    log "INFO" "Certificate bundle created: $CERT_DIR/fullchain.pem"
}

# Function to display certificate info
show_cert_info() {
    local cert_file="$1"
    
    if [[ -f "$cert_file" ]]; then
        echo "Certificate Information for $cert_file:"
        echo "=========================================="
        openssl x509 -in "$cert_file" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"
        echo ""
    fi
}

# Function to display help
show_help() {
    cat << EOF
SOAR Ransomware Lab - Certificate Generation Script

Usage: $0 [OPTIONS] [HOSTNAME...]

Options:
    -c, --cert-dir DIR       Certificate directory (default: ../certs)
    -l, --log-dir DIR        Log directory (default: /var/log/soar-lab)
    -C, --country COUNTRY    Country code (default: US)
    -S, --state STATE        State/province (default: California)
    -L, --city CITY          City (default: San Francisco)
    -O, --organization ORG   Organization (default: SOAR Ransomware Lab)
    -U, --org-unit UNIT       Organizational unit (default: Security Team)
    -e, --email EMAIL        Email address (default: security@soar-lab.local)
    -n, --common-name NAME    Common name (default: localhost)
    -v, --verify             Verify existing certificates
    -i, --info FILE          Show certificate information
    -h, --help              Show this help message

Examples:
    $0                                    # Generate CA and localhost cert
    $0 thehive cortex                    # Generate certs for specific hosts
    $0 -c /etc/ssl/certs -O "My Org" web # Custom directory and org
    $0 --verify                          # Verify all certificates
    $0 --info /path/to/cert.crt         # Show certificate info

Description:
    This script generates SSL/TLS certificates for secure communications
    in the SOAR Ransomware Lab environment. It creates a Certificate
    Authority and server/client certificates with proper SAN extensions.

EOF
}

# Main function
main() {
    local cert_dir=""
    local verify_only=false
    local show_info=""
    local hostnames=()
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--cert-dir)
                CERT_DIR="$2"
                shift 2
                ;;
            -l|--log-dir)
                LOG_DIR="$2"
                LOG_FILE="${LOG_DIR}/gen_certs.log"
                shift 2
                ;;
            -C|--country)
                COUNTRY="$2"
                shift 2
                ;;
            -S|--state)
                STATE="$2"
                shift 2
                ;;
            -L|--city)
                CITY="$2"
                shift 2
                ;;
            -O|--organization)
                ORGANIZATION="$2"
                shift 2
                ;;
            -U|--org-unit)
                ORG_UNIT="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -n|--common-name)
                COMMON_NAME="$2"
                shift 2
                ;;
            -v|--verify)
                verify_only=true
                shift
                ;;
            -i|--info)
                show_info="$2"
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
                hostnames+=("$1")
                shift
                ;;
        esac
    done
    
    # Handle special modes
    if [[ -n "$show_info" ]]; then
        show_cert_info "$show_info"
        exit 0
    fi
    
    if [[ "$verify_only" == true ]]; then
        verify_certificates
        exit $?
    fi
    
    # Check prerequisites
    check_openssl
    
    # Create directories
    create_directories
    
    # Set default hostname if none provided
    if [[ ${#hostnames[@]} -eq 0 ]]; then
        hostnames=("$COMMON_NAME")
    fi
    
    log "INFO" "Starting certificate generation"
    log "INFO" "Certificate directory: $CERT_DIR"
    log "INFO" "Hostnames: ${hostnames[*]}"
    
    # Generate CA certificate
    generate_ca
    
    # Generate server certificates
    for hostname in "${hostnames[@]}"; do
        generate_server_cert "$hostname"
    done
    
    # Create certificate bundle
    create_bundle
    
    # Verify all certificates
    verify_certificates
    
    log "INFO" "Certificate generation completed successfully"
    log "INFO" "Generated files:"
    log "INFO" "  - $CERT_DIR/ca.key (CA private key)"
    log "INFO" "  - $CERT_DIR/ca.crt (CA certificate)"
    log "INFO" "  - $CERT_DIR/fullchain.pem (Certificate bundle)"
    
    for hostname in "${hostnames[@]}"; do
        log "INFO" "  - $CERT_DIR/${hostname}.key (Private key)"
        log "INFO" "  - $CERT_DIR/${hostname}.crt (Certificate)"
    done
}

# Run main function with all arguments
main "$@"
