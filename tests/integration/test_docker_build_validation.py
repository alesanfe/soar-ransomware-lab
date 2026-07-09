#!/usr/bin/env python3
"""
Integration tests for Docker build validation
Validates Dockerfile structure and build configuration without requiring Docker runtime
"""

import os
import pytest
from pathlib import Path


class TestDockerBuildValidation:
    """Test Docker build configuration and Dockerfile structure"""

    def test_apps_api_dockerfile_exists(self):
        """Test that apps/api/Dockerfile exists and has required content"""
        # Skip when running inside container unless Dockerfiles are available
        if os.path.exists('/.dockerenv') and not Path("apps/api/Dockerfile").exists():
            pytest.skip("Dockerfiles not available inside container")
        dockerfile_path = Path("apps/api/Dockerfile")
        assert dockerfile_path.exists(), "apps/api/Dockerfile should exist"

        content = dockerfile_path.read_text()

        # Check for essential Dockerfile instructions
        assert "FROM" in content, "Dockerfile should have FROM instruction"
        assert "WORKDIR" in content or "cd" in content, "Dockerfile should set working directory"
        assert "COPY" in content or "ADD" in content, "Dockerfile should copy files"
        assert "EXPOSE" in content or "CMD" in content or "ENTRYPOINT" in content, "Dockerfile should expose port or define entrypoint"

    def test_apps_docs_site_dockerfile_exists(self):
        """Test that apps/docs-site/Dockerfile exists and has required content"""
        # Skip when running inside container unless Dockerfiles are available
        if os.path.exists('/.dockerenv') and not Path("apps/docs-site/Dockerfile").exists():
            pytest.skip("Dockerfiles not available inside container")
        dockerfile_path = Path("apps/docs-site/Dockerfile")
        assert dockerfile_path.exists(), "apps/docs-site/Dockerfile should exist"

        content = dockerfile_path.read_text()

        # Check for essential Dockerfile instructions
        assert "FROM" in content, "Dockerfile should have FROM instruction"
        assert "WORKDIR" in content or "cd" in content, "Dockerfile should set working directory"
        assert "COPY" in content or "ADD" in content, "Dockerfile should copy files"
        assert "EXPOSE" in content or "CMD" in content or "ENTRYPOINT" in content, "Dockerfile should expose port or define entrypoint"

    def test_apps_web_management_dockerfile_exists(self):
        """Test that apps/web-management/Dockerfile exists and has required content"""
        # Skip when running inside container unless Dockerfiles are available
        if os.path.exists('/.dockerenv') and not Path("apps/web-management/Dockerfile").exists():
            pytest.skip("Dockerfiles not available inside container")
        dockerfile_path = Path("apps/web-management/Dockerfile")
        assert dockerfile_path.exists(), "apps/web-management/Dockerfile should exist"

        content = dockerfile_path.read_text()

        # Check for essential Dockerfile instructions
        assert "FROM" in content, "Dockerfile should have FROM instruction"
        # Nginx-based Dockerfiles may not need WORKDIR
        assert "COPY" in content or "ADD" in content, "Dockerfile should copy files"
        assert "EXPOSE" in content or "CMD" in content or "ENTRYPOINT" in content, "Dockerfile should expose port or define entrypoint"

    def test_docker_compose_structure_exists(self):
        """Test that infra/docker/compose/docker-compose.yml exists and has valid structure"""
        # Skip when running inside container unless compose files are available
        if os.path.exists('/.dockerenv') and not Path("infra/docker/compose/docker-compose.yml").exists():
            pytest.skip("Docker compose files not available inside container")
        compose_path = Path("infra/docker/compose/docker-compose.yml")
        assert compose_path.exists(), "infra/docker/compose/docker-compose.yml should exist"

        content = compose_path.read_text()

        # Check for essential docker-compose elements
        assert "version:" in content or "services:" in content, "docker-compose.yml should have version or services"
        assert "services:" in content, "docker-compose.yml should define services"

    def test_apps_api_main_exists(self):
        """Test that src/soar_lab/api/main.py (canonical API entrypoint) exists"""
        main_path = Path("src/soar_lab/api/main.py")
        assert main_path.exists(), "src/soar_lab/api/main.py should exist"

        content = main_path.read_text()

        # Check for FastAPI app definition
        assert "app" in content and "FastAPI" in content, "main.py should define a FastAPI app"

    def test_apps_web_management_static_files_exist(self):
        """Test that web-management static files exist"""
        # Skip when running inside container unless static files are available
        if os.path.exists('/.dockerenv') and not Path("apps/web-management/index.html").exists():
            pytest.skip("Static files not available inside container")
        required_files = [
            "apps/web-management/index.html",
            "apps/web-management/script.js",
            "apps/web-management/styles.css"
        ]

        for file_path in required_files:
            full_path = Path(file_path)
            assert full_path.exists(), f"{file_path} should exist"

            # Read with UTF-8 encoding to handle potential encoding issues
            try:
                content = full_path.read_text(encoding='utf-8')
                assert len(content.strip()) > 0, f"{file_path} should not be empty"
            except UnicodeDecodeError:
                # If file is binary or has encoding issues, just check it exists and has size
                assert full_path.stat().st_size > 0, f"{file_path} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__])
