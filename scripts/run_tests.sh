#!/bin/bash

# SOAR Ransomware Lab - Test Runner
# Executes all tests in the project

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"
}

# Function to run a test suite
run_test_suite() {
    local suite_name="$1"
    local test_command="$2"
    
    log "=== Running $suite_name ==="
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_command"; then
        log "✓ $suite_name PASSED"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        error "✗ $suite_name FAILED"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Main execution
log "=== SOAR Ransomware Lab - Test Suite ==="
log "Starting test execution..."
echo ""

# Check if we should run specific test types
RUN_UNIT="${RUN_UNIT:-true}"
RUN_INTEGRATION="${RUN_INTEGRATION:-true}"
RUN_E2E="${RUN_E2E:-true}"

# Unit Tests
if [ "$RUN_UNIT" = "true" ]; then
    info "Running Unit Tests..."
    echo ""
    
    # Test send_alert.py
    if [ -f "tests/unit/test_send_alert.py" ]; then
        run_test_suite "Unit: send_alert.py" "python3 -m pytest tests/unit/test_send_alert.py -v" || true
    else
        warn "test_send_alert.py not found, skipping"
    fi
    
    # Test calc_kpis.py
    if [ -f "tests/unit/test_calc_kpis.py" ]; then
        run_test_suite "Unit: calc_kpis.py" "python3 -m pytest tests/unit/test_calc_kpis.py -v" || true
    else
        warn "test_calc_kpis.py not found, skipping"
    fi
    
    # Run all unit tests with pytest if available
    if command -v pytest &> /dev/null; then
        run_test_suite "Unit: All (pytest)" "pytest tests/unit/ -v" || true
    else
        # Fallback to unittest
        run_test_suite "Unit: All (unittest)" "python3 -m unittest discover tests/unit/ -v" || true
    fi
    
    echo ""
fi

# Integration Tests
if [ "$RUN_INTEGRATION" = "true" ]; then
    info "Running Integration Tests..."
    echo ""
    
    # Check if Docker is available
    if command -v docker &> /dev/null; then
        # Test Docker configuration
        if [ -f "tests/integration/test_docker.py" ]; then
            run_test_suite "Integration: Docker" "python3 -m pytest tests/integration/test_docker.py -v" || true
        else
            warn "test_docker.py not found, skipping"
        fi
        
        # Run all integration tests
        if command -v pytest &> /dev/null; then
            run_test_suite "Integration: All (pytest)" "pytest tests/integration/ -v" || true
        else
            run_test_suite "Integration: All (unittest)" "python3 -m unittest discover tests/integration/ -v" || true
        fi
    else
        warn "Docker not available, skipping integration tests"
    fi
    
    echo ""
fi

# E2E Tests
if [ "$RUN_E2E" = "true" ]; then
    info "Running E2E Tests..."
    echo ""
    
    # TC-01: Malicious case
    if [ -f "tests/e2e/TC-01/test_malicious.sh" ]; then
        run_test_suite "E2E: TC-01 Malicious" "bash tests/e2e/TC-01/test_malicious.sh" || true
    else
        warn "TC-01 test not found, skipping"
    fi
    
    # TC-02: Benign case
    if [ -f "tests/e2e/TC-02/test_benign.sh" ]; then
        run_test_suite "E2E: TC-02 Benign" "bash tests/e2e/TC-02/test_benign.sh" || true
    else
        warn "TC-02 test not found, skipping"
    fi
    
    # TC-03: Edge cases
    if [ -f "tests/e2e/TC-03/test_edge_cases.sh" ]; then
        run_test_suite "E2E: TC-03 Edge Cases" "bash tests/e2e/TC-03/test_edge_cases.sh" || true
    else
        warn "TC-03 test not found, skipping"
    fi
    
    # TC-04: Performance
    if [ -f "tests/e2e/TC-04/test_performance.sh" ]; then
        run_test_suite "E2E: TC-04 Performance" "bash tests/e2e/TC-04/test_performance.sh" || true
    else
        warn "TC-04 test not found, skipping"
    fi
    
    echo ""
fi

# Summary
log "=== Test Execution Summary ==="
log "Total test suites: $TOTAL_TESTS"
log -e "${GREEN}Passed: $PASSED_TESTS${NC}"
log -e "${RED}Failed: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    log -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    log -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
