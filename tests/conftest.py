#!/usr/bin/env python3
"""
pytest configuration for SOAR Ransomware Lab
Provides common fixtures and configuration for all tests
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


def get_headless_mode():
    """Determine if tests should run in headless mode"""
    # Default to False (visible browser) unless explicitly set to True
    headless_env = os.getenv('HEADLESS', '').lower()
    return headless_env in ('true', '1', 'yes')


@pytest.fixture(scope="session")
def chrome_options():
    """Provide Chrome options with configurable headless mode"""
    options = Options()
    
    # Configure headless mode based on environment variable
    if get_headless_mode():
        options.add_argument('--headless')
        print("Running Chrome in HEADLESS mode")
    else:
        print("Running Chrome in VISIBLE mode")
        # Maximize window for visible mode
        options.add_argument('--start-maximized')
    
    # Common Chrome options for stability
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Additional stability options
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    return options


@pytest.fixture(scope="class")
def driver(chrome_options):
    """Setup Chrome driver for browser testing"""
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        yield driver
    except WebDriverException as e:
        # Don't skip - let the test handle the driver unavailability
        # Tests should handle this gracefully within their logic
        raise Exception(f"Chrome WebDriver not available: {e}")
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass


@pytest.fixture(scope="function")
def driver_function(chrome_options):
    """Setup Chrome driver for individual test functions"""
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        yield driver
    except WebDriverException as e:
        # Don't skip - let the test handle the driver unavailability
        # Tests should handle this gracefully within their logic
        raise Exception(f"Chrome WebDriver not available: {e}")
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass


# Docker tests should run regardless of Docker availability
# Tests should handle Docker unavailability gracefully within the test logic
# This ensures all tests remain active as required by project standards


# Custom markers
pytest_plugins = []

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers", "browser: marks tests as browser tests requiring Selenium"
    )
    config.addinivalue_line(
        "markers", "docker: marks tests as requiring Docker"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
