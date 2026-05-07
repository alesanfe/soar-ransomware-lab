#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Test Runner
Comprehensive test runner for all test suites
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path
import logging
import subprocess
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestRunner:
    """Comprehensive test runner for SOAR lab tests"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = []
        self.start_time = datetime.now(timezone.utc)
        
    def discover_tests(self, test_dir: str, pattern: str = "test_*.py") -> list:
        """Discover test modules in a directory"""
        test_path = self.project_root / "tests" / test_dir
        
        if not test_path.exists():
            logger.warning(f"Test directory not found: {test_path}")
            return []
        
        loader = unittest.TestLoader()
        suite = loader.discover(str(test_path), pattern=pattern)
        
        return suite
    
    def run_test_suite(self, suite_name: str, test_dir: str, pattern: str = "test_*.py") -> dict:
        """Run a test suite and return results"""
        logger.info(f"Running test suite: {suite_name}")
        
        start_time = time.time()
        
        try:
            # Discover tests
            suite = self.discover_tests(test_dir, pattern)
            
            if not suite.countTestCases():
                logger.warning(f"No tests found in {test_dir}")
                return {
                    'suite_name': suite_name,
                    'total_tests': 0,
                    'passed': 0,
                    'failed': 0,
                    'errors': 0,
                    'skipped': 0,
                    'duration': 0,
                    'success': True,
                    'details': 'No tests found'
                }
            
            # Run tests
            runner = unittest.TextTestRunner(
                verbosity=2,
                stream=sys.stdout,
                buffer=True
            )
            
            result = runner.run(suite)
            
            end_time = time.time()
            duration = end_time - start_time
            
            test_result = {
                'suite_name': suite_name,
                'total_tests': result.testsRun,
                'passed': result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                'failed': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'duration': duration,
                'success': result.wasSuccessful(),
                'failures': [{'test': str(f[0]), 'error': f[1]} for f in result.failures],
                'errors': [{'test': str(e[0]), 'error': e[1]} for e in result.errors],
                'skipped': [{'test': str(s[0]), 'reason': s[1]} for s in result.skipped]
            }
            
            logger.info(f"Test suite {suite_name} completed in {duration:.2f}s")
            logger.info(f"Results: {test_result['passed']} passed, {test_result['failed']} failed, {test_result['errors']} errors, {test_result['skipped']} skipped")
            
            return test_result
            
        except Exception as e:
            logger.error(f"Error running test suite {suite_name}: {e}")
            return {
                'suite_name': suite_name,
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'duration': 0,
                'success': False,
                'details': str(e)
            }
    
    def run_e2e_tests(self) -> dict:
        """Run E2E tests"""
        logger.info("Running E2E tests...")
        
        e2e_results = {}
        
        # Run individual E2E test cases
        e2e_cases = ["TC-01", "TC-02", "TC-03"]
        
        for case in e2e_cases:
            case_dir = f"e2e/{case}"
            case_result = self.run_test_suite(f"E2E-{case}", case_dir, "test_*.py")
            e2e_results[case] = case_result
        
        # Calculate overall E2E results
        total_tests = sum(r['total_tests'] for r in e2e_results.values())
        total_passed = sum(r['passed'] for r in e2e_results.values())
        total_failed = sum(r['failed'] for r in e2e_results.values())
        
        # Count errors properly since 'errors' key is replaced by list in successful runs
        total_errors = 0
        for r in e2e_results.values():
            if isinstance(r['errors'], list):
                total_errors += len(r['errors'])
            else:
                total_errors += r['errors']

        # Count skipped properly
        total_skipped = 0
        for r in e2e_results.values():
            if isinstance(r['skipped'], list):
                total_skipped += len(r['skipped'])
            else:
                total_skipped += r['skipped']
        total_duration = sum(r['duration'] for r in e2e_results.values())
        overall_success = all(r['success'] for r in e2e_results.values())
        
        return {
            'suite_name': 'E2E',
            'total_tests': total_tests,
            'passed': total_passed,
            'failed': total_failed,
            'errors': total_errors,
            'skipped': total_skipped,
            'duration': total_duration,
            'success': overall_success,
            'cases': e2e_results
        }
    
    def run_unit_tests(self) -> dict:
        """Run unit tests"""
        logger.info("Running unit tests...")
        return self.run_test_suite("Unit", "unit", "test_*.py")
    
    def run_integration_tests(self) -> dict:
        """Run integration tests"""
        logger.info("Running integration tests...")
        return self.run_test_suite("Integration", "integration", "test_*.py")
    
    def run_performance_tests(self) -> dict:
        """Run performance tests"""
        logger.info("Running performance tests...")
        return self.run_test_suite("Performance", "performance", "test_*.py")
    
    def run_security_tests(self) -> dict:
        """Run security tests"""
        logger.info("Running security tests...")
        return self.run_test_suite("Security", "security", "test_*.py")
    
    def run_all_tests(self, test_types: list = None) -> dict:
        """Run all specified test suites"""
        if test_types is None:
            test_types = ['unit', 'integration', 'performance', 'security', 'e2e']
        
        logger.info(f"Running test suites: {', '.join(test_types)}")
        
        all_results = {}
        
        # Run each test suite
        if 'unit' in test_types:
            all_results['unit'] = self.run_unit_tests()
        
        if 'integration' in test_types:
            all_results['integration'] = self.run_integration_tests()
        
        if 'performance' in test_types:
            all_results['performance'] = self.run_performance_tests()
        
        if 'security' in test_types:
            all_results['security'] = self.run_security_tests()
        
        if 'e2e' in test_types:
            all_results['e2e'] = self.run_e2e_tests()
        
        # Calculate overall results
        total_tests = sum(r['total_tests'] for r in all_results.values())
        total_passed = sum(r['passed'] for r in all_results.values())
        total_failed = sum(r['failed'] for r in all_results.values())
        
        # Count errors properly
        total_errors = 0
        for r in all_results.values():
            if isinstance(r['errors'], list):
                total_errors += len(r['errors'])
            else:
                total_errors += r['errors']

        # Count skipped properly
        total_skipped = 0
        for r in all_results.values():
            if isinstance(r['skipped'], list):
                total_skipped += len(r['skipped'])
            else:
                total_skipped += r['skipped']
        total_duration = sum(r['duration'] for r in all_results.values())
        overall_success = all(r['success'] for r in all_results.values())
        
        overall_results = {
            'run_start': self.start_time.isoformat(),
            'run_end': datetime.now(timezone.utc).isoformat(),
            'total_duration': total_duration,
            'test_suites': test_types,
            'overall': {
                'total_tests': total_tests,
                'passed': total_passed,
                'failed': total_failed,
                'errors': total_errors,
                'skipped': total_skipped,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
                'success': overall_success
            },
            'suites': all_results,
            'summary': self.generate_summary(all_results)
        }
        
        return overall_results
    
    def generate_summary(self, results: dict) -> dict:
        """Generate test summary"""
        summary = {
            'critical_failures': [],
            'recommendations': [],
            'coverage_analysis': {},
            'performance_issues': [],
            'security_issues': []
        }
        
        # Analyze failures
        for suite_name, suite_result in results.items():
            if not suite_result['success']:
                summary['critical_failures'].append({
                    'suite': suite_name,
                    'failed_tests': suite_result['failed'],
                    'error_tests': suite_result['errors'],
                    'total_impact': suite_result['total_tests']
                })
        
        # Generate recommendations
        if results.get('unit', {}).get('success') is False:
            summary['recommendations'].append("Unit tests failed - review code logic and dependencies")
        
        if results.get('integration', {}).get('success') is False:
            summary['recommendations'].append("Integration tests failed - check service connectivity and configuration")
        
        if results.get('performance', {}).get('success') is False:
            summary['recommendations'].append("Performance tests failed - optimize code and resource usage")
        
        if results.get('security', {}).get('success') is False:
            summary['recommendations'].append("Security tests failed - address security vulnerabilities")
        
        if results.get('e2e', {}).get('success') is False:
            summary['recommendations'].append("E2E tests failed - review complete workflow functionality")
        
        # Analyze performance
        perf_result = results.get('performance', {})
        if perf_result.get('duration', 0) > 300:  # 5 minutes
            summary['performance_issues'].append("Performance tests taking too long - consider optimization")
        
        # Analyze security
        sec_result = results.get('security', {})
        if sec_result.get('failed', 0) > 0:
            summary['security_issues'].append(f"Security issues detected: {sec_result['failed']} failures")
        
        return summary
    
    def save_results(self, results: dict, output_file: str = None):
        """Save test results to file"""
        if output_file is None:
            timestamp = int(self.start_time.timestamp())
            output_file = self.project_root / "results" / f"test_results_{timestamp}.json"
        
        # Ensure results directory exists
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {output_file}")
        return output_file
    
    def generate_report(self, results: dict) -> str:
        """Generate human-readable test report"""
        report_lines = [
            "SOAR Ransomware Lab - Test Report",
            "=" * 50,
            f"Run Start: {results['run_start']}",
            f"Run End: {results['run_end']}",
            f"Total Duration: {results['total_duration']:.2f} seconds",
            "",
            "Overall Results:",
            f"  Total Tests: {results['overall']['total_tests']}",
            f"  Passed: {results['overall']['passed']}",
            f"  Failed: {results['overall']['failed']}",
            f"  Errors: {results['overall']['errors']}",
            f"  Skipped: {results['overall']['skipped']}",
            f"  Success Rate: {results['overall']['success_rate']:.1f}%",
            f"  Overall Success: {'✓' if results['overall']['success'] else '✗'}",
            ""
        ]
        
        # Add suite details
        for suite_name, suite_result in results['suites'].items():
            status = '✓' if suite_result['success'] else '✗'
            report_lines.extend([
                f"{suite_name.upper()} Tests: {status}",
                f"  Total: {suite_result['total_tests']}",
                f"  Passed: {suite_result['passed']}",
                f"  Failed: {suite_result['failed']}",
                f"  Errors: {suite_result['errors']}",
                f"  Duration: {suite_result['duration']:.2f}s",
                ""
            ])
        
        # Add summary
        summary = results.get('summary', {})
        if summary.get('critical_failures'):
            report_lines.append("Critical Failures:")
            for failure in summary['critical_failures']:
                report_lines.append(f"  - {failure['suite']}: {failure['failed_tests']} failed, {failure['error_tests']} errors")
            report_lines.append("")
        
        if summary.get('recommendations'):
            report_lines.append("Recommendations:")
            for rec in summary['recommendations']:
                report_lines.append(f"  - {rec}")
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Main test runner execution"""
    parser = argparse.ArgumentParser(description="SOAR Ransomware Lab Test Runner")
    parser.add_argument(
        '--test-types',
        nargs='+',
        choices=['unit', 'integration', 'performance', 'security', 'e2e'],
        default=['unit', 'integration', 'performance', 'security', 'e2e'],
        help='Test types to run'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for test results'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate human-readable report'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create test runner
    runner = TestRunner()
    
    # Run tests
    logger.info("Starting SOAR Ransomware Lab test execution...")
    results = runner.run_all_tests(args.test_types)
    
    # Save results
    results_file = runner.save_results(results, args.output)
    
    # Generate report if requested
    if args.report:
        report = runner.generate_report(results)
        report_file = results_file.parent / f"test_report_{results_file.stem.split('_')[-1]}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"Test report saved to: {report_file}")
        print("\n" + report)
    
    # Print summary
    print(f"\nTest execution completed!")
    print(f"Overall Success: {'✓' if results['overall']['success'] else '✗'}")
    print(f"Success Rate: {results['overall']['success_rate']:.1f}%")
    print(f"Results saved to: {results_file}")
    
    # Exit with appropriate code
    exit_code = 0 if results['overall']['success'] else 1
    sys.exit(exit_code)


if __name__ == '__main__':
    main()


class TestRunAllTests(unittest.TestCase):
    """Test the run_all_tests.py functionality"""
    
    def test_test_runner_initialization(self):
        """Test TestRunner initialization"""
        runner = TestRunner()
        self.assertIsNotNone(runner.project_root)
        self.assertEqual(runner.test_results, [])
        self.assertIsNotNone(runner.start_time)
    
    def test_discover_tests_existing_directory(self):
        """Test test discovery in existing directory"""
        runner = TestRunner()
        suite = runner.discover_tests("unit")
        self.assertIsNotNone(suite)
        # Should find tests in unit directory
        self.assertGreater(suite.countTestCases(), 0)
    
    def test_discover_tests_nonexistent_directory(self):
        """Test test discovery in non-existent directory"""
        runner = TestRunner()
        suite = runner.discover_tests("nonexistent")
        self.assertEqual(suite, [])
    
    def test_discover_tests_with_pattern(self):
        """Test test discovery with custom pattern"""
        runner = TestRunner()
        suite = runner.discover_tests("unit", "test_*.py")
        self.assertIsNotNone(suite)
        self.assertGreater(suite.countTestCases(), 0)
    
    def test_run_test_suite_integration(self):
        """Integration test for running test suites"""
        runner = TestRunner()
        # Run a simple test suite integration
        suite = runner.discover_tests("unit")
        self.assertIsNotNone(suite)
        # Test that we can count tests without running them
        test_count = suite.countTestCases()
        self.assertGreater(test_count, 0)
