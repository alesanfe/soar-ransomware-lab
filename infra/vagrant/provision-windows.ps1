# ==============================================================================
# SOAR Ransomware Lab - Windows VM Provisioning
# Instala Wazuh Agent, Python y el simulador SIEM para generar trafico
# ==============================================================================

$ErrorActionPreference = "Stop"
$SOAR_IP = "192.168.56.10"
$WAZUH_MANAGER_IP = $SOAR_IP
$WAZUH_AGENT_VERSION = "4.7.3-1"
$PYTHON_VERSION = "3.11.9"
$REPO_DIR = "C:\vagrant"
$SIEM_WEBHOOK_URL = "http://${SOAR_IP}:5001/api/v1/hooks/siem-alerts"
$SIEM_WEBHOOK_TOKEN = "SiemToken123!@#"

Write-Host "==> [1/5] Instalando Chocolatey..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue))
{
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

Write-Host "==> [2/5] Instalando Python ${PYTHON_VERSION}..."
choco install python --version=$PYTHON_VERSION -y --no-progress
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

Write-Host "==> [3/5] Instalando Wazuh Agent ${WAZUH_AGENT_VERSION}..."
$wazuhInstaller = "C:\wazuh-agent-${WAZUH_AGENT_VERSION}.msi"
$wazuhUrl = "https://packages.wazuh.com/4.x/windows/wazuh-agent-${WAZUH_AGENT_VERSION}.msi"
if (-not (Test-Path $wazuhInstaller))
{
    Write-Host "    Descargando Wazuh Agent..."
    Invoke-WebRequest -Uri $wazuhUrl -OutFile $wazuhInstaller -UseBasicParsing
}
Write-Host "    Instalando Wazuh Agent apuntando a ${WAZUH_MANAGER_IP}..."
Start-Process msiexec.exe -ArgumentList "/i `"${wazuhInstaller}`" /qn WAZUH_MANAGER=`"${WAZUH_MANAGER_IP}`" WAZUH_AGENT_GROUP=`"default`" WAZUH_AGENT_NAME=`"victima-windows`"" -Wait
Write-Host "    Iniciando servicio Wazuh Agent..."
Start-Service -Name "WazuhSvc" -ErrorAction SilentlyContinue
Set-Service -Name "WazuhSvc" -StartupType Automatic -ErrorAction SilentlyContinue

Write-Host "==> [4/5] Instalando dependencias Python del simulador SIEM..."
# El repo ya está sincronizado via synced_folder en C:\vagrant
pip install requests 2> $null
if (Test-Path "$REPO_DIR\apps\api\requirements.txt")
{
    pip install -r "$REPO_DIR\apps\api\requirements.txt" 2> $null
}
if (Test-Path "$REPO_DIR\pyproject.toml")
{
    pip install -e $REPO_DIR 2> $null
}

Write-Host "==> [5/5] Creando script de simulacion de ataque..."
$simulateScript = @"
# simulate-attack.ps1 - Ejecutar para simular ataque de ransomware
# Envia alertas al SOAR via webhook de Shuffle

`$env:SHUFFLE_WEBHOOK_URL = "${SIEM_WEBHOOK_URL}"
`$env:SIEM_WEBHOOK_TOKEN  = "${SIEM_WEBHOOK_TOKEN}"
`$env:PYTHONPATH          = "${REPO_DIR}\src"
`$env:BASE_DIR             = "${REPO_DIR}"

Write-Host "Iniciando simulacion de ataque ransomware..."
Write-Host "  SOAR IP     : ${SOAR_IP}"
Write-Host "  Webhook URL : `$env:SHUFFLE_WEBHOOK_URL"
Write-Host ""

python -m soar_lab.services.send_alert --type malicious --num-alerts 5 --delay 3 --webhook-url `$env:SHUFFLE_WEBHOOK_URL --api-token `$env:SIEM_WEBHOOK_TOKEN
"@
$simulateScript | Out-File -FilePath "C:\simulate-attack.ps1" -Encoding UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host " Windows VM lista"
Write-Host " Wazuh Agent apunta a: ${WAZUH_MANAGER_IP}"
Write-Host " Para simular ataque ejecutar:"
Write-Host "   powershell C:\simulate-attack.ps1"
Write-Host "============================================================"
