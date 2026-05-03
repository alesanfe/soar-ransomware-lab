#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 02 (Benign)
Tests the SOAR workflow with a benign file alert (false positive scenario)
"""

import json
import time
import requests
import subprocess
from datetime import datetime, timezone
from pathlib import Path

class BenignTestCase:
    def __init__(self):
        self.test_start_time = datetime.now(timezone.utc)
        self.results_dir = Path("../results")
        self.logs_dir = Path("../logs")
        self.payload_file = Path("../payloads/payload_case2.json")
        
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
        """Load benign alert payload"""
        try:
            with open(self.payload_file, 'r') as f:
                payload = json.load(f)
            self.log(f"Loaded benign payload: {payload['alert_id']}")
            return payload
        except Exception as e:
            self.log(f"ERROR: Failed to load payload: {e}")
            return None
    
    def send_alert(self, payload):
        """Send alert to Shuffle webhook"""
        self.log("STEP: Sending benign alert to Shuffle")
        
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
                self.log("✓ Benign alert sent successfully to Shuffle")
                return True
            else:
                self.log(f"✗ Failed to send benign alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"✗ Network error sending benign alert: {e}")
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
                        if 'benign' in case.get('title', '').lower() or payload['alert_id'] in case.get('description', ''):
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
    
    def verify_no_containment(self, case_id, max_wait=120):
        """Verify that no containment actions were executed"""
        self.log("STEP: Verifying no containment actions were executed")
        
        # Check if containment script was NOT executed
        containment_log = self.logs_dir / "containment.log"
        if containment_log.exists():
            with open(containment_log, 'r') as f:
                log_content = f.read()
                if "Containment executed" in log_content:
                    self.log("✗ WARNING: Containment was executed for benign case")
                    return False
                else:
                    self.log("✓ Containment correctly NOT executed for benign case")
                    return True
        
        self.log("✓ Containment log not found (good for benign case)")
        return True
    
    def verify_case_status(self, case_id, max_wait=60):
        """Verify case was marked as benign/observe"""
        self.log("STEP: Verifying case status")
        
        try:
            response = requests.get(
                f"{self.thehive_api}/case/{case_id}",
                headers={'Authorization': f'Bearer {self.thehive_key}'},
                timeout=10
            )
            
            if response.status_code == 200:
                case = response.json()
                status = case.get('status', '')
                
                if status in ['Open', 'Resolved', 'FalsePositive']:
                    self.log(f"✓ Case status appropriate: {status}")
                    return True
                else:
                    self.log(f"✗ Unexpected case status: {status}")
                    return False
            
        except Exception as e:
            self.log(f"Warning: Error checking case status: {e}")
        
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
            "test_case": "TC-02-Benign",
            "test_start": self.test_start_time.isoformat(),
            "test_end": datetime.now(timezone.utc).isoformat(),
            "payload": "payload_case2.json",
            "results": results,
            "success": all(results.values()),
            "mttr_metrics": self.extract_kpis(),
            "recommendations": self.generate_recommendations(results)
        }
        
        report_file = self.results_dir / "TC-02_benign_report.json"
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
        
        if not results.get('notifications_sent', False):
            recommendations.append("Check notification system configuration")
        
        if results.get('containment_executed', False):
            recommendations.append("✓ GOOD: Containment correctly avoided for benign case")
        else:
            recommendations.append("⚠️ WARNING: Containment executed for benign case - review decision logic")
        
        return recommendations
    
    def run_test(self):
        """Execute complete benign test case"""
        self.log("=== STARTING BENIGN TEST CASE TC-02 ===")
        
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
                
                # Step 4: Verify NO containment was executed
                results['containment_executed'] = self.verify_no_containment(case_id)
                
                # Step 5: Verify case status
                results['case_status_verified'] = self.verify_case_status(case_id)
                
                # Step 6: Verify notifications
                results['notifications_sent'] = self.verify_notifications()
        
        # Step 7: Calculate MTTR
        results['mttr_calculated'] = self.calculate_mttr()
        
        # Step 8: Generate report
        report_file = self.generate_test_report(results)
        
        # Summary
        self.log("=== TEST CASE TC-02 COMPLETED ===")
        self.log(f"Overall Success: {all(results.values())}")
        self.log(f"Report saved to: {report_file}")
        
        return all(results.values())

def main():
    """Main test execution"""
    test = BenignTestCase()
    success = test.run_test()
    
    if success:
        print("\n✓ Benign test case TC-02 completed successfully")
        exit(0)
    else:
        print("\n✗ Benign test case TC-02 failed")
        exit(1)

if __name__ == '__main__':
    main()
