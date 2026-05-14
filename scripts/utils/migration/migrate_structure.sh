#!/bin/bash

# Script de migración de estructura de directorios
# Ejecutar desde la raíz del proyecto

echo "Iniciando migración de estructura..."

# Crear directorios necesarios
mkdir -p artifacts/coverage/htmlcov
mkdir -p artifacts/logs
mkdir -p artifacts/results
mkdir -p docs/user-guide
mkdir -p docs/project
mkdir -p docs/playbooks

# Mover archivos de raíz a artifacts/
echo "Moviendo archivos de raíz a artifacts/..."
if [ -d "backups" ]; then
    mv backups/* artifacts/backups/
    rmdir backups
fi

if [ -d "htmlcov" ]; then
    mv htmlcov/* artifacts/coverage/htmlcov/
    rmdir htmlcov
fi

if [ -d "results" ]; then
    mv results/* artifacts/results/
    rmdir results
fi

# Mover archivos de src/soar_lab/
echo "Moviendo archivos de src/soar_lab/..."
if [ -f "src/soar_lab/services/tfm_data_enhancer.py" ]; then
    mv src/soar_lab/services/tfm_data_enhancer.py src/soar_lab/analytics/
fi

if [ -f "src/soar_lab/services/tfm_data_viewer.py" ]; then
    mv src/soar_lab/services/tfm_data_viewer.py src/soar_lab/analytics/
fi

if [ -f "src/soar_lab/utils/generate_secrets.py" ]; then
    mv src/soar_lab/utils/generate_secrets.py src/soar_lab/services/
fi

if [ -d "src/soar_lab/results" ]; then
    mv src/soar_lab/results/* artifacts/results/
    rmdir src/soar_lab/results
fi

# Mover archivos de tests/
echo "Moviendo archivos de tests/..."
if [ -d "tests/logs" ]; then
    mv tests/logs/* artifacts/logs/
    rmdir tests/logs
fi

if [ -d "tests/results" ]; then
    mv tests/results/* artifacts/results/
    rmdir tests/results
fi

# Mover archivos de docs/
echo "Moviendo archivos de docs/..."
if [ -f "docs/operations/user_guide.md" ]; then
    mv docs/operations/user_guide.md docs/user-guide/
fi

if [ -f "docs/objectives.md" ]; then
    mv docs/objectives.md docs/project/
fi

if [ -f "docs/plan.md" ]; then
    mv docs/plan.md docs/project/
fi

if [ -f "docs/scope.md" ]; then
    mv docs/scope.md docs/project/
fi

# Mover playbooks/
echo "Moviendo playbooks/..."
if [ -d "playbooks" ]; then
    mv playbooks docs/
fi

# Eliminar __pycache__
echo "Eliminando directorios __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "Migración completada."
