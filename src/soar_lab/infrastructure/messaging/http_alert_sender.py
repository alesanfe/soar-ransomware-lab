#!/usr/bin/env python3
"""
SOAR Ransomware Lab - HTTP Alert Sender (messaging re-export shim).
Canonical implementation now lives in soar_lab.infrastructure.http_alert_sender.
"""

from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender, AlertSendResult

__all__ = ["HTTPAlertSender", "AlertSendResult"]
