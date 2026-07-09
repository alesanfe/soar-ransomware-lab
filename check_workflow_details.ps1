try {
    $response = Invoke-RestMethod -Uri 'http://localhost:5001/api/v1/workflows/c08b9bed-b093-408d-8a4c-d11d5ada7578' -Headers @{'Authorization' = 'Bearer c8410826-0c52-484f-a894-8aceafa5ffd0'} -TimeoutSec 10
    Write-Host 'Workflow details:'
    Write-Host "Name: $($response.name)"
    Write-Host "Status: $($response.status)"
    Write-Host "Actions count: $($response.actions.Count)"
    
    Write-Host "`nActions with new SOAR features:"
    $response.actions | Where-Object { $_.label -match 'Tenzir|Network|Redis|Loki' } | ForEach-Object {
        Write-Host "- $($_.label)"
    }
} catch {
    Write-Host 'Error checking workflow:'
    Write-Host $_.Exception.Message
}
