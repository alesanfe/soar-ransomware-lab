#!/bin/bash

# TC-04: Performance Testing
# Tests system performance under load

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

# Test 1: Single alert latency
log "=== Test 1: Single alert latency ==="
START=$(date +%s%N)
python3 -m soar_lab.infrastructure.messaging.send_alert --type malicious --single
END=$(date +%s%N)
LATENCY=$(( (END - START) / 1000000 ))
log "Single alert latency: ${LATENCY}ms"
if [ $LATENCY -lt 5000 ]; then
    log "✓ Single alert latency acceptable (< 5s)"
else
    warn "Single alert latency high: ${LATENCY}ms"
fi

# Test 2: Concurrent alerts
log "=== Test 2: Concurrent alerts (10 in parallel) ==="
START=$(date +%s%N)
for i in {1..10}; do
    python3 -m soar_lab.infrastructure.messaging.send_alert --type malicious --single &
done
wait
END=$(date +%s%N)
TOTAL_TIME=$(( (END - START) / 1000000 ))
log "10 concurrent alerts completed in ${TOTAL_TIME}ms"
AVG_LATENCY=$(( TOTAL_TIME / 10 ))
log "Average latency per alert: ${AVG_LATENCY}ms"

# Test 3: Sequential batch
log "=== Test 3: Sequential batch (20 alerts) ==="
START=$(date +%s%N)
python3 -m soar_lab.infrastructure.messaging.send_alert --type malicious --num-alerts 20 --delay 0.5
END=$(date +%s%N)
TOTAL_TIME=$(( (END - START) / 1000000 ))
log "20 sequential alerts completed in ${TOTAL_TIME}ms"
AVG_LATENCY=$(( TOTAL_TIME / 20 ))
log "Average latency per alert: ${AVG_LATENCY}ms"

# Test 4: Memory usage check
log "=== Test 4: Memory usage check ==="
if command -v docker &> /dev/null; then
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" soar_thehive soar_cortex soar_shuffle_backend
    log "✓ Memory usage captured"
else
    warn "Docker not available for memory check"
fi

# Test 5: CPU usage check
log "=== Test 5: CPU usage check ==="
if command -v docker &> /dev/null; then
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}" soar_thehive soar_cortex soar_shuffle_backend
    log "✓ CPU usage captured"
else
    warn "Docker not available for CPU check"
fi

# Test 6: Disk usage check
log "=== Test 6: Disk usage check ==="
df -h | grep -E "/$|/var" || warn "Disk usage check failed"

# Test 7: KPI calculation performance
log "=== Test 7: KPI calculation performance ==="
# Generate test log with 100 entries
mkdir -p ../../logs
for i in {1..100}; do
    echo "[$(date -d "+$i seconds" '+%Y-%m-%d %H:%M:%S')] STEP: Alert received" >> ../../logs/notify.log
    echo "[$(date -d "+$((i + 90)) seconds" '+%Y-%m-%d %H:%M:%S')] STEP: Containment executed" >> ../../logs/notify.log
done

START=$(date +%s%N)
python3 -m soar_lab.data.calc_kpis
END=$(date +%s%N)
CALC_TIME=$(( (END - START) / 1000000 ))
log "KPI calculation for 100 entries: ${CALC_TIME}ms"
if [ $CALC_TIME -lt 1000 ]; then
    log "✓ KPI calculation performance acceptable (< 1s)"
else
    warn "KPI calculation slow: ${CALC_TIME}ms"
fi

# Clean up test log
rm -f ../../logs/notify.log

log "=== TC-04: Performance Testing Completed ==="
