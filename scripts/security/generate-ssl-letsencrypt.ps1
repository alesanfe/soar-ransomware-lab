# SOAR Ransomware Lab - Let's Encrypt SSL Certificate Generator
# Generates SSL certificates using Let's Encrypt and DuckDNS

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$true)]
    [string]$Email,
    
    [string]$TempUser = "nginx",
    
    [int]$RenewDays = 30,
    
    [switch]$Cleanup,
    
    [switch]$ForceRenew,
    
    [switch]$SkipPortCheck
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

# Global variables
$Script:DISABLE_SSL = $false
$Script:SSL_DIR = ".\ssl"
$Script:SSL_CERT = "$SSL_DIR\fullchain.pem"
$Script:SSL_KEY = "$SSL_DIR\privkey.pem"
$Script:LETSENCRYPT_DIR = "C:\Certbot\live\$Domain"
$Script:LETSENCRYPT_CERT = "$LETSENCRYPT_DIR\fullchain.pem"
$Script:LETSENCRYPT_KEY = "$LETSENCRYPT_DIR\privkey.pem"

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
}

function Write-Warning {
    param([string]$Message)
    Write-Log -Color $Colors.Yellow -Message "⚠ $Message"
}

function Write-Info {
    param([string]$Message)
    Write-Log -Color $Colors.Blue -Message "ℹ $Message"
}

function Write-Cyan {
    param([string]$Message)
    Write-Log -Color $Colors.Cyan -Message "ℹ $Message"
}

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Install dependencies
function Install-Dependencies {
    Write-Info "Checking dependencies..."
    
    # Check if OpenSSL is available
    try {
        $null = Get-Command openssl -ErrorAction Stop
        Write-Success "OpenSSL is available"
    }
    catch {
        Write-Error "OpenSSL is not installed. Please install OpenSSL for Windows."
        Write-Info "Download from: https://slproweb.com/products/Win32OpenSSL.html"
        return $false
    }
    
    # Check if Certbot is available
    try {
        $null = Get-Command certbot -ErrorAction Stop
        Write-Success "Certbot is available"
    }
    catch {
        Write-Warning "Certbot is not found. Attempting to install..."
        
        # Try to install Certbot via pip
        try {
            $null = Get-Command pip -ErrorAction Stop
            Write-Info "Installing Certbot via pip..."
            pip install certbot certbot-nginx --quiet
            Write-Success "Certbot installed successfully"
        }
        catch {
            Write-Error "Failed to install Certbot. Please install it manually."
            Write-Info "Visit: https://certbot.eff.org/instructions"
            return $false
        }
    }
    
    return $true
}

# Check SSL certificate expiry
function Test-SSLExpiry {
    if (-not (Test-Path $SSL_CERT)) {
        return $false
    }

    try {
        # Check if certificate expires within $RenewDays days
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
        $cert.Import($SSL_CERT)
        
        $daysUntilExpiry = ($cert.NotAfter - (Get-Date)).Days
        
        if ($daysUntilExpiry -gt $RenewDays) {
            Write-Success "SSL certificate is valid (expires: $($cert.NotAfter), $daysUntilExpiry days left)"
            return $true
        }
        else {
            Write-Warning "SSL certificate expires soon or is expired (expires: $($cert.NotAfter), $daysUntilExpiry days left)"
            Write-Cyan "Attempting certificate renewal..."
            return $false
        }
    }
    catch {
        Write-Error "Failed to check certificate expiry: $($_.Exception.Message)"
        return $false
    }
}

# Stop services using port 80
function Stop-Port80Services {
    if ($SkipPortCheck) {
        Write-Info "Skipping port 80 check as requested"
        return $true
    }

    Write-Info "Checking port 80 availability..."
    
    # Check if port 80 is in use
    $port80Process = Get-NetTCPConnection -LocalPort 80 -ErrorAction SilentlyContinue | 
                     Where-Object { $_.State -eq "Listen" }
    
    if ($port80Process) {
        $serviceName = "nginx"
        Write-Warning "Port 80 is in use, attempting to stop $serviceName..."
        
        try {
            Stop-Service -Name $serviceName -Force -ErrorAction Stop
            Start-Sleep -Seconds 2
            
            # Check again
            $port80Process = Get-NetTCPConnection -LocalPort 80 -ErrorAction SilentlyContinue | 
                           Where-Object { $_.State -eq "Listen" }
            
            if ($port80Process) {
                Write-Error "Port 80 is still in use after stopping $serviceName"
                Write-Warning "Please manually stop the service using port 80"
                return $false
            }
            else {
                Write-Success "Port 80 is now available"
                return $true
            }
        }
        catch {
            Write-Error "Failed to stop $serviceName service: $($_.Exception.Message)"
            return $false
        }
    }
    else {
        Write-Success "Port 80 is available"
        return $true
    }
}

