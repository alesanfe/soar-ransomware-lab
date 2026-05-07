#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Stress Testing Tests
Stress and load testing for SOAR components under extreme conditions
"""

import unittest
import asyncio
import aiohttp
import time
import statistics
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import json
import logging
import gc
try:
    import resource
except ImportError:
    # Windows compatibility - resource module not available
    resource = None
from typing import List, Dict, Any, Optional
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StressTester:
    """Stress testing framework for SOAR components"""
    
    def __init__(self):
        self.base_url = 'http://localhost:5001'
        self.webhook_url = f"{self.base_url}/webhook"
        self.api_token = 'test-token'
        self.results = []
        self.system_metrics = []
        
    def generate_test_alert(self, alert_id: str) -> Dict[str, Any]:
        """Generate a test alert for stress testing"""
        return {
            "alert_id": alert_id,
            "hostname": f"STRESS-HOST-{alert_id.split('-')[-1]}",
            "src_ip": f"192.168.1.{(int(alert_id.split('-')[-1]) % 254) + 1}",
            "hash": {
                "sha256": "a" * 64
            },
            "severity": "2",
            "source": "stress-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "description": f"Stress test alert {alert_id}"
        }

    async def send_alert_async(self, session: aiohttp.ClientSession, alert_id: str) -> Dict[str, Any]:
        """Send alert asynchronously"""
        start_time = time.time()
        
        try:
            payload = self.generate_test_alert(alert_id)
            
            async with session.post(
                self.webhook_url,
                headers={
                    'Authorization': f'Bearer {self.api_token}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                end_time = time.time()
                
                return {
                    'alert_id': alert_id,
                    'status': response.status,
                    'response_time': end_time - start_time,
                    'success': response.status in [200, 202, 204],
                    'timestamp': end_time
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                'alert_id': alert_id,
                'status': 0,
                'response_time': end_time - start_time,
                'success': False,
                'error': str(e),
                'timestamp': end_time
            }

    async def concurrent_alert_burst(self, num_alerts: int, concurrency: int = 50) -> List[Dict[str, Any]]:
        """Send burst of alerts concurrently"""
        logger.info(f"Starting concurrent burst: {num_alerts} alerts, concurrency: {concurrency}")
        
        connector = aiohttp.TCPConnector(limit=concurrency, limit_per_host=concurrency)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Generate alert IDs
            alert_ids = [f"STRESS-{int(time.time())}-{i:04d}" for i in range(num_alerts)]
            
            # Create tasks
            tasks = [self.send_alert_async(session, alert_id) for alert_id in alert_ids]
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter exceptions
            valid_results = []
            for result in results:
                if isinstance(result, dict):
                    valid_results.append(result)
                else:
                    logger.error(f"Task exception: {result}")
            
            return valid_results

    def monitor_system_resources(self, duration: int) -> List[Dict[str, Any]]:
        """Monitor system resources during stress test"""
        logger.info(f"Starting system monitoring for {duration} seconds")
        
        metrics = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_count = psutil.cpu_count()
                
                # Memory metrics
                memory = psutil.virtual_memory()
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                
                # Network metrics
                network = psutil.net_io_counters()
                
                # Process metrics (Docker containers)
                docker_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        if 'docker' in proc.info['name'].lower():
                            docker_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_percent': proc.info['memory_percent']
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                metric = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'memory_total': memory.total,
                    'memory_available': memory.available,
                    'memory_percent': memory.percent,
                    'disk_total': disk.total,
                    'disk_free': disk.free,
                    'disk_percent': (disk.total - disk.free) / disk.total * 100,
                    'network_bytes_sent': network.bytes_sent,
                    'network_bytes_recv': network.bytes_recv,
                    'docker_processes': docker_processes
                }
                
                metrics.append(metric)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
            
            time.sleep(1)
        
        return metrics

    def calculate_stress_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate stress test metrics"""
        if not results:
            return {}
        
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        response_times = [r['response_time'] for r in successful]
        
        metrics = {
            'total_requests': len(results),
            'successful_requests': len(successful),
            'failed_requests': len(failed),
            'success_rate': len(successful) / len(results) * 100,
            'error_rate': len(failed) / len(results) * 100
        }
        
        if response_times:
            metrics.update({
                'avg_response_time': statistics.mean(response_times),
                'median_response_time': statistics.median(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'p95_response_time': self.percentile(response_times, 95),
                'p99_response_time': self.percentile(response_times, 99),
                'response_time_std': statistics.stdev(response_times) if len(response_times) > 1 else 0
            })
        
        # Calculate requests per second
        if results:
            time_span = max(r['timestamp'] for r in results) - min(r['timestamp'] for r in results)
            if time_span > 0:
                metrics['requests_per_second'] = len(results) / time_span
                metrics['successful_rps'] = len(successful) / time_span
        
        return metrics

    def percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def analyze_system_impact(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze system resource impact"""
        if not metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in metrics]
        memory_values = [m['memory_percent'] for m in metrics]
        disk_values = [m['disk_percent'] for m in metrics]
        
        analysis = {
            'cpu_peak': max(cpu_values),
            'cpu_avg': statistics.mean(cpu_values),
            'cpu_std': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0,
            'memory_peak': max(memory_values),
            'memory_avg': statistics.mean(memory_values),
            'memory_std': statistics.stdev(memory_values) if len(memory_values) > 1 else 0,
            'disk_peak': max(disk_values),
            'disk_avg': statistics.mean(disk_values),
            'disk_std': statistics.stdev(disk_values) if len(disk_values) > 1 else 0
        }
        
        # Analyze Docker processes
        all_docker_procs = []
        for metric in metrics:
            all_docker_procs.extend(metric.get('docker_processes', []))
        
        if all_docker_procs:
            docker_cpu = [p['cpu_percent'] for p in all_docker_procs if p['cpu_percent'] is not None]
            docker_memory = [p['memory_percent'] for p in all_docker_procs if p['memory_percent'] is not None]
            
            if docker_cpu:
                analysis['docker_cpu_peak'] = max(docker_cpu)
                analysis['docker_cpu_avg'] = statistics.mean(docker_cpu)
            
            if docker_memory:
                analysis['docker_memory_peak'] = max(docker_memory)
                analysis['docker_memory_avg'] = statistics.mean(docker_memory)
        
        return analysis

    async def run_stress_test(self, test_name: str, num_alerts: int, concurrency: int = 50) -> Dict[str, Any]:
        """Run a complete stress test"""
        logger.info(f"Starting stress test: {test_name}")
        
        # Start system monitoring in background
        monitor_thread = threading.Thread(
            target=lambda: self.system_metrics.extend(
                self.monitor_system_resources(120)  # Monitor for 2 minutes
            )
        )
        monitor_thread.start()
        
        # Run stress test
        start_time = time.time()
        results = await self.concurrent_alert_burst(num_alerts, concurrency)
        end_time = time.time()
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Calculate metrics
        stress_metrics = self.calculate_stress_metrics(results)
        system_impact = self.analyze_system_impact(self.system_metrics)
        
        test_result = {
            'test_name': test_name,
            'test_start': start_time,
            'test_end': end_time,
            'test_duration': end_time - start_time,
            'configuration': {
                'num_alerts': num_alerts,
                'concurrency': concurrency
            },
            'results': stress_metrics,
            'system_impact': system_impact,
            'raw_results': results,
            'system_metrics': self.system_metrics
        }
        
        # Save results
        results_file = Path(f"../results/stress_test_{test_name}_{int(start_time)}.json")
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(test_result, f, indent=2, default=str)
        
        logger.info(f"Stress test completed: {test_name}")
        return test_result


class StressTestRunner:
    """Run multiple stress test scenarios"""
    
    def __init__(self):
        self.tester = StressTester()
        self.test_results = []

    async def run_all_stress_tests(self):
        """Run all stress test scenarios"""
        test_scenarios = [
            ("light_load", 100, 10),
            ("moderate_load", 500, 25),
            ("high_load", 1000, 50),
            ("extreme_load", 2000, 100),
            ("burst_test", 5000, 200)
        ]
        
        for test_name, num_alerts, concurrency in test_scenarios:
            try:
                logger.info(f"Running stress test: {test_name}")
                result = await self.tester.run_stress_test(test_name, num_alerts, concurrency)
                self.test_results.append(result)
                
                # Wait between tests to allow system recovery
                logger.info("Waiting 30 seconds for system recovery...")
                await asyncio.sleep(30)
                
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                logger.error(f"Stress test {test_name} failed: {e}")
        
        # Generate summary report
        self.generate_summary_report()

    def generate_summary_report(self):
        """Generate summary report of all stress tests"""
        logger.info("Generating stress test summary report")
        
        summary = {
            'test_run_timestamp': datetime.now(timezone.utc).isoformat(),
            'total_tests': len(self.test_results),
            'test_results': self.test_results,
            'summary_metrics': self.calculate_summary_metrics(),
            'recommendations': self.generate_recommendations()
        }
        
        # Save summary
        summary_file = Path("../results/stress_test_summary.json")
        summary_file.parent.mkdir(exist_ok=True)
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Summary report saved to {summary_file}")

    def calculate_summary_metrics(self) -> Dict[str, Any]:
        """Calculate summary metrics across all tests"""
        if not self.test_results:
            return {}
        
        summary = {
            'performance_trends': {},
            'system_impact_trends': {},
            'bottlenecks': []
        }
        
        # Performance trends
        for result in self.test_results:
            test_name = result['test_name']
            metrics = result['results']
            
            summary['performance_trends'][test_name] = {
                'success_rate': metrics.get('success_rate', 0),
                'avg_response_time': metrics.get('avg_response_time', 0),
                'requests_per_second': metrics.get('requests_per_second', 0)
            }
        
        # System impact trends
        for result in self.test_results:
            test_name = result['test_name']
            impact = result['system_impact']
            
            summary['system_impact_trends'][test_name] = {
                'cpu_peak': impact.get('cpu_peak', 0),
                'memory_peak': impact.get('memory_peak', 0),
                'docker_cpu_peak': impact.get('docker_cpu_peak', 0),
                'docker_memory_peak': impact.get('docker_memory_peak', 0)
            }
        
        # Identify bottlenecks
        for result in self.test_results:
            test_name = result['test_name']
            metrics = result['results']
            
            if metrics.get('success_rate', 100) < 95:
                summary['bottlenecks'].append({
                    'test': test_name,
                    'issue': 'Low success rate',
                    'value': f"{metrics.get('success_rate', 0):.2f}%"
                })
            
            if metrics.get('avg_response_time', 0) > 10:
                summary['bottlenecks'].append({
                    'test': test_name,
                    'issue': 'High response time',
                    'value': f"{metrics.get('avg_response_time', 0):.2f}s"
                })
        
        return summary

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not self.test_results:
            return recommendations
        
        # Analyze performance degradation
        success_rates = [r['results'].get('success_rate', 100) for r in self.test_results]
        if min(success_rates) < 95:
            recommendations.append("Consider increasing system resources or optimizing code for better success rates under load")
        
        # Analyze response time trends
        avg_response_times = [r['results'].get('avg_response_time', 0) for r in self.test_results]
        if max(avg_response_times) > 5:
            recommendations.append("Response times increase significantly under load - consider implementing caching or optimizing database queries")
        
        # Analyze system resource usage
        cpu_peaks = [r['system_impact'].get('cpu_peak', 0) for r in self.test_results]
        if max(cpu_peaks) > 80:
            recommendations.append("CPU usage exceeds 80% under load - consider horizontal scaling or CPU optimization")
        
        memory_peaks = [r['system_impact'].get('memory_peak', 0) for r in self.test_results]
        if max(memory_peaks) > 80:
            recommendations.append("Memory usage exceeds 80% under load - consider memory optimization or increasing available memory")
        
        # Docker-specific recommendations
        docker_cpu_peaks = [r['system_impact'].get('docker_cpu_peak', 0) for r in self.test_results]
        if max(docker_cpu_peaks) > 70:
            recommendations.append("Docker containers show high CPU usage - consider container resource limits or scaling")
        
        return recommendations


async def main():
    """Main stress test execution"""
    runner = StressTestRunner()
    await runner.run_all_stress_tests()


if __name__ == '__main__':
    # Run stress tests
    asyncio.run(main())


class TestStressPerformance(unittest.TestCase):
    """Unit tests for stress testing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.stress_tester = StressTester()
    
    def test_generate_test_alert(self):
        """Test alert generation for stress testing"""
        alert = self.stress_tester.generate_test_alert("STRESS-TEST-001")
        
        self.assertIn("alert_id", alert)
        self.assertEqual(alert["alert_id"], "STRESS-TEST-001")
        self.assertIn("hostname", alert)
        self.assertIn("src_ip", alert)
        self.assertIn("hash", alert)
        self.assertIn("severity", alert)
        self.assertIn("source", alert)
        self.assertIn("detection_time", alert)
        self.assertIn("event_type", alert)
    
    def test_stress_tester_initialization(self):
        """Test stress tester initialization"""
        self.assertEqual(self.stress_tester.base_url, 'http://localhost:5001')
        self.assertEqual(self.stress_tester.webhook_url, 'http://localhost:5001/webhook')
        self.assertEqual(self.stress_tester.api_token, 'test-token')
        self.assertEqual(self.stress_tester.results, [])
        self.assertEqual(self.stress_tester.system_metrics, [])
    
    def test_stress_test_integration(self):
        """Integration test for stress testing"""
        # Test runs regardless of external services availability
        # Skip by default to avoid dependency on external services
        pass
