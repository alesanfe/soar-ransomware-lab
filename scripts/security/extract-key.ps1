# Extract private key from PFX file for nginx
$pfxPath = ".\infra\nginx\ssl\soar.local.pfx"
$keyPath = ".\infra\nginx\ssl\soar.local.key"
$password = "Password_123!"

try {
    # Load the PFX certificate
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
    $cert.Import($pfxPath, $password, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::MachineKeySet)
    
    # Get the private key
    $rsa = $cert.PrivateKey
    $keyBytes = $rsa.ExportCspBlob($true)
    
    # Convert to PEM format
    $base64Key = [System.Convert]::ToBase64String($keyBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
    
    # Create PEM format private key
    $pemKey = @"
-----BEGIN RSA PRIVATE KEY-----
$base64Key
-----END RSA PRIVATE KEY-----
"@
    
    # Save to file
    $pemKey | Out-File -FilePath $keyPath -Encoding UTF8
    
    Write-Host "Private key extracted successfully!"
    Write-Host "Key file: $keyPath"
}
catch {
    Write-Error "Failed to extract private key: $($_.Exception.Message)"
}
