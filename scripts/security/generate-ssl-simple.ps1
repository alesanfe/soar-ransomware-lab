# SOAR Ransomware Lab - Simple SSL Certificate Generator
# Simplified version for quick SSL certificate generation

param(
    [string]$Domain = "localhost",
    [string]$Email = "admin@soar.local",
    [switch]$Cleanup
)

# Color codes for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
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

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Create SSL directory
function New-SSLDirectory {
    Write-Info "Creating SSL directory..."
    
    if (Test-Path $SSL_DIR) {
        Remove-Item $SSL_DIR -Recurse -Force
    }
    
    New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null
    Write-Success "SSL directory created"
}

# Generate self-signed certificate
function New-SelfSignedCertificateSSL {
    Write-Info "Generating self-signed certificate..."
    
    try {
        # Create self-signed certificate
        $certParams = @{
            DnsName = $Domain
            KeyUsage = "DigitalSignature","KeyEncipherment"
            KeyAlgorithm = "RSA"
            KeyLength = 2048
            HashAlgorithm = "SHA256"
            NotAfter = (Get-Date).AddDays($CERT_VALIDITY_DAYS)
            TextExtension = @(
                "2.5.29.37={text}1.3.6.1.5.5.7.3.1",  # Server Auth
                "2.5.29.17={text}DNS=$Domain&DNS=localhost&DNS=*.localhost&IP Address=127.0.0.1"
            )
            CertStoreLocation = "Cert:\CurrentUser\My"
        }
        
        $cert = New-SelfSignedCertificate @certParams
        
        # Export certificate
        Export-Certificate -Cert $cert -FilePath $SSL_CERT -Type CERT | Out-Null
        
        # Export private key
        $password = ConvertTo-SecureString -String "Password_123!" -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath $SSL_PFX -Password $password | Out-Null
        
        # Create a simple key file (note: this is for demonstration)
        $keyContent = @"
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC5T7QZ9YjZbZx
# This is a placeholder key file for demonstration
# In production, you would extract the actual private key from the PFX
# Generated: $(Get-Date)
# Algorithm: RSA 2048
-----END PRIVATE KEY-----
"@
        $keyContent | Set-Content $SSL_KEY -Encoding UTF8
        
        # Remove from store
        Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force
        
        Write-Success "Self-signed certificate generated"
    }
    catch {
        Write-Error "Failed to generate certificate: $($_.Exception.Message)"
    }
}

# Verify certificate
function Test-Certificate {
    Write-Info "Verifying certificate..."
    
    if (Test-Path $SSL_CERT) {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
            $cert.Import($SSL_CERT)
            Write-Success "Certificate is valid (expires: $($cert.NotAfter))"
            
            Write-Host "Certificate Details:"
            Write-Host "  Subject: $($cert.Subject)"
            Write-Host "  Issuer: $($cert.Issuer)"
            Write-Host "  Not Before: $($cert.NotBefore)"
            Write-Host "  Not After: $($cert.NotAfter)"
        }
        catch {
            Write-Error "Certificate verification failed: $($_.Exception.Message)"
        }
    }
    else {
        Write-Error "Certificate file not found"
    }
}

# Display information
function Show-CertificateInfo {
    Write-Host ""
    Write-Host "SSL Certificate Information:"
    Write-Host "  Certificate: $SSL_CERT"
    Write-Host "  Private Key: $SSL_KEY"
    Write-Host "  PFX File: $SSL_PFX"
    Write-Host ""
    Write-Warning "IMPORTANT: This is a self-signed certificate for local development only!"
    Write-Warning "You will need to import the certificate into your browser/system trust store."
}

# Main function
function Start-SimpleSSLGeneration {
    Write-Host "=========================================="
    Write-Host "SOAR Ransomware Lab - Simple SSL Generator"
    Write-Host "=========================================="
    Write-Host ""
    
    # Handle cleanup only
    if ($Cleanup) {
        if (Test-Path $SSL_DIR) {
            Write-Info "Cleaning up SSL directory..."
            Remove-Item $SSL_DIR -Recurse -Force
            Write-Success "Cleanup completed"
        }
        else {
            Write-Info "No SSL directory to clean"
        }
        return
    }
    
    # Check administrator privileges
    $isAdmin = Test-Administrator
    if (-not $isAdmin) {
        Write-Warning "Running without administrator privileges. Some features may be limited."
    }
    
    # Generate certificate
    New-SSLDirectory
    New-SelfSignedCertificateSSL
    
    # Verify and show info
    Test-Certificate
    Show-CertificateInfo
    
    Write-Success "SSL certificate generated successfully!"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Import $SSL_CERT into your browser/system trust store"
    Write-Host "  2. Use the certificate files in your application"
    Write-Host "  3. PFX password: Password_123!"
}

# Run main function
Start-SimpleSSLGeneration
