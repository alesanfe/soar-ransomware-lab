"""Shared cleanup helpers for E2E tests."""

import subprocess

__all__ = [
    "remove_docker_volumes",
    "remove_docker_networks",
    "remove_test_artifacts",
    "cleanup_test_resources",
]


def remove_docker_volumes(volume_prefix: str) -> bool:
    """Remove Docker volumes with a given prefix.

    Args:
        volume_prefix: Prefix of volumes to remove (e.g., "soar")

    Returns:
        True if volumes were removed, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "volume", "ls", "-q"], capture_output=True, text=True, timeout=10
        )
        volumes = result.stdout.strip().split("\n") if result.stdout.strip() else []

        matching_volumes = [v for v in volumes if v.startswith(volume_prefix)]

        for volume in matching_volumes:
            subprocess.run(
                ["docker", "volume", "rm", "-f", volume], capture_output=True, timeout=10
            )

        return True
    except Exception:
        return False


def remove_docker_networks(network_prefix: str) -> bool:
    """Remove Docker networks with a given prefix.

    Args:
        network_prefix: Prefix of networks to remove (e.g., "soar")

    Returns:
        True if networks were removed, False otherwise
    """
    try:
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        networks = result.stdout.strip().split("\n") if result.stdout.strip() else []

        matching_networks = [n for n in networks if n.startswith(network_prefix)]

        for network in matching_networks:
            subprocess.run(["docker", "network", "rm", network], capture_output=True, timeout=10)

        return True
    except Exception:
        return False


def remove_test_artifacts(artifact_dirs: list[str]) -> bool:
    """Remove test artifact directories.

    Args:
        artifact_dirs: List of directory paths to remove

    Returns:
        True if artifacts were removed, False otherwise
    """
    try:
        import shutil

        for dir_path in artifact_dirs:
            if dir_path.exists():
                shutil.rmtree(dir_path, ignore_errors=True)
        return True
    except Exception:
        return False


def cleanup_test_resources(
    volume_prefix: str = "soar",
    network_prefix: str = "soar",
    artifact_dirs: list[str] | None = None,
) -> bool:
    """Comprehensive cleanup of test resources.

    Args:
        volume_prefix: Prefix of volumes to remove
        network_prefix: Prefix of networks to remove
        artifact_dirs: List of artifact directories to remove

    Returns:
        True if cleanup was successful, False otherwise
    """
    from pathlib import Path

    if artifact_dirs is None:
        artifact_dirs = []

    artifact_paths = [Path(d) for d in artifact_dirs]

    success = True
    success &= remove_docker_volumes(volume_prefix)
    success &= remove_docker_networks(network_prefix)
    success &= remove_test_artifacts(artifact_paths)

    return success
