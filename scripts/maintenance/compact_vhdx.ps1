#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Compact the Docker Desktop WSL2 data VHDX (RB-08).

.DESCRIPTION
    WSL2 does not return space freed inside the Docker VHDX to the host.
    Compaction requires Docker Desktop and every WSL distro to be fully
    stopped — the VHDX is locked while any of them runs.

    This script refuses to proceed while Docker/WSL is still active rather
    than failing halfway. Run it from an elevated PowerShell:

        powershell -ExecutionPolicy Bypass -File scripts\maintenance\compact_vhdx.ps1

    It will:
      1. Verify the VHDX exists and report current size.
      2. Check that Docker/WSL are fully stopped (refuse otherwise).
      3. Compact via Optimize-VHD (Hyper-V tools) or diskpart fallback.
      4. Report the space reclaimed.

.PARAMETER AutoStop
    When set, the script stops the SOAR compose stack, quits Docker
    Desktop, and shuts down WSL itself before compacting, then restarts
    Docker Desktop. Without it, the script only verifies and refuses if
    anything is still running.

.EXAMPLE
    .\compact_vhdx.ps1 -AutoStop
#>
[CmdletBinding()]
param(
    [switch]$AutoStop
)

$ErrorActionPreference = 'Stop'

$vhdx = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'
if (-not (Test-Path $vhdx)) {
    # Older Docker Desktop layouts
    $alt = Join-Path $env:LOCALAPPDATA 'Docker\wsl\data\ext4.vhdx'
    if (Test-Path $alt) { $vhdx = $alt } else {
        Write-Error "Docker VHDX not found under $env:LOCALAPPDATA\Docker\wsl — locate it manually (docker info | Select-String Root)."
    }
}

function Test-WslDockerActive {
    # wsl --list --running exits non-zero-ish silently when nothing runs;
    # parse for any running distro.
    $running = (wsl.exe --list --running --quiet 2>$null) -join ' '
    if ($running -match '\S') { return $true }
    $dockerProcs = Get-Process -Name 'com.docker*','Docker Desktop','vpnkit','wslservice' -ErrorAction SilentlyContinue
    return [bool]$dockerProcs
}

$sizeBefore = (Get-Item $vhdx).Length
Write-Host "VHDX: $vhdx"
Write-Host ("Size before: {0:N1} GB" -f ($sizeBefore/1GB))

if (Test-WslDockerActive) {
    if (-not $AutoStop) {
        Write-Error @"
Docker/WSL is still running — the VHDX is locked.

Either stop it manually:
    docker compose -p soar down    # from the repo root
    # quit Docker Desktop, then:
    wsl --shutdown
and re-run this script, or re-run with -AutoStop to let it stop
everything for you (it will restart Docker Desktop afterwards).
"@
    }
    Write-Host "AutoStop: bringing the SOAR stack down and stopping WSL..."
    Push-Location (Split-Path $PSScriptRoot -Parent | Split-Path -Parent)
    try { docker compose -p soar down 2>$null | Out-Null } catch {}
    Pop-Location
    Get-Process -Name 'com.docker*','Docker Desktop' -ErrorAction SilentlyContinue |
        ForEach-Object { $_.CloseMainWindow() | Out-Null }
    Start-Sleep -Seconds 15
    # Hard stop if still up
    Get-Process -Name 'com.docker*','Docker Desktop' -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    wsl.exe --shutdown
    Start-Sleep -Seconds 5
    if (Test-WslDockerActive) {
        Write-Error "WSL still reports running distros after shutdown — stop them manually and retry."
    }
}

Write-Host "Compacting (this can take several minutes on large disks)..."

$optimized = $false
if (Get-Command Optimize-VHD -ErrorAction SilentlyContinue) {
    Optimize-VHD -Path $vhdx -Mode Full
    $optimized = $true
} else {
    # diskpart fallback — works without Hyper-V management tools.
    Write-Host "Optimize-VHD unavailable (Hyper-V tools not installed) — using diskpart."
    $script = @"
select vdisk file="$vhdx"
attach vdisk readonly
compact vdisk
detach vdisk
"@
    $script | diskpart | Out-Null
    $optimized = $true
}

$sizeAfter = (Get-Item $vhdx).Length
$reclaimed = ($sizeBefore - $sizeAfter) / 1GB
Write-Host ("Size after:  {0:N1} GB" -f ($sizeAfter/1GB))
Write-Host ("Reclaimed:   {0:N1} GB" -f $reclaimed)

if ($AutoStop) {
    Write-Host "Restarting Docker Desktop..."
    $dockerExe = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (Test-Path $dockerExe) { Start-Process $dockerExe }
    Write-Host "Docker Desktop is starting — run 'make up' once it reports healthy."
}
