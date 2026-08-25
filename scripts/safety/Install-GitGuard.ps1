<#
.SYNOPSIS
  Instala un guard de git en el $PROFILE de PowerShell del usuario actual.

.DESCRIPTION
  Añade una funcion 'git' al perfil de PowerShell que intercepta comandos destructivos
  (reset, checkout --, restore, stash, clean -fd, rebase, commit --amend, branch -D,
  push --force, rm, revert, update-ref) y pide confirmacion 'SI-CONFIRMO' antes de
  ejecutarlos.

  Los agentes automatizados (Devin, Copilot) no pueden responder al prompt, asi que
  el bloqueo es efectivo contra ellos. El usuario humano puede confirmar manualmente.

.PARAMETER Uninstall
  Quita el guard del perfil.

.EXAMPLE
  .\Install-GitGuard.ps1
  .\Install-GitGuard.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [switch]$Uninstall
)

$markerStart = "# >>> GIT-GUARD soar-ransomware-lab >>>"
$markerEnd   = "# <<< GIT-GUARD soar-ransomware-lab <<<"

if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if (-not $profileContent) { $profileContent = "" }

if ($Uninstall) {
    if ($profileContent -match "(?s)$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))") {
        $new = $profileContent -replace "(?s)$([regex]::Escape($markerStart)).*?$([regex]::Escape($markerEnd))\r?\n?", ""
        Set-Content -Path $PROFILE -Value $new -NoNewline
        Write-Host "Git-Guard desinstalado de $PROFILE" -ForegroundColor Green
    } else {
        Write-Host "Git-Guard no estaba instalado en $PROFILE" -ForegroundColor Yellow
    }
    return
}

if ($profileContent -match $markerStart) {
    Write-Host "Git-Guard ya esta instalado en $PROFILE" -ForegroundColor Yellow
    return
}

$guard = @"

$markerStart
function git {
    `$sub = if (`$args.Count -gt 0) { `$args[0] } else { "" }
    `$argString = (`$args | ForEach-Object { `$_ }) -join " "
    `$destructive = @('reset','stash','clean','rebase','revert','rm','update-ref')
    `$needsConfirm = `$false
    `$reason = ""
    if (`$destructive -contains `$sub) {
        `$needsConfirm = `$true; `$reason = "git `$sub es potencialmente destructivo"
    } elseif (`$sub -eq 'checkout' -and (`$argString -match '--\s' -or `$argString -match '\s\.\s*$' -or `$argString -match '\s\.$')) {
        `$needsConfirm = `$true; `$reason = "git checkout -- descarta cambios del working tree"
    } elseif (`$sub -eq 'restore') {
        `$needsConfirm = `$true; `$reason = "git restore descarta cambios del working tree"
    } elseif (`$sub -eq 'commit' -and `$argString -match '--amend') {
        `$needsConfirm = `$true; `$reason = "git commit --amend reescribe historial"
    } elseif (`$sub -eq 'branch' -and `$argString -match '-D|--delete') {
        `$needsConfirm = `$true; `$reason = "git branch -D fuerza el borrado de rama"
    } elseif (`$sub -eq 'push' -and `$argString -match '--force|`-f\b') {
        `$needsConfirm = `$true; `$reason = "git push --force reescribe historial remoto"
    }
    if (`$needsConfirm) {
        Write-Host ""
        Write-Host "  BLOQUEO DE SEGURIDAD — soar-ransomware-lab" -ForegroundColor Yellow
        Write-Host "  `$reason" -ForegroundColor Yellow
        Write-Host "  Comando: git `$argString" -ForegroundColor Cyan
        Write-Host ""
        `$resp = Read-Host "  Escriba 'SI-CONFIRMO' para ejecutar (cualquier otra cosa cancela)"
        if (`$resp -ne 'SI-CONFIRMO') {
            Write-Host "  Operacion cancelada." -ForegroundColor Green
            return
        }
        Write-Host "  Ejecutando con confirmacion..." -ForegroundColor Green
    }
    & git.exe @args
}
$markerEnd
"@

Add-Content -Path $PROFILE -Value $guard
Write-Host "Git-Guard instalado en $PROFILE" -ForegroundColor Green
Write-Host "Reinicia PowerShell o ejecuta: . `$PROFILE" -ForegroundColor Cyan
Write-Host "Para desinstalar: .\Install-GitGuard.ps1 -Uninstall" -ForegroundColor Cyan
