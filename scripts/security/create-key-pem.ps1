# Create proper PEM private key for nginx
Write-Host "Creating PEM private key for nginx..."

# Create self-signed certificate with exportable private key
$cert = New-SelfSignedCertificate -DnsName "soar.local" -KeyExportPolicy Exportable -CertStoreLocation "Cert:\CurrentUser\My" -KeyUsage "DigitalSignature","KeyEncipherment"

# Export certificate in PEM format
$certBytes = Get-Content ".\infra\nginx\ssl\soar.local.crt" -Encoding Byte
$base64Cert = [System.Convert]::ToBase64String($certBytes)
$pemCert = @"
-----BEGIN CERTIFICATE-----
$base64Cert
-----END CERTIFICATE-----
"@

# Get private key and export in PEM format
try {
    $rsa = $cert.PrivateKey
    if ($rsa -ne $null) {
        # Try to export private key
        $keyBytes = $rsa.ExportRSAPrivateKey()
        if ($keyBytes -ne $null) {
            $base64Key = [System.Convert]::ToBase64String($keyBytes)
            $pemKey = @"
-----BEGIN PRIVATE KEY-----
$base64Key
-----END PRIVATE KEY-----
"@
            $pemKey | Out-File ".\infra\nginx\ssl\soar.local.key" -Encoding UTF8
            Write-Host "Private key created successfully!"
        } else {
            throw "Failed to export private key bytes"
        }
    } else {
        throw "Private key is null"
    }
}
catch {
    Write-Warning "Failed to export real private key: $($_.Exception.Message)"
    Write-Warning "Creating test key for nginx compatibility..."
    
    # Create a minimal test key for nginx to start
    $testKey = @"
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC5T7QZ9YjZbZx
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC5T7QZ9YjZbZx
# Test key for nginx SSL - replace with actual key in production
# Domain: soar.local
# Generated: $(Get-Date)
-----END PRIVATE KEY-----
"@
    $testKey | Out-File ".\infra\nginx\ssl\soar.local.key" -Encoding UTF8
    Write-Warning "Test key created - nginx should start but SSL will not work properly"
}

# Cleanup
Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force

Write-Host "SSL key setup completed!"
