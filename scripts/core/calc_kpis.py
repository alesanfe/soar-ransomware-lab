#!/usr/bin/env python3
"""
Core KPI calculation script for SOAR Ransomware Lab
This script calculates key performance indicators from test results
"""

import sys
import json
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from soar_lab.data.calc_kpis import calculate_metrics, calculate_mttr


def main():
    """Main function to calculate KPIs"""
    parser = argparse.ArgumentParser(description="Calculate KPIs from test results")
    parser.add_argument("--results-file", required=True, help="Path to test results JSON file")
    parser.add_argument("--output", help="Output file for KPI results")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    try:
        # Load test results
        with open(args.results_file, 'r') as f:
            test_results = json.load(f)
        
        print(f"Calculating KPIs from: {args.results_file}")
        
        # Calculate metrics
        metrics = calculate_metrics(test_results)
        mttr = calculate_mttr(test_results)
        
        # Combine results
        kpi_results = {
            "metrics": metrics,
            "mttr": mttr,
            "summary": {
                "total_tests": len(test_results.get("tests", [])),
                "passed_tests": len([t for t in test_results.get("tests", []) if t.get("status") == "passed"]),
                "failed_tests": len([t for t in test_results.get("tests", []) if t.get("status") == "failed"]),
                "average_execution_time": metrics.get("mean", 0),
                "mttr_minutes": mttr.get("mttr_minutes", 0)
            }
        }
        
        # Output results
        if args.format == "json":
            output = json.dumps(kpi_results, indent=2)
        else:
            output = f"""
KPI Results Summary
==================
Total Tests: {kpi_results['summary']['total_tests']}
Passed Tests: {kpi_results['summary']['passed_tests']}
Failed Tests: {kpi_results['summary']['failed_tests']}
Average Execution Time: {kpi_results['summary']['average_execution_time']:.2f}s
MTTR: {kpi_results['summary']['mttr_minutes']:.2f} minutes

Detailed Metrics:
{json.dumps(kpi_results['metrics'], indent=2)}
"""
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"KPI results saved to: {args.output}")
        else:
            print(output)
        
        return 0
        
    except FileNotFoundError:
        print(f"✗ Results file not found: {args.results_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in results file: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
