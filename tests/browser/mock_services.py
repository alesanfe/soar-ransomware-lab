#!/usr/bin/env python3
"""
Mock services for browser tests
These services simulate the web interfaces of Docker services
to make browser tests reproducible without requiring full Docker infrastructure
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json


class TheHiveMockHandler(BaseHTTPRequestHandler):
    """Mock TheHive web interface"""
    
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/index'):
            self.serve_main_page()
        elif self.path.startswith('/api'):
            self.serve_api_response()
        else:
            self.send_404()
    
    def serve_main_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>TheHive - Incident Response Platform</title>
</head>
<body>
    <div id="app">
        <h1>TheHive</h1>
        <div class="dashboard">
            <h2>Dashboard</h2>
            <div class="cases">
                <h3>Recent Cases</h3>
                <div class="case-item">Ransomware Investigation #001</div>
                <div class="case-item">Malware Analysis #002</div>
            </div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_api_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        api_response = {
            "status": "ok",
            "cases": [
                {"id": "001", "title": "Ransomware Investigation", "severity": "high"},
                {"id": "002", "title": "Malware Analysis", "severity": "medium"}
            ]
        }
        self.wfile.write(json.dumps(api_response).encode())
    
    def send_404(self):
        self.send_response(404)
        self.end_headers()


class CortexMockHandler(BaseHTTPRequestHandler):
    """Mock Cortex web interface"""
    
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/index'):
            self.serve_main_page()
        elif self.path.startswith('/api'):
            self.serve_api_response()
        else:
            self.send_404()
    
    def serve_main_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Cortex - Analysis Engine</title>
</head>
<body>
    <div id="app">
        <h1>Cortex</h1>
        <div class="analyzers">
            <h2>Available Analyzers</h2>
            <div class="analyzer">VirusTotal</div>
            <div class="analyzer">OTX</div>
            <div class="analyzer">PassiveDNS</div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_api_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        api_response = {
            "status": "ok",
            "analyzers": [
                {"name": "VirusTotal", "status": "Ready"},
                {"name": "OTX", "status": "Ready"}
            ]
        }
        self.wfile.write(json.dumps(api_response).encode())
    
    def send_404(self):
        self.send_response(404)
        self.end_headers()


class GrafanaMockHandler(BaseHTTPRequestHandler):
    """Mock Grafana web interface"""
    
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/login'):
            self.serve_login_page()
        elif self.path.startswith('/dashboard'):
            self.serve_dashboard()
        else:
            self.send_404()
    
    def serve_login_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Grafana - Login</title>
</head>
<body>
    <div class="login-page">
        <h1>Grafana</h1>
        <form class="login-form">
            <input type="text" placeholder="Username" />
            <input type="password" placeholder="Password" />
            <button type="submit">Log in</button>
        </form>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_dashboard(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Grafana - Dashboard</title>
</head>
<body>
    <div class="dashboard">
        <h1>Grafana Dashboard</h1>
        <div class="panel">
            <h3>System Metrics</h3>
            <div class="metric">CPU Usage: 45%</div>
            <div class="metric">Memory: 2.1GB</div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def send_404(self):
        self.send_response(404)
        self.end_headers()


class PrometheusMockHandler(BaseHTTPRequestHandler):
    """Mock Prometheus web interface"""
    
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/graph'):
            self.serve_main_page()
        elif self.path.startswith('/api'):
            self.serve_api_response()
        else:
            self.send_404()
    
    def serve_main_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Prometheus - Time Series Database</title>
</head>
<body>
    <div class="prometheus">
        <h1>Prometheus</h1>
        <div class="metrics">
            <h2>Available Metrics</h2>
            <div class="metric">http_requests_total</div>
            <div class="metric">cpu_usage_percent</div>
            <div class="metric">memory_usage_bytes</div>
        </div>
        <div class="targets">
            <h3>Targets</h3>
            <div class="target">localhost:9090 (UP)</div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_api_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        api_response = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {"metric": {"__name__": "up"}, "value": [1234567890, "1"]}
                ]
            }
        }
        self.wfile.write(json.dumps(api_response).encode())
    
    def send_404(self):
        self.send_response(404)
        self.end_headers()


class ShuffleMockHandler(BaseHTTPRequestHandler):
    """Mock Shuffle web interface"""
    
    def do_GET(self):
        if self.path == '/' or self.path.startswith('/login'):
            self.serve_login_page()
        elif self.path.startswith('/app'):
            self.serve_main_app()
        else:
            self.send_404()
    
    def serve_login_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Shuffle - Workflow Automation</title>
</head>
<body>
    <div class="login-page">
        <h1>Shuffle</h1>
        <form class="login-form">
            <input type="text" placeholder="Username" />
            <input type="password" placeholder="Password" />
            <button type="submit">Log in</button>
        </form>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_main_app(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Shuffle - Workflows</title>
</head>
<body>
    <div class="shuffle-app">
        <h1>Shuffle</h1>
        <div class="workflows">
            <h2>Active Workflows</h2>
            <div class="workflow">Security Alert Processing</div>
            <div class="workflow">Automated Incident Response</div>
            <div class="workflow">Threat Intelligence Enrichment</div>
        </div>
        <div class="automation">
            <h3>Automation Status</h3>
            <div class="status">All systems operational</div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def send_404(self):
        self.send_response(404)
        self.end_headers()


class APIMockHandler(BaseHTTPRequestHandler):
    """Mock API service"""
    
    def do_GET(self):
        if self.path == '/health' or self.path == '/api/health':
            self.serve_health_response()
        elif self.path.startswith('/api'):
            self.serve_api_response()
        else:
            self.serve_main_page()
    
    def serve_main_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>SOAR API - FastAPI Service</title>
</head>
<body>
    <div class="api-docs">
        <h1>SOAR Ransomware Lab API</h1>
        <div class="endpoints">
            <h2>Available Endpoints</h2>
            <div class="endpoint">GET /health</div>
            <div class="endpoint">GET /api/alerts</div>
            <div class="endpoint">POST /api/alerts</div>
        </div>
    </div>
</body>
</html>
        """
        self.wfile.write(html_content.encode())
    
    def serve_health_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        health_response = {
            "status": "healthy",
            "service": "soar-api",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        self.wfile.write(json.dumps(health_response).encode())
    
    def serve_api_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        api_response = {
            "message": "SOAR API is operational",
            "endpoints": [
                "/health", "/api/alerts", "/api/cases", "/api/analytics"
            ]
        }
        self.wfile.write(json.dumps(api_response).encode())


class MockServiceManager:
    """Manages multiple mock services for browser testing"""
    
    def __init__(self):
        self.services = []
        self.threads = []
    
    def start_all_services(self):
        """Start all mock services"""
        service_configs = [
            (8000, APIMockHandler, "API"),
            (9000, TheHiveMockHandler, "TheHive"),
            (9001, CortexMockHandler, "Cortex"),
            (3000, GrafanaMockHandler, "Grafana"),
            (9090, PrometheusMockHandler, "Prometheus"),
            (3001, ShuffleMockHandler, "Shuffle")
        ]
        
        for port, handler_class, name in service_configs:
            try:
                server = HTTPServer(('localhost', port), handler_class)
                self.services.append(server)
                
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                self.threads.append(thread)
                
                print(f"✅ Started mock {name} service on port {port}")
                
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    print(f"⚠️  Port {port} already in use, skipping mock {name} service")
                else:
                    print(f"❌ Failed to start mock {name} service: {e}")
    
    def stop_all_services(self):
        """Stop all mock services"""
        for server in self.services:
            server.shutdown()
        
        for thread in self.threads:
            thread.join(timeout=1)
        
        print("🛑 All mock services stopped")


# Global instance for use in tests
mock_manager = MockServiceManager()


def start_mock_services():
    """Start all mock services (call this in test setup)"""
    mock_manager.start_all_services()
    time.sleep(1)  # Give services time to start


def stop_mock_services():
    """Stop all mock services (call this in test teardown)"""
    mock_manager.stop_all_services()


if __name__ == "__main__":
    # Run standalone for testing
    try:
        print("Starting mock services for browser testing...")
        start_mock_services()
        print("Mock services running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping mock services...")
        stop_mock_services()
        print("Done.")
