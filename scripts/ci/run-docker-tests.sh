#!/bin/bash

# Docker Ports Testing CI/CD Script
# Comprehensive testing for Docker ports and services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_PROJECT_NAME="soartest"
ELASTIC_PASSWORD="testpassword123"
REDIS_PASSWORD="testpassword123"
GRAFANA_PASSWORD="admin123"
THEHIVE_SECRET="thehive-test-secret"
THEHIVE_API_KEY="thehive-test-api-key"
CORTEX_SECRET="cortex-test-secret"
CORTEX_API_KEY="cortex-test-api-key"

# Test types
TEST_TYPE="${1:-all}"
SERVICES="${2:-core}"

echo -e "${BLUE}🐳 Docker Ports Testing CI/CD${NC}"
echo -e "${BLUE}===================================${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check Docker daemon
check_docker() {
    if ! docker --version > /dev/null 2>&1; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_status "Docker daemon is running"
}

# Function to start services
start_services() {
    print_status "Starting Docker services: $SERVICES"
    
    case "$SERVICES" in
        "core")
            cd infra/docker
            export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
            export ELASTIC_PASSWORD="$ELASTIC_PASSWORD"
            export REDIS_PASSWORD="$REDIS_PASSWORD"
            export GRAFANA_PASSWORD="$GRAFANA_PASSWORD"
            
            docker-compose -f docker-compose-ports.yml up -d
            ;;
        "extended")
            cd infra/docker
            export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
            export ELASTIC_PASSWORD="$ELASTIC_PASSWORD"
            export REDIS_PASSWORD="$REDIS_PASSWORD"
            export GRAFANA_PASSWORD="$GRAFANA_PASSWORD"
            export THEHIVE_SECRET="$THEHIVE_SECRET"
            export THEHIVE_API_KEY="$THEHIVE_API_KEY"
            export CORTEX_SECRET="$CORTEX_SECRET"
            export CORTEX_API_KEY="$CORTEX_API_KEY"
            
            docker-compose -f docker-compose-extended.yml up -d
            ;;
        "full")
            cd infra/docker
            export COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME"
            export ELASTIC_PASSWORD="$ELASTIC_PASSWORD"
            export REDIS_PASSWORD="$REDIS_PASSWORD"
            export GRAFANA_PASSWORD="$GRAFANA_PASSWORD"
            export THEHIVE_SECRET="$THEHIVE_SECRET"
            export THEHIVE_API_KEY="$THEHIVE_API_KEY"
            export CORTEX_SECRET="$CORTEX_SECRET"
            export CORTEX_API_KEY="$CORTEX_API_KEY"
            export MISP_DB_ROOT_PASSWORD="misptest123"
            export MISP_DB_PASSWORD="misptest123"
            export MISP_REDIS_PASSWORD="misptest123"
            export MISP_GPG_PASSWORD="misptest123"
            export MISP_ADMIN_PASSWORD="misptest123"
            export OPENCTI_DB_PASSWORD="openctitest123"
            export OPENCTI_ADMIN_PASSWORD="openctitest123"
            export MINIO_ROOT_PASSWORD="miniotest123"
            export INFLUXDB_PASSWORD="influxtest123"
            export API_AUTH_SECRET="apitestsecret123"
            
            docker-compose up -d elasticsearch redis thehive cortex grafana prometheus
            ;;
        *)
            print_error "Unknown services type: $SERVICES"
            exit 1
            ;;
    esac
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 30
    
    # Show running containers
    docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
}

