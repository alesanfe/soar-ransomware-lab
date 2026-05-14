# Script de migración de estructura de directorios para PowerShell
# Ejecutar desde la raíz del proyecto

Write-Host "Iniciando migración de estructura..."

# Crear directorios necesarios
New-Item -ItemType Directory -Force -Path "artifacts\coverage\htmlcov" | Out-Null
New-Item -ItemType Directory -Force -Path "artifacts\logs" | Out-Null
New-Item -ItemType Directory -Force -Path "artifacts\results" | Out-Null
New-Item -ItemType Directory -Force -Path "docs\user-guide" | Out-Null
New-Item -ItemType Directory -Force -Path "docs\project" | Out-Null
New-Item -ItemType Directory -Force -Path "docs\playbooks" | Out-Null

# Mover archivos de raíz a artifacts/
Write-Host "Moviendo archivos de raíz a artifacts/..."
if (Test-Path "backups") {
    Move-Item -Path "backups\*" -Destination "artifacts\backups\" -Force
    Remove-Item -Path "backups" -Recurse -Force
}

if (Test-Path "htmlcov") {
    Move-Item -Path "htmlcov\*" -Destination "artifacts\coverage\htmlcov\" -Force
    Remove-Item -Path "htmlcov" -Recurse -Force
}

if (Test-Path "results") {
    Move-Item -Path "results\*" -Destination "artifacts\results\" -Force
    Remove-Item -Path "results" -Recurse -Force
}

# Mover archivos de src/soar_lab/
Write-Host "Moviendo archivos de src/soar_lab/..."
if (Test-Path "src\soar_lab\services\tfm_data_enhancer.py") {
    Move-Item -Path "src\soar_lab\services\tfm_data_enhancer.py" -Destination "src\soar_lab\analytics\" -Force
}

if (Test-Path "src\soar_lab\services\tfm_data_viewer.py") {
    Move-Item -Path "src\soar_lab\services\tfm_data_viewer.py" -Destination "src\soar_lab\analytics\" -Force
}

if (Test-Path "src\soar_lab\utils\generate_secrets.py") {
    Move-Item -Path "src\soar_lab\utils\generate_secrets.py" -Destination "src\soar_lab\services\" -Force
}

if (Test-Path "src\soar_lab\results") {
    Move-Item -Path "src\soar_lab\results\*" -Destination "artifacts\results\" -Force
    Remove-Item -Path "src\soar_lab\results" -Recurse -Force
}

# Mover archivos de tests/
Write-Host "Moviendo archivos de tests/..."
if (Test-Path "tests\logs") {
    Move-Item -Path "tests\logs\*" -Destination "artifacts\logs\" -Force
    Remove-Item -Path "tests\logs" -Recurse -Force
}

if (Test-Path "tests\results") {
    Move-Item -Path "tests\results\*" -Destination "artifacts\results\" -Force
    Remove-Item -Path "tests\results" -Recurse -Force
}

# Mover archivos de docs/
Write-Host "Moviendo archivos de docs/..."
if (Test-Path "docs\operations\user_guide.md") {
    Move-Item -Path "docs\operations\user_guide.md" -Destination "docs\user-guide\" -Force
}

if (Test-Path "docs\objectives.md") {
    Move-Item -Path "docs\objectives.md" -Destination "docs\project\" -Force
}

if (Test-Path "docs\plan.md") {
    Move-Item -Path "docs\plan.md" -Destination "docs\project\" -Force
}

if (Test-Path "docs\scope.md") {
    Move-Item -Path "docs\scope.md" -Destination "docs\project\" -Force
}

# Mover playbooks/
Write-Host "Moviendo playbooks/..."
if (Test-Path "playbooks") {
    Move-Item -Path "playbooks" -Destination "docs\" -Force
}

# Eliminar __pycache__
Write-Host "Eliminando directorios __pycache__..."
Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object {
    Remove-Item -Path $_ -Recurse -Force -ErrorAction SilentlyContinue
}
Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | ForEach-Object {
    Remove-Item -Path $_ -Force -ErrorAction SilentlyContinue
}

Write-Host "Migración completada."