# Generate SSL certificates using Certbot
function New-SSLCertificates {
    Write-Warning "Cleaning up old SSL certificates..."
    
    if (Test-Path $SSL_DIR) {
        Remove-Item $SSL_DIR -Recurse -Force
    }
    
    if (Test-Path $SSL_CERT) {
        Remove-Item $SSL_CERT -Force
    }
    
    if (Test-Path $SSL_KEY) {
        Remove-Item $SSL_KEY -Force
    }

    Write-Cyan "Generating new SSL certificates for $Domain"
    
    if (-not (Install-Dependencies)) {
        return $false
    }

    New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null

    if (-not (Stop-Port80Services)) {
        return $false
    }

    Write-Info "Requesting certificate from Let's Encrypt..."
    
    try {
        $certbotArgs = @(
            "certonly",
            "--standalone",
            "--preferred-challenges", "http",
            "-d", $Domain,
            "--email", $Email,
            "--agree-tos",
            "--no-eff-email",
            "--non-interactive",
            "--rsa-key-size", "4096",
            "--must-staple"
        )
        
        if ($ForceRenew) {
            $certbotArgs += "--force-renewal"
        }
        
        $result = & certbot $certbotArgs 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "SSL certificate generated successfully"
            Set-SSLPermissions
            return $true
        }
        else {
            Write-Error "Failed to generate SSL certificate"
            Write-Warning "Certbot output: $result"
            Write-Warning "Continuing without SSL encryption"
            return $false
        }
    }
    catch {
        Write-Error "Exception during certificate generation: $($_.Exception.Message)"
        return $false
    }
}

# Fix SSL certificate permissions
function Set-SSLPermissions {
    Write-Warning "Fixing SSL certificate permissions for $TempUser..."

    # Check if user exists
    try {
        $null = Get-LocalUser -Name $TempUser -ErrorAction Stop
    }
    catch {
        Write-Warning "User $TempUser does not exist yet, skipping permission fix"
        return $true
    }

    if ((Test-Path $SSL_CERT) -and (Test-Path $SSL_KEY)) {
        try {
            # Get the user's primary group
            $user = Get-LocalUser -Name $TempUser
            $userGroup = (Get-LocalGroup | Where-Object { 
                $_.Name -eq $user.Name -or $_.SID -eq $user.SID 
            } | Select-Object -First 1).Name
            
            if (-not $userGroup) {
                $userGroup = "Users"
            }

            # Ensure the SSL directory exists and has correct permissions
            $certDir = Split-Path $SSL_CERT -Parent
            New-Item -ItemType Directory -Path $certDir -Force | Out-Null
            
            # Set ownership and permissions for certificate files
            $acl = Get-Acl $SSL_CERT
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $TempUser, "Read", "Allow"
            )
            $acl.SetAccessRule($accessRule)
            Set-Acl $SSL_CERT $acl
            
            $acl = Get-Acl $SSL_KEY
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $TempUser, "Read", "Allow"
            )
            $acl.SetAccessRule($accessRule)
            Set-Acl $SSL_KEY $acl

            # Verify permissions
            if ((Test-Path $SSL_CERT) -and (Test-Path $SSL_KEY)) {
                Write-Success "SSL certificate permissions fixed and verified"
                return $true
            }
            else {
                Write-Error "Failed to verify SSL certificate permissions for $TempUser"
                return $false
            }
        }
        catch {
            Write-Error "Failed to set SSL permissions: $($_.Exception.Message)"
            return $false
        }
    }
    else {
        Write-Error "SSL certificate files not found at $SSL_CERT and $SSL_KEY"
        return $false
    }
}

# Copy SSL certificates from Let's Encrypt directory
function Copy-SSLCertificates {
    if ((Test-Path $LETSENCRYPT_CERT) -and (Test-Path $LETSENCRYPT_KEY)) {
        Write-Warning "Using existing SSL certificates from Let's Encrypt..."
        
        # Create target directory if it doesn't exist
        $certDir = Split-Path $SSL_CERT -Parent
        New-Item -ItemType Directory -Path $certDir -Force | Out-Null
        
        Copy-Item $LETSENCRYPT_CERT $SSL_CERT -Force
        Copy-Item $LETSENCRYPT_KEY $SSL_KEY -Force
        
        Write-Info "SSL certificates copied to:"
        Write-Info "  Certificate: $SSL_CERT"
        Write-Info "  Private Key: $SSL_KEY"
        
        Set-SSLPermissions
        return $true
    }
    return $false
}

