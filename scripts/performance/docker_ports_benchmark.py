#!/usr/bin/env python3
"""
Docker Ports Performance Benchmark
Performance testing for Docker ports and services
"""

import json
import time
import requests
import statistics
import subprocess
from datetime import datetime
from typing import Dict, List, Any


class DockerPortsBenchmark:
    """Performance benchmark for Docker ports"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'summary': {}
        }
    
    def benchmark_service(self, service_name: str, url: str, endpoint: str = "/") -> Dict[str, Any]:
        """Benchmark a specific service"""
        print(f"Benchmarking {service_name}...")
        
        response_times = []
        success_count = 0
        error_count = 0
        
        # Run 10 requests
        for i in range(10):
            try:
                start_time = time.time()
                response = requests.get(f"{url}{endpoint}", timeout=10)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"  Request {i+1} failed: {e}")
        
        # Calculate statistics
        if response_times:
            stats = {
                'avg_response_time': statistics.mean(response_times),
                'median_response_time': statistics.median(response_times),
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'std_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'success_rate': success_count / 10,
                'error_rate': error_count / 10,
                'total_requests': 10
            }
        else:
            stats = {
                'avg_response_time': 0,
                'median_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'std_deviation': 0,
                'success_rate': 0,
                'error_rate': 1,
                'total_requests': 10
            }
        
        return stats
    
    def benchmark_docker_services(self) -> Dict[str, Any]:
        """Benchmark all Docker services"""
        services = {
            'elasticsearch': 'http://localhost:19200',
            'redis': 'http://localhost:6379',  # Will be handled differently
            'grafana': 'http://localhost:3000',
            'prometheus': 'http://localhost:9090',
            'thehive': 'http://localhost:9000',
            'cortex': 'http://localhost:9001'
        }
        
        for service_name, base_url in services.items():
            if service_name == 'redis':
                # Redis benchmark using docker exec
                self.results['services'][service_name] = self.benchmark_redis()
            else:
                endpoint = self.get_health_endpoint(service_name)
                self.results['services'][service_name] = self.benchmark_service(
                    service_name, base_url, endpoint
                )
        
        return self.results
    
    def benchmark_redis(self) -> Dict[str, Any]:
        """Benchmark Redis using docker exec"""
        print("Benchmarking Redis...")
        
        try:
            # Test Redis ping latency
            ping_times = []
            for i in range(10):
                start_time = time.time()
                result = subprocess.run(
                    ["docker", "exec", "soartest_redis", "redis-cli", "ping"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                end_time = time.time()
                
                if result.returncode == 0:
                    ping_time = (end_time - start_time) * 1000
                    ping_times.append(ping_time)
            
            if ping_times:
                return {
                    'avg_response_time': statistics.mean(ping_times),
                    'median_response_time': statistics.median(ping_times),
                    'min_response_time': min(ping_times),
                    'max_response_time': max(ping_times),
                    'std_deviation': statistics.stdev(ping_times) if len(ping_times) > 1 else 0,
                    'success_rate': len(ping_times) / 10,
                    'error_rate': (10 - len(ping_times)) / 10,
                    'total_requests': 10
                }
            else:
                return {
                    'avg_response_time': 0,
                    'success_rate': 0,
                    'error_rate': 1,
                    'total_requests': 10
                }
        except Exception as e:
            print(f"Redis benchmark failed: {e}")
            return {
                'avg_response_time': 0,
                'success_rate': 0,
                'error_rate': 1,
                'total_requests': 10
            }
    
    def get_health_endpoint(self, service_name: str) -> str:
        """Get health endpoint for service"""
        endpoints = {
            'elasticsearch': '/_cluster/health',
            'grafana': '/api/health',
            'prometheus': '/-/healthy',
            'thehive': '/api/health',
            'cortex': '/api/health'
        }
        return endpoints.get(service_name, '/')
    
    def calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        services = self.results['services']
        
        if not services:
            return {}
        
        # Calculate overall statistics
        all_response_times = []
        total_success_rate = 0
        total_services = len(services)
        
        for service_stats in services.values():
            if service_stats.get('avg_response_time', 0) > 0:
                all_response_times.append(service_stats['avg_response_time'])
            total_success_rate += service_stats.get('success_rate', 0)
        
        summary = {
            'total_services': total_services,
            'overall_success_rate': total_success_rate / total_services if total_services > 0 else 0,
            'fastest_service': None,
            'slowest_service': None,
            'most_reliable': None,
            'least_reliable': None
        }
        
        if all_response_times:
            summary['avg_response_time_all'] = statistics.mean(all_response_times)
            summary['median_response_time_all'] = statistics.median(all_response_times)
        
        # Find fastest and slowest services
        fastest_time = float('inf')
        slowest_time = 0
        most_reliable = 0
        least_reliable = 1
        
        for service_name, stats in services.items():
            avg_time = stats.get('avg_response_time', 0)
            success_rate = stats.get('success_rate', 0)
            
            if avg_time > 0 and avg_time < fastest_time:
                fastest_time = avg_time
                summary['fastest_service'] = service_name
            
            if avg_time > slowest_time:
                slowest_time = avg_time
                summary['slowest_service'] = service_name
            
            if success_rate > most_reliable:
                most_reliable = success_rate
                summary['most_reliable'] = service_name
            
            if success_rate < least_reliable:
                least_reliable = success_rate
                summary['least_reliable'] = service_name
        
        return summary
    
    def save_results(self, filename: str = 'benchmark-results.json'):
        """Save benchmark results to file"""
        self.results['summary'] = self.calculate_summary()
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Benchmark results saved to {filename}")
    
    def print_summary(self):
        """Print benchmark summary"""
        summary = self.calculate_summary()
        
        print("\n" + "="*60)
        print("DOCKER PORTS PERFORMANCE BENCHMARK")
        print("="*60)
        
        print(f"\n📊 SUMMARY:")
        print(f"Total Services: {summary.get('total_services', 0)}")
        print(f"Overall Success Rate: {summary.get('overall_success_rate', 0):.2%}")
        
        if 'avg_response_time_all' in summary:
            print(f"Average Response Time: {summary['avg_response_time_all']:.2f}ms")
            print(f"Median Response Time: {summary['median_response_time_all']:.2f}ms")
        
        print(f"\n🏆 PERFORMANCE LEADERS:")
        if summary.get('fastest_service'):
            fastest = self.results['services'][summary['fastest_service']]
            print(f"Fastest: {summary['fastest_service']} ({fastest['avg_response_time']:.2f}ms)")
        
        if summary.get('slowest_service'):
            slowest = self.results['services'][summary['slowest_service']]
            print(f"Slowest: {summary['slowest_service']} ({slowest['avg_response_time']:.2f}ms)")
        
        if summary.get('most_reliable'):
            most_rel = self.results['services'][summary['most_reliable']]
            print(f"Most Reliable: {summary['most_reliable']} ({most_rel['success_rate']:.2%})")
        
        if summary.get('least_reliable'):
            least_rel = self.results['services'][summary['least_reliable']]
            print(f"Least Reliable: {summary['least_reliable']} ({least_rel['success_rate']:.2%})")
        
        print(f"\n📈 SERVICE DETAILS:")
        for service_name, stats in self.results['services'].items():
            status = "✅" if stats['success_rate'] >= 0.8 else "⚠️" if stats['success_rate'] >= 0.5 else "❌"
            print(f"{status} {service_name}:")
            print(f"  Response Time: {stats['avg_response_time']:.2f}ms (±{stats['std_deviation']:.2f}ms)")
            print(f"  Success Rate: {stats['success_rate']:.2%}")
            print(f"  Min/Max: {stats['min_response_time']:.2f}ms / {stats['max_response_time']:.2f}ms")
        
        print("\n" + "="*60)


def main():
    """Main benchmark execution"""
    print("🚀 Starting Docker Ports Performance Benchmark")
    print("This will test response times and reliability of all Docker services...")
    
    benchmark = DockerPortsBenchmark()
    
    try:
        # Run benchmarks
        benchmark.benchmark_docker_services()
        
        # Print summary
        benchmark.print_summary()
        
        # Save results
        benchmark.save_results()
        
        print("\n✅ Benchmark completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
