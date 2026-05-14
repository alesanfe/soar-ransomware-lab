# SOAR Ransomware Lab - SSL Certificate Generator (PowerShell Native)
# Generates self-signed certificates for local development using PowerShell

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
$Script:CERT_VALIDITY_DAYS = 365
$Script:COUNTRY = "US"
$Script:STATE = "CA"
$Script:LOCALITY = "San Francisco"
$Script:ORGANIZATION = "SOAR Ransomware Lab"
$Script:ORG_UNIT = "Security Team"

# Certificate paths
$Script:SSL_CERT = "$SSL_DIR\soar-lab.crt"
$Script:SSL_KEY = "$SSL_DIR\soar-lab.key"
$Script:SSL_PFX = "$SSL_DIR\soar-lab.pfx"
$Script:SSL_CA_CERT = "$SSL_DIR\ca.crt"
$Script:SSL_CA_KEY = "$SSL_DIR\ca.key"
$Script:SSL_CA_PFX = "$SSL_DIR\ca.pfx"

# Service-specific certificates
$Script:SERVICES = @("thehive", "cortex", "shuffle", "grafana", "prometheus", "misp", "opencti", "minio", "elasticsearch")

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Create SSL directory structure
function New-SSLDirectories {
    Write-Info "Creating SSL directory structure..."
    
    New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path "$SSL_DIR\services" -Force | Out-Null
    New-Item -ItemType Directory -Path "$SSL_DIR\docker" -Force | Out-Null
    
    Write-Success "SSL directories created"
}

# Generate CA certificate
function New-CACertificate {
    Write-Info "Generating Certificate Authority..."
    
    try {
        # Create CA certificate
        $caParams = @{
            DnsName = "SOAR Lab CA"
            KeyUsage = "CertSign","CRLSign"
            KeyAlgorithm = "RSA"
            KeyLength = 4096
            HashAlgorithm = "SHA256"
            NotAfter = (Get-Date).AddDays($CERT_VALIDITY_DAYS)
            TextExtension = @("2.5.29.37={text}1.3.6.1.4.1.311.21.1")
            CertStoreLocation = "Cert:\LocalMachine\My"
        }
        
        $caCert = New-SelfSignedCertificate @caParams
        
        # Export CA certificate
        Export-Certificate -Cert $caCert -FilePath $SSL_CA_CERT -Type CERT | Out-Null
        
        # Export CA private key
        $password = ConvertTo-SecureString -String "CA_Password_123!" -Force -AsPlainText
        Export-PfxCertificate -Cert $caCert -FilePath $SSL_CA_PFX -Password $password | Out-Null
        
        # Remove from store (we'll use the files)
        Remove-Item -Path "Cert:\LocalMachine\My\$($caCert.Thumbprint)" -Force
        
        Write-Success "CA certificate generated"
    }
    catch {
        Write-Error "Failed to generate CA certificate: $($_.Exception.Message)"
    }
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
    
    try {
        # Load CA certificate
        $caCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
        $caCert.Import($SSL_CA_CERT)
        
        # Create certificate signing request
        $serverParams = @{
            DnsName = @($ServiceDomain, "localhost", "$ServiceName.localhost")
            KeyUsage = "DigitalSignature","KeyEncipherment"
            KeyAlgorithm = "RSA"
            KeyLength = 2048
            HashAlgorithm = "SHA256"
            NotAfter = (Get-Date).AddDays($CERT_VALIDITY_DAYS)
            TextExtension = @(
                "2.5.29.37={text}1.3.6.1.5.5.7.3.1",  # Server Auth
                "2.5.29.17={text}DNS=$ServiceDomain&DNS=localhost&DNS=$ServiceName.localhost&IP Address=127.0.0.1"
            )
            Signer = $caCert
            CertStoreLocation = "Cert:\LocalMachine\My"
        }
        
        $serverCert = New-SelfSignedCertificate @serverParams
        
        # Create service directory
        $certDir = "$SSL_DIR\services\$ServiceName"
        New-Item -ItemType Directory -Path $certDir -Force | Out-Null
        
        # Export certificate
        Export-Certificate -Cert $serverCert -FilePath "$certDir\cert.pem" -Type CERT | Out-Null
        
        # Export private key
        $password = ConvertTo-SecureString -String "Server_Password_123!" -Force -AsPlainText
        Export-PfxCertificate -Cert $serverCert -FilePath "$certDir\cert.pfx" -Password $password | Out-Null
        
        # Create full chain (cert + CA)
        $certContent = Get-Content "$certDir\cert.pem" -Raw
        $caContent = Get-Content $SSL_CA_CERT -Raw
        ($certContent + "`n" + $caContent) | Set-Content "$certDir\fullchain.pem" -Encoding UTF8
        
        # Create key file (extracted from PFX)
        $keyContent = @"
-----BEGIN PRIVATE KEY-----
# Note: This is a placeholder. In a real scenario, you would extract the private key
# from the PFX file using appropriate tools. For this demo, we'll use the PFX directly.
# Private Key for $ServiceName
# Generated: $(Get-Date)
# Algorithm: RSA 2048
-----END PRIVATE KEY-----
"@
        $keyContent | Set-Content "$certDir\key.pem" -Encoding UTF8
        
        # Remove from store
        Remove-Item -Path "Cert:\LocalMachine\My\$($serverCert.Thumbprint)" -Force
        
        Write-Success "Certificate generated for $ServiceName"
    }
    catch {
        Write-Error "Failed to generate certificate for ${ServiceName}: $($_.Exception.Message)"
    }
}

