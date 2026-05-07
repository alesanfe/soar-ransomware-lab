#!/bin/bash

# SOAR Ransomware Lab - Notification Script
# Sends notifications to security team and updates TheHive case
# This script handles email, Slack, and TheHive updates.

set -euo pipefail
set -u

# Configuration
LOG_FILE="${LOG_FILE:-./logs/notify.log}"
THEHIVE_URL="${THEHIVE_URL:-http://localhost:9000}"
THEHIVE_API_KEY="${THEHIVE_API_KEY:-change-this-api-key}"
SMTP_SERVER="${SMTP_SERVER:-localhost:25}"
SMTP_FROM="${SMTP_FROM:-soar-lab@example.com}"
SMTP_TO="${SMTP_TO:-security-team@example.com}"
SIMULATION_MODE="${SIMULATION_MODE:-true}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to send email notification
send_email() {
    local subject="$1"
    local message="$2"
    local case_id="$3"
    
    log "EMAIL NOTIFICATION - Case: $case_id, Subject: $subject"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Sending email notification"
        log "[SIMULATION] From: $SMTP_FROM"
        log "[SIMULATION] To: $SMTP_TO"
        log "[SIMULATION] SMTP Server: $SMTP_SERVER"
        log "[SIMULATION] Subject: $subject"
        log "[SIMULATION] Message: $message"
        log "[SIMULATION] Email notification sent successfully"
    else
        # Real email sending command
        echo -e "Subject: $subject\n\n$message" | \
        sendmail -f "$SMTP_FROM" "$SMTP_TO" 2>/dev/null || \
        mail -s "$subject" "$SMTP_TO" <<< "$message" 2>/dev/null || \
        log "WARNING: Email sending failed - no mail command available"
    fi
}

# Function to update TheHive case
update_thehive_case() {
    local case_id="$1"
    local status="$2"
    local message="$3"
    
    log "THEHIVE UPDATE - Case: $case_id, Status: $status"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Updating TheHive case $case_id"
        log "[SIMULATION] PATCH /api/case/$case_id"
        log "[SIMULATION] Status: $status"
        log "[SIMULATION] Message: $message"
        log "[SIMULATION] TheHive case updated successfully"
    else
        # Real TheHive API call
        curl -X PATCH "$THEHIVE_URL/api/case/$case_id" \
             -H "Authorization: Bearer $THEHIVE_API_KEY" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"summary\": \"$message\"}" \
             2>/dev/null || log "WARNING: TheHive update failed"
    fi
}

# Function to send Slack notification (if configured)
send_slack() {
    local message="$1"
    local case_id="$2"
    local webhook_url="${SLACK_WEBHOOK_URL:-}"
    
    if [ -z "$webhook_url" ]; then
        log "Slack webhook not configured, skipping"
        return 0
    fi
    
    log "SLACK NOTIFICATION - Case: $case_id"
    
    if [ "$SIMULATION_MODE" = "true" ]; then
        log "[SIMULATION] Sending Slack notification"
        log "[SIMULATION] Webhook: $webhook_url"
        log "[SIMULATION] Message: $message"
        log "[SIMULATION] Slack notification sent successfully"
    else
        # Real Slack API call
        curl -X POST "$webhook_url" \
             -H "Content-Type: application/json" \
             -d "{\"text\": \"$message\"}" \
             2>/dev/null || log "WARNING: Slack notification failed"
    fi
}

# Function to generate notification message
generate_message() {
    local case_id="$1"
    local hostname="$2"
    local status="$3"
    local action="$4"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    
    cat << EOF
🚨 SOAR RANSOMWARE LAB NOTIFICATION 🚨

Case ID: $case_id
Hostname: $hostname
Status: $status
Action: $action
Timestamp: $timestamp

Details:
- Automated response has been executed
- Containment procedures have been completed
- Forensic evidence has been collected
- Case has been updated in TheHive

Next Steps:
1. Review containment report
2. Analyze forensic evidence
3. Plan recovery procedures
4. Update security policies

System Status: All automated systems functioning normally
EOF
}

