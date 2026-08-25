import json
import logging

import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)

webhook_url = "http://localhost:15001/api/v1/hooks/webhook_173215fb-a272-5f47-a982-0fe2933e965c"
alert_data = {
    "ioc": "10.0.0.5",
    "severity": "2",
    "type": "ransomware",
    "description": "Test webhook verification",
    "detection_time": "2026-07-16T09:00:00Z",
}

logger.info(f"Testing webhook: {webhook_url}")
logger.info(f"Payload: {json.dumps(alert_data, indent=2)}")

try:
    response = requests.post(webhook_url, json=alert_data, timeout=30, verify=False)
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Response: {response.text[:500]}")

    if response.status_code == 200:
        logger.info("PASS: Webhook test PASSED - HTTP 200 received")
    else:
        logger.error(f"FAIL: Webhook test FAILED - Expected 200, got {response.status_code}")
except Exception as e:
    logger.error(f"Webhook test ERROR: {e}")
