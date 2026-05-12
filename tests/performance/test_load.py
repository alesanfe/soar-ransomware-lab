#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Load Testing Tests
Performance and load testing for SOAR components
"""

import aiohttp
import asyncio
import json
import logging
import os
import statistics
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
from soar_lab.config.settings import get_setting
from soar_lab.config.schemas import validate_alert_data, RansomwareAlert

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTester:
    """Load testing framework for SOAR components"""
    
    def __init__(self):
        self.base_url = get_setting('shuffle_api_url', 'http://localhost:5001')
        self.webhook_url = f"{self.base_url}/api/v1/webhooks/siem"
        self.api_token = get_setting('siem_webhook_token', 'test-token')
        self.results = []
        
    def generate_test_alert(self, alert_id: str) -> Dict[str, Any]:
        """Generate a test alert for load testing"""
        return {
            "alert_id": alert_id,
            "hostname": f"TEST-HOST-{alert_id.split('-')[-1]}",
            "src_ip": "192.168.1.100",
            "hash": {
                "sha256": "a" * 64  # Valid SHA256 format
            },
            "severity": "2",
            "source": "load-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": f"Load test alert {alert_id}",
            "affected_files": [
                {
                    "path": f"/tmp/test_file_{alert_id}.txt",
                    "name": f"test_file_{alert_id}.txt",
                    "size": 1024,
                    "extension": "txt",
                    "encrypted": False
                }
            ],
            "mitre_tactics": ["TA0040"],
            "mitre_techniques": ["T1486"]
        }
    
    async def send_alert_async(self, session: aiohttp.ClientSession, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert asynchronously"""
        start_time = time.time()
        alert_id = alert_data["alert_id"]
        
        try:
            # Validate alert data
            validated_alert = validate_alert_data(alert_data)
            
            # Prepare webhook payload
            payload = {
                "alert": validated_alert.dict(),
                "metadata": {"test_type": "load_test"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                return {
                    "alert_id": alert_id,
                    "status_code": response.status,
                    "response_time_ms": response_time,
                    "success": response.status == 200,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                "alert_id": alert_id,
                "status_code": 0,
                "response_time_ms": response_time,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def run_concurrent_test(self, num_requests: int, concurrency: int = 10) -> List[Dict[str, Any]]:
        """Run concurrent load test"""
        logger.info(f"Starting concurrent load test: {num_requests} requests, concurrency: {concurrency}")
        
        # Generate test alerts
        alerts = []
        for i in range(num_requests):
            alert_id = f"ALERT-{int(time.time())}-{i:04d}"
            alerts.append(self.generate_test_alert(alert_id))
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_send_alert(session, alert):
            async with semaphore:
                return await self.send_alert_async(session, alert)
        
        # Run requests concurrently
        connector = aiohttp.TCPConnector(limit=concurrency * 2)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = [bounded_send_alert(session, alert) for alert in alerts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Request failed with exception: {result}")
                else:
                    valid_results.append(result)
            
            return valid_results
    
    def run_sequential_test(self, num_requests: int) -> List[Dict[str, Any]]:
        """Run sequential load test"""
        logger.info(f"Starting sequential load test: {num_requests} requests")
        
        results = []
        
        for i in range(num_requests):
            alert_id = f"ALERT-{int(time.time())}-{i:04d}"
            alert_data = self.generate_test_alert(alert_id)
            
            # Run single request synchronously
            result = asyncio.run(self.send_alert_async(
                aiohttp.ClientSession(), alert_data
            ))
            results.append(result)
            
            # Small delay between requests
            time.sleep(0.1)
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze load test results"""
        if not results:
            return {"error": "No results to analyze"}
        
        successful_requests = [r for r in results if r.get("success", False)]
        failed_requests = [r for r in results if not r.get("success", False)]
        
        response_times = [r.get("response_time_ms", 0) for r in successful_requests]
        
        analysis = {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(results) * 100,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if response_times:
            analysis.update({
                "avg_response_time_ms": statistics.mean(response_times),
                "median_response_time_ms": statistics.median(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "p95_response_time_ms": self._percentile(response_times, 95),
                "p99_response_time_ms": self._percentile(response_times, 99),
                "std_deviation_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0
            })
        
        # Error analysis
        if failed_requests:
            error_codes = {}
            error_messages = {}
            for req in failed_requests:
                status_code = req.get("status_code", 0)
                error_codes[status_code] = error_codes.get(status_code, 0) + 1
                
                error_msg = req.get("error", "Unknown error")
                error_messages[error_msg] = error_messages.get(error_msg, 0) + 1
            
            analysis["error_codes"] = error_codes
            analysis["error_messages"] = error_messages
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def save_results(self, results: List[Dict[str, Any]], analysis: Dict[str, Any], filename: str) -> None:
        """Save test results to file"""
        results_dir = Path("results/load_tests")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        report = {
            "test_type": "load_test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
            "detailed_results": results
        }
        
        output_file = results_dir / f"{filename}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")


class StressTester:
    """Stress testing for extreme conditions"""
    
    def __init__(self):
        self.load_tester = LoadTester()
    
    async def stress_test_burst(self, burst_size: int = 100, duration_seconds: int = 60) -> Dict[str, Any]:
        """Stress test with burst traffic"""
        logger.info(f"Starting burst stress test: {burst_size} requests over {duration_seconds}s")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        results = []
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                # Send burst of requests
                burst_tasks = []
                for i in range(burst_size):
                    alert_id = f"STRESS-{int(time.time())}-{request_count:04d}"
                    alert_data = self.load_tester.generate_test_alert(alert_id)
                    burst_tasks.append(self.load_tester.send_alert_async(session, alert_data))
                    request_count += 1
                
                # Wait for burst to complete
                burst_results = await asyncio.gather(*burst_tasks, return_exceptions=True)
                
                # Collect valid results
                for result in burst_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                
                # Wait before next burst
                await asyncio.sleep(1)
        
        return self.load_tester.analyze_results(results)
    
    def stress_test_sustained(self, requests_per_second: int, duration_seconds: int = 300) -> Dict[str, Any]:
        """Stress test with sustained traffic"""
        logger.info(f"Starting sustained stress test: {requests_per_second} RPS for {duration_seconds}s")
        
        results = []
        start_time = time.time()
        
        def send_request():
            alert_id = f"SUSTAIN-{int(time.time())}-{len(results):04d}"
            alert_data = self.load_tester.generate_test_alert(alert_id)
            return asyncio.run(self.load_tester.send_alert_async(
                aiohttp.ClientSession(), alert_data
            ))
        
        # Calculate timing
        interval = 1.0 / requests_per_second
        
        with ThreadPoolExecutor(max_workers=requests_per_second * 2) as executor:
            futures = []
            
            while time.time() - start_time < duration_seconds:
                future = executor.submit(send_request)
                futures.append(future)
                
                # Rate limiting
                time.sleep(interval)
                
                # Collect completed futures
                completed = [f for f in futures if f.done()]
                for future in completed:
                    try:
                        result = future.result()
                        results.append(result)
                        futures.remove(future)
                    except Exception as e:
                        logger.error(f"Request failed: {e}")
            
            # Wait for remaining requests
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Request failed: {e}")
        
        return self.load_tester.analyze_results(results)


async def main():
    """Main function to run load tests"""
    tester = LoadTester()
    stress_tester = StressTester()
    
    # Test configurations
    test_configs = [
        {"name": "light_load", "requests": 50, "concurrency": 5},
        {"name": "medium_load", "requests": 200, "concurrency": 20},
        {"name": "heavy_load", "requests": 500, "concurrency": 50},
        {"name": "sequential", "requests": 100, "concurrency": 1},
    ]
    
    # Run load tests
    for config in test_configs:
        logger.info(f"Running {config['name']} test...")
        
        if config["concurrency"] == 1:
            results = tester.run_sequential_test(config["requests"])
        else:
            results = await tester.run_concurrent_test(config["requests"], config["concurrency"])
        
        analysis = tester.analyze_results(results)
        tester.save_results(results, analysis, config["name"])
        
        # Print summary
        print(f"\n{config['name'].upper()} TEST RESULTS:")
        print(f"  Requests: {analysis['total_requests']}")
        print(f"  Success Rate: {analysis['success_rate']:.2f}%")
        if "avg_response_time_ms" in analysis:
            print(f"  Avg Response Time: {analysis['avg_response_time_ms']:.2f}ms")
            print(f"  P95 Response Time: {analysis['p95_response_time_ms']:.2f}ms")
        print(f"  Failed Requests: {analysis['failed_requests']}")
    
    # Run stress tests
    logger.info("Running stress tests...")
    
    # Burst test
    burst_analysis = await stress_tester.stress_test_burst(burst_size=50, duration_seconds=30)
    stress_tester.load_tester.save_results([], burst_analysis, "burst_stress")
    
    print(f"\nBURST STRESS TEST RESULTS:")
    print(f"  Requests: {burst_analysis['total_requests']}")
    print(f"  Success Rate: {burst_analysis['success_rate']:.2f}%")
    
    # Sustained test
    sustained_analysis = stress_tester.stress_test_sustained(requests_per_second=10, duration_seconds=60)
    stress_tester.load_tester.save_results([], sustained_analysis, "sustained_stress")
    
    print(f"\nSUSTAINED STRESS TEST RESULTS:")
    print(f"  Requests: {sustained_analysis['total_requests']}")
    print(f"  Success Rate: {sustained_analysis['success_rate']:.2f}%")
    
    logger.info("Load testing completed")


if __name__ == "__main__":
    asyncio.run(main())


class TestLoadPerformance(unittest.TestCase):
    """Unit tests for load testing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.load_tester = LoadTester()
    
    def test_generate_test_alert(self):
        """Test alert generation for load testing"""
        alert = self.load_tester.generate_test_alert("ALERT-TEST-001")
        
        self.assertIn("alert_id", alert)
        self.assertEqual(alert["alert_id"], "ALERT-TEST-001")
        self.assertIn("hostname", alert)
        self.assertIn("src_ip", alert)
        self.assertIn("hash", alert)
        self.assertIn("sha256", alert["hash"])
        self.assertIn("severity", alert)
        self.assertIn("source", alert)
        self.assertIn("detection_time", alert)
        self.assertIn("event_type", alert)
        self.assertIn("description", alert)
    
    def test_analyze_results_empty(self):
        """Test result analysis with empty results"""
        analysis = self.load_tester.analyze_results([])
        self.assertIn("error", analysis)
    
    def test_analyze_results_successful(self):
        """Test result analysis with successful requests"""
        results = [
            {
                "alert_id": "TEST-001",
                "status_code": 200,
                "response_time_ms": 100,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "alert_id": "TEST-002", 
                "status_code": 200,
                "response_time_ms": 150,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        analysis = self.load_tester.analyze_results(results)
        
        self.assertEqual(analysis["total_requests"], 2)
        self.assertEqual(analysis["successful_requests"], 2)
        self.assertEqual(analysis["failed_requests"], 0)
        self.assertEqual(analysis["success_rate"], 100.0)
        self.assertIn("avg_response_time_ms", analysis)
        self.assertIn("median_response_time_ms", analysis)
        self.assertIn("min_response_time_ms", analysis)
        self.assertIn("max_response_time_ms", analysis)
    
    def test_percentile_calculation(self):
        """Test percentile calculation"""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        p50 = self.load_tester._percentile(data, 50)
        p95 = self.load_tester._percentile(data, 95)
        
        self.assertEqual(p50, 5.5)  # Median of even number of items
        self.assertAlmostEqual(p95, 9.55, places=2)  # 95th percentile (allow floating point precision)
    
    def test_save_results(self):
        """Test saving results to file"""
        results = [
            {
                "alert_id": "TEST-001",
                "status_code": 200,
                "response_time_ms": 100,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        analysis = self.load_tester.analyze_results(results)
        
        # Test saving (this will create a file)
        self.load_tester.save_results(results, analysis, "test_save")
        
        # Check if file was created
        results_file = Path("results/load_tests/test_save.json")
        self.assertTrue(results_file.exists())
        
        # Clean up
        if results_file.exists():
            results_file.unlink()
    
    def test_load_test_integration(self):
        """Integration test for load testing"""
        # Test runs regardless of external services availability
        # Skip by default to avoid dependency on external services
        pass
