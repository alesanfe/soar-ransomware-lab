try {
    $body = '{"query":{"term":{"alert_id":"WF-COMPLETE-1783607000-7000"}}}'
    $response = Invoke-RestMethod -Uri 'http://localhost:19200/soar-metrics/_search' -Method POST -ContentType 'application/json' -Body $body -TimeoutSec 10
    Write-Host 'Metrics found in Elasticsearch:'
    if ($response.hits.hits.Count -gt 0) {
        $response.hits.hits | ForEach-Object { 
            Write-Host ($_._source | ConvertTo-Json -Compress)
        }
    } else {
        Write-Host 'No metrics found for this alert'
    }
} catch {
    Write-Host 'Error searching metrics:'
    Write-Host $_.Exception.Message
}
