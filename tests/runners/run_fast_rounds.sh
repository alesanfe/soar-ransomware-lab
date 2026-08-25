#!/bin/sh
set -e

echo "=== Starting FAST round 1 (excluding e2e) at $(date -Iseconds) ==="
python3 -m pytest /app/tests --ignore=/app/tests/e2e -q --tb=short --reruns 1 > /tmp/fast1.log 2>&1
ROUND1=$?
echo "=== Fast round 1 finished at $(date -Iseconds) with exit code $ROUND1 ==="
cat /tmp/fast1.log

if [ $ROUND1 -ne 0 ]; then
    echo "=== Fast round 1 failed; skipping fast round 2 ==="
    exit $ROUND1
fi

echo "=== Starting FAST round 2 (excluding e2e) at $(date -Iseconds) ==="
python3 -m pytest /app/tests --ignore=/app/tests/e2e -q --tb=short --reruns 1 > /tmp/fast2.log 2>&1
ROUND2=$?
echo "=== Fast round 2 finished at $(date -Iseconds) with exit code $ROUND2 ==="
cat /tmp/fast2.log

if [ $ROUND2 -ne 0 ]; then
    exit $ROUND2
fi

echo "=== Both fast rounds passed ==="
