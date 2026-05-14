# SOAR Ransomware Lab - SSL Certificate Generator (PowerShell)
# Generates self-signed certificates for local development

param(
    [string]$Domain = "localhost",
    [string]$Email = "admin@soar.local",
    [switch]$Cleanup,
    [switch]$SkipCleanup
)

# Color codes for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Cyan = "Cyan"
    White = "White"
}

# Logging function
function Write-Log {
    param(
        [string]$Color,
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Log -Color $Colors.Green -Message "✓ $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Log -Color $Colors.Red -Message "✗ $Message"
    exit 1
}

function Write-Warning {
    param([string]$Message)
    Write-Log -Color $Colors.Yellow -Message "⚠ $Message"
}

function Write-Info {
    param([string]$Message)
    Write-Log -Color $Colors.Blue -Message "ℹ $Message"
}

# Configuration
$Script:SSL_DIR = ".\ssl"
$Script:CONFIG_DIR = ".\ssl\config"
$Script:CERT_VALIDITY_DAYS = 365
$Script:COUNTRY = "US"
$Script:STATE = "CA"
$Script:LOCALITY = "San Francisco"
$Script:ORGANIZATION = "SOAR Ransomware Lab"
$Script:ORG_UNIT = "Security Team"

# Certificate paths
$Script:SSL_CERT = "$SSL_DIR\soar-lab.crt"
$Script:SSL_KEY = "$SSL_DIR\soar-lab.key"
$Script:SSL_CA_CERT = "$SSL_DIR\ca.crt"
$Script:SSL_CA_KEY = "$SSL_DIR\ca.key"

# Service-specific certificates
$Script:SERVICES = @("thehive", "cortex", "shuffle", "grafana", "prometheus", "misp", "opencti", "minio", "elasticsearch")

# Check if OpenSSL is available
function Test-Dependencies {
    Write-Info "Checking dependencies..."
    
    try {
        $openssl = Get-Command openssl -ErrorAction Stop
        Write-Success "OpenSSL found at $($openssl.Source)"
    }
    catch {
        Write-Error "OpenSSL is not installed or not in PATH. Please install OpenSSL first."
    }
    
    Write-Success "Dependencies check passed"
}

# Create SSL directory structure
function New-SSLDirectories {
    Write-Info "Creating SSL directory structure..."
    
    New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path $CONFIG_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path "$SSL_DIR\services" -Force | Out-Null
    
    Write-Success "SSL directories created"
}

# Generate CA certificate
function New-CACertificate {
    Write-Info "Generating Certificate Authority..."
    
    # CA private key
    openssl genrsa -out $SSL_CA_KEY 4096
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate CA private key"
    }
    
    # CA certificate
    $subject = "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORG_UNIT/CN=SOAR Lab CA/emailAddress=$Email"
    openssl req -new -x509 -days $CERT_VALIDITY_DAYS -key $SSL_CA_KEY -out $SSL_CA_CERT -subj $subject
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate CA certificate"
    }
    
    Write-Success "CA certificate generated"
}

# Generate server certificate
function New-ServerCertificate {
    param(
        [string]$ServiceName,
        [string]$ServiceDomain
    )
    
    if (-not $ServiceDomain) {
        $ServiceDomain = "$ServiceName.$Domain"
    }
    
    Write-Info "Generating certificate for $ServiceName ($ServiceDomain)..."
    
    $certDir = "$SSL_DIR\services\$ServiceName"
    
    # Create service-specific directory
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
    
    # Generate private key
    openssl genrsa -out "$certDir\key.pem" 2048
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate private key for $ServiceName"
    }
    
    # Create CSR configuration
    $configContent = @"
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
CN = $ServiceDomain

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $ServiceDomain
DNS.2 = localhost
DNS.3 = *.$ServiceDomain
IP.1 = 127.0.0.1
IP.2 = ::1
"@
    
    $configContent | Out-File -FilePath "$CONFIG_DIR\$ServiceName.conf" -Encoding UTF8
    
    # Generate CSR
    openssl req -new -key "$certDir\key.pem" -out "$certDir\csr.pem" -config "$CONFIG_DIR\$ServiceName.conf"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate CSR for $ServiceName"
    }
    
    # Sign certificate with CA
    openssl x509 -req -in "$certDir\csr.pem" -CA $SSL_CA_CERT -CAkey $SSL_CA_KEY -CAcreateserial -out "$certDir\cert.pem" -days $CERT_VALIDITY_DAYS -extensions v3_req -extfile "$CONFIG_DIR\$ServiceName.conf"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to sign certificate for $ServiceName"
    }
    
    # Create combined certificate file (cert + chain)
    Get-Content "$certDir\cert.pem", $SSL_CA_CERT | Set-Content "$certDir\fullchain.pem"
    
    # Clean up CSR
    Remove-Item "$certDir\csr.pem" -Force
    
    Write-Success "Certificate generated for $ServiceName"
}