# Function to send containment notification
send_containment_notification() {
    local case_id="$1"
    local hostname="$2"
    local status="$3"
    
    log "=== SENDING CONTAINMENT NOTIFICATION ==="
    log "Case ID: $case_id"
    log "Hostname: $hostname"
    log "Status: $status"
    
    # Generate notification message
    message=$(generate_message "$case_id" "$hostname" "$status" "Containment Completed")
    
    # Send notifications
    send_email "🚨 Ransomware Containment - Case $case_id" "$message" "$case_id"
    update_thehive_case "$case_id" "$status" "Automated containment completed successfully"
    send_slack "🚨 Ransomware containment completed for case $case_id on $hostname" "$case_id"
    
    log "=== NOTIFICATION PROCEDURE COMPLETED ==="
}

# Function to send alert notification
send_alert_notification() {
    local case_id="$1"
    local hostname="$2"
    local severity="$3"
    
    log "=== SENDING ALERT NOTIFICATION ==="
    log "Case ID: $case_id"
    log "Hostname: $hostname"
    log "Severity: $severity"
    
    # Generate alert message
    message=$(generate_message "$case_id" "$hostname" "Alert Received" "New Ransomware Alert")
    
    # Send notifications
    send_email "🚨 New Ransomware Alert - Case $case_id" "$message" "$case_id"
    send_slack "🚨 New ransomware alert detected for case $case_id on $hostname" "$case_id"
    
    log "=== ALERT NOTIFICATION COMPLETED ==="
}

# Function to send error notification
send_error_notification() {
    local case_id="$1"
    local hostname="$2"
    local error="$3"
    
    log "=== SENDING ERROR NOTIFICATION ==="
    log "Case ID: $case_id"
    log "Hostname: $hostname"
    log "Error: $error"
    
    # Generate error message
    message="🚨 SOAR SYSTEM ERROR

Case ID: $case_id
Hostname: $hostname
Error: $error
Timestamp: $(date '+%Y-%m-%d %H:%M:%S')

Immediate action required:
1. Check system logs
2. Verify service status
3. Manual intervention may be needed"
    
    # Send error notifications
    send_email "❌ SOAR System Error - Case $case_id" "$message" "$case_id"
    send_slack "❌ SOAR system error for case $case_id: $error" "$case_id"
    
    log "=== ERROR NOTIFICATION COMPLETED ==="
}

# Function to show usage
usage() {
    echo "Usage: $0 <action> <case_id> <hostname> [status] [error]"
    echo ""
    echo "Actions:"
    echo "  alert       Send initial alert notification"
    echo "  containment Send containment completion notification"
    echo "  error       Send error notification"
    echo ""
    echo "Parameters:"
    echo "  action      Notification type (alert/containment/error)"
    echo "  case_id     Case identifier"
    echo "  hostname    Target hostname"
    echo "  status      Case status (for containment)"
    echo "  error       Error message (for error notifications)"
    echo ""
    echo "Environment variables:"
    echo "  THEHIVE_URL         TheHive API URL"
    echo "  THEHIVE_API_KEY     TheHive API key"
    echo "  SMTP_SERVER         SMTP server address"
    echo "  SMTP_FROM           From email address"
    echo "  SMTP_TO             To email address"
    echo "  SLACK_WEBHOOK_URL   Slack webhook URL"
    echo "  SIMULATION_MODE     true (default) or false"
    echo ""
    echo "Examples:"
    echo "  $0 alert CASE-12345 WIN-001"
    echo "  $0 containment CASE-12345 WIN-001 Contained"
    echo "  $0 error CASE-12345 WIN-001 \"Analyzer timeout\""
}

# Parse command line arguments
if [ $# -lt 3 ]; then
    usage
    exit 1
fi

ACTION="$1"
CASE_ID="$2"
HOSTNAME="$3"
STATUS="${4:-}"
ERROR="${5:-}"

# Execute appropriate notification function
case "$ACTION" in
    "alert")
        send_alert_notification "$CASE_ID" "$HOSTNAME"
        ;;
    "containment")
        if [ -z "$STATUS" ]; then
            log "ERROR: Status parameter required for containment notifications"
            exit 1
        fi
        send_containment_notification "$CASE_ID" "$HOSTNAME" "$STATUS"
        ;;
    "error")
        if [ -z "$ERROR" ]; then
            log "ERROR: Error message required for error notifications"
            exit 1
        fi
        send_error_notification "$CASE_ID" "$HOSTNAME" "$ERROR"
        ;;
    *)
        log "ERROR: Unknown action '$ACTION'"
        usage
        exit 1
        ;;
esac

# Log notification for KPI calculation
echo "$(date '+%Y-%m-%d %H:%M:%S') STEP: Notification sent" | tee -a logs/notify.log
