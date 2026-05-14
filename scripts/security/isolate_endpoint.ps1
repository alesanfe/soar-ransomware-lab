#Requires -Version 5.1

<#
.SYNOPSIS
    SOAR Ransomware Lab - Windows Endpoint Isolation Script
.DESCRIPTION
    Simulates endpoint containment actions for ransomware response.
    Includes network isolation, process termination, and account lockdown.
.PARAMETER Hostname
    Target hostname to contain.
.PARAMETER CaseId
    Case identifier for tracking.
.EXAMPLE
    .\isolate_endpoint.ps1 -Hostname 'WIN-001' -CaseId 'CASE-12345'
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Hostname,
    
    [Parameter(Mandatory=$true)]
    [string]$CaseId,
    
    [Parameter()]
    [string]$LogFile = "./artifacts/logs/containment.log",
    
    [Parameter()]
    [string]$BackupDir = "./artifacts/backups",
    
    [Parameter()]
    [bool]$SimulationMode = $true
)

# Ensure log directory exists
$logDir = Split-Path $LogFile -Parent
if ($logDir) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

# Logging function
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] $Message"
    Write-Host $logEntry
    Add-Content -Path $LogFile -Value $logEntry
}

# Function to simulate network isolation
function Disable-Network {
    param([string]$Hostname, [string]$CaseId)
    
    Write-Log "NETWORK ISOLATION - Host: $Hostname, Case: $CaseId"
    
    if ($SimulationMode) {
        Write-Log "[SIMULATION] Disabling network adapters on $Hostname"
        Write-Log "[SIMULATION] Get-NetAdapter | Disable-NetAdapter"
        Write-Log "[SIMULATION] New-NetFirewallRule -DisplayName 'Block All' -Direction Outbound -Action Block"
        Write-Log "[SIMULATION] New-NetFirewallRule -DisplayName 'Block All In' -Direction Inbound -Action Block"
        Write-Log "[SIMULATION] Network isolation completed for $Hostname"
    } else {
        Write-Log "WARNING: Real network isolation mode enabled"
        # Get-NetAdapter | Disable-NetAdapter
        # New-NetFirewallRule -DisplayName "Block All" -Direction Outbound -Action Block
        # New-NetFirewallRule -DisplayName "Block All In" -Direction Inbound -Action Block
        Write-Log "Real network isolation would be executed here"
    }
}

# Compatibility alias for tests
function Isolate-Network { Disable-Network @PSBoundParameters }

# Function to simulate process termination
function Stop-MaliciousProcess {
    param([string]$Hostname, [string]$CaseId)
    
    Write-Log "PROCESS TERMINATION - Host: $Hostname, Case: $CaseId"
    
    if ($SimulationMode) {
        Write-Log "[SIMULATION] Scanning for suspicious processes on $Hostname"
        Write-Log "[SIMULATION] Found processes: ransomware.exe (PID: 1234), cryptolocker.exe (PID: 5678)"
        Write-Log "[SIMULATION] Terminating malicious processes"
        Write-Log "[SIMULATION] Stop-Process -Id 1234 -Force"
        Write-Log "[SIMULATION] Stop-Process -Id 5678 -Force"
        Write-Log "[SIMULATION] Process termination completed"
    } else {
        Write-Log "WARNING: Real process termination mode enabled"
        # Get-Process -Name "ransomware" | Stop-Process -Force
        # Get-Process -Name "cryptolocker" | Stop-Process -Force
        Write-Log "Real process termination would be executed here"
    }
}

# Compatibility alias for tests
function Terminate-MaliciousProcesses { Stop-MaliciousProcess @PSBoundParameters }

