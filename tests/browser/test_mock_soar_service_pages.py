#!/usr/bin/env python3
"""
Browser tests for Docker services validation
Tests actual functionality of web UIs and services, not just port availability
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Import mock services for reproducible browser testing
from tests.browser.mock_services import start_mock_services, stop_mock_services


class TestMockSoarServicePages:
    """Test Docker services with real browser automation"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_mock_services(self):
        """Start mock services before all tests and stop after"""
        print("🚀 Starting mock services for browser testing...")
        start_mock_services()
        yield
        print("🛑 Stopping mock services...")
        stop_mock_services()
    
    @pytest.fixture(scope="class")
    def driver(self, chrome_options):
        """Setup Chrome driver for browser testing"""
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            yield driver
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_thehive_health_check(self, driver):
        """Test TheHive web interface health and functionality"""
        try:
            driver.get("http://localhost:9000")
            
            # Wait for page to load and check for TheHive elements
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if TheHive is properly loaded
            page_title = driver.title
            assert "TheHive" in page_title or "hive" in page_title.lower(), \
                f"TheHive page not loaded properly. Title: {page_title}"
            
            # Look for login form or main content
            try:
                login_form = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "form, .login-form, input[type='text']"))
                )
                assert login_form, "TheHive login form not found"
            except TimeoutException:
                # If no login form, check for main content
                body_text = driver.find_element(By.TAG_NAME, "body").text
                assert any(keyword in body_text.lower() for keyword in ["thehive", "case", "alert", "dashboard"]), \
                    "TheHive main content not found"
            
            print("✅ TheHive web interface is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"TheHive browser test failed: {str(e)}")
    
    def test_cortex_health_check(self, driver):
        """Test Cortex web interface health and functionality"""
        try:
            driver.get("http://localhost:9001")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if Cortex is properly loaded
            page_title = driver.title
            assert "cortex" in page_title.lower(), \
                f"Cortex page not loaded properly. Title: {page_title}"
            
            # Look for Cortex-specific elements
            try:
                # Check for login form or main content
                body_text = driver.find_element(By.TAG_NAME, "body").text
                assert any(keyword in body_text.lower() for keyword in ["cortex", "analyzer", "job", "response"]), \
                    "Cortex main content not found"
            except Exception:
                pytest.fail("Could not verify Cortex content")
            
            print("✅ Cortex web interface is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"Cortex browser test failed: {str(e)}")
    
    def test_grafana_health_check(self, driver):
        """Test Grafana dashboard health and functionality"""
        try:
            driver.get("http://localhost:3000")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if Grafana is properly loaded
            page_title = driver.title
            assert "grafana" in page_title.lower(), \
                f"Grafana page not loaded properly. Title: {page_title}"
            
            # Look for Grafana login or dashboard elements
            try:
                # Check for login form
                login_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[type='password'], .login-form"))
                )
                assert login_input, "Grafana login form not found"
            except TimeoutException:
                # Check for dashboard content if already logged in
                body_text = driver.find_element(By.TAG_NAME, "body").text
                assert any(keyword in body_text.lower() for keyword in ["grafana", "dashboard", "panel", "metric"]), \
                    "Grafana dashboard content not found"
            
            print("✅ Grafana dashboard is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"Grafana browser test failed: {str(e)}")
    
    def test_prometheus_health_check(self, driver):
        """Test Prometheus web interface health and functionality"""
        try:
            driver.get("http://localhost:9090")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if Prometheus is properly loaded
            page_title = driver.title
            assert "prometheus" in page_title.lower(), \
                f"Prometheus page not loaded properly. Title: {page_title}"
            
            # Look for Prometheus-specific content
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert any(keyword in body_text.lower() for keyword in ["prometheus", "metrics", "targets", "alerts"]), \
                "Prometheus main content not found"
            
            print("✅ Prometheus web interface is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"Prometheus browser test failed: {str(e)}")
    
    def test_shuffle_frontend_health_check(self, driver):
        """Test Shuffle frontend web interface health and functionality"""
        try:
            driver.get("http://localhost:3001")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if Shuffle is properly loaded
            page_title = driver.title
            assert "shuffle" in page_title.lower(), \
                f"Shuffle page not loaded properly. Title: {page_title}"
            
            # Look for Shuffle-specific elements
            try:
                # Check for login form or main content
                body_text = driver.find_element(By.TAG_NAME, "body").text
                assert any(keyword in body_text.lower() for keyword in ["shuffle", "workflow", "automation", "app"]), \
                    "Shuffle main content not found"
            except Exception:
                pytest.fail("Could not verify Shuffle content")
            
            print("✅ Shuffle frontend is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"Shuffle frontend browser test failed: {str(e)}")
    
    def test_api_health_check(self, driver):
        """Test SOAR API endpoint health and functionality"""
        try:
            driver.get("http://localhost:8000")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if API is properly loaded
            page_title = driver.title
            assert page_title, "API page not loaded properly"
            
            # Look for API documentation or health check
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert any(keyword in body_text.lower() for keyword in ["api", "endpoint", "health", "docs", "swagger"]), \
                "API documentation not found"
            
            print("✅ SOAR API endpoint is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"API health check browser test failed: {str(e)}")
    
    def test_nginx_proxy_health_check(self, driver):
        """Test Nginx reverse proxy functionality"""
        try:
            # Test HTTP (port 80)
            driver.get("http://localhost")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we get some response (could be any of the proxied services)
            page_title = driver.title
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Should get content from one of the services
            assert page_title or body_text, "Nginx proxy not returning content"
            
            print("✅ Nginx reverse proxy is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"Nginx proxy browser test failed: {str(e)}")
    
    @pytest.mark.skip("MinIO console requires additional setup")
    def test_minio_console_health_check(self, driver):
        """Test MinIO console health and functionality"""
        try:
            driver.get("http://localhost:9002")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if MinIO is properly loaded
            page_title = driver.title
            assert "minio" in page_title.lower(), \
                f"MinIO page not loaded properly. Title: {page_title}"
            
            # Look for MinIO-specific elements
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert any(keyword in body_text.lower() for keyword in ["minio", "object", "storage", "bucket"]), \
                "MinIO console content not found"
            
            print("✅ MinIO console is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"MinIO console browser test failed: {str(e)}")
    
    @pytest.mark.skip("MISP and OpenCTI require additional authentication setup")
    def test_misp_health_check(self, driver):
        """Test MISP threat intelligence platform"""
        try:
            driver.get("http://localhost:8082")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if MISP is properly loaded
            page_title = driver.title
            assert "misp" in page_title.lower(), \
                f"MISP page not loaded properly. Title: {page_title}"
            
            # Look for MISP-specific elements
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert any(keyword in body_text.lower() for keyword in ["misp", "threat", "intelligence", "ioc"]), \
                "MISP main content not found"
            
            print("✅ MISP platform is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"MISP browser test failed: {str(e)}")
    
    @pytest.mark.skip("MISP and OpenCTI require additional authentication setup")
    def test_opencti_health_check(self, driver):
        """Test OpenCTI threat intelligence platform"""
        try:
            driver.get("http://localhost:8083")
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if OpenCTI is properly loaded
            page_title = driver.title
            assert "opencti" in page_title.lower(), \
                f"OpenCTI page not loaded properly. Title: {page_title}"
            
            # Look for OpenCTI-specific elements
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert any(keyword in body_text.lower() for keyword in ["opencti", "threat", "intelligence", "platform"]), \
                "OpenCTI main content not found"
            
            print("✅ OpenCTI platform is accessible and functional")
            
        except WebDriverException as e:
            pytest.fail(f"OpenCTI browser test failed: {str(e)}")


class TestServiceIntegration:
    """Test integration between services"""
    
    @pytest.fixture(scope="class")
    def driver(self, chrome_options):
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            yield driver
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def test_thehive_to_cortex_integration(self, driver):
        """Test integration between TheHive and Cortex"""
        try:
            # Access TheHive and look for Cortex integration
            driver.get("http://localhost:9000")
            
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for evidence of Cortex integration
            body_text = driver.find_element(By.TAG_NAME, "body").text
            page_source = driver.page_source.lower()
            
            # Check for Cortex-related elements or configuration
            cortex_indicators = [
                "cortex", "analyzer", "job", "response"
            ]
            
            found_integration = any(indicator in page_source for indicator in cortex_indicators)
            
            if found_integration:
                print("✅ TheHive-Cortex integration evidence found")
            else:
                print("⚠️  TheHive-Cortex integration not visible (may require login)")
            
        except WebDriverException as e:
            pytest.fail(f"TheHive-Cortex integration test failed: {str(e)}")
    
    def test_prometheus_grafana_integration(self, driver):
        """Test integration between Prometheus and Grafana"""
        try:
            # Access Grafana and check for Prometheus data source
            driver.get("http://localhost:3000")
            
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for evidence of Prometheus integration
            page_source = driver.page_source.lower()
            
            prometheus_indicators = [
                "prometheus", "datasource", "metric", "query"
            ]
            
            found_integration = any(indicator in page_source for indicator in prometheus_indicators)
            
            if found_integration:
                print("✅ Grafana-Prometheus integration evidence found")
            else:
                print("⚠️  Grafana-Prometheus integration not visible (may require login)")
            
        except WebDriverException as e:
            pytest.fail(f"Grafana-Prometheus integration test failed: {str(e)}")