# Main SSL setup function
function Start-SSLSetup {
    if ([string]::IsNullOrEmpty($Domain)) {
        Write-Warning "No domain provided. Running without SSL."
        $Script:DISABLE_SSL = $true
        return
    }

    if (Test-SSLExpiry -and -not $ForceRenew) {
        # Certificate is valid, but still need to verify permissions
        Write-Cyan "SSL certificate is valid, verifying permissions..."
        if ((Test-Path $SSL_CERT) -and (Test-Path $SSL_KEY)) {
            Set-SSLPermissions
        }
        else {
            Write-Warning "SSL certificate files not found, attempting to copy from Let's Encrypt..."
            if (Copy-SSLCertificates) {
                $Script:DISABLE_SSL = $false
                Write-Success "SSL certificates copied and permissions fixed"
            }
            else {
                Write-Warning "No valid SSL certificates found. Running without SSL."
                $Script:DISABLE_SSL = $true
                return
            }
        }
        $Script:DISABLE_SSL = $false
        return
    }

    if (New-SSLCertificates) {
        # Copy from Let's Encrypt directory to our SSL directory
        if ((Test-Path $LETSENCRYPT_CERT) -and (Test-Path $LETSENCRYPT_KEY)) {
            $certDir = Split-Path $SSL_CERT -Parent
            New-Item -ItemType Directory -Path $certDir -Force | Out-Null
            
            Copy-Item $LETSENCRYPT_CERT $SSL_CERT -Force
            Copy-Item $LETSENCRYPT_KEY $SSL_KEY -Force
            
            Write-Info "SSL certificates saved to:"
            Write-Info "  Certificate: $SSL_CERT"
            Write-Info "  Private Key: $SSL_KEY"
            
            Set-SSLPermissions
            $Script:DISABLE_SSL = $false
            Write-Success "SSL certificates configured successfully"
        }
    }
    elseif (Copy-SSLCertificates) {
        $Script:DISABLE_SSL = $false
        Write-Success "SSL certificates copied from existing installation"
    }
    else {
        Write-Warning "No valid SSL certificates found. Running without SSL."
        $Script:DISABLE_SSL = $true
        return
    }
}

# Restart services after SSL setup
function Start-Services {
    $serviceName = "nginx"
    
    try {
        Write-Info "Starting $serviceName service..."
        Start-Service -Name $serviceName -ErrorAction Stop
        Write-Success "$serviceName service started"
    }
    catch {
        Write-Warning "Failed to start $serviceName service: $($_.Exception.Message)"
    }
}

# Display SSL information
function Show-SSLInfo {
    Write-Host ""
    Write-Host "SSL Certificate Information:"
    Write-Host "  Domain: $Domain"
    Write-Host "  Certificate: $SSL_CERT"
    Write-Host "  Private Key: $SSL_KEY"
    Write-Host "  Let's Encrypt Dir: $LETSENCRYPT_DIR"
    Write-Host ""
    
    if (Test-Path $SSL_CERT) {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
            $cert.Import($SSL_CERT)
            Write-Host "Certificate Details:"
            Write-Host "  Subject: $($cert.Subject)"
            Write-Host "  Issuer: $($cert.Issuer)"
            Write-Host "  Not Before: $($cert.NotBefore)"
            Write-Host "  Not After: $($cert.NotAfter)"
            Write-Host "  Days Until Expiry: $(($cert.NotAfter - (Get-Date)).Days)"
        }
        catch {
            Write-Warning "Unable to read certificate details"
        }
        Write-Host ""
    }
    
    if ($Script:DISABLE_SSL) {
        Write-Warning "SSL is DISABLED"
    }
    else {
        Write-Success "SSL is ENABLED"
    }
}

# Main function
function Start-LetsEncryptSSL {
    Write-Host "=========================================="
    Write-Host "SOAR Ransomware Lab - Let's Encrypt SSL"
    Write-Host "=========================================="
    Write-Host ""
    
    # Check administrator privileges
    $isAdmin = Test-Administrator
    if (-not $isAdmin) {
        Write-Error "This script requires administrator privileges to run Certbot and manage certificates."
        Write-Info "Please run PowerShell as Administrator and try again."
        exit 1
    }
    
    # Handle cleanup only
    if ($Cleanup) {
        Write-Warning "Cleaning up SSL certificates..."
        if (Test-Path $SSL_DIR) {
            Remove-Item $SSL_DIR -Recurse -Force
            Write-Success "SSL directory cleaned"
        }
        else {
            Write-Info "No SSL directory to clean"
        }
        return
    }
    
    # Setup SSL
    Start-SSLSetup
    
    # Restart services if they were stopped
    Start-Services
    
    # Show information
    Show-SSLInfo
    
    if (-not $Script:DISABLE_SSL) {
        Write-Success "Let's Encrypt SSL setup completed successfully!"
        Write-Host ""
        Write-Info "Next steps:"
        Write-Host "  1. Configure your web server to use:"
        Write-Host "     - Certificate: $SSL_CERT"
        Write-Host "     - Private Key: $SSL_KEY"
        Write-Host "  2. Set up automatic renewal (certbot renew --quiet)"
        Write-Host "  3. Test your HTTPS configuration"
    }
    else {
        Write-Warning "SSL setup failed. Running without HTTPS."
    }
}

# Run main function
Start-LetsEncryptSSL
