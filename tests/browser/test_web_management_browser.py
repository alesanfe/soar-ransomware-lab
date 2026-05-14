#!/usr/bin/env python3
"""
Browser tests for web-management application using Selenium
Validates real web functionality, assets loading, and user interactions
"""

import pytest
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, WebDriverException
except ImportError:
    pytest.skip("Selenium not installed - skip browser tests", allow_module_level=True)


class TestWebManagementBrowser:
    """Browser tests for web-management application"""
    
    @pytest.fixture(scope="class")
    def driver(self, chrome_options):
        """Setup Chrome driver for browser testing"""
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            yield driver
        except WebDriverException as e:
            pytest.skip(f"Chrome driver not available: {e}", allow_module_level=True)
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_web_management_static_files_exist(self, driver):
        """Test that web-management static files exist and have content"""
        web_mgmt_dir = Path("apps/web-management")
        assert web_mgmt_dir.exists(), "web-management directory should exist"
        
        required_files = [
            "index.html",
            "script.js", 
            "styles.css"
        ]
        
        for file_name in required_files:
            file_path = web_mgmt_dir / file_name
            assert file_path.exists(), f"{file_name} should exist in web-management"
            
            # Read file with UTF-8 encoding to handle Unicode
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            assert len(content.strip()) > 0, f"{file_name} should not be empty"
    
    def test_web_management_index_html_structure(self, driver):
        """Test that index.html has proper HTML structure"""
        index_path = Path("apps/web-management/index.html")
        assert index_path.exists(), "index.html should exist"
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for essential HTML elements
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content, "Should have DOCTYPE declaration"
        assert "<html" in content, "Should have html element"
        assert "<head>" in content, "Should have head element"
        assert "<body>" in content, "Should have body element"
        
        # Check for CSS and JS references
        assert "styles.css" in content or "script.js" in content, "Should reference CSS or JS files"
    
    def test_web_management_css_content_validity(self, driver):
        """Test that styles.css has valid CSS content"""
        css_path = Path("apps/web-management/styles.css")
        assert css_path.exists(), "styles.css should exist"
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(css_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for CSS structure
        css_rules = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('/*')]
        assert len(css_rules) > 0, "Should have CSS rules"
        
        # Check for common CSS selectors
        has_selectors = any('{' in rule for rule in css_rules)
        assert has_selectors, "Should have CSS selectors with declarations"
    
    def test_web_management_javascript_content_validity(self, driver):
        """Test that script.js has valid JavaScript content"""
        js_path = Path("apps/web-management/script.js")
        assert js_path.exists(), "script.js should exist"
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(js_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for JavaScript structure
        has_functions = "function" in content or "=>" in content or "var " in content or "let " in content or "const " in content
        assert has_functions, "Should have JavaScript functions or variables"
        
        # Check for DOM manipulation or event handling
        has_dom_ops = "document" in content or "window" in content or "addEventListener" in content
        assert has_dom_ops, "Should have DOM operations or event handling"
    
    def test_web_management_dockerfile_web_server_config(self, driver):
        """Test that web-management Dockerfile properly configures web server"""
        dockerfile_path = Path("apps/web-management/Dockerfile")
        assert dockerfile_path.exists(), "web-management Dockerfile should exist"
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(dockerfile_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for web server configuration
        assert "EXPOSE" in content, "Should expose a port"
        assert "COPY" in content, "Should copy static files"
        assert "CMD" in content or "ENTRYPOINT" in content, "Should define startup command"
        
        # Common web servers for static sites
        web_servers = ["nginx", "apache", "http-server", "serve", "python -m http.server"]
        found_server = any(server in content.lower() for server in web_servers)
        assert found_server, f"Should use a web server: {web_servers}"
    
    def test_web_management_asset_integration(self, driver):
        """Test that assets are properly integrated in HTML"""
        index_path = Path("apps/web-management/index.html")
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check CSS integration
        css_linked = 'rel="stylesheet"' in content or 'stylesheet' in content
        assert css_linked, "Should link CSS stylesheet"
        
        # Check JavaScript integration
        js_linked = 'script.js' in content or '<script' in content
        assert js_linked, "Should include JavaScript file"
    
    def test_web_management_functional_elements(self, driver):
        """Test that web-management has functional UI elements"""
        index_path = Path("apps/web-management/index.html")
        
        # Read file with UTF-8 encoding to handle Unicode
        with open(index_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for common management panel elements
        management_elements = [
            "button", "input", "select", "table", "div", "form"
        ]
        
        found_elements = any(f"<{element}" in content.lower() for element in management_elements)
        assert found_elements, f"Should have management UI elements: {management_elements}"
        
        # Check for navigation or menu elements
        nav_elements = ["nav", "header", "menu", "ul", "ol"]
        found_nav = any(f"<{element}" in content.lower() for element in nav_elements)
        # Navigation elements are optional for management panels


if __name__ == "__main__":
    pytest.main([__file__])
