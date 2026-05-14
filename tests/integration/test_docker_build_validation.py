#!/usr/bin/env python3
"""
Integration tests for Docker build validation
Validates Dockerfile structure and build configuration without requiring Docker runtime
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')


class TestDockerBuildValidation:
    """Test Docker build configuration and Dockerfile structure"""
    
    def test_apps_api_dockerfile_exists(self):
        """Test that apps/api/Dockerfile exists and has required content"""
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
        dockerfile_path = Path("apps/web-management/Dockerfile")
        assert dockerfile_path.exists(), "apps/web-management/Dockerfile should exist"
        
        content = dockerfile_path.read_text()
        
        # Check for essential Dockerfile instructions
        assert "FROM" in content, "Dockerfile should have FROM instruction"
        assert "WORKDIR" in content or "cd" in content, "Dockerfile should set working directory"
        assert "COPY" in content or "ADD" in content, "Dockerfile should copy files"
        assert "EXPOSE" in content or "CMD" in content or "ENTRYPOINT" in content, "Dockerfile should expose port or define entrypoint"
    
    def test_docker_compose_structure_exists(self):
        """Test that infra/docker/docker-compose.yml exists and has valid structure"""
        compose_path = Path("infra/docker/docker-compose.yml")
        assert compose_path.exists(), "infra/docker/docker-compose.yml should exist"
        
        content = compose_path.read_text()
        
        # Check for essential docker-compose elements
        assert "version:" in content or "services:" in content, "docker-compose.yml should have version or services"
        assert "services:" in content, "docker-compose.yml should define services"
    
    def test_apps_api_entrypoint_exists(self):
        """Test that apps/api/entrypoint.py exists"""
        entrypoint_path = Path("apps/api/entrypoint.py")
        assert entrypoint_path.exists(), "apps/api/entrypoint.py should exist"
        
        content = entrypoint_path.read_text()
        
        # Check for basic Python script structure
        assert "import" in content or "def" in content or "if __name__" in content, "entrypoint.py should be a valid Python script"
    
    def test_apps_web_management_static_files_exist(self):
        """Test that web-management static files exist"""
        required_files = [
            "apps/web-management/index.html",
            "apps/web-management/script.js",
            "apps/web-management/styles.css"
        ]
        
        for file_path in required_files:
            full_path = Path(file_path)
            assert full_path.exists(), f"{file_path} should exist"
            
            content = full_path.read_text()
            assert len(content.strip()) > 0, f"{file_path} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__])
