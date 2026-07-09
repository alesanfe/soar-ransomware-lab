




try {
    $response = Invoke-RestMethod -Uri 'http://localhost:19000/api/case' -Method GET -Headers @{'Authorization' = 'Bearer yLZ2P6Hx3lKk1vHk8jM4sN7qR5tW2uX9eA4cF6bD8'} -TimeoutSec 10
    Write-Host 'Cases found in TheHive:'
    if ($response.Count -gt 0) {
        $response | ForEach-Object { 
            Write-Host "Case ID: $($_._id), Title: $($_.title), Severity: $($_.severity)"
        }
    } else {
        Write-Host 'No cases found'
    }
} catch {
    Write-Host 'Error checking TheHive cases:'
    Write-Host $_.Exception.Message
}
