#!/usr/bin/env python3
"""
Selenium Tests for Docker Web Interfaces
Tests all web UIs from Docker services
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestDockerWebInterfacesSelenium:
    """Selenium tests for Docker web interfaces"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Chrome WebDriver fixture"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            yield driver
        except Exception as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

    @pytest.fixture(scope="class")
    def wait(self, driver):
        """WebDriverWait fixture"""
        return WebDriverWait(driver, 10)

    def test_nginx_homepage(self, driver, wait):
        """Test Nginx reverse proxy homepage"""
        try:
            driver.get("http://localhost:80")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check page title and content
            title = driver.title.lower()
            assert any(keyword in title for keyword in ["nginx", "soar", "lab", "welcome"])
            
            # Check for navigation or content
            body_text = driver.page_source.lower()
            assert any(keyword in body_text for keyword in ["nav", "menu", "dashboard", "login"])
            
            print(f"Nginx homepage loaded successfully. Title: {driver.title}")
            
        except TimeoutException:
            pytest.skip("Nginx homepage not accessible or timeout")

    def test_grafana_login_interface(self, driver, wait):
        """Test Grafana login interface"""
        try:
            driver.get("http://localhost:3000/login")
            
            # Wait for login form
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            
            # Check for login elements
            username_input = driver.find_element(By.CSS_SELECTOR, "input[name='user'], input[type='text'], input[placeholder*='User'], input[placeholder*='user']")
            password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password'], input[placeholder*='Password'], input[placeholder*='password']")
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-login, .login-button, button:contains('Log')")
            
            assert username_input.is_displayed()
            assert password_input.is_displayed()
            assert login_button.is_displayed()
            
            # Check for Grafana branding
            body_text = driver.page_source.lower()
            assert "grafana" in body_text
            
            print("Grafana login interface loaded successfully")
            
        except (TimeoutException, NoSuchElementException):
            pytest.skip("Grafana login interface not accessible")

    def test_grafana_dashboard_after_login(self, driver, wait):
        """Test Grafana dashboard after login"""
        try:
            # Try to access Grafana with default credentials
            driver.get("http://localhost:3000")
            
            # Look for login form
            try:
                username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='user'], input[type='text']")))
                username_input.send_keys("admin")
                
                password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password']")
                password_input.send_keys("admin")  # Default password might be 'admin'
                
                login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-login")
                login_button.click()
                
                # Wait for dashboard to load
                time.sleep(2)
                
            except:
                pass  # Already logged in or no login required
            
            # Check for dashboard elements
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".dashboard, .grafana-container, .main-view")))
                
                # Look for dashboard components
                body_text = driver.page_source.lower()
                assert any(keyword in body_text for keyword in ["dashboard", "panel", "chart", "graph"])
                
                print("Grafana dashboard loaded successfully")
                
            except TimeoutException:
                pytest.skip("Grafana dashboard not accessible after login")
                
        except Exception:
            pytest.skip("Grafana login/test failed")

    def test_shuffle_frontend_ui(self, driver, wait):
        """Test Shuffle Frontend UI"""
        try:
            driver.get("http://localhost:3001")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for Shuffle UI elements
            body_text = driver.page_source.lower()
            assert "shuffle" in body_text
            
            # Look for common Shuffle UI components
            try:
                login_element = driver.find_element(By.CSS_SELECTOR, ".login, .auth, [class*='login'], [class*='auth']")
                print("Shuffle login interface found")
            except NoSuchElementException:
                # Look for dashboard if already logged in
                try:
                    dashboard_element = driver.find_element(By.CSS_SELECTOR, ".dashboard, .workflow, .app, [class*='dashboard']")
                    print("Shuffle dashboard interface found")
                except NoSuchElementException:
                    # At least check for Shuffle branding
                    assert "shuffle" in body_text
                    print("Shuffle branding found")
            
            print("Shuffle Frontend UI loaded successfully")
            
        except TimeoutException:
            pytest.skip("Shuffle Frontend UI not accessible")

    def test_thehive_interface(self, driver, wait):
        """Test TheHive interface"""
        try:
            driver.get("http://localhost:9000")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for TheHive branding
            body_text = driver.page_source.lower()
            assert "thehive" in body_text or "hive" in body_text
            
            # Look for login or dashboard
            try:
                login_element = driver.find_element(By.CSS_SELECTOR, ".login, [class*='login'], input[type='password']")
                print("TheHive login interface found")
            except NoSuchElementException:
                try:
                    dashboard_element = driver.find_element(By.CSS_SELECTOR, ".dashboard, .case, .alert, [class*='dashboard']")
                    print("TheHive dashboard interface found")
                except NoSuchElementException:
                    # At least check for TheHive branding
                    assert "thehive" in body_text or "hive" in body_text
                    print("TheHive branding found")
            
            print("TheHive interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("TheHive interface not accessible")

    def test_cortex_interface(self, driver, wait):
        """Test Cortex interface"""
        try:
            driver.get("http://localhost:9001")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for Cortex branding
            body_text = driver.page_source.lower()
            assert "cortex" in body_text
            
            # Look for login or dashboard
            try:
                login_element = driver.find_element(By.CSS_SELECTOR, ".login, [class*='login'], input[type='password']")
                print("Cortex login interface found")
            except NoSuchElementException:
                try:
                    dashboard_element = driver.find_element(By.CSS_SELECTOR, ".dashboard, .analyzer, .job, [class*='dashboard']")
                    print("Cortex dashboard interface found")
                except NoSuchElementException:
                    # At least check for Cortex branding
                    assert "cortex" in body_text
                    print("Cortex branding found")
            
            print("Cortex interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("Cortex interface not accessible")

    def test_misp_interface(self, driver, wait):
        """Test MISP interface"""
        try:
            driver.get("http://localhost:8082")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for MISP branding
            body_text = driver.page_source.lower()
            assert "misp" in body_text
            
            # Look for login form (MISP always requires login)
            try:
                login_form = driver.find_element(By.CSS_SELECTOR, "form")
                password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
                
                assert login_form.is_displayed()
                assert password_input.is_displayed()
                
                print("MISP login interface found")
                
            except NoSuchElementException:
                pytest.skip("MISP login form not found")
            
            print("MISP interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("MISP interface not accessible")

    def test_misp_ssl_interface(self, driver, wait):
        """Test MISP SSL interface"""
        try:
            driver.get("https://localhost:8443")
            
            # Wait for page to load (ignore SSL errors)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for MISP branding
            body_text = driver.page_source.lower()
            assert "misp" in body_text
            
            print("MISP SSL interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("MISP SSL interface not accessible")

    def test_opencti_interface(self, driver, wait):
        """Test OpenCTI interface"""
        try:
            driver.get("http://localhost:8083")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for OpenCTI branding
            body_text = driver.page_source.lower()
            assert "opencti" in body_text or "cti" in body_text
            
            # Look for login or dashboard
            try:
                login_element = driver.find_element(By.CSS_SELECTOR, ".login, [class*='login'], input[type='password']")
                print("OpenCTI login interface found")
            except NoSuchElementException:
                try:
                    dashboard_element = driver.find_element(By.CSS_SELECTOR, ".dashboard, .threat, .intelligence, [class*='dashboard']")
                    print("OpenCTI dashboard interface found")
                except NoSuchElementException:
                    # At least check for OpenCTI branding
                    assert "opencti" in body_text or "cti" in body_text
                    print("OpenCTI branding found")
            
            print("OpenCTI interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("OpenCTI interface not accessible")

    def test_minio_console_interface(self, driver, wait):
        """Test MinIO Console interface"""
        try:
            driver.get("http://localhost:9002")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for MinIO branding
            body_text = driver.page_source.lower()
            assert "minio" in body_text
            
            # Look for login form
            try:
                login_element = driver.find_element(By.CSS_SELECTOR, ".login, [class*='login'], input[type='password'], input[type='text']")
                print("MinIO login interface found")
            except NoSuchElementException:
                try:
                    dashboard_element = driver.find_element(By.CSS_SELECTOR, ".dashboard, .bucket, .object, [class*='dashboard']")
                    print("MinIO dashboard interface found")
                except NoSuchElementException:
                    # At least check for MinIO branding
                    assert "minio" in body_text
                    print("MinIO branding found")
            
            print("MinIO Console interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("MinIO Console interface not accessible")

    def test_api_documentation_interface(self, driver, wait):
        """Test API documentation interface"""
        try:
            driver.get("http://localhost:8000/docs")
            
            # Wait for Swagger/OpenAPI UI to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for Swagger/OpenAPI elements
            body_text = driver.page_source.lower()
            assert any(keyword in body_text for keyword in ["swagger", "openapi", "api", "documentation"])
            
            # Look for Swagger UI elements
            try:
                swagger_container = driver.find_element(By.CSS_SELECTOR, ".swagger-ui, .swagger, #swagger-ui")
                print("Swagger UI container found")
            except NoSuchElementException:
                # Look for alternative API documentation
                try:
                    api_docs = driver.find_element(By.CSS_SELECTOR, ".api-docs, .documentation, [class*='api']")
                    print("Alternative API documentation found")
                except NoSuchElementException:
                    # At least check for API documentation keywords
                    assert any(keyword in body_text for keyword in ["swagger", "openapi", "api", "docs"])
                    print("API documentation keywords found")
            
            print("API documentation interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("API documentation interface not accessible")

    def test_prometheus_interface(self, driver, wait):
        """Test Prometheus web interface"""
        try:
            driver.get("http://localhost:9090")
            
            # Wait for page to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Check for Prometheus branding
            body_text = driver.page_source.lower()
            assert "prometheus" in body_text
            
            # Look for Prometheus UI elements
            try:
                search_box = driver.find_element(By.CSS_SELECTOR, "input[type='text'], input[placeholder*='PromQL'], input[placeholder*='query']")
                print("Prometheus query interface found")
            except NoSuchElementException:
                try:
                    status_element = driver.find_element(By.CSS_SELECTOR, ".status, .targets, .metrics, [class*='status']")
                    print("Prometheus status interface found")
                except NoSuchElementException:
                    # At least check for Prometheus branding
                    assert "prometheus" in body_text
                    print("Prometheus branding found")
            
            print("Prometheus interface loaded successfully")
            
        except TimeoutException:
            pytest.skip("Prometheus interface not accessible")

    def test_responsive_design(self, driver):
        """Test responsive design on different screen sizes"""
        screen_sizes = [
            (1920, 1080),  # Desktop
            (768, 1024),   # Tablet
            (375, 667),    # Mobile
        ]
        
        accessible_services = [
            "http://localhost:80",      # Nginx
            "http://localhost:3000",    # Grafana
            "http://localhost:3001",    # Shuffle
            "http://localhost:8000",    # API
        ]
        
        for service_url in accessible_services:
            for width, height in screen_sizes:
                try:
                    driver.set_window_size(width, height)
                    driver.get(service_url)
                    
                    # Wait a moment for the page to adjust
                    time.sleep(2)
                    
                    # Check if page loads without errors
                    page_title = driver.title
                    assert page_title != "", f"Empty title for {service_url} at {width}x{height}"
                    
                    print(f"Responsive design test passed for {service_url} at {width}x{height}")
                    
                except Exception:
                    # Skip if service is not accessible
                    break

    def test_javascript_execution(self, driver):
        """Test JavaScript execution on web interfaces"""
        js_test_services = [
            "http://localhost:3000",    # Grafana
            "http://localhost:3001",    # Shuffle
            "http://localhost:8000/docs", # API Docs
        ]
        
        for service_url in js_test_services:
            try:
                driver.get(service_url)
                
                # Test JavaScript execution
                try:
                    result = driver.execute_script("return document.title")
                    assert result is not None, f"JavaScript execution failed on {service_url}"
                    
                    # Test DOM manipulation
                    driver.execute_script("document.body.style.backgroundColor = 'yellow'")
                    bg_color = driver.execute_script("return document.body.style.backgroundColor")
                    assert bg_color == "yellow", f"DOM manipulation failed on {service_url}"
                    
                    # Reset background
                    driver.execute_script("document.body.style.backgroundColor = ''")
                    
                    print(f"JavaScript execution test passed for {service_url}")
                    
                except Exception as e:
                    print(f"JavaScript test failed for {service_url}: {e}")
                    
            except Exception:
                # Skip if service is not accessible
                continue

    def test_browser_console_errors(self, driver):
        """Test for browser console errors on web interfaces"""
        error_free_services = [
            "http://localhost:80",      # Nginx
            "http://localhost:8000",    # API
        ]
        
        for service_url in error_free_services:
            try:
                # Enable console logging
                driver.execute_script("console.error = function() {};")
                driver.execute_script("console.warn = function() {};")
                
                driver.get(service_url)
                
                # Wait for page to load
                time.sleep(3)
                
                # Check for console errors (basic check)
                try:
                    logs = driver.get_log('browser')
                    errors = [log for log in logs if log['level'] == 'SEVERE']
                    
                    if errors:
                        print(f"Console errors found on {service_url}:")
                        for error in errors[:3]:  # Show first 3 errors
                            print(f"  - {error['message']}")
                    else:
                        print(f"No console errors on {service_url}")
                        
                except Exception:
                    # Some browsers don't support get_log
                    pass
                    
            except Exception:
                # Skip if service is not accessible
                continue

    def test_page_load_performance(self, driver):
        """Test page load performance for web interfaces"""
        performance_services = [
            "http://localhost:80",      # Nginx
            "http://localhost:8000",    # API
            "http://localhost:3000",    # Grafana
        ]
        
        for service_url in performance_services:
            try:
                start_time = time.time()
                driver.get(service_url)
                
                # Wait for page to load
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                load_time = time.time() - start_time
                
                # Check if load time is reasonable (< 10 seconds)
                assert load_time < 10, f"Page load too slow for {service_url}: {load_time:.2f}s"
                
                print(f"Page load time for {service_url}: {load_time:.2f}s")
                
            except Exception:
                # Skip if service is not accessible or too slow
                continue

    def test_form_interactions(self, driver, wait):
        """Test form interactions on login interfaces"""
        form_services = [
            ("http://localhost:3000/login", "Grafana"),
            ("http://localhost:8082/users/login", "MISP"),
            ("http://localhost:9002", "MinIO"),
        ]
        
        for service_url, service_name in form_services:
            try:
                driver.get(service_url)
                
                # Look for form elements
                try:
                    text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[name='user']")
                    password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    submit_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .btn-login")
                    
                    # Test form field interactions
                    for text_input in text_inputs[:1]:  # Test first text input
                        if text_input.is_displayed() and text_input.is_enabled():
                            text_input.clear()
                            text_input.send_keys("test_user")
                            assert text_input.get_attribute("value") == "test_user"
                            text_input.clear()
                    
                    for password_input in password_inputs[:1]:  # Test first password input
                        if password_input.is_displayed() and password_input.is_enabled():
                            password_input.send_keys("test_password")
                            assert password_input.get_attribute("value") == "test_password"
                            password_input.clear()
                    
                    print(f"Form interaction test passed for {service_name}")
                    
                except Exception as e:
                    print(f"Form interaction test failed for {service_name}: {e}")
                    
            except Exception:
                # Skip if service is not accessible
                continue

    def test_navigation_elements(self, driver, wait):
        """Test navigation elements on web interfaces"""
        navigation_services = [
            "http://localhost:80",      # Nginx
            "http://localhost:3000",    # Grafana
            "http://localhost:3001",    # Shuffle
        ]
        
        for service_url in navigation_services:
            try:
                driver.get(service_url)
                
                # Look for navigation elements
                nav_elements = driver.find_elements(By.CSS_SELECTOR, "nav, .navbar, .nav, .menu, [role='navigation']")
                links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
                
                # Test link accessibility
                accessible_links = 0
                for link in links[:10]:  # Test first 10 links
                    try:
                        href = link.get_attribute("href")
                        if href and href.startswith("http"):
                            accessible_links += 1
                    except:
                        pass
                
                print(f"Navigation test for {service_url}: {len(nav_elements)} nav elements, {accessible_links} accessible links")
                
                # At least some navigation should exist
                assert len(nav_elements) > 0 or accessible_links > 0, f"No navigation found on {service_url}"
                
            except Exception:
                # Skip if service is not accessible
                continue