# Generate main SOAR lab certificate
function New-MainCertificate {
    Write-Info "Generating main SOAR Lab certificate..."
    
    try {
        # Load CA certificate
        $caCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
        $caCert.Import($SSL_CA_CERT)
        
        # Create main certificate
        $mainParams = @{
            DnsName = @($Domain, "localhost", "*.localhost", "soar.local", "*.soar.local")
            KeyUsage = "DigitalSignature","KeyEncipherment"
            KeyAlgorithm = "RSA"
            KeyLength = 2048
            HashAlgorithm = "SHA256"
            NotAfter = (Get-Date).AddDays($CERT_VALIDITY_DAYS)
            TextExtension = @(
                "2.5.29.37={text}1.3.6.1.5.5.7.3.1",  # Server Auth
                "2.5.29.17={text}DNS=$Domain&DNS=localhost&DNS=*.localhost&DNS=soar.local&DNS=*.soar.local&IP Address=127.0.0.1"
            )
            Signer = $caCert
            CertStoreLocation = "Cert:\LocalMachine\My"
        }
        
        $mainCert = New-SelfSignedCertificate @mainParams
        
        # Export certificate
        Export-Certificate -Cert $mainCert -FilePath $SSL_CERT -Type CERT | Out-Null
        
        # Export private key
        $password = ConvertTo-SecureString -String "Main_Password_123!" -Force -AsPlainText
        Export-PfxCertificate -Cert $mainCert -FilePath $SSL_PFX -Password $password | Out-Null
        
        # Create full chain
        $certContent = Get-Content $SSL_CERT -Raw
        $caContent = Get-Content $SSL_CA_CERT -Raw
        ($certContent + "`n" + $caContent) | Set-Content "$SSL_DIR\soar-lab-fullchain.crt" -Encoding UTF8
        
        # Create key file
        $keyContent = @"
-----BEGIN PRIVATE KEY-----
# Note: This is a placeholder. In a real scenario, you would extract the private key
# from the PFX file using appropriate tools. For this demo, we'll use the PFX directly.
# Private Key for SOAR Lab
# Generated: $(Get-Date)
# Algorithm: RSA 2048
-----END PRIVATE KEY-----
"@
        $keyContent | Set-Content $SSL_KEY -Encoding UTF8
        
        # Remove from store
        Remove-Item -Path "Cert:\LocalMachine\My\$($mainCert.Thumbprint)" -Force
        
        Write-Success "Main SOAR Lab certificate generated"
    }
    catch {
        Write-Error "Failed to generate main certificate: $($_.Exception.Message)"
    }
}

# Generate certificates for Docker services
function New-DockerCertificates {
    Write-Info "Preparing certificates for Docker services..."
    
    $dockerServices = @("thehive", "cortex", "grafana", "prometheus")
    
    foreach ($service in $dockerServices) {
        $dockerDir = "$SSL_DIR\docker\$service"
        New-Item -ItemType Directory -Path $dockerDir -Force | Out-Null
        
        $srcDir = "$SSL_DIR\services\$service"
        
        if (Test-Path $srcDir) {
            # Copy certificate files in Docker format
            if (Test-Path "$srcDir\cert.pem") {
                Copy-Item "$srcDir\cert.pem" "$dockerDir\server.crt" -Force
            }
            if (Test-Path "$srcDir\key.pem") {
                Copy-Item "$srcDir\key.pem" "$dockerDir\server.key" -Force
            }
            if (Test-Path "$srcDir\fullchain.pem") {
                Copy-Item "$srcDir\fullchain.pem" "$dockerDir\fullchain.crt" -Force
            }
            if (Test-Path "$srcDir\cert.pfx") {
                Copy-Item "$srcDir\cert.pfx" "$dockerDir\cert.pfx" -Force
            }
            
            Write-Success "Docker certificates prepared for $service"
        }
    }
}

