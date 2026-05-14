"""Business logic services for SOAR Lab API."""
import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import psutil
import aiohttp

from .config import settings, redis_client, docker_client


class BackupError(Exception):
    """Custom exception for backup operations."""
    pass


def _build_tar_command(backup_path: Path, operation: str = "create") -> list:
    """
    Build tar command arguments securely.
    
    Args:
        backup_path: Path to backup file
        operation: 'create' or 'extract'
    
    Returns:
        List of command arguments for subprocess.run
    """
    # Validate operation parameter
    if operation not in ["create", "extract"]:
        raise ValueError(f"Unsupported tar operation: {operation}")
    
    # Validate backup path
    if not isinstance(backup_path, Path):
        backup_path = Path(backup_path)
    
    # Prevent path traversal attacks
    backup_str = str(backup_path.resolve())
    if '..' in str(backup_path) or backup_str.startswith('/etc/') or backup_str.startswith('/usr/') or backup_str.startswith('C:\\Windows\\') or 'etc' in backup_str.lower():
        raise ValueError(f"Invalid backup path: {backup_path}")
    
    if operation == "create":
        excludes = [
            '--exclude=__pycache__',
            '--exclude=*.pyc',
            '--exclude=.git',
            '--exclude=node_modules',
            '--exclude=htmlcov',
            '--exclude=.pytest_cache',
            '--exclude=coverage.xml',
            '--exclude=.coverage'
        ]
        return ['tar', '-czf', backup_str] + excludes + ['.']
    elif operation == "extract":
        return ['tar', '-xzf', backup_str]

logger = logging.getLogger(__name__)


async def check_service(service_name: str, service_config: Dict[str, str]) -> bool:
    """
    Check if a service is running by checking Docker container or HTTP endpoint.
    
    Args:
        service_name: Name of the service
        service_config: Service configuration dict with 'url' and 'container' keys
    
    Returns:
        bool: True if service is running, False otherwise
    """
    if not docker_client:
        return False
    
    try:
        # Try to check container status
        container_name = service_config.get("container", f"soar_{service_name}")
        container = docker_client.containers.get(container_name)
        return container.status == "running"
    except Exception as docker_error:
        logger.debug(f"Container check failed for {service_name}: {docker_error}")
        
        # Container not found, try HTTP check
        try:
            url = service_config.get("url")
            if not url:
                return False
                
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status < 400
        except Exception:
            logger.warning(f"HTTP health check failed for {service_name}")
            return False


async def get_all_services_status() -> Dict[str, bool]:
    """
    Get status of all configured services.
    
    Returns:
        Dict mapping service names to their status (running/not running)
    """
    status = {}
    
    for service_name, service_config in settings.SERVICES.items():
        try:
            status[service_name] = await check_service(service_name, service_config)
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            status[service_name] = False
    
    return status


