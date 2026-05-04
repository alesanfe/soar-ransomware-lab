#!/bin/bash

# TC-03: Edge Cases Testing
# Tests various edge cases and error scenarios

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

# Test 1: Invalid webhook URL
log "=== Test 1: Invalid webhook URL ==="
python3 ../scripts/send_alert.py --webhook-url "http://invalid-host:9999" --single 2>&1 || {
    log "✓ Correctly failed with invalid webhook URL"
}

# Test 2: Missing API token
log "=== Test 2: Missing API token ==="
SIEM_WEBHOOK_TOKEN="" python3 ../scripts/send_alert.py --single 2>&1 || {
    log "✓ Correctly failed with missing API token"
}

# Test 3: Invalid alert type
log "=== Test 3: Invalid alert type ==="
python3 ../scripts/send_alert.py --type "invalid_type" --single 2>&1 || {
    log "✓ Correctly failed with invalid alert type"
}

# Test 4: Zero alerts in batch
log "=== Test 4: Zero alerts in batch ==="
python3 ../scripts/send_alert.py --num-alerts 0 --single 2>&1 || {
    log "✓ Correctly failed with zero alerts"
}

# Test 5: Negative delay
log "=== Test 5: Negative delay ==="
python3 ../scripts/send_alert.py --num-alerts 1 --delay -5 2>&1 || {
    log "✓ Correctly failed with negative delay"
}

# Test 6: Very large number of alerts
log "=== Test 6: Large number of alerts (stress test) ==="
python3 ../scripts/send_alert.py --num-alerts 50 --delay 0.1 --type benign
log "✓ Handled 50 alerts successfully"

# Test 7: Containment script with invalid hostname
log "=== Test 7: Containment with invalid hostname ==="
bash ../scripts/isolate_host.sh "invalid@hostname" "CASE-999" 2>&1 || {
    log "✓ Correctly rejected invalid hostname"
}

# Test 8: Containment script with missing parameters
log "=== Test 8: Containment with missing parameters ==="
bash ../scripts/isolate_host.sh 2>&1 || {
    log "✓ Correctly rejected missing parameters"
}

# Test 9: KPI calculation with empty log
log "=== Test 9: KPI calculation with empty log ==="
mkdir -p ../../logs
echo "" > ../../logs/notify.log
python3 ../scripts/calc_kpis.py 2>&1 || {
    log "✓ Correctly handled empty log file"
}

# Test 10: KPI calculation with malformed log
log "=== Test 10: KPI calculation with malformed log ==="
echo "Invalid log entry without timestamp" > ../../logs/notify.log
echo "Another invalid entry" >> ../../logs/notify.log
python3 ../scripts/calc_kpis.py 2>&1 || {
    log "✓ Correctly handled malformed log"
}

log "=== TC-03: Edge Cases Testing Completed ==="
