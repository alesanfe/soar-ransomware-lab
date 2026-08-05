"""
Shared Docker control helpers for E2E tests.
"""

import subprocess
import time
from typing import List, Optional


def get_container_status(container_name: str) -> str:
    """
    Get the status of a Docker container.

    Args:
        container_name: Name of the container

    Returns:
        Container status (running, exited, etc.)
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception:
        return "error"


def stop_container(container_name: str, timeout: int = 30) -> bool:
    """
    Stop a Docker container.

    Args:
        container_name: Name of the container
        timeout: Timeout in seconds

    Returns:
        True if container was stopped, False otherwise
    """
    try:
        subprocess.run(
            ["docker", "stop", container_name],
            capture_output=True,
            timeout=timeout
        )
        return True
    except Exception:
        return False


def start_container(container_name: str, timeout: int = 30) -> bool:
    """
    Start a Docker container.

    Args:
        container_name: Name of the container
        timeout: Timeout in seconds

    Returns:
        True if container was started, False otherwise
    """
    try:
        subprocess.run(
            ["docker", "start", container_name],
            capture_output=True,
            timeout=timeout
        )
        return True
    except Exception:
        return False


def restart_container(container_name: str, timeout: int = 60) -> bool:
    """
    Restart a Docker container.

    Args:
        container_name: Name of the container
        timeout: Timeout in seconds

    Returns:
        True if container was restarted, False otherwise
    """
    try:
        subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            timeout=timeout
        )
        return True
    except Exception:
        return False


def get_container_logs(container_name: str, tail: int = 100) -> str:
    """
    Get logs from a Docker container.

    Args:
        container_name: Name of the container
        tail: Number of lines to get from the end

    Returns:
        Container logs as string
    """
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout
    except Exception:
        return ""


def list_containers(filter_label: Optional[str] = None) -> List[str]:
    """
    List Docker containers, optionally filtered by label.

    Args:
        filter_label: Optional label filter (e.g., "com.docker.compose.project=soar")

    Returns:
        List of container names
    """
    try:
        cmd = ["docker", "ps", "--format", "{{.Names}}"]
        if filter_label:
            cmd.extend(["--filter", f"label={filter_label}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        return []


def wait_for_container(container_name: str, timeout: int = 60) -> bool:
    """
    Wait for a container to be running.

    Args:
        container_name: Name of the container
        timeout: Timeout in seconds

    Returns:
        True if container is running, False otherwise
    """
    start = time.time()
    while time.time() - start < timeout:
        if get_container_status(container_name) == "running":
            return True
        time.sleep(1)
    return False
