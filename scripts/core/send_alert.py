#!/usr/bin/env python3
"""
Core alert sending script for SOAR Ransomware Lab
This script handles sending alerts to various security systems
"""

import sys
import json
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from soar_lab.services.send_alert import send_alert_to_thehive, send_alert_to_cortex


def main():
    """Main function to send alerts"""
    parser = argparse.ArgumentParser(description="Send security alerts")
    parser.add_argument("--alert-file", required=True, help="Path to alert JSON file")
    parser.add_argument("--target", choices=["thehive", "cortex", "all"], default="all", 
                       help="Target system for alert")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without sending")
    
    args = parser.parse_args()
    
    try:
        # Load alert data
        with open(args.alert_file, 'r') as f:
            alert_data = json.load(f)
        
        print(f"Processing alert: {alert_data.get('alert_id', 'unknown')}")
        
        if args.dry_run:
            print("DRY RUN - Would send alert to:", args.target)
            print("Alert data:", json.dumps(alert_data, indent=2))
            return 0
        
        # Send alert based on target
        success = False
        if args.target in ["thehive", "all"]:
            try:
                result = send_alert_to_thehive(alert_data)
                if result:
                    print("✓ Alert sent to TheHive successfully")
                    success = True
                else:
                    print("✗ Failed to send alert to TheHive")
            except Exception as e:
                print(f"✗ Error sending to TheHive: {e}")
        
        if args.target in ["cortex", "all"]:
            try:
                result = send_alert_to_cortex(alert_data)
                if result:
                    print("✓ Alert sent to Cortex successfully")
                    success = True
                else:
                    print("✗ Failed to send alert to Cortex")
            except Exception as e:
                print(f"✗ Error sending to Cortex: {e}")
        
        return 0 if success else 1
        
    except FileNotFoundError:
        print(f"✗ Alert file not found: {args.alert_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in alert file: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
