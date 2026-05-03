
#!/usr/bin/env bash

# SOAR Ransomware Lab - TLS Certificate Generator
# Generates self-signed certificates for TheHive and Shuffle services

set -euo pipefail

# Configuration
CERT_DIR="${CERT_DIR:-./certs}"
COUNTRY="${COUNTRY:-ES}"
STATE="${STATE:-Madrid}"
LOCALITY="${LOCALITY:-Madrid}"
ORGANIZATION="${ORGANIZATION:-SOAR Lab}"
ORG_UNIT="${ORG_UNIT:-Security}"
COMMON_NAME="${COMMON_NAME:-localhost}"
DAYS_VALID="${DAYS_VALID:-365}"

# Create certificates directory
mkdir -p "${CERT_DIR}"

echo "Generating self-signed certificates for SOAR Lab..."
echo "Certificate directory: ${CERT_DIR}"
echo "Common Name: ${COMMON_NAME}"
echo "Valid for: ${DAYS_VALID} days"

# Generate private key
openssl genrsa -out "${CERT_DIR}/thehive.key" 2048

# Generate certificate signing request
openssl req -new -key "${CERT_DIR}/thehive.key" -out "${CERT_DIR}/thehive.csr" -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORGANIZATION}/OU=${ORG_UNIT}/CN=${COMMON_NAME}"

# Generate self-signed certificate
openssl x509 -req -in "${CERT_DIR}/thehive.csr" -signkey "${CERT_DIR}/thehive.key" -out "${CERT_DIR}/thehive.crt" -days "${DAYS_VALID}"

# Generate combined PEM file for Shuffle
cat "${CERT_DIR}/thehive.crt" "${CERT_DIR}/thehive.key" > "${CERT_DIR}/shuffle.pem"

# Set appropriate permissions
chmod 600 "${CERT_DIR}"/*.key
chmod 644 "${CERT_DIR}"/*.crt
chmod 644 "${CERT_DIR}"/*.pem

# Clean up CSR
rm -f "${CERT_DIR}/thehive.csr"

echo "Certificates generated successfully!"
echo "Files created:"
echo "  - ${CERT_DIR}/thehive.key (private key)"
echo "  - ${CERT_DIR}/thehive.crt (certificate)"
echo "  - ${CERT_DIR}/shuffle.pem (combined for Shuffle)"
echo ""
echo "Add these to your .env file:"
echo "  ENABLE_TLS=true"
echo "  TLS_CERT_PATH=${CERT_DIR}/thehive.crt"
echo "  TLS_KEY_PATH=${CERT_DIR}/thehive.key"
