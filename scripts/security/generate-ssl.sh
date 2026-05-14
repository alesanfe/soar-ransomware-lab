#!/bin/bash
# SOAR Ransomware Lab - SSL Certificate Generator
# Generates self-signed certificates for local development

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local color=$1
    shift
    echo -e "${color}[$(date +'%Y-%m-%d %H:%M:%S')] $*${NC}"
}

success() {
    log "$GREEN" "✓ $*"
}

error() {
    log "$RED" "✗ $*"
    exit 1
}

warning() {
    log "$YELLOW" "⚠ $*"
}

info() {
    log "$BLUE" "ℹ $*"
}

# Configuration
SSL_DIR="./ssl"
CONFIG_DIR="./ssl/config"
CERT_VALIDITY_DAYS=365
COUNTRY="US"
STATE="CA"
LOCALITY="San Francisco"
ORGANIZATION="SOAR Ransomware Lab"
ORG_UNIT="Security Team"

# Default domain for local development
DOMAIN=${DOMAIN:-"localhost"}
EMAIL=${EMAIL:-"admin@soar.local"}

# Certificate paths
SSL_CERT="${SSL_DIR}/soar-lab.crt"
SSL_KEY="${SSL_DIR}/soar-lab.key"
SSL_CA_CERT="${SSL_DIR}/ca.crt"
SSL_CA_KEY="${SSL_DIR}/ca.key"

# Service-specific certificates
SERVICES=("thehive" "cortex" "shuffle" "grafana" "prometheus" "misp" "opencti" "minio" "elasticsearch")

# Check if OpenSSL is available
check_dependencies() {
    info "Checking dependencies..."
    
    if ! command -v openssl &> /dev/null; then
        error "OpenSSL is not installed. Please install OpenSSL first."
    fi
    
    success "Dependencies check passed"
}

# Create SSL directory structure
create_directories() {
    info "Creating SSL directory structure..."
    
    mkdir -p "$SSL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "${SSL_DIR}/services"
    
    success "SSL directories created"
}

# Generate CA certificate
generate_ca() {
    info "Generating Certificate Authority..."
    
    # CA private key
    openssl genrsa -out "$SSL_CA_KEY" 4096
    
    # CA certificate
    openssl req -new -x509 -days "$CERT_VALIDITY_DAYS" -key "$SSL_CA_KEY" -out "$SSL_CA_CERT" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORG_UNIT/CN=SOAR Lab CA/emailAddress=$EMAIL"
    
    success "CA certificate generated"
}

# Generate server certificate
generate_server_cert() {
    local service_name=$1
    local service_domain=${2:-"$service_name.$DOMAIN"}
    local cert_dir="${SSL_DIR}/services"
    
    info "Generating certificate for $service_name ($service_domain)..."
    
    # Create service-specific directory
    mkdir -p "$cert_dir/$service_name"
    
    # Generate private key
    openssl genrsa -out "$cert_dir/$service_name/key.pem" 2048
    
    # Create CSR configuration
    cat > "$CONFIG_DIR/${service_name}.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $LOCALITY
O = $ORGANIZATION
OU = $ORG_UNIT
CN = $service_domain

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $service_domain
DNS.2 = localhost
DNS.3 = *.$service_domain
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
    
    # Generate CSR
    openssl req -new -key "$cert_dir/$service_name/key.pem" \
        -out "$cert_dir/$service_name/csr.pem" \
        -config "$CONFIG_DIR/${service_name}.conf"
    
    # Sign certificate with CA
    openssl x509 -req -in "$cert_dir/$service_name/csr.pem" \
        -CA "$SSL_CA_CERT" -CAkey "$SSL_CA_KEY" -CAcreateserial \
        -out "$cert_dir/$service_name/cert.pem" \
        -days "$CERT_VALIDITY_DAYS" \
        -extensions v3_req \
        -extfile "$CONFIG_DIR/${service_name}.conf"
    
    # Create combined certificate file (cert + chain)
    cat "$cert_dir/$service_name/cert.pem" "$SSL_CA_CERT" > "$cert_dir/$service_name/fullchain.pem"
    
    # Clean up CSR
    rm "$cert_dir/$service_name/csr.pem"
    
    success "Certificate generated for $service_name"
}

# Generate main SOAR lab certificate
generate_main_cert() {
    info "Generating main SOAR Lab certificate..."
    
    # Generate private key
    openssl genrsa -out "$SSL_KEY" 2048
    
    # Create CSR configuration
    cat > "$CONFIG_DIR/soar-lab.conf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $LOCALITY
O = $ORGANIZATION
OU = $ORG_UNIT
CN = $DOMAIN

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = localhost
DNS.3 = *.localhost
DNS.4 = soar.local
DNS.5 = *.soar.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF
    
    # Generate CSR
    openssl req -new -key "$SSL_KEY" \
        -out "$SSL_DIR/soar-lab.csr" \
        -config "$CONFIG_DIR/soar-lab.conf"
    
    # Sign certificate with CA
    openssl x509 -req -in "$SSL_DIR/soar-lab.csr" \
        -CA "$SSL_CA_CERT" -CAkey "$SSL_CA_KEY" -CAcreateserial \
        -out "$SSL_CERT" \
        -days "$CERT_VALIDITY_DAYS" \
        -extensions v3_req \
        -extfile "$CONFIG_DIR/soar-lab.conf"
    
    # Create full chain
    cat "$SSL_CERT" "$SSL_CA_CERT" > "$SSL_DIR/soar-lab-fullchain.crt"
    
    # Clean up CSR
    rm "$SSL_DIR/soar-lab.csr"
    
    success "Main SOAR Lab certificate generated"
}

