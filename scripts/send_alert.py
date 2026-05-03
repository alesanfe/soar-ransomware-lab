
#!/usr/bin/env python3
"""
SOAR Ransomware Lab - SIEM Simulator
Sends simulated ransomware alerts to Shuffle webhook
"""

import json
import time
import argparse
import random
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path

class SIEMSimulator:
    def __init__(self, webhook_url, api_token):
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        
        # Sample data for realistic simulation
        self.malicious_hashes = [
            '44d88612fea8a8f36de82e1278abb02f',  # EICAR test
            'd41d8cd98f00b204e9800998ecf8427e',  # Empty file
            '098f6bcd4621d373cade4e832627b4f6',  # test
            '5d41402abc4b2a76b9719d911017c592'   # hello
        ]
        
        self.benign_hashes = [
            'e3b0c44298fc1c149afbf4c8996fb924',  # Common system file
            'a665a45920422f9d417e4867efdc4fb8',  # Another benign
            '7c222fb2927d828af22f592134e89324'   # Config file
        ]
        
        self.sample_ips = [
            '192.168.1.100', '10.0.0.50', '172.16.0.25',
            '192.168.2.75', '10.1.1.200', '172.20.0.10'
        ]
        
        self.sample_hostnames = [
            'WIN-001', 'WIN-002', 'WIN-003', 
            'SRV-001', 'LAPTOP-001', 'DC-001'
        ]
        
        self.malicious_ips = [
            '185.220.101.182',  # Known malicious
            '198.54.131.67',    # Suspicious
            '94.102.52.10'      # C2 server
        ]

    def generate_alert(self, alert_type='malicious'):
        """Generate a realistic ransomware alert"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if alert_type == 'malicious':
            hash_value = random.choice(self.malicious_hashes)
            src_ip = random.choice(self.malicious_ips)
            severity = random.choice([2, 3])  # High/Critical
            source = 'siem-ransomware-detection'
        else:
            hash_value = random.choice(self.benign_hashes)
            src_ip = random.choice(self.sample_ips)
            severity = random.choice([0, 1])  # Low/Medium
            source = 'siem-file-monitoring'
        
        alert = {
            'alert_id': f'ALERT-{int(time.time())}-{random.randint(1000, 9999)}',
            'hostname': random.choice(self.sample_hostnames),
            'src_ip': src_ip,
            'hash': hash_value,
            'severity': severity,
            'source': source,
            'detection_time': timestamp,
            'event_type': 'ransomware_detection',
            'description': f'Ransomware activity detected on {random.choice(self.sample_hostnames)}',
            'affected_files': [
                'C:\\Users\\Documents\\important.docx',
                'C:\\Data\\financial.xlsx',
                'C:\\Backup\\database.sql'
            ] if alert_type == 'malicious' else [],
            'mitre_tactics': ['TA0040'] if alert_type == 'malicious' else [],
            'mitre_techniques': ['T1486'] if alert_type == 'malicious' else []
        }
        
        return alert

    def send_alert(self, alert):
        """Send alert to Shuffle webhook"""
        try:
            print(f"[{datetime.now().isoformat()}] Sending alert {alert['alert_id']} to {self.webhook_url}")
            
            response = requests.post(
                self.webhook_url,
                headers=self.headers,
                json=alert,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"[✓] Alert {alert['alert_id']} sent successfully")
                return True
            else:
                print(f"[✗] Failed to send alert {alert['alert_id']}: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[✗] Network error sending alert {alert['alert_id']}: {e}")
            return False
        except Exception as e:
            print(f"[✗] Unexpected error sending alert {alert['alert_id']}: {e}")
            return False

    def validate_alert(self, alert):
        """Validate alert against JSON schema"""
        required_fields = ['alert_id', 'hostname', 'hash', 'src_ip']
        
        for field in required_fields:
            if field not in alert or not alert[field]:
                print(f"[✗] Validation failed: missing or empty field '{field}'")
                return False
        
        # Basic IP validation
        if not self._is_valid_ip(alert['src_ip']):
            print(f"[✗] Validation failed: invalid IP address '{alert['src_ip']}'")
            return False
        
        # Basic hash validation
        if not self._is_valid_hash(alert['hash']):
            print(f"[✗] Validation failed: invalid hash '{alert['hash']}'")
            return False
        
        print(f"[✓] Alert {alert['alert_id']} validation passed")
        return True

    def _is_valid_ip(self, ip):
        """Basic IP validation"""
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except:
            return False

    def _is_valid_hash(self, hash_value):
        """Basic hash validation"""
        return len(hash_value) in [32, 40, 64] and all(c in '0123456789abcdefABCDEF' for c in hash_value)

    def run_simulation(self, num_alerts=3, delay=5, alert_type='malicious'):
        """Run simulation with specified number of alerts"""
        print(f"Starting SIEM simulation: {num_alerts} {alert_type} alerts with {delay}s delay")
        
        success_count = 0
        for i in range(num_alerts):
            print(f"\n--- Alert {i+1}/{num_alerts} ---")
            
            alert = self.generate_alert(alert_type)
            
            if self.validate_alert(alert):
                if self.send_alert(alert):
                    success_count += 1
            
            if i < num_alerts - 1:  # Don't delay after last alert
                print(f"Waiting {delay} seconds before next alert...")
                time.sleep(delay)
        
        print(f"\n=== Simulation Complete ===")
        print(f"Successfully sent: {success_count}/{num_alerts} alerts")
        return success_count == num_alerts

def main():
    parser = argparse.ArgumentParser(description='SOAR SIEM Simulator')
    parser.add_argument('--webhook-url', 
                       default='http://localhost:5001/webhook',
                       help='Shuffle webhook URL')
    parser.add_argument('--api-token',
                       default='siem-webhook-token-change-this',
                       help='Authentication token')
    parser.add_argument('--num-alerts', type=int, default=3,
                       help='Number of alerts to send')
    parser.add_argument('--delay', type=int, default=5,
                       help='Delay between alerts (seconds)')
    parser.add_argument('--type', choices=['malicious', 'benign'], default='malicious',
                       help='Type of alerts to generate')
    parser.add_argument('--single', action='store_true',
                       help='Send single alert and exit')
    
    args = parser.parse_args()
    
    # Load configuration from environment if available
    webhook_url = os.getenv('SHUFFLE_WEBHOOK_URL', args.webhook_url)
    api_token = os.getenv('SIEM_WEBHOOK_TOKEN', args.api_token)
    
    simulator = SIEMSimulator(webhook_url, api_token)
    
    if args.single:
        alert = simulator.generate_alert(args.type)
        if simulator.validate_alert(alert):
            simulator.send_alert(alert)
    else:
        success = simulator.run_simulation(args.num_alerts, args.delay, args.type)
        exit(0 if success else 1)

if __name__ == '__main__':
    import os
    main()
