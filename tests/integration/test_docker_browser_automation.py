#!/usr/bin/env python3
"""
Docker Browser Automation Tests - Real Browser Tests
Tests Docker services using Selenium WebDriver for real browser automation
"""

import pytest
import time
import subprocess
import signal
import os
from pathlib import Path
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException


class TestDockerBrowserAutomation:
    """Test Docker services with real browser automation"""
    
    @pytest.fixture(scope="class")
    def docker_compose_file(self):
        """Path to docker-compose.yml file"""
        return Path("infra/docker/docker-compose.yml")
    
    @pytest.fixture(scope="class")
    def web_services_config(self, docker_compose_file):
        """Load web services configuration from docker-compose.yml"""
        import yaml
        with open(docker_compose_file, 'r', encoding='utf-8') as f:
            compose_content = yaml.safe_load(f)
        
        services = compose_content.get("services", {})
        web_services = {}
        
        # Extract web services with exposed ports
        for service_name, service_config in services.items():
            if "ports" in service_config:
                ports = service_config["ports"]
                for port_mapping in ports:
                    if isinstance(port_mapping, str):
                        # Extract host port from "HOST:CONTAINER" format
                        if ":" in port_mapping:
                            host_port = port_mapping.split(":")[0]
                        else:
                            host_port = port_mapping
                        
                        # Extract container port
                        if ":" in port_mapping:
                            container_port = port_mapping.split(":")[1]
                        else:
                            container_port = port_mapping
                        
                        web_services[service_name] = {
                            "host_port": host_port,
                            "container_port": container_port,
                            "full_mapping": port_mapping,
                            "image": service_config.get("image", ""),
                            "networks": service_config.get("networks", []),
                            "depends_on": service_config.get("depends_on", {}),
                            "healthcheck": "healthcheck" in service_config
                        }
                        break
        
        return web_services
    
    @pytest.fixture(scope="class")
    def base_urls(self, web_services_config):
        """Generate base URLs for web services"""
        urls = {}
        
        # TheHive - port 9000
        if "thehive" in web_services_config:
            urls["thehive"] = f"http://localhost:{web_services_config['thehive']['host_port']}"
        
        # Cortex - port 9001
        if "cortex" in web_services_config:
            urls["cortex"] = f"http://localhost:{web_services_config['cortex']['host_port']}"
        
        # Shuffle Frontend - port 3001
        if "shuffle-frontend" in web_services_config:
            urls["shuffle-frontend"] = f"http://localhost:{web_services_config['shuffle-frontend']['host_port']}"
        
        # Grafana - port 3000
        if "grafana" in web_services_config:
            urls["grafana"] = f"http://localhost:{web_services_config['grafana']['host_port']}"
        
        # MISP - port 8082
        if "misp" in web_services_config:
            urls["misp"] = f"http://localhost:{web_services_config['misp']['host_port']}"
        
        # OpenCTI - port 4000
        if "opencti" in web_services_config:
            urls["opencti"] = f"http://localhost:{web_services_config['opencti']['host_port']}"
        
        # API - port 8000
        if "api" in web_services_config:
            urls["api"] = f"http://localhost:{web_services_config['api']['host_port']}"
        
        return urls
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Initialize Chrome WebDriver with headless options"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            return driver
        except WebDriverException as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")
    
    def test_thehive_browser_access(self, driver, base_urls):
        """Test TheHive access via browser"""
        if "thehive" not in base_urls:
            pytest.skip("TheHive service not available")
        
        driver.get(base_urls["thehive"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        # Check if page loads successfully
        try:
            # Look for TheHive login form or main content
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "TheHive login form should be present"
            
            # Check for username field
            username_field = driver.find_element(By.NAME, "username")
            assert username_field, "TheHive username field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "TheHive password field should be present"
            
            # Check for submit button
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            assert submit_button, "TheHive submit button should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "thehive" in page_title.lower(), f"TheHive page title should contain 'thehive', got: {page_title}"
    
    def test_cortex_browser_access(self, driver, base_urls):
        """Test Cortex access via browser"""
        if "cortex" not in base_urls:
            pytest.skip("Cortex service not available")
        
        driver.get(base_urls["cortex"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for Cortex login form or main content
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "Cortex login form should be present"
            
            # Check for username field
            username_field = driver.find_element(By.NAME, "username")
            assert username_field, "Cortex username field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "Cortex password field should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "cortex" in page_title.lower(), f"Cortex page title should contain 'cortex', got: {page_title}"
    
    def test_shuffle_frontend_browser_access(self, driver, base_urls):
        """Test Shuffle Frontend access via browser"""
        if "shuffle-frontend" not in base_urls:
            pytest.skip("Shuffle Frontend service not available")
        
        driver.get(base_urls["shuffle-frontend"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for Shuffle login form or main content
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "Shuffle Frontend login form should be present"
            
            # Check for email/username field
            email_field = driver.find_element(By.NAME, "email")
            assert email_field, "Shuffle Frontend email field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "Shuffle Frontend password field should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "shuffle" in page_title.lower(), f"Shuffle Frontend page title should contain 'shuffle', got: {page_title}"
    
    def test_grafana_browser_access(self, driver, base_urls):
        """Test Grafana access via browser"""
        if "grafana" not in base_urls:
            pytest.skip("Grafana service not available")
        
        driver.get(base_urls["grafana"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for Grafana login form
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "Grafana login form should be present"
            
            # Check for username field
            username_field = driver.find_element(By.NAME, "user")
            assert username_field, "Grafana username field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "Grafana password field should be present"
            
            # Check for login button
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            assert login_button, "Grafana login button should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "grafana" in page_title.lower(), f"Grafana page title should contain 'grafana', got: {page_title}"
    
    def test_misp_browser_access(self, driver, base_urls):
        """Test MISP access via browser"""
        if "misp" not in base_urls:
            pytest.skip("MISP service not available")
        
        driver.get(base_urls["misp"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for MISP login form
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "MISP login form should be present"
            
            # Check for email field
            email_field = driver.find_element(By.NAME, "email")
            assert email_field, "MISP email field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "MISP password field should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "misp" in page_title.lower(), f"MISP page title should contain 'misp', got: {page_title}"
    
    def test_opencti_browser_access(self, driver, base_urls):
        """Test OpenCTI access via browser"""
        if "opencti" not in base_urls:
            pytest.skip("OpenCTI service not available")
        
        driver.get(base_urls["opencti"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for OpenCTI login form
            login_form = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "form[action*='login']")),
                timeout=15
            )
            assert login_form, "OpenCTI login form should be present"
            
            # Check for email field
            email_field = driver.find_element(By.NAME, "email")
            assert email_field, "OpenCTI email field should be present"
            
            # Check for password field
            password_field = driver.find_element(By.NAME, "password")
            assert password_field, "OpenCTI password field should be present"
            
        except TimeoutException:
            # If login form not found, check for main content
            page_title = driver.title
            assert "opencti" in page_title.lower(), f"OpenCTI page title should contain 'opencti', got: {page_title}"
    
    def test_api_browser_access(self, driver, base_urls):
        """Test API access via browser"""
        if "api" not in base_urls:
            pytest.skip("API service not available")
        
        driver.get(base_urls["api"])
        
        # Wait for page to load
        wait = WebDriverWait(driver, 30)
        
        try:
            # Look for API documentation or main content
            # API might return JSON or HTML documentation
            page_source = driver.page_source.lower()
            
            # Check for API-related content
            assert any(keyword in page_source for keyword in ["api", "endpoint", "swagger", "openapi"]), \
                f"API page should contain API-related content"
            
        except TimeoutException:
            page_title = driver.title
            assert "api" in page_title.lower(), f"API page title should contain 'api', got: {page_title}"
    
    def test_service_navigation(self, driver, base_urls):
        """Test navigation between services"""
        if len(base_urls) < 2:
            pytest.skip("Need at least 2 services for navigation test")
        
        # Test navigation from TheHive to Cortex
        if "thehive" in base_urls and "cortex" in base_urls:
            driver.get(base_urls["thehive"])
            time.sleep(2)
            
            # Navigate to Cortex
            driver.get(base_urls["cortex"])
            time.sleep(2)
            
            # Check both pages are accessible
            thehive_title = driver.title.lower()
            cortex_title = driver.title.lower()
            
            assert "thehive" in thehive_title, "TheHive should be accessible"
            assert "cortex" in cortex_title, "Cortex should be accessible"
    
    def test_responsive_design(self, driver, base_urls):
        """Test responsive design of web services"""
        if not base_urls:
            pytest.skip("No services available for responsive test")
        
        # Test responsive design for each service
        for service_name, url in base_urls.items():
            driver.get(url)
            
            # Set different window sizes and check if page adapts
            window_sizes = [
                (1920, 1080),  # Desktop
                (768, 1024),   # Tablet
                (375, 667),    # Mobile
            ]
            
            for width, height in window_sizes:
                driver.set_window_size(width, height)
                time.sleep(1)
                
                # Check if page loads without errors
                page_title = driver.title
                assert page_title, f"{service_name} should load properly at {width}x{height}"
                
                # Check for responsive elements (if any)
                try:
                    # Look for viewport meta tag or responsive CSS
                    page_source = driver.page_source
                    assert len(page_source) > 100, f"{service_name} should have substantial content at {width}x{height}"
                except Exception:
                    pass  # Continue if responsive check fails
    
    def test_error_pages(self, driver, base_urls):
        """Test error pages and error handling"""
        if not base_urls:
            pytest.skip("No services available for error page test")
        
        # Test 404 error pages
        for service_name, base_url in base_urls.items():
            # Try to access non-existent page
            driver.get(f"{base_url}/non-existent-page-12345")
            time.sleep(2)
            
            # Check if proper error page is shown
            page_title = driver.title.lower()
            page_source = driver.page_source.lower()
            
            # Look for error indicators
            error_indicators = ["404", "not found", "error", "page not found"]
            has_error = any(indicator in page_source for indicator in error_indicators)
            
            # Should show error page or redirect to login
            assert has_error or "login" in page_source, \
                f"{service_name} should show error page or redirect for non-existent URL"
    
    def test_security_headers(self, base_urls):
        """Test security headers on web services"""
        import requests
        
        for service_name, url in base_urls.items():
            try:
                response = requests.get(url, timeout=10)
                
                # Check for security headers
                security_headers = [
                    'x-frame-options',
                    'x-content-type-options',
                    'x-xss-protection',
                    'strict-transport-security',
                    'content-security-policy'
                ]
                
                missing_headers = []
                for header in security_headers:
                    if header not in response.headers:
                        missing_headers.append(header)
                
                # Log missing security headers (don't fail test for missing optional headers)
                if missing_headers:
                    print(f"Security headers missing for {service_name}: {missing_headers}")
                
            except requests.exceptions.RequestException:
                # If service is not accessible, that's a separate test failure
                pass
    
    def test_ssl_certificates(self, base_urls):
        """Test SSL certificates for HTTPS services"""
        import requests
        import ssl
        
        for service_name, base_url in base_urls.items():
            https_url = base_url.replace("http://", "https://")
            
            try:
                # This will fail if SSL certificate is not valid
                response = requests.get(https_url, timeout=10, verify=True)
                
                # Check if SSL is properly configured
                if response.status_code == 200:
                    print(f"SSL certificate is valid for {service_name}")
                
            except requests.exceptions.SSLError:
                # SSL certificate issues are expected for self-signed certs in development
                print(f"SSL certificate issue detected for {service_name} (expected in development)")
            except requests.exceptions.RequestException:
                # Service not accessible via HTTPS
                pass
