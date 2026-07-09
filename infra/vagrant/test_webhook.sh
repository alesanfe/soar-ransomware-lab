#!/bin/bash
# Probar el webhook de Shuffle directamente
curl -s -X POST http://soar_shuffle_backend:5001/api/v1/hooks/webhook_a1d9d3cc-b27a-504c-be2c-8bee750ed5f8 \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "TEST-001",
    "alert_type": "ransomware",
    "hostname": "WIN-TEST-001",
    "src_ip": "172.31.54.117",
    "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
    "severity": 3,
    "source": "siem-ransomware-detection",
    "detection_time": "2026-06-15T21:00:00Z",
    "event_type": "ransomware_detection",
    "mitre_tactics": ["TA0040"],
    "mitre_techniques": ["T1486"]
  }'