def get_system_metrics() -> Dict[str, Any]:
    """
    Get system metrics (CPU, memory, disk usage).
    
    Returns:
        Dict with cpu, memory, disk percentages and timestamp
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        return {
            "cpu": round(cpu_percent, 1),
            "memory": round(memory_percent, 1),
            "disk": round(disk_percent, 1),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise


async def run_tests(category: str) -> Dict[str, Any]:
    """
    Run tests and return results.
    
    Args:
        category: Test category (unit, integration, e2e, all)
    
    Returns:
        Dict with test results including passed, failed, skipped, coverage, output, duration
    """
    try:
        # Validate category parameter to prevent command injection
        allowed_categories = ['unit', 'integration', 'e2e', 'all']
        if category not in allowed_categories:
            raise ValueError(f"Invalid test category: {category}")
        
        # Build command securely using list instead of string formatting
        base_cmd = ['python', '-m', 'pytest']
        
        if category == "all":
            base_cmd.extend(['tests/', '-v', '--tb=short'])
        else:
            # Validate category doesn't contain path traversal
            if '..' in category or '/' in category or '\\' in category:
                raise ValueError(f"Invalid category path: {category}")
            base_cmd.extend([f'tests/{category}', '-v', '--tb=short'])
        
        # Add coverage options
        base_cmd.extend([
            f'--cov={settings.TEST_COVERAGE_PATH}',
            '--cov-report=term-missing'
        ])
        
        # Run tests asynchronously
        start_time = datetime.now()
        try:
            process = await asyncio.create_subprocess_exec(
                *base_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=settings.TEST_TIMEOUT_SECONDS
            )
            
            # Decode bytes to strings
            if isinstance(stdout, bytes):
                stdout = stdout.decode('utf-8', errors='ignore')
            if isinstance(stderr, bytes):
                stderr = stderr.decode('utf-8', errors='ignore')
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            output = stdout + stderr
            
        except asyncio.TimeoutError:
            duration = float(settings.TEST_TIMEOUT_SECONDS)
            output = f"Test execution timed out after {settings.TEST_TIMEOUT_SECONDS} seconds"
        
        # Parse test results from output
        passed = failed = skipped = 0
        coverage = 0.0
        
        for line in output.split('\n'):
            # Parse test summary line
            if 'passed' in line or 'failed' in line or 'skipped' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i < len(parts) - 1:
                        next_word = parts[i + 1].replace(',', '').replace(':', '')
                        if next_word == 'passed':
                            passed = int(part)
                        elif next_word == 'failed':
                            failed = int(part)
                        elif next_word == 'skipped':
                            skipped = int(part)
            # Parse coverage from TOTAL line
            elif line.startswith('TOTAL') and '%' in line:
                parts = line.split()
                if len(parts) >= 4:
                    coverage = float(parts[-1].replace('%', ''))
        
        return {
            "category": category,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "coverage": coverage,
            "output": output,
            "duration": duration
        }
        
    except subprocess.TimeoutExpired:
        raise Exception(f"Tests timed out after {settings.TEST_TIMEOUT_SECONDS} seconds")
    except OSError as e:
        logger.error(f"OS error running tests: {e}")
        raise Exception(f"Failed to run tests: {str(e)}")
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise Exception(f"Failed to run tests: {str(e)}")


async def get_test_coverage() -> Dict[str, float]:
    """
    Get current test coverage from cache or by running pytest.
    
    Returns:
        Dict with unit, integration, and overall coverage percentages
    """
    try:
        # Try to get from cache first
        if redis_client:
            cached = redis_client.get("test_coverage")
            if cached:
                return json.loads(cached)
        
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "pytest", "tests/",
            f"--cov={settings.TEST_COVERAGE_PATH}",
            "--cov-report=json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        # Parse coverage JSON if available
        coverage_data = {"unit": 0, "integration": 0, "overall": 0}
        
        try:
            # Try to import aiofiles, fall back to sync if not available
            try:
                import aiofiles
                async with aiofiles.open("coverage.json", "r") as f:
                    content = await f.read()
                    coverage_json = json.loads(content)
                    coverage_data["overall"] = coverage_json.get("totals", {}).get("percent_covered", 0)
            except ImportError:
                # Fallback to sync file reading
                with open("coverage.json", "r") as f:
                    content = f.read()
                    coverage_json = json.loads(content)
                    coverage_data["overall"] = coverage_json.get("totals", {}).get("percent_covered", 0)
        except FileNotFoundError:
            logger.warning("Coverage file not found")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing coverage JSON: {e}")
        except Exception as e:
            logger.error(f"Error reading coverage: {e}")
        
        # Cache the result
        if redis_client:
            redis_client.setex("test_coverage", 300, json.dumps(coverage_data))
        
        return coverage_data
        
    except Exception as e:
        logger.error(f"Error getting coverage: {e}")
        return {"unit": 0, "integration": 0, "overall": 0}


def create_backup(user: Optional[str] = None) -> Dict[str, str]:
    """
    Create a backup of the project.
    
    Args:
        user: Username for audit logging
    
    Returns:
        Dict with filename and message
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"soar_backup_{timestamp}.tar.gz"
        
        # Ensure backups directory exists
        os.makedirs(settings.BACKUP_DIR, exist_ok=True)
        
        # Build backup command securely using helper function
        backup_path = Path(settings.BACKUP_DIR) / backup_filename
        cmd_args = _build_tar_command(backup_path, "create")
        
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=settings.BACKUP_TIMEOUT_SECONDS
        )
        
        if result.returncode != 0:
            raise BackupError(f"Backup failed: {result.stderr}")
        
        # Audit logging
        audit_info = f"backup_name={backup_filename}, user={user or 'unknown'}, timestamp={timestamp}"
        logger.info(f"Backup created successfully: {audit_info}")
        
        return {"filename": backup_filename, "message": "Backup created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise


def list_backups() -> Dict[str, Any]:
    """
    List available backups.
    
    Returns:
        Dict with list of backup information
    """
    try:
        backups_dir = Path(settings.BACKUP_DIR)
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
        raise


def restore_backup(backup_name: str, user: Optional[str] = None) -> Dict[str, str]:
    """
    Restore from a backup file.
    
    Args:
        backup_name: Name of the backup file to restore
        user: Username for audit logging
    
    Returns:
        Dict with message
    """
    try:
        backup_path = Path(settings.BACKUP_DIR) / backup_name
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_name}")
        
        # Restore command securely using helper function
        cmd_args = _build_tar_command(backup_path, "extract")
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=settings.BACKUP_TIMEOUT_SECONDS
        )
        
        if result.returncode != 0:
            raise BackupError(f"Restore failed: {result.stderr}")
        
        # Audit logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audit_info = f"backup_name={backup_name}, user={user or 'unknown'}, timestamp={timestamp}"
        logger.info(f"Backup restored successfully: {audit_info}")
        
        return {"message": f"Backup {backup_name} restored successfully"}
        
    except FileNotFoundError as e:
        logger.error(f"Backup file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise
