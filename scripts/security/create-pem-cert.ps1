# Create proper PEM format SSL certificate for nginx
Write-Host "Creating PEM format SSL certificate for nginx..."

# Create SSL directory if it doesn't exist
$sslDir = ".\infra\nginx\ssl"
if (-not (Test-Path $sslDir)) {
    New-Item -ItemType Directory -Path $sslDir -Force | Out-Null
    Write-Host "Created SSL directory: $sslDir"
}

# Create self-signed certificate
$cert = New-SelfSignedCertificate -DnsName "soar.local" -CertStoreLocation "Cert:\CurrentUser\My" -KeyUsage "DigitalSignature","KeyEncipherment" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.1")

# Export certificate in PEM format
$certPath = ".\infra\nginx\ssl\soar.local.crt"
$pemPath = ".\infra\nginx\ssl\soar.local.pem"
$pfxPath = ".\infra\nginx\ssl\soar.local.pfx"

# Export as DER first, then convert to PEM
Export-Certificate -Cert $cert -FilePath $certPath -Type CERT | Out-Null

# Read the DER certificate and convert to PEM format
try {
    $certBytes = Get-Content $certPath -Encoding Byte
    $base64Cert = [System.Convert]::ToBase64String($certBytes)

    # Create PEM format certificate
    $pemContent = @"
-----BEGIN CERTIFICATE-----
$base64Cert
-----END CERTIFICATE-----
"@

    $pemContent | Out-File -FilePath $pemPath -Encoding UTF8

    # Replace the original with PEM format
    if (Test-Path $certPath) {
        Remove-Item $certPath -Force
    }
    if (Test-Path $pemPath) {
        Move-Item $pemPath $certPath -Force
    }

    Write-Host "PEM certificate created successfully!"
}
catch {
    Write-Error "Failed to create PEM certificate: $($_.Exception.Message)"
}

# Export PFX
$password = ConvertTo-SecureString -String "Password_123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $password | Out-Null

# Remove from store
Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force

Write-Host "SSL certificate setup completed!"
Write-Host "Certificate: $certPath"
Write-Host "PFX: $pfxPath"