# Function to simulate user account lockdown
function Lockdown-Accounts {
    param([string]$Hostname, [string]$CaseId)
    
    Write-Log "ACCOUNT LOCKDOWN - Host: $Hostname, Case: $CaseId"
    
    if ($SimulationMode) {
        Write-Log "[SIMULATION] Locking down user accounts on $Hostname"
        Write-Log "[SIMULATION] Disable-ADAccount -Identity 'infected_user'"
        Write-Log "[SIMULATION] Set-ADAccountPassword -Identity 'infected_user' -Reset -NewPassword (ConvertTo-SecureString 'TempPass123!' -AsPlainText -Force)"
        Write-Log "[SIMULATION] Account lockdown completed"
    } else {
        Write-Log "WARNING: Real account lockdown mode enabled"
        # Disable-ADAccount -Identity "infected_user"
        # Set-ADAccountPassword -Identity "infected_user" -Reset -NewPassword (ConvertTo-SecureString "TempPass123!" -AsPlainText -Force)
        Write-Log "Real account lockdown would be executed here"
    }
}

# Function to simulate file system protection
function Protect-Filesystem {
    param([string]$Hostname, [string]$CaseId)
    
    Write-Log "FILESYSTEM PROTECTION - Host: $Hostname, Case: $CaseId"
    
    if ($SimulationMode) {
        Write-Log "[SIMULATION] Encrypting sensitive files on $Hostname"
        Write-Log "[SIMULATION] BitLocker-Locker: C: -MountPoint 'C:' -Password 'SecurePass123!'"
        Write-Log "[SIMULATION] Setting file permissions to read-only"
        Write-Log "[SIMULATION] Get-ChildItem -Path 'C:\Users' -Recurse | Set-ItemProperty -Name IsReadOnly -Value $true"
        Write-Log "[SIMULATION] Filesystem protection completed"
    } else {
        Write-Log "WARNING: Real filesystem protection mode enabled"
        # Enable-BitLocker -MountPoint "C:" -PasswordProtector
        # Get-ChildItem -Path "C:\Users" -Recurse | Set-ItemProperty -Name IsReadOnly -Value $true
        # Set-Acl -Path "C:\Data" -AclObject $null
        Write-Log "Real filesystem protection would be executed here"
    }
}

# Function to create forensic backup
function New-ForensicBackup {
    param([string]$Hostname, [string]$CaseId)
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $BackupDir "${CaseId}_${Hostname}_${timestamp}"
    
    Write-Log "FORENSIC BACKUP - Host: $Hostname, Case: $CaseId"
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    
    if ($SimulationMode) {
        Write-Log "[SIMULATION] Creating forensic backup at $backupPath"
        Write-Log "[SIMULATION] Dumping memory: C:\temp\memory.dmp -> $backupPath\memory.dmp"
        Write-Log "[SIMULATION] Copying event logs: C:\Windows\System32\winevt\Logs -> $backupPath\logs"
        Write-Log "[SIMULATION] Copying registry: reg export HKLM -> $backupPath\registry_hkml.reg"
        Write-Log "[SIMULATION] Copying prefetch: C:\Windows\Prefetch -> $backupPath\prefetch"
        Write-Log "[SIMULATION] Forensic backup completed"
        Write-Log "[SIMULATION] Compress-Archive -Path $backupPath -DestinationPath $backupPath.zip"
    } else {
        Write-Log "Creating real forensic backup at $backupPath"
        # Copy-Item "C:\temp\memory.dmp" $backupPath -ErrorAction SilentlyContinue
        # Copy-Item "C:\Windows\System32\winevt\Logs" $backupPath\logs -Recurse -ErrorAction SilentlyContinue
        # reg export "HKLM" "$backupPath\registry_hkml.reg"
        # Copy-Item "C:\Windows\Prefetch" $backupPath\prefetch -Recurse -ErrorAction SilentlyContinue
        # Compress-Archive -Path $backupPath -DestinationPath "$backupPath.zip"
        Write-Log "Real forensic backup would be created here"
    }
    
    return $backupPath
}

