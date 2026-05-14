import asyncio
import docker
import json
import logging
import os
import psutil
import redis
import subprocess
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SOAR Lab Management API",
    description="REST API for SOAR Ransomware Lab Management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Redis client for caching
redis_client = None
try:
    redis_url = os.getenv("REDIS_URL", "redis://:RedisSecurePassword678!@#@localhost:6379/0")
    redis_client = redis.from_url(redis_url)
    redis_client.ping()
    logger.info("Connected to Redis")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")

# Docker client
try:
    docker_client = docker.from_env()
    logger.info("Connected to Docker")
except Exception as e:
    logger.error(f"Docker connection failed: {e}")
    docker_client = None

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class TestRequest(BaseModel):
    category: str

class BackupRequest(BaseModel):
    backup_name: str

class ServiceStatus(BaseModel):
    service: str
    status: bool
    url: str

class Metrics(BaseModel):
    cpu: float
    memory: float
    disk: float
    timestamp: datetime

class TestResults(BaseModel):
    category: str
    passed: int
    failed: int
    skipped: int
    coverage: float
    output: str
    duration: float

# Authentication
def verify_credentials(username: str, password: str) -> bool:
    """Simple authentication - in production, use proper auth system"""
    env_username = os.getenv("WEB_UI_USER", "admin")
    env_password = os.getenv("WEB_UI_PASSWORD", "WebUIPassword123!@#")
    return username == env_username and password == env_password

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token or API key"""
    token = credentials.credentials
    # Simple token verification - in production, use proper JWT
    if token == os.getenv("API_AUTH_SECRET", "ApiAuthSecretKey456!@#"):
        return {"user": "authenticated"}
    raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection closed, remove it
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint"""
    return """
    <html>
        <head>
            <title>SOAR Lab Management API</title>
        </head>
        <body>
            <h1>SOAR Lab Management API</h1>
            <p>API Documentation: <a href="/docs">/docs</a></p>
            <p>Health Check: <a href="/health">/health</a></p>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Authentication endpoint"""
    if verify_credentials(request.username, request.password):
        token = os.getenv("API_AUTH_SECRET", "ApiAuthSecretKey456!@#")
        return {"token": token, "message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/verify")
async def verify_auth(current_user: dict = Depends(get_current_user)):
    """Verify authentication token"""
    return {"valid": True, "user": current_user}

