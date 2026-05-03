#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 01 (Malicious)
Tests the complete SOAR workflow with a malicious ransomware alert
"""

import json
import time
import requests
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class MaliciousTestCase:
    def __init__(self):
        self.test_start_time = datetime.now(timezone.utc)
        self.results_dir = Path("../results")
        self.logs_dir = Path("../logs")
        self.payload_file = Path("../payloads/payload_case1.json")
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Test configuration
        self.shuffle_webhook = "http://localhost:5001/webhook"
        self.thehive_api = "http://localhost:9000/api"
        self.cortex_api = "http://localhost:9001/api"
        self.webhook_token = "siem-webhook-token-change-this"
        self.thehive_key = "change-this-api-key-in-production"
        self.cortex_key = "change-this-api-key-in-production"
        
    def log(self, message):
        """Log test progress"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        
        # Also log to notify.log for KPI calculation
        with open(self.logs_dir / "notify.log", "a") as f:
            f.write(f"{log_entry}\n")
    
    def load_payload(self):
        """Load the malicious alert payload"""
        try:
            with open(self.payload_file, 'r') as f:
                payload = json.load(f)
            self.log(f"Loaded malicious payload: {payload['alert_id']}")
            return payload
        except Exception as e:
            self.log(f"ERROR: Failed to load payload: {e}")
            return None
    
    def send_alert(self, payload):
        """Send alert to Shuffle webhook"""
        self.log("STEP: Sending malicious alert to Shuffle")
        
        headers = {
            'Authorization': f'Bearer {self.webhook_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                self.shuffle_webhook,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log("✓ Alert sent successfully to Shuffle")
                return True
            else:
                self.log(f"✗ Failed to send alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"✗ Network error sending alert: {e}")
            return False
    
    def wait_for_case_creation(self, max_wait=120):
        """Wait for case to be created in TheHive"""
        self.log("STEP: Waiting for case creation in TheHive")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.thehive_api}/case",
                    headers={'Authorization': f'Bearer {self.thehive_key}'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    cases = response.json()
                    # Look for recent case with our alert ID
                    for case in cases:
                        if 'ransomware' in case.get('title', '').lower():
                            self.log(f"✓ Found case in TheHive: {case.get('id')}")
                            return case.get('id')
                
                time.sleep(5)
                
            except Exception as e:
                self.log(f"Warning: Error checking cases: {e}")
                time.sleep(5)
        
        self.log("✗ Timeout waiting for case creation")
        return None
    
    def check_analyzer_execution(self, case_id, max_wait=180):
        """Wait for Cortex analyzers to complete"""
        self.log("STEP: Waiting for Cortex analyzer execution")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.thehive_api}/case/{case_id}/observable",
                    headers={'Authorization': f'Bearer {self.thehive_key}'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    observables = response.json()
                    for obs in observables:
                        if obs.get('dataType') == 'hash':
                            # Check if analyzer report exists
                            if obs.get('reports'):
                                self.log("✓ Analyzer reports found in TheHive")
                                return True
                
                time.sleep(10)
                
            except Exception as e:
                self.log(f"Warning: Error checking observables: {e}")
                time.sleep(10)
        
        self.log("✗ Timeout waiting for analyzer execution")
        return False
    
    def verify_containment(self, case_id, max_wait=120):
        """Verify containment actions were executed"""
        self.log("STEP: Verifying containment actions")
        
        # Check if containment script was executed
        containment_log = self.logs_dir / "containment.log"
        if containment_log.exists():
            with open(containment_log, 'r') as f:
                log_content = f.read()
                if "Containment executed" in log_content:
                    self.log("✓ Containment script executed successfully")
                    return True
        
        self.log("✗ Containment script not found in logs")
        return False
    
    def verify_notifications(self, max_wait=60):
        """Verify notifications were sent"""
        self.log("STEP: Verifying notifications")
        
        notify_log = self.logs_dir / "notify.log"
        if notify_log.exists():
            with open(notify_log, 'r') as f:
                log_content = f.read()
                if "Notification sent" in log_content:
                    self.log("✓ Notifications sent successfully")
                    return True
        
        self.log("✗ Notifications not found in logs")
        return False
    
    def calculate_mttr(self):
        """Calculate Mean Time to Respond (MTTR)"""
        self.log("STEP: Calculating MTTR metrics")
        
        try:
            # Run KPI calculation script
            result = subprocess.run(
                ['python3', '../../scripts/calc_kpis.py'],
                capture_output=True,
                text=True,
                cwd='../../'
            )
            
            if result.returncode == 0:
                self.log("✓ KPI calculation completed")
                self.log(result.stdout)
                return True
            else:
                self.log(f"✗ KPI calculation failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log(f"✗ Error running KPI calculation: {e}")
            return False
    
    def generate_test_report(self, results):
        """Generate comprehensive test report"""
        self.log("STEP: Generating test report")
        
        report = {
            "test_case": "TC-01-Malicious",
            "test_start": self.test_start_time.isoformat(),
            "test_end": datetime.now(timezone.utc).isoformat(),
            "payload": "payload_case1.json",
            "results": results,
            "success": all(results.values()),
            "mttr_metrics": self.extract_kpis(),
            "recommendations": self.generate_recommendations(results)
        }
        
        report_file = self.results_dir / "TC-01_malicious_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.log(f"✓ Test report generated: {report_file}")
        return report_file
    
    def extract_kpis(self):
        """Extract KPIs from results file"""
        kpi_file = self.results_dir / "kpis.csv"
        if kpi_file.exists():
            try:
                with open(kpi_file, 'r') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        headers = lines[0].strip().split(',')
                        values = lines[1].strip().split(',')
                        return dict(zip(headers, values))
            except Exception as e:
                self.log(f"Warning: Could not extract KPIs: {e}")
        return {}
    
    def generate_recommendations(self, results):
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not results.get('alert_sent', False):
            recommendations.append("Check Shuffle webhook configuration and connectivity")
        
        if not results.get('case_created', False):
            recommendations.append("Verify TheHive API integration and permissions")
        
        if not results.get('analyzers_executed', False):
            recommendations.append("Check Cortex configuration and analyzer availability")
        
        if not results.get('containment_executed', False):
            recommendations.append("Verify containment script permissions and execution")
        
        if not results.get('notifications_sent', False):
            recommendations.append("Check notification system configuration")
        
        return recommendations
    
    def run_test(self):
        """Execute the complete malicious test case"""
        self.log("=== STARTING MALICIOUS TEST CASE TC-01 ===")
        
        results = {
            'alert_sent': False,
            'case_created': False,
            'analyzers_executed': False,
            'containment_executed': False,
            'notifications_sent': False,
            'mttr_calculated': False
        }
        
        # Step 1: Load and send alert
        payload = self.load_payload()
        if payload:
            results['alert_sent'] = self.send_alert(payload)
        
        if results['alert_sent']:
            # Step 2: Wait for case creation
            case_id = self.wait_for_case_creation()
            if case_id:
                results['case_created'] = True
                
                # Step 3: Wait for analyzer execution
                results['analyzers_executed'] = self.check_analyzer_execution(case_id)
                
                # Step 4: Verify containment
                results['containment_executed'] = self.verify_containment(case_id)
                
                # Step 5: Verify notifications
                results['notifications_sent'] = self.verify_notifications()
        
        # Step 6: Calculate MTTR
        results['mttr_calculated'] = self.calculate_mttr()
        
        # Step 7: Generate report
        report_file = self.generate_test_report(results)
        
        # Summary
        self.log("=== TEST CASE TC-01 COMPLETED ===")
        self.log(f"Overall Success: {all(results.values())}")
        self.log(f"Report saved to: {report_file}")
        
        return all(results.values())

def main():
    """Main test execution"""
    test = MaliciousTestCase()
    success = test.run_test()
    
    if success:
        print("\n✓ Malicious test case TC-01 completed successfully")
        exit(0)
    else:
        print("\n✗ Malicious test case TC-01 failed")
        exit(1)

if __name__ == '__main__':
    main()