# Set proper permissions
set_permissions() {
    info "Setting SSL certificate permissions..."
    
    # Set restrictive permissions for private keys
    chmod 600 "$SSL_KEY" "$SSL_CA_KEY"
    chmod 600 "${SSL_DIR}/services"/*/key.pem
    
    # Set readable permissions for certificates
    chmod 644 "$SSL_CERT" "$SSL_CA_CERT"
    chmod 644 "${SSL_DIR}/services"/*/cert.pem
    chmod 644 "${SSL_DIR}/services"/*/fullchain.pem
    
    # Set directory permissions
    chmod 755 "$SSL_DIR"
    chmod 755 "${SSL_DIR}/services"
    
    success "SSL certificate permissions set"
}

# Verify certificates
verify_certificates() {
    info "Verifying generated certificates..."
    
    # Verify main certificate
    if openssl verify -CAfile "$SSL_CA_CERT" "$SSL_CERT" &>/dev/null; then
        success "Main certificate verification passed"
    else
        error "Main certificate verification failed"
    fi
    
    # Verify service certificates
    for service in "${SERVICES[@]}"; do
        local cert_file="${SSL_DIR}/services/$service/cert.pem"
        if [[ -f "$cert_file" ]]; then
            if openssl verify -CAfile "$SSL_CA_CERT" "$cert_file" &>/dev/null; then
                success "$service certificate verification passed"
            else
                error "$service certificate verification failed"
            fi
        fi
    done
}

# Display certificate information
display_info() {
    info "SSL Certificate Information:"
    echo
    
    echo "Main Certificate:"
    echo "  Certificate: $SSL_CERT"
    echo "  Private Key: $SSL_KEY"
    echo "  CA Certificate: $SSL_CA_CERT"
    echo
    
    # Show certificate details
    if [[ -f "$SSL_CERT" ]]; then
        echo "Certificate Details:"
        openssl x509 -in "$SSL_CERT" -noout -text | grep -E "(Subject:|Issuer:|Not Before:|Not After:)" | sed 's/^/    /'
        echo
    fi
    
    echo "Service Certificates:"
    for service in "${SERVICES[@]}"; do
        local cert_dir="${SSL_DIR}/services/$service"
        if [[ -d "$cert_dir" ]]; then
            echo "  $service: $cert_dir/"
        fi
    done
    echo
    
    warning "IMPORTANT: These are self-signed certificates for local development only!"
    warning "You will need to import the CA certificate ($SSL_CA_CERT) into your browser/system."
}

# Clean up existing certificates
cleanup() {
    warning "Cleaning up existing SSL certificates..."
    rm -rf "$SSL_DIR"
    rm -rf "$CONFIG_DIR"
    success "Cleanup completed"
}

# Generate certificates for Docker services
generate_docker_certs() {
    info "Generating certificates for Docker services..."
    
    # Create Docker-compatible directory structure
    mkdir -p "${SSL_DIR}/docker/thehive"
    mkdir -p "${SSL_DIR}/docker/cortex"
    mkdir -p "${SSL_DIR}/docker/grafana"
    mkdir -p "${SSL_DIR}/docker/prometheus"
    
    # Copy certificates to Docker directories
    for service in "${SERVICES[@]}"; do
        local src_dir="${SSL_DIR}/services/$service"
        local dst_dir="${SSL_DIR}/docker/$service"
        
        if [[ -d "$src_dir" && -d "$dst_dir" ]]; then
            cp "$src_dir/cert.pem" "$dst_dir/server.crt"
            cp "$src_dir/key.pem" "$dst_dir/server.key"
            cp "$src_dir/fullchain.pem" "$dst_dir/fullchain.crt"
            success "Docker certificates prepared for $service"
        fi
    done
}

# Main function
main() {
    echo "=========================================="
    echo "SOAR Ransomware Lab - SSL Certificate Generator"
    echo "=========================================="
    echo
    
    # Parse command line arguments
    local cleanup_only=false
    local skip_cleanup=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                cleanup_only=true
                shift
                ;;
            --skip-cleanup)
                skip_cleanup=true
                shift
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --email)
                EMAIL="$2"
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
    
    # Handle cleanup only
    if [[ "$cleanup_only" == true ]]; then
        cleanup
        exit 0
    fi
    
    # Clean up existing certificates unless skipped
    if [[ "$skip_cleanup" != true ]]; then
        cleanup
    fi
    
    # Generate certificates
    check_dependencies
    create_directories
    generate_ca
    generate_main_cert
    
    # Generate service-specific certificates
    for service in "${SERVICES[@]}"; do
        generate_server_cert "$service"
    done
    
    # Prepare Docker certificates
    generate_docker_certs
    
    # Finalize
    set_permissions
    verify_certificates
    display_info
    
    success "SSL certificates generated successfully!"
    echo
    info "Next steps:"
    echo "  1. Import $SSL_CA_CERT into your browser/system"
    echo "  2. Update your docker-compose.yml files to use the certificates"
    echo "  3. Restart your services with HTTPS enabled"
}

# Run main function with all arguments
main "$@"