# Function to run tests
run_tests() {
    local test_type="$1"
    
    # Create reports directory
    mkdir -p reports
    
    case "$test_type" in
        "internal"|"all"|"")
            print_status "Running internal Docker tests..."
            python -m pytest tests/integration/test_docker_ports_internal.py -v \
                --tb=short \
                --html=reports/internal-tests.html \
                --cov=src/soar_lab \
                --cov-report=html:reports/coverage-internal \
                --cov-report=xml:reports/coverage-internal.xml \
                --junitxml=reports/internal-tests.xml || true
            ;;
    esac
    
    case "$test_type" in
        "external"|"all"|"")
            print_status "Running external port tests..."
            python -m pytest tests/integration/test_docker_ports_complete.py -v \
                --tb=short \
                --html=reports/external-tests.html \
                --cov=src/soar_lab \
                --cov-report=html:reports/coverage-external \
                --cov-report=xml:reports/coverage-external.xml \
                --junitxml=reports/external-tests.xml || true
            ;;
    esac
    
    case "$test_type" in
        "selenium"|"all"|"")
            print_status "Running Selenium UI tests..."
            python -m pytest tests/browser/test_docker_ports_selenium.py -v \
                --tb=short \
                --html=reports/selenium-tests.html \
                --cov=src/soar_lab \
                --cov-report=html:reports/coverage-selenium \
                --cov-report=xml:reports/coverage-selenium.xml \
                --junitxml=reports/selenium-tests.xml || true
            ;;
    esac
    
    # Generate summary report
    print_status "Generating comprehensive test report..."
    python -m pytest tests/integration/test_docker_ports_summary.py -v \
        --tb=short \
        --html=reports/summary-report.html \
        --junitxml=reports/summary-tests.xml || true
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up Docker resources..."
    cd infra/docker
    
    docker-compose -f docker-compose-ports.yml down -v || true
    docker-compose -f docker-compose-extended.yml down -v || true
    docker-compose down -v || true
    docker system prune -f
    
    print_status "Cleanup completed"
}

# Function to generate summary report
generate_summary() {
    print_status "Generating test summary..."
    
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo -e "${BLUE}==============${NC}"
    
    if [ -f "reports/internal-tests.xml" ]; then
        echo -e "${GREEN}Internal Tests:${NC}"
        python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('reports/internal-tests.xml')
    root = tree.getroot()
    testsuite = root.find('testsuite')
    if testsuite is not None:
        print(f'  Tests: {testsuite.get(\"tests\", \"N/A\")}')
        print(f'  Failures: {testsuite.get(\"failures\", \"N/A\")}')
        print(f'  Time: {testsuite.get(\"time\", \"N/A\")}s')
except:
    print('  Could not parse results')
"
    fi
    
    if [ -f "reports/external-tests.xml" ]; then
        echo -e "${GREEN}External Tests:${NC}"
        python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('reports/external-tests.xml')
    root = tree.getroot()
    testsuite = root.find('testsuite')
    if testsuite is not None:
        print(f'  Tests: {testsuite.get(\"tests\", \"N/A\")}')
        print(f'  Failures: {testsuite.get(\"failures\", \"N/A\")}')
        print(f'  Time: {testsuite.get(\"time\", \"N/A\")}s')
except:
    print('  Could not parse results')
"
    fi
    
    if [ -f "reports/selenium-tests.xml" ]; then
        echo -e "${GREEN}Selenium Tests:${NC}"
        python -c "
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('reports/selenium-tests.xml')
    root = tree.getroot()
    testsuite = root.find('testsuite')
    if testsuite is not None:
        print(f'  Tests: {testsuite.get(\"tests\", \"N/A\")}')
        print(f'  Failures: {testsuite.get(\"failures\", \"N/A\")}')
        print(f'  Time: {testsuite.get(\"time\", \"N/A\")}s')
except:
    print('  Could not parse results')
"
    fi
    
    echo -e "${BLUE}Reports generated in: reports/${NC}"
}

# Main execution
main() {
    print_status "Starting Docker Ports Testing CI/CD"
    print_status "Test Type: $TEST_TYPE"
    print_status "Services: $SERVICES"
    
    # Trap for cleanup
    trap cleanup EXIT
    
    # Check prerequisites
    check_docker
    
    # Start services
    start_services
    
    # Run tests
    run_tests "$TEST_TYPE"
    
    # Generate summary
    generate_summary
    
    print_status "Docker Ports Testing CI/CD completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    "help"|"-h"|"--help")
        echo "Usage: $0 [TEST_TYPE] [SERVICES]"
        echo ""
        echo "TEST_TYPE:"
        echo "  internal    Run internal Docker tests only"
        echo "  external    Run external port tests only"
        echo "  selenium    Run Selenium UI tests only"
        echo "  all         Run all tests (default)"
        echo ""
        echo "SERVICES:"
        echo "  core        Start core services only (default)"
        echo "  extended    Start extended services"
        echo "  full        Start all services"
        echo ""
        echo "Examples:"
        echo "  $0                    # Run all tests with core services"
        echo "  $0 internal core     # Run internal tests with core services"
        echo "  $0 selenium extended # Run Selenium tests with extended services"
        exit 0
        ;;
    *)
        main
        ;;
esac
