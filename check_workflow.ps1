try {
    $response = Invoke-RestMethod -Uri 'http://localhost:5001/api/v1/flows/1109250e-93ab-45f6-a286-f335a8b07271' -Headers @{'Authorization' = 'Bearer c8410826-0c52-484f-a894-8aceafa5ffd0'} -TimeoutSec 10
    Write-Host 'Workflow execution status:'
    $json = $response | ConvertTo-Json
    Write-Host $json
} catch {
    Write-Host 'Error checking workflow status:'
    Write-Host $_.Exception.Message
}
