$body = Get-Content 'alert.json' -Raw
try {
    $response = Invoke-RestMethod -Uri 'http://localhost:15001/api/v1/hooks/webhook_cbc11c64-2bde-576d-8538-73fa6b395d10' -Method POST -ContentType 'application/json' -Body $body -TimeoutSec 30
    Write-Host 'Workflow triggered successfully'
    $json = $response | ConvertTo-Json
    Write-Host $json
} catch {
    Write-Host 'Error triggering workflow:'
    Write-Host $_.Exception.Message
}