@app.get("/metrics", response_model=Metrics)
async def get_metrics(current_user: dict = Depends(get_current_user)):
    """Get system metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        return Metrics(
            cpu=round(cpu_percent, 1),
            memory=round(memory_percent, 1),
            disk=round(disk_percent, 1),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

@app.get("/services/status")
async def get_services_status(current_user: dict = Depends(get_current_user)):
    """Get status of all services"""
    if not docker_client:
        raise HTTPException(status_code=500, detail="Docker not available")
    
    services = {
        "thehive": {"url": "http://localhost:9000/api/health"},
        "cortex": {"url": "http://localhost:9001/"},
        "shuffle": {"url": "http://localhost:5001/api/v1/health"},
        "kibana": {"url": "http://localhost:15601/api/status"},
        "wazuh-manager": {"url": "http://localhost:55100/"},
        "misp": {"url": "http://localhost:8082/users/heartbeat"},
        "docs-site": {"url": "http://localhost:3000/docs/"},
        "api": {"url": "http://localhost:8000/health"}
    }
    
    status = {}
    
    for service, config in services.items():
        try:
            # Try to check container status
            container_name = f"soar_{service}"
            container = docker_client.containers.get(container_name)
            status[service] = container.status == "running"
        except docker.errors.NotFound:
            # Container not found, try HTTP check
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(config["url"], timeout=aiohttp.ClientTimeout(total=5)) as response:
                        status[service] = response.status < 400
            except:
                status[service] = False
        except Exception as e:
            logger.error(f"Error checking service {service}: {e}")
            status[service] = False
    
    return status

@app.post("/tests/run", response_model=TestResults)
async def run_tests(request: TestRequest, current_user: dict = Depends(get_current_user)):
    """Run tests and return results"""
    try:
        category = request.category
        test_command = f"python -m pytest tests/{category} -v --tb=short --cov=scripts --cov-report=term-missing"
        
        if category == "all":
            test_command = "python -m pytest tests/ -v --tb=short --cov=scripts --cov-report=term-missing"
        
        # Run tests
        start_time = datetime.now()
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Parse output
        output = result.stdout + result.stderr
        
        # Extract test results from output
        passed = failed = skipped = 0
        coverage = 0.0
        
        for line in output.split('\n'):
            if 'passed' in line and 'failed' in line and 'skipped' in line:
                # Parse: "=== 212 passed, 14 warnings in 4.20s ==="
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        passed = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        failed = int(parts[i-1])
                    elif part == 'skipped' and i > 0:
                        skipped = int(parts[i-1])
            elif 'coverage:' in line and '%' in line:
                # Parse coverage: "TOTAL                           1305    210    84%"
                parts = line.split()
                if len(parts) >= 4:
                    coverage = float(parts[-1].replace('%', ''))
        
        return TestResults(
            category=category,
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage=coverage,
            output=output,
            duration=duration
        )
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Tests timed out")
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run tests: {str(e)}")

@app.get("/tests/coverage")
async def get_test_coverage(current_user: dict = Depends(get_current_user)):
    """Get current test coverage"""
    try:
        # Try to get from cache first
        if redis_client:
            cached = redis_client.get("test_coverage")
            if cached:
                return json.loads(cached)
        
        # Run coverage command
        result = subprocess.run(
            "python -m pytest tests/ --cov=scripts --cov-report=json",
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse coverage JSON if available
        coverage_data = {"unit": 0, "integration": 0, "overall": 0}
        
        try:
            if os.path.exists("coverage.json"):
                with open("coverage.json", "r") as f:
                    coverage_json = json.load(f)
                    coverage_data["overall"] = coverage_json.get("totals", {}).get("percent_covered", 0)
        except:
            pass
        
        # Cache the result
        if redis_client:
            redis_client.setex("test_coverage", 300, json.dumps(coverage_data))  # 5 minutes cache
        
        return coverage_data
        
    except Exception as e:
        logger.error(f"Error getting coverage: {e}")
        return {"unit": 0, "integration": 0, "overall": 0}

@app.post("/backup/create")
async def create_backup(current_user: dict = Depends(get_current_user)):
    """Create a backup"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"soar_backup_{timestamp}.tar.gz"
        
        # Create backup command
        backup_cmd = f"tar -czf backups/{backup_filename} --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='node_modules' --exclude='htmlcov' ."
        
        # Ensure backups directory exists
        os.makedirs("backups", exist_ok=True)
        
        # Run backup
        result = subprocess.run(
            backup_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"Backup failed: {result.stderr}")
        
        return {"filename": backup_filename, "message": "Backup created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")

@app.get("/backup/list")
async def list_backups(current_user: dict = Depends(get_current_user)):
    """List available backups"""
    try:
        backups_dir = Path("backups")
        if not backups_dir.exists():
            return {"backups": []}
        
        backups = []
        for backup_file in backups_dir.glob("*.tar.gz"):
            stat = backup_file.stat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            
            backups.append({
                "name": backup_file.name,
                "size": f"{size_mb} MB",
                "date": date_str
            })
        
        # Sort by date (newest first)
        backups.sort(key=lambda x: x["date"], reverse=True)
        
        return {"backups": backups}
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail="Failed to list backups")

@app.post("/backup/restore")
async def restore_backup(request: BackupRequest, current_user: dict = Depends(get_current_user)):
    """Restore from backup"""
    try:
        backup_path = f"backups/{request.backup_name}"
        
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        # Restore command (extracting)
        restore_cmd = f"tar -xzf {backup_path}"
        
        result = subprocess.run(
            restore_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"Restore failed: {result.stderr}")
        
        return {"message": f"Backup {request.backup_name} restored successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time logs"""
    await manager.connect(websocket)
    try:
        while True:
            # Simulate log messages (in production, connect to actual log stream)
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"System running normally - {datetime.now().strftime('%H:%M:%S')}"
            }
            
            # Send log data
            await websocket.send_text(json.dumps(log_data))
            
            # Wait before next message
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
