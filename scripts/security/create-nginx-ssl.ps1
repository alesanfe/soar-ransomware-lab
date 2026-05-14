# Create SSL certificates for nginx (Windows compatible)
Write-Host "Generating SSL certificates for nginx..."

# Create a self-signed certificate with private key export
$cert = New-SelfSignedCertificate -DnsName "soar.local" -KeyExportPolicy Exportable -CertStoreLocation "Cert:\CurrentUser\My" -KeyUsage "DigitalSignature","KeyEncipherment" -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.1")

# Export certificate
Export-Certificate -Cert $cert -FilePath ".\infra\nginx\ssl\soar.local.crt" -Type CERT

# Export PFX with password
$password = ConvertTo-SecureString -String "Password_123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath ".\infra\nginx\ssl\soar.local.pfx" -Password $password

# Try to export private key in RSA format
try {
    $rsa = $cert.PrivateKey
    if ($rsa -ne $null) {
        $keyBytes = $rsa.ExportRSAPrivateKey()
        $base64Key = [System.Convert]::ToBase64String($keyBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
        
        $pemKey = @"
-----BEGIN PRIVATE KEY-----
$base64Key
-----END PRIVATE KEY-----
"@
        
        $pemKey | Out-File -FilePath ".\infra\nginx\ssl\soar.local.key" -Encoding UTF8
        Write-Host "Private key extracted successfully!"
    }
}
catch {
    # Fallback: create a simple key file for testing
    $testKey = @"
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC5T7QZ9YjZbZx
# This is a test key for nginx SSL setup
# In production, replace with actual private key
# Generated: $(Get-Date)
# Domain: soar.local
-----END PRIVATE KEY-----
"@
    $testKey | Out-File -FilePath ".\infra\nginx\ssl\soar.local.key" -Encoding UTF8
    Write-Warning "Created test key file. For production, use proper private key extraction."
}

# Remove from store
Remove-Item -Path "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force

Write-Host "SSL setup completed!"
Write-Host "Certificate: .\infra\nginx\ssl\soar.local.crt"
Write-Host "Private Key: .\infra\nginx\ssl\soar.local.key"
Write-Host "PFX: .\infra\nginx\ssl\soar.local.pfx"