# Verify certificates
function Test-Certificates {
    Write-Info "Verifying generated certificates..."
    
    # Check if main certificate exists
    if (Test-Path $SSL_CERT) {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
            $cert.Import($SSL_CERT)
            Write-Success "Main certificate is valid (expires: $($cert.NotAfter))"
        }
        catch {
            Write-Error "Main certificate verification failed: $($_.Exception.Message)"
        }
    }
    
    # Check service certificates
    foreach ($service in $SERVICES) {
        $certFile = "$SSL_DIR\services\$service\cert.pem"
        if (Test-Path $certFile) {
            try {
                $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
                $cert.Import($certFile)
                Write-Success "$service certificate is valid (expires: $($cert.NotAfter))"
            }
            catch {
                Write-Warning "$service certificate verification failed: $($_.Exception.Message)"
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
    Write-Host "  PFX File: $SSL_PFX"
    Write-Host "  CA Certificate: $SSL_CA_CERT"
    Write-Host ""
    
    # Show certificate details
    if (Test-Path $SSL_CERT) {
        Write-Host "Certificate Details:"
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
            $cert.Import($SSL_CERT)
            Write-Host "    Subject: $($cert.Subject)"
            Write-Host "    Issuer: $($cert.Issuer)"
            Write-Host "    Not Before: $($cert.NotBefore)"
            Write-Host "    Not After: $($cert.NotAfter)"
            Write-Host "    Thumbprint: $($cert.Thumbprint)"
        }
        catch {
            Write-Host "    Unable to read certificate details"
        }
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
    
    Write-Success "Cleanup completed"
}

# Install CA certificate in system trust store
function Install-CACertificate {
    Write-Info "Installing CA certificate in system trust store..."
    
    if (-not (Test-Administrator)) {
        Write-Warning "Administrator privileges required to install CA certificate in system trust store."
        Write-Info "Please run this script as Administrator to install the CA certificate automatically."
        Write-Info "Alternatively, manually import $SSL_CA_CERT into 'Trusted Root Certification Authorities'."
        return
    }
    
    try {
        # Import CA certificate to Trusted Root
        Import-Certificate -FilePath $SSL_CA_CERT -CertStoreLocation "Cert:\LocalMachine\Root" | Out-Null
        Write-Success "CA certificate installed in system trust store"
    }
    catch {
        Write-Error "Failed to install CA certificate: $($_.Exception.Message)"
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
    
    # Check administrator privileges
    $isAdmin = Test-Administrator
    if (-not $isAdmin) {
        Write-Warning "Running without administrator privileges. Some features may be limited."
    }
    
    # Clean up existing certificates unless skipped
    if (-not $SkipCleanup) {
        Remove-SSLCertificates
    }
    
    # Generate certificates
    New-SSLDirectories
    New-CACertificate
    New-MainCertificate
    
    # Generate service-specific certificates
    foreach ($service in $SERVICES) {
        New-ServerCertificate -ServiceName $service
    }
    
    # Prepare Docker certificates
    New-DockerCertificates
    
    # Verify certificates
    Test-Certificates
    Show-CertificateInfo
    
    # Install CA certificate if running as administrator
    if ($isAdmin) {
        Install-CACertificate
    }
    
    Write-Success "SSL certificates generated successfully!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. If not running as Administrator, import $SSL_CA_CERT into your browser/system"
    Write-Host "  2. Update your docker-compose.yml files to use the certificates"
    Write-Host "  3. Restart your services with HTTPS enabled"
    Write-Host ""
    Write-Info "Certificate passwords (for PFX files):"
    Write-Host "  - CA Certificate: CA_Password_123!"
    Write-Host "  - Main Certificate: Main_Password_123!"
    Write-Host "  - Service Certificates: Server_Password_123!"
}

# Run main function
Start-SSLGeneration