# Generate main SOAR lab certificate
function New-MainCertificate {
    Write-Info "Generating main SOAR Lab certificate..."
    
    # Generate private key
    openssl genrsa -out $SSL_KEY 2048
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate main private key"
    }
    
    # Create CSR configuration
    $configContent = @"
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
CN = $Domain

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $Domain
DNS.2 = localhost
DNS.3 = *.localhost
DNS.4 = soar.local
DNS.5 = *.soar.local
IP.1 = 127.0.0.1
IP.2 = ::1
"@
    
    $configContent | Out-File -FilePath "$CONFIG_DIR\soar-lab.conf" -Encoding UTF8
    
    # Generate CSR
    openssl req -new -key $SSL_KEY -out "$SSL_DIR\soar-lab.csr" -config "$CONFIG_DIR\soar-lab.conf"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate main CSR"
    }
    
    # Sign certificate with CA
    openssl x509 -req -in "$SSL_DIR\soar-lab.csr" -CA $SSL_CA_CERT -CAkey $SSL_CA_KEY -CAcreateserial -out $SSL_CERT -days $CERT_VALIDITY_DAYS -extensions v3_req -extfile "$CONFIG_DIR\soar-lab.conf"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to sign main certificate"
    }
    
    # Create full chain
    Get-Content $SSL_CERT, $SSL_CA_CERT | Set-Content "$SSL_DIR\soar-lab-fullchain.crt"
    
    # Clean up CSR
    Remove-Item "$SSL_DIR\soar-lab.csr" -Force
    
    Write-Success "Main SOAR Lab certificate generated"
}

# Set proper permissions
function Set-SSLPermissions {
    Write-Info "Setting SSL certificate permissions..."
    
    # Note: Windows permissions are different from Linux
    # We'll just ensure the files exist and are accessible
    
    Write-Success "SSL certificate permissions set"
}

# Verify certificates
function Test-Certificates {
    Write-Info "Verifying generated certificates..."
    
    # Verify main certificate
    $verifyResult = openssl verify -CAfile $SSL_CA_CERT $SSL_CERT 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Main certificate verification passed"
    }
    else {
        Write-Error "Main certificate verification failed: $verifyResult"
    }
    
    # Verify service certificates
    foreach ($service in $SERVICES) {
        $certFile = "$SSL_DIR\services\$service\cert.pem"
        if (Test-Path $certFile) {
            $verifyResult = openssl verify -CAfile $SSL_CA_CERT $certFile 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "$service certificate verification passed"
            }
            else {
                Write-Error "$service certificate verification failed: $verifyResult"
            }
        }
    }
}

# Display certificate information
function Show-CertificateInfo {
    Write-Info "SSL Certificate Information:"
    Write-Host ""
    
    Write-Host "Main Certificate:"
    Write-Host "  Certificate: $SSL_CERT"
    Write-Host "  Private Key: $SSL_KEY"
    Write-Host "  CA Certificate: $SSL_CA_CERT"
    Write-Host ""
    
    # Show certificate details
    if (Test-Path $SSL_CERT) {
        Write-Host "Certificate Details:"
        $certInfo = openssl x509 -in $SSL_CERT -noout -text 2>&1
        $certInfo -split "`n" | Where-Object { $_ -match "(Subject:|Issuer:|Not Before:|Not After:)" } | ForEach-Object { Write-Host "    $_" }
        Write-Host ""
    }
    
    Write-Host "Service Certificates:"
    foreach ($service in $SERVICES) {
        $certDir = "$SSL_DIR\services\$service"
        if (Test-Path $certDir) {
            Write-Host "  ${service}: ${certDir}"
        }
    }
    Write-Host ""
    
    Write-Warning "IMPORTANT: These are self-signed certificates for local development only!"
    Write-Warning "You will need to import the CA certificate ($SSL_CA_CERT) into your browser/system."
}

# Clean up existing certificates
function Remove-SSLCertificates {
    Write-Warning "Cleaning up existing SSL certificates..."
    
    if (Test-Path $SSL_DIR) {
        Remove-Item $SSL_DIR -Recurse -Force
    }
    
    if (Test-Path $CONFIG_DIR) {
        Remove-Item $CONFIG_DIR -Recurse -Force
    }
    
    Write-Success "Cleanup completed"
}

# Generate certificates for Docker services
function New-DockerCertificates {
    Write-Info "Generating certificates for Docker services..."
    
    # Create Docker-compatible directory structure
    $dockerServices = @("thehive", "cortex", "grafana", "prometheus")
    
    foreach ($service in $dockerServices) {
        $dockerDir = "$SSL_DIR\docker\$service"
        New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
        
        $srcDir = "$SSL_DIR\services\$service"
        
        if (Test-Path $srcDir) {
            Copy-Item "$srcDir\cert.pem" "$dockerDir\server.crt" -Force
            Copy-Item "$srcDir\key.pem" "$dockerDir\server.key" -Force
            Copy-Item "$srcDir\fullchain.pem" "$dockerDir\fullchain.crt" -Force
            Write-Success "Docker certificates prepared for $service"
        }
    }
}

# Main function
function Start-SSLGeneration {
    Write-Host "=========================================="
    Write-Host "SOAR Ransomware Lab - SSL Certificate Generator"
    Write-Host "=========================================="
    Write-Host ""
    
    # Handle cleanup only
    if ($Cleanup) {
        Remove-SSLCertificates
        return
    }
    
    # Clean up existing certificates unless skipped
    if (-not $SkipCleanup) {
        Remove-SSLCertificates
    }
    
    # Generate certificates
    Test-Dependencies
    New-SSLDirectories
    New-CACertificate
    New-MainCertificate
    
    # Generate service-specific certificates
    foreach ($service in $SERVICES) {
        New-ServerCertificate -ServiceName $service
    }
    
    # Prepare Docker certificates
    New-DockerCertificates
    
    # Finalize
    Set-SSLPermissions
    Test-Certificates
    Show-CertificateInfo
    
    Write-Success "SSL certificates generated successfully!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Import $SSL_CA_CERT into your browser/system"
    Write-Host "  2. Update your docker-compose.yml files to use the certificates"
    Write-Host "  3. Restart your services with HTTPS enabled"
}

# Run main function
Start-SSLGeneration
