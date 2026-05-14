# Fix PEM certificate for nginx
Remove-Item ".\infra\nginx\ssl\soar.local.crt" -Force -ErrorAction SilentlyContinue

# Create certificate
$cert = New-SelfSignedCertificate -DnsName "soar.local" -CertStoreLocation "Cert:\CurrentUser\My"

# Export as DER
Export-Certificate -Cert $cert -FilePath ".\infra\nginx\ssl\temp.cer" -Type CERT | Out-Null

# Convert to PEM
$certBytes = Get-Content ".\infra\nginx\ssl\temp.cer" -Encoding Byte
$base64 = [System.Convert]::ToBase64String($certBytes)

# Create PEM file
$pemContent = @"
-----BEGIN CERTIFICATE-----
$base64
-----END CERTIFICATE-----
"@

$pemContent | Out-File ".\infra\nginx\ssl\soar.local.crt" -Encoding UTF8

# Cleanup
Remove-Item ".\infra\nginx\ssl\temp.cer" -Force
Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force

Write-Host "PEM certificate fixed!"