# Function to generate containment report
function New-ContainmentReport {
    param([string]$Hostname, [string]$CaseId, [string]$BackupPath)
    
    Write-Log "CONTAINMENT REPORT - Host: $Hostname, Case: $CaseId"
    
    $reportFile = Join-Path $BackupDir "${CaseId}_${Hostname}_containment_report.json"
    
    $report = @{
        case_id = $CaseId
        hostname = $Hostname
        containment_timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
        actions_performed = @(
            "network_isolation",
            "process_termination", 
            "account_lockdown",
            "filesystem_protection",
            "forensic_backup"
        )
        backup_location = $BackupPath
        simulation_mode = $SimulationMode
        status = "completed"
        next_steps = @(
            "Analyze forensic evidence",
            "Restore from backup",
            "Update security policies",
            "User education"
        )
    }
    
    $report | ConvertTo-Json -Depth 10 | Set-Content -Path $reportFile -Encoding UTF8
    Write-Log "Containment report generated: $reportFile"
    
    return $reportFile
}

# Main containment function
function Invoke-Containment {
    param([string]$Hostname, [string]$CaseId)
    
    Write-Log "=== STARTING CONTAINMENT PROCEDURE ==="
    Write-Log "Host: $Hostname"
    Write-Log "Case ID: $CaseId"
    Write-Log "Simulation Mode: $SimulationMode"
    
    # Validate inputs
    try {
        if ([string]::IsNullOrEmpty($Hostname) -or [string]::IsNullOrEmpty($CaseId)) {
            throw "Missing required parameters: hostname and case_id"
        }
        
        if (-not ($Hostname -match '^[a-zA-Z0-9_-]+$')) {
            throw "Invalid hostname format"
        }
        
        # Execute containment steps
        Disable-Network -Hostname $Hostname -CaseId $CaseId
        Stop-MaliciousProcess -Hostname $Hostname -CaseId $CaseId
        Lockdown-Accounts -Hostname $Hostname -CaseId $CaseId
        Protect-Filesystem -Hostname $Hostname -CaseId $CaseId
        
        # Create forensic backup
        $backupPath = New-ForensicBackup -Hostname $Hostname -CaseId $CaseId
        
        # Generate report
        $reportFile = New-ContainmentReport -Hostname $Hostname -CaseId $CaseId -BackupPath $backupPath
        
        Write-Log "=== CONTAINMENT PROCEDURE COMPLETED ==="
        Write-Log "Backup location: $backupPath"
        Write-Log "Report file: $reportFile"
        
        # Log to notify.log for KPI calculation
        $notifyLog = "artifacts/logs/notify.log"
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') STEP: Containment executed" | Out-File -Append -FilePath $notifyLog
        
        # Return success
        Write-Output "SUCCESS: Host $Hostname contained successfully"
        Write-Output "Case ID: $CaseId"
        Write-Output "Backup: $backupPath"
        Write-Output "Report: $reportFile"
    } catch {
        Write-Log "ERROR: $($_.Exception.Message)"
        exit 1
    }
}

# Function to show usage
function Show-Usage {
    Write-Host "Usage: .\$($MyInvocation.MyCommand.Name) -Hostname <hostname> -CaseId <case_id>"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Hostname    Target hostname to contain"
    Write-Host "  -CaseId      Case identifier for tracking"
    Write-Host "  -LogFile     Path to log file (default: ./artifacts/logs/containment.log)"
    Write-Host "  -BackupDir    Directory for backups (default: ./artifacts/backups)"
    Write-Host "  -SimulationMode  true (default) or false"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\$($MyInvocation.MyCommand.Name) -Hostname 'WIN-001' -CaseId 'CASE-12345'"
    Write-Host "  .\$($MyInvocation.MyCommand.Name) -Hostname 'WIN-001' -CaseId 'CASE-12345' -SimulationMode `$false"
}

# Parse command line arguments
if ($args.Count -eq 0 -and (-not $PSBoundParameters.ContainsKey('Hostname') -or -not $PSBoundParameters.ContainsKey('CaseId'))) {
    Show-Usage
    exit 1
}

# Execute main function
Invoke-Containment -Hostname $Hostname -CaseId $CaseId
