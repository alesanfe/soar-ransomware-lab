#!/bin/bash

# SOAR Ransomware Lab - Dependency Checker
# Verifies that all required dependencies are installed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL=0
PASSED=0
FAILED=0

# Function to check command
check_command() {
    local cmd="$1"
    local name="$2"
    local install_cmd="${3:-}"
    
    TOTAL=$((TOTAL + 1))
    
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name ($(command -v "$cmd"))"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name no encontrado"
        if [ -n "$install_cmd" ]; then
            echo -e "  ${YELLOW}Instalar con:${NC} $install_cmd"
        fi
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    local pkg="$1"
    local name="$2"
    
    TOTAL=$((TOTAL + 1))
    
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name (Python package)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name no encontrado (Python package)"
        echo -e "  ${YELLOW}Instalar con:${NC} pip3 install $pkg"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to check file
check_file() {
    local file="$1"
    local name="$2"
    
    TOTAL=$((TOTAL + 1))
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $name existe"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name no encontrado"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to check directory
check_dir() {
    local dir="$1"
    local name="$2"
    
    TOTAL=$((TOTAL + 1))
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $name existe"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $name no encontrado"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to check Docker
check_docker() {
    TOTAL=$((TOTAL + 1))
    
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Docker funcionando ($(docker --version))"
            PASSED=$((PASSED + 1))
            return 0
        else
            echo -e "${RED}✗${NC} Docker instalado pero no funcionando (daemon no iniciado)"
            FAILED=$((FAILED + 1))
            return 1
        fi
    else
        echo -e "${RED}✗${NC} Docker no encontrado"
        echo -e "  ${YELLOW}Instalar con:${NC} https://docs.docker.com/get-docker/"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Function to check Docker Compose
check_docker_compose() {
    TOTAL=$((TOTAL + 1))
    
    if docker compose version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker Compose funcionando ($(docker compose version))"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Docker Compose no encontrado"
        echo -e "  ${YELLOW}Instalar con:${NC} https://docs.docker.com/compose/install/"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "=== Verificación de Dependencias - SOAR Ransomware Lab ==="
echo ""

echo "## Dependencias del Sistema"
check_command "docker" "Docker"
check_docker
check_docker_compose
check_command "python3" "Python 3" "apt-get install python3 o brew install python3"
check_command "pip3" "pip3" "apt-get install python3-pip o brew install python3"
check_command "openssl" "OpenSSL" "apt-get install openssl o brew install openssl"
check_command "curl" "curl" "apt-get install curl o brew install curl"
check_command "wget" "wget" "apt-get install wget o brew install wget"
check_command "jq" "jq" "apt-get install jq o brew install jq"

echo ""
echo "## Paquetes Python"
check_python_package "json" "json"
check_python_package "requests" "requests"
check_python_package "jsonschema" "jsonschema"
check_python_package "statistics" "statistics"
check_python_package "pathlib" "pathlib"

echo ""
echo "## Archivos de Configuración"
check_file "infra/docker/.env" "Archivo .env"
check_file "infra/docker/compose/docker-compose.yml" "Docker Compose"
check_file "infra/docker/docker/thehive.application.conf/thehive.conf" "TheHive config"
check_file "infra/docker/docker/cortex.application.conf/cortex.conf" "Cortex config"
check_file "schemas/alert.schema.json" "Alert schema"

echo ""
echo "## Directorios"
check_dir "scripts" "Directorio scripts"
check_dir "schemas" "Directorio schemas"
check_dir "infra/docker" "Directorio infra/docker"
check_dir "docs" "Directorio docs"

echo ""
echo "## Resumen"
echo "Total de checks: $TOTAL"
echo -e "${GREEN}Pasados: $PASSED${NC}"
echo -e "${RED}Fallidos: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Todas las dependencias están instaladas${NC}"
    echo "El laboratorio está listo para iniciar."
    echo ""
    echo "Para iniciar el laboratorio:"
    echo "  make up"
    echo ""
    echo "Para generar certificados TLS:"
    echo "  make certs"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Faltan $FAILED dependencias${NC}"
    echo "Por favor, instale las dependencias faltantes antes de continuar."
    echo ""
    echo "Para instalar dependencias Python:"
    echo "  make deps"
    exit 1
fi
