$log = "C:\Users\alex0\PycharmProjects\soar-ransomware-lab\reports\validation\results\test-all.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
make test-all > $log 2>&1
$exitCode = $LASTEXITCODE
Add-Content -Path $log -Value "EXIT:$exitCode"
if ($exitCode -eq 0)
{
    Write-Host "test-all completed successfully"
}
else
{
    Write-Host "test-all failed with exit code $exitCode"
}
Write-Host "--- LOG TAIL ---"
Get-Content $log -Tail 30 | ForEach-Object { Write-Host $_ }
Write-Host "--- SUMMARY ---"
Get-Content $log | Where-Object { $_ -match 'FAILED|ERROR|passed|failed|short test summary' } | Select-Object -Last 30 | ForEach-Object { Write-Host $_ }
Write-Host "--- END ---"
